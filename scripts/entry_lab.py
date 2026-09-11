#!/usr/bin/env python3
r"""
entry_lab.py — **언제 사고 언제 파나 · 손절은 어디에** (2026-09-01 신설)

⚠️⚠️⚠️ **이 스크립트를 만든 진짜 이유 — 기존 분석에 look-ahead 오류가 있다.**
```
갭①은 「장 마감 후(15:30 이후) 공시」다.
그런데 gap1_lab·gap_all·omni_lab은 전부 **그날 종가(c1)에 샀다고 가정**한다.
⚠️ 15:30에 장이 닫혔는데 16:00 공시를 보고 그날 종가에 살 수는 없다.
   → 실제로 살 수 있는 가장 빠른 시점은 **다음날 시가**다.
   → 그 사이 **갭상승분을 우리가 못 먹는데 성적에는 들어가 있다.**
   → **+1.490%p는 부풀려진 숫자일 수 있다.**
```
이 스크립트가 그 차이를 숫자로 낸다.

**재는 것**
```
매수 시점   ① D 종가 (기존 방식 ⚠️불가능)  ② D+1 시가 (현실)  ③ D+1 종가 (하루 늦게)
보유 기간   1 · 3 · 5 · 10 · 20 거래일
손절        없음 · −5% · −7% · −10%   (보유 중 **저가**가 닿으면 그 값에 판다)
```
⚠️ 손절은 **저가 기준**이라 낙관적이다 — 실제로는 손절가 아래로 갭하락하면 더 나쁘다.

⚠️ 네 겹 규칙: 초과수익(실제 지수) · 국면 분리 · 표본 명시 · 여러 지평.
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 3, 5, 10, 20)
_손절 = (None, -0.05, -0.07, -0.10)
_MIN = 50


def _주가full():
    """⚠️ omni_lab의 5-튜플엔 시가·저가가 없다. 여기서는 7개를 든다."""
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"]); 시 = float(v["시가"]); 저 = float(v["저가"])
                if 종 <= 0 or 시 <= 0:
                    continue
                하루[c] = (종, 시, 저, float(v.get("시총") or 0),
                           float(v.get("거래대금") or 0), float(v.get("등락률") or 0),
                           1 if "KOSDAQ" in str(v.get("시장", "")).upper() else 0)
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = _주가full()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    print(f"  주가 {len(날)}일 (시가·저가 포함)", flush=True)

    # (매수시점, 보유, 손절, 국면) → [합, n]
    통 = {}

    def 담(k, v):
        s = 통.setdefault(k, [0.0, 0])
        s[0] += v
        s[1] += 1

    for i, d1 in enumerate(날):
        a = 지수.get(d1)
        if not a:
            continue
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        for code, r in ds.items():
            # ⚠️ 갭①④ 신호만 본다 — 지금까지 가장 좋았던 조합
            if "호재" not in r.get("성격", set()):
                continue
            분 = r.get("분")
            if 분 is None or 분 < 930:
                continue
            v1 = s1.get(code)
            if not v1:
                continue
            종1, 시1, 저1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or abs(등락) >= 1:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if ("관리종목" in 부) or ("SPAC" in 부) or \
               (str(bb.get("상장일") or "") > "20240101") or \
               (bb.get("증권구분") not in (None, "주권")):
                continue
            장 = "KOSDAQ" if 코스닥 else "KOSPI"

            for 시점 in ("D종가(기존⚠️)", "D+1시가(현실)", "D+1종가"):
                if 시점 == "D종가(기존⚠️)":
                    시작i, 매수가 = i, 종1
                else:
                    if i + 1 >= len(날):
                        continue
                    v2 = 주가[날[i + 1]].get(code)
                    if not v2:
                        continue
                    시작i = i + 1
                    매수가 = v2[1] if 시점 == "D+1시가(현실)" else v2[0]
                if 매수가 <= 0 or 지수.get(날[시작i]) is None:
                    continue
                a0 = 지수[날[시작i]]
                for h in _H:
                    j = 시작i + h
                    if j >= len(날) or not 지수.get(날[j]):
                        continue
                    b = 지수[날[j]]
                    for 컷 in _손절:
                        매도가 = None
                        if 컷 is not None:
                            선 = 매수가 * (1 + 컷)
                            # ⚠️ **매수 당일부터** 본다. 시작i+1부터 보면 매수 당일 장중에
                            #    손절선에 닿은 것을 놓쳐 **성적이 낙관 쪽으로 부풀려진다.**
                            #    (D+1시가 매수면 그날 오후에 무너질 수 있다)
                            시작k = 시작i if 시점 != "D종가(기존⚠️)" else 시작i + 1
                            for k in range(시작k, j + 1):
                                vv = 주가[날[k]].get(code)
                                if vv and vv[2] <= 선:      # 저가가 손절선에 닿음
                                    매도가 = 선
                                    break
                        if 매도가 is None:
                            vv = 주가[날[j]].get(code)
                            if not vv:
                                continue
                            매도가 = vv[0]
                        시장 = b[장] / a0[장] - 1
                        초과 = ((매도가 / 매수가 - 1) - 시장) * 100
                        국면 = "상승" if 시장 > 0 else "하락"
                        라 = "없음" if 컷 is None else f"{int(컷*100)}%"
                        담((시점, h, 라, "전체"), 초과)
                        담((시점, h, 라, 국면), 초과)
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print("\n  신호: 호재 + 장 마감 후 + 무반응 + 정상종목 (갭①④)\n")
    for 국면 in ("전체", "상승", "하락"):
        print(f"  ══════ {국면} ══════")
        print(f"    {'매수 시점':<16}{'손절':<7}" + "".join(f"{'D+'+str(h):>13}" for h in _H))
        for 시점 in ("D종가(기존⚠️)", "D+1시가(현실)", "D+1종가"):
            for 컷 in _손절:
                라 = "없음" if 컷 is None else f"{int(컷*100)}%"
                칸 = []
                for h in _H:
                    s = 통.get((시점, h, 라, 국면))
                    칸.append(f"{s[0]/s[1]:+.2f}({s[1]:,})" if s and s[1] >= _MIN else "—")
                if all(c == "—" for c in 칸):
                    continue
                print(f"    {시점 if 컷 is None else '':<16}{라:<7}"
                      + "".join(f"{c:>13}" for c in 칸))
        print()
    print("  ⚠️⚠️ 「D종가(기존)」과 「D+1시가(현실)」의 차이가 **look-ahead로 부풀려졌던 양**이다.")
    print("     장 마감 후 공시를 그날 종가에 살 수는 없다. 그 차이만큼 기존 결론을 깎아야 한다.")
    print("  ⚠️ 손절은 **저가 기준**이라 낙관적이다 — 손절선 아래로 갭하락하면 실제로는 더 나쁘다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
