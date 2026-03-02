"""Tests for LLM provider protocol conformance and error handling."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from archex.exceptions import ProviderError
from archex.providers.base import LLMProvider, get_provider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_anthropic_mock() -> MagicMock:
    """Build a minimal mock of the anthropic SDK module."""
    sdk = MagicMock()
    client = MagicMock()
    sdk.Anthropic.return_value = client
    text_block = MagicMock()
    text_block.text = "response text"
    msg = MagicMock()
    msg.content = [text_block]
    client.messages.create.return_value = msg
    return sdk


def _make_openai_mock() -> MagicMock:
    """Build a minimal mock of the openai SDK module."""
    sdk = MagicMock()
    client = MagicMock()
    sdk.OpenAI.return_value = client
    choice = MagicMock()
    choice.message.content = "response text"
    resp = MagicMock()
    resp.choices = [choice]
    client.chat.completions.create.return_value = resp
    return sdk


# ---------------------------------------------------------------------------
# Protocol conformance tests
# ---------------------------------------------------------------------------


def test_anthropic_provider_satisfies_protocol() -> None:
    anthropic_mock = _make_anthropic_mock()
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        from archex.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider()
        assert isinstance(provider, LLMProvider)


def test_openai_provider_satisfies_protocol() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        from archex.providers.openai import OpenAIProvider

        provider = OpenAIProvider()
        assert isinstance(provider, LLMProvider)


def test_openrouter_provider_satisfies_protocol() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        from archex.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider()
        assert isinstance(provider, LLMProvider)


# ---------------------------------------------------------------------------
# get_provider() factory tests
# ---------------------------------------------------------------------------


def test_get_provider_anthropic() -> None:
    anthropic_mock = _make_anthropic_mock()
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        from archex.providers.anthropic import AnthropicProvider

        provider = get_provider("anthropic")
        assert isinstance(provider, AnthropicProvider)
        assert provider.name == "anthropic"


def test_get_provider_openai() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        from archex.providers.openai import OpenAIProvider

        provider = get_provider("openai")
        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "openai"


def test_get_provider_openrouter() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        from archex.providers.openrouter import OpenRouterProvider

        provider = get_provider("openrouter")
        assert isinstance(provider, OpenRouterProvider)
        assert provider.name == "openrouter"


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent_provider")


# ---------------------------------------------------------------------------
# SDK not installed error handling
# ---------------------------------------------------------------------------


def test_anthropic_provider_raises_when_sdk_missing() -> None:
    with patch.dict(sys.modules, {"anthropic": None}):  # type: ignore[dict-item]
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        with pytest.raises(ImportError, match="anthropic"):
            mod.AnthropicProvider(api_key="test-key")


def test_openai_provider_raises_when_sdk_missing() -> None:
    with patch.dict(sys.modules, {"openai": None}):  # type: ignore[dict-item]
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        with pytest.raises(ImportError, match="openai"):
            mod.OpenAIProvider(api_key="test-key")


def test_openrouter_provider_raises_when_sdk_missing() -> None:
    with patch.dict(sys.modules, {"openai": None}):  # type: ignore[dict-item]
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        with pytest.raises(ImportError, match="openai"):
            mod.OpenRouterProvider(api_key="test-key")


# ---------------------------------------------------------------------------
# Provider name property tests
# ---------------------------------------------------------------------------


def test_anthropic_name() -> None:
    anthropic_mock = _make_anthropic_mock()
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "k"}),
    ):
        from archex.providers.anthropic import AnthropicProvider

        assert AnthropicProvider().name == "anthropic"


def test_openai_name() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "k"}),
    ):
        from archex.providers.openai import OpenAIProvider

        assert OpenAIProvider().name == "openai"


def test_openrouter_name() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "k"}),
    ):
        from archex.providers.openrouter import OpenRouterProvider

        assert OpenRouterProvider().name == "openrouter"


# ---------------------------------------------------------------------------
# Missing API key raises ProviderError
# ---------------------------------------------------------------------------


def test_anthropic_provider_raises_without_api_key() -> None:
    anthropic_mock = _make_anthropic_mock()
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {}, clear=True),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        with pytest.raises(ProviderError, match="API key"):
            mod.AnthropicProvider()


def test_openai_provider_raises_without_api_key() -> None:
    openai_mock = _make_openai_mock()
    with patch.dict(sys.modules, {"openai": openai_mock}), patch.dict("os.environ", {}, clear=True):
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        with pytest.raises(ProviderError, match="API key"):
            mod.OpenAIProvider()


# ---------------------------------------------------------------------------
# Anthropic complete() and complete_structured() tests
# ---------------------------------------------------------------------------


def test_anthropic_complete() -> None:
    anthropic_mock = _make_anthropic_mock()
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        provider = mod.AnthropicProvider()
        result = provider.complete("hello")
        assert result == "response text"


def test_anthropic_complete_with_system() -> None:
    anthropic_mock = _make_anthropic_mock()
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        provider = mod.AnthropicProvider()
        provider.complete("hello", system="be concise")
        call_kwargs = anthropic_mock.Anthropic.return_value.messages.create.call_args[1]
        assert call_kwargs.get("system") == "be concise"


def test_anthropic_complete_api_error() -> None:
    anthropic_mock = _make_anthropic_mock()
    anthropic_mock.Anthropic.return_value.messages.create.side_effect = RuntimeError("boom")
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        provider = mod.AnthropicProvider()
        with pytest.raises(ProviderError, match="Anthropic API error"):
            provider.complete("hello")


def test_anthropic_complete_structured() -> None:
    anthropic_mock = _make_anthropic_mock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "structured_output"
    tool_block.input = {"key": "value"}
    msg = MagicMock()
    msg.content = [tool_block]
    anthropic_mock.Anthropic.return_value.messages.create.return_value = msg
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        provider = mod.AnthropicProvider()
        result = provider.complete_structured("hello", schema={"type": "object"})
        assert result == {"key": "value"}


def test_anthropic_complete_structured_with_system() -> None:
    anthropic_mock = _make_anthropic_mock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "structured_output"
    tool_block.input = {"key": "value"}
    msg = MagicMock()
    msg.content = [tool_block]
    anthropic_mock.Anthropic.return_value.messages.create.return_value = msg
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        provider = mod.AnthropicProvider()
        provider.complete_structured("hello", schema={"type": "object"}, system="be precise")
        call_kwargs = anthropic_mock.Anthropic.return_value.messages.create.call_args[1]
        assert call_kwargs.get("system") == "be precise"


def test_anthropic_complete_structured_no_tool_use() -> None:
    anthropic_mock = _make_anthropic_mock()
    text_block = MagicMock()
    text_block.type = "text"
    msg = MagicMock()
    msg.content = [text_block]
    anthropic_mock.Anthropic.return_value.messages.create.return_value = msg
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        provider = mod.AnthropicProvider()
        with pytest.raises(ProviderError, match="tool_use"):
            provider.complete_structured("hello", schema={"type": "object"})


def test_anthropic_complete_structured_api_error() -> None:
    anthropic_mock = _make_anthropic_mock()
    anthropic_mock.Anthropic.return_value.messages.create.side_effect = RuntimeError("boom")
    with (
        patch.dict(sys.modules, {"anthropic": anthropic_mock}),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.anthropic as mod

        importlib.reload(mod)
        provider = mod.AnthropicProvider()
        with pytest.raises(ProviderError, match="Anthropic structured API error"):
            provider.complete_structured("hello", schema={"type": "object"})


# ---------------------------------------------------------------------------
# OpenAI complete() and complete_structured() tests
# ---------------------------------------------------------------------------


def test_openai_complete() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        provider = mod.OpenAIProvider()
        result = provider.complete("hello")
        assert result == "response text"


def test_openai_complete_with_system() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        provider = mod.OpenAIProvider()
        provider.complete("hello", system="be concise")
        call_kwargs = openai_mock.OpenAI.return_value.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "be concise"}


def test_openai_complete_api_error() -> None:
    openai_mock = _make_openai_mock()
    openai_mock.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("boom")
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        provider = mod.OpenAIProvider()
        with pytest.raises(ProviderError, match="OpenAI API error"):
            provider.complete("hello")


def test_openai_complete_structured() -> None:
    openai_mock = _make_openai_mock()
    choice = MagicMock()
    choice.message.content = '{"key": "value"}'
    resp = MagicMock()
    resp.choices = [choice]
    openai_mock.OpenAI.return_value.chat.completions.create.return_value = resp
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        provider = mod.OpenAIProvider()
        result = provider.complete_structured("hello", schema={"type": "object"})
        assert result == {"key": "value"}


def test_openai_complete_structured_with_system() -> None:
    openai_mock = _make_openai_mock()
    choice = MagicMock()
    choice.message.content = '{"key": "value"}'
    resp = MagicMock()
    resp.choices = [choice]
    openai_mock.OpenAI.return_value.chat.completions.create.return_value = resp
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        provider = mod.OpenAIProvider()
        provider.complete_structured("hello", schema={"type": "object"}, system="be precise")
        call_kwargs = openai_mock.OpenAI.return_value.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "be precise"}


def test_openai_complete_structured_api_error() -> None:
    openai_mock = _make_openai_mock()
    openai_mock.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("boom")
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openai as mod

        importlib.reload(mod)
        provider = mod.OpenAIProvider()
        with pytest.raises(ProviderError, match="OpenAI structured API error"):
            provider.complete_structured("hello", schema={"type": "object"})


# ---------------------------------------------------------------------------
# OpenRouter complete() and complete_structured() tests
# ---------------------------------------------------------------------------


def test_openrouter_complete() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        provider = mod.OpenRouterProvider()
        result = provider.complete("hello")
        assert result == "response text"


def test_openrouter_complete_with_system() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        provider = mod.OpenRouterProvider()
        provider.complete("hello", system="be concise")
        call_kwargs = openai_mock.OpenAI.return_value.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "be concise"}


def test_openrouter_complete_api_error() -> None:
    openai_mock = _make_openai_mock()
    openai_mock.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("boom")
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        provider = mod.OpenRouterProvider()
        with pytest.raises(ProviderError, match="OpenRouter API error"):
            provider.complete("hello")


def test_openrouter_complete_structured() -> None:
    openai_mock = _make_openai_mock()
    choice = MagicMock()
    choice.message.content = '{"key": "value"}'
    resp = MagicMock()
    resp.choices = [choice]
    openai_mock.OpenAI.return_value.chat.completions.create.return_value = resp
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        provider = mod.OpenRouterProvider()
        result = provider.complete_structured("hello", schema={"type": "object"})
        assert result == {"key": "value"}


def test_openrouter_complete_structured_with_system() -> None:
    openai_mock = _make_openai_mock()
    choice = MagicMock()
    choice.message.content = '{"key": "value"}'
    resp = MagicMock()
    resp.choices = [choice]
    openai_mock.OpenAI.return_value.chat.completions.create.return_value = resp
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        provider = mod.OpenRouterProvider()
        provider.complete_structured("hello", schema={"type": "object"}, system="be precise")
        call_kwargs = openai_mock.OpenAI.return_value.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "be precise"}


def test_openrouter_complete_structured_api_error() -> None:
    openai_mock = _make_openai_mock()
    openai_mock.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("boom")
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
    ):
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        provider = mod.OpenRouterProvider()
        with pytest.raises(ProviderError, match="OpenRouter structured API error"):
            provider.complete_structured("hello", schema={"type": "object"})


def test_openrouter_missing_api_key() -> None:
    openai_mock = _make_openai_mock()
    with (
        patch.dict(sys.modules, {"openai": openai_mock}),
        patch.dict("os.environ", {}, clear=True),
    ):
        import importlib

        import archex.providers.openrouter as mod

        importlib.reload(mod)
        with pytest.raises(ProviderError, match="API key"):
            mod.OpenRouterProvider()
