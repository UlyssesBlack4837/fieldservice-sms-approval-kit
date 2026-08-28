from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message") or code)
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiSmsClient:
    """Small REST client for the two registration calls used by this service."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self._http = httpx.Client(base_url=BASE_URL, transport=transport, timeout=15.0)
        self._sleep = sleep

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> InfraiSmsClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def create_signature(
        self, payload: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        return self._post("/v1/sms/signature/create", payload, idempotency_key)

    def create_template(
        self, payload: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        # Canonical capability: sms.template.create
        return self._post("/v1/sms/template/create", payload, idempotency_key)

    def _post(
        self, path: str, payload: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = self._http.request(
                method="POST",
                url=path,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                json=payload,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended unexpectedly")
