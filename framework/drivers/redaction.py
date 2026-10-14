"""Secret masking. Everything that reaches a log file or a failure message goes through here."""

from __future__ import annotations

from collections.abc import Iterable


class Redactor:
    """Replace known secret strings (Wi-Fi password, sudo password) with ``***``."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        self._secrets: list[str] = []
        for s in secrets:
            self.add(s)

    def add(self, secret: str | None) -> None:
        # skip very short secrets - they'd mangle unrelated text
        if secret and len(secret) >= 4 and secret not in self._secrets:
            self._secrets.append(secret)
            self._secrets.sort(key=len, reverse=True)  # mask longer secrets first

    def clean(self, text: str) -> str:
        for s in self._secrets:
            text = text.replace(s, "***")
        return text
