#!/usr/bin/env python3
r"""
backfill_flow.py — **전 종목 수급을 과거로 거슬러 받는다** (2026-09-01 신설)

⚠️⚠️ **왜 프로젝트 안으로 옮겼나.** 처음엔 `/tmp/flowfill.py`로 돌렸는데
   **2026-09-01 PC가 과부하로 재부팅되면서 프로세스가 죽었다**(33/69에서). 임시 폴더는
   재부팅에 날아갈 수 있다. **오래 도는 것은 프로젝트 안에 둔다.**

✅ **소실은 없었다** — 기준일 하나가 끝날 때마다 파일로 쓰기 때문이다. 깨진 파일 0개.

⚠️ **이어받는다.** 이미 채워진 기준일은 건너뛴다. 그래서 몇 번이 죽어도 다시 돌리면 된다.

⚠️ **호출 사이에 쉰다**(`_쉼`). 2,766종목 × 69기준일 = 약 19만 호출이라
   쉬지 않으면 PC와 네이버 양쪽에 부담이다. 재부팅의 원인일 수도 있다.

네이버 `trend` API가 `?bizdate=YYYYMMDD`를 받으면 **그 날짜 직전 10거래일**을 준다.
그래서 14일(달력) 간격으로 기준일을 잡으면 빠짐없이 덮인다.

쓰는 법:
    python scripts\backfill_flow.py            # 안 받은 것만 이어받는다
    python scripts\backfill_flow.py --확인       # 뭐가 빠졌는지만 보고 안 받는다
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_stock as F  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KRX = os.path.join(_BASE, "data", "krx-daily")
OUT = os.path.join(_BASE, "data", "flow-daily")
LOG = os.path.join(_BASE, "data", "_flowfill.log")
LOCK = os.path.join(_BASE, "data", "_flowfill.lock")   # ⚠️ 도는 동안만 존재한다

_쉼 = 0.015          # 호출 사이 (초). 2,766종목이면 기준일당 약 41초 더 걸린다
_다찼다 = 2000       # 이 종목 수 이상이면 그 날은 다 받은 것으로 본다


def _거래일():
    return sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(KRX, "*.json")))


def _채워진날():
    """이미 충분히 받은 날짜 집합."""
    out = set()
    for f in glob.glob(os.path.join(OUT, "*.json")):
        try:
            if json.load(io.open(f, encoding="utf-8-sig")).get("종목수", 0) >= _다찼다:
                out.add(os.path.basename(f)[:-5])
        except Exception:
            pass
    return out


def _기준일들():
    # ⚠️ 2026-09-02: KRX가 2010년까지 준다는 걸 확인해 시작을 **2010-01**로 당겼다.
    #    (그전에는 「2024-01이 한계」라고 잘못 알고 있었다)
    out, d = [], dt.date(2010, 1, 15)
    끝 = dt.date.today()
    while d <= 끝:
        out.append(d.strftime("%Y%m%d"))
        d += dt.timedelta(days=14)
    return out


def _덮는날(기준, 거래일):
    """기준일 직전 10거래일."""
    앞 = [d for d in 거래일 if d < 기준]
    return 앞[-10:]


def _n(v):
    try:
        return int(str(v).replace(",", "").replace("+", ""))
    except (TypeError, ValueError):
        return None


def _찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def main():
    확인만 = "--확인" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    거래일 = _거래일()
    if not 거래일:
        _찍기("  ⚠️ krx-daily가 비었다 — 받을 기준이 없다.")
        return 1
    채움 = _채워진날()
    k = json.load(io.open(os.path.join(KRX, 거래일[-1] + ".json"),
                          encoding="utf-8-sig"))["종목"]
    codes = [c for c, _ in sorted(k.items(), key=lambda kv: -float(kv[1].get("시총") or 0))]

    할것 = []
    for b in _기준일들():
        덮 = _덮는날(b, 거래일)
        if 덮 and not all(d in 채움 for d in 덮):
            할것.append(b)

    남은날 = sorted(set(거래일) - 채움)
    _찍기(f"  거래일 {len(거래일)}일 · 채워진 날 {len(채움)}일 "
          f"({len(채움)/len(거래일)*100:.0f}%) · 남은 날 {len(남은날)}일")
    _찍기(f"  이어받을 기준일 {len(할것)}개 · 종목 {len(codes)} "
          f"· 예상 호출 {len(할것)*len(codes):,}회 "
          f"· 예상 시간 약 {len(할것)*len(codes)*(_쉼+0.02)/60:.0f}분")
    if 확인만 or not 할것:
        _찍기("  받을 것이 없다." if not 할것 else "  --확인 이라 받지 않았다.")
        return 0

    # ⚠️⚠️ 잠금을 건다. 저녁 수집(collect_evening)이 **동시에 네이버를 때리지 않도록** —
    #    2026-09-01에 PC가 과부하로 얼어붙은 적이 있다. 두 배로 때리면 또 그럴 수 있다.
    io.open(LOCK, "w", encoding="utf-8").write(dt.datetime.now().isoformat())
    호출 = 실패 = 0
    for bi, b in enumerate(할것, 1):
        모음 = {}
        for c in codes:
            try:
                rows = F.get(f"https://m.stock.naver.com/api/stock/{c}/trend?bizdate={b}")
                호출 += 1
                for r in (rows or []):
                    일 = r.get("bizdate")
                    if not 일:
                        continue
                    모음.setdefault(일, {})[c] = {
                        "외국인": _n(r.get("foreignerPureBuyQuant")),
                        "기관": _n(r.get("organPureBuyQuant")),
                        "개인": _n(r.get("individualPureBuyQuant")),
                        # ⚠️ 2026-09-01: **이미 오던 값인데 버리고 있었다.**
                        #    강화항목 「외국인지분율추이」의 재료다.
                        "외국인지분율": r.get("foreignerHoldRatio"),
                        "종가": r.get("closePrice")}
            except Exception:
                실패 += 1
            time.sleep(_쉼)
        # ⚠️ 기준일 하나가 끝날 때마다 쓴다 — 죽어도 여기까지는 남는다
        for 일, 표 in 모음.items():
            p = os.path.join(OUT, 일 + ".json")
            기존 = {}
            if os.path.exists(p):
                try:
                    기존 = json.load(io.open(p, encoding="utf-8-sig")).get("종목") or {}
                except Exception:
                    기존 = {}
            기존.update(표)
            io.open(p, "w", encoding="utf-8").write(json.dumps(
                {"기준일": 일, "종목수": len(기존), "종목": 기존}, ensure_ascii=False))
        _찍기(f"  [{bi}/{len(할것)}] {b} — 호출 {호출:,} 실패 {실패} "
              f"· 쌓인 날 {len(glob.glob(os.path.join(OUT, '*.json')))}")
    try:
        os.remove(LOCK)
    except OSError:
        pass
    _찍기("  끝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
