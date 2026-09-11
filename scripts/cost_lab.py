#!/usr/bin/env python3
r"""
cost_lab.py — **거래비용·세금을 빼고도 남나** (2026-09-01 신설)

⚠️⚠️ **지금까지 낸 숫자는 전부 「세전·비용전」이다.** 실제로 손에 남는 건 다르다.
```
증권거래세  0.18%  (매도 시. 2026년 기준)
위탁수수료  0.015% × 2 (매수·매도)
슬리피지   0.05% 가정  ⚠️ **가정이다** — 실제로는 종목·시각·금액에 따라 다르다
합계      약 0.26%p 를 왕복마다 뺀다
```

⚠️⚠️ **회전율이 성적을 갉아먹는다.** D+1 전략은 5일에 5번 사고팔지만 D+5는 1번이다.
   같은 「하루 +0.3%p」라도 **D+1 전략은 비용을 5배 낸다.**
   그래서 **지평별로 「연 환산 순수익」**을 같이 낸다.

⚠️ **신호 빈도도 넣는다.** 하루 0.3건이면 자본이 논다 — 「신호가 있을 때만」의 수익률과
   「자본 전체 기준」 수익률은 전혀 다르다.

쓰는 법:
    python scripts\cost_lab.py
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 5, 20)
_세금 = 0.0018
_수수료 = 0.00015 * 2
_슬리피지 = 0.0005          # ⚠️ 가정
_왕복 = (_세금 + _수수료 + _슬리피지) * 100      # %p
_거래일 = 245


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    print(f"  왕복 비용 {_왕복:.3f}%p (세금 {_세금*100:.2f} + 수수료 {_수수료*100:.3f} "
          f"+ 슬리피지 {_슬리피지*100:.2f}⚠️가정)", flush=True)

    전략 = [
        ("공시 호재", lambda x: "호재" in x["성격"]),
        ("갭① 호재+장후", lambda x: "호재" in x["성격"] and x["장후"]),
        ("갭①④ +무반응", lambda x: "호재" in x["성격"] and x["장후"] and x["무반응"]),
        ("갭①③④ +수급", lambda x: "호재" in x["성격"] and x["장후"] and x["무반응"] and x["갭3"]),
        ("갭①④ 정상종목만", lambda x: "호재" in x["성격"] and x["장후"] and x["무반응"]
         and not x["더럽"]),
    ]
    통 = {}
    날수 = 0
    for i, d1 in enumerate(날):
        a = 지수.get(d1)
        if not a:
            continue
        날수 += 1
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        지평 = [(h, 날[i + h]) for h in _H if i + h < len(날) and 지수.get(날[i + h])]
        for code, v1 in s1.items():
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            r = ds.get(code) or {}
            if not r:
                continue
            f = fl.get(code) or {}
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            x = {"성격": r.get("성격", set()),
                 "장후": r.get("분") is not None and r["분"] >= 930,
                 "무반응": abs(등락) < 1,
                 "갭3": (f.get("외국인") or 0) > 0 and (f.get("기관") or 0) > 0,
                 "더럽": (("관리종목" in 부) or ("SPAC" in 부)
                          or (str(bb.get("상장일") or "") > "20240101")
                          or (bb.get("증권구분") not in (None, "주권")))}
            맞 = [n for n, fn in 전략 if fn(x)]
            if not 맞:
                continue
            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            for h, d2 in 지평:
                v2 = 주가[d2].get(code)
                if not v2:
                    continue
                b = 지수[d2]
                초과 = ((v2[0] / c1 - 1) - (b[장] / a[장] - 1)) * 100
                for n in 맞:
                    s = 통.setdefault((n, h), [0.0, 0])
                    s[0] += 초과
                    s[1] += 1
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print(f"\n  거래일 {날수}일\n")
    print(f"  {'전략':<20}{'지평':>5}{'세전':>10}{'순(비용후)':>12}{'건수':>8}"
          f"{'하루신호':>9}{'연환산순':>10}")
    for n, _ in 전략:
        for h in _H:
            s = 통.get((n, h))
            if not s or s[1] < 50:
                continue
            세전 = s[0] / s[1]
            순 = 세전 - _왕복
            빈도 = s[1] / 날수
            # ⚠️ 「신호가 있을 때만」이 아니라 **자본이 늘 한 종목에 들어가 있다고 가정**한
            #    낙관적 상한이다. 실제로는 신호가 없으면 자본이 논다.
            연 = ((1 + 순 / 100) ** (_거래일 / h) - 1) * 100
            print(f"  {n:<20}D+{h:<3}{세전:>+9.3f}{순:>+12.3f}{s[1]:>8,}"
                  f"{빈도:>9.2f}{연:>+9.1f}%")
    print()
    print("  ⚠️⚠️ 「연환산순」은 **자본이 늘 투입돼 있다는 비현실적 낙관**이다.")
    print("     하루 신호가 0.3건이면 3일에 한 번만 살 수 있어 자본이 논다.")
    print("  ⚠️ 그리고 이건 **초과수익**이다 — 시장이 −20%면 우리도 −20%+α다.")
    print(f"  ⚠️ 슬리피지 {_슬리피지*100:.2f}%는 **가정**이다. 실제 체결가로 검증한 적 없다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
