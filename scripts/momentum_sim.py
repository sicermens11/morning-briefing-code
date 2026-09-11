#!/usr/bin/env python3
r"""
momentum_sim.py — **최종 판정: 기간을 갈라도 이기나** (2026-09-02 · 4차)

⚠️⚠️⚠️ **여기까지 온 경위**
```
1차  기존 규칙(갭①④)이 작동 안 함 · look-ahead 오류로 성적 대부분이 허수
2차  「전부 음수」는 잣대(시총가중) 문제였음 · 동일가중으로 보니 **52주 신고가**만 살아남음
3차  모멘텀은 **대형주에서만** 작동 · **손절은 독** · **길게 들어야 함**
4차  ← **여기.** 전 기간 성적은 좋았다(배수 2.988 vs 코스피 2.554).
     그런데 **기간을 갈라도 이기는가?**
```
⚠️ **전 기간 성적만 보면 과최적화를 못 잡는다.** 학습에서 고른 규칙이 검증에서도 이겨야 한다.

**규칙**: 52주 신고가 + 시총 1조↑ · 매수 D+1 종가 · **D+20 보유** · **손절 없음** · 10종목 분산
**비교**: 같은 구간 코스피 그냥 보유.

⚠️ 체결 100% 가정 · 왕복비용 0.26%(세금 0.18 + 수수료 0.03 + 슬리피지 0.05⚠️가정)
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
# ⚠️ 2026-09-02: 표본이 2.6년 → **16.7년**이 됐다(2010-01~).
#    학습/검증 경계를 **절반 지점(2018-01)**으로 옮긴다.
_경계 = "20180101"


def _주가full():
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


def 굴리기(날, 주가, 신호, 시작, 끝, 보유일, 최대):
    """[시작, 끝) 구간에서 매수한다. 보유는 끝을 넘어가도 청산까지 간다.

    ⚠️⚠️ **현금과 보유를 나눠 회계한다** (2026-09-02 버그 수정).
       예전 판은 보유 중인 돈을 잔고에서 안 뺐다. 그래서 10종목을 들고도
       매번 「잔고÷10」을 새 몫으로 써 **자본의 100%를 훨씬 넘게 투입**했다(레버리지).
       그 탓에 낙폭이 −92.9%까지 나왔다. **현금이 없으면 못 산다**가 맞다.
    """
    현금 = 1.0
    보유 = []          # [(청산일idx, 코드, 매수가, 주수)]
    곡선 = [1.0]
    이긴 = 진 = 0
    for i in range(시작, len(날)):
        s1 = 주가[날[i]]
        # ── 청산 ──
        남 = []
        for (끝i, code, 매수가, 주수) in 보유:
            if i >= 끝i:
                v = s1.get(code)
                팔 = v[0] if v else 매수가
                현금 += 주수 * 팔 * (1 - _비용 / 2)
                수익 = (팔 / 매수가 - 1) - _비용
                이긴 += 1 if 수익 > 0 else 0
                진 += 1 if 수익 <= 0 else 0
            else:
                남.append((끝i, code, 매수가, 주수))
        보유 = 남
        # ── 총자산 (현금 + 보유 평가액) ──
        평가 = 0.0
        for (_, code, 매수가, 주수) in 보유:
            v = s1.get(code)
            평가 += 주수 * (v[0] if v else 매수가)
        총자산 = 현금 + 평가
        # ── 매수 ──
        if i < 끝 and i + 1 < len(날) and 총자산 > 0:
            자리 = 최대 - len(보유)
            몫 = 총자산 / 최대
            후보 = sorted(신호.get(날[i]) or [], reverse=True)
            산것 = 0
            for _, code in 후보:
                if 산것 >= 자리 or 현금 < 몫 * 0.5:
                    break
                v2 = 주가[날[i + 1]].get(code)
                if not v2 or v2[0] <= 0:
                    continue
                쓸 = min(몫, 현금)          # ⚠️ **현금이 없으면 못 산다**
                if 쓸 <= 0:
                    break
                주수 = 쓸 * (1 - _비용 / 2) / v2[0]
                현금 -= 쓸
                보유.append((i + 1 + 보유일, code, v2[0], 주수))
                산것 += 1
        곡선.append(max(총자산, 0.0))
        if i >= 끝 and not 보유:
            break
    최고, 낙 = 곡선[0], 0.0
    for x in 곡선:
        최고 = max(최고, x)
        낙 = min(낙, x / 최고 - 1) if 최고 > 0 else 낙
    return 곡선[-1], 이긴, 진, 낙 * 100


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = _주가full()
    날 = sorted(주가)
    지수, 기본 = O._지수(), O._기본()
    종가계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종가계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종가계[c]) - 1

    # 신호: 52주 신고가 + 시총 1조↑ (거래대금 큰 것부터 담는다)
    신호 = {}
    for i, d1 in enumerate(날):
        if i < 250:
            continue
        묶 = []
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < 1e12 or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (str(bb.get("상장일") or "") > "20240101")
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            if c1 >= max(종가계[code][k - 250:k + 1]) * 0.999:
                묶.append((대금, code))
        신호[d1] = 묶
    print(f"  신호 있는 날 {sum(1 for v in 신호.values() if v)}일 "
          f"· 총 {sum(len(v) for v in 신호.values()):,}건", flush=True)

    경계i = next(i for i, d in enumerate(날) if d >= _경계)
    def i번(d):
        return next((i for i, x in enumerate(날) if x >= d), len(날))
    구간들 = [("학습 2010~2017", 250, 경계i),
              ("검증 2018~2026", 경계i, len(날)),
              ("전체 2010~2026", 250, len(날)),
              ("── 국면별 ──", None, None),
              ("2020 코로나", i번("20200101"), i번("20210101")),
              ("2022 약세장", i번("20220101"), i번("20230101")),
              ("2024~26 강세장", i번("20240101"), len(날))]

    print("\n  규칙: 52주 신고가 + 시총 1조↑ · 매수 D+1 종가 · 손절 없음\n")
    for 보유일, 최대 in ((20, 10), (20, 5), (10, 10), (60, 10)):
        print(f"  ── D+{보유일} 보유 · {최대}종목 ──")
        print(f"    {'구간':<24}{'배수':>8}{'연환산':>9}{'거래':>6}{'승률':>6}"
              f"{'낙폭':>8}{'코스피':>9}{'초과':>9}")
        for 이름, a, b in 구간들:
            if a is None:
                print(f"    {이름}")
                continue
            잔고, 이긴, 진, 낙 = 굴리기(날, 주가, 신호, a, b, 보유일, 최대)
            n = b - a
            년 = n / 245
            연 = (잔고 ** (1 / 년) - 1) * 100 if 잔고 > 0 else -100
            있 = [d for d in 날[a:b] if 지수.get(d)]
            배 = (지수[있[-1]]["KOSPI"] / 지수[있[0]]["KOSPI"]) if len(있) > 1 else 1
            지연 = (배 ** (1 / 년) - 1) * 100
            총 = 이긴 + 진
            print(f"    {이름:<24}{잔고:>8.3f}{연:>8.1f}%{총:>6}"
                  f"{이긴 / max(1, 총) * 100:>5.0f}%{낙:>7.1f}%"
                  f"{배:>9.3f}{연 - 지연:>+8.1f}%")
        print()
    print("  읽는 법")
    print("    - '초과'가 학습·검증 **둘 다 양수**여야 진짜다")
    print("    - 학습만 양수면 과최적화다")
    print("    - 낙폭이 -30%를 넘으면 사람이 못 버틴다")
    print("    - 체결 100% 가정 · 슬리피지 0.05%는 가정값이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
