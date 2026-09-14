#!/usr/bin/env python3
r"""
build_site.py — 브리핑 전체를 **웹사이트 한 장**으로 묶는다 (Artifact 고정 링크용)

    표지  ─▶ [오늘 브리핑 보기] ─▶ 그날 브리핑 (카드형 ⇄ 세로형 전환)
          └▶ [지난 브리핑 보기] ─▶ 달력 ─▶ 날짜 선택 ─▶ 그날 브리핑

⚠️ **서버가 없다.** 모든 날짜를 이 파일 안에 미리 넣어 두고 화면 전환만 JS로 한다.
   그래서 "과거 날짜 누르면 불러온다"가 아니라 **이미 다 들어 있는 걸 보여준다**.
   Artifact는 정적 페이지라 이게 유일한 방법이고, 대신 링크가 고정된다.

⚠️ **용량이 조용히 늘어난다.** 하루치가 카드형 ~40KB + 세로형 ~32KB다. Artifact 상한이
   16MB라 산술적으로는 200일 넘게 들어가지만, 첫 로딩이 무거워진다. `--days`로
   최근 N일만 담는다(기본 60). 그보다 오래된 날은 달력에 회색으로 남고 눌러도 안 열린다 —
   **없는 척하지 않는다.** 조용히 빠지면 "왜 안 열리지"가 되고, 회색이면 이유가 보인다.

⚠️ 내용은 `build_cards`·`build_scroll`이 만든다. 여기서 다시 그리지 않는다 —
   세 벌이 되면 어느 하나만 고치고 나머지가 뒤처진다.
"""
import argparse
import calendar
import io
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⭐⭐⭐ **규칙 숫자는 `rule_def.py` 한 곳에서** (2026-09-11).
#    화면 문구도 **값에서 만들어** 쓴다 — 손으로 적으면 낡는다
import rule_def as R  # noqa: E402
import build_scroll  # noqa: E402
from build_cards import (  # noqa: E402
    예산맞추기,  # ⚠️ 안 부르면 웹에 **줄이기 전 카드**가 나간다 (2026-09-11)
    LOG, PAGE_CSS, PAGE_JS, WEEKDAY, _copy, _f, cards_for,
)
from card_theme import BRAND, C, CARD_H, CARD_W, FONTS, LS_KO, MONO, SANS  # noqa: E402

DEFAULT_DAYS = 60

# 이 사이트가 올라가는 **고정 주소.** 아이폰 홈 화면에 올려 둔 링크가 이것이다.
# ⚠️ `archive-url.txt`(옛 아카이브)와 다른 파일이다. 헷갈리면 엉뚱한 곳에 덮어쓴다.
SITE_URL_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "site-url.txt")
_DATA = os.path.dirname(SITE_URL_FILE)


def _갱신시각(경로들):
    r"""그 자료가 마지막으로 바뀐 시각 -> 「09/09(수) 15:47 갱신」"""
    import datetime as _dt2
    최신 = None
    for p in (경로들 if isinstance(경로들, (list, tuple)) else [경로들]):
        if p and os.path.exists(p):
            m = os.path.getmtime(p)
            if 최신 is None or m > 최신:
                최신 = m
    if not 최신:
        return None
    d = _dt2.datetime.fromtimestamp(최신)
    return f"{d.month:02d}/{d.day:02d}({WEEKDAY[d.weekday()]}) {d:%H:%M} 갱신"
SITE_CSS = """<style>
/* ⚠️ 화면이 셋(표지·달력·브리핑)인데 **페이지는 하나**다. `hidden` 속성으로 갈아 끼운다. */
/* ⚠️ **iOS Safari 텍스트 자동 확대를 끈다** · 아이폰에서만 글자가 커져 상자를 밀어내고,
   `overflow-x:clip`이 그걸 잘라 버린다. 데스크톱에서는 재현되지 않는 원인이다. */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{font-family:__MONO__}
/* ⚠️⚠️ **좌우 고정은 어떤 환경에서도. 넘치면 자르지 말고 행을 바꾼다.**(2026-08-27 재지시)
   `build_cards.PAGE_CSS`가 뿌리(html·body)를 잠그고, 여기서는 그 안쪽을 잠근다.
   `overflow-wrap`은 새 이름이라 모르는 엔진이 있어 `word-wrap`을 **먼저** 쓴다. */
.view,.pad,.top,.top .in,.nav{max-width:100%;box-sizing:border-box}
/* ⚠️ `:not(.rail *)` 같은 복합 :not() 은 쓰지 않는다 · 모르는 엔진이 **규칙을 통째로
   버려서** 잠금이 사라진다. 방금 그 실수를 한 번 했다. 레일은 애초에 건드리지 않는다. */
.top,.top *,.pad,.pad *,.scrollwrap *{word-wrap:break-word;overflow-wrap:break-word}
[hidden]{display:none!important}
.view{min-height:100vh;display:flex;flex-direction:column}
/* ⭐⭐ **퀀트 화면만 어둡다** (2026-09-14 디자인 지시).
   가로 요약 8장은 크림색 그대로다 — `#qt` 안에서만 덮는다.
   ⚠️ 전에는 종목 블록만 어둡고 카드가 크림색이라 **종목명이 안 보였다** */
#qt{background:#12100d;color:#d3ccbe}
#qt .top{background:#12100d;border-bottom:1px solid #3a342b}
#qt .tbtn{background:#24201a;border-color:#3f382d;color:#d3ccbe}
#qt .tbtn:hover{border-color:#d4ab45;color:#f2efe8}
#qt .top .now{color:#f2efe8}
#qt .rail::-webkit-scrollbar-thumb{background:#3f382d}
.pad{max-width:760px;margin:0 auto;padding:0 20px;width:100%;box-sizing:border-box}

/* ── 표지 ── */
/* ⚠️⚠️ **왼쪽 정렬이다** (2026-09-11 · 시안).
   전에는 `align-items:center;text-align:center` 로 전부 가운데였는데,
   시안은 제목·지수·메뉴가 모두 **왼쪽에 줄맞춰** 있다.
   가운데로 두면 지수 3칸의 글이 칸마다 다른 자리에서 시작해 읽기 나쁘다 */
/* ⚠️⚠️ **`box-sizing:border-box` 가 없으면 오른쪽이 잘린다** (2026-09-11).
   `max-width:430px` 에 좌우 패딩 22px 이 **더해져** 474px 이 되고,
   390px 폰에서 지수 값(「7,033.92」)과 갱신시각이 화면 밖으로 나갔다 */
#home{justify-content:flex-start;align-items:flex-start;text-align:left;gap:0;
  padding:24px 22px 22px;max-width:430px;margin:0 auto;width:100%;
  box-sizing:border-box}
/* ⚠️ 페이지 바탕(#e8e4dc)은 카드 바탕(#f2efe8)보다 어두워서 **같은 글자색이라도 대비가 낮다**.
   그래서 페이지 UI의 흐린 글씨는 `card_theme.C["faint"]`(#6b665c, 대비 4.50)를 쓴다 ·
   카드용 `muted`(#6f6a60)를 여기 쓰면 4.24로 기준 미달이다(2026-08-31 실측). */
/* ⭐⭐ 아래는 **시안 그대로**다 (2026-09-11).
   정본: design-share/reference/confirmed-design-source.dc.html
   명세: 「이 문서와 그림이 어긋나면 **그림이 이긴다**」
   ⚠️ 폰은 **날짜**(2026.09.11 FRI), 데스크톱은 **MORNING BRIEFING**.
      둘 다 넣고 화면 폭으로 바꿔 보인다 */
#home .eyebrow{font-size:12.5px;font-weight:700;letter-spacing:.24em;color:#6b665c}
#home .eyebrow .pc{display:none}
/* ⚠️ 폰에서는 **2줄**로 앉는다 (「깜댕의 / 주식 브리핑」) */
#home h1{font-size:34px;font-weight:800;letter-spacing:-.045em;
  color:#1c1813;margin:12px 0 0;line-height:1.06}
/* ⚠️ 폰에서는 제목 아래 부제를 **숨긴다** · 시안에 없다. 한 화면에 들어가야
   하는데 이 줄이 지수 블록을 아래로 밀어낸다. 데스크톱에서만 되살린다.
   ⚠️⚠️ **`>` 를 반드시 붙인다.** `#home .sub` 로 쓰면 메뉴 칸의 부제
      (`.big .sub`)까지 숨겨져 「뉴스·공시·수급으로 읽는 시장」이 사라진다 ·
      실제로 그렇게 만들어 놓고 왜 안 보이나 한참 찾았다 (2026-09-11) */
#home > .sub{display:none}
/* ⭐⭐ **밤사이 지수** · 「지수는 줄로, 메뉴는 칸으로」.
   ⚠️ 홈 3칸에는 **세로선을 넣지 않는다**(카드의 kv 와 다르다). 시안은 gap 만 쓴다 */
#home .idxw{width:100%;max-width:none;margin:18px 0 0;padding:0 2px 14px;
  border-bottom:1px solid #d5cec0}
#home .idxh{display:flex;align-items:baseline;justify-content:space-between;
  gap:8px;margin-bottom:10px}
#home .idxh b{font-size:12px;font-weight:700;color:#8a7038}
#home .idxh span{font-size:12px;color:#6b665c;font-weight:400}
#home .idx{display:flex;gap:14px;text-align:left;width:100%}
#home .idx > div{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}
#home .idx .il{font-size:12px;color:#6b665c}
#home .idx .iv{font-size:18px;font-weight:800;letter-spacing:-.03em}
#home .idx .ic{font-size:12.5px;font-weight:700}
/* ⚠️ 시안에는 이 줄이 **없다**. 날짜·후보는 데스크톱 부제 한 줄에 들어가고,
   폰에서는 위쪽 캡션(2026.09.11 FRI)이 그 몫을 한다 */
#home .when{display:none}
#home .btns{display:flex;flex-direction:column;gap:10px;margin-top:14px;width:100%}
/* ⭐ 시안 · 칸 바탕 #f2efe8 · 모서리 14 · 테두리 1px #d5cec0 · 패딩 17/18 */
.big{display:block;width:100%;box-sizing:border-box;padding:17px 18px;border-radius:14px;
  font-family:inherit;letter-spacing:-.01em;cursor:pointer;
  border:1px solid #d5cec0;background:#f2efe8;color:#1c1813;transition:.15s;text-align:left;
  /* ⚠️⚠️ **세로 2줄**이다 (시안). 전에는 `align-items:center` 한 줄이라
     부제가 옆으로 밀려 **안 보였다**.
     1줄 = 제목 + 갱신시각 + 화살표 · 2줄 = 부제 **전폭**
     ⚠️ 화살표는 `.lab` **바깥**에 있는데 1줄 오른쪽에 놓아야 한다.
        HTML 을 안 건드리려고 `.lab` 을 `display:contents` 로 녹여
        자식(`.t1`·`.sub`)을 직접 격자 칸에 앉힌다 */
  display:grid;grid-template-columns:1fr auto;align-items:baseline;gap:4px 10px;
  /* ⚠️⚠️ **높이 고정을 풀었다** (2026-09-11 · 시안).
     2026-09-09에 `height:78px`로 네 상자를 같게 맞췄는데, 부제를 9px -> 13px 로
     키우면 그 안에 안 들어간다. 시안은 「높이 고정 금지 · 부제가 길어지면 칸이
     늘어난다」다. ⚠️ 되돌리려면 `height:78px` 를 살린다 */
  word-break:keep-all}
.big:hover{border-color:#1b3bf0;color:#1b3bf0}
/* 안쪽은 두 줄: ① 제목 + 갱신일시  ② 부제 */
/* ⚠️ `contents` · 이 상자는 사라지고 자식이 바로 격자 칸에 앉는다 */
.big > .lab{display:contents}
.big .t1{grid-column:1;grid-row:1;min-width:0;
  display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.big .arw2{grid-column:2;grid-row:1}
.big .sub{grid-column:1/-1;grid-row:2}
.big .t1 b{font-weight:700;font-size:17.5px;line-height:1.2;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.big .up,.big .sub{font-style:normal;font-weight:400;opacity:1}
.big .up{font-size:12px;flex:none;color:#6b665c;white-space:nowrap;line-height:1.3}
/* ⭐⭐ 부제 **9px -> 13px** (시안). 9px 은 폰에서 읽히지 않는다.
   ⚠️ `white-space:nowrap` 을 뺀다 · 13px 이면 한 줄에 안 들어가고,
      nowrap 이면 말줄임으로 잘려 **뜻이 사라진다** */
.big .sub{font-size:13px;display:block;margin-top:4px;color:#6f6a60;
  word-break:keep-all;line-height:1.5}
/* ⭐ 시안 · 화살표는 **파랑**이고 흐리지 않다 */
.big .arw2{font-size:16px;color:#1b3bf0;flex:none;opacity:1}
#home .note{font-size:12.5px;color:#6b665c;margin-top:10px;line-height:1.7}
#home .note .pconly{display:none}

/* ⭐⭐ **데스크톱도 폰과 같은 크기다** (2026-09-11 지시서 5절).
   「본문 열 `max-width:430px` 가운데 정렬, 좌우는 여백.
    **글자·칸을 키우지 않는다.**」
   ⚠️ 전에 데스크톱만 760px 로 넓히고 글자를 키웠는데 지시서와 어긋난다.
      한 벌로 두면 폰에서 본 것과 PC 에서 본 것이 **같은 화면**이 된다 */
@media(min-width:560px){
  #home{padding:48px 20px 56px}
  /* 데스크톱 캡션만 로마자로 바꾼다 (정본 소스) */
  #home .eyebrow .mo{display:none}
  #home .eyebrow .pc{display:inline}
}

/* ── 위쪽 막대 (달력·브리핑 공통) ── */
.top{position:sticky;top:0;z-index:6;background:#e8e4dcf2;backdrop-filter:blur(8px);
  border-bottom:1px solid #d5cec0}
/* ⚠️ `flex-wrap:wrap` · 좁은 화면에서 단추가 다 안 들어가면 **다음 줄로 내린다.**
   예전처럼 한 줄에 우겨넣으면 막대가 화면보다 넓어져 페이지 전체가 좌우로 밀린다. */
.top .in{display:flex;align-items:center;gap:10px;padding:11px 16px;
  max-width:1100px;margin:0 auto;flex-wrap:wrap;box-sizing:border-box;width:100%}
.tbtn{border:1px solid #d5cec0;background:#e8e4dc;color:#1c1813;border-radius:8px;
  padding:8px 13px;font-family:inherit;font-size:14px;cursor:pointer;white-space:nowrap;
  transition:.15s}
.tbtn:hover{border-color:#1b3bf0;color:#1b3bf0}
.tbtn[disabled]{opacity:.3;cursor:default}
/* ⚠️ `min-width:0`이 없으면 flex 안에서 **줄어들지 못한다.** 좁은 화면에서 이 날짜
   글자가 버티는 바람에 상단 막대가 320px 화면에서 334px로 벌어졌다(2026-08-27 실측). */
.top .now{font-family:__MONO__;font-size:15px;font-weight:700;color:#1c1813;
  margin-left:4px;white-space:nowrap;min-width:0;overflow:hidden;text-overflow:ellipsis}
/* 아이폰 SE(320px)까지 들어가게 조인다.
   ⚠️ 예전엔 좁은 화면에서 전환 버튼의 "세로 · "를 숨겨 "상세/요약"만 남겼다. 그건
      **틀린 처방**이었다(2026-08-27 지적). 사용자는 "가로 요약 / 세로 상세"를 그대로
      보고 싶어 한다. 숨기는 대신 **넘치면 행을 바꾼다** · 그게 지시받은 규칙이다. */
@media(max-width:430px){
  .top .in{gap:6px;padding:9px 10px}
  .tbtn{padding:7px 9px;font-size:13px}
  .top .now{font-size:13px}
  .seg button{padding:7px 9px;font-size:12px}
}
/* 표지 목차 · 넓은 화면은 온전한 이름, 좁은 화면은 줄인 이름. 둘 다 **한 줄**이다. */
/* 목차는 온전한 이름을 쓰고, 안 들어가면 접힌다(2026-08-28 되돌림). */

/* 당겨서 새로고침 표시 · 당기는 만큼 진해지고, 놓으면 돌다가 사라진다.
   ⚠️ 눈에 보이는 응답이 없으면 사용자는 "된 건가?" 하고 계속 당긴다(2026-08-28 요청). */
.ptr{position:fixed;top:0;left:0;right:0;display:flex;justify-content:center;
  padding:16px 0;z-index:9;opacity:0;pointer-events:none;transition:opacity .12s}
.ptr i{display:block;width:26px;height:26px;border-radius:50%;
  border:2px solid #d5cec0;border-top-color:#1c1813}
.ptr.on{opacity:1}
.ptr.on i{animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.ptr.on i{animation:none}}

/* 글씨 크기 조절 · 전환 단추와 같은 모양으로 붙여 둔다. */
.fs{display:flex;border:1px solid #d5cec0;border-radius:8px;overflow:hidden;flex:none;
  margin-left:auto}
.fs button{border:0;background:#e8e4dc;color:#6b665c;font-family:inherit;font-size:13px;
  font-weight:700;padding:8px 12px;cursor:pointer;transition:.15s;white-space:nowrap}
.fs button:hover{color:#1b3bf0}
.fs+.seg{margin-left:6px}
@media(max-width:430px){.fs button{padding:7px 9px;font-size:12px}}

/* 형식 전환. 누른 쪽이 눌린 티가 나야 한다. */
.seg{display:flex;border:1px solid #d5cec0;border-radius:8px;overflow:hidden;
  flex:none}
.seg button{border:0;background:#e8e4dc;color:#6b665c;font-family:inherit;font-size:13px;
  padding:8px 13px;cursor:pointer;transition:.15s;white-space:nowrap}
.seg button[aria-pressed="true"]{background:#17181a;color:#e8e4dc;font-weight:700}

/* ── 달력 ── */
.cal{max-width:520px;margin:26px auto 60px;padding:0 16px}
.cal .mon{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.cal .mon b{font-size:19px;font-weight:800;letter-spacing:-.02em;color:#1c1813}
.grid{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}
.grid .dow{text-align:center;font-size:12px;color:#9c968c;padding:6px 0}
.grid .dow.sun{color:#b8443b}
.cell{aspect-ratio:1;border:1px solid transparent;border-radius:9px;background:transparent;
  font-family:inherit;color:#b8b1a3;font-size:14px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:3px;padding:0}
.cell.has{background:#e8e4dc;border-color:#d5cec0;color:#1c1813;cursor:pointer;font-weight:700}
.cell.has:hover{border-color:#1b3bf0;color:#1b3bf0}
.cell.old{background:#efece5;border-color:#d5cec0;color:#b3aca0;cursor:not-allowed}
.cell.today{border-color:#1b3bf0;border-width:2px}
.cell .dot{width:5px;height:5px;border-radius:50%;background:#1b3bf0}
.cell.old .dot{background:#b8b1a3}
.cal .legend{margin-top:18px;font-size:12px;color:#9c968c;line-height:1.7}
.cal .legend i{display:inline-block;width:9px;height:9px;border-radius:3px;
  background:#efece5;border:1px solid #d5cec0;margin-right:5px;vertical-align:-1px}

/* ── 세로형 본문 ── */
/* ⚠️⚠️ **세로형일 때는 페이지 전체가 세로로만 움직여야 한다** (2026-08-27 재지적).
   예전엔 `touch-action:pan-y`를 `.scrollwrap`에만 걸었는데, 그러면 그 상자 **바깥**을
   짚고 밀 때는 여전히 좌우로 딸려 간다. 그래서 `body.lock-x`로 페이지에 건다 ·
   `SITE_JS`의 `paintFmt()`가 세로형일 때만 이 클래스를 붙인다.
   ⚠️ 카드형에는 절대 붙이면 안 된다. 가로 스와이프가 통째로 죽는다. */
body.lock-x{touch-action:pan-y}
/* ⚠️⚠️ **`width:100%`가 반드시 있어야 한다. 지우지 마라.** (2026-08-28 실측으로 확정)
   이 상자는 `.view{display:flex;flex-direction:column}`의 자식이고 `margin:0 auto`가 붙어 있다.
   flex 자식에 **좌우 auto 여백**이 있으면 부모 폭으로 늘어나지 않고 "내용에 맞춘 폭"이 된다.
   그 폭은 줄바꿈이 안 되는 요소(`white-space:nowrap` 등)의 **최소 폭**을 밑돌 수 없어서,
   아이폰에서 화면이 393px인데 상자가 **482px**로 잡혔다. 글은 446px에서 줄바꿈하고
   화면 밖 89px이 잘려 나갔다 · 사용자가 "오른쪽 글자가 잘린다"고 다섯 번 말한 그것이다.
   ⚠️ 데스크톱 크롬에서는 320~430px 어디서도 재현되지 않았다. 그 최소 폭은 **글꼴에 따라
      달라지는데**, 헤드리스 크롬에서는 393px보다 작게 나왔기 때문이다. 측정을 믿고
      "괜찮다"고 세 번 보고했다가 세 번 틀렸다. 폭은 재는 게 아니라 **박아 두는 것**이다. */
.scrollwrap{width:100%;min-width:0;max-width:760px;margin:0 auto;background:#f2efe8;
  padding:34px 40px 72px;box-shadow:0 2px 24px #17181a14}
/* ⚠️ 긴 낱말·숫자가 상자를 밀어내지 못하게 막는다. `overflow-x:clip`은 넘친 걸
   **잘라 버려서** 손가락으로도 못 보게 만든다 · 자르기 전에 안 넘치게 하는 게 먼저다. */
/* ⚠️ `overflow-wrap:anywhere`는 새 값이라 카톡 인앱 브라우저 같은 오래된 엔진이
   **통째로 무시한다.** 그러면 긴 글자가 안 접혀 상자를 밀어낸다. 예전 값을 같이 쓴다.
   ⚠️ `overflow-x:hidden`은 마지막 방어다 · 넘칠 것을 없애는 게 먼저고, 이건 그래도
   새는 경우를 위한 잠금이다. 이것만 믿고 원인을 안 찾으면 글자가 조용히 잘린다. */
/* ⚠️⚠️ **`box-sizing:border-box`가 없으면 안쪽 여백(좌우 36px)이 폭에 더해진다.**
   2026-08-28, 아이폰에서 줄 끝이 서너 글자씩 잘렸다 · 잘린 양이 딱 그 여백만큼이었다.
   데스크톱 크롭은 이 상자를 전체 폭으로 잡아 재현되지 않았다. 상자 계산은 **박아 둔다.** */
.scrollwrap,.scrollwrap *{box-sizing:border-box}
.scrollwrap{overflow-x:hidden}
.scrollwrap *{max-width:100%;word-wrap:break-word;overflow-wrap:break-word}
.scrollwrap td,.scrollwrap th{word-break:keep-all}
@media(max-width:800px){.scrollwrap{padding:24px 18px 48px;box-shadow:none}}
.scrollwrap table{table-layout:fixed}
/* ⚠️ **좁은 화면에서는 표를 위아래로 접는다** (2026-08-27 요청). 2단으로 두면
   글 칸이 화면의 60%밖에 안 돼 줄바꿈이 너무 잦다. 접으면 이름이 위, 글이 아래로
   가면서 글 폭이 100%가 된다 · 마크다운 문서와 같은 모양이다. */
@media(max-width:560px){
  .kv,.kv tbody,.kv tr,.kv td{display:block;width:auto!important}
  .kv td:first-child{padding:8px 10px 0!important;font-weight:700}
  .kv td:last-child{padding:2px 10px 10px!important}
  .kv tr{margin-bottom:2px}
  /* ⚠️ 3칸 표(날짜·D-day·내용)는 앞 두 칸을 **한 줄에** 둔다. 셋을 다 쌓으면
     한 행이 세 줄이 되어 표가 세로로 길어지기만 한다(2026-08-28 실측). */
  .kv3 td:nth-child(1),.kv3 td:nth-child(2){display:inline-block;width:auto!important;
    padding:8px 10px 0 10px!important}
  .kv3 td:nth-child(2){padding-left:0!important}
  .kv3 td:nth-child(3){display:block;width:auto!important;padding:2px 10px 10px!important}
}
/* ⚠️ `.g3`(업종 격자)는 **접지 않는다.** 좁은 화면에서도 3칸을 유지한다 ·
   접으면 11개가 한 줄씩 쌓여 화면이 세로로만 길어진다(2026-08-28 지적).
   대신 글자를 한 단계 줄이고 낱말을 접어 칸 안에 들어가게 한다. */
@media(max-width:430px){
  .g3 td{padding:9px 6px!important}
  .g3 td div:first-child{font-size:12px!important}
  .g3 td div:last-child{font-size:16px!important}
}
@media(max-width:560px){
  .cols,.cols tbody,.cols tr{display:block}
  .cols td{display:block;width:auto!important;box-sizing:border-box;margin:0 0 6px}
}
/* ⚠️⚠️ `colsx` = **절대 안 접히는 가로 칸**(2026-08-31 신설).
   지수 셋(S&P500·나스닥100·나스닥선물)과 수급 셋(외국인·기관·개인)은
   **나란히 놓여야 비교가 된다.** 세로로 쌓이면 그냥 목록이지 비교가 아니다.
   실제로 아이폰에서 세 개가 한 줄씩 쌓여 지적받았다.
   ⚠️ 대신 좁아지면 **글자를 줄여** 칸 안에 넣는다 · `.g3`와 같은 처리다.
      접는 대신 줄이는 쪽이 맞다. 넘쳐서 가로 스크롤이 생기는 것만 막으면 된다. */
@media(max-width:560px){
  .colsx td{padding:10px 6px!important}
  .colsx td div:first-child{font-size:13px!important}
  .colsx td div:last-child{font-size:17px!important}
}
@media(max-width:400px){
  .colsx td{padding:8px 4px!important}
  .colsx td div:first-child{font-size:12px!important}
  .colsx td div:last-child{font-size:15px!important}
}
</style>"""

SITE_JS = """<script>
(function(){
 // ⚠️⚠️ **새 화면을 만들면 여기에 반드시 넣는다** (2026-09-04에 이걸 빠뜨렸다).
 //    show()는 이 목록만 훑어 hidden을 켜고 끈다. 목록에 없으면 단추를 눌러도
 //    **다른 화면만 사라지고 새 화면은 안 나타난다** · 빈 화면이 된다
 var VIEWS=['home','cal','day','pf','qt'];
 function $(s){return document.querySelector(s)}
 function show(v){
   VIEWS.forEach(function(k){var e=$('#'+k); if(e) e.hidden=(k!==v)});
   // 화살표는 브리핑 화면에서만. 표지·달력에 떠 있으면 누를 게 없다.
   document.querySelectorAll('.arw').forEach(function(a){a.hidden=(v!=='day')});
   if(v==='qt'&&window.__cards&&window.__cards.fit){try{window.__cards.fit()}catch(e){}}
   window.scrollTo(0,0);
 }
 // 기본은 **세로형**이다(2026-08-27 사용자 선택). 처음 여는 사람은 위에서 아래로
 // 읽는 쪽이 익숙하고, 카드형은 넘겨야 한다는 걸 먼저 알아야 쓸 수 있다.
 var fmt='scroll';
 function paintFmt(){
   document.querySelectorAll('.seg button').forEach(function(b){
     b.setAttribute('aria-pressed',String(b.dataset.f===fmt))});
   document.querySelectorAll('.rail:not(.qrail)').forEach(function(r){r.hidden=(fmt!=='card')});
   document.querySelectorAll('.scrollwrap').forEach(function(s){s.hidden=(fmt!=='scroll')});
   $('.nav').hidden=(fmt!=='card');
   document.querySelectorAll('.arw').forEach(function(a){
     a.style.display=(fmt==='card')?'':'none'});
   // ⚠️ 세로형일 때만 페이지를 세로로 잠근다. 카드형에 걸면 가로 넘기기가 죽는다.
   document.body.classList.toggle('lock-x', fmt==='scroll');
   var fsb=document.querySelector('.fs'); if(fsb) fsb.style.display=(fmt==='scroll')?'flex':'none';
   try{localStorage.setItem('brief-fmt',fmt)}catch(e){}
 }
 var cur=null;
 function openDay(d){
   cur=d;
   $('.now').textContent=d.replace(/-/g,'.')+' ('+WD[new Date(d+'T00:00:00').getDay()]+')';
   document.querySelectorAll('.scrollwrap').forEach(function(s){s.dataset.on=String(s.dataset.d===d)});
   document.querySelectorAll('.scrollwrap').forEach(function(s){
     s.style.display=(s.dataset.d===d)?'':'none'});
   show('day');
   // ⚠️ 순서가 중요하다. 레일이 숨어 있는 동안은 폭이 0이라 배율이 엉뚱하게 잡힌다.
   //    **보이게 만든 다음** show→fit 순으로 부른다.
   if(window.__cards){window.__cards.show(d);window.__cards.fit();window.__cards.paint();}
   paintFmt();
 }
 var WD=['일','월','화','수','목','금','토'];
 window.__site={openDay:openDay,show:show};

 $('#btn-today').addEventListener('click',function(){openDay(this.dataset.d)});
 $('#btn-past').addEventListener('click',function(){show('cal')});
 var _pf=$('#btn-pf'); if(_pf) _pf.addEventListener('click',function(){show('pf')});
 var _qt=$('#btn-qt'); if(_qt) _qt.addEventListener('click',function(){show('qt')});
 document.querySelectorAll('[data-home]').forEach(function(b){
   b.addEventListener('click',function(){show('home')})});
 document.querySelectorAll('[data-back]').forEach(function(b){
   b.addEventListener('click',function(){show('cal')})});
 document.querySelectorAll('.seg button').forEach(function(b){
   b.addEventListener('click',function(){
     fmt=b.dataset.f; paintFmt();
     if(fmt==='card'&&window.__cards){window.__cards.fit();window.__cards.paint();}
     window.scrollTo(0,0);})});
 document.querySelectorAll('.cell.has').forEach(function(c){
   c.addEventListener('click',function(){openDay(c.dataset.d)})});

 // 달 넘기기. 달 이름은 각 `.month`의 `data-label`에서 읽는다.
 var months=[].slice.call(document.querySelectorAll('.month'));
 var mi=months.length-1;
 function paintMonth(){
   months.forEach(function(m,i){m.hidden=(i!==mi)});
   if(months[mi]) $('#m-label').textContent=months[mi].dataset.label;
   $('#m-prev').disabled=(mi<=0); $('#m-next').disabled=(mi>=months.length-1);
 }
 $('#m-prev').addEventListener('click',function(){if(mi>0){mi--;paintMonth()}});
 $('#m-next').addEventListener('click',function(){if(mi<months.length-1){mi++;paintMonth()}});
 paintMonth();

/* ⚠️⚠️ **항상 최신을 보여준다.** GitHub Pages는 `Cache-Control: max-age=600`을 보내고
    그 헤더는 우리가 못 바꾼다 · 즉 링크로 들어온 사람은 **최대 10분 전 화면**을 본다.
    아이폰 홈 화면에 올려 둔 경우엔 더 오래 남는다. 2026-08-28에 실제로 새 판을 올려도
    폰에서는 계속 옛 판이 나왔다. "링크 들어갈 때마다 최종 반영된 정보"라는 요구가
    이 헤더 하나로 깨진다. 그래서 페이지가 **스스로** 최신 판을 확인한다.
    ⚠️ 무한 새로고침을 막으려고 `?v=`가 붙은 상태에서는 다시 확인하지 않는다. */
 (function(){
   var meta=document.querySelector('meta[name="build"]');
   var mine=meta?meta.content:'';
   if(/[?&]v=/.test(location.search)){
     try{history.replaceState({},'',location.pathname);}catch(e){}
     return;
   }
   if(!mine||!window.fetch) return;
   fetch('index.html?_='+Date.now(),{cache:'no-store'})
     .then(function(r){return r.ok?r.text():null})
     .then(function(t){
       if(!t) return;
       var m=t.match(/name="build" content="([^"]+)"/);
       if(m&&m[1]&&m[1]!==mine) location.replace(location.pathname+'?v='+m[1]);
     })
     .catch(function(){});   /* 인터넷이 없으면 조용히 넘어간다 · 있는 화면이라도 보여준다 */
 })();

 /* ⚠️ 첫 화면에서 **아래로 당기면 새로고침**한다(2026-08-28 요청).
    이 화면은 `min-height:100vh`라 스크롤이 없어서 사파리 기본 당겨서 새로고침이 안 걸린다.
    그래서 손가락 움직임을 직접 본다. `?v=`를 붙여 캐시를 건너뛴다 ·
    그냥 reload()면 GitHub Pages가 물고 있는 10분 캐시를 다시 받아 온다. */
 (function(){
   var y0 = null, home = $('#home'), ptr = $('.ptr'), THRESH = 90;
   function show(p){                       /* p: 0~1 만큼 당겼다 */
     if(!ptr) return;
     ptr.style.opacity = Math.min(1, p);
     ptr.style.transform = 'translateY(' + Math.min(24, p * 24) + 'px)';
   }
   addEventListener('touchstart', function(e){
     y0 = (!home.hidden && scrollY <= 0) ? e.touches[0].clientY : null;
   }, {passive:true});
   addEventListener('touchmove', function(e){
     if(y0 === null || home.hidden) return;
     var dy = e.touches[0].clientY - y0;
     if(dy <= 0) return;
     show(dy / THRESH);
     if(dy > THRESH){
       y0 = null;
       if(ptr) ptr.classList.add('on');    /* 돌기 시작 · 새로고침이 걸렸다는 신호 */
       setTimeout(function(){
         location.replace(location.pathname + '?v=' + Date.now());
       }, 260);
     }
   }, {passive:true});
   addEventListener('touchend', function(){
     y0 = null;
     if(ptr && !ptr.classList.contains('on')) show(0);
   }, {passive:true});
 })();

 /* ⚠️ 세로 본문은 **인라인 px**로 크기가 박혀 있다(지메일과 같은 HTML을 쓰기 때문에
    클래스를 못 쓴다). 그래서 CSS로는 못 키우고, 원래 값을 기억해 두고 곱한다. */
 var FS = [0.85, 1, 1.15, 1.35], fsi = 1;
 try{var v=parseInt(localStorage.getItem('brief-fs'),10);
     if(v>=0&&v<FS.length) fsi=v;}catch(e){}
 function applyFs(){
   document.querySelectorAll('.scrollwrap').forEach(function(w){
     w.querySelectorAll('*').forEach(function(el){
       var base = el.getAttribute('data-fs0');
       if(base===null){
         var cur = el.style.fontSize;
         if(!cur || cur.slice(-2)!=='px') return;      /* 인라인 px 만 손댄다 */
         base = parseFloat(cur); el.setAttribute('data-fs0', base);
       }
       el.style.fontSize = (parseFloat(base)*FS[fsi]).toFixed(1)+'px';
     });
   });
   try{localStorage.setItem('brief-fs', fsi);}catch(e){}
 }
 document.querySelectorAll('.fs button').forEach(function(b){
   b.addEventListener('click', function(){
     fsi = Math.max(0, Math.min(FS.length-1, fsi + (b.dataset.fs==='+'?1:-1)));
     applyFs();
   });
 });
 applyFs();

 try{var f=localStorage.getItem('brief-fmt'); if(f==='card'||f==='scroll') fmt=f;}catch(e){}
 show('home'); paintFmt();

 /* ⚠️ 진단 막대 · 주소 뒤에 `?diag=1`을 붙였을 때만 뜬다.
    2026-08-27: 아이폰에서 글이 오른쪽으로 잘리는데 데스크톱 크롬은 320·393·430px 어디서도
    넘침이 0으로 나왔다. **재현이 안 되는 것을 추측으로 고치다 세 번 틀렸다.** 그래서
    그 기기가 실제로 무엇을 보고 있는지 화면에서 직접 읽는다. 평소에는 아무 영향이 없다. */
 /* ⚠️ `?diag=1`이 없어도 **잘림이 실제로 일어나면 스스로 띄운다.**
    2026-08-28: 아이폰에서 글이 잘리는데 데스크톱 크롬은 320~430px 어디서도 0으로 나왔다.
    사용자에게 진단 주소를 다시 눌러 달라고 하는 대신, 그 기기가 신고하게 한다.
    데스크톱에서는 잘림이 없으니 뜨지 않는다 · 평소 화면은 그대로다. */
 var badly=function(){
   var n=0, W=document.documentElement.clientWidth;
   document.querySelectorAll('#day *').forEach(function(el){
     if(el.closest('.rail')) return;
     var r=el.getBoundingClientRect();
     if(r.width>0&&(r.right>W+1||r.left<-1)) n++;
   });
   return n;
 };
 /* 원인(2026-08-28 `.scrollwrap` 폭)은 잡혔으니 평소에는 뜨지 않는다.
    다시 잘리는 날이 오면 **스스로 나타난다** · 그게 이걸 남겨 두는 이유다. */
 if(/[?&]diag=1/.test(location.search)||badly()>0){
   var box=document.createElement('div');
   box.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:99;background:#17181a;'
     +'color:#e8e4dc;font:11px/1.5 monospace;padding:7px 9px;white-space:pre-wrap';
   var draw=function(){
     var vv=window.visualViewport, sw=document.querySelector('.scrollwrap[data-on="true"]');
     var w=[];
     w.push('innerWidth '+innerWidth+'  clientWidth '+document.documentElement.clientWidth);
     w.push('visual '+(vv?Math.round(vv.width)+' scale '+vv.scale.toFixed(2):'없음')
            +'  dpr '+devicePixelRatio);
     w.push('doc '+document.documentElement.scrollWidth+'  body '+document.body.scrollWidth);
     if(sw){var r=sw.getBoundingClientRect();
       w.push('본문 '+Math.round(r.width)+'  L'+Math.round(r.left)+' R'+Math.round(r.right));}
     var W=document.documentElement.clientWidth, wide=[], n=0;
     document.querySelectorAll('#day *').forEach(function(el){
       if(el.closest('.rail')) return;
       var q=el.getBoundingClientRect();
       if(q.width<1) return;
       if(q.right>W+1||q.left<-1){
         n++;
         if(wide.length<3){
           var cs=getComputedStyle(el);
           wide.push(el.tagName+'.'+(el.className||'').toString().slice(0,10)
             +' w'+Math.round(q.width)+' L'+Math.round(q.left)+' R'+Math.round(q.right)
             +' bs:'+cs.boxSizing.slice(0,7)+' ov:'+cs.overflowX.slice(0,4));
         }
       }});
     var chain=[['body',document.body],['view',document.getElementById('day')],
                ['wrap',document.querySelector('.scrollwrap[data-on=\"true\"]')]];
     chain.forEach(function(c){
       if(!c[1]) return;
       var q=c[1].getBoundingClientRect(), cs=getComputedStyle(c[1]);
       w.push(c[0]+' '+Math.round(q.width)+' (client'+c[1].clientWidth
              +' scroll'+c[1].scrollWidth+') '+cs.boxSizing.slice(0,7)
              +' pad'+cs.paddingLeft+'/'+cs.paddingRight);
     });
     var t=document.querySelector('.scrollwrap[data-on=\"true\"] h2, .scrollwrap[data-on=\"true\"] p');
     if(t){var q=t.getBoundingClientRect();
       w.push('첫 글줄 w'+Math.round(q.width)+' R'+Math.round(q.right));}
     w.push('밖으로 나간 요소 '+n);
     wide.forEach(function(x){w.push('  '+x)});
     box.textContent=w.join(String.fromCharCode(10));
   };
   document.body.appendChild(box); draw();
   addEventListener('resize',draw);
   if(window.visualViewport){visualViewport.addEventListener('resize',draw);
                             visualViewport.addEventListener('scroll',draw);}
   setInterval(draw,1000);
 }
})();
</script>"""


PF_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "portfolio.json")


def _portfolio():
    r"""보유 현황. **없으면 `None`** — 그러면 단추도 화면도 안 만든다.

    ⚠️ 이 파일에 계좌번호·주문내역을 넣지 않는다. 공개 사이트의 재료다.
    """
    if not os.path.exists(PF_FILE):
        return None
    try:
        with io.open(PF_FILE, encoding="utf-8-sig") as fp:
            d = json.load(fp)
        return d if (d.get("holdings") or []) else None
    except Exception:  # noqa: BLE001
        return None


QT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "data", "forward-log.jsonl")


INDUSTRY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "industry.json")
_업종캐시 = {}


# ⚠️⚠️ **2026-09-11 고침 — 나눠팔기를 안 따르고 있었다.**
#    2026-09-07 에 매도가 **반 +15%(D+40) · 반 +40%(D+90)** 로 바뀌었는데
#    여기는 `40 - 지난` 하나만 세고 있었다. 그래서 화면이
#    **「D+40 에 전량 정리하라」**고 말했다 — 실제로는 **반만** 정리이고
#    나머지 반의 **D+90 은 아무도 안 알려주고 있었다.**
#    +40% 까지 기다리는 뒤 몫이 이 전략의 수익을 떠받친다
_몫들 = R.몫들        # ⭐ rule_def 하나에서


def _보유(q):
    r"""아직 안 판 것 + **앞 몫(D+40)·뒤 몫(D+90)** 까지 며칠 남았나"""
    import glob as _g
    _K = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", "krx-daily")
    날 = sorted(os.path.basename(p)[:8] for p in _g.glob(
        os.path.join(_K, "*.json")))
    out = []
    for r in (q or []):
        for x in (r.get("산것") or []):
            if x.get("판날"):
                continue
            산날 = x.get("산날") or r.get("신호기준일")
            앞남 = 뒤남 = 지난 = None
            if 산날 in 날:
                지난 = len(날) - 1 - 날.index(산날)
                앞남 = _몫들[0][2] - 지난      # 앞 몫 D+40
                뒤남 = _몫들[1][2] - 지난      # 뒤 몫 D+90
            out.append({**x, "남은날": 앞남, "앞남은날": 앞남,
                        "뒤남은날": 뒤남, "지난날": 지난})
    return out


def _업종(code):
    """종목의 업종명. ⚠️ KRX 「업종」은 소속부(벤처/중견/우량기업부)라 못 쓴다 —
    실제 업종은 data/industry.json 에 3,988종목 전부 들어 있다 (2026-09-04 발견)"""
    if not _업종캐시:
        try:
            with io.open(INDUSTRY, encoding="utf-8-sig") as fp:
                _업종캐시.update(json.load(fp))
        except Exception:  # noqa: BLE001
            _업종캐시["_"] = {}
    return ((_업종캐시.get(code) or {}).get("업종명") or "").strip()


def _esc(s):
    """HTML 이스케이프. ⚠️ `_f`는 숫자 변환기라 문자열에 쓰면 None이 된다"""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _quant():
    r"""오늘의 퀀트 후보. **없으면 `None`** — 그러면 단추도 화면도 안 만든다.

    ⚠️ 이건 브리핑 본문과 **다른 물건**이다 (2026-09-04 신설).
       브리핑 ①~⑥은 뉴스·수급·공시를 읽고 쓴 **시장 이야기**이고,
       여기는 재무제표와 주가만 보는 **기계 규칙**이다.
       그래서 **나오는 종목이 서로 다른 게 정상**이다 — 그 점을 화면에 적는다.
    """
    if not os.path.exists(QT_FILE):
        return None
    줄 = None
    try:
        with io.open(QT_FILE, encoding="utf-8") as fp:
            for x in fp:
                x = x.strip()
                if x:
                    try:
                        줄 = json.loads(x)
                    except ValueError:
                        continue
    except Exception:  # noqa: BLE001
        return None
    # ⚠️ **후보 0개인 날에도 돌려준다** (2026-09-07 고침).
    #    전에는 후보가 있어야만 단추를 만들었는데, 그러면 「오늘은 살 게
    #    없는 날」과 「시스템이 고장난 날」이 화면에서 **똑같아 보인다.**
    #    규칙상 대부분의 날은 0개다 — 그걸 보여줘야 믿을 수 있다
    return 줄 or None


def _특징(후보):
    r"""종목마다 **넷을 구별해주는 특징 한 마디**를 붙인다.

    ⚠️ 숫자를 그냥 나열하면 결국 표가 된다. 표가 안 읽혀서 서술로 바꾸는 것이니
       각 종목이 **어느 칸에서 제일인지** 한 가지만 고른다.
    ⚠️ 이미 쓴 특징은 다시 안 쓴다. 넷이 다 「가장 많이 빠졌다」면 구별이 안 된다.
    """
    if not 후보:
        return {}
    # ⚠️ 넷째 칸은 **짧은 딱지**다 (2026-09-11). 1장 박스는 높이가 고정이라
    #    긴 문장을 넣을 자리가 없다. 뜻은 같고 길이만 다르다
    잣대 = (
        ("잉여금비율", True, "쌓아둔 이익이 가장 많습니다", "이익 1위"),
        ("부채비율", False, "빚이 가장 적습니다", "빚 최저"),
        ("볼린저", False, "평소 움직이던 폭에서 가장 멀리 벗어났습니다", "볼린저 1위"),
        ("20일낙폭", False, "가장 많이 빠졌습니다", "낙폭 1위"),
    )
    # ⚠️⚠️ **「가장」은 전체에서 1등일 때만 붙인다** (2026-09-04 고침)
    #    처음엔 「남은 종목 중 1등」으로 골랐다. 그러면 **마지막 종목은 사실이든
    #    아니든 남은 딱지가 붙는다** — 넷 중 제일 적게(-10.0%) 빠진 젝시믹스에
    #    「가장 많이 빠졌습니다」가 붙어 나갈 뻔했다. 브리핑에 나가는 거짓말이다
    #    ⇒ 전체 1등을 먼저 정하고, 이미 딱지가 있으면 **그 잣대는 그냥 버린다**.
    #       딱지 없는 종목이 생기는 건 괜찮다 — 틀린 말을 붙이는 것보다 낫다
    쓴곳 = {}
    for 칸, 클수록, 말, 짧 in 잣대:
        있 = [x for x in 후보 if x.get(칸) is not None]
        if not 있:
            continue
        best = (max if 클수록 else min)(있, key=lambda z: z[칸])
        if best["종목코드"] in 쓴곳:
            continue                      # 이미 다른 딱지가 있다 — 이 잣대는 버린다
        쓴곳[best["종목코드"]] = (말, 짧)
    return 쓴곳


# ⭐⭐⭐ **퀀트 전용 색표** (2026-09-14 디자인 지시).
#    퀀트 화면은 **배경 전체가 어둡다.** 종목 블록만 어둡고 카드가 크림색이라
#    **종목명이 안 보였다** (어두운 블록 + 어두운 글자).
#    ⚠️ 가로 요약 8장은 **크림색 그대로다** — 퀀트만 어둡다
QC = {
    "쪽": "#12100d",      # 페이지 배경
    "카드": "#1a1713",    # 카드 바탕
    "블록": "#24201a",    # 종목 블록
    "블록선": "#3f382d",  # 종목 블록 테두리
    "이름": "#f2efe8",    # 큰 글자 · 이름
    "본문": "#d3ccbe",
    "보조": "#a49c8e",    # 보조 · 라벨
    "금": "#d4ab45",      # 금색 강조
    "빨": "#ef7a6c",      # 낙폭 · 경고
    "파": "#7fa6ff",
    "선": "#3a342b",      # 구분선
}


def quant_view(q):
    """퀀트 후보 — 1080x1350 카드 2장 (2026-09-04)

    1장  **종목만** — 오늘 뭘 볼지. 여기에 다 담는다
    2장  **안내·주의사항** — 어떻게 뽑았고 무엇을 조심할지
    ⚠️ 2장에 종목을 또 쓰지 않는다. 같은 걸 두 번 보면 기능이 겹쳐 보인다
       (2026-09-04 사용자 지적)

    ⚠️ 여백은 **기존 브리핑 카드와 같은 기준**: section `padding:80px`,
       안쪽은 `justify-content:space-between`으로 위아래를 채운다.
       그렇게 안 하면 아래쪽이 비어 보인다 (사용자 지적)
    ⚠️ 글자는 **1080 기준**이다 (기존 카드 본문 29px). 화면에서는 scale로 줄어든다
    """
    후보 = q.get("후보") or []
    특 = _특징(후보)
    # ⚠️ **숫자를 화면에 박지 않는다** (2026-09-07).
    #    전에는 「210건·86%」를 코드에 적어 뒀는데, build_rule_cases 를
    #    실전 절차로 고치자 107건이 되어 **화면만 옛 숫자로 남았다**
    # ⚠️ 계좌 낙폭은 **자료에서 읽는다** (2026-09-11). 손으로 적으면 낡는다
    _옛낙, _새낙 = -9.0, -3.3
    try:
        _cp = json.load(io.open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "data", "rule-capital.json"),
            encoding="utf-8-sig"))
        _새낙 = _cp.get("계좌낙폭", _새낙)
        _옛낙 = (_cp.get("옛값_참고") or {}).get("계좌낙폭", _옛낙)
    except Exception:  # noqa: BLE001
        pass

    _사례 = {}
    _p = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data", "rule-cases.json")
    if os.path.exists(_p):
        try:
            _사례 = json.load(io.open(_p, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            _사례 = {}
    기 = str(q.get("신호기준일") or "")
    기표 = f"{기[:4]}.{기[4:6]}.{기[6:]}" if len(기) == 8 else 기
    아침 = ""
    try:
        _d = datetime.strptime(기, "%Y%m%d")
        for _k in range(1, 5):
            _n = _d + timedelta(days=_k)
            if _n.weekday() < 5:
                아침 = f"{_n.month}월 {_n.day}일({WEEKDAY[_n.weekday()]}) 아침"
                break
    except (ValueError, TypeError):
        아침 = ""
    try:
        찍 = str(q.get("기록시각") or "")[:10]
        난 = (datetime.now() - datetime.strptime(찍, "%Y-%m-%d")).days if 찍 else 0
    except (ValueError, TypeError):
        찍, 난 = "", 0
    # ⚠️ 08:50에 예상체결가로 **확정**되었나 (2026-09-07 신설).
    #    확정 전 = 「볼 종목」 / 확정 후 = 「살 것」. 화면이 그때그때 달라야
    #    사용자가 따로 확인할 것이 없다 (기존 브리핑의 09:05 갱신과 같은 방식)
    # 보유 중인 것 — 파일 전체를 다시 읽는다 (q 는 마지막 줄뿐)
    _줄들 = []
    try:
        for _x in io.open(QT_FILE, encoding="utf-8"):
            _x = _x.strip()
            if _x:
                _줄들.append(json.loads(_x))
    except Exception:  # noqa: BLE001
        _줄들 = []
    보유 = _보유(_줄들)
    # ⚠️ 앞 몫(D+40)과 뒤 몫(D+90)은 **정리하는 날이 다르다**
    팔것 = [x for x in 보유
            if x.get("앞남은날") is not None and x["앞남은날"] <= 0
            and (x.get("뒤남은날") or 99) > 0]
    뒤팔것 = [x for x in 보유
              if x.get("뒤남은날") is not None and x["뒤남은날"] <= 0]
    _동 = q.get("동시호가") or {}
    확정 = _동.get("예상시장갭") is not None
    잰때 = str(_동.get("잰시각") or "")[11:16]
    살것 = [x for x in 후보 if x.get("규칙매수")][:4] if 확정 else []
    # ⭐⭐⭐ **제목·목록·상태 칩이 같은 집합을 가리킨다** (2026-09-14 디자인 지시).
    #    전에는 제목이 `살것` 을 세는데 화면은 `후보[:4]` 를 그렸다 —
    #    사는 종목이 앞 4개에 없으면 제목은 「2개」인데 넷 다
    #    「안 샀습니다」가 됐다. 9/14 아침 화면이 그랬다. **돈이 걸린 자리다**
    #      사는 날    -> 실제 매수 종목만
    #      안 사는 날 -> 후보 상위 4개
    보일것 = 살것 if 살것 else 후보[:4]

    # ⚠️⚠️ **글은 언제나 왼쪽 80 · 오른쪽 1000** (2026-09-11 사용자 지시).
    #    「각 페이지 왼쪽에서 시작하는 지점, 오른쪽에서 끝나는 지점 맞춰.
    #     글이든 박스든!」
    #    전에는 박스 안 글이 **테두리 9 + 안여백 24 = 33px 안쪽**에서 시작해
    #    맨 글(80)과 어긋나 보였다. 박스를 **기둥 밖으로 밀어내** 맞춘다:
    #        박스 바깥 47 ~ 1024   ·   박스 안 글 80 ~ 1000
    #    ⚠️ 테두리 색을 안 줘도 **투명 9px 을 반드시 둔다** — 안 그러면
    #       색 있는 박스와 글 시작점이 또 어긋난다
    # ⚠️⚠️ **박스 규격은 하나다** (2026-09-11 사용자 지시).
    #    「상자는 각진 거 말고 **끝을 둥글게**」 · 「박스에서 글 쓸 때
    #     **좌우상하 일정 공간 남겨둬. 페이지에서 좌우 여백 남기듯이!**」
    #        바깥 = 글 기둥(80~1000)과 **같은 선**
    #        안여백 = 사방 30px   ·   모서리 = 20px
    #    ⚠️ 직전 판은 박스를 기둥 **밖으로** 밀어내 박스 안 글을 80 에
    #       맞췄는데, 그러면 박스가 여백을 파먹어 **답답해 보인다.**
    #       이 지시가 더 나중이고 더 분명하다 — 되돌렸다
    _선, _안 = 9, 30

    def 박스(속, 바탕="#1f1b16", 선=None, 글=28, 줄=1.75, 둥글=20):
        return (f'<div style="border-left:{_선}px solid {선 or "transparent"};'
                f'background:{바탕};border-radius:{둥글}px;'
                f'padding:26px {_안}px;'
                f'font-size:{글}px;line-height:{줄}">{속}</div>')

    _제목아래 = 54        # 제목 ↔ 첫 내용. **네 장 모두 같다**

    def 장(위, 가운데, 아래, 딱지="", 틈=20, 채움=True):
        """기존 카드와 같은 틀 — padding:80px + space-between 으로 세로를 채운다

        ⚠️⚠️ **`data-label` 이 반드시 있어야 한다** (2026-09-11 사고).
           `check_layout.py` 는 **`section[data-label]` 만** 재는데 퀀트 3장에는
           그게 없어서 **검사를 한 번도 안 받았다.** 브리핑 8장은 매일 재는 동안
           퀀트 카드는 넘쳐도 조용히 통과했고, 실제로 4번째 종목이 잘려 나갔다
        """
        return (f'<section data-label="{딱지}" '
                f'style="width:{CARD_W}px;height:{CARD_H}px;'
                f'background:{QC["카드"]};border-radius:26px;box-sizing:border-box;'
                f'padding:80px;overflow:hidden;font-family:{SANS};'
                f'color:{QC["이름"]};display:flex;flex-direction:column">'
                f'<div style="display:flex;flex-direction:column;'
                f'justify-content:space-between;width:100%;height:100%;'
                f'box-sizing:border-box">'
                # ⚠️ 제목 바로 밑에 내용이 붙어 답답했다 (2026-09-11 지적).
                #    브리핑 카드와 **같은 40px** 을 둔다 (card_theme.HEAD_GAP).
                #    ⚠️ `margin-bottom` 은 상쇄돼 사라진다 — **padding** 이어야 한다
                #       (card_theme 이 2026-08-31 에 같은 일을 겪었다)
                # ⚠️ 제목 아래 간격은 **모든 장이 같아야 한다** (2026-09-11 지시).
                #    「답답하니까 일정 간격으로」 — 넓히는 게 아니라 **맞추는** 것이다.
                #    브리핑 카드와 같은 값(card_theme.HEAD_GAP = 40)
                f'<div style="flex:none;padding-bottom:{_제목아래}px">{위}</div>'
                # ⚠️⚠️ **space-evenly 를 쓰면 안 된다** (2026-09-07 사용자 신고).
                #    자식 높이 합이 칸보다 크면 flex 가 못 줄이고,
                #    space-evenly 가 **음수 여백**을 만들어 **글이 글 위에 겹친다.**
                #
                # ⚠️ 대신 **space-between 은 안전하다** (2026-09-11).
                #    남는 자리가 **음수**가 되면 규격상 `flex-start` 처럼 동작한다 —
                #    앞뒤로 벌리는 space-evenly/around 와 달리 **겹치지 않는다.**
                #    사용자: 「내용이 비어서 아래가 남으면 **상자 간 간격을 벌리고**
                #    폰트 크기를 키워서 페이지를 적당히 키우는 게 좋아」
                #    gap 은 **최소 간격**으로 남는다
                f'<div style="flex:1;display:flex;flex-direction:column;'
                # ⚠️ `채움=False` 면 남는 자리를 **안 벌린다.** 3장처럼
                #    무리가 둘뿐이면 space-between 이 213px 까지 벌려 버린다
                f'justify-content:'
                f'{"space-between" if 채움 else "flex-start"};'
                f'gap:{틈}px;min-height:0;'
                f'overflow:hidden">{가운데}</div>'
                # ⚠️ space-between 이 가운데 **마지막 칸을 바닥까지** 밀어서
                #    아래 글과 맞닿았다 (2026-09-11 그림으로 확인). 띄운다
                f'<div style="flex:none;padding-top:22px">{아래}</div>'
                f'</div></section>')

    # ══ 1장 · 종목만 ══
    _제목 = (("오늘 살 것: " + str(len(살것)) + "개") if (확정 and 살것)
             else ("오늘 살 것: 없음" if 확정
                   # ⚠️ **2026-09-11 고침** — 「오늘의 40종목」은 오해를 부른다.
                   #    40개가 다 그려져 있는데 화면에는 4개만 보여서
                   #    「40개는 어디서 왔지?」가 된다 (사용자 지적)
                   else ("오늘 볼 종목" if 후보
                         else "오늘의 목록")))
    _딱지뜻 = "".join(
        f'<span style="background:{_bg};color:{_fg};border-radius:5px;'
        f'padding:2px 11px;font-size:22px;font-weight:800;'
        f'margin-right:6px">{_라}</span>'
        for _라, _bg, _fg in (("시장", "#1b2536", "#7fa6ff"),
                              ("낙폭", "#26231d", "#a49c8e"),
                              ("섹터", "#231d2e", "#b89ae8")))
    # ⚠️⚠️ 딱지 설명은 **목록보다 먼저** 나와야 한다 (2026-09-11 지시).
    #    아래에 두면 종목을 다 읽은 **뒤에야** 딱지 뜻을 알게 된다 —
    #    「첫페이지만 보면 무슨 뜻인지 모르겠네」. 위1 로 옮겼다
    위1 = (f'<div style="font-family:{MONO};font-size:26px;color:{QC["금"]};'
           # ⭐ **디자인 답 B-4** — 전환을 **여기서 한 번에** 알린다.
           #    아래 종목 줄은 자리·라벨·크기가 그대로라 조용히 값만 바뀐다
           f'letter-spacing:.18em;font-weight:700">QUANT · '
           + ("08:50 확정" if 확정 else "08:00 후보") + '</div>'
           f'<div style="font-size:62px;font-weight:800;letter-spacing:-.035em;'
           f'margin-top:16px;line-height:1.1">{_제목}</div>'
           + (f'<div style="font-size:31px;color:{QC["금"]};font-weight:700;'
              f'margin-top:12px">{아침}에 볼 목록'
              # ⭐ **목록이 무엇인지 그대로 적는다** (2026-09-14).
              #    「4개」가 박혀 있어 사는 날에는 틀렸다 —
              #    그날 목록은 **실제 매수 종목**이고 개수도 다르다
              + (f'<span style="color:{QC["보조"]};font-weight:400"> · '
                 + (f'{len(후보)}개 중 **규칙이 사라고 한 {len(보일것)}개**'
                    if 살것 else
                    f'{len(후보)}개 중 많이 걸린 순서로 {len(보일것)}개')
                 + '</span>'
                 # ⚠️ 확정 뒤에도 남긴다 — 08:50 이후 이 줄이 사라져
                 #    「무슨 목록인지」가 화면에서 없어졌다 (2026-09-11 지적)
                 if len(후보) > len(보일것) else '')
              + '</div>' if 아침 else '')
           # ⭐ **딱지 뜻을 목록 바로 위에** 놓는다 (2026-09-11 지시)
           + ((f'<div style="margin-top:14px;font-size:25px;'
               f'color:{QC["보조"]};line-height:1.5">{_딱지뜻}'
               f'<span style="margin-left:6px">딱지는 <b>그 종목이 어느 '
               f'규칙으로 걸렸는지</b>입니다. 뜻은 2장에</span></div>')
              if (후보 and not 확정) else '')
           # ⚠️ **2026-09-11** — 「{기표} 종가 기준 · 오른쪽 숫자는 20거래일 낙폭」을
           #    뺐다. 종목마다 아래 줄에 같은 정보가 또 있어 **겹쳤다** (사용자 지적).
           #    ⚠️ 3차: 이 줄을 **위 날짜 줄에 합쳤다** — 머리말이 207px 이나 되어
           #       가운데 칸을 눌렀다 (실측)
           + '')
    if 뒤팔것:
        _이2 = " · ".join((x.get("이름") or x.get("종목코드", ""))
                          for x in 뒤팔것)
        위1 += (f'<div style="margin-top:18px;background:#2a1c1a;'
                f'border-left:9px solid #ef7a6c;border-radius:20px;'
                f'padding:24px 30px;font-size:30px;line-height:1.6">'
                f'🔴 <b>오늘 나머지 반 정리: {_이2}</b><br>'
                f'<span style="font-size:26px">90거래일이 지났습니다. '
                f'+40%에 안 닿았어도 <b>남은 반을 전부</b> 정리합니다.'
                f'</span></div>')
    if 팔것:
        _이 = " · ".join((x.get("이름") or x.get("종목코드", "")) for x in 팔것)
        위1 += (f'<div style="margin-top:18px;background:#2a1c1a;'
                f'border-left:9px solid #ef7a6c;border-radius:20px;'
                f'padding:24px 30px;'
                f'font-size:30px;line-height:1.6">'
                f'🔴 <b>오늘 반만 정리: {_이}</b><br>'
                f'<span style="font-size:26px">40거래일이 지났습니다. '
                f'+15%에 안 닿은 <b>앞의 반</b>만 정리하고, '
                f'<b>나머지 반은 +40%까지 D+90</b>을 기다립니다.</span></div>')
    elif [x for x in 보유 if (x.get("남은날") or 99) <= 3]:
        _곧 = " · ".join(
            (x.get("이름") or x.get("종목코드", "")) + " " + str(x["남은날"]) + "일"
            for x in 보유 if (x.get("남은날") or 99) <= 3)
        위1 += (f'<div style="margin-top:18px;background:#241f14;'
                f'border-left:9px solid #d4ab45;border-radius:20px;'
                f'padding:22px 30px;'
                f'font-size:27px;line-height:1.6">'
                f'🟡 곧 정리: {_곧}</div>')
    elif 보유:
        위1 += (f'<div style="margin-top:18px;font-size:25px;'
                f'color:{QC["보조"]}">들고 있는 것 {len(보유)}개 · '
                f'<b>반은 +15% · 반은 +40%</b> 지정가가 걸려 있어야 합니다</div>')
    if 난 >= 1:
        위1 += (f'<div style="margin-top:18px;background:#2a1c1a;'
                f'border-left:9px solid #ef7a6c;border-radius:20px;'
                f'padding:22px 30px;font-size:27px;'
                f'line-height:1.55">⚠️ <b>오늘 만든 목록이 아닙니다</b> '
                f'({찍} · {난}일 전). 매매하지 마세요.</div>')

    가1 = []
    if not 후보:
        # ⚠️ 규칙상 **대부분의 날은 0개**다 (실제로 사는 날은 **36일에 한 번** — 2026-09-07 실측, 최근 1년은 21일).
        #    빈 화면을 두면 고장인지 없는 날인지 알 수 없다 (2026-09-07 신설)
        # ⭐⭐⭐ **2026-09-11 디자인 답 B-3** — 0 을 크게 보여 준다.
        #    ⚠️ 이 카드만 `space-between` 대신 **고정 간격 60px + 위 정렬**,
        #       본문 31 -> **33px** (채움 70% 미만 규칙 · 정본 §5-5)
        #    ⚠️ 조건 값은 **`rule_def` 에서 읽는다** — 손으로 적으면 규칙이
        #       바뀔 때 화면만 낡는다
        _조건들 = (f"쌓은 이익 {R.잉여금하한:g}% 이상",
                   f"빚 {R.부채상한:g}% 이하",
                   "작년 순이익 흑자",
                   f"시총 {R.시총하한억:,.0f}억~{R.시총상한억:,.0f}억",
                   f"하루 거래 {R.대금하한억:g}억 이상")
        가1.append(
            f'<div style="display:flex;flex-direction:column;'
            f'justify-content:flex-start;gap:60px;height:100%">'
            f'<div><div style="font-size:96px;font-weight:800;'
            f'letter-spacing:-.04em;line-height:1;color:{QC["금"]}">0개</div>'
            f'<div style="font-size:33px;line-height:1.6;margin-top:18px;'
            f'color:{QC["본문"]};word-break:keep-all">'
            f'조건을 통과한 종목이 없습니다. 열흘에 세 번쯤 있습니다. '
            f'고장이 아닙니다.</div></div>'
            f'<div><div style="font-size:25px;font-weight:700;'
            f'color:#d4ab45">먼저 지나야 하는 문</div>'
            f'<div style="font-size:33px;line-height:1.6;margin-top:8px;'
            f'color:{QC["본문"]};word-break:keep-all">'
            + " · ".join(_조건들) + '</div></div>'
            f'<div><div style="font-size:25px;font-weight:700;'
            f'color:#d4ab45">그 다음</div>'
            f'<div style="font-size:33px;line-height:1.6;margin-top:8px;'
            f'color:{QC["본문"]};word-break:keep-all">'
            f'낙폭 · 섹터 · 시장 <b>셋 중 하나</b>에 걸려야 합니다.</div></div>'
            f'</div>')

    # ⚠️⚠️ **2026-09-11** — 카드는 1080x1350 **고정 + overflow:hidden** 이라
    #    40개를 넣으면 **잘린다**. 실제로 화면에서 잘려 나갔다 (사용자 지적).
    #    => **상위 4종목까지만** 쓴다. 하루에 사는 것도 최대 4종목이다
    for n, x in enumerate(보일것):
        업 = _업종(x["종목코드"])
        잉, 부 = x.get("잉여금비율"), x.get("부채비율")
        수 = []
        if 잉 is not None:
            수.append(f'쌓은 이익 <b>{잉:.0f}%</b>')
        if 부 is not None:
            수.append(f'빚 <b>{부:.0f}%</b>')
        _짧 = (특.get(x["종목코드"]) or ("", ""))[1] if not 확정 else ""
        _딱 = "".join(
            f'<span style="background:{_bg};color:{_fg};border-radius:5px;'
            f'padding:2px 12px;font-size:22px;font-weight:800;'
            f'margin-left:9px">{_라}</span>'
            for _라, _bg, _fg, _on in (
                ("시장", "#1b2536", "#7fa6ff", x.get("시장규칙")),
                ("낙폭", "#26231d", "#a49c8e", x.get("기존규칙")),
                ("섹터", "#231d2e", "#b89ae8", x.get("섹터규칙")))
            if _on)
        if _짧:
            _딱 += (f'<span style="background:#2b2519;color:#d4ab45;'
                    f'border-radius:5px;padding:2px 12px;font-size:22px;'
                    f'font-weight:800;margin-left:9px">{_짧}</span>')

        # ⚠️ 라벨 붙은 **네 칸**. 줄줄이 잇던 한 줄을 나눈 것이다 —
        #    무엇이 무슨 숫자인지 눈으로 바로 갈려야 한다 (2026-09-11 지시)
        _칸 = [("전날 종가", f'{x["어제종가"]:,}원'),
               ("시가총액", f'{x["시총억"]:,}억')]
        if 잉 is not None:
            _칸.append(("쌓은 이익", f'{잉:.0f}%'))
        if 부 is not None:
            _칸.append(("빚", f'{부:.0f}%'))

        # ⚠️⚠️ **확정 전/후가 같은 자리를 쓴다** (2026-09-11 지시).
        # ⭐⭐⭐ **디자인 답 B-1·B-2·B-4** (2026-09-11):
        #    ⓐ 라벨은 **세 상태 모두 같다** — 자리·말·색이 안 흔들려야 조용한 전환
        #    ⓑ 색도 세 상태 모두 **금색**. 확정 전 파랑(#7fa6ff)은 버렸다 —
        #       「파랑까지 바뀌면 조용한 전환이 아니다」
        #    ⓒ 상태는 **오른쪽 끝 칩**으로만 가른다. 흐리게 쓰는 건 칩뿐이다
        _갭말 = (f'<span style="display:block;font-size:21px;color:{QC["보조"]};'
                 f'font-family:{MONO}">상대갭 {x["상대갭"]:+.2f}%p</span>'
                 if x.get("상대갭") is not None else '')
        _위라, _위색 = "문턱가 · 이 값 아래여야 산다", "#d4ab45"
        if not 확정:
            _위값 = "~".join(f"{_v:,}" for _v in R.매수범위(x["어제종가"])) + "원"
            # ⚠️⚠️ **이 한 줄을 빼지 마라.** 문턱가는 전날 종가 근처가 아니라
            #    3.5%p 아래다. 안 밝히면 사람이 **비싸게 산다** (디자인 지시)
            _작, _칩 = f"전날 종가보다 {abs(R.상대갭문턱):g}%p 아래", ""
        else:
            # ⭐ B-2 — 「안 산다」에도 **같은 크기로** 띄운다.
            #    「얼마였는데 못 샀나」가 보여야 규칙을 신뢰한다
            _위값 = f'{format(x.get("문턱가") or 0, ",")}원'
            if x.get("규칙매수"):
                _작 = (f'주문가 {format(x.get("주문가") or 0, ",")}원'
                       if x.get("주문가") else "")
                _칩 = ('<span style="display:inline-block;border-radius:6px;'
                       'padding:3px 12px;font-size:21px;font-weight:800;'
                       'background:#2a1c1a;color:#ef7a6c">산다</span>')
            else:
                _작 = "넘겨서 안 샀습니다"
                _칩 = ('<span style="display:inline-block;border-radius:6px;'
                       'padding:3px 12px;font-size:21px;font-weight:800;'
                       f'background:#2b2519;color:{QC["보조"]}">안 산다</span>')
        _위끝 = ((f'<span style="display:block;font-size:21px;'
                  f'color:{QC["보조"]};font-family:{MONO}">{_작}</span>')
                 if _작 else "") + (_갭말 if 확정 else "")
        _오른위 = (f'<span style="margin-left:auto;text-align:right;'
                   f'white-space:nowrap">'
                   # ⭐ B-1 — 상태는 **오른쪽 끝 칩**으로만 가른다
                   + (f'<span style="display:block;margin-bottom:3px">{_칩}</span>'
                      if _칩 else '')
                   + f'<span style="display:block;font-size:21px;color:{_위색};'
                     f'font-weight:700">{_위라}</span>'
                   + (f'<span style="font-size:29px;font-weight:800;'
                      f'color:{_위색};font-family:{MONO};line-height:1.02">'
                      f'{_위값}</span>' if _위값 else '')
                   + _위끝 + '</span>')

        # ⭐⭐⭐ **QUANT-Q1-REFLOW.md (2026-09-14) — 종목 블록 3줄**
        #    전에는 둘째 줄에 다 넣어 **1,018px** 이 920px 칸에서 잘렸다.
        #    글자를 줄인 게 아니라 **줄을 바꿨다.** 실측 블록 176px x 4 = 704
        #    ⚠️ 상대갭은 **1줄**에 둔다 — 3줄에 두면 보조 문구가 눌려 접힌다
        _낙 = (f'<span style="flex:none;margin-left:14px;white-space:nowrap">'
               f'<span style="font-size:24px;color:#a49c8e">20일 낙폭</span> '
               f'<span style="font-size:32px;font-weight:800;color:#ef7a6c;'
               f'font-family:{MONO}">{x["20일낙폭"]:.1f}%</span></span>')
        _상대 = (f'<span style="flex:none;margin-left:auto;font-size:23px;'
                 f'color:#a49c8e;white-space:nowrap;font-family:{MONO}">'
                 f'상대갭 {x["상대갭"]:+.2f}%p</span>'
                 if x.get("상대갭") is not None else
                 '<span style="margin-left:auto"></span>')
        _줄1 = (f'<div style="display:flex;align-items:baseline;'
                f'white-space:nowrap">'
                f'<span style="flex:none;font-size:34px;font-weight:700;'
                # ⭐ **색을 박는다** (2026-09-14) — 물려받으면 어두운 블록에
                #    어두운 글자로 들어가 **안 보인다**
                f'letter-spacing:-.02em;color:#f2efe8">{_esc(x["이름"])}</span>'
                + (f'<span style="flex:none;font-size:26px;font-weight:700;'
                   f'color:#d3ccbe;margin-left:11px">{_esc(업)}</span>'
                   if 업 else '')
                + f'<span style="flex:none;font-family:{MONO};font-size:23px;'
                  f'color:#a49c8e;margin-left:9px">{x["종목코드"]}</span>'
                + _상대 + _낙 + '</div>')
        _줄2 = ('<div style="display:flex;align-items:baseline;gap:18px;'
                'margin-top:10px;white-space:nowrap">'
                + "".join(
                    f'<span style="flex:none">'
                    f'<span style="font-size:23px;color:#a49c8e">{_라}</span> '
                    f'<span style="font-size:26px;font-weight:800;'
                    f'color:#f2efe8;font-family:{MONO}">{_값}</span></span>'
                    for _라, _값 in _칸)
                + (f'<span style="flex:none;margin-left:auto">{_딱}</span>'
                   if _딱 else '')
                + '</div>')
        _줄3 = (f'<div style="display:flex;align-items:baseline;gap:12px;'
                f'margin-top:11px;padding-top:11px;'
                f'border-top:1px solid #3f382d;white-space:nowrap">'
                f'<span style="flex:none;font-size:23px;font-weight:700;'
                f'color:#d4ab45">{_위라}</span>'
                f'<span style="flex:none;font-size:29px;font-weight:800;'
                f'color:#f2efe8;font-family:{MONO}">{_위값}</span>'
                + (f'<span style="flex:1;min-width:0;font-size:21px;'
                   f'color:#a49c8e;overflow:hidden;text-overflow:ellipsis">'
                   f'{_작}</span>' if _작 else '<span style="flex:1"></span>')
                + (f'<span style="flex:none">{_칩}</span>' if _칩 else '')
                + '</div>')
        가1.append(
            f'<div style="flex:none;background:#24201a;'
            f'border:1px solid #3f382d;border-radius:16px;'
            f'padding:14px 22px;box-sizing:border-box'
            + ('' if n == 0 else ';margin-top:12px') + '">'
            + _줄1 + _줄2 + _줄3 + '</div>')

    # ⚠️ 매수 상한은 **시장 보합 기준**이다. 시장이 같이 빠지면 더 내려간다
    _상한말 = ((f'<div style="font-size:25px;color:#7fa6ff;line-height:1.5;'
                f'margin-bottom:10px;padding:8px 14px;background:#1b2536;'
                f'border-radius:11px"><b>매수 적정 범위</b>는 08:50에 정해질 '
                f'값이 들어올 자리입니다 (열에 아홉 날 기준). 시장이 더 많이 '
                f'빠져 있으면 <b>이보다 낮아집니다.</b> 반은 +15%, 반은 +40%에 '
                f'팝니다.</div>')
               if (후보 and not 확정) else '')

    _팔계획 = ((f'<div style="font-size:26px;color:{QC["금"]};line-height:1.5;'
                # ⚠️ 두 줄이면 아래 칸이 236px 이 되어 가운데가 21px 잘린다
                f'margin-bottom:14px">네 종목 <b>모두 같습니다</b>. '
                f'<b>반은 +15%</b>, <b>나머지 반은 +40%</b>에 팝니다</div>')
               if (후보 and not 확정) else '')

    아1 = (_상한말 + ((f'<div style="background:#2a1c1a;border-left:9px solid #ef7a6c;'
            f'border-radius:20px;padding:22px 30px;'
            f'font-size:29px;line-height:1.6">'
            # ⭐ **한 줄** (2026-09-14 디자인 ②) — 두 줄이면 아래 여백이 45px 로 죽는다
            f'⚠️⚠️ <b>09:01에 체결 안 된 주문은 반드시 취소</b> '
            f'(장중 체결분은 수익 1/6)</div>') if (확정 and 살것) else
           (f'<div style="background:#1f1b16;border-left:9px solid {QC["선"]};'
            f'border-radius:20px;padding:22px 30px;'
            f'font-size:29px;line-height:1.6">'
            # ⭐ 「상대갭 … 없었습니다」는 **위 리드에 이미 있다** — 각주에서 뺐다
            f'<b>아무것도 사지 않는 것도 규칙대로</b> 한 것입니다.</div>'
            ) if 확정 else
           (f'<div style="background:#2a1c1a;border-left:9px solid #ef7a6c;'
            f'border-radius:20px;padding:22px 30px;'
            f'font-size:29px;line-height:1.6">'
            # ⚠️ 「08:50 이후에 매수 적정 범위가 표시됩니다」는 **거꾸로**다.
            #    범위는 **08:50 전**에 미리 보여 주는 것이고, 08:50이 되면
            #    범위가 사라지고 **정확한 지정가 한 값**으로 바뀐다 (2026-09-11)
            f'⚠️ 아직 <b>「살 종목」이 아닙니다</b> · '
            f'<b>08:50</b>에 살지와 지정가가 정해집니다</div>') if 후보 else
           (f'<div style="background:#1f1b16;border-left:9px solid {QC["선"]};'
            f'border-radius:20px;padding:22px 30px;'
            f'font-size:29px;line-height:1.6">'
            f'아무것도 사지 않는 것도 <b>규칙대로 한 것</b>입니다</div>'))
           + f'<div style="display:flex;align-items:baseline;margin-top:20px">'
           f'<span style="font-size:27px;color:{QC["금"]};font-weight:700">'
           f'넘기면 <b>어떻게 뽑았는지</b> 나옵니다 →</span>'
           f'<span style="margin-left:auto;font-family:{MONO};font-size:24px;'
           f'color:{QC["보조"]};letter-spacing:.14em">1 / 4</span></div>')

    # ══ 2장 · 안내와 주의사항 ══
    위2 = (f'<div style="font-family:{MONO};font-size:26px;color:{QC["금"]};'
           f'letter-spacing:.18em;font-weight:700">HOW THEY WERE PICKED</div>'
           f'<div style="font-size:56px;font-weight:800;letter-spacing:-.035em;'
           f'margin-top:16px;line-height:1.12">어떻게 뽑았나</div>'
           # ⚠️ 본문에 있던 설명을 **머리말로** 올렸다 (2026-09-11).
           #    가운데 칸을 비워 「셋 중 하나」를 같은 장에 들인다
           f'<div style="font-size:27px;color:{QC["금"]};margin-top:12px;'
           f'line-height:1.55">브리핑은 뉴스를 읽는 <b>이야기</b>, 여기는 '
           f'<b>재무제표와 주가만 보는 기계 규칙</b>이라 종목이 서로 다른 것이 '
           f'정상입니다. 찾는 것은 하나, <b>번 돈을 착실히 쌓아온 작은 회사가 '
           f'회사 사정과 상관없이 크게 빠진 날.</b></div>')

    # ── ⭐⭐⭐ **오늘 왜 이 종목들인가** (2026-09-11 · 1장에서 옮겨 왔다) ──
    #    사용자: 「"오늘 왜 이 종목들인가"는 **두번째 페이지로** 보내자」
    #    ⚠️ 1장은 1080x1350 고정이라 이것까지 넣으면 종목이 잘렸다
    _왜 = ""
    # ⚠️⚠️ **08:50 뒤에도 보여 준다** (2026-09-11 지적).
    #    전에는 `not 확정` 이라 확정되면 이 칸이 통째로 사라졌고,
    #    그러면 ❶❷ 가 **위로 밀려 자리가 바뀌었다.**
    #    「오늘 왜 이 종목들인가」는 확정 뒤에도 그대로 맞는 말이다
    if 후보:
        _기존 = sum(1 for x in 후보 if x.get("기존규칙"))
        _섹 = sum(1 for x in 후보 if x.get("섹터규칙"))
        _시 = sum(1 for x in 후보 if x.get("시장규칙"))
        _지 = (q.get("국면") or {}).get("지수낙폭") or {}
        _눌 = [k for k, v in _지.items()
               if isinstance(v, (list, tuple)) and len(v) >= 2
               and ((v[0] is not None and v[0] <= -7)
                    or (v[1] is not None and v[1] <= -10))]
        _줄9 = []
        for _라, _bg, _fg, _n, _말 in (
                ("시장", "#1b2536", "#7fa6ff", _시,
                 "지수가 크게 빠져 있어서 종목이 <b>조금만</b> 빠져도 후보"
                 + (f" ({' · '.join(_눌)})" if _눌 else "")),
                ("낙폭", "#26231d", "#a49c8e", _기존,
                 "20일에 <b>10% 넘게</b> 빠지고 볼린저 아래"),
                ("섹터", "#231d2e", "#b89ae8", _섹,
                 "방산·원전·반도체 등 <b>업종마다 다른 기준</b>")):
            if not _n:
                continue
            _줄9.append((_라, _bg, _fg, _n, _말))
        # ⚠️⚠️ **세 규칙이 다 걸리는 날 자리가 모자란다** (2026-09-11 지적).
        #    오늘은 「시장」 하나라 딱 맞지만, 셋이 다 나오면 줄이 셋 —
        #    설명까지 붙으면 두 줄씩 여섯 줄이 되어 **2장이 넘친다.**
        #    ⇒ **둘 이상이면 설명을 빼고 한 줄로 모은다.** 셋이든 하나든
        #       칸 높이가 안 변한다. 설명은 바로 아래 ② 에 그대로 있다
        _여럿 = len(_줄9) >= 2
        if _여럿:
            _줄9 = ['<div style="font-size:27px;line-height:1.75">'
                    + " ".join(
                        f'<span style="display:inline-block;background:{_b};'
                        f'color:{_f};border-radius:6px;padding:2px 13px;'
                        f'font-size:24px;font-weight:800">{_r}</span>'
                        f'<b style="margin:0 14px 0 8px">{_c}개</b>'
                        for _r, _b, _f, _c, _ in _줄9)
                    + '</div>'
                    + f'<div style="font-size:24px;color:#5a6b78;'
                      f'margin-top:7px">셋 중 <b>하나만</b> 맞아도 후보입니다 '
                      f'각 규칙은 아래 ❷에</div>']
        else:
            _줄9 = [f'<div style="margin-bottom:9px">'
                    f'<span style="display:inline-block;background:{_b};'
                    f'color:{_f};border-radius:6px;padding:2px 13px;'
                    f'font-size:25px;font-weight:800">{_r}</span>'
                    f'<span style="font-size:27px;margin-left:11px">'
                    f'<b>{_c}개</b> · {_말2}</span></div>'
                    for _r, _b, _f, _c, _말2 in _줄9]
        if _줄9:
            _왜 = (f'<div style="padding:15px 28px;background:#1b2230;'
                   f'border:2px solid #d6e4ef;border-radius:20px">'
                   f'<div style="font-size:28px;font-weight:800;color:#7fa6ff;'
                   f'margin-bottom:10px">🧭 오늘 왜 이 종목들인가</div>'
                   + "".join(_줄9)
                   # ⚠️ 꼬리 한 줄을 뺐다 — 1장 딱지 설명과 **같은 말**이고,
                   #    「셋 중 하나」는 이제 **바로 아래에** 있다
                   + '</div>')

    # ⚠️ 딱지를 **글 첫 줄 안에** 넣는다. 전에는 딱지가 자기 줄(34px)을
    #    차지하고 아래 여백(12px)까지 둬서 **두 줄 글 위에 46px 이 얹혀**
    #    박스가 내용보다 커 보였다 (2026-09-11 사용자 지적)
    def _규칙줄(라, 바탕, 글색, 띠, 속):
        return (f'<div style="background:{바탕};border-left:9px solid {띠};'
                f'border-radius:20px;padding:14px 26px;'
                f'font-size:26px;line-height:1.55">'
                f'<span style="display:inline-block;background:#1f1b16cc;'
                f'color:{글색};border-radius:6px;padding:1px 13px;'
                f'font-size:23px;font-weight:800;margin-right:11px">{라}</span>'
                f'{속}</div>')

    # ⚠️⚠️ **가까운 것은 한 무리, 다른 무리는 더 멀리** (2026-09-11 지시).
    #    「🧭 왜 / ① 먼저 / ② 셋 중 하나」는 **서로 다른 항목**이라 사이를 벌리고,
    #    한 무리 안(낙폭·섹터·시장)은 **붙인다.**
    #        무리 사이  20(칸 틈) + 16(margin) = **36px**
    #        무리 안    **6px**
    #    ⚠️ 칸 틈(`장()`의 gap)을 키우면 **다른 장까지 같이 늘어나** 잘린다.
    #       그래서 이 장에서만 `margin-top` 으로 벌린다
    # ⚠️ 36px 은 **너무 넓었다** (2026-09-11). 「지금의 서로 반 수준이면 돼」
    #    ⇒ 무리 사이 **18px** (장(틈=18)) · 무리 안 **13px**.
    #       margin 은 없애고 **칸 틈 하나로** 준다 — 두 군데서 주면 또 어긋난다
    _무리 = ''
    # ⚠️ ① 머리말도 **박스 밖**에 둔다 — ② 가 밖이라 짝이 안 맞았다 (지시)
    # ⭐⭐ **부제를 카드뉴스 꼴로** (2026-09-11 지시).
    #    「① ②」 문자 대신 **동그란 번호 딱지 + 굵은 한글**.
    #    순서는 딱지가, 뜻은 글자가 나른다 — 눈이 번호부터 잡는다
    def _머리표(번, 글, 색="#7fa6ff"):
        return (f'<div style="display:flex;align-items:center;gap:13px;'
                f'margin:0 0 7px">'
                f'<span style="flex:none;width:34px;height:34px;'
                f'border-radius:50%;background:{색};color:#12100d;'
                f'font-family:{MONO};font-size:21px;font-weight:800;'
                f'display:flex;align-items:center;justify-content:center;'
                f'line-height:1">{번}</span>'
                f'<span style="font-size:28px;font-weight:800;'
                f'letter-spacing:-.015em">{글}</span></div>')


    가2 = ([_왜] if _왜 else []) + [
           f'<div style="{_무리}">'
           + _머리표(1, '먼저, 이걸 <b>모두</b> 통과')
           + f'<div style="padding:19px 28px;background:#1f1b16;'
           f'border-radius:20px;font-size:26px;line-height:1.55">'
           f'· 자기 돈의 <b>{R.잉여금하한:g}% 이상</b>이 벌어서 쌓은 이익 · '
           f'빚은 <b>{R.부채상한:g}% 이하</b> · 작년 <b>순이익 흑자</b><br>'
           f'· 시가총액 <b>{R.시총하한억:,.0f}억~{R.시총상한억:,.0f}억</b> · '
           f'하루 거래 <b>{R.대금하한억:g}억 이상</b> '
           f'<span style="font-size:23px;color:#a49c8e">'
           f'(관리종목·우선주·스팩 제외)</span></div></div>',

           f'<div style="{_무리}">'
           + _머리표(2, '그 다음, <b>셋 중 하나</b>만 맞으면 후보')
           + _규칙줄("낙폭", "#211d18", "#a49c8e", "#9a968d",
                     f"20거래일 동안 <b>{abs(R.낙폭20문턱):g}% 넘게</b> 빠졌고, "
                     f"값이 평소 움직이던 폭의 <b>아래쪽</b>"
                     f"(볼린저 −{abs(R.볼린저문턱):g}σ)에 있다")
           + '<div style="height:11px"></div>'
           + _규칙줄("섹터", "#231d2e", "#b89ae8", "#8b6ec4",
                     f"방산·원전·반도체 등 <b>{len(R.섹터규칙)}개 업종</b>은 "
                     f"업종마다 "
                     "<b>다른 기준</b>을 쓴다. 잘 빠지는 업종은 더 많이 빠져야 "
                     "걸린다")
           + '<div style="height:11px"></div>'
           + _규칙줄("시장", "#1b2536", "#7fa6ff", "#7fa6ff",
                     f"<b>지수가 눌려 있는 날</b>"
                     f"(20일 −{abs(R.지수낙20문턱):g}% · "
                     f"60일 −{abs(R.지수낙60문턱):g}%)에는 <b>조금만</b> "
                     f"빠져도 걸린다 (볼린저 −{abs(R.시장볼문턱):g}σ · "
                     f"20일 −{abs(R.시장낙20문턱):g}% · "
                     f"60일 −{abs(R.시장낙60문턱):g}%)")
           + '</div>']

    아2 = (f'<div style="font-size:26px;color:{QC["보조"]};line-height:1.65">'
           f'여러 규칙에 걸린 종목이 <b>1장 위쪽</b>에 옵니다. '
           f'다음 장은 <b>언제 사고 언제 파는지</b>입니다.</div>'
           f'<div style="text-align:right;margin-top:16px;font-family:{MONO};'
           f'font-size:24px;color:{QC["보조"]};letter-spacing:.14em">2 / 4</div>')

    # ══ 4장 · 어떻게 사고 파나 ══ (2026-09-11 신설)
    #    ⚠️ 2장이 **2251px** 까지 부풀어 901px 이 카드 밖으로 나갔다.
    #       「얼마나 넣나 · 어떻게 파나 · 08:50에 5분」이 통째로 안 보였다.
    #       내용을 버리지 않고 **장을 하나 늘린다**
    위2b = (f'<div style="font-family:{MONO};font-size:26px;color:{QC["금"]};'
            f'letter-spacing:.18em;font-weight:700">HOW TO BUY &amp; SELL</div>'
            f'<div style="font-size:56px;font-weight:800;letter-spacing:-.035em;'
            f'margin-top:16px;line-height:1.12">어떻게 사고 파나</div>'
            # ⚠️ 3장 제목과 ❶ 사이가 비어 있었다 (2026-09-11 지시).
            #    「설명글이나, 공간이 모자라서 뺐거나 그런 내용을 넣어줬으면」
            #    ⇒ **규칙이 정하는 것과 안 정하는 것**을 여기서 못 박는다
            f'<div style="font-size:27px;color:{QC["금"]};margin-top:12px;'
            f'line-height:1.55">규칙이 정하는 것은 <b>언제 사고 언제 파는지</b> '
            f'둘뿐입니다. <b>얼마를 넣을지는 정하지 않습니다.</b></div>')
    # ⚠️⚠️ **「얼마나 넣나」를 뺐다** (2026-09-11 사용자 지적).
    #    「한 종목에 자산의 20% · 하루 최대 자산의 80%」는 **종목을 고르는
    #     규칙이 아니라 금액 배분**이다. 자산관리는 안 하기로 정했는데
    #     화면에 있으면 **권고처럼 읽힌다.**
    #    ⚠️ 사실과도 안 맞는다 — 사용자는 하루 50~100만원(잘 되면 1,000만원)으로
    #       매매한다. 20% 는 **자본 시뮬 안에서 쓰는 가정**이지 사용자 몫이 아니다.
    #       실험 스크립트(sell_lab·liquidity_lab 등)의 20% 는 **시뮬 내부 값**이라
    #       그대로 둔다 — 그건 화면에 안 나간다
    #    ⚠️ 「하루 최대 4종목」만 **규칙의 일부**라 08:50 칸에 남겼다
    # ⚠️ **사는 순서대로** 놓는다 — 08:50(사기) → 목표에 닿으면 → 안 닿으면.
    #    「얼마나 넣나」를 뺀 자리가 비어서, 한 박스에 뭉쳐 있던 「파는 법」을
    #    **둘로 풀었다** (2026-09-11). 빽빽하던 것도 같이 풀린다
    # ⚠️⚠️ **사는 법 / 파는 법을 갈라 놓는다** (2026-09-11 지시).
    #    「주제가 어떻게 사고 파나니까 어떻게 사는지, 어떻게 파는지
    #     **두 항목**이 있는 거니까 구분되도록」
    #    2장과 **같은 방식**을 쓴다 — 머리말은 박스 밖, 무리 사이는 칸 틈(18),
    #    무리 안은 13px. 눈이 두 덩어리로 읽는다
    # ⚠️⚠️ **무리를 div 로 감싸야 한다** (2026-09-11 실측으로 잡았다).
    #    `"".join(가2b)` 는 파이썬 목록을 **한 덩어리 HTML** 로 만든다.
    #    그러면 flex 자식은 목록 항목이 아니라 **그 안의 최상위 div 들**이 되고,
    #    space-between 이 머리말·박스·박스를 **똑같이** 벌린다.
    #    실측: 머리말↓박스 73px · 같은 무리 박스끼리 143px (거꾸로였다)
    # ⚠️ ❶ 무리만 내린다 (2026-09-11 지시). `space-between` 은 **마지막 자식을
    #    바닥에 붙이므로** 여기에 margin 을 줘도 ❷ 는 안 움직인다
    가2b = ['<div style="margin-top:74px">'
            + _머리표(1, '어떻게 <b>사나</b>', 색="#d4ab45")
            + 박스('<b>08:50에 5분, 여기서 살지 정해진다</b><br>'
                   '후보들의 예상체결가를 보고, 그 값들의 <b>중앙값</b>보다 '
                   f'<b>{abs(R.상대갭문턱):g}%p 더 빠진 것</b>만 '
                   f'<b>최대 {R.하루최대종목}종목</b> 지정가로 삽니다.<br>'
                   '<b>⚠️ 09:01에 체결 안 된 주문은 반드시 취소하세요.</b><br>'
                   '<span style="font-size:24px;color:#a49c8e">'
                   '맞는 게 없으면 <b>아무것도 사지 않습니다.</b></span>',
                   바탕="#241f14", 선="#d4ab45", 글=25, 줄=1.55) + '</div>',

            '<div>' + _머리표(2, '어떻게 <b>파나</b>')
            + 박스('<b>목표에 닿으면 · 둘로 나눠 판다</b><br>'
                   '한 종목을 사면 <b>주문을 둘로 나눠</b> 겁니다. 산 주식의 '
                   f'반은 <b>+{R.앞몫목표:g}%</b>에 팔아 이익을 일찍 챙기고, '
                   f'나머지 반은 <b>+{R.뒷몫목표:g}%</b>까지 기다립니다.<br>'
                   '<span style="font-size:23px;color:#a49c8e">나눠 팔면 '
                   f'계좌 흔들림이 <b>{abs(_옛낙):.1f}% → {abs(_새낙):.1f}%</b>'
                   '로 줄었습니다.</span>', 글=25, 줄=1.55)
            + '<div style="height:11px"></div>'
            + 박스('<b>목표에 안 닿으면 · 날짜로 끝낸다</b><br>'
                   f'앞의 반은 <b>{R.앞몫기한}거래일</b>, 뒤의 반은 '
                   f'<b>{R.뒷몫기한}거래일</b>이 지나면 그날 값에 정리합니다.<br>'
                   '<b>손절은 하지 않습니다.</b> 값이 빠졌다는 이유로 중간에 '
                   '팔지 않습니다.', 글=25, 줄=1.55) + '</div>']

    # ⚠️⚠️ **성적 숫자를 뺐다** (2026-09-11 지적). 4장이 성적표 전용인데
    #    여기에도 「130건 · 85.4% · 평균 +17.9% · 47일」을 적어 **겹쳤다.**
    #    5장으로 쪼갤 때 내가 옮겨 붙인 것이다 — 4장에만 둔다
    아2b = (f'<div style="font-size:26px;color:{QC["보조"]};line-height:1.65">'
            f'다음 장은 이 규칙이 <b>과거에 어땠는지</b>입니다.</div>'
            f'<div style="text-align:right;margin-top:16px;font-family:{MONO};'
            f'font-size:24px;color:{QC["보조"]};letter-spacing:.14em">3 / 4</div>')

    # ══ 3장 · 과거에 어땠나 ══ (2026-09-07 — 세로 상세에서 옮겨 왔다)
    위3 = (f'<div style="font-family:{MONO};font-size:26px;color:{QC["금"]};'
           f'letter-spacing:.18em;font-weight:700">TRACK RECORD</div>'
           f'<div style="font-size:56px;font-weight:800;letter-spacing:-.035em;'
           f'margin-top:16px;line-height:1.12">과거에 어땠나</div>'
           f'<div style="font-size:24px;color:{QC["보조"]};margin-top:8px">'
           f'{_사례.get("기간", "")} · {_사례.get("해수", 0)}개 해</div>')
    # ⚠️ 8 → 6 (2026-09-11). 8건이면 「가장 나빴던 셋」 박스가
    #    아래 문단과 **포개져** 글이 글 위에 찍혔다 (실측)
    # ⚠️ 5 → 4 (2026-09-11). 박스에 숨통(안여백 30)을 주면서 13px 이 잘렸다.
    #    「답답하지 않게」가 목적이니 **글을 다시 조이는 대신 줄 수를 줄인다**
    _최근 = (_사례.get("최근") or [])[:3]
    _최악 = (_사례.get("최악") or [])[:3]
    가3 = [f'<p style="font-size:28px;line-height:1.75;margin:0">'
           f'이 규칙이 <b>과거에 있었다면</b> 이렇게 됐을 것입니다. '
           f'아무도 실제로 사지 않았고, 컴퓨터가 옛 주가로 계산한 것입니다.</p>']
    if _사례:
        가3.append(
            f'<div style="padding:26px 30px;background:#1f1b16;'
            f'border-radius:20px;'
            f'font-size:28px;line-height:1.85">'
            f'모두 <b>{_사례.get("전체건수", 0)}번</b> 샀고 그중 '
            f'<b>{_사례.get("승률", 0)}%</b>가 수익이었습니다. '
            f'평균 <b>{_사례.get("평균", 0):+.1f}%</b>를 '
            f'<b>{_사례.get("평균보유", 0):.0f}일</b> 만에 냈습니다.<br>'
            f'<span style="color:#ef7a6c">가장 나빴던 한 건은 '
            f'<b>{_사례.get("가장나쁨", 0):+.1f}%</b>였습니다.</span></div>')
    if _최근:
        _칸 = "".join(
            '<tr><td style="padding:8px 0;font-size:25px;color:#d3ccbe">'
            + _esc(x.get("날짜", "")) + '</td>'
            '<td style="padding:8px 0;font-size:25px;color:#d3ccbe;font-weight:700">'
            + _esc(x.get("이름", "")) + '</td>'
            '<td style="padding:8px 0;font-size:25px;color:#d3ccbe;text-align:right">'
            + format(x.get("매수가", 0), ",") + '원</td>'
            '<td style="padding:8px 0;font-size:25px;text-align:right;'
            'font-weight:700;color:'
            + ("#ef7a6c" if (x.get("결과") or 0) > 0 else "#2050c8") + '">'
            + format(x.get("결과") or 0, "+.1f") + '%</td>'
            '<td style="padding:8px 0;font-size:24px;text-align:right;color:'
            + QC["보조"] + '">' + str(x.get("며칠", "")) + '일</td></tr>'
            for x in _최근)
        # ⚠️⚠️ **머리글이 없어 숫자가 뭔지 몰랐다** (2026-09-09 사용자 지적)
        #    「5230원, +27.2%, 7일 이것들이 뭐 의미하는지 모르겠어」
        #    그리고 **+27.2%가 계속 같은 이유**도 적어 준다:
        #    반 +15% · 반 +40% 에 팔아 둘 다 닿으면 언제나 0.5x14.74+0.5x39.74
        _머 = ('<tr><td style="padding:2px 0;font-size:21px;color:' + QC["보조"]
               + '">날짜</td>'
               '<td style="padding:2px 0;font-size:21px;color:' + QC["보조"]
               + '">종목</td>'
               '<td style="padding:2px 0;font-size:21px;text-align:right;color:'
               + QC["보조"] + '">산 값</td>'
               '<td style="padding:2px 0;font-size:21px;text-align:right;color:'
               + QC["보조"] + '">수익률</td>'
               '<td style="padding:2px 0;font-size:21px;text-align:right;color:'
               + QC["보조"] + '">며칠</td></tr>')
        가3.append(
            '<div><div style="font-size:26px;font-weight:800;'
            'margin-bottom:6px">최근 ' + str(len(_최근)) + '건</div>'
            '<table style="width:100%;border-collapse:collapse">'
            + _머 + _칸 + '</table>'
            '<div style="font-size:21px;color:' + QC["보조"]
            + ';margin-top:6px;line-height:1.45">'
            '산 값 = 그날 시가 · 며칠 = 다 팔 때까지 걸린 날<br>'
            '수익률이 자주 <b>+27.2%</b>로 같은 것은 '
            '<b>반은 +15%, 반은 +40%</b>에 팔기 때문입니다. '
            '둘 다 목표에 닿으면 언제나 같은 값이 됩니다'
            '</div></div>')
    if _최악:
        _나 = " · ".join(_esc(x.get("이름", "")) + " "
                         + format(x.get("결과") or 0, "+.1f") + "%"
                         for x in _최악)
        가3.append(
            '<div style="padding:24px 30px;background:#2a1c1a;'
            'border-left:9px solid #ef7a6c;border-radius:20px;'
            'font-size:26px;line-height:1.6">'
            '<b>가장 나빴던 셋</b><br>' + _나 + '</div>')
    아3 = (f'<div style="font-size:25px;color:{QC["보조"]};line-height:1.7">'
           f'위 숫자는 전부 <b>과거 자료로 계산한 것</b>입니다. '
           f'「과거에 이랬다」이지 「앞으로 이럴 것」이 아닙니다. '
           f'실제로 산 기록은 오늘부터 쌓입니다.<br>'
           f'<b>매수 추천이 아닙니다.</b> 판단과 책임은 본인에게 있습니다.</div>'
           f'<div style="text-align:right;margin-top:10px;font-family:{MONO};'
           f'font-size:24px;color:{QC["보조"]};letter-spacing:.14em">4 / 4</div>')


    return (f'<section class="view" id="qt" hidden>'
            f'<div class="top"><div class="in">'
            f'<button class="tbtn" data-home type="button">← 처음</button>'
            f'<span class="now">퀀트 후보</span></div></div>'
            f'<div class="rail qrail" data-active="true">'
            + 장(위1, "".join(가1), 아1, "퀀트1 종목", 틈=16)
            + 장(위2, "".join(가2), 아2, "퀀트2 어떻게뽑았나", 틈=18)
            + 장(위2b, "".join(가2b), 아2b, "퀀트3 사고파나", 틈=34)
            + 장(위3, "".join(가3), 아3, "퀀트4 성적표")
            + f'</div>'
            f'<div style="text-align:center;font-size:13px;color:{QC["보조"]};'
            f'padding:0 0 30px">← 옆으로 넘겨서 보세요 →</div>'
            f'</section>')


def _month_grid(year, month, have, have_all, oldest_kept, today):
    """한 달치 칸. **이 페이지에 담긴 날만** 누를 수 있다.

    기록은 있는데 안 담긴 날(`--days` 밖)은 회색으로 남긴다 — 아예 빼 버리면
    "그날은 브리핑이 없었나?"가 되고, 회색이면 "있는데 여기엔 없다"가 보인다.
    """
    cells = ""
    first_dow = (datetime(year, month, 1).weekday() + 1) % 7   # 일요일=0
    cells += '<div></div>' * first_dow
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = f"{year:04d}-{month:02d}-{day:02d}"
        if d in have:
            cls = "cell has" + (" today" if d == today else "")
            cells += (f'<button class="{cls}" data-d="{d}" type="button">'
                      f'{day}<span class="dot"></span></button>')
        elif d in have_all:
            cells += (f'<div class="cell old" title="기록은 있지만 이 페이지에 '
                      f'담기지 않았습니다">{day}<span class="dot"></span></div>')
        else:
            cells += f'<div class="cell">{day}</div>'
    dows = "".join(f'<div class="dow{" sun" if i == 0 else ""}">{w}</div>'
                   for i, w in enumerate(["일", "월", "화", "수", "목", "금", "토"]))
    # 달 이름은 여기 `data-label`에 넣는다. JS가 그걸 읽어 머리글에 쓴다 —
    # 파이썬과 JS 양쪽에 같은 문자열을 두면 한쪽만 고치게 된다.
    return (f'<div class="month" data-label="{year}. {month:02d}" hidden>'
            f'<div class="grid">{dows}{cells}</div></div>')


# ⚠️ 섹터 색 — 오르내림(빨강·파랑)이나 제목(청동)과 겹치지 않는 색으로만 고른다.
#    겹치면 "이 색이 무슨 뜻이지"가 화면마다 달라진다(2026-08-28).
PF_COLORS = ["#5f7a8a", "#d4ab45", "#6b8f6b", "#8a5f7a", "#7a6f5f",
             "#4f6f8f", "#9c8a4a", "#6f8a8a", "#8a6b5f", "#7f7f6b"]


def portfolio_view(day, cp):
    r"""**깜댕의 포트폴리오** — 섹터별 비율만 보여 준다.

    ⚠️⚠️ **금액을 화면에 내보내지 않는다** (2026-08-28 사용자 선택 A).
       이 사이트는 주소를 아는 사람이면 누구나 본다. 종목 추천은 남이 봐도 되지만
       **내 평가금액은 다른 문제다.** `평가금액`은 비율 계산에만 쓰고 화면에는
       **퍼센트만** 나간다. 금액을 넣고 싶어지면 그때는 사이트를 비공개로 옮기는 것이
       먼저다 — GitHub Pages 무료 요금제는 비공개가 안 된다.

    ⚠️ 파일이 없거나 보유가 비면 **단추 자체를 안 만든다.** 빈 화면보다 없는 편이 낫다.
    """
    pf = _portfolio()
    if not pf:
        return ""
    hold = [h for h in (pf.get("holdings") or []) if h.get("code")]
    if not hold:
        return ""
    total = sum(_f(h.get("평가금액"), 0) or 0 for h in hold)
    균등 = total <= 0

    def w(h):
        return 1.0 if 균등 else (_f(h.get("평가금액"), 0) or 0)

    denom = (len(hold) if 균등 else total) or 1

    by = {}
    for h in hold:
        by.setdefault(h.get("섹터") or "미분류", []).append(h)
    secs = sorted(by.items(), key=lambda kv: -sum(w(x) for x in kv[1]))
    pcts = [(sec, sum(w(x) for x in hs) / denom * 100, hs) for sec, hs in secs]

    # 오늘 후보와 겹치는 종목 — 이 화면의 쓸모다.
    today = {p_.get("code") for p_ in (day.get("picks") or [])}
    dup = [h for h in hold if h["code"] in today]

    # ── 도넛 — `conic-gradient` 하나로 그린다(라이브러리 없이). ──
    stops, acc = [], 0.0
    for i2, (sec, pct_, _hs) in enumerate(pcts):
        col = PF_COLORS[i2 % len(PF_COLORS)]
        stops.append(f"{col} {acc:.2f}% {acc + pct_:.2f}%")
        acc += pct_
    donut = (f'<div style="display:flex;justify-content:center;margin-top:22px">'
             f'<div style="width:190px;height:190px;border-radius:50%;'
             f'background:conic-gradient({", ".join(stops)});position:relative">'
             f'<div style="position:absolute;inset:26%;border-radius:50%;'
             f'background:{C["card"]};display:flex;flex-direction:column;'
             f'align-items:center;justify-content:center">'
             f'<div style="font-family:{MONO};font-size:26px;font-weight:800;'
             f'color:{C["text"]}">{len(hold)}</div>'
             f'<div style="font-size:12px;color:{C["muted"]}">종목</div>'
             f'</div></div></div>')

    # ── 섹터별 막대 ──
    bars = ""
    for i2, (sec, pct_, hs) in enumerate(pcts):
        col = PF_COLORS[i2 % len(PF_COLORS)]
        hit = any(h["code"] in today for h in hs)
        bars += (f'<div style="margin-top:14px">'
                 f'<div style="display:flex;justify-content:space-between;'
                 f'align-items:baseline;font-size:15px">'
                 f'<span><span style="display:inline-block;width:10px;height:10px;'
                 f'background:{col};margin-right:8px"></span>'
                 f'<b style="color:{C["text"]}">{sec}</b>'
                 + (f'<b style="color:{C["up"]};font-size:13px;margin-left:8px">'
                    f'오늘 후보</b>' if hit else "")
                 + f'</span>'
                 f'<b style="font-family:{MONO};color:{C["text"]}">{pct_:.1f}%</b></div>'
                 f'<div style="height:10px;background:{C["line"]};margin-top:6px">'
                 f'<div style="height:10px;width:{min(100, pct_):.1f}%;'
                 f'background:{col}"></div></div></div>')

    # ── 종목별 표 — 무엇이 어느 섹터인지 ──
    rows = ""
    for i2, (sec, _p, hs) in enumerate(pcts):
        col = PF_COLORS[i2 % len(PF_COLORS)]
        for h in sorted(hs, key=lambda x: -w(x)):
            hp = w(h) / denom * 100
            rows += (f'<tr style="border-top:1px solid {C["line"]}">'
                     f'<td style="padding:11px 8px 11px 0;font-size:15px;'
                     f'font-weight:700;color:{C["text"]}">{h.get("name") or h["code"]}'
                     + (f' <b style="color:{C["up"]};font-size:12px">오늘 후보</b>'
                        if h["code"] in today else "")
                     + f'</td>'
                     f'<td style="padding:11px 8px;font-size:14px;color:{C["muted"]};'
                     f'white-space:nowrap"><span style="display:inline-block;width:8px;'
                     f'height:8px;background:{col};margin-right:6px"></span>{sec}</td>'
                     f'<td align="right" style="padding:11px 0;font-family:{MONO};'
                     f'font-size:15px;font-weight:700;color:{C["text"]}">'
                     f'{hp:.1f}%</td></tr>')

    note = ("보유 <b>종목 수</b>로 나눈 비율입니다(금액 정보 없음)." if 균등
            else "평가금액 기준 비율입니다. <b>금액 자체는 화면에 나가지 않습니다.</b>")
    미분류 = [h.get("name") for h in hold if (h.get("섹터") or "미분류") == "미분류"]

    return (f'<section class="view" id="pf" hidden>'
            f'<div class="top"><div class="in">'
            f'<button class="tbtn" data-home type="button">← 처음</button>'
            f'<span class="now">깜댕의 포트폴리오</span></div></div>'
            f'<div class="pad" style="padding-top:22px;padding-bottom:60px">'
            f'<div style="font-size:23px;font-weight:800;color:{C["text"]};'
            f'letter-spacing:-.02em">섹터별 비중</div>'
            f'<div style="font-size:14px;color:{C["muted"]};margin-top:6px">{note} '
            f'계좌 {pf.get("계좌수", 1)}개 합산 · 기준 {pf.get("updated", "-")}</div>'
            + donut + bars
            + f'<div style="font-size:19px;font-weight:800;color:{C["sub"]};'
              f'letter-spacing:{LS_KO};margin:30px 0 0">종목별</div>'
              f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
              f'border="0" style="margin-top:8px;table-layout:fixed;width:100%">'
              f'{rows}</table>'
            + (f'<div style="margin-top:24px;padding:14px 16px;background:#17181a08;'
               f'border-left:3px solid {C["up"]}">'
               f'<b style="font-size:15px;color:{C["up"]}">이미 들고 있는 오늘 후보</b>'
               f'<div style="font-size:14px;color:{C["text2"]};margin-top:6px">'
               + " · ".join(h.get("name") or h["code"] for h in dup)
               + " · 더 담기 전에 이미 얼마나 쏠려 있는지 보십시오.</div></div>"
               if dup else "")
            + (f'<div style="font-size:13px;color:{C["muted"]};margin-top:18px">'
               f'섹터를 못 찾은 종목: {" · ".join(미분류)} · '
               f'가치사슬맵에 없는 종목입니다.</div>' if 미분류 else "")
            + f'<div style="font-size:13px;color:{C["faint"]};margin-top:24px">'
              f'금액·수량은 담지 않습니다. 이 화면은 <b>쏠림</b>을 보는 용도입니다.</div>'
            + '</div></section>')


def _entry_band(date):
    r"""**09:05 진입체크 결과**를 그날 화면 맨 위에 띠로 붙인다 (2026-08-31 신설).

    ⚠️⚠️ 왜 웹으로 옮겼나: 진입체크의 **유일한 출력이 카카오**였는데, 카카오는
       알림이 오지 않아 실제로 안 읽혔다(2026-08-31 사용자 결정으로 카카오 폐지).
       매수는 **09:00~09:30**에 이뤄진다 — 그 시각에 보는 화면이 이 웹이므로,
       판정이 여기 있어야 쓸모가 있다.

    ⚠️ **판정만 옮긴다. 새로 계산하지 않는다.** 값은 `entry-check-log.jsonl`에 이미
       쌓여 있다. 화면이 다시 계산하면 09:05 판정과 낮에 본 화면이 달라진다.

    ⚠️ 없는 날은 **아무것도 그리지 않는다.** 빈 띠가 있으면 "오늘은 체크가 안 돌았나"와
       "아직 09:05 전인가"가 구분되지 않는다.
    """
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "entry-check-log.jsonl")
    if not os.path.exists(path):
        return ""
    rec = None
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        # 같은 날 여러 슬롯이 있으면 09:05를 쓴다(12:20은 2026-08-31에 껐다).
        if o.get("date") == date and o.get("ok") and o.get("slot", "0905") == "0905":
            rec = o
    if not rec or not (rec.get("results") or []):
        return ""

    색 = {"조건충족": C["green"], "보류": C["gold"], "철회검토": C["down"],
         "확인필요": C["gold"], "확인불가": C["muted"]}
    칩 = ""
    for r in rec["results"]:
        v = r.get("verdict") or "확인불가"
        c = 색.get(v, C["muted"])
        호가 = (r.get("호가") or {})
        sp = 호가.get("스프레드pct")
        칩 += (f'<span style="display:inline-block;border:1px solid {c};color:{c};'
              f'border-radius:999px;padding:5px 12px;margin:5px 8px 0 0;font-size:13px;'
              f'font-weight:700;white-space:nowrap">{r.get("grade","")} {r.get("name","")} '
              f'· {v}'
              + (f' · 스프레드 {sp}%' if sp is not None else "")
              + '</span>')
    t = str(rec.get("checked_at", ""))[11:16]
    return (f'<div style="border:1px solid {C["line"]};background:{C["dim"]}55;'
            f'padding:12px 14px;margin:0 0 14px">'
            f'<div style="font-family:{SANS};font-size:13px;font-weight:800;'
            f'color:{C["green"]};letter-spacing:-.01em">장 시작 후 확인 · {t}</div>'
            f'<div style="font-family:{SANS};font-size:12px;color:{C["muted"]};'
            f'margin-top:2px">아침에 써 둔 진입 조건이 지금 맞는지 대조한 결과입니다. '
            f'매수 권유가 아닙니다</div>{칩}</div>')


_ENG = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


def _코스피():
    # 어제 코스피 종가·등락률 (홈 **세 번째 칸**).
    # ⚠️ 홈은 「밤사이 미국 둘 + 어제 한국 하나」다. 카드 01 은 미국 셋
    #    (S&P·나스닥·다우존스)이라 **홈과 카드가 다르다** — 시안이 그렇게 돼 있고
    #    2026-09-11 사용자가 카드 쪽만 다우존스로 정했다
    import glob as _g
    _f = sorted(_g.glob(os.path.join(_DATA, "index-daily", "*.json")))
    if not _f:
        return None
    try:
        _d = json.load(io.open(_f[-1], encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return None
    return (_d.get("지수") or {}).get("코스피")


def _밤사이지수():
    # 홈 첫 화면의 **밤사이 지수 3칸** (시안 그대로).
    #
    # ## 어디서 읽나 — **낡은 파일을 피한다**
    #   data/us-index.json                  마지막 2026-09-01 (열흘 낡음) ❌
    #   data/snapshots/<날짜>/fetch_us.json  기준일 2026-09-10          ✅
    #
    # ⚠️⚠️ 홈은 **첫 화면**이다. 여기에 낡은 값을 띄우면 가장 눈에 띄는 자리에
    #    틀린 숫자를 놓게 된다. 못 읽으면 **블록을 아예 안 그린다** —
    #    빈 자리가 틀린 숫자보다 낫다
    import glob as _g
    _벌들 = sorted(_g.glob(os.path.join(_DATA, "snapshots", "*",
                                        "fetch_us.json")))
    if not _벌들:
        return ""
    try:
        _j = json.load(io.open(_벌들[-1], encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return ""
    _지 = _j.get("지수") or {}
    _칸 = []
    for _라, _src in (("S&P 500", _지.get("S&P500")),
                      ("나스닥 100", _지.get("나스닥100")),
                      ("코스피", _코스피())):
        if not isinstance(_src, dict) or _src.get("종가") is None:
            continue
        try:
            _v = float(_src["종가"])
            _c = float(_src.get("등락률") or 0)
        except (TypeError, ValueError):
            continue
        _색 = "#c8352b" if _c > 0 else ("#2050c8" if _c < 0 else "#6b665c")
        _칸.append(f'<div><span class="il">{_라}</span>'
                   f'<span class="iv">{_v:,.2f}</span>'
                   f'<span class="ic" style="color:{_색}">{_c:+.2f}%</span></div>')
    if len(_칸) < 2:
        return ""
    # ⚠️ 「밤사이 지수」 라벨과 **갱신시각**을 같이 둔다 (시안)
    _때 = ""
    try:
        _때 = datetime.fromtimestamp(
            os.path.getmtime(_벌들[-1])).strftime("%m/%d %H:%M")
    except Exception:  # noqa: BLE001
        pass
    return ('<div class="idxw"><div class="idxh"><b>밤사이 지수</b>'
            f'<span>{_때}</span></div>'
            '<div class="idx">' + "".join(_칸) + '</div></div>')


def build(out, days=DEFAULT_DAYS):
    # ⭐⭐ **카드 예산을 먼저 맞춘다** (2026-09-11).
    #    사이트는  을 읽는 게 아니라  로
    #    **다시 그린다.** 이걸 안 부르면 웹에 **줄이기 전 카드**가 나간다 —
    #    9/11 에 실제로 그랬다 (02 국면이 카드는 32px, 사이트는 19px)
    _카드 = os.path.join(os.path.dirname(os.path.abspath(out)) or ".",
                          "briefing-cards.html")
    if os.path.exists(_카드):
        예산맞추기("all", _카드)
    if not os.path.exists(LOG):
        return {"error": f"{LOG} 없음"}
    rows = [json.loads(x) for x in io.open(LOG, encoding="utf-8-sig") if x.strip()]
    rows = sorted([r for r in rows if r.get("date")], key=lambda r: r["date"])
    if not rows:
        return {"error": "기록이 하나도 없다"}

    all_dates = [r["date"] for r in rows]
    kept = rows[-days:]
    kept_dates = {r["date"] for r in kept}
    latest = kept[-1]["date"]
    oldest_kept = kept[0]["date"]

    rails, scrolls, missing = [], [], []
    for o in kept:
        cp = _copy(o["date"])
        if not cp:
            missing.append(o["date"])
        rails.append(f'<div class="rail" data-d="{o["date"]}" data-active="false">'
                     + "".join(cards_for(o, cp)) + "</div>")
        # ⚠️ 09:05 판정은 **세로에 넣지 않는다** (2026-08-31 재조정). 세로는 "왜 이
        #    종목인가"를 길게 설명하는 자리이고, 09:05 대조 결과는 성격이 다르다 —
        #    맨 위에 띠로 붙였더니 상세라는 취지와 어긋났다.
        #    ⇒ **가로 요약의 「장 시작 후 확인」을 그 결과로 갈아 끼운다**(build_cards).
        #       아침엔 "무엇을 볼지" 체크리스트였다가 09:05 뒤엔 "어떻게 됐나"가 된다.
        scrolls.append(f'<div class="scrollwrap" data-d="{o["date"]}" style="display:none">'
                       + build_scroll.render(o, cp, "web") + "</div>")

    # 달력 — 자료가 있는 달만 만든다. 빈 달을 넘기게 하면 넘길 이유가 없다.
    have = set(kept_dates)
    have_all = set(all_dates)
    months = sorted({(int(d[:4]), int(d[5:7])) for d in all_dates})
    today = datetime.now().strftime("%Y-%m-%d")
    grids = "".join(_month_grid(y, m, have, have_all, oldest_kept, today)
                    for y, m in months)

    dt = datetime.strptime(latest, "%Y-%m-%d")
    n_pick = len(kept[-1].get("picks") or [])
    # 이 화면을 언제 만들었는지. 캐시로 옛 화면을 보고 있는지 가리는 유일한 단서다.
    built = datetime.now().strftime("%m/%d %H:%M")
    # ⭐ 단추마다 **그 자료가 실제로 바뀐 시각**을 보여준다 (2026-09-09 · 09-10 고침)
    # ⚠️⚠️ **한 단추에 파일을 여럿 넣으면 안 된다** — 나중 것이 이겨서
    #    엉뚱한 시각이 찍힌다. 2026-09-10 에 사용자가 짚었다:
    #      「오늘 브리핑 보기에 맞춰서 **퀀트 갱신 일시도 맞춰지는 것 같은데?**」
    #      실제로 둘 다 **08:50** 이었다 —
    #      `forward-log.jsonl` 은 **동시호가 기록**(08:50 예약)이지 후보 갱신이 아니고,
    #      `briefing-cards.html` 은 카드 **이미지** 만든 시각이다
    _브리핑갱신 = _갱신시각([os.path.join(_DATA, "briefing-daily-log.jsonl")])
    # ⚠️⚠️ **2026-09-11 고침** — 전에는 `today-rule.html` 의 **파일 시각**을 썼다.
    #    그런데 그 파일은 **화면에 한 글자도 안 쓰인다**
    #    (`_갱신시각` 이 그걸 읽는 곳이 여기뿐이다).
    #    => **카드 내용을 고쳐도 시각이 안 바뀌었다.**
    #       09-11 09:35 에 카드를 고쳤는데 화면은 여전히 **08:03 갱신**이었다
    #    사용자: 「실제로 뭔가가 갱신됐으면 갱신된 시간이 **각각 따로** 나와야해」
    #    => 후보를 **실제로 뽑은 시각**(forward-log 의 `기록시각`)을 쓴다
    _퀀트갱신 = None
    try:
        _마지막9 = None
        for _x9 in io.open(QT_FILE, encoding="utf-8"):
            _x9 = _x9.strip()
            if _x9:
                _마지막9 = json.loads(_x9)
        _찍9 = str((_마지막9 or {}).get("기록시각") or "")
        if len(_찍9) >= 16:
            _d9 = datetime.strptime(_찍9[:16], "%Y-%m-%d %H:%M")
            _퀀트갱신 = (f"{_d9.month:02d}/{_d9.day:02d}"
                        f"({WEEKDAY[_d9.weekday()]}) {_d9:%H:%M} 갱신")
    except Exception:  # noqa: BLE001
        _퀀트갱신 = None
    if not _퀀트갱신:
        _퀀트갱신 = _갱신시각([os.path.join(_DATA, "today-rule.html")])
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    shell = (PAGE_CSS + PAGE_JS).replace("__W__", str(CARD_W)).replace("__H__", str(CARD_H))
    css, js = shell.split("</style>", 1)

    home = (
        f'<section class="view" id="home">'
        # ⚠️ 폰은 **날짜**, 데스크톱은 **MORNING BRIEFING** (시안).
        #    둘 다 넣고 CSS 로 바꿔 보인다
        f'<div class="eyebrow"><span class="mo">'
        f'{dt.strftime("%Y.%m.%d")} {_ENG[dt.weekday()]}</span>'
        f'<span class="pc">MORNING BRIEFING</span></div>'
        # ⚠️ 폰에서 **2줄**로 앉힌다 (시안: 「깜댕의 / 주식 브리핑」)
        # ⚠️ `<br>` **뒤에 공백을 남긴다.** 데스크톱에서는 br 을 숨기는데,
        #    공백까지 없애면 「깜댕의주식 브리핑」으로 붙어 버린다 (실제로 그랬다)
        f'<h1>{BRAND.replace(" ", "<br> ", 1)}</h1>'
        # ⚠️ 데스크톱에서만 보인다. 시안은 날짜·후보까지 **한 줄**로 합쳐 둔다
        f'<div class="sub">3분 만에 읽는 어제와 오늘의 시장 · '
        f'{dt.strftime("%Y.%m.%d")} {WEEKDAY[dt.weekday()]}요일 · 후보 {n_pick}</div>'
        f'<div class="when">{dt.strftime("%Y.%m.%d")} '
        f'{WEEKDAY[dt.weekday()]}요일 · 후보 {n_pick}</div>'
        + _밤사이지수()
        + f'<div class="btns">'
        f'<button class="big" id="btn-today" type="button" data-d="{latest}">'
        f'<span class="lab"><span class="t1"><b>오늘 브리핑 보기</b>'
        f'<i class="up">{_브리핑갱신 or ""}</i></span>'
        f'<i class="sub">뉴스·공시·수급으로 읽는 시장</i></span>'
        f'<span class="arw2">→</span></button>'
        # ⚠️ 후보가 없는 날은 단추를 안 만든다 — 눌렀는데 빈 화면이 뜨는 것보다 낫다
        + (f'<button class="big" id="btn-qt" type="button">'
           f'<span class="lab"><span class="t1"><b>퀀트 후보</b>'
           f'<i class="up">{_퀀트갱신 or ""}</i></span>'
           f'<i class="sub">재무·주가만 보는 데이터 분석</i></span>'
           f'<span class="arw2">→</span></button>' if _quant() else "")
        + f'<button class="big" id="btn-past" type="button">'
        f'<span class="lab"><span class="t1"><b>지난 브리핑 보기</b></span>'
        f'<i class="sub">달력에서 날짜 고르기</i></span>'
        f'<span class="arw2">→</span></button>'
        # ⚠️ 포트폴리오 파일이 없으면 **단추 자체를 안 만든다**
        + (f'<button class="big" id="btn-pf" type="button">'
           f'<span class="lab"><span class="t1"><b>깜댕의 포트폴리오</b></span>'
           # ⚠️ 「—」(em dash)는 쓰지 않는다 — 명세 6절 ⑦ · `check_typo` 가 잡는다
           f'<i class="sub">섹터별 비중 · 금액 비공개</i></span>'
           f'<span class="arw2">→</span></button>' if _portfolio() else "")
        + f'</div>'
        # ⚠️ **만든 시각을 찍는다** (2026-08-27 추가). 카톡 인앱 브라우저처럼 캐시가 센
        #    환경에서는 옛 화면이 그대로 뜨는데, 겉만 봐서는 옛것인지 알 수 없다.
        #    이 줄이 있으면 "언제 만든 화면을 보고 있는지"가 바로 보인다.
        # ⚠️ 폰에서는 **첫 줄만** 보인다 (시안). 수록 기간·생성 시각은
        #    데스크톱에서만 — 폰은 한 화면에 들어가야 한다.
        #    ⚠️ 생성 시각 자체는 없애지 않는다: 카톡 인앱처럼 캐시가 센 데서
        #       옛 화면인지 가려내는 유일한 단서다 (2026-08-27)
        f'<div class="note">투자 참고용이며 매수 권유가 아닙니다.'
        f'<span class="pconly"> 수록 {len(kept)}일 '
        f'({oldest_kept} ~ {latest}) · 화면 생성 {built}</span></div>'
        f'</section>')

    # ⚠️ 포트폴리오 화면은 달력과 나란한 형제다 — `cal` 문자열 앞에 붙인다.
    pf_html = portfolio_view(kept[-1], _copy(latest))
    _q = _quant()
    qt_html = quant_view(_q) if _q else ""

    cal = (
        pf_html
        + qt_html
        + f'<section class="view" id="cal" hidden>'
        f'<div class="top"><div class="in">'
        f'<button class="tbtn" data-home type="button">← 처음</button>'
        f'<span class="now">지난 브리핑</span></div></div>'
        f'<div class="cal"><div class="mon">'
        f'<button class="tbtn" id="m-prev" type="button">‹</button>'
        f'<b id="m-label"></b>'
        f'<button class="tbtn" id="m-next" type="button">›</button></div>'
        f'{grids}'
        f'<div class="legend"><i></i>회색으로 채워진 날은 기록은 있지만 이 페이지에 '
        f'담기지 않은 날입니다 · 최근 {days}일만 싣습니다.</div></div>'
        f'</section>')

    day = (
        f'<section class="view" id="day" hidden>'
        f'<div class="top"><div class="in">'
        f'<button class="tbtn" data-home type="button">← 처음</button>'
        f'<button class="tbtn" data-back type="button">달력</button>'
        f'<span class="now"></span>'
        # ⚠️ 글씨 크기 조절 — **세로 상세에서만** 쓴다. 가로 카드는 배율로 그려서
        #    글자만 키우면 카드 밖으로 넘친다(2026-08-28 요청).
        f'<span class="fs"><button data-fs="-" type="button" aria-label="글씨 작게">'
        f'A&minus;</button><button data-fs="+" type="button" aria-label="글씨 크게">'
        f'A+</button></span>'
        f'<span class="seg">'
        # ⚠️ 좁은 화면에서 숨기는 쪽은 **"가로·세로"**다(2026-08-27 지적).
        #    그건 넘기는 방식이고, 읽는 사람에게 필요한 정보는 "상세·요약"이다.
        f'<button data-f="scroll" type="button" aria-pressed="true">'
        f'<span class="ax">세로 </span>상세</button>'
        f'<button data-f="card" type="button" aria-pressed="false">'
        f'<span class="ax">가로 </span>요약</button>'
        f'</span></div></div>'
        + "".join(rails) + "".join(scrolls)
        + '<div class="nav"></div>'
        + '<button class="arw prev" type="button" aria-label="이전 카드">&#8249;</button>'
        + '<button class="arw next" type="button" aria-label="다음 카드">&#8250;</button>'
        + '</section>')

    html = (f"<title>{BRAND}</title>"
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            # ⚠️ **검색엔진 수집 차단** (2026-08-27 사용자 선택). 링크를 아는 사람은
            #    볼 수 있게 두되, 검색으로는 찾히지 않게 한다. `robots.txt`만으로는
            #    부족하다 — 다른 데서 링크가 걸리면 그걸 타고 색인될 수 있어서
            #    페이지 자체에도 박아 둔다. 둘 다 있어야 한다.
            '<div class="ptr"><i></i></div>'
            '<meta name="robots" content="noindex,nofollow,noarchive">'
            # ⚠️ **판 번호.** 아래 자기 점검이 이 값을 새로 받아온 것과 비교한다.
            f'<meta name="build" content="{stamp}">'
            + FONTS + "\n" + css + "</style>"
            + SITE_CSS.replace("__MONO__", SANS)
            + home + cal + day + js + SITE_JS)
# ⚠️⚠️ **화면 글의 `—`(em dash)를 `·` 로 바꾼다** (2026-09-11 지시).
    #    서술 파일(`card-copy`)에서 들어오는 문장에 섞여 있어 **소스만 고쳐서는
    #    안 없어진다.** 매일 새 글이 오므로 **내보내는 자리**에서 걸러야 한다.
    #    ⚠️ `<style>`·`<script>` 안에는 em dash 를 쓰지 않으므로 통째로 바꿔도 안전하다
    html = html.replace("—", "·")
    io.open(out, "w", encoding="utf-8").write(html)

    res = {"ok": True, "파일": out, "수록일": len(kept), "전체기록": len(all_dates),
           "최신": latest, "가장오래된": oldest_kept, "크기KB": round(len(html) / 1024, 1)}
    if os.path.exists(SITE_URL_FILE):
        res["url"] = io.open(SITE_URL_FILE, encoding="utf-8-sig").read().strip() or None
    if missing:
        res["_경고"] = f"서술 파일 없음: {missing} · 그날은 숫자만 나온다"
    if len(all_dates) > len(kept):
        res["_안내"] = f"오래된 {len(all_dates)-len(kept)}일은 달력에 회색으로만 남는다"
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS,
                    help=f"최근 며칠을 담을지 (기본 {DEFAULT_DAYS})")
    a = ap.parse_args()
    print(json.dumps(build(a.out, a.days), ensure_ascii=False))













