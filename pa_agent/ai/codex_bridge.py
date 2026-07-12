"""Atomic file protocol for Codex-controlled PA Agent analysis."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pa_agent.ai.deepseek_client import CancelledError

PROTOCOL_VERSION = 1
_VALID_STAGES = {"stage1", "stage2"}


@dataclass(frozen=True, slots=True)
class BridgeRequest:
    request_id: str
    path: Path


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class CodexBridgeStore:
    """Read and write the local request/response exchange directory."""

    def __init__(self, root: Path, *, poll_interval_s: float = 0.2) -> None:
        self.root = Path(root)
        self.requests_dir = self.root / "requests"
        self.responses_dir = self.root / "responses"
        self.cancelled_dir = self.root / "cancelled"
        self.poll_interval_s = max(0.01, float(poll_interval_s))

    def create_request(
        self,
        *,
        messages: list[dict[str, Any]],
        stage: str,
        timeout_s: float,
    ) -> BridgeRequest:
        if stage not in _VALID_STAGES:
            raise ValueError(f"无效 Codex 阶段: {stage}")
        request_id = uuid.uuid4().hex
        now = datetime.now(UTC)
        path = self.requests_dir / f"{request_id}.json"
        _atomic_write_json(
            path,
            {
                "protocol_version": PROTOCOL_VERSION,
                "request_id": request_id,
                "status": "pending",
                "stage": stage,
                "created_at": now.isoformat(timespec="milliseconds"),
                "expires_at": (now + timedelta(seconds=max(0.0, timeout_s))).isoformat(
                    timespec="milliseconds"
                ),
                "messages": messages,
            },
        )
        return BridgeRequest(request_id=request_id, path=path)

    def _request_path(self, request_id: str) -> Path:
        return self.requests_dir / f"{request_id}.json"

    def _response_path(self, request_id: str) -> Path:
        return self.responses_dir / f"{request_id}.json"

    def _cancelled_path(self, request_id: str) -> Path:
        return self.cancelled_dir / f"{request_id}.json"

    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Codex bridge JSON 无法读取: {path.name}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Codex bridge JSON 必须是对象: {path.name}")
        return payload

    def read_request(self, request_id: str) -> dict[str, Any]:
        path = self._request_path(request_id)
        if not path.exists():
            raise ValueError(f"找不到请求: {request_id}")
        payload = self._read_json(path)
        if payload.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError("Codex bridge request protocol version mismatch")
        if payload.get("request_id") != request_id:
            raise ValueError("Codex bridge request_id mismatch")
        return payload

    def list_pending_requests(self) -> list[dict[str, Any]]:
        if not self.requests_dir.exists():
            return []
        pending: list[dict[str, Any]] = []
        for path in sorted(self.requests_dir.glob("*.json"), key=lambda item: item.stat().st_mtime):
            try:
                payload = self._read_json(path)
            except ValueError:
                continue
            request_id = str(payload.get("request_id") or "")
            if not request_id or payload.get("status") != "pending":
                continue
            if self._response_path(request_id).exists() or self._cancelled_path(request_id).exists():
                continue
            pending.append(payload)
        return pending

    def write_response(
        self,
        request_id: str,
        *,
        content: str,
        reasoning_content: str = "",
    ) -> Path:
        self.read_request(request_id)
        path = self._response_path(request_id)
        _atomic_write_json(
            path,
            {
                "protocol_version": PROTOCOL_VERSION,
                "request_id": request_id,
                "created_at": _iso_now(),
                "content": str(content),
                "reasoning_content": str(reasoning_content),
            },
        )
        return path

    def cancel_request(self, request_id: str) -> Path:
        self.read_request(request_id)
        path = self._cancelled_path(request_id)
        _atomic_write_json(
            path,
            {
                "protocol_version": PROTOCOL_VERSION,
                "request_id": request_id,
                "cancelled_at": _iso_now(),
            },
        )
        return path

    def wait_for_response(
        self,
        request_id: str,
        *,
        timeout_s: float,
        cancel_token: Any = None,
    ) -> dict[str, Any]:
        self.read_request(request_id)
        deadline = time.monotonic() + max(0.0, float(timeout_s))
        while True:
            if cancel_token is not None and cancel_token.is_set():
                raise CancelledError("Codex bridge request cancelled")
            if self._cancelled_path(request_id).exists():
                raise CancelledError("Codex bridge request cancelled")
            response_path = self._response_path(request_id)
            if response_path.exists():
                payload = self._read_json(response_path)
                if payload.get("protocol_version") != PROTOCOL_VERSION:
                    raise ValueError("Codex bridge response protocol version mismatch")
                if payload.get("request_id") != request_id:
                    raise ValueError("Codex bridge response request_id mismatch")
                return payload
            if time.monotonic() >= deadline:
                raise TimeoutError(f"等待 Codex 响应超时: {request_id}")
            time.sleep(min(self.poll_interval_s, max(0.0, deadline - time.monotonic())))
