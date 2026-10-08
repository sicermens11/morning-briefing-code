#!/usr/bin/env python3
r"""
collect_estimates.py — **다음 분기 실적 예상치를 매일 저장한다** (2026-10-08 신설)

사용자 10/8: 「실적발표도 기대보다 높으면 오르고, 기대만큼이거나 낮으면 주가가 떨어지는거겠지?」
  → 그걸 재려면 **발표 전 예상치**가 있어야 한다. 과거 예상치는 쌓아 둔 게 없다(consensus-history 는 목표주가·의견뿐).
  ⇒ 오늘부터 매일 모든 종목의 네이버 분기 표에서 **isConsensus "Y" 분기(아직 안 나온 분기의 증권사 예상치)**를 저장한다.
     회사가 실적을 내면 그 분기가 isConsensus "N"(확정)으로 바뀐다 → 발표 직전 예상 vs 확정 · 주가 반응을 잰다
     (3분기 실적 시즌 10월 중순~11월 중순 → 11월 말 첫 결과)

저장: data/estimates/YYYYMMDD.jsonl — 한 줄에 한 종목 {code, name, 분기, 예상{매출액·영업이익·당기순이익}, 직전확정{분기·같은 칸}}
      예상치가 없는 종목(증권사가 안 다루는 종목)은 적지 않는다
쓰는 법: python scripts\collect_estimates.py            (전 종목 · 약 2,700번 요청 · 0.15초 간격 · 7~10분)
         python scripts\collect_estimates.py --codes 005930,222800
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_D = os.path.join(_B, "data")
KEEP = ("매출액", "영업이익", "당기순이익")
HDR = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}


def 분기표(code):
    req = urllib.request.Request(f"https://m.stock.naver.com/api/stock/{code}/finance/quarter", headers=HDR)
    fi = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8")).get("financeInfo") or {}
    tt = fi.get("trTitleList") or []
    예상 = [t for t in tt if t.get("isConsensus") == "Y"]
    확정 = [t for t in tt if t.get("isConsensus") != "Y"]
    if not 예상:
        return None
    rows = {r.get("title"): r.get("columns") or {} for r in fi.get("rowList") or [] if r.get("title") in KEEP}

    def 값(key):
        return {k: (rows.get(k, {}).get(key) or {}).get("value") for k in KEEP}
    e, last = 예상[0], (확정[-1] if 확정 else None)
    # ⚠️ 10/8 첫 실행: 증권사가 안 다루는 종목도 예상 칸이 있고 값이 전부 「-」 였다(658줄 중 398) — 빈 것은 안 적는다
    if all(v in (None, "", "-") for v in 값(e.get("key")).values()):
        return None
    return {"분기": e.get("key"), "예상": 값(e.get("key")),
            "직전확정": {"분기": last.get("key"), **값(last.get("key"))} if last else None}


def main():
    if "--codes" in sys.argv:
        목록 = [(c, "") for c in sys.argv[sys.argv.index("--codes") + 1].split(",")]
    else:
        최근 = sorted(glob.glob(os.path.join(_D, "krx-daily", "*.json")))[-1]
        j = json.load(io.open(최근, encoding="utf-8-sig"))
        목록 = [(c, v.get("이름") or "") for c, v in (j.get("종목") or {}).items()]
    오늘 = dt.date.today().strftime("%Y%m%d")
    os.makedirs(os.path.join(_D, "estimates"), exist_ok=True)
    밖 = os.path.join(_D, "estimates", f"{오늘}.jsonl")
    n = 잘 = 실 = 0
    with io.open(밖, "w", encoding="utf-8") as f:
        for code, name in 목록:
            n += 1
            try:
                r = 분기표(code)
            except Exception:  # noqa: BLE001
                실 += 1
                r = None
            if r:
                f.write(json.dumps({"code": code, "name": name, **r}, ensure_ascii=False) + "\n")
                잘 += 1
            time.sleep(0.15)
            if n % 500 == 0:
                print(f"  {n:,}/{len(목록):,} · 예상치 있는 종목 {잘:,} · 실패 {실}", flush=True)
    print(f"끝 — {len(목록):,}종목 중 예상치 있는 {잘:,} · 실패 {실} → {밖}")


if __name__ == "__main__":
    main()
