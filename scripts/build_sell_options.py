#!/usr/bin/env python3
r"""
build_sell_options.py — 매도 비율 **선택지 표**를 시험 결과에서 뽑아 둔다 (2026-09-14 저녁)

## 왜
퀀트 3장에 「지금 규칙은 40:60 · 30:70 이면 돈은 더 많고 흔들림도 더 크다」를 적는다
(사용자: 「매도 타이밍이 선택지를 주는 건 좋은 것 같은데」).
⚠️ **숫자를 화면에 박지 않는다** — 149억·−10.5% 같은 값은 시험 결과라 손으로 적으면
   다음 시험에서 낡는다. 여기서 `data/_labs/*.txt` 를 읽어 `data/sell-options.json` 으로 두고
   `quant_cards` 가 읽는다 (계좌 낙폭을 `rule-capital.json` 에서 읽는 것과 같은 방식).

## 어디서 읽나 (전부 같은 바탕 ㉯ + 후보 60 · 매도만 다르다)
    50:50   2026-09-14_L_후보60.txt
    40:60   2026-09-14_N2_합침_표본만_후보60_4060.txt
    30:70   2026-09-14_N_합침_표본만_후보60_3070.txt
  · 239차 A 첫 줄 「Ⓗ (지금 · 견줌)」 → 제약없음 끝 자산 · 낙폭
  · 264차 D 「±0.5」 줄 → 오차 포함 낙폭 (화면이 쓰는 잣대 — 2026-09-14 실측 08:55 오차 평균 0.60%p)

쓰는 법:  python scripts\build_sell_options.py
"""
import datetime as dt
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LABS = os.path.join(_BASE, "data", "_labs")
OUT = os.path.join(_BASE, "data", "sell-options.json")

판들 = (
    ((0.5, 0.5), "2026-09-14_L_후보60.txt", "L"),
    ((0.4, 0.6), "2026-09-14_N2_합침_표본만_후보60_4060.txt", "N2"),
    ((0.3, 0.7), "2026-09-14_N_합침_표본만_후보60_3070.txt", "N"),
)
_기준 = re.compile(r"Ⓗ \(지금 · 견줌\)\s+([\d,]+)원\s+(-?[\d.]+)%\s+\d+\s+[\d.]+\s*\|\s*([\d,]+)원\s+(-?[\d.]+)%")
_오차 = re.compile(r"^\s+±0\.5\s+\d+\s+([\d,]+)원\s+(-?[\d.]+)%", re.M)


def 읽기(파일):
    t = io.open(os.path.join(_LABS, 파일), encoding="utf-8").read()
    # 239차(제약 없는 판) 절 안의 첫 기준선 줄
    i = t.find("239차")
    m = _기준.search(t, i if i >= 0 else 0)
    d = _오차.search(t)
    if not m or not d:
        raise SystemExit(f"{파일}: 기준선 또는 ±0.5 줄을 못 찾았다")
    return {
        "있돈억": round(int(m.group(1).replace(",", "")) / 1e8, 2),
        "있낙폭": float(m.group(2)),
        "돈억": round(int(m.group(3).replace(",", "")) / 1e8, 1),
        "낙폭": float(m.group(4)),
        "낙폭오차": float(d.group(2)),
    }


안들 = []
for (앞, 뒤), 파일, 판 in 판들:
    r = 읽기(파일)
    r.update({"앞": 앞, "뒤": 뒤, "판": 판, "파일": 파일})
    안들.append(r)
    print(f"  {앞:.0%}:{뒤:.0%}  {r['돈억']:>7.1f}억  낙폭 {r['낙폭']:>5.1f}%  "
          f"오차±0.5 {r['낙폭오차']:>5.1f}%   ({판})")

나온 = {
    "만든날": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "출처": "scripts/build_sell_options.py ← data/_labs (gate7_lab 판 · 바탕 ㉯ + 후보 60)",
    "잣대": "돈 = 제약 없는 판 끝 자산(억) · 낙폭 = 계좌 낙폭 · 낙폭오차 = 08:55 예상체결가 오차 ±0.5%p 포함",
    "한계낙폭": -10.0,
    "안들": 안들,
}
io.open(OUT, "w", encoding="utf-8").write(json.dumps(나온, ensure_ascii=False, indent=1))
print(f"  ✅ {OUT}")
