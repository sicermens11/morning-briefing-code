#!/usr/bin/env python3
r"""
build_cards.py — 브리핑을 카드뉴스 7장으로 렌더링 (**요약판**)

⚠️ **수치만 늘어놓지 않는다.** 초보자는 숫자만으로 시장을 못 읽는다. 카드마다
   **수치 + 그게 무슨 뜻인지**를 함께 싣는다. 그래서 입력이 둘이다:

   ① 숫자  — `data\snapshots\<날짜>\` 의 API 원본과 `briefing-daily-log.jsonl`
   ② 서술  — `data\card-copy\<날짜>.json` (브리핑 STEP5 직후 모델이 짧게 쓴다)

   ②가 없으면 숫자만 나온다. 그건 **실패**로 본다 — 경고를 띄운다.

디자인·규격·글꼴 규칙은 전부 `card_theme.py`에 있다 — **거기 맨 위 경고를 먼저 읽는다.**
1080x1350(4:5) · Pretendard Variable **한 벌** · 베이지 단색 바탕.

⚠️ **여백** (2026-08-27). 본문이 사방으로 패딩 경계에 딱 붙어 있었다.
   `card_theme.BREATH_*`가 그 여백이고, 카드마다 `margin-top:auto`로
   **아래까지 꽉 채우지 않는다** — 남는 공간은 남겨 둔다.

카드 구성 (후보 2개마다 액션플랜이 한 장씩 늘어난다):
    01 타이틀      `card_theme.BRAND` (제목은 거기서만 정한다)
    02 뉴스        미장 / 국장
    03 국면        현재 시장 상황 · 이미 시장 반영 · 시장 미반영
    04 돈의 흐름   지수 · 외국인/기관/개인 · 예탁금 · 업종/테마
    05 캘린더      D-7 이벤트 · 경제지표 · 정책
    06 기관 의견   증권사 리포트 · 애널리스트 컨센서스
    06~           액션플랜 — **한 장에 한 종목, 상위 2개까지.** 이름·등급·갭·긍정/부정
                  신호·확인/손절/발굴가. 첫 장에 참고사항(등급 설명 + 숫자 뜻),
                  마지막 장에 카드에 없는 나머지 후보 + 장 시작 후 확인.
    ⚠️ **표지는 쪽을 세지 않는다** — "02 뉴스"가 01/07이다(2026-08-28).
    ⚠️ 두 액션 카드의 **채움을 맞춘다**. 한 장이 텅 비고 한 장이 꽉 차면 눈에 거슬린다.
       실측으로 안내문은 첫 장, 나머지 후보 목록은 마지막 장에 두었다(159px / 123px).

⚠️⚠️ **카드는 요약, 세로형(`build_scroll.py`)이 상세다** (2026-08-27 합의).
   같은 내용을 1080x1350 상자에 다 넣으려다 카드가 10장까지 늘고 글자가 계속 작아졌다.
   카드는 뉴스 `머리`·종목 이름·등급까지만 싣고, `몸`·긍정/부정 신호·용어 설명은
   세로형에 있다. **여기에 상세를 도로 넣지 않는다** — 넣는 순간 같은 일이 반복된다.

   ⚠️ 서술 파일(`card-copy`)은 **한 벌이다.** 카드용 짧은 판을 따로 쓰지 않는다 —
      두 벌이면 한쪽만 고쳐서 둘이 다른 말을 하게 된다. 코드가 잘라 쓴다.
"""
import datetime as dt
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from itertools import zip_longest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from card_theme import (  # noqa: E402
    BRAND, C, CARD_H, CARD_W, FONTS, GAP, RADIUS, RADIUS_BIG, GRADE_HELP, LS_KO, MONO, TEXT_MAX,
    BLOCK_PAD, BLOCK_RULE, LABEL_COLOR, FS, FS_TIGHT, LH, SEC,
    KV_DIVIDER, KV_PAD_L,
    band_color, band_label,
    card, cut, first_sentence, head, kicker, mono_if, pct, sign_color, signed,
    tint_pct, link,
)

# 한 카드에 올리는 액션플랜 후보 수. **2개가 가운데 값이다.**
# 4개면 글자가 19px까지 내려가 확대해야 읽히고, 1개면 카드가 10장이 된다.
# ⚠️ 이 값을 바꾸면 반드시 여백을 재본다. 눈대중으로 올리면 카드 밖으로 넘친다.
# ⚠️⚠️ **카드에 들어갈 글의 상한(자)**. 카드는 1080x1350 고정인데 글은 매일 길이가 다르다.
#    2026-08-28 아침 `강한신호`가 271자로 와서 액션플랜이 547px 넘쳐 게시가 막혔다.
#    글쓴이에게 매일 "짧게 써라"를 요구하는 대신 여기서 자른다 — 전문은 세로 상세에 있다.
#    ⚠️ 이 숫자를 늘리려면 `check_layout.py`를 돌려 여백이 90px 위로 남는지 먼저 본다.
# ⭐ **본문 크기** (2026-09-11 지시).
#    「넘칠 때 문장을 자르지 마. **본문만 31 -> 29** 로 한 단계 줄이고,
#     그래도 넘치면 같은 섹션의 2/2 장을 만들어 항목을 옮겨」
#    ⚠️ 값을 카드마다 손으로 박지 않는다 — 여기서 가져다 쓴다
BODY_FS = 31         # 기본 본문
BODY_FS_TIGHT = 29   # 한 단계 줄인 것 (하한)
BODY_LH = 1.6

CUT = {
    # ⚠️ 이 숫자는 **감이 아니라 실측**이다. `check_layout.py`로 카드별 아래 여백을 재서
    #    하한 90px을 남기고 남는 만큼만 올린다. **바꾸면 반드시 다시 잰다.**
    #    ⚠️ 2026-08-28에 있던 "액션플랜은 여유 8px이니 건드리지 마라"는 주석은
    #       **한 장에 두 종목이던 시절 값**이라 지웠다. 한 종목으로 바꾼 뒤 여유가 생겼다.
    # ⚠️ 96 -> 78 / 32 -> 26 (2026-09-11 지시서 7절). 03 국면의 항목 간격이
    #    **46px**(하한 50) 로 좁았다 — 지시서: 「넘치면 문장을 cut() 으로 줄인다」
    "시장국면": 96, "반영": 32,         # 03 국면 (`반영`은 첫 문장 상한)
    # ⚠️⚠️ **05 캘린더의 「이번 주 핵심」에 예산이 아예 없었다** (2026-09-11).
    #    128~283자가 통째로 들어가 9/09 에 항목 간격이 **3px** 까지 죽었다.
    #    ⭐ 디자인 답: **고정 100자** (의견해설과 같은 급).
    #       「남는 만큼 준다」는 쓰지 않는다 — 날마다 줄 수가 달라져
       #    장 전체가 흔들린다. 고정값이라야 매일 같은 모양이 나온다
    "캘린더해설": 100,


    # ⚠️ 72 -> 64 (2026-09-11). 04 수급이 아래 여백 **88px** 로 2px 모자랐다.
    #    지시서 4절: 넘치면 **글자 크기가 아니라 예산**으로 흡수한다
    "수급해설": 72,                      # 04 돈의 흐름
    # ⚠️ 「언제 사나」를 카드에서 빼고 그 자리를 신호로 돌렸다(2026-08-31).
    #    신호는 살 이유와 망설일 이유라 **숫자로 대체할 수 없는 카드의 유일한 판단 재료**다.
    # ⚠️ 140 -> 186 (2026-09-11 지시서 7절). 06 액션의 항목 간격이 **125px**
    #    (상한 93) 로 벌어졌다 — 내용이 적어 남는 자리가 항목 사이로 갔다.
    #    지시서 4절 예산은 「긍정/부정 신호 각 4문장 · 190자」라 여유가 있다
    "신호": 140,
    # ⚠️ 06 기관 의견에는 **예산이 아예 없었다**(2026-08-31 발견). 두 글을 통째로
    #    넣어서 긴 날엔 넘치고(실측 여백 35px) 짧은 날엔 290px가 남았다 —
    #    같은 카드가 날마다 다른 길이로 끝나는 게 "끝점이 안 맞는" 원인이었다.
    "의견해설": 100, "컨센서스": 110, "장초확인": 48, "일정": 46, "미장요약": 76,  # 07~ 액션플랜
}

# ⚠️⚠️ **한 장에 한 종목, 상위 두 종목까지만** (2026-08-28 결정).
#    두 종목을 한 장에 넣으니 글자를 26px 위로 못 올렸다 — 액션플랜이 유일한 병목이었다.
#    자리를 벌려 글자와 글을 같이 키운다. 나머지 후보는 **세로 상세에 전부 있다** —
#    카드는 요약이고, 요약은 다 담는 자리가 아니다.
PICKS_PER_CARD = 1
CARD_PICKS_MAX = 2

KST = timezone(timedelta(hours=9))
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LOG = os.path.join(_DATA, "briefing-daily-log.jsonl")
COPY_DIR = os.path.join(_DATA, "card-copy")
OUT = os.path.join(_DATA, "briefing-cards.html")
URL_FILE = os.path.join(_DATA, "archive-url.txt")
WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
# ⚠️ 등급 배지는 **오르내림이 아니다.** `up`/`down`을 쓰면 상승=빨강으로 바꾼 순간
#    🔴가 파랑이 된다(2026-08-28). 색을 여기서 직접 정한다.
GRADE = {"🔴": (C["up"], "최우선매수"), "🟢": (C["green"], "주목"), "🟡": (C["yellow"], "점검")}


def _snap(date, prefix):
    d = os.path.join(_DATA, "snapshots", date)
    if not os.path.isdir(d):
        return {}
    for f in sorted(os.listdir(d)):
        if f.startswith(prefix) and f.endswith(".json"):
            try:
                return json.load(io.open(os.path.join(d, f), encoding="utf-8-sig"))
            except Exception:
                continue
    return {}


def _copy(date):
    p = os.path.join(COPY_DIR, f"{date}.json")
    if os.path.exists(p):
        try:
            return json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:
            pass
    return {}


def _f(v, d=None):
    try:
        return float(str(v).replace(",", "").replace("%", "").replace("+", ""))
    except (TypeError, ValueError):
        return d


# ── 조각 ────────────────────────────────────────────────────────
def _note(idx, head_, body):
    """번호 붙은 서술 한 덩어리 — 카드뉴스의 핵심. 숫자를 문장 안에 녹인다."""
    return (f'<div style="display:flex;gap:20px;align-items:flex-start">'
            f'<span style="font-family:{MONO};font-size:29px;color:{C["blue"]};'
            f'font-weight:700;flex:none;padding-top:7px">{idx:02d}</span>'
            f'<div style="max-width:{TEXT_MAX}">'
            f'<div style="font-size:33px;font-weight:700;color:{C["text"]};'
            f'letter-spacing:-.02em;margin-bottom:9px">{head_}</div>'
            f'<div style="font-size:29px;line-height:1.55;color:{C["text2"]};'
            f'word-break:keep-all">{body}</div></div></div>')


# 항목 하나를 감싸는 **중립 바탕.** 검정 4%라 어떤 바탕 위에서도 같은 만큼 눌린다.
# ⚠️ 색을 지정하지 않는다 — 좋고 나쁨을 뜻하지 않는 "그냥 한 덩어리"라는 표시다.
TINT = "#17181a0a"
# ⚠️ **TINT 상자는 전부 `border-radius:{RADIUS}px`를 함께 쓴다** (2026-08-31).
#    `block()`만 둥글게 했더니 같은 모양의 상자가 카드마다 각지고 둥글고 갈렸다.
#    상자를 그리는 코드가 여섯 군데로 흩어져 있어서 생긴 일이다 — 새로 그릴 때도 맞춘다.
#    (테두리는 안 붙인다. 붙이면 상자마다 높이가 2px씩 늘어 여백을 먹는다.)


def stat_cell(label, value, change=None, big=44, note="", first=False):
    r"""지수·수급처럼 **숫자 한 칸**. 바탕을 깔아 옆 칸과 갈린다.

    ⚠️ `note`는 "이 숫자가 오르면 무슨 뜻인가"다(2026-08-27 요청).
       숫자만 있으면 초보는 높은 건지 낮은 건지 모른다.
    """
    ch = ""
    if change is not None:
        v = _f(change)
        ch = (f'<div style="font-size:29px;font-weight:700;'
              f'color:{sign_color(v or 0)};margin-top:6px">{pct(v)}</div>')
    nt = (f'<div style="font-size:29px;line-height:1.4;color:{C["text2"]};'
          f'margin-top:9px;word-break:keep-all">{note}</div>') if note else ""
    # ⭐⭐ **바탕 상자 대신 세로선** (2026-09-11 · 디자인 명세 2절 `kv`).
    #    「3칸 가로 · 칸 사이 세로선 1px #d5cec0 + 왼여백 22px」
    #    ⚠️ 칸마다 바탕을 깔면 **한 줄에 상자가 셋**이 된다 —
    #       명세 7절이 막는 「모든 항목에 둥근 상자」와 같은 부류다.
    #    ⚠️ 첫 칸에는 선이 없다. 인라인 스타일이라 형제 선택자를 못 쓰므로
    #       `first` 를 받는다 — 안 넘기면 선이 그려진다(가운데·오른쪽 칸)
    _벽 = ("" if first
           else f"border-left:{KV_DIVIDER};padding-left:{KV_PAD_L}px;")
    return (f'<div style="flex:1;min-width:0;{_벽}">'
            f'<div style="font-size:29px;color:{C["muted"]};margin-bottom:9px">'
            f'{label}</div>'
            f'<div style="font-size:{big}px;font-weight:700;color:{C["text"]};'
            f'letter-spacing:-.02em">{value}</div>{ch}{nt}</div>')


def _us_gist(idx, fut):
    r"""지수 셋을 묶어 "그래서 오늘 아침 미국은 어땠나"를 **한 문장**으로.

    ⚠️ `card-copy`의 `미장요약`이 있으면 그쪽이 우선이다. 이건 그게 없을 때의 대비다 —
       숫자에서 기계적으로 만들되, **없는 말은 지어내지 않는다.**
    """
    sp = _f((idx.get("S&P500") or {}).get("등락률"))
    nq = _f((idx.get("나스닥100") or {}).get("등락률"))
    ft = _f((fut.get("나스닥100 선물") or {}).get("등락률"))
    if sp is None and nq is None and ft is None:
        return ""
    day = ("거의 안 움직였습니다" if max(abs(sp or 0), abs(nq or 0)) < 0.3
           else ("올랐습니다" if (nq or sp or 0) > 0 else "내렸습니다"))
    if ft is None:
        return f"어젯밤 미국 증시는 {day}."
    if ft > 0.5:
        tail = ("그런데 <b>선물이 오르고 있습니다</b> · 미국 장이 닫힌 뒤 좋은 소식이 "
                "나왔다는 뜻이라, 오늘 아침 우리 기술주도 오를 가능성이 있습니다.")
    elif ft < -0.5:
        tail = ("그런데 <b>선물이 내리고 있습니다</b> · 미국 장이 닫힌 뒤 나쁜 소식이 "
                "나왔다는 뜻이라, 오늘 아침 우리 시장도 눌릴 수 있습니다.")
    else:
        tail = "선물도 큰 변화가 없어 오늘 아침 출발은 무난할 것으로 봅니다."
    return f"어젯밤 미국 증시는 {day}. {tail}"


def pg(num, total):
    r"""머리글 오른쪽 쪽 번호.

    ⚠️ 예전에는 "01 / 07"처럼 총 장수를 같이 적었다. 2026-08-28에 **번호만** 남겼다 —
       총 장수는 후보 수에 따라 매일 바뀌어서 오히려 헷갈렸고, 넘기다 보면 끝은 어차피
       안다. `total`은 자리를 지키느라 남겨 둔다(호출부를 다 고치는 것보다 낫다).
    """
    return f"{num:02d}"


def block(label, color, inner, sub="", top=None, size=26, first=False):
    r"""항목 한 덩어리 — 색 박스 없이 **라벨 + 얇은 줄**로만 구분한다.

    ⚠️ 고정 여백(`margin-top`)을 주지 않는다. 항목 사이 간격은 본문 상자의
       `justify-content:space-between` 이 분배한다. 둘을 같이 쓰면 카드마다
       간격이 달라진다 (2026-09-11 사고: 같은 덱에서 28 / 40 / 167px 로 갈렸다).
    ⚠️ 색 배경·테두리·왼쪽 막대를 다시 넣지 않는다. 확정 디자인은 줄로만 나눈다.
    ⚠️ `first=True` 는 카드의 첫 항목 — 위쪽 경계선을 두지 않는다.

    ⚠️ `top=` 은 **받아서 안 쓴다**(호출부 호환). 다만 예전 호출부가
       `top=0` 으로 첫 항목을 알리고 있어 그것도 첫 항목으로 친다.
    """
    _첫 = first or top == 0
    edge = "" if _첫 else f'border-top:1px solid {C["line"]};padding-top:18px;'
    # ⚠️⚠️ **설명글은 라벨 아래 줄이다** (2026-09-11 디자인 답 ③).
    #    전에는 라벨 오른쪽 같은 줄이었다. 아래로 내리는 까닭 둘:
    #      ⓐ 03 국면이 31px 에서 항목 간격 26px 로 좁아졌는데, **글자를 줄이는
    #         대신 설명줄을 내려 높이를 만든다** (디자인 답 ②)
    #      ⓑ 25px/#6b665c 는 라벨(#8a7038)보다 작고 본문(31px)보다 작은
    #         **보조 글**이다. 같은 줄에 붙이면 라벨의 일부처럼 읽힌다
    #    ⚠️ 간격은 `gap` 으로 준다 — `margin-top` 은 쓰지 않는다
    #       (항목 간격을 분배하는 `space-between` 과 겹치면 카드마다 갈린다)
    _머리 = (f'<div style="display:flex;flex-direction:column;gap:4px">'
             f'<span style="flex:none;font-size:{size}px;font-weight:700;'
             f'letter-spacing:{LS_KO};color:{color or LABEL_COLOR}">{label}</span>'
             + (f'<span style="font-size:25px;line-height:1.45;'
                f'color:#6b665c;word-break:keep-all">{sub}</span>'
                if sub else "")
             + '</div>')
    return (f'<div style="{edge}display:flex;flex-direction:column;gap:10px">'
            + _머리
            + f'<div>{inner}</div></div>')


def numbers(p):
    r"""확인선 · 손절선 · 발굴가를 한 줄로. **카드(요약)의 결론 줄이다.**

    ⚠️ `entry_conditions`는 보통 두 개다 — 평균선(확인선)과 지지선(손절선).
       예전에는 첫 개만 쓰고 버렸다(2026-08-28 재검토에서 발견).
       손절선 없이 사라고 하는 요약은 위험하다.
    """
    conf = stop = None
    for c_ in p.get("entry_conditions") or []:
        v = c_.get("value")
        if v is None:
            continue
        if c_.get("type") in ("sma20", "sma60", "resistance") and conf is None:
            conf = int(v)
        elif c_.get("type") == "support" and stop is None:
            stop = int(v)
    # ⚠️⚠️ **`stop_loss`도 본다** (2026-08-31 사고). 08-31에 세 종목 전부
    #    `entry_conditions`에 `support`가 없어 **손절가가 한 줄도 안 나갔다.**
    #    그런데 글(`진입조건`)에는 "손해를 끊을 기준선은 128,000원"이라고 **쓰여 있었다** —
    #    즉 값이 없던 게 아니라 **기록 필드로 안 옮겨졌다.**
    #    ⚠️ `entry_conditions`에 억지로 넣지 않는다. 그건 09:05 진입체크의 판정 입력이라,
    #       조건을 하나 더 붙이면 **과거 판정이 소급해서 바뀐다.** 별도 칸으로 받는다.
    if stop is None and p.get("stop_loss"):
        stop = int(_f(p.get("stop_loss")) or 0) or None
    # ⚠️⚠️ **한 줄에 「라벨 + 값」 3쌍**이다 (2026-09-11 · 시안 「반복 금지」 ⑦).
    #    「확인 / 손절 / 발굴을 문장 안에 섞었다 → 값선은 **한 줄 3쌍**
    #     (라벨 25px + 값 34px/800)」
    #    전에는 `확인 <b>…</b> · 손절 <b>…</b>` 처럼 가운뎃점으로 이은 **문장**이라
    #    세 값이 한 덩어리로 읽혔다. 값은 값끼리 눈에 들어와야 한다
    def _쌍(라, 값, 흐림=False):
        _색 = C["muted"] if 흐림 else C["text"]
        return (f'<span style="display:flex;align-items:baseline;gap:10px">'
                f'<span style="font-size:25px;color:{C["faint"]}">{라}</span>'
                f'<span style="font-size:34px;font-weight:800;color:{_색};'
                f'letter-spacing:-.02em">{값}</span></span>')

    bits = []
    if conf:
        bits.append(_쌍("확인", f'{conf:,}원'))
    if stop:
        bits.append(_쌍("손절", f'{stop:,}원'))
    else:
        # ⚠️ **조용히 생략하지 않는다.** 손절선이 없는 요약과 원래 그런 요약이
        #    똑같이 보이면, 없다는 사실 자체가 안 보인다.
        bits.append(_쌍("손절", "미기재", 흐림=True))
    if p.get("found_price"):
        bits.append(_쌍("발굴", f'{int(p["found_price"]):,}원'))
    return ('<span style="display:flex;align-items:baseline;gap:26px;'
            'flex-wrap:wrap">' + "".join(bits) + '</span>')


def entry_text(p):
    r"""진입 조건을 **문장으로** 돌려준다.

    ⚠️ 예전엔 "진입 · 20일선 23,329원"이라고만 썼다. 초보에게 이건 사라는 건지
       기다리라는 건지 알 수 없다(2026-08-27 지적). **무슨 뜻인지**를 같이 쓴다.
    """
    for c_ in (p.get("entry_conditions") or [])[:1]:
        t, v = c_.get("type"), c_.get("value")
        if v is None:
            continue
        won = f'{int(v):,}원'
        if t in ("sma20", "sma60"):
            days = "20" if t == "sma20" else "60"
            return (f'<b>{won}</b>을 넘어서면 그때 봅니다. 최근 {days}거래일 평균값이라 '
                    f'이 선 아래에 있는 동안은 아직 힘이 덜 붙은 것으로 봅니다.')
        if t == "support":
            return (f'<b>{won}</b>을 지키는지 봅니다. 예전에 여러 번 이 가격에서 '
                    f'반등했던 자리라, 여기를 내주면 더 내려갈 수 있습니다.')
        if t == "resistance":
            return (f'<b>{won}</b>을 뚫는지 봅니다. 예전에 이 가격에서 여러 번 막혔던 '
                    f'자리라, 넘어서면 위로 길이 열립니다.')
        return f'<b>{won}</b> 기준으로 봅니다.'
    return ""


def grade_legend(size=26):
    r"""등급이 무슨 뜻인지 — **셋을 한 줄에** (2026-08-31 요청: "어차피 참고사항이니").

    ⚠️ 예전 주석에 "셋을 합치면 1,090px이라 928px을 넘는다"고 적혀 있었는데
       **다시 재보니 897px로 들어간다**(2026-08-31 실측). 그 사이 글꼴이 바뀌었다.
       ⇒ **낡은 측정값을 근거로 남겨 두면 안 되는 일을 안 된다고 믿게 된다.**
    ⚠️ 그래도 여유가 크지 않아 가운뎃점(` · `)으로 잇고 **`상승`을 뺐다** — 세 줄일
       때는 "상승 조건 다수"가 자연스러웠지만 한 줄에서는 같은 말이 두 번 나온다.
    ⚠️ 글꼴은 **26px 그대로다.** `check_layout`이 26px 미만을 막으므로 줄일 수 없고,
       줄일 필요도 없었다.
    """
    # ⚠️⚠️ **시안대로 색을 뺐다** (2026-09-11).
    #    시안 `chips`: `font-size:24px;line-height:1.3;color:#4b4740` —
    #    이모지 + **이름만 볼드** + 설명. 등급 색을 글자에 칠하지 않는다.
    #    (등급 색은 종목 줄의 「🟢 주목」에서만 쓴다)
    return ('<div style="display:flex;flex-wrap:wrap;align-items:baseline;'
            'gap:6px 18px">'
            + "".join(
                f'<span style="flex:none;font-size:24px;line-height:1.3;'
                f'color:{C["text2"]}">{e} <b>{w}</b> '
                f'{d.replace("상승 ", "")}</span>'
                for e, w, d in GRADE_HELP)
            + '</div>')


# ⚠️ **D-숫자는 "며칠 남았나"다.** 임박할수록 진하게 — 색이 곧 급함의 척도다(2026-08-28).
_D = re.compile(r'(D-(\d+)|오늘)')


def dcolor(text):
    def _s(m):
        if m.group(0) == "오늘":
            return f'<b style="color:{C["up"]}">오늘</b>'
        # ⚠️ 금색은 베이지 바탕에서 눈에 안 띈다(2026-08-28 지적). 두 단계로 줄인다 —
        #    **오늘·내일이면 빨강, 그 뒤는 전부 파랑.** 급한지 아닌지만 갈리면 된다.
        d = int(m.group(2))
        c = C["up"] if d <= 1 else C["blue"]
        return f'<b style="color:{c}">{m.group(0)}</b>'
    return _D.sub(_s, str(text or ""))


def sector_rows(sectors, size=26):
    r"""**섹터 흐름** — 어제 어느 업종·테마가 올랐는지.

    후보 종목이 왜 그 업종에서 나왔는지를 이걸 보면 설명 없이 알 수 있다.
    """
    # ⭐ 지시서 2절 — 업종도 **3칸 블록**이다 (`kv`).
    #    칸 이름 29px #6b665c · 값 42px/800/-.035em · gap:22px · 2·3번째에 세로선
    return ('<div style="display:flex;gap:22px">'
            + "".join(
                f'<div style="flex:1;min-width:0;'
                f'{"" if not i else f"border-left:{KV_DIVIDER};padding-left:{KV_PAD_L}px;"}">'
                f'<div style="font-size:29px;color:{C["faint"]};'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                f'{x.get("이름")}</div>'
                # ⚠️ `line-height:1` 은 정본 값이라 그대로 두되, **아래 4px**을 준다.
                #    이 칸이 04 카드의 **마지막 항목**이라 글자 꼬리(descender)가
                #    카드 아래 숨 자리를 4px 파고들어 88px 로 잡혔다(하한 90)
                f'<div style="font-size:42px;font-weight:800;letter-spacing:-.035em;'
                f'line-height:1;margin-top:8px;padding-bottom:4px;'
                f'color:{sign_color(x.get("등락률"))}">'
                f'{pct(x.get("등락률"))}</div></div>'
                for i, x in enumerate(sectors[:3]))
            + '</div>')


# ── 카드 7종 ────────────────────────────────────────────────────
def c01_cover(o, cp, num, total):
    dt = datetime.strptime(o["date"], "%Y-%m-%d")
    picks = o.get("picks") or []
    # ⭐⭐ **목차는 세로 6줄**이다 (2026-09-11 · 시안).
    #    전에는 3열 격자에 번호 + 제목만 있었다. 시안은 한 줄에
    #    「번호 · 제목 ……… 그 장의 물음」이고 줄마다 위에 구분선이 있다.
    #    물음이 있어야 **무엇을 보게 되는지** 알고 넘긴다
    # ⭐ 2026-09-11 디자인 답 ④ — **문구 확정.** 지어내지 않는다
    _TOC = (("뉴스", "밤사이 무슨 일이 있었나"),
            ("국면", "지금 시장은 어디쯤인가"),
            ("수급", "누가 사고 누가 팔았나"),
            ("일정", "이번 주에 무엇을 볼까"),
            ("기관", "전문가는 뭐라고 하나"),
            ("액션", "오늘의 기회는 어디에 있나"))
    toc = "".join(
        f'<div style="display:flex;align-items:baseline;gap:22px;'
        f'border-top:1px solid {C["line"]};padding:22px 0">'
        f'<span style="font-size:26px;color:#8a7038;font-weight:700">{i:02d}</span>'
        f'<span style="font-size:38px;font-weight:700">{t}</span>'
        f'<span style="margin-left:auto;font-size:28px;color:{C["faint"]}">{s}</span>'
        f'</div>'
        for i, (t, s) in enumerate(_TOC, 1))
    # ⭐⭐ **시안 그대로** (2026-09-11 · confirmed-design-source.dc.html).
    #    위 = 로마자 캡션 + 제목 + 부제 + 날짜 · 가운데 = 목차 · 아래 = 넘겨서 보기
    #    `justify-content:space-between` 이라 남는 자리는 **셋 사이로** 갈린다
    inner = (
        f'<div style="display:flex;flex-direction:column;gap:18px">'
        f'<span style="font-size:28px;font-weight:700;letter-spacing:.24em;'
        f'color:{C["faint"]}">MORNING BRIEFING</span>'
        # 표지 제목은 첫 낱말 뒤에서 줄을 바꾼다("깜댕의 / 주식 브리핑")
        f'<span style="font-size:126px;font-weight:800;letter-spacing:-.05em;'
        f'line-height:1.05">{BRAND.replace(" ", "<br>", 1)}</span>'
        f'<span style="font-size:40px;line-height:1.5;color:{C["text2"]}">'
        f'{cp.get("부제", "3분 만에 읽는 어제와 오늘의 시장")}</span>'
        f'<span style="font-size:32px;font-weight:700;color:#8a7038">'
        f'{dt.strftime("%Y.%m.%d")} {WEEKDAY[dt.weekday()]}요일 · '
        f'후보 {len(picks)}</span></div>'

        f'<div style="display:flex;flex-direction:column">{toc}</div>'

        f'<div style="font-size:30px;color:{C["faint"]}">넘겨서 보기 →</div>'
    )
    # ⚠️⚠️ **배경 아트워크와 장식 막대를 걷었다** (2026-09-11 · 시안).
    #    캔들차트가 목차 글씨와 겹쳐 읽기 나빴고, 시안 표지는 **바탕이 비어 있다**.
    #    `card_theme.ART` 자체는 남겨 둔다 — 되돌리려면 `art=True` 를 살린다
    # ⚠️ 표지는 머리글이 없어 본문 상자 좌우 패딩(18)이 그대로 글을 밀어
    #    왼쪽 98px 이 된다. 지시서 7절은 **왼쪽 80** 이다 -> 표지만 여백을 끈다
    return card(inner, "00 표지", frame=False, art=False, spread=True,
                여백=False, 바닥=3)


def c02_news(o, cp, num, total):
    us = cp.get("미장뉴스") or []
    kr = cp.get("국장뉴스") or []
    snap = _snap(o["date"], "fetch_us")
    idx = snap.get("지수") or {}
    fut = snap.get("선물원자재") or {}
    # ⚠️ 칸 안에는 **수치까지만.** 해석은 칸마다 쪼개지 않고 아래 한 문단으로 모은다
    #    (2026-08-27 요청). 세 칸에 각각 설명을 넣었더니 같은 말이 세 번 나뉘어
    #    오히려 안 읽혔다.
    cells = []
    # ⚠️⚠️ **셋째 칸은 다우존스**다 (2026-09-11 사용자 결정:
    #    「시안 카드 01 를 S&P 500 · 나스닥 100 · 다우존스로 가자」).
    #    시안 원본은 나스닥 선물이었는데, 다우가 브리핑 어디에도 없다는
    #    지적이 나와 수집기(`fetch_us.INDICES`)에 `^DJI` 를 더하고 여기 넣었다.
    #    ⚠️ 홈 화면의 셋째는 **코스피**다 — 홈은 「밤사이 미국 둘 + 어제 한국」이고
    #       여기는 미국 셋이다. 일부러 다르다
    for nm, src, key in (("S&P 500", idx.get("S&P500"), "종가"),
                         ("나스닥 100", idx.get("나스닥100"), "종가"),
                         ("다우존스", idx.get("다우"), "종가")):
        if src and src.get(key) is not None:
            # ⚠️ **첫 칸에는 세로선이 없다** (명세 2절 `kv`)
            cells.append(stat_cell(nm, f'{src[key]:,}', src.get("등락률"),
                                   # ⭐ 2026-09-11 답 1 — 정본 시안의 실측값은 **50px** 이다.
                                   #    「52/56」은 어림이었고, 정확히는
                                   #    밤사이 지수 3칸 **50** · 코스피 종가 56 · 수급·업종 42
                                   #    ⚠️ 넘치면 **크기를 되돌리지 말고** lines 예산(32자)에서 줄인다 —
                                   #    지수 숫자는 이 카드에서 제일 먼저 읽히는 값이다
                                   big=50, first=not cells))
    strip = ""
    if cells:
        # ⚠️ 칸을 세로선으로 가르므로 `gap` 을 벌린다 — 선 왼쪽 22px 과 짝이다.
        #    전에는 칸마다 바탕을 깔아 12px 이면 충분했다
        # ⚠️ 지시서 3절 — 3칸 블록은 `display:flex; gap:22px` 다.
        #    격자(grid)로 두면 검사기가 3칸 블록으로 못 알아본다
        strip = ('<div style="display:flex;gap:22px">'
                 + "".join(cells) + "</div>")
    # ⚠️ 지수 셋을 묶은 한 문장은 **따로 항목**이다 (지시서 2절 「어젯밤 미국」).
    #    전에는 지수 블록에 붙여 놓아 두 내용이 한 덩이로 읽혔다
    요약 = first_sentence(cp.get("미장요약") or _us_gist(idx, fut), CUT["미장요약"])
    # ⚠️ **두 쪽에서 번갈아 뽑는다.** 예전엔 `(us + kr)[:3]`이었는데, 미장 뉴스가
    #    3건이 되자 **국장 뉴스가 통째로 밀려나** 카드 제목이 "미국·한국 뉴스"인데
    #    한국 뉴스가 한 건도 없었다(2026-08-27). 어느 한쪽이 길어져도 다른 쪽이
    #    사라지지 않게, 앞에서 자르지 말고 **번갈아** 집는다.
    # ⚠️ 카드는 **요약**이다 — `머리`만 싣고 `몸`은 세로형에 맡긴다(2026-08-27 합의).
    #    예전엔 몸까지 넣느라 3건밖에 못 실었고, 그래서 국장 뉴스가 통째로 밀려났다.
    #    이제 머리만 싣기 때문에 양쪽을 **다 실을 수 있다** — 자르지 않는다.
    def group(label, items):
        _어느 = "미장뉴스" if "미국" in label else "한국뉴스"
        if not items:
            return ""
        # ⭐⭐ **글머리 기호와 볼드를 걷었다** (2026-09-11 · 시안).
        #    시안의 `lines` 블록은 「문장을 줄 단위로 쌓음」일 뿐이다 —
        #    가운뎃점도 굵은 글씨도 없다. 명세 7절이 「숫자에 볼드·형광·밑줄
        #    강조」를 막는 것과 같은 뜻이다: 다 굵으면 **아무것도 안 도드라진다**
        rows = ('<div style="display:flex;flex-direction:column;gap:6px">'
                + "".join(
                    f'<span style="font-size:31px;line-height:1.6;'
                    f'color:{C["text2"]};word-break:keep-all">'
                    f'{n.get("머리","")}</span>'
                    # ⭐ 건수 예산 §2·§3 — 미장·국장을 따로 센다
                    for n in items[:건수[_어느]])
                + 남은줄(max(0, len(items) - 건수[_어느]))
                + '</div>')
        return block(label, "", rows)

    # ⭐⭐ **지시서 2절 블록 순서**: 밤사이 지수(3칸) -> 어젯밤 미국(문단)
    #    -> 미국 증시(줄목록) -> 한국 증시(줄목록). 네 항목 전부 `block()` 이라
    #    첫 항목 빼고 **전부 구분선**이 붙는다
    inner = (head(SEC["뉴스"], "뉴스", pg(num, total), "밤사이 무슨 일이 있었나")
             + block("밤사이 지수", "", strip, top=0)
             + block("어젯밤 미국", "",
                     f'<div style="font-size:31px;line-height:1.6;'
                     f'color:{C["text2"]};word-break:keep-all">{요약}</div>')
             + group("미국 증시", us)
             + group("한국 증시", kr))
    return card(inner, "01 뉴스")


def c03_regime(o, cp, num, total):
    reg = o.get("market_regime") or {}
    kv = reg.get("kospi_vs_sma20_pct")
    band = reg.get("band", "")
    pos = 50 + max(-50, min(50, (kv or 0) * 5))
    # ⚠️⚠️ **국면색은 국면을 따라간다** (2026-08-31). 금색은 어느 국면에서나 같아서
    #    **색이 아무 말도 안 하고 있었다.** 위로 뜬 것은 상승색, 아래로 처진 것은 하락색.
    #    ⚠️ 세로 상세(`build_scroll`)만 고치고 여기를 빼먹어 한 번 더 지적받았다
    #       ("가로든 세로든 황금색이야"). **같은 뜻은 두 화면에서 같은 색이어야 한다.**
    band = band_label(band)          # ⚠️ 세로와 **같은 함수**를 쓴다
    국면색 = band_color(band)
    # ⭐ 3구간 띠에서 **몇 번째 칸**을 채울까 (0 눌림 · 1 평균 · 2 과열).
    #    라벨 글자로 고른다 — `band_label` 이 이미 셋 중 하나로 줄여 준다
    _몇 = 2 if "과열" in band else (0 if "눌림" in band else 1)
    def lst(items, _fs=BODY_FS, _lh=BODY_LH, _몇=3):
        # ⚠️ 카드는 **첫 문장만** 쓴다. 원본은 세로 상세용으로 길게 적혀 있다 —
        #    글자 수로 자르면 "올라 값…"처럼 말을 하다 만다(2026-08-28).
        # ⚠️ 지시서 `lines` 블록 — 글머리표 없이 **줄 단위로 쌓는다**
        return "".join(
            f'<span style="font-size:{_fs}px;line-height:{_lh};'
            f'color:{C["text2"]};word-break:keep-all">'
            f'{first_sentence(x, CUT["반영"])}</span>'
            # ⚠️⚠️ **3줄을 지킨다.** 2줄로 줄였더니 「시장 이미 반영」·「미반영」이
            #    한 줄씩 사라졌다 — 간격을 맞추려고 **내용을 버린 것**이라 되돌렸다
            #    (2026-09-11 사용자 지적: 「내용에 영향 주는 게 있는지 확인해봐」)
            # ⭐ 건수 예산 §2·§3 — 3줄이 기본, 넓으면 4줄 · 좁으면 그대로
            for x in (items or [])[:_몇])
    # ⭐⭐ **지시서 2절 블록 순서** (2026-09-11):
    #    코스피 20일선 대비(큰 수치 + 띠) -> 무슨 뜻인가 -> 시장 이미 반영 -> 시장 미반영
    #    ⚠️ 전에는 큰 수치·띠·구간 라벨이 **각각 따로** 놓여 항목이 여섯이 됐고,
    #       그래서 항목 간격이 14~28px 로 붙었다(하한 40). **한 항목으로 묶는다**
    _띠 = ('<div style="display:flex;gap:10px;height:38px">'
           + "".join(f'<div style="flex:1;border-radius:9px;background:'
                     f'{국면색 if _q == _몇 else C["line"]}"></div>'
                     for _q in range(3))
           + '</div>'
           + f'<div style="display:flex;font-size:28px;color:{C["faint"]};'
             f'margin-top:14px">'
           + "".join(f'<span style="flex:1;{_맞}'
                     f'{f"color:{국면색};font-weight:700" if _i == _몇 else ""}">'
                     f'{_라}</span>'
                     for _i, (_라, _맞) in enumerate(
                         (("눌림", ""), ("평균", "text-align:center;"),
                          ("과열", "text-align:right;"))))
           + '</div>')
    _큰 = (f'<div style="display:flex;align-items:flex-end;gap:22px;'
           f'margin-bottom:14px">'
           f'<span style="font-size:100px;font-weight:800;line-height:1;'
           f'color:{국면색};letter-spacing:-.05em">{pct(kv)}</span>'
           f'<span style="font-size:36px;font-weight:700;color:{국면색};'
           f'padding-bottom:12px">{band}</span></div>')
    # ⭐⭐ **본문은 31px 이다** (FINAL-CARDS §5). 전에 간격을 맞추려고
    #    29 -> 27 까지 내렸던 것이 남아 있었다 — **하한 29 밑이라 위반**이다.
    #    이제 넘치면 크기가 아니라 **§2 줄이는 순서**로 흡수한다
    #    (시장국면 96 -> 80 · 반영/미반영 32 -> 26)
    # ⭐ 기본은 31px. 3순위가 걸리면 29px (2026-09-11 디자인 답 ⓐ)
    _fs = 국면본문[0]
    _lh = BODY_LH if _fs >= BODY_FS else 1.55
    inner = (head(SEC["국면"], "국면", pg(num, total), "지금 시장은 어디쯤인가")
             + block("코스피 · 20일 평균선 대비", "", _큰 + _띠, top=0)
             + block("무슨 뜻인가", "",
                     f'<div style="font-size:{_fs}px;line-height:{_lh};'
                     f'color:{C["text2"]};word-break:keep-all">'
                     f'{first_sentence(cp.get("시장국면"), CUT["시장국면"])}</div>')
             # ⚠️ `sub=` 는 **라벨이 무슨 뜻인지** 말해 주는 줄이다. 블록을
             #    다시 짜면서 빠뜨렸다가 되살렸다 (2026-09-11 내용 대조에서 발견)
             + block("시장 이미 반영", "",
                     f'<div style="display:flex;flex-direction:column;gap:6px">'
                     f'{lst(cp.get("이미반영"), _fs, _lh, 건수["이미반영줄"])}</div>',
                     sub="주가가 이미 올라 지금 들어가기엔 늦은 것")
             + block("시장 미반영", "",
                     f'<div style="display:flex;flex-direction:column;gap:6px">'
                     f'{lst(cp.get("미반영"), _fs, _lh, 건수["미반영줄"])}</div>',
                     sub="좋은 소식은 나왔는데 주가에 아직 안 붙은 것"))
    return card(inner, "02 국면")


def c04_flows(o, cp, num, total):
    mk = (_snap(o["date"], "fetch_market") or {}).get("summary") or {}
    kospi = mk.get("코스피") or {}
    dep = mk.get("예탁금") or {}
    # 섹터 흐름 — 어제 어느 업종·테마로 돈이 몰렸는지. 후보 종목이 왜 그 업종인지를
    # 여기서 설명 없이도 알 수 있다(2026-08-27 추가 요청).
    # ⭐ 건수 예산 §2·§3
    _업n = 건수["업종테마"]
    sectors = ((mk.get("업종랭킹") or [])[:_업n]
               + (mk.get("테마랭킹") or [])[:1])[:_업n]
    dv, dd = _f(dep.get("투자자예탁금_억원"), 0), _f(dep.get("전일대비_억원"), 0)
    # ⚠️ **외국인·기관·개인 순매수는 스냅샷에 없다.** `fetch_market --summary`가 주는 건
    #    코스피/예탁금/업종·테마 랭킹/외국인 순매수 *상위 종목*까지고, 투자자별 **금액**은
    #    없다. 그래서 브리핑 본문에 쓴 값을 `card-copy`의 `수급`에 받아 적는다.
    #    2026-08-27에 이 세 값이 코드에 박혀 있었다 — 그날은 맞았지만 **다음 날부터
    #    전부 거짓말**이 된다. 값이 없으면 칸을 그리지 않는다. 지어내지 않는다.
    fl = (cp.get("수급") or [])[:3]
    flows_box = ""
    if fl:
        cells = ""
        for x in fl:
            fc = {"up": C["up"], "down": C["down"]}.get(x.get("부호"), C["muted"])
            # ⚠️ 바탕을 깔아 세 칸이 갈리게 한다 — 테두리만으로는 카드 바탕에 묻혔다.
            # ⭐ 명세 2절 `kv` — 바탕 상자 대신 **칸 사이 세로선**
            cells += (f'<div style="flex:1;min-width:0;'
                      f'{"" if not cells else f"border-left:{KV_DIVIDER};padding-left:{KV_PAD_L}px;"}">'
                      + kicker(x.get("주체", ""), C["muted"], 26)
                      + '<div style="height:10px"></div>'
                      f'<div style="font-size:34px;font-weight:700;'
                      f'color:{fc}">{x.get("값","")}</div></div>')
        # ⚠️ 지시서 3절 — 3칸 블록은 `display:flex; gap:22px`
        flows_box = f'<div style="display:flex;gap:22px">{cells}</div>'
    # ⭐⭐ **지시서 2절 블록 순서** (2026-09-11):
    #    코스피(행) -> 누가 사고팔았나(3칸) -> 읽는 법(문단)
    #    -> 투자자 예탁금(행) -> 어제 오른 업종·테마(3칸)
    #    행 블록(지시서 3절): 왼쪽 설명 29px #6b665c + 오른쪽 값 56px/800 + 등락 33px/700
    def _행(설명, 값, 등락색, 등락):
        return (f'<div style="display:flex;align-items:flex-end;'
                f'justify-content:space-between;gap:20px">'
                f'<span style="font-size:29px;line-height:1.5;'
                f'color:{C["faint"]}">{설명}</span>'
                f'<span style="flex:none;display:flex;align-items:baseline;gap:16px">'
                f'<span style="font-size:56px;font-weight:800;'
                f'letter-spacing:-.04em">{값}</span>'
                f'<span style="font-size:33px;font-weight:700;'
                f'color:{등락색}">{등락}</span></span></div>')

    inner = (head(SEC["수급"], "수급", pg(num, total), "돈은 어디로 움직였나")
             + block("코스피", "",
                     _행("어제 종가", kospi.get("지수", "·"),
                         sign_color(_f(kospi.get("등락률"), 0)),
                         pct(kospi.get("등락률"))), top=0)
             + block("누가 사고팔았나", "", flows_box)
             + block("읽는 법", "",
                     f'<div style="font-size:31px;line-height:1.6;'
                     f'color:{C["text2"]};word-break:keep-all">'
                     f'{first_sentence(cp.get("수급해설"), CUT["수급해설"])}</div>')
             + block("투자자 예탁금", "",
                     _행("주식을 사려고 증권계좌에 넣어 둔 대기 자금",
                         f'{dv/10000:.1f}조', sign_color(dd),
                         signed(dd / 10000, 1, "조")))
             + block("어제 오른 업종·테마", "", sector_rows(sectors)))
    return card(inner, "03 수급", 바닥=3)


def c05_calendar(o, cp, num, total):
    # ⚠️ 항목마다 **바탕을 깔아** 나눈다(2026-08-27 요청). 줄만으로는 어디서 끊기는지
    #    안 보였다. 오늘 것은 파란 왼쪽 막대로 한 번 더 도드라지게 한다.
    rows = ""
    _일정전부 = sorted((cp.get("캘린더") or []),
                       key=lambda y: "오늘" not in y.get("when", ""))
    # ⭐ 건수 예산 — 40px 미만인 날만 3 -> 2 로 내려간다 (2026-09-11 답 1절 ②)
    #    ⚠️ **일정 한 건의 46자는 건드리지 않는다** (디자인 지시)
    items = _일정전부[:건수["일정"]]
    # ⚠️⚠️ **색 막대와 D-숫자 색을 걷었다** (2026-09-11 · 시안).
    #    시안 `cal` 블록은 「날짜 · 제목 · 설명」이 전부다 — 왼쪽 막대도,
    #    오늘만 파랗게 칠하는 것도 없다. 오늘 것은 **맨 위에 오는 것**으로 안다
    #    (이미 `sorted` 로 오늘을 앞에 둔다)
    # ⚠️ 일정 **한 건이 한 항목**이다 (지시서 2절). 셋을 한 덩이로 묶으면
    #    항목이 둘뿐이라 사이가 189px 로 벌어진다
    for i, x in enumerate(items):
        rows += (f'<div style="padding-top:{BLOCK_PAD}px;'
                 f'border-top:{BLOCK_RULE};'
                 f'display:flex;flex-direction:column;gap:8px">'
                 f'<span style="font-size:28px;color:{C["faint"]}">'
                 f'{x.get("when","")}</span>'
                 f'<span style="font-size:35px;font-weight:700;color:{C["text"]};'
                 f'line-height:1.35;letter-spacing:-.02em">{x.get("what")}</span>'
                 f'<span style="font-size:29px;color:{C["text2"]};line-height:1.5;'
                 f'word-break:keep-all">'
                 f'{first_sentence(x.get("note",""), CUT["일정"])}</span></div>')
    # ⭐ 지시서 2절 — 이번 주 핵심(문단) -> 일정 3건
    # ⭐ 잘린 건수는 **그 블록 안**에 알린다 (FINAL-CARDS §4).
    #    ⚠️ 일정은 **한 건이 한 항목**이라 뒤에 그냥 붙이면 **새 항목**이 되고
    #       구분선이 없어 §6-7 에 걸린다. **마지막 칸 안**에 넣는다
    _남 = 남은줄(len(_일정전부) - len(items))
    if _남 and rows.endswith("</div>"):
        rows = rows[:-len("</div>")] + _남 + "</div>"
    inner = (head(SEC["일정"], "일정", pg(num, total), "무엇이 시장을 흔들 수 있나")
             + block("이번 주 핵심", "",
                     f'<div style="font-size:31px;line-height:1.6;'
                     f'color:{C["text2"]};word-break:keep-all">'
                     # ⭐ 2026-09-11 디자인 답 1 — **고정 100자**
                     f'{cut(str(cp.get("캘린더해설", "") or ""), CUT["캘린더해설"])}'
                     f'</div>', top=0)
             + rows
             # ⚠️ 꼬리말도 블록을 다시 짜면서 빠뜨렸다 (2026-09-11 대조에서 발견)
             + f'<div style="border-top:{BLOCK_RULE};padding-top:{BLOCK_PAD}px;'
               f'font-size:25px;color:{C["faint"]}">'
               f'※ 중요도 최상 등급 지표만 추렸습니다</div>')
    return card(inner, "04 일정", 바닥=3)


def c06_opinion(o, cp, num, total):
    rows = ""
    # 카드는 요약 — **점수를 실제로 움직인 것 2건**만. 나머지는 세로형에서 본다.
    ops = sorted((cp.get("의견") or []), key=lambda y: y.get("부호", "flat") == "flat")
    # ⚠️ 항목마다 바탕을 깔고, 목표주가를 올렸나 내렸나를 **왼쪽 막대 색**으로 표시한다.
    _리n = 건수['리포트']
    for i, x in enumerate(ops[:_리n]):
        tone = x.get("부호", "flat")
        col = {"up": C["up"], "down": C["down"], "flat": C["muted"]}[tone]
        # ⚠️⚠️ **색 막대도 색 글자도 걷었다** (2026-09-11 · 시안).
        #    전에는 목표주가 상향/하향을 **왼쪽 빨강·파랑 막대**로 표시했는데,
        #    명세 7절이 막는 「상승 빨강 / 하락 파랑을 **등락 아닌 뜻으로** 쓰기」가
        #    정확히 이 경우다. 등락률이 아니라 「의견의 방향」이라 같은 색을 쓰면
        #    숫자 색과 뜻이 섞인다.
        #    시안 `report` 블록: 인용 32px #1c1813 · 코멘트 28px #6f6a60. 색 없음
        rows += (f'<div style="padding-top:{BLOCK_PAD if i else 0}px;'
                 f'{f"border-top:{BLOCK_RULE};" if i else ""}'
                 f'display:flex;flex-direction:column;gap:9px">'
                 f'<div style="display:flex;gap:12px;align-items:baseline">'
                 f'<span style="font-size:28px;color:{C["faint"]}">{x.get("날짜")}</span>'
                 f'<span style="font-size:28px;color:{C["faint"]}">{x.get("사")}</span>'
                 f'<span style="font-size:29px;font-weight:700;color:{C["text"]}">'
                 f'{x.get("종목")}</span></div>'
                 f'<div style="font-size:32px;line-height:1.55;color:{C["text"]};'
                 f'word-break:keep-all">"{tint_pct(x.get("말"))}"</div>'
                 f'<div style="font-size:28px;line-height:1.5;color:{C["faint"]};'
                 f'word-break:keep-all">→ {tint_pct(x.get("뜻"))}</div></div>')
    # ⭐ 지시서 2절 — 보는 법(문단) -> 리포트 2건 -> 애널리스트 컨센서스(문단)
    inner = (head(SEC["기관"], "기관", pg(num, total), "증권가는 뭐라고 했나")
             + block("보는 법", "",
                     f'<div style="font-size:31px;line-height:1.6;'
                     f'color:{C["text2"]};word-break:keep-all">'
                     f'{first_sentence(cp.get("의견해설"), CUT["의견해설"])}</div>', top=0)
             + block("리포트", "", rows + 남은줄(len(ops) - _리n))
             + block("애널리스트 컨센서스", "",
                     f'<div style="font-size:31px;line-height:1.6;'
                     f'color:{C["text2"]};word-break:keep-all">'
                     f'{first_sentence(cp.get("컨센서스"), CUT["컨센서스"])}</div>'))
    return card(inner, "05 기관")


def _조건여유(r):
    r"""판정이 **얼마나 아슬아슬한가** — 조건선에서 몇 % 떨어져 있나 (2026-08-31 신설).

    ⚠️⚠️ 왜 필요한가: 판정만 보면 `+0.07%로 겨우 넘은 것`과 `+23%로 훌쩍 넘은 것`이
       **똑같이 「조건충족」**으로 보인다. 실제로 2026-08-25 엘에스일렉트릭은
       조건선 195,265원에 현재가 195,400원 — **0.07% 차이로 갈렸다.**
       한 시간 뒤에 쟀으면 반대 판정이 나왔을 값이다.
       ⚠️ 20건을 재보니 조건선 ±2% 안이 3건(15%)이었다. 나머지 85%는 시각과 무관하다.
          **그 15%를 눈에 보이게 하는 것**이 이 함수가 하는 일이다.

    ⚠️ **판정을 바꾸지 않는다.** 아슬아슬하다고 「보류」로 내리지 않는다 —
       그건 사람이 볼 일이다. 화면은 사실만 말한다.

    반환: (퍼센트, 아슬아슬한가) 또는 None
    """
    쌍 = [( (c.get("actual") - c.get("value")) / c.get("value") * 100 )
         for c in (r.get("conditions") or [])
         if c.get("value") and c.get("actual")]
    if not 쌍:
        return None
    # 충족이면 **가장 빠듯한 것**, 미충족이면 **0에 가장 가까운 것**을 보여준다.
    d = min(쌍) if all(x >= 0 for x in 쌍) else max(x for x in 쌍 if x < 0)
    return round(d, 2), abs(d) < 2


def _전일픽(cp):
    """어제 후보 성적 — 마지막 액션 카드 맨 끝. 한 줄에 흘려 쓴다."""
    xs = cp.get("전일픽") or []
    if not xs:
        return ""
    # ⚠️⚠️ **판정은 글자로 쓴다** (2026-08-31 사용자 선택). 한때 기호(✅⚖️❌)로 줄였는데
    #    **"⚖️가 무슨 뜻인지 직관적으로 모르겠다"**는 지적을 받았다. 맞는 말이다 —
    #    기호는 자리를 아끼지만 **뜻을 배워야** 읽힌다. 아침에 폰으로 훑는 화면에서
    #    배워야 읽히는 표시는 안 읽히는 것과 같다.
    #    ⚠️⚠️ **판정 값은 넷이다: 적중 · 빗나감 · 놓침 · 보합** (2026-09-01 개정).
    #       「지수 하회」는 폐지했다 — 초과수익률로 재면 그 개념이 판정에 이미 들어 있다.
    #       **「놓침」이 새로 생겼다**: 🟡로 낮게 봤는데 시장보다 오른 경우다.
    #       ⚠️ 규칙은 `SKILL.md`의 「전일픽 판정 규칙」이 정본이다. 여기서 다시 정하지 않는다.
    부호색 = {"up": C["up"], "down": C["down"]}
    조각 = [f'<span style="flex:none;display:flex;align-items:baseline;gap:10px">'
           f'<span style="font-size:26px;font-weight:700">{x.get("종목", "")}</span>'
           f'<span style="font-size:26px;font-weight:700;'
           f'color:{부호색.get(x.get("부호"), C["faint"])}">{x.get("결과", "")}</span>'
           f'<span style="font-size:24px;color:{C["faint"]}">'
           f'{x.get("판정", "")}</span></span>'
           for x in xs[:4]]
    # ⚠️ 제목을 **줄 안으로** 넣는다. 별도 제목 줄을 두면 40px가 더 드는데,
    #    액션 카드에는 그만한 자리가 없다(실측: 제목 있으면 139px, 없으면 95px).
    # ⚠️⚠️ **같은 덩이 안에 20px 아래**다 (2026-09-11 지시서 0절 ⑦ · 3절).
    #    전에는 위에 줄(`border-top`)을 그어 **별도 항목처럼** 떼어 놨다.
    #    지시서: 「어제 후보는 같은 덩이 안 20px 아래 · 라벨 25px/700 #8a7038 ·
    #    항목: 종목 26px/700 + 등락 26px/700(색) + 결과 24px #6b665c」
    return ('<div style="display:flex;flex-wrap:wrap;align-items:baseline;'
            'gap:8px 20px;padding-top:20px">'
            f'<span style="flex:none;font-size:25px;font-weight:700;'
            f'color:#8a7038">어제 후보</span>' + "".join(조각) + '</div>')


def _진입판정(date):
    r"""그날 **09:05 진입체크 판정**. 없으면 빈 목록.

    ⚠️⚠️ 이게 왜 카드에 있나(2026-08-31): 카카오를 폐지하면서 09:05 판정의 출구가
       사라졌다. 세로 상세 맨 위에 띠로 붙여 봤는데 **상세라는 취지와 안 맞았다**.
       ⇒ 가로 요약의 「장 시작 후 확인」을 **그 결과로 갈아 끼운다.**
          아침엔 "9시에 무엇을 볼지" 체크리스트이고, 09:05이 지나면 "어떻게 됐나"다.
          **같은 자리에서 질문이 답으로 바뀐다** — 자리를 새로 만들지 않아도 된다.

    ⚠️ 새로 계산하지 않는다. `entry-check-log.jsonl`에 저장된 그 판정을 그대로 옮긴다.
    """
    path = os.path.join(_DATA, "entry-check-log.jsonl")
    if not os.path.exists(path):
        return []
    rec = None
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if o.get("date") == date and o.get("ok") and o.get("slot", "0905") == "0905":
            rec = o
    return (rec or {}).get("results") or []


def _pick_block(p, idx, me, first_on_card=True):
    r"""후보 한 종목 — 이름·등급 + **긍정/부정 신호** + 기준가.

    ⚠️ 한 장에 **둘까지만** 올린다(`PICKS_PER_CARD`). 넷을 넣으면 글자가 19px까지
       내려가 확대해야 읽히고, 하나만 넣으면 카드가 10장이 된다. 둘이 가운데다.
    ⚠️ 배경색 박스를 쓰지 않는다 — 색은 "긍정 신호"·"부정 신호" 라벨 글자에만 준다.
    """
    col, word = GRADE.get(p["grade"], (C["muted"], ""))
    entry = ""
    for c_ in (p.get("entry_conditions") or [])[:1]:
        nm = {"sma20": "20일선", "sma60": "60일선", "support": "지지선",
              "resistance": "저항선"}.get(c_.get("type"), c_.get("type"))
        if c_.get("value") is not None:
            entry = f'{nm} {int(c_["value"]):,}원'

    def sig(lab, txt, lc, _fs=29, _lh=1.55):
        """긍정·부정을 왼쪽 색 막대로 가른다 — 색은 옅게, 라벨 글자만 진하게."""
        if not txt:
            return ""
        # ⚠️⚠️ **색 박스도 색 막대도 쓰지 않는다** (2026-09-11 · 시안 「반복 금지」①).
        #    「긍정/부정 신호를 분홍·파랑 색 박스로 감쌌다 → 색 박스 없음.
        #     구분은 **라벨 색 + 얇은 줄**뿐이다.」
        #    한 장에 색 박스가 둘이면 카드가 알록달록해져 정작 종목 이름이 안 보인다
        # ⚠️ `margin-top` 을 뺐다 (2026-09-11 지시서 2절). 항목 경계는
        #    `border-top + padding-top:18` **뿐**이다. margin 이 붙어 있으면
        #    `space-between` 이 나눠 준 간격 위에 22px 이 더해져 **이 항목 앞만
        #    넓어지고** 마지막 간격이 43px 로 좁아진다(65,65,43)
        return (f'<div style="padding-top:{BLOCK_PAD}px;'
                f'border-top:{BLOCK_RULE};'
                f'display:flex;flex-direction:column;gap:10px">'
                f'<span style="font-size:26px;color:{lc};font-weight:700;'
                f'letter-spacing:{LS_KO}">{lab}</span>'
                f'<span style="font-size:{_fs}px;line-height:{_lh};'
                f'color:{C["text2"]};word-break:keep-all">{txt}</span></div>')

    return (
        # 종목 사이는 **굵은 줄**로 나눈다 — 신호가 여러 줄이라 얇은 줄로는 안 갈린다.
        # ⚠️ 이 선은 **종목 사이를 가르는** 것이지 제목 밑줄이 아니다. 첫 종목에까지
        #    그리면 제목 바로 아래에 띠가 생겨, 참고사항 상자가 있는 첫 장과
        #    없는 둘째 장의 제목 모양이 달라진다(2026-08-28 지적).
        # ⚠️ 이 선은 **종목 사이를 가르는** 것이지 제목 밑줄이 아니다. 한 장의 첫 종목에
        #    그리면 제목 바로 아래에 띠가 생겨, 다른 장 제목과 모양이 달라진다.
        #    `idx`는 전체 순번이라 둘째 장(idx=2)에서 선이 되살아났다 — 장 기준으로 본다.
        # ⚠️⚠️ **항목을 평평하게 편다** (2026-09-11 지시서 2절).
        #    「06 액션 1/2: 종목 -> 긍정 신호 -> 부정 신호 -> [등급칩 …]」
        #    전에는 셋을 `<div>` 하나로 감싸 **본문 상자의 직계 자식이 하나**였고,
        #    그래서 검사기가 항목 간격을 못 쟀다. 각각을 형제로 올린다
        f'<div style="{"" if first_on_card else f"border-top:{BLOCK_RULE};padding-top:{BLOCK_PAD}px;"}'
        f'display:flex;flex-direction:column;gap:12px">'
        # ⚠️ 지시서 3절 — 이름 46px/800/-.035em · 코드 27px #6b665c ·
        #    등급 `margin-left:auto` 30px/700 **색만** (배지 아님)
        + (f'<div style="display:flex;gap:18px;align-items:baseline">'
           f'<span style="font-size:46px;font-weight:800;color:{C["text"]};'
           f'letter-spacing:-.035em">{p["name"]}</span>'
           f'<span style="font-size:27px;color:{C["faint"]}">{p["code"]}</span>'
           f'<span style="margin-left:auto;color:{col};font-size:30px;'
           f'font-weight:700;white-space:nowrap">{p["grade"]} {word}</span></div>')
        + (f'{numbers(p)}' if numbers(p) else "")
        + '</div>'
        # ⚠️ **비면 본문만 한 단계 키운다** (2026-09-11 지시). 첫 액션 장은
        #    내용이 적어 항목 간격이 118px(상한 93) 까지 벌어졌다.
        #    문장을 늘리는 게 아니라 **글자만** 29 -> 31 로 올린다
        + sig("긍정 신호", first_sentence(me.get("강한신호"), CUT["신호"]),
              C["up"], 31 if first_on_card else 29, 1.6 if first_on_card else 1.55)
        + sig("부정 신호", first_sentence(me.get("고려할점"), CUT["신호"]),
              C["down"], 31 if first_on_card else 29,
              1.6 if first_on_card else 1.55)
        # ⚠️ **손절선과 발굴가를 같이 준다** (2026-08-28 재검토). `entry_conditions`에
        #    이미 들어 있는데 첫 조건 하나만 쓰고 버리고 있었다. 살지 말지 정하는
        #    자리에서 "어디서 물러날지"가 빠지면 요약으로서 쓸모가 반이다.

        # ⚠️⚠️ **핵심근거를 서술로 넣는다** (2026-08-31 요청: "공간이 남으면 서술형으로").
        #    예전 액션플랜 카드는 신호 두 줄(각 28자)과 숫자 한 줄이 전부라
        #    **아래 여백이 182px 남았다** — 한 장에 두 종목이던 시절 배치를 한 종목으로
        #    바꾸면서 자리만 벌어지고 내용은 그대로였다.
        #    "왜 이 종목인가"가 빠진 요약은 종목명만 던지는 것과 다르지 않다.
        # ⚠️⚠️ **「언제 사나」 문단을 뺐다** (2026-08-31 지적: "확인·손절·발굴 뜻을
        #    설명했으면 그걸 풀어 쓴 것밖에 안 된다"). 맞는 말이다 —
        #    숫자 줄에 이미 `확인 140,170 · 손절 128,000`이 있고 바로 아래 뜻풀이가 있는데,
        #    그 위에 "140,170원을 넘은 뒤에 매수를 검토합니다"를 또 쓰면 **같은 말 세 번**이다.
        #    ⇒ 그 자리는 **긍정·부정 신호를 늘려서** 채운다. 살 이유와 망설일 이유는
        #       숫자로 대체할 수 없는 유일한 내용이다.
        # ⚠️ 뜻풀이 문장은 **종목마다 반복하지 않는다.** 같은 설명을 네 번 쓰면
        #    카드가 넘친다(2026-08-28 실측: 08 액션플랜 여백 32px). 뜻은 카드 머리에
        #    한 번만 쓰고, 종목 줄에는 숫자만 둔다. 긴 설명은 세로 상세에 있다.
        # ⚠️ 종목 상자는 값선 뒤에서 이미 닫았다 — 여기서 또 닫지 않는다
        )


def 후보요약(o, cp):
    r"""**오늘 후보 전부**를 한 줄씩. 카드에 못 실은 종목까지 여기서 이름이라도 본다.

    ⚠️ 예전에는 이 자리에 `결론`("오늘은 사이버보안 하나가 눈에 띄고…") 같은 총평이
       있었다. 2026-08-28 지적으로 뺐다 — 카드에서 필요한 건 감상이 아니라
       **오늘 뭐가 있나**다. 뒤 장에 실리지 않는 종목도 여기서는 보인다.
    """
    # ⚠️⚠️ **2026-09-01 폐지 — 항상 빈 문자열을 돌려준다.**
    #    후보가 3개 이상인 날 이 목록이 마지막 액션 카드를 넘겼다(09-01 실측 **−25px**,
    #    후보 4종목 중 2종목이 여기 실렸다). 그리고 바로 위에 이미 이렇게 적혀 있다:
    #    **"오늘 후보 N종목 중 둘만 실었습니다. 나머지와 자세한 근거는 세로 상세에."**
    #    ⇒ **같은 말을 두 번 하면서 카드를 넘기고 있었다.** 안내 문장만 남긴다.
    #    ⚠️ 되살리려면 먼저 `tune_budget`으로 마지막 액션 카드 여백을 재라 —
    #       후보 4종목인 날에 25px 이상 남아야 한다.
    return ""
    picks = (o.get("picks") or [])[CARD_PICKS_MAX:]
    if not picks:
        return ""
    per = cp.get("종목") or {}
    rows = ""
    for i, p in enumerate(picks):
        col, word = GRADE.get(p["grade"], (C["muted"], ""))
        갭 = "".join("①②③④"[g - 1] for g in (p.get("gaps") or []) if 1 <= g <= 4)
        rows += (f'<div style="display:flex;gap:14px;align-items:baseline;'
                 f'margin-top:{8 if i else 0}px">'
                 f'<span style="font-size:29px;font-weight:700;color:{col};'
                 f'flex:none;white-space:nowrap">{p["grade"]} {p["name"]}</span>'
                 + (f'<span style="font-size:26px;color:{C["muted"]};flex:none">'
                    f'갭 {갭}</span>' if 갭 else "")
                 # ⚠️ 한 줄 **설명**은 뺐다(2026-08-28) — 넣으면 첫 액션 카드가 넘친다.
                 #    근거는 세로 상세에 있다.
                 + '</div>'
                 # ⚠️⚠️ 다만 **숫자는 넣는다**(2026-08-31). 예전엔 이름과 갭만 있어서
                 #    세 번째 후보는 **확인선도 손절선도 한 자리 없이** 나갔다.
                 #    "무엇이 더 있나"만 알려주고 **어디서 물러날지를 안 알려주는 것**이
                 #    요약으로서 제일 나쁜 형태다. 설명과 달리 숫자는 한 줄이라 안 넘친다.
                 + f'<div style="font-family:{MONO};font-size:26px;color:{C["muted"]};'
                   f'margin-top:4px">{numbers(p)}</div>')
    # ⚠️ **보조 정보는 상자, 종목 본문은 맨바닥** — 이게 액션플랜 카드의 규칙이다
    #    (2026-08-28). 성격이 다른 글이 같은 바탕에 이어지면 어디까지가 오늘의 결론이고
    #    어디부터가 참고인지 안 갈린다.
    return (f'<div style="margin-top:18px;padding-top:{BLOCK_PAD}px;'
            f'border-top:{BLOCK_RULE}">'
            + kicker("카드에 없는 나머지 후보", C["muted"], 26)
            + f'<div style="height:12px"></div>{rows}</div>')


def c07_action(o, cp, num, total, chunk=(), first=True, offset=0, last=True,
               part=1, parts=1, rest=0):
    r"""액션플랜. 후보가 셋 이상이면 **여러 장으로 쪼개진다**(`PICKS_PER_CARD`).

    `first`면 결론과 등급 설명을, `last`면 장초 확인 리스트를 얹는다.
    가운데 장은 종목만 싣는다 — 같은 문장을 장마다 반복하면 넘길 이유가 없어진다.
    """
    per = cp.get("종목") or {}
    # ⚠️⚠️ **마지막 장에 나머지 후보 목록이 붙는 날은 근거 문단을 뺀다** (2026-08-31).
    #    후보가 셋 이상이면 마지막 액션 카드에 "카드에 없는 나머지 후보"와 "장 시작 후
    #    확인"이 함께 들어간다. 거기에 근거 문단까지 얹으면 넘친다 —
    #    실측으로 08-28(후보 4개) 카드가 **−128px** 넘쳤다.
    #    ⚠️ 무엇을 뺄지가 문제인데, **나머지 후보 목록이 먼저다.** 그건 "오늘 뭐가 더
    #       있나"라서 다른 데 없지만, 근거는 세로 상세에 전문이 있다.
    rows = "".join(_pick_block(p, offset + i + 1, per.get(p["code"]) or {},
                               first_on_card=(i == 0))
                   for i, p in enumerate(chunk))
    lead = ""
    if first:
        # ⚠️ **등급 설명이 맨 위다** (2026-08-27 확정). 종목 배지를 보기 전에 읽어야
        #    무슨 뜻인지 안다 — 맨 끝에 두면 다 읽고 나서야 알게 된다.
        #    순서를 바꾸려면 `card_theme.py`의 레이아웃 정본을 먼저 고친다.
        # ⚠️ 상자로 감싸지 않는다 — 안쪽 여백이 카드를 넘치게 했다(실측).
        #    아래 줄 하나로 본문과 갈라 놓는 것으로 충분하다.
        # ⚠️ **참고사항은 첫 장에 한 번만** (2026-08-28 정리). 예전에는 등급 설명이
        #    첫 장에, 숫자 뜻풀이가 마지막 장에 따로 있어 같은 성격의 글이 흩어졌다.
        #    둘을 붙여 맨 앞 "참고사항"으로 모으고, 마지막 장에서는 뺐다.
        # ⚠️⚠️ **「참고사항」 라벨을 지웠다** (2026-09-11 지시서 0절 ⑦).
        #    「라벨 삭제, 어제 후보는 같은 덩이 안 20px 아래」
        #    등급칩 자체가 무엇인지 말해 주므로 라벨이 한 줄을 더 먹을 이유가 없다
        lead = (f'<div style="padding-top:{BLOCK_PAD}px;'
                f'border-top:{BLOCK_RULE}">'
                + grade_legend(24)
                + f'<div style="font-size:24px;line-height:1.35;color:{C["faint"]};'
                  f'margin-top:12px;word-break:keep-all">'
                  # ⚠️ **"되찾는지 보는 선"이 무슨 뜻인지 아무도 모른다** (2026-08-31 지적).
                # 무엇을 "본다"는 건지, 그래서 사라는 건지 말라는 건지가 빠져 있었다.
                # ⇒ **동사를 분명히 쓴다** — 넘으면 매수 검토, 내주면 매도.
                # ⚠️ 볼드를 걷었다 — 지시서 3절 「형광·밑줄·볼드 강조」 금지
                f'확인은 이 값을 넘어야 매수를 검토하는 선, '
                  f'손절은 이 값을 내주면 파는 선, '
                  f'발굴은 직전 거래일 종가입니다.</div>'
                # ⚠️ **균형** — 첫 장이 337px 남고 마지막 장은 90px뿐이었다(2026-08-28 실측).
                #    한 장은 텅 비고 한 장은 꽉 차 보인다. 오늘 후보 전체 안내를 앞으로
                #    옮겨 두 장의 채움을 맞춘다. "나머지"라는 말이 나오면 그 목록이
                #    바로 이어져야 하므로 안내문과 목록은 **붙여서** 옮긴다.
                # ⚠️ 2026-09-11 지시 — **2페이지 셋째 항목**으로 옮겼다
                + ''
                # ⚠️⚠️ **어제 후보가 어떻게 됐나** (2026-08-31 신설). 지메일·세로에는 있는데
                #    **가로 요약에만 없었다.** 아침에 폰으로 보는 건 가로인데, 거기에
                #    "어제 맞았나"가 없으면 **오늘 고른 종목을 믿을 근거가 화면에 없다.**
                #    ⚠️ 좋은 것만 보여주지 않는다 — 빗나간 것도 그대로 싣는다.
                #    ⚠️ **자리는 액션플랜, 오늘 후보 바로 앞이다.**
                #       "어제는 이랬다 → 오늘은 이걸 본다"로 이야기가 이어진다.
                #       ⚠️ 마지막 액션 장이 더 맞지만 **자리가 없다**(실측 −15px:
                #          09:05 판정·나머지 후보·장초확인으로 이미 꽉 찼다).
                #          기관 의견 장에 뒀다가 "성격이 안 맞는다"고 지적받고 옮겼다.
                # ⚠️ **같은 덩이 안**이다 (지시서 0절 ⑦) — `</div>` 앞에 넣는다.
                #    밖으로 빼면 별도 항목이 되어 구분선이 붙는다
                + _전일픽(cp) + '</div>')
    tail = ""
    if last:
        판정 = _진입판정(o["date"])
        if 판정:
            # ⚠️ 09:05이 지났다 — 체크리스트 대신 **실제 판정**을 보여준다.
            색 = {"조건충족": C["green"], "보류": C["gold"], "철회검토": C["down"],
                 "확인필요": C["gold"], "확인불가": C["muted"]}

            def _여유표시(r):
                v = _조건여유(r)
                if v is None:
                    return ""
                d, 아슬 = v
                # ⚠️ 아슬아슬하면 **말로도 적는다.** 숫자만 두면 `+0.07%`가 작다는 걸
                #    사람이 스스로 환산해야 한다. 그 환산을 화면이 대신한다.
                return (f'<span style="font-size:26px;color:'
                        f'{C["down"] if 아슬 else C["faint"]};margin-left:2px">'
                        f'조건선 {d:+.2f}%' + ('<b> 아슬아슬</b>' if 아슬 else '') + '</span>')
            checks = "".join(
                f'<div style="display:flex;gap:12px;align-items:baseline;margin-bottom:3px">'
                f'<span style="font-size:29px;font-weight:700;color:'
                f'{색.get(r.get("verdict"), C["muted"])};flex:none;white-space:nowrap">'
                f'{r.get("verdict", "?")}</span>'
                f'<span style="font-size:29px;color:{C["text2"]};flex:none">'
                f'{r.get("grade", "")} {r.get("name", "")}</span>'
                + (f'<span style="font-size:26px;color:{C["faint"]}">'
                   f'{int(r["now"]):,}원</span>' if r.get("now") else "")
                + _여유표시(r)
                + '</div>'
                # ⚠️ **문장·항목을 자르지 않는다** (2026-09-11 지시).
                #    간격 때문에 2줄로 줄였다가 되돌렸다 — 종목 하나가 안 보였다
                # ⭐ 건수 예산 §2·§3 (어제 후보)
                for r in 판정[:건수["어제후보"]])
        else:
            checks = "".join(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:8px">'
                f'<span style="width:14px;height:14px;border:1px solid {C["pill"]};flex:none;'
                f'margin-top:5px"></span>'
                f'<span style="font-size:29px;line-height:1.4;color:{C["faint"]};'
                f'word-break:keep-all">{first_sentence(x, CUT["장초확인"])}</span></div>'
                for x in (cp.get("장초확인") or [])[:2])
        # ⚠️ **장 시작 후 확인은 맨 마지막이다** (2026-08-28 지시). 그날 마지막으로
        #    읽고 나가는 글이라야 9시에 무엇을 볼지가 손에 남는다.
        #    숫자 뜻풀이는 **첫 장 참고사항**으로 옮겼다 — 여기 없다.
        # ⚠️ `margin-top:auto`를 쓰지 않는다 — 꼬리가 **카드 바닥에 붙어** 버려서
        #    글을 줄여도 아래 여백이 안 늘어난다(2026-08-28 실측: 78px에서 안 움직였다).
        #    자연스럽게 흐르게 두면 남는 자리가 그대로 여백이 된다.
        # ⚠️ **균형** — 안내 문장은 첫 장, 목록은 여기다(2026-08-28 실측으로 정함).
        #    둘을 같은 장에 두면 한 장은 105px, 다른 장은 346px가 남아 한쪽이 텅 빈다.
        # ⚠️ 목록은 여기가 아니라 **첫 장 안내 문장 바로 아래**다(2026-08-28 최종).
        #    마지막 장에 두었더니 그 장만 꽉 차 끝나는 높이가 80px 어긋났다.
        # ⚠️ 차례: 장 시작 후 확인 -> 오늘 후보 N종목 중 둘만 (2026-09-11 지시)
        # ⚠️⚠️ **09:05 결과와 마무리 문구는 한 덩이**다 (2026-09-11 지시서 0절 ⑦).
        #    「`09:05 결과`와 마무리 문구(`오늘 후보 N종목 중 둘만…`)도 **한 덩이**,
        #     14px 아래」 — 전에는 둘 사이에 줄을 긋고 22px 을 띄워 **별개 항목**처럼
        #    보였다. 라벨 색도 초록(#0d8f74)이었는데 지시서는 **#8a7038** 이다
        tail = (f'<div style="padding-top:{BLOCK_PAD}px;'
                  f'border-top:{BLOCK_RULE}">'
                + f'<div style="font-size:25px;font-weight:700;color:#8a7038">'
                  f'{"장 시작 후 확인" if not _진입판정(o["date"]) else "장 시작 후 확인 · 09:05 결과"}'
                  f'</div>'
                + f'<div style="height:12px"></div>{checks}'
                + (f'<div style="font-size:25px;color:{C["faint"]};'
                   f'line-height:1.5;padding-top:14px;word-break:keep-all">'
                   f'오늘 후보 {2 + rest}종목 중 둘만 실었습니다. '
                   f'나머지와 자세한 근거는 세로 상세에.</div>'
                   if rest > 0 else
                   f'<div style="font-size:25px;color:{C["faint"]};'
                   f'line-height:1.5;padding-top:14px;word-break:keep-all">'
                   f'자세한 근거는 세로 상세에 있습니다.</div>')
                # ⚠️⚠️ **면책은 뺄 수 없다.** 간격을 맞추려고 지웠다가 되돌렸다 —
                #    「투자 참고용이며 매수 권유가 아닙니다」는 투자 문구다
                #    (2026-09-11 사용자 지적)
                + f'<div style="font-size:25px;color:{C["faint"]};'
                  f'padding-top:14px">투자 참고용이며 매수 권유가 아닙니다.</div>'
                + '</div>')
    # 후보가 많아 여러 장이면 제목에 번호를 붙인다 — 안 붙이면 같은 제목이 반복돼
    # 넘겼는지 안 넘겼는지 알 수 없다(2026-08-27 지적).
    # ⚠️ **"주목"은 등급 이름과 겹친다**(🟢 주목). 카드 제목과 등급이 같은 낱말을 쓰면
    #    "이 카드에 있는 게 다 🟢인가?"로 읽힌다 — 실제로는 🟡도 여기 실린다.
    #    **"고른"**은 발굴했다는 뜻만 있고 등급어와 안 겹친다(2026-08-31 지적).
    # ⚠️ 다른 장 부제가 전부 **질문형**이다 — "밤사이 무슨 일이 있었나" ·
    #    "지금 시장은 어디쯤인가" · "돈은 어디로 움직였나" · "증권가는 뭐라고 했나".
    #    여기만 명사구("오늘 주목할 종목")라 결이 튀었고, "주목"은 등급 이름(🟢 주목)과도
    #    겹쳐 "이 카드가 다 🟢인가"로 읽혔다(2026-08-31 지적). 질문형으로 맞춘다.
    # ⚠️ 제목을 세 번 바꿨다(2026-08-31). 기록으로 남긴다:
    #    "오늘 주목할 종목" → **"주목"이 등급 이름(🟢 주목)과 겹쳐** 이 카드가 다 🟢로 읽혔다
    #    "오늘 고른 종목"   → 다른 장 부제가 전부 질문형인데 여기만 명사구라 결이 튀었다
    #    "오늘 무엇을 볼까"  → 질문형이지만 "본다"가 모호했다(어제 「언제 보나」를
    #                        「언제 사나」로 바꾼 이유와 같은 말이다)
    #    ⇒ **"오늘의 픽"** — 짧고, 발굴 결과라는 뜻이 분명하고, 등급어와 안 겹친다.
    #    ⚠️ **느낌표를 붙이지 않는다.** 매 장에 "투자 참고용이며 매수 권유가 아닙니다"를
    #       다는 화면이다. 느낌표 하나가 그 톤과 정면으로 부딪친다.
    #    ⚠️ **영어 "Pick"이 아니라 한글 "픽"이다.** 스킬에 티커·약어를 한국어로 푸는
    #       규칙이 길게 있고, 시스템도 이미 `전일픽`으로 쓰고 있다.
    # ⚠️ 제목을 네 번 바꿨다(2026-08-31). "액션플랜"은 내부 용어 냄새가 났고,
    #    "주목할 종목"은 등급 이름(🟢 주목)과 겹쳤고, "고른 종목"·"무엇을 볼까"·"픽"은
    #    다른 장 부제(질문형)와 결이 안 맞았다.
    #    ⇒ 제목은 **「액션플랜」** 그대로 두고 부제만 **「오늘의 기회는 어디에 있나」**로
    #      한다(2026-08-31 최종). 다른 장이 전부 "제목 = 짧은 이름 / 부제 = 질문"이라
    #      그 짜임에 맞는다: "시장 국면 / 지금 시장은 어디쯤인가".
    title = ("오늘의 기회는 어디에 있나" if parts < 2
             else f"오늘의 기회는 어디에 있나 {part}")
    # ⚠️⚠️ **제목·안내·종목을 한 덩어리로 묶는다** (2026-08-31 지적: "종목2는 시작점이
    #    한참 아래").
    #    `card(spread=True)`는 남는 자리를 **항목 사이로** 나눈다. 그래서 항목 수가 다르면
    #    같은 자리에서 시작하지 않는다 — 종목1 카드(제목·안내문·종목)와 종목2 카드
    #    (제목·종목·마무리)는 덩어리 수가 달라 **본문이 다른 높이에서 시작했다.**
    #    ⚠️ 묶으면 시작점은 고정되지만 **남는 자리가 아래에 몰린다.** 그 자리는
    #       내용으로 채운다("왜 이 종목인가" 상자) — 간격으로 때우면 시작점이 또 흔들린다.
    # ⚠️ **차례만 바꾼다** (2026-09-11 지시) — 종목 -> 참고사항 -> 어제 후보.
    #    2026-08-27 에 「배지 뜻을 먼저」로 lead 를 앞에 뒀는데 오늘 지시가 나중이다
    # ⚠️ 항목을 **감싸지 않는다** (2026-09-11 지시서 2절). 감싸면 본문 상자의
    #    직계 자식이 하나뿐이라 `space-between` 이 안 먹고 검사도 못 한다
    inner = (head(SEC["액션플랜"], "액션", pg(num, total), title)
             + rows + lead + tail)
    # ⚠️ 마지막 줄이 25px 라 꼬리가 짧다. 3이면 96px(상한 95) 이 된다
    return card(inner, f"{num:02d} 액션", 바닥=2)


def cards_for(o, cp):
    """하루치 카드 전부. 액션플랜이 후보 수에 따라 쪼개져 **장수가 달라진다**."""
    # ⚠️ 카드에는 **신호가 가장 강한 두 종목만** 싣는다. `picks`는 원점수 내림차순이라
    #    앞에서 자르면 그대로 상위 두 개다(SKILL STEP4 "최종 순서 = 원점수 내림차순").
    picks = (o.get("picks") or [])[:CARD_PICKS_MAX]
    남은 = len(o.get("picks") or []) - len(picks)
    chunks = [picks[i:i + PICKS_PER_CARD]
              for i in range(0, len(picks), PICKS_PER_CARD)] or [[]]
    # ⚠️ **표지는 세지 않는다** — "밤사이 무슨 일이 있었나"가 01이다(2026-08-28 지시).
    #    세로 상세도 같은 규칙이라 두 화면의 쪽 번호가 맞는다.
    total = 5 + len(chunks)
    out = [b(o, cp, max(i, 1), total) for i, b in enumerate(
        [c01_cover, c02_news, c03_regime, c04_flows, c05_calendar, c06_opinion], 0)]
    for j, ch in enumerate(chunks):
        out.append(c07_action(o, cp, 6 + j, total, chunk=ch, first=(j == 0),
                              offset=j * PICKS_PER_CARD, last=(j == len(chunks) - 1),
                              part=j + 1, parts=len(chunks), rest=남은))
    return out

PAGE_CSS = """<style>
/* ⚠️ 카드뉴스는 **가로로 넘기는 게 목적**이라 `touch-action:pan-y`를 걸면 안 된다.
   다만 레일 끝에서 더 밀면 iOS가 그걸 "뒤로 가기"로 받아 페이지를 떠나 버린다.
   `overscroll-behavior-x:none`이 그 끝단 제스처만 막는다(넘기기는 그대로 된다). */
/* ⚠️ iOS Safari 텍스트 자동 확대 차단 · 카드는 배율(transform:scale)로 그리는데
   글자만 따로 커지면 카드 안에서 넘친다. */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
/* ⚠️⚠️ **좌우는 어떤 환경에서도 고정한다.** (2026-08-27 세 번째 지적)
   여기에 `overflow-x:clip` **하나만** 걸어 뒀던 게 화근이었다. `clip`은 비교적 새 값이라
   그 값을 모르는 엔진은 **선언 전체를 버린다** · 그러면 잠금이 통째로 사라진다.
   데스크톱 크롬에서는 393px에서도 넘침이 0으로 나오는데 아이폰에서는 밀렸다. 즉
   "어느 요소가 범인인지 재서 잡는" 방식이 여기서는 통하지 않는다. 뿌리에서 막는다.
     · `hidden`을 먼저 쓰고 `clip`으로 덮는다 · 모르는 엔진은 `hidden`에서 멈춘다.
     · `max-width:100%`로 뿌리 자체가 넓어지는 길도 닫는다.
   ⚠️ `.rail`(가로 카드)은 제 안에서 따로 스크롤하므로 이 규칙에 걸리지 않는다. */
html,body{overscroll-behavior-x:none;max-width:100%;overflow-x:hidden}
body{margin:0;background:#e8e3d8;-webkit-font-smoothing:antialiased;overflow-x:clip}
a{color:#9d7a17;text-decoration:none} a:hover{color:#c9a227}
.days{display:flex;gap:8px;overflow-x:auto;padding:20px 20px 0;scrollbar-width:none}
.days::-webkit-scrollbar{display:none}
/* ⚠️ 이 8px은 **카드가 아니라 페이지 UI**(날짜 버튼)다. `RADIUS`로 묶지 않는다
   · 카드 상자 모서리를 바꿀 때 버튼까지 따라 바뀌면 안 된다(2026-09-01). */
.day{flex:none;background:#efece5;border:1px solid #d5cec0;border-radius:8px;
  padding:9px 15px;cursor:pointer;text-align:left;font-family:inherit;
  font-size:12px;line-height:1.35;color:#6b665c;white-space:nowrap}
.day b{display:block;font-size:13px;font-weight:700;color:#1c1813}
.day[aria-selected="true"]{border-color:#2050c8;background:#fff}
.rail{display:none;overflow-x:auto;scroll-snap-type:x mandatory;
  scroll-behavior:smooth;padding:20px;scrollbar-width:none}
.rail[data-active="true"]{display:flex}
.rail::-webkit-scrollbar{display:none}
/* ⚠️ **폰에서는 카드가 화면 폭을 꽉 채운다** (2026-08-27 지적).
   예전엔 배율이 고정(.32)이라 폰에서 카드가 화면 한가운데 작게 떴고,
   가뜩이나 작은 글씨가 더 안 보였다.

   ⚠️⚠️ 배율(`--s`)은 **CSS로 계산할 수 없다.** `calc((100vw - 16px)/1080)`은
   길이(px)를 내놓는데 `scale()`은 **숫자**를 받는다. 길이를 넣으면 값이 무효라
   **transform 전체가 통째로 무시되고** 카드가 1080px 원본 크기로 뜬다.
   그래서 폰 배율만 JS(`fit()`)에서 넣는다. 아래 값은 JS가 죽었을 때의 대비다. */
.rail{--s:.40;--gap:22px}
@media(max-width:1240px){.rail{--s:.33}}
@media(max-width:900px){
  .rail{--s:.36;--gap:6px;padding:0}
  .days{padding:10px 8px 0}
  .nav{padding:10px 0 22px}
}
.rail section{scroll-snap-align:center;flex:none;box-shadow:0 2px 18px #17181a14;
  transform:scale(var(--s));transform-origin:top left;
  margin-right:calc(var(--gap) - __W__px*(1 - var(--s)));
  margin-bottom:calc(-__H__px*(1 - var(--s)))}
.nav{display:flex;justify-content:center;align-items:center;gap:7px;padding:14px 0 34px}
.nav i{width:7px;height:7px;border-radius:50%;background:#c4bdae;display:block;transition:.15s}
.nav i.on{background:#2050c8;transform:scale(1.4)}
@media(prefers-reduced-motion:reduce){
  .rail{scroll-behavior:auto}
  .nav i,.arw{transition:none}
}
/* ⚠️ **넘기는 방법이 보여야 한다** (2026-08-27 지적). 예전엔 가로 스크롤뿐이라
   데스크톱에서는 넘길 수 있다는 사실 자체를 몰랐다. 표지의 "넘겨서 보기 →"는
   첫 장에만 있어서 힌트 구실을 못 했다. 화살표는 **항상 떠 있다.** */
.arw{position:fixed;top:50%;transform:translateY(-50%);z-index:5;
  width:52px;height:52px;border-radius:50%;border:1px solid #d5cec0;background:#efece5ee;
  color:#1c1813;font-size:22px;line-height:1;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 2px 12px #17181a1f;transition:.15s}
.arw:hover{background:#fff;border-color:#2050c8;color:#2050c8}
.arw[disabled]{opacity:.28;cursor:default;box-shadow:none}
.arw.prev{left:16px} .arw.next{right:16px}
/* 폰은 손가락으로 쓸어 넘기는 게 자연스럽고, 카드가 화면을 꽉 채워서
   화살표를 띄우면 본문을 가린다. 그래서 좁은 화면에서는 숨긴다. */
@media(max-width:900px){.arw{display:none}}
</style>"""

PAGE_JS = """<script>
(function(){
 var nav=document.querySelector('.nav');
 var chips=[].slice.call(document.querySelectorAll('.day'));
 // ⚠️⚠️ **퀀트 레일(.qrail)은 여기서 빼야 한다** (2026-09-07 고침).
 //    show(d) 가 `r.dataset.d === d` 로 data-active 를 다시 쓰는데,
 //    퀀트 레일에는 data-d 가 없어 **항상 false** 가 되어 화면이 꺼졌다.
 //    (`.rail[data-active="true"]{display:flex}` 이므로 안 보인다)
 //    새로 고치면 build_site 가 심어둔 data-active="true" 가 살아나
 //    다시 보인다 · 「가끔 안 나온다」의 정체가 이것이다
 var rails=[].slice.call(document.querySelectorAll('.rail:not(.qrail)'));
 // 배율(--s)은 퀀트 레일에도 필요하다 · 그것만 전부를 대상으로 한다
 var 배율레일=[].slice.call(document.querySelectorAll('.rail'));
 function live(){return document.querySelector('.rail:not(.qrail)[data-active="true"]')||rails[0]}
 var prev=document.querySelector('.arw.prev');
 var next=document.querySelector('.arw.next');
 // 지금 화면 한가운데 있는 카드의 번호. 점 표시와 화살표 활성/비활성이 같이 쓴다.
 //
 // ⚠️ **`offsetLeft`/`offsetWidth`를 쓰지 않는다.** 카드에 `transform:scale`이 걸려
 //    있어서 그 둘은 **축척 전 크기(1080)**를 돌려준다. 예전엔 `offsetWidth*0.26`
 //    같은 보정 상수를 곱해 맞췄는데, 축척을 .52에서 .40으로 바꾸자 그대로 틀어져
 //    첫 카드에서도 번호가 1로 나오고 화살표가 먹지 않았다(2026-08-27).
 //    `getBoundingClientRect()`는 변형이 반영된 **실제 화면 좌표**라 보정이 필요 없다.
 function at(r){
   var cs=[].slice.call(r.querySelectorAll('section'));
   var rr=r.getBoundingClientRect(), mid=rr.left+rr.width/2, best=0, bd=1e9;
   cs.forEach(function(c,i){
     var q=c.getBoundingClientRect(), d=Math.abs(q.left+q.width/2-mid);
     if(d<bd){bd=d;best=i}});
   return {list:cs,i:best};
 }
 // 점 표시와 화살표 상태를 i번 카드 기준으로 맞춘다.
 function mark(i,n){
   if(nav){
     if(nav.childElementCount!==n)
       nav.innerHTML=Array.apply(null,{length:n}).map(function(){return '<i></i>'}).join('');
     [].forEach.call(nav.children,function(el,k){el.className=(k===i)?'on':''});
   }
   // 끝에 닿으면 화살표를 흐리게 · 더 넘길 게 없다는 걸 눌러 보기 전에 알려 준다.
   if(prev) prev.disabled=(i<=0);
   if(next) next.disabled=(i>=n-1);
 }
 function paint(){
   var r=live(); if(!r) return;
   var s=at(r); mark(s.i,s.list.length);
 }
 // 목표 카드의 한가운데를 레일 한가운데로 옮긴다. `scroll-snap-align:center`와
 // 같은 기준이라, 스냅이 다시 잡아당겨 어긋나는 일이 없다.
 function go(dir){
   var r=live(); if(!r) return;
   var s=at(r), j=Math.max(0,Math.min(s.list.length-1,s.i+dir)), t=s.list[j];
   if(!t) return;
   var rr=r.getBoundingClientRect(), q=t.getBoundingClientRect();
   // behavior를 넘기지 않는다 · CSS의 `scroll-behavior`가 결정하게 둔다.
   // 여기서 'smooth'를 박으면 CSS를 덮어써 `prefers-reduced-motion`을 무시하고,
   // 애니메이션이 없는 환경(헤드리스 측정 포함)에서는 아예 움직이지 않는다.
   r.scrollBy({left:(q.left+q.width/2)-(rr.left+rr.width/2)});
   // ⚠️ 스크롤 이벤트를 기다리지 않고 **여기서 바로** 표시를 갱신한다.
   //    `paint()`는 rAF 뒤에 도는 데다 부드러운 스크롤이 끝나야 제 위치를 재므로,
   //    누른 직후에는 이전 카드 기준으로 남아 있다 · 마지막 장까지 갔는데도
   //    다음 화살표가 켜져 보였다(2026-08-27). 목표 번호를 이미 아는데 기다릴 이유가 없다.
   mark(j,s.list.length);
 }
 if(prev) prev.addEventListener('click',function(){go(-1)});
 if(next) next.addEventListener('click',function(){go(1)});
 // 배율을 직접 계산한다. CSS로는 못 한다 · 위 스타일시트의 경고 참고.
 //
 // 폰: 폭을 꽉 채운다.
 // 데스크톱: **화면 높이에 맞춰 한 장을 최대한 크게.** 카드가 4:5로 길어져서
 //   이제 가로가 아니라 세로가 병목이다. 고정 배율(.40)을 쓰면 큰 화면에서
 //   공간이 남는데도 글자가 작아진다.
 function fit(){
   var vw=window.innerWidth, vh=window.innerHeight, s;
   if(vw<=900){ s=vw/__W__; }
   else {
     var chrome=(chips.length?96:0)+68;   // 날짜 칩 + 아래 점 표시가 먹는 높이
     s=Math.max(.30,Math.min((vh-chrome)/__H__,(vw-160)/__W__,.62));
   }
   배율레일.forEach(function(r){
     r.style.setProperty('--s',s);
     // 첫 장과 마지막 장도 한가운데 설 수 있게 레일 양옆을 비운다.
     // 이게 없으면 `scroll-snap-align:center`가 끝 카드를 가운데로 못 데려온다.
     var side=(vw<=900)?0:Math.max(0,(r.clientWidth-__W__*s)/2);
     r.style.paddingLeft=side+'px'; r.style.paddingRight=side+'px';
   });
 }
 function show(d){
   chips.forEach(function(c){c.setAttribute('aria-selected',String(c.dataset.d===d))});
   rails.forEach(function(r){r.setAttribute('data-active',String(r.dataset.d===d))});
   var r=live(); if(r) r.scrollLeft=0;
   try{localStorage.setItem('cards-day',d)}catch(e){}
   paint();
 }
 chips.forEach(function(c){c.addEventListener('click',function(){show(c.dataset.d)})});
 var t=false;
 rails.forEach(function(r){r.addEventListener('scroll',function(){
   if(t)return;t=true;requestAnimationFrame(function(){paint();t=false})},{passive:true})});
 window.addEventListener('resize',function(){fit();paint()});
 fit();
 document.addEventListener('keydown',function(e){
   if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;
   go(e.key==='ArrowRight'?1:-1);
 });
 var w=null; try{w=localStorage.getItem('cards-day')}catch(e){}
 var ok=chips.some(function(c){return c.dataset.d===w});
 if(chips.length) show(ok?w:chips[0].dataset.d); else paint();
 // `build_site.py`가 날짜를 바꾸거나 화면을 전환한 뒤 부른다. 레일이 숨어 있는 동안은
 // 폭이 0이라 배율 계산이 틀어지므로, **보이게 만든 다음** `fit()`을 다시 불러야 한다.
 // ⭐⭐ 2026-09-11 디자인 답 ① — **채움 비율로 간격을 고른다**
 //    70% 이상 -> space-between (지금처럼 남는 자리를 고루 나눈다)
 //    70% 미만 -> flex-start + 고정 60px, 남는 자리는 **아래에 그대로** 둔다
 //    (항목이 적은 지난 날짜 카드가 600~900px 씩 벌어지던 것을 막는다)
 //    ⚠️ 글자 크기는 **건드리지 않는다** — 지난 날짜와 오늘 카드의 글자가
 //       달라지면 더 이상하다 (디자인 지시)
 function 채움(){
   var bs=document.querySelectorAll('[data-body="1"]');
   for(var i=0;i<bs.length;i++){
     var el=bs[i], cs=getComputedStyle(el);
     var 가용=el.clientHeight
              -(parseFloat(cs.paddingTop)||0)-(parseFloat(cs.paddingBottom)||0);
     var 합=0;
     for(var j=0;j<el.children.length;j++) 합+=el.children[j].offsetHeight;
     var 성김=(가용>0 && 합/가용<0.70);
     /* ⭐⭐ **01 뉴스는 늘 `space-between` 이다** (2026-09-14 지시).
        2026-09-14 에 01 뉴스만 비율 0.688 로 문턱 0.70 을 **2%p 차이로** 놓쳐
        `flex-start` 로 빠졌고, 아래여백이 **220px** 이 됐다(다른 장은 90~95).
        뉴스 넷은 날마다 길이가 들쭉날쭉해 이 문턱을 오락가락 넘나든다 —
        그때마다 아래여백이 95 <-> 220 으로 **널뛰는 게 더 이상하다.**
        ⚠️ 다만 **항목이 셋 미만이면 그대로 둔다** — 옛 장(2026-08-25)은 항목이
           2개뿐이라 `space-between` 이면 둘 사이가 **800px** 벌어진다.
           그게 애초에 `flex-start` 를 넣은 이유다(2026-09-11 디자인 답 ①) */
     var _s=el.closest("section");
     if(_s&&(_s.dataset.label||"").indexOf("01")===0&&el.children.length>=3)
       성김=false;
     el.style.justifyContent = 성김 ? 'flex-start' : 'space-between';
     el.style.gap = 성김 ? '60px' : '';
   }
 }
 채움();
 window.addEventListener('resize',채움);
 window.__cards={show:show,fit:fit,paint:paint,채움:채움};
})();
</script>"""


def build(date, out):
    rows = [json.loads(l) for l in io.open(LOG, encoding="utf-8-sig") if l.strip()]
    days = (sorted(rows, key=lambda x: x.get("date", ""), reverse=True)
            if date == "all" else [o for o in rows if o.get("date") == date])
    if not days:
        return {"error": f"{date} 기록 없음. 있는 날짜: {[o.get('date') for o in rows][-5:]}"}

    chips, rails, missing = [], [], []
    for i, o in enumerate(days):
        cp = _copy(o["date"])
        if not cp:
            missing.append(o["date"])
        dt = datetime.strptime(o["date"], "%Y-%m-%d")
        picks = o.get("picks") or []
        headline = " · ".join(p["grade"] + p["name"] for p in picks[:2]) or "관망"
        if len(picks) > 2:
            headline += f" 외 {len(picks)-2}"
        chips.append(f'<button class="day" data-d="{o["date"]}" '
                     f'aria-selected="{"true" if i == 0 else "false"}">'
                     f'<b>{dt.month:02d}/{dt.day:02d}({WEEKDAY[dt.weekday()]})</b>'
                     f'<span>{headline}</span></button>')
        cs = cards_for(o, cp)
        n_cards = len(cs)
        rails.append(f'<div class="rail" data-d="{o["date"]}" '
                     f'data-active="{"true" if i == 0 else "false"}">'
                     + "".join(cs) + "</div>")

    # 카드 규격은 `card_theme`가 정본이다. CSS/JS의 자리표시자에 그 값을 꽂는다 —
    # 두 군데에 1080을 따로 적어 두면 규격을 바꿀 때 반드시 한쪽이 남는다.
    shell = (PAGE_CSS + PAGE_JS).replace("__W__", str(CARD_W)).replace("__H__", str(CARD_H))
    css, js = shell.split("</style>", 1)
    title = BRAND
    html = (f"<title>{title}</title>\n"
            # ⚠️ 이 태그가 없으면 폰이 데스크톱 폭(980px)으로 가정해 전부 축소해 그린다.
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            + FONTS + "\n" + css + "</style>"
            + (f'<div class="days">{"".join(chips)}</div>' if len(days) > 1 else "")
            + "".join(rails)
            + '<button class="arw prev" type="button" aria-label="이전 카드">&#8249;</button>'
            + '<button class="arw next" type="button" aria-label="다음 카드">&#8250;</button>'
            + '<div class="nav"></div>' + js)
# ⚠️⚠️ **화면 글의 `—`(em dash)를 `·` 로 바꾼다** (2026-09-11 지시).
    #    서술 파일(`card-copy`)에서 들어오는 문장에 섞여 있어 **소스만 고쳐서는
    #    안 없어진다.** 매일 새 글이 오므로 **내보내는 자리**에서 걸러야 한다.
    #    ⚠️ `<style>`·`<script>` 안에는 em dash 를 쓰지 않으므로 통째로 바꿔도 안전하다
    html = html.replace("—", "·")
    io.open(out, "w", encoding="utf-8").write(html)

    res = {"ok": True, "파일": out, "날짜수": len(days), "카드수": n_cards,
           "규격": f"{CARD_W}x{CARD_H}", "크기자": len(html), "최신": days[0]["date"]}
    if os.path.exists(URL_FILE):
        res["url"] = io.open(URL_FILE, encoding="utf-8-sig").read().strip() or None
    if missing:
        res["_경고"] = (f"서술 파일 없음: {missing}. `data\\card-copy\\<날짜>.json` 이 없으면 "
                        f"숫자만 나온다 · 카드뉴스의 목적을 잃는다.")
    return res


# ⭐⭐⭐ **40px 미만인 날만 발동하는 예비 예산** (2026-09-11 디자인 답 2·3).
#    {날짜: {예산이름: 값}} — 비어 있으면 지금 값 그대로다
빠듯한날 = {}

# ⭐ **건수 예산** — 글자가 아니라 **몇 건을 싣나**. 줄이면 「나머지 N건은
#    세로 상세에」가 그 블록 안에 붙는다 (2026-09-11 디자인 답 4)
# ⭐ **건수 예산** — FINAL-CARDS §2·§3. 줄일 때도 늘릴 때도 **건수만** 움직인다.
#    글자 수 상한은 **올리지 않는다** (올리면 다른 날이 넘친다 · §3)
# ⭐ **02 국면만 예외** — 블록이 넷이라 자리가 안 난다.
#    줄이는 3순위로 본문을 29px 까지 내린다 (§5 하한 29는 지킨다).
#    ⚠️ 블록을 빼거나 넷->셋으로 줄이지 **않는다** — 네 블록이 이 장의 뼈대다.
#    「내용을 지우는 것보다 여백이 좁은 게 낫다」 (2026-09-11 디자인 답)
국면본문 = [31]
건수 = {"미장뉴스": 3, "한국뉴스": 3, "이미반영줄": 3, "미반영줄": 3,
        "업종테마": 3, "일정": 3, "리포트": 2, "어제후보": 3}


def 남은줄(n):
    r"""「나머지 N건은 세로 상세에」 — **그 블록 안** 마지막 항목 아래.

    ⚠️ 카드 맨 아래 각주와 다르다. 각주는 **장 전체**에 대한 말이고,
       이 줄은 **잘린 그 블록**에 붙는 말이라 블록 안에 있어야 한다.
       한 장에 잘린 블록이 둘이면 줄도 둘이다 (2026-09-11 디자인 답 4)
    ⚠️ 말줄임 없음 · 건수만 바뀐다
    """
    if n <= 0:
        return ""
    return (f'<div style="padding-top:14px;font-size:25px;line-height:1.5;'
            f'color:#6b665c">나머지 {n}건은 세로 상세에</div>')


# 디자인이 정한 **낮추는 순서**. 위에서부터 하나씩 쓴다 (2026-09-11 답 1~3)
#   ⚠️ 컨센서스 90 · 의견해설 85 가 **하한**이다. 그 아래로 가면 문장이 뜻을 잃는다
#   ⚠️ 03 국면은 80자로도 모자라면 **더 줄이지 않는다** — 30px 까지는 봐준다
#   ⚠️ 02 뉴스의 지수 50px 은 되돌리지 않는다 (그 카드에서 제일 먼저 읽히는 값)
# §2 — 여백 **50px 미만**일 때. 위에서부터 하나씩, 될 때까지
줄이는순서 = {
    "01 뉴스": (("미장요약", 60), ("건수:한국뉴스", 2), ("건수:미장뉴스", 2)),
    # 3순위 = 본문 29px. 그래도 모자라면 **그대로 낸다** (§6 예외)
    "02 국면": (("시장국면", 80), ("반영", 26), ("국면본문", 29)),
    "03 수급": (("수급해설", 60), ("건수:업종테마", 2)),
    "04 일정": (("캘린더해설", 80), ("건수:일정", 2), ("일정", 36)),
    "05 기관": (("컨센서스", 90), ("건수:리포트", 1), ("의견해설", 85)),
    "06 액션": (("신호", 120), ("건수:어제후보", 2)),
    "07 액션": (("신호", 120), ("건수:어제후보", 2)),
}
# §3 — 여백 **110px 초과**일 때. **건수만** 늘린다
채우는순서 = {
    "01 뉴스": (("건수:미장뉴스", 4), ("건수:한국뉴스", 4)),
    # 명세 §3 — 1순위 반영 3->4줄 · 2순위 미반영 3->4줄 (**따로**)
    "02 국면": (("건수:이미반영줄", 4), ("건수:미반영줄", 4)),
    "03 수급": (("건수:업종테마", 4),),
    "04 일정": (("건수:일정", 4),),
    "05 기관": (("건수:리포트", 3),),
    "06 액션": (("건수:어제후보", 4),),
    "07 액션": (("건수:어제후보", 4),),
}


def 예산(이름, 날짜=None):
    r"""그날 쓸 예산. 빠듯한 날이면 낮춘 값을 준다"""
    return (빠듯한날.get(날짜 or "") or {}).get(이름, CUT[이름])


def 좁은장재기(html):
    r"""헤드리스 크롬으로 **항목 간격 40px 미만인 장**을 찾는다.

    `check_layout` 의 프로브를 그대로 쓴다 — 두 벌로 갈라지면
    한쪽만 고치고 조용히 어긋난다
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import check_layout as K
        exe = K._chrome()
        if not exe:
            return None, "크롬이 없어 좁은 장을 못 쟀다"
        probe = K.CARD_PROBE.replace("__MINFONT__", str(K.MIN_FONT))
        raw, err = K._run(exe, html + "<script>" + probe + "</script>",
                          1500, 1300, "R::")
        if err or not raw:
            return None, err or "좁은 장 측정값을 못 읽었다"
    except Exception as e:  # noqa: BLE001
        return None, f"좁은 장 측정 실패: {type(e).__name__}"
    좁 = []
    for row in raw.split("@@"):
        p = row.split("|")
        if len(p) < 10 or "커버" in p[0]:
            continue
        g = [int(z) for z in (p[9].split(",") if p[9] else [])
             if z.lstrip("-").isdigit()]
        # ⭐ **오늘 이후 날짜만** 본다 (2026-09-11 디자인 답 5).
        #    지난 날짜는 글이 고정돼 있어 줄이면 그날 글만 더 잘린다
        _날 = p[12] if len(p) > 12 else ""
        if _날 and _날 < dt.date.today().isoformat():
            continue
        if not g:
            continue
        # §1 목표 50~110px. 아래로 벗어나면 §2, 위로 벗어나면 §3
        if min(g) < 50:
            좁.append(("좁", p[0], min(g)))
        elif max(g) > 110:
            좁.append(("넓", p[0], max(g)))
    return 좁, None


def 예산맞추기(date, out, res=None):
    r"""**FINAL-CARDS §1~3** — 범위 밖이면 한 단계 적용하고 다시 잰다 (최대 3회).

    ⚠️⚠️ `build_site` 도 이걸 **반드시** 부른다. 사이트는 카드 파일을 읽는 게
       아니라 `cards_for()` 로 다시 그리기 때문에, 안 부르면 **웹에 줄이기 전
       카드가 나간다** (2026-09-11 에 실제로 그랬다)
    """
    res = res if res is not None else {}
    _쓴, _남, _쓴순서 = [], [], {}
    for _돌 in range(3):
        try:
            _h = io.open(out, encoding="utf-8").read()
        except OSError:
            break
        밖, _err = 좁은장재기(_h)
        if _err:
            res["_안내"] = (res.get("_안내") or "") + " · " + _err
            break
        if not 밖:
            _남 = []
            break
        _바뀜 = False
        for _쪽, _라, _px in 밖:
            표 = 줄이는순서 if _쪽 == "좁" else 채우는순서
            _벌 = 표.get(_라, ())
            _단 = _쓴순서.get((_쪽, _라), 0)
            if _단 >= len(_벌):
                continue
            _이름, _값 = _벌[_단]
            _쓴순서[(_쪽, _라)] = _단 + 1
            if _이름.startswith("건수:"):
                건수[_이름[3:]] = _값
            elif _이름 == "국면본문":
                국면본문[0] = _값
            else:
                CUT[_이름] = _값
            _쓴.append(f"{_라}({_px}px): {_이름} -> {_값}")
            _바뀜 = True
        _남 = [f"{_라} {_px}px" for _쪽, _라, _px in 밖]
        if not _바뀜:
            break
        build(date, out)
    if _쓴:
        res["_예비예산"] = _쓴
    if _남:
        res["_범위밖"] = _남
    return res


def main():
    argv = sys.argv[1:]
    known = {"--date", "--out"}
    bad = [a for a in argv if a.startswith("--") and a not in known]
    if bad:
        print(json.dumps({"error": f"모르는 인자: {bad} (허용: {sorted(known)})"}, ensure_ascii=False))
        return
    if "--date" not in argv:
        print(json.dumps({"error": "--date YYYY-MM-DD 또는 --date all"}, ensure_ascii=False))
        return
    date = argv[argv.index("--date") + 1]
    out = argv[argv.index("--out") + 1] if "--out" in argv else OUT
    res = build(date, out)
    # ⭐⭐ **2패스** — 40px 미만인 장이 있으면 그 예산만 낮춰 다시 그린다.
    #    디자인: 「셋 다 40px 미만일 때만 발동하는 예비 규칙 ·
    #             평소에는 지금 값 그대로 두세요」
    # ⭐ 2패스는 `예산맞추기()` 에 있다 — **사이트도 같은 걸 쓴다**
    if res.get("ok"):
        예산맞추기(date, out, res)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()








































































































