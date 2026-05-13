from unittest.mock import MagicMock, patch

from src.agent.utils import DynamicModel, load_chat_model


def test_load_chat_model_passes_base_url():
    with patch("src.agent.utils.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        load_chat_model("openai/gpt-4o", base_url="https://proxy.example.com")
        mock_init.assert_called_once_with(
            "gpt-4o", model_provider="openai", base_url="https://proxy.example.com"
        )


def test_load_chat_model_no_base_url_omits_kwarg():
    with patch("src.agent.utils.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        load_chat_model("openai/gpt-4o")
        mock_init.assert_called_once_with("gpt-4o", model_provider="openai")


def test_resolve_reads_model_id_from_configurable():
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        proxy = DynamicModel()
        config = {
            "configurable": {
                "model": "anthropic/claude-sonnet-4-6",
                "model_base_url": None,
            }
        }
        result = proxy._resolve(config)

        mock_load.assert_called_once_with("anthropic/claude-sonnet-4-6", None)
        assert result is mock_model


def test_resolve_reads_base_url_from_configurable():
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        proxy = DynamicModel()
        config = {
            "configurable": {
                "model": "ollama/llama3",
                "model_base_url": "http://localhost:11434",
            }
        }
        proxy._resolve(config)

        mock_load.assert_called_once_with("ollama/llama3", "http://localhost:11434")


def test_resolve_falls_back_to_env_var(monkeypatch):
    monkeypatch.setenv("MODEL", "openai/gpt-4o-mini")
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_load.return_value = MagicMock()
        proxy = DynamicModel()
        proxy._resolve({})
        mock_load.assert_called_once_with("openai/gpt-4o-mini", None)


def test_resolve_none_config_falls_back_to_env_var(monkeypatch):
    monkeypatch.setenv("MODEL", "openai/gpt-4o-mini")
    with patch("src.agent.utils._cached_load") as mock_load:
        mock_load.return_value = MagicMock()
        proxy = DynamicModel()
        proxy._resolve(None)
        mock_load.assert_called_once_with("openai/gpt-4o-mini", None)


def test_bind_tools_returns_new_proxy_with_tools():
    tool_a = MagicMock()
    tool_b = MagicMock()

    proxy = DynamicModel()
    bound = proxy.bind_tools([tool_a, tool_b])

    assert isinstance(bound, DynamicModel)
    assert bound is not proxy
    assert bound.bound_tools == [tool_a, tool_b]


def test_bind_tools_passes_kwargs():
    proxy = DynamicModel()
    bound = proxy.bind_tools([], tool_choice="any")
    assert bound.bound_kwargs == {"tool_choice": "any"}


def test_resolve_binds_tools_to_real_model():
    with patch("src.agent.utils._cached_load") as mock_load:
        real_model = MagicMock()
        bound_model = MagicMock()
        real_model.bind_tools.return_value = bound_model
        mock_load.return_value = real_model

        tool = MagicMock()
        proxy = DynamicModel(bound_tools=[tool])
        config = {"configurable": {"model": "openai/gpt-4o"}}
        result = proxy._resolve(config)

        real_model.bind_tools.assert_called_once_with([tool])
        assert result is bound_model


def test_invoke_delegates_to_resolved_model():
    with patch("src.agent.utils._cached_load") as mock_load:
        real_model = MagicMock()
        mock_load.return_value = real_model
        real_model.invoke.return_value = MagicMock()

        proxy = DynamicModel()
        config = {"configurable": {"model": "openai/gpt-4o"}}
        messages = [MagicMock()]
        proxy.invoke(messages, config)

        real_model.invoke.assert_called_once_with(messages, config)
