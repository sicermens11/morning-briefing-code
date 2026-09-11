#!/usr/bin/env python3
r"""
day_lab.py — **날짜 단위로 다시 잰다 + 조건 완화 + 연간 재무 투입** (2026-09-03 · 58차)

⚠️⚠️⚠️ **오늘 찾은 심각한 결함.**
```
52~56차의 「최고 신호」  승률 84.0% · 표본 1,271 · 15해 15해 +
실제로는                신호가 난 날 **129일**(16.7년) · **상위 10일이 전체의 69.2%**
                        20200313(코로나) 137건 · 20181030 131건 · 20110809 84건 …
```
**같은 날 148종목은 통계적으로 1건이지 148건이 아니다.** 그 신호의 정체는
「**폭락 다음날 사라**」이고, 폭락은 16.7년에 10~20번뿐이다.
⇒ 표본이 1,271이 아니라 **10~20**이다. 지금 숫자를 그대로 믿으면 안 된다.

## 그래서 셋을 한다
```
① **날짜 단위 재평가** — 하루를 **1건**으로 센다(그날 뽑힌 종목의 평균 수익).
   이게 진짜 표본 크기다.
② **조건 완화판** — 상대갭 문턱을 −1 ~ −5%p, 시장갭 문턱을 0 ~ −1.0%로 훑어
   **빈도-성적 곡선**을 그린다. 일상적으로 쓸 신호가 있는지 본다.
③ **연간 재무 11년치 투입** — `data/dart-fin/2015~2025`가 있는데 **안 쓰고 있었다**.
   sweep(57차)이 표본 188밖에 못 쓴 건 6분기짜리 `naver-quarter`를 봤기 때문이다.
```

⚠️ **look-ahead**: Y년 사업보고서는 Y+1년 3월말 공시 → **Y+1년 4월 1일부터** 쓴다.
⚠️ 판정: 절대 수익 · 다음날 시가 매수 · D+20 · 비용 0.26% · **연도별 3분의 2**.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_보유 = 20


def 연간재무():
    """{코드: [(적용시작일, {지표: 값})]} — ⚠️ Y년치는 **Y+1년 4월 1일부터** 쓴다."""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-fin", "*.json"))):
        y = os.path.basename(f)[:-5]
        if not y.isdigit():
            continue
        적용 = f"{int(y) + 1}0401"
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for code, v in d.items():
            def g(k):
                x = v.get(k)
                return float(x) if isinstance(x, (int, float)) else None
            자산, 자본, 부채 = g("자산총계"), g("자본총계"), g("부채총계")
            매출, 영익, 순익 = g("매출액"), g("영업이익"), g("당기순이익(손실)")
            유자, 유부 = g("유동자산"), g("유동부채")
            잉여 = g("이익잉여금")
            m = {}
            if 자본 and 자본 > 0:
                if 부채 is not None:
                    m["부채비율"] = 부채 / 자본 * 100
                if 순익 is not None:
                    m["ROE"] = 순익 / 자본 * 100
            if 자산 and 자산 > 0 and 순익 is not None:
                m["ROA"] = 순익 / 자산 * 100
            if 매출 and 매출 > 0:
                if 영익 is not None:
                    m["영업이익률"] = 영익 / 매출 * 100
                if 순익 is not None:
                    m["순이익률"] = 순익 / 매출 * 100
            if 유부 and 유부 > 0 and 유자 is not None:
                m["유동비율"] = 유자 / 유부 * 100
            if 순익 is not None:
                m["흑자"] = 1.0 if 순익 > 0 else 0.0
            if 영익 is not None:
                m["영업흑자"] = 1.0 if 영익 > 0 else 0.0
            if 잉여 is not None and 자본 and 자본 > 0:
                m["잉여금비율"] = 잉여 / 자본 * 100
            m["_자본"] = 자본 or 0.0
            m["_순익"] = 순익 or 0.0
            m["_매출"] = 매출 or 0.0
            if m:
                out.setdefault(code, []).append((적용, m))
    for code in out:
        out[code].sort()
    return out


def 요약날(날별, 이름, 년수, 폭=34):
    """⚠️⚠️ **하루를 1건으로 센다.** 그날 뽑힌 종목의 평균 수익이 그날의 성적이다."""
    if len(날별) < 8:
        print(f"    {이름:<{폭}}신호일 {len(날별)}일 — 표본 부족")
        return None
    수 = [st.mean(v) for v in 날별.values()]
    승 = sum(1 for x in 수 if x > 0) / len(수) * 100
    해별 = {}
    for d, v in 날별.items():
        해별.setdefault(d[:4], []).append(st.mean(v))
    전 = 플 = 0
    for y, arr in 해별.items():
        if len(arr) < 3:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(수)
    종목수 = sum(len(v) for v in 날별.values())
    별 = "⭐" if (st.mean(수) > 0 and 승 >= 60 and 전 >= 10
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(수):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(날별)/년수:>7.1f}일{f'{플}/{전}':>8}{len(날별):>7}일{종목수:>7}종{별}")
    return st.mean(수), 승, len(날별)


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본 = O._기본()
    재무 = 연간재무()
    print(f"  연간재무 {len(재무):,}종목 · 해 "
          f"{len({a for v in 재무.values() for a, _ in v})}개", flush=True)
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

    # ── 후보를 한 번만 모은다. 조건(문턱)은 뒤에서 거른다 ──
    후보 = []      # (매수일, 종목, 수익, 상대갭, 시장갭, 볼밴드, 20일수익, 재무)
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        시갭 = 시장갭.get(다음)
        if 시갭 is None or 시갭 >= 0.5:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -1:
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
            볼 = (c1 - s20) / (2 * sd)
            if sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            후보.append((다음, code, (끝[0] / 매수 - 1) * 100 - _비용,
                         g - 시갭, 시갭, 볼, r20, 재무값(code, d1)))
        if i % 800 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    년수 = len(날) / 245
    print(f"  후보 {len(후보):,}건 · {년수:.1f}년\n", flush=True)

    def 모으기(상대, 시장, 볼, r20):
        t = {}
        for d, c, r, rg, mg, bb, rr, fm in 후보:
            if rg <= 상대 and mg < 시장 and bb <= 볼 and rr <= r20:
                t.setdefault(d, []).append(r)
        return t

    머 = (f"    {'조합':<34}{'평균':>9}{'승률':>8}{'하위25%':>10}"
          f"{'연간':>8}{'연도별':>8}{'신호일':>8}{'종목':>8}")

    print("  ══ ① 원래 신호를 **날짜 단위**로 다시 잰다 ══")
    print("     ⚠️ 하루 = 1건. 그날 뽑힌 종목의 평균이 그날 성적이다")
    print(머)
    요약날(모으기(-4, -0.3, -1.0, -10), "원래 신호 (상대−4·시장−0.3)", 년수)

    print("\n  ══ ② 조건 완화 — 빈도를 늘리면 성적이 얼마나 떨어지나 ══")
    print("     ⚠️ 목표: **일상적으로 쓸 수 있는** 신호 (연 50일 이상)")
    print(머)
    for 상대 in (-5, -4, -3, -2, -1):
        요약날(모으기(상대, -0.3, -1.0, -10), f"상대{상대}%p · 시장−0.3 · 볼−1 · 20일−10", 년수)
    print()
    for 시장 in (-1.0, -0.6, -0.3, 0.0, 0.5):
        요약날(모으기(-3, 시장, -1.0, -10), f"상대−3 · **시장{시장:+.1f}** · 볼−1 · 20일−10", 년수)
    print()
    for 볼, r20 in ((-1.0, -10), (-0.7, -10), (-0.5, -5), (-0.3, 0), (0.0, 99)):
        요약날(모으기(-3, 0.5, 볼, r20), f"상대−3 · 시장무관 · **볼{볼:+.1f} · 20일{r20}**", 년수)

    print("\n  ══ ③ 연간 재무 11년치를 조건으로 (2016-04 이후만 가능) ══")
    print("     ⚠️ Y년 사업보고서는 **Y+1년 4월 1일부터** 쓴다 (look-ahead 방지)")
    바탕 = [x for x in 후보 if x[3] <= -3 and x[5] <= -1.0 and x[6] <= -10
            and x[0] >= "20160401"]
    있 = [x for x in 바탕 if x[7]]
    print(f"     바탕 {len(바탕):,}건 중 재무 있는 것 {len(있):,}건 "
          f"({len(있)/max(1,len(바탕))*100:.0f}%)")
    print(머)

    def 재무모으기(cond):
        t = {}
        for d, c, r, rg, mg, bb, rr, fm in 있:
            if cond(fm):
                t.setdefault(d, []).append(r)
        return t

    요약날(재무모으기(lambda m: True), "재무 있는 것 전부 (기준선)", 년수)
    for 항, 단위 in (("부채비율", "%"), ("ROE", "%"), ("ROA", "%"),
                     ("영업이익률", "%"), ("순이익률", "%"),
                     ("유동비율", "%"), ("잉여금비율", "%")):
        값 = sorted(m[항] for _, _, _, _, _, _, _, m in 있 if 항 in m)
        if len(값) < 200:
            print(f"    {항:<34}표본 {len(값)} — 부족")
            continue
        하, 상 = 값[len(값) // 3], 값[len(값) * 2 // 3]
        요약날(재무모으기(lambda m, h=하, a=항: a in m and m[a] <= h),
               f"{항} 하위1/3 (≤{하:.1f}{단위})", 년수)
        요약날(재무모으기(lambda m, s=상, a=항: a in m and m[a] >= s),
               f"{항} 상위1/3 (≥{상:.1f}{단위})", 년수)
    요약날(재무모으기(lambda m: m.get("흑자") == 1.0), "**흑자 기업만**", 년수)
    요약날(재무모으기(lambda m: m.get("흑자") == 0.0), "  (참고) 적자 기업만", 년수)
    요약날(재무모으기(lambda m: m.get("영업흑자") == 1.0), "**영업흑자 기업만**", 년수)
    요약날(재무모으기(lambda m: m.get("흑자") == 1.0 and m.get("부채비율", 999) <= 100),
           "흑자 + 부채비율 100%↓", 년수)

    print("\n  ══ 신호가 난 날 — 몰림 확인 ══")
    t = 모으기(-4, -0.3, -1.0, -10)
    v = sorted(((len(x), d) for d, x in t.items()), reverse=True)
    총 = sum(n for n, _ in v)
    print(f"    신호일 {len(t)}일 · 종목 {총:,}건")
    for k in (1, 3, 5, 10, 20):
        if k <= len(v):
            print(f"      상위 {k:>2}일이 종목의 {sum(n for n,_ in v[:k])/총*100:5.1f}%")
    print("    가장 몰린 날: " + " · ".join(f"{d}({n})" for n, d in v[:6]))

    print("\n  읽는 법")
    print("    - **①의 표본이 진짜 표본이다.** 「신호일」 칸이 통계의 근거 개수다")
    print("    - ②에서 **연간 50일 이상 + 연도별 통과**가 나오면 브리핑에 쓸 수 있다")
    print("    - ③은 2016-04부터만 잰다 — 그래서 ②와 직접 견주면 안 된다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
