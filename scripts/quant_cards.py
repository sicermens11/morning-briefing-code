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
    # ⭐ QUANT-ANSWER-0929 ★ — 종목 상자 4행 표형 (정본 quant-box-source 맨 왼쪽 카드)
    "줄선": "#ece5d6",   # 행 사이 가는 선 (상자 테두리 #d5cec0 보다 옅다)
    "금진": "#8a6425",   # 행 라벨 · 문턱가 값 (금 #8a7038 보다 진하다)
}
_요일 = "월화수목금토일"

# ⭐⭐ **한 장에 담는 종목 수** (2026-09-29 · 크롬으로 실측)
#    블록에 숨 자리를 넣은 뒤 재보니
#      3개 ✅ 여유 · 4개 +42px(하한 90 에 48 모자람) · 5개 **-205px** · 8개 -644px
#    ⇒ **3개**. 그보다 많으면 장을 늘린다 (글을 줄이지 않는다)
#    ⚠️ 2026-09-29 아침에 6개를 그려 **190px 가 잘렸다.** 조판 검사는 「통과」라고 했다
# ⭐⭐⭐ 2026-09-29 (사용자 「8개라면 차라리 한페이지당 4개씩 낫겠는데?」)
#    3 -> 4. 8개면 **4+4 두 장**이다. 상자가 `flex:1` 로 자리를 나눠 먹으므로
#    3개일 때처럼 아래가 휑하지 않다
_한장에 = 4
# ⭐ 상자가 무한정 길어지지 않게. 한 장에 1~2개만 남는 날 우스꽝스러워진다
_상자최대 = 340
# ⭐⭐⭐ **글자 계단** (QUANT-FIX-0929 E + ANSWER 답 4) — 이 파일은 이 단만 쓴다
#    제목 68(1장) / 64(2~6장) · 부제 35 · 본문 31 · 라벨 26~28 ·
#    보조·각주 24~25 · 큰 수치 38~40 · **30 = 종목 상자 값**(ANSWER 답 4 에서 추가)
#    계단 밖으로 남긴 둘 (디자인이 「그대로」라고 답함):
#      · 13px  — 카드 **밖** 「← 옆으로 넘겨서 보세요 →」 (화면 안내지 카드가 아니다)
#      · 114px — 「0개」 카드의 큰 숫자 (일부러 크게 쓴 것)
#    ⚠️ 옛 `_줄1윗`·`_줄1아래` 는 상자를 4행 표형으로 갈아 끼우며 **아무도 안 쓴다** — 치웠다

# ⭐ **Q2 한 장에 담는 규칙 줄 수** (2026-09-29 · 실측)
#    Q2 는 143px 넘쳤다 (속 1,420 / 보이는 1,277). 업종 줄이 압도적으로 길다
#    ⚠️ 글을 줄이지 않는다 — 장을 늘린다
_장2에 = int(os.environ.get("QT2_MAX") or 3)


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


# ⭐ 눈에 안 보이는 글자 셋 — **글은 하나도 안 바뀐다. 끊을 자리만 바꾼다**
_NBSP = "\u00a0"   # 안 끊기는 칸
_WJ = "\u2060"     # 여기서 끊지 마라
_ZWSP = "\u200b"   # 여기서 끊어도 된다


def _점안끊김(html_):
    r"""**가운뎃점으로 줄이 시작하지 않게** 한다 (QUANT-FIX-0929 C · 검사 5).

    브라우저는 `·` 를 **뒷말에 붙여** 끊는다 — 그래서 `(관리종목·우선주` ↵ `·스팩`
    처럼 다음 줄이 `·` 로 시작했다. `·` 를 **앞말에 붙이면** 끊김이 `·` 뒤에서
    일어나 다음 줄이 낱말로 시작한다.

    ⚠️ 문서는 「괄호 전체를 nowrap」이라 했지만 그 괄호는 31px 로 약 845px 인데
       본문 칸은 약 748px 이다 — **통째로 묶으면 칸 밖으로 나간다.**
       막으려는 것(·로 시작하는 줄)은 이 방법으로 똑같이 막힌다
       [[layout-never-cuts-content]]
    ⚠️ 글자는 **하나도 안 바뀐다.** 눈에 안 보이는 끊김 표시만 넣는다
    """
    html_ = html_.replace(" ·", _NBSP + "·")
    return re.sub(r"(?<![\s" + _NBSP + r"])·", _WJ + "·" + _ZWSP, html_)


def _홀글자묶음(html_):
    r"""**한 글자 낱말**을 뒷말에 붙인다 (QUANT-FIX-0929 C · 3장 「잘 빠지는」).

    `다른 기준을 쓴다. 잘` ↵ `빠지는` — 한 글자가 줄 끝에 혼자 남았다.
    한글 한 글자 + 칸 + 한글 을 **안 끊기는 칸**으로 잇는다 (글자는 그대로).
    """
    return re.sub(r"(?<=[\s>])([가-힣])\s(?=[가-힣])", r"\1" + _NBSP, html_)


def _괄호nowrap(html_):
    r"""괄호 문구는 통째로 nowrap (5절) — **뒤 조사까지** 한 묶음.

    ⭐ QUANT-FIX-0929 C — `왜 빠졌는지(회사` ↵ `사정)는` 이 나왔다.
       괄호만 묶으면 뒤 조사가 떨어진다. 조사까지 넣는다.
    ⚠️ 40자 한계는 그대로 둔다 — 더 긴 괄호를 묶으면 칸 밖으로 나간다
       (`_점안끊김` 이 그쪽을 맡는다)
    """
    _조 = r"(?:는|은|을|를|이|가|에|의|로|으로|와|과|도|만|에서|까지|부터)?"
    return re.sub(r"\([^()<>]{2,40}\)" + _조,
                  lambda m: f'<span style="white-space:nowrap">{m.group(0)}</span>', html_)


def _묶음(html_):
    """C 의 셋을 한 번에 — 괄호·가운뎃점·한 글자 낱말"""
    return _홀글자묶음(_점안끊김(_괄호nowrap(html_)))


def _파는말():
    r"""악재 매도 공시 말 — `bad_news_check._파는말` 을 **읽기만** 한다 (2026-09-29 밤).

    ⚠️ 그 파일은 불러오면 **맨 위부터 돌고 끝에 `raise SystemExit`** 한다 — import 하면 안 된다.
       파일을 글로 읽어 `_파는말 = (…)` 한 줄만 꺼낸다. 못 읽으면 빈 것 (그러면 문장을 안 붙인다)
    """
    import ast as _ast
    try:
        _src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "bad_news_check.py"), encoding="utf-8-sig").read()
        for _n in _ast.parse(_src).body:
            if isinstance(_n, _ast.Assign) and any(getattr(t, "id", None) == "_파는말"
                                                   for t in _n.targets):
                return tuple(_ast.literal_eval(_n.value))
    except Exception:  # noqa: BLE001
        pass
    return ()


def _문턱글():
    r"""「−3.5%p · 업종 규칙 종목은 −1.5%p」 — 규칙 파일에서 (업종 문턱이 없으면 앞만)"""
    _업 = getattr(R, "업종전용상대갭", None)
    return (f"−{abs(R.상대갭문턱):g}%p"
            + (f" · 업종 규칙 종목은 −{abs(_업):g}%p" if (_업 is not None and getattr(R, "업종규칙_켬", False)) else "")
            # ⭐ 2026-09-30 — 원전 기자재 바구니 (rule_def.바구니전용)
            + "".join(f" · {n} 종목은 −{abs(v['상대갭']):g}%p"
                      for n, v in getattr(R, "바구니전용", {}).items()))


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


def _배수():
    r"""나눠 팔기가 11년 성적을 몇 배로 만드나. 자료에 없으면 None (그럼 옛 문장을 쓴다).

    ⚠️ 손으로 안 적는다 — `rule-capital.json` 에서 읽는다 ([[hand-written-numbers-freeze]])
    """
    try:
        cp = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8-sig"))
        v = cp.get("나눠팔기_배수")
        return float(v) if v and float(v) > 1.0 else None
    except Exception:  # noqa: BLE001
        return None


def _계좌낙폭():
    """계좌 낙폭은 **자료에서 읽는다** — 손으로 적으면 낡는다"""
    옛, 새 = -9.0, -3.3
    try:
        cp = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8-sig"))
        새 = cp.get("계좌낙폭", 새)
        옛 = (cp.get("옛값_참고") or {}).get("계좌낙폭", 옛)
        # ⭐ 10/2 사실 바로잡기 — 위 둘은 **산 값 기준**(팔 때만 손실 반영)이라 −6.3% 였는데 매일 종가로 보면 −38.9% 였다.
        #    CARDLIVE 가 「종가」 칸을 쓰면 그걸 쓴다 (사용자 「「사실 바로잡기(화면 문구)」 … 진행해.」)
        종 = cp.get("종가") or {}
        if 종.get("계좌낙폭") is not None and 종.get("옛값_계좌낙폭") is not None:
            옛, 새 = 종["옛값_계좌낙폭"], 종["계좌낙폭"]
    except Exception:  # noqa: BLE001
        pass
    return 옛, 새


def _종가기준():
    """화면 낙폭이 매일 종가 평가 값인가 (CARDLIVE 「종가」 칸이 있나) — 문구에 「매일 종가로 평가」 를 붙일지"""
    try:
        cp = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8-sig"))
        return bool((cp.get("종가") or {}).get("계좌낙폭") is not None)
    except Exception:  # noqa: BLE001
        return False


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
    # ⭐ 10/6 사용자 「퀀트 3장의 낙폭 숫자는 사실대로 적어야지.」 — 위 본문은 **오차 없는 매일 종가** 값(−38.9%)인데
    #    이 줄은 08:55 예상가 오차를 넣은 나쁜 경우(−45.2%)라 같은 규칙에 기준이 다른 숫자가 둘 찍혔다.
    #    ⇒ 같은 기준(「낙폭종가」)이 있으면 그것 · 없으면(CARDLIVE 다시 돌기 전) 오차 값에 **「예상가 오차 넣고」 를 붙인다**
    _같은기준 = all(x.get("낙폭종가") is not None for x in 안들)
    def 낙(x):
        if _같은기준:
            return f"{x['낙폭종가']:g}%".replace("-", "−")
        v = x.get("낙폭종가오차", x["낙폭오차"])
        return f"{v:g}%".replace("-", "−") + ("(예상가 오차 넣고)" if "낙폭종가오차" in x else "")
    # ⚠️ 31px 세 줄로 넣으니 3장 아래여백이 4px 로 바닥에 붙었다 (2026-09-14 실측).
    #    각주 크기(25px · 보조색)로 두 줄 — 숫자는 _굵 이 굵게 만든다
    # ⭐⭐⭐ QUANT-FIX-0929 F — **두 줄로 나누고 앞말을 붙인다.**
    #    전에는 한 줄에 25px 로 숫자가 여섯이라 뜻이 안 읽혔다
    #    (`지금 40:60은 111.4억 · 낙폭 −8.9%. 30:70이면 149.3억 · −10.5%로 …`).
    #    ⚠️ 숫자는 그대로 `sell-options.json` 에서 읽는다 — 손으로 안 적는다
    # ⭐ QUANT-ANSWER-0929 답 6(b) — **기간 말을 뺐다.**
    #    문서 초안은 「11년에」였는데 재보니 시뮬은 **10.5년**이고
    #    (2016-05-19~2026-08-04 · 52.17배 · 연평균 45.77%),
    #    `sell-options.json` 에는 **기간 칸 자체가 없다.**
    #    자료에 없는 기간을 화면에 적지 않는다
    _말1 = (f"지금 비율({비(지금)}) · {지금['돈억']:g}억 · "
            f"가장 크게 빠질 때 {낙(지금)}")
    # ⚠️ 10/1 — 돈만 보고 「덜 벌고 덜 흔들립니다」를 골랐다. 같은 판으로 다시 재니 30:70 이 **덜 벌고 더 흔들린다**
    #    (2.97억 · −8.7% vs 지금 2.99억 · −7.6%) → 돈과 흔들림을 **따로** 견준다 (낙폭은 음수 — 더 작으면 더 흔들린다)
    # ⚠️ 10/4 — 2.96억 vs 2.97억(0.3%) · −45.1% vs −45.2%(0.1%p) 를 「덜 벌고 덜 흔들립니다」 라고 썼다 — 차이가 잡음 수준이면 「비슷」
    _k키 = "낙폭종가" if _같은기준 else "낙폭종가오차"
    _ka = a.get(_k키, a["낙폭오차"]); _kn = 지금.get(_k키, 지금["낙폭오차"])
    _돈같 = abs(a["돈억"] / 지금["돈억"] - 1) < 0.01 if 지금["돈억"] else False
    _흔같 = abs(_ka - _kn) < 0.5
    if _돈같 and _흔같:
        _말끝 = "벌이도 흔들림도 비슷합니다"
    else:
        _벌 = "벌이는 비슷하고" if _돈같 else ("더 벌고" if a["돈억"] > 지금["돈억"] else "덜 벌고")
        _흔 = "흔들림은 비슷합니다" if _흔같 else ("더 흔들립니다" if _ka < _kn else "덜 흔들립니다")
        _말끝 = f"{_벌} {_흔}"
    _말2 = f"{비(a)}로 바꾸면 · {a['돈억']:g}억 · {낙(a)} · {_말끝}"
    return [(_말1, 25), (_말2, 25)]


# ── 카드 틀 (0절 공통) ───────────────────────────────────────────
# ⭐⭐⭐ QUANT-FIX-0929 A — **쪽 번호 자리표시는 하나뿐이다.**
#    전에는 장마다 제 번호를 셈해 넣었는데(Q2 는 「Q1 이 한 장」이라 치고 +2),
#    Q1 이 두 장이 되자 자리표시와 실제 번호가 어긋나 **「2 / %d」가 그대로 찍혔다.**
#    셈은 `_쪽번호매기기` 한 곳에서만 한다 [[hand-written-numbers-freeze]]
_쪽표 = "@@PAGE@@"


def _킥커(글, 쪽):
    return (f'<div style="display:flex;align-items:center;gap:16px">'
            f'<span style="flex:none;font-size:28px;font-weight:700;color:{C["금"]};'
            f'letter-spacing:.1em">{글}</span>'
            f'<span style="flex:1;height:1px;background:{C["선"]}"></span>'
            f'<span style="flex:none;font-size:28px;font-weight:700;color:{C["보"]}">'
            f'{쪽}</span></div>')


def _머리(킥커, 쪽, 제목, 크기=64, 부제=None, 배지=None, 배지색=None, 틈=20, 밑=30, 제목높이=None):
    제 = (f'<span style="flex:1;min-width:0;font-size:{크기}px;font-weight:800;'
          f'line-height:1.2;letter-spacing:-.045em">{제목}</span>')
    if 배지:
        제 = (f'<div style="display:flex;align-items:flex-end;gap:20px">{제}'
              f'<span style="flex:none;font-size:28px;font-weight:700;color:{배지색};'
              f'white-space:nowrap;padding-bottom:10px">{_esc(배지)}</span></div>')
    # ⭐ ANSWER-0929-4 — 여러 장을 **같은 높이로** 맞출 때 제목 줄 높이를 고정한다
    #    (1장 68px · 2장 64px 이라 그대로면 머리가 약 5px 다르다)
    if 제목높이:
        제 = (f'<div class="qtitleh" style="height:{제목높이}px;display:flex;flex-direction:column;'
              f'justify-content:flex-end">{제}</div>')
    부 = (f'<span style="font-size:35px;line-height:1.5;color:{C["보"]}">{부제}</span>'
          if 부제 else "")
    return (f'<div style="flex:none;display:flex;flex-direction:column;gap:{틈}px;'
            f'padding-bottom:{밑}px">{_킥커(킥커, 쪽)}{제}{부}</div>')


def _카드(라벨, 머리, 몸, 패딩="10px 16px", 틈=None, 정렬="flex-start"):
    # ⭐⭐⭐ QUANT-FIX-0929-2 ★ **빈 자리 규칙** — 모든 퀀트 카드: 위로 붙이고 남는 자리는 아래.
    #    항목 사이 **56px 고정** (종목 상자 장은 부르는 쪽이 40 을 준다). space-between 을 안 쓴다 —
    #    내용 적은 장은 항목 사이가 128~346px 로 벌어졌다
    r"""1080×1350 · padding 80 · overflow hidden. 본문은 flex:1 · space-between.

    ⭐ 2026-09-29 — `정렬="flex-start"` 면 **위로 붙인다**.
       사용자: 「야 이거 밸런스 맞아? 위치를 통일해야지」
       여러 장으로 나눈 뒤 장마다 내용 양이 달라져 `space-between` 이
       빈자리를 위아래로 벌려 놨다 (1장은 블록이 한참 아래, 3장은 각주가 바닥에 홀로).
       ⚠️ 꽉 찬 장(퀀트3·퀀트4)은 그대로 둔다 — 거긴 space-between 이 맞다
    """
    g = f"gap:{틈}px;" if 틈 else ""
    return (f'<section data-label="{라벨}" '
            f'style="width:{CARD_W}px;height:{CARD_H}px;background:{C["카드"]};'
            f'border-radius:26px;box-sizing:border-box;padding:80px;overflow:hidden;'
            f'font-family:{SANS};color:{C["먹"]};display:flex;flex-direction:column;'
            f'font-feature-settings:\'tnum\';letter-spacing:-.01em;word-break:keep-all">'
            f'{머리}'
            # ⭐⭐⭐ 2026-09-29 — `data-align` 표식. **화면 JS(`채움()`)가 내 정렬을
            #    덮어쓰고 있었다** — 조건 없이 `style.justifyContent` 를 다시 썼다.
            #    1장은 채움 72% 라 `space-between` 으로 되돌아가 상자가 216px 아래에서
            #    시작했다(2·3장은 62%·40% 라 flex-start 로 남아 283px 어긋났다).
            #    표식이 있으면 `채움()` 이 손대지 않는다
            f'<div data-body="1"' + (f' data-align="{정렬}"' if 정렬 else "")
            + f' style="flex:1;display:flex;flex-direction:column;'
            f'justify-content:{정렬 or "space-between"};'
            + (f'gap:{틈 or 56}px;' if 정렬 else g)
            + f'min-height:0;padding:{패딩}">{몸}</div>'
            f'</section>')


def _블록(라벨, 속, 틈=11):
    """2·3·4장 항목 — 첫 항목 외 border-top (호출자가 첫 항목엔 선을 안 준다)"""
    return (f'<div style="display:flex;flex-direction:column;gap:{틈}px;'
            f'border-top:1px solid {C["선"]};padding-top:18px">'
            f'<span style="font-size:28px;font-weight:700;color:{C["금"]}">{라벨}</span>'
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
    # ⭐ 2026-09-22 — 업종 규칙과 변동성·자사주도 딱지를 단다.
    #    규칙은 켜져 있는데 화면이 말을 안 해 주고 있었다
    if x.get("업종규칙"):
        t.append("업종")
    if x.get("변동성자사주"):
        t.append("변동성")
    # ⭐ 2026-10-12 B — 업종·섹터·규모 전용 규칙(사용자 10/7 「B 라벨 이름 너가 제안한대로 하자」)
    t.extend(x.get("B라벨") or [])
    # ⭐ 10/20 보완 후보 — 중형 · 대형(주의)
    if x.get("보완규칙"):
        t.append("대형 · 주의" if x["보완규칙"] == "대형" else x["보완규칙"])
    return " · ".join(t)


def _오늘왜(q, 목록):
    r"""오늘 왜 이 종목들인가 — 한 문단 (10/20 사용자 「지금 바로 넣자!」 ①). 그날 지수 낙폭과 갈래별 개수로만 만든다"""
    if not 목록:
        return ""
    낙 = ((q.get("국면") or {}).get("지수낙폭") or {})
    이름 = {"KOSPI": "코스피", "KOSDAQ": "코스닥"}
    앞 = []
    for k in ("KOSPI", "KOSDAQ"):
        v = 낙.get(k) or [None, None]
        if v[0] is not None and v[0] <= R.지수낙20문턱:
            앞.append(f"{이름[k]}가 20일 동안 {abs(v[0]):.0f}% 빠진 날")
        elif len(v) > 1 and v[1] is not None and v[1] <= R.지수낙60문턱:
            앞.append(f"{이름[k]}가 60일 동안 {abs(v[1]):.0f}% 빠진 날")
    # 10/20 — 길게 쓰면 갈래가 여럿인 날 PC 1장이 14~16px 넘쳤다(실측) → 짧은 말로(뜻은 같다)
    갈 = [("시장규칙", "같이 빠진 튼튼한 소형주", "시장"),
         ("기존규칙", "혼자 크게 빠진 종목", "낙폭"),
         ("섹터규칙", "정해 둔 업종에서 빠진 종목", "섹터"),
         ("변동성자사주", "흔들리는 장에 자사주를 산 회사", "변동성")]
    뒤 = [f"{말} {n}개({표})" for 키, 말, 표 in 갈 for n in [sum(1 for x in 목록 if x.get(키))] if n]
    if not 뒤:
        return ""
    return ((" · ".join(앞) + "입니다. " if 앞 else "") + " · ".join(뒤) + ".")


def _팔값(x):
    r"""주문가 기준 40%·60% 팔 값 (10/20 ②) — 주문가가 없으면(08:55 전) None"""
    주 = x.get("주문가")
    if not 주:
        return None
    return [round(주 * (1 + 몫[1] / 100)) for 몫 in R.몫들[:2]]


def _시험표():
    r"""「어떤 시험을 거쳤나」 줄들 (10/20 ③) — data/rule-tests.json · @건수·@분할 은 화면 숫자 파일에서 채운다"""
    try:
        t = json.load(io.open(os.path.join(_DATA, "rule-tests.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return [], ""
    s = _사례()
    out = []
    for z in t.get("줄") or []:
        값 = z.get("값", "")
        if 값 == "@건수":
            값 = f'{s.get("전체건수", 0)}번'
        elif 값 == "@분할":
            try:
                cap = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8"))
                연 = [float(d["연"]) for d in cap.get("분할") or [] if d.get("연") is not None]
                값 = f"연 {min(연):.0f}~{max(연):.0f}%" if 연 else "—"
            except Exception:  # noqa: BLE001
                값 = "—"
        out.append((z.get("이름", ""), 값, z.get("설명", "")))
    return out, str(t.get("시험날짜") or "")


def _장시험():
    r"""PC 「어떤 시험을 거쳤나」 장"""
    줄, 날 = _시험표()
    if not 줄:
        return []
    몸 = _본문("성적표 숫자를 그대로 믿어도 되는지, 넣기 전에 이렇게 확인했습니다.", 31)
    for 이, 값, 설 in 줄:
        몸 += (f'<div style="display:flex;flex-direction:column;gap:6px;border-top:1px solid {C["선"]};padding-top:16px">'
              f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:16px">'
              f'<span style="font-size:32px;font-weight:800">{_esc(이)}</span>'
              f'<span style="font-size:32px;font-weight:800;color:{C["금진"]};white-space:nowrap">{_esc(값)}</span></div>'
              f'<span style="font-size:26px;line-height:1.5;color:{C["본"]}">{_esc(설)}</span></div>')
    몸 += f'<span style="font-size:24px;color:{C["보"]}">시험 날짜 {_esc(날)} · 규칙이 바뀌면 다시 잽니다.</span>'
    return [_카드("퀀트 시험", _머리("TESTS", _쪽표, "어떤 시험을 거쳤나", 틈=18, 밑=28), 몸, 정렬=None)]


def _폰시험():
    r"""핸드폰 「어떤 시험을 거쳤나」 카드"""
    줄, 날 = _시험표()
    if not 줄:
        return []
    몸 = ('<p class="t">어떤 시험을 거쳤나</p><div class="notes">'
          + "".join(f'<div class="nt"><b>{_e(이)} · {_e(값)}</b><span>{_e(설)}</span></div>' for 이, 값, 설 in 줄)
          + f'</div><p class="note">시험 날짜 {_e(날)} · 규칙이 바뀌면 다시 잽니다.</p>')
    return [_폰카드("TESTS", 몸)]


def _보완자료(q):
    r"""보완 후보(10/20 · 사용자 「오케이 너의 권고대로 하자!」) — (목록, 상자 상태, 글들) · 없으면 목록 []"""
    목록 = list(q.get("보완후보") or [])
    if not 목록:
        return [], "wait", {}
    산 = [x for x in 목록 if x.get("오늘산다")]
    상태 = "buy" if 산 else "wait"       # 08:55 전에는 문턱가가 없다 → 「—」 · 「08:55 확정 뒤」
    문 = abs(getattr(R, "보완상대갭", -1.0))
    중lo, 중hi = R.보완중형["시총억"]
    글 = {
        "리드": (f"지금 규칙과 다른 방법으로 고른 종목입니다. 지금 규칙 주문과 따로, 그날 나온 것을 다 싣습니다. "
               f"시장보다 {문:g}%p 더 싸게 시작하는 값(문턱가)에 지정가를 걸고, 9시 시가가 그 값 이하일 때만 삽니다."
               + ("" if 산 else f" 문턱가는 {R.판정시각}에 정해집니다.")),
        "규칙": (f"중형 = 시가총액 {_억말(중lo)}~{_억말(중hi)} · 그 시장 지수가 20일 동안 {abs(R.보완중형['지수낙20']):g}% 넘게 빠진 날 · "
               f"대형 = {_억말(R.보완대형['시총억'][0])} 이상 · 그 종목이 40일 동안 {abs(R.보완대형['낙40']):g}% 넘게 빠졌을 때 · "
               "재무 조건은 지금 규칙과 같습니다."),
        "주의": ("대형은 크게 빠진 뒤 더 빠진 적이 있습니다(2023년 주가조작 폭락 때 −86%)."
               if any(x.get("보완규칙") == "대형" for x in 목록) else ""),
    }
    return 목록, 상태, 글


def _장보완(q):
    r"""PC 보완 후보 장 — 한 장에 3개씩 · 첫 장에만 리드 · 마지막 장에 규칙·주의"""
    목록, 상태, 글 = _보완자료(q)
    if not 목록:
        return []
    업 = _업종표()
    n장 = max(1, -(-len(목록) // 3))
    장들, i0, 남 = [], 0, len(목록)
    for j in range(n장):
        m = -(-남 // (n장 - j))
        조각 = 목록[i0:i0 + m]
        부 = []
        if j == 0:
            부.append(_본문(_esc(글["리드"]), 31))
        블록들 = "".join(_종목블록(x, (업.get(x.get("종목코드", "")) or {}).get("업종명") or "", 상태, 상태 == "buy")
                       for x in 조각)
        부.append(f'<div style="flex:1;min-height:0;display:flex;flex-direction:column;gap:12px">'
                 f'<span style="flex:none;font-size:28px;font-weight:700;color:{C["보"]}">'
                 f'{_esc("보완 후보 · 지금 규칙 주문과 따로")}{"" if n장 == 1 else f" ({j + 1}/{n장})"}</span>'
                 f'<div style="flex:1;min-height:0;display:flex;flex-direction:column;gap:14px">{블록들}</div></div>')
        if j == n장 - 1:
            부.append(f'<div style="flex:none;font-size:25px;line-height:1.55;color:{C["보"]}">'
                     f'{_esc(글["규칙"] + ((" " + 글["주의"]) if 글["주의"] else ""))}</div>')
        배 = (f"지정가 주문 {len(목록)}" if 상태 == "buy" else f"{R.판정시각} 확정 전")
        머 = _머리("QUANT · 보완 후보", _쪽표, _esc(f"보완 후보 {len(목록)}개" + ("" if j == 0 else " (이어서)")),
                  크기=68, 배지=(배 if j == 0 else None), 배지색=(C["빨"] if 상태 == "buy" else C["보"]), 틈=24, 밑=32,
                  제목높이=(82 if n장 > 1 else None))
        장들.append(_카드(f"퀀트 보완{'' if j == 0 else j + 1}", 머, "".join(부), 패딩="12px 18px", 정렬="flex-start", 틈=40))
        i0 += m
        남 -= m
    return 장들


def _폰보완장들(q):
    r"""핸드폰 보완 후보 카드 — 한 장에 2개씩(3개면 리드·규칙 글과 함께 23~29px 잘렸다 · 10/20 실측) · 첫 장에 리드 · 마지막 장에 규칙·주의"""
    목록, 상태, 글 = _보완자료(q)
    if not 목록:
        return []
    업 = _업종표()
    n장 = max(1, -(-len(목록) // 2))
    out, i0, 남 = [], 0, len(목록)
    for j in range(n장):
        m = -(-남 // (n장 - j))
        조각 = 목록[i0:i0 + m]
        상자 = "".join(_폰종목(x, (업.get(x.get("종목코드", "")) or {}).get("업종명") or "", 상태) for x in 조각)
        몸 = (f'<p class="t">보완 후보 {len(목록)}개'
              + (f' <span class="badge" style="background:{C["빨"] if 상태 == "buy" else C["보"]}">'
                 f'{_e(f"지정가 {len(목록)}" if 상태 == "buy" else R.판정시각 + " 확정 전")}</span>' if j == 0 else " <small>(이어서)</small>")
              + '</p>')
        if j == 0:
            몸 += f'<p class="lead">{_e(글["리드"])}</p>'
        몸 += f'<div class="stks">{상자}</div>'
        if j == n장 - 1:
            몸 += f'<p class="note mt">{_e(글["규칙"] + ((" " + 글["주의"]) if 글["주의"] else ""))}</p>'
        out.append(_폰카드(f"보완 후보 · {i0 + 1}~{i0 + m}", 몸))
        i0 += m
        남 -= m
    return out


def _B글(q):
    r"""B(업종·섹터·규모 전용 규칙 8개) 오늘 상태 한 줄 — record_pick --B합치기 가 남긴 값만 읽는다 (2026-10-12)"""
    if str(q.get("신호기준일") or "") < "20261012":
        return ""
    # 10/13 — B 사기를 꺼 뒀으면(사용자 10/12 「꺼!」) 「B 계산이 안 끝나 빠졌다」 는 틀린 말이다 · 아무것도 안 쓴다
    if not getattr(R, "B사기", False):
        return ""
    b, 늦 = q.get("B") or {}, q.get("B늦음") or {}
    글 = []
    if b and not b.get("끝난규칙"):
        글.append("업종·섹터 전용 규칙(B) 계산이 판정 시각까지 끝나지 않아 오늘은 빠졌습니다.")
    elif b:
        n후 = sum((b.get("후보") or {}).values())
        글.append(f"업종·섹터 전용 규칙(B) {len(b.get('끝난규칙') or [])}개가 오늘 후보 {n후}종목을 냈습니다. "
                 "B는 문턱 없이, 지금 규칙이 쓰고 남은 자리만 채웁니다.")
        if b.get("못끝난규칙"):
            글.append(f"계산이 늦은 B 규칙 {len(b['못끝난규칙'])}개는 오늘 빠졌습니다.")
    if 늦:
        _이 = 늦.get("이름") or {}
        _목 = [f"{_이.get(c) or c}({(늦.get('라벨') or {}).get(k, k)})" for k, cs in (늦.get("규칙") or {}).items() for c in cs]
        글.append("늦게 나온 B 후보: " + (" · ".join(_목[:6]) + (f" 외 {len(_목) - 6}" if len(_목) > 6 else "") if _목 else "없음")
                 + " — 오늘 시가 매수 시점은 지나 사지 않습니다.")
    if not b and not 늦 and (q.get("동시호가") or {}).get("예상시장갭") is not None:
        글.append("업종·섹터 전용 규칙(B) 계산이 판정 시각까지 끝나지 않아 오늘은 빠졌습니다.")
    return " ".join(글)


def _행(라1, 값1, 라2, 값2, 색1=None, 색2=None):
    r"""종목 상자의 한 행 — [라벨 130px][값] x 2 (정본 C 카드).

    라벨 25px/700 금색 · 값 30px/800. **전부 nowrap** — 한 행은 한 줄이다.
    """
    # ⭐ QUANT-FIX-0929-2 ③ — **왼쪽 라벨 열만 180px** (오른쪽은 130 그대로).
    #    pre 의 「매수 적정 범위」(7자)가 130 을 넘어 값에 붙어 보였다.
    #    네 상태 모두 같은 폭 — 상태마다 열이 움직이지 않게
    # ⭐ QUANT-FIX-0929-2 ③ 실측 — 왼쪽 라벨을 180 으로 넓히니 pre 의 「42,350~42,700원」이
    #    왼쪽 값 칸(245px)을 **11px 넘었다.** 오른쪽 값 칸을 190px 로 두어 왼쪽 값이
    #    나머지(약 300px)를 다 쓴다. ⚠️ 정본은 두 값 칸이 flex:1 — 다른 자리라 디자인에 알렸다
    # ⭐ 10/14 핸드폰 판 — 칸 둘을 `qpair` 로 묶는다. 넓은 화면은 전과 같은 배치(왼쪽 묶음 flex:1 · 오른쪽 고정 폭)이고,
    #    핸드폰(.qmob)에서는 묶음이 안 들어가면 **다음 줄로 넘어간다** (값이 잘리지 않게)
    def _칸(라, 값, 색, 폭, 값폭=None):
        _vs = (f"flex:none;width:{값폭}px" if 값폭 else "flex:1;min-width:0")
        _묶 = "flex:none" if 값폭 else "flex:1;min-width:0"
        return (f'<span class="qpair" style="{_묶};display:flex;align-items:baseline;gap:12px">'
                f'<span class="qlab" style="flex:none;width:{폭}px;font-size:25px;font-weight:700;'
                f'color:{C["금진"]}">{라}</span>'
                f'<span class="qval" style="{_vs};font-size:30px;font-weight:800;'
                f'letter-spacing:-.02em;color:{색 or C["먹"]}">{값}</span></span>')
    return (f'<div class="qrow" style="display:flex;align-items:baseline;gap:12px;'
            f'white-space:nowrap;padding:6px 0;border-top:1px solid {C["줄선"]}">'   # 0929-2 ③ 8→6
            + _칸(라1, 값1, 색1, 180) + _칸(라2, 값2, 색2, 130, 190) + '</div>')


def _종목값(x, 업종, 상태):
    r"""종목 상자에 들어가는 **값 글자** — PC 카드(_종목블록)와 핸드폰 카드(_폰종목)가 같이 쓴다 (10/16 · 글을 두 벌로 안 적는다)"""
    _낙 = x.get("20일낙폭")
    _낙글 = _음(_낙, 1) if _낙 is not None else ("B 규칙은 안 봄" if x.get("B전용") else "—")   # 10/12 B 전용 종목
    _낙색 = None if _낙 is None else (C["빨"] if _낙 >= 0 else C["파"])
    # ⚠️ 10/8 독립 검사 — 「20일 낙폭 +23.4%」 처럼 오른 값에 「빠진 폭」 이름이 붙었다(섹터·업종 갈래는 안 빠져도 후보가 된다)
    _낙라 = "20일 낙폭" if (_낙 is None or _낙 < 0) else "20일 등락"
    _갭있음 = x.get("상대갭") is not None
    # 08:00 후보 때는 상대갭이 아직 없다 (08:55 에 정해진다)
    _갭글 = _음(x["상대갭"], 2, "%p") if _갭있음 else f"{R.판정시각} 확정 뒤"
    if 상태 == "pre":
        _a, _b = R.매수범위(x.get("어제종가", 0) or 0)
        _라4, _값4 = "매수 적정 범위", f"{_a:,}~{_b:,}원"
    else:
        _문 = x.get("문턱가")
        _라4, _값4 = "문턱가", (f"{_문:,}원" if _문 else ("문턱 없음(B)" if x.get("B전용") else "—"))
    _잉, _부 = x.get("잉여금비율"), x.get("부채비율")
    _재 = " · ".join(f"{z:.0f}%" for z in (_잉, _부) if z is not None) or ("B 규칙은 안 봄" if x.get("B전용") else "—")
    return {"이름": x.get("이름", ""), "업종": 업종 or "", "코드": x.get("종목코드", ""), "딱지": _딱지(x),
            "낙라": _낙라, "낙글": _낙글, "낙색": _낙색, "갭있음": _갭있음, "갭글": _갭글,
            "종가": f'{x.get("어제종가", 0):,}원', "시총": f'{x.get("시총억", 0):,}억',
            "라4": _라4, "값4": _값4, "재": _재}


def _종목블록(x, 업종, 상태, 확정):
    r"""종목 상자 — **4행 표형** (QUANT-ANSWER-0929 ★).

    정본: `quant-box-source.dc.html` 맨 왼쪽 카드 「C · 라벨 강조 (금색 굵게)」.
    한 행에 **한 가지 뜻**만 둔다. 전에는 3줄인데 맨 위 줄이 넘쳐 줄바꿈됐다.

    ⚠️ 상자 안 「넘겨서 안 샀습니다」·「안 산다」는 **넣지 않는다** —
       머리 배지와 목록 라벨이 이미 말한다 (한 장에 다섯 번 나오던 것)
    ⚠️ **종목코드가 빠졌다.** 정본 1행에도 답 문서 1행에도 코드가 없다.
       내용이 하나 사라지는 것이지만 둘 다 같은 말이라 그대로 따랐다
    ⚠️ 낙폭에 **색이 다시 들어온다** — 정본이 음수 파랑·양수 빨강이다
    """
    v = _종목값(x, 업종, 상태)
    # ── 1행 — 종목명 · 업종 ……… (사는 날) 지정가 주문 칩 · 딱지 ──
    _칩들 = ""
    if 상태 == "buy":
        _칩들 += (f'<span style="flex:none;font-size:24px;font-weight:700;color:#ffffff;'
                  f'background:{C["빨"]};border-radius:6px;padding:3px 12px">'
                  f'지정가 주문</span>')
    _딱 = _딱지(x)
    if _딱:
        _칩들 += (f'<span style="flex:none;font-size:24px;font-weight:700;'
                  f'color:{C["금"]};background:{C["딱"]};border-radius:6px;'
                  f'padding:3px 12px">{_esc(_딱)}</span>')
    _1행 = (f'<div class="qhead1" style="display:flex;align-items:center;gap:14px;white-space:nowrap;'
            f'padding-bottom:8px">'     # 0929-2 ③ 10→8
            f'<span style="font-size:38px;font-weight:800;letter-spacing:-.03em">'
            f'{_esc(x.get("이름", ""))}</span>'
            + (f'<span style="font-size:26px;font-weight:700;color:{C["본"]}">'
               f'{_esc(업종)}</span>' if 업종 else "")
            # ⭐ 2026-09-29 (사용자 결정) — **종목코드를 업종 옆에** 되살린다.
            #    정본 1행엔 코드가 없다 — 정본과 다른 자리라 디자인에 알렸다
            #    (design-share/ASK-QUANT-0929-2.md). 보조 24px · #6b665c
            + (f'<span style="font-size:24px;color:{C["보"]}">'
               f'{_esc(x.get("종목코드", ""))}</span>' if x.get("종목코드") else "")
            + '<span style="flex:1"></span>' + _칩들 + '</div>')

    # ── 2행 — 20일 낙폭 │ 상대갭 ──  (값은 _종목값 — 핸드폰 카드와 같이 쓴다)
    _갭글 = (_esc(v["갭글"]) if v["갭있음"] else
             f'<span style="font-size:24px;font-weight:700;color:{C["보"]}">{_esc(v["갭글"])}</span>')
    _2행 = _행(v["낙라"], _esc(v["낙글"]), "상대갭", _갭글, v["낙색"], None)

    # ── 3행 — 전날 종가 │ 시가총액 ──
    _3행 = _행("전날 종가", v["종가"], "시가총액", v["시총"])

    # ── 4행 — 문턱가(또는 매수 적정 범위) │ 이익 · 빚 ──
    _4행 = _행(v["라4"], _esc(v["값4"]).replace("~", "~<wbr>"), "이익 · 빚", _esc(v["재"]), C["금진"], None)
    # ⭐ 10/20 ② 팔 값을 가격으로 (주문가 기준 · 사는 날만)
    _팔 = _팔값(x) if 상태 == "buy" else None
    if _팔:
        _4행 += _행(f"{R.몫들[0][0] * 100:g}% 팔 값", f"{_팔[0]:,}원", f"{R.몫들[1][0] * 100:g}% 팔 값", f"{_팔[1]:,}원", C["빨"], C["빨"])

    return (f'<div data-block="1" style="background:{C["블록"]};'
            f'border:1px solid {C["선"]};border-radius:16px;padding:13px 24px;'   # 0929-2 ③ 16→13
            f'display:flex;flex-direction:column;'
            f'flex:1;min-height:0;max-height:{_상자최대}px;'
            f'justify-content:space-between">{_1행}{_2행}{_3행}{_4행}</div>')


# ⭐ 2026-09-23 (사용자 「고쳐」) — 갈래 수를 **켜진 것에서 센다.** 「넷 중 하나」가 손으로 적혀 있어
#    업종 갈래가 생긴 뒤 하나 모자랐다 [[hand-written-numbers-freeze]]. _장1·_장2 가 같이 쓴다
_갈래들 = ["낙폭", "섹터", "시장"]
if R.변동성자사주_켬:
    _갈래들.append("변동성")
if R.업종규칙_켬 and R.업종규칙:
    _갈래들.append("업종")
_갈래수 = {3: "셋", 4: "넷", 5: "다섯", 6: "여섯", 7: "일곱"}.get(len(_갈래들), str(len(_갈래들)))
_제문 = bool(R.섹터규칙_큰회사 or any(v.get("재무") for v in R.업종규칙.values()))
_문안내 = " (섹터·업종 규칙에 걸린 종목은 그 규칙의 문을 따릅니다)" if _제문 else ""


def _악재알림():
    r"""보유·최근 후보에 악재 공시가 떴나 → (보유목록, 후보목록). 없으면 ([], []).

    ⚠️ **악재가 있을 때만** 화면이 바뀐다. 평소엔 아무것도 안 붙는다
    ⚠️ 이 함수가 어떻게 터지든 **쪽은 그대로 그려져야 한다**
    """
    import datetime as _dt
    import subprocess as _sp
    import sys as _sys
    _길 = os.path.join(_DATA, "bad-news-today.json")
    try:
        _오늘 = _dt.date.today().strftime("%Y-%m-%d")
        _낡음 = True
        if os.path.exists(_길):
            _j = json.load(io.open(_길, encoding="utf-8-sig"))
            _낡음 = not str(_j.get("만든날", "")).startswith(_오늘)
        if _낡음:
            _sp.run([_sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "bad_news_check.py"), "--조용"],
                    capture_output=True, timeout=120)
        _j = json.load(io.open(_길, encoding="utf-8-sig"))
        return (_j.get("보유악재") or []), (_j.get("후보악재") or [])
    except Exception:  # noqa: BLE001
        return [], []


def _악재줄():
    r"""악재가 있을 때만 한 줄(HTML). 없으면 빈 글자."""
    try:
        _보, _후 = _악재알림()
    except Exception:  # noqa: BLE001
        return ""
    if not _보 and not _후:
        return ""
    _글 = []
    for z in _보[:3]:
        _글.append(f"들고 있는 <b>{_esc(z.get('이름') or z.get('종목코드'))}</b>에 "
                   f"{_esc(str(z.get('공시명'))[:32])} 공시가 떴습니다"
                   + (" (반대말일 수 있습니다)" if z.get("반대말") else ""))
    for z in _후[:2]:
        _글.append(f"후보였던 {_esc(z.get('이름') or z.get('종목코드'))}에 "
                   f"{_esc(str(z.get('공시명'))[:28])} · 참고")    # ⭐ QUANT-FIX-0929-2 ④ — 「—」 안 씀
    _색 = C["빨"] if _보 else C["본"]
    _머 = "🔴 보유 종목 악재 · 규칙은 <b>다음 날 시가 매도</b>입니다" if _보 else "악재 공시 (참고)"
    # ⭐ 0929-2 새 판 ★ — `margin-top:16px` 을 뺐다. 항목 사이는 56 고정인데 이 줄만 72 였다
    return (f'<div style="font-size:31px;line-height:1.5;color:{_색};'
            f'border-top:1px solid {C["선"]};padding-top:16px">'
            f'{_머}<br>' + "<br>".join(_글) + '</div>')


_폰자료 = {}
_띠색 = ("#3C4250", "#5A6272")   # 10/20 새 카드 위 띠 색 — build_site 가 그날 홈 색으로 바꾼다(없으면 보합 회색)


def _장1(q, 보유):
    후보 = q.get("후보") or []
    동 = q.get("동시호가") or {}
    확정 = 동.get("예상시장갭") is not None
    # ⭐ ㉥ (2026-09-21) — 지수가 크게 빠진 날엔 더 산다.
    #    그날 지수 낙폭은 record_pick 이 재서 forward-log 에 남긴 값을 그대로 쓴다.
    #    ⚠️ 여기서 다시 재지 않는다 — 두 곳에서 재면 언젠가 갈라진다
    # ⚠️ **시뮬과 똑같이** 맨 위 후보의 시장 지수를 본다 (gate7 _빠진장Q13 과 같은 자리).
    #    하루 상한은 날 단위 결정인데 코스피·코스닥 낙폭이 다를 수 있다 —
    #    어느 쪽을 볼지 정해야 하고, 시뮬이 「맨 위 후보의 시장」을 썼으므로 그대로 맞춘다.
    #    옛 기록(시장지수낙20 이 없는 날)은 None -> 평소 값
    _낙20 = next((x.get("시장지수낙20") for x in 후보
                  if x.get("시장지수낙20") is not None), None)
    최대 = R.오늘최대종목(_낙20)
    # ⭐ 2026-09-29 — **섹터 갈래 전용 자리**만큼 더 그린다.
    #    규칙은 6 + 섹터 2 = 최대 8 을 산다. 화면이 6 에서 자르면
    #    **산 것이 화면에 안 나온다.** 조판이 내용을 깎으면 안 된다
    _섹더C = getattr(R, "섹터전용자리", 0)
    최대 = 최대 + _섹더C
    # ⭐⭐⭐ **실제로 산 것**을 쓴다 (2026-09-29)
    #    `규칙매수` 는 문턱을 넘은 **전부**에 찍힌다(채점용). 그걸로 앞에서 자르면
    #    문턱 넘은 게 자리보다 많은 날 **안 산 종목이 화면에 나온다.**
    #    `오늘산다` 는 record_pick 이 실제로 고른 것에만 찍는다.
    #    ⚠️ 옛 기록엔 그 표시가 없다 — 없으면 지금까지처럼 `규칙매수` 로 돌아간다
    #    ⚠️ 차례는 **후보 차례 그대로** 둔다 = 규칙 겹친 수 많은 순 → 낙폭 깊은 순.
    #       사용자: 「가장 강한 신호가 첫번째에 오는 거 맞아?」 → 맞다. 안 건드린다
    _산것들 = [x for x in 후보 if x.get("오늘산다")]
    살것 = (_산것들 if _산것들
            else [x for x in 후보 if x.get("규칙매수")][:최대]) if 확정 else []
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
        # ⭐ 2026-09-29 밤 — 업종 규칙 종목은 −1.5%p (오늘 반영). 화면이 옛 문턱만 말하고 있었다
        리드 = (f"상대갭이 문턱({_문턱글()})까지 내려온 종목이 없었습니다. "
              "아무것도 사지 않는 것도 규칙대로 한 것입니다.")
        라벨, 라벨색 = "사지 않습니다 · 조건에 걸린 종목 (참고용)", C["보"]
        # ⭐⭐⭐ 2026-09-29 (사용자 「세로 상세는 오늘 브리핑 보기 쪽인데 연관 없잖아?」)
        #    전에는 「나머지 N개는 **상세에**」라고 썼는데 **거짓말이었다.**
        #    세로 상세는 브리핑 카드 쪽 화면이고 퀀트 후보는 거기에 없다
        #    (사이트 레일 26일치에 브리핑 카드는 다 있지만 퀀트 장은 0일치다).
        #    ⇒ 없는 곳을 가리키지 말고 **싣지 않는다고 그대로 쓴다**
        각주 = (f"후보 {전체}종목 중 갭이 깊은 순으로 {n}개만 싣습니다."
              + (f" 나머지 {전체 - n}개는 화면에 넣지 않습니다." if 전체 > n else "")
              + " 오늘은 문턱가를 넘어 아무것도 사지 않았습니다.")
    elif 상태 == "buy":
        킥, 제, 배, 배색 = (f"QUANT · {R.판정시각} 확정", f"오늘 살 것: {n}개",
                        f"지정가 주문 {n}", C["빨"])
        # ⭐ 10/13 — 08:55 예상가는 얇은 주문으로 튄다(실전 16건 중 실제로 문턱 밑에서 시작한 건 3건) ·
        #    시험과 같게 **문턱가에 지정가**를 걸고 9시 시가가 닿을 때만 산다 (사용자 「응」)
        리드 = (f"문턱가(시장보다 {_문턱글()} 더 싸게 시작하는 값)에 지정가를 걸어 두고, "
              f"9시 시가가 그 값 이하일 때만 삽니다. 시가가 더 높으면 사지 않습니다. 갭이 깊은 순으로 최대 {최대}종목입니다."
              # ⭐ 2026-10-12 B — B 로 산 것이 있으면 문턱 말이 틀리게 읽힌다
              + (" 「○○ 전용」 표시는 업종·섹터 전용 규칙(B)으로 고른 것이라 문턱 없이, 남은 자리에서 삽니다."
                 if any(x.get("B로산다") for x in 살것) else ""))
        라벨, 라벨색 = "살 종목 · 지정가 주문 대상", C["빨"]
        앞, 뒤 = R.몫들[0], R.몫들[1]
        각주 = (f"{_몫말(앞[0])} +{앞[1]:g}%에, {_몫말(뒤[0], 뒤=True)} +{뒤[1]:g}%에 파는 "
              "지정가를 같이 걸어 둡니다 · 09:01에 체결 안 된 주문은 반드시 취소하세요.")
    else:
        킥, 제, 배, 배색 = (f"QUANT · {R.판정시각} 확정" if 확정 else "QUANT · 08:00 후보",
                        "오늘 볼 것 없음", "후보 0", C["보"])
        리드, 라벨, 라벨색 = "", "", C["보"]
        각주 = "규칙을 낮춰 억지로 후보를 만들지 않습니다. 다음 장에 어떤 조건으로 걸러내는지 있습니다."

    _bg = _B글(q)
    if _bg:
        각주 = (각주 + " " if 각주 else "") + _bg

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
              f'border-radius:16px;padding:14px 24px;font-size:31px;line-height:1.5;'
              f'color:{C["먹"]}">{" ".join(말)}</div>')

    부 = [알림] if 알림 else []
    # ⭐ 10/16 핸드폰 4:5 카드(_폰덱)가 같은 값을 쓴다 — 여기서 정한 상태·목록·글을 넘긴다 (다시 계산하면 언젠가 갈라진다)
    _폰자료.clear()
    _폰자료.update(상태=상태, 목록=목록, 업=업, 킥=킥, 제=제, 배=배, 배색=배색, 리드=리드, 라벨=라벨,
                  라벨색=라벨색, 각주=각주, 알림말=(말 if (팔것 or 뒤팔것) else []), 전체=전체, 보유=보유)
    # ⭐ 10/20 ① 오늘 왜 이 종목들인가 (사용자 「지금 바로 넣자!」)
    _왜 = _오늘왜(q, 목록) if 상태 in ("buy", "wait", "pre") else ""
    _폰자료["왜"] = _왜
    if 리드:
        부.append(_본문(_esc(리드), 35))
    if _왜:
        부.append(_본문(f'<b style="font-weight:800">왜 오늘 이 종목인가 · </b>{_esc(_왜)}', 29))   # 31 이면 08:00 상태에서 4px 넘쳤다
    if 상태 == "none":
        부.append(f'<div style="display:flex;flex-direction:column;gap:18px">'
                 f'<span style="font-size:114px;font-weight:800;letter-spacing:-.05em;'
                 f'line-height:1.15;color:{C["금"]}">0개</span>'
                 f'<span style="font-size:31px;line-height:1.6;color:{C["본"]}">조건을 통과한 '
                 f'종목이 없습니다. 규칙상 이런 날은 열흘에 세 번쯤 있습니다. 고장이 아닙니다.'
                 f'</span></div>')
        for 글 in (f"후보가 되려면 먼저 이걸 모두 통과해야 합니다 · 쌓은 이익 {R.잉여금하한:g}% 이상 · "
                  f"빚 {R.부채상한:g}% 이하 · 작년 순이익 흑자 · 시가총액 {R.시총하한억:,.0f}억 이상 · "
                  f"하루 거래 {R.대금하한억:g}억 이상 · 상장한 지 {R.상장최소거래일}거래일 이상 "
                  f"({_뽑기글()['상한글']})"
                  + _문안내 + ".",
                  f"그 다음 {' · '.join(_갈래들)} {_갈래수} 중 하나에"
                  + " 걸려야 합니다. 오늘은 어느 것도 걸리지 않았습니다."
                  + (f" 들고 있는 것 {len(보유)}개에는 +{R.앞몫목표:g}% · +{R.뒷몫목표:g}% "
                     f"지정가가 걸려 있습니다." if 보유 else "")):
            부.append(f'<div style="font-size:31px;line-height:1.55;color:{C["본"]};'
                     f'border-top:1px solid {C["선"]};padding-top:18px">{_esc(글)}</div>')
        # ⭐ 2026-09-28 — 악재 공시가 있을 때만 한 줄 (없으면 아무것도 안 붙는다)
        _악 = _악재줄()
        if _악:
            부.append(_악)
        부.append(f'<div style="font-size:25px;line-height:1.55;color:{C["보"]}">'
                 f'{_esc(각주)}</div>')
        머리 = _머리(킥, _쪽표, _esc(제), 크기=68, 배지=배, 배지색=배색, 틈=24, 밑=32)
        return [_카드("퀀트1 종목", 머리, "".join(부), 패딩="12px 18px",
                      틈=56)]   # ★ 후보 0개 1장도 56 (상자 없는 장)

    # ⭐⭐ 2026-09-29 — **3개씩 끊어 여러 장으로** (사용자 「3개씩으로 하자」)
    #    한 장에 4개부터 잘린다 (실측). 글을 줄이는 대신 **장을 늘린다**
    # ⭐⭐ 2026-09-29 — **고르게 나눈다.** 앞에서부터 채우면 8개가 4+4 가 아니라
    #    4+4 여도 6개는 4+2 가 되어 마지막 장이 휑하다. 8->4+4 · 7->4+3 · 6->3+3 · 5->3+2
    _쪽수 = max(1, -(-len(목록) // (3 if _왜 else _한장에)))   # 10/20 「왜」 가 붙으면 한 장 4개는 2~4px 넘쳤다 → 3개
    _쪽들, _i0, _남 = [], 0, len(목록)
    for _j in range(_쪽수):
        _몫 = -(-_남 // (_쪽수 - _j))
        _쪽들.append(목록[_i0:_i0 + _몫])
        _i0 += _몫
        _남 -= _몫
    _쪽들 = _쪽들 or [[]]
    _장들 = []
    # ⭐⭐⭐ ANSWER-0929-4 — **1·2장 위치 맞추기.** 여러 장이면 쪽마다 「리드 칸」에 넣을 글:
    #    1장 = 알림 + 리드 · 마지막 장 = **원래 맨 아래 각주**(1장 리드와 같은 글꼴로) · 사이 장 = 없음.
    #    **모든 장의 리드 칸에 이 글들을 겹쳐 넣고 제 것만 보이게** 한다 → 칸 높이가 저절로
    #    긴 쪽에 맞아 목록 라벨·첫 상자·마지막 상자가 두 장에서 같은 높이가 된다
    _여러 = len(_쪽들) > 1
    _리드글 = []
    if _여러:
        for _k0 in range(len(_쪽들)):
            if _k0 == 0:
                _리드글.append("".join(부))
            elif _k0 == len(_쪽들) - 1:
                _리드글.append(_본문(_esc(각주), 35))
            else:
                _리드글.append("")

    def _리드칸(보일):
        return ('<div style="flex:none;display:grid">'
                + "".join(f'<div style="grid-area:1/1;display:flex;flex-direction:column;gap:40px;'
                          f'visibility:{"visible" if _i == 보일 else "hidden"}">{_g}</div>'
                          for _i, _g in enumerate(_리드글))
                + '</div>')

    for _k, _쪽 in enumerate(_쪽들):
        블록들 = "".join(_종목블록(x, (업.get(x.get("종목코드", "")) or {}).get("업종명")
                              or (x.get("섹터") or ""), 상태, 확정) for x in _쪽)
        _라 = 라벨 if _k == 0 else f"{라벨} (이어서 {_k + 1}/{len(_쪽들)})"
        _부 = [_리드칸(_k)] if _여러 else (list(부) if _k == 0 else [])
        # ⭐⭐⭐ 상자 묶음이 **남는 자리를 다 쓴다** (flex:1). 라벨·각주는 제 높이만.
        #    이러면 아래에 빈 자리가 안 남고, 상자들이 그 자리를 똑같이 나눠 갖는다
        _부.append(f'<div style="flex:1;min-height:0;display:flex;'
                   f'flex-direction:column;gap:12px">'
                   f'<span style="flex:none;font-size:28px;font-weight:700;color:{라벨색}">'
                   f'{_esc(_라)}</span>'
                   f'<div style="flex:1;min-height:0;display:flex;flex-direction:column;'
                   f'gap:14px">{블록들}</div></div>')
        if _k == len(_쪽들) - 1 and not _여러:
            # ⭐ 한 장뿐인 날만 맨 아래 각주. 여러 장이면 마지막 장 **리드 칸**으로 올라갔다
            #    (ANSWER-0929-4 — 같은 문구를 두 번 안 쓴다)
            _부.append(f'<div style="flex:none;font-size:25px;line-height:1.55;'
                       f'color:{C["보"]}">{_esc(각주)}</div>')
        # ⭐ E — 제목은 **1장만 68**, 이어지는 장은 64 (정본 계단)
        _머 = _머리(킥, _쪽표, _esc(제) if _k == 0 else _esc(제) + " (이어서)",
                   # ⭐ 2026-09-29 밤 (디자인) — 1·2장은 **같은 성격이라 제목도 같은 68px**.
                   #    글자 크기가 달라 보이면 안 된다. 줄 높이 82px 고정은 그대로
                   크기=68,
                   배지=(배 if _k == 0 else None), 배지색=배색, 틈=24, 밑=32,
                   제목높이=(82 if _여러 else None))   # ⭐ 68px x 1.2 — 두 장 머리 같게
        _장들.append(_카드(f"퀀트1 종목{'' if _k == 0 else _k + 1}", _머,
                        "".join(_부), 패딩="12px 18px", 정렬="flex-start", 틈=40))   # ★ 상자 장 40
    return _장들


def _억말(v):
    r"""시총 억 → 「2,000억」 · 「1조」 (1만억 단위로 딱 떨어지면 조)"""
    v = float(v)
    if v >= 10000 and v % 10000 == 0:
        return f"{v / 10000:g}조"
    return f"{v:,.0f}억"


def _거래소업종(묶음):
    r"""업종지수 이름 → 거래소 업종 이름들 (규칙 파일 `업종맵` 을 거꾸로).

    「자동차」「자동차부품」처럼 앞말이 같은 짝은 「자동차·부품」으로 붙인다 (글자 뜻은 그대로)
    """
    이름들 = [k for k, v in R.업종맵.items() if v == 묶음]
    out = []
    for k in 이름들:
        짝 = next((z for z in 이름들 if z != k and k.startswith(z) and len(k) > len(z)), None)
        if 짝:
            continue                       # 「자동차부품」은 「자동차」 쪽에서 붙인다
        긴 = next((z for z in 이름들 if z != k and z.startswith(k) and len(z) > len(k)), None)
        out.append(f"{k}·{긴[len(k):]}" if 긴 else k)
    return " · ".join(out)


def _업종덩이들():
    r"""4장 — 업종마다 **한 덩이** (QUANT-PICK-0929 · 표를 없앴다).

    1줄 묶음 이름 · 거래소 업종 · 시총 / 2줄 「60거래일 동안 20.59% 넘게 빠지면 걸립니다」 /
    3줄 재무 문. ⚠️ 숫자는 전부 `rule_def.업종규칙` 에서 — 손으로 안 적는다
    ⚠️ 1·2줄은 nowrap — 말줄임하지 않는다. 넘치면 검사 ①·⑨ 가 잡는다 (디자인: 「알려줘」)
    """
    _기간 = {"낙폭60": 60, "낙120": 120, "낙폭20": 20, "낙40": 40}
    _칩 = (f'flex:none;font-size:23px;font-weight:700;color:{C["먹"]};background:#f4f1ea;'
           f'border-radius:6px;padding:3px 10px;white-space:nowrap')
    덩이 = []
    for _업, _v in R.업종규칙.items():
        띠 = _v.get("띠")
        시총 = (f"{_억말(띠[0])}~{_억말(띠[1])}" if 띠 else f"{_억말(R.시총하한억)} 이상")
        빠짐 = " · ".join(
            f'<b style="font-weight:800;color:{C["먹"]}">{_기간.get(재, 재)}거래일</b> 동안 '
            f'<b style="font-weight:800;color:{C["파"]}">{abs(문):g}%</b>'
            for 재, 문, _ in _v["재료"]) + " 넘게 빠지면 걸립니다"
        if _v.get("재무"):
            라 = "재무 문 · 1단계 대신"
            칩들 = [f"잉여금 {_v['재무'][0]:g}%↑", f"빚 {_v['재무'][1]:g}%↓",
                  f"거래 {_v['대금하한억']:g}억↑"] + (["흑자"] if R.흑자필수 else [])
        else:
            라 = "재무 문"
            칩들 = ["1단계 공통 문 그대로"]
        덩이.append(
            f'<div data-lump="1" style="background:#ffffff;border:1px solid {C["선"]};'
            f'border-radius:16px;padding:16px 24px;display:flex;flex-direction:column;gap:8px">'
            f'<div style="display:flex;align-items:baseline;gap:12px;white-space:nowrap">'
            f'<span style="flex:none;font-size:33px;font-weight:800;letter-spacing:-.03em">'
            f'{_esc(_업)}</span>'
            f'<span style="flex:1;min-width:0;font-size:23px;color:{C["보"]}">'
            f'{_esc(_거래소업종(_업))}</span>'
            f'<span style="flex:none;font-size:23px;color:{C["보"]}">시총 '
            f'<b style="font-weight:800;color:{C["먹"]}">{시총}</b></span></div>'
            f'<span style="font-size:30px;line-height:1.4;color:{C["본"]};white-space:nowrap">'
            f'{빠짐}</span>'
            f'<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 8px;'
            f'border-top:1px solid #ece5d6;padding-top:9px">'
            f'<span style="flex:none;font-size:22px;font-weight:700;color:#8a6425">{_esc(라)}</span>'
            + "".join(f'<span style="{_칩}">{_esc(z)}</span>' for z in 칩들)
            + '</div></div>')
    return 덩이


# ── 3장 · 어떻게 뽑았나 (1단계 → 2단계) · 4장 · 업종마다 다른 문 ──────────
def _뽑기글():
    r"""「어떻게 뽑았나」 글 조각 — PC 3장(_장2)과 핸드폰 카드가 같이 쓴다 (10/16 · 글을 두 벌로 안 적는다).

    ⭐ 10/16 사용자 「300억~2천억 시가총액 * 이거 맞아?」 — 아니었다. 「300억~2,000억」 을 1단계 공통 조건처럼 적어
       섹터 종목도 2천억까지인 것처럼 읽혔다(실전: 300억↑ 공통 · 2,000억 미만은 크게 빠짐·시장·변동성 갈래만 · 섹터는 상한 없음).
       또 실전 조건 「상장 250거래일↑」(record_pick)이 카드에 없었다 → 둘 다 고친다
    """
    리드 = ("재무가 튼튼한 회사가 크게 빠진 날을 찾습니다. 왜 빠졌는지(회사 사정)는 보지 않고 "
          "재무·주가·지수와 공시 몇 가지를 숫자로만 보는 기계 규칙이라 브리핑과 종목이 다른 것이 정상입니다.")
    문들 = ([(f"{R.잉여금하한:g}%", "이상 · 벌어서 쌓은 이익"), (f"{R.부채상한:g}%", "이하 · 빚")]
          + ([("흑자", "· 작년 순이익")] if R.흑자필수 else [])
          + [(f"{R.시총하한억:,.0f}억", "이상 · 시가총액"),
             (f"{R.대금하한억:g}억", "이상 · 하루 거래"),
             (f"{R.상장최소거래일}거래일", "이상 · 상장한 지")])
    _업켬 = bool(R.업종규칙_켬 and R.업종규칙)
    _갈래상한 = "크게 빠짐·시장" + ("·변동성" if R.변동성자사주_켬 else "")
    상한글 = (f"시가총액 {R.시총상한억:,.0f}억 미만은 {_갈래상한} 갈래만"
            + (" · 섹터 갈래는 상한이 없습니다" if R.섹터규칙_큰회사 else ""))
    제외 = ("관리종목·우선주·스팩은 제외합니다 · " + 상한글
          + (f" · 업종 갈래는 업종마다 범위가 다릅니다 ({_다음쪽}장)." if _업켬 else "."))
    규칙 = ((("낙폭", f"20거래일 동안 {abs(R.낙폭20문턱):g}% 넘게 빠졌고, 평소 움직이던 폭의 "
                     f"아래쪽(볼린저 −{abs(R.볼린저문턱):g}σ)에 있다"),
             # ⭐ 10/14 ②-0 — 섹터 종목 목록(value-chain-map)은 2026년에 만든 목록이라 그 뒤 사라진 회사가 빠져 있다 · 과거 성적이 좋게 나왔을 수 있다
             ("섹터", f"방산·원전·반도체 등 {len(R.섹터규칙)}개 섹터는 섹터마다 기준이 다르다"
                     " (섹터 종목 목록은 올해 기준이라 과거 성적은 실제보다 좋게 나왔을 수 있다)"),
             ("시장", f"지수가 눌린 날(20일 −{abs(R.지수낙20문턱):g}% · 60일 −{abs(R.지수낙60문턱):g}%)"
                     f"에는 종목이 조금만 빠져도 걸린다 (볼린저 −{abs(R.시장볼문턱):g}σ · "
                     f"20일 −{abs(R.시장낙20문턱):g}% · 60일 −{abs(R.시장낙60문턱):g}%)"))
            + ((("변동성·자사주", f"지수가 크게 출렁이는 날(20일 변동성 {R.시장변동성문턱:g}% 이상)에는 "
                                f"{R.자사주창일}거래일 안에 자사주 매입을 공시한 회사도 걸린다"),)
               if R.변동성자사주_켬 else ())
            + ((("업종", "업종마다 따로 낸 기준 · 다음 장에 있다"),) if _업켬 else ()))
    _갈 = {3: "세", 4: "네", 5: "다섯", 6: "여섯"}.get(len(규칙), str(len(규칙)))
    return {"리드": 리드, "문들": 문들, "제외": 제외, "상한글": 상한글, "규칙": 규칙, "업켬": _업켬, "갈": _갈,
            "앞쪽": "여러 갈래에 걸린 종목이 앞쪽에 옵니다."}


def _장2():
    # ⭐⭐⭐ 2026-09-29 밤 QUANT-PICK-0929 — 3장은 「어떤 순서로 거르나」 하나만,
    #    4장은 표 대신 업종마다 한 덩이. 문구는 디자인 판 그대로 · 숫자는 규칙 파일에서.
    #    ASK-QUANT-0929-5 에서 짚은 것: 「업종」→「섹터」(⑥) · 지수 숫자/종목 숫자 분리(⑦) ·
    #    「섹터·업종 갈래는 시가총액 범위를 따로」(⑧) · 「없음」→「1단계 공통 문 그대로」(①)
    # (옛 판의 이력: 2026-09-23 「회사 사정과 상관없이」 삭제 · 09-29 B137 재무 문 — 커밋 d39873f 이전 참고)
    # ⭐ ANSWER-0929-7 답 2 — 「왜 빠졌는지(회사 사정)는 보지 않고」 되살림 (디자인: 「내 실수다」)
    g = _뽑기글()
    리드, 문들, 규칙, _업켬, _갈 = g["리드"], g["문들"], g["규칙"], g["업켬"], g["갈"]

    def _단계(칩글, 제목, 속, 틈):
        return (f'<div style="display:flex;flex-direction:column;gap:{틈}px;'
                f'border-top:1px solid {C["선"]};padding-top:20px">'
                f'<div style="display:flex;align-items:baseline;gap:14px">'
                f'<span style="flex:none;font-size:26px;font-weight:800;color:#ffffff;'
                f'background:{C["금"]};border-radius:7px;padding:3px 13px">{칩글}</span>'
                f'<span style="font-size:28px;font-weight:700;color:{C["금"]}">{제목}</span></div>'
                f'{속}</div>')

    def _각주(글):
        return (f'<span style="font-size:25px;line-height:1.55;color:{C["보"]}">{글}</span>')

    격자 = ('<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 28px">'
          + "".join(f'<span style="font-size:31px;line-height:1.45;color:{C["본"]}">'
                    f'<b style="font-weight:800;color:{C["먹"]};white-space:nowrap">{_esc(v)}</b> '
                    f'{_점안끊김(_esc(k))}</span>' for v, k in 문들)
          + '</div>'
          # ⭐ ANSWER-0929-7 답 2·3 — 제외 셋 되살림 + 섹터·업종 범위를 **사실대로** (한 줄로 합침)
          + _각주(_묶음(_esc(g["제외"]))))
    # ⚠️ 「(4장)」을 손으로 적지 않는다 — 종목 장 수가 날마다 달라 업종 장이 3~4쪽을 오간다
    줄들 = "".join(
        f'<div style="display:flex;align-items:flex-start;gap:18px">'
        f'<span style="flex:none;width:176px;box-sizing:border-box;text-align:center;'
        f'font-size:25px;font-weight:700;color:{C["금"]};background:{C["딱"]};border-radius:7px;'
        f'padding:5px 0;white-space:nowrap">{태}</span>'
        f'<span style="flex:1;min-width:0;font-size:30px;line-height:1.5;color:{C["본"]}">'
        f'{_묶음(_esc(글))}</span></div>' for 태, 글 in 규칙)
    몸3 = (_본문(_esc(리드), 33)
          + _단계("1단계", "먼저, 이걸 모두 통과", 격자, 14)
          + _단계("2단계", f"{_갈} 갈래 중 하나에 걸리면 후보", 줄들, 16)
          + _각주("여러 갈래에 걸린 종목이 1장 위쪽에 옵니다."
                 + ("" if _업켬 else " 다음 장은 언제 사고 언제 파는지입니다.")))
    장들 = [_카드("퀀트2 어떻게뽑았나", _머리("HOW THEY WERE PICKED", _쪽표, "어떻게 뽑았나"),
                몸3, 정렬="flex-start", 틈=56)]
    if not _업켬:
        return 장들

    # ── 4장 · 한 장에 덩이 넷까지 · 다섯 이상이면 「(이어서)」 장으로 ──
    덩이 = _업종덩이들()
    묶 = [덩이[i:i + 4] for i in range(0, len(덩이), 4)]
    _업갭 = getattr(R, "업종전용상대갭", None)
    for k, 쪽 in enumerate(묶):
        몸4 = ""
        if k == 0:
            몸4 += _본문("2단계 「업종」 갈래는 업종마다 그 업종 자료로만 낸 기준을 씁니다. "
                        "잘 빠지는 업종일수록 더 많이 빠져야 걸립니다.", 33)
        몸4 += ('<div style="display:flex;flex-direction:column;gap:16px">'
                + "".join(쪽) + '</div>')
        if k == len(묶) - 1:
            if _업갭 is not None:
                몸4 += (f'<div style="display:flex;flex-direction:column;gap:8px;'
                        f'border-top:1px solid {C["선"]};padding-top:18px">'
                        f'<span style="font-size:26px;font-weight:700;color:{C["금"]}">'
                        f'이 갈래로 걸린 종목은 사는 문턱이 다릅니다</span>'
                        f'<span style="font-size:31px;line-height:1.5;color:{C["본"]}">'
                        f'{R.판정시각} 상대갭이 <b style="font-weight:800;color:{C["먹"]};'
                        f'white-space:nowrap">−{abs(_업갭):g}%p</b> 아래면 삽니다. 다른 갈래는 '
                        f'<b style="font-weight:800;color:{C["먹"]};white-space:nowrap">'
                        f'−{abs(R.상대갭문턱):g}%p</b>입니다.</span></div>')
            몸4 += _각주("기간은 거래일 기준 · ↑ 이 값 이상, ↓ 이 값 이하입니다. "
                        "다음 장은 언제 사고 언제 파는지입니다.")
        장들.append(_카드(f"퀀트2 업종문{'' if k == 0 else k + 1}",
                         _머리("HOW THEY WERE PICKED", _쪽표,
                               "업종마다 다른 문" + ("" if k == 0 else " (이어서)")),
                         몸4, 정렬="flex-start", 틈=56))
    return 장들


_5장선 = 2   # 5장 첫 장에 둘 블록 수 (ANSWER-0929-7 답 1 · 10/7: 가정 금액 설명 한 줄을 넣자 둘째 장이 10px 넘쳐 한 블록 앞으로 — 실측)


def _억만(원):
    """2억 4,800만 원 꼴 (100만 원 단위 반올림) — 시뮬 금액이다 (사용자 자산이 아니다)"""
    억, 나머지 = divmod(int(round(원)), 100_000_000)
    만 = int(round(나머지 / 1_000_000)) * 100
    if 만 >= 10000:
        억, 만 = 억 + 1, 0
    if 억 and 만:
        return f"{억}억 {만:,}만 원"
    return f"{억}억 원" if 억 else f"{만:,}만 원"


def _가정금액말():
    r"""화면의 금액(「2.92억」 등)이 무엇인지 한 문장 (2026-10-07).

    사용자 10/7: 「실제 금액이 아닌 이해를 위해 가정 계산 금액은 써도 되고, 그거에 대해 설명만 잘 되어있으면 돼!」
    — 그때 화면 어디에도 「500만 원으로 시작했다면」 이 없었다(게시본 전체 확인).
    시작 금액 = rule-capital.json 시작자산 · 시작 달 = rule-cases.json 기간 첫 날. 둘 중 하나라도 없으면 빈 글(지어내지 않는다).
    """
    try:
        cp = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8-sig"))
        시작 = float(cp.get("시작자산") or 0)
        rc = json.load(io.open(os.path.join(_DATA, "rule-cases.json"), encoding="utf-8-sig"))
        첫 = str(rc.get("기간") or "")[:10]
        if not 시작 or len(첫) != 10:
            return ""
        return (f"금액은 실제 돈이 아니라, {int(첫[:4])}년 {int(첫[5:7])}월에 {_억만(시작)}으로 시작해 "
                f"이 규칙대로 사고팔았다고 가정한 계산입니다. ")
    except Exception:  # noqa: BLE001
        return ""


def _또사기문(묶):
    r"""「또 사기」 가정 문장(HTML) — PC 6장과 핸드폰 가정 카드가 같이 쓴다. `묶` = 숫자를 굵게 묶는 함수. 자료가 없으면 빈 글"""
    try:
        cp = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8-sig"))
        g = cp.get("또사기금지") or {}
        덜, 끝, 낙 = g.get("덜번비율"), g.get("끝자산"), g.get("계좌낙폭")
        낙 = (cp.get("종가") or {}).get("또사기금지_계좌낙폭", 낙)
    except Exception:  # noqa: BLE001
        return ""
    if 덜 is None or 끝 is None or 낙 is None:
        return ""
    낙글 = f"{낙:g}%".replace("-", "−")
    return (_esc("이미 들고 있는 종목이 다시 후보에 뜨면 또 산다고 가정한 성적입니다. "
                 "다시 뜨는 것은 산 뒤 더 빠졌다는 뜻이라, 더 사지 않았다면 이보다 약 ")
            + 묶(f"{덜:.0f}%") + _esc(" 낮았습니다(같은 기간 ") + 묶(_억만(끝))
            + _esc(" · 계좌 낙폭" + ("(매일 종가)" if _종가기준() else "") + " ") + 묶(낙글 + ")."))


def _또사기가정():
    r"""6장 비교 줄 아래 「또 사기」 가정 문구 (QUANT-ASSUME-1001 · 2026-10-01).

    사용자: 「또 사기 허용하고 화면에 그 내용만 적시하면 될 것 같은데?」
    숫자 셋은 `rule-capital.json` 「또사기금지」에서 읽는다 — 비교 줄(sell-options.json)·5장·7장과 **같은 판**
    (gate7 CARDLIVE · 지금 실전 규칙 · 제약 있는 판 · 시드 500만). 자료가 없으면 **블록을 뺀다**(지어내지 않는다).
    ⚠️ 숫자+단위+조사는 한 묶음 nowrap — `_굵` 은 「4,800만」의 「만」을 조사로 읽어 쪼갤 수 있어 여기서 직접 묶는다.
       낙폭은 하락색을 쓰지 않는다(가정 설명이라 먹색 굵게만)
    """
    try:
        cp = json.load(io.open(os.path.join(_DATA, "rule-capital.json"), encoding="utf-8-sig"))
        g = cp.get("또사기금지") or {}
        덜, 끝, 낙 = g.get("덜번비율"), g.get("끝자산"), g.get("계좌낙폭")
        # ⭐ 10/2 사실 바로잡기 — 종가 기준 칸이 있으면 그 낙폭 (산 값 기준 −7.4% ↔ 종가 −40% 대)
        낙 = (cp.get("종가") or {}).get("또사기금지_계좌낙폭", 낙)
    except Exception:  # noqa: BLE001
        덜 = 끝 = 낙 = None
    _설명 = _가정금액말()
    if 덜 is None or 끝 is None or 낙 is None:
        if not _설명:
            return ""
        return (f'<div style="display:flex;flex-direction:column;gap:10px;border-top:1px solid {C["선"]};'
                f'padding-top:18px">'
                f'<span style="font-size:26px;font-weight:700;color:{C["금"]}">'
                f'{_esc("이 성적의 가정 · 이 장과 다음 장 숫자 모두")}</span>'
                f'<span style="font-size:31px;line-height:1.55;color:{C["본"]}">{_esc(_설명.strip())}</span>'
                f'</div>')

    def 묶(v):
        return f'<b style="font-weight:800;color:{C["먹"]};white-space:nowrap">{_esc(v)}</b>'
    본 = _esc(_설명) + _또사기문(묶)
    return (f'<div style="display:flex;flex-direction:column;gap:10px;border-top:1px solid {C["선"]};'
            f'padding-top:18px">'
            f'<span style="font-size:26px;font-weight:700;color:{C["금"]}">'
            f'{_esc("이 성적의 가정 · 이 장과 다음 장 숫자 모두")}</span>'
            f'<span style="font-size:31px;line-height:1.55;color:{C["본"]}">{본}</span>'
            f'</div>')


# ── 3장 · 어떻게 사고 파나 (라벨 2열형) ──────────────────────────
def _사고팔기글():
    r"""「어떻게 사고 파나」 글 조각 — PC 5장(_장3)은 이어 붙이고 핸드폰 카드는 시간순 칸에 나눠 쓴다 (10/16 · 글은 여기 한 곳)"""
    옛낙, 새낙 = _계좌낙폭()
    앞, 뒤 = R.몫들[0], R.몫들[1]
    g = {"앞": 앞, "뒤": 뒤}
    g["머리말"] = "규칙이 정하는 것은 언제 사고 언제 파는지 둘뿐입니다. 얼마를 넣을지는 정하지 않습니다."
    # ⭐ 2026-10-13 — 「후보들의 예상체결가 중앙값보다 빠진 것만 산다」 는 옛 말이었다(9/14 부터 시장 표본 30종목) ·
    #    또 예상가는 튄다 → **문턱가 지정가 · 9시 시가가 닿아야 산다** (사용자 「응」) · 업종 갈래는 10/13 뺐다
    g["판정제목"] = "5분, 여기서 살지 정해진다"
    g["문턱"] = (f"시장 대표 30종목의 예상 시작 갭(중앙값)보다 "
               f"{abs(R.상대갭문턱):g}%p 더 싸게 시작하는 값(문턱가)을 종목마다 내고, 그 값에 지정가를 겁니다"
               + (f"(업종 규칙 종목은 {abs(R.업종전용상대갭):g}%p"
                  # ⭐ 2026-09-30 — 원전 기자재
                  + "".join(f" · {n} 종목은 {abs(v['상대갭']):g}%p" for n, v in getattr(R, "바구니전용", {}).items())
                  + ")"
                  if (getattr(R, "업종전용상대갭", None) is not None and getattr(R, "업종규칙_켬", False)) else ""))
    g["시가"] = "9시 시가가 문턱가 이하일 때만 사고, 더 높게 시작하면 사지 않습니다"
    g["시가제목"], g["시가본"] = "9시 시가가 문턱가 이하일 때만 삽니다", "더 높게 시작하면 사지 않습니다."
    g["예상"] = "예상체결가는 주문이 얇아 자주 튀어서 판단에 쓰지 않습니다"
    g["자리"] = (f"하루 최대 {R.오늘최대종목(None)}종목"
               + (f"이고, 섹터 규칙 종목은 {R.섹터전용자리}종목"
                  + "".join(f", {n} 종목은 {v['자리']}종목" for n, v in getattr(R, "바구니전용", {}).items())
                  + "까지 더 삽니다."
                  if getattr(R, "섹터전용자리", 0) else "입니다.")
               + (f" 지수가 20일에 {abs(R.빠지는장문턱):g}% 넘게 빠진 날은 "
                  f"{R.빠지는장최대종목}종목까지 삽니다." if R.빠지는장_켬 else ""))
    g["갭하한"] = (f"예상체결가가 전날보다 {abs(R.예상갭하한):g}% 넘게 빠진 종목은 사지 않습니다. 호가가 얇아 나온 가짜 값이거나 "
                f"진짜 폭락이거나, 둘 다 살 이유가 아닙니다.")
    g["취소"], g["없음"] = "체결 안 된 주문은 반드시 취소하세요", "맞는 게 없으면 아무것도 사지 않습니다."
    # ⭐ 몫 이름과 조사는 `_몫말` 이 정한다 — 50:50 「반은/나머지 반은」, 그 밖엔 「30%는/나머지 70%는」
    g["나눔"] = (f"한 종목을 사면 주문을 둘로 나눠 겁니다. 산 주식의 {_몫말(앞[0])} +{앞[1]:g}%에 팔아 이익을 "
               f"일찍 챙기고, {_몫말(뒤[0], 뒤=True)} +{뒤[1]:g}%까지 기다립니다.")
    # ⭐ 2026-09-28 — **문장이 효과를 과장하고 있었다.** 옛 값(9.0→6.2)은 2026-09-14 에
    #    손으로 적은 것이고, 지금 규칙으로 다시 재니 11.3% → 11.0% 로 **거의 안 줄었다**.
    #    나눠 팔기의 진짜 값은 낙폭이 아니라 **돈**이다 (11년 성적 1.25배).
    #    ⓘ 이 문장은 배수로 적는다 (9/28 표현 선택 · 10/7 사용자 확인: 「금액 안 씀」 원칙은 **실제 포트폴리오 금액**이다 — 시뮬 금액은 해당 없음)
    # ⭐ 10/2 — 종가 기준으로 바뀌면 「줄었다」 가 사실이 아닐 수 있다 ⇒ 숫자 크기로 말을 고른다
    g["배수"] = (f"나눠 팔면 11년 성적이 {_배수():.2f}배가 되고, 계좌 흔들림{'(매일 종가로 평가)은' if _종가기준() else '도'} "
               f"{abs(옛낙):.1f}% → {abs(새낙):.1f}%"
               + (("로 조금 줄었습니다." if abs(abs(옛낙) - abs(새낙)) < 3 else "로 줄었습니다.") if abs(새낙) < abs(옛낙) - 0.05 else
                  (("로 조금 늘었습니다." if abs(abs(옛낙) - abs(새낙)) < 3 else "로 늘었습니다.") if abs(새낙) > abs(옛낙) + 0.05
                   else "로 거의 같습니다."))
               if _배수() else
               f"나눠 팔면 계좌 흔들림이 {abs(옛낙):.1f}% → {abs(새낙):.1f}%"
               + ("로 줄었습니다." if abs(새낙) < abs(옛낙) - 0.05 else "입니다."))
    g["기한"] = (f"{_몫말(앞[0], 앞뒤=True)} {앞[2]}거래일, {_몫말(뒤[0], 뒤=True, 앞뒤=True)} {뒤[2]}거래일이 "
               f"지나면 그날 값으로 정리합니다.")
    g["손절"] = ("손절은 하지 않습니다. 값이 빠졌다는 이유로 중간에 팔지 않습니다."
               # ⭐ 2026-09-29 밤 — 악재 매도(오늘 반영)가 화면에 없었다. 「중간에 팔지 않는다」만 보면 모른다
               + (f" 다만 들고 있는 종목에 {'·'.join(_파는말())} 공시가 뜨면 다음 날 시가에 팝니다."
                  if _파는말() else ""))
    return g


def _장3():
    g = _사고팔기글()
    앞, 뒤 = g["앞"], g["뒤"]
    블록 = (
        ("어떻게 사나",
         [f"{R.판정시각}에 {g['판정제목']}. {g['문턱']}. {g['시가']}. {g['예상']}. {g['자리']}",
          g["갭하한"],
          f"09:01에 {g['취소']}. {g['없음']}"]),
        ("목표에 닿으면 · 둘로 나눠 판다", [g["나눔"], g["배수"]]),
        ("목표에 안 닿으면 · 날짜로 끝낸다", [g["기한"], g["손절"]]),
    )
    def _행(라, 줄들):
        return (
        f'<div style="display:flex;gap:28px;border-top:1px solid {C["선"]};padding-top:18px">'
        # ⭐ QUANT-FIX-0929 C — 라벨 `목표에 닿으면 · 둘로 나눠 판다` 가
        #    `목표에 닿으면 ·` ↵ `둘로 나눠 판다` 로 끊겼다.
        #    가운뎃점을 빼고 **두 줄로 고정**한다 (말은 그대로)
        f'<span style="flex:none;width:210px;text-align:right;font-size:28px;font-weight:700;'
        f'line-height:1.35;color:{C["금"]}">'
        + "<br>".join(_esc(z) for z in 라.split(" · ")) + '</span>'
        f'<div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:9px;'
        f'border-left:1px solid {C["선"]};padding-left:28px">'
        # 줄은 글(31px 본문) 또는 (글, 크기) — 크기가 오면 보조색 각주 꼴 (비교 줄)
        + "".join(_본문(_묶음(_굵(x)))
                  if isinstance(x, str) else
                  _본문(_묶음(_굵(x[0])), x[1], 1.5, C["보"])
                  for x in 줄들) + '</div></div>')
    행들 = [_행(라, 줄들) for 라, 줄들 in 블록]
    # ⭐ 비교 줄은 **블록 밖 · 세 블록 다 끝난 뒤** (디자인 답 2 · 2026-09-14).
    #    「목표에 닿으면」 안에 두면 그 블록만 규칙이 둘인 것처럼 보인다. 각주 계단(25px 보조색)
    비교 = "".join(_본문(_묶음(_굵(x[0])), x[1], 1.5, C["보"]) for x in _선택지(앞, 뒤))
    # ⭐⭐ 2026-09-29 밤 QUANT-PICK-0929 5장 — **두 장으로 나눈다 (a).**
    #    설명글(업종 −1.5%p · 섹터 +2 · 감자·유상증자 매도)이 늘어 항목 사이 0px · 아래 78px.
    #    문서 순서대로 (b) 라벨 열 170 + (c) 리드 31 을 먼저 해 봤다 → 아래 90px 이 됐지만
    #    **항목 사이는 여전히 0px** (기준 ≥ 20). 그래서 (a) · (b)(c) 는 되돌렸다.
    #    1장 = 어떻게 사나 · 목표에 닿으면 / 2장 = 목표에 안 닿으면(감자·유상증자 매도 포함) ·
    #    비교 줄 · 각주. 두 장 모두 위로 붙이고 56px 고정. 글은 한 글자도 안 줄였다
    # ⭐ ANSWER-0929-7 답 1 — **나누는 선** = 첫 장에 두는 블록 수. 블록 경계마다 옮겨 재고
    #    두 장 아래 여백 차가 가장 작은 선을 골랐다 (비교 줄은 「목표에 안 닿으면」과 같은 장,
    #    각주는 둘째 장 맨 아래)
    몸1 = (_본문(_esc(g["머리말"]), 35)
          + "".join(행들[:_5장선]))
    몸2 = ("".join(행들[_5장선:])
          + 비교
          + _또사기가정()
          + f'<span style="font-size:25px;line-height:1.55;color:{C["보"]}">다음 장은 이 규칙이 '
            f'과거에 어땠는지입니다.</span>')
    return [_카드("퀀트3 사고파나", _머리("HOW TO BUY &amp; SELL", _쪽표, "어떻게 사고 파나"), 몸1,
                  정렬="flex-start", 틈=56),
            _카드("퀀트3 사고파나2", _머리("HOW TO BUY &amp; SELL", _쪽표, "어떻게 사고 파나 (이어서)"),
                  몸2, 정렬="flex-start", 틈=56)]


# ── 4장 · 과거에 어땠나 ─────────────────────────────────────────
def _수익색(v):
    return C["빨"] if (v or 0) >= 0 else C["파"]


_성적머리말 = "이 규칙이 과거에 있었다면 이렇게 됐을 것입니다. 컴퓨터가 옛 주가로 계산한 것입니다."
_성적주의 = ("위 숫자는 전부 과거 자료로 계산한 것입니다.", "「과거에 이랬다」이지 「앞으로 이럴 것」이 아닙니다.",
          "실제로 산 기록은 오늘부터 쌓입니다.", "매수 추천이 아닙니다.", "판단과 책임은 본인에게 있습니다.")
# ⭐ 10/20 사용자 「오케이 너의 권고대로 하자!」 — BOLLWALK: 볼린저 −1.0 은 16년을 다 보고 고른 값 · 그때그때 골랐다면 65~80%
_볼린저주의 = ("실제보다 좋게 나왔을 수 있습니다",
          "규칙의 문턱 하나(볼린저 −1.0)는 16년 자료를 다 보고 고른 값입니다. 그때그때 과거 자료로 골랐다면 이 성적의 65~80%쯤이었습니다.")


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
            + 셀("날짜", 200, 24, C["보"]) + 셀("종목", 220, 24, C["보"], 늘=True)
            + 셀("산 값", 140, 24, C["보"], 오른=True) + 셀("수익률", 130, 24, C["보"], 오른=True)
            + 셀("며칠", 90, 24, C["보"], 오른=True) + '</div>')
    행들 = ""
    for r in (s.get("최근") or [])[:3]:
        결 = r.get("결과")
        행들 += ('<div style="display:flex;align-items:baseline;gap:14px;white-space:nowrap;'
               f'padding:9px 0;border-bottom:1px solid {C["선"]}">'
               + 셀(r.get("날짜", ""), 200, 26, C["보"])
               + 셀(r.get("이름", ""), 220, 31, C["먹"], 굵=700, 늘=True)
               + 셀(f'{r.get("매수가", 0):,}원', 140, 26, C["본"], 오른=True)    # ⭐ 0929-2 ⑤ 「283,000원」이 12px 넘쳤다
               + 셀(_음(결, 1) if 결 is not None else "—", 130, 31, _수익색(결), 굵=800, 오른=True)
               + 셀(f'{r.get("며칠")}일' if r.get("며칠") is not None else "—", 90, 26, C["보"], 오른=True)
               + '</div>')
    표 = f'<div class="qtbl" style="display:flex;flex-direction:column">{머리행}{행들}</div>'   # 10/14 qtbl — 폰 판에서 칸 폭을 글에 맞춘다

    # 가장 좋았던 셋 — 코드가 채운다 (6절 1). 자료에 없으면 지어내지 않는다
    최고 = s.get("최고") or []
    if 최고:
        # ⭐ QUANT-FIX-0929 C — **종목 한 건이 통째로 한 묶음**이다.
        #    전에는 `(2일)` 만 nowrap 이라 `+29.7% (2일)` 이 둘째 줄로 떨어졌다
        좋 = _본문(_점안끊김(" · ".join(
            f'<span style="white-space:nowrap">{_esc(r.get("이름", ""))} '
            f'{강(_음(r.get("결과", 0), 1), C["빨"])} ({r.get("며칠")}일)</span>'
            for r in 최고[:3])))
    else:
        좋 = _본문("코드 확인 뒤 채웁니다", 색=C["보"])
    # 가장 나빴던 셋 + 손실 거래 평균 (6절 2 — 있을 때만)
    나 = _본문(_점안끊김(" · ".join(
        f'<span style="white-space:nowrap">{_esc(r.get("이름", ""))} '
        f'{강(_음(r.get("결과", 0), 1), C["파"])}</span>'
        for r in (s.get("최악") or [])[:3])))
    if s.get("손실평균") is not None and s.get("손실건수"):
        나 += _본문(f'손실로 끝난 {강(f"{s["손실건수"]}건")}의 평균은 '
                  f'{강(_음(s["손실평균"], 1), C["파"])}였습니다.')

    각주 = " ".join(_성적주의) + " " + _볼린저주의[0] + " — " + _볼린저주의[1]
    몸 = (_본문(_esc(_성적머리말), 31, 1.6)
         + _블록("10년 남짓을 계산하면", 요약, 틈=10)
         + _블록("최근 3건", 표)
         + _블록("가장 좋았던 셋", 좋, 틈=10)
         + _블록("가장 나빴던 셋", 나, 틈=10)
         + f'<span style="font-size:25px;line-height:1.55;color:{C["보"]}">{_esc(각주)}</span>')
    # ⚠️ 0929-2 새 판 ★(56 고정)을 걸면 아래 여백이 **24px** — 꽉 찬 장이다. 전처럼 둔다(디자인에 물었다)
    return _카드("퀀트4 성적표", _머리("TRACK RECORD", _쪽표, "과거에 어땠나", 부제=_esc(부제), 틈=18, 밑=28), 몸,
                 정렬=None)


_다음쪽 = "@@NEXTPAGE@@"   # 「다음 장 번호」 표식 — `_쪽번호매기기` 가 바꾼다


def _쪽번호매기기(장들):
    r"""`1 / 4` 를 **전체 장 수**에 맞춰 다시 매긴다 (2026-09-29).

    1장이 여러 쪽으로 늘면 뒤 장의 번호도 밀린다. 손으로 적으면 어긋난다
    ([[hand-written-numbers-freeze]]) — 여기서 한 번에 센다
    """
    _n = len(장들)
    _밖 = []
    for _i, _h in enumerate(장들, 1):
        # ⭐ QUANT-FIX-0929 A — 표식 하나만 바꾼다. 장이 제 번호를 셈하지 않으므로
        #    장 수가 어떻게 바뀌어도 어긋날 데가 없다
        _밖.append(_h.replace(_쪽표, f"{_i} / {_n}").replace(_다음쪽, str(_i + 1)))
    _남 = [h for h in _밖 if _쪽표 in h or _다음쪽 in h]
    assert not _남, f"쪽 번호 표식이 안 바뀐 장 {len(_남)}개"
    return "".join(_밖)


# ── 화면 ────────────────────────────────────────────────────────
def _묵은종가(q):
    r"""후보가 **직전 거래일 종가가 아닌** 자료로 골라졌으면 경고 한 줄 (2026-10-07).

    사용자 10/7: 「묵은 종가인지 모르니까 여태까지 조용히 넘어간거 아니야?」 — 맞다. 견주는 곳이 없었다
    (10/6 08:14~08:55 · 10/1 종가로 고른 후보가 경고 없이 떠 있었다).
    기준 = forward-log 줄의 **기록시각 날짜의 직전 거래일**(krx_calendar). 페이지를 언제 다시 만들든 같은 답.
    신호기준일이 그보다 **앞**일 때만 띄운다. 평소엔 아무것도 안 그린다.
    """
    try:
        from krx_calendar import 직전거래일
        import datetime as _dt
        기록 = str(q.get("기록시각") or "")[:10]
        신호 = str(q.get("신호기준일") or "")
        if len(기록) != 10 or len(신호) != 8:
            return ""
        기대 = 직전거래일(_dt.date.fromisoformat(기록))
        if not 기대 or 신호 >= f"{기대:%Y%m%d}":
            return ""
        신호글 = f"{int(신호[4:6])}/{int(신호[6:8])}"
        기대글 = f"{기대.month}/{기대.day}"
    except Exception:  # noqa: BLE001
        return ""
    return (f'<div role="alert" style="max-width:min(760px,calc(100vw - 32px));margin:12px auto 0;padding:10px 16px;box-sizing:border-box;'
            f'background:{C["경고"]};color:{C["빨"]};border:1px solid {C["빨"]};border-radius:8px;'
            f'font-size:15px;line-height:1.5;font-weight:700">'
            f'{_esc(f"⚠️ {기대글} 종가가 아직 안 들어와 {신호글} 종가로 고른 후보입니다. 오늘 사기 전에 확인하세요.")}'
            f'</div>')


# ⭐⭐ 2026-10-14 핸드폰 판 (사용자 「퀀트 A안 해도 되는데」)
#    카드는 1080 폭으로 그려 화면 폭에 맞춰 줄인다 → 393~430 폭 폰에서 **0.4배**라 숫자 12px · 항목 이름 10px 이었다.
#    폰에서는 **같은 카드 HTML** 의 px 값만 0.56 배로 바꾼 사본을 줄이지 않고(배율 1) 위아래로 잇는다.
#    ⚠️ 글을 두 벌로 적지 않는다 — 같은 함수가 낸 HTML 을 숫자만 바꾼다 (build_scroll._scale_px 와 같은 생각)
#    ⚠️ 카드 높이(1600) 고정·overflow:hidden 을 폰에서는 푼다 → **잘리는 내용이 없다**
_폰배 = 0.56
_폰폭 = 600     # 이 폭 이하에서 폰 판을 쓴다


def _폰사본(html_):
    r"""인라인 `Npx` 를 _폰배 만큼 줄인다. 1px 선은 1px 로 둔다"""
    def _바(m):
        v = float(m.group(1))
        if v <= 1:
            return m.group(0)
        n = round(v * _폰배, 1)
        return f"{n:g}px"
    return re.sub(r"(?<![\w.])(\d+(?:\.\d+)?)px", _바, html_)


_폰CSS = (
    "<style>"
    ".qmob{display:none}"
    f"@media(max-width:{_폰폭}px){{"
    "#qt .qrail{display:none!important}"
    # ⭐ 10/14 저녁 — **가로 넘김으로 되돌림** (사용자 「퀀트 후보 가로 페이지였는데 세로 넘김으로 바꿔놨네. 가로 바꿔!」)
    #    글자 크기(0.56배 사본)는 그대로 · 한 장씩 옆으로 넘기고 제자리에 멈춘다(scroll-snap) · 장마다 높이는 제 내용만큼
    "#qt .qmob{display:flex;flex-direction:row;align-items:flex-start;gap:12px;padding:12px 16px 14px;box-sizing:border-box;width:100%;"
    "overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;scrollbar-width:none;touch-action:pan-x pan-y}"
    "#qt .qmob::-webkit-scrollbar{display:none}"
    "#qt .qmob section[data-label]{flex:0 0 100%!important;scroll-snap-align:center;scroll-snap-stop:always;"
    "width:auto!important;height:auto!important;overflow:visible!important;"
    "padding:24px 18px!important;border-radius:16px!important}"
    "#qt .qhint{display:block!important;padding:4px 0 26px!important}"
    "#qt .qmob section [style*='letter-spacing:.1em']{flex:0 1 auto!important;min-width:0}"   # 10/14 영문 머리글이 320 폭에서 쪽 번호를 밀어냈다
    "#qt .qmob [data-body]{flex:none!important;min-height:0;padding-left:0!important;padding-right:0!important}"
    "#qt .qmob [data-block]{max-height:none!important;flex:none!important;padding:12px 14px!important}"
    # 줄바꿈 금지로 묶은 긴 글(괄호 설명 등)은 폰 폭을 넘는다 → 폰에서만 풀어 준다 (숫자 칸·표는 아래에서 다시 묶는다)
    "#qt .qmob [style*='white-space:nowrap']{white-space:normal!important}"
    "#qt .qmob .qrow{flex-wrap:nowrap;column-gap:14px;white-space:normal;padding:8px 0!important}"
    "#qt .qmob .qpair{flex:1 1 0!important;min-width:0;flex-direction:column;align-items:flex-start!important;gap:2px!important}"
    "#qt .qmob .qlab{width:auto!important;white-space:normal}"
    "#qt .qmob .qval{flex:1 1 auto!important;width:auto!important;white-space:normal!important;word-break:keep-all}"
    "#qt .qmob .qhead1{flex-wrap:wrap;row-gap:6px;white-space:normal}"
    "#qt .qmob .qhead1>span[style*='flex:1']{display:none}"
    "#qt .qmob .qtbl>div{display:grid!important;grid-template-columns:minmax(0,1fr) 76px 72px 36px;column-gap:8px!important;row-gap:2px!important;align-items:baseline}"
    "#qt .qmob .qtbl>div>span:first-child{grid-column:1/-1}"
    "#qt .qmob .qtbl span{flex:0 0 auto!important;width:auto!important;min-width:0!important;white-space:nowrap!important}"
    "#qt .qmob .qtbl span:nth-child(2){white-space:normal!important}"
    "#qt .qmob .qtbl>div>span:nth-child(3){grid-column:2}"
    "#qt .qmob .qtbl>div>span:nth-child(4){grid-column:3}"
    "#qt .qmob .qtbl>div>span:nth-child(5){grid-column:4}"
    # 10/14 제목 줄 높이 고정(두 장 머리 맞춤용)은 폰에서 풀어 준다 · 두 줄이 되면 위 줄을 덮었다
    "#qt .qmob .qtitleh{height:auto!important}"
    "#qt .qmob *{max-width:100%}"
    "}"
    # 아주 좁은 폰(아이폰 SE 320)은 종목 이름 칸이 37px 뿐이다 → 이름을 날짜 아래 제 줄로
    "@media(max-width:360px){#qt .qmob .qtbl>div>span:nth-child(2){grid-column:1/-1}}"
    "</style>")


# ⭐⭐ 2026-10-14 퀀트 「지난 날」 (사용자 10/14 「지난 브리핑 보기가 … 퀀트 후보의 과거는 못 보잖아」 · 「그대로 반영하자」)
#    ‹ 날짜 › 로 지난 날로 가면 그날 산 것과 **그 뒤 결과**를 한 장 표로 보여 준다. 오늘은 카드 그대로.
#    값: forward-log 그날 줄(주문가 · 매수가=그날 실제 시가 · 체결) + krx-daily 최근 종가
#    ⚠️ 「지금까지」 는 **최근 종가 ÷ 매수가** 다 — 40%/60% 나눠 팔기 전 값이다 (표 아래에 그대로 적는다)
#    ⚠️ 체결 표시가 없는 줄(채점 전)은 「채점 전」 으로 둔다 · 지어내지 않는다
_지난CSS = (
    "<style>"
    ".qpast{max-width:760px;margin:12px auto 28px;padding:20px 18px;background:#f2efe8;border-radius:16px;box-sizing:border-box;width:calc(100% - 24px)}"
    ".qpast .k{font-size:12.5px;font-weight:700;color:#8a7038;letter-spacing:.04em}"
    ".qpast h3{font-size:24px;margin:4px 0 0;letter-spacing:-.03em;color:#1c1813}"
    ".qpast .sum{font-size:14px;color:#4b4740;margin-top:6px;line-height:1.6}"
    ".qpast table{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px;font-feature-settings:'tnum'}"
    ".qpast th{font-weight:500;font-size:11.5px;color:#7c766b;text-align:left;padding:6px 4px;border-bottom:1.5px solid #1c1813;white-space:nowrap}"
    ".qpast td{padding:9px 4px;border-bottom:1px solid #d5cec0;vertical-align:top;color:#1c1813}"
    ".qpast td.r,.qpast th.r{text-align:right}"
    ".qpast td small{display:block;font-size:11px;color:#7c766b}"
    ".qpast .tag{display:inline-block;font-size:11px;font-weight:700;border-radius:5px;padding:1px 6px;white-space:nowrap}"
    ".qpast .y{background:#1c1813;color:#fff}.qpast .n{background:#e8e3d8;color:#6b665c}.qpast .w{background:#fff;color:#8a7038;border:1px solid #d5cec0}"
    ".qpast .foot{font-size:12px;color:#7c766b;margin-top:12px;line-height:1.6}"
    "#qt.past .qrail,#qt.past .qmob,#qt.past .qm45,#qt.past .qhint,#qt.past [role=alert]{display:none!important}"
    "</style>")


def _최근종가():
    r"""krx-daily 마지막 파일의 {종목코드: 종가} 와 그 날짜"""
    import glob as _g
    _K = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "krx-daily")
    _fs = sorted(_g.glob(os.path.join(_K, "*.json")))
    if not _fs:
        return {}, ""
    try:
        j = json.load(io.open(_fs[-1], encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}, ""
    return ({c: v.get("종가") for c, v in (j.get("종목") or {}).items()}, str(j.get("기준일") or ""))


def _지난한날(d, r, 종가, 기준):
    r"""지난 하루치 표 HTML. d='YYYY-MM-DD', r=forward-log 그날 줄"""
    import datetime as _dt
    _d = _dt.date.fromisoformat(d)
    _요 = "월화수목금토일"[_d.weekday()]
    _시 = str(((r.get("동시호가") or {}).get("잰시각")) or "")[11:16]
    후보 = r.get("후보") or []
    산 = [x for x in 후보 if x.get("오늘산다")]
    _기 = f"{int(기준[4:6])}/{int(기준[6:8])}" if len(기준) == 8 else "최근"
    if not 산:
        본 = (f'<h3>그날 살 것: 없음</h3>'
              f'<div class="sum">후보 {len(후보)}개 중 문턱가까지 내려온 종목이 없어 주문을 내지 않았습니다.</div>')
    else:
        줄, 체, 수 = [], 0, []
        for x in 산:
            _주 = x.get("주문가") or x.get("문턱가")
            _매 = x.get("매수가")
            _체 = x.get("체결")
            if _체 is True:
                체 += 1
                _태 = '<span class="tag y">체결</span>'
            elif _체 is False:
                _태 = '<span class="tag n">못 삼</span>'
            else:
                _태 = '<span class="tag w">채점 전</span>'
            _지 = "·"
            _c = 종가.get(str(x.get("종목코드") or ""))
            if _체 is True and _매 and _c:
                _p = (float(_c) / float(_매) - 1) * 100
                수.append(_p)
                _색 = "#C8352B" if _p > 0 else ("#2050C8" if _p < 0 else "#4b4740")
                _지 = f'<b style="color:{_색}">{"+" if _p > 0 else ("−" if _p < 0 else "")}{abs(_p):.1f}%</b>'
            줄.append(f'<tr><td>{_esc(x.get("이름", ""))}<small>{_esc(x.get("종목코드", ""))}</small></td>'
                      f'<td class="r">{f"{int(_주):,}" if _주 else "·"}</td>'
                      f'<td class="r">{f"{int(_매):,}" if _매 else "·"}</td>'
                      f'<td>{_태}</td><td class="r">{_지}</td></tr>')
        _평 = (f" · 체결된 것 평균 {'+' if sum(수) / len(수) > 0 else '−'}{abs(sum(수) / len(수)):.1f}%" if 수 else "")
        본 = (f'<h3>그날 살 것: {len(산)}개</h3>'
              f'<div class="sum">지정가 {len(산)}개 중 체결 {체}개{_평} ({_기} 종가 기준)</div>'
              f'<table><tr><th>종목</th><th class="r">주문가</th><th class="r">그날 시가</th><th>체결</th><th class="r">지금까지</th></tr>'
              + "".join(줄) + '</table>')
    return (f'<div class="qpast" data-d="{d}" hidden>'
            f'<div class="k">QUANT · {_d.month}/{_d.day}({_요}){f" {_시} 확정" if _시 else ""}</div>'
            + 본
            + '<div class="foot">「못 삼」 = 9시 시가가 주문가보다 높아 체결되지 않은 것 · 「지금까지」 = 최근 종가 ÷ 그날 시가 (나눠 팔기 전 값) · '
              '10/13 전에는 지정가가 아니라 예상가로 사던 때라 체결 표시가 없을 수 있습니다 · 매수 추천이 아닙니다</div>'
            f'</div>')


def _지난들(줄들, 오늘):
    r"""forward-log 전체 → (날짜 목록, 지난 날 HTML). 같은 날 줄이 여럿이면 마지막 것"""
    날별 = {}
    for r in 줄들 or []:
        d = str(r.get("기록시각") or "")[:10]
        if len(d) == 10:
            날별[d] = r
    날들 = sorted(날별)[-35:]
    if not 날들:
        return [], ""
    종가, 기준 = _최근종가()
    html = "".join(_지난한날(d, 날별[d], 종가, 기준) for d in 날들 if d != 오늘)
    return 날들, html


# ════════════════════════════════════════════════════════════════════
# ⭐⭐⭐ 2026-10-16 핸드폰 4:5 카드 (사용자 「핸드폰 퀀트 화면, 둘다 너 권고대로 반영하고 바꾸자!」)
#    시안 https://claude.ai/artifact/4HSDcSyGjwBswmCcb7V9ia 6판 그대로 · 폭 600 이하에서만 보인다(PC 는 .qrail 그대로)
#    · 카드는 4:5 고정 · 카드 폭 361 에서 1em=16px 로 **그림처럼 통째로** 커지고 작아진다(cqw)
#    · 글자 하한: 본문 약 13px · 라벨 11px · 숫자 15px — 넘치면 글자를 줄이지 않고 장을 나눈다(종목 장)
#    · 글·숫자는 PC 카드와 **같은 함수**에서 (_폰자료 · _종목값 · _뽑기글 · _사고팔기글 · _선택지 · _또사기문 · _사례)
#    · 상자 왼쪽 색 띠 금지 (사용자 10/16 「너무 클로드 같아」)
#    · 넘긴 뒤 카드가 화면 끝에 붙던 것 = scroll-padding 없음 → 넣었다
# ════════════════════════════════════════════════════════════════════
def _e(s):
    return _esc(str(s))


def _폰카드(킥커, 몸, 덧=""):
    return (f'<section class="c4{(" " + 덧) if 덧 else ""}" data-m45="1"><div class="k">'
            f'<span>{킥커}</span><span class="pg">{_쪽표}</span></div>{몸}</section>')


def _폰종목(x, 업종, 상태):
    v = _종목값(x, 업종, 상태)
    낙색 = (' style="color:%s"' % v["낙색"]) if v["낙색"] else ""
    갭 = (f'<strong>{_e(v["갭글"])}</strong>' if v["갭있음"] else f'<strong class="w sub">{_e(v["갭글"])}</strong>')
    값4 = _e(v["값4"]).replace("~", "~<wbr>")
    머리 = (f'<div class="s"><div class="sh"><b>{_e(v["이름"])}</b>'
            f'<i>{_e((v["업종"] + " · ") if v["업종"] else "")}{_e(v["코드"])}</i>'
            + (f'<span class="tg">{_e(v["딱지"])}</span>' if v["딱지"] else "") + '</div>')
    if 상태 == "pre":
        # 08:00 후보 — 상대갭은 아직 없다(「08:55 확정 뒤」 는 표지 첫 줄이 말한다) · 매수 적정 범위가 길어 두 칸을 준다
        return (머리 +
                f'<div class="g3"><div><small>{_e(v["낙라"])}</small><strong{낙색}>{_e(v["낙글"])}</strong></div>'
                f'<div><small>시가총액</small><strong>{_e(v["시총"])}</strong></div>'
                f'<div><small>이익 · 빚</small><strong>{_e(v["재"])}</strong></div></div>'
                f'<div class="g3"><div><small>전날 종가</small><strong>{_e(v["종가"])}</strong></div>'
                f'<div class="span2"><small>{_e(v["라4"])}</small><strong class="gd">{값4}</strong></div></div></div>')
    _팔 = _팔값(x) if 상태 == "buy" else None      # 10/20 ② 팔 값을 가격으로
    _팔줄 = (f'<div class="g3"><div class="span2"><small>{_e(_몫말(R.몫들[0][0])[:-1])} · {_e(_몫말(R.몫들[1][0], 뒤=True)[:-1])} 팔 값</small>'
            f'<strong class="pos">{_팔[0]:,} · {_팔[1]:,}원</strong></div></div>') if _팔 else ""
    return (머리 + _팔줄 +
            f'<div class="g3"><div><small>{_e(v["낙라"])}</small><strong{낙색}>{_e(v["낙글"])}</strong></div>'
            f'<div><small>상대갭</small>{갭}</div>'
            f'<div><small>{_e(v["라4"])}</small><strong class="gd{" w" if 상태 == "pre" else ""}">{값4}</strong></div></div>'
            f'<div class="g3"><div><small>전날 종가</small><strong>{_e(v["종가"])}</strong></div>'
            f'<div><small>시가총액</small><strong>{_e(v["시총"])}</strong></div>'
            f'<div><small>이익 · 빚</small><strong>{_e(v["재"])}</strong></div></div></div>')


def _폰표지(d, bg글):
    상태 = d.get("상태")
    목록 = d.get("목록") or []
    업 = d.get("업") or {}
    배색 = d.get("배색") or C["보"]
    몸 = (f'<p class="t">{_e(d.get("제", ""))}'
          + (f' <span class="badge" style="background:{배색}">{_e(d.get("배"))}</span>' if d.get("배") else "")
          + '</p>')
    for 말 in d.get("알림말") or []:
        몸 += f'<div class="alert">{_e(말)}</div>'
    if d.get("리드"):
        몸 += f'<p class="lead">{_e(d["리드"])}</p>'
    if 상태 == "none":
        g = _뽑기글()
        몸 += ('<div class="zero"><b>0개</b><span>조건을 통과한 종목이 없습니다. 규칙상 이런 날은 열흘에 세 번쯤 '
               '있습니다. 고장이 아닙니다.</span></div>')
        몸 += (f'<p class="note">후보가 되려면 먼저 1단계를 모두 통과하고 ({" · ".join(f"{a} {b}" for a, b in g["문들"])}), '
               f'{" · ".join(_갈래들)} {_갈래수} 중 하나에 걸려야 합니다. 오늘은 어느 것도 걸리지 않았습니다.'
               + (f" 들고 있는 것 {len(d.get('보유') or [])}개에는 +{R.앞몫목표:g}% · +{R.뒷몫목표:g}% 지정가가 걸려 있습니다."
                  if d.get("보유") else "") + '</p>')
        악 = _악재줄()
        if 악:
            몸 += '<div class="alert">' + re.sub(r"<[^>]+>", " ", 악.replace("<br>", " · ")).strip() + '</div>'
    elif 목록:
        # 08:00 후보는 상대갭이 아직 없다 — 종목 · 매수 적정 범위 두 칸 (범위가 길다)
        머리 = ("종목", "매수 적정 범위") if 상태 == "pre" else ("종목", "상대갭", "문턱가")
        줄 = ""
        for x in 목록:
            v = _종목값(x, (업.get(x.get("종목코드", "")) or {}).get("업종명") or (x.get("섹터") or ""), 상태)
            칸 = [v["값4"]] if 상태 == "pre" else [v["갭글"], v["값4"]]
            줄 += (f'<tr><td>{_e(v["이름"])}' + (f'<i>{_e(v["업종"])}</i>' if v["업종"] else "") + '</td>'
                   + "".join(f'<td{" class=th" if k == len(칸) - 1 else ""}>{_e(z)}</td>' for k, z in enumerate(칸))
                   + '</tr>')
        몸 += (f'<p class="lab" style="color:{d.get("라벨색") or C["보"]}">{_e(d.get("라벨", ""))}</p>'
               f'<table class="ct"><thead><tr>{"".join(f"<th>{z}</th>" for z in 머리)}</tr></thead>'
               f'<tbody>{줄}</tbody></table>')
    각 = " ".join(z for z in (d.get("각주") or "", bg글 or "") if z)
    if 각:
        몸 += f'<p class="note mt">{_e(각)}</p>'
    return _폰카드(_e(d.get("킥", "QUANT")), 몸, "dense" if len(목록) > 6 else "")


def _폰종목장들(d):
    목록 = d.get("목록") or []
    상태 = d.get("상태")
    if not 목록 or 상태 == "none":
        return []
    업 = d.get("업") or {}
    # PC 와 같은 나눔 — 한 장에 최대 _한장에(4) · 고르게 (6→3+3 · 8→4+4 · 5→3+2)
    # 10/20 — 사는 날은 상자에 「팔 값」 줄이 붙어 3개면 20~26px 잘렸다(실측) → 한 장에 2개
    _한 = 2 if 상태 == "buy" else (3 if d.get("왜") else _한장에)   # 08:00 상태 4개 + 「왜」 는 45~59px 잘렸다
    n쪽 = max(1, -(-len(목록) // _한))
    out, i0, 남 = [], 0, len(목록)
    이름 = {"buy": "살 종목", "wait": "참고 종목", "pre": "볼 종목"}.get(상태, "종목")
    for j in range(n쪽):
        m = -(-남 // (n쪽 - j))
        조각 = 목록[i0:i0 + m]
        상자 = "".join(_폰종목(x, (업.get(x.get("종목코드", "")) or {}).get("업종명") or (x.get("섹터") or ""), 상태)
                     for x in 조각)
        # 10/20 ① 「왜 오늘 이 종목인가」 는 첫 종목 장 맨 위에 (표지에 두면 19~26px 잘렸다)
        _왜글 = (f'<p class="lead"><b>왜 오늘 이 종목인가</b> · {_e(d["왜"])}</p>' if (j == 0 and d.get("왜")) else "")
        out.append(_폰카드(f"{이름} · {i0 + 1}~{i0 + m}", f'{_왜글}<div class="stks">{상자}</div>',
                         "dense" if m > 3 else ""))
        i0 += m
        남 -= m
    return out


def _폰뽑기():
    g = _뽑기글()
    def _칸(a, b):
        # PC 의 (값, 「이상 · 설명」) 한 쌍 → 핸드폰 (「값 이상」, 설명)
        for 앞말 in ("이상", "이하"):
            if b.startswith(앞말 + " · "):
                return f"{a} {앞말}", b[len(앞말) + 3:]
        return a, b.lstrip("· ").strip()
    줄 = ""
    for a, b in g["문들"]:
        값, 설명 = _칸(a, b)
        줄 += (f'<div class="li"><b>{_e(값)}</b><span>{_e(설명)}'
               + (f'<small>{_e(g["상한글"])}</small>' if 설명 == "시가총액" else "") + '</span></div>')
    줄 += '<div class="li"><b>제외</b><span>관리종목 · 우선주 · 스팩</span></div>'
    장1 = _폰카드("HOW THEY WERE PICKED",
               '<p class="t">어떻게 뽑았나 <small>① 먼저 거르는 조건</small></p>'
               f'<p class="lead">{_e(g["리드"])}</p>'
               '<p class="sub"><small>1단계</small>이걸 모두 통과해야 후보가 됩니다</p>'
               f'<div class="list">{줄}</div>')
    상자 = "".join(f'<div class="br"><h4><i>{_e(태)}</i></h4><p>{_e(글)}</p></div>' for 태, 글 in g["규칙"])
    장2 = _폰카드("HOW THEY WERE PICKED",
               f'<p class="t">어떻게 뽑았나 <small>② {_e(g["갈"])} 갈래</small></p>'
               f'<p class="sub"><small>2단계</small>하나에만 걸려도 후보<em>{_e(g["앞쪽"])}</em></p>'
               f'<div class="fill">{상자}</div>')
    return [장1, 장2]


def _폰사고팔기():
    g = _사고팔기글()
    앞, 뒤 = g["앞"], g["뒤"]
    사나 = _폰카드("HOW TO BUY",
                '<p class="t">어떻게 사나</p>'
                f'<p class="lead">{_e(g["머리말"])}</p>'
                '<div class="tl2">'
                f'<div class="t2"><b>{_e(R.판정시각)}</b><div><strong>{_e(g["판정제목"])}</strong>{_e(g["문턱"])}.</div></div>'
                f'<div class="t2"><b>09:00</b><div><strong>{_e(g["시가제목"])}</strong>{_e(g["시가본"])} {_e(g["자리"])}</div></div>'
                f'<div class="t2 red"><b>09:01</b><div><strong>{_e(g["취소"])}</strong>{_e(g["없음"])}</div></div>'
                '</div>'
                f'<div class="warn"><b>이럴 땐 안 삽니다</b> · {_e(g["예상"])}. {_e(g["갭하한"])}</div>')
    비 = _선택지(앞, 뒤)
    칸 = ""
    for 말, _ in 비:
        머, _, 나 = 말.partition(" · ")
        칸 += f'<div><b>{_e(머)}</b>{_e(나)}</div>'
    파나 = _폰카드("HOW TO SELL",
                '<p class="t">어떻게 파나</p>'
                f'<p class="lead">{_e(g["나눔"])}</p>'
                '<div class="half">'
                + "".join(f'<div class="hp"><span class="pct">{z[0] * 100:g}%</span><span class="tgt">+{z[1]:g}%에 팜</span>'
                          f'<small>못 닿으면 {z[2]}거래일이 지난 날 그날 값으로 정리</small></div>' for z in (앞, 뒤))
                + '</div>'
                f'<div class="warn">{_e(g["손절"])}</div>'
                f'<p class="note">{_e(g["배수"])}</p>'
                + (f'<div class="cmp2">{칸}</div>' if 칸 else ""))
    return [사나, 파나]


def _폰성적():
    s = _사례()
    기간 = str(s.get("기간") or "")
    년 = re.findall(r"(\d{4})-", 기간)
    부제 = f"{년[0]}~{년[-1]}" if len(년) >= 2 else 기간
    평균, 나쁨 = s.get("평균", 0) or 0, s.get("가장나쁨", 0) or 0
    칸 = [("산 횟수", f'{s.get("전체건수", 0)}번', ""), ("수익으로 끝남", f'{s.get("승률", 0)}%', ""),
          ("평균", _음(평균, 1), "pos"), ("평균 걸린 날", f'{s.get("평균보유", 0):.0f}일', ""),
          ("최악", _음(나쁨, 1), "neg")]
    if s.get("손실평균") is not None and s.get("손실건수"):
        칸.append((f'손실 {s["손실건수"]}건 평균', _음(s["손실평균"], 1), "neg"))
    표 = "".join(f'<tr><td>{_e(str(r.get("날짜", ""))[5:])} {_e(r.get("이름", ""))}</td>'
                f'<td>{r.get("매수가", 0):,}원</td>'
                f'<td class="{"pos" if (r.get("결과") or 0) >= 0 else "neg"}">'
                f'{_e(_음(r.get("결과"), 1)) if r.get("결과") is not None else "—"}</td>'
                f'<td>{_e(str(r.get("며칠")) + "일") if r.get("며칠") is not None else "—"}</td></tr>'
                for r in (s.get("최근") or [])[:3])
    좋 = " · ".join(f'{_e(r.get("이름", ""))} {_e(_음(r.get("결과", 0), 1))} ({r.get("며칠")}일)' for r in (s.get("최고") or [])[:3])
    나 = " · ".join(f'{_e(r.get("이름", ""))} {_e(_음(r.get("결과", 0), 1))}' for r in (s.get("최악") or [])[:3])
    성적 = _폰카드("TRACK RECORD",
                f'<p class="t">과거에 어땠나 <small>{_e(부제)}</small></p>'
                f'<p class="lead">{_e(_성적머리말)}</p>'
                '<div class="stat">' + "".join(f'<div><small>{_e(a)}</small><strong class="{c}">{_e(b)}</strong></div>' for a, b, c in 칸) + '</div>'
                + (f'<table class="rt"><thead><tr><th>최근 3건</th><th>산 값</th><th>수익률</th><th>며칠</th></tr></thead>'
                   f'<tbody>{표}</tbody></table>' if 표 else "")
                + '<div class="br bw">'
                + (f'<p><b class="pos">가장 좋았던 셋</b> {좋}</p>' if 좋 else "")
                + (f'<p><b class="neg">가장 나빴던 셋</b> {나}</p>' if 나 else "")
                + '</div>')
    또 = _또사기문(lambda z: f"<b>{_esc(z)}</b>")
    금 = _가정금액말().strip()
    줄 = []
    if 금:
        줄.append(("시작 금액", _e(금)))
    if 또:
        줄.append(("또 사는 것도 가정", 또))
    # 10/20 볼린저 주의는 이 줄에 붙인다 — 따로 한 줄을 두면 폭 320~430 에서 5px 잘렸다(글은 그대로 · 줄 제목만 합침)
    줄.append((_성적주의[1], _e(_성적주의[0] + " " + _성적주의[2] + " " + _볼린저주의[0] + " — " + _볼린저주의[1])))
    줄.append((_성적주의[3], _e(_성적주의[4])))
    가정 = _폰카드("TRACK RECORD", '<p class="t">이 성적의 가정</p><div class="notes">'
                 # ⚠️ 본문은 <span> 하나로 감싼다 — .nt 가 세로 flex 라 감싸지 않으면 굵은 숫자마다 줄이 갈렸다(10/16 사용자 「줄바꿈 이상한데?」)
                 + "".join(f'<div class="nt"><b>{_e(a)}</b><span>{b}</span></div>' for a, b in 줄) + '</div>')
    return [성적, 가정]


def _폰덱(q, 보유):
    r"""핸드폰 4:5 카드 전부 (HTML). _장1 이 먼저 돌아 _폰자료 를 채운 뒤에 부른다"""
    d = dict(_폰자료)
    장들 = [_폰표지(d, _B글(q))] + _폰종목장들(d) + _폰보완장들(q) + _폰뽑기()   # 10/20 보완 후보
    if _뽑기글()["업켬"]:
        # 업종 갈래가 켜진 날은 PC 업종 장을 옛 핸드폰 꼴로 덧붙인다(지금은 꺼짐)
        장들 += [f'<div class="qold">{_폰사본(h)}</div>' for h in _장2()[1:]]
    장들 += _폰사고팔기() + _폰성적() + _폰시험()   # 10/20 ③ 시험
    n = len(장들)
    return "".join(h.replace(_쪽표, f"{i} / {n}") for i, h in enumerate(장들, 1))


_폰45CSS = (
    "<style>"
    "#qt .qm45{display:none}"
    f"@media(max-width:{_폰폭}px){{"
    "#qt .qrail{display:none!important}"
    "#qt .qm45{display:flex;gap:12px;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scroll-padding-inline:16px;"
    "padding:12px 16px 10px;scrollbar-width:none;container-type:inline-size;-webkit-overflow-scrolling:touch;box-sizing:border-box;width:100%}"
    "#qt .qm45::-webkit-scrollbar{display:none}"
    "#qt .qhint{display:block!important;padding:4px 0 26px!important}"
    "}"
    # 카드 — 폭 361 에서 1em=16px · 4:5
    f"#qt .qm45 .c4{{flex:0 0 100%;min-width:0;height:125cqw;scroll-snap-align:start;scroll-snap-stop:always;overflow:hidden;"
    f"font-size:4.43vw;font-size:calc(100cqw / 22.5625);box-sizing:border-box;background:{C['카드']};color:{C['먹']};"
    f"border-radius:1em;padding:.85em .95em .75em;display:flex;flex-direction:column;gap:.36em;line-height:1.36;"
    f"word-break:keep-all;font-family:{SANS};font-feature-settings:'tnum';letter-spacing:-.01em}}"
    "#qt .qm45 .c4 *{box-sizing:border-box}"
    f"#qt .qm45 .k{{display:flex;align-items:center;gap:.5em;font-size:.75em;font-weight:700;letter-spacing:.06em;color:{C['금']}}}"
    f"#qt .qm45 .k::after{{content:'';flex:1;height:1px;background:{C['선']};order:1}}"
    "#qt .qm45 .k span:last-child{order:2;letter-spacing:0}"
    "#qt .qm45 .t{margin:0;font-size:1.45em;font-weight:800;letter-spacing:-.035em;line-height:1.2;display:flex;align-items:center;gap:.35em;flex-wrap:wrap}"
    f"#qt .qm45 .t small{{font-size:.55em;color:{C['보']};font-weight:700}}"
    "#qt .qm45 .badge{font-size:.55em;font-weight:700;color:#fff;border-radius:.35em;padding:.2em .55em;letter-spacing:0}"
    f"#qt .qm45 .lead{{margin:0;font-size:.84em;color:{C['본']};line-height:1.38}}"
    f"#qt .qm45 .note{{margin:0;font-size:.76em;color:{C['보']};line-height:1.4}}"
    "#qt .qm45 .note b{color:inherit}"
    "#qt .qm45 .mt{margin-top:auto}"
    f"#qt .qm45 .lab{{margin:0;font-size:.8em;font-weight:700}}"
    f"#qt .qm45 .alert{{background:{C['경고']};color:{C['빨']};border-radius:.6em;padding:.45em .7em;font-size:.8em;line-height:1.4;font-weight:700}}"
    f"#qt .qm45 .neg{{color:{C['파']}}}#qt .qm45 .pos{{color:{C['빨']}}}#qt .qm45 .gd{{color:{C['금진']}}}"
    # 표지 표
    f"#qt .qm45 .ct{{width:100%;border-collapse:collapse;background:{C['블록']};border-radius:.7em;overflow:hidden;font-size:.94em}}"
    f"#qt .qm45 .ct th{{font-size:.8em;color:{C['금진']};font-weight:700;text-align:right;padding:.4em .7em .3em;border-bottom:1px solid {C['선']}}}"
    "#qt .qm45 .ct th:first-child,#qt .qm45 .ct td:first-child{text-align:left}"
    f"#qt .qm45 .ct td{{padding:.26em .7em;border-top:1px solid {C['줄선']};text-align:right;font-weight:700;white-space:nowrap}}"
    f"#qt .qm45 .ct td:first-child i{{font-style:normal;font-weight:500;color:{C['보']};font-size:.8em;margin-left:.35em}}"
    f"#qt .qm45 .ct td.th{{color:{C['금진']};font-weight:800}}"
    "#qt .qm45 .c4.dense .ct td{padding:.17em .7em}#qt .qm45 .c4.dense .ct{font-size:.9em}#qt .qm45 .c4.dense{gap:.36em}"
    # 0개
    f"#qt .qm45 .zero{{display:flex;flex-direction:column;gap:.2em}}#qt .qm45 .zero b{{font-size:3.2em;font-weight:800;line-height:1.1;color:{C['금']}}}"
    f"#qt .qm45 .zero span{{font-size:.86em;color:{C['본']}}}"
    # 종목 상자
    "#qt .qm45 .stks{display:flex;flex-direction:column;gap:.35em;flex:1;min-height:0}"
    f"#qt .qm45 .s{{background:{C['블록']};border-radius:.7em;padding:.3em .7em .28em;display:flex;flex-direction:column;gap:.1em;flex:1 0 auto;justify-content:center;max-height:9.5em}}"
    "#qt .qm45 .sh{display:flex;align-items:baseline;gap:.4em;min-width:0}"
    "#qt .qm45 .sh b{font-size:1.06em;letter-spacing:-.03em;white-space:nowrap}"
    f"#qt .qm45 .sh i{{font-style:normal;font-size:.75em;color:{C['보']};white-space:nowrap;overflow:hidden;min-width:0}}"
    f"#qt .qm45 .sh .tg{{font-size:.72em;font-weight:700;color:{C['금']};background:{C['딱']};border-radius:.3em;padding:.05em .4em;margin-left:auto;white-space:nowrap}}"
    f"#qt .qm45 .g3{{display:grid;grid-template-columns:1fr 1fr 1fr;border-top:1px solid {C['줄선']};padding-top:.1em}}"
    "#qt .qm45 .g3 div{display:flex;flex-direction:column;min-width:0;line-height:1.2}"
    f"#qt .qm45 .g3 div+div{{padding-left:.55em;border-left:1px solid {C['줄선']}}}"
    f"#qt .qm45 .g3 small{{font-size:.72em;color:{C['금진']};font-weight:700;white-space:nowrap}}"
    "#qt .qm45 .g3 strong{font-size:.98em;font-weight:800;letter-spacing:-.02em;white-space:nowrap}"
    f"#qt .qm45 .g3 strong.w{{white-space:normal;font-size:.86em}}#qt .qm45 .g3 strong.sub{{color:{C['보']};font-weight:700}}"
    "#qt .qm45 .g3 .span2{grid-column:span 2}"
    "#qt .qm45 .ct td:first-child{white-space:normal;word-break:keep-all}"
    "#qt .qm45 .c4.dense .s{padding:.18em .7em .14em;gap:0}#qt .qm45 .c4.dense .g3 div{line-height:1.12}#qt .qm45 .c4.dense .stks{gap:.28em}"
    # 설명 장
    "#qt .qm45 .sub{margin:0;font-size:.88em;font-weight:800;display:flex;gap:.45em;align-items:baseline}"
    f"#qt .qm45 .sub small{{font-size:.86em;color:{C['금']}}}"
    f"#qt .qm45 .sub em{{font-style:normal;font-weight:500;font-size:.8em;color:{C['보']};margin-left:auto;text-align:right}}"
    "#qt .qm45 .fill{flex:1;display:flex;flex-direction:column;justify-content:space-between;gap:.3em;min-height:0}"
    f"#qt .qm45 .list{{background:{C['블록']};border-radius:.75em;padding:.15em .8em;display:flex;flex-direction:column;flex:1;justify-content:space-around}}"
    f"#qt .qm45 .li{{display:grid;grid-template-columns:5.6em 1fr;gap:.6em;align-items:baseline;padding:.32em 0;border-top:1px solid {C['줄선']}}}"
    "#qt .qm45 .li:first-child{border-top:0}"
    f"#qt .qm45 .li b{{font-size:.95em;color:{C['금진']};white-space:nowrap}}"
    "#qt .qm45 .li span{font-size:.86em}"
    f"#qt .qm45 .li span small{{display:block;font-size:.88em;color:{C['보']};line-height:1.35}}"
    f"#qt .qm45 .br{{background:{C['블록']};border-radius:.75em;padding:.4em .7em;display:flex;flex-direction:column;gap:.08em;flex:1 0 auto;justify-content:center}}"
    "#qt .qm45 .br h4{margin:0;font-size:.95em;display:flex;align-items:baseline;gap:.45em}"
    f"#qt .qm45 .br h4 i{{font-style:normal;font-size:.82em;font-weight:700;color:{C['금']};background:{C['딱']};border-radius:.3em;padding:0 .4em}}"
    f"#qt .qm45 .br p{{margin:0;font-size:.82em;color:{C['본']};line-height:1.38}}"
    f"#qt .qm45 .br p b{{color:inherit}}#qt .qm45 .br.bw{{flex:1 1 auto;gap:.3em}}#qt .qm45 .br.bw b.pos{{color:{C['빨']}}}#qt .qm45 .br.bw b.neg{{color:{C['파']}}}"
    f"#qt .qm45 .tl2{{background:{C['블록']};border-radius:.75em;padding:.2em .8em;display:flex;flex-direction:column;flex:1;justify-content:space-around}}"
    f"#qt .qm45 .t2{{display:grid;grid-template-columns:3em 1fr;gap:.55em;padding:.28em 0;border-top:1px solid {C['줄선']};align-items:baseline}}"
    "#qt .qm45 .t2:first-child{border-top:0}"
    "#qt .qm45 .t2 b{font-size:1em;font-weight:800}"
    "#qt .qm45 .t2 div{font-size:.82em;line-height:1.38}"
    "#qt .qm45 .t2 div strong{display:block;font-size:1.04em}"
    f"#qt .qm45 .t2.red b,#qt .qm45 .t2.red strong{{color:{C['빨']}}}"
    f"#qt .qm45 .warn{{background:{C['블록']};border-radius:.75em;padding:.5em .75em;font-size:.82em;line-height:1.4;color:{C['본']}}}"
    f"#qt .qm45 .warn b{{color:{C['먹']}}}"
    "#qt .qm45 .half{display:grid;grid-template-columns:1fr 1fr;gap:.45em}"
    f"#qt .qm45 .hp{{background:{C['블록']};border-radius:.75em;padding:.4em .7em;display:flex;flex-direction:column}}"
    "#qt .qm45 .hp .pct{font-size:1.5em;font-weight:800;letter-spacing:-.03em;line-height:1.1}"
    f"#qt .qm45 .hp .tgt{{font-size:1.05em;font-weight:800;color:{C['빨']}}}"
    f"#qt .qm45 .hp small{{font-size:.8em;color:{C['본']};line-height:1.35}}"
    "#qt .qm45 .cmp2{display:grid;grid-template-columns:1fr 1fr;gap:.45em}"
    f"#qt .qm45 .cmp2 div{{background:{C['블록']};border-radius:.65em;padding:.35em .6em;font-size:.8em;line-height:1.35}}"
    f"#qt .qm45 .cmp2 b{{display:block;font-size:.92em;color:{C['금진']}}}"
    "#qt .qm45 .stat{display:grid;grid-template-columns:repeat(3,1fr);gap:.3em}"
    f"#qt .qm45 .stat div{{background:{C['블록']};border-radius:.55em;padding:.3em .5em;display:flex;flex-direction:column;line-height:1.2}}"
    f"#qt .qm45 .stat small{{font-size:.72em;color:{C['금진']};font-weight:700;white-space:nowrap}}"
    "#qt .qm45 .stat strong{font-size:1.08em;font-weight:800;letter-spacing:-.02em;white-space:nowrap}"
    f"#qt .qm45 .rt{{width:100%;border-collapse:collapse;background:{C['블록']};border-radius:.7em;overflow:hidden;font-size:.82em}}"
    f"#qt .qm45 .rt th{{font-size:.9em;color:{C['금진']};text-align:right;font-weight:700;padding:.3em .55em .15em;border-bottom:1px solid {C['선']}}}"
    "#qt .qm45 .rt th:first-child,#qt .qm45 .rt td:first-child{text-align:left}"
    f"#qt .qm45 .rt td{{text-align:right;padding:.25em .55em;border-top:1px solid {C['줄선']};font-weight:700;white-space:nowrap}}"
    f"#qt .qm45 .notes{{background:{C['블록']};border-radius:.75em;padding:.1em .8em;display:flex;flex-direction:column;flex:1}}"
    f"#qt .qm45 .nt{{padding:.36em 0;border-top:1px solid {C['줄선']};font-size:.82em;line-height:1.4;color:{C['본']};flex:1;display:flex;flex-direction:column;justify-content:center}}"
    "#qt .qm45 .nt:first-child{border-top:0}"
    f"#qt .qm45 .nt b{{color:{C['먹']}}}#qt .qm45 .nt>b:first-child{{display:block;font-size:1.02em;margin-bottom:.1em}}"
    "#qt .qm45 .qold{flex:0 0 100%;min-width:0;scroll-snap-align:start}"
    "#qt .qm45 .qold section[data-label]{width:auto!important;height:auto!important;padding:24px 18px!important}"
    "</style>")


def quant_view(q, 보유=None, 줄들=None):
    """`build_site.quant_view` 가 여기로 넘긴다. `q` 는 forward-log 마지막 줄, `보유` 는 `_보유()`, `줄들` 은 forward-log 전체."""
    보유 = 보유 or []
    # ⭐ 2026-09-29 — _장1 이 **여러 장**을 돌려준다. 쪽 번호를 전체에 맞춰 다시 매긴다
    _덱 = _쪽번호매기기(_장1(q, 보유) + _장보완(q) + _장2() + _장3() + [_장4()] + _장시험())   # 10/20 보완 후보 장 · 시험 장
    # ⭐ 10/16 핸드폰 4:5 카드 — _장1 이 _폰자료 를 채운 **뒤에** 만든다
    try:
        _폰 = _폰덱(q, 보유)
        _폰판 = f'<div class="qm45">{_폰}</div>'
        _폰css = _폰45CSS
    except Exception as _ex:  # noqa: BLE001
        # 새 판이 터져도 쪽은 그려져야 한다 — 옛 핸드폰 판으로 돌아간다 (조판은 게시를 막지 않는다)
        print(f"  ⚠️ 핸드폰 4:5 카드 실패 — 옛 핸드폰 판으로: {type(_ex).__name__}: {_ex}")
        _폰판 = f'<div class="qmob">{_폰사본(_덱)}</div>'
        _폰css = _폰CSS
    # ⭐ 10/20 새 카드(3:4 · 홈 결) — 사용자 「A로 해서 반영하자!」 · PC·핸드폰 같은 카드 · 터지면 옛 화면(qrail · qm45) 그대로
    _새 = ""
    try:
        import quant_n34 as _N
        _새 = (_N.CSS(*_띠색) + '<div class="qn34"><div class="nrow">' + _N.덱(q, 보유, 줄들) + '</div></div>')
    except Exception as _ex:  # noqa: BLE001
        print(f"  ⚠️ 퀀트 새 카드 실패 — 옛 화면으로: {type(_ex).__name__}: {_ex}")
        _새 = ""
    _오늘 = str(q.get("기록시각") or "")[:10]
    _날들, _지난html = _지난들(줄들, _오늘)
    _날값 = ",".join(_날들)
    return (f'<section class="view" id="qt" hidden data-today="{_오늘}" data-days="{_날값}">'
            + _폰css + _지난CSS
            + f'<div class="top"><div class="in">'
            f'<button class="tbtn" data-home type="button">← 처음</button>'
            # ⭐ 10/14 ‹ 날짜 › — 브리핑과 같은 자리 · 오늘이면 카드, 지난 날이면 표
            + (f'<span class="dnav">'
               f'<button class="tbtn qprev dprev" type="button" aria-label="전날">‹</button>'
               f'<span class="tbtn dnow"><span class="now qnow">퀀트 후보</span></span>'
               f'<button class="tbtn qnext dnext" type="button" aria-label="다음 날">›</button>'
               f'</span>' if len(_날들) > 1 else f'<span class="now">퀀트 후보</span>')
            + '</div></div>'
            + _묵은종가(q)
            + _지난html
            + (_새 if _새 else
               (f'<div class="rail qrail" data-active="true">' + _덱 + '</div>'
                # ⭐ 10/16 핸드폰 판 — 4:5 카드 (.qrail 은 폰에서 숨김) · 실패하면 10/14 옛 사본
                + _폰판))
            + f'<div class="qhint" style="text-align:center;font-size:13px;color:{C["보"]};padding:0 0 30px">'
            f'← 옆으로 넘겨서 보세요 →</div></section>')
