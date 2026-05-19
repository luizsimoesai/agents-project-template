"""Tests for runtime model selection: Context, _load, and configurable_model."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agent.model import (
    Context,
    _load,
    _split_provider,
    configurable_model,
    dynamic_system_prompt,
)

# ---------------------------------------------------------------------------
# _split_provider — accepts both "provider/model" and "provider:model"
# ---------------------------------------------------------------------------


class TestSplitProvider:
    def test_slash_separator(self) -> None:
        assert _split_provider("openai/gpt-4o") == ("openai", "gpt-4o")

    def test_colon_separator(self) -> None:
        assert _split_provider("anthropic:claude-sonnet-4-6") == (
            "anthropic",
            "claude-sonnet-4-6",
        )

    def test_ollama_with_tag_preserves_inner_colon(self) -> None:
        # ollama/llama3:8b → ('ollama', 'llama3:8b') — first separator wins.
        assert _split_provider("ollama/llama3:8b") == ("ollama", "llama3:8b")

    def test_no_separator_returns_none(self) -> None:
        assert _split_provider("just-a-model-name") is None

    def test_strips_whitespace_around_parts(self) -> None:
        assert _split_provider(" openai / gpt-4o ") == ("openai", "gpt-4o")


# ---------------------------------------------------------------------------
# _load — calls init_chat_model with the right arguments
# ---------------------------------------------------------------------------


class TestLoad:
    def setup_method(self) -> None:
        # lru_cache survives across tests — clear it so call counts are accurate.
        _load.cache_clear()

    def test_passes_provider_and_model(self) -> None:
        with patch("src.agent.model.init_chat_model") as mock:
            mock.return_value = MagicMock()
            _load("openai/gpt-4o")
            mock.assert_called_once_with("gpt-4o", model_provider="openai")

    def test_passes_base_url_when_given(self) -> None:
        with patch("src.agent.model.init_chat_model") as mock:
            mock.return_value = MagicMock()
            _load("ollama/llama3", base_url="http://localhost:11434")
            mock.assert_called_once_with(
                "llama3", model_provider="ollama", base_url="http://localhost:11434"
            )

    def test_colon_separator_works(self) -> None:
        with patch("src.agent.model.init_chat_model") as mock:
            mock.return_value = MagicMock()
            _load("anthropic:claude-sonnet-4-6")
            mock.assert_called_once_with(
                "claude-sonnet-4-6", model_provider="anthropic"
            )

    def test_no_separator_delegates_to_init_chat_model(self) -> None:
        with patch("src.agent.model.init_chat_model") as mock:
            mock.return_value = MagicMock()
            _load("opaque-model-id")
            mock.assert_called_once_with("opaque-model-id")

    def test_cached_across_calls_with_same_args(self) -> None:
        with patch("src.agent.model.init_chat_model") as mock:
            mock.return_value = MagicMock()
            _load("openai/gpt-4o")
            _load("openai/gpt-4o")
            assert mock.call_count == 1


# ---------------------------------------------------------------------------
# Context — defaults come from MODEL / MODEL_BASE_URL env vars
# ---------------------------------------------------------------------------


class TestContext:
    def test_explicit_model_wins_over_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL", "openai/gpt-4o-mini")
        ctx = Context(model="anthropic/claude-sonnet-4-6")
        assert ctx.model == "anthropic/claude-sonnet-4-6"

    def test_empty_model_falls_back_to_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL", "openai/gpt-4o-mini")
        ctx = Context()
        assert ctx.model == "openai/gpt-4o-mini"

    def test_base_url_falls_back_to_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MODEL", "ollama/llama3")
        monkeypatch.setenv("MODEL_BASE_URL", "http://litellm.example.com/v1")
        ctx = Context()
        assert ctx.model_base_url == "http://litellm.example.com/v1"

    def test_explicit_base_url_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MODEL_BASE_URL", "http://from-env.example.com")
        ctx = Context(
            model="ollama/llama3", model_base_url="http://explicit.example.com"
        )
        assert ctx.model_base_url == "http://explicit.example.com"


# ---------------------------------------------------------------------------
# configurable_model — wrap_model_call middleware
# ---------------------------------------------------------------------------


def _make_request(model: str = "openai/gpt-4o", model_base_url: str | None = None):
    """Build a minimal ModelRequest-shaped object the middleware can consume."""
    ctx = Context(model=model, model_base_url=model_base_url) if model else Context()
    request = MagicMock()
    request.runtime = SimpleNamespace(context=ctx)
    overridden = MagicMock(name="overridden_request")
    request.override = MagicMock(return_value=overridden)
    return request, overridden


class TestConfigurableModel:
    async def test_loads_model_from_context_and_overrides_request(self) -> None:
        fake_model = MagicMock(name="loaded_model")
        with patch("src.agent.model._load", return_value=fake_model) as mock_load:
            request, overridden = _make_request("openai/gpt-4o")
            handler_response = MagicMock(name="response")

            async def fake_handler(req):
                assert req is overridden
                return handler_response

            result = await configurable_model.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]

            mock_load.assert_called_once_with("openai/gpt-4o", None)
            request.override.assert_called_once_with(model=fake_model)
            assert result is handler_response

    async def test_passes_base_url_to_load(self) -> None:
        fake_model = MagicMock()
        with patch("src.agent.model._load", return_value=fake_model) as mock_load:
            request, _ = _make_request("ollama/llama3", "http://localhost:11434")

            async def fake_handler(req):
                return MagicMock()

            await configurable_model.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]
            mock_load.assert_called_once_with("ollama/llama3", "http://localhost:11434")

    async def test_raises_when_no_model_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Clear MODEL env var so Context.model is empty.
        monkeypatch.delenv("MODEL", raising=False)
        request, _ = _make_request(model="")

        async def fake_handler(req):
            return MagicMock()

        with pytest.raises(ValueError, match="No model configured"):
            await configurable_model.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]

    async def test_annotates_model_id_on_ai_messages(self) -> None:
        fake_model = MagicMock(name="loaded_model")
        with patch("src.agent.model._load", return_value=fake_model):
            request, _ = _make_request("openai/gpt-4o")
            ai_msg = AIMessage(content="hello")
            human_msg = HumanMessage(content="hi")
            tool_msg = ToolMessage(content="ok", tool_call_id="c1")
            response = SimpleNamespace(result=[human_msg, ai_msg, tool_msg])

            async def fake_handler(_req):
                return response

            result = await configurable_model.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]

            assert result is response
            assert ai_msg.additional_kwargs.get("model_id") == "openai/gpt-4o"
            # HumanMessage and ToolMessage must NOT be touched.
            assert "model_id" not in human_msg.additional_kwargs
            assert "model_id" not in tool_msg.additional_kwargs

    async def test_does_not_overwrite_existing_model_id(self) -> None:
        fake_model = MagicMock()
        with patch("src.agent.model._load", return_value=fake_model):
            request, _ = _make_request("openai/gpt-4o")
            ai_msg = AIMessage(content="hi", additional_kwargs={"model_id": "preset"})
            response = SimpleNamespace(result=[ai_msg])

            async def fake_handler(_req):
                return response

            result = await configurable_model.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]

            assert result is response
            assert ai_msg.additional_kwargs["model_id"] == "preset"


# ---------------------------------------------------------------------------
# dynamic_system_prompt — overrides system_message when ctx.system_prompt set
# ---------------------------------------------------------------------------


def _request_with_prompt(prompt: str | None):
    """Build a ModelRequest stub whose runtime.context exposes system_prompt."""
    ctx = Context(model="openai/gpt-4o", system_prompt=prompt)
    request = MagicMock()
    request.runtime = SimpleNamespace(context=ctx)
    overridden = MagicMock(name="overridden_request")
    request.override = MagicMock(return_value=overridden)
    return request, overridden


class TestDynamicSystemPrompt:
    async def test_overrides_system_message_when_set(self) -> None:
        request, overridden = _request_with_prompt("Respond in haiku.")
        captured: dict[str, object] = {}

        async def fake_handler(req):
            captured["req"] = req
            return MagicMock(name="response")

        await dynamic_system_prompt.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]

        request.override.assert_called_once()
        kwargs = request.override.call_args.kwargs
        assert isinstance(kwargs["system_message"], SystemMessage)
        assert kwargs["system_message"].content == "Respond in haiku."
        assert captured["req"] is overridden

    async def test_no_override_when_prompt_absent(self) -> None:
        request, _ = _request_with_prompt(None)

        async def fake_handler(req):
            assert req is request  # passthrough — no override
            return MagicMock()

        await dynamic_system_prompt.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]
        request.override.assert_not_called()

    async def test_no_override_when_prompt_empty(self) -> None:
        request, _ = _request_with_prompt("")

        async def fake_handler(req):
            assert req is request
            return MagicMock()

        await dynamic_system_prompt.awrap_model_call(request, fake_handler)  # type: ignore[attr-defined]
        request.override.assert_not_called()
