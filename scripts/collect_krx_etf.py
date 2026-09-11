#!/usr/bin/env python3
r"""
collect_krx_etf.py — **국내 상장 ETF 전종목을 16.7년치 받는다** (2026-09-03 신설)

⚠️⚠️ **사용자 요청에서 나왔다.**
   *"지수뿐만 아니라 다른 국내 ETF 정보(가능하면 해외 ETF도)도 수집해서 분석에 필요할 것 같은데?"*
   *"우리가 미국 상승 신호를 잡아 수익 실현을 위한 매수 방법에 대한 테스트는 못하나?"*

⚠️⚠️ **KRX OpenAPI `etp/etf_bydd_trd`가 승인돼 있고 2010년부터 다 준다** (2026-09-03 실측).
```
20100104   50종목        20200102  450종목       20250102  935종목
20150102  172종목        20230102  666종목       20260902 1,167종목
```
⚠️ **선물·국고채·일반상품은 2024-01-02 이전을 안 주는데 ETF는 2010년부터 준다.** 서비스마다 다르다.

⚠️⚠️ **이게 「미국 상승 신호로 매수」를 푸는 열쇠다.**
   미국 지수를 추종하는 **국내 상장 ETF**(TIGER 미국나스닥100 등)가 이 목록에 들어 있다.
   ⇒ 미국 지수 원본은 3년치뿐이지만, **국내 ETF로는 훨씬 길게 시험할 수 있고**
      실제로 **원화로 살 수 있다**(해외 계좌·환전이 필요 없다).

⚠️ 네이버 경로는 다 막혔다 (2026-09-03 확인): `etf/list` 400 · `etf/all` 404 ·
   해외 `stock/SPY.O` 409 · `worldstock` 404. **KRX가 유일한 길이다.**

**받는 것**: 종목코드 · 이름 · 시가/고가/저가/종가 · 등락률 · **NAV** · 거래량/대금 · 시가총액
저장: `data/etf-krx/{YYYYMMDD}.json`

쓰는 법:
    python scripts\collect_krx_etf.py                 # 안 받은 날을 다 받는다
    python scripts\collect_krx_etf.py --최근 400      # 최근 400일만
    python scripts\collect_krx_etf.py --확인          # 하루만 시험
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "etf-krx")
KRX = os.path.join(_BASE, "data", "krx-daily")
LOG = os.path.join(_BASE, "data", "_etfkrx.log")
_쉼 = 0.22


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 숫(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def 하루(날, key):
    u = f"https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd?basDd={날}"
    req = urllib.request.Request(u, headers={"AUTH_KEY": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    k = [x for x in d if isinstance(d[x], list)]
    rows = d[k[0]] if k else []
    out = {}
    for x in rows:
        code = str(x.get("ISU_CD") or "").strip()
        if not code:
            continue
        out[code] = {
            "이름": (x.get("ISU_NM") or "").strip(),
            "종가": 숫(x.get("TDD_CLSPRC")), "시가": 숫(x.get("TDD_OPNPRC")),
            "고가": 숫(x.get("TDD_HGPRC")), "저가": 숫(x.get("TDD_LWPRC")),
            "등락률": 숫(x.get("FLUC_RT")), "NAV": 숫(x.get("NAV")),
            "거래량": 숫(x.get("ACC_TRDVOL")), "거래대금": 숫(x.get("ACC_TRDVAL")),
            "시가총액": 숫(x.get("MKTCAP")), "지수명": (x.get("IDX_IND_NM") or "").strip(),
        }
    return out


def main():
    확인만 = "--확인" in sys.argv
    최근 = int(sys.argv[sys.argv.index("--최근") + 1]) if "--최근" in sys.argv else 0
    key = config.require("KRX_API_KEY")
    os.makedirs(OUT, exist_ok=True)
    거래일 = sorted(os.path.basename(f)[:-5]
                    for f in glob.glob(os.path.join(KRX, "*.json")))
    if not 거래일:
        찍기("  krx-daily가 비었다.")
        return 1
    받 = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(OUT, "*.json"))}
    할것 = [d for d in 거래일 if d not in 받]
    if 최근:
        할것 = 할것[-최근:]
    if 확인만:
        할것 = 할것[-1:]
    찍기("===== 국내 ETF 수집 (KRX etp/etf_bydd_trd) =====")
    찍기(f"  거래일 {len(거래일):,} · 이미 받은 것 {len(받):,} · 할 것 {len(할것):,}일"
         f" · 예상 {len(할것)*(_쉼+0.35)/60:.0f}분")
    ok = 빈 = 실패 = 0
    for i, 날 in enumerate(할것, 1):
        try:
            표 = 하루(날, key)
        except urllib.error.HTTPError as e:
            실패 += 1
            if 실패 <= 3:
                찍기(f"  ⚠️ {날} HTTP {e.code}")
            # ⚠️ 401이면 승인이 풀린 것이다 — 계속 두드려도 소용없다
            if e.code in (401, 403):
                찍기("  ⚠️⚠️ 권한 오류 — 멈춘다. KRX 승인 상태를 확인해야 한다")
                break
            time.sleep(1.0)
            continue
        except Exception as e:
            실패 += 1
            if 실패 <= 3:
                찍기(f"  ⚠️ {날} {type(e).__name__}")
            time.sleep(1.0)
            continue
        if 표:
            io.open(os.path.join(OUT, 날 + ".json"), "w",
                    encoding="utf-8").write(json.dumps(
                        {"기준일": 날, "종목수": len(표), "종목": 표},
                        ensure_ascii=False))
            ok += 1
        else:
            빈 += 1
        time.sleep(_쉼)
        if i % 200 == 0:
            찍기(f"    {i}/{len(할것)} · 받음 {ok:,} · 빈 날 {빈} · 실패 {실패}")
    찍기(f"  끝 · 받음 {ok:,}일 · 빈 날 {빈} · 실패 {실패}")
    g = sorted(glob.glob(os.path.join(OUT, "*.json")))
    if g:
        찍기(f"  현재 {len(g):,}일 · {os.path.basename(g[0])[:-5]} ~ "
             f"{os.path.basename(g[-1])[:-5]}")
    if 확인만 and g:
        d = json.load(io.open(g[-1], encoding="utf-8-sig"))
        찍기(f"  시험: {d['기준일']} · {d['종목수']}종목")
        for c, v in list(d["종목"].items())[:3]:
            찍기(f"    {c} {v['이름'][:24]:24} 종가 {v['종가']} · NAV {v['NAV']}"
                 f" · 지수 {v['지수명'][:20]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
