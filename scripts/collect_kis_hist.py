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


대차칸 = ["bsop_date", "stck_prpr", "acml_vol", "new_stcn", "rdmp_stcn", "rmnd_stcn", "rmnd_amt"]
의견칸 = ["stck_bsop_date", "mbcr_name", "invt_opnn", "invt_opnn_cls_code", "rgbf_invt_opnn", "hts_goal_prc", "stck_prdy_clpr"]


def 대차받기(k, 코드, 이름, p):
    """2014-01 부터 120일 창(거래일 80개 안팎 < 한 번 최대 100건)"""
    행, 본 = [], set()
    오늘 = dt.date.today()
    d = dt.date(2014, 1, 1)
    while d <= 오늘:
        e = min(d + dt.timedelta(days=120), 오늘)
        for r in k.대차일별(코드, d.strftime("%Y%m%d"), e.strftime("%Y%m%d")):
            dd = str(r.get("bsop_date") or "")
            if dd and dd not in 본:
                본.add(dd)
                행.append(r)
        d = e + dt.timedelta(days=1)
    행.sort(key=lambda r: str(r.get("bsop_date")))
    저장(p, 코드, 이름, 행, True, 대차칸)
    return len(행)


def 의견받기(k, 코드, 이름, p):
    """2010~ 를 1년씩 · 한 창에서 100건이 차면 반으로 쪼개 다시(최근 것부터 100건만 주므로)"""
    행, 본 = [], set()

    def 창(a, b):
        rows = k.투자의견(코드, a.strftime("%Y%m%d"), b.strftime("%Y%m%d"))
        if len(rows) >= 100 and (b - a).days > 3:
            m = a + (b - a) / 2
            창(a, m)
            창(m + dt.timedelta(days=1), b)
            return
        for r in rows:
            key = tuple(str(r.get(c)) for c in 의견칸)
            if key not in 본:
                본.add(key)
                행.append(r)
    오늘 = dt.date.today()
    for 해 in range(2010, 오늘.year + 1):
        창(dt.date(해, 1, 1), min(dt.date(해, 12, 31), 오늘))
    행.sort(key=lambda r: str(r.get("stck_bsop_date")))
    저장(p, 코드, 이름, 행, True, 의견칸)
    return len(행)


def 대형종목():
    """2010~ 어느 날이든 시총 1조↑ 였던 종목(krx-daily 20번째 날마다) — 지금 큰 것만 고르면 사라진·작아진 대형주가 빠진다"""
    fs = sorted(glob.glob(os.path.join(_B, "data", "krx-daily", "*.json")))
    코드 = {}
    for f in fs[::20] + fs[-1:]:
        try:
            s = json.load(io.open(f, encoding="utf-8")).get("종목") or {}
        except ValueError:
            continue
        for c, v in s.items():
            if (v.get("시총") or 0) >= 1e12:
                코드.setdefault(c, v.get("이름", ""))
    return 코드


투자자칸 = ["stck_bsop_date", "stck_clpr", "acml_vol", "frgn_ntby_qty", "prsn_ntby_qty", "orgn_ntby_qty", "scrt_ntby_qty", "ivtr_ntby_qty",
         "bank_ntby_qty", "insu_ntby_qty", "mrbn_ntby_qty", "fund_ntby_qty", "etc_ntby_qty"]
프로그램칸 = ["stck_bsop_date", "acml_vol", "whol_smtn_seln_vol", "whol_smtn_shnu_vol", "whol_smtn_ntby_qty", "whol_smtn_ntby_tr_pbmn"]
체결량칸 = ["stck_bsop_date", "total_seln_qty", "total_shnu_qty"]
시장투자자칸 = ["stck_bsop_date", "bstp_nmix_prpr", "frgn_ntby_qty", "prsn_ntby_qty", "orgn_ntby_qty", "scrt_ntby_qty", "ivtr_ntby_qty",
           "pe_fund_ntby_vol", "bank_ntby_qty", "insu_ntby_qty", "mrbn_ntby_qty", "fund_ntby_qty", "etc_ntby_qty",
           "frgn_ntby_tr_pbmn", "prsn_ntby_tr_pbmn", "orgn_ntby_tr_pbmn"]
Q = "/uapi/domestic-stock/v1/quotations/"


def 거슬러받기(받기, 날칸, 칸, 코드, 이름, p):
    """기준일부터 거슬러 N건씩 주는 API(투자자·프로그램·시장투자자) — 가장 옛 날 전날로 다시 · 2010-01 까지 · 새 줄 없으면 45일 건너 세 번"""
    행, 본 = [], set()
    # 어제부터 — 투자자별 일별은 장중에 오늘 날짜를 넣으면 OPSQ2001 「TIME LIMIT 00:00 ~ 15:40」(10/23 실측)
    기준 = (dt.date.today() - dt.timedelta(days=1)).strftime("%Y%m%d")
    막힘 = 0
    while 기준 >= 시작일 and 막힘 < 3:
        rows = 받기(기준)
        새 = 0
        for r in rows:
            dd = str(r.get(날칸) or "")
            if dd and dd not in 본:
                본.add(dd)
                행.append(r)
                새 += 1
        if not rows or 새 == 0:
            막힘 += 1
            기준 = (dt.datetime.strptime(기준, "%Y%m%d").date() - dt.timedelta(days=45)).strftime("%Y%m%d")
            continue
        막힘 = 0
        가장옛 = min(str(r.get(날칸)) for r in rows if r.get(날칸))
        기준 = (dt.datetime.strptime(가장옛, "%Y%m%d").date() - dt.timedelta(days=1)).strftime("%Y%m%d")
    행.sort(key=lambda r: str(r.get(날칸)))
    저장(p, 코드, 이름, 행, True, 칸)
    return len(행)


def 투자자받기(k, 코드, 이름, p):
    return 거슬러받기(lambda d: k._get(Q + "investor-trade-by-stock-daily", "FHPTJ04160001",
                                  {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": 코드, "FID_INPUT_DATE_1": d, "FID_ORG_ADJ_PRC": "", "FID_ETC_CLS_CODE": ""}).get("output2") or [],
                      "stck_bsop_date", 투자자칸, 코드, 이름, p)


def 프로그램받기(k, 코드, 이름, p):
    return 거슬러받기(lambda d: k._get(Q + "program-trade-by-stock-daily", "FHPPG04650201",
                                  {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": 코드, "FID_INPUT_DATE_1": d}).get("output") or [],
                      "stck_bsop_date", 프로그램칸, 코드, 이름, p)


_시장코드 = {"0001": "KSP", "1001": "KSQ"}


def 시장투자자받기(k, 코드, 이름, p):
    return 거슬러받기(lambda d: k._get(Q + "inquire-investor-daily-by-market", "FHPTJ04040000",
                                  {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": 코드, "FID_INPUT_DATE_1": d, "FID_INPUT_ISCD_1": _시장코드[코드],
                                   "FID_INPUT_DATE_2": d, "FID_INPUT_ISCD_2": 코드}).get("output") or [],
                      "stck_bsop_date", 시장투자자칸, 코드, 이름, p)


def 체결량받기(k, 코드, 이름, p):
    """날짜 범위 API — 80일 창(거래일 55개 안팎 · 한 분기 61건이 그대로 나왔다)"""
    행, 본 = [], set()
    오늘 = dt.date.today()
    d = dt.date(2010, 1, 4)
    while d <= 오늘:
        e = min(d + dt.timedelta(days=80), 오늘)
        j = k._get(Q + "inquire-daily-trade-volume", "FHKST03010800",
                   {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": 코드, "FID_INPUT_DATE_1": d.strftime("%Y%m%d"),
                    "FID_INPUT_DATE_2": e.strftime("%Y%m%d"), "FID_PERIOD_DIV_CODE": "D"})
        for r in j.get("output2") or []:
            dd = str(r.get("stck_bsop_date") or "")
            if dd and dd not in 본:
                본.add(dd)
                행.append(r)
        d = e + dt.timedelta(days=1)
    행.sort(key=lambda r: str(r.get("stck_bsop_date")))
    저장(p, 코드, 이름, 행, True, 체결량칸)
    return len(행)


종류표 = {"신용공매도": (("kis-credit", 신용받기), ("kis-short", 공매도받기)),
         "대차": (("kis-loan", 대차받기),),
         "의견": (("kis-opinion", 의견받기),),
         "투자자": (("kis-investor", 투자자받기),),
         "프로그램": (("kis-program", 프로그램받기),),
         "체결량": (("kis-tradevol", 체결량받기),),
         "시장투자자": (("kis-mktflow", 시장투자자받기),)}


def main():
    import kis_api
    최대 = 0
    if "--최대" in sys.argv:
        최대 = int(sys.argv[sys.argv.index("--최대") + 1])
    종류 = sys.argv[sys.argv.index("--종류") + 1] if "--종류" in sys.argv else "신용공매도"
    환경 = "실전"
    try:
        k = kis_api.KIS("실전")
    except RuntimeError:
        환경 = "모의"
        k = kis_api.KIS("모의")
    # 일감 = (폴더, 받는 함수, 코드, 이름) — 종류 여럿은 「대차+의견」 처럼 잇는다 · 조각은 일감 순번으로 나눈다
    일 = []
    for 종 in 종류.split("+"):
        목록 = 대형종목() if 종 == "의견" else ({"0001": "코스피", "1001": "코스닥"} if 종 == "시장투자자" else 대상종목())
        for 폴더, fn in 종류표[종]:
            os.makedirs(os.path.join(_B, "data", 폴더), exist_ok=True)
            일 += [(폴더, fn, c, 목록[c]) for c in sorted(목록)]
    전체 = 일
    조각 = ""
    if "--조각" in sys.argv:
        조각 = sys.argv[sys.argv.index("--조각") + 1]
        i, n = (int(x) for x in 조각.split("/"))
        일 = [z for j, z in enumerate(전체) if j % n == i]
        조각 = f"조각 {조각} · "
    if 최대:
        일 = 일[:최대]
    적기(f"===== 시작 · {환경} · {종류} · {조각}일감 {len(일):,} · 이미 끝난 것 {sum(1 for z in 일 if 끝났나(os.path.join(_B, 'data', z[0], z[2] + '.json'))):,} =====")
    t0 = time.time()
    실패 = 0
    for i, (폴더, fn, c, 이름) in enumerate(일, 1):
        p = os.path.join(_B, "data", 폴더, c + ".json")
        if not 끝났나(p):
            for 번 in range(3):   # 종목 단위로도 세 번 — 한 번 막혔다고 그 종목을 버리지 않는다(10/22 여섯 조각에서 EGW00201 로 종목이 줄줄이 빠졌다)
                try:
                    fn(k, c, 이름, p)
                    break
                except Exception as e:  # noqa: BLE001
                    적기(f"  ✗ {이름} {c} {폴더} ({번 + 1}/3): {str(e)[:100]}")
                    time.sleep(10)
            else:
                실패 += 1
                if 실패 >= 30:
                    적기("🛑 실패 30건 — 멈춘다")
                    return 1
        if i % 25 == 0:
            적기(f"  {조각}{i:,}/{len(일):,} · {(time.time() - t0) / 60:.0f}분 · 실패 {실패}")
    적기(f"===== 끝 · {조각}일감 {len(일):,} · 실패 {실패} · {(time.time() - t0) / 60:.0f}분 =====")
    if 환경 == "실전" and not 최대:
        # 다른 조각이 아직 받는 중이면 토큰을 죽이면 안 된다 — 이 종류의 일감이 전부 「끝」일 때만
        남은 = sum(1 for z in 전체 if not 끝났나(os.path.join(_B, "data", z[0], z[2] + ".json")))
        if 남은:
            적기(f"  다른 조각 아직 받는 중(남은 파일 {남은:,}) — 토큰은 마지막 조각이 폐기한다")
        else:
            적기("토큰 폐기: " + k.토큰폐기())
            적기("⚠️ 실전 열쇠를 secrets.json 에서 지워 주세요 (KIS_APP_KEY · KIS_APP_SECRET · KIS_ACCOUNT) — 받기 끝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
