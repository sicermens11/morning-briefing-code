#!/usr/bin/env python3
r"""
collect_index.py — **코스피·코스닥 지수(업종별 포함)를 과거로 받는다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가 — 두 가지 구멍을 메운다.**

**① 지금까지 「초과수익률」의 기준이 근사값이었다.**
   전 종목 시총가중 등락률로 지수를 흉내 냈다. 실제 코스피와 다르다
   (코스피는 외국주 제외·우선주 처리 등 규칙이 따로 있다).
   ⚠️ 오늘 내린 결론이 전부 이 근사값 위에 서 있다.

**② 섹터 기준선이 아예 없었다.** ← 이게 더 크다
   우리는 **섹터 브리핑**을 하는데, 종목이 오른 게 **그 섹터가 다 올라서인지
   그 종목만 오른 것인지** 구분할 수단이 없었다.
   `idx/kospi_dd_trd`는 **업종 지수 51개**(화학·제약·금속·건설·정보기술…)를 준다.
   코스닥은 40개. → **「섹터 대비 초과수익」**을 처음으로 잴 수 있다.

✅ 하루 2회 호출(코스피·코스닥)이면 91개 지수가 다 온다. 648일 = **1,296회**. 가볍다.

저장: `data/index-daily/{YYYYMMDD}.json`

쓰는 법:
    python scripts\collect_index.py            # 안 받은 날만
    python scripts\collect_index.py --확인
"""
import glob
import io
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
KRX = os.path.join(_DATA, "krx-daily")
OUT = os.path.join(_DATA, "index-daily")
LOG = os.path.join(_DATA, "_index.log")

API = "https://data-dbg.krx.co.kr/svc/apis/idx"
EPS = (("KOSPI", "kospi_dd_trd"), ("KOSDAQ", "kosdaq_dd_trd"))
_쉼 = 0.1


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def 하루(날, key):
    """그날의 모든 지수. {지수명: {종가, 등락률}}"""
    표 = {}
    for mkt, ep in EPS:
        req = urllib.request.Request(f"{API}/{ep}?basDd={날}", headers={"AUTH_KEY": key})
        try:
            rows = json.loads(urllib.request.urlopen(req, timeout=30).read()).get("OutBlock_1") or []
        except Exception:
            continue                    # ⚠️ 한쪽이 막혀도 나머지는 받는다
        for r in rows:
            이름 = r.get("IDX_NM")
            if not 이름:
                continue
            표[이름] = {"시장": mkt, "분류": r.get("IDX_CLSS"),
                        "종가": _n(r.get("CLSPRC_IDX")),
                        "등락률": _n(r.get("FLUC_RT"))}
        time.sleep(_쉼)
    return 표


def main():
    확인만 = "--확인" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    key = config.get("KRX_API_KEY")
    거래일 = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(KRX, "*.json")))
    받 = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(OUT, "*.json"))}
    할것 = [d for d in 거래일 if d not in 받]
    찍기(f"  거래일 {len(거래일)}일 · 이미 받음 {len(받)}일 · 받을 것 {len(할것)}일")
    찍기(f"  예상 호출 {len(할것)*2:,}회 · 예상 시간 약 {len(할것)*2*(_쉼+0.25)/60:.0f}분")
    if 확인만 or not 할것:
        찍기("  받을 것이 없다." if not 할것 else "  --확인 이라 받지 않았다.")
        return 0

    ok = 빈 = 0
    for i, 날 in enumerate(할것, 1):
        표 = 하루(날, key)
        if 표:
            io.open(os.path.join(OUT, 날 + ".json"), "w", encoding="utf-8").write(
                json.dumps({"기준일": 날, "지수수": len(표), "지수": 표}, ensure_ascii=False))
            ok += 1
        else:
            빈 += 1
        if i % 100 == 0:
            찍기(f"    {i}/{len(할것)} — 받음 {ok} 빈날 {빈}")
    찍기(f"  끝 — 받음 {ok}일 · 빈날 {빈}일")
    return 0


if __name__ == "__main__":
    sys.exit(main())
