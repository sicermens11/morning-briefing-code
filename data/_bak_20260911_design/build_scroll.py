#!/usr/bin/env python3
r"""
build_scroll.py — 같은 브리핑을 **세로 스크롤 한 장**으로 렌더링

카드뉴스(`build_cards.py`)와 **내용은 같고 그릇만 다르다.** 입력도 똑같이 둘이다:
숫자는 `data\snapshots\<날짜>\`, 서술은 `data\card-copy\<날짜>.json`.
그래서 `build_cards`에서 로더를 그대로 빌려 쓴다 — 두 벌로 갈라놓으면 반드시 어긋난다.

내보내는 곳이 둘이라 `--mode`가 있다:

    web   — Artifact 웹페이지. 카드뉴스와 **어느 쪽이 읽기 좋은지 비교하려고** 만든다.
            웹폰트를 쓰고 폭이 넓고 글자가 크다. 기본값.
    gmail — 메일 `htmlBody`에 그대로 넣는 조각. 아래 제약이 전부 여기서 나온다.

⚠️ 두 모드의 차이는 **글꼴 스택·폭·글자 크기뿐**이다. 섹션 코드는 한 벌이다 —
   갈라놓으면 한쪽만 고치고 다른 쪽이 뒤처지는 일이 반드시 생긴다.

⚠️⚠️ **지메일은 보통 HTML을 못 받는다** (`--mode gmail`). 지메일 웹에서 **실제로 죽는 것들**:

     · `<style>` 블록과 `<link>` — 통째로 지운다. **그래서 모든 스타일은 인라인**이고
       웹폰트(Pretendard·JetBrains Mono)를 못 쓴다. 시스템 글꼴로 간다.
     · `display:flex` / `grid` / `position` / `transform` — 무시되거나 깨진다.
       **가로 배치는 `<table>`로만** 한다. 2000년대 방식이 맞다.
     · `<script>` — 지운다. 날짜 넘기기·스와이프 같은 건 애초에 불가능하다.
     · 배경 SVG data URI — 지운다. 카드뉴스의 배경 아트워크는 못 옮긴다.
     · `rem`/`vw` — `px`만 쓴다.

   그래서 이 버전의 성격은 **"마크다운 문서"**다. 화려함을 포기하고 위에서 아래로
   읽히는 것만 노린다. 카드뉴스가 훑어보기용이면 이건 정독용이다.

⚠️ 지메일 폭은 **600px**. 지메일 웹 본문이 그 근처에서 잘리고, 폰에서는
   `max-width:100%`로 접힌다. 더 넓히면 폰에서 가로 스크롤이 생긴다.
   웹은 **720px** — 한 줄이 너무 길면 눈이 다음 줄 첫머리를 못 찾는다.

`--mode gmail` 출력은 `htmlBody`에 그대로 넣을 수 있는 조각이다(`<html>`/`<head>` 없음).
"""
import argparse
import io
import json
import os
import re
import sys
from datetime import datetime
from itertools import zip_longest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_cards import (  # noqa: E402
    GRADE, LOG, WEEKDAY, _copy, _f, _snap, entry_text, pg,
)
from card_theme import (  # noqa: E402
    BRAND, C, FONTS, GRADE_HELP, LS_KO, RADIUS, TERMS, band_color, band_label,
    pct, sign_color, signed, tint_pct, link,
)
from card_theme import MONO as WEB_MONO  # noqa: E402
from card_theme import SANS as WEB_SANS  # noqa: E402
from card_theme import mono_if as _mono_if  # noqa: E402
# ⚠️ D-숫자 색칠은 가로·세로가 **같은 규칙**을 써야 한다. 한쪽만 고치면 또 갈린다.
from build_cards import dcolor  # noqa: E402

# ⚠️⚠️ **바탕색 깔린 상자는 `border-radius:{RADIUS}px`를 함께 준다** (2026-08-31).
#    가로 요약(`build_cards`)의 상자를 둥글게 하면서 여기를 빼먹어 **가로는 둥글고
#    세로는 각진** 상태가 됐다. 사이트를 직접 세어보고서야 발견했다 —
#    ⚠️ `check_layout`은 `section[data-label]`(카드)만 검사한다. **세로는 검사 대상이
#       아니라서, 여기가 어긋나도 아무도 알려주지 않는다.** 세로를 고칠 땐 눈으로 대조한다.
#    ⚠️ 표는 `cellspacing`을 쓰므로(= border-collapse가 아니므로) `<td>`에 모서리가 먹는다.

# 지메일에서 살아남는 글꼴만. 웹폰트는 `<link>`가 지워져서 못 쓴다.
MAIL_SANS = "-apple-system,'Segoe UI','Malgun Gothic','Apple SD Gothic Neo',sans-serif"
MAIL_MONO = "'SFMono-Regular',Consolas,'D2Coding',monospace"

# 섹션 코드가 읽는 현재 설정. `build()`가 모드에 따라 갈아 끼운다.
SANS, MONO, W = MAIL_SANS, MAIL_MONO, 600

# 웹은 글자를 키운다. 메일은 좁은 칸에 들어가야 해서 15px가 상한인데, 웹에서 그대로 쓰면
# 작다. **크기를 두 벌로 적지 않고** 마지막에 한 번 곱한다 — 두 벌로 적으면 한쪽만 고친다.
WEB_SCALE = 1.18


def _scale_px(html, k):
    """`font-size:15px` 같은 인라인 값만 골라 배율을 먹인다.

    ⚠️ `font-size`만 건드린다. padding·margin까지 같이 키우면 표 칸이 어긋난다 —
       여백은 이미 600px 기준으로 맞춰 놨고, 폭이 720px로 넓어지면서 자연히 넉넉해진다.
    """
    return re.sub(r"font-size:(\d+)px",
                  lambda m: f"font-size:{round(int(m.group(1)) * k)}px", html)


def mono_if(text):
    """한글이 섞이면 MONO를 안 쓴다 — **지금 모드의 글꼴 스택으로** 판정한다."""
    return _mono_if(text, MONO, SANS)


# ── 조각 ────────────────────────────────────────────────────────
def h2(num, label, title, color):
    r"""섹션 머리 — 카드뉴스의 `head()`와 같은 자리, 같은 순서.

    ⚠️ 섹션 사이를 **굵은 줄**로 끊는다(2026-08-27 요청). 세로형은 한 번에 다 쏟아져
       내려오기 때문에, 어디서 새 섹션이 시작하는지가 보이지 않으면 읽다 길을 잃는다.
       라벨 칸에 옅은 바탕을 깔아 색으로도 갈리게 한다.
    """
    return (
        # ⚠️ 첫 섹션은 표지 바로 아래라 **위 공백을 두지 않는다**(2026-08-28 요청).
        #    56px를 그대로 주면 표지와 본문 사이가 휑하게 벌어진다.
        # ⚠️ **섹션 머리 색은 하나다** (2026-08-28). 섹션마다 색이 돌아가면 색이
        #    "무슨 뜻"이 아니라 "그냥 장식"이 된다. 본문에서 색은 오르내림(빨강·파랑)과
        #    강조(금색)에만 쓴다. 머리는 `head` 한 색만 쓰고 **다른 데서는 안 쓴다**.
        f'<div style="border-top:3px solid {C["head"]};'
        f'margin:{16 if str(num) == "01" else 56}px 0 0"></div>'
        # ⚠️ **대제목과 번호는 검정이다** (2026-08-28). 청동색 하나로 대·소제목을 다 칠했더니
        #    둘이 구분되지 않았다. 제목은 검정, 소제목은 청동(`sub`), 본문은 회갈색으로
        #    **색으로도 층을 만든다.** 띠와 바탕은 청동을 유지해 섹션 경계를 표시한다.
        f'<div style="background:{C["head"]}14;border-radius:{RADIUS}px;padding:13px 16px">'
        f'<span style="font-family:{MONO};font-size:17px;letter-spacing:.14em;'
        f'color:{C["text"]};font-weight:700">{num}</span>'
        f'<span style="font-size:23px;font-weight:800;color:{C["text"]};'
        f'margin-left:12px;letter-spacing:{LS_KO}">{label}</span></div>'
        + (f'<h2 style="font-family:{SANS};font-size:24px;font-weight:800;line-height:1.3;'
           f'letter-spacing:-.02em;color:{C["text"]};margin:18px 0 0">{title}</h2>'
           if title else ""))


def p(text, size=15, color=None, top=18):
    if not text:
        return ""
    text = tint_pct(text)
    return (f'<p style="font-family:{SANS};font-size:{size}px;line-height:1.7;'
            f'color:{color or C["text2"]};margin:{top}px 0 0;word-break:keep-all">{text}</p>')


def rule(top=26):
    return (f'<div style="border-top:1px solid {C["line"]};margin:{top}px 0 0;'
            f'font-size:0;line-height:0">&nbsp;</div>')


def bullets(items, mark="·", color=None):
    """`<ul>`은 지메일이 들여쓰기를 제멋대로 준다. 표로 그린다."""
    if not items:
        return ""
    rows = "".join(
        f'<tr><td valign="top" style="font-family:{SANS};font-size:15px;line-height:1.7;'
        f'color:{color or C["muted"]};padding:3px 8px 3px 0;width:14px">{mark}</td>'
        f'<td style="font-family:{SANS};font-size:15px;line-height:1.7;'
        f'color:{C["text2"]};padding:3px 0;word-break:keep-all">{tint_pct(x)}</td></tr>'
        for x in items)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin:12px 0 0">{rows}</table>')


def grid(cells, per=3):
    r"""칸을 **`per`개씩 줄바꿈**해서 격자로 놓는다. `cols()`는 한 줄에 다 넣는다.

    ⚠️ 업종 11개를 두 칸 표로 늘어놓으면 화면이 세로로만 길어진다(2026-08-28 지적).
       셋씩 묶으면 네 줄에 들어가고, 어느 업종이 위인지 한눈에 비교된다.
    """
    if not cells:
        return ""
    w = round(100 / per, 2)
    out = ""
    for i in range(0, len(cells), per):
        row = cells[i:i + per]
        tds = "".join(
            f'<td width="{w}%" valign="top" style="padding:12px 10px;'
            f'border:1px solid {C["line"]};word-break:break-word">'
            f'<div style="font-family:{SANS};font-size:13px;font-weight:700;'
            f'color:{C["muted"]};margin-bottom:6px">{lab}</div>'
            f'<div style="font-family:{MONO};font-size:18px;font-weight:700;'
            f'color:{col}">{val}</div></td>'
            for lab, val, col in row)
        tds += f'<td width="{w}%"></td>' * (per - len(row))
        out += f'<tr>{tds}</tr>'
    # ⚠️ `.cols`를 쓰면 안 된다 — 좁은 화면에서 칸을 **세로로 접는** 규칙이 걸려 있어
    #    3칸 격자가 한 줄씩 쌓인다(2026-08-28 지적). 전용 클래스로 접힘을 피한다.
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="6" '
            f'border="0" class="g3" style="margin:14px 0 0;table-layout:fixed;'
            f'width:100%">{out}</table>')


def _전일등급(date):
    """직전 브리핑 날짜의 **종목명 → 등급** 표. 없으면 빈 표를 돌려준다.

    ⚠️ `card-copy`의 `전일픽`에는 등급이 없다. 로그(JSONL)에는 `grade`가 있으므로
       **date보다 앞선 가장 최근 날짜**의 `picks`에서 끌어온다.
    ⚠️ 못 찾으면 조용히 비운다. 등급을 지어내면 성적 대조 자체가 거짓이 된다.
    """
    import json as _json
    앞 = None
    try:
        with io.open(LOG, encoding="utf-8-sig") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    d = _json.loads(ln)
                except ValueError:
                    continue
                dt = d.get("date")
                if dt and dt < (date or "9999"):
                    if 앞 is None or dt > 앞.get("date", ""):
                        앞 = d
    except OSError:
        return {}
    if not 앞:
        return {}
    return {p.get("name"): p.get("grade") or "" for p in (앞.get("picks") or []) if p.get("name")}


def cols(cells, big=False, fold=True):
    r"""가로 N칸. flex/grid가 죽으므로 `<table>`로 그린다.

    ⚠️ **`table-layout:fixed`가 없으면 안 된다.** 기본값(`auto`)에서는 칸 안의 글자가
       길면 표가 `width:100%`를 무시하고 제 마음대로 넓어진다. 2026-08-27에 아이폰
       폭(390px)에서 이 표가 **446px로 벌어져** 페이지 전체에 가로 스크롤이 생겼고,
       세로로 내릴 때 좌우로 딸려 움직였다.

    ⚠️ 바깥 음수 마진(`margin:… -6px`)도 같은 이유로 뺐다. `cellspacing`을 상쇄하려고
       넣었는데, 그만큼 표가 부모 밖으로 나간다.

    `class="cols"`는 **웹 모드 전용**이다 — 좁은 화면에서 칸을 세로로 접는 데 쓴다.
    지메일은 `<style>`을 지우므로 클래스가 무시되고 표 그대로 나온다(그래서 무해하다).
    """
    if not cells:
        return ""
    # ⚠️ `big`은 **이름표가 주인공인 칸**에 쓴다(2026-08-31 요청: "S&P500 이런 거 잘 보이게").
    #    지수 이름·수급 주체는 숫자만큼 중요하다 — 무엇의 숫자인지 모르면 숫자도 못 읽는다.
    #    ⚠️ 값 글자를 키우지 않고 **이름표만** 키운다. 둘 다 키우면 칸이 넘쳐 좁은 화면에서
    #       접힌다(2026-08-27 아이폰 가로 스크롤 사고와 같은 자리다).
    lab_css = (f'font-size:15px;font-weight:800;color:{C["text"]};'
               f'letter-spacing:{LS_KO};margin-bottom:8px'
               if big else f'font-size:12px;color:{C["muted"]};margin-bottom:7px')
    val_px = 22 if big else 19
    w = round(100 / len(cells), 2)
    tds = "".join(
        f'<td width="{w}%" valign="top" style="padding:14px 10px;'
        f'border:1px solid {C["line"]};word-break:break-word">'
        f'<div style="font-family:{mono_if(lab)};{lab_css}">{lab}</div>'
        f'<div style="font-family:{mono_if(val)};font-size:{val_px}px;font-weight:700;'
        f'color:{col}">{val}</div></td>'
        for lab, val, col in cells)
    # ⚠️ `fold=False`면 **좁은 화면에서도 안 접힌다**(`colsx`). 지수 셋·수급 셋처럼
    #    나란히 놓여야 비교가 되는 것에만 쓴다. 접힘 대신 글자가 줄어든다.
    return (f'<table class="{"cols" if fold else "colsx"}" role="presentation" '
            f'width="100%" cellpadding="0" '
            f'cellspacing="6" border="0" '
            f'style="margin:16px 0 0;table-layout:fixed;width:100%">'
            f'<tr>{tds}</tr></table>')


def tinted(label, sub, items, tone, mark="·", lead=""):
    r"""제목 + 한 줄 설명 + 목록. **배경색을 쓰지 않는다.**

    ⚠️ 2026-08-27에 이걸 색 박스로 감쌌다가 "완전 구려졌다"는 지적을 받고 되돌렸다.
       구분은 얇은 줄로 하고, 색은 **라벨 글자에만** 준다.
       `tone`은 이제 라벨 색만 고른다 — pos(초록)·neg(붉은)·info(파랑).
    """
    if not items:
        return ""
    # ⚠️ 상승이 빨강이 되면서 `pos` 상자가 **막대·바탕·라벨까지 전부 빨강**이 됐다
    #    (2026-08-28 지적: "배경도 빨간색이라 너무 튄다"). 숫자는 빨강이 맞지만
    #    상자까지 빨갛게 하면 눈이 아프다. `plain`은 상자를 조용하게 두고
    #    **안쪽 숫자만** 색이 살아나게 한다.
    fg = {"pos": C["up"], "neg": C["down"], "info": C["blue"],
          "plain": C["muted"]}[tone]
    rows = "".join(
        f'<tr><td valign="top" style="font-family:{SANS};font-size:14px;line-height:1.7;'
        f'color:{fg};padding:3px 8px 3px 0;width:14px">{mark}</td>'
        f'<td style="font-family:{SANS};font-size:15px;line-height:1.7;'
        f'color:{C["text2"]};padding:3px 0;word-break:keep-all">{tint_pct(x)}</td></tr>'
        for x in items)
    # 왼쪽 색 막대 + 아주 옅은 바탕 — 카드뉴스의 `block()`과 같은 방식이다.
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin:26px 0 0"><tr>'
            f'<td width="3" style="background:{fg};font-size:0;line-height:0">&nbsp;</td>'
            f'<td style="background:{fg}0f;border-radius:{RADIUS}px;padding:13px 16px">'
            + (f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
               f'letter-spacing:{LS_KO};color:{C["sub"]}">{label}</div>' if label else "")
            + (f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
               f'margin-top:4px">{sub}</div>' if sub else "")
            # ⚠️ `lead`는 상자 **안쪽 맨 위**에 오는 제목이다(2026-08-28). 목록 항목으로
            #    넣으면 글머리 기호가 붙어 항목처럼 보인다.
            + lead
            + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
              f'border="0" style="margin:8px 0 0;table-layout:fixed;width:100%">{rows}</table>'
            + '</td></tr></table>')


def term_note(*names, top=20):
    """뜻을 모르면 문장이 안 읽히는 낱말만 아래에 풀어 준다. 정본은 `card_theme.TERMS`."""
    got = [(n, TERMS[n]) for n in names if n in TERMS]
    if not got:
        return ""
    rows = "".join(
        f'<div style="margin-top:{7 if i else 0}px">'
        f'<b style="color:{C["blue"]}">{n}</b>'
        f'<span style="color:{C["muted"]}">. {d}</span></div>'
        for i, (n, d) in enumerate(got))
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin:{top}px 0 0"><tr><td '
            f'style="border-top:1px solid {C["line"]};padding:14px 0 0;'
            f'font-family:{SANS};font-size:13px;'
            f'line-height:1.7;word-break:keep-all">{rows}</td></tr></table>')


def field(label, text, color=None, top=22):
    r"""**라벨을 위에, 글은 아래 전체 폭에.** 서술에는 표를 쓰지 않는다.

    ⚠️ 2026-08-27 지적: 갭 분석처럼 문장이 긴 항목을 이름·값 2단 표에 넣었더니
       글 칸이 화면의 60%밖에 안 돼 **줄바꿈이 너무 잦았고**, 좁은 화면에서는 표가
       밖으로 밀려 좌우로 흔들렸다. 표는 **짧은 지표 목록에만** 쓴다(`kv_table`).
       문장은 마크다운처럼 위아래로 쌓는다 — 글 폭이 100%가 되어 줄바꿈이 준다.
    """
    if not text:
        return ""
    fg = color or C["muted"]
    return (f'<div style="margin-top:{top}px">'
            f'<div style="font-family:{SANS};font-size:15px;font-weight:800;'
            f'letter-spacing:{LS_KO};color:{fg}">{label}</div>'
            f'<div style="font-family:{SANS};font-size:15px;line-height:1.75;'
            f'color:{C["text2"]};margin-top:5px;word-break:keep-all;'
            f'word-wrap:break-word;overflow-wrap:break-word">{tint_pct(text)}</div></div>')


def kv3_table(rows, label="", sub="", 강조색=None):
    r"""세 칸짜리 표 — **날짜 · 며칠 남음 · 내용**.

    ⚠️ 2026-08-28: 두 칸에 "09/01 D-4"를 한 덩어리로 넣었더니 D만 색·굵기가 붙어
       **그것만 튀었다.** 칸을 나누면 색을 옅게 해도 자기 자리에서 읽힌다.
    ⚠️ 좁은 화면에서는 `.kv`가 칸을 세로로 접는다(560px 미만). 3칸이라도 접히면
       한 줄씩 쌓이므로 자리가 모자라지 않는다 — 실측으로 확인했다.
    """
    if not rows:
        return ""
    강조색 = 강조색 or C["up"]
    # ⚠️⚠️ **네 번째 칸이 있으면 강조 행이다** (2026-08-31 신설).
    #    D-7에 열 몇 줄이 나오는데 **전부 같은 무게로 보여 무엇이 중요한지 안 보였다.**
    #    강조 기준은 **오늘 고른 종목과 연결된 일정** — 매수 판단에 직접 걸리는 것이다.
    #    ⚠️ 색만 바꾸지 않고 **왼쪽에 막대**를 둔다. 색맹이거나 화면이 어두워도 보이게.
    body = "".join(
        f'<tr style="background:{강조색 + "0f" if (len(r) > 3 and r[3]) else ("#17181a08" if i % 2 else "transparent")}">'
        f'<td valign="top" width="20%" style="font-family:{MONO};font-size:14px;'
        f'font-weight:700;line-height:1.7;padding:7px 8px 7px 10px;word-wrap:break-word;'
        f'color:{강조색 if (len(r) > 3 and r[3]) else C["text2"]};'
        f'border-left:3px solid {강조색 if (len(r) > 3 and r[3]) else "transparent"}">{d}</td>'
        f'<td valign="top" width="16%" style="font-family:{MONO};font-size:13px;'
        f'line-height:1.7;color:{C["muted"]};padding:7px 8px;'
        f'word-wrap:break-word">{dd}</td>'
        f'<td valign="top" width="64%" style="font-family:{SANS};font-size:14px;'
        f'line-height:1.7;color:{C["text2"]};padding:7px 10px 7px 0;'
        f'word-break:keep-all;word-wrap:break-word;overflow-wrap:break-word">{v}</td></tr>'
        for i, r in enumerate(rows) for d, dd, v in [r[:3]])
    head_ = ""
    if label:
        head_ = (f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
                 f'letter-spacing:{LS_KO};color:{C["sub"]};margin:26px 0 0">{label}</div>'
                 + (f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
                    f'margin-top:4px;word-break:keep-all">{sub}</div>' if sub else ""))
    return (head_ + f'<table role="presentation" width="100%" cellpadding="0" '
            f'cellspacing="0" class="kv kv3" border="0" '
            f'style="margin:8px 0 0;table-layout:fixed;width:100%">{body}</table>')


def kv_table(rows, label="", sub=""):
    r"""이름·값 두 칸짜리 표. 지표를 죽 늘어놓을 때 쓴다.

    ⚠️ 세로형은 **상세판**이라 지메일에 있는 표를 최대한 옮겨 온다(2026-08-27 합의).
       스냅샷에 이미 있는 값은 서술 파일을 거치지 않고 여기서 바로 그린다 —
       모델이 매일 옮겨 적게 하면 옮기다 틀린다.
    """
    if not rows:
        return ""
    # ⚠️ 키 칸에 `white-space:nowrap`을 걸지 않는다. 긴 이름("환율 · 원자재 · 미국 금리")이
    #    줄바꿈을 못 해 표를 밖으로 밀어냈다(2026-08-27). **칸 너비를 못 박고 접게 한다.**
    # ⚠️ `overflow-wrap`은 `break-word`를 쓴다. `anywhere`는 새 값이라 카톡 인앱
    #    브라우저 같은 오래된 엔진이 무시할 수 있고, 그러면 안 접혀서 표가 밀린다.
    # ⚠️ 한 줄 걸러 옅은 바탕을 깔아 눈이 행을 따라가게 한다(2026-08-27 요청).
    body = "".join(
        f'<tr style="background:{"#17181a08" if i % 2 else "transparent"}">'
        f'<td valign="top" width="38%" style="font-family:{SANS};font-size:14px;'
        f'line-height:1.7;color:{C["muted"]};padding:7px 12px 7px 10px;'
        f'word-break:keep-all;word-wrap:break-word;overflow-wrap:break-word">{k}</td>'
        f'<td valign="top" width="62%" style="font-family:{SANS};font-size:14px;'
        f'line-height:1.7;color:{C["text2"]};padding:7px 10px 7px 0;'
        f'word-break:keep-all;word-wrap:break-word;overflow-wrap:break-word">{v}</td></tr>'
        for i, (k, v) in enumerate(rows))
    head_ = ""
    if label:
        head_ = (f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
                 f'letter-spacing:{LS_KO};color:{C["sub"]}">{label}</div>'
                 + (f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
                    f'margin-top:4px">{sub}</div>' if sub else ""))
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin:26px 0 0"><tr><td '
            f'style="border-top:1px solid {C["line"]};padding:16px 0 0">{head_}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'class="kv" border="0" style="margin:8px 0 0;table-layout:fixed;width:100%">'
            f'{body}</table></td></tr></table>')


def grade_legend():
    """등급이 무슨 뜻인지. 뜻풀이는 `card_theme.GRADE_HELP`가 정본이다."""
    rows = "".join(
        f'<span style="white-space:nowrap;margin-right:16px">'
        f'<b style="color:{GRADE.get(e, (C["muted"], ""))[0]}">{e} {w}</b>'
        f'<span style="color:{C["muted"]}"> {d}</span></span>'
        for e, w, d in GRADE_HELP)
    return (f'<div style="font-family:{SANS};font-size:12px;line-height:1.9;'
            f'margin-top:12px;word-break:keep-all">{rows}</div>')


def callout(label, body, color):
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin:20px 0 0"><tr>'
            f'<td width="3" style="background:{color};font-size:0;line-height:0">&nbsp;</td>'
            f'<td style="background:{color}0d;border-radius:{RADIUS}px;padding:16px 18px">'
            # ⚠️ 라벨은 **본문 크기에 굵게**("후보끼리 얼마나 겹치나", "미국 직접 기회").
            #    작게 두면 본문에 묻혀 어디부터가 그 이야기인지 안 보인다(2026-08-28).
            f'<div style="font-family:{SANS};font-size:15px;letter-spacing:{LS_KO};'
            f'color:{color};font-weight:800;margin-bottom:8px">{label}</div>'
            f'<div style="font-family:{SANS};font-size:15px;line-height:1.7;'
            f'color:{C["text2"]};word-break:keep-all">{tint_pct(body)}</div></td></tr></table>')


# ── 섹션 7개 (카드뉴스와 같은 순서) ──────────────────────────────
def s01_cover(o, cp, num, total):
    dt = datetime.strptime(o["date"], "%Y-%m-%d")
    n = len(o.get("picks") or [])
    # ⚠️ 목차는 **실제 섹션과 같은 이름·같은 번호**여야 한다. 예전에는 "뉴스"·"시장 국면"이
    #    남아 있었는데 그 섹션들은 2026-08-28에 합쳐져 사라진 상태였다 — 목차만 옛 지도였다.
    # ⚠️ **한 줄에 넣으라는 요청인데, 좁은 화면에서는 긴 이름으로 불가능하다**
    #    (2026-08-28 실측: 13px 여섯 항목이 585px, 아이폰 본문 폭은 357px).
    #    글자를 8px로 줄이면 들어가지만 읽을 수가 없다. 그래서 **이름을 줄인다** —
    #    넓은 화면은 온전한 이름, 430px 아래는 짧은 이름. 둘 다 한 줄이다.
    # ⚠️ 좁은 화면에서 두 글자로 줄여 봤다가 되돌렸다(2026-08-28) — "한눈에·근거·수급"은
    #    무슨 말인지 알 수 없다. **이름은 온전히 쓰고, 안 들어가면 접힌다.**
    toc = "   ".join(
        f'<b style="color:{C["head"]}">{i:02d}</b> {t}' for i, t in enumerate(
            ["시장 한눈에", "근거 데이터", "국장 수급", "D-7 이벤트",
             "기관 의견", "액션플랜"], 1))
    return (
        f'<div style="font-family:{SANS};font-size:15px;letter-spacing:{LS_KO};'
        f'color:{C["gold"]};font-weight:700">{dt.strftime("%Y.%m.%d")} '
        f'{WEEKDAY[dt.weekday()]}요일 · 후보 {n}</div>'
        f'<h1 style="font-family:{SANS};font-size:38px;font-weight:800;line-height:1.15;'
        f'letter-spacing:-.03em;color:{C["text"]};margin:14px 0 0">{BRAND}</h1>'
        # ⚠️ 부제는 뺐다(2026-08-28) — 제목 바로 아래 목차가 오는 편이 낫다.
        # ⚠️ 목차는 **한 줄에** 둔다. 접히면 표지가 두 겹으로 보인다.
        + f'<div style="font-family:{SANS};font-size:13px;color:{C["faint"]};'
          f'margin-top:14px;padding-top:12px;border-top:1px solid {C["line"]};'
          f'line-height:1.9;word-break:keep-all" class="toc">{toc}</div>')


def dash_br(x):
    r"""`A — B` 를 두 줄로 나눈다. **`—` 뒤에서 줄을 바꾼다**(2026-08-28 요청).

    ⚠️ 색칠(`tint_pct`)을 **먼저** 하고 나눈다. 순서를 바꾸면 `<br>`이 들어간 순간
       `tint_pct`가 "이미 태그가 섞인 글"로 보고 손을 떼서 숫자 색이 사라진다.
    """
    t = tint_pct(x)
    return str(t).replace(" — ", "<br>", 1)


def s02_overview(o, cp, num, total):
    r"""**시장 한눈에** — 지메일 ①을 그대로 옮긴 자리.

    ⚠️ 2026-08-28에 두 번 합쳤다.
       · `s05_regime`(시장 국면) — 이 섹션 첫 줄과 내용이 통째로 겹쳤다.
       · `s03_news`(미국·한국 뉴스) — 기사가 미장 전반·전날 국장과 겹쳤다.
       지수 셋(S&P500·나스닥100·나스닥 선물)도 뉴스 섹션 맨 위에 따로 있었는데,
       **코스피 20일선 대비와 나란히 있어야** "어젯밤 밖은 어땠고 우리는 어디쯤인가"가
       한 줄에서 읽힌다. 그래서 맨 위 박스 한 줄로 모았다.

    ⚠️ 형식을 섞지 않는다 — 예전에는 미장 전반·미반영만 상자였고 전날 국장·핵심은
       표 한 칸이었다. "그 부분만 다른 게 의미가 없다"는 지적을 받아 전부 상자로 통일했다.
    """
    reg = o.get("market_regime") or {}
    mk = (_snap(o["date"], "fetch_market") or {}).get("summary") or {}
    kospi = mk.get("코스피") or {}
    snap_us = _snap(o["date"], "fetch_us")
    idx = snap_us.get("지수") or {}
    sec = snap_us.get("미국섹터") or {}
    com = snap_us.get("선물원자재") or {}

    # ── 맨 위 박스 한 줄 — 우리 자리 + 어젯밤 미국 ──────────────
    kv, band = reg.get("kospi_vs_sma20_pct"), reg.get("band", "")
    # ⚠️ 코스피 국면은 **박스 줄에 넣지 않는다**(2026-08-28 재조정). 위 세 칸은 어젯밤
    #    미국이고, 우리 자리는 성격이 다르다. 미장 전반을 읽은 **다음**, 전날 국장을
    #    읽기 **직전**에 큰 글씨로 놓아야 "밖은 저랬고 우리는 여기"가 순서대로 읽힌다.
    # ⚠️ 코스피 국면도 **미국 지수와 같은 네모 박스**로 그린다(2026-08-28 요청).
    #    하나만 다른 모양이면 "왜 저것만 다르지"가 된다. 내용은 그대로 둔다.
    # ⚠️ **국면 색은 국면을 따라간다** (2026-08-31 요청: "황금색이라 과열 느낌이 안 난다").
    #    금색은 어느 국면에서나 같아서 **색이 아무 말도 안 하고 있었다.**
    #    과열은 위로 뜬 것이니 상승색(빨강), 눌림은 아래로 처진 것이니 하락색(파랑).
    #    사이 구간은 조용한 색으로 둔다 — 중간까지 색을 주면 색의 뜻이 닳는다.
    #    ⚠️ 네 국면 전부에 색을 준다. `위`·`아래`를 회색으로 두면 색이 바뀌는 날이
    #       1년에 몇 번뿐이라 **색이 있다는 사실 자체를 못 알아챈다.**
    #       **방향은 색이, 세기는 말이** 말한다 — 색은 위/아래만, `과열`·`깊은 눌림`은 글자로.
    # ⚠️ **국면 이름에 문턱을 같이 쓴다**(2026-08-31 요청). `위`·`아래`만 있으면
    #    "얼마나 위인지"가 안 보인다. `과열(+3%↑)`처럼 기준이 붙어야 뜻이 선다.
    band = band_label(band)
    국면색 = band_color(band)
    온도 = cols([("코스피 · 20일 평균선 대비",
                 f'{pct(kv)}<span style="font-size:13px;font-weight:700;'
                 f'margin-left:8px">{band}</span>', 국면색)], big=True) if kv is not None else ""

    cells = []
    for nm, src, key in (("S&P 500", idx.get("S&P500"), "종가"),
                         ("나스닥 100", idx.get("나스닥100"), "종가"),
                         ("나스닥 선물", com.get("나스닥100 선물"), "현재")):
        if src:
            v = _f(src.get("등락률"), 0)
            cells.append((nm, f'{src[key]:,}<span style="font-size:14px">'
                              f' {pct(v)}</span>', sign_color(v)))

    def _n(k, key="종가"):
        v = (idx.get(k) or {}).get(key)
        return f'{v:,}' if isinstance(v, (int, float)) else "—"

    # ── 미장 전반 — 어젯밤 미국 (뉴스까지 여기로 합쳤다) ──────────
    미장 = []
    if sec:
        오른 = [k for k, v in sec.items() if (_f(v.get("등락률"), 0) or 0) > 0]
        top = max(sec.items(), key=lambda kv2: _f(kv2[1].get("등락률"), 0) or 0)
        미장.append(f'업종 {len(sec)}개 중 <b>{len(오른)}개만 상승</b>. 가장 많이 오른 곳은 '
                  f'<b>{top[0]} {tint_pct(pct(top[1].get("등락률")))}</b>입니다.')
    vix = idx.get("VIX") or {}
    if vix.get("종가") is not None:
        v = _f(vix.get("종가"), 0)
        b = "안정" if v < 15 else "보통" if v < 20 else "불안" if v < 30 else "공포"
        미장.append(f'공포지수(VIX) <b>{v}</b> {tint_pct(pct(vix.get("등락률")))}<br><b>{b} 구간</b>'
                  f'입니다. 15 미만이면 안정, 20을 넘으면 불안, 30을 넘으면 공포로 봅니다.')
    sf = com.get("S&P500 선물") or {}
    nf = com.get("나스닥100 선물") or {}
    if sf or nf:
        미장.append(f'지금 이 순간 미국 선물<br>S&P500 {tint_pct(pct(sf.get("등락률")))} · '
                  f'나스닥100 {tint_pct(pct(nf.get("등락률")))}. 현물 시장은 닫혀 있지만 선물은 '
                  f'열려 있어, 오늘 한국 장이 어느 쪽에서 출발할지를 미리 보여줍니다.')
    # ⚠️ 원자재는 **3칸 격자**로 놓는다(2026-08-31 요청). 예전엔 다섯 개를 가운뎃점으로
    #    이어 붙인 한 문단이었는데, 금·구리·원유가 문장 속에 묻혀 **하나씩 찾아 읽어야** 했다.
    #    격자로 놓으면 무엇이 오르고 내렸는지 한 번에 보인다.

    for x in (cp.get("미장뉴스") or []):
        미장.append(f'<b>{link(x.get("머리", ""), x.get("url"))}</b><br>{x.get("몸", "")}')

    # ── 전날 국장 — 어제 한국 (국장 뉴스도 여기로) ───────────────
    국장 = []
    if kospi:
        국장.append(f'코스피 <b>{kospi.get("지수", "—")}</b> '
                  f'{tint_pct(pct(kospi.get("등락률")))}로 마감했습니다.')
    if cp.get("수급해설"):
        국장.append(cp["수급해설"])
    for x in (cp.get("국장뉴스") or []):
        국장.append(f'<b>{link(x.get("머리", ""), x.get("url"))}</b><br>{x.get("몸", "")}')

    핵심 = cp.get("핵심") or cp.get("결론")
    # ⚠️ **박스는 자기 이야기 아래에 둔다** (2026-08-28 요청).
    #    지수 셋은 "어젯밤 미국" 이야기이고, 코스피 국면은 "어제 한국" 이야기다.
    #    맨 위에 다 모아 놓으면 무엇이 무엇의 숫자인지 짝이 끊긴다.
    def 머리(t):
        return (f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
                f'letter-spacing:{LS_KO};color:{C["sub"]};margin:30px 0 0">{t}</div>')

    # ⚠️ 부제("어젯밤 미국은 어땠나")는 **상자 안 맨 위**에 둔다(2026-08-28 요청).
    #    상자 밖에 두면 박스 줄과 본문 사이에 떠서 어느 쪽 제목인지 흐려진다.
    #    굵기·크기·색은 바깥 제목과 같게 맞춘다.
    def 속머리(t):
        return (f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
                f'letter-spacing:{LS_KO};color:{C["sub"]};margin-bottom:10px">{t}</div>')

    return (h2(pg(num, total), "시장 한눈에", "", C["gold"])
            + 머리("미장 전반")
            + cols(cells, big=True, fold=False)
            + tinted("", "", 미장, "plain", lead=속머리("어젯밤 미국은 어땠나"))
            # ⚠️ 원자재·환율은 여기 두지 않는다(2026-08-31). `근거 데이터`에 이미
            #    같은 표가 있어 **두 곳에 겹쳤다.** 겹치면 어느 쪽이 정본인지 흐려지고,
            #    한쪽만 고치는 날 두 화면이 어긋난다. 근거 데이터 한 곳으로 모았다.
            + 머리("전날 국장")
            + 온도
            + p(cp.get("시장국면"), top=12)
            + tinted("", "", 국장, "plain", lead=속머리("어제 한국은 어땠나"))
            + tinted("시장 이미 반영", "주가가 이미 올라 지금 들어가기엔 늦은 것",
                     [dash_br(x) for x in (cp.get("이미반영") or [])], "plain")
            + tinted("시장 미반영", "좋은 소식은 나왔는데 주가에 아직 안 붙은 것",
                     [dash_br(x) for x in (cp.get("미반영") or [])], "plain")
            + tinted("핵심 — 오늘을 한 문단으로", "", [핵심] if 핵심 else [], "info")
            + term_note("20일 평균선"))


def s04_evidence(o, cp, num, total):
    r"""**근거 데이터** — 지메일의 같은 이름 섹션. 해외 연관 + 오늘의 공시.

    ⚠️ 전부 스냅샷에서 바로 읽는다. 서술 파일에 옮겨 적게 하지 않는다 —
       매일 옮기면 옮기다 틀린다. `공시`만 `card-copy`에서 온다.
    """
    snap = _snap(o["date"], "fetch_us")
    sec = snap.get("미국섹터") or {}
    # ⚠️ 예전에는 `(XLK)` 같은 **ETF 종목코드를 그대로** 붙여 놨다. 2026-08-28 지적:
    #    "XLK는 미국 기술 ETF인데 그게 올랐다는 건지 모르겠다." 맞는 말이다 —
    #    이 줄이 말하려는 건 **그 업종 전체가 얼마나 올랐나**이지 ETF 시세가 아니다.
    # ⚠️ "기술"만 적으면 그게 업종인지 종목인지 모른다 — **"기술주"**로 적는다(2026-08-28).
    # ⚠️⚠️ **ETF 이름을 되살린다** (2026-08-31 요청: "근거가 되는 ETF 기재해줘. 원래 있었어").
    #    08-28에 `(XLK)`를 뺐던 이유는 **그게 주인공처럼 보였기** 때문이다
    #    ("XLK가 올랐다는 건지 모르겠다"). 뺀 것 자체가 과했다 — 그러면 이 숫자가
    #    **어디서 나온 값인지 확인할 길이 없어진다.**
    #    그래서 되살리되 **작고 흐리게, 뒤에** 붙인다. 주인공은 업종, ETF는 출처다.
    sec_rows = [(f'{k}주<span style="font-family:{MONO};font-size:11px;'
                 f'font-weight:600;color:{C["muted"]};margin-left:6px">'
                 f'({v.get("ETF","")})</span>',
                 pct(v.get("등락률")), sign_color(v.get("등락률")))
                for k, v in sorted(sec.items(),
                                   key=lambda kv: -(_f(kv[1].get("등락률"), 0) or 0))]
    bm = snap.get("해외벤치마크") or {}
    bm_rows = [(f'{k} · {v.get("섹터","")}', pct(v.get("등락률"))) for k, v in bm.items()]

    # ⚠️⚠️ **지메일의 "해외 연관" 표를 그대로 옮긴다** (2026-08-28 지시).
    #    예전 "해외 같은 업종 회사"는 회사 이름과 등락률만 있어서 **그래서 뭘 보라는
    #    건지**가 빠져 있었다. 지메일에는 "→ 오늘 국장 연관주" 칸이 있고 거기에
    #    "국내 연관: 지니언스·라온시큐어 · 미반영"처럼 **연결이 적혀 있다.** 그게 핵심이다.
    링크 = ""
    for x in (cp.get("해외연관") or []):
        등락 = x.get("등락", "")
        링크 += (f'<div style="border-top:1px solid {C["line"]};padding:13px 0">'
                f'<span style="font-family:{SANS};font-size:15px;font-weight:700;'
                f'color:{C["text"]}">{link(x.get("종목",""), x.get("url"))}</span>'
                f'<span style="font-family:{MONO};font-size:15px;font-weight:700;'
                f'margin-left:10px">{tint_pct(등락)}</span>'
                f'<span style="font-family:{SANS};font-size:13px;color:{C["muted"]};'
                f'margin-left:10px">{x.get("섹터","")}</span>'
                # ⚠️ **국내 연관주가 이 표의 결론이다** (2026-08-28 지시).
                #    "그래서 오늘 뭘 보라는 건가"가 바로 이 종목들인데, 설명 문장에
                #    묻혀 있으면 눈에 안 들어온다. 칩으로 따로 뽑아 앞에 세운다.
                + ("".join(
                    f'<span style="display:inline-block;font-family:{SANS};font-size:13px;'
                    f'font-weight:700;color:{C["gold"]};background:#c9a2271f;'
                    f'padding:4px 10px;margin:8px 6px 0 0">{n}</span>'
                    for n in (x.get("국내") or []))
                   or "")
                + f'<div style="font-family:{SANS};font-size:14px;line-height:1.7;'
                  f'color:{C["text2"]};margin-top:7px;word-break:keep-all">'
                  f'{tint_pct(x.get("연관",""))}</div></div>')
    if 링크:
        링크 = (f'<div style="margin-top:26px">'
              f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
              f'letter-spacing:{LS_KO};color:{C["sub"]}">어젯밤 해외에서 크게 움직인 회사</div>'
              f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
              f'margin-top:4px">그 회사와 같은 일을 하는 <b>국내 종목</b>이 오늘 움직일 수 '
              f'있습니다. 아래가 그 연결입니다</div>{링크}</div>')
    com = snap.get("선물원자재") or {}
    # ⚠️ **세로 목록이 아니라 3칸 격자로 놓는다**(2026-08-31 요청). 여섯 줄을 세로로
    #    늘어놓으면 화면 한 판을 다 먹으면서도 **무엇이 오르고 내렸는지 비교가 안 된다.**
    #    격자면 두 줄에 들어가고 색으로 방향이 한 번에 읽힌다.
    com_cells = [(k, f'{v.get("현재"):,} <span style="font-size:14px">'
                    f'{pct(v.get("등락률"))}</span>', sign_color(v.get("등락률")))
                 for k, v in com.items() if k not in ("S&P500 선물", "나스닥100 선물")]
    ust = snap.get("미국채금리") or {}
    if ust:
        # ⚠️ 국채는 **등락률이 아니라 수준**이라 색을 주지 않는다. 4.73%가 오른 건지
        #    내린 건지 이 값만으론 모른다 — 모르는 것에 색을 주면 색이 거짓말을 한다.
        com_cells.append(("미국 국채 10년 / 2년",
                          f'{ust.get("10년","—")}% / {ust.get("2년","—")}%', C["text"]))
    return (h2(pg(num, total), "근거 데이터", "", C["gold"])
            + f'<div style="font-family:{SANS};font-size:14px;color:{C["faint"]};'
              f'margin-top:10px">※ 매수 추천이 아닙니다. 아래 액션플랜의 근거 참고용입니다.</div>'
            + f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
              f'letter-spacing:{LS_KO};color:{C["sub"]};margin:26px 0 0">'
              f'어젯밤 미국 업종 흐름</div>'
              f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
              f'margin-top:4px;word-break:keep-all">미국 증시를 11개 업종으로 나눴을 때 '
              f'어제 각 업종이 얼마나 올랐는지입니다. 우리 시장의 같은 업종이 따라가는 '
              f'경우가 많습니다</div>'
            + grid(sec_rows, 3)
            + (링크 if 링크
               else kv_table(bm_rows, "해외 같은 업종 회사",
                             "우리 종목과 같은 사업을 하는 해외 회사들의 어제 움직임"))
            + (f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
               f'letter-spacing:{LS_KO};color:{C["sub"]};margin:26px 0 0">'
               f'환율 · 원자재 · 미국 금리</div>'
               f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
               f'margin-top:4px;word-break:keep-all">우리 시장 밖에서 값이 정해지는 것들입니다. '
               f'오늘 어느 업종이 유리한지를 여기서 먼저 읽습니다</div>'
               + grid(com_cells, 3)
               + p("유가가 오르면 조선·정유·화학이 유리하고, 구리가 오르면 전력 설비·전선이 "
                   "유리합니다. 금은 불안할 때 오릅니다. 원/달러가 오르면 외국인이 한국 주식을 "
                   "팔기 쉬워지고, 미국 국채 금리가 오르면 빚이 많은 회사가 불리해집니다.",
                   top=12)
               if com_cells else "")
            + (callout("오늘의 공시", cp.get("공시", ""), C["blue"])
               if cp.get("공시") else ""))


def s06_flows(o, cp, num, total):
    mk = (_snap(o["date"], "fetch_market") or {}).get("summary") or {}
    kospi, dep = mk.get("코스피") or {}, mk.get("예탁금") or {}
    kv = _f(kospi.get("등락률"), 0)
    dv, dd = _f(dep.get("투자자예탁금_억원"), 0), _f(dep.get("전일대비_억원"), 0)
    # ⚠️ 카드뉴스와 같은 규칙 — 투자자별 금액은 스냅샷에 없다. 없으면 안 그린다.
    fl = [(x.get("주체", ""), x.get("값", ""),
           {"up": C["up"], "down": C["down"]}.get(x.get("부호"), C["muted"]))
          for x in (cp.get("수급") or [])]
    # 섹터 흐름 — 어제 어느 업종·테마로 돈이 몰렸는지(2026-08-27 추가 요청).
    # ⚠️ 상자는 조용하게(`plain`) 두고 **숫자만** 오르내림 색을 준다(2026-08-28).
    sectors = [f'{x.get("이름")} '
               f'<b style="color:{sign_color(x.get("등락률"))}">{pct(x.get("등락률"))}</b>'
               for x in ((mk.get("업종랭킹") or [])[:3]
                         + (mk.get("테마랭킹") or [])[:2])[:5]]
    return (h2(pg(num, total), "국장 수급", "", C["green"])
            + f'<div style="margin-top:18px">'
              f'<span style="font-family:{MONO};font-size:34px;font-weight:700;'
              f'color:{C["text"]};letter-spacing:-.02em">{kospi.get("지수","—")}</span>'
              f'<span style="font-family:{MONO};font-size:17px;font-weight:700;'
              f'color:{sign_color(kv)};margin-left:12px">{pct(kv)}</span>'
              f'<span style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
              f'margin-left:10px">코스피</span></div>'
            # ⚠️ **외국인·기관·개인은 이름표가 주인공이다**(2026-08-31 요청).
            #    "−1조7,585억"만 커 봐야 누가 판 돈인지 모르면 아무 뜻이 없다.
            + cols(fl, big=True, fold=False) + p(cp.get("수급해설"))
            + rule(22)
            # 예탁금 — 숫자만 던지지 않는다. 늘었나 줄었나가 **무슨 뜻인지**를 붙인다.
            + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
              f'border="0" style="margin:20px 0 0"><tr><td '
              f'style="border-top:1px solid {C["line"]};padding:14px 0 0">'
              f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
              f'border="0"><tr>'
              # ⚠️ 항목 이름은 **본문 크기에 굵게** — 다른 라벨과 같은 규격이다.
              f'<td style="font-family:{SANS};font-size:15px;font-weight:800;'
              f'color:{C["text"]}">투자자 예탁금</td>'
              f'<td align="right" style="font-family:{SANS};font-size:21px;font-weight:700;'
              f'color:{C["text"]}">{dv/10000:.1f}조'
              f'<span style="font-size:15px;color:{sign_color(dd)};margin-left:10px">'
              + signed(dd / 10000, 1, "조") + '</span></td></tr></table>'
            + f'<div style="font-family:{SANS};font-size:13px;line-height:1.65;'
              f'color:{C["text2"]};margin-top:8px;word-break:keep-all">'
              f'주식을 사려고 증권계좌에 넣어 둔 <b>대기 자금</b>입니다. '
              + ("줄었다는 건 사려는 힘이 그만큼 빠졌다는 뜻입니다."
                 if dd < 0 else "늘었다는 건 살 돈이 그만큼 들어왔다는 뜻입니다.")
            + '</div></td></tr></table>'
            # ⚠️ 지메일 ③에는 "수급 온도" 판정 한 문단이 있는데 세로에는 없었다
            #    (2026-08-28 대조). 숫자만 있고 **그래서 좋은 건지 나쁜 건지**가 빠져 있었다.
            + (callout("수급 온도", cp.get("수급온도", ""), C["green"])
               if cp.get("수급온도") else "")
            + tinted("어제 오른 업종·테마", "돈이 어느 쪽으로 몰렸는지 보여줍니다",
                     sectors, "plain", mark="▲")
            # 세로형 전용 상세 — 외국인이 실제로 무엇을 샀는지, 국고채 금리는 얼마인지.
            + kv_table([(f'{x.get("순위")}. {x.get("종목")}',
                         f'{int(_f(x.get("현재가"),0)):,}원 {pct(x.get("등락률"))}')
                        for x in (mk.get("외국인순매수상위") or [])[:8]],
                       "외국인이 가장 많이 산 종목",
                       "외국인은 큰돈을 굴리는 쪽이라, 이들이 사는 종목은 방향을 봅니다")
            + kv_table([(k, f'{v.get("금리")}%')
                        for k, v in (mk.get("국채금리") or {}).items()],
                       "한국 국채 금리",
                       "나라가 빌리는 값입니다. 오르면 회사가 빌리는 값도 같이 오릅니다"))


# ⚠️ 경제지표는 **회사 실적 발표가 아니다.** 2026-08-28에 사용자가 물었다 —
#    "한국 광공업생산·서비스업생산 직전 각각 +6.4%, +0.7% 이게 무슨 뜻이야? 회사야?"
#    지표 이름만 던지면 그렇게 읽힌다. 무엇을 재는 발표인지 한 마디로 풀어 준다.
#    ⚠️ 모르는 지표는 **지어내지 않는다** — 공통 설명만 붙인다.
_ECON_뜻 = [
    ("광공업생산", "공장이 얼마나 돌았는지"),
    ("산업생산", "공장이 얼마나 돌았는지"),
    ("서비스업생산", "식당·유통·운수 같은 서비스업이 얼마나 굴러갔는지"),
    ("소비자물가", "물가가 얼마나 올랐는지"),
    ("생산자물가", "공장 출고가 기준으로 물가가 얼마나 올랐는지"),
    ("수출", "나라 전체가 해외에 얼마나 팔았는지"),
    ("수입", "나라 전체가 해외에서 얼마나 사 왔는지"),
    ("무역수지", "판 돈에서 사 온 돈을 뺀 값"),
    ("소매판매", "사람들이 물건을 얼마나 샀는지"),
    ("실업률", "일자리를 못 구한 사람의 비율"),
    ("고용", "일자리가 얼마나 늘었는지"),
    ("비농업", "농업을 뺀 일자리가 얼마나 늘었는지"),
    ("구매관리자지수", "기업 구매 담당자에게 물어 만든 경기 체감 지수 — 50을 넘으면 확장"),
    ("PMI", "기업 구매 담당자에게 물어 만든 경기 체감 지수 — 50을 넘으면 확장"),
    ("GDP", "나라가 한 해 만들어 낸 가치의 총합"),
    ("기준금리", "중앙은행이 정하는 돈의 값"),
    ("경상수지", "나라 전체가 벌어들인 돈과 나간 돈의 차이"),
    ("건설수주", "건설 회사가 새로 따낸 일감"),
    ("소비자심리", "사람들이 살림살이를 어떻게 느끼는지 물어본 지수"),
    ("기업경기", "기업이 경기를 어떻게 느끼는지 물어본 지수"),
]
# 이름에 이 말이 들어 있으면 **변화율**이다 — 그때만 오르내림 색을 준다.
# ⚠️ PMI 55.6 같은 **수준 값에 색을 칠하면 거짓말**이 된다. 오른 게 아니라 그냥 값이다.
_ECON_변화 = ("전월비", "전년대비", "전년동월", "증감", "률", "율")


def _econ_line(x):
    """경제지표 한 줄 — 무슨 발표인지, 적힌 숫자가 무엇인지까지 말로."""
    name = str(x.get("지표") or "")
    뜻 = next((v for k, v in _ECON_뜻 if k in name), "")
    prev = x.get("이전치")
    변화 = any(k in name for k in _ECON_변화)
    if prev is None or prev == "":
        num = "지난번 값 없음"
    elif 변화:
        num = (f'지난번 발표 <b style="color:{sign_color(prev)}">{signed(prev, 1, "%")}</b>')
    else:
        num = f'지난번 발표 <b>{prev}</b>'
    기준 = ("전달과 비교한 값입니다" if "전월비" in name else
            "1년 전과 비교한 값입니다" if ("전년" in name) else "")
    끝 = " · ".join(y for y in [뜻, num, 기준] if y)
    return f'{name}<br><span style="color:{C["muted"]}">{끝}</span>'


def s07_calendar(o, cp, num, total):
    # ⚠️⚠️ **D-7 이벤트는 세 갈래다** (2026-08-28 지시, 지메일 ④와 같은 구성).
    #      ① 실적 발표 — 기업이 성적표를 내는 날
    #      ② 경제지표 — 정부·기관이 나라 전체 통계를 내는 날
    #      ③ 정책 발표 — 정부·국회 일정
    #    예전에는 이 셋이 뒤섞이고, 골라 쓴 실적과 스냅샷 실적 목록이 **따로 두 번** 나왔다.
    #    같은 회사가 두 번 보여 "뭐가 다르냐"는 지적을 받았다. 하나로 합친다.
    mk = (_snap(o["date"], "fetch_market") or {}).get("summary") or {}
    us = _snap(o["date"], "fetch_us")

    def _md(x):
        x = str(x)
        return f"{x[4:6]}/{x[6:8]}" if len(x) == 8 else x

    def _dday(ymd):
        try:
            d0 = datetime.strptime(str(o["date"]), "%Y-%m-%d").date()
            d1 = datetime.strptime(str(ymd), "%Y%m%d").date()
            return f'D-{(d1 - d0).days}'
        except Exception:  # noqa: BLE001
            return ""

    # ① 실적 발표 — 스냅샷이 전부를 주고, `card-copy` 캘린더가 **해설을 얹는다**.
    #    티커로 짝을 맞춘다. 해설이 붙은 것이 위로 온다.
    # ⚠️⚠️ **오늘 고른 종목이 언급된 일정은 강조한다** (2026-08-31 신설).
    #    D-7에 열 몇 줄이 나오는데 전부 같은 무게로 보였다. 무엇이 중요한지를 정하는 기준은
    #    **"오늘 판단에 직접 걸리나"**다 — 후보 종목 이름이 그 일정 해설에 나오면 걸리는 것이다.
    #    (예: 팔로알토 실적 → "안랩·지니언스에 온기" / HD현대일렉트릭 주총)
    #    ⚠️ 모델이 별도로 표시하지 않아도 된다. **이름이 나오는지만 보면 되므로 자동이다.**
    후보명 = [p.get("name", "") for p in (o.get("picks") or []) if p.get("name")]

    # ⚠️⚠️ **중요 기준 둘** (2026-08-31). 가로 요약과 같은 기준을 쓰되 하나를 더한다.
    #      ① **모델이 `card-copy`의 `캘린더`에 올린 것** — 그날 골라 해설까지 붙인 일정이다.
    #         가로 요약이 이 목록의 상위 3건만 싣는다. **모델이 이미 고른 것**이 곧 중요한 것.
    #      ② **오늘 후보 종목 이름이 나오는 것** — 매수 판단에 직접 걸린다.
    #    ⚠️ ①이 없으면 강조가 거의 안 걸린다. 실측: 팔로알토 해설이 어제 후보(안랩·지니언스)를
    #       말해서 ②만으로는 안 걸렸다. 그런데 모델은 그걸 "이번 주 최대 이벤트"로 꼽았다.
    골린티커 = {str(x.get("티커", "")).upper() for x in (cp.get("캘린더") or []) if x.get("티커")}
    골린내용 = " ".join(str(x.get("what", "")) + str(x.get("note", ""))
                     for x in (cp.get("캘린더") or []))

    def _중요(txt):
        t = str(txt)
        return any(nm and nm in t for nm in 후보명)

    해설 = {str(x.get("티커", "")).upper(): x for x in (cp.get("캘린더") or []) if x.get("티커")}
    ern = sorted((us.get("실적캘린더") or []),
                 key=lambda x: (x.get("D", 99), str(x.get("티커", "")).upper() not in 해설,
                                str(x.get("회사", ""))))
    ern_rows = []
    for x in ern:
        t = str(x.get("티커", "")).upper()
        note = (해설.get(t) or {}).get("note", "")
        body = f'{x.get("회사")} ({t}). 증권가 예상 <b>{x.get("예상EPS")}</b>'
        if note:
            body += (f'<div style="margin-top:5px;color:{C["text2"]}">'
                     f'{tint_pct(note)}</div>')
        ern_rows.append((_md(str(x.get("날짜", "")).replace("-", "")),
                         f'D-{x.get("D")}', body,
                         bool(note) or t in 골린티커 or _중요(x.get("회사"))))

    # ② 경제지표
    econ = [x for x in (mk.get("경제지표예정") or []) if int(x.get("중요도", 0)) >= 4]
    # ⚠️ 경제지표도 **모델이 캘린더에 올려 해설을 붙인 것**이면 강조한다.
    #    이름으로 맞춘다 — 티커가 없는 항목이라 다른 수가 없다.
    econ_rows = [(f'{_md(x.get("발표일"))} {x.get("국가")}', _dday(x.get("발표일")),
                  _econ_line(x),
                  bool(x.get("지표명") and str(x.get("지표명")) in 골린내용))
                 for x in econ]

    # ⚠️⚠️ **모델이 고른 일정 중 스냅샷에 없는 것을 따로 싣는다** (2026-08-31 신설).
    #    세로는 스냅샷만 보는데, 스냅샷 `경제지표예정`은 **사흘치**뿐이고 `지표명`도 비어 있다.
    #    실측: 모델은 09/04 미국 고용보고서를 "이번 주 방향을 정한다"고 꼽았는데
    #    스냅샷에 없어서 **가로 요약에만 나오고 세로 상세에는 통째로 빠졌다.**
    #    ⚠️ 세로가 상세인데 가로보다 적게 나오면 이름값을 못 한다.
    실린 = 골린티커 | {r[0] for r in ern_rows} | {r[0] for r in econ_rows}
    남은 = []
    for x in (cp.get("캘린더") or []):
        w = str(x.get("when", ""))
        t = str(x.get("티커", "")).upper()
        if t and t in {str(y.get("티커", "")).upper() for y in ern}:
            continue                      # 실적표에 이미 있다
        날 = w.split()[0] if w else ""
        dd = w.split()[-1] if "D-" in w else ""
        남은.append((날, dd,
                   f'<b>{x.get("what", "")}</b>'
                   + (f'<div style="margin-top:5px;color:{C["text2"]}">'
                      f'{tint_pct(x.get("note", ""))}</div>' if x.get("note") else ""),
                   True))                 # 모델이 고른 것이므로 전부 강조

    return (h2(pg(num, total), "D-7 이벤트", "", C["blue"])
            + p(cp.get("캘린더해설"))
            + f'<div style="font-family:{SANS};font-size:14px;color:{C["faint"]};'
              f'margin-top:8px">앞으로 이레 안에 있는 일정을 <b>실적 발표 · 경제지표 · '
              f'정책 발표</b> 셋으로 나눠 실었습니다.</div>'
            + kv3_table(ern_rows, "① 실적 발표",
                        "회사가 분기 성적표를 내는 날입니다. 옆 숫자는 <b>주당순이익 예상치</b>로, "
                        "회사가 주식 한 주당 얼마를 벌 것이라고 증권가가 미리 내놓은 값입니다 — "
                        "<b>주가 예상이 아닙니다.</b> 실제 발표가 이 값을 넘으면 대체로 주가에 좋고, "
                        "밑돌면 나쁩니다. 설명이 붙은 것은 <b>오늘 후보와 직접 연결되는 일정</b>입니다")
            + kv3_table(econ_rows, "② 경제지표",
                        "정부·기관이 정해진 날에 내는 나라 전체 통계입니다. 회사 실적이 아닙니다 — "
                        "적힌 숫자는 <b>지난번 발표값</b>이고, 이번에 그보다 좋게 나오는지가 "
                        "시장을 움직입니다")
            + kv3_table(남은, "③ 그 밖에 눈여겨볼 일정",
                        "실적표·지표표에 안 잡히지만 <b>오늘 브리핑이 따로 꼽은 일정</b>입니다 — "
                        "고용 지표·주주총회처럼 성격이 다른 것들입니다")
            + ((f'<div style="font-family:{SANS};font-size:19px;font-weight:800;'
                f'letter-spacing:{LS_KO};color:{C["sub"]};margin:26px 0 0">④ 정책 발표</div>'
                f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
                f'margin-top:4px;word-break:keep-all">정부·국회 일정입니다. 날짜가 확정되지 '
                f'않은 것이 많아 표 대신 문단으로 씁니다</div>'
                + p(cp.get("정책캘린더"), top=10))
               if cp.get("정책캘린더") else ""))


def s08_opinion(o, cp, num, total):
    rows = ""
    for x in (cp.get("의견") or []):
        col = {"up": C["up"], "down": C["down"]}.get(x.get("부호"), C["muted"])
        rows += (f'<div style="padding:16px 0;border-top:1px solid {C["line"]}">'
                 f'<div style="font-family:{SANS};font-size:13px;color:{C["muted"]}">'
                 f'{x.get("날짜")} · {x.get("사")} '
                 f'<span style="font-family:{SANS};font-size:15px;font-weight:700;'
                 f'color:{C["text"]}">{link(x.get("종목"), x.get("url"))}</span></div>'
                 f'<div style="font-family:{SANS};font-size:15px;line-height:1.65;'
                 f'color:{C["text2"]};margin-top:7px;word-break:keep-all">'
                 f'&ldquo;{x.get("말")}&rdquo;</div>'
                 f'<div style="font-family:{SANS};font-size:14px;color:{col};'
                 f'margin-top:6px;word-break:keep-all">&rarr; {x.get("뜻")}</div></div>')
    return (h2(pg(num, total), "기관 의견 · 애널리스트", "", C["gold"])
            + p(cp.get("의견해설"))
            + f'<div style="margin-top:14px">{rows}</div>' + rule(0)
            + callout("애널리스트 컨센서스", cp.get("컨센서스", ""), C["blue"]))


def s09_action(o, cp, num, total):
    picks, per = o.get("picks") or [], cp.get("종목") or {}
    rows = ""
    for i, pk in enumerate(picks):
        col, word = GRADE.get(pk["grade"], (C["muted"], ""))
        me = per.get(pk["code"]) or {}
        entry = entry_text(pk)
        # ⚠️ 종목마다 **옅은 바탕**으로 감싼다(2026-08-27 요청). 아래에 갭 분석·주의사항이
        #    여러 문단 붙기 때문에, 줄 하나로는 어디서 다음 종목이 시작하는지 안 보인다.
        rows += (f'<div style="background:#17181a08;'
                 f'border-left:3px solid {col};padding:18px 20px;margin-top:24px">'
                 f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                 f'border="0"><tr><td>'
                 f'<span style="font-family:{MONO};font-size:14px;color:{C["muted"]}">'
                 f'{i+1:02d}</span>'
                 f'<span style="font-family:{SANS};font-size:19px;font-weight:800;'
                 f'color:{C["text"]};margin-left:10px">{pk["name"]}</span>'
                 f'<span style="font-family:{MONO};font-size:14px;color:{C["muted"]};'
                 f'margin-left:8px">{pk["code"]}</span></td>'
                 f'<td align="right"><span style="font-family:{SANS};font-size:12px;'
                 f'font-weight:700;color:{col};border:1px solid {col};'
                 f'padding:3px 10px">{pk["grade"]} {word}</span></td></tr></table>'
                 # ⚠️ 지메일에는 등급 옆에 **갭 해당·품질참고**가 붙어 있는데 세로에는
                 #    통째로 없었다(2026-08-28 대조). 같은 종목을 두 곳에서 볼 때
                 #    한쪽에만 있는 표기가 있으면 "어느 게 맞나"가 된다.
                 + ((f'<div style="font-family:{SANS};font-size:14px;color:{C["muted"]};'
                     f'margin-top:7px;letter-spacing:{LS_KO}">'
                     + " · ".join(x for x in [me.get("갭해당"),
                                              (f'품질참고 {me["품질참고"]}'
                                               if me.get("품질참고") else "")] if x)
                     + '</div>')
                    if (me.get("갭해당") or me.get("품질참고")) else "")
                 # 긍정·부정을 **색이 다른 박스**로 나눈다. 줄글이면 뭐가 좋고 나쁜지 안 갈린다.
                 # ⚠️ 지메일에는 종목마다 **'핵심 근거'** 긴 서술이 맨 앞에 있는데
                 #    세로에는 없었다(2026-08-28 지적: "내용은 지메일 쪽이 더 충실하다").
                 #    "왜 이 등급인가"를 먼저 읽어야 아래 신호·갭이 뜻을 갖는다.
                 + field("왜 이 종목인가", me.get("핵심근거"), col, top=16)
                 # ⚠️⚠️ **긍정·부정 신호를 세로에서 뺐다** (2026-08-31).
                 #    스킬에 `강한신호`·`고려할점`은 **"카드(요약)용 한 줄"**이라고 적혀 있다.
                 #    바로 위 「왜 이 종목인가」가 같은 이야기를 문단으로 하고 있어서,
                 #    세로에서는 **자기 요약을 자기 밑에 또 붙이는 꼴**이었다.
                 #    ⚠️ 요약은 요약이 필요한 자리에만 둔다 — 가로 요약 카드가 그 자리다.
                 # ⚠️ 「언제 보나」→「언제 사나」 (2026-08-31 지적: "뭘 보라는 건지 모르겠다").
                 #    이 칸이 답하는 질문은 **"어느 값을 넘으면 매수를 검토하나"**다.
                 #    "본다"는 말은 관찰인지 매수인지 갈리지 않아 아무 지침도 못 준다.
                 + field("언제 사나", me.get("진입조건") or entry, C["up"])
                 # ⚠️ **표가 아니라 쌓아 쓴다.** 문장이 길어 2단 표에서는 줄바꿈이 잦았다.
                 # ⚠️⚠️ **「언제 파나」는 「언제 사나」 바로 아래**에 둔다(2026-08-31 신설).
                 #    사는 이야기와 파는 이야기가 붙어 있어야 한 벌로 읽힌다.
                 #    브리핑이 그동안 "언제 사나"만 말하고 있었다 — 실측에서
                 #    **버티는 방식이 성과의 절반**을 결정했는데(손절 없이 +10.21%,
                 #    −7% 손절이면 +4.59%) 규칙이 하나도 없었다.
                 + field("언제 파나", me.get("언제파나"), C["down"])
                 + field("⭐ 신호", me.get("신호"))
                 # ⚠️ 아래 넷은 **세로형에만** 싣는 상세다(2026-08-27 합의: 지메일 수준).
                 #    `card-copy`의 종목별 항목에서 온다. 없으면 그냥 안 나온다 —
                 #    지어내지 않는다. 채우는 규칙은 스킬 STEP7.5에 있다.
                 + field("갭 분석", me.get("갭분석"))
                 + field("묶음 점수", me.get("묶음점수"))
                 + field("자세히 볼 점", me.get("주의사항"), C["gold"])
                 + field("길게 보면", me.get("장기"), C["blue"])
                 + '</div>')
    checks = bullets(cp.get("장초확인"), "☐", C["faint"])
    # ⚠️ **어제 후보가 어떻게 됐는지**는 `card-copy`에 이미 있었는데 아무도 안 그리고
    #    있었다(2026-08-27 발견). 맞았는지 틀렸는지를 안 보여주면 신뢰할 근거가 없다.
    # ⚠️⚠️ **어제 등급을 같이 보여준다** (2026-08-31 요청). 종목·등락·판정만 있으면
    #    **"무엇이 맞았나"는 알아도 "우리 판정이 맞았나"는 모른다.**
    #    실제 2026-08-28이 그랬다 — 제일 낮은 🟡 지니언스가 +19.02%로 1등이고
    #    🔴 안랩은 +4.57%였다. 등급이 없으면 이 사실이 화면에서 사라진다.
    #    ⚠️ 등급은 `card-copy`에 없다. **그날 로그(JSONL)에서 종목명으로 찾아온다.**
    #       못 찾으면 그냥 비운다 — 지어내지 않는다.
    _등급 = _전일등급(o.get("date"))
    prev = [(f'{_등급.get(x.get("종목"), "")} {x.get("종목")}'.strip(),
             f'{x.get("결과")} · {x.get("판정")}')
            for x in (cp.get("전일픽") or [])]
    return (h2(pg(num, total), "액션플랜", "", C["up"])
            + p(cp.get("결론"))
            + grade_legend()
            # ⚠️ 지메일에는 "🧭 읽는 법"이 있는데 세로에는 없었다(2026-08-28 대조).
            #    갭이 뭔지, 네 묶음 만점이 왜 다른지를 모르면 아래 숫자가 전부 무의미하다.
            #    읽는 사람은 주식 초보이고 지인에게도 공유된다.
            + (tinted("읽는 법 — 처음 보시는 분께", "", cp.get("읽는법") or [], "info")
               if cp.get("읽는법") else "")
            + f'<div style="margin-top:12px">{rows}</div>' + rule(0)
            # ⚠️⚠️ **오늘 뺀 후보** (2026-08-31 신설). 지메일에는 있었고 세로에만 없었다.
            #    "왜 안 골랐나"는 "왜 골랐나"만큼 값이 있다 — 특히 **어제 후보였다가
            #    오늘 빠진 종목**이 그렇다. 안 적으면 읽는 사람은 그 종목이 아직
            #    유효한 줄 안다.
            #    ⚠️ `이미반영`과 겹치지 않게 **종목 단위 갭 판정만** 여기 쓴다
            #       (업종·테마 이야기는 `이미반영`이 담당한다).
            + (tinted("오늘 뺀 후보", "후보에 올렸다가 자격 미달로 뺀 종목입니다",
                      cp.get("뺀후보") or [], "neg")
               if cp.get("뺀후보") else "")
            # 아래 둘은 세로형 전용. `card-copy`에 없으면 안 나온다.
            + (callout("후보끼리 얼마나 겹치나", cp.get("상관관계", ""), C["gold"])
               if cp.get("상관관계") else "")
            # ⚠️ 지메일의 "🇺🇸 미국 직접 기회" — 세로에 없었다(2026-08-28 대조).
            + (callout("미국 직접 기회", cp.get("미국기회", ""), C["blue"])
               if cp.get("미국기회") else "")
            + kv_table(prev, "어제 후보는 어떻게 됐나",
                       "맞았는지 틀렸는지를 남깁니다 — 좋은 것만 보여주지 않습니다")
            + f'<div style="font-family:{SANS};font-size:15px;letter-spacing:{LS_KO};'
              f'color:{C["muted"]};font-weight:700;margin-top:26px">장 시작 후 확인</div>'
            + checks
            + f'<div style="font-family:{SANS};font-size:14px;color:{C["faint"]};'
              f'margin-top:24px;padding-top:14px;border-top:1px solid {C["line"]}">'
              f'투자 참고용이며 매수 권유가 아닙니다.</div>')


# ⚠️ **지메일과 같은 순서·같은 묶음**이다(2026-08-27 합의). 지메일에 내용을 더할 때
# 여기 어디에 넣을지 고민하지 않아도 되도록 구성을 맞춰 두었다.
#   시장 한눈에 → 뉴스 → 근거 데이터 → 시장 국면 → 국장 수급 → 일정 → 증권가 → 액션플랜
# ⚠️ `s05_regime`은 2026-08-28에 **없앴다** — `s02_overview`와 내용이 통째로
#    겹쳤다. 시장 국면은 이제 "시장 한눈에" 맨 위에 온도로 들어간다.
# ⚠️ `s03_news`도 2026-08-28에 없앴다 — 기사가 미장 전반·전날 국장과 겹쳤고,
#    지수 셋은 맨 위 박스로 옮겼다. 세로는 이제 표지 + 6장이다.
SECTIONS = [s01_cover, s02_overview, s04_evidence,
            s06_flows, s07_calendar, s08_opinion, s09_action]


WEB_CSS = """<style>
/* 이 페이지는 밝은 테마 하나로 간다 — 카드뉴스와 **나란히 비교**하려고 만든 것이라
   둘의 바탕색이 다르면 비교가 안 된다. 그래서 배경·글자색을 전부 명시한다. */

/* ⚠️ **세로로만 움직인다.** 아이폰에서 내릴 때 좌우로 딸려 움직인다는 지적을 받았다
   (2026-08-27). 진짜 원인은 지수 3칸 표가 390px 화면에서 446px로 벌어진 것이었고
   그건 `cols()`에서 고쳤다. 아래 세 줄은 **다시 그런 일이 생겨도 페이지가 옆으로는
   안 밀리게** 하는 이중 잠금이다 — 원인을 못 찾았을 때 이것만 넣고 끝내면 안 된다.
     · `overflow-x:clip`  — 옆으로 삐져나간 걸 잘라낸다. `hidden`이 아니라 `clip`인 건
                            `hidden`이 스크롤 컨테이너를 만들어 `position:fixed`
                            진행 막대를 어긋나게 하기 때문이다.
     · `touch-action:pan-y` — 손가락 제스처를 **세로로만** 받는다.
     · `overscroll-behavior-x:none` — 가로 끝에서 튕기거나 뒤로가기가 걸리지 않게. */
/* ⚠️ **iOS Safari의 텍스트 자동 확대를 끈다.** 이게 없으면 아이폰이 CSS보다 글자를
   크게 그려서 상자를 밖으로 밀어낸다 — 그리고 `overflow-x:clip`이 그걸 잘라 버려
   손가락으로도 못 본다. "오른쪽 글자가 잘린다"는 지적이 세 번 반복됐는데
   데스크톱 크롬에서는 한 번도 재현되지 않았다. 원인이 이것이다. */
html{overflow-x:hidden;overscroll-behavior-x:none;
  -webkit-text-size-adjust:100%;text-size-adjust:100%}
body{margin:0;background:#e8e4dc;-webkit-font-smoothing:antialiased;
  overflow-x:clip;touch-action:pan-y}
.wrap{max-width:__W__px;margin:0 auto;background:#e8e4dc;
  padding:44px 40px 72px;box-shadow:0 2px 24px #17181a14}
@media(max-width:760px){.wrap{padding:28px 18px 48px;box-shadow:none}}
/* 읽은 만큼 채워지는 얇은 막대. 세로형은 끝이 안 보여서 얼마나 남았는지 모른다. */
.bar{position:fixed;top:0;left:0;height:3px;width:0;background:#1b3bf0;z-index:9}
img,table{max-width:100%}
table{table-layout:fixed}
/* ⚠️ **좁은 화면에서는 표를 위아래로 접는다** (2026-08-27 요청). 2단으로 두면
   글 칸이 화면의 60%밖에 안 돼 줄바꿈이 너무 잦다. 접으면 이름이 위, 글이 아래로
   가면서 글 폭이 100%가 된다 — 마크다운 문서와 같은 모양이다. */
@media(max-width:560px){
  .kv,.kv tbody,.kv tr,.kv td{display:block;width:auto!important}
  .kv td:first-child{padding:8px 10px 0!important;font-weight:700}
  .kv td:last-child{padding:2px 10px 10px!important}
  .kv tr{margin-bottom:2px}
}
/* 폰에서는 3칸이 안 들어간다. 억지로 밀어 넣지 말고 세로로 쌓는다. */
@media(max-width:560px){
  .cols,.cols tbody,.cols tr{display:block}
  .cols td{display:block;width:auto!important;box-sizing:border-box;margin:0 0 6px}
}
</style>
<script>
window.addEventListener('scroll',function(){
  var d=document.documentElement, h=d.scrollHeight-d.clientHeight;
  document.querySelector('.bar').style.width=(h>0?d.scrollTop/h*100:0)+'%';
},{passive:true});
</script>"""


def _use(mode):
    """섹션 코드가 읽는 글꼴·폭을 모드에 맞게 갈아 끼운다."""
    global SANS, MONO, W
    if mode == "gmail":
        SANS, MONO, W = MAIL_SANS, MAIL_MONO, 600
    else:
        SANS, MONO, W = WEB_SANS, WEB_MONO, 720


def render(o, cp, mode="web"):
    """하루치 세로형 **본문만** 돌려준다(껍데기 없음).

    `build_site.py`가 날짜별로 이걸 불러 한 페이지에 모은다. 껍데기까지 주면
    페이지 안에 `<title>`과 `<style>`이 여러 벌 들어간다.
    """
    _use(mode)
    # ⚠️ **표지는 번호를 세지 않는다** (2026-08-28 지시: "시장 한눈에부터 1페이지").
    #    표지는 읽는 내용이 아니라 문패다. 01/07이 "시장 한눈에"가 되어야
    #    "몇 번째 장을 보고 있나"가 지메일 섹션 번호와 맞는다.
    n = len(SECTIONS) - 1
    body = "".join(f(o, cp, max(i, 1), n) for i, f in enumerate(SECTIONS, 0))
    # ⚠️ **「숫자만 보는 규칙」을 여기서 뺐다** (2026-09-07 사용자 지적).
    #    그건 퀀트 규칙이라 브리핑 본문(시장 이야기)에 섞이면 안 된다.
    #    ⇒ 첫 화면 ②「퀀트 후보」의 **3장**으로 옮겼다
    #       (build_site.quant_view 의 3/3 카드)
    return body if mode == "gmail" else _scale_px(body, WEB_SCALE)


def build(date=None, out=None, mode="web"):
    _use(mode)
    if not os.path.exists(LOG):
        return {"error": f"{LOG} 없음"}
    rows = [json.loads(x) for x in io.open(LOG, encoding="utf-8-sig") if x.strip()]
    rows = [r for r in rows if r.get("date")]
    o = next((r for r in reversed(rows) if r["date"] == date), None) if date else (
        rows[-1] if rows else None)
    if not o:
        return {"error": f"{date} 기록 없음. 있는 날짜: {[r['date'] for r in rows][-5:]}"}
    cp = _copy(o["date"])
    if not cp:
        return {"error": f"data/card-copy/{o['date']}.json 없음 — 서술 없이는 숫자만 남는다"}

    body = render(o, cp, mode)

    if mode == "gmail":
        # 지메일은 바깥 여백을 안 주므로 표로 가운데 정렬한다. `max-width`로 폰에서 접힌다.
        html = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                f'border="0" style="background:{C["card"]}"><tr>'
                f'<td align="center" style="padding:24px 16px">'
                f'<table role="presentation" width="{W}" cellpadding="0" cellspacing="0" '
                f'border="0" style="width:100%;max-width:{W}px;text-align:left">'
                f'<tr><td>{body}</td></tr></table></td></tr></table>')
    else:
        html = (f'<title>{BRAND} · 세로형</title>'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                + FONTS + WEB_CSS.replace("__W__", str(W))
                + '<div class="bar"></div>'
                + f'<div class="wrap">{body}</div>')
    if out:
        io.open(out, "w", encoding="utf-8").write(html)
    return {"ok": True, "date": o["date"], "모드": mode, "폭": W,
            "크기자": len(html), "파일": out, "섹션": len(SECTIONS)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--out")
    ap.add_argument("--mode", choices=["web", "gmail"], default="web",
                    help="web=Artifact 웹페이지(기본) / gmail=메일 htmlBody 조각")
    a = ap.parse_args()
    print(json.dumps(build(a.date, a.out, a.mode), ensure_ascii=False))


















































