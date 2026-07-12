"""Integration coverage for the local Codex conversation bridge."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from pa_agent.ai.codex_bridge import CodexBridgeClient, CodexBridgeStore
from pa_agent.ai.router import route_strategy_files
from pa_agent.config.settings import AIProviderSettings
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.util.threading import CancelToken, OrchestratorEvent
from tests.fixtures.validators import schema_test_validator

from .conftest import VALID_STAGE1, VALID_STAGE2


def _wait_for_pending(store: CodexBridgeStore, expected_stage: str) -> dict:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        pending = store.list_pending_requests()
        if pending:
            request = pending[-1]
            assert request["stage"] == expected_stage
            return request
        time.sleep(0.01)
    raise AssertionError(f"未收到 {expected_stage} Codex bridge 请求")


def test_codex_bridge_completes_two_stage_analysis(
    tmp_path: Path, frame, pending_writer, assembler, exp_reader
) -> None:
    """Two-stage orchestration waits for and consumes both Codex responses."""
    store = CodexBridgeStore(tmp_path, poll_interval_s=0.01)
    client = CodexBridgeClient(
        AIProviderSettings(runtime_mode="codex"), store=store
    )
    orchestrator = TwoStageOrchestrator(
        client=client,
        assembler=assembler,
        router=route_strategy_files,
        validator=schema_test_validator(),
        pending_writer=pending_writer,
        exp_reader=exp_reader,
    )
    events: list[OrchestratorEvent] = []
    result: dict[str, object] = {}

    def submit() -> None:
        result["record"] = orchestrator.submit(
            frame=frame,
            cancel_token=CancelToken(),
            on_event=events.append,
        )

    worker = threading.Thread(target=submit)
    worker.start()
    try:
        stage1 = _wait_for_pending(store, "stage1")
        store.write_response(
            stage1["request_id"], content=json.dumps(VALID_STAGE1, ensure_ascii=False)
        )
        stage2 = _wait_for_pending(store, "stage2")
        store.write_response(
            stage2["request_id"], content=json.dumps(VALID_STAGE2, ensure_ascii=False)
        )
    finally:
        worker.join(timeout=3.0)

    assert not worker.is_alive()
    assert events == [
        OrchestratorEvent.Stage1Started,
        OrchestratorEvent.Stage1Done,
        OrchestratorEvent.Stage2Started,
        OrchestratorEvent.Stage2Done,
        OrchestratorEvent.RecordSaved,
    ]
    record = result["record"]
    assert record.stage1_response["content"] == json.dumps(
        VALID_STAGE1, ensure_ascii=False
    )
    assert record.stage2_response["content"] == json.dumps(
        VALID_STAGE2, ensure_ascii=False
    )
    assert record.stage1_diagnosis is not None
    assert record.stage2_decision is not None
    pending_writer.save_full.assert_called_once_with(record)
