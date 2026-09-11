#!/usr/bin/env python3
r"""
collect_etf.py — **벤치마크용 ETF 일별 시세를 받는다** (2026-09-03 신설)

⚠️⚠️ **사용자 질문에서 나왔다.** *"KODEX 200 TR 실제 연간 수익률은 너가 조사해서 알 수 있지 않아?"*
   → 맞다. 받을 수 있었다. 그동안 **지수(배당 제외)만 벤치마크로 썼다.**

⚠️⚠️ **왜 중요한가.** 지수와 TR ETF는 **매년 2%p씩 다르다**(배당분).
```
해      KODEX 200TR   코스피200 지수    차이
2018      -17.2%       -19.3%      +2.1%p
2020      +35.1%       +32.5%      +2.6%p
2022      -24.1%       -26.2%      +2.0%p
2024       -9.2%       -11.2%      +2.0%p
2025      +94.6%       +90.7%      +3.9%p
```
⇒ 「지수를 이겼다」고 말하려면 **TR 기준**으로 견줘야 공정하다. 2%p를 그냥 얹어주면 안 된다.

⚠️ **경로 주의.** 네이버 API 셋 중 하나만 과거를 준다 (2026-09-03 실측):
```
api.stock.naver.com/chart/domestic/item/{code}   ❌ 날짜 인자를 무시하고 **110건 고정**
m.stock.naver.com/api/stock/{code}/price          ❌ HTTP 400
api.finance.naver.com/siseJson.naver              ✅ **전체 이력** (여기 쓴다)
fchart.stock.naver.com/sise.nhn                   ✅ 전체 이력 (EUC-KR XML)
```
⚠️ KODEX 200TR(278530)은 **2017-11-21 상장**이라 그 이전은 없다.
   더 긴 게 필요하면 KODEX 200(069500·2014-06부터 받힘)이나 지수를 쓴다.

저장: `data/etf-daily.json`  →  `{종목코드: {"이름": ..., "종가": {날짜: 값}}}`

쓰는 법:
    python scripts\collect_etf.py
"""
import io
import json
import os
import sys
import time
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "etf-daily.json")
_H = {"User-Agent": "Mozilla/5.0"}

# ⚠️ 벤치마크로 쓸 것만. 늘리려면 여기에 (코드, 이름)을 더한다
대상 = (("278530", "KODEX 200TR"),
        ("069500", "KODEX 200"),
        ("229200", "KODEX 코스닥150"),
        ("152100", "TIGER 200"))


def 받(code):
    """api.finance.naver.com/siseJson.naver — **파이썬 리터럴 꼴**로 온다."""
    u = ("https://api.finance.naver.com/siseJson.naver"
         f"?symbol={code}&requestType=1&startTime=20100101"
         "&endTime=20991231&timeframe=day")
    with urllib.request.urlopen(urllib.request.Request(u, headers=_H),
                                timeout=40) as r:
        t = r.read().decode("utf-8", errors="replace")
    # ⚠️ 응답이 JSON이 아니라 **작은따옴표 파이썬 리터럴**이다. json.loads가 안 먹는다.
    import ast
    rows = ast.literal_eval(t.strip())
    out = {}
    for x in rows[1:]:
        try:
            d, c = str(x[0]), float(x[4])
            if len(d) == 8 and c > 0:
                out[d] = c
        except (TypeError, ValueError, IndexError):
            continue
    return out


def main():
    표 = {}
    if os.path.exists(OUT):
        try:
            표 = json.load(io.open(OUT, encoding="utf-8-sig"))
        except Exception:
            표 = {}
    for code, 이름 in 대상:
        try:
            a = 받(code)
        except Exception as e:
            print(f"  ⚠️ {이름}({code}) 실패: {type(e).__name__} {e}", flush=True)
            continue
        if not a:
            print(f"  ⚠️ {이름}({code}) 빈 응답", flush=True)
            continue
        옛 = (표.get(code) or {}).get("종가") or {}
        옛.update(a)
        표[code] = {"이름": 이름, "종가":옛}
        k = sorted(옛)
        print(f"  {이름:18} {k[0]} ~ {k[-1]} · {len(옛):,}일", flush=True)
        time.sleep(0.5)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(표, ensure_ascii=False))
    print(f"  저장 → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
