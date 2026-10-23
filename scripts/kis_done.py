#!/usr/bin/env python3
r"""
kis_done.py — **한국투자증권 받기가 다 끝났나** (2026-10-23 · 시험 줄이 자료를 기다릴 때 쓴다)
    python scripts\kis_done.py 대차+의견           → 끝났으면 코드 0 · 아니면 1 (남은 파일 수를 찍는다) — 후보 종목 기준
    python scripts\kis_done.py 신용공매도 --전종목  → 전 종목(KIS_ALL) 기준 (10/23 독립 검사: 환경변수에 기대면 968 기준으로 「다 받음」 이 일찍 난다)
일감 목록은 collect_kis_hist 와 같은 함수로 만든다 — 그래야 「다 받았다」 가 받는 쪽과 같은 뜻이다
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_kis_hist as C  # noqa: E402


def main():
    종류 = sys.argv[1]
    if "--전종목" in sys.argv:
        os.environ["KIS_ALL"] = "1"
    else:
        os.environ.pop("KIS_ALL", None)
    남은 = 0
    전체 = 0
    for 종 in 종류.split("+"):
        목록 = C.대형종목() if 종 == "의견" else ({"0001": "코스피", "1001": "코스닥"} if 종 == "시장투자자" else C.대상종목())
        for 폴더, _ in C.종류표[종]:
            for c in 목록:
                전체 += 1
                if not C.끝났나(os.path.join(C._B, "data", 폴더, c + ".json")):
                    남은 += 1
    print(f"{종류}{' (전 종목)' if os.environ.get('KIS_ALL') else ' (후보 종목)'}: 전체 {전체:,} · 남은 {남은:,}")
    return 0 if 남은 == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
