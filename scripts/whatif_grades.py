#!/usr/bin/env python3
r"""
whatif_grades.py — **"이 규칙을 넣었다면 등급이 몇 건 바뀌었을까"** (2026-08-31 신설)

⚠️⚠️ **왜 필요한가.**
   사용자가 원래 요구한 것은 "서술 전용 11개를 갭처럼 점수화하자"였다. 그중 **4개**는
   새 주장이 아니라 **이미 점수인 항목을 더 잘 재는 것**이다(AGENDA A-핵심):

     · 외국인지분율추이 — 갭③은 **하루치**인데 10일 추세는 같은 것의 **강도**
     · 의견추이·등급변경  — 목표주가 하향은 −2인데 **"매수→중립" 강등은 0점**
     · 분기6개(부채비율)  — 재무취약을 **연간(8개월 늦음)** 대신 **최신 분기**로
     · 당좌비율          — 부채비율·순이익률은 보면서 **단기 지급능력을 안 본다**

   ⚠️ **"새 주장이 아니다" ≠ "안전하다".** 넣으면 등급이 바뀐다. 특히 갭③은 지금까지
      백테스트에서 **가장 성과가 나빴다**(있음 +0.16%p n=7 vs 없음 +9.58%p n=15).
      외국인지분율추이로 갭③을 강화하는 것은 **가장 약한 신호에 무게를 더 싣는 것**일 수 있다.

⚠️ **이 스크립트는 판단하지 않는다. 세기만 한다.**
   "등급이 몇 건 바뀌나"만 답한다. 좋아지는지 나빠지는지는 **표본 20건이 쌓인 뒤**
   `backtest_returns.py`가 답할 일이다(9월 하순). 여기서 결론을 내면 안 된다.

⚠️ **아무것도 고치지 않는다.** 스냅샷과 일일 로그를 **읽기만** 한다.
   브리핑·점수·등급 어느 것도 건드리지 않는다.

쓰는 법:
    python scripts\whatif_grades.py                 # 네 규칙 전부
    python scripts\whatif_grades.py --rule 분기부채   # 하나만
    python scripts\whatif_grades.py --verbose        # 종목별 상세
"""
import argparse
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
SNAP = os.path.join(_BASE, "data", "snapshots")

try:
    from fetch_consensus import change_for as _consensus_change, load_history as _chist
except Exception:  # noqa: BLE001
    _consensus_change = _chist = None


# ── 등급 규칙 ───────────────────────────────────────────────────
# ⚠️⚠️ **같은 규칙이 두 곳에 있다** — `SKILL.md`(모델이 등급을 매기는 곳)와 여기.
#    소급 계산은 "그때의 규칙"으로 돌려야 의미가 있어서 별도로 두지만,
#    **스킬만 고치고 여기를 안 고치면 결과가 조용히 거짓이 된다.**
#    ⚠️ 주석으로 "같이 보라"고만 적어 두는 것은 소용없다 — 2026-08-31 하루에만
#       낡은 주석 넷을 찾았다. **그래서 실행할 때마다 스킬을 읽어 대조한다.**
_컷 = {"🔴": 5, "🟢": 3}       # 이 점수 **이상**이면 그 등급. 나머지는 🟡.
SKILL = os.path.join(os.path.expanduser("~"), ".claude", "skills",
                     "morning-sector-briefing", "SKILL.md")


def 컷오프대조():
    r"""`SKILL.md`의 등급 컷오프를 읽어 위 `_컷`과 **대조**한다.

    스킬 원문: `**5점+** → 🔴 최우선매수 · **3~4점** → 🟢 주목 · **1~2점** → 🟡 점검`
    ⚠️ 못 읽으면 **못 읽었다고 말한다.** "일치"로 넘기면 대조가 있으나 마나다.
    """
    try:
        t = io.open(SKILL, encoding="utf-8-sig").read()
    except Exception as e:  # noqa: BLE001
        return {"상태": "스킬을 못 읽었다", "오류": f"{type(e).__name__}: {e}"}
    m = re.search(r"\*\*(\d+)점\+\*\*\s*→\s*🔴.*?\*\*(\d+)~(\d+)점\*\*\s*→\s*🟢", t, re.S)
    if not m:
        return {"상태": "스킬에서 컷오프 문장을 못 찾았다 — 표현이 바뀌었는지 본다"}
    스킬컷 = {"🔴": int(m.group(1)), "🟢": int(m.group(2))}
    if 스킬컷 == _컷:
        return {"상태": "일치", "컷오프": _컷}
    return {"상태": "⚠️⚠️ 어긋남 — 이 결과를 믿지 마라",
            "스킬": 스킬컷, "이_스크립트": _컷,
            "조치": "SKILL.md가 정본이다. whatif_grades.py의 `_컷`을 스킬에 맞춘다."}


def 등급(총점, 갭합산):
    r"""점수 → 등급. **하한 규칙**까지 그대로 옮긴다.

    5점+ → 🔴 · 3~4점 → 🟢 · 1~2점 → 🟡
    ⚠️ 갭합산이 1점 이상인데 마이너스가 겹쳐 총점이 0 이하면 **🟡 고정**(하한 규칙).
    """
    if 갭합산 >= 1 and 총점 <= 0:
        return "🟡"
    if 총점 >= _컷["🔴"]:
        return "🔴"
    if 총점 >= _컷["🟢"]:
        return "🟢"
    return "🟡"


def _num(x):
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x or "").replace(",", "").replace("%", "").replace("+", "").strip()
    if s in ("", "-", "N/A", "없음"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _last(seq):
    """뒤에서부터 처음 나오는 숫자. 분기 표의 마지막 칸은 `-`인 경우가 많다."""
    for x in reversed(list(seq or [])):
        v = _num(x)
        if v is not None:
            return v
    return None


def _snap_stocks(date):
    """그날 스냅샷의 종목별 원본. 여러 파일로 나뉘어 있으면 합친다."""
    out = {}
    for f in sorted(glob.glob(os.path.join(SNAP, date, "*fetch_stock*"))):
        try:
            with io.open(f, encoding="utf-8") as fp:
                out.update((json.load(fp).get("stocks") or {}))
        except Exception:  # noqa: BLE001
            pass
    return out


# ── 네 규칙 ─────────────────────────────────────────────────────
# 각 함수는 (점수변화, 이유) 또는 (0, 사유) 를 돌려준다.
# ⚠️ 판정 못 할 때 **0점으로 처리하고 이유를 남긴다.** 조용히 넘기면 "규칙이 안 걸린 것"과
#    "데이터가 없어서 못 잰 것"이 섞여, 영향도가 실제보다 작게 보인다.

def r_외국인추세(pick, st, date, chist):
    r"""갭③(수급 +1)을 **10일 추세**로 강화한다.

    지금: 하루치로 외국인·기관이 **둘 다** 순매수면 +1.
    제안: 10일 중 외국인 증가일이 70% 이상이면 **추가 +1**.
    ⚠️ 갭③은 백테스트에서 가장 나빴다. 이 규칙은 **그 갭을 더 키운다.**
    """
    v = (st.get("외국인지분율추이") or {})
    raw = v.get("증가일비율")
    # ⚠️⚠️ 이 값은 **"3/9" 같은 분수 문자열**이다(2026-08-31 실측). 숫자로 읽으려다
    #    13건 전부 "없음"으로 빠졌다 — 규칙이 안 걸린 게 아니라 **못 읽은 것**이었다.
    비율 = None
    if isinstance(raw, str) and "/" in raw:
        a, _, b = raw.partition("/")
        na, nb = _num(a), _num(b)
        if na is not None and nb:
            비율 = na / nb * 100
    else:
        비율 = _num(raw)
        if 비율 is not None and 비율 <= 1:
            비율 *= 100
    if 비율 is None:
        return 0, f"증가일비율을 못 읽었다({raw!r})"
    if 비율 >= 70:
        return 1, f"외국인 증가일 {비율:.0f}% (70%↑)"
    return 0, f"외국인 증가일 {비율:.0f}%"


def r_의견강등(pick, st, date, chist):
    r"""**투자의견 강등**에 −1. 지금은 목표주가 하향만 −2이고 의견 강등은 0점이다.

    ⚠️ 의견점수는 5점 만점이고 **낮을수록 매수 쪽**이 아니라 **높을수록 매수 쪽**이다
       (네이버 `recommMean` 4.0 = 매수). 그래서 **떨어지면** 강등이다.
    """
    if chist is None or _consensus_change is None:
        return 0, "컨센서스 이력 모듈 없음"
    ch = _consensus_change(pick["code"], date, chist)
    if not ch:
        return 0, "직전 관측 없음(차분 불가)"
    d = ch.get("의견점수_변화")
    if d is None:
        return 0, "의견점수 없음"
    if d <= -0.1:
        return -1, f"의견점수 {d:+.2f} ({ch.get('간격일')}일 만에)"
    return 0, f"의견점수 {d:+.2f}"


def r_분기부채(pick, st, date, chist):
    r"""재무취약(−2) 판정을 **연간 → 최신 분기**로.

    ⚠️⚠️ 이게 무조건 옳지는 않다. 연간은 **8개월 늦고**, 분기는 **계절성에 흔들린다.**
       조선업은 배값을 미리 받는 구조라 분기 부채비율이 원래 출렁인다 —
       한 분기 악화가 위험 신호인지 계절 변동인지 이 값만으로는 구분이 안 된다.
    ⚠️ 지금 규칙의 문턱은 **부채비율 200%**다(SKILL 재무취약 판정).
    """
    연 = _last((st.get("재무3개년") or {}).get("부채비율"))
    분 = _last((st.get("분기6개") or {}).get("부채비율"))
    if 연 is None or 분 is None:
        return 0, f"부채비율 연간={연} 분기={분} (한쪽 없음)"
    옛 = -2 if 연 >= 200 else 0
    새 = -2 if 분 >= 200 else 0
    if 새 != 옛:
        return 새 - 옛, f"부채비율 연간 {연:.0f}% → 분기 {분:.0f}% (문턱 200%)"
    return 0, f"부채비율 연간 {연:.0f}% · 분기 {분:.0f}% (판정 같음)"


def r_당좌비율(pick, st, date, chist):
    r"""**단기 지급능력**을 재무취약에 더한다.

    당좌비율 = 1년 안에 갚을 돈 대비 당장 현금으로 바꿀 수 있는 자산.
    **100 미만이면 주의**가 통상 기준이다. 지금 점수표에는 아예 없다.
    """
    v = _last((st.get("재무3개년") or {}).get("당좌비율"))
    if v is None:
        return 0, "당좌비율 없음"
    if v < 100:
        return -1, f"당좌비율 {v:.1f}% (100 미만)"
    return 0, f"당좌비율 {v:.1f}%"


규칙 = {
    "외국인추세": r_외국인추세,
    "의견강등": r_의견강등,
    "분기부채": r_분기부채,
    "당좌비율": r_당좌비율,
}


def run(only=None, verbose=False):
    if not os.path.exists(LOG):
        return {"ok": False, "이유": "일일 로그가 없다"}
    rows = [json.loads(l) for l in io.open(LOG, encoding="utf-8") if l.strip()]
    chist = _chist() if _chist else None
    쓸규칙 = {k: v for k, v in 규칙.items() if not only or k in only}

    결과, 건수 = [], {"전체": 0, "스냅샷있음": 0, "등급바뀜": 0}
    규칙별 = {k: {"걸림": 0, "점수합": 0, "못잼": 0} for k in 쓸규칙}

    for o in rows:
        date = o.get("date")
        st_all = _snap_stocks(date)
        for p in (o.get("picks") or []):
            건수["전체"] += 1
            st = st_all.get(p["code"])
            if not st:
                continue          # 스냅샷 이전 날짜 — 소급 불가
            건수["스냅샷있음"] += 1
            # ⚠️⚠️ 일일 로그의 점수 필드 이름은 "score"다("원점수"가 아니다).
            #    처음에 "원점수"로 읽어서 **13건 전부 조용히 건너뛰었다.** 결과가
            #    "등급바뀜 0"으로 나왔는데, 그건 규칙이 안 걸린 게 아니라 **안 돈 것**이었다.
            #    ⚠️ 0이 나오면 "영향 없음"이 아니라 **"안 돌았나"를 먼저 의심한다.**
            원점수 = p.get("score")
            갭 = len(p.get("gaps") or [])
            if 원점수 is None:
                continue
            변화, 이유들 = 0, []
            for 이름, fn in 쓸규칙.items():
                try:
                    d, why = fn(p, st, date, chist)
                except Exception as e:  # noqa: BLE001
                    d, why = 0, f"오류 {type(e).__name__}"
                if d:
                    규칙별[이름]["걸림"] += 1
                    규칙별[이름]["점수합"] += d
                elif "없음" in why or "불가" in why or "오류" in why:
                    규칙별[이름]["못잼"] += 1
                변화 += d
                이유들.append(f"{이름} {d:+d} ({why})")
            새점수 = 원점수 + 변화
            옛등급, 새등급 = 등급(원점수, 갭), 등급(새점수, 갭)
            바뀜 = 옛등급 != 새등급
            if 바뀜:
                건수["등급바뀜"] += 1
            if 바뀜 or verbose:
                결과.append({
                    "date": date, "종목": p.get("name"), "코드": p["code"],
                    "원점수": 원점수, "새점수": 새점수, "변화": 변화,
                    "기록등급": p.get("grade"), "옛등급": 옛등급, "새등급": 새등급,
                    "바뀜": 바뀜, "이유": 이유들,
                })
    대조 = 컷오프대조()
    # ⚠️ 어긋나면 **결과를 내지 않는다.** 틀린 기준으로 센 숫자를 보여주면
    #    그 숫자로 결정을 내린다 — 아예 안 주는 편이 낫다.
    if 대조.get("상태", "").startswith("⚠️"):
        return {"ok": False, "이유": "등급 컷오프가 스킬과 어긋난다", "대조": 대조}
    return {"ok": True, "컷오프대조": 대조, "규칙": list(쓸규칙), "건수": 건수,
            "규칙별": 규칙별, "상세": 결과}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", nargs="*", help="일부 규칙만 (외국인추세·의견강등·분기부채·당좌비율)")
    ap.add_argument("--verbose", action="store_true", help="안 바뀐 것도 전부 보여준다")
    a = ap.parse_args()
    print(json.dumps(run(a.rule, a.verbose), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
