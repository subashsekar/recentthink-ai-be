"""Streaming cancellation helpers."""


class StreamCancelledError(Exception):
    """Raised when a client disconnects or aborts an in-flight stream."""
