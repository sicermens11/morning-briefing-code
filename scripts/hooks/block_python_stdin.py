#!/usr/bin/env python3
r"""
block_python_stdin.py — Claude Code 사전 검사(PreToolUse) · **`python -` · `python -c` · heredoc 파이썬을 막는다** (2026-10-13)

왜: 셸 명령 끝에 `python - </dev/null` 같은 찌꺼기를 붙여 2분씩 멈춘 게 10번(10/13 하루 두 번).
    기억(memory/no-heredoc-for-python.md)에 적어도 안 막혔다 → 명령이 나가기 전에 여기서 막는다.
허용: `python 파일.py` · `python -m 모듈` · `python -I 파일.py` · `python -X utf8 파일.py`
막음: `python -` · `python -c "..."` · `python <<EOF` · `python3 -` · `py -`
나가는 법: 막으면 exit 2 + 이유(stderr) — Claude 에게 그대로 보인다
"""
import json
import re
import sys

_막음 = re.compile(
    r"(?:^|[\s;&|(`])(?:python3?|py)(?:\.exe)?\"?\s+"
    r"(?:-(?=\s|$|<|;|\||&|\))|-c\b|<<)"
    r"|(?:^|[\s;&|(`])(?:python3?|py)(?:\.exe)?\"?\s*<<",
    re.IGNORECASE,
)


def main():
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    try:
        j = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    명령 = str(((j or {}).get("tool_input") or {}).get("command") or "")
    if _막음.search(명령):
        sys.stderr.write(
            "⛔ 막음: `python -` · `python -c` · heredoc 으로 파이썬을 넘기는 명령은 금지다 "
            "(10번 멈춤 · memory/no-heredoc-for-python.md). Write 로 .py 를 만들고 `python 파일.py` 로 돌려라.\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
