#!/usr/bin/env python3
r"""
rest_lab2.py — **215차 · 안 써본 재료 아홉** (2026-09-10 신설)

## 사용자 물음
```
「아까 규모 섹터 종목 말고도 한 **10가지 더** 있다고 했는데 그것들도 테스트해본건가?」
```
=> 정직하게: **185차에서 「나누는 법」으로는** 22가지를 다 봤지만(전부 탈락),
   **「재료로 AND/OR 붙이기」로는 아홉 가지를 안 해봤다.**
   209차의 「AND 로 되는 재료 0개」는 **재료를 다 넣고 나온 게 아니다**

## 안 써본 아홉
```
① **외국인 순매수** (20일)      flow-daily
② **기관 순매수** (20일)        flow-daily
③ **투매인가** (거래량 급증)     krx-daily 거래량 / 20일 평균
④ **신저가인가** (250일 최저)
⑤ **며칠째 빠지나** (연속 하락일)
⑥ **빠지는 모양** (한 번에 vs 여러 날에 걸쳐)
⑦ **회사 나이** (상장일부터)     stock-base
⑧ **금리 국면** (미국 기준금리)   fred/AV_FEDFUNDS
⑨ **5% 대량보유** (최근 신고)    dart-major
```

## 판정 기준 (먼저 밝힌다)
```
**AND 로 붙일 때**  ① 승률 **+3%p 이상** ② 기회 **절반 이상** 남음
**OR 로 더할 때**   ① 기회 늘고 ② 승률 **-0.5%p 이내**
둘 다             ③ **최근 3년(2023~)에도** 같은 방향 ④ **바탕 대비**로 잰다
```

쓰는 법:
    python scripts\rest_lab2.py
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_시작 = "20100104"
_최소 = 300


def _수급():
    r"""{날짜: {코드: (외국인, 기관)}}"""
    난것 = {}
    for f in sorted(glob.glob(os.path.join(_BASE, "data", "flow-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        하루 = {}
        for c, v in (d.get("종목") or {}).items():
            try:
                하루[c] = (float(v.get("외국인") or 0), float(v.get("기관") or 0))
            except (TypeError, ValueError):
                continue
        if 하루:
            난것[d8] = 하루
    return 난것


def _대량보유():
    r"""{코드: [접수일…]} — 5% 대량보유 신고가 난 날"""
    난것 = {}
    for f in glob.glob(os.path.join(_BASE, "data", "dart-major", "*.json")):
        c = os.path.basename(f)[:-5]
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        날들 = []
        for r in (d.get("이력") or []):
            z = str(r.get("접수일") or "").replace("-", "")
            if len(z) == 8:
                날들.append(z)
        if 날들:
            난것[c] = sorted(날들)
    return 난것


def _금리():
    p = os.path.join(_BASE, "data", "fred", "AV_FEDFUNDS.json")
    if not os.path.exists(p):
        return {}
    try:
        return json.load(io.open(p, encoding="utf-8-sig")).get("값") or {}
    except Exception:  # noqa: BLE001
        return {}


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    자리 = {d: i for i, d in enumerate(날)}
    print(f"  거래일 {len(날):,}일", flush=True)

    수급 = _수급()
    print(f"  수급 {len(수급):,}일", flush=True)
    보유 = _대량보유()
    print(f"  5%보유 {len(보유):,}종목", flush=True)
    금리 = _금리()
    금날 = sorted(금리)
    print(f"  금리 {len(금리):,}일", flush=True)
    기본 = O._기본()

    # 금리 국면 (60일 전보다 올랐나)
    국면 = {}
    for d in 날:
        # 그날 이하의 마지막 금리
        import bisect as _b
        i = _b.bisect_right(금날, d) - 1
        if i < 60:
            continue
        지금값 = 금리[금날[i]]
        옛값 = 금리[금날[i - 60]]
        국면[d] = 지금값 - 옛값

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)

    print("  사건 만드는 중...", flush=True)
    사건 = []
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        bb = 기본.get(c) or {}
        상장 = str(bb.get("상장일") or "")
        보유날 = 보유.get(c) or []
        for k in range(250, len(vs)):
            시총억 = vs[k][1] / 1e8
            대금억 = vs[k][2] / 1e8
            if 시총억 < 100 or 대금억 < 1.0:
                continue
            c1 = 종[k]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100
            if not ((볼20 is not None and 볼20 <= -0.5) or 낙20 <= -5):
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            d8 = 날[i]
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)

            # ③ 투매 — 그날 거래량 / 20일 평균
            량 = (거량.get(d8) or {}).get(c) or 0
            앞량 = []
            for z in range(max(0, k - 20), k):
                d2 = 날[ii[z]] if z < len(ii) else None
                if d2:
                    v2 = (거량.get(d2) or {}).get(c)
                    if v2:
                        앞량.append(v2)
            투매 = (량 / (sum(앞량) / len(앞량))) if 앞량 else None

            # ④ 신저가 — 250일 최저 대비
            최저 = min(종[k - 250:k + 1])
            신저 = (c1 / 최저 - 1) * 100 if 최저 > 0 else None

            # ⑤ 며칠째 빠지나
            연속 = 0
            for z in range(k, max(0, k - 15), -1):
                if z > 0 and 종[z] < 종[z - 1]:
                    연속 += 1
                else:
                    break

            # ⑥ 빠지는 모양 — 하루 최대 낙폭 / 20일 낙폭
            하루낙 = []
            for z in range(k - 19, k + 1):
                앞 = 종[z - 1]
                if 앞 > 0:
                    하루낙.append((종[z] / 앞 - 1) * 100)
            한방 = (min(하루낙) / 낙20 * 100) if (하루낙 and 낙20 < 0) else None

            # ⑦ 회사 나이 (해)
            나이 = None
            if len(상장) == 8:
                try:
                    나이 = (int(d8[:4]) - int(상장[:4])
                            + (int(d8[4:6]) - int(상장[4:6])) / 12)
                except ValueError:
                    나이 = None

            # ①② 수급 20일 누적
            외, 기 = 0.0, 0.0
            for z in range(max(0, i - 19), i + 1):
                v3 = (수급.get(날[z]) or {}).get(c)
                if v3:
                    외 += v3[0]
                    기 += v3[1]

            # ⑨ 5% 대량보유 — 60일 안에 신고가 있나
            앞60 = 날[max(0, i - 60)]
            보유최근 = any(앞60 <= z <= d8 for z in 보유날)

            사건.append({
                "해": d8[:4], "_날짜": d8,
                "볼20": 볼20, "낙20": 낙20,
                "시총억": 시총억, "대금억": 대금억,
                "외국인20": 외, "기관20": 기,
                "투매": 투매, "신저가": 신저, "연속": 연속,
                "한방": 한방, "나이": 나이,
                "금리국면": 국면.get(d8),
                "보유신고": 보유최근,
                "_20": 뒤,
            })
    print(f"  사건 {len(사건):,}건", flush=True)

    해수 = max(len({x["해"] for x in 사건}), 1)

    def 셈(칸, 최소=None):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < (최소 or _최소):
            return None
        return (len(v), len(v) / 해수,
                sum(1 for z in v if z > 0) / len(v) * 100, sum(v) / len(v))

    def 지금(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] <= -10.0 and 300 <= x["시총억"] < 2000)

    뼈칸 = [x for x in 사건 if 지금(x)]
    r뼈 = 셈(뼈칸)
    뼈최 = 셈([x for x in 뼈칸 if x["해"] >= "2023"], 100)

    print("\n" + "=" * 112)
    print("  215차 · **안 써본 재료 아홉**")
    print("  사용자: 「규모 섹터 종목 말고도 한 **10가지 더** 있다고 했는데")
    print("          그것들도 **테스트해본건가?**」")
    print("  ⚠️ 185차는 「나누는 법」으로만 봤다. **재료로 AND/OR 붙이기**는 안 했다")
    print("=" * 112)
    if r뼈:
        print(f"\n  [뼈대] 지금 규칙 — 1년 {r뼈[1]:.0f}개 · **{r뼈[2]:.1f}%**"
              f" (최근 {뼈최[2] if 뼈최 else 0:.1f}%)")

    재료들 = []
    for 문 in (0, 1e8, 1e9):
        재료들.append((f"외국인20 ≥ {문/1e8:.0f}억주" if 문 else "외국인20 순매수",
                      lambda x, a=문: (x.get("외국인20") or 0) > a))
    재료들.append(("외국인20 **순매도**", lambda x: (x.get("외국인20") or 0) < 0))
    for 문 in (0, 1e8):
        재료들.append((f"기관20 ≥ {문/1e8:.0f}억주" if 문 else "기관20 순매수",
                      lambda x, a=문: (x.get("기관20") or 0) > a))
    for 문 in (1.5, 2.5, 4):
        재료들.append((f"투매 (거래량 {문}배↑)",
                      lambda x, a=문: (x.get("투매") or 0) >= a))
    재료들.append(("투매 아님 (1.2배↓)",
                  lambda x: (x.get("투매") or 9) <= 1.2))
    for 문 in (3, 10, 25):
        재료들.append((f"신저가 +{문}% 안",
                      lambda x, a=문: (x.get("신저가") or 999) <= a))
    for 문 in (3, 5):
        재료들.append((f"{문}일째 하락", lambda x, a=문: (x.get("연속") or 0) >= a))
    재료들.append(("하락 끊김 (연속 0)", lambda x: (x.get("연속") or 0) == 0))
    for 문 in (40, 60):
        재료들.append((f"**한방 낙폭** ({문}%↑)",
                      lambda x, a=문: (x.get("한방") or 0) >= a))
    재료들.append(("여러 날에 걸쳐 (한방 25%↓)",
                  lambda x: 0 < (x.get("한방") or 0) <= 25))
    for 문 in (3, 10, 20):
        재료들.append((f"회사 나이 {문}해↑",
                      lambda x, a=문: (x.get("나이") or 0) >= a))
    재료들.append(("회사 나이 5해↓",
                  lambda x: 0 < (x.get("나이") or 99) <= 5))
    재료들.append(("금리 **인하 국면**",
                  lambda x: (x.get("금리국면") is not None
                             and x["금리국면"] <= -0.2)))
    재료들.append(("금리 **인상 국면**",
                  lambda x: (x.get("금리국면") is not None
                             and x["금리국면"] >= 0.2)))
    재료들.append(("금리 동결",
                  lambda x: (x.get("금리국면") is not None
                             and abs(x["금리국면"]) < 0.2)))
    재료들.append(("⭐ 5%보유 신고 60일 안", lambda x: bool(x.get("보유신고"))))
    재료들.append(("5%보유 신고 없음", lambda x: not x.get("보유신고")))

    print(f"\n  {'재료':<26}{'AND 이김':>9}{'AND 기회':>9}{'AND 최근':>9}"
          f"{'  |':<3}{'OR 이김':>8}{'OR 기회':>8}   판정")
    됨A, 됨O = [], []
    for 라, fn in 재료들:
        A칸 = [x for x in 뼈칸 if fn(x)]
        rA = 셈(A칸, 100)
        O칸 = [x for x in 사건 if 지금(x) or fn(x)]
        rO = 셈(O칸)
        if not rA or not rO or not r뼈:
            print(f"  {라:<26}{'표본 부족':>9}")
            continue
        rA최 = 셈([x for x in A칸 if x["해"] >= "2023"], 60)
        기A = rA[0] / r뼈[0] * 100
        차A = rA[2] - r뼈[2]
        기O = rO[0] / r뼈[0] * 100
        차O = rO[2] - r뼈[2]
        좋A = (차A >= 3 and 기A >= 50
               and rA최 and 뼈최 and (rA최[2] - 뼈최[2]) >= 0)
        좋O = (기O > 100 and 차O >= -0.5)
        if 좋A:
            됨A.append((라, 차A, 기A))
        if 좋O:
            됨O.append((라, 차O, 기O))
        표 = ("  ⭐AND" if 좋A else "") + ("  ⭐OR" if 좋O else "")
        print(f"  {라:<26}{rA[2]:>8.1f}%{기A:>8.0f}%"
              f"{(rA최[2] if rA최 else 0):>8.1f}%   |"
              f"{rO[2]:>7.1f}%{기O:>7.0f}%{표}")

    print(f"\n     ⇒ **AND 로 된 것 {len(됨A)}개** · **OR 로 된 것 {len(됨O)}개**")
    if 됨A:
        print("       AND: " + " · ".join(f"{라}({차:+.1f}%p/{기:.0f}%)"
                                          for 라, 차, 기 in 됨A))
    if 됨O:
        print("       OR : " + " · ".join(f"{라}({차:+.1f}%p/{기:.0f}%)"
                                          for 라, 차, 기 in 됨O))

    print("\n" + "=" * 112)
    print("  읽는 법")
    print("    - 209차에서 「AND 로 되는 재료 0개」가 나왔는데")
    print("      그건 **이 아홉을 안 넣고** 나온 값이다. 여기서 채운다")
    print("    - AND 는 기회를 깎는다. 기회가 절반 밑이면 안 쓴다")
    print("=" * 112)
    return 0


if __name__ == "__main__":
    _p = os.path.join(_BASE, "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_215차_안써본재료아홉.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
