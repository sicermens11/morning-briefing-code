#!/usr/bin/env python3
r"""
bench_lead_check.py — **해외 대표 4곳이 다음 날 한국 섹터를 미리 알려 주나** (2026-10-08)

사용자 10/8: 「왜 이 4종목이 각 섹터를 대표하게 됐는지 모르겠네..」
8/4 에 「비미국 공급망을 선행 신호로」 넣었지만 **정말 앞서나는 한 번도 안 쟀다.**
⚠️ TSMC·CATL·중국선박은 한국과 거의 같은 시간대에 장이 열리고 닫힌다 — 그날 움직임은 같은 날 한국에 이미 들어간다.
   「다음 날」 신호가 될 수 있는 건 한국 장이 닫힌 뒤 움직이는 라인메탈(유럽)뿐일 것이다 — 그걸 숫자로 본다.

잰다 (야후 일봉 · 최근 3년):
  ① 같은 날: 해외 D일 등락 vs 한국 섹터 ETF D일 등락 (함께 움직이나)
  ② 다음 날 아침: 해외 D일 등락 vs 한국 ETF D+1 시가 갭 (08:55 에 쓸 수 있나 · 이게 「선행」)
  ③ 다음 날 하루: 해외 D일 등락 vs 한국 ETF D+1 종가 등락
  ※ 상관계수 · 해외가 ±2% 넘게 움직인 날만 따로 「같은 방향 비율」
"""
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")
짝 = [("TSMC", "2330.TW", "반도체 KODEX", "091160.KS"),
     ("CATL", "300750.SZ", "2차전지 TIGER", "305540.KS"),
     ("라인메탈", "RHM.DE", "방산 PLUS K방산", "449450.KS"),
     ("중국선박", "600150.SS", "조선 TIGER 조선TOP10", "494670.KS")]
# 견줌: 한국 장이 닫힌 **뒤에** 움직이는 미국 쪽 (BENCH_SET=US)
if os.environ.get("BENCH_SET") == "US":
    짝 = [("필라델피아반도체 SOXX", "SOXX", "반도체 KODEX", "091160.KS"),
         ("마이크론 MU", "MU", "반도체 KODEX", "091160.KS"),
         ("엔비디아 NVDA", "NVDA", "반도체 KODEX", "091160.KS"),
         ("테슬라 TSLA", "TSLA", "2차전지 TIGER", "305540.KS"),
         ("리튬 ETF LIT", "LIT", "2차전지 TIGER", "305540.KS"),
         ("미국 방산 ITA", "ITA", "방산 PLUS K방산", "449450.KS"),
         ("미국 산업재 XLI", "XLI", "조선 TIGER 조선TOP10", "494670.KS")]
# 바탕: 미국 시장 전체(S&P500 SPY) — 섹터 회사가 「시장 전체」 보다 더 알려 주나 (BENCH_SET=SPY)
if os.environ.get("BENCH_SET") == "SPY":
    짝 = [("S&P500 SPY", "SPY", 국, s2) for 국, s2 in (("반도체 KODEX", "091160.KS"), ("2차전지 TIGER", "305540.KS"),
                                                     ("방산 PLUS K방산", "449450.KS"), ("조선 TIGER 조선TOP10", "494670.KS"))]


def 일봉(sym):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=3y&interval=1d"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    out = {}
    for t, o, c in zip(r["timestamp"], q["open"], q["close"]):
        if o and c:
            out[datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")] = (o, c)
    return out


def 상관(xs, ys):
    n = len(xs)
    if n < 30:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else None


def main():
    밖 = io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "_labs",
                             "2026-10-08_해외대표4_선행확인" + {"US": "_미국견줌", "SPY": "_시장전체바탕"}.get(os.environ.get("BENCH_SET") or "", "") + ".txt"),
             "w", encoding="utf-8")

    def 찍기(s=""):
        print(s, flush=True)
        밖.write(s + "\n")
    찍기("해외 대표 4곳 → 한국 섹터 ETF · 야후 일봉 최근 3년 · 상관계수(−1~+1 · 0이면 관계 없음)")
    찍기(f"{'해외':<8}{'한국 ETF':<22}{'①같은 날':>9}{'②다음날 갭':>11}{'③다음날 하루':>12}  ±2% 넘은 날: 다음날 갭 같은 방향")
    for 이름, s1, 국, s2 in 짝:
        try:
            a, b = 일봉(s1), 일봉(s2)
        except Exception as e:  # noqa: BLE001
            찍기(f"{이름:<8}{국:<22} 못 받음 {type(e).__name__}")
            continue
        ad, bd = sorted(a), sorted(b)
        a등 = {d: (a[d][1] / a[ad[i - 1]][1] - 1) * 100 for i, d in enumerate(ad) if i}
        b등 = {d: (b[d][1] / b[bd[i - 1]][1] - 1) * 100 for i, d in enumerate(bd) if i}
        b갭 = {d: (b[d][0] / b[bd[i - 1]][1] - 1) * 100 for i, d in enumerate(bd) if i}
        같x, 같y, 갭x, 갭y, 하x, 하y = [], [], [], [], [], []
        for i, d in enumerate(bd[1:], 1):
            if d in a등 and d in b등:
                같x.append(a등[d]); 같y.append(b등[d])
            # 다음 날: 한국 d 의 직전에 끝난 해외 마지막 거래일 (같은 날짜는 빼야 「다음 날」 이다 — 해외 d-1 이전)
            앞 = [x for x in ad if x < d]
            if not 앞 or 앞[-1] not in a등:
                continue
            x = a등[앞[-1]]
            갭x.append(x); 갭y.append(b갭[d]); 하x.append(x); 하y.append(b등[d])
        큰 = [(x, y) for x, y in zip(갭x, 갭y) if abs(x) >= 2]
        같방 = sum(1 for x, y in 큰 if x * y > 0) / len(큰) * 100 if 큰 else None
        f = lambda v: f"{v:+.2f}" if v is not None else "  · "
        찍기(f"{이름:<8}{국:<22}{f(상관(같x, 같y)):>9}{f(상관(갭x, 갭y)):>11}{f(상관(하x, 하y)):>12}  "
             f"{len(큰)}일 중 {같방:.0f}%" if 같방 is not None else f"{이름:<8}{국:<22} 자료 부족")
    찍기("\n읽는 법: ② 다음날 갭이 0.1 안팎이면 08:55 에 쓸 만한 신호가 아니다 · ±2% 넘은 날 같은 방향이 50% 근처면 동전 던지기")
    밖.close()


if __name__ == "__main__":
    main()
