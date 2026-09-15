#!/usr/bin/env python3
r"""
collect_earnings_dates.py — **종목별 실적 발표일(잠정실적 공시일) 2010~** (2026-09-15 신설)

## 왜
사용자: 「실적발표 정책발표 경제지표 전후 테스트한 적 있나?」 → 없다. 「수집 예정이면 **언제** 수집해?」 → 지금.
dart-daily 는 **챙길공시만** 저장한 해가 대부분이다(2015-04-15: 전체 555건 중 54건).
2020~2023 만 `그밖의공시` 까지 다 있다. 그래서 「(잠정)실적」 공시가 그 네 해에만 촘촘하다.

## 무엇을 받나
DART 공시목록(list.json) 을 **거래소공시(pblntf_ty=I)** 로 좁혀 날마다 받고,
공시명에 **「(잠정)실적」** 또는 **「매출액또는손익구조」** 가 든 것만 남긴다.
```
data/earnings-dates.json          {"종목": {code: [[날짜8, 종류], …]}, …}
data/earnings-dates.progress      받은 날짜 한 줄씩 (이어받기)
data/_earnings.log
```
## 한도
DART 하루 **20,000회**. 하루 1~3회(페이지) × 3,000여 일 ≈ 6,000~9,000회. `--상한` 기본 12,000.
00:10 밤 수집이 DART 를 또 쓰니 자정 전에 끝나게 상한을 둔다. 몇 번을 돌려도 안전하다(이어받기).
⚠️ 이미 `그밖의공시` 가 찬 날(2020~23)은 **API 를 안 부르고** 파일에서 뽑는다.
⚠️ KRX 포털은 안 두드린다. DART OpenAPI 만.

쓰는 법:
    python scripts\collect_earnings_dates.py --상한 12000
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_dart as D  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_OUT = os.path.join(_DATA, "earnings-dates.json")
_PROG = os.path.join(_DATA, "earnings-dates.progress")
_LOG = os.path.join(_DATA, "_earnings.log")
_쉼 = 0.02
_말 = (("잠정실적", "(잠정)실적"), ("손익구조", "매출액또는손익구조"))


def 찍기(s):
    줄 = f"{dt.datetime.now():%m-%d %H:%M}  {s}"
    print(줄, flush=True)
    io.open(_LOG, "a", encoding="utf-8").write(줄 + "\n")


def _종류(명):
    for k, w in _말:
        if w in 명:
            return k
    return None


def main():
    상한 = int(sys.argv[sys.argv.index("--상한") + 1]) if "--상한" in sys.argv else 12000
    표 = {}
    if os.path.exists(_OUT):
        try:
            표 = json.load(io.open(_OUT, encoding="utf-8-sig")).get("종목") or {}
        except ValueError:
            표 = {}
    받은날 = set()
    if os.path.exists(_PROG):
        받은날 = {l.strip() for l in io.open(_PROG, encoding="utf-8") if l.strip()}

    def 담기(code, d8, 종):
        벌 = 표.setdefault(code, [])
        if [d8, 종] not in 벌:
            벌.append([d8, 종])

    def 저장():
        for c in 표:
            표[c].sort()
        json.dump({"만든날": dt.date.today().strftime("%Y%m%d"), "출처": "DART list.json (pblntf_ty=I)",
                   "종류": {k: w for k, w in _말}, "종목": 표},
                  io.open(_OUT, "w", encoding="utf-8"), ensure_ascii=False)

    찍기(f"===== 시작 · 상한 {상한:,}회 · 이미 받은 날 {len(받은날):,} · 종목 {len(표):,} =====")
    날 = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    날 = [d for d in 날 if d >= "20100101"]

    # ① 파일에서 공짜로 — 그밖의공시까지 찬 날
    공짜 = 0
    for d8 in 날:
        if d8 in 받은날:
            continue
        p = os.path.join(_DATA, "dart-daily", f"{d8}.json")
        if not os.path.exists(p):
            continue
        try:
            j = json.load(io.open(p, encoding="utf-8-sig"))
        except ValueError:
            continue
        if not (j.get("그밖의공시") or []):
            continue                       # 걸러진 날 — API 로
        for k in ("챙길공시", "그밖의공시"):
            for x in (j.get(k) or []):
                c, 종 = str(x.get("종목코드") or ""), _종류(str(x.get("공시명") or ""))
                if c and 종:
                    담기(c, d8, 종)
        받은날.add(d8)
        io.open(_PROG, "a", encoding="utf-8").write(d8 + "\n")
        공짜 += 1
    찍기(f"[파일] 그밖의공시가 찬 날 {공짜:,}일에서 뽑음 · 종목 {len(표):,}")
    저장()

    # ② API — 나머지 날 (거래소공시만)
    할 = [d for d in 날 if d not in 받은날]
    찍기(f"[API] 받을 날 {len(할):,}일")
    호출 = ok = 실패 = 0
    for i, d8 in enumerate(할, 1):
        if 호출 + 3 > 상한:
            찍기(f"⚠️ 상한 {상한:,} 도달 — {i - 1:,}일까지. 다시 돌리면 이어받는다")
            break
        try:
            page, total, 건 = 1, 0, 0
            while page <= 12:
                d = D.api("list.json", bgn_de=d8, end_de=d8, pblntf_ty="I",
                          page_no=str(page), page_count="100")
                호출 += 1
                st = d.get("status")
                if st == "013":            # 그날 거래소공시 없음
                    break
                if st != "000":
                    raise RuntimeError(f"DART {st}: {d.get('message')}")
                rows = d.get("list") or []
                total = int(d.get("total_count") or 0)
                for x in rows:
                    c, 종 = str(x.get("stock_code") or "").strip(), _종류(str(x.get("report_nm") or ""))
                    if c and 종:
                        담기(c, d8, 종)
                        건 += 1
                if page * 100 >= total or not rows:
                    break
                page += 1
                time.sleep(_쉼)
            받은날.add(d8)
            io.open(_PROG, "a", encoding="utf-8").write(d8 + "\n")
            ok += 1
        except Exception as e:  # noqa: BLE001
            실패 += 1
            찍기(f"  ⚠️ {d8} 실패: {type(e).__name__}: {str(e)[:80]}")
            if 실패 >= 30:
                찍기("⚠️ 실패 30번 — 멈춘다 (한도·키·망 점검)")
                break
        time.sleep(_쉼)
        if i % 200 == 0:
            저장()
            찍기(f"  [API] {i:,}/{len(할):,} — 받음 {ok:,} 실패 {실패} · 호출 {호출:,} · 종목 {len(표):,}")
    저장()
    총 = sum(len(v) for v in 표.values())
    찍기(f"[끝] 받음 {ok:,}일 실패 {실패} · 호출 {호출:,}회 · 종목 {len(표):,} · 공시일 {총:,}건 → {_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
