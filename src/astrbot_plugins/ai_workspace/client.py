from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


class JsonApiClient:
    def __init__(self, base_url: str, default_timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.default_timeout = default_timeout

    def get(self, path: str, timeout: int | None = None) -> dict:
        with urllib.request.urlopen(
            f"{self.base_url}{path}",
            timeout=timeout or self.default_timeout,
        ) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_params(self, path: str, params: dict, timeout: int | None = None) -> dict:
        query = urllib.parse.urlencode(params)
        return self.get(f"{path}?{query}", timeout=timeout)

    def post(self, path: str, payload: dict, timeout: int | None = None) -> dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.default_timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(body or str(exc)) from exc
