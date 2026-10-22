#!/usr/bin/env python3
r"""
collect_kis_hist.py — **한국투자증권에서 신용잔고 일별 · 공매도 일별을 2010년부터 받는다** (2026-10-22 신설 · 조회만)

사용자 10/22 「그전에 먼저 테스트해볼 가치가 있는지 한번 검토해봐」 → 신용잔고 ◎ · 공매도 △ → 「실전 열쇠로 받고 키를 지우면 어때?」 → 「넣었어」
대상: 신호가 났던 종목(data/_labs/news_events.jsonl 의 code ∪ forward-log 후보·보완) — 전 종목이 아니다
저장: data/kis-credit/{code}.json  {"받은날","종목","칸":[…],"행":[[날,…]…]}  (신용잔고 · 30건/호출 · 거슬러 받기 · 2009-11~)
      data/kis-short/{code}.json   {"받은날","종목","칸":[…],"행":[[날,…]…]}  (공매도 · 100건/호출 · 2010-01-04 부터 150일 창)
      칸을 줄여 저장(전체 칸이면 종목당 2.7MB · 968종목 5GB) · 두 폴더는 .gitignore
이어 받기: 이미 파일이 있고 「끝」 표시가 있으면 건너뛴다 · 로그 data/_kis_collect.log
속도: 실측 호출 하나 0.5초(서버 응답) → 종목 하나 1.5분 → 968종목 혼자면 24시간 → 조각을 나란히. 6조각(12번/초)은 바로 EGW00201 → **3조각**(약 6번/초 · 8시간)
⚠️ 조회만 · 주문 없음 · 모든 조각이 끝나면(전 종목 파일 「끝」) 마지막 조각이 토큰을 폐기하고 「실전 열쇠를 지워 달라」 고 로그에 적는다

쓰는 법:  python scripts\collect_kis_hist.py                (실전 열쇠 · 없으면 모의로)
          python scripts\collect_kis_hist.py --조각 0/6      6조각 중 0번째(코드 정렬 i%6==0) — run_kis_collect.ps1 이 6개 띄운다
          python scripts\collect_kis_hist.py --최대 5        시험으로 5종목만
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_B, "scripts"))
_LOG = os.path.join(_B, "data", "_kis_collect.log")
시작일 = "20100104"


def 적기(s):
    줄 = f"{dt.datetime.now():%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    with io.open(_LOG, "a", encoding="utf-8") as f:
        f.write(줄 + "\n")


def 대상종목():
    코드 = {}
    p = os.path.join(_B, "data", "_labs", "news_events.jsonl")
    if os.path.exists(p):
        for z in io.open(p, encoding="utf-8"):
            if z.strip():
                r = json.loads(z)
                코드.setdefault(r["code"], r.get("이름", ""))
    for z in io.open(os.path.join(_B, "data", "forward-log.jsonl"), encoding="utf-8"):
        if z.strip():
            r = json.loads(z)
            for x in (r.get("후보") or []) + (r.get("보완후보") or []):
                코드.setdefault(x["종목코드"], x.get("이름", ""))
    return 코드


def 끝났나(p):
    try:
        return bool(json.load(io.open(p, encoding="utf-8")).get("끝"))
    except (OSError, ValueError):
        return False


신용칸 = ["deal_date", "stck_prpr", "acml_vol", "whol_loan_rmnd_stcn", "whol_loan_rmnd_rate", "whol_loan_new_stcn", "whol_loan_rdmp_stcn", "whol_loan_rmnd_amt", "whol_stln_rmnd_stcn"]
공매도칸 = ["stck_bsop_date", "stck_clpr", "acml_vol", "ssts_cntg_qty", "ssts_vol_rlim", "acml_ssts_cntg_qty", "acml_ssts_cntg_qty_rlim", "ssts_tr_pbmn"]


def 저장(p, 종목, 이름, 행, 끝, 칸):
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump({"받은날": dt.date.today().isoformat(), "종목": 종목, "이름": 이름, "끝": 끝, "건수": len(행), "칸": 칸,
                   "행": [[r.get(c) for c in 칸] for r in 행]}, f, ensure_ascii=False, separators=(",", ":"))


def 공매도받기(k, 코드, 이름, p):
    행, 본 = [], set()
    오늘 = dt.date.today()
    d = dt.date(2010, 1, 4)
    while d <= 오늘:
        e = min(d + dt.timedelta(days=150), 오늘)
        rows = k.공매도일별(코드, d.strftime("%Y%m%d"), e.strftime("%Y%m%d"))
        for r in rows:
            dd = str(r.get("stck_bsop_date") or "")
            if dd and dd not in 본:
                본.add(dd)
                행.append(r)
        if len(rows) >= 100:   # 창이 넘쳤다 — 받은 마지막 날 다음부터 다시
            dd = max(str(r.get("stck_bsop_date")) for r in rows)
            d = dt.datetime.strptime(dd, "%Y%m%d").date() + dt.timedelta(days=1)
        else:
            d = e + dt.timedelta(days=1)
    행.sort(key=lambda r: str(r.get("stck_bsop_date")))
    저장(p, 코드, 이름, 행, True, 공매도칸)
    return len(행)


def 신용받기(k, 코드, 이름, p):
    행, 본 = [], set()
    기준 = dt.date.today().strftime("%Y%m%d")
    막힘 = 0
    while 기준 >= 시작일 and 막힘 < 3:
        rows = k.신용잔고일별(코드, 기준)
        새 = 0
        for r in rows:
            dd = str(r.get("deal_date") or "")
            if dd and dd not in 본:
                본.add(dd)
                행.append(r)
                새 += 1
        if not rows or 새 == 0:
            막힘 += 1
            기준 = (dt.datetime.strptime(기준, "%Y%m%d").date() - dt.timedelta(days=45)).strftime("%Y%m%d")
            continue
        막힘 = 0
        가장옛 = min(str(r.get("deal_date")) for r in rows)
        기준 = (dt.datetime.strptime(가장옛, "%Y%m%d").date() - dt.timedelta(days=1)).strftime("%Y%m%d")
    행.sort(key=lambda r: str(r.get("deal_date")))
    저장(p, 코드, 이름, 행, True, 신용칸)
    return len(행)


def main():
    import kis_api
    최대 = 0
    if "--최대" in sys.argv:
        최대 = int(sys.argv[sys.argv.index("--최대") + 1])
    환경 = "실전"
    try:
        k = kis_api.KIS("실전")
    except RuntimeError:
        환경 = "모의"
        k = kis_api.KIS("모의")
    for d in ("kis-credit", "kis-short"):
        os.makedirs(os.path.join(_B, "data", d), exist_ok=True)
    목록 = 대상종목()
    전체 = sorted(목록)
    코드들 = 전체
    조각 = ""
    if "--조각" in sys.argv:
        조각 = sys.argv[sys.argv.index("--조각") + 1]
        i, n = (int(x) for x in 조각.split("/"))
        코드들 = [c for j, c in enumerate(전체) if j % n == i]
        조각 = f"조각 {조각} · "
    if 최대:
        코드들 = 코드들[:최대]
    적기(f"===== 시작 · {환경} · {조각}종목 {len(코드들):,} · 이미 끝난 것 신용 {sum(1 for c in 코드들 if 끝났나(os.path.join(_B, 'data', 'kis-credit', c + '.json'))):,} · 공매도 {sum(1 for c in 코드들 if 끝났나(os.path.join(_B, 'data', 'kis-short', c + '.json'))):,} =====")
    t0 = time.time()
    실패 = 0
    for i, c in enumerate(코드들, 1):
        이름 = 목록[c]
        for 종류, fn in (("kis-credit", 신용받기), ("kis-short", 공매도받기)):
            p = os.path.join(_B, "data", 종류, c + ".json")
            if 끝났나(p):
                continue
            for 번 in range(3):   # 종목 단위로도 세 번 — 한 번 막혔다고 그 종목을 버리지 않는다(10/22 여섯 조각에서 EGW00201 로 종목이 줄줄이 빠졌다)
                try:
                    n = fn(k, c, 이름, p)
                    break
                except Exception as e:  # noqa: BLE001
                    적기(f"  ✗ {이름} {c} {종류} ({번 + 1}/3): {str(e)[:100]}")
                    time.sleep(10)
            else:
                실패 += 1
                if 실패 >= 30:
                    적기("🛑 실패 30건 — 멈춘다")
                    return 1
        if i % 25 == 0:
            적기(f"  {조각}{i:,}/{len(코드들):,} · {(time.time() - t0) / 60:.0f}분 · 실패 {실패}")
    적기(f"===== 끝 · {조각}종목 {len(코드들):,} · 실패 {실패} · {(time.time() - t0) / 60:.0f}분 =====")
    if 환경 == "실전" and not 최대:
        # 다른 조각이 아직 받는 중이면 토큰을 죽이면 안 된다 — 전 종목 두 폴더 모두 「끝」일 때만
        남은 = sum(1 for c in 전체 for d in ("kis-credit", "kis-short") if not 끝났나(os.path.join(_B, "data", d, c + ".json")))
        if 남은:
            적기(f"  다른 조각 아직 받는 중(남은 파일 {남은:,}) — 토큰은 마지막 조각이 폐기한다")
        else:
            적기("토큰 폐기: " + k.토큰폐기())
            적기("⚠️ 실전 열쇠를 secrets.json 에서 지워 주세요 (KIS_APP_KEY · KIS_APP_SECRET · KIS_ACCOUNT) — 받기 끝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
