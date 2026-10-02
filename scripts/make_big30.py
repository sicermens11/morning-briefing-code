#!/usr/bin/env python3
r"""
make_big30.py — **큰 종목 30** (2026-10-02 · 계획표 6 「종목별 규칙 · 큰 종목 30개쯤만」)
· 가장 최근 krx-daily 의 시총 상위 30 보통주(주권) — 우선주·스팩·관리종목 뺌
· 결과 data/big30.json {"기준일", "종목": [{"code","이름","시총조"}]}
⚠️ 한 종목은 사건이 「날마다 한 번」 이라 이어진 날이 많다 — 우연이 규칙처럼 보이기 쉽다(9/30 설계 메모). 결과에 표본 크기를 같이 적는다
"""
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def main():
    f = sorted(glob.glob(os.path.join(_D, "krx-daily", "*.json")))[-1]
    d = json.load(io.open(f, encoding="utf-8-sig"))
    base = json.load(io.open(os.path.join(_D, "stock-base.json"), encoding="utf-8-sig"))["종목"]
    줄 = []
    for c, v in d["종목"].items():
        b = base.get(c) or {}
        if b.get("증권구분") not in (None, "주권") or b.get("종류") not in (None, "보통주"):
            continue
        if "관리" in str(b.get("업종") or "") or "스팩" in str(b.get("이름") or ""):
            continue
        try:
            시총 = float(str(v.get("시총") or v.get("시가총액") or 0).replace(",", ""))
        except ValueError:
            continue
        줄.append((시총, c, b.get("이름") or v.get("이름") or c))
    줄.sort(reverse=True)
    out = {"기준일": d.get("기준일") or os.path.basename(f)[:8],
           "종목": [{"code": c, "이름": n, "시총조": round(s / 1e12, 1)} for s, c, n in 줄[:30]]}
    io.open(os.path.join(_D, "big30.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["기준일"], " · ".join(f"{z['이름']}({z['시총조']}조)" for z in out["종목"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
