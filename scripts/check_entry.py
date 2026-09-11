#!/usr/bin/env python3
"""
check_entry.py — 오늘 브리핑 픽의 진입 조건을 기계적으로 판정 (2026-08-25 신설)

무엇을 하나:
  브리핑(STEP8-A)이 남긴 `briefing-daily-log.jsonl`의 오늘 항목을 읽어,
  각 픽의 `entry_conditions`(20일선·지지선 등 숫자로 명시된 조건)를 **현재가와 대조**해
  진입/보류/철회를 결론낸다. 시세는 네이버 실시간 API를 직접 호출한다(MCP 호출 0회).

왜 필요한가:
  브리핑은 이미 "20일선 26,235원 회복 확인 후"처럼 **숫자로 된 조건부 명령**을 쓰고 있는데,
  그걸 실제로 대조하는 주체가 없었다. 사용자가 직접 HTS를 열어 확인해야 했다.
  조건이 숫자로 박혀 있으므로 판단이 필요 없고 대조만 하면 된다 — 그래서 스크립트로 뺐다.

⚠️ 판정 범위를 일부러 좁게 잡았다 (09:05 실행 전제):
  개장 직후 5분은 노이즈 구간이라 "오늘 추세"·"당일 수급"은 의미가 없다.
  대신 **시가는 동시호가로 확정된 단일가**라 흔들리지 않는다. 그래서 이 스크립트는
  시가·현재가·전일종가 대비 갭률처럼 **노이즈에 영향받지 않는 값만** 본다.
  추세·수급 확인이 필요하면 그건 점심(12:20) 체크의 몫이다.

출력(stdout, JSON):
  {
    "checked_at": "...", "date": "2026-08-26",
    "results": [
      {"name","code","grade","found_price","now","open","prev_close",
       "gap_pct",            // 시초가가 전일종가 대비 몇 % (재료 반영 여부의 핵심 지표)
       "change_from_found",  // 발굴가 대비 등락
       "conditions": [{"type","value","op","actual","met":true/false}],
       "verdict": "조건충족"|"보류"|"철회검토",
       "reason": "..."}
    ]
  }

판정 규칙(단순·기계적):
  - 모든 조건 충족 → 조건충족
  - 하나라도 미충족 → 보류
  - 시초가 갭률이 +5% 이상 → 철회검토 (브리핑이 "미반영"이라던 재료가 개장에 이미 반영됨)
  - 조건이 아예 없으면 갭률만 보고 판정

⚠️ **"진입가능" → "조건충족"으로 이름을 바꿨다 (2026-08-27).**
   이 스크립트는 **매수를 권하지 않는다.** 아침 브리핑이 써둔 숫자(`entry_conditions`)가
   지금 시세로 충족됐는지 **대조만** 한다. 그런데 "진입가능"이라는 말이 매수 권고처럼 읽혔다.

   실제로 모순이 났다 — 주간 리뷰 규칙은 **"🟡점검은 관망으로 취급한다"**고 못박고 있는데,
   2026-08-27에 🟡인 디아이·유니테스트에 "진입가능"이 떴다. 같은 종목을 두고 아침엔 관망,
   09:05엔 진입가능이라고 말한 셈이다. 등급은 "기회가 얼마나 큰가"를, 이 스크립트는
   "써둔 조건이 맞았나"를 답하는데 **두 답이 같은 단어처럼 들린 것**이 원인이다.

⚠️ **옛 로그에는 "진입가능"이 그대로 남아 있다**(2026-08-25~08-27, 8건).
   집계하는 쪽에서 두 값을 **같은 것으로** 취급해야 한다. `backtest_returns.py --entry-check`가
   그렇게 처리한다.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL = os.path.join(BASE, "data", "briefing-daily-log.jsonl")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://stock.naver.com/",
    "Accept": "application/json",
}

# 시초가에 재료가 이미 반영됐다고 볼 문턱. 이 이상이면 갭 전략의 전제가 무너진 것으로 본다.
GAP_ABSORBED_PCT = 5.0


def _num(v):
    """'22,950' 같은 문자열도 숫자로."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def fetch_quote(code: str):
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    d = (data.get("datas") or [None])[0]
    if not d:
        raise ValueError("빈 응답")
    now = _num(d.get("closePrice"))
    diff = _num(d.get("compareToPreviousClosePrice"))
    return {
        "now": now,
        "open": _num(d.get("openPrice")),
        "high": _num(d.get("highPrice")),
        "low": _num(d.get("lowPrice")),
        "prev_close": (now - diff) if (now is not None and diff is not None) else None,
        "change_rate": _num(d.get("fluctuationsRatio")),
        "name": d.get("stockName"),
    }


def today_row(date_str: str):
    if not os.path.exists(JSONL):
        return None
    with open(JSONL, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("date") == date_str:
                return row
    return None


def judge(pick, q):
    """진입 조건을 현재가와 대조한다.

    ⚠️ **"조건을 안 쓴 것"과 "조건이 없는 것"은 다르다** (2026-08-25 수정).
       이전 버전은 둘을 똑같이 "조건 없음 → 조건충족"으로 처리했다. 그러면
       브리핑이 `entry_conditions`를 빠뜨렸을 때 **조건이 있는데도 "조건충족"으로
       오판**한다. 아침 브리핑이 "20일선 회복 후 진입"이라고 써놓고 JSONL에 숫자를
       안 넣으면, 09:05가 그걸 모른 채 진입 신호를 보내는 셈이다.

       - 키 자체가 없음        → 기록 누락. **자동 판정하지 않고 사람에게 넘긴다.**
       - 빈 배열 `[]`          → "조건 없음"을 명시한 것. 갭률만 보고 판정.
    """
    raw = pick.get("entry_conditions", "__MISSING__")
    field_missing = (raw == "__MISSING__" or raw is None)

    conds = []
    all_met = True
    for c in (raw if isinstance(raw, list) else []):
        target = _num(c.get("value"))
        op = c.get("op", ">=")
        actual = q["now"]
        met = None
        if target is not None and actual is not None:
            met = actual >= target if op == ">=" else actual <= target
            if not met:
                all_met = False
        else:
            all_met = False
        conds.append({"type": c.get("type"), "value": target, "op": op,
                      "actual": actual, "met": met})

    gap_pct = None
    if q["open"] is not None and q["prev_close"]:
        gap_pct = round((q["open"] - q["prev_close"]) / q["prev_close"] * 100, 2)

    # 판정 — 갭 소진이 조건 충족보다 우선한다(전제가 무너지면 조건은 의미가 없다).
    if gap_pct is not None and gap_pct >= GAP_ABSORBED_PCT:
        verdict = "철회검토"
        reason = (f"시초가가 전일종가 대비 +{gap_pct}%로 열려 재료가 이미 반영된 것으로 보인다"
                  f"(문턱 +{GAP_ABSORBED_PCT}%). 브리핑의 '미반영' 전제가 무너졌다.")
    elif field_missing:
        # ⚠️ 절대 "조건충족"으로 넘기지 않는다. 조건이 있었는지조차 모르는 상태다.
        verdict = "확인필요"
        reason = ("아침 브리핑이 진입 조건을 기록하지 않았다(entry_conditions 필드 누락). "
                  "조건이 있었는지 알 수 없으므로 자동 판정하지 않는다 — "
                  "브리핑 본문의 '진입 조건'을 직접 확인할 것.")
    elif not conds:
        verdict = "조건충족" if (gap_pct is None or gap_pct < GAP_ABSORBED_PCT) else "보류"
        reason = "브리핑이 진입 조건 없음을 명시했다. 시초가 갭도 크지 않아 브리핑 판단이 그대로 유효하다."
    elif all_met:
        verdict = "조건충족"
        reason = "명시된 진입 조건을 모두 충족했다."
    else:
        unmet = [c for c in conds if c["met"] is False]
        parts = [f'{c["type"]} {c["value"]:,.0f} {c["op"]} (현재 {c["actual"]:,.0f})'
                 for c in unmet if c["value"] is not None and c["actual"] is not None]
        verdict = "보류"
        reason = "미충족: " + (" / ".join(parts) if parts else "조건 값 확인 불가")
    return conds, gap_pct, verdict, reason, field_missing


def 호가요약(d):
    r"""호가창 원본 → **사람이 읽는 몇 개 값.** `d`는 MCP 도구 응답의 `data` 블록.

    ⚠️⚠️ **판정(`verdict`)을 바꾸지 않는다. 기록만 한다.**
       "스프레드가 몇 %면 사지 마라"는 문턱에 아직 근거가 없다. 근거 없이 문턱을 박으면
       그때부터 그 숫자가 매수를 막기 시작하고, **틀려도 틀린 줄 모른다.**
       먼저 쌓고, 표본이 차면 "스프레드가 넓은 날 실제로 손해였나"를 계산해서 정한다.
       (서술 11개를 점수에 안 넣고 `features`로만 쌓는 것과 같은 처리다.)

    ⚠️ **체결 가능성은 이 계좌 규모에선 문제가 아니다** (2026-08-28 실측).
       안랩 최우선 매도에 314주가 걸려 있었고 실제 주문은 2주였다. 백 배 넘게 여유다.
       그래서 "살 수 있나"가 아니라 **"얼마에 사게 되나"(스프레드)**만 남긴다.
       ⚠️ 주문 규모가 커지면 이 전제가 무너진다 — 그때 `최우선매도잔량`을 다시 본다.
          그래서 지금 안 쓰더라도 **값은 남겨 둔다.**
    """
    asks = d.get("asks") or []
    bids = d.get("bids") or []
    if not asks or not bids:
        return {"상태": "호가 없음(장 시작 전이거나 거래정지)"}
    a1, b1 = asks[0], bids[0]
    ap, bp = _num(a1.get("price")), _num(b1.get("price"))
    out = {
        "최우선매도": ap, "최우선매수": bp,
        "최우선매도잔량": _num(a1.get("quantity")),
        "매도잔량": _num(d.get("total_ask_qty")),
        "매수잔량": _num(d.get("total_bid_qty")),
    }
    if ap and bp and ap > 0:
        # 시장가로 사면 최우선 매수호가보다 이만큼 비싸게 산다는 뜻.
        out["스프레드pct"] = round((ap - bp) / ap * 100, 3)
    if out.get("매도잔량") and out.get("매수잔량"):
        # 1보다 크면 파는 물량이 더 두껍다. ⚠️ 방향 예측력은 **검증 안 됐다.** 기록만.
        out["매도매수잔량비"] = round(out["매도잔량"] / out["매수잔량"], 2)
    return out


def main():
    argv = sys.argv[1:]
    date_str = argv[argv.index("--date") + 1] if "--date" in argv \
        else datetime.now(KST).strftime("%Y-%m-%d")

    row = today_row(date_str)
    if not row:
        print(json.dumps({"ok": False, "date": date_str,
                          "error": f"{date_str} 항목이 briefing-daily-log.jsonl에 없다 "
                                   "(오늘 브리핑이 아직 안 돌았거나 실패)"}, ensure_ascii=False))
        return

    # ⚠️ 호가는 **파이썬이 못 가져온다.** 네이버 공개 엔드포인트에 호가가 없고
    #    (2026-08-28 4곳 확인), MCP 도구는 모델만 부를 수 있다. 그래서 스킬이 먼저
    #    도구를 불러 파일로 넘겨주고, 여기서는 **읽기만** 한다.
    #    ⚠️ 없어도 진입체크는 그대로 돌아간다 — 호가는 곁다리지 판정 근거가 아니다.
    호가맵 = {}
    if "--orderbook" in argv:
        try:
            with open(argv[argv.index("--orderbook") + 1], encoding="utf-8-sig") as fp:
                호가맵 = json.load(fp) or {}
        except Exception as e:  # noqa: BLE001
            호가맵 = {"_오류": f"{type(e).__name__}: {e}"}

    results = []
    missing_cond_picks = []   # entry_conditions를 아예 안 쓴 픽 — 상위로 알려 사람이 보게 한다
    for pick in row.get("picks") or []:
        code = pick.get("code")
        entry = {"name": pick.get("name"), "code": code, "grade": pick.get("grade"),
                 "rank": pick.get("rank"), "found_price": _num(pick.get("found_price"))}
        try:
            q = fetch_quote(code)
        except Exception as e:
            entry.update({"verdict": "확인불가", "reason": f"시세 조회 실패: {type(e).__name__}: {e}"})
            results.append(entry)
            continue

        conds, gap_pct, verdict, reason, field_missing = judge(pick, q)
        if field_missing:
            missing_cond_picks.append(pick.get("name"))
        chg = None
        if entry["found_price"] and q["now"]:
            chg = round((q["now"] - entry["found_price"]) / entry["found_price"] * 100, 2)
        entry.update({
            "now": q["now"], "open": q["open"], "prev_close": q["prev_close"],
            "gap_pct": gap_pct, "change_from_found": chg,
            "conditions": conds, "verdict": verdict, "reason": reason,
        })
        ob = 호가맵.get(code) or 호가맵.get(str(code))
        if isinstance(ob, dict):
            # 도구 응답을 통째로 넘겨도 되고 `data`만 넘겨도 되게 둘 다 받는다.
            entry["호가"] = 호가요약(ob.get("data") if "data" in ob else ob)
        results.append(entry)

    payload = {
        "ok": True,
        "checked_at": datetime.now(KST).isoformat(timespec="seconds"),
        "date": date_str,
        "results": results,
    }
    if missing_cond_picks:
        # 브리핑 쪽 기록 누락이다. 조용히 넘기면 09:05가 오판하므로 눈에 띄게 올린다.
        payload["_경고"] = {
            "진입조건_미기록": missing_cond_picks,
            "조치": ("아침 브리핑 STEP8-A가 entry_conditions를 채우지 않았다. "
                     "해당 픽은 '확인필요'로 처리했으니 카카오 본문에도 그대로 알리고, "
                     "브리핑 본문의 진입 조건을 사람이 직접 보게 할 것."),
        }

    # --save: 결과를 별도 JSONL에 append 한다.
    #   백테스트 표본을 매일 쌓기 위한 것이다. 시초가·시초갭·발굴가 대비 등락을 남겨두면
    #   나중에 "어떤 갭 조합이 실제로 맞았나"를 D+1 지평에서 계산할 수 있다.
    #   (매일 찍어두면 지평은 나중에 고를 수 있지만, 안 쌓으면 영원히 복원 못 한다.)
    #   같은 (date, slot) 조합은 교체한다 — 09:05·12:20을 하루에 각각 한 번씩만 남긴다.
    if "--save" in argv:
        slot = argv[argv.index("--slot") + 1] if "--slot" in argv else "0905"
        path = os.path.join(BASE, "data", "entry-check-log.jsonl")
        rec = dict(payload)
        rec["slot"] = slot
        keep = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.rstrip("\n")
                    if not line.strip():
                        continue
                    try:
                        o = json.loads(line)
                        if o.get("date") == date_str and o.get("slot") == slot:
                            continue  # 같은 날 같은 슬롯은 교체
                    except Exception:
                        pass  # 깨진 줄도 버리지 않는다
                    keep.append(line)
        keep.append(json.dumps(rec, ensure_ascii=False, sort_keys=True))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fp:
            for l in keep:
                fp.write(l + "\n")
        payload["saved_to"] = path
        payload["slot"] = slot

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
