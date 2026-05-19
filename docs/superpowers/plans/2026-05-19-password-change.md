# Password Change Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow an authenticated user to change their own password, with the same min-8-chars validation as signup, current-password verification, and full session invalidation on success.

**Architecture:** New endpoint `POST /api/v1/auth/change-password` (requires Bearer + current_password). Service mutates `users.password_hash` and clears `users.refresh_jti`. Route clears refresh cookie. Frontend posts to it from a card on the profile page, clears local auth state, and redirects to `/login`.

**Tech Stack:** FastAPI + slowapi, SQLAlchemy async + bcrypt, Pydantic v2; Next.js 16 + React 19, TanStack Query is irrelevant (no cache invalidation needed), react-hook-form + Zod, Vitest.

**Reference spec:** `docs/superpowers/specs/2026-05-19-password-change-design.md`

---

## File Structure

**Backend (modify):**
- `backend/src/schemas/auth.py` — add `PasswordChangeRequest` (one schema, ~12 lines).
- `backend/src/services/auth_service.py` — add `AuthService.change_password` (~25 lines).
- `backend/src/api/routes/auth.py` — add `POST /auth/change-password` route (~15 lines).
- `backend/tests/test_auth_service.py` — append `TestChangePassword` class (3 tests).
- `backend/tests/test_routes_auth.py` — append `TestChangePassword` class (5 tests).

**Frontend (create + modify):**
- `frontend/lib/api/auth.ts` — add `changePassword(currentPassword, newPassword)` function.
- `frontend/lib/api/auth.test.ts` — **new** test file (no existing tests for this module).
- `frontend/components/profile/ChangePasswordCard.tsx` — **new** component (the directory does not exist yet).
- `frontend/app/(app)/(chat)/profile/page.tsx` — mount the card under the existing account card.

---

## Task 1: Backend — `AuthService.change_password` (TDD)

**Files:**
- Test: `backend/tests/test_auth_service.py` (append `TestChangePassword`)
- Create schema: `backend/src/schemas/auth.py` (add `PasswordChangeRequest`)
- Modify: `backend/src/services/auth_service.py` (add `change_password` method)

- [ ] **Step 1: Write the failing service tests**

Append the following at the end of `backend/tests/test_auth_service.py`:

```python
# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------


class TestChangePassword:
    """Service-level tests for AuthService.change_password.

    Covers the happy path (rehash + jti cleared), wrong current password
    (raises 400, no state changes), and new == current rejection.
    """

    async def test_success_updates_hash_and_clears_refresh_jti(
        self, mock_session, user_factory
    ):
        from src.schemas.auth import PasswordChangeRequest

        user = user_factory()
        user.refresh_jti = "active-jti"
        original_hash = user.password_hash
        mock_session.execute.return_value = _make_execute_result(user)

        service = AuthService(mock_session)
        data = PasswordChangeRequest(
            current_password="password123",
            new_password="brand-new-password",
        )
        await service.change_password(user.id, data)

        # password_hash was rotated (different bytes, verifies against the new
        # password — not the old one).
        assert user.password_hash != original_hash
        import bcrypt
        assert bcrypt.checkpw(b"brand-new-password", user.password_hash.encode())
        assert not bcrypt.checkpw(b"password123", user.password_hash.encode())
        # All refresh sessions invalidated.
        assert user.refresh_jti is None
        mock_session.commit.assert_awaited()

    async def test_wrong_current_password_raises_400(
        self, mock_session, user_factory
    ):
        from src.schemas.auth import PasswordChangeRequest

        user = user_factory()
        user.refresh_jti = "active-jti"
        original_hash = user.password_hash
        mock_session.execute.return_value = _make_execute_result(user)

        service = AuthService(mock_session)
        data = PasswordChangeRequest(
            current_password="wrong-current",
            new_password="brand-new-password",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(user.id, data)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Current password is incorrect"
        # No mutation occurred.
        assert user.password_hash == original_hash
        assert user.refresh_jti == "active-jti"
        mock_session.commit.assert_not_awaited()

    async def test_new_equals_current_raises_400(self, mock_session, user_factory):
        from src.schemas.auth import PasswordChangeRequest

        user = user_factory()
        user.refresh_jti = "active-jti"
        original_hash = user.password_hash
        mock_session.execute.return_value = _make_execute_result(user)

        service = AuthService(mock_session)
        # Both current and new are the seeded password.
        data = PasswordChangeRequest(
            current_password="password123",
            new_password="password123",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(user.id, data)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "New password must be different from current password"
        assert user.password_hash == original_hash
        assert user.refresh_jti == "active-jti"
        mock_session.commit.assert_not_awaited()
```

- [ ] **Step 2: Run the new tests — confirm they fail**

Run from `backend/`:
```bash
uv run pytest tests/test_auth_service.py::TestChangePassword -vv
```
Expected: 3 tests collected, all fail with `ImportError`/`AttributeError` referencing `PasswordChangeRequest` or `change_password`.

- [ ] **Step 3: Add `PasswordChangeRequest` schema**

Edit `backend/src/schemas/auth.py`. Append at the end of the file (preserving the existing `_MIN_PASSWORD_LEN` import-time constant at the top):

```python
class PasswordChangeRequest(BaseModel):
    """Body schema for POST /api/v1/auth/change-password.

    The new_password rule mirrors UserCreate (signup): at least 8 chars.
    current_password has no length rule — it must just match what is in
    the database, which the service enforces by bcrypt-verifying it.
    """

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < _MIN_PASSWORD_LEN:
            raise ValueError("password must be at least 8 characters")
        return v
```

- [ ] **Step 4: Implement `AuthService.change_password`**

Edit `backend/src/services/auth_service.py`. Add this method inside the `AuthService` class (place it right after `refresh`, before `logout`):

```python
    async def change_password(
        self, user_id: uuid.UUID, data: "PasswordChangeRequest"
    ) -> None:
        """Verify current password, rehash the new one, invalidate all sessions.

        Side effects on success:
          * users.password_hash is rotated to bcrypt(new_password).
          * users.refresh_jti is cleared — every active refresh token across
            every device is invalidated. The route is responsible for also
            clearing the refresh cookie on the current response.

        Raises:
            HTTPException 401: user not found or inactive (defensive — the
                route's get_current_user dependency already filters these
                cases, but the service revalidates so it stays safe to call
                from other entry points).
            HTTPException 400: current_password does not match, OR
                new_password equals the current password.
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not _verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        if _verify_password(data.new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        user.password_hash = _hash_password(data.new_password)
        user.refresh_jti = None
        await self.session.commit()
```

Also update the imports at the top of `backend/src/services/auth_service.py`. Find:

```python
from src.core.security import (
    _BCRYPT_ROUNDS,
    _verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
```

Add `_hash_password` to that import list (alphabetical order):

```python
from src.core.security import (
    _BCRYPT_ROUNDS,
    _hash_password,
    _verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
```

And update the schema import. Find:
```python
from src.schemas.auth import LoginRequest, TokenPair
```
Change to:
```python
from src.schemas.auth import LoginRequest, PasswordChangeRequest, TokenPair
```

Then in the method signature replace the forward-reference string `"PasswordChangeRequest"` with the bare `PasswordChangeRequest` since the import now exists:

```python
    async def change_password(
        self, user_id: uuid.UUID, data: PasswordChangeRequest
    ) -> None:
```

- [ ] **Step 5: Run the service tests — confirm they pass**

```bash
uv run pytest tests/test_auth_service.py::TestChangePassword -vv
```
Expected: 3 passed.

- [ ] **Step 6: Run the full service test file to confirm no regression**

```bash
uv run pytest tests/test_auth_service.py -vv
```
Expected: every existing test still passes alongside the 3 new ones.

- [ ] **Step 7: Commit**

```bash
git add backend/src/schemas/auth.py backend/src/services/auth_service.py backend/tests/test_auth_service.py
git commit -m "$(cat <<'EOF'
feat(auth): AuthService.change_password — verify + rehash + invalidate sessions

Adds PasswordChangeRequest schema (8-char min, same as signup) and
service method that rotates password_hash and clears refresh_jti when
the current password verifies. 400 on wrong current or no-op (new == current).
EOF
)"
```

---

## Task 2: Backend — `POST /auth/change-password` route (TDD)

**Files:**
- Test: `backend/tests/test_routes_auth.py` (append `TestChangePassword`)
- Modify: `backend/src/api/routes/auth.py` (add route)

- [ ] **Step 1: Write the failing route tests**

Append at the end of `backend/tests/test_routes_auth.py`:

```python
# ---------------------------------------------------------------------------
# POST /api/v1/auth/change-password
# ---------------------------------------------------------------------------


class TestChangePassword:
    async def test_success_returns_204_and_clears_cookie(self, test_app):
        """Happy path: 204, AuthService.change_password is called with the
        current user's id, and the refresh cookie is cleared in the response."""
        user = _make_user_read(email="me@example.com")
        test_app.dependency_overrides[get_current_user] = lambda: user

        mock_auth_svc = AsyncMock(spec=AuthService)
        test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "password123",
                    "new_password": "brand-new-password",
                },
                cookies={"refresh_token": "old.refresh.token"},
            )

        assert resp.status_code == _HTTP_204
        # Service called once with user id + request body
        mock_auth_svc.change_password.assert_awaited_once()
        called_user_id, called_data = mock_auth_svc.change_password.await_args.args
        assert called_user_id == user.id
        assert called_data.current_password == "password123"
        assert called_data.new_password == "brand-new-password"
        # Refresh cookie cleared (Set-Cookie clears with Path=/api/v1/auth)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert "Path=/api/v1/auth" in set_cookie

    async def test_missing_bearer_returns_401(self, test_app):
        """OAuth2PasswordBearer returns 401 when the Authorization header
        is absent — no dependency override so the real dependency runs."""
        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "password123",
                    "new_password": "brand-new-password",
                },
            )

        assert resp.status_code == _HTTP_401

    async def test_wrong_current_password_returns_400(self, test_app):
        user = _make_user_read()
        test_app.dependency_overrides[get_current_user] = lambda: user

        mock_auth_svc = AsyncMock(spec=AuthService)
        mock_auth_svc.change_password.side_effect = HTTPException(
            status_code=400, detail="Current password is incorrect"
        )
        test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "wrong",
                    "new_password": "brand-new-password",
                },
            )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Current password is incorrect"

    async def test_new_equals_current_returns_400(self, test_app):
        user = _make_user_read()
        test_app.dependency_overrides[get_current_user] = lambda: user

        mock_auth_svc = AsyncMock(spec=AuthService)
        mock_auth_svc.change_password.side_effect = HTTPException(
            status_code=400,
            detail="New password must be different from current password",
        )
        test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "password123",
                    "new_password": "password123",
                },
            )

        assert resp.status_code == 400
        assert "different from current" in resp.json()["detail"]

    async def test_short_new_password_returns_422(self, test_app):
        """Pydantic validator rejects new_password shorter than 8 chars."""
        user = _make_user_read()
        test_app.dependency_overrides[get_current_user] = lambda: user

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "password123",
                    "new_password": "short",
                },
            )

        assert resp.status_code == _HTTP_422
```

- [ ] **Step 2: Run the new tests — confirm they fail**

```bash
uv run pytest tests/test_routes_auth.py::TestChangePassword -vv
```
Expected: 5 tests collected, all fail with 404 Not Found (route does not exist yet) — except possibly `test_missing_bearer_returns_401` which may also 404.

- [ ] **Step 3: Implement the route**

Edit `backend/src/api/routes/auth.py`. First update the imports — find:

```python
from src.schemas.auth import AccessTokenResponse, LoginRequest, TokenPair
```
Change to:
```python
from src.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    PasswordChangeRequest,
    TokenPair,
)
```

Add `get_current_user` to the imports. Find:
```python
from src.core.security import get_current_user
```
(It is already imported — confirm; if not, add it.)

Also confirm `UserRead` is already imported — it is (used by the `/me` route).

Now append this route at the **end** of the file (after the `/me` route):

```python
@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    response: Response,
    data: PasswordChangeRequest,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    """Change the current user's password.

    Requires a valid Bearer access token AND the current password.  On
    success, every refresh token across all devices is invalidated (the
    service clears users.refresh_jti) and the refresh cookie is cleared
    on the current response. The frontend must clear its local auth
    state and redirect to /login.

    Errors:
      * 401 — Bearer missing/invalid/expired or user inactive.
      * 400 — current password wrong, or new password equals current.
      * 422 — new_password shorter than 8 characters.
      * 429 — rate limit (5/min per IP).
    """
    await auth_service.change_password(current_user.id, data)
    _clear_refresh_cookie(response)
```

- [ ] **Step 4: Run the route tests — confirm they pass**

```bash
uv run pytest tests/test_routes_auth.py::TestChangePassword -vv
```
Expected: 5 passed.

- [ ] **Step 5: Run lint + full test suite**

```bash
task test
```
Expected: lint passes (no ruff or mypy errors) and the full test suite passes including the 8 new tests (3 service + 5 route).

If `task test` fails on a lint rule, fix the offending line and re-run. Do not skip the lint.

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/routes/auth.py backend/tests/test_routes_auth.py
git commit -m "$(cat <<'EOF'
feat(auth): POST /api/v1/auth/change-password endpoint

Requires Bearer + current password (5/min IP rate-limit). On success
returns 204 and clears the refresh cookie; service-side every refresh
token is invalidated via refresh_jti=None.
EOF
)"
```

---

## Task 3: Frontend — `changePassword` API client (TDD)

**Files:**
- Modify: `frontend/lib/api/auth.ts`
- Create: `frontend/lib/api/auth.test.ts`

- [ ] **Step 1: Write the failing client tests**

Create `frontend/lib/api/auth.test.ts` with the following content:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { useAuthStore } from "@/lib/store/auth"

beforeEach(() => {
  useAuthStore.setState({ accessToken: "live-token", user: null })
  localStorage.clear()
  vi.restoreAllMocks()
  vi.resetModules()
})

describe("changePassword", () => {
  it("POSTs current + new password and clears auth on 204", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal("fetch", fetchMock)

    const { changePassword } = await import("./auth")
    await changePassword("password123", "brand-new-password")

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0]!
    expect(String(url)).toContain("/api/v1/auth/change-password")
    expect(options.method).toBe("POST")
    expect(JSON.parse(options.body as string)).toEqual({
      current_password: "password123",
      new_password: "brand-new-password",
    })
    // Local auth state was wiped — user must re-login.
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it("throws server detail on 400 and does not clear auth", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Current password is incorrect" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      ),
    )
    vi.stubGlobal("fetch", fetchMock)

    const { changePassword } = await import("./auth")

    await expect(
      changePassword("wrong", "brand-new-password"),
    ).rejects.toThrow("Current password is incorrect")
    // Auth state untouched on failure.
    expect(useAuthStore.getState().accessToken).toBe("live-token")
  })

  it("falls back to generic message when body is not JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("oops", { status: 500 }),
    )
    vi.stubGlobal("fetch", fetchMock)

    const { changePassword } = await import("./auth")

    await expect(
      changePassword("password123", "brand-new-password"),
    ).rejects.toThrow("Failed to change password")
  })
})
```

- [ ] **Step 2: Run the new tests — confirm they fail**

From `frontend/`:
```bash
npm run test:run -- lib/api/auth.test.ts
```
Expected: 3 tests collected, all fail because `changePassword` is not exported from `./auth`.

- [ ] **Step 3: Implement `changePassword`**

Edit `frontend/lib/api/auth.ts`. Append at the end of the file:

```typescript
export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const res = await apiClient("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
  if (!res.ok) {
    let detail = "Failed to change password"
    try {
      const err = await res.json()
      if (typeof err.detail === "string") detail = err.detail
    } catch { /* non-JSON body, use fallback */ }
    throw new Error(detail)
  }
  // Server invalidated every refresh token; clear local state so the
  // in-memory access token cannot be used after the password rotation.
  useAuthStore.getState().clearAuth()
}
```

- [ ] **Step 4: Run the client tests — confirm they pass**

```bash
npm run test:run -- lib/api/auth.test.ts
```
Expected: 3 passed.

- [ ] **Step 5: Run the full frontend test suite to confirm no regression**

```bash
npm run test:run
```
Expected: every existing test plus the 3 new ones pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api/auth.ts frontend/lib/api/auth.test.ts
git commit -m "$(cat <<'EOF'
feat(api): frontend changePassword() client

Posts current + new password to /api/v1/auth/change-password.  On 204
clears local auth state (so the in-memory access token is no longer
usable); on 4xx surfaces the server's detail message to the caller.
EOF
)"
```

---

## Task 4: Frontend — `ChangePasswordCard` component + profile mount

**Files:**
- Create: `frontend/components/profile/ChangePasswordCard.tsx`
- Modify: `frontend/app/(app)/(chat)/profile/page.tsx`

There is no test step for this task — `ChangePasswordCard` is a thin form wrapper over `changePassword` (which is already covered by Vitest in Task 3); render testing the form is low-ROI here. End-to-end manual verification happens in Task 5.

- [ ] **Step 1: Create the component directory**

```bash
mkdir -p frontend/components/profile
```
Expected: directory created (no error).

- [ ] **Step 2: Write `ChangePasswordCard.tsx`**

Create `frontend/components/profile/ChangePasswordCard.tsx`:

```tsx
"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { changePassword } from "@/lib/api/auth"

const schema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required"),
    newPassword: z.string().min(8, "Minimum 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  })
  .refine((d) => d.newPassword !== d.currentPassword, {
    message: "New password must be different from current",
    path: ["newPassword"],
  })

type FormData = z.infer<typeof schema>

export function ChangePasswordCard() {
  const router = useRouter()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  async function onSubmit(data: FormData) {
    try {
      await changePassword(data.currentPassword, data.newPassword)
      toast.success("Password changed. Please sign in again.")
      router.push("/login")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to change password")
    }
  }

  return (
    <Card className="border-border mt-6">
      <CardHeader>
        <CardTitle className="font-mono text-sm">change password</CardTitle>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="currentPassword">Current password</Label>
            <Input
              id="currentPassword"
              type="password"
              autoComplete="current-password"
              {...register("currentPassword")}
            />
            {errors.currentPassword && (
              <p className="text-xs text-destructive">{errors.currentPassword.message}</p>
            )}
          </div>
          <div className="space-y-1">
            <Label htmlFor="newPassword">New password</Label>
            <Input
              id="newPassword"
              type="password"
              autoComplete="new-password"
              {...register("newPassword")}
            />
            {errors.newPassword && (
              <p className="text-xs text-destructive">{errors.newPassword.message}</p>
            )}
          </div>
          <div className="space-y-1">
            <Label htmlFor="confirmPassword">Confirm new password</Label>
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              {...register("confirmPassword")}
            />
            {errors.confirmPassword && (
              <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
            )}
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "changing..." : "change password"}
          </Button>
        </CardContent>
      </form>
    </Card>
  )
}
```

- [ ] **Step 3: Mount the card in the profile page**

Edit `frontend/app/(app)/(chat)/profile/page.tsx`. At the top, add the import alongside the existing UI imports:

```tsx
import { ChangePasswordCard } from "@/components/profile/ChangePasswordCard"
```

Then locate the existing `<Card className="border-border">` block in the returned JSX (the one containing "account details"). Immediately after its closing `</Card>` and **before** the outer wrapper's closing `</div>`, add:

```tsx
        <ChangePasswordCard />
```

The final JSX of the returned wrapper should look like:

```tsx
  return (
    <div className="p-8 max-w-2xl w-full">
      <div className="flex items-center gap-3 mb-6">
        {/* ...heading + badges unchanged... */}
      </div>

      <Card className="border-border">
        {/* ...existing account-details card unchanged... */}
      </Card>

      <ChangePasswordCard />
    </div>
  )
```

- [ ] **Step 4: Type-check and build the frontend**

```bash
npm run build
```
Expected: build succeeds. If TypeScript fails on a missing import or a mismatched prop, fix the diagnostic and re-run.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/profile/ChangePasswordCard.tsx frontend/app/\(app\)/\(chat\)/profile/page.tsx
git commit -m "$(cat <<'EOF'
feat(profile): change-password card on /profile

Adds a card below account details with current/new/confirm fields,
Zod-validated (8-char min, must differ from current, must match confirm).
On success: toast + redirect to /login (changePassword clears local auth).
EOF
)"
```

---

## Task 5: End-to-end manual verification

Per `CLAUDE.md`: "For UI or frontend changes, start the dev server and use the feature in a browser before reporting the task as complete." This task is a manual smoke test — no code changes, no commit.

- [ ] **Step 1: Start the backend dev server**

In a terminal at `backend/`:
```bash
uv run aegra dev
```
Expected: server boots on `http://localhost:2026`, runs migrations, no errors in the log.

- [ ] **Step 2: Start the frontend dev server**

In a second terminal at `frontend/`:
```bash
npm run dev
```
Expected: Next.js dev server on `http://localhost:3000`.

- [ ] **Step 3: Verify the happy path**

1. Open `http://localhost:3000` in a browser. Log in with any existing account (or register at `/signup` then come back).
2. Navigate to `/profile`. Confirm the **change password** card is rendered below account details with 3 password fields and a `change password` button.
3. Submit with the **wrong current password** + a new password ≥ 8 chars. Expected: a destructive toast appears with `Current password is incorrect`; you stay on `/profile`; you are still logged in.
4. Submit with the **correct current password** but a **new password shorter than 8 chars**. Expected: Zod inline error `Minimum 8 characters`; the request is not sent (no network call in DevTools → Network).
5. Submit with the correct current password, a new password ≥ 8 chars, and a **mismatching confirmation**. Expected: inline error `Passwords don't match` on the confirm field; no network call.
6. Submit with the correct current password, a valid new password matching the confirmation, but **identical to the current password**. Expected: inline error `New password must be different from current` on the new-password field; no network call.
7. Submit with valid current password, a valid new password ≠ current, with matching confirmation. Expected: success toast `Password changed. Please sign in again.`; the browser navigates to `/login`. The auth Zustand store is empty (check DevTools Application → Local Storage).
8. On `/login`, try the **old password**. Expected: `Invalid credentials` toast.
9. On `/login`, try the **new password**. Expected: login succeeds, you land on the assistant picker (`/assistants`).

- [ ] **Step 4: Verify session invalidation across tabs**

1. Log in again in a new browser profile or incognito window (call this **Tab B**), so you have two active sessions for the same user.
2. In your main browser (**Tab A**), navigate to `/profile` and change the password successfully.
3. Tab A is now logged out as expected.
4. In Tab B (still showing the assistant picker or any app screen), navigate or refresh. Expected: a network request 401s → `apiClient` calls `/auth/refresh`, the refresh fails (server-side `refresh_jti` was cleared by the password change), `apiClient` redirects Tab B to `/login`. Tab B can no longer access the app with its old session.

- [ ] **Step 5: Stop the dev servers**

`Ctrl+C` in both terminals.

If everything in steps 3 and 4 behaved as described, the feature is done. If any step diverges, write the divergence down and stop — do not commit or report success.

---

## Self-Review Notes

Performed before saving:

1. **Spec coverage:**
   - Schema with min-8 rule → Task 1, Step 3.
   - `change_password` service (verify, rehash, clear jti, 400 paths) → Task 1, Steps 1+4.
   - Route with rate limit + `_clear_refresh_cookie` → Task 2, Step 3.
   - Backend tests (3 service + 5 route) → Tasks 1, 2.
   - Frontend `changePassword` clearing auth → Task 3, Step 3.
   - `ChangePasswordCard` with Zod (8-char + confirm + differs-from-current) → Task 4, Step 2.
   - Mount in `/profile` → Task 4, Step 3.
   - Redirect to `/login` on success → Task 4, Step 2 (`router.push("/login")`).
   - Session-invalidation behavior across tabs → Task 5, Step 4.
   No gaps.
2. **Placeholders:** None. Every step contains the exact code or exact command.
3. **Type consistency:**
   - `PasswordChangeRequest` field names `current_password` / `new_password` are used consistently in schema, service, route tests, route handler, frontend API body, and zod-to-camelCase mapping in the component.
   - `changePassword(currentPassword, newPassword)` argument order matches the order used in the component (`data.currentPassword, data.newPassword`).
   - HTTP status codes consistent: 204 success, 400 on wrong current / no-op, 422 on Pydantic validation, 401 on missing bearer.
