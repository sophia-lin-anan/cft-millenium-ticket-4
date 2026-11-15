"""Shared provider utilities."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    pass


class AnalystProvider(ABC):
    name: str

    @abstractmethod
    def analyze(self, snapshot: dict, instructions: str, schema: dict) -> dict:
        raise NotImplementedError


def post_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 90) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise ProviderError(f"Provider returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Provider request failed: {exc}") from exc
