#!/usr/bin/env python3
r"""
etf_lab.py — **「품질 필터 인덱스」 ETF가 실제로 코스피를 이겼나** (2026-09-02 · 6차)

⚠️⚠️ **이름만 보고 고르면 안 된다.** 「우량」·「퀄리티」·「멀티팩터」라는 이름을 달았다고
   실제로 인덱스를 이겼다는 뜻이 아니다. **숫자로 판정한다.**

⚠️⚠️ **NAV가 아니라 종가로 잰다.** 실제로 사고파는 가격이 종가이기 때문이다.
   ⚠️ 다만 **분배금(배당)이 빠진다** — 고배당 ETF는 실제보다 나쁘게 나온다.
      `TR`(Total Return)이 이름에 붙은 것은 분배금을 재투자하므로 그 왜곡이 없다.

**비교 기준**: `KODEX 200`(코스피200 ETF, 거래대금 2.4조 — 사실상 표준)

⚠️ **거래대금을 반드시 같이 본다.** 팩터 ETF는 대부분 하루 0~5억이라
   실제로 사고팔 때 호가가 벌어지고, **상장폐지 위험**도 있다.

쓰는 법:
    python scripts\etf_lab.py
"""
import io
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import omni_lab as O  # noqa: E402

API = "https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd"
CACHE = os.path.join(O._DATA, "etf-daily")


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def 하루(날, key):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, 날 + ".json")
    if os.path.exists(p):
        try:
            return json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:
            pass
    r = urllib.request.Request(f"{API}?basDd={날}", headers={"AUTH_KEY": key})
    rows = json.loads(urllib.request.urlopen(r, timeout=30).read()).get("OutBlock_1") or []
    표 = {}
    for x in rows:
        c = x.get("ISU_CD")
        if not c:
            continue
        표[c] = {"이름": x.get("ISU_NM"), "종가": _n(x.get("TDD_CLSPRC")),
                 "거래대금": _n(x.get("ACC_TRDVAL"))}
    io.open(p, "w", encoding="utf-8").write(json.dumps(표, ensure_ascii=False))
    time.sleep(0.15)
    return 표


def main():
    key = config.get("KRX_API_KEY")
    지수 = O._지수()
    날 = sorted(지수)
    # 분기 첫 거래일만 받는다 (성적 비교엔 충분하고 호출이 1/60로 준다)
    점 = []
    본 = None
    for d in 날:
        분 = (d[:4], (int(d[4:6]) - 1) // 3)
        if 분 != 본:
            점.append(d)
            본 = 분
    점 = [d for d in 점 if d >= "20120101"]
    print(f"  분기 시점 {len(점)}개 ({점[0]} ~ {점[-1]}) 받는 중...", flush=True)
    표 = {}
    for i, d in enumerate(점, 1):
        try:
            표[d] = 하루(d, key)
        except Exception:
            pass
        if i % 20 == 0:
            print(f"    {i}/{len(점)}", flush=True)
    점 = [d for d in 점 if 표.get(d)]
    print(f"  받음 {len(점)}개 시점\n", flush=True)

    # 기준: KODEX 200
    def 찾(이름조각, d):
        for c, v in (표.get(d) or {}).items():
            if v["이름"] and 이름조각 == v["이름"].strip():
                return c, v
        return None, None

    후보이름 = [
        "KODEX 200", "TIGER 200", "KODEX 코스피",
        "KODEX 우량주", "TIGER 우량가치", "KODEX 200가치저변동",
        "KODEX 멀티팩터", "TIGER 로우볼", "PLUS 고배당주", "KODEX 고배당주",
        "KODEX 200TR", "KODEX 배당가치", "TIGER 배당성장",
        "KODEX 200ESG", "RISE ESG사회책임투자", "PLUS 중형주저변동50",
        "KODEX 코리아밸류업", "TIGER 코리아밸류업",
    ]
    print(f"  {'ETF':<26}{'시작':<9}{'끝':<9}{'배수':>8}{'연환산':>9}"
          f"{'코스피200 대비':>14}{'하루거래대금':>13}")
    기준 = {}
    줄 = []
    for 이름 in 후보이름:
        있 = [d for d in 점 if 찾(이름, d)[0]]
        if len(있) < 8:                     # 2년 미만이면 판정 불가
            줄.append((None, 이름, len(있)))
            continue
        시, 끝 = 있[0], 있[-1]
        _, v1 = 찾(이름, 시)
        _, v2 = 찾(이름, 끝)
        if not v1 or not v2 or not v1["종가"] or not v2["종가"]:
            줄.append((None, 이름, len(있)))
            continue
        배 = v2["종가"] / v1["종가"]
        년 = (int(끝[:4]) * 12 + int(끝[4:6]) - int(시[:4]) * 12 - int(시[4:6])) / 12
        if 년 <= 0:
            continue
        연 = (배 ** (1 / 년) - 1) * 100
        # 같은 구간 KODEX 200
        k1 = 찾("KODEX 200", 시)[1]
        k2 = 찾("KODEX 200", 끝)[1]
        기 = None
        if k1 and k2 and k1["종가"]:
            기 = ((k2["종가"] / k1["종가"]) ** (1 / 년) - 1) * 100
        대금 = v2["거래대금"] or 0
        줄.append((연 - 기 if 기 is not None else None, 이름, (시, 끝, 배, 연, 기, 대금, len(있))))
    for 초, 이름, 정보 in sorted(줄, key=lambda x: (x[0] is None, -(x[0] or 0))):
        if isinstance(정보, int) or 정보 is None:
            print(f"  {이름:<26}자료 부족 ({정보}분기)")
            continue
        시, 끝, 배, 연, 기, 대금, n = 정보
        표시 = "⭐" if (초 or 0) > 0 else "  "
        초s = f"{초:+.1f}%" if 초 is not None else "-"
        print(f"  {이름:<26}{시[:6]:<9}{끝[:6]:<9}{배:>8.3f}{연:>8.1f}%"
              f"{초s:>14}{대금/1e8:>11,.0f}억{표시}")
    print("\n  읽는 법")
    print("    - '코스피200 대비'가 양수여야 인덱스보다 나은 것이다")
    print("    - ⚠️ 종가 기준이라 **분배금(배당)이 빠져 있다**. 고배당 ETF는 실제보다 나쁘게 나온다")
    print("      (이름에 TR이 붙은 것은 분배금 재투자라 왜곡이 없다)")
    print("    - ⚠️ 하루 거래대금이 작으면 사고팔 때 손해를 보고, 상장폐지 위험도 있다")
    print("    - 상장 시점이 다르면 비교 구간도 다르다. '시작' 열을 같이 볼 것")
    return 0


if __name__ == "__main__":
    sys.exit(main())
