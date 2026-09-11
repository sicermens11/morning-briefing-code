#!/usr/bin/env python3
r"""collect_flow.py — **전 종목 투자자별 수급을 쌓는다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 2026-09-01 전 종목 검증에서 **갭③(외국인·기관 순매수)만 못 쟀다.**
   KRX OpenAPI에 투자자별 자료가 **없고**(404), 정보데이터시스템은 400으로 막히고,
   네이버는 종목별이라 과거 648일 × 2,766종목 = 180만 호출이 필요해 불가능했다.
   ⇒ **과거는 못 받는다. 대신 오늘부터 쌓는다.**

⚠️⚠️ **과거도 받을 수 있다** (2026-09-01 발견). 네이버 `trend` API가 **`?bizdate=YYYYMMDD`**를
   받는다 — 그 날짜 **직전 10거래일**을 돌려준다. 사용자 지적: *"10일치씩 과거로 60번 정도
   수집하면 되는 거 아니야?"* 맞다. **종목당 65회 × 2,766종목 = 약 18만 호출**이면 2년치가 된다.
   ⚠️ 이건 **네이버에 보내는 HTTP 요청**이라 **클로드 토큰과 무관하다.** 제약은 시간과 차단이다.

⚠️ **`수급10일`이 열흘치를 한 번에 준다.** 그래서 **열흘에 한 번만 받으면 연속 자료**가 된다.
   전 종목 2,766개에 약 26분. 열흘에 한 번이면 하루 평균 2.6분이다.
   ⚠️ **열흘을 넘기면 구멍이 난다.** 주 1회(예: 매주 금요일)로 돌리면 안전하다.

⚠️ 받은 자료는 `data/flow-daily/{기준일}.json`에 **날짜별로 쪼개서** 쌓는다
   (그래야 `krx-daily`와 같은 방식으로 실험에 붙는다).

⚠️ **이 자료가 쌓이면 무엇을 할 수 있나**: 갭③을 전 종목으로 검증한다 —
   "외국인·기관이 둘 다 사는 종목이 실제로 시장보다 오르나". 지금은 **표본이 19건뿐**이라
   백테스트에서 갭③이 최악(+0.16%p n=7)으로 나왔는데 그걸 믿을 수 없는 상태다.

쓰는 법:
    python scripts\collect_flow.py              # 전 종목
    python scripts\collect_flow.py --limit 200  # 시총 상위 200개만(시험용)
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_stock as _FS  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_OUT = os.path.join(_DATA, "flow-daily")


def _대상(limit=None):
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    if not fs:
        return []
    with io.open(fs[-1], encoding="utf-8-sig") as fp:
        종 = json.load(fp).get("종목") or {}
    쌍 = sorted(종.items(), key=lambda kv: -float(kv[1].get("시총") or 0))
    if limit:
        쌍 = 쌍[:limit]
    return [c for c, _ in 쌍]


def _숫자(s):
    try:
        return int(str(s).replace(",", "").replace("+", ""))
    except (TypeError, ValueError):
        return None


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    # ⚠️ `--bizdate YYYYMMDD` — 그 날짜 **직전 10거래일**을 받는다(과거 채우기용).
    기준일 = sys.argv[sys.argv.index("--bizdate") + 1] if "--bizdate" in sys.argv else None
    codes = _대상(limit)
    if not codes:
        print(json.dumps({"ok": False, "이유": "krx-daily가 비었다"}, ensure_ascii=False))
        return 1
    os.makedirs(_OUT, exist_ok=True)
    모음 = {}          # {기준일: {코드: {외국인, 기관, 개인, 지분율}}}
    실패 = 0
    for i in range(0, len(codes), 10):
        덩 = codes[i:i + 10]
        # ⚠️ **하위 프로세스로 부르지 않는다.** 윈도 기본 인코딩(cp949)이 한글 출력을 깨뜨려
        #    2026-09-01에 200종목이 통째로 실패했다. 모듈을 직접 부른다.
        try:
            if 기준일:
                # ⚠️ 과거 구간: `trend` API를 직접 부른다(`fetch_one`은 최근 10일만 준다).
                d = {}
                for c in 덩:
                    rows = _FS.get(f"https://m.stock.naver.com/api/stock/{c}/trend"
                                   f"?bizdate={기준일}")
                    d[c] = {"수급10일": [{
                        "거래일": r.get("bizdate"),
                        "외국인순매수수량": r.get("foreignerPureBuyQuant"),
                        "기관순매수수량": r.get("organPureBuyQuant"),
                        "개인순매수수량": r.get("individualPureBuyQuant"),
                        # ⚠️ 2026-09-01: **이미 오던 값인데 버리고 있었다.**
                        #    강화항목 「외국인지분율추이」의 재료다.
                        "외국인지분율": r.get("foreignerHoldRatio"),
                        "종가": r.get("closePrice"),
                    } for r in (rows or [])]}
            else:
                d = {c: _FS.fetch_one(c) for c in 덩}
        except Exception:
            실패 += len(덩)
            continue
        for code, v in d.items():
            for row in (v.get("수급10일") or []):
                일 = row.get("거래일")
                if not 일:
                    continue
                모음.setdefault(일, {})[code] = {
                    "외국인": _숫자(row.get("외국인순매수수량")),
                    "기관": _숫자(row.get("기관순매수수량")),
                    "개인": _숫자(row.get("개인순매수수량")),
                    "외국인지분율": row.get("외국인지분율"),
                    "종가": _숫자(row.get("종가")),
                }
        if (i // 10) % 50 == 0:
            print(f"  {i}/{len(codes)} — 모은 날 {len(모음)}", flush=True)
    # ⚠️ 이미 있는 날은 **덮어쓰지 않고 합친다.** 같은 날을 여러 번 받아도 종목이 늘어난다.
    쓴날 = 0
    for 일, 표 in 모음.items():
        p = os.path.join(_OUT, f"{일}.json")
        기존 = {}
        if os.path.exists(p):
            try:
                with io.open(p, encoding="utf-8-sig") as fp:
                    기존 = json.load(fp).get("종목") or {}
            except (OSError, ValueError):
                기존 = {}
        기존.update(표)
        with io.open(p, "w", encoding="utf-8") as fp:
            json.dump({"기준일": 일, "종목수": len(기존), "종목": 기존}, fp, ensure_ascii=False)
        쓴날 += 1
    print(json.dumps({"ok": True, "종목": len(codes), "실패": 실패,
                      "쌓은날": 쓴날, "폴더": _OUT}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
