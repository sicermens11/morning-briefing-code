#!/usr/bin/env python3
r"""
check_copy.py — `data\card-copy\<날짜>.json`이 **약속한 모양대로 왔는지** 본다

⚠️⚠️ **왜 필요한가** (2026-08-28 신설).
   레이아웃은 코드에 고정이고 매일 바뀌는 건 이 파일의 글뿐인데, **그 파일에는
   아무 검사가 없었다.** 키 이름을 하나 잘못 쓰면 그 항목이 화면에서 조용히 사라진다.
   오류도 안 나고 경고도 안 뜬다 — 그냥 빈다. 하루에 필드를 다섯 개 늘린 날
   (`해외연관`·`읽는법`·`핵심근거`·`수급온도`·`미국기회`) 이 위험이 눈에 보였다.

⚠️ **이건 '있나 없나'를 보는 검사다.** 내용이 옳은지는 못 본다 — 그건 사람이 읽어야 한다.
   다만 **숫자 몇 개는 대조한다**(아래 `_check_numbers`). 서술에 적힌 값이 스냅샷·픽과
   어긋나면 그건 기계가 잡을 수 있는 거짓말이다.

⚠️ 실패해도 **브리핑 발행을 막지는 않는다**(지메일은 이미 나갔다). 웹 게시만 막는다 —
   빈 화면을 올리느니 어제 것을 두는 편이 낫다. `run-briefing.ps1`이 그렇게 쓴다.
"""
import argparse
import glob
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY_DIR = os.path.join(_BASE, "data", "card-copy")
LOG = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
SNAP = os.path.join(_BASE, "data", "snapshots")

# ⚠️ 여기 이름은 `build_cards`·`build_scroll`이 실제로 읽는 것과 **같아야** 한다.
#    한쪽만 고치면 검사는 통과하는데 화면은 비는, 제일 나쁜 상태가 된다.
필수 = ["date", "부제", "핵심", "미장요약", "미장뉴스", "국장뉴스", "시장국면",
       "이미반영", "미반영", "수급", "수급해설", "예탁금해설", "캘린더해설", "캘린더",
       "의견해설", "의견", "컨센서스", "상관관계", "종목", "결론", "장초확인",
       "해외연관", "읽는법", "수급온도", "미국기회"]
# 없을 수 있는 것 — 그날 해당 사항이 없으면 비운다(지어내지 않는다).
선택 = ["공시", "전일픽", "정책캘린더", "뺀후보"]
종목필수 = ["핵심근거", "강한신호", "고려할점", "갭해당", "품질참고",
          "갭분석", "묶음점수", "신호", "주의사항", "진입조건", "장기", "언제파나"]

# ⚠️⚠️ **한 줄만 적고 넘어가는 것을 막는다** (2026-08-28 신설). 키가 있는지만 보면
#    "확인 필요" 네 글자로도 통과한다. 세로 상세가 지메일 수준이어야 한다는 약속은
#    **분량으로도 지켜져야** 한다. 숫자는 오늘(08-28) 실제로 쓴 글의 60% 선으로 잡았다 —
#    막으려는 것은 "짧게 쓴 날"이 아니라 **"안 쓴 날"**이다.
# ⚠️⚠️ **2026-08-31 상향 — 세로 상세는 요약본이 아니다.**
#    지메일과 대조하니 세로가 62%였다(종목당 1,569자 vs 2,520자). 특히 `신호`·`주의사항`이
#    44%로 얕았다. 요약은 **가로 요약 카드**가 하는 일이고, 세로는 지메일과 같은 깊이여야 한다.
#    숫자는 지메일 실측의 약 80% 선이다 — 자연스러운 변동은 허용하되 **반쪽짜리는 막는다.**
최소 = {"핵심근거": 400, "갭분석": 360, "묶음점수": 60, "신호": 430,
       "주의사항": 450, "진입조건": 180, "장기": 150, "언제파나": 150,
       # 가로 요약 카드 전용(세로에 안 나간다) — 여기는 짧은 게 맞다.
       "강한신호": 110, "고려할점": 110}
최소상위 = {"핵심": 60, "시장국면": 50, "수급해설": 40, "결론": 60, "컨센서스": 50,
         "수급온도": 50, "미국기회": 30}

_돈 = re.compile(r"([0-9][0-9,]{2,})\s*원")


def _snap(date, name):
    for f in glob.glob(os.path.join(SNAP, date, f"*{name}*")):
        try:
            with io.open(f, encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:  # noqa: BLE001
            pass
    return {}


def _day(date):
    if not os.path.exists(LOG):
        return {}
    with io.open(LOG, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if o.get("date") == date:
                return o
    return {}


def _check_numbers(d, day, date):
    r"""서술에 박힌 **가격**이 실제 데이터에 있는 값인지 본다.

    ⚠️ 완전한 검사가 아니다. 잡는 것은 **종목 글에 나온 '…원'** 중 그 종목의
       진입선·손절선·발굴가 어디에도 없는 값이다. 지지선처럼 글에만 나오는 수치도
       있어서 **경고로만** 남긴다 — 막지 않는다. 그래도 "57,695원"을 "57,659원"으로
       잘못 옮긴 날은 여기서 눈에 띈다.
    """
    경고 = []
    for pk in (day.get("picks") or []):
        me = (d.get("종목") or {}).get(pk["code"]) or {}
        아는값 = {int(pk["found_price"])} if pk.get("found_price") else set()
        for c in (pk.get("entry_conditions") or []):
            if c.get("value") is not None:
                아는값.add(int(c["value"]))
        # ⚠️ 손절선은 `entry_conditions`가 아니라 `stop_loss`에 있다(2026-08-31 분리).
        #    빼먹으면 **정상적으로 적힌 손절가가 매일 오류로 뜬다** — 실제로 08-31에
        #    세 종목 다 그렇게 떴다. 잡음이 되는 경고는 아무도 안 읽게 된다.
        if pk.get("stop_loss"):
            아는값.add(int(float(pk["stop_loss"])))
        # ⚠️ **`진입조건`만 본다.** 다른 항목에는 저항선·목표주가처럼 글에만 나오는
        #    정상 값이 많아, 전부 대조하면 경고가 잡음이 되어 아무도 안 읽는다.
        #    진입조건은 확인선·손절선·발굴가만 적는 자리라 어긋나면 곧 오류다.
        글 = str(me.get("진입조건") or "")
        for m in _돈.findall(글):
            v = int(m.replace(",", ""))
            # ⚠️ **저항선·52주 최고가·평균값은 진입조건에 정상적으로 나온다**(2026-08-31).
            #    이걸 "어디에도 없는 값"이라고 매일 경고하면 잡음이 되고, 잡음이 되면
            #    진짜 오타 경고까지 같이 묻힌다. 숫자 앞뒤 문맥으로 가린다.
            j = 글.find(m)
            문맥 = 글[max(0, j - 30):j + 30]
            if any(w in 문맥 for w in ("저항", "최고가", "평균값", "지지", "눌린", "눌렸")):
                continue
            if v >= 1000 and v not in 아는값:
                경고.append(f'{pk["name"]}({pk["code"]}) 글에 "{m}원"이 있는데 '
                          f'진입·손절·발굴가 어디에도 없는 값이다 — 옮겨 적다 틀렸는지 확인')
    # ⚠️ 코스피 지수처럼 **화면이 스냅샷에서 직접 그리는 값**은 서술에 없어도 정상이다.
    #    예전에 그걸 경고로 띄웠다가 잡음만 늘렸다(2026-08-28).
    return 경고


# ⚠️⚠️ **검사가 언제 마지막으로 걸렸나를 센다** (2026-08-31 신설).
#    사용자 지적: **"문제가 생겨서 검사기를 만든 거니, 문제가 없으면 검사기도 필요없다."**
#    맞는 말인데 함정이 하나 있다 — 검사가 안 걸리는 이유가 둘이다:
#      · 문제가 없어졌다        → 빼도 된다
#      · 검사가 있어서 안 생긴다  → 빼면 다시 생긴다
#    둘을 구분하려면 **"언제 마지막으로 걸렸나"**를 알아야 하는데 아무도 안 세고 있었다.
#    ⚠️ 판단은 사람이 한다. 이 기록은 **"4주간 한 번도 안 걸린 검사"를 후보로 올려줄 뿐**이다.
#       자동으로 빼지 않는다 — 안 걸린 게 곧 필요 없다는 뜻은 아니다.
_적발 = os.path.join(_BASE, "data", "check-hits.jsonl")


def _적발기록(date, 오류, 경고):
    """그날 무엇이 몇 건 걸렸나를 한 줄로 남긴다. 같은 날은 덮어쓴다."""
    def 이름(msgs):
        # 메시지 앞부분을 검사 이름으로 삼는다 — 종목코드·숫자는 빼고 유형만 센다.
        키 = {}
        for m in msgs:
            t = str(m)
            for pat in ("손절선(support)", "첫 문장이 40자", "항목끼리 같은 말",
                        "손절가가 `신호`에도", "`신호`에 빠진 항목", "이미반영",
                        "미반영", "너무 짧다", "비어 있는 항목", "약속에 없는 키",
                        "어디에도 없는 값", "`이미반영`과 `뺀후보`"):
                if pat in t:
                    키[pat] = 키.get(pat, 0) + 1
                    break
            else:
                키["기타"] = 키.get("기타", 0) + 1
        return 키
    rec = {"date": date, "오류": 이름(오류), "경고": 이름(경고)}
    keep = []
    if os.path.exists(_적발):
        for line in io.open(_적발, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                if json.loads(line).get("date") == date:
                    continue
            except Exception:  # noqa: BLE001
                pass
            keep.append(line)
    keep.append(json.dumps(rec, ensure_ascii=False))
    with io.open(_적발, "w", encoding="utf-8") as fp:
        fp.write("\n".join(keep) + "\n")


def 적발요약(주=4):
    """최근 `주`주간 검사별 마지막 적발일. **한 번도 안 걸린 검사가 은퇴 후보다.**"""
    from datetime import datetime, timedelta
    if not os.path.exists(_적발):
        return {}
    끝 = {}
    for line in io.open(_적발, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        for 그룹 in ("오류", "경고"):
            for k, n in (o.get(그룹) or {}).items():
                if n:
                    끝[k] = max(끝.get(k, ""), o["date"])
    기준 = (datetime.now() - timedelta(weeks=주)).strftime("%Y-%m-%d")
    return {"마지막적발": dict(sorted(끝.items(), key=lambda x: x[1], reverse=True)),
            "기준일": 기준,
            "은퇴후보": [k for k, v in 끝.items() if v < 기준]}


_판정값 = {"적중", "빗나감", "놓침", "보합", "미확인"}


def _코스피(date):
    r"""전일픽 구간의 **올바른** 코스피 등락률. 못 구하면 None.

    ⚠️⚠️ **2026-09-03 버그 수정 — 하루 어긋나 있었다.**
    ```
    전일픽 수익률 구간 = 어제 종가 -> 오늘 브리핑이 보는 종가
      (오늘 09-03이면 09-01 종가 -> 09-02 종가)
    올바른 벤치마크 = **09-02의 등락률**

    그런데 옛 코드는 `x[0] < date`로 **09-02 로그**를 봤다.
    브리핑 로그는 **전날 값**을 적으므로 09-02 로그의 코스피등락률은 **09-01 것**이다.
    ⇒ 하루 어긋났다.
    ```
    실제 사고: 2026-09-03 로그에 *"스크립트가 벤치마크로 09-02 로그의
    코스피등락률(+0.23%, 실제로는 09-01 등락률)을 써서 하루 어긋남.
    올바른 벤치마크는 09-02 코스피 -3.99%"* 라고 적혀 있었다.
    그 때문에 파이버프로·대한해운이 「적중」으로 잘못 판정될 뻔했다.

    ⇒ **오늘(date) 로그의 코스피등락률**을 써야 한다. 그게 어제 등락률이고,
       전일픽 구간의 벤치마크다.
    """
    import re as _re
    # ⚠️ jsonl이 더 정확하다 — md 파싱보다 구조가 분명하다. 먼저 본다
    j = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
    try:
        for line in io.open(j, encoding="utf-8-sig"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("date") == date:
                v = (r.get("kospi") or {}).get("등락률")
                if v is not None:
                    return float(str(v).replace("−", "-").replace("%", ""))
    except OSError:
        pass
    # ── 폴백: md에서 **오늘 날짜** 절을 찾는다 (옛 코드는 어제를 봤다) ──
    f = os.path.join(_BASE, "data", "briefing-daily-log.md")
    try:
        t = io.open(f, encoding="utf-8-sig").read()
    except OSError:
        return None
    날 = [(m.group(1), m.start())
          for m in _re.finditer(r"^##\s*\[?\s*(\d{4}-\d{2}-\d{2})", t, _re.M)]
    같 = [x for x in 날 if x[0] == date]
    if not 같:
        return None
    d, pos = 같[0]
    끝 = next((p2 for dd, p2 in 날 if p2 > pos), len(t))
    m = _re.search(r"코스피등락률:\s*([+\-−]?\d+\.\d+)%", t[pos:끝])
    return float(m.group(1).replace("−", "-")) if m else None


def _판정검사(d, date, 오류, 경고):
    r"""**전일픽 판정이 규칙과 맞나** (2026-09-01 신설).

    ⚠️ 왜 필요한가 — 2026-09-01까지 **판정 기준이 아예 없었다.** 예시 한 줄만 있어서
       모델이 그날그날 다르게 판단했다. 실측: `−1.11%`는 「빗나감」, `−1.13%`는 「보합」.
       13건 중 **10건이 규칙과 어긋났다.**

    ⚠️ **규칙은 `SKILL.md`의 「전일픽 판정 규칙」이 정본이다.** 여기서 새로 정하지 않고
       그 표를 그대로 적용한다 — 기준이 두 곳에 살면 또 갈라진다.

    ⚠️ **경고로만 낸다.** 코스피 값을 못 구하는 날이 있고(휴장·수집 실패), 그때 게시를
       막으면 옛 페이지가 그대로 남는다. **틀린 라벨보다 게시 실패가 더 나쁘다.**
    """
    xs = d.get("전일픽") or []
    if not xs:
        return
    나쁜값 = [x.get("판정") for x in xs if x.get("판정") not in _판정값]
    if 나쁜값:
        오류.append(f"전일픽 판정에 없는 값: {나쁜값} (허용: {sorted(_판정값)}) "
                    "— 「지수 하회」는 2026-09-01 폐지됐다")
    k = _코스피(date)
    if k is None:
        경고.append("전일픽 판정을 대조 못 했다 — 그날 코스피등락률을 못 찾았다")
        return
    등급 = _전일등급(date)
    for x in xs:
        try:
            r = float(str(x.get("결과", "")).replace("%", "").replace("−", "-"))
        except ValueError:
            continue
        초과 = r - k
        g = 등급.get(x.get("종목"))
        if not g:
            continue
        매수 = g in ("🔴", "🟢")
        기대 = ("보합" if abs(초과) < 1 else
                (("적중" if 초과 >= 1 else "빗나감") if 매수 else
                 ("적중" if 초과 <= -1 else "놓침")))
        if x.get("판정") not in (기대, "미확인"):
            경고.append(f"전일픽 판정 어긋남 — {x.get('종목')} {g} {r:+.2f}% "
                        f"(코스피 {k:+.2f}% · 초과 {초과:+.2f}%p) "
                        f"→ 규칙상 「{기대}」인데 「{x.get('판정')}」로 적혔다")


def _전일등급(date):
    """직전 브리핑 날짜의 종목명 → 등급. `build_scroll._전일등급`과 같은 규칙이다."""
    f = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
    앞 = None
    try:
        for ln in io.open(f, encoding="utf-8-sig"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except ValueError:
                continue
            dt = o.get("date")
            if dt and dt < date and (앞 is None or dt > 앞.get("date", "")):
                앞 = o
    except OSError:
        return {}
    return {q.get("name"): q.get("grade") or "" for q in ((앞 or {}).get("picks") or []) if q.get("name")}


def check(date):
    out = {"ok": False, "날짜": date}
    path = os.path.join(COPY_DIR, f"{date}.json")
    if not os.path.exists(path):
        out["오류"] = [f"서술 파일이 없다: {path} — 웹 페이지에 숫자만 나온다"]
        return out
    try:
        with io.open(path, encoding="utf-8-sig") as fp:
            d = json.load(fp)
    except Exception as e:  # noqa: BLE001
        out["오류"] = [f"JSON이 깨졌다: {type(e).__name__}"]
        return out

    오류, 경고 = [], []
    _판정검사(d, date, 오류, 경고)
    빈 = [k for k in 필수 if not str(d.get(k, "")).strip() or d.get(k) in ([], {})]
    if 빈:
        오류.append("비었거나 없는 키: " + ", ".join(빈))

    # ⚠️ 오타 잡기 — 약속에 없는 키가 있으면 **십중팔구 이름을 잘못 쓴 것**이다.
    앎 = set(필수) | set(선택) | {"date"}
    낯선 = [k for k in d if k not in 앎 and not k.startswith("_")]
    if 낯선:
        경고.append("약속에 없는 키(오타일 수 있다): " + ", ".join(낯선))

    day = _day(date)
    코드 = [p["code"] for p in (day.get("picks") or [])]
    per = d.get("종목") or {}
    if 코드:
        빠짐 = [c for c in 코드 if c not in per]
        군더더기 = [c for c in per if c not in 코드]
        if 빠짐:
            오류.append("후보인데 서술이 없는 종목: " + ", ".join(빠짐))
        if 군더더기:
            경고.append("후보가 아닌데 서술이 있는 종목: " + ", ".join(군더더기))
    for c, me in per.items():
        모자람 = [k for k in 종목필수 if not str(me.get(k, "")).strip()]
        if 모자람:
            오류.append(f"{c}: 비어 있는 항목 — " + ", ".join(모자람))
        짧음 = [f'{k}({len(str(me.get(k, "")))}자<{n})'
              for k, n in 최소.items()
              if str(me.get(k, "")).strip() and len(str(me.get(k, ""))) < n]
        if 짧음:
            # ⚠️⚠️ **길이 미달은 경고다. 게시를 막지 않는다** (2026-08-31 정정).
            #    이 파일 위쪽에 "막으려는 것은 '짧게 쓴 날'이 아니라 '안 쓴 날'"이라고
            #    적어 놓고, 정작 최소치를 400자로 올리면서 오류로 뒀다 — **내가 세운
            #    원칙을 내가 어겼다.**
            #    ⚠️ 짧으면 읽을 수는 있다. 그런데 막으면 **그날 웹이 통째로 어제 것으로
            #       남는다** — 짧은 글보다 어제 글이 훨씬 나쁘다.
            #    ⇒ **빈 항목(안 쓴 것)만 오류**, 짧은 것은 경고로 남겨 다음 날 고친다.
            경고.append(f"{c}: 너무 짧다 — " + ", ".join(짧음))
    짧음2 = [f'{k}({len(str(d.get(k, "")))}자<{n})'
           for k, n in 최소상위.items()
           if str(d.get(k, "")).strip() and len(str(d.get(k, ""))) < n]
    if 짧음2:
        경고.append("너무 짧다 — " + ", ".join(짧음2))

    # ⚠️⚠️ **손절선이 있나** (2026-08-31 신설). 08-31에 세 종목 전부 `entry_conditions`가
    #    한 개(확인선)뿐이라 **카드에 손절가가 한 줄도 안 나갔다.** 사용자가 바로 알아챘다.
    #    ⚠️ 조용히 빠지는 게 문제다 — `numbers()`는 `support`가 없으면 그 조각을 통째로
    #       생략해서, **손절선이 없는 요약과 원래 그런 요약이 똑같이 보인다.**
    #    ⚠️ 막지는 않는다(경고). 손절 하나 때문에 그날 웹 전체를 어제 것으로 두는 건 더 나쁘다.
    #       대신 카드가 "손절 미기재"를 눈에 보이게 찍는다.
    없음 = []
    for pk in (day.get("picks") or []):
        타입 = {c.get("type") for c in (pk.get("entry_conditions") or [])}
        if "support" not in 타입 and not pk.get("stop_loss"):
            없음.append(f'{pk.get("name")}({pk.get("code")})')
    if 없음:
        경고.append("손절선(support)이 없는 후보: " + ", ".join(없음)
                  + " — 확인선만 있으면 어디서 물러날지가 안 적힌다")

    # ⚠️ **이미반영·미반영은 이유가 있어야 한다** (2026-08-31 요청: "너무 간단하게 나왔다").
    #    08-31에 "정유 — 유가 상승분이 값에 이미 붙음"처럼 20자짜리가 나갔다.
    #    세로는 **상세**가 이름값이다. 무엇이·왜·그래서 어떻게 보라는 건지가 들어가야 한다.
    for 키 in ("이미반영", "미반영"):
        짧은것 = [f'{i+1}번({len(str(x))}자)' for i, x in enumerate(d.get(키) or [])
                if len(str(x)) < 45]
        if 짧은것:
            경고.append(f"{키}가 너무 짧다 — " + ", ".join(짧은것)
                      + " (45자 이상: 무엇이 · 왜 그렇게 보는지 · 그래서 어떻게 볼지)")

    # ── ③ 첫 문장 40자 (가로 요약 카드가 첫 문장을 통째로 가져간다) ──────
    # ⚠️⚠️ 스킬에 규칙만 있고 **검사가 없었다.** 그래서 08-31에 −28px·−128px 넘쳤다.
    #    규칙은 지켜지지 않을 때 조용하지만, 검사는 소리를 낸다.
    def _첫문장(t):
        return re.split(r"(?<=니다\.)\s*|(?<=[.!?])\s+", str(t).strip())[0]

    긴첫줄 = []
    for 키 in ("이미반영", "미반영"):
        for i, x in enumerate(d.get(키) or []):
            if len(_첫문장(x)) > 40:
                긴첫줄.append(f"{키} {i+1}번({len(_첫문장(x))}자)")
    # ⚠️⚠️ **카드에 실제로 나가는 필드만 본다** (2026-08-31 정정).
    #    처음엔 `핵심근거`·`진입조건`·`주의사항`·`신호`도 검사했는데, 「언제 사나」를
    #    카드에서 빼면서 그 넷은 **세로 전용**이 됐다. 세로는 길이 제한이 없다.
    #    ⚠️ 규칙이 실제와 어긋나면 **경고가 잡음이 되고, 잡음은 아무도 안 읽는다.**
    #       그러면 진짜 경고까지 같이 묻힌다.
    for c, me in per.items():
        for 키 in ("강한신호", "고려할점"):
            v = me.get(키)
            if v and len(_첫문장(v)) > 40:
                긴첫줄.append(f"{c}·{키}({len(_첫문장(v))}자)")
    for 키 in ("미장요약", "수급해설", "시장국면", "의견해설", "컨센서스"):
        v = d.get(키)
        if v and len(_첫문장(v)) > 40:
            긴첫줄.append(f"{키}({len(_첫문장(v))}자)")
    if 긴첫줄:
        경고.append("첫 문장이 40자를 넘는다 — " + ", ".join(긴첫줄)
                  + " (카드가 첫 문장을 통째로 싣는다. 결론을 먼저, 설명은 두 번째 문장부터)")

    # ── ⑤ 항목끼리 같은 말을 하고 있나 ───────────────────────────
    # ⚠️⚠️ 2026-08-31에 `강한신호`가 `핵심근거`의 요약이고 `신호`와 `진입조건`이
    #    **둘 다 같은 지지선 가격**을 말하고 있었다. 사람이 읽어야만 보이던 문제다.
    #    ⚠️ 완전한 검사가 아니다 — **긴 어절이 그대로 겹치는 것**만 잡는다.
    #       그래도 "복사해 붙인 수준"의 중복은 여기서 걸린다.
    def _토막(t, n=12):
        t = re.sub(r"\s+", "", str(t))
        return {t[i:i + n] for i in range(0, max(0, len(t) - n), 4)}

    겹침 = []
    for c, me in per.items():
        쌍 = (("핵심근거", "주의사항"), ("핵심근거", "갭분석"), ("신호", "진입조건"))
        for a, b in 쌍:
            ta, tb = me.get(a), me.get(b)
            if not (ta and tb):
                continue
            공통 = _토막(ta) & _토막(tb)
            if 공통:
                겹침.append(f"{c}: {a}↔{b} — \"{sorted(공통)[0]}…\"")
    if 겹침:
        경고.append("항목끼리 같은 말이 겹친다 — " + " / ".join(겹침)
                  + " (항목마다 답하는 질문이 하나씩이다. SKILL 역할 구분표 참고)")

    # ── ⑥ `신호`에 지지·저항 가격이 들어갔나 ─────────────────────
    # ⚠️ `신호`는 "지금 주가가 어디 있나", `진입조건`은 "어느 값을 넘으면 사나"다.
    #    가격을 둘 다 쓰면 같은 숫자가 두 번 나온다(2026-08-31 실제로 그랬다).
    # ⚠️⚠️ **손절가가 `신호`에도 있나** (2026-08-31 정밀화 2차).
    #    처음엔 "`신호`에 지지·저항 가격 금지"로 넓게 잡았다가, 저항선처럼 한 곳에만
    #    나오는 값까지 걸려 잡음이 됐다. 다음엔 "같은 숫자 전부"로 잡았는데 이번엔
    #    **"주가가 20일선 140,170을 밑돈다"(상태)와 "140,170을 넘으면 산다"(행동)**까지
    #    걸렸다 — 같은 숫자지만 **다른 정보**라 지우면 안 되는 것이다.
    #    ⇒ 진짜 중복은 하나다: **손절선**. 그건 `진입조건`에만 있어야 한다.
    #       실제로 현대로템은 128,000원과 "한 번만 눌린 약한 자리"라는 설명까지
    #       `신호`와 `진입조건`에 **똑같이** 들어 있었다.
    손절중복 = []
    for pk in (day.get("picks") or []):
        sl = pk.get("stop_loss")
        me = per.get(pk["code"]) or {}
        if not sl or not me.get("신호"):
            continue
        for form in (f"{int(float(sl)):,}", str(int(float(sl)))):
            if form in str(me["신호"]):
                손절중복.append(f'{pk.get("name")}({form}원)')
                break
    if 손절중복:
        경고.append("손절가가 `신호`에도 있다: " + ", ".join(손절중복)
                  + " — 그 숫자와 설명은 `진입조건` 한 곳에만 둔다")

    # ── `신호`에 넣기로 한 넷이 들어갔나 (2026-08-31) ─────────────
    # ⚠️ 지메일에는 세 종목 전부 공매도가 있는데 세로에는 1건뿐이었다.
    #    규칙만 적어두면 다음 날 또 빠진다 — 그래서 검사한다.
    필수신호 = {"공매도": ("공매도",), "평균진폭": ("평균진폭", "ATR"),
             "거래량": ("거래량",), "120일선": ("120일",)}
    빠진신호 = []
    for c, me in per.items():
        t = str(me.get("신호") or "")
        없 = [k for k, ws in 필수신호.items() if not any(w in t for w in ws)]
        if 없:
            빠진신호.append(f"{c}({'·'.join(없)})")
    if 빠진신호:
        경고.append("`신호`에 빠진 항목: " + ", ".join(빠진신호)
                  + " — 공매도·평균진폭·거래량·120일선은 지메일에 있는 것이다")

    # ── 같은 종목이 `이미반영`과 `뺀후보`에 겹쳐 있나 ─────────────
    # ⚠️ 지메일 자체가 유니테스트를 두 곳에 썼다(2026-08-31). 같은 종목을 두 곳에서
    #    다루면 어느 쪽이 결론인지 흐려진다. `이미반영`은 업종, `뺀후보`는 종목이다.
    반영글 = " ".join(str(x) for x in (d.get("이미반영") or []))
    뺀글 = " ".join(str(x) for x in (d.get("뺀후보") or []))
    if 반영글 and 뺀글:
        겹종목 = [nm for nm in re.findall(r"[가-힣A-Za-z0-9]{2,12}(?=\s*\(\d{6}\))", 뺀글)
               if nm and nm in 반영글]
        if 겹종목:
            경고.append("같은 종목이 `이미반영`과 `뺀후보`에 둘 다 있다: "
                      + ", ".join(겹종목) + " — `이미반영`은 업종·테마만 쓴다")

    # ⚠️⚠️ **줄표(—) 금지** (2026-08-31). AI가 쓴 티가 가장 크게 나는 기호다.
    #    두 문장으로 나눈다 — 다른 기호로 바꾸면 같은 문제가 모양만 달라져 남는다.
    #    ⚠️ 값이 없을 때 쓰는 `—` 한 글자(표 빈칸)는 기호가 아니라 표시라 세지 않는다.
    줄표 = []
    for k, v in d.items():
        if k.startswith("_") or k == "종목":
            continue
        n = str(json.dumps(v, ensure_ascii=False)).count(" — ")
        if n:
            줄표.append(f"{k}({n})")
    for c, me in per.items():
        n = str(json.dumps(me, ensure_ascii=False)).count(" — ")
        if n:
            줄표.append(f"{c}({n})")
    if 줄표:
        경고.append("줄표(—)를 썼다: " + ", ".join(줄표)
                  + " — 두 문장으로 나눈다(다른 기호로 바꾸지 않는다)")

    경고 += _check_numbers(d, day, date)

    _적발기록(date, 오류, 경고)
    out["ok"] = not 오류
    if 오류:
        out["오류"] = 오류
    if 경고:
        out["경고"] = 경고
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="비우면 가장 최근 서술 파일")
    a = ap.parse_args()
    date = a.date
    if not date:
        files = sorted(glob.glob(os.path.join(COPY_DIR, "*.json")))
        date = os.path.basename(files[-1])[:-5] if files else ""
    res = check(date)
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res.get("ok") else 1)
