from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from pa_agent.ai.deepseek_client import CancelledError
from pa_agent.util.threading import CancelToken


def test_store_creates_versioned_pending_request_without_temp_artifacts(tmp_path: Path) -> None:
    from pa_agent.ai.codex_bridge import CodexBridgeStore

    store = CodexBridgeStore(tmp_path)
    request = store.create_request(
        messages=[{"role": "user", "content": "分析当前行情"}],
        stage="stage1",
        timeout_s=60,
    )

    payload = json.loads(request.path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 1
    assert payload["request_id"] == request.request_id
    assert payload["status"] == "pending"
    assert payload["stage"] == "stage1"
    assert payload["expires_at"]
    assert payload["messages"] == [{"role": "user", "content": "分析当前行情"}]
    assert not list(request.path.parent.glob("*.tmp"))


def test_store_waits_for_matching_response(tmp_path: Path) -> None:
    from pa_agent.ai.codex_bridge import CodexBridgeStore

    store = CodexBridgeStore(tmp_path, poll_interval_s=0.01)
    request = store.create_request(messages=[], stage="stage1", timeout_s=1)

    def respond() -> None:
        store.write_response(
            request.request_id,
            content='{"gate_result":"proceed"}',
            reasoning_content="已检查行情结构",
        )

    timer = threading.Timer(0.03, respond)
    timer.start()
    try:
        response = store.wait_for_response(request.request_id, timeout_s=1.0)
    finally:
        timer.join()

    assert response["request_id"] == request.request_id
    assert response["content"] == '{"gate_result":"proceed"}'
    assert response["reasoning_content"] == "已检查行情结构"


def test_store_rejects_unknown_request_and_bad_response_protocol(tmp_path: Path) -> None:
    from pa_agent.ai.codex_bridge import CodexBridgeStore

    store = CodexBridgeStore(tmp_path)
    with pytest.raises(ValueError, match="找不到请求"):
        store.write_response("missing", content="{}")

    request = store.create_request(messages=[], stage="stage1", timeout_s=1)
    response_path = store.responses_dir / f"{request.request_id}.json"
    response_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.write_text(
        json.dumps({"protocol_version": 999, "request_id": request.request_id}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="protocol version"):
        store.wait_for_response(request.request_id, timeout_s=0.1)


def test_store_honours_cancel_marker_and_cancel_token(tmp_path: Path) -> None:
    from pa_agent.ai.codex_bridge import CodexBridgeStore

    store = CodexBridgeStore(tmp_path, poll_interval_s=0.01)
    request = store.create_request(messages=[], stage="stage1", timeout_s=1)
    store.cancel_request(request.request_id)
    with pytest.raises(CancelledError):
        store.wait_for_response(request.request_id, timeout_s=1.0)

    request = store.create_request(messages=[], stage="stage1", timeout_s=1)
    token = CancelToken()
    token.set()
    with pytest.raises(CancelledError):
        store.wait_for_response(request.request_id, timeout_s=1.0, cancel_token=token)


def test_store_times_out_when_no_response_arrives(tmp_path: Path) -> None:
    from pa_agent.ai.codex_bridge import CodexBridgeStore

    store = CodexBridgeStore(tmp_path, poll_interval_s=0.01)
    request = store.create_request(messages=[], stage="stage2", timeout_s=1)

    with pytest.raises(TimeoutError, match="等待 Codex 响应超时"):
        store.wait_for_response(request.request_id, timeout_s=0.03)
