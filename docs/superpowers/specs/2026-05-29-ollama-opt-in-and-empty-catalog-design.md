# Ollama Opt-In & Empty Catalog — Design Spec

**Date:** 2026-05-29
**Status:** Draft
**Owner:** Luiz Simoes

## Overview

Today `task bootstrap` always seeds a local Ollama model (`ollama:llama3.2`) into
the catalog and force-promotes it to default whenever no cloud provider key was
configured. A user who skips every API key ends up with `ollama:llama3.2` as the
default model even though they may not have Ollama installed or that model pulled
— so the first chat fails with a runtime `ValueError`.

This design makes Ollama an **explicit opt-in** in the bootstrap wizard (the user
types a model name, the way other providers ask for an API key), stops forcing any
default the user did not ask for, and treats an **empty catalog as a valid, expected
state**. When no model is configured, bootstrap completes cleanly, the admin can add
a model later through the existing admin UI, and the chat surface guides the user
instead of crashing.

### Why this design

- **Don't seed infrastructure the user didn't ask for.** Forcing `ollama:llama3.2`
  assumes Ollama is installed and that model is pulled. Neither is guaranteed.
- **Default selection should reflect choice.** A default model the user never picked
  is surprising. The wizard should only auto-pick a default among providers/models the
  user actually configured.
- **Empty catalog is a normal first state.** With Ollama no longer forced, "no models
  configured" becomes common. It must be a guided, non-crashing state — consistent with
  the onboarding principle that empty states are part of onboarding (see
  `2026-05-23-onboarding-and-template-launch-design.md`).

### Scope

| In scope | Out of scope |
|---|---|
| Bootstrap CLI: Ollama opt-in step, default policy, empty catalog | Admin model CRUD UI (already supports Ollama: `provider` + `base_url` fields exist) |
| `seeds/models.yaml`: remove the Ollama entry (cloud-only catalog) | `AssistantForm` (no model field; creation is unaffected) |
| Frontend `ChatInput`: guard send when no active models | Verifying Ollama is running / the model is pulled (best-effort seed only) |
| Backend + frontend tests for the new behavior | Changing how cloud keys are prompted |

## Current behavior (ground truth)

- `configured_providers(env)` (`src/cli/bootstrap.py`) always starts with
  `{"ollama"}`, then adds cloud providers whose API key is non-placeholder.
- `seeds/models.yaml` contains an `ollama:llama3.2` entry with the curated
  `is_default: true` flag living on the Anthropic entry.
- `step_seed_models` → `filter_seeds_by_providers(catalogue, providers)` keeps every
  seed whose `provider` is in `providers`. Because `ollama` is always present, the
  Ollama seed is always kept; if the catalogue's default provider (anthropic) is not
  configured, `filter_seeds_by_providers` promotes the first survivor (ollama) to
  default.
- The assistant create form (`frontend/components/assistants/AssistantForm.tsx`) has
  no model field — model is chosen at chat time via `ModelPicker` inside
  `frontend/components/chat/ChatInput.tsx`.
- `ModelPicker` returns `null` when `models` is empty. `ChatInput` only renders the
  picker when `models.length > 0`, but its send button is gated solely on
  `!value.trim()` — so a user can send with no model.
- A run with no model reaches `configurable_model` (`src/agent/model.py`), which raises
  `ValueError("No model configured. Set MODEL in .env or pass via config.configurable.")`.
  `Context.__post_init__` falls back to the `MODEL` env var if set (empty by default).

## Design

### Backend — bootstrap & seed

**1. Catalog becomes cloud-only.**
Remove the `ollama:llama3.2` entry from `seeds/models.yaml`. The curated catalogue now
contains only Anthropic and OpenAI entries. The `is_default: true` flag stays on
`anthropic:claude-sonnet-4-6`.

**2. `configured_providers` no longer auto-includes Ollama.**
It returns only the cloud providers whose API key is non-placeholder. Ollama is handled
separately by the new step (below), not by catalogue filtering.

**3. New `step_ollama` — a `.env` step, not a DB step (renumber wizard to `/9`).**
Critical ordering: model rows can only be inserted **after** migrations (the cloud
seed runs in the DB phase, currently step 8). So the Ollama step does **not** touch the
DB. Like the API-key steps, it only records the user's choice in `.env`; the actual row
is seeded later in the DB phase from the re-hydrated env.

Placed in the `.env` mutation phase, right after the LLM provider keys step:

- **Interactive:**
  - `? Use a local Ollama model? [y/N]` (default No).
  - If yes: `? Ollama model name (e.g. llama3.2)` — free text.
  - Writes `OLLAMA_MODEL=<name>` to `.env` (and `OLLAMA_BASE_URL=http://localhost:11434`
    if not already present), via `update_env_file`.
- **Non-interactive:** if `OLLAMA_MODEL` is already in the environment / `.env` and
  non-placeholder, keep it; otherwise skip silently — same contract as cloud keys.
- **Idempotent:** if `.env` already has a non-placeholder `OLLAMA_MODEL`, skip the
  prompt and report "already configured".

The DB seed step (now step 9, inside `_run_db_steps`) reads `OLLAMA_MODEL` /
`OLLAMA_BASE_URL` from the re-hydrated env and, when present, inserts
`LLMModel(display_name="<name> (local)", model_id="ollama:<name>", provider="ollama",
base_url=<base_url>, is_active=True, is_default=False)` alongside the cloud catalogue
entries. The default flag is decided by the election pass below. The model name is
stored verbatim after `ollama:`; an inner `:tag` (e.g. `llama3:8b`) is preserved,
consistent with `_split_provider` in `model.py`. Seeding is idempotent: an existing
row with the same `model_id` is skipped.

**4. Default policy — "auto-default only among what was chosen".**
After the DB seed step has inserted both cloud and Ollama rows, exactly one model is
chosen as default (or none), in this priority order:

1. The catalogue's `is_default` entry **if its provider was configured**
   (`anthropic:claude-sonnet-4-6` when an Anthropic key is present).
2. Else the first seeded cloud model (catalogue order).
3. Else the Ollama model, if one was seeded.
4. Else **no default** — the catalog may legitimately be empty.

Enforcement guarantees at most one `is_default=True` row (same invariant as
`ModelService._set_default`: clear all, set one). Implementation note: the seed steps
insert rows with `is_default=False`, and a final "elect default" pass sets the single
default per the priority above. This avoids the current double-default risk of
inserting `is_default=True` directly.

**5. Empty catalog is valid.**
If neither a cloud key nor an Ollama model was configured, no rows are seeded and no
default is set. Bootstrap still exits 0. The completion panel gains a conditional line:

```
⚠ No LLM model configured. Add one at http://localhost:3000/admin before chatting.
```

shown only when no model was configured (empty catalog). Because the election pass
always sets a default when at least one row exists, "no default" and "empty catalog"
are the same condition.

### Frontend — empty catalog guard in chat

**6. `ChatInput.tsx` guards send when there are no active models.**
The chat view already fetches active models and passes them to `ChatInput`. Add:

- A derived `noModels = Array.isArray(models) && models.length === 0` (only when the
  consumer opts into model selection by passing `models` + `onModelChange`).
- When `noModels`: disable the send button and render an inline notice in place of the
  picker, e.g. *"No model configured — ask an admin to add one in /admin."*
- When models exist: unchanged (picker renders, send gated only on non-empty text).

This converts the current "send → stream crashes with `ValueError`" into a clear,
up-front message. The backend `ValueError` remains as defense-in-depth for API clients.

**7. No change to `AssistantForm` / assistant creation.**
Creating an assistant does not reference the catalog and continues to work with an
empty catalog.

## Data flow

```
bootstrap main()
  .env phase (sync):
    step 1: .env file        step 2: jwt secret
    step 3: db password       step 4: cloud LLM keys
    step 5: ollama (new) -> write OLLAMA_MODEL / OLLAMA_BASE_URL to .env
  infra phase:
    step 6: postgres          step 7: migrations
  DB phase (_run_db_steps, after re-hydrating env from .env):
    step 8: admin user
    step 9: seed models -> cloud catalogue rows + ollama row (all is_default=False)
            elect-default pass: set exactly one is_default per priority, or none
  completion panel: warn when no model was configured (empty catalog)
```

```
chat view -> useModels() -> ChatInput
  models.length > 0 -> ModelPicker + send (gated on text)
  models.length === 0 -> notice + send disabled
```

## Error handling

- `step_ollama` non-interactive with no `OLLAMA_MODEL`: skip silently (not an error).
- Empty catalog: not an error; bootstrap exits 0 with a warning line.
- Chat with empty catalog: send disabled in UI; backend `ValueError` retained for
  non-UI callers.
- Ollama model that doesn't actually exist on the host: out of scope to validate; the
  seed succeeds and the failure (if any) surfaces at chat time as it does today.

## Testing

**Backend (`tests/cli/`):**
- `step_ollama` (.env step) interactive: yes + model name → `.env` gains
  `OLLAMA_MODEL=<name>` and `OLLAMA_BASE_URL=http://localhost:11434`; No → `.env`
  unchanged. Idempotent: pre-existing non-placeholder `OLLAMA_MODEL` → prompt skipped.
- `step_ollama` non-interactive: `OLLAMA_MODEL` present → kept; absent → skipped.
- DB seed step: with `OLLAMA_MODEL` in env → one `ollama:<name>` row with the right
  `base_url`; idempotent (existing `model_id` skipped).
- Default election:
  - no providers, no ollama → empty catalog, no default.
  - only ollama → ollama model is default.
  - cloud only → catalogue default (Claude when anthropic configured).
  - cloud + ollama → catalogue cloud default wins; ollama not default.
- `filter_seeds_by_providers` / `seeds/models.yaml`: no Ollama entry remains.
- Existing `test_bootstrap_flow.py` updated for the new step count (`/9`) and the
  no-forced-ollama behavior. The fresh-clone import regression test stays.

**Frontend (`components/chat/`):**
- `ChatInput` with `models={[]}`: send button disabled + notice visible.
- `ChatInput` with non-empty `models`: unchanged (picker visible, send gated on text).

## Migration / compatibility notes

- This changes seed behavior only for **new** bootstraps. Existing installs that already
  have `ollama:llama3.2` as default are untouched (idempotent steps skip existing rows).
  An admin can deactivate/relabel it via the existing admin UI if desired.
- No DB schema change. No new migration.
- New env vars (`OLLAMA_MODEL`, `OLLAMA_BASE_URL`) are optional; document them in
  `.env.example` comments and in the `--non-interactive` help text.
