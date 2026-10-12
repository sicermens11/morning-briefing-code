#!/usr/bin/env python3
r"""
december_lab.py — **12월에 많이 빠진 종목이 1월에 되오르나** (2026-10-12 · 사용자 10/8 「다음에 잴 10가지」 중 12월 양도세)

한국은 대주주 양도세 기준일(12월 말) 앞에 큰손이 팔고 1월에 되사는 일이 있다는 말이 있다 — 숫자로 본다
· 해마다(2010~2025) 12월 수익률(11월 마지막 거래일 종가 → 12월 마지막 거래일 종가) 아래 10%·20% 종목
· 12월 마지막 거래일 종가에 사서 1월 마지막 거래일 종가에 판다 · 비용 0.26% · 시총 300억↑
· 견줌: 같은 해 대상 전체 1월 수익 · 1월 말까지 사라진 종목은 마지막 값의 절반
쓰는 법: python scripts\december_lab.py  → data/_labs/<날>_12월양도세.txt
"""
import datetime as dt
import io
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_밖 = io.open(os.path.join(O._DATA, "_labs", f"{dt.date.today():%Y-%m-%d}_12월양도세.txt"), "w", encoding="utf-8")


def 찍기(s=""):
    print(s, flush=True)
    _밖.write(s + "\n")


def main():
    주가 = O.수정주가(("시총",))
    날 = sorted(주가)

    def 달끝(y, m):
        ks = [d for d in 날 if d[:6] == f"{y}{m:02d}"]
        return ks[-1] if ks else None
    찍기("=" * 100)
    찍기("  12월에 많이 빠진 종목 → 1월 수익 (12월 마지막 날 종가 매수 · 1월 마지막 날 종가 매도 · 비용 0.26% · 시총 300억↑)")
    찍기("=" * 100)
    찍기(f"  {'해':<8}{'대상':>6}{'전체 1월':>10}{'12월 아래10% 1월':>18}{'아래20% 1월':>14}{'위10%(많이 오른) 1월':>22}")
    차10, 차20, 차위 = [], [], []
    for y in range(2010, 2026):
        n11, d12, j1 = 달끝(y, 11), 달끝(y, 12), 달끝(y + 1, 1)
        if not (n11 and d12 and j1):
            continue
        사이 = [d for d in 날 if d12 < d <= j1]
        표 = []
        for c, v in 주가[d12].items():
            시총 = v[1] if len(v) > 1 else None
            a = 주가[n11].get(c)
            if not 시총 or 시총 < 300e8 or not a or not a[0] or not v[0]:
                continue
            e = 주가[j1].get(c)
            if e and e[0]:
                r1 = e[0] / v[0] - 1
            else:
                마 = next((주가[d][c][0] for d in reversed(사이) if 주가[d].get(c) and 주가[d][c][0]), v[0])
                r1 = 마 * 0.5 / v[0] - 1
            표.append((v[0] / a[0] - 1, r1 * 100 - 0.26))
        if len(표) < 100:
            continue
        표.sort()
        n = len(표)
        전 = st.mean(z[1] for z in 표)
        a10 = st.mean(z[1] for z in 표[: n // 10])
        a20 = st.mean(z[1] for z in 표[: n // 5])
        w10 = st.mean(z[1] for z in 표[-(n // 10):])
        차10.append(a10 - 전)
        차20.append(a20 - 전)
        차위.append(w10 - 전)
        찍기(f"  {y}→{y + 1 - 2000:02d}{n:>6}{전:>+9.2f}%{a10:>+17.2f}%{a20:>+13.2f}%{w10:>+21.2f}%")
    찍기(f"\n  전체보다 나은 해: 아래10% {sum(1 for z in 차10 if z > 0)}/{len(차10)} · 평균 차 {st.mean(차10):+.2f}%p"
         f"  |  아래20% {sum(1 for z in 차20 if z > 0)}/{len(차20)} · {st.mean(차20):+.2f}%p"
         f"  |  위10% {sum(1 for z in 차위 if z > 0)}/{len(차위)} · {st.mean(차위):+.2f}%p")
    찍기("  ⚠️ 해마다 한 번뿐이라 표본이 16해 · 평균 수익이지 계좌 시뮬이 아니다(돈으로 보려면 지금 규칙과 합쳐 다시)")
    찍기("  [대조] 12월 끝")


if __name__ == "__main__":
    main()
