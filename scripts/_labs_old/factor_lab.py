#!/usr/bin/env python3
r"""
factor_lab.py — **팩터 포트폴리오: 형식을 바꿔서 다시** (2026-09-02 · 5차)

⚠️⚠️⚠️ **지금까지 우리가 시험한 건 전부 한 가지 형식이었다.**
```
우리가 한 것       며칠~몇 주 보유 · 5~10종목 · **매일** 신호
검증된 팩터 투자    **분기~연 단위 리밸런싱** · **30~100종목** · **순위** 기반
```
**형식이 애초에 안 맞았을 수 있다.** 모멘텀·밸류·퀄리티는 **분기 리밸런싱**에서 검증된 것이지
「오늘 살 종목」이 아니다. 그래서 형식을 바꿔 다시 잰다.

**재는 것 (분기마다 리밸런싱 · 30종목 동일가중)**
```
0 코스피 시총가중        ← 기준선. 인덱스 ETF를 산 것과 같다
1 전 종목 동일가중        ← 「모두 조금씩」
2 대형주 동일가중         ← 시총 상위 30
3 모멘텀 (12개월 수익률 상위 30)
4 모멘텀 (6개월)
5 저변동성 (최근 60일 변동성 낮은 30)
6 단기반전 (최근 1개월 많이 빠진 30)
7 고거래대금 (유동성 상위 30)
8 모멘텀 + 대형주
```
⚠️ **재무 팩터(밸류·퀄리티)는 아직 못 한다** — `dart-fin` 2015~2022가 09-03 새벽에 들어온다.
   지금은 **주가만으로 되는 팩터**를 먼저 잰다.

⚠️ **look-ahead 회피**: 리밸런싱 날의 **종가**로 사고, 그 이전 데이터만 순위에 쓴다.
⚠️ 왕복비용 0.26%를 **리밸런싱마다** 뺀다. 분기면 연 4회다.
⚠️ 학습(2010~2017) / 검증(2018~2026)을 갈라 낸다.
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
_종목수 = 30
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
    종가계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종가계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종가계[c]) - 1
    print(f"  거래일 {len(날):,} · 종목 {len(종가계):,}", flush=True)

    # 리밸런싱 날: 분기마다 (1·4·7·10월 첫 거래일)
    리밸 = []
    본 = None
    for i, d in enumerate(날):
        분 = (d[:4], (int(d[4:6]) - 1) // 3)
        if 분 != 본:
            리밸.append(i)
            본 = 분
    리밸 = [i for i in 리밸 if i >= 250]
    print(f"  리밸런싱 {len(리밸)}회 (분기)", flush=True)

    def 후보(i):
        """그날 살 수 있는 종목 (오염 제외 · 유동성 최소)"""
        out = []
        for code, v in 주가[날[i]].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(날[i])
            if k is None or k < 250:
                continue
            out.append((code, v, k))
        return out

    def 순위(이름, i):
        c = 후보(i)
        if len(c) < 50:
            return []
        if 이름 == "1 전 종목 동일가중":
            return [x[0] for x in c]
        if 이름 == "2 대형주 30":
            return [x[0] for x in sorted(c, key=lambda x: -x[1][1])[:_종목수]]
        if 이름 == "7 고거래대금 30":
            return [x[0] for x in sorted(c, key=lambda x: -x[1][2])[:_종목수]]
        점 = []
        for code, v, k in c:
            seq = 종가계[code]
            if 이름 == "3 모멘텀 12개월":
                if k < 250:
                    continue
                점.append((seq[k] / seq[k - 250] - 1, code))
            elif 이름 == "4 모멘텀 6개월":
                if k < 125:
                    continue
                점.append((seq[k] / seq[k - 125] - 1, code))
            elif 이름 == "5 저변동성":
                if k < 60:
                    continue
                r = [seq[j] / seq[j - 1] - 1 for j in range(k - 59, k + 1)]
                점.append((-st.pstdev(r), code))
            elif 이름 == "6 단기반전(1개월↓)":
                if k < 20:
                    continue
                점.append((-(seq[k] / seq[k - 20] - 1), code))
            elif 이름 == "8 모멘텀12 + 대형주":
                if k < 250 or v[1] < 1e12:
                    continue
                점.append((seq[k] / seq[k - 250] - 1, code))
        점.sort(reverse=True)
        return [c2 for _, c2 in 점[:_종목수]]

    전략 = ["1 전 종목 동일가중", "2 대형주 30", "3 모멘텀 12개월", "4 모멘텀 6개월",
            "5 저변동성", "6 단기반전(1개월↓)", "7 고거래대금 30", "8 모멘텀12 + 대형주"]

    def 값(code, i):
        """⚠️ 그날 거래가 없으면(거래정지·누락) **직전 가격**으로 평가한다.
           예전 판은 없으면 현금에 안 더해 **전액 손실**로 처리했다.
           모멘텀 상위 30은 급등주라 거래정지가 잦아 그 탓에 −93%가 나왔다."""
        v = 주가[날[i]].get(code)
        if v:
            return v[0]
        for j in range(i - 1, max(-1, i - 30), -1):
            v = 주가[날[j]].get(code)
            if v:
                return v[0]
        return None

    def 굴리기(이름, 시작i, 끝i):
        자산 = 1.0
        보유 = {}          # code -> 주수
        현금 = 1.0
        곡선 = [1.0]
        점들 = [x for x in 리밸 if 시작i <= x < 끝i]
        for n, i in enumerate(점들):
            s = 주가[날[i]]
            # 평가 후 전량 청산
            for code, 주수 in 보유.items():
                p2 = 값(code, i)
                if p2:
                    현금 += 주수 * p2 * (1 - _비용 / 2)
            보유 = {}
            자산 = 현금
            뽑 = 순위(이름, i)
            if 뽑:
                몫 = 자산 / len(뽑)
                for code in 뽑:
                    v = s.get(code)
                    if not v:
                        continue
                    보유[code] = 몫 * (1 - _비용 / 2) / v[0]
                    현금 -= 몫
            곡선.append(자산)
        # 마지막 청산
        마지막 = min(끝i, len(날)) - 1
        for code, 주수 in 보유.items():
            p2 = 값(code, 마지막)
            if p2:
                현금 += 주수 * p2 * (1 - _비용 / 2)
        곡선.append(현금)
        최고, 낙 = 1.0, 0.0
        for x in 곡선:
            최고 = max(최고, x)
            낙 = min(낙, x / 최고 - 1)
        return 현금, 낙 * 100, len(점들)

    경계i = next(i for i, d in enumerate(날) if d >= _경계)
    구간들 = [("학습 2010~2017", 250, 경계i),
              ("검증 2018~2026", 경계i, len(날)),
              ("전체 2010~2026", 250, len(날))]

    print(f"\n  분기 리밸런싱 · {_종목수}종목 동일가중 · 왕복비용 {_비용*100:.2f}%\n")
    for 이름, a, b in 구간들:
        있 = [d for d in 날[a:b] if 지수.get(d)]
        배 = 지수[있[-1]]["KOSPI"] / 지수[있[0]]["KOSPI"]
        년 = (b - a) / 245
        지연 = (배 ** (1 / 년) - 1) * 100
        print(f"  ══════ {이름} ══════   (코스피 배수 {배:.3f} · 연 {지연:+.1f}%)")
        print(f"    {'전략':<24}{'배수':>8}{'연환산':>9}{'낙폭':>9}{'초과':>9}")
        줄 = []
        for s in 전략:
            자, 낙, n = 굴리기(s, a, b)
            연 = (자 ** (1 / 년) - 1) * 100 if 자 > 0 else -100
            줄.append((연 - 지연, s, 자, 연, 낙))
        for 초, s, 자, 연, 낙 in sorted(줄, reverse=True):
            표 = "⭐" if 초 > 0 else "  "
            print(f"    {s:<24}{자:>8.3f}{연:>8.1f}%{낙:>8.1f}%{초:>+8.1f}%{표}")
        print()
    print("  읽는 법")
    print("    - '초과'가 학습·검증 둘 다 양수여야 진짜다")
    print("    - 코스피(시총가중)를 기준으로 잰다. 인덱스 ETF를 산 것과 같다")
    print("    - 재무 팩터(밸류·퀄리티)는 dart-fin 2015~2022가 들어온 뒤(09-03) 추가한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
