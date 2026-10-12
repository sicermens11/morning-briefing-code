#!/usr/bin/env python3
r"""
collect_cashflow.py — **연간 현금흐름(영업활동·설비 투자)을 받는다** (2026-10-12 · B251)

왜: F점수 9점 중 현금흐름 둘(영업현금흐름>0 · 발생액 = 순이익 − 영업현금흐름)과 「이익의 질」 재료는
    현금흐름이 있어야 잰다. dart-fin(fnlttMultiAcnt)엔 현금흐름이 없다 — 회사마다 전체 재무제표(fnlttSinglAcntAll)를 따로 불러야 한다
    사용자 10/8 계획 「OpenDART 현금흐름 받기(토·일 · 하루 한도 나눠) → B251」 — 연휴에 안 돌렸다(10/12 다시)
· 별도 재무(OFS) — dart-fin 과 같은 기준 · 없으면 연결(CFS)
· 한 회사·한 해 = 1번 부름 · OpenDART 하루 한도(약 2만)를 다른 수집과 나눠 쓴다 → `--최대`(기본 2,700 = 한 해치쯤)
· 이어받는다: data/dart-cf/{해}.part.json 에 받은 것을 쌓고, 다 받으면 {해}.json 으로 바꾼다
· 한도 넘음(status 020)이면 그 자리에서 멈춘다 — 다음 날 이어서
쓰는 법: python scripts\collect_cashflow.py --해 2024 [--최대 2700]
"""
import glob
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_dart as D  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
OUT = os.path.join(_DATA, "dart-cf")
LOG = os.path.join(_DATA, "_cashflow.log")
_영업ID = ("ifrs-full_CashFlowsFromUsedInOperatingActivities",)
_설비ID = ("ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
           "ifrs-full_PurchaseOfPropertyPlantAndEquipment")


def 찍기(s):
    import datetime as dt
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    try:
        io.open(LOG, "a", encoding="utf-8").write(줄 + "\n")
    except OSError:
        pass


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def 뽑기(rows):
    영, 설 = None, None
    for r in rows:
        if r.get("sj_div") not in ("CF",):
            continue
        aid, nm = r.get("account_id") or "", r.get("account_nm") or ""
        v = _n(r.get("thstrm_amount"))
        if v is None:
            continue
        if 영 is None and (aid in _영업ID or ("영업활동" in nm and ("현금흐름" in nm or "인한" in nm))):
            영 = v
        if 설 is None and (aid in _설비ID or nm.replace(" ", "") in ("유형자산의취득", "유형자산취득")):
            설 = v
    return 영, 설


def main():
    해 = sys.argv[sys.argv.index("--해") + 1] if "--해" in sys.argv else "2024"
    최대 = int(sys.argv[sys.argv.index("--최대") + 1]) if "--최대" in sys.argv else 2700
    os.makedirs(OUT, exist_ok=True)
    끝파일, 부분 = os.path.join(OUT, f"{해}.json"), os.path.join(OUT, f"{해}.part.json")
    if os.path.exists(끝파일):
        찍기(f"  {해}.json 이 이미 있다 — 받지 않는다")
        return 0
    corp = json.load(io.open(os.path.join(_DATA, "dart-corpcode.json"), encoding="utf-8-sig"))
    fin = os.path.join(_DATA, "dart-fin", f"{해}.json")
    if os.path.exists(fin):
        종목 = sorted(json.load(io.open(fin, encoding="utf-8-sig")))       # 그 해 재무가 있는 종목만
    else:
        종목 = sorted(json.load(io.open(sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))[-1], encoding="utf-8-sig"))["종목"])
    받음 = json.load(io.open(부분, encoding="utf-8")) if os.path.exists(부분) else {}
    할 = [c for c in 종목 if c not in 받음 and c in corp]
    찍기(f"  {해}년 현금흐름 — 대상 {len(종목):,} · 받은 것 {len(받음):,} · 남은 것 {len(할):,} · 이번 최대 {최대:,}번")
    n, 실패 = 0, 0
    for c in 할[:최대]:
        for fs in ("OFS", "CFS"):
            try:
                d = D.api("fnlttSinglAcntAll.json", corp_code=corp[c]["corp_code"], bsns_year=해, reprt_code="11011", fs_div=fs)
            except Exception as e:  # noqa: BLE001
                실패 += 1
                d = {"status": "ERR", "message": str(e)[:60]}
            n += 1
            st = d.get("status")
            if st == "020":
                찍기(f"  🛑 하루 한도에 닿았다(020) — 여기서 멈춘다 · 다음에 이어서")
                io.open(부분, "w", encoding="utf-8").write(json.dumps(받음, ensure_ascii=False))
                return 0
            if st == "000":
                영, 설 = 뽑기(d.get("list") or [])
                if 영 is not None or fs == "CFS":
                    받음[c] = {"영업현금흐름": 영, "설비투자": 설, "기준": fs}
                    break
            elif fs == "CFS":
                받음[c] = {"영업현금흐름": None, "설비투자": None, "기준": None, "status": st}
            time.sleep(0.05)
        if len(받음) % 100 == 0:
            io.open(부분, "w", encoding="utf-8").write(json.dumps(받음, ensure_ascii=False))
            찍기(f"    {len(받음):,}/{len(종목):,} · 부름 {n:,} · 실패 {실패}")
    io.open(부분, "w", encoding="utf-8").write(json.dumps(받음, ensure_ascii=False))
    남 = [c for c in 종목 if c not in 받음 and c in corp]
    if not 남:
        os.replace(부분, 끝파일)
        찍기(f"  ✅ {해}년 끝 — {len(받음):,}종목 · 영업현금흐름 있음 {sum(1 for v in 받음.values() if v.get('영업현금흐름') is not None):,}")
    else:
        찍기(f"  {해}년 이번 몫 끝 — 받은 것 {len(받음):,} · 남은 것 {len(남):,} · 부름 {n:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
