"""HTML-to-text utilities for LeetCode problem descriptions."""

from __future__ import annotations

from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    """Convert LeetCode HTML problem content to plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
