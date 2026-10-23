#!/usr/bin/env python3
r"""
lab_ledger.py — **시험 결과 중 기록 안 된 것을 찾는다** (2026-10-23 신설)

사용자 10/23 「메모는 내가 말안해도 꾸준히 할 수 있게 시스템적으로 못 만드나? 몇번 테스트 결과 기록 안한 적 있었는데」
→ 기억(memory)에 「결과는 남긴다」 고 적어도 빠뜨렸다. 사람이 아니라 코드가 「안 적힌 결과」 를 찾아 대화가 끝날 때마다 막는다.

어떻게:
  data/_labs/2026-*.txt 중 기준일(10/01) 뒤 파일 하나하나가 docs/할일.md 나 docs/*.md 에 적혀 있나 본다
    적힘 = 파일 이름(확장자 뺀 것)이 docs 어딘가에 그대로 있다
         또는 시험 꼬리표(이름의 날짜·시각 뒤 첫 낱말 · 예 CONTRIB)가 그 날(M/D) 할일 줄에 같이 있다
  빼는 것: 매일 도는 예측 기록(예측_* · 예측기록_* · *.시간) · 이름에 「첫판·터짐·_err」 가 든 것 · 만든 지 20분 안 된 것(아직 도는 중)
쓰는 법:
  python scripts\lab_ledger.py            안 적힌 것 목록 · 있으면 코드 1
  python scripts\lab_ledger.py --hook     Claude Code Stop 훅 — 안 적힌 게 있으면 코드 2 + 이유(막는다 · stop_hook_active 면 안 막는다)
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
기준일 = "2026-10-21"   # 그 전 B161~ 무리 판 수백 개는 묶음 줄로 적혀 있어 파일 이름으로는 못 맞춘다 — 장치는 여기서부터
_빼기 = re.compile(r"(예측_|예측기록_|\.시간$|첫판|터짐|_err|_터짐)")
_이름 = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:_\d{4})?_([A-Za-z0-9]+)")


def 안적힌것(최소분=20):
    문서 = ""
    for p in glob.glob(os.path.join(_B, "docs", "*.md")):
        try:
            문서 += io.open(p, encoding="utf-8").read() + "\n"
        except OSError:
            pass
    할일줄 = []
    try:
        할일줄 = io.open(os.path.join(_B, "docs", "할일.md"), encoding="utf-8").read().splitlines()
    except OSError:
        pass
    지금 = dt.datetime.now()
    결과 = []
    for p in sorted(glob.glob(os.path.join(_B, "data", "_labs", "2026-*.txt"))):
        stem = os.path.basename(p)[:-4]
        if stem < 기준일 or _빼기.search(stem):
            continue
        if (지금 - dt.datetime.fromtimestamp(os.path.getmtime(p))).total_seconds() < 최소분 * 60:
            continue
        if stem in 문서:
            continue
        m = _이름.match(stem)
        if m:
            d = dt.date.fromisoformat(m.group(1))
            꼬리 = m.group(2)
            날말 = (f"{d.month}/{d.day}", f"{d.month}/{d.day + 1}")   # 밤 판은 다음 날 적는다
            if any(꼬리 in z and any(n in z for n in 날말) for z in 할일줄):
                continue
        결과.append(stem)
    return 결과


def main():
    훅 = "--hook" in sys.argv
    if 훅:
        try:
            j = json.load(sys.stdin)
        except Exception:  # noqa: BLE001
            j = {}
        if j.get("stop_hook_active"):
            return 0
    없 = 안적힌것()
    if not 없:
        if not 훅:
            print("시험 결과 기록: 빠진 것 없음")
        return 0
    글 = f"⛔ 시험 결과 {len(없)}개가 docs/할일.md 에 안 적혔다(lab_ledger) — 결과 줄(숫자·판단·반영 여부)을 적고 끝내라:\n" + "\n".join(f"  · data/_labs/{z}.txt" for z in 없[:15])
    if 훅:
        print(글, file=sys.stderr)
        return 2
    print(글)
    return 1


if __name__ == "__main__":
    sys.exit(main())
