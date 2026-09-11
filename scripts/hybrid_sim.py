#!/usr/bin/env python3
r"""
hybrid_sim.py — **절대수익 + 「인덱스에 얹기」로 다시 본다** (2026-09-02 · 8차)

⚠️⚠️⚠️ **사용자 지적에서 나왔다.**
   *"개별 종목이 코스피에서 지더라도 어떤 조건으로 실제 상승했다면 그걸로 매수 실현할 수
   있는 거 아니야? 코스피가 1.45% 상승했는데 개별종목이 1% 상승해도 실제 수익을 실현할
   수 있는 거잖아!"*
   → **맞다. 내가 잣대를 하나만 봤다.**
```
내가 잰 것   초과수익(코스피 대비)  →  「인덱스를 샀으면 더 벌었나」
안 잰 것     절대수익(현금 대비)    →  「실제로 돈을 벌었나」
```

⚠️⚠️ **그리고 여기서 진짜 문제가 드러난다 — 비교가 애초에 불공정했다.**
```
인덱스는        **항상 100% 투자**돼 있다
개별종목 전략은   신호가 있을 때만 산다 (실측 투입일 **60%**, 40%는 현금)
```
→ 현금 40%를 놀리면서 인덱스와 비교하면 당연히 진다. **현금이 문제지 신호가 문제가 아닐 수 있다.**

**그래서 세 가지를 나란히 낸다**
```
A 신호만 (나머지 현금)      지금까지 잰 방식. 절대수익도 같이 낸다
B **신호 + 나머지는 인덱스**  ← **이게 공정한 비교다.** 놀리는 돈을 인덱스에 둔다
C 항상 인덱스              기준선
```
⚠️ B가 C보다 나으면 **「인덱스에 얹어서 이득」**이라는 뜻이다. 그게 우리가 찾던 것이다.

⚠️ 매수 D+1 종가(look-ahead 회피) · 오염 제외 · 왕복비용 0.26% · 16.7년.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.0026
_경계 = "20180101"


def _주가():
    표 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, float(v.get("시총") or 0), float(v.get("거래대금") or 0))
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    공시 = O._공시(날)
    종가계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종가계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종가계[c]) - 1

    # 신호 미리 계산: (날 -> [(우선순위, 코드)])
    신호 = {"신고가+대형주": {}, "호재+대형주": {}, "신고가+대형주+호재": {}}
    for i, d1 in enumerate(날):
        if i < 250:
            continue
        ds = 공시.get(d1) or {}
        a, b, c3 = [], [], []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < 1e12 or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            신고 = c1 >= max(종가계[code][k - 250:k + 1]) * 0.999
            호재 = "호재" in (ds.get(code) or {}).get("성격", set())
            if 신고:
                a.append((대금, code))
            if 호재:
                b.append((대금, code))
            if 신고 and 호재:
                c3.append((대금, code))
        신호["신고가+대형주"][d1] = a
        신호["호재+대형주"][d1] = b
        신호["신고가+대형주+호재"][d1] = c3
    for k2, v2 in 신호.items():
        print(f"  {k2:<20} 신호 있는 날 {sum(1 for x in v2.values() if x):,}일 "
              f"· 총 {sum(len(x) for x in v2.values()):,}건", flush=True)

    def 굴리기(신호표, 시작, 끝, 보유일, 최대, 놀때인덱스):
        """놀때인덱스=True 면 남는 현금을 코스피 지수에 넣는다."""
        현금 = 1.0
        보유 = []          # (청산idx, 코드, 매수가, 주수)
        지수몫 = 0.0        # 지수에 넣은 '단위' (지수값 × 지수몫 = 평가액)
        곡선 = [1.0]
        이긴 = 진 = 0
        투입일 = 0
        앞ix = None          # ⚠️ 지수가 하루 빠진 날(2016-10-10)이 있다. 그날 자산이
                             #    0으로 찍혀 낙폭 −100%가 나왔다. 직전 값을 이어 쓴다.
        for i in range(시작, len(날)):
            s1 = 주가[날[i]]
            ix = (지수.get(날[i]) or {}).get("KOSPI") or 앞ix
            if ix:
                앞ix = ix
            # 청산
            남 = []
            for (끝i, code, 매수가, 주수) in 보유:
                if i >= 끝i:
                    v = s1.get(code)
                    팔 = v[0] if v else 매수가
                    현금 += 주수 * 팔 * (1 - _비용 / 2)
                    수 = (팔 / 매수가 - 1) - _비용
                    이긴 += 1 if 수 > 0 else 0
                    진 += 1 if 수 <= 0 else 0
                else:
                    남.append((끝i, code, 매수가, 주수))
            보유 = 남
            평가 = sum(주수 * ((s1.get(code) or (매수가,))[0])
                       for (_, code, 매수가, 주수) in 보유)
            지수평 = 지수몫 * ix if (놀때인덱스 and ix) else 0.0
            총 = 현금 + 평가 + 지수평
            if 보유 and i < 끝:
                투입일 += 1
            # 매수
            if i < 끝 and i + 1 < len(날) and 총 > 0:
                자리수 = 최대 - len(보유)
                뽑 = sorted(신호표.get(날[i]) or [], reverse=True)[:max(0, 자리수)]
                if 뽑:
                    몫 = 총 / 최대
                    for _, code in 뽑:
                        v2 = 주가[날[i + 1]].get(code)
                        if not v2 or v2[0] <= 0:
                            continue
                        필요 = 몫
                        # ⚠️ 현금이 모자라면 **지수를 판다**
                        if 현금 < 필요 and 놀때인덱스 and ix and 지수몫 > 0:
                            팔몫 = min(지수몫, (필요 - 현금) / ix)
                            현금 += 팔몫 * ix * (1 - _비용 / 2)
                            지수몫 -= 팔몫
                        쓸 = min(필요, 현금)
                        if 쓸 <= 0:
                            break
                        보유.append((i + 1 + 보유일, code,
                                     v2[0], 쓸 * (1 - _비용 / 2) / v2[0]))
                        현금 -= 쓸
            # 남는 현금을 지수에 넣는다
            if 놀때인덱스 and ix and 현금 > 1e-9:
                지수몫 += 현금 * (1 - _비용 / 2) / ix
                현금 = 0.0
            곡선.append(max(총, 0.0))
            if i >= 끝 and not 보유:
                break
        # 최종 청산
        마 = min(끝, len(날)) - 1
        s1 = 주가[날[마]]
        for (_, code, 매수가, 주수) in 보유:
            v = s1.get(code)
            현금 += 주수 * ((v[0] if v else 매수가)) * (1 - _비용 / 2)
        ix = (지수.get(날[마]) or {}).get("KOSPI") or 앞ix
        if 놀때인덱스 and ix:
            현금 += 지수몫 * ix * (1 - _비용 / 2)
        최고, 낙 = 1.0, 0.0
        for x in 곡선:
            최고 = max(최고, x)
            낙 = min(낙, x / 최고 - 1)
        총거래 = 이긴 + 진
        return 현금, 낙 * 100, 총거래, (이긴 / 총거래 * 100 if 총거래 else 0), \
            투입일 / max(1, 끝 - 시작) * 100

    경계i = next(i for i, d in enumerate(날) if d >= _경계)
    구간들 = [("학습 2010~2017", 250, 경계i),
              ("검증 2018~2026", 경계i, len(날)),
              ("전체 2010~2026", 250, len(날))]

    print(f"\n  D+20 보유 · 10종목 · 손절 없음 · 왕복비용 {_비용*100:.2f}%\n")
    for 이름, a, b in 구간들:
        있 = [d for d in 날[a:b] if 지수.get(d)]
        배 = 지수[있[-1]]["KOSPI"] / 지수[있[0]]["KOSPI"]
        년 = (b - a) / 245
        지연 = (배 ** (1 / 년) - 1) * 100
        print(f"  ══════ {이름} ══════")
        print(f"    {'전략':<28}{'배수':>8}{'연환산':>9}{'낙폭':>8}"
              f"{'거래':>6}{'승률':>6}{'투입일':>7}{'코스피대비':>10}")
        print(f"    {'C 항상 인덱스(기준선)':<28}{배:>8.3f}{지연:>8.1f}%"
              f"{'':>8}{'':>6}{'':>6}{'100%':>7}{'0.0%':>10}")
        for 신호이름 in ("신고가+대형주", "호재+대형주", "신고가+대형주+호재"):
            for 라벨, 놀 in (("A 신호만(나머지 현금)", False),
                             ("B 신호+나머지 인덱스", True)):
                자, 낙, 거, 승, 투 = 굴리기(신호[신호이름], a, b, 20, 10, 놀)
                연 = (자 ** (1 / 년) - 1) * 100 if 자 > 0 else -100
                표 = "⭐" if 연 > 지연 else "  "
                print(f"    {(라벨 + ' / ' + 신호이름)[:26]:<28}{자:>8.3f}{연:>8.1f}%"
                      f"{낙:>7.1f}%{거:>6}{승:>5.0f}%{투:>6.0f}%{연-지연:>+9.1f}%{표}")
        print()
    print("  읽는 법")
    print("    - A는 '신호 없으면 현금'. 절대수익은 나지만 놀리는 돈이 많다")
    print("    - **B가 공정한 비교다.** 놀리는 돈을 인덱스에 두고 신호 때만 갈아탄다")
    print("    - B가 C(항상 인덱스)보다 나으면 '인덱스에 얹어서 이득'이라는 뜻이다")
    print("    - ⚠️ 호재 신호는 공시가 2010·2011·2024~2026만 있어 아직 불완전하다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
