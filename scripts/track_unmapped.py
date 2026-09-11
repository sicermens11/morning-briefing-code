#!/usr/bin/env python3
# ⚠️ 아래 docstring은 반드시 r"""(raw)로 둔다. 본문에 `data\unmapped-log.jsonl` 같은 윈도 경로가
#    들어 있어서, 일반 문자열이면 `\u`가 유니코드 이스케이프로 해석돼 **파일 전체가 SyntaxError**가 된다
#    (2026-08-26에 실제로 겪었다. 에러는 2번째 줄을 가리키는데 원인은 한참 아래 줄이라 찾기 어렵다).
r"""
track_unmapped.py — 가치사슬맵 밖 후보의 반복 등장을 집계한다 (2026-08-26 신설)

풀려는 문제:
  브리핑은 매일 "이건 가치사슬맵에 없어서 정식 후보로 안 올린다"는 종목·섹터를 만난다.
  그런데 그 사실이 **일일 로그에 산문으로만** 남아서, 같은 이야기가 며칠이고 반복돼도
  아무도 세지 않았다. 실제로 **해운이 2026-08-19부터 7거래일 연속** 미매핑으로 기록됐는데,
  그 "7거래일 연속"이 문장 안에 묻혀 있었다. 그게 정확히 "맵에 넣어라"는 신호다.

  등장 횟수와 연속 일수를 계산해주면 가치사슬맵 갱신이 **감이 아니라 근거**로 바뀐다.

⚠️ 판정은 하지 않는다. "몇 번 나왔나"만 센다. 맵에 넣을지 말지는 사람과
   `value-chain-map-updater`가 정한다 — 등장 횟수가 곧 편입 조건은 아니다.

사용:
    run-py.ps1 -Script track_unmapped.py -Args @('--report')
    run-py.ps1 -Script track_unmapped.py -Args @('--report','--min-days','3')
    run-py.ps1 -Script track_unmapped.py -Args @('--backfill')   # 마크다운 로그에서 1회 복원

데이터: `data\unmapped-log.jsonl` (append_log.py가 브리핑 payload의 `unmapped`를 받아 씀)
"""
import json
import os
import re
import sys

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
UNMAPPED_PATH = os.path.join(_DATA, "unmapped-log.jsonl")
MD_LOG = os.path.join(_DATA, "briefing-daily-log.md")
MAP_PATH = os.path.join(_DATA, "value-chain-map.md")

# 백필이 산문에서 긁어오다 보니 이름 자리에 들어온 비-이름들. 집계에서 뺀다.
# (2026-08-13 기록의 "미확인(스크린샷 범위 밖)"이 종목명처럼 잡혀 있었다.)
NON_NAMES = {"미확인", "없음", "해당없음", "해당 없음", "N/A", "-"}


def load_rows():
    if not os.path.exists(UNMAPPED_PATH):
        return []
    out = []
    # ⚠️ utf-8-sig. PowerShell로 이 파일을 한 번이라도 손대면 BOM이 붙는데, 그냥 utf-8로 읽으면
    #    **첫 줄만 조용히 파싱 실패**한다(에러가 안 난다 — 아래 except가 삼킨다).
    #    그러면 백필의 중복 검사에서 그 줄이 "없는 것"이 돼 같은 항목이 다시 들어온다.
    #    2026-08-26에 실제로 07-29 냉방주가 이렇게 두 줄이 됐다.
    with open(UNMAPPED_PATH, "r", encoding="utf-8-sig") as fp:
        for line in fp:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def map_text():
    try:
        with open(MAP_PATH, "r", encoding="utf-8") as fp:
            return fp.read()
    except Exception:
        return ""


def backfill():
    """일일 로그 마크다운의 `미매핑테마후보:` 줄에서 과거 기록을 복원한다.

    ⚠️ 산문을 기계적으로 자른 것이라 정확하지 않을 수 있어 `backfilled: true`로 표시한다.
       구조화 기록은 2026-08-26부터라, 그 이전 연속 일수를 잃지 않으려고 한 번만 돌린다.
    """
    if not os.path.exists(MD_LOG):
        return {"ok": False, "error": "일일 로그 마크다운 없음"}
    date, rows, seen = None, [], set()
    with open(MD_LOG, "r", encoding="utf-8") as fp:
        for line in fp:
            m = re.match(r"^##\s*(\d{4}-\d{2}-\d{2})", line)
            if m:
                date = m.group(1)
                continue
            if not date or not line.startswith("미매핑테마후보:"):
                continue
            body = line.split(":", 1)[1].strip()
            if body.startswith("없음"):
                continue
            for chunk in body.split(" / "):
                # "해운(업종랭킹 2위...)" → 이름은 첫 괄호 앞까지
                name = chunk.split("(")[0].strip().rstrip(".").strip()
                if not name or len(name) > 40:
                    continue
                key = (date, name)
                if key in seen:
                    continue
                seen.add(key)
                codes = re.findall(r"\b(\d{6})\b", chunk)
                rows.append({"date": date, "name": name, "kind": "미분류",
                             "codes": codes, "why": chunk[:200], "backfilled": True})
    existing = load_rows()
    have = {(r.get("date"), r.get("name")) for r in existing}
    fresh = [r for r in rows if (r["date"], r["name"]) not in have]
    with open(UNMAPPED_PATH, "a", encoding="utf-8") as fp:
        for r in fresh:
            fp.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return {"ok": True, "added": len(fresh), "skipped_existing": len(rows) - len(fresh),
            "path": UNMAPPED_PATH}


def report(min_days: int):
    rows = load_rows()
    if not rows:
        return {"ok": True, "총건수": 0, "후보": [], "_안내": "누적 기록이 아직 없다"}

    all_dates = sorted({r["date"] for r in rows})
    mtext = map_text()

    agg = {}
    for r in rows:
        nm = r.get("name")
        if not nm:
            continue
        a = agg.setdefault(nm, {"이름": nm, "날짜": set(), "코드": set(),
                                "종류": r.get("kind") or "미분류", "사유": ""})
        a["날짜"].add(r["date"])
        for c in r.get("codes") or []:
            a["코드"].add(c)
        if r.get("why"):
            a["사유"] = r["why"][:160]   # 가장 최근 줄의 사유가 남는다

    out = []
    for a in agg.values():
        if a["이름"] in NON_NAMES:
            continue
        ds = sorted(a["날짜"])
        # 연속 일수는 **브리핑이 실제로 돈 날(all_dates) 기준**으로 센다. 휴장일 계산이 필요 없다.
        # ⚠️ 두 가지를 따로 낸다. `연속일수`(지금도 이어지는 중)만 내면, 어제까지 5일 연속이던
        #    항목이 오늘 하루 빠졌다는 이유로 **0으로 보이고 사라진다** — 2026-08-26 해운이 그랬다.
        cur, i = 0, len(all_dates) - 1
        while i >= 0 and all_dates[i] in a["날짜"]:
            cur += 1
            i -= 1
        longest = run = 0
        for d in all_dates:
            run = run + 1 if d in a["날짜"] else 0
            longest = max(longest, run)
        # 이미 맵에 있으면 후보에서 뺀다 — 반영이 끝난 항목이다.
        # ⚠️ 단순 문자열 포함 검사라 **힌트일 뿐 확정이 아니다**(짧거나 흔한 이름은 오탐 가능).
        in_map = bool(len(a["이름"]) >= 2 and a["이름"] in mtext) or \
            any(c in mtext for c in a["코드"])
        out.append({
            "이름": a["이름"], "종류": a["종류"],
            "등장일수": len(ds), "최초": ds[0], "최근": ds[-1],
            "연속일수": cur, "최장연속": longest, "코드": sorted(a["코드"]),
            "맵등재": in_map, "사유": a["사유"],
        })

    out.sort(key=lambda x: (-x["등장일수"], -x["최장연속"], x["최초"]))
    pending = [o for o in out if not o["맵등재"] and o["등장일수"] >= min_days]
    return {
        "ok": True,
        "집계기준일수": len(all_dates),
        "기간": f"{all_dates[0]}~{all_dates[-1]}",
        "총건수": len(rows),
        "검토대상": pending,          # 맵 미등재 + 기준 이상 반복
        "전체": out,
        "_판정없음": "등장 횟수만 센다. 맵 편입 여부는 value-chain-map-updater와 사람이 정한다.",
    }


def main():
    argv = sys.argv[1:]
    # ⚠️ 알 수 없는 인자는 **조용히 무시하지 않는다.** `--report`가 기본 동작이라
    #    오타(`--reprot`)를 쳐도 리포트가 나와서 "먹혔다"고 착각하기 쉽다(2026-08-26 감사에서 발견).
    KNOWN = {"--report", "--backfill", "--min-days"}
    unknown = [a for a in argv if a.startswith("--") and a not in KNOWN]
    if unknown:
        print(json.dumps({"_fatal_error": f"알 수 없는 인자: {unknown} (지원: {sorted(KNOWN)})"},
                         ensure_ascii=False))
        return
    if "--backfill" in argv:
        print(json.dumps(backfill(), ensure_ascii=False))
        return
    min_days = int(argv[argv.index("--min-days") + 1]) if "--min-days" in argv else 2
    print(json.dumps(report(min_days), ensure_ascii=False))


if __name__ == "__main__":
    main()
