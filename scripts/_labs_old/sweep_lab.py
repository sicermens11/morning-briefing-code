#!/usr/bin/env python3
r"""
sweep_lab.py — **안 쓴 데이터를 빠짐없이 훑는다** (2026-09-03 · 57차)

⚠️⚠️ **사용자 지적.**
   *"수집하는 정보 100여 가지도 테스트해봐야 하는 거 아니야? 빠짐없이 다 테스트하는 게 맞지 않아?"*
   → 맞다. 지금까지 **가격·수급·공시 위주로만** 했고 나머지는 미뤄뒀다. 여기서 전부 훑는다.

## 기반 신호 (52~56차에서 확정)
```
시장 −0.3%↓ + 상대 −4%p↓ + 볼하단 + 20일−10%↓ · 소형
  D+20 +21.09% · 승률 84.0% · 15해 15해 + · 연 76건
```
여기에 **안 쓴 데이터를 하나씩 조건으로 붙여** 도움이 되는지 본다.

## 훑는 것 — 기간이 다르니 **표본과 기간을 반드시 같이 찍는다**
```
지수 71개 (16.7년 · 유일하게 완비)
  코스피/코스닥 등락 · 코스피200 섹터 12개 · 대형/중형/소형주 지수 · 코스피−코스닥 격차
매크로 (2.6~3년 — 짧다)
  선물(코스피200) · 국고채 금리 · 유가(휘발유) · 금 · 원달러 · S&P500
재무 16항목 (⚠️ naver-quarter가 **최근 6분기**뿐이라 과거 적용이 거의 안 된다)
  PER · PBR · ROE · 부채비율 · 영업이익률 · 순이익률 · 유보율 · 당좌비율 · EPS · BPS · 주당배당금
대주주 (2년)
  최근 20일 지분 +1%p↑ / −1%p↓
```
⚠️⚠️ **기간이 짧으면 「신호 없음」이 아니라 「판단 불가」다.** 그 구분을 표에 찍는다.
⚠️ 판정: 절대 수익 · 승률 · 연도별. 매수 다음날 시가 · D+20 · 비용 0.26%.
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
재무항목 = ["PER", "PBR", "ROE", "부채비율", "영업이익률", "순이익률",
            "유보율", "당좌비율", "EPS", "BPS", "주당배당금"]


def _숫(x):
    try:
        return float(str(x).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _krx추가(폴더, 키, 뽑기):
    """krx-extra의 한 폴더를 {날: 값}으로. 뽑기(rows)가 값을 낸다."""
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-extra", 폴더, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        rows = (d.get("자료") or {}).get(키) or []
        v = 뽑기(rows)
        if v is not None:
            out[d.get("기준일")] = v
    return out


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    지수, 기본, 수급 = O._지수(), O._기본(), O._수급()
    분기 = O._분기재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # 지수 전체 (이름 -> {날: 종가})
    지수전체 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for n, v in (d.get("지수") or {}).items():
            c = v.get("종가")
            if c:
                try:
                    지수전체.setdefault(n, {})[d["기준일"]] = float(c)
                except (TypeError, ValueError):
                    pass
    print(f"  지수 {len(지수전체)}종", flush=True)

    # ⚠️⚠️ **2026-09-03 성능 수정.** 전에는 매 호출마다 `[x for x in a if x < d8]`로
    #   전체 날짜(4,103일)를 훑었다. 지수 16종 × 4,103일이면 **2억 6천만 연산**이라 안 끝난다.
    #   ⇒ 등락률을 **미리 한 번** 계산해 표로 만든다.
    등락표 = {}
    for n, a in 지수전체.items():
        키 = sorted(a)
        t = {}
        for j in range(1, len(키)):
            p, c = a[키[j - 1]], a[키[j]]
            if p and c:
                t[키[j]] = (c / p - 1) * 100
        등락표[n] = t

    def 지수등락(이름, d8):
        return (등락표.get(이름) or {}).get(d8)

    # 매크로
    선물 = _krx추가("선물", "fut_bydd_trd", lambda rows: next(
        (_숫(r.get("CMPPREVDD_PRC")) for r in rows
         if "코스피200" in str(r.get("PROD_NM") or "") and r.get("MKT_NM") == "정규"), None))
    국고채 = _krx추가("국고채", "kts_bydd_trd", lambda rows: next(
        (_숫(r.get("CMPPREVDD_PRC")) for r in rows
         if str(r.get("GOVBND_ISU_TP_NM") or "") == "지표"), None))
    유가 = _krx추가("일반상품", "oil_bydd_trd", lambda rows: next(
        (_숫(r.get("WT_AVG_PRC")) for r in rows
         if "휘발유" in str(r.get("OIL_NM") or "")), None))
    금 = _krx추가("일반상품", "gold_bydd_trd", lambda rows:
                  _숫(rows[0].get("TDD_CLSPRC")) if rows else None)
    try:
        미 = json.load(io.open(os.path.join(O._DATA, "us-index.json"),
                               encoding="utf-8-sig"))
    except Exception:
        미 = {}
    try:
        환 = json.load(io.open(os.path.join(O._DATA, "fx-daily.json"),
                               encoding="utf-8-sig"))
    except Exception:
        환 = {}
    print(f"  선물 {len(선물)}일 · 국고채 {len(국고채)}일 · 유가 {len(유가)}일 "
          f"· 금 {len(금)}일 · 미국 {len(미)}종 · 환율 {len(환)}종", flush=True)

    # ⚠️ 여기도 같은 이유로 미리 만든다.
    def _변화표(표):
        키 = sorted(표)
        t = {}
        for j in range(1, len(키)):
            a, b = 표[키[j - 1]], 표[키[j]]
            if a:
                t[키[j]] = (b / a - 1) * 100
        return t

    변화 = {"유가(휘발유)": _변화표(유가), "금": _변화표(금),
            "환율 USDKRW": _변화표({k: _숫(v) for k, v in (환.get("USDKRW") or {}).items()
                                    if _숫(v)}),
            "환율 JPYKRW": _변화표({k: _숫(v) for k, v in (환.get("JPYKRW") or {}).items()
                                    if _숫(v)})}

    def 앞값변화(표, d8):
        return 표.get(d8)

    def 미등락(이름, d8):
        a = 미.get(이름) or {}
        앞 = [x for x in a if x < d8]
        if not 앞:
            return None
        try:
            return float((a[max(앞)] or {}).get("등락률"))
        except (TypeError, ValueError, AttributeError):
            return None

    # 대주주 지분변동
    대주 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-major", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        code = d.get("종목")
        for x in (d.get("이력") or []):
            지, 직 = _숫(x.get("지분율")), _숫(x.get("직전지분율"))
            날짜 = str(x.get("접수일") or "").replace("-", "")
            if 지 is None or 직 is None or len(날짜) != 8:
                continue
            대주.setdefault(code, []).append((날짜, 지 - 직))
    print(f"  대주주 {len(대주):,}종목", flush=True)

    def 재무값(code, d8, 항목):
        줄 = 분기.get(code)
        if not 줄:
            return None
        val = None
        for 적용, 값 in 줄:
            if 적용 <= d8:
                v = 값.get(항목)
                if v is not None:
                    val = v
            else:
                break
        return val

    # 갭
    갭표, 시장갭 = {}, {}
    앞종 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
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
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

    # ── 기반 사건 + 조건들 ──
    섹터들 = [n for n in 지수전체 if n.startswith("코스피 200 ")
              and "비중" not in n and "TOP" not in n and "중소형" not in n][:12]
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 + _보유 >= len(날):
            continue
        다음 = 날[i + 1]
        시갭 = 시장갭.get(다음)
        if 시갭 is None or 시갭 >= -0.3:
            continue
        하루갭 = 갭표.get(다음) or {}
        fl = 수급.get(d1) or {}
        # 그날의 시장·매크로 조건 (종목 무관)
        공통 = {}
        for n in ["코스피", "코스닥", "코스피 대형주", "코스피 소형주"] + 섹터들:
            v = 지수등락(n, d1)
            if v is not None:
                공통[f"지수 {n}"] = v
        kp, kq = 공통.get("지수 코스피"), 공통.get("지수 코스닥")
        if kp is not None and kq is not None:
            공통["코스닥−코스피 격차"] = kq - kp
        대, 소 = 공통.get("지수 코스피 대형주"), 공통.get("지수 코스피 소형주")
        if 대 is not None and 소 is not None:
            공통["소형−대형 격차"] = 소 - 대
        for 라, 표 in (("선물 코스피200", 선물), ("국고채 지표금리", 국고채)):
            if d1 in 표:
                공통[라] = 표[d1]
        for 라 in ("유가(휘발유)", "금", "환율 USDKRW", "환율 JPYKRW"):
            v = 변화[라].get(d1)
            if v is not None:
                공통[라] = v
        for 라 in ("S&P500", "나스닥"):
            v = 미등락(라, 다음)
            if v is not None:
                공통[f"미국 {라}"] = v

        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 3e11:
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
            if (c1 - s20) / (2 * sd) > -1.0:
                continue
            if k < 20 or sq[k - 20] <= 0 or (c1 / sq[k - 20] - 1) * 100 > -10:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -4:
                continue
            끝 = 주가[날[i + 1 + _보유]].get(code)
            if not 끝:
                continue
            매수 = c1 * (1 + g / 100)
            if 매수 <= 0:
                continue
            r = (끝[0] / 매수 - 1) * 100 - _비용
            개 = dict(공통)
            for 항 in 재무항목:
                x = 재무값(code, d1, 항)
                if x is not None:
                    개[f"재무 {항}"] = x
            줄 = 대주.get(code)
            if 줄:
                최근 = [c for (날짜, c) in 줄 if 날짜 <= d1][-1:]
                if 최근:
                    개["대주주 지분변동"] = 최근[0]
            사건.append((d1[:4], r, 개))
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 사건 {len(사건):,}", flush=True)

    년수 = len(날) / 245
    전부 = [x[1] for x in 사건]
    승전 = sum(1 for x in 전부 if x > 0) / len(전부) * 100
    print(f"\n  ══ 기반: 시장−0.3%↓ + 상대−4%p↓ + 볼하단 + 20일−10%↓ · 소형 ══")
    print(f"    평균 {st.mean(전부):+.2f}% · 승률 {승전:.1f}% · "
          f"연 {len(전부)/년수:.0f}건 · 표본 {len(전부):,}")

    축들 = sorted({k for _, _, 개 in 사건 for k in 개})
    print(f"\n  ══ 안 쓴 데이터를 조건으로 붙였을 때 (칸 {len(축들)}개) ══")
    print("     ⚠️ **표본이 적으면 「신호 없음」이 아니라 「판단 불가」다**")
    print(f"    {'조건':<26}{'구간':<14}{'평균':>9}{'기반차':>9}{'승률':>8}"
          f"{'연도별':>8}{'표본':>8}  판정")
    결과 = []
    for 축 in 축들:
        값들 = sorted(개[축] for _, _, 개 in 사건 if 축 in 개)
        if len(값들) < 200:
            print(f"    {축:<26}{'—':<14}{'':>9}{'':>9}{'':>8}{'':>8}"
                  f"{len(값들):>8}  ⚠️ 판단 불가(표본 {len(값들)})")
            continue
        하 = 값들[len(값들) // 3]
        상 = 값들[len(값들) * 2 // 3]
        for 라, 조건 in ((f"하위1/3(≤{하:.2f})", lambda v: v <= 하),
                         (f"상위1/3(≥{상:.2f})", lambda v: v >= 상)):
            a = [(y, r) for y, r, 개 in 사건 if 축 in 개 and 조건(개[축])]
            if len(a) < 100:
                continue
            수 = [r for _, r in a]
            승 = sum(1 for x in 수 if x > 0) / len(수) * 100
            해별 = {}
            for y, r in a:
                해별.setdefault(y, []).append(r)
            전 = 플 = 0
            for y, arr in 해별.items():
                if len(arr) < 10:
                    continue
                전 += 1
                플 += 1 if st.mean(arr) > 0 else 0
            차 = st.mean(수) - st.mean(전부)
            통과 = 전 >= 8 and 플 / 전 >= 2 / 3
            판 = ("⭐ 도움" if (차 > 2 and 승 > 승전 and 통과) else
                  "○ 조금" if 차 > 0 else
                  "❌ 해로움" if 차 < -2 else "  ")
            if 전 < 8:
                판 = f"⚠️ 판단 불가(연도 {전})"
            결과.append((차, 축, 라, st.mean(수), 승, 전, 플, len(수), 판))
            print(f"    {축:<26}{라:<14}{st.mean(수):>+8.2f}%{차:>+8.2f}%"
                  f"{승:>7.1f}%{f'{플}/{전}':>8}{len(수):>8}  {판}")

    print(f"\n  ══ ⭐ 도움이 되는 것 (기반차 +2%p↑ · 승률↑ · 연도별 통과) ══")
    좋 = [x for x in 결과 if x[0] > 2 and x[4] > 승전 and x[5] >= 8
          and x[6] / max(1, x[5]) >= 2 / 3]
    좋.sort(reverse=True)
    if not 좋:
        print("    ❌ 없다")
    for 차, 축, 라, m, 승, 전, 플, n, _ in 좋[:15]:
        print(f"    {축} · {라}   {m:+.2f}% (기반차 {차:+.2f}%p) · 승률 {승:.1f}% "
              f"· {플}/{전} · 표본 {n:,}")

    print(f"\n  ══ ❌ 해로운 것 (기반차 −2%p↓) ══")
    나 = [x for x in 결과 if x[0] < -2]
    나.sort()
    for 차, 축, 라, m, 승, 전, 플, n, _ in 나[:10]:
        print(f"    {축} · {라}   {m:+.2f}% (기반차 {차:+.2f}%p) · 승률 {승:.1f}% "
              f"· 표본 {n:,}")

    print("\n  읽는 법")
    print("    - **「판단 불가」와 「신호 없음」은 다르다.** 표본·연도가 모자라면 판단 불가다")
    print("    - 재무는 `naver-quarter`가 **최근 6분기**뿐이라 과거 적용이 거의 안 된다")
    print("      → 표본이 작게 나오면 그 때문이다. **DART로 과거 재무를 받아야 제대로 잰다**")
    print("    - 매크로(선물·국고채·유가·금·환율·미국)는 **2.6~3년**뿐이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
