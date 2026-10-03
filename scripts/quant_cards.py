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
            + (f" · 업종 규칙 종목은 −{abs(_업):g}%p" if _업 is not None else "")
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
    def 낙(x):
        return f"{x.get('낙폭종가오차', x['낙폭오차']):g}%".replace("-", "−")   # 10/2 — 종가 평가 값이 있으면 그것
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
    _ka = a.get("낙폭종가오차", a["낙폭오차"]); _kn = 지금.get("낙폭종가오차", 지금["낙폭오차"])
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
        제 = (f'<div style="height:{제목높이}px;display:flex;flex-direction:column;'
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
    return " · ".join(t)


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
    def _칸(라, 값, 색, 폭, 값폭=None):
        _vs = (f"flex:none;width:{값폭}px" if 값폭 else "flex:1;min-width:0")
        return (f'<span style="flex:none;width:{폭}px;font-size:25px;font-weight:700;'
                f'color:{C["금진"]}">{라}</span>'
                f'<span style="{_vs};font-size:30px;font-weight:800;'
                f'letter-spacing:-.02em;color:{색 or C["먹"]}">{값}</span>')
    return (f'<div style="display:flex;align-items:baseline;gap:12px;'
            f'white-space:nowrap;padding:6px 0;border-top:1px solid {C["줄선"]}">'   # 0929-2 ③ 8→6
            + _칸(라1, 값1, 색1, 180) + _칸(라2, 값2, 색2, 130, 190) + '</div>')


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
    _1행 = (f'<div style="display:flex;align-items:center;gap:14px;white-space:nowrap;'
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

    # ── 2행 — 20일 낙폭 │ 상대갭 ──
    _낙 = x.get("20일낙폭")
    _낙글 = _esc(_음(_낙, 1)) if _낙 is not None else "—"
    _낙색 = None if _낙 is None else (C["빨"] if _낙 >= 0 else C["파"])
    if x.get("상대갭") is not None:
        _갭글, _갭색 = _esc(_음(x["상대갭"], 2, "%p")), None
    else:
        # 08:00 후보 때는 상대갭이 아직 없다 (08:55 에 정해진다)
        _갭글 = (f'<span style="font-size:24px;font-weight:700;color:{C["보"]}">'
                 f'{_esc(R.판정시각)} 확정 뒤</span>')
        _갭색 = None
    _2행 = _행("20일 낙폭", _낙글, "상대갭", _갭글, _낙색, _갭색)

    # ── 3행 — 전날 종가 │ 시가총액 ──
    _3행 = _행("전날 종가", f'{x.get("어제종가", 0):,}원',
               "시가총액", f'{x.get("시총억", 0):,}억')

    # ── 4행 — 문턱가(또는 매수 적정 범위) │ 이익 · 빚 ──
    if 상태 == "pre":
        _a, _b = R.매수범위(x.get("어제종가", 0) or 0)
        _라4, _값4 = "매수 적정 범위", f"{_a:,}~{_b:,}원"
    else:
        _문 = x.get("문턱가")
        _라4, _값4 = "문턱가", (f"{_문:,}원" if _문 else "—")
    _잉, _부 = x.get("잉여금비율"), x.get("부채비율")
    _재 = " · ".join(f"{v:.0f}%" for v in (_잉, _부) if v is not None) or "—"
    _4행 = _행(_라4, _esc(_값4), "이익 · 빚", _esc(_재), C["금진"], None)

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
        리드 = (f"상대갭이 문턱({_문턱글()}) 아래로 내려간 종목만 삽니다. "
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
              f'border-radius:16px;padding:14px 24px;font-size:31px;line-height:1.5;'
              f'color:{C["먹"]}">{" ".join(말)}</div>')

    부 = [알림] if 알림 else []
    if 리드:
        부.append(_본문(_esc(리드), 35))
    if 상태 == "none":
        부.append(f'<div style="display:flex;flex-direction:column;gap:18px">'
                 f'<span style="font-size:114px;font-weight:800;letter-spacing:-.05em;'
                 f'line-height:1.15;color:{C["금"]}">0개</span>'
                 f'<span style="font-size:31px;line-height:1.6;color:{C["본"]}">조건을 통과한 '
                 f'종목이 없습니다. 규칙상 이런 날은 열흘에 세 번쯤 있습니다. 고장이 아닙니다.'
                 f'</span></div>')
        for 글 in (f"후보가 되려면 먼저 이걸 모두 통과해야 합니다 · 쌓은 이익 {R.잉여금하한:g}% 이상 · "
                  f"빚 {R.부채상한:g}% 이하 · 작년 순이익 흑자 · 시가총액 {R.시총하한억:,.0f}억~"
                  f"{R.시총상한억:,.0f}억 · 하루 거래 {R.대금하한억:g}억 이상"
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
    _쪽수 = max(1, -(-len(목록) // _한장에))
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
def _장2():
    # ⭐⭐⭐ 2026-09-29 밤 QUANT-PICK-0929 — 3장은 「어떤 순서로 거르나」 하나만,
    #    4장은 표 대신 업종마다 한 덩이. 문구는 디자인 판 그대로 · 숫자는 규칙 파일에서.
    #    ASK-QUANT-0929-5 에서 짚은 것: 「업종」→「섹터」(⑥) · 지수 숫자/종목 숫자 분리(⑦) ·
    #    「섹터·업종 갈래는 시가총액 범위를 따로」(⑧) · 「없음」→「1단계 공통 문 그대로」(①)
    # (옛 판의 이력: 2026-09-23 「회사 사정과 상관없이」 삭제 · 09-29 B137 재무 문 — 커밋 d39873f 이전 참고)
    # ⭐ ANSWER-0929-7 답 2 — 「왜 빠졌는지(회사 사정)는 보지 않고」 되살림 (디자인: 「내 실수다」)
    리드 = ("재무가 튼튼한 회사가 크게 빠진 날을 찾습니다. 왜 빠졌는지(회사 사정)는 보지 않고 "
          "재무제표와 주가만 보는 기계 규칙이라 브리핑과 종목이 다른 것이 정상입니다.")
    문들 = ([(f"{R.잉여금하한:g}%", "이상 · 벌어서 쌓은 이익"), (f"{R.부채상한:g}%", "이하 · 빚")]
          + ([("흑자", "· 작년 순이익")] if R.흑자필수 else [])
          + [(f"{R.시총하한억:,.0f}억~{R.시총상한억:,.0f}억", "· 시가총액"),
             (f"{R.대금하한억:g}억", "이상 · 하루 거래")])
    _업켬 = bool(R.업종규칙_켬 and R.업종규칙)
    규칙 = ((("낙폭", f"20거래일 동안 {abs(R.낙폭20문턱):g}% 넘게 빠졌고, 평소 움직이던 폭의 "
                     f"아래쪽(볼린저 −{abs(R.볼린저문턱):g}σ)에 있다"),
             ("섹터", f"방산·원전·반도체 등 {len(R.섹터규칙)}개 섹터는 섹터마다 기준이 다르다"),
             ("시장", f"지수가 눌린 날(20일 −{abs(R.지수낙20문턱):g}% · 60일 −{abs(R.지수낙60문턱):g}%)"
                     f"에는 종목이 조금만 빠져도 걸린다 (볼린저 −{abs(R.시장볼문턱):g}σ · "
                     f"20일 −{abs(R.시장낙20문턱):g}% · 60일 −{abs(R.시장낙60문턱):g}%)"))
            + ((("변동성·자사주", f"지수가 크게 출렁이는 날(20일 변동성 {R.시장변동성문턱:g}% 이상)에는 "
                                f"{R.자사주창일}거래일 안에 자사주 매입을 공시한 회사도 걸린다"),)
               if R.변동성자사주_켬 else ())
            + ((("업종", "업종마다 따로 낸 기준 · 다음 장에 있다"),) if _업켬 else ()))
    _갈 = {3: "세", 4: "네", 5: "다섯", 6: "여섯"}.get(len(규칙), str(len(규칙)))

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
          + _각주(_묶음(_esc("관리종목·우선주·스팩은 제외합니다"
                          + (f" · 섹터 갈래는 시가총액 상한이 없고({R.시총하한억:,.0f}억 이상)"
                             if R.섹터규칙_큰회사 else "")
                          + (f", 업종 갈래는 업종마다 범위가 다릅니다 ({_다음쪽}장)." if _업켬 else ".")))))
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


_5장선 = 1   # 5장 첫 장에 둘 블록 수 (ANSWER-0929-7 답 1)


def _억만(원):
    """2억 4,800만 원 꼴 (100만 원 단위 반올림) — 시뮬 금액이다 (사용자 자산이 아니다)"""
    억, 나머지 = divmod(int(round(원)), 100_000_000)
    만 = int(round(나머지 / 1_000_000)) * 100
    if 만 >= 10000:
        억, 만 = 억 + 1, 0
    if 억 and 만:
        return f"{억}억 {만:,}만 원"
    return f"{억}억 원" if 억 else f"{만:,}만 원"


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
        return ""
    if 덜 is None or 끝 is None or 낙 is None:
        return ""

    def 묶(v):
        return f'<b style="font-weight:800;color:{C["먹"]};white-space:nowrap">{_esc(v)}</b>'
    낙글 = f"{낙:g}%".replace("-", "−")
    본 = (_esc("이미 들고 있는 종목이 다시 후보에 뜨면 또 산다고 가정한 성적입니다. "
               "다시 뜨는 것은 산 뒤 더 빠졌다는 뜻이라, 더 사지 않았다면 이보다 약 ")
          + 묶(f"{덜:.0f}%") + _esc(" 낮았습니다(같은 기간 ") + 묶(_억만(끝))
          + _esc(" · 계좌 낙폭" + ("(매일 종가)" if _종가기준() else "") + " ") + 묶(낙글 + ").")
          )
    return (f'<div style="display:flex;flex-direction:column;gap:10px;border-top:1px solid {C["선"]};'
            f'padding-top:18px">'
            f'<span style="font-size:26px;font-weight:700;color:{C["금"]}">'
            f'{_esc("이 성적의 가정 · 이 장과 다음 장 숫자 모두")}</span>'
            f'<span style="font-size:31px;line-height:1.55;color:{C["본"]}">{본}</span>'
            f'</div>')


# ── 3장 · 어떻게 사고 파나 (라벨 2열형) ──────────────────────────
def _장3():
    옛낙, 새낙 = _계좌낙폭()
    앞, 뒤 = R.몫들[0], R.몫들[1]
    # ⭐ 몫 이름과 조사는 `_몫말` 이 정한다 — 50:50 「반은/나머지 반은」, 그 밖엔 「30%는/나머지 70%는」
    블록 = (
        ("어떻게 사나",
         [f"{R.판정시각}에 5분, 여기서 살지 정해진다. 후보들의 예상체결가를 보고, 그 값들의 중앙값보다 "
          # ⭐ 2026-09-29 밤 — 오늘 반영한 둘(업종 −1.5%p · 섹터 +2)이 빠져 있었다. 규칙 파일에서 읽는다
          f"{abs(R.상대갭문턱):g}%p 더 빠진 것만 삽니다"
          + (f"(업종 규칙 종목은 {abs(R.업종전용상대갭):g}%p"
             # ⭐ 2026-09-30 — 원전 기자재
             + "".join(f" · {n} 종목은 {abs(v['상대갭']):g}%p" for n, v in getattr(R, "바구니전용", {}).items())
             + ")"
             if getattr(R, "업종전용상대갭", None) is not None else "")
          + f". 하루 최대 {R.오늘최대종목(None)}종목"
          + (f"이고, 섹터 규칙 종목은 {R.섹터전용자리}종목"
             + "".join(f", {n} 종목은 {v['자리']}종목" for n, v in getattr(R, "바구니전용", {}).items())
             + "까지 더 삽니다."
             if getattr(R, "섹터전용자리", 0) else "입니다.")
          + (f" 지수가 20일에 {abs(R.빠지는장문턱):g}% 넘게 빠진 날은 "
             f"{R.빠지는장최대종목}종목까지 삽니다." if R.빠지는장_켬 else ""),
          f"예상체결가가 전날보다 {abs(R.예상갭하한):g}% 넘게 빠진 종목은 사지 않습니다. 호가가 얇아 나온 가짜 값이거나 "
          f"진짜 폭락이거나, 둘 다 살 이유가 아닙니다.",
          "09:01에 체결 안 된 주문은 반드시 취소하세요. 맞는 게 없으면 아무것도 사지 않습니다."]),
        ("목표에 닿으면 · 둘로 나눠 판다",
         [f"한 종목을 사면 주문을 둘로 나눠 겁니다. 산 주식의 {_몫말(앞[0])} +{앞[1]:g}%에 팔아 이익을 "
          f"일찍 챙기고, {_몫말(뒤[0], 뒤=True)} +{뒤[1]:g}%까지 기다립니다.",
          # ⭐ 2026-09-28 — **문장이 효과를 과장하고 있었다.** 옛 값(9.0→6.2)은 2026-09-14 에
          #    손으로 적은 것이고, 지금 규칙으로 다시 재니 11.3% → 11.0% 로 **거의 안 줄었다**.
          #    나눠 팔기의 진짜 값은 낙폭이 아니라 **돈**이다 (11년 성적 1.25배).
          #    ⚠️ 금액은 화면에 안 쓴다 — **배수**로만 적는다
          # ⭐ 10/2 — 종가 기준으로 바뀌면 「줄었다」 가 사실이 아닐 수 있다 ⇒ 숫자 크기로 말을 고른다
          (f"나눠 팔면 11년 성적이 {_배수():.2f}배가 되고, 계좌 흔들림{'(매일 종가로 평가)은' if _종가기준() else '도'} "
           f"{abs(옛낙):.1f}% → {abs(새낙):.1f}%"
           + (("로 조금 줄었습니다." if abs(abs(옛낙) - abs(새낙)) < 3 else "로 줄었습니다.") if abs(새낙) < abs(옛낙) - 0.05 else
              (("로 조금 늘었습니다." if abs(abs(옛낙) - abs(새낙)) < 3 else "로 늘었습니다.") if abs(새낙) > abs(옛낙) + 0.05
               else "로 거의 같습니다."))
           if _배수() else
           f"나눠 팔면 계좌 흔들림이 {abs(옛낙):.1f}% → {abs(새낙):.1f}%"
           + ("로 줄었습니다." if abs(새낙) < abs(옛낙) - 0.05 else "입니다."))]),
        ("목표에 안 닿으면 · 날짜로 끝낸다",
         [f"{_몫말(앞[0], 앞뒤=True)} {앞[2]}거래일, {_몫말(뒤[0], 뒤=True, 앞뒤=True)} {뒤[2]}거래일이 "
          f"지나면 그날 값으로 정리합니다.",
          "손절은 하지 않습니다. 값이 빠졌다는 이유로 중간에 팔지 않습니다."
          # ⭐ 2026-09-29 밤 — 악재 매도(오늘 반영)가 화면에 없었다. 「중간에 팔지 않는다」만 보면 모른다
          + (f" 다만 들고 있는 종목에 {'·'.join(_파는말())} 공시가 뜨면 다음 날 시가에 팝니다."
             if _파는말() else "")]),
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
    몸1 = (_본문(_esc("규칙이 정하는 것은 언제 사고 언제 파는지 둘뿐입니다. 얼마를 넣을지는 정하지 않습니다."), 35)
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
    표 = f'<div style="display:flex;flex-direction:column">{머리행}{행들}</div>'

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

    각주 = ("위 숫자는 전부 과거 자료로 계산한 것입니다. 「과거에 이랬다」이지 「앞으로 이럴 것」이 "
          "아닙니다. 실제로 산 기록은 오늘부터 쌓입니다. 매수 추천이 아닙니다. 판단과 책임은 "
          "본인에게 있습니다.")
    몸 = (_본문(_esc("이 규칙이 과거에 있었다면 이렇게 됐을 것입니다. 컴퓨터가 옛 주가로 계산한 것입니다."), 31, 1.6)
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
def quant_view(q, 보유=None):
    """`build_site.quant_view` 가 여기로 넘긴다. `q` 는 forward-log 마지막 줄, `보유` 는 `_보유()`."""
    보유 = 보유 or []
    return (f'<section class="view" id="qt" hidden>'
            f'<div class="top"><div class="in">'
            f'<button class="tbtn" data-home type="button">← 처음</button>'
            f'<span class="now">퀀트 후보</span></div></div>'
            f'<div class="rail qrail" data-active="true">'
            # ⭐ 2026-09-29 — _장1 이 **여러 장**을 돌려준다. 쪽 번호를 전체에 맞춰 다시 매긴다
            + _쪽번호매기기(_장1(q, 보유) + _장2() + _장3() + [_장4()])
            + '</div>'
            f'<div style="text-align:center;font-size:13px;color:{C["보"]};padding:0 0 30px">'
            f'← 옆으로 넘겨서 보세요 →</div></section>')
