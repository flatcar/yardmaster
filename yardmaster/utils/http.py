from __future__ import annotations

from typing import Any

import requests


class HttpClient:
    def __init__(self, timeout: int = 30, retries: int = 3, verify_ssl: bool = True) -> None:
        self.timeout = timeout
        self.retries = retries
        self.verify_ssl = verify_ssl
        self.session = requests.Session()

    def _get(self, url: str, headers: dict[str, str] | None = None) -> requests.Response:
        last_exc: requests.RequestException | None = None
        for _ in range(max(1, self.retries)):
            try:
                resp = self.session.get(
                    url, headers=headers, timeout=self.timeout, verify=self.verify_ssl
                )
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
        raise RuntimeError(f"GET failed for {url}") from last_exc

    def get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        return self._get(url, headers).text

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        return self._get(url, headers).json()
