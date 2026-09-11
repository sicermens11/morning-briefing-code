#!/usr/bin/env python3
r"""
collect_fx.py — **원/달러·엔/원 환율을 과거로 받는다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 사용자가 짚었다:
   *"내일 09:30 시점에 선물·유가·금·국고채는 안 쌓여 있을 거 아니야? 그럼 테스트에서 제외되잖아?!"*
   맞다. 그 넷은 **KRX 승인이 필요**해서 내일 테스트에 못 들어간다.
   ✅ **환율은 네이버가 주고 과거분도 된다.** KRX와 무관하다.

⚠️ **한국 증시에서 원/달러는 시장 축으로 가장 설명력이 크다고 알려져 있다** —
   외국인 수급과 수출주 실적에 직결된다. 금리·유가보다 먼저다.
   그래서 넷 중 **가장 중요한 하나는 지금 채울 수 있다.**

⚠️ `pageSize`를 키우면 **HTTP 400**이다(2026-09-01 확인). 기본 10건씩 쪽을 넘긴다.
   648거래일이면 약 65쪽 × 2종 = 130회. 1분이면 끝난다.

저장: `data/fx-daily.json`  →  `{"USDKRW": {날짜: 종가}, "JPYKRW": {…}}`

쓰는 법:
    python scripts\collect_fx.py
"""
import io
import json
import os
import sys
import time
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "fx-daily.json")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
종목 = (("USDKRW", "FX_USDKRW"), ("JPYKRW", "FX_JPYKRW"))
_쉼 = 0.1


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


# ⚠️⚠️ **2026-09-03 수정.** 최소날이 `20231201`로 **일부러 끊겨 있었다** → 2.7년치뿐이었다.
#   사용자 지적: *"표본이 부족하거나 기간이 짧으면 수집 방법 찾아서 받아야 하는 거고!"*
#   → 2010년까지 열고 쪽수도 늘린다. 네이버가 주는 데까지 받는다.
def 받기(코드, 최소날="20100101", 최대쪽=1200):
    표 = {}
    for p in range(1, 최대쪽 + 1):
        u = (f"https://api.stock.naver.com/marketindex/exchange/{코드}"
             f"/prices?page={p}&pageSize=10")
        try:
            rows = json.loads(urllib.request.urlopen(
                urllib.request.Request(u, headers=H), timeout=25).read())
        except Exception:
            break
        if not rows:
            break
        for r in rows:
            d = (r.get("localTradedAt") or "").replace("-", "")
            v = _n(r.get("closePrice"))
            if d and v:
                표[d] = v
        if min(표) <= 최소날:          # ⚠️ 목표 기간을 넘어가면 멈춘다
            break
        time.sleep(_쉼)
    return 표


def main():
    out = {}
    if os.path.exists(OUT):
        try:
            out = json.load(io.open(OUT, encoding="utf-8-sig"))
        except Exception:
            out = {}
    for 이름, 코드 in 종목:
        표 = 받기(코드)
        out[이름] = 표
        print(f"  {이름}  {len(표)}일  {min(표) if 표 else '-'} ~ {max(표) if 표 else '-'}",
              flush=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    print(f"  저장 → {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
