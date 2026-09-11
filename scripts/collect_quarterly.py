#!/usr/bin/env python3
r"""
collect_quarterly.py — **분기 재무를 전 종목 소급 수집** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 스킬의 `재무취약`(−2점)이 **「최신 분기」 기준**인데,
   소급 검증용으로 받아둔 `dart-fin`은 **연간**뿐이다. **8개월 늦은 값으로 검증하고 있었다.**

⚠️ `fetch_stock.quarterly()`가 이미 있지만 **8항목만 남긴다.** 여기서는 **16항목 전부** 받는다 —
   특히 **당좌비율**은 AGENDA에 *"지금 아예 안 보고 있는 지표"*로 적혀 있던 것이다.

**받는 것** (네이버 `finance/quarter`, 종목당 1회, 과거 분기 6개가 같이 온다)
```
매출액 · 영업이익 · 당기순이익 · 지배주주순이익 · 비지배주주순이익 · 영업이익률 · 순이익률
· ROE · **부채비율** · **당좌비율** · 유보율 · EPS · PER · BPS · PBR · 주당배당금
```

⚠️⚠️ **look-ahead 주의.** 분기 실적은 분기 종료 후 **45일 이내**에 공시된다.
   예: 2025Q1(3월 말)은 5월 중순에 나온다. **쓸 때는 공시 시점 이후부터** 적용한다.

⚠️ **DART 한도와 무관하다** — 네이버다. DART 수집과 **병행해도 된다.**
⚠️ 이어받는다. 호출 사이 쉰다.

저장: `data/naver-quarter/{종목코드}.json`

쓰는 법:
    python scripts\collect_quarterly.py
    python scripts\collect_quarterly.py --확인
"""
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_stock as F  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
KRX = os.path.join(_DATA, "krx-daily")
OUT = os.path.join(_DATA, "naver-quarter")
LOG = os.path.join(_DATA, "_quarter.log")
_쉼 = 0.05


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def main():
    확인만 = "--확인" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    종목 = json.load(io.open(sorted(glob.glob(os.path.join(KRX, "*.json")))[-1],
                             encoding="utf-8-sig"))["종목"]
    받 = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(OUT, "*.json"))}
    # ⭐⭐ **--갱신일 N** (2026-09-09 신설) — 파일이 N일보다 오래됐으면 **다시 받는다**.
    #    ⚠️ 이게 없으면 **종목 단위**로 「이미 받았으면 건너뛴다」라서,
    #       전 종목이 한 번 받아진 뒤로는 **새 자료가 생겨도 영영 안 받는다.**
    #       임원매매·5%보유가 이 병으로 2026-09-01 이후 8일간 멈춰 있었다
    _갱신일 = 0
    if "--갱신일" in sys.argv:
        _갱신일 = int(sys.argv[sys.argv.index("--갱신일") + 1])
    if _갱신일 > 0:
        import time as _time
        _낡음 = _time.time() - _갱신일 * 86400
        받 = {c for c in 받
              if os.path.exists(os.path.join(OUT, f"{c}.json"))
              and os.path.getmtime(os.path.join(OUT, f"{c}.json")) >= _낡음}
    할것 = [c for c in 종목 if c not in 받]
    찍기(f"  [분기재무] 전 종목 {len(종목):,} · 이미 받음 {len(받):,} · 받을 것 {len(할것):,}")
    찍기(f"  예상 시간 약 {len(할것)*(_쉼+0.3)/60:.0f}분 (네이버 — DART 한도와 무관)")
    if 확인만 or not 할것:
        찍기("  받을 것이 없다." if not 할것 else "  --확인 이라 받지 않았다.")
        return 0

    ok = 빈 = 실패 = 0
    for i, code in enumerate(할것, 1):
        try:
            fi = (F.get(f"https://m.stock.naver.com/api/stock/{code}/finance/quarter")
                  or {}).get("financeInfo") or {}
            기간 = [t.get("title") for t in (fi.get("trTitleList") or [])]
            표 = {}
            for row in (fi.get("rowList") or []):
                t = row.get("title")
                if not t:
                    continue
                표[t] = [v.get("value") for _, v in sorted((row.get("columns") or {}).items())]
            io.open(os.path.join(OUT, code + ".json"), "w", encoding="utf-8").write(
                json.dumps({"종목": code, "분기": 기간, "항목수": len(표), "값": 표},
                           ensure_ascii=False))
            ok += 1
            빈 += 1 if not 표 else 0
        except Exception:
            실패 += 1
        time.sleep(_쉼)
        if i % 250 == 0:
            찍기(f"    {i:,}/{len(할것):,} — 성공 {ok:,} (자료없음 {빈:,}) 실패 {실패}")
    찍기(f"  [분기재무] 끝 — 성공 {ok:,} · 자료없음 {빈:,} · 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
