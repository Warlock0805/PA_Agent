"""Command-line interface for a current Codex conversation bridge."""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pa_agent.ai.codex_bridge import CodexBridgeStore
from pa_agent.config.paths import CODEX_BRIDGE_DIR


def _emit(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pa-agent-codex")
    parser.add_argument("--bridge-dir", type=Path, default=CODEX_BRIDGE_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    show = commands.add_parser("show")
    show.add_argument("request_id")
    respond = commands.add_parser("respond")
    respond.add_argument("request_id")
    respond.add_argument("--content-file", type=Path, required=True)
    respond.add_argument("--reasoning-file", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    store = CodexBridgeStore(args.bridge_dir)
    try:
        if args.command == "list":
            _emit(
                [
                    {
                        key: request[key]
                        for key in ("request_id", "stage", "created_at", "expires_at")
                        if key in request
                    }
                    for request in store.list_pending_requests()
                ]
            )
            return 0
        if args.command == "show":
            _emit(store.read_request(args.request_id))
            return 0
        if args.command == "respond":
            content = args.content_file.read_text(encoding="utf-8")
            reasoning = ""
            if args.reasoning_file is not None:
                reasoning = args.reasoning_file.read_text(encoding="utf-8")
            store.write_response(args.request_id, content=content, reasoning_content=reasoning)
            _emit({"status": "responded", "request_id": args.request_id})
            return 0
    except (OSError, ValueError) as exc:
        _emit({"status": "error", "message": str(exc)})
        return 2
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
