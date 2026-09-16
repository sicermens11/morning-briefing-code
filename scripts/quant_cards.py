#!/usr/bin/env python3
r"""
quant_cards.py — 퀀트 후보 **4장** (2026-09-14 · 밝은 판)

정본  design-share/reference/QUANT-FINAL.md
      design-share/reference/quant-cards-source.dc.html   ← 값이 어긋나면 이쪽이 이긴다

⚠️ 어두운 판(2026-09-14 오전)은 폐기. 페이지 #e8e3d8 · 카드 #f2efe8 · 종목 블록 #ffffff.
⚠️ 가로 요약 8장은 손대지 않는다 — 이 파일은 `#qt` 안 네 장만 만든다.
⚠️ 검사(퀀트는 이 셋만): 잘림 0(차단) · 높이 1350 · 마지막 종목 블록 밑 → 카드끝 ≥ 90px.
   종목 블록은 `data-block="1"` 표식으로 잰다 (밝은 판이라 바탕색으론 못 가른다).

정본과 명세가 다른 두 곳은 **정본**을 따랐다 (README: 「규칙과 정본이 어긋나면 정본이 이긴다」):
  · Q1 제목 68px (명세 64)
  · 후보 0개 카드는 space-between + gap 40 (명세 「고정 60px + 위 정렬」)
"""
import html
import io
import json
import os
import re

import rule_def as R
from card_theme import CARD_H, CARD_W, SANS

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# ── 색 (QUANT-FINAL 0절) ─────────────────────────────────────────
C = {
    "쪽": "#e8e3d8", "카드": "#f2efe8", "블록": "#ffffff",
    "먹": "#1c1813", "본": "#4b4740", "보": "#6b665c", "선": "#d5cec0", "금": "#8a7038",
    "빨": "#c8352b", "파": "#2050c8", "딱": "#f0e7d2", "경고": "#fbeeea",
}
_요일 = "월화수목금토일"


def _esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def _음(v, 소수=1, 기호="%"):
    """부호 있는 수 → 「−32.0%」꼴. 마이너스는 U+2212 (정본이 그 글자를 쓴다)"""
    s = f"{v:+.{소수}f}{기호}"
    return s.replace("-", "−")


def _몫말(비율, 뒤=False, 앞뒤=False):
    """매도 몫 이름 + 조사 (2026-09-14 디자인 답 6).

    50:50 이면   「반은」 / 「나머지 반은」 / 「앞의 반은」 / 「뒤의 반은」
    그 밖에는    「30%는」 / 「나머지 70%는」 / 「앞의 30%는」 / 「뒤의 70%는」
    ⚠️ 퍼센트 숫자 뒤 조사는 **항상 「는」·「를」·「가」** — 「30%은」이 아니다.
       비율이 바뀌면(30:70) 문구가 따라오고 조사도 틀리지 않는다
    """
    반 = abs(비율 - .5) < 1e-9
    if 앞뒤:
        머리 = "뒤의 " if 뒤 else "앞의 "
        return 머리 + ("반은" if 반 else f"{비율 * 100:g}%는")
    if 뒤:
        return "나머지 반은" if 반 else f"나머지 {비율 * 100:g}%는"
    return "반은" if 반 else f"{비율 * 100:g}%는"


def _굵(글, 색=None):
    """숫자 + 단위 + 뒤따르는 조사를 **한 묶음**으로 굵게·nowrap (QUANT-FINAL 5절).

    정본 `emph()` 를 그대로 옮겼다. 「3.3%로」「+40%까지」가 한 덩어리라
    조사만 다음 줄로 떨어지지 않는다. `9.0% → 3.3%` 같은 짝은 화살표까지 한 묶음.
    ⚠️ 색은 넣지 않는다 — 색은 방향(이익·손실)에만 쓴다 (`색` 을 주면 그것만 예외)
    """
    수 = r"(?:[+\-−])?\d[\d,.]*"
    단 = r"(?:%p|%|σ|억|조|원|거래일|일|분|번|해|종목|개|년)?"
    조 = r"(?:이상|이하|까지|부터|으로|로|에서|에|의|가|이|은|는|을|를|와|과|만)?"
    짝 = rf"{수}%?\s*(?:→|->)\s*{수}%?(?:으로|로)?"
    범 = rf"{수}{단}~{수}{단}{조}"          # 300억~2,000억
    홀 = rf"{수}(?::\d\d)?{단}{조}"
    re_ = re.compile(rf"({짝}|{범}|{홀})")
    색s = f";color:{색}" if 색 else f";color:{C['먹']}"
    out, last = [], 0
    for m in re_.finditer(글):
        if m.start() > last:
            out.append(_esc(글[last:m.start()]))
        out.append(f'<b style="font-weight:800{색s};white-space:nowrap">'
                   f'{_esc(m.group(0))}</b>')
        last = m.end()
    out.append(_esc(글[last:]))
    return "".join(out)


def _괄호nowrap(html_):
    """괄호 문구는 통째로 nowrap (5절) — 가운뎃점으로 줄이 시작하면 안 된다"""
    return re.sub(r"\([^()<>]{2,40}\)",
                  lambda m: f'<span style="white-space:nowrap">{m.group(0)}</span>', html_)


def _업종표():
    try:
        return json.load(io.open(os.path.join(_DATA, "industry.json"), encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def _사례():
    p = os.path.join(_DATA, "rule-cases.json")
    try:
        return json.load(io.open(p, encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def _계좌낙폭():
    """계좌 낙폭은 **자료에서 읽는다** — 손으로 적으면 낡는다"""
    옛, 새 = -9.0, -3.3
    try:
        cp = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8-sig"))
        새 = cp.get("계좌낙폭", 새)
        옛 = (cp.get("옛값_참고") or {}).get("계좌낙폭", 옛)
    except Exception:  # noqa: BLE001
        pass
    return 옛, 새


def _선택지(앞, 뒤):
    """3장 「목표에 닿으면」 아래 한 줄 — 지금 비율과 **다른 비율이면 어떻게 되나** (2026-09-14 저녁).

    사용자: 「매도 타이밍이 선택지를 주는 건 좋은 것 같은데」
    ⚠️ 아침에 고르는 게 아니다 — 규칙은 하나(`rule_def.몫들`)고, 이 줄은 **한 번 정할 때** 보는 것.
       비율을 바꾸면 이 줄이 스스로 뒤집힌다 (지금 규칙 = 자료에서 R.몫들 과 맞는 안)
    ⚠️ 숫자는 `data/sell-options.json`(build_sell_options.py ← 시험 결과)에서 읽는다. 손으로 안 적는다.
       자료가 없거나 지금 비율이 표에 없으면 **줄을 뺀다** (지어내지 않는다)
    """
    try:
        s = json.load(io.open(os.path.join(_DATA, "sell-options.json"), encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return []
    안들 = s.get("안들") or []
    지금 = next((a for a in 안들 if abs(a["앞"] - 앞[0]) < 1e-9 and abs(a["뒤"] - 뒤[0]) < 1e-9), None)
    if not 지금:
        return []
    다른 = [a for a in 안들 if a is not 지금]
    if not 다른:
        return []
    # 돈이 가장 많은 다른 안 하나만 — 줄이 길어지면 3장이 넘친다
    a = max(다른, key=lambda z: z["돈억"])
    def 비(x):
        # 디자인 덧(2026-09-14): 「40%:60%」는 수치로 읽힌다 — 비율은 「40:60」
        return f"{x['앞'] * 100:g}:{x['뒤'] * 100:g}"
    # ⚠️ 브리핑 전체에서 「—」는 안 쓴다 · 마이너스는 「−」(U+2212)
    def 낙(x):
        return f"{x['낙폭오차']:g}%".replace("-", "−")
    # ⚠️ 31px 세 줄로 넣으니 3장 아래여백이 4px 로 바닥에 붙었다 (2026-09-14 실측).
    #    각주 크기(25px · 보조색)로 두 줄 — 숫자는 _굵 이 굵게 만든다
    말 = (f"지금 {비(지금)}은 {지금['돈억']:g}억 · 낙폭 {낙(지금)}. "
         f"{비(a)}이면 {a['돈억']:g}억 · {낙(a)}"
         + ("로 더 벌고 더 흔들립니다." if a["돈억"] > 지금["돈억"] else "로 덜 벌고 덜 흔들립니다.")
         + " 규칙은 하나로 둡니다.")
    return [(말, 25)]


# ── 카드 틀 (0절 공통) ───────────────────────────────────────────
def _킥커(글, 쪽):
    return (f'<div style="display:flex;align-items:center;gap:16px">'
            f'<span style="flex:none;font-size:25px;font-weight:700;color:{C["금"]};'
            f'letter-spacing:.1em">{글}</span>'
            f'<span style="flex:1;height:1px;background:{C["선"]}"></span>'
            f'<span style="flex:none;font-size:25px;font-weight:700;color:{C["보"]}">'
            f'{쪽}</span></div>')


def _머리(킥커, 쪽, 제목, 크기=64, 부제=None, 배지=None, 배지색=None, 틈=20, 밑=30):
    제 = (f'<span style="flex:1;min-width:0;font-size:{크기}px;font-weight:800;'
          f'line-height:1.2;letter-spacing:-.045em">{제목}</span>')
    if 배지:
        제 = (f'<div style="display:flex;align-items:flex-end;gap:20px">{제}'
              f'<span style="flex:none;font-size:28px;font-weight:700;color:{배지색};'
              f'white-space:nowrap;padding-bottom:10px">{_esc(배지)}</span></div>')
    부 = (f'<span style="font-size:35px;line-height:1.5;color:{C["보"]}">{부제}</span>'
          if 부제 else "")
    return (f'<div style="flex:none;display:flex;flex-direction:column;gap:{틈}px;'
            f'padding-bottom:{밑}px">{_킥커(킥커, 쪽)}{제}{부}</div>')


def _카드(라벨, 머리, 몸, 패딩="10px 16px", 틈=None):
    """1080×1350 · padding 80 · overflow hidden. 본문은 flex:1 · space-between."""
    g = f"gap:{틈}px;" if 틈 else ""
    return (f'<section data-label="{라벨}" '
            f'style="width:{CARD_W}px;height:{CARD_H}px;background:{C["카드"]};'
            f'border-radius:26px;box-sizing:border-box;padding:80px;overflow:hidden;'
            f'font-family:{SANS};color:{C["먹"]};display:flex;flex-direction:column;'
            f'font-feature-settings:\'tnum\';letter-spacing:-.01em;word-break:keep-all">'
            f'{머리}'
            f'<div data-body="1" style="flex:1;display:flex;flex-direction:column;'
            f'justify-content:space-between;{g}min-height:0;padding:{패딩}">{몸}</div>'
            f'</section>')


def _블록(라벨, 속, 틈=11):
    """2·3·4장 항목 — 첫 항목 외 border-top (호출자가 첫 항목엔 선을 안 준다)"""
    return (f'<div style="display:flex;flex-direction:column;gap:{틈}px;'
            f'border-top:1px solid {C["선"]};padding-top:18px">'
            f'<span style="font-size:26px;font-weight:700;color:{C["금"]}">{라벨}</span>'
            f'{속}</div>')


def _본문(html_, 크기=31, 줄=1.55, 색=None):
    return (f'<span style="font-size:{크기}px;line-height:{줄};color:{색 or C["본"]}">'
            f'{html_}</span>')


# ── 1장 · 종목 ───────────────────────────────────────────────────
def _딱지(x):
    """걸린 규칙 — 시장·낙폭·섹터가 **동시에** 붙는다 (정본 rows)"""
    t = []
    if x.get("시장규칙"):
        t.append("시장")
    if x.get("기존규칙"):
        t.append("낙폭")
    if x.get("섹터규칙"):
        t.append("섹터")
    return " · ".join(t)


def _줄1(x, 업종, 확정):
    갭 = ""
    if 확정 and x.get("상대갭") is not None:
        갭 = (f'<span style="flex:none;margin-left:auto;font-size:23px;color:{C["보"]};'
              f'white-space:nowrap">상대갭 {_esc(_음(x["상대갭"], 2, "%p"))}</span>')
    낙자리 = "flex:none;font-size:24px;color:%s;white-space:nowrap" % C["보"]
    if not 갭:
        낙자리 = "flex:none;margin-left:auto;" + 낙자리[len("flex:none;"):]
    낙 = x.get("20일낙폭")
    낙글 = _esc(_음(낙, 1)) if 낙 is not None else "—"
    return (f'<div style="display:flex;align-items:baseline;gap:13px">'
            f'<span style="flex:none;font-size:34px;font-weight:700;letter-spacing:-.02em;'
            f'white-space:nowrap">{_esc(x.get("이름", ""))}</span>'
            + (f'<span style="flex:none;font-size:26px;font-weight:700;color:{C["본"]};'
               f'white-space:nowrap">{_esc(업종)}</span>' if 업종 else "")
            + f'<span style="flex:none;font-size:23px;color:{C["보"]};white-space:nowrap">'
              f'{_esc(x.get("종목코드", ""))}</span>'
            + 갭
            + f'<span style="{낙자리}">20일 낙폭 <b style="font-weight:800;font-size:32px;'
              f'color:{C["빨"]}">{낙글}</b></span></div>')


def _줄2(x):
    def 칸(라, 값):
        return (f'<span style="flex:none;font-size:23px;color:{C["보"]};white-space:nowrap">'
                f'{라} <b style="font-weight:800;font-size:26px;color:{C["먹"]}">{값}</b></span>')
    잉 = x.get("잉여금비율")
    부 = x.get("부채비율")
    칸들 = [칸("전날 종가", f'{x.get("어제종가", 0):,}원'),
           칸("시총", f'{x.get("시총억", 0):,}억')]
    if 잉 is not None:
        칸들.append(칸("이익", f"{잉:.0f}%"))
    if 부 is not None:
        칸들.append(칸("빚", f"{부:.0f}%"))
    딱 = _딱지(x)
    if 딱:
        칸들.append(f'<span style="flex:none;margin-left:auto;font-size:22px;font-weight:700;'
                   f'color:{C["금"]};background:{C["딱"]};border-radius:6px;padding:3px 11px;'
                   f'white-space:nowrap">{_esc(딱)}</span>')
    return ('<div style="display:flex;align-items:baseline;gap:18px">'
            + "".join(칸들) + '</div>')


def _줄3(x, 상태):
    """셋째 줄 — 상태별 (QUANT-FINAL 1절 표 · QUANT-Q1-ORDER-COLUMN 답 「둘 다」)"""
    if 상태 == "pre":
        a, b = R.매수범위(x.get("어제종가", 0) or 0)
        라, 값, 보, 칩, 칩색 = ("매수 적정 범위", f"{a:,}~{b:,}원",
                              f"전날 종가 −{abs(R.상대갭문턱):g}%p", "주문 전", C["보"])
    else:
        문 = x.get("문턱가")
        값 = f"{문:,}원" if 문 else "—"
        라 = "문턱가 · 이 값 아래여야 산다"
        if 상태 == "buy":
            주 = x.get("주문가")
            보, 칩, 칩색 = (f"주문가 {주:,}원" if 주 else "주문가 —"), "지정가 주문", C["빨"]
        else:
            보 = "넘겨서 안 샀습니다" if 문 else "예상체결가를 못 받았습니다"
            칩, 칩색 = "안 산다", C["보"]
    return (f'<div style="display:flex;align-items:baseline;gap:12px;'
            f'border-top:1px solid {C["선"]};padding-top:11px">'
            f'<span style="flex:none;font-size:23px;font-weight:700;color:{C["금"]};'
            f'white-space:nowrap">{라}</span>'
            f'<span style="flex:none;font-size:29px;font-weight:800;letter-spacing:-.03em;'
            f'color:{C["먹"]};white-space:nowrap">{_esc(값)}</span>'
            f'<span style="flex:1;min-width:0;font-size:21px;color:{C["보"]};'
            f'white-space:nowrap;overflow:hidden;text-overflow:clip">{_esc(보)}</span>'
            f'<span style="flex:none;font-size:24px;font-weight:700;color:{칩색}">{칩}</span>'
            f'</div>')


def _종목블록(x, 업종, 상태, 확정):
    return (f'<div data-block="1" style="background:{C["블록"]};border:1px solid {C["선"]};'
            f'border-radius:16px;padding:14px 22px;display:flex;flex-direction:column;'
            f'gap:10px">{_줄1(x, 업종, 확정)}{_줄2(x)}{_줄3(x, 상태)}</div>')


def _장1(q, 보유):
    후보 = q.get("후보") or []
    동 = q.get("동시호가") or {}
    확정 = 동.get("예상시장갭") is not None
    최대 = R.하루최대종목
    살것 = [x for x in 후보 if x.get("규칙매수")][:최대] if 확정 else []
    if 살것:
        상태 = "buy"
    elif 확정:
        상태 = "wait"
    else:
        상태 = "pre"
    if not 후보:
        상태 = "none"

    # 목록 — 사는 날은 실제 매수 종목 · 안 사는 날은 **갭이 깊은 순** 4개 (정본)
    #        08:55 전에는 갭이 없으니 08:00 후보 차례 그대로
    if 상태 == "buy":
        목록 = 살것
    elif 상태 == "wait":
        목록 = sorted([x for x in 후보 if x.get("상대갭") is not None],
                    key=lambda z: z["상대갭"])
        목록 += [x for x in 후보 if x.get("상대갭") is None]
        목록 = 목록[:최대]
    else:
        목록 = 후보[:최대]
    n, 전체 = len(목록), len(후보)
    업 = _업종표()

    # 머리 (정본 states)
    if 상태 == "pre":
        킥, 제, 배, 배색 = "QUANT · 08:00 후보", f"오늘 볼 종목 {n}", "매수 적정 범위", C["금"]
        리드 = (f"{R.판정시각}에 예상체결가를 보고 살지 정합니다. 그 전까지는 참고용 목록이고, "
              "아래 범위는 문턱가가 들어올 자리입니다.")
        라벨, 라벨색 = "아침에 볼 목록 · 아직 주문 아님", C["보"]
        각주 = (f"후보 {전체}종목 중 {n}개 · 열에 아홉 날 문턱가가 이 범위에 듭니다. "
              f"실제 값은 {R.판정시각}에 하나로 정해집니다.")
    elif 상태 == "wait":
        킥, 제, 배, 배색 = f"QUANT · {R.판정시각} 확정", "오늘 살 것: 없음", "안 산다", C["보"]
        리드 = (f"상대갭이 −{abs(R.상대갭문턱):g}%p까지 내려온 종목이 없었습니다. "
              "아무것도 사지 않는 것도 규칙대로 한 것입니다.")
        라벨, 라벨색 = "사지 않습니다 · 조건에 걸린 종목 (참고용)", C["보"]
        각주 = (f"후보 {전체}종목 중 갭이 깊은 순으로 {n}개 · 문턱가를 넘어 안 샀습니다."
              + (f" 나머지 {전체 - n}개는 상세에." if 전체 > n else ""))
    elif 상태 == "buy":
        킥, 제, 배, 배색 = (f"QUANT · {R.판정시각} 확정", f"오늘 살 것: {n}개",
                        f"지정가 주문 {n}", C["빨"])
        리드 = (f"상대갭이 −{abs(R.상대갭문턱):g}%p 아래로 내려간 종목만 삽니다. "
              f"갭이 깊은 순으로 최대 {최대}종목입니다.")
        라벨, 라벨색 = "살 종목 · 지정가 주문 대상", C["빨"]
        앞, 뒤 = R.몫들[0], R.몫들[1]
        각주 = (f"{_몫말(앞[0])} +{앞[1]:g}%에, {_몫말(뒤[0], 뒤=True)} +{뒤[1]:g}%에 파는 "
              "지정가를 같이 걸어 둡니다 · 09:01에 체결 안 된 주문은 반드시 취소하세요.")
    else:
        킥, 제, 배, 배색 = (f"QUANT · {R.판정시각} 확정" if 확정 else "QUANT · 08:00 후보",
                        "오늘 볼 것 없음", "후보 0", C["보"])
        리드, 라벨, 라벨색 = "", "", C["보"]
        각주 = "규칙을 낮춰 억지로 후보를 만들지 않습니다. 다음 장에 어떤 조건으로 걸러내는지 있습니다."

    # 정리 알림 — 들고 있는 것의 기한이 찼다 (돈이 걸린 자리라 모든 상태에서 띄운다)
    팔것 = [x for x in 보유 if x.get("앞남은날") is not None and x["앞남은날"] <= 0
           and (x.get("뒤남은날") or 99) > 0]
    뒤팔것 = [x for x in 보유 if x.get("뒤남은날") is not None and x["뒤남은날"] <= 0]
    알림 = ""
    if 팔것 or 뒤팔것:
        말 = []
        if 팔것:
            말.append(f"오늘 반만 정리: {' · '.join(_esc(x.get('이름', '')) for x in 팔것)} · "
                     f"{R.앞몫기한}거래일이 지났습니다. {_몫말(R.몫들[0][0], 앞뒤=True)[:-1]}만 "
                     f"정리하고 {_몫말(R.몫들[1][0], 뒤=True)} +{R.뒷몫목표:g}%까지 기다립니다.")
        if 뒤팔것:
            말.append(f"오늘 나머지 정리: {' · '.join(_esc(x.get('이름', '')) for x in 뒤팔것)} · "
                     f"{R.뒷몫기한}거래일이 지났습니다.")
        알림 = (f'<div style="border-left:9px solid {C["빨"]};background:{C["경고"]};'
              f'border-radius:16px;padding:14px 24px;font-size:26px;line-height:1.5;'
              f'color:{C["먹"]}">{" ".join(말)}</div>')

    부 = [알림] if 알림 else []
    if 리드:
        부.append(_본문(_esc(리드), 35))
    if 상태 == "none":
        부.append(f'<div style="display:flex;flex-direction:column;gap:18px">'
                 f'<span style="font-size:96px;font-weight:800;letter-spacing:-.05em;'
                 f'line-height:1.15;color:{C["금"]}">0개</span>'
                 f'<span style="font-size:31px;line-height:1.6;color:{C["본"]}">조건을 통과한 '
                 f'종목이 없습니다. 규칙상 이런 날은 열흘에 세 번쯤 있습니다. 고장이 아닙니다.'
                 f'</span></div>')
        for 글 in (f"후보가 되려면 먼저 이걸 모두 통과해야 합니다 · 쌓은 이익 {R.잉여금하한:g}% 이상 · "
                  f"빚 {R.부채상한:g}% 이하 · 작년 순이익 흑자 · 시가총액 {R.시총하한억:,.0f}억~"
                  f"{R.시총상한억:,.0f}억 · 하루 거래 {R.대금하한억:g}억 이상"
                  + (" (섹터 규칙에 걸린 종목은 시총 상한 없음)" if R.섹터규칙_큰회사 else "") + ".",
                  "그 다음 낙폭 · 섹터 · 시장 셋 중 하나에 걸려야 합니다. 오늘은 어느 것도 "
                  "걸리지 않았습니다."
                  + (f" 들고 있는 것 {len(보유)}개에는 +{R.앞몫목표:g}% · +{R.뒷몫목표:g}% "
                     f"지정가가 걸려 있습니다." if 보유 else "")):
            부.append(f'<div style="font-size:33px;line-height:1.55;color:{C["본"]};'
                     f'border-top:1px solid {C["선"]};padding-top:18px">{_esc(글)}</div>')
    else:
        블록들 = "".join(_종목블록(x, (업.get(x.get("종목코드", "")) or {}).get("업종명")
                              or (x.get("섹터") or ""), 상태, 확정) for x in 목록)
        부.append(f'<div style="display:flex;flex-direction:column;gap:12px">'
                 f'<span style="font-size:27px;font-weight:700;color:{라벨색}">{_esc(라벨)}</span>'
                 f'{블록들}</div>')
    부.append(f'<div style="font-size:25px;line-height:1.55;color:{C["보"]}">{_esc(각주)}</div>')

    머리 = _머리(킥, "1 / 4", _esc(제), 크기=68, 배지=배, 배지색=배색, 틈=24, 밑=32)
    return _카드("퀀트1 종목", 머리, "".join(부), 패딩="12px 18px",
              틈=40 if 상태 == "none" else None)


# ── 2장 · 어떻게 뽑았나 (딱지 한 줄형) ───────────────────────────
def _장2():
    리드 = ("번 돈을 착실히 쌓아온 작은 회사가 회사 사정과 상관없이 크게 빠진 날을 찾습니다. "
          "재무제표와 주가만 보는 기계 규칙이라 브리핑과 종목이 다른 것이 정상입니다.")
    통과 = (f"자기 돈의 {R.잉여금하한:g}% 이상이 벌어서 쌓은 이익 · 빚은 {R.부채상한:g}% 이하 · "
          f"작년 순이익 흑자 · 시가총액 {R.시총하한억:,.0f}억~{R.시총상한억:,.0f}억 · "
          f"하루 거래 {R.대금하한억:g}억 이상 (관리종목·우선주·스팩 제외"
          + (" · 섹터 규칙에 걸린 종목은 시총 상한 없음" if R.섹터규칙_큰회사 else "") + ")")
    규칙 = (
        ("낙폭", f"20거래일 동안 {abs(R.낙폭20문턱):g}% 넘게 빠졌고, 값이 평소 움직이던 폭의 "
                f"아래쪽(볼린저 −{abs(R.볼린저문턱):g}σ)에 있다"),
        ("섹터", f"방산·원전·반도체 등 {len(R.섹터규칙)}개 업종은 업종마다 다른 기준을 쓴다. "
                "잘 빠지는 업종은 더 많이 빠져야 걸린다"),
        ("시장", f"지수가 눌려 있는 날(20일 −{abs(R.지수낙20문턱):g}% · 60일 −{abs(R.지수낙60문턱):g}%)"
                f"에는 조금만 빠져도 걸린다 (볼린저 −{abs(R.시장볼문턱):g}σ · "
                f"20일 −{abs(R.시장낙20문턱):g}% · 60일 −{abs(R.시장낙60문턱):g}%)"),
    )
    칩 = (f'flex:none;font-size:26px;font-weight:700;white-space:nowrap;border-radius:7px;'
         f'padding:5px 15px;color:{C["금"]};background:{C["딱"]}')
    줄들 = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:16px">'
        f'<div style="display:flex;align-items:center;gap:12px;flex:none;padding-top:4px">'
        f'<span style="{칩}">{태}</span></div>'
        f'{_본문(_괄호nowrap(_굵(글)))}</div>'
        for 태, 글 in 규칙)
    몸 = (_본문(_esc(리드), 35)
         + _블록("먼저, 이걸 모두 통과", _본문(_괄호nowrap(_굵(통과))))
         + _블록("그 다음, 셋 중 하나만 맞으면 후보 · 1장 딱지가 이것입니다", 줄들, 틈=14)
         + f'<span style="font-size:25px;line-height:1.55;color:{C["보"]}">여러 규칙에 걸린 종목이 '
           f'1장 위쪽에 옵니다. 다음 장은 언제 사고 언제 파는지입니다.</span>')
    return _카드("퀀트2 어떻게뽑았나", _머리("HOW THEY WERE PICKED", "2 / 4", "어떻게 뽑았나"), 몸)


# ── 3장 · 어떻게 사고 파나 (라벨 2열형) ──────────────────────────
def _장3():
    옛낙, 새낙 = _계좌낙폭()
    앞, 뒤 = R.몫들[0], R.몫들[1]
    # ⭐ 몫 이름과 조사는 `_몫말` 이 정한다 — 50:50 「반은/나머지 반은」, 그 밖엔 「30%는/나머지 70%는」
    블록 = (
        ("어떻게 사나",
         [f"{R.판정시각}에 5분, 여기서 살지 정해진다. 후보들의 예상체결가를 보고, 그 값들의 중앙값보다 "
          f"{abs(R.상대갭문턱):g}%p 더 빠진 것만 최대 {R.하루최대종목}종목 지정가로 삽니다.",
          f"예상체결가가 전날보다 {abs(R.예상갭하한):g}% 넘게 빠진 종목은 사지 않습니다. 호가가 얇아 나온 가짜 값이거나 "
          f"진짜 폭락이거나, 둘 다 살 이유가 아닙니다.",
          "09:01에 체결 안 된 주문은 반드시 취소하세요. 맞는 게 없으면 아무것도 사지 않습니다."]),
        ("목표에 닿으면 · 둘로 나눠 판다",
         [f"한 종목을 사면 주문을 둘로 나눠 겁니다. 산 주식의 {_몫말(앞[0])} +{앞[1]:g}%에 팔아 이익을 "
          f"일찍 챙기고, {_몫말(뒤[0], 뒤=True)} +{뒤[1]:g}%까지 기다립니다.",
          f"나눠 팔면 계좌 흔들림이 {abs(옛낙):.1f}% → {abs(새낙):.1f}%로 줄었습니다."]),
        ("목표에 안 닿으면 · 날짜로 끝낸다",
         [f"{_몫말(앞[0], 앞뒤=True)} {앞[2]}거래일, {_몫말(뒤[0], 뒤=True, 앞뒤=True)} {뒤[2]}거래일이 "
          f"지나면 그날 값으로 정리합니다.",
          "손절은 하지 않습니다. 값이 빠졌다는 이유로 중간에 팔지 않습니다."]),
    )
    행 = "".join(
        f'<div style="display:flex;gap:28px;border-top:1px solid {C["선"]};padding-top:18px">'
        f'<span style="flex:none;width:210px;text-align:right;font-size:26px;font-weight:700;'
        f'line-height:1.35;color:{C["금"]}">{라}</span>'
        f'<div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:9px;'
        f'border-left:1px solid {C["선"]};padding-left:28px">'
        # 줄은 글(31px 본문) 또는 (글, 크기) — 크기가 오면 보조색 각주 꼴 (비교 줄)
        + "".join(_본문(_괄호nowrap(_굵(x)))
                  if isinstance(x, str) else
                  _본문(_괄호nowrap(_굵(x[0])), x[1], 1.5, C["보"])
                  for x in 줄들) + '</div></div>'
        for 라, 줄들 in 블록)
    # ⭐ 비교 줄은 **블록 밖 · 세 블록 다 끝난 뒤** (디자인 답 2 · 2026-09-14).
    #    「목표에 닿으면」 안에 두면 그 블록만 규칙이 둘인 것처럼 보인다. 각주 계단(25px 보조색)
    비교 = "".join(_본문(_괄호nowrap(_굵(x[0])), x[1], 1.5, C["보"]) for x in _선택지(앞, 뒤))
    몸 = (_본문(_esc("규칙이 정하는 것은 언제 사고 언제 파는지 둘뿐입니다. 얼마를 넣을지는 정하지 않습니다."), 35)
         + 행
         + 비교
         + f'<span style="font-size:24px;line-height:1.55;color:{C["보"]}">다음 장은 이 규칙이 '
           f'과거에 어땠는지입니다.</span>')
    return _카드("퀀트3 사고파나", _머리("HOW TO BUY &amp; SELL", "3 / 4", "어떻게 사고 파나"), 몸)


# ── 4장 · 과거에 어땠나 ─────────────────────────────────────────
def _수익색(v):
    return C["빨"] if (v or 0) >= 0 else C["파"]


def _장4():
    s = _사례()
    기간 = str(s.get("기간") or "")
    년 = re.findall(r"(\d{4})-", 기간)
    부제 = f"{년[0]}년부터 {년[-1]}년까지" if len(년) >= 2 else 기간
    평균, 나쁨 = s.get("평균", 0) or 0, s.get("가장나쁨", 0) or 0

    def 강(v, 색=None):
        return (f'<b style="font-weight:800;color:{색 or C["먹"]};white-space:nowrap">'
                f'{_esc(v)}</b>')

    요약 = (_본문(f'모두 {강(f"{s.get("전체건수", 0)}번")} 샀고 그중 {강(f"{s.get("승률", 0)}%")}가 '
               f'수익이었습니다.')
          + _본문(f'평균 {강(_음(평균, 1), C["빨"])}를 {강(f"{s.get("평균보유", 0):.0f}일")} 만에 냈고, '
                f'최악은 {강(_음(나쁨, 1), C["파"])}였습니다.'))

    # 최근 3건 — 열 폭 200 · flex(min 240) · 120 · 130 · 90 · gap 14
    def 셀(글, 폭, 크기, 색, 굵=None, 오른=False, 늘=False):
        st = (f'flex:1;min-width:{폭}px' if 늘 else f'flex:none;width:{폭}px')
        return (f'<span style="{st};font-size:{크기}px;color:{색};'
                f'{"font-weight:%d;" % 굵 if 굵 else ""}{"text-align:right;" if 오른 else ""}'
                f'white-space:nowrap">{_esc(글)}</span>')
    머리행 = ('<div style="display:flex;align-items:baseline;gap:14px;white-space:nowrap;'
            f'padding-bottom:9px;border-bottom:1px solid {C["선"]}">'
            + 셀("날짜", 200, 24, C["보"]) + 셀("종목", 240, 24, C["보"], 늘=True)
            + 셀("산 값", 120, 24, C["보"], 오른=True) + 셀("수익률", 130, 24, C["보"], 오른=True)
            + 셀("며칠", 90, 24, C["보"], 오른=True) + '</div>')
    행들 = ""
    for r in (s.get("최근") or [])[:3]:
        결 = r.get("결과")
        행들 += ('<div style="display:flex;align-items:baseline;gap:14px;white-space:nowrap;'
               f'padding:9px 0;border-bottom:1px solid {C["선"]}">'
               + 셀(r.get("날짜", ""), 200, 26, C["보"])
               + 셀(r.get("이름", ""), 240, 31, C["먹"], 굵=700, 늘=True)
               + 셀(f'{r.get("매수가", 0):,}원', 120, 26, C["본"], 오른=True)
               + 셀(_음(결, 1) if 결 is not None else "—", 130, 31, _수익색(결), 굵=800, 오른=True)
               + 셀(f'{r.get("며칠")}일' if r.get("며칠") is not None else "—", 90, 26, C["보"], 오른=True)
               + '</div>')
    표 = f'<div style="display:flex;flex-direction:column">{머리행}{행들}</div>'

    # 가장 좋았던 셋 — 코드가 채운다 (6절 1). 자료에 없으면 지어내지 않는다
    최고 = s.get("최고") or []
    if 최고:
        좋 = _본문(" · ".join(f'{_esc(r.get("이름", ""))} {강(_음(r.get("결과", 0), 1), C["빨"])} '
                          f'<span style="white-space:nowrap">({r.get("며칠")}일)</span>'
                          for r in 최고[:3]))
    else:
        좋 = _본문("코드 확인 뒤 채웁니다", 색=C["보"])
    # 가장 나빴던 셋 + 손실 거래 평균 (6절 2 — 있을 때만)
    나 = _본문(" · ".join(f'{_esc(r.get("이름", ""))} {강(_음(r.get("결과", 0), 1), C["파"])}'
                       for r in (s.get("최악") or [])[:3]))
    if s.get("손실평균") is not None and s.get("손실건수"):
        나 += _본문(f'손실로 끝난 {강(f"{s["손실건수"]}건")}의 평균은 '
                  f'{강(_음(s["손실평균"], 1), C["파"])}였습니다.')

    각주 = ("위 숫자는 전부 과거 자료로 계산한 것입니다. 「과거에 이랬다」이지 「앞으로 이럴 것」이 "
          "아닙니다. 실제로 산 기록은 오늘부터 쌓입니다. 매수 추천이 아닙니다. 판단과 책임은 "
          "본인에게 있습니다.")
    몸 = (_본문(_esc("이 규칙이 과거에 있었다면 이렇게 됐을 것입니다. 컴퓨터가 옛 주가로 계산한 것입니다."), 31, 1.6)
         + _블록("10년 남짓을 계산하면", 요약, 틈=10)
         + _블록("최근 3건", 표)
         + _블록("가장 좋았던 셋", 좋, 틈=10)
         + _블록("가장 나빴던 셋", 나, 틈=10)
         + f'<span style="font-size:25px;line-height:1.55;color:{C["보"]}">{_esc(각주)}</span>')
    return _카드("퀀트4 성적표", _머리("TRACK RECORD", "4 / 4", "과거에 어땠나", 부제=_esc(부제), 틈=18, 밑=28), 몸)


# ── 화면 ────────────────────────────────────────────────────────
def quant_view(q, 보유=None):
    """`build_site.quant_view` 가 여기로 넘긴다. `q` 는 forward-log 마지막 줄, `보유` 는 `_보유()`."""
    보유 = 보유 or []
    return (f'<section class="view" id="qt" hidden>'
            f'<div class="top"><div class="in">'
            f'<button class="tbtn" data-home type="button">← 처음</button>'
            f'<span class="now">퀀트 후보</span></div></div>'
            f'<div class="rail qrail" data-active="true">'
            + _장1(q, 보유) + _장2() + _장3() + _장4()
            + '</div>'
            f'<div style="text-align:center;font-size:13px;color:{C["보"]};padding:0 0 30px">'
            f'← 옆으로 넘겨서 보세요 →</div></section>')
