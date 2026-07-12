from __future__ import annotations

import json


def test_cli_lists_and_shows_pending_request(tmp_path, capsys) -> None:
    from pa_agent.ai.codex_bridge import CodexBridgeStore
    from pa_agent.codex_bridge_cli import main

    store = CodexBridgeStore(tmp_path)
    request = store.create_request(
        messages=[{"role": "user", "content": "完整 Prompt"}],
        stage="stage1",
        timeout_s=60,
    )

    assert main(["--bridge-dir", str(tmp_path), "list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["request_id"] == request.request_id
    assert "messages" not in listed[0]

    assert main(["--bridge-dir", str(tmp_path), "show", request.request_id]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["messages"][0]["content"] == "完整 Prompt"


def test_cli_writes_response_from_utf8_file(tmp_path, capsys) -> None:
    from pa_agent.ai.codex_bridge import CodexBridgeStore
    from pa_agent.codex_bridge_cli import main

    store = CodexBridgeStore(tmp_path)
    request = store.create_request(messages=[], stage="stage1", timeout_s=60)
    content_file = tmp_path / "candidate.json"
    content_file.write_text('{"结论":"等待"}', encoding="utf-8")

    assert (
        main(
            [
                "--bridge-dir",
                str(tmp_path),
                "respond",
                request.request_id,
                "--content-file",
                str(content_file),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "responded"
    response = store.wait_for_response(request.request_id, timeout_s=0.1)
    assert response["content"] == '{"结论":"等待"}'
