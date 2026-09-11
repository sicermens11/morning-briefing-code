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
CUT = {
    # ⚠️ 이 숫자는 **감이 아니라 실측**이다. `check_layout.py`로 카드별 아래 여백을 재서
    #    하한 90px을 남기고 남는 만큼만 올린다. **바꾸면 반드시 다시 잰다.**
    #    ⚠️ 2026-08-28에 있던 "액션플랜은 여유 8px이니 건드리지 마라"는 주석은
    #       **한 장에 두 종목이던 시절 값**이라 지웠다. 한 종목으로 바꾼 뒤 여유가 생겼다.
    "시장국면": 96, "반영": 32,         # 03 국면 (`반영`은 첫 문장 상한)
    "수급해설": 72,                      # 04 돈의 흐름
    # ⚠️ 「언제 사나」를 카드에서 빼고 그 자리를 신호로 돌렸다(2026-08-31).
    #    신호는 살 이유와 망설일 이유라 **숫자로 대체할 수 없는 카드의 유일한 판단 재료**다.
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


def stat_cell(label, value, change=None, big=44, note=""):
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
    return (f'<div style="background:{TINT};border-radius:{RADIUS}px;padding:20px 18px">'
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
        tail = ("그런데 <b>선물이 오르고 있습니다</b> — 미국 장이 닫힌 뒤 좋은 소식이 "
                "나왔다는 뜻이라, 오늘 아침 우리 기술주도 오를 가능성이 있습니다.")
    elif ft < -0.5:
        tail = ("그런데 <b>선물이 내리고 있습니다</b> — 미국 장이 닫힌 뒤 나쁜 소식이 "
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


def block(label, color, inner, sub="", top=40, size=26):
    r"""항목 한 덩어리 — **왼쪽 색 막대 + 아주 옅은 바탕**으로 구분한다.

    ⚠️ 여기 색은 **아주 옅어야 한다**(불투명도 약 7%, 아래 `{color}12`).
       2026-08-27에 진한 색 박스로 감쌌다가 "완전 구려졌다"는 지적을 받고 되돌렸고,
       이번엔 사용자가 "애널리스트 컨센서스처럼 너무 튀지 않는 색"을 요청해서
       그 상자와 **같은 방식**(왼쪽 막대 3px + 옅은 바탕)으로 통일했다.
       ⚠️ 진하게 만들고 싶으면 먼저 눈으로 확인받는다.
    """
    # ⚠️ **모서리만 둥글게 하고 바탕 농도는 손대지 않는다** (2026-08-31). 전에 되돌린 것은
    #    "진한 색 박스"였지 둥근 모서리가 아니었다. 테두리도 색의 20%로 아주 옅게만 둔다.
    return (f'<div style="margin-top:{top}px;background:{color}0f;'
            f'border:1px solid {color}33;border-left:3px solid {color};'
            f'border-radius:{RADIUS_BIG}px;padding:15px 20px">'
            + kicker(label, color, size)
            # ⚠️ 설명글을 `muted`로 두면 바탕에 묻혀 안 읽힌다(2026-08-27 지적).
            #    본문색(`text2`)으로 올리고 크기도 라벨에 가깝게 둔다.
            + (f'<div style="font-size:{max(size, 26)}px;line-height:1.45;'
               f'color:{C["text2"]};margin-top:7px">{sub}</div>' if sub else "")
            + f'<div style="margin-top:10px">{inner}</div></div>')


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
    bits = []
    if conf:
        bits.append(f'확인 <b>{conf:,}원</b>')
    if stop:
        bits.append(f'손절 <b>{stop:,}원</b>')
    else:
        # ⚠️ **조용히 생략하지 않는다.** 손절선이 없는 요약과 원래 그런 요약이
        #    똑같이 보이면, 없다는 사실 자체가 안 보인다.
        bits.append(f'<span style="color:{C["muted"]}">손절 미기재</span>')
    if p.get("found_price"):
        bits.append(f'발굴 {int(p["found_price"]):,}원')
    return " · ".join(bits)


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
    부 = " <span style=\"color:%s\">·</span> " % C["line"]
    return (f'<div style="font-size:{size}px;line-height:1.5">'
            + 부.join(
                f'<b style="color:{GRADE.get(e, (C["muted"], ""))[0]}">{e} {w}</b>'
                f'<span style="color:{C["muted"]}"> {d.replace("상승 ", "")}</span>'
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
    return "".join(
        f'<div style="display:flex;align-items:baseline;gap:12px;'
        f'margin-top:{10 if i else 0}px">'
        f'<span style="font-size:{size}px;color:{C["text2"]};flex:1;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.get("이름")}</span>'
        f'<span style="font-family:{MONO};font-size:{size}px;font-weight:700;'
        f'color:{sign_color(x.get("등락률"))}">{pct(x.get("등락률"))}</span></div>'
        for i, x in enumerate(sectors))


# ── 카드 7종 ────────────────────────────────────────────────────
def c01_cover(o, cp, num, total):
    dt = datetime.strptime(o["date"], "%Y-%m-%d")
    picks = o.get("picks") or []
    toc = "".join(
        f'<div style="display:flex;gap:12px;align-items:baseline">'
        f'<span style="font-family:{MONO};font-size:29px;color:{C["muted"]}">{i:02d}</span>'
        f'<span style="font-size:29px;color:{C["text2"]}">{t}</span></div>'
        for i, t in enumerate(["뉴스", "시장 국면", "근거·수급", "캘린더", "기관 의견", "액션플랜"], 1))
    bars = "".join(
        f'<div style="flex:1;height:{h}px;background:{c}"></div>'
        for h, c in ((120, C["dim"]), (180, C["dim"]), (150, C["dim"]), (250, C["dim"]),
                     (210, C["dim"]), (330, "#0d8f7433"), (430, "#0d8f7444")))
    inner = (
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;flex:none">'
        # 날짜는 숫자라 MONO. 자간을 벌려도 되는 건 여기처럼 **숫자·로마자일 때뿐**이다.
        f'<span style="font-family:{MONO};font-size:29px;letter-spacing:.14em;'
        f'color:{C["gold"]};font-weight:700">{dt.strftime("%Y.%m.%d")}</span>'
        f'<span style="display:flex;gap:10px;align-items:center">'
        f'<span style="width:11px;height:11px;border-radius:50%;background:{C["blue"]}"></span>'
        f'<span style="width:11px;height:11px;border-radius:50%;background:{C["gold"]}"></span>'
        f'<span style="font-size:29px;letter-spacing:{LS_KO};'
        f'color:{C["muted"]};margin-left:8px">{WEEKDAY[dt.weekday()]}요일 · '
        f'후보 {len(picks)}</span></span></div>'

        f'<div style="margin-top:120px">'
        f'<div style="font-size:29px;letter-spacing:{LS_KO};'
        f'color:{C["muted"]};margin-bottom:32px">모닝 브리핑</div>'
        # 표지 제목은 첫 낱말 뒤에서 줄을 바꾼다("깜댕의 / 주식 브리핑").
        # 한 줄로 두면 142px에서 카드 폭을 넘는다.
        f'<h1 style="font-size:114px;font-weight:800;line-height:1.04;letter-spacing:-.05em;'
        f'color:{C["text"]};margin:0">{BRAND.replace(" ", "<br>", 1)}</h1>'
        f'<div style="display:flex;gap:24px;align-items:center;margin-top:38px">'
        f'<span style="width:88px;height:1px;background:{C["goldArt"]};flex:none"></span>'
        f'<span style="font-size:34px;color:{C["muted"]}">'
        f'{cp.get("부제", "3분 만에 읽는 어제와 오늘의 시장")}</span></div></div>'

        f'<div style="display:flex;justify-content:space-between;align-items:flex-end;'
        f'flex:none;margin-top:auto;padding-top:60px">'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px 34px">{toc}</div>'
        f'<span style="font-size:29px;letter-spacing:{LS_KO};'
        f'color:{C["muted"]};white-space:nowrap">넘겨서 보기 →</span></div>'
    )
    # 장식 막대는 카드 좌표계에 직접 얹는다(본문 패딩 박스 기준으로 밀면 넘친다).
    deco = (f'<div style="position:absolute;left:44px;right:44px;bottom:44px;height:470px;'
            f'display:flex;gap:14px;align-items:flex-end;opacity:.4;'
            f'pointer-events:none">{bars}</div>')
    # ⚠️ 배경 아트워크(`art=True`)는 **이 카드에서만** 켠다. 나머지는 바탕을 비운다.
    return card(inner, "01 커버", frame=True, deco=deco, art=True, spread=False)


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
    for nm, src, key in (("S&P 500", idx.get("S&P500"), "종가"),
                         ("나스닥 100", idx.get("나스닥100"), "종가"),
                         ("나스닥 선물", fut.get("나스닥100 선물"), "현재")):
        if src:
            cells.append(stat_cell(nm, f'{src[key]:,}', src.get("등락률"), big=40))
    strip = ""
    if cells:
        strip = ('<div style="display:grid;grid-template-columns:1fr 1fr 1fr;'
                 f'gap:12px;margin:0">' + "".join(cells) + "</div>")
        # 지수 셋을 묶어 "그래서 오늘 아침 미국은 어땠나"를 한 문단으로. 서술 파일에
        # `미장요약`이 있으면 그걸 쓰고, 없으면 숫자에서 바로 문장을 만든다.
        strip += (f'<div style="font-size:28px;line-height:1.5;color:{C["text2"]};'
                  f'margin-top:18px;word-break:keep-all;max-width:{TEXT_MAX}">'
                  f'{first_sentence(cp.get("미장요약") or _us_gist(idx, fut), CUT["미장요약"])}</div>')
    # ⚠️ **두 쪽에서 번갈아 뽑는다.** 예전엔 `(us + kr)[:3]`이었는데, 미장 뉴스가
    #    3건이 되자 **국장 뉴스가 통째로 밀려나** 카드 제목이 "미국·한국 뉴스"인데
    #    한국 뉴스가 한 건도 없었다(2026-08-27). 어느 한쪽이 길어져도 다른 쪽이
    #    사라지지 않게, 앞에서 자르지 말고 **번갈아** 집는다.
    # ⚠️ 카드는 **요약**이다 — `머리`만 싣고 `몸`은 세로형에 맡긴다(2026-08-27 합의).
    #    예전엔 몸까지 넣느라 3건밖에 못 실었고, 그래서 국장 뉴스가 통째로 밀려났다.
    #    이제 머리만 싣기 때문에 양쪽을 **다 실을 수 있다** — 자르지 않는다.
    def group(label, items, color):
        if not items:
            return ""
        rows = "".join(
            f'<div style="display:flex;gap:16px;align-items:flex-start;'
            f'margin-top:{16 if i else 0}px">'
            f'<span style="color:{color};font-size:30px;flex:none;'
            f'line-height:1.3">·</span>'
            f'<span style="font-size:34px;font-weight:700;line-height:1.35;'
            f'color:{C["text"]};letter-spacing:-.02em;word-break:keep-all">'
            f'{n.get("머리","")}</span></div>'
            for i, n in enumerate(items[:3]))
        return block(label, color, rows, top=(0 if label == "미국 증시" else GAP), size=26)

    inner = (head(C["blue"], "미국·한국 뉴스", pg(num, total), "밤사이 무슨 일이 있었나")
             + strip
             + group("미국 증시", us, C["blue"])
             + group("한국 증시", kr, C["gold"]))
    return card(inner, "02 뉴스")


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
    국면연 = 국면색 + "1f"   # 배지 배경 — 같은 색의 옅은 판
    def lst(items):
        # ⚠️ 카드는 **첫 문장만** 쓴다. 원본은 세로 상세용으로 길게 적혀 있다 —
        #    글자 수로 자르면 "올라 값…"처럼 말을 하다 만다(2026-08-28).
        return "".join(f'<li style="margin-bottom:15px">{first_sentence(x, CUT["반영"])}</li>'
                       for x in (items or [])[:3])
    inner = (head(C["gold"], "시장 국면", pg(num, total), "지금 시장은 어디쯤인가")
             + f'<div style="display:flex;align-items:flex-end;gap:24px;flex:none">'
               f'<div><div style="font-size:29px;color:{C["muted"]};margin-bottom:10px">'
               f'코스피 · 20일 평균선 대비</div>'
               f'<div style="font-family:{MONO};font-size:92px;font-weight:700;'
               f'line-height:.92;color:{국면색};letter-spacing:-.04em">{pct(kv)}</div></div>'
               f'<span style="padding:12px 24px;border-radius:999px;background:{국면연};'
               f'color:{국면색};font-size:29px;font-weight:700;margin-bottom:12px">{band}</span></div>'

             # ⚠️ **띠 색이 곧 눈금이다** (2026-08-31). 예전에는 회색 막대에 국면색을
             #    채우기만 해서 "얼마나 벗어났나"만 보이고 **어느 구간인지는 안 보였다.**
             #    이제 띠가 하락색 → 회색 → 상승색으로 흐르고 동그라미가 그 위에 선다.
             #    ⚠️ **띠 색은 `C["down"]`·`C["up"]`을 쓴다.** v2 시안의 코발트·민트·금색을
             #       가져오지 않는다 — 금색을 과열에 쓰지 않기로 한 결정과 어긋난다.
             + f'<div style="margin-top:22px;position:relative;height:22px;flex:none">'
               f'<div style="position:absolute;top:6px;left:0;right:0;height:10px;'
               f'border-radius:999px;background:linear-gradient(90deg,{C["down"]},'
               f'{C["muted"]} 50%,{C["up"]})"></div>'
               # 가운데 눈금 — 0%(평균) 자리. 띠를 파낸 것처럼 보이게 카드색을 쓴다.
               f'<div style="position:absolute;left:50%;top:4px;height:14px;width:2px;'
               f'background:{C["card"]}"></div>'
               f'<div style="position:absolute;left:{max(0,min(100,pos))}%;top:0;'
               f'transform:translateX(-50%);width:22px;height:22px;border-radius:50%;'
               f'background:{C["card"]};border:4px solid {국면색};box-sizing:border-box;'
               f'box-shadow:0 1px 4px rgba(0,0,0,.20)"></div></div>'
             + f'<div style="display:flex;justify-content:space-between;margin-top:12px;'
               f'font-size:29px;color:{C["muted"]};flex:none"><span>눌림</span><span>평균</span>'
               f'<span>과열</span></div>'

             + f'<p style="font-size:31px;line-height:1.55;color:{C["text2"]};margin:28px 0 0;'
               f'word-break:keep-all;max-width:{TEXT_MAX}">{first_sentence(cp.get("시장국면"), CUT["시장국면"])}</p>'

             # ⚠️ 좌우 2단으로 놓았다가 칸이 좁아 낱말이 어색하게 끊겼다("붙었습니 / 다").
             #    위아래로 쌓으면 한 줄이 넉넉해진다. 색은 라벨 글자에만 준다.
             + block("시장 이미 반영", C["up"],
                     f'<ul style="margin:0;padding-left:24px;font-size:29px;'
                     f'line-height:1.5;color:{C["text2"]};max-width:{TEXT_MAX}">'
                     f'{lst(cp.get("이미반영"))}</ul>',
                     sub="주가가 이미 올라 지금 들어가기엔 늦은 것", top=24)
             + block("시장 미반영", C["gold"],
                     f'<ul style="margin:0;padding-left:24px;font-size:29px;'
                     f'line-height:1.5;color:{C["text2"]};max-width:{TEXT_MAX}">'
                     f'{lst(cp.get("미반영"))}</ul>',
                     sub="좋은 소식은 나왔는데 주가에 아직 안 붙은 것", top=18))
    return card(inner, "03 국면")


def c04_flows(o, cp, num, total):
    mk = (_snap(o["date"], "fetch_market") or {}).get("summary") or {}
    kospi = mk.get("코스피") or {}
    dep = mk.get("예탁금") or {}
    # 섹터 흐름 — 어제 어느 업종·테마로 돈이 몰렸는지. 후보 종목이 왜 그 업종인지를
    # 여기서 설명 없이도 알 수 있다(2026-08-27 추가 요청).
    sectors = ((mk.get("업종랭킹") or [])[:3] + (mk.get("테마랭킹") or [])[:1])[:3]
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
            cells += (f'<div style="background:{TINT};border-radius:{RADIUS}px;padding:20px 18px">'
                      + kicker(x.get("주체", ""), C["muted"], 26)
                      + '<div style="height:10px"></div>'
                      f'<div style="font-size:34px;font-weight:700;'
                      f'color:{fc}">{x.get("값","")}</div></div>')
        flows_box = (f'<div style="display:grid;grid-template-columns:repeat({len(fl)},1fr);'
                     f'gap:12px;margin-top:26px;flex:none">{cells}</div>')
    inner = (head(C["green"], "근거 데이터 · 수급", pg(num, total), "돈은 어디로 움직였나")
             + f'<div style="display:flex;align-items:flex-end;gap:26px;flex:none">'
               f'<div><div style="font-size:29px;color:{C["muted"]};margin-bottom:10px">코스피</div>'
               f'<div style="font-family:{MONO};font-size:80px;font-weight:700;line-height:1;'
               f'color:{C["text"]};letter-spacing:-.04em">{kospi.get("지수","—")}</div></div>'
               f'<div style="font-family:{MONO};font-size:32px;font-weight:700;'
               f'color:{sign_color(_f(kospi.get("등락률"),0))};padding-bottom:10px">'
               f'{pct(kospi.get("등락률"))}</div></div>'

             + flows_box

             + f'<p style="font-size:29px;line-height:1.55;color:{C["text2"]};margin:0 0 0;'
               f'word-break:keep-all;max-width:{TEXT_MAX}">{first_sentence(cp.get("수급해설"), CUT["수급해설"])}</p>'

             # 예탁금 — 숫자만 던지지 않는다. **늘었나 줄었나가 무슨 뜻인지**를 붙인다.
             + block("투자자 예탁금", C["muted"],
                     f'<div style="display:flex;justify-content:space-between;'
                     f'align-items:baseline">'
                     # '조'가 붙으므로 MONO를 못 쓴다 — `mono_if`가 알아서 SANS로 돌린다.
                     f'<span style="font-family:{mono_if("조")};font-size:44px;'
                     f'font-weight:700;color:{C["text"]}">{dv/10000:.1f}조</span>'
                     f'<span style="font-family:{mono_if("조")};font-size:30px;font-weight:700;'
                     f'color:{sign_color(dd)}">{signed(dd/10000, 1, "조")}</span></div>',
                     sub=("주식을 사려고 증권계좌에 넣어 둔 대기 자금 — "
                          + ("줄면 사려는 힘이 빠진 것" if dd < 0 else "늘면 살 돈이 들어온 것")),
                     top=30)

             # ⚠️ 상자를 `up`(빨강)으로 두면 **막대·바탕·라벨까지 전부 빨강**이 된다.
             #    2026-08-28에 세로만 고치고 여기를 빠뜨려 같은 지적을 두 번 받았다.
             #    상자는 조용하게(`pill`), 색은 **안쪽 등락률 숫자에만** 준다.
             + block("어제 오른 업종·테마", C["muted"], sector_rows(sectors),
                     sub="돈이 어느 쪽으로 몰렸는지 보여줍니다", top=34))
    return card(inner, "04 근거·수급")


def c05_calendar(o, cp, num, total):
    # ⚠️ 항목마다 **바탕을 깔아** 나눈다(2026-08-27 요청). 줄만으로는 어디서 끊기는지
    #    안 보였다. 오늘 것은 파란 왼쪽 막대로 한 번 더 도드라지게 한다.
    rows = ""
    items = sorted((cp.get("캘린더") or []),
                   key=lambda y: "오늘" not in y.get("when", ""))[:3]
    for i, x in enumerate(items):
        today = "오늘" in x.get("when", "")
        bar = f'border-left:3px solid {C["blue"]};' if today else ""
        rows += (f'<div style="background:{TINT};{bar}border-radius:{RADIUS}px;padding:20px 22px;'
                 f'margin-top:{16 if i else 0}px">'
                 # ⚠️ **D-숫자에 색을 준다** (2026-08-28 요청). 며칠 남았는지가
                 #    이 카드에서 제일 먼저 읽혀야 하는 값인데 흐린 회색이었다.
                 f'<div style="font-size:29px;font-weight:700;'
                 f'color:{C["blue"] if today else C["muted"]};'
                 f'margin-bottom:8px">{dcolor(x.get("when",""))}</div>'
                 f'<div style="font-size:33px;font-weight:700;color:{C["text"]};'
                 f'letter-spacing:-.02em">{x.get("what")}</div>'
                 f'<div style="font-size:29px;color:{C["text2"]};line-height:1.5;'
                 f'margin-top:8px;word-break:keep-all">{first_sentence(x.get("note",""), CUT["일정"])}</div></div>')
    inner = (head(C["blue"], "이번 주 일정", pg(num, total), "무엇이 시장을 흔들 수 있나")
             + f'<p style="font-size:29px;line-height:1.55;color:{C["text2"]};margin:0 0 22px;'
               f'word-break:keep-all;max-width:{TEXT_MAX}">{cp.get("캘린더해설","")}</p>'
             + f'<div>{rows}</div>'
             + f'<div style="font-size:29px;color:{C["faint"]};margin-top:20px">'
               f'※ 중요도 최상 등급 지표만 추렸습니다</div>')
    return card(inner, "05 캘린더")


def c06_opinion(o, cp, num, total):
    rows = ""
    # 카드는 요약 — **점수를 실제로 움직인 것 2건**만. 나머지는 세로형에서 본다.
    ops = sorted((cp.get("의견") or []), key=lambda y: y.get("부호", "flat") == "flat")
    # ⚠️ 항목마다 바탕을 깔고, 목표주가를 올렸나 내렸나를 **왼쪽 막대 색**으로 표시한다.
    for i, x in enumerate(ops[:2]):
        tone = x.get("부호", "flat")
        col = {"up": C["up"], "down": C["down"], "flat": C["muted"]}[tone]
        rows += (f'<div style="background:{TINT};border-left:3px solid {col};border-radius:{RADIUS}px;'
                 f'padding:20px 22px;margin-top:{16 if i else 0}px">'
                 f'<div style="display:flex;gap:12px;align-items:baseline;margin-bottom:9px">'
                 f'<span style="font-size:29px;color:{C["muted"]}">{x.get("날짜")}</span>'
                 f'<span style="font-size:29px;color:{C["muted"]}">{x.get("사")}</span>'
                 f'<span style="font-size:29px;font-weight:700;color:{C["text"]}">'
                 f'{x.get("종목")}</span></div>'
                 f'<div style="font-size:29px;line-height:1.5;color:{C["text2"]};'
                 f'word-break:keep-all">"{tint_pct(x.get("말"))}"</div>'
                 f'<div style="font-size:29px;color:{col};margin-top:9px;'
                 f'word-break:keep-all">→ {tint_pct(x.get("뜻"))}</div></div>')
    inner = (head(C["gold"], "기관 의견", pg(num, total), "증권가는 뭐라고 했나")
             + f'<p style="font-size:29px;line-height:1.55;color:{C["text2"]};margin:0 0 0;'
               f'word-break:keep-all;max-width:{TEXT_MAX}">'
               f'{first_sentence(cp.get("의견해설"), CUT["의견해설"])}</p>'
             + f'<div style="margin-top:22px">{rows}</div>'
             # ⚠️ 이 상자만 `padding:24px 28px`에 폭 86%였다. 다른 장의 `block()`은
             #    `15px 20px`에 전체 폭이다 — 같은 성격의 상자는 같은 규격이어야 한다
             #    (2026-08-28 지적). `block()`을 그대로 쓴다.
             + block("애널리스트 컨센서스", C["blue"],
                     f'<div style="font-size:29px;line-height:1.6;color:{C["text2"]};'
                     f'word-break:keep-all">'
                     f'{first_sentence(cp.get("컨센서스"), CUT["컨센서스"])}</div>'))
    return card(inner, "06 기관 의견")


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
    조각 = [f'<span style="white-space:nowrap">{x.get("종목", "")} '
           f'<b style="color:{부호색.get(x.get("부호"), C["muted"])}">{x.get("결과", "")}</b> '
           f'<span style="color:{C["muted"]}">{x.get("판정", "")}</span></span>'
           for x in xs[:4]]
    # ⚠️ 제목을 **줄 안으로** 넣는다. 별도 제목 줄을 두면 40px가 더 드는데,
    #    액션 카드에는 그만한 자리가 없다(실측: 제목 있으면 139px, 없으면 95px).
    return (f'<div style="margin-top:12px;padding-top:10px;'
            f'border-top:1px solid {C["line"]};font-size:27px;line-height:1.45;'
            f'color:{C["text2"]};word-break:keep-all">'
            f'<b style="color:{C["muted"]}">어제 후보</b> · ' + " · ".join(조각) + '</div>')


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

    def sig(lab, txt, lc):
        """긍정·부정을 왼쪽 색 막대로 가른다 — 색은 옅게, 라벨 글자만 진하게."""
        if not txt:
            return ""
        return (f'<div style="background:{lc}0f;border-left:3px solid {lc};'
                f'border-radius:{RADIUS}px;padding:15px 20px;margin-top:{GAP}px">'
                f'<div style="font-size:29px;color:{lc};font-weight:700;'
                f'letter-spacing:{LS_KO}">{lab}</div>'
                f'<div style="font-size:29px;line-height:1.45;color:{C["text2"]};'
                f'margin-top:6px;word-break:keep-all">{txt}</div></div>')

    return (
        # 종목 사이는 **굵은 줄**로 나눈다 — 신호가 여러 줄이라 얇은 줄로는 안 갈린다.
        # ⚠️ 이 선은 **종목 사이를 가르는** 것이지 제목 밑줄이 아니다. 첫 종목에까지
        #    그리면 제목 바로 아래에 띠가 생겨, 참고사항 상자가 있는 첫 장과
        #    없는 둘째 장의 제목 모양이 달라진다(2026-08-28 지적).
        # ⚠️ 이 선은 **종목 사이를 가르는** 것이지 제목 밑줄이 아니다. 한 장의 첫 종목에
        #    그리면 제목 바로 아래에 띠가 생겨, 다른 장 제목과 모양이 달라진다.
        #    `idx`는 전체 순번이라 둘째 장(idx=2)에서 선이 되살아났다 — 장 기준으로 본다.
        f'<div style="{"" if first_on_card else f"border-top:2px solid {C['line']};"}'
        f'padding:{4 if first_on_card else 18}px 0 4px">'
        # ⚠️ 등급 배지가 카드 폭 100%까지 나가고 신호 상자는 86%에서 끝나 **오른쪽이
        #    어긋나 보였다**(2026-08-28 지적). 머리줄도 같은 폭 안에 넣어 끝을 맞춘다.
        # ⚠️ 신호 상자는 **다른 장의 상자와 같은 폭**이어야 한다(2026-08-28 지적).
        #    예전엔 여기만 86%로 좁혀 놓아 03·04 카드의 상자보다 작아 보였다.
        #    폭 제한을 없애면 머리줄 배지도 상자 끝과 자연히 맞는다.
        f'<div>'
        f'<div style="display:flex;gap:14px;align-items:baseline">'
        f'<span style="font-size:29px;color:{C["muted"]};flex:none">{idx:02d}</span>'
        f'<span style="font-size:36px;font-weight:800;color:{C["text"]};'
        f'letter-spacing:-.03em">{p["name"]}</span>'
        f'<span style="font-size:29px;color:{C["muted"]}">{p["code"]}</span>'
        f'<span style="margin-left:auto;padding:6px 15px;border-radius:999px;'
        f'border:1px solid {col};color:{col};font-size:29px;font-weight:700;'
        f'white-space:nowrap;letter-spacing:{LS_KO}">{p["grade"]} {word}</span></div>'
        f'<div>'
        + sig("긍정 신호", first_sentence(me.get("강한신호"), CUT["신호"]), C["up"])
        + sig("부정 신호", first_sentence(me.get("고려할점"), CUT["신호"]), C["down"])
        # ⚠️ **손절선과 발굴가를 같이 준다** (2026-08-28 재검토). `entry_conditions`에
        #    이미 들어 있는데 첫 조건 하나만 쓰고 버리고 있었다. 살지 말지 정하는
        #    자리에서 "어디서 물러날지"가 빠지면 요약으로서 쓸모가 반이다.
        + (f'<div style="font-size:29px;color:{C["text2"]};margin-top:14px">'
           f'{numbers(p)}</div>' if numbers(p) else "")
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
        + "</div></div>")


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
    return (f'<div style="margin-top:16px;padding:14px 20px;background:{TINT};border-radius:{RADIUS}px">'
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
        lead = (f'<div style="padding:14px 20px;background:{TINT};border-radius:{RADIUS}px;'
                f'border-left:3px solid {C["pill"]}">'
                + kicker("참고사항", C["muted"], 26)
                + f'<div style="height:10px"></div>{grade_legend(26)}'
                + f'<div style="font-size:29px;line-height:1.5;color:{C["text2"]};'
                  f'margin-top:12px;word-break:keep-all">'
                  # ⚠️ **"되찾는지 보는 선"이 무슨 뜻인지 아무도 모른다** (2026-08-31 지적).
                # 무엇을 "본다"는 건지, 그래서 사라는 건지 말라는 건지가 빠져 있었다.
                # ⇒ **동사를 분명히 쓴다** — 넘으면 매수 검토, 내주면 매도.
                f'<b>확인</b>은 <b>이 값을 넘어야 매수를 검토</b>하는 선, '
                  f'<b>손절</b>은 <b>이 값을 내주면 파는</b> 선, '
                  f'<b>발굴</b>은 <b>직전 거래일 종가</b>입니다.</div></div>'
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
                + _전일픽(cp))
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
                for r in 판정[:3])
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
        tail = (f'<div style="padding:16px 20px;background:{TINT};border-radius:{RADIUS}px;'
                  f'border-left:3px solid {C["green"]}">'
                + kicker("장 시작 후 확인" if not _진입판정(o["date"]) else "장 시작 후 확인 · 09:05 결과",
                          C["green"], 26)
                + f'<div style="height:12px"></div>{checks}'
                # ⚠️ 면책은 **상자 안 마지막 줄**로 넣는다. 따로 블록을 두면 그만큼
                #    마지막 장만 높아져 끝나는 높이가 다른 장과 어긋난다(2026-08-28).
                + f'<div style="font-size:26px;color:{C["faint"]};margin-top:10px">'
                  f'투자 참고용이며 매수 권유가 아닙니다.</div></div>'
                # ── 셋째 항목 ──
                + f'<div style="height:14px"></div>'
                  f'<div style="border-top:1px solid {C["line"]};margin:0 0 22px"></div>'
                + (f'<div style="font-size:29px;color:{C["faint"]};'
                   f'line-height:1.5;word-break:keep-all">'
                   f'오늘 후보 {2 + rest}종목 중 둘만 실었습니다. '
                   f'나머지와 <b>자세한 근거는 세로 상세</b>에.</div>'
                   if rest > 0 else
                   f'<div style="font-size:29px;color:{C["faint"]};'
                   f'line-height:1.5;word-break:keep-all">'
                   f'<b>자세한 근거는 세로 상세</b>에 있습니다.</div>')
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
    본문 = (head(C["up"], "액션플랜", pg(num, total), title)
           + f'<div>{rows}<div style="border-top:2px solid {C["line"]}"></div></div>'
           + lead)
    inner = f'<div>{본문}</div>' + tail
    return card(inner, f"{num:02d} 액션플랜")


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
/* ⚠️ iOS Safari 텍스트 자동 확대 차단 — 카드는 배율(transform:scale)로 그리는데
   글자만 따로 커지면 카드 안에서 넘친다. */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
/* ⚠️⚠️ **좌우는 어떤 환경에서도 고정한다.** (2026-08-27 세 번째 지적)
   여기에 `overflow-x:clip` **하나만** 걸어 뒀던 게 화근이었다. `clip`은 비교적 새 값이라
   그 값을 모르는 엔진은 **선언 전체를 버린다** — 그러면 잠금이 통째로 사라진다.
   데스크톱 크롬에서는 393px에서도 넘침이 0으로 나오는데 아이폰에서는 밀렸다. 즉
   "어느 요소가 범인인지 재서 잡는" 방식이 여기서는 통하지 않는다. 뿌리에서 막는다.
     · `hidden`을 먼저 쓰고 `clip`으로 덮는다 — 모르는 엔진은 `hidden`에서 멈춘다.
     · `max-width:100%`로 뿌리 자체가 넓어지는 길도 닫는다.
   ⚠️ `.rail`(가로 카드)은 제 안에서 따로 스크롤하므로 이 규칙에 걸리지 않는다. */
html,body{overscroll-behavior-x:none;max-width:100%;overflow-x:hidden}
body{margin:0;background:#e8e4dc;-webkit-font-smoothing:antialiased;overflow-x:clip}
a{color:#9d7a17;text-decoration:none} a:hover{color:#c9a227}
.days{display:flex;gap:8px;overflow-x:auto;padding:20px 20px 0;scrollbar-width:none}
.days::-webkit-scrollbar{display:none}
/* ⚠️ 이 8px은 **카드가 아니라 페이지 UI**(날짜 버튼)다. `RADIUS`로 묶지 않는다
   — 카드 상자 모서리를 바꿀 때 버튼까지 따라 바뀌면 안 된다(2026-09-01). */
.day{flex:none;background:#efece5;border:1px solid #d5cec0;border-radius:8px;
  padding:9px 15px;cursor:pointer;text-align:left;font-family:inherit;
  font-size:12px;line-height:1.35;color:#6b665c;white-space:nowrap}
.day b{display:block;font-size:13px;font-weight:700;color:#1c1813}
.day[aria-selected="true"]{border-color:#1b3bf0;background:#fff}
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
.nav i.on{background:#1b3bf0;transform:scale(1.4)}
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
.arw:hover{background:#fff;border-color:#1b3bf0;color:#1b3bf0}
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
 //    다시 보인다 — 「가끔 안 나온다」의 정체가 이것이다
 var rails=[].slice.call(document.querySelectorAll('.rail:not(.qrail)'));
 // 배율(--s)은 퀀트 레일에도 필요하다 — 그것만 전부를 대상으로 한다
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
   // 끝에 닿으면 화살표를 흐리게 — 더 넘길 게 없다는 걸 눌러 보기 전에 알려 준다.
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
   // behavior를 넘기지 않는다 — CSS의 `scroll-behavior`가 결정하게 둔다.
   // 여기서 'smooth'를 박으면 CSS를 덮어써 `prefers-reduced-motion`을 무시하고,
   // 애니메이션이 없는 환경(헤드리스 측정 포함)에서는 아예 움직이지 않는다.
   r.scrollBy({left:(q.left+q.width/2)-(rr.left+rr.width/2)});
   // ⚠️ 스크롤 이벤트를 기다리지 않고 **여기서 바로** 표시를 갱신한다.
   //    `paint()`는 rAF 뒤에 도는 데다 부드러운 스크롤이 끝나야 제 위치를 재므로,
   //    누른 직후에는 이전 카드 기준으로 남아 있다 — 마지막 장까지 갔는데도
   //    다음 화살표가 켜져 보였다(2026-08-27). 목표 번호를 이미 아는데 기다릴 이유가 없다.
   mark(j,s.list.length);
 }
 if(prev) prev.addEventListener('click',function(){go(-1)});
 if(next) next.addEventListener('click',function(){go(1)});
 // 배율을 직접 계산한다. CSS로는 못 한다 — 위 스타일시트의 경고 참고.
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
 window.__cards={show:show,fit:fit,paint:paint};
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
    io.open(out, "w", encoding="utf-8").write(html)

    res = {"ok": True, "파일": out, "날짜수": len(days), "카드수": n_cards,
           "규격": f"{CARD_W}x{CARD_H}", "크기자": len(html), "최신": days[0]["date"]}
    if os.path.exists(URL_FILE):
        res["url"] = io.open(URL_FILE, encoding="utf-8-sig").read().strip() or None
    if missing:
        res["_경고"] = (f"서술 파일 없음: {missing}. `data\\card-copy\\<날짜>.json` 이 없으면 "
                        f"숫자만 나온다 — 카드뉴스의 목적을 잃는다.")
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
    print(json.dumps(build(date, out), ensure_ascii=False))


if __name__ == "__main__":
    main()








































































































