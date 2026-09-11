#!/usr/bin/env python3
r"""
fail_lab.py — **진 것들은 왜 졌나** (2026-09-03 · 81차)

⚠️⚠️ **지금까지 이긴 것만 봤다.** 진 것을 한 번도 안 봤다.
```
78차에서 실제로 이런 게 있었다
  인포바인   **-36.1%** (40일 보유)      티비씨   -35.1%
  대영포장    -16.7%                    에스텍    -8.7%
⇒ 손절이 없으니 이런 게 나온다. **왜 그랬는지 알면 피할 수 있을지 모른다**
```

## 재는 것
```
A 진 것과 이긴 것의 **매수 시점 특성**이 다른가
  상대갭 · 볼린저 · 20일낙폭 · 60일낙폭 · 시총 · 거래대금
  재무(잉여금·부채·ROE·영업이익률·유동비율)
  미국 등락 · 시장 갭 · 그날 시가가 저가였나
B 진 것들이 **어떻게 졌나** — 처음부터 빠졌나, 오르다 꺾였나
C ⭐ **피할 수 있었나** — 특성으로 거르면 진 것이 줄고 이긴 것은 남나
D 최악 20건을 **눈으로** 본다
```
⚠️ **사후편향 주의.** 「진 것은 이랬다」는 사실이지만 「이러면 진다」는 결론이 아니다.
   C에서 거른 뒤 **전체 성적이 좋아지는지**를 봐야 한다. 그게 진짜 판정이다.
⚠️ 매도는 76차 규칙(목표 +20% · 최대 D+40 · 손절 없음)을 쓴다.
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


def main():
    print("  자료 읽는 중...", flush=True)
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
                저 = float(v.get("저가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 저, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 저 / 종, 고 / 종)
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    try:
        spy = json.load(io.open(os.path.join(O._DATA, "us-daily", "SPY.json"),
                                encoding="utf-8-sig"))["종가"]
    except Exception:
        spy = {}
    sk = sorted(spy)
    미맵 = {}
    import datetime as dt
    for d in 날:
        앞 = [x for x in sk if x < d]
        if len(앞) < 2:
            continue
        전 = max(앞)
        앞2 = [x for x in sk if x < 전]
        if not 앞2 or not spy[max(앞2)]:
            continue
        try:
            if (dt.datetime.strptime(d, "%Y%m%d")
                    - dt.datetime.strptime(전, "%Y%m%d")).days > 4:
                continue
        except Exception:
            pass
        미맵[d] = (spy[전] / spy[max(앞2)] - 1) * 100

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
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -1.0 or sq[k - 20] <= 0 or sq[k - 60] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > -10:
                continue
            r60 = (c1 / sq[k - 60] - 1) * 100
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            시가바닥 = abs(b0[1] / b0[0] - 1) < 0.002
            # 76차 매도 규칙 + 경로 기록
            결과, 며칠, 최고, 최저 = None, _최대보유, -99.0, 99.0
            for h in range(0, _최대보유 + 1):
                j = i + 1 + h
                if j >= len(날):
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    break
                고2 = vv[0] * bb2[2]
                저2 = vv[0] * bb2[1]
                최고 = max(최고, (고2 / 매수 - 1) * 100)
                최저 = min(최저, (저2 / 매수 - 1) * 100)
                if 결과 is None and 고2 >= 매수 * (1 + _목표 / 100):
                    결과, 며칠 = _목표 - _비용, max(1, h)
            if 결과 is None:
                j = i + 1 + _최대보유
                if j >= len(날):
                    continue
                끝 = 주가[날[j]].get(code)
                if not 끝:
                    continue
                결과 = (끝[0] / 매수 - 1) * 100 - _비용
            사건.append({
                "날": 다음, "code": code, "이름": bb.get("이름") or "",
                "결과": 결과, "며칠": 며칠, "최고": 최고, "최저": 최저,
                "상대갭": g - 시갭, "시장갭": 시갭, "볼린저": 볼,
                "낙폭20": r20, "낙폭60": r60, "시총": 시총 / 1e8,
                "대금": 대금 / 1e8, "미국": 미맵.get(다음),
                "시가바닥": 시가바닥, "잉여금": fm.get("잉여금비율"),
                "부채": fm.get("부채비율"), "ROE": fm.get("ROE"),
                "영업이익률": fm.get("영업이익률"), "유동비율": fm.get("유동비율"),
                "i": i + 1})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)
    년수 = len([d for d in 날 if d >= _시작]) / 245
    이긴 = [x for x in 사건 if x["결과"] > 0]
    진 = [x for x in 사건 if x["결과"] <= 0]
    크게진 = [x for x in 사건 if x["결과"] <= -15]
    print(f"  사건 {len(사건):,}건 · 이긴 것 {len(이긴):,} ({len(이긴)/len(사건)*100:.1f}%)"
          f" · 진 것 {len(진):,} · **-15% 넘게 진 것 {len(크게진):,}**\n", flush=True)

    # ══ A 특성 비교 ══
    print("  ══ A **이긴 것 vs 진 것**의 매수 시점 특성 ══")
    print("     ⚠️ 「진 것은 이랬다」는 사실이지 **「이러면 진다」가 아니다**")
    축 = ["상대갭", "시장갭", "볼린저", "낙폭20", "낙폭60", "시총", "대금",
          "미국", "잉여금", "부채", "ROE", "영업이익률", "유동비율"]
    print(f"    {'특성':<12}{'이긴 것':>11}{'진 것':>11}{'크게진 것':>11}"
          f"{'차이(이-진)':>13}{'판정':>10}")
    후보축 = []
    for a in 축:
        i2 = [x[a] for x in 이긴 if x.get(a) is not None]
        j2 = [x[a] for x in 진 if x.get(a) is not None]
        k2 = [x[a] for x in 크게진 if x.get(a) is not None]
        if len(i2) < 50 or len(j2) < 30:
            continue
        mi, mj = st.median(i2), st.median(j2)
        mk = st.median(k2) if len(k2) >= 10 else float("nan")
        # 사분위 폭으로 표준화
        s = sorted(i2 + j2)
        폭 = (s[len(s) * 3 // 4] - s[len(s) // 4]) or 1e-9
        z = (mi - mj) / 폭
        판 = ("⭐ 뚜렷" if abs(z) > 0.4 else "○ 조금" if abs(z) > 0.2 else "  ")
        if abs(z) > 0.2:
            후보축.append((abs(z), a, mi, mj))
        print(f"    {a:<12}{mi:>11,.2f}{mj:>11,.2f}{mk:>11,.2f}"
              f"{mi-mj:>+13,.2f}{판:>10} (z={z:+.2f})")
    시바이 = sum(1 for x in 이긴 if x["시가바닥"]) / max(1, len(이긴)) * 100
    시바진 = sum(1 for x in 진 if x["시가바닥"]) / max(1, len(진)) * 100
    print(f"    {'시가=저가':<12}{시바이:>10.1f}%{시바진:>10.1f}%")

    # ══ B 어떻게 졌나 ══
    print("\n  ══ B **어떻게 졌나** — 처음부터 빠졌나, 오르다 꺾였나 ══")
    print(f"    {'구분':<24}{'건수':>7}{'최고 도달':>11}{'최저':>10}{'결과':>10}")
    for 라, cond in (("이긴 것", lambda x: x["결과"] > 0),
                     ("진 것 전체", lambda x: x["결과"] <= 0),
                     ("  └ -15% 넘게 진 것", lambda x: x["결과"] <= -15),
                     ("  └ -30% 넘게 진 것", lambda x: x["결과"] <= -30)):
        a = [x for x in 사건 if cond(x)]
        if len(a) < 5:
            continue
        print(f"    {라:<24}{len(a):>7}{st.median([x['최고'] for x in a]):>+10.1f}%"
              f"{st.median([x['최저'] for x in a]):>+9.1f}%"
              f"{st.median([x['결과'] for x in a]):>+9.1f}%")
    한번도 = [x for x in 진 if x["최고"] < 5]
    올랐다 = [x for x in 진 if x["최고"] >= 10]
    print(f"    ⇒ 진 것 중 **한 번도 +5% 못 간 것**: {len(한번도)}건 "
          f"({len(한번도)/max(1,len(진))*100:.0f}%)")
    print(f"    ⇒ 진 것 중 **+10% 넘게 갔다가 꺾인 것**: {len(올랐다)}건 "
          f"({len(올랐다)/max(1,len(진))*100:.0f}%)")

    # ══ C 피할 수 있었나 ══
    def 재기(a, 라):
        if len(a) < 30:
            print(f"    {라:<34}{len(a):>6}건  — 부족")
            return
        t = {}
        for x in a:
            t.setdefault(x["날"], []).append(x["결과"])
        수 = [st.mean(v) for v in t.values()]
        승 = sum(1 for z in 수 if z > 0) / len(수) * 100
        해 = {}
        for d, v in t.items():
            해.setdefault(d[:4], []).append(st.mean(v))
        전 = 플 = 0
        for y, arr in 해.items():
            if len(arr) < 3:
                continue
            전 += 1
            플 += 1 if st.mean(arr) > 0 else 0
        큰손실 = sum(1 for x in a if x["결과"] <= -15)
        print(f"    {라:<34}{len(a):>6}건{st.mean(수):>+9.2f}%{승:>7.1f}%"
              f"{f'{플}/{전}':>8}{len(t)/년수:>7.1f}일{큰손실:>7}건")

    print("\n  ══ C ⭐ **피할 수 있었나** — 걸러도 이긴 것이 남나 ══")
    print("     ⚠️ 거른 뒤 **전체 성적이 좋아져야** 값어치가 있다")
    print(f"    {'조건':<34}{'표본':>8}{'평균':>9}{'승률':>8}{'연도별':>8}"
          f"{'연간':>8}{'큰손실':>7}")
    재기(사건, "전부 (기준선)")
    # >>> 2026-09-03 버그 수정. 쓰지 않는 빈 루프가 남아 있어 터졌다
    #     (후보축은 (z, 축, 이긴중앙, 진중앙) 네 값인데 셋으로 풀려 했다)
    for 라, cond in (
            ("시가 = 저가였던 것만", lambda x: x["시가바닥"]),
            ("어젯밤 미국 하락", lambda x: (x["미국"] or 9) <= 0),
            ("어젯밤 미국 -0.5%↓", lambda x: (x["미국"] or 9) <= -0.5),
            ("시장도 같이 빠진 날 (-0.3%↓)", lambda x: x["시장갭"] < -0.3),
            ("60일 낙폭 -20%↓ 제외", lambda x: x["낙폭60"] > -20),
            ("60일 낙폭 -30%↓ 제외", lambda x: x["낙폭60"] > -30),
            ("시총 1000억↑", lambda x: x["시총"] >= 1000),
            ("거래대금 5억↑", lambda x: x["대금"] >= 5),
            ("잉여금 50%↑", lambda x: (x["잉여금"] or 0) >= 50),
            ("부채비율 50%↓", lambda x: (x["부채"] or 9e9) <= 50),
            ("ROE 5%↑", lambda x: (x["ROE"] or -9e9) >= 5),
            ("영업이익률 5%↑", lambda x: (x["영업이익률"] or -9e9) >= 5),
            ("유동비율 150%↑", lambda x: (x["유동비율"] or 0) >= 150)):
        재기([x for x in 사건 if cond(x)], 라)

    # ══ D 눈으로 ══
    print("\n  ══ D **최악 15건** — 눈으로 본다 ══")
    print(f"    {'매수일':<10}{'종목':<8}{'이름':<12}{'결과':>8}{'최고':>8}"
          f"{'상대갭':>8}{'20일':>8}{'60일':>8}{'시총':>8}{'미국':>8}")
    for x in sorted(사건, key=lambda z: z["결과"])[:15]:
        미 = f"{x['미국']:+.2f}%" if x["미국"] is not None else "  —"
        print(f"    {x['날']:<10}{x['code']:<8}{(x['이름'] or '')[:10]:<12}"
              f"{x['결과']:>+7.1f}%{x['최고']:>+7.1f}%{x['상대갭']:>+7.1f}%"
              f"{x['낙폭20']:>+7.1f}%{x['낙폭60']:>+7.1f}%{x['시총']:>7,.0f}억{미:>8}")

    print("\n  읽는 법")
    print("    - A에서 **z가 큰 특성**이 거를 후보다")
    print("    - **C가 진짜 판정이다.** 걸렀는데 평균·승률·연도별이 좋아져야 한다")
    print("    - ⚠️ 거르면 **표본도 줄어든다.** 연간 신호일이 너무 줄면 못 쓴다")
    print("    - ⚠️⚠️ **사후편향 주의** — 여기서 찾은 건 가설이다. 걷기검증을 다시 해야 한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
