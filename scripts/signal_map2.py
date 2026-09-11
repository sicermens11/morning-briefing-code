#!/usr/bin/env python3
r"""
signal_map2.py — **안 써본 자료를 전부 지도에** (2026-09-07 신설)

## 왜
```
사용자 지시: 「꼭 공시가 아니라 우리가 테스트 안 해본 정보로도 테스트해보는 게
              중요해. 테스트는 있는 거 다 해봐」

9/4 필드 감사: 927개 중 사용 311개(34%) · **미사용 616개(66%)**
그런데 실제로 쓸 수 있는 것만 추리면 훨씬 적다 — 확인한 결과:
  X flow-daily 외국인지분율   값이 전부 '-' (실제로 없다)
  X naver-quarter            분기 6개(1.5년)뿐 — 10년 백테스트 불가
  X index-daily 시가          종가·등락률만
  O 업종 지수 등락률           4,104일 · 71개
  O 공시 **종류별**           챙길공시 vs 그밖의공시
  O 계약 공시                금액 · 매출대비% (33개월)
  O 컨센서스 리포트            81개월
  O 임원 지분 증감            2,650종목
  O 대주주 지분율 변화         2,650종목
```
⚠️ **이건 지도다. 규칙이 아니다.** 여기서 좋아 보여도 자본 시뮬을 통과해야 한다
⚠️ **표본 수를 반드시 찍는다.** 2026-09-07 에 갭 신호가 조회 버그로 표본 0이 되어
   표에서 통째로 사라졌는데, 표본을 안 찍어서 한참 못 알아챘다

## 구분
```
중형 3천억~1조 · 중소형 2~3천억 · 소형 500억~2천억
(대형·초대형은 오늘 자본 시뮬에서 기각됐다. 표본도 얇다)
```

쓰는 법:
    python scripts\signal_map2.py
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

    # ── 공시 **종류별** ──
    챙길, 그밖 = {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = d.get("기준일")
        if not d8:
            continue
        for k, 통 in (("챙길공시", 챙길), ("그밖의공시", 그밖)):
            났 = set()
            for x in (d.get(k) or []):
                c = x.get("종목코드")
                if c:
                    났.add(str(c).zfill(6))
            통[d8] = 났

    # ── 계약 공시 (금액 · 매출대비%) ──
    print("  계약 공시 읽는 중...", flush=True)
    계약 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "contract", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        for _, x in (d.get("건") or {}).items():
            c, 날짜2 = x.get("코드"), str(x.get("날짜") or "")
            if not c or len(날짜2) != 8:
                continue
            try:
                p = float(x.get("매출대비pct") or 0)
            except (TypeError, ValueError):
                p = 0.0
            계약.setdefault(날짜2, {})[str(c).zfill(6)] = p

    # ── 컨센서스 리포트 ──
    print("  컨센서스 읽는 중...", flush=True)
    리포트 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "consensus", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        for x in (d.get("리포트") or []):
            c, 날짜2 = x.get("코드"), str(x.get("날짜") or "").replace("-", "")
            if c and len(날짜2) == 8:
                리포트.setdefault(날짜2, set()).add(str(c).zfill(6))

    # ── 임원 지분 증감 · 대주주 지분율 변화 ──
    print("  지분 이력 읽는 중...", flush=True)
    임원, 대주주 = {}, {}
    for 폴, 통, 키 in (("dart-exec", 임원, "증감"),
                       ("dart-major", 대주주, "지분율")):
        for f in sorted(glob.glob(os.path.join(O._DATA, 폴, "*.json"))):
            try:
                d = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                continue
            c = str(d.get("종목") or "").zfill(6)
            for x in (d.get("이력") or []):
                날짜2 = str(x.get("접수일") or "").replace("-", "")
                if len(날짜2) != 8:
                    continue
                if 폴 == "dart-exec":
                    try:
                        v = float(str(x.get("증감") or 0).replace(",", ""))
                    except (TypeError, ValueError):
                        v = 0.0
                else:
                    try:
                        v = (float(str(x.get("지분율") or 0)) -
                             float(str(x.get("직전지분율") or 0)))
                    except (TypeError, ValueError):
                        v = 0.0
                통.setdefault(날짜2, {})[c] = v

    # ── 업종 지수 (그날 그 업종이 올랐나) ──
    print("  업종 지수 읽는 중...", flush=True)
    업종지수 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = d.get("기준일")
        하 = {}
        for k, v in (d.get("지수") or {}).items():
            try:
                r = float(v.get("등락률"))
            except (TypeError, ValueError):
                continue
            하[k] = r
        if d8 and 하:
            업종지수[d8] = 하
    # 종목 -> 업종명
    업맵 = {}
    _ip = os.path.join(O._DATA, "industry.json")
    if os.path.exists(_ip):
        try:
            for c, v in json.load(io.open(_ip, encoding="utf-8-sig")).items():
                n = (v or {}).get("업종명")
                if n:
                    업맵[c] = n
        except Exception:  # noqa: BLE001
            pass

    # ⚠️⚠️ **안전장치** (2026-09-07). 자료 읽기에서 (거래일 목록)을
    #    반복 변수로 덮어써서 훑기가 통째로 안 돈 적이 있다.
    #    한글 짧은 이름은 충돌하기 쉽다 — 오늘만 네 번째다
    assert isinstance(날, list) and len(날) > 1000, (
        "거래일 목록이 망가졌다 — 어디선가  을 덮어썼다: " + repr(날)[:80])
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
            if code in (챙길.get(d1) or set()):
                담기(라, "⑦ **챙길공시**", rs)
            if code in (그밖.get(d1) or set()):
                담기(라, "⑧ 그밖의 공시", rs)
            계 = (계약.get(d1) or {}).get(code)
            if 계 is not None:
                담기(라, "⑨ 계약 공시", rs)
                if 계 >= 10:
                    담기(라, "⑩ 계약 **매출 10%↑**", rs)
            if code in (리포트.get(d1) or set()):
                담기(라, "⑪ 증권사 리포트", rs)
            임 = (임원.get(d1) or {}).get(code)
            if 임 is not None:
                담기(라, "⑫ 임원 지분 변동", rs)
                if 임 > 0:
                    담기(라, "⑬ 임원 지분 **증가**", rs)
                elif 임 < 0:
                    담기(라, "⑭ 임원 지분 감소", rs)
            대 = (대주주.get(d1) or {}).get(code)
            if 대 is not None and abs(대) > 0.01:
                담기(라, "⑮ 대주주 지분율 변동", rs)
                if 대 > 0:
                    담기(라, "⑯ 대주주 지분 **증가**", rs)
            업 = 업맵.get(code)
            if 업:
                오늘업 = 업종지수.get(d1) or {}
                후보들 = [v for k, v in 오늘업.items() if 업[:2] in k]
                if 후보들:
                    z = st.mean(후보들)
                    if z <= -1.0:
                        담기(라, "⑰ 업종 지수 -1%↓", rs)
                    elif z >= 1.0:
                        담기(라, "⑱ 업종 지수 +1%↑", rs)

    print("\n" + "=" * 96)
    print("  구분마다 통하는 신호가 다른가 — **지도**")
    print("=" * 96)
    print("  ⚠️ 이건 규칙이 아니다. 「나눌 값어치가 있나」만 본다\n")

    차례 = ("아무 날이나 (기준선)", "① 20일 -10%↓", "② 볼린저 -1.0σ↓",
            "③ 갭 -2%↓", "④ 외국인 순매수 상위20%", "⑤ 외국인 순매도 하위20%",
            "⑥ 그날 공시 있음", "⑦ **챙길공시**", "⑧ 그밖의 공시",
            "⑨ 계약 공시", "⑩ 계약 **매출 10%↑**", "⑪ 증권사 리포트",
            "⑫ 임원 지분 변동", "⑬ 임원 지분 **증가**", "⑭ 임원 지분 감소",
            "⑮ 대주주 지분율 변동", "⑯ 대주주 지분 **증가**",
            "⑰ 업종 지수 -1%↓", "⑱ 업종 지수 +1%↑")
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
            # ⚠️ **표본이 적어도 줄은 찍는다.** 2026-09-07 에 갭 신호가 조회
            #    버그로 표본 0이 되어 표에서 통째로 사라졌는데, 안 찍으니
            #    한참 못 알아챘다. **없으면 없다고 보여야 한다**
            if not 칸 or len(칸[20]) < 30:
                n0 = len(칸[20]) if 칸 else 0
                print("  " + 신.ljust(26) + format(n0, ",").rjust(9)
                      + "   ⚠️ 표본 부족 (30건 미만)")
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
