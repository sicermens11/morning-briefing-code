#!/usr/bin/env python3
r"""
check_secrets.py — `data\secrets.json` 이 멀쩡한지 **값을 절대 드러내지 않고** 본다

⚠️⚠️ **왜 이 파일이 있나** (2026-08-27).
   secrets.json에 쉼표 하나가 빠져 있었는데, 그걸 확인하겠다고 파싱 오류 메시지를
   그대로 찍었다. **오류 메시지에 파일 내용이 통째로 들어 있었다.** 키 두 개가
   대화 기록에 남았고 둘 다 재발급해야 했다.

   그래서 규칙: **secrets.json은 사람이 직접 읽거나 오류를 그대로 찍지 않는다.**
   확인은 반드시 이 스크립트로 한다. 여기서는 무슨 일이 있어도 값이 밖으로 안 나간다
   — 오류 메시지도 줄·칸 위치만 옮기고 본문은 버린다.

쓰는 법:
    python scripts\check_secrets.py
    python scripts\check_secrets.py --need DART_API_KEY GITHUB_TOKEN
"""
import argparse
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS = os.path.join(_BASE, "data", "secrets.json")


def _safe_json_error(e: Exception) -> str:
    """예외에서 **위치만** 남기고 본문은 버린다. 이게 이 파일의 존재 이유다."""
    if isinstance(e, json.JSONDecodeError):
        return f"{e.msg} (줄 {e.lineno}, 칸 {e.colno})"
    return type(e).__name__


def _hint(raw: str) -> str:
    """제일 흔한 실수 — 줄 끝 쉼표 빠짐. 값은 안 보고 **모양만** 본다."""
    lines = raw.splitlines()
    for i in range(len(lines) - 1):
        cur, nxt = lines[i].rstrip(), lines[i + 1].strip()
        if re.search(r'"\s*$', cur) and nxt.startswith('"'):
            return f"줄 {i + 1} 끝에 쉼표가 빠진 것 같다 (다음 줄에 항목이 더 있다)"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--need", nargs="*", default=["DART_API_KEY"],
                    help="반드시 있어야 하는 키 이름")
    a = ap.parse_args()

    out = {"ok": False, "파일": SECRETS}

    if not os.path.exists(SECRETS):
        out["오류"] = "파일이 없다"
        print(json.dumps(out, ensure_ascii=False)); return 2

    with open(SECRETS, "r", encoding="utf-8-sig") as f:
        raw = f.read()

    try:
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        out["오류"] = "JSON이 깨졌다: " + _safe_json_error(e)
        h = _hint(raw)
        if h:
            out["짚이는것"] = h
        # ⚠️ raw 는 절대 넣지 않는다.
        print(json.dumps(out, ensure_ascii=False)); return 1

    # 값은 길이만 본다. 앞뒤 몇 글자도 안 보여준다 — 토큰은 앞부분만으로도 단서가 된다.
    out["키"] = {k: f"길이 {len(str(v))}" for k, v in data.items() if not k.startswith("_")}

    빈것 = [k for k in a.need if not str(data.get(k, "")).strip()]
    if 빈것:
        out["오류"] = "비어 있거나 없는 키: " + ", ".join(빈것)
        print(json.dumps(out, ensure_ascii=False)); return 1

    out["ok"] = True
    print(json.dumps(out, ensure_ascii=False)); return 0


if __name__ == "__main__":
    sys.exit(main())
