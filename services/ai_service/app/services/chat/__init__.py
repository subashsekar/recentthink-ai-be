"""Conversational chat service package."""

__all__ = ["ChatService"]


def __getattr__(name: str):
    if name == "ChatService":
        from app.services.chat.chat_service import ChatService

        return ChatService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
