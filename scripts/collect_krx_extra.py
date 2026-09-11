#!/usr/bin/env python3
r"""
collect_krx_extra.py — **선물·유가·금·국고채를 받는다 (승인됐을 때만)** (2026-09-01 신설)

⚠️⚠️ **승인 여부를 스스로 확인한다.** 401(권한 없음)이면 **조용히 넘어간다.**
   사용자가 언제 승인받을지 모르기 때문이다 — 2026-09-01 상황:
   *"퇴근하고 집에 가서 신청하면 IP 다르니까 승인 받을 수 있지 않아?"*
   맞다. 차단된 건 `data.krx.co.kr`(웹 포털)이고 **신청은 `openapi.krx.co.kr`,
   받는 건 `data-dbg.krx.co.kr`**이라 셋이 다른 곳이다. `AUTH_KEY`는 계정 기반이라
   집에서 승인받으면 **회사 PC에서 그대로 먹는다.**

**받는 것** (승인 필요한 서비스 3개)
```
drv  파생상품   ⭐ 코스피200 선물 — 베이시스로 시장 방향
gen  일반상품   🔸 유가·금
bon  채권      🔸 국고채 금리
```

⚠️ 이어받는다. 이미 받은 날은 건너뛴다.
⚠️ **KRX 웹 포털은 절대 두드리지 않는다** — OpenAPI(`data-dbg`)만 쓴다.

저장: `data/krx-extra/{서비스}/{YYYYMMDD}.json`

쓰는 법:
    python scripts\collect_krx_extra.py
    python scripts\collect_krx_extra.py --확인    # 승인됐는지만 본다
"""
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
_DATA = os.path.join(_BASE, "data")
KRX = os.path.join(_DATA, "krx-daily")
OUTB = os.path.join(_DATA, "krx-extra")
LOG = os.path.join(_DATA, "_krxextra.log")
API = "https://data-dbg.krx.co.kr/svc/apis"

# (이름, 서비스, 엔드포인트들)
서비스 = [
    ("선물",   "drv", ["fut_bydd_trd"]),
    ("옵션",   "drv", ["opt_bydd_trd"]),
    # ⭐ 2026-09-07 추가 — 사용자가 「주식선물(유가)」를 신청해 승인받았다.
    #    미결제약정(ACC_OPNINT_QTY)과 베이시스(SPOT_PRC vs TDD_CLSPRC)를 재려는 것.
    #    ⚠️ 기초자산은 유가 210 + 코스닥 74 = 284종목이다. 전 종목이 아니다
    ("주식선물유가", "drv", ["eqsfu_stk_bydd_trd"]),
    ("주식선물코스닥", "drv", ["eqkfu_ksq_bydd_trd"]),
    ("일반상품", "gen", ["oil_bydd_trd", "gold_bydd_trd"]),
    ("국고채", "bon", ["kts_bydd_trd"]),
]
_쉼 = 0.15


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def 한번(svc, ep, 날, key):
    r = urllib.request.Request(f"{API}/{svc}/{ep}?basDd={날}", headers={"AUTH_KEY": key})
    with urllib.request.urlopen(r, timeout=30) as res:
        return json.loads(res.read()).get("OutBlock_1") or []


def 승인됐나(svc, ep, 날, key):
    """200이면 True · 401이면 False · 그 밖의 오류는 None(알 수 없음)."""
    try:
        한번(svc, ep, 날, key)
        return True
    except urllib.error.HTTPError as e:
        return False if e.code in (401, 403) else None
    except Exception:
        return None


def main():
    확인만 = "--확인" in sys.argv
    key = config.get("KRX_API_KEY")
    거래일 = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(KRX, "*.json")))
    if not 거래일:
        찍기("  krx-daily가 비었다.")
        return 1
    최근 = 거래일[-1]

    찍기(f"===== KRX 추가 서비스 · 승인 확인 ({최근} 기준) =====")
    열린것 = []
    for 이름, svc, eps in 서비스:
        상태 = 승인됐나(svc, eps[0], 최근, key)
        말 = {True: "✅ 승인됨", False: "🔒 아직 승인 안 됨", None: "⚠️ 알 수 없음"}[상태]
        찍기(f"  {이름:8s} {svc}/{eps[0]:16s} {말}")
        if 상태:
            열린것.append((이름, svc, eps))
    if 확인만:
        return 0
    if not 열린것:
        찍기("  승인된 서비스가 없다 — 아무것도 받지 않는다. (신청 후 다시 돌리면 된다)")
        return 0

    for 이름, svc, eps in 열린것:
        OUT = os.path.join(OUTB, 이름)
        os.makedirs(OUT, exist_ok=True)
        받 = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(OUT, "*.json"))}
        할것 = [d for d in 거래일 if d not in 받]
        찍기(f"  [{이름}] 받을 날 {len(할것)}일 · 예상 {len(할것)*len(eps)*(_쉼+0.25)/60:.0f}분")
        ok = 빈 = 0
        for i, 날 in enumerate(할것, 1):
            표 = {}
            for ep in eps:
                try:
                    표[ep] = 한번(svc, ep, 날, key)
                except Exception:
                    표[ep] = []
                time.sleep(_쉼)
            if any(표.values()):
                io.open(os.path.join(OUT, 날 + ".json"), "w", encoding="utf-8").write(
                    json.dumps({"기준일": 날, "자료": 표}, ensure_ascii=False))
                ok += 1
            else:
                빈 += 1
            if i % 100 == 0:
                찍기(f"    {i}/{len(할것)} — 받음 {ok} 빈날 {빈}")
        찍기(f"  [{이름}] 끝 — 받음 {ok}일 · 빈날 {빈}일")
    찍기("===== 끝 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
