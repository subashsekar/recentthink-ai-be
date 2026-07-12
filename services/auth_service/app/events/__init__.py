"""Account lifecycle events package."""

from app.events.account_events import publish_account_deleted

__all__ = ["publish_account_deleted"]
