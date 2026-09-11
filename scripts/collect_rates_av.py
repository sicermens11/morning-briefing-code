#!/usr/bin/env python3
r"""
collect_rates_av.py — **금리를 Alpha Vantage 로 받는다** (2026-09-09 밤 신설)

## 왜 만드나 — FRED 가 9/3부터 접속이 안 된다
```
2026-09-03 20:41  ⚠️ DFEDTAR   TimeoutError
2026-09-03 20:55  ⚠️ DGS3MO    ConnectionResetError [WinError 10054]
2026-09-09 22:28  ⚠️ DFF       TimeoutError -> 600초를 넘겨 저녁 수집에서 실패
=> **매일 저녁 10분을 여기서 버린다.** data/fred/ 에 파일이 2개뿐이다

그런데 그 2개는 **이미 Alpha Vantage 로 받은 것**이고(AV_ 접두사),
시험들(brief_lab·cut_lab·group_lab·prob2_lab)이 **그걸 읽고 있다.**
⚠️ 다만 **2026-09-03 에 멈춰 있다** — 갱신하는 스크립트가 없었다
```

## 받는 것 (Alpha Vantage · 무료 티어를 아끼려고 셋만)
```
FEDERAL_FUNDS_RATE            -> AV_FEDFUNDS.json   미국 기준금리
TREASURY_YIELD 2year          -> AV_DGS2.json       미국 2년물
TREASURY_YIELD 10year         -> AV_DGS10.json      미국 10년물  ⭐ 새로 받는다
```

## ⚠️ 오늘 배운 것을 지킨다
```
① **0건이면 저장하지 않는다** — 컨센서스 빈 파일 38개가 그 병이었다
   (오류로 0건 받았는데 저장해버려서, 다음엔 「이미 받음」으로 영영 건너뛰었다)
② **「이미 받았으면 건너뛴다」를 안 쓴다** — 매번 전체를 받아 덮어쓴다
   (임원매매가 종목 단위 건너뛰기로 8일간 멈춰 있었다)
③ 실패하면 **기존 파일을 안 건드린다**
```

쓰는 법:
    python scripts\collect_rates_av.py
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "fred")
LOG = os.path.join(_BASE, "data", "_rates_av.log")

# (파일이름, 이름, function, 추가 인자)
_받을것 = (
    ("AV_FEDFUNDS", "미국 기준금리(Alpha Vantage)", "FEDERAL_FUNDS_RATE", {}),
    ("AV_DGS2", "미국 2년물(Alpha Vantage)", "TREASURY_YIELD",
     {"maturity": "2year"}),
    ("AV_DGS10", "미국 10년물(Alpha Vantage)", "TREASURY_YIELD",
     {"maturity": "10year"}),
)


def 찍기(s):
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(줄 + "\n")
    except OSError:
        pass


def 받기(키, 펑션, 더):
    """{'20260901': 3.63, ...} 또는 None"""
    q = f"function={펑션}&interval=daily&apikey={키}"
    for k, v in 더.items():
        q += f"&{k}={v}"
    u = f"https://www.alphavantage.co/query?{q}"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    # ⚠️ 한도 초과·오류일 때 Alpha Vantage 는 200 으로 **말만 돌려준다**
    if "Note" in d or "Information" in d or "Error Message" in d:
        말 = (d.get("Note") or d.get("Information")
              or d.get("Error Message") or "")[:90]
        raise RuntimeError(f"AV가 자료 대신 말을 돌려줬다: {말}")
    줄 = d.get("data") or []
    난것 = {}
    for z in 줄:
        나 = str(z.get("date") or "")
        값 = z.get("value")
        if len(나) == 10 and 값 not in (None, "", "."):
            try:
                난것[나.replace("-", "")] = float(값)
            except ValueError:
                continue
    return 난것


def main():
    키 = config.get("ALPHAVANTAGE_API_KEY")
    if not 키:
        찍기("⚠️ ALPHAVANTAGE_API_KEY 가 없다 — 그만둔다")
        return 1
    os.makedirs(OUT, exist_ok=True)
    찍기(f"===== 금리(Alpha Vantage) · {len(_받을것)}가지 =====")
    성공 = 0
    for 파, 이름, 펑, 더 in _받을것:
        p = os.path.join(OUT, f"{파}.json")
        옛수 = 0
        if os.path.exists(p):
            try:
                옛수 = len(json.load(io.open(p, encoding="utf-8-sig"))
                          .get("값") or {})
            except Exception:  # noqa: BLE001
                pass
        try:
            값 = 받기(키, 펑, 더)
        except Exception as e:  # noqa: BLE001
            # ⚠️ ③ 실패하면 **기존 파일을 안 건드린다**
            찍기(f"  ⚠️ {파:<14}실패: {type(e).__name__} {str(e)[:70]}"
                 f" — 기존 {옛수:,}개를 그대로 둔다")
            continue
        # ⚠️ ① **0건이면 저장하지 않는다**
        if not 값:
            찍기(f"  ⚠️ {파:<14}**0건이 왔다 — 저장하지 않는다**"
                 f" (기존 {옛수:,}개 유지)")
            continue
        if 옛수 and len(값) < 옛수 * 0.8:
            찍기(f"  ⚠️ {파:<14}받은 게 {len(값):,}개인데 기존이 {옛수:,}개다 —"
                 f" **줄었으니 저장하지 않는다**")
            continue
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump({"시리즈": 파, "이름": 이름, "주기": "daily",
                       "출처": "Alpha Vantage", "값": 값},
                      f, ensure_ascii=False)
        k = sorted(값)
        찍기(f"  ✅ {파:<14}{len(값):,}개 · {k[0]} ~ {k[-1]}"
             f" (전 {옛수:,}개)")
        성공 += 1
        time.sleep(15)          # ⚠️ 무료 티어는 분당 호출 수가 적다
    찍기(f"===== 끝 · 성공 {성공}/{len(_받을것)} =====")
    return 0 if 성공 else 1


if __name__ == "__main__":
    sys.exit(main())
