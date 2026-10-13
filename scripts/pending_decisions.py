#!/usr/bin/env python3
r"""
pending_decisions.py — **사용자가 아직 결정 안 한 것** 을 기록에서 다 긁어 온다 (2026-10-13)

왜: 사용자 「내가 결정할 거 있냐고 했을 때 왜 안 나온거야?」 — B242(빠르게 빠지는 후보 빼기)가
    10/8 메모 한 줄에 「안 넣음(내 권고 · 결정 전)」 으로만 묻혀 있었는데, 나는 머리로 목록을 만들어 빠뜨렸다.
    ⇒ 「결정할 거 있나」 에 답하기 전에 이것을 돌린다.

· 찾는 표시: 결정 전 · 결정 대기 · 사용자 결정 없음/아님 · 답 대기 · 권고 · 결정 전
· 같은 줄이나 바로 다음 몇 줄에 「결정(사용자」 가 있으면 끝난 것으로 본다
· 대상: docs/할일.md · docs/목표와_규칙_기준.md · docs/*탈락규칙_대장*.md · docs/*규칙_성적표*.md
쓰는 법: python scripts\pending_decisions.py
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
_뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_대상 = ([os.path.join(_뿌리, "docs", "할일.md"), os.path.join(_뿌리, "docs", "목표와_규칙_기준.md")]
        + sorted(glob.glob(os.path.join(_뿌리, "docs", "*탈락규칙_대장*.md")))
        + sorted(glob.glob(os.path.join(_뿌리, "docs", "*규칙_성적표*.md"))))
_표시 = re.compile(r"결정 전|결정 대기|결정 없음|결정 아님|답 대기|⏸ 결정")
_끝남줄 = re.compile(r"결정\(사용자|\d+/\d+ 결정 —|탈락 — 사용자|✅ 뺌|✅ 반영|너 권고대로|권고대로 하자|지금 정할 것 없음")
_끝남다음 = re.compile(r"결정\(사용자|\d+/\d+ 결정 —")


def main():
    남음 = []
    for f in _대상:
        if not os.path.exists(f):
            continue
        줄 = io.open(f, encoding="utf-8").read().splitlines()
        for i, l in enumerate(줄):
            if not _표시.search(l) or l.lstrip().startswith("상태:"):
                continue
            # 표의 한 줄은 그 줄만 본다(옆 줄은 다른 항목) · 글머리(-) 줄만 위아래 줄의 「결정(사용자」 를 본다
            _옆 = [] if l.lstrip().startswith("|") else [z for z in 줄[max(0, i - 1):i] + 줄[i + 1:i + 3] if not z.lstrip().startswith("|")]
            if _끝남줄.search(l) or any(_끝남다음.search(z) for z in _옆):
                continue
            남음.append((os.path.basename(f), i + 1, l.strip()[:200]))
    print(f"아직 결정 안 한 것으로 보이는 줄 {len(남음)}개 (같은 줄·다음 두 줄에 「결정(사용자」 가 없는 것)")
    for f, n, l in 남음:
        print(f"  {f}:{n}  {l}")


if __name__ == "__main__":
    main()
