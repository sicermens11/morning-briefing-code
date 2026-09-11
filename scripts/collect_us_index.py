#!/usr/bin/env python3
r"""
collect_us_index.py — **미국 지수를 받는다** (2026-09-02 신설)

⚠️⚠️ **사용자 지적에서 나왔다.**
   *"한국 종목이지만, 한국은 미국 산업과 밀접한 영향이 있고, 미장 뉴스에 영향을 많이 받기
   때문에 이런 부분에서는 연계가 되는 게 맞지!"* → **맞다.**

⚠️ 내가 앞서 「미국 데이터는 우선순위가 낮다」고 한 것은 **점수표의 `강화-G/B`(개별 종목
   대응) 기준**이었다. 그건 **종목 대응표가 없어서** 못 한다.
   **하지만 「미국 지수 → 한국 시장」은 전혀 다른 얘기고, 그게 훨씬 중요하다.**
   지수는 **대응표가 필요 없다.**
```
S&P500 · 나스닥 · 다우 전일 등락  →  한국 당일 방향
필라델피아 반도체(SOX)           →  삼성전자·SK하이닉스 등 반도체
```
⚠️⚠️ **시차가 핵심이다.** 미국장은 한국 시간으로 **새벽에 끝난다.**
   그래서 「어젯밤 미국」은 **오늘 아침 08:00 브리핑에 이미 알 수 있다.** look-ahead가 아니다.

**출처**: `api.stock.naver.com/index/{심볼}/price` (무료 · 키 불필요)
```
.INX  S&P500     .IXIC 나스닥     .DJI  다우     .SOX  필라델피아 반도체
```
⚠️ `pageSize`는 **10 고정**(더 크면 HTTP 400) · 페이지는 약 199까지 → **약 8년치(2018~)**

저장: `data/us-index.json`  →  `{심볼: {날짜: {종가, 등락률}}}`
"""
import io
import json
import os
import sys
import time
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "us-index.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
지수들 = [(".INX", "S&P500"), (".IXIC", "나스닥"), (".DJI", "다우"), (".SOX", "필라반도체")]
_쉼 = 0.1


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def 받기(심볼, 최대쪽=210):
    표 = {}
    for p in range(1, 최대쪽 + 1):
        u = f"https://api.stock.naver.com/index/{심볼}/price?pageSize=10&page={p}"
        try:
            rows = json.loads(urllib.request.urlopen(
                urllib.request.Request(u, headers=H), timeout=25).read())
        except Exception:
            break
        if not rows:
            break
        for r in rows:
            d = (r.get("localTradedAt") or "")[:10].replace("-", "")
            c = _n(r.get("closePrice"))
            if d and c:
                표[d] = {"종가": c, "등락률": _n(r.get("fluctuationsRatio"))}
        time.sleep(_쉼)
    return 표


def main():
    out = {}
    if os.path.exists(OUT):
        try:
            out = json.load(io.open(OUT, encoding="utf-8-sig"))
        except Exception:
            out = {}
    for 심볼, 이름 in 지수들:
        표 = 받기(심볼)
        out[이름] = 표
        if 표:
            print(f"  {이름:12s} {len(표):,}일  {min(표)} ~ {max(표)}", flush=True)
        else:
            print(f"  {이름:12s} ❌ 못 받았다", flush=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    print(f"  저장 → {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
