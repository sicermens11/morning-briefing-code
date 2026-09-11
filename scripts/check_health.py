#!/usr/bin/env python3
# ⚠️ docstring은 r"""(raw). 윈도 경로의 `\u`가 유니코드 이스케이프로 해석되면 파일 전체가 깨진다.
r"""
check_health.py — 브리핑 실행 건강도 추적 (2026-08-26 신설)

무엇을 보나: **반복되는 실패**와 **비용·시간 추이**.

왜 필요한가 — 매일 실행 로그에 `_실패항목`이 남는데 **아무도 모아 보지 않았다.**
그래서 같은 실패가 며칠씩 반복돼도 알아채지 못했다. 실제 사례:
  - 임시파일 이름 충돌이 **매일** 나고 있었는데, 모델이 매번 새 이름을 지어내 우회해서
    로그엔 1건처럼 보였다(2026-08-26에 임시 폴더를 열어보고서야 발견).
  - `list_drafts` 응답 초과가 **이틀 연속** 검증을 무력화했다.
둘 다 "하루치만 보면 사소해 보이는데 며칠을 겹쳐 보면 명백한" 종류다.

⚠️ **판정하지 않는다.** 세기만 한다. 무엇을 고칠지는 사람이 정한다.

데이터 출처 둘:
  ① `data\briefing-daily-log.jsonl`의 `errors` 배열 — 구조화돼 있어 이쪽이 낫다
  ② `run-logs\briefing_*.log` — 턴·토큰·비용·소요시간

사용:
    run-py.ps1 -Script check_health.py -Args @('--report')
    run-py.ps1 -Script check_health.py -Args @('--report','--days','14')
"""
import io
import json
import os
import re
import sys
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL = os.path.join(_ROOT, "data", "briefing-daily-log.jsonl")
RUNLOGS = os.path.join(_ROOT, "run-logs")

# 실패 문구를 유형으로 묶는 규칙. **하나도 안 걸리면 `기타`**로 두고 원문을 남긴다 —
# 억지로 분류하면 없는 패턴이 생긴다.
PATTERNS = [
    ("임시파일_충돌", r"File has not been read|잔재파일|파일명.*우회"),
    ("응답크기_초과", r"초과|too large|토큰 상한|96,?\d{3}|143,?\d{3}"),
    ("도구_타임아웃", r"TIMEOUT|타임아웃|CRAWL_LIVECRAWL"),
    ("도구_파싱오류", r"unparsedToolInput|파싱오류|파싱 실패"),
    ("데이터_stale", r"stale|낡[은음]|기준일 불명"),
    ("지수_이상값", r"change.*0 ?비정상|비정상 반환"),
    ("등록_실패", r"register_watchlist|등록실패|등록 실패"),
    ("조회_실패", r"조회 ?실패|데이터 ?미확인|미확인으로"),
]


def classify(text: str) -> str:
    for name, pat in PATTERNS:
        if re.search(pat, text, re.I):
            return name
    return "기타"


def from_jsonl(days: int):
    if not os.path.exists(JSONL):
        return [], []
    rows = []
    with io.open(JSONL, encoding="utf-8-sig") as fp:
        for line in fp:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    rows.sort(key=lambda r: r.get("date", ""))
    rows = rows[-days:]
    items = []
    for r in rows:
        for e in (r.get("errors") or []):
            t = e if isinstance(e, str) else json.dumps(e, ensure_ascii=False)
            items.append({"date": r.get("date"), "유형": classify(t), "원문": t[:220]})
    return rows, items


def from_runlogs(days: int):
    """런처 로그에서 턴·토큰·시간. ⚠️ 형식이 바뀐 적이 있어 **못 읽는 줄은 건너뛴다.**"""
    if not os.path.isdir(RUNLOGS):
        return []
    files = sorted(f for f in os.listdir(RUNLOGS) if f.startswith("briefing_") and f.endswith(".log"))
    out = []
    for f in files[-days:]:
        try:
            t = io.open(os.path.join(RUNLOGS, f), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        rec = {"파일": f, "날짜": f[9:19]}
        m = re.search(r"소요 ([\d.]+)분", t)
        if m:
            rec["소요분"] = float(m.group(1))
        m = re.search(r"턴 ([\d,]+).*?캐시읽기 ([\d,]+).*?캐시생성 ([\d,]+).*?출력 ([\d,]+)", t, re.S)
        if m:
            g = [int(x.replace(",", "")) for x in m.groups()]
            rec.update({"턴": g[0], "캐시읽기": g[1], "캐시생성": g[2], "출력": g[3]})
            # Opus 5 환산(캐시읽기 $0.5 · 캐시생성 $6.25 · 출력 $25 / 1M)
            rec["추정비용USD"] = round(g[1] / 1e6 * 0.5 + g[2] / 1e6 * 6.25 + g[3] / 1e6 * 25, 2)
        m = re.search(r"MCP 호출수\*{0,2}\s*—?\s*수집 (\d+)", t)
        if m:
            rec["MCP수집"] = int(m.group(1))
        out.append(rec)
    return out


def _수정시각(path):
    import datetime
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")


def 갈라진파일():
    r"""**옛 폴더에 같은 이름의 데이터 파일이 남아 있나** (2026-09-01 신설).

    ⚠️ 왜 필요한가 — 2026-08-25에 예약 작업의 **런처 경로만** 옛 폴더에서 이 폴더로
       옮기고 **데이터는 안 옮겼다.** 그래서 일주일 넘게 두 벌이 각자 자랐다:
         · backtest-track-record.md   프로젝트 24일 / 옛 폴더 28일
         · weekly-review-history.md   프로젝트 7주  / 옛 폴더 8주
         · value-chain-map.md         프로젝트 14섹터 / 옛 폴더 13섹터(살아있는 종목 6개 누락)
       **아무 오류도 안 났다.** 사용자가 "가치사슬맵 카톡이 왜 오지?"라고 묻지 않았으면
       계속 벌어졌을 것이다.

    ⚠️ **"낡았나"는 알기 어렵지만 "같은 파일이 두 개인가"는 한 줄로 안다.**
       그래서 내용을 비교하지 않고 **존재 여부와 수정 시각만** 본다. 판정은 사람이 한다.
    """
    옛 = os.path.join(os.path.dirname(_ROOT), "Templates")
    감시 = ["value-chain-map.md", "backtest-track-record.md",
            "weekly-review-history.md", "briefing-daily-log.md"]
    out = []
    for n in 감시:
        a = os.path.join(옛, n)
        b = os.path.join(_ROOT, "data", n)
        if not os.path.exists(a):
            continue
        rec = {"파일": n, "프로젝트에도있나": os.path.exists(b)}
        try:
            rec["옛폴더수정"] = _수정시각(a)
            if os.path.exists(b):
                rec["프로젝트수정"] = _수정시각(b)
                rec["⚠️옛것이더새것"] = rec["옛폴더수정"] > rec["프로젝트수정"]
        except OSError:
            pass
        out.append(rec)
    return out


def main():
    argv = sys.argv[1:]
    # ⚠️ 알 수 없는 인자는 **조용히 무시하지 않는다.** `--report`가 기본 동작이라
    #    오타(`--reprot`)를 쳐도 리포트가 나와서 "먹혔다"고 착각하기 쉽다(2026-08-26 감사에서 발견).
    KNOWN = {"--report", "--days"}
    unknown = [a for a in argv if a.startswith("--") and a not in KNOWN]
    if unknown:
        print(json.dumps({"_fatal_error": f"알 수 없는 인자: {unknown} (지원: {sorted(KNOWN)})"},
                         ensure_ascii=False))
        return
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else 30
    rows, items = from_jsonl(days)
    runs = from_runlogs(days)

    cnt = Counter(i["유형"] for i in items)
    # ⚠️ **며칠에 걸쳐 반복된 유형**이 핵심이다. 하루 1건은 사고지만 3일 연속은 구조 문제다.
    bydate = {}
    for i in items:
        bydate.setdefault(i["유형"], set()).add(i["date"])
    repeated = sorted(((k, len(v), sorted(v)) for k, v in bydate.items() if len(v) >= 2),
                      key=lambda x: -x[1])

    res = {
        "기간": f"최근 {days}일",
        "브리핑기록": len(rows),
        "실행로그": len(runs),
        "실패건수": len(items),
        "유형별": dict(cnt.most_common()),
        "반복유형": [{"유형": k, "발생일수": n, "날짜": d} for k, n, d in repeated],
        "추이": runs,
        "갈라진파일": 갈라진파일(),
    }
    if len(runs) >= 2:
        a, b = runs[0], runs[-1]
        if "추정비용USD" in a and "추정비용USD" in b:
            res["비용추이"] = {"처음": f"{a['날짜']} ${a['추정비용USD']}",
                                "최근": f"{b['날짜']} ${b['추정비용USD']}"}
    res["_주의"] = ("① `반복유형`이 핵심이다 — 하루 1건은 사고지만 **여러 날 반복되면 구조 문제**다. "
                    "② `기타`가 많으면 분류 규칙(PATTERNS)이 실제 실패를 못 따라가는 것이니 "
                    "원문을 보고 규칙을 늘린다. **억지로 분류하지 않는다.** "
                    "③ 실행로그 형식이 바뀐 적이 있어 못 읽는 날은 조용히 빠진다 — "
                    "`실행로그` 수가 `브리핑기록`보다 적으면 그 때문이다.")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
