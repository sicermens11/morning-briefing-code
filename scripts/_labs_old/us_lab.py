#!/usr/bin/env python3
r"""
us_lab.py — **국내 상장 미국 ETF로 「미국 신호」를 시험한다** (2026-09-03 · 66차)

⚠️⚠️ **사용자 질문에서 나왔다.**
   *"우리가 미국 상승 신호를 잡아 수익 실현을 위한 매수 방법에 대한 테스트는 못하나?"*

## 왜 국내 상장 ETF인가
```
미국 지수 원본(us-index.json)  **3년치뿐** — 네이버가 그 이상 안 준다
국내 상장 미국 ETF             KRX가 **2010년부터** 준다 · 거래대금도 충분
  TIGER 미국나스닥100 133690  5,032억   TIGER 미국S&P500 360750  6,182억
  KODEX 미국S&P500 379800     5,181억   TIGER 미국필라델피아반도체 381180  519억
⇒ **원화로 바로 살 수 있다.** 해외 계좌·환전이 필요 없다
```
⚠️⚠️ **구조 주의.** 국내 상장 미국 ETF는 **전날 미국 종가를 반영해 갭으로 시작**한다.
   「미국이 올랐다」를 알고 사면 **이미 갭에 반영돼 있다.** 우리 한국 신호와 같은 구조다.

## 재는 것
```
A 그냥 들고 있기 (기준선) — ETF별 연평균·낙폭
B **빠진 걸 산다**  갭 하락 + 볼린저 하단 + 20일 하락 → 다음날 시가 매수 · D+20
C **오른 걸 산다**  갭 상승 + 볼린저 상단 + 20일 상승 (한국에선 실패했다)
D 문턱 훑기        갭·볼린저·20일 문턱을 흔들어 빈도-성적 곡선
E ⭐ **한국 신호와 겹치나** — 안 겹치면 **노는 82%를 쓸 수 있다**
```
⚠️ ETF는 **재무가 없다.** 「재무 우량」 조건을 못 쓴다 — 가격 조건만으로 승부해야 한다.
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · 비용 0.26%(ETF는 증권거래세 면제라 실제론 더 싸다)
      · **날짜 단위** · 연도별 3분의 2.
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
_보유 = 20
_ETF = os.path.join(O._DATA, "etf-krx")
# ⚠️ 거래대금 상위 + 이력이 긴 것. 이름이 바뀐 적이 있어 **코드로** 잡는다
대상 = {
    "133690": "TIGER 미국나스닥100",
    "360750": "TIGER 미국S&P500",
    "379800": "KODEX 미국S&P500",
    "381180": "TIGER 미국필라델피아반도체",
    "390390": "KODEX 미국반도체",
    "367380": "ACE 미국나스닥100",
    "360200": "ACE 미국S&P500",
    "458730": "TIGER 미국배당다우존스",
}


def 재기(날별, 이름, 년수, 폭=34):
    if len(날별) < 8:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 부족")
        return None
    수 = [st.mean(v) for v in 날별.values()]
    승 = sum(1 for x in 수 if x > 0) / len(수) * 100
    해 = {}
    for d, v in 날별.items():
        해.setdefault(d[:4], []).append(st.mean(v))
    전 = 플 = 0
    for y, arr in 해.items():
        if len(arr) < 3:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(수)
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 6
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/max(0.1,년수):>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{별}")
    return set(날별)


def main():
    print("  ETF 자료 읽는 중...", flush=True)
    파일 = sorted(glob.glob(os.path.join(_ETF, "*.json")))
    if len(파일) < 500:
        print(f"  ⚠️ etf-krx가 {len(파일)}일뿐이다. collect_krx_etf.py를 먼저 돌려야 한다")
        return 1
    시세 = {}      # code -> {날: (시가, 종가, 거래대금)}
    for f in 파일:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        d8 = d["기준일"]
        for c, v in (d.get("종목") or {}).items():
            if c not in 대상:
                continue
            종, 시 = v.get("종가"), v.get("시가")
            if not 종 or 종 <= 0:
                continue
            시 = 시 if (시 and 시 > 0) else 종
            시세.setdefault(c, {})[d8] = (시, 종, v.get("거래대금") or 0)
    print(f"  ETF {len(파일):,}일 · 대상 {len(시세)}종목", flush=True)
    for c in sorted(시세, key=lambda x: -len(시세[x])):
        k = sorted(시세[c])
        대 = st.median([시세[c][d][2] for d in k[-250:]]) if len(k) >= 250 else 0
        print(f"    {c} {대상[c]:<24} {k[0]} ~ {k[-1]} · {len(k):,}일 "
              f"· 최근 거래대금 중앙 {대/1e8:,.0f}억")

    # ══ A 그냥 들고 있기 ══
    print("\n  ══ A 그냥 들고 있기 (기준선) ══")
    print(f"    {'ETF':<28}{'연평균':>10}{'최대낙폭':>10}{'일수':>8}{'해':>7}")
    for c in sorted(시세, key=lambda x: -len(시세[x])):
        k = sorted(시세[c])
        if len(k) < 300:
            continue
        해 = len(k) / 245
        연 = ((시세[c][k[-1]][1] / 시세[c][k[0]][1]) ** (1 / 해) - 1) * 100
        최고 = 낙 = 시세[c][k[0]][1]
        낙폭 = 0.0
        for d in k:
            v = 시세[c][d][1]
            최고 = max(최고, v)
            낙폭 = min(낙폭, v / 최고 - 1)
        print(f"    {대상[c]:<28}{연:>+9.2f}%{낙폭*100:>9.1f}%{len(k):>8}{해:>7.1f}")

    # ══ 후보 모으기 ══
    def 후보모으기(code):
        k = sorted(시세[code])
        if len(k) < 300:
            return []
        종 = [시세[code][d][1] for d in k]
        out = []
        for i in range(60, len(k) - 1 - _보유):
            c1 = 종[i]
            s20 = st.mean(종[i - 19:i + 1])
            sd = st.pstdev(종[i - 19:i + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 종[i - 20] <= 0:
                continue
            r20 = (c1 / 종[i - 20] - 1) * 100
            시, _, 대 = 시세[code][k[i + 1]]
            갭 = (시 / c1 - 1) * 100
            if abs(갭) > 20:
                continue
            끝 = 종[i + 1 + _보유]
            if 시 <= 0:
                continue
            out.append((k[i + 1], (끝 / 시 - 1) * 100 - _비용, 갭, 볼, r20, 대))
        return out

    전체 = {c: 후보모으기(c) for c in 시세}
    긴것 = sorted(전체, key=lambda c: -len(전체[c]))
    주력 = [c for c in 긴것 if len(전체[c]) >= 800][:4]
    print(f"\n  주력 ETF (후보 800건 이상): "
          + " · ".join(f"{대상[c]}({len(전체[c]):,})" for c in 주력))

    def 모으기(codes, 갭문, 볼문, r문, 위=False):
        t = {}
        for c in codes:
            for d, r, g, b, rr, 대 in 전체[c]:
                if 위:
                    if g >= 갭문 and b >= 볼문 and rr >= r문:
                        t.setdefault(d, []).append(r)
                else:
                    if g <= 갭문 and b <= 볼문 and rr <= r문:
                        t.setdefault(d, []).append(r)
        return t

    년 = {}
    for c in 주력:
        for d, *_ in 전체[c]:
            년[d] = 1
    년수 = len(년) / 245 if 년 else 1

    머 = (f"    {'조합':<34}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}")
    print(f"\n  ══ B **빠진 걸 산다** (주력 {len(주력)}종목 · D+{_보유}) ══")
    print(머)
    미국신호 = None
    for 갭, 볼, r in ((99, 99, 99), (0, 99, 99), (-1, -1.0, -5), (-1.5, -1.0, -10),
                      (-2, -1.0, -10), (-1, -1.5, -10), (-2, -1.5, -15)):
        라 = ("기준선 (조건 없음)" if 갭 == 99 else
              f"갭≤{갭}% · 볼≤{볼} · 20일≤{r}%")
        s = 재기(모으기(주력, 갭, 볼, r), 라, 년수)
        if 갭 == -1.5:
            미국신호 = s

    print(f"\n  ══ C **오른 걸 산다** (한국에선 실패했다) ══")
    print(머)
    for 갭, 볼, r in ((1, 1.0, 5), (1.5, 1.0, 10), (2, 1.0, 10), (1, 1.5, 10)):
        재기(모으기(주력, 갭, 볼, r, 위=True),
             f"갭≥{갭}% · 볼≥{볼} · 20일≥{r}%", 년수)

    print(f"\n  ══ D 문턱 훑기 — 빈도-성적 곡선 ══")
    print(머)
    for 갭 in (-0.5, -1, -1.5, -2, -3):
        재기(모으기(주력, 갭, -0.5, 0), f"갭≤{갭}% · 볼≤-0.5 · 20일≤0%", 년수)
    print()
    for 볼 in (0.0, -0.5, -1.0, -1.5):
        재기(모으기(주력, -1, 볼, 0), f"갭≤-1% · **볼≤{볼}** · 20일≤0%", 년수)

    # ══ E 한국 신호와 겹침 ══
    print(f"\n  ══ E ⭐ **한국 신호와 겹치나** ══")
    print("     ⚠️ 안 겹치면 **노는 82%를 드디어 쓸 수 있다**")
    print("     (한국 신호 = 재무 우량 소형주 · 잉여금≥30% · 부채≤80% · 흑자 · 상대−3 · 볼−1 · 20일−10)")
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    갭표, 시장갭, 앞종 = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                if 종 <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d["기준일"]] = 하루
        if len(하루) >= 100:
            시장갭[d["기준일"]] = st.median(list(하루.values()))

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

    한국 = set()
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
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
            한국.add(다음)
            break
    print(f"    한국 신호가 난 날 **{len(한국)}일**")
    print(f"    {'미국 ETF 신호':<34}{'그 날':>8}{'겹침':>8}{'겹침률':>9}{'합치면':>9}")
    for 갭, 볼, r in ((-1, -0.5, 0), (-1.5, -1.0, -10), (-2, -1.0, -10)):
        s = set(모으기(주력, 갭, 볼, r))
        # ⚠️ 한국 신호는 재무가 있는 2016-04부터만 난다. 같은 창으로 자른다
        s2 = {d for d in s if d >= "20160401"}
        한2 = {d for d in 한국 if d >= "20160401"}
        겹 = len(s2 & 한2)
        print(f"    {f'갭≤{갭}% · 볼≤{볼} · 20일≤{r}%':<34}{len(s2):>8}{겹:>8}"
              f"{겹/max(1,len(s2))*100:>8.1f}%{len(s2|한2):>9}일")
    print(f"    {'(한국 신호 단독 · 2016-04~)':<34}"
          f"{len({d for d in 한국 if d >= '20160401'}):>8}")

    print("\n  읽는 법")
    print("    - B가 A(그냥 들고 있기)보다 나아야 신호로 쓸 값어치가 있다")
    print("    - **E의 겹침률이 낮고 B가 좋으면** 한국 신호와 합쳐 자금을 더 쓸 수 있다")
    print("    - ⚠️ ETF는 재무가 없다. **가격 조건만**으로 승부해야 한다")
    print("    - ⚠️ 국내 상장 미국 ETF는 **전날 미국 종가를 갭에 반영**한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
