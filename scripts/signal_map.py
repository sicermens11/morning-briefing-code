#!/usr/bin/env python3
r"""
signal_map.py — **구분마다 통하는 신호가 다른가** (2026-09-07 신설)

## ⚠️ 이건 「규칙 만들기」가 아니라 **「지도 만들기」**다
```
사용자 지적: 「수급에 등락하는 종목, 공시에 등락하는 종목이 다 다를 것 같다.
              구분이 가능하면 구분별 매수 기준이 필요할 것 같다」
맞는 방향이다. 그런데 바로 구분별 규칙을 만들면 위험하다:
   신호 6개 x 규모 5구간 = 30가지. 섹터까지 나누면 수백 가지.
   **28만 개를 뒤졌더니 78%가 「세 판 통과」였던 게 오늘 아침 일이다**
⇒ 먼저 **「나눌 값어치가 있나」만 잰다.** 규칙은 안 만든다.
  성적이 구분마다 안 갈리면 나눌 이유가 없다
```

## 재는 것
```
구분  규모 5구간 (초대형 10조↑ / 대형 1~10조 / 중형 3천억~1조 /
                 중소형 2~3천억 / 소형 500억~2천억)
신호  ① 20일 낙폭 깊음 (-10%↓)      ② 볼린저 -1.0σ 아래
      ③ 전날 갭 하락 (-2%↓)         ④ 외국인 순매수 (상위 20%)
      ⑤ 외국인 순매도 (하위 20%)     ⑥ 그날 공시 있음
결과  D+1 · D+5 · D+20 수익률 (다음날 시가 매수 기준) · 승률
비교  **같은 구분의 「아무 날이나」와 견준다** — 그게 기준선이다
```
⚠️ 신호는 **전날까지의 정보만** 쓴다 (미리보기 금지).
⚠️ 여기서 좋아 보여도 **자본 시뮬을 통과해야** 규칙이 된다.

쓰는 법:
    python scripts\signal_map.py
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20160401"
구간 = (
    ("초대형 10조↑", 10e12, 9e15),
    ("대형 1~10조", 1e12, 10e12),
    ("중형 3천억~1조", 3e11, 1e12),
    ("중소형 2~3천억", 2e11, 3e11),
    ("소형 500억~2천억", 5e10, 2e11),
)


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본 = O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # ── 갭 (전날 종가 → 그날 시가) ──
    갭표, 앞종, 비 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                if min(종c, 시) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = 시 / 종c
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루

    # ── 수급 (외국인 순매수) ──
    print("  수급 읽는 중...", flush=True)
    수급 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "flow-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = d.get("기준일")
        if not d8:
            continue
        하루 = {}
        for c, v in (d.get("종목") or {}).items():
            try:
                하루[c] = float(v.get("외국인") or 0)
            except (TypeError, ValueError):
                continue
        if 하루:
            수급[d8] = 하루

    # ── 공시 (그날 공시가 있었나) ──
    print("  공시 읽는 중...", flush=True)
    공시 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = d.get("기준일")
        if not d8:
            continue
        났 = set()
        for k in ("챙길공시", "그밖의공시"):
            for x in (d.get(k) or []):
                c = x.get("종목코드")
                if c:
                    났.add(str(c).zfill(6))
        공시[d8] = 났

    print("  훑는 중...", flush=True)
    # 구분 -> 신호 -> [수익률들]
    모 = {라: {} for 라, _, _ in 구간}
    앞날 = (1, 5, 20)

    def 담기(라, 신호, rs):
        칸 = 모[라].setdefault(신호, {h: [] for h in 앞날})
        for h in 앞날:
            if rs.get(h) is not None:
                칸[h].append(rs[h])

    for i, d1 in enumerate(날):
        if i < 260 or i + 21 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        하루갭 = 갭표.get(다음) or {}
        오늘수급 = 수급.get(d1) or {}
        # 그날 수급 상하위 20% 자르는 값
        벌 = sorted(오늘수급.values())
        상컷 = 벌[int(len(벌) * 0.8)] if len(벌) > 10 else None
        하컷 = 벌[int(len(벌) * 0.2)] if len(벌) > 10 else None
        오늘공시 = 공시.get(d1) or set()

        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 대금 < O._MIN_AMT:
                continue
            라 = None
            for n, 하, 상 in 구간:
                if 하 <= 시총 < 상:
                    라 = n
                    break
            if 라 is None:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0          # 수정 시가
            if 매수 <= 0:
                continue
            rs = {}
            for h in 앞날:
                j = i + 1 + h
                if j < len(날):
                    vv = 주가[날[j]].get(code)
                    if vv:
                        rs[h] = (vv[0] / 매수 - 1) * 100
            if not rs:
                continue

            담기(라, "아무 날이나 (기준선)", rs)

            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if sq[kk - 20] > 0:
                낙 = (c1 / sq[kk - 20] - 1) * 100
                if 낙 <= -10:
                    담기(라, "① 20일 -10%↓", rs)
            if 볼 <= -1.0:
                담기(라, "② 볼린저 -1.0σ↓", rs)
            # ⚠️ 2026-09-07: 여기를  으로 써서 **날짜로 조회**했다.
            #    하루갭은 이미 그날 것이라 **종목코드**로 찾아야 한다.
            #    그래서 갭 신호가 표본 0으로 통째로 빠졌다 (실제로는 7.1%)
            g = 하루갭.get(code)
            if g is not None and g <= -2:
                담기(라, "③ 갭 -2%↓", rs)
            f2 = 오늘수급.get(code)
            if f2 is not None and 상컷 is not None:
                if f2 >= 상컷:
                    담기(라, "④ 외국인 순매수 상위20%", rs)
                elif f2 <= 하컷:
                    담기(라, "⑤ 외국인 순매도 하위20%", rs)
            if code in 오늘공시:
                담기(라, "⑥ 그날 공시 있음", rs)

    print("\n" + "=" * 96)
    print("  구분마다 통하는 신호가 다른가 — **지도**")
    print("=" * 96)
    print("  ⚠️ 이건 규칙이 아니다. 「나눌 값어치가 있나」만 본다\n")

    차례 = ("아무 날이나 (기준선)", "① 20일 -10%↓", "② 볼린저 -1.0σ↓",
            "③ 갭 -2%↓", "④ 외국인 순매수 상위20%", "⑤ 외국인 순매도 하위20%",
            "⑥ 그날 공시 있음")
    for 라, _, _ in 구간:
        print("=" * 96)
        print("  == " + 라 + " ==")
        print("  " + "신호".ljust(26) + "표본".rjust(9)
              + "D+1".rjust(9) + "D+5".rjust(9) + "D+20".rjust(9)
              + "D+20승률".rjust(10) + "기준선대비".rjust(11))
        기 = 모[라].get("아무 날이나 (기준선)")
        기20 = st.mean(기[20]) if (기 and 기[20]) else 0.0
        for 신 in 차례:
            칸 = 모[라].get(신)
            if not 칸 or len(칸[20]) < 30:
                continue
            n = len(칸[20])
            m = {h: (st.mean(칸[h]) if 칸[h] else 0.0) for h in 앞날}
            승 = sum(1 for x in 칸[20] if x > 0) / n * 100
            대 = m[20] - 기20
            별 = " ⭐" if (신 != "아무 날이나 (기준선)" and 대 >= 1.0) else ""
            print("  " + 신.ljust(26) + format(n, ",").rjust(9)
                  + format(m[1], "+.2f").rjust(8) + "%"
                  + format(m[5], "+.2f").rjust(8) + "%"
                  + format(m[20], "+.2f").rjust(8) + "%"
                  + format(승, ".1f").rjust(9) + "%"
                  + (format(대, "+.2f") + "%p").rjust(11) + 별)
        print("")

    print("=" * 96)
    print("  읽는 법")
    print("    · **기준선대비**가 그 구분에서 그 신호의 값어치다")
    print("    · 구분마다 순위가 다르면 **나눌 값어치가 있다**")
    print("    · 다 비슷하면 나눌 이유가 없다 — 하나로 간다")
    print("    · ⚠️ 여기서 좋아 보여도 **자본 시뮬을 통과해야** 규칙이 된다")
    print("      (평균 수익은 돈이 아니다 — 아홉 번 겪었다)")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
