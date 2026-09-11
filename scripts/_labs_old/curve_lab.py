#!/usr/bin/env python3
r"""
curve_lab.py — **수익 곡선의 모양: 길게 가는 신호인가, 반짝하고 되밀리는가** (2026-09-02 · 38차)

⚠️⚠️ **사용자 취지.**
   *"브리핑에 언급한 종목이 그날 하루라도, 또 장기적으로 상승하면 그걸로 충분해."*
   *"상승의 이유가 땡땡땡이니 상승이 길게 이어지지 않을 수 있다 — 이런 분석도 있으면 좋지"*

## 지금까지 **한 점**만 봤다
```
「D+20에 +1.29%」   ← 이러면 두 신호가 구분이 안 된다
  신호 A  D+1 +0.5 → D+5 +1.8 → D+20 +2.1 → D+60 +2.3    **계속 오른다**
  신호 B  D+1 +1.2 → D+5 +1.5 → D+20 +0.4 → D+60 −0.8    **5일에 정점, 그 뒤 반납**
⇒ B라면 브리핑에 **「5일 안에 정리하세요」**라고 쓸 수 있다
```

## ⭐ 그리고 「그날 하루」를 처음 잰다
```
브리핑을 보고 **09:00~09:30에 산다** → 지금까지 시험은 전부 **종가 매수**였다
여기서는 **D+1 시가 매수**로 잰다 (아침에 사는 것과 가장 가깝다)
그리고 **당일 종가**까지의 수익부터 잰다 — 「그날 하루라도 상승하면 충분」
```

## 재는 것
```
매수    사건 다음날(D+1) **시가**
지평    **당일종가** · D+2 · 3 · 5 · 10 · 20 · 40 · 60 · 120
사건    신고가 첫날 · RSI 과매수 진입 · 볼린저 하단 이탈 · 공시 18유형
낸다    지평별 **절대 수익 + 승률**, 그리고
        **정점이 언제인가** · **정점 이후 얼마나 반납하는가**
```
⚠️ 비용은 왕복 0.26%를 한 번만 뺀다(사서 한 번 판다). 판정은 **절대 수익**(35차 기준).
⚠️ 시가 매수는 갭에 걸린다 — 상한가로 시작하면 못 산다. **그건 42차에서 따로 본다.**
"""
import glob
import io
import json
import os
import re
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
# ⚠️⚠️ **첫 판(2026-09-02)의 설계 결함 둘을 고쳤다.**
#  ① D+120이 마지막이라 거의 모든 사건이 「D+120에 정점」으로 나왔다 — 그 뒤를 안 봐서 생긴 착시다
#     → **D+250(1년)까지** 늘려 정점을 실제로 찾는다
#  ② 절대 수익이라 **시장 상승분이 다 들어 있었다**. 코스피는 16.7년에 4배(연 +8.7%)다.
#     D+120이면 시장만 따라가도 +4.3%다 → 「길게 간다」가 대부분 **그냥 시장이 올랐다**는 뜻이었다
#     → 같은 기간 **코스피 수익률을 빼서** 나란히 찍는다. 판정은 절대 수익으로 하되
#       「시장 덕인지 신호 덕인지」를 같이 보이게 한다
_지평 = [("당일종가", 0), ("D+2", 1), ("D+3", 2), ("D+5", 4), ("D+10", 9),
         ("D+20", 19), ("D+40", 39), ("D+60", 59), ("D+120", 119), ("D+250", 249)]
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]

유형규칙 = [
    ("계약해지", r"공급계약해지|계약해지"), ("수주계약", r"단일판매|공급계약"),
    ("유상증자", r"유상증자"), ("무상증자", r"무상증자"),
    ("전환사채CB", r"전환사채"), ("신주인수권BW", r"신주인수권"),
    ("자사주취득", r"자기주식\s*취득"), ("자사주처분", r"자기주식\s*처분"),
    ("배당", r"배당"), ("실적", r"영업실적|손익구조|매출액또는손익"),
    ("최대주주변경", r"최대주주\s*변경"), ("합병", r"합병"), ("분할", r"분할"),
    ("소송", r"소송"), ("감자", r"감자"), ("횡령배임", r"횡령|배임"),
    ("시설투자", r"신규시설투자|시설투자"), ("특허", r"특허"),
]


def _유형(이름):
    n = re.sub(r"\[[^\]]*\]", "", str(이름 or ""))
    for 라벨, 패턴 in 유형규칙:
        if re.search(패턴, n):
            return 라벨
    return None


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def _주가():
    """⚠️ 여기서는 **시가**도 필요하다. 수정 배율을 시가에도 똑같이 먹인다."""
    원 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            등 = v.get("등락률")
            try:
                등 = float(등) if 등 not in (None, "") else None
            except (TypeError, ValueError):
                등 = None
            if 등 is not None and abs(등) > 31.0:
                등 = None
            try:
                시총 = float(v.get("시총") or 0)
                대금 = float(v.get("거래대금") or 0)
            except (TypeError, ValueError):
                시총 = 대금 = 0.0
            하루[c] = (종, 시, 등, 시총, 대금)
        원[d["기준일"]] = 하루
    날 = sorted(원)
    앞원, 앞수, 배 = {}, {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 시, 등, 시총, 대금) in 원[d].items():
            p, s = 앞원.get(c), 앞수.get(c)
            if p is None or s is None:
                수 = 종
                배[c] = 1.0
            elif 등 is not None:
                수 = s * (1 + 등 / 100.0)
                배[c] = 수 / 종 if 종 else 1.0
            else:
                r = 종 / p - 1 if p > 0 else 0.0
                수 = s * (1 + (0.0 if abs(r) > 0.32 else r))
                배[c] = 수 / 종 if 종 else 1.0
            if 수 <= 0:
                수 = s if s and s > 0 else 종
            앞원[c], 앞수[c] = 종, 수
            하루[c] = (수, 시 * 배.get(c, 1.0), 시총, 대금)   # (수정종가, 수정시가, 시총, 대금)
        out[d] = 하루
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    기본 = O._기본()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종계):,}", flush=True)

    최대 = max(h for _, h in _지평)
    사건 = {}
    앞상태 = {}
    print("  사건 찾는 중...", flush=True)
    for i, d1 in enumerate(날):
        if i < 250 or i + 1 + 최대 >= len(날):
            앞상태 = {}
            continue
        오늘 = {}
        for code, v in 주가[d1].items():
            c1, _시, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
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
            고 = max(sq[k - 250:k + 1])
            신 = bool(고) and c1 >= 고 * 0.999
            변 = [sq[j] - sq[j - 1] for j in range(k - 13, k + 1)]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            상태 = (신, rsi >= 70, 볼 <= -1.0)
            오늘[code] = 상태
            앞 = 앞상태.get(code)
            if 앞 is None:
                continue
            g = _크기(시총)
            if 상태[0] and not 앞[0]:
                사건.setdefault("① 신고가 첫날", []).append((i, code, g))
            if 상태[1] and not 앞[1]:
                사건.setdefault("② RSI 과매수 진입", []).append((i, code, g))
            if 상태[2] and not 앞[2]:
                사건.setdefault("③ 볼린저 하단 이탈", []).append((i, code, g))
        앞상태 = 오늘
        if i % 600 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    날인덱스 = {d: i for i, d in enumerate(날)}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            g0 = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = g0.get("기준일")
        i = 날인덱스.get(d8)
        if i is None or i < 250 or i + 1 + 최대 >= len(날):
            continue
        for x in (g0.get("챙길공시") or []):
            code = x.get("종목코드")
            if not code or code not in 주가[d8]:
                continue
            v = 주가[d8][code]
            if v[2] < O._MIN_MC or v[3] < O._MIN_AMT:
                continue
            라벨 = _유형(x.get("공시명"))
            if 라벨:
                사건.setdefault(f"공 {라벨}", []).append((i, code, _크기(v[2])))
    print(f"  사건 {len(사건)}종 · 총 {sum(len(v) for v in 사건.values()):,}건", flush=True)

    # ⚠️ 같은 기간 코스피를 빼기 위해 지수를 읽는다
    지수 = O._지수()
    ixv, 앞x = [], None
    for d in 날:
        x = (지수.get(d) or {}).get("KOSPI") or 앞x
        if x:
            앞x = x
        ixv.append(x)

    def 곡선(목록):
        """D+1 시가 매수 → 각 지평 종가 매도.
        (절대 수익, **같은 기간 코스피를 뺀 수익**) 두 벌을 낸다.
        ⚠️ 첫 판에서 절대 수익만 보다가 「길게 간다」가 대부분 **그냥 시장이 오른 것**이었다."""
        절대 = {이름: [] for 이름, _ in _지평}
        대비 = {이름: [] for 이름, _ in _지평}
        for (i, code, g) in 목록:
            b = 주가[날[i + 1]].get(code)
            if not b or b[1] <= 0:
                continue
            매수 = b[1]                      # 다음날 시가
            ix0 = ixv[i + 1]
            for 이름, h in _지평:
                j = i + 1 + h
                if j >= len(날):
                    continue
                e = 주가[날[j]].get(code)
                if not e:
                    continue
                r = (e[0] / 매수 - 1) * 100 - _비용
                절대[이름].append(r)
                if ix0 and ixv[j]:
                    대비[이름].append(r - (ixv[j] / ix0 - 1) * 100)
        return 절대, 대비

    이름들 = sorted(사건)
    print(f"\n  ══ 수익 곡선 — D+1 **시가** 매수 후 며칠 뒤 얼마 (절대 수익 · 비용 차감) ══")
    print("     ⚠️ '당일종가'는 **아침에 사서 그날 장 끝에 판 것**이다")
    print(f"\n    {'사건':<20}{'크기':<6}" + "".join(f"{n:>13}" for n, _ in _지평)
          + f"{'표본':>9}")
    표 = {}
    for 이름 in 이름들:
        for g, _, _ in 크기표:
            목록 = [x for x in 사건[이름] if x[2] == g]
            if len(목록) < 400:
                continue
            c, c대 = 곡선(목록)
            줄, 줄대 = [], []
            평균들, 대비들 = [], []
            for n, _ in _지평:
                a, a대 = c[n], c대[n]
                if len(a) < 300:
                    줄.append("-")
                    줄대.append("-")
                    평균들.append(None)
                    대비들.append(None)
                    continue
                m = st.mean(a)
                승 = sum(1 for x in a if x > 0) / len(a) * 100
                줄.append(f"{m:+.2f}({승:.0f})")
                평균들.append(m)
                md = st.mean(a대) if len(a대) >= 300 else None
                줄대.append(f"{md:+.2f}" if md is not None else "-")
                대비들.append(md)
            if all(x is None for x in 평균들):
                continue
            표[(이름, g)] = (평균들, 대비들, len(목록))
            print(f"    {이름:<20}{g:<6}" + "".join(f"{x:>13}" for x in 줄)
                  + f"{len(목록):>9,}")
            print(f"    {'  └ 코스피 뺀 것':<26}" + "".join(f"{x:>13}" for x in 줄대))

    print(f"\n\n  ══ ⭐ 상승이 **길게 가나, 반짝하고 되밀리나** ══")
    print("     ⚠️ 이게 브리핑에 **「며칠 안에 정리하세요」**를 쓸 근거다")
    print("     ⚠️ **판정은 「코스피 뺀 것」으로 한다.** 절대만 보면 시장 상승분에 묻힌다")
    print(f"    {'사건':<20}{'크기':<6}{'정점':>10}{'정점(대비)':>10}"
          f"{'정점(절대)':>10}{'끝':>10}{'반납':>10}   판정")
    for (이름, g), (평균들, 대비들, n) in sorted(표.items(), key=lambda x: -max(
            [v for v in x[1][1] if v is not None] or [-99])):
        유효 = [(i, v) for i, v in enumerate(대비들) if v is not None]
        if len(유효) < 5:
            continue
        # ⚠️ **판정은 「코스피 뺀 것」으로 한다.** 절대 수익만 보면 시장 상승분에 다 묻힌다
        정i, 정v = max(유효, key=lambda x: x[1])
        끝v = 유효[-1][1]
        반납 = 정v - 끝v
        정이름 = _지평[정i][0]
        절대정 = 평균들[정i]
        if 정v <= 0:
            판 = "❌ 시장을 못 넘는다 (올라도 시장 덕이다)"
        elif 정i >= len(_지평) - 2:
            판 = "⭐ 길게 간다 — 1년까지 계속 벌어진다"
        elif 반납 > 정v * 0.5:
            판 = f"⚠️ **반짝**이다 — {정이름} 안에 정리"
        else:
            판 = f"○ {정이름} 부근이 정점, 그 뒤 완만"
        print(f"    {이름:<20}{g:<6}{정이름:>10}{정v:>+9.2f}%"
              f"{(절대정 if 절대정 is not None else 0):>+9.2f}%"
              f"{끝v:>+9.2f}%{반납:>+9.2f}%   {판}")

    print("\n  읽는 법")
    print("    - 표의 값은 **평균 수익(승률%)**이다")
    print("    - '당일종가'가 +이고 승률 50%↑면 **그날 하루만 잡아도 된다**")
    print("    - '반납'이 정점의 절반을 넘으면 **반짝**이다 → 브리핑에 정리 시점을 쓴다")
    print("    - ⚠️ 시가 매수는 갭에 걸린다. 상한가로 시작하면 못 산다 (다음 시험에서 따로 본다)")
    print("    - ⚠️ 공시는 909일(2.6년)뿐이라 예비다. 09-04에 4,102일로 다시 돌린다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
