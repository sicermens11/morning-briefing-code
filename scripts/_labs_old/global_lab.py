#!/usr/bin/env python3
r"""
global_lab.py — **32개 해외 지표 중 무엇이 한국 신호를 강화하나** (2026-09-03 · 88차)

⚠️⚠️ **사용자 지적으로 가능해졌다.**
   *"QQQ·SOXX 이거 꼭 써야해"* → Yahoo로 32종목 확보 (실패 0)
   *"XLK(기술)·IWM(소형주) — 미국 안에서도 어느 쪽이 한국과 연결되나. 이거 중요하다"*

## 지금까지의 한계
```
71차에서 **SPY 하나**로만 봤다 (그때는 그것뿐이었다)
결과: 어젯밤 미국 -0.5%↓면 +10.05% -> **+13.98%** · 승률 72.2% -> 78.5%
⇒ 다른 지표는 더 나을까? **한 번도 못 봤다**
```

## 재는 것
```
A 전체 훑기   32개 지표를 하나씩 신호에 붙여 **도달률·수익**을 잰다
B ⭐ **XLK vs IWM vs SOXX** — 미국 안에서 어느 쪽이 한국과 맞나
C ⭐ **대만·일본** — 산업 구조가 비슷한 아시아. 다만 **하루 늦게** 써야 한다
D VIX(공포지수) — 한 번도 못 써본 지표
E 원자재·금리·환율
F 조합 — 둘 이상을 겹치면
```

⚠️⚠️ **시차를 반드시 지킨다** (브리핑은 한국 08:00)
```
✅ 당일 새벽 값 사용  미국(06:00) · 유럽(01:00) · 유가·금(선물, 거의 24시간)
⚠️ **하루 늦게** 사용  일본·중국·홍콩·대만 — 한국과 같은 시간대다
   ⇒ 한국 T일에 쓸 수 있는 건 아시아 **T-1일 종가**다
```
⚠️ 판정: 도달률(+20%) · 평균 · 연도별 · **표본**.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_목표 = 20.0
_최대보유 = 40
_YH = os.path.join(O._DATA, "yahoo")

# ⚠️ 아시아는 한국과 같은 시간대 — **하루 늦게** 쓴다
아시아 = {"IDX_N225", "000001.SS", "IDX_HSI", "IDX_TWII", "IDX_KS11", "IDX_KQ11"}


def main():
    print("  자료 읽는 중...", flush=True)
    # ── Yahoo 지표 ──
    지표 = {}
    for f in sorted(glob.glob(os.path.join(_YH, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        키 = os.path.basename(f)[:-5]
        종 = d.get("종가") or {}
        if len(종) < 500:
            continue
        k = sorted(종)
        등락 = {}
        for j in range(1, len(k)):
            p = 종[k[j - 1]]
            if p:
                등락[k[j]] = (종[k[j]] / p - 1) * 100
        지표[키] = {"이름": d.get("이름") or 키, "등락": 등락,
                    "아시아": 키 in 아시아}
    print(f"  Yahoo 지표 {len(지표)}종", flush=True)

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종)
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

    # ⚠️⚠️ 한국 T일에 **쓸 수 있는** 각 지표 값을 미리 만든다
    #   미국·유럽·원자재 : T 직전 거래일 (한국 새벽에 확정)
    #   아시아          : **T-1일 이전** (같은 시간대라 하루 늦다)
    import datetime as dt
    쓸값 = {}
    for 키, v in 지표.items():
        등락 = v["등락"]
        ek = sorted(등락)
        t = {}
        for d in 날:
            if v["아시아"]:
                # 하루 늦게: 한국 전 거래일보다 앞선 것
                i = 날.index(d) if d in 날 else -1
                기준 = 날[i - 1] if i > 0 else d
            else:
                기준 = d
            앞 = [x for x in ek if x < 기준]
            if not 앞:
                continue
            전 = max(앞)
            try:
                if (dt.datetime.strptime(기준, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            t[d] = 등락[전]
        쓸값[키] = t
    print("  시차 반영 완료", flush=True)

    def 재무값(code, d8):
        줄 = 재무.get(code)
        if not 줄:
            return None
        m = None
        for 적용, v in 줄:
            if 적용 <= d8:
                m = v
            else:
                break
        return m

    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _최대보유 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -3:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            if (c1 - s20) / (2 * sd) > -1.0 or sq[k - 20] <= 0:
                continue
            if (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            결과, 며칠 = None, _최대보유
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    break
                if vv[0] * bb2[1] >= 매수 * (1 + _목표 / 100):
                    결과, 며칠 = _목표 - _비용, max(1, h)
                    break
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과 = (끝[0] / 매수 - 1) * 100 - _비용
            사건.append({"날": 다음, "code": code, "결과": 결과, "며칠": 며칠,
                        "도달": 결과 > _목표 - _비용 - 1e-9, "상대갭": g - 시갭})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    n = len(사건)
    기준도달 = sum(1 for x in 사건 if x["도달"]) / n * 100
    기준평균 = st.mean([x["결과"] for x in 사건])
    년수 = len([d for d in 날 if d >= _시작]) / 245
    print(f"\n  사건 {n:,}건 · 기준선 도달률 **{기준도달:.1f}%** · "
          f"평균 {기준평균:+.2f}%\n", flush=True)

    def 재기(a, 라, 폭=26):
        if len(a) < 40:
            return None
        d2 = sum(1 for x in a if x["도달"]) / len(a) * 100
        m = st.mean([x["결과"] for x in a])
        해 = {}
        for x in a:
            해.setdefault(x["날"][:4], []).append(x["결과"])
        전 = 플 = 0
        for y, arr in 해.items():
            if len(arr) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        별 = "⭐" if (d2 - 기준도달 > 5 and 플 / max(1, 전) >= 2 / 3) else "  "
        print(f"    {라:<{폭}}{len(a):>7}건{d2:>8.1f}%{d2-기준도달:>+8.1f}%p"
              f"{m:>+9.2f}%{f'{플}/{전}':>8}{별}")
        return d2 - 기준도달

    머 = (f"    {'지표':<26}{'표본':>9}{'도달률':>8}{'기준대비':>9}"
          f"{'평균':>9}{'연도별':>8}")

    # ══ A 전체 훑기 ══
    print("  ══ A **32개 지표를 하나씩 붙여본다** (그 지표가 하락한 날) ══")
    print("     ⚠️ 아시아는 **하루 늦게** 반영했다 (같은 시간대)")
    print(머)
    점수 = []
    for 키 in sorted(지표, key=lambda z: 지표[z]["이름"]):
        t = 쓸값.get(키) or {}
        a = [x for x in 사건 if t.get(x["날"]) is not None and t[x["날"]] <= -0.5]
        라 = f"{지표[키]['이름']}" + (" (하루늦)" if 지표[키]["아시아"] else "")
        r = 재기(a, f"{라} −0.5%↓")
        if r is not None:
            점수.append((r, 키, 라, len(a)))

    print(f"\n  ══ ⭐ **가장 잘 듣는 지표 순** ══")
    점수.sort(reverse=True)
    print(f"    {'순':<4}{'지표':<26}{'기준대비':>10}{'표본':>9}")
    for i2, (r, 키, 라, ln) in enumerate(점수[:12], 1):
        print(f"    {i2:<4}{라:<26}{r:>+9.1f}%p{ln:>8}건")

    # ══ B XLK vs IWM vs SOXX ══
    print(f"\n  ══ B ⭐ **미국 안에서 어느 쪽이 한국과 맞나** ══")
    print("     (사용자 지적: XLK 기술 vs IWM 소형주 — 우리는 한국 **소형주**를 산다)")
    print(머)
    for 키 in ("SPY", "QQQ", "SOXX", "SMH", "XLK", "IWM", "DIA"):
        t = 쓸값.get(키) or {}
        if not t:
            continue
        for 문 in (-0.5, -1.0):
            a = [x for x in 사건 if t.get(x["날"]) is not None and t[x["날"]] <= 문]
            재기(a, f"{지표[키]['이름']} {문}%↓")

    # ══ C 아시아 ══
    print(f"\n  ══ C ⭐ **아시아** — 산업 구조가 비슷하다 (⚠️ 하루 늦게) ══")
    print(머)
    for 키 in ("IDX_TWII", "IDX_N225", "IDX_HSI", "000001.SS"):
        t = 쓸값.get(키) or {}
        if not t:
            continue
        for 문 in (-0.5, -1.0):
            a = [x for x in 사건 if t.get(x["날"]) is not None and t[x["날"]] <= 문]
            재기(a, f"{지표[키]['이름']} {문}%↓")

    # ══ D VIX ══
    print(f"\n  ══ D **VIX(공포지수)** — 한 번도 못 써봤다 ══")
    print("     ⚠️ VIX는 **오를수록** 공포다. 방향이 반대다")
    print(머)
    t = 쓸값.get("IDX_VIX") or {}
    if t:
        for 문, 라 in ((5, "+5%↑"), (10, "+10%↑"), (-5, "−5%↓")):
            if 문 > 0:
                a = [x for x in 사건
                     if t.get(x["날"]) is not None and t[x["날"]] >= 문]
            else:
                a = [x for x in 사건
                     if t.get(x["날"]) is not None and t[x["날"]] <= 문]
            재기(a, f"VIX {라}")

    # ══ E 원자재·금리·환율 ══
    print(f"\n  ══ E **원자재·금리·환율** ══")
    print(머)
    for 키 in ("CL=F", "GC=F", "HG=F", "IDX_TNX", "KRW=X", "DX-Y.NYB"):
        t = 쓸값.get(키) or {}
        if not t:
            continue
        for 문 in (-1.0, 1.0):
            표 = "↓" if 문 < 0 else "↑"
            if 문 < 0:
                a = [x for x in 사건
                     if t.get(x["날"]) is not None and t[x["날"]] <= 문]
            else:
                a = [x for x in 사건
                     if t.get(x["날"]) is not None and t[x["날"]] >= 문]
            재기(a, f"{지표[키]['이름']} {abs(문)}%{표}")

    # ══ F 조합 ══
    print(f"\n  ══ F **둘을 겹치면** (상위 지표끼리) ══")
    print(머)
    상위 = [키 for _, 키, _, _ in 점수[:5]]
    for i2 in range(len(상위)):
        for j2 in range(i2 + 1, len(상위)):
            t1 = 쓸값.get(상위[i2]) or {}
            t2 = 쓸값.get(상위[j2]) or {}
            a = [x for x in 사건
                 if t1.get(x["날"]) is not None and t1[x["날"]] <= -0.5
                 and t2.get(x["날"]) is not None and t2[x["날"]] <= -0.5]
            재기(a, f"{지표[상위[i2]]['이름'][:10]} + {지표[상위[j2]]['이름'][:10]}")

    print("\n  읽는 법")
    print("    - **기준대비**가 +5%p 넘고 연도별을 통과하면 ⭐ — 쓸 값어치가 있다")
    print("    - ⚠️ 아시아는 **하루 늦게** 반영했다. 그래도 좋으면 진짜다")
    print("    - ⚠️ 표본이 줄면 그만큼 신호 빈도가 준다. 자본 시뮬로 다시 봐야 한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
