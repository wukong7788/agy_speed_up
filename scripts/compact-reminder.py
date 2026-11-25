#!/usr/bin/env python3
"""PreInvocation hook that reminds the user to run /compact when context grows large."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_WARN_TOKENS = 250_000
DEFAULT_STEP_TOKENS = 100_000
TAIL_BYTES = 262_144


def read_latest_prompt_tokens(transcript_path: str) -> tuple[int, int] | None:
    path = Path(transcript_path)
    if not path.is_file():
        return None

    size = path.stat().st_size
    if size <= 0:
        return None

    with path.open("rb") as fh:
        offset = max(0, size - TAIL_BYTES)
        fh.seek(offset)
        chunk = fh.read().decode("utf-8", errors="ignore")

    lines = chunk.splitlines()
    if offset > 0 and lines:
        lines = lines[1:]

    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "PLANNER_RESPONSE":
            continue
        if "input_tokens" not in entry and "cache_read_tokens" not in entry:
            continue
        total = int(entry.get("input_tokens") or 0) + int(entry.get("cache_read_tokens") or 0)
        step_index = int(entry.get("step_index") or 0)
        return total, step_index

    return None


def safe_state_path(conversation_id: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]", "_", conversation_id or "default")
    return Path(tempfile.gettempdir()) / f"agy_compact_reminder_{slug}.json"


def format_k(tokens: int) -> str:
    return f"{tokens / 1000:.0f}k"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("{}")
        return 0

    if payload.get("hookEventName") != "PreInvocation":
        print("{}")
        return 0

    raw_invocation = payload.get("invocationNum")
    invocation_num = 0 if raw_invocation is None else int(raw_invocation)
    if invocation_num != 0:
        print("{}")
        return 0

    last_user_input = str(payload.get("lastUserInput") or "").strip()
    if last_user_input.startswith("/compact"):
        print("{}")
        return 0

    transcript_path = str(payload.get("transcriptPath") or "").strip()
    if not transcript_path:
        print("{}")
        return 0

    usage = read_latest_prompt_tokens(transcript_path)
    if usage is None:
        print("{}")
        return 0

    total_tokens, step_index = usage
    warn_tokens = max(50_000, int(os.environ.get("AGY_COMPACT_WARN_TOKENS", DEFAULT_WARN_TOKENS)))
    step_tokens = max(25_000, int(os.environ.get("AGY_COMPACT_REPEAT_STEP_TOKENS", DEFAULT_STEP_TOKENS)))
    remind_every_turn = os.environ.get("AGY_COMPACT_REMIND_EVERY_TURN", "0") == "1"

    state_file = safe_state_path(str(payload.get("conversationId") or "default"))

    if total_tokens < warn_tokens:
        if state_file.exists():
            try:
                state_file.unlink()
            except OSError:
                pass
        print("{}")
        return 0

    bucket = (total_tokens - warn_tokens) // step_tokens
    if not remind_every_turn and state_file.is_file():
        try:
            prev = json.loads(state_file.read_text(encoding="utf-8"))
            if int(prev.get("bucket", -1)) == bucket and int(prev.get("last_step", 0)) <= step_index:
                print("{}")
                return 0
        except Exception:
            pass

    try:
        state_file.write_text(
            json.dumps({"bucket": bucket, "last_step": step_index, "tokens": total_tokens}),
            encoding="utf-8",
        )
    except OSError:
        pass

    next_tier = warn_tokens + (bucket + 1) * step_tokens
    level = "⚠️" if total_tokens >= warn_tokens + step_tokens else "⚡"
    message = (
        f"{level} **上下文已达 ~{format_k(total_tokens)} tokens**（提醒阈值 {format_k(warn_tokens)}，"
        f"下次升级提醒 {format_k(next_tier)}）：上下文越长模型思考越慢，当前任务收尾后建议发送 `/compact` 压缩会话。"
    )

    print(
        json.dumps(
            {
                "injectSteps": [
                    {
                        "systemMessage": {
                            "systemMessage": "",
                            "metadata": {
                                "user_markdown": message,
                            },
                        }
                    }
                ]
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("{}")
        raise SystemExit(0)
