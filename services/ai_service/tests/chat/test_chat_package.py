"""Chat package lazy import tests."""

from __future__ import annotations

import importlib

import pytest


def test_chat_package_lazy_import() -> None:
    package = importlib.import_module("app.services.chat")
    ChatService = package.ChatService
    assert ChatService.__name__ == "ChatService"


def test_chat_package_unknown_attribute() -> None:
    package = importlib.import_module("app.services.chat")
    with pytest.raises(AttributeError):
        _ = package.DoesNotExist
