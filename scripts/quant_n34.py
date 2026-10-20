#!/usr/bin/env python3
r"""
quant_n34.py — 퀀트 후보 새 카드(3:4 · 홈 첫 화면 결) · 2026-10-20

사용자 10/20 「A로 해서 반영하자!」 — 시안 https://claude.ai/artifact/27khtNb5farQNFNJYbhJic
- 홈 첫 화면과 같은 부품: 위 띠 = 그날 코스피 색 그라데이션(build_site 가 quant_cards._띠색 에 넣는다) · 연회색 바탕 · 흰 둥근 카드 · 파랑 강조
- 표지 없음: 첫 종목 장 위 띠에 오늘 요약 · 종목 한 장에 셋 · 그다음 보완 · 무엇을 노리나 · 오늘 나온 길 · 갈래 넷 · 사고 파는 법 · 시험 · 과거 성적
- 갈래 이름 넷: 크게 빠짐 · 시장 급락 · 변동성·자사주 · 섹터 6업종 (사용자 「통일되어야 할 것 같은데?」)
- 숫자는 전부 기록(forward-log)·rule_def·화면 숫자 파일에서 — 손으로 안 적는다
- quant_cards.quant_view 가 부른다. 여기서 터지면 옛 화면(qrail · qm45)으로 돌아간다(조판은 게시를 막지 않는다)
⚠️ 주문은 없다 — 화면만 만든다
"""
import json
import os
import io

import rule_def as R

갈래이름 = [("섹터규칙", "섹터 6업종"), ("기존규칙", "크게 빠짐"), ("시장규칙", "시장 급락"), ("변동성자사주", "변동성·자사주"), ("업종규칙", "업종")]
지수이름 = {"KOSPI": "코스피", "KOSDAQ": "코스닥"}


def _e(s):
    return (str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _원(v):
    try:
        return f"{int(round(float(v))):,}"
    except (TypeError, ValueError):
        return "—"


def _퍼(v, 소수=1, 부호=True):
    if v is None:
        return "—"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    s = f"{abs(v):.{소수}f}%"
    return ("−" if v < 0 else ("+" if (부호 and v > 0) else "")) + s


def _억(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{v / 10000:.1f}조" if v >= 10000 else f"{v:,.0f}억"


def _갈래(x):
    t = [이 for 키, 이 in 갈래이름 if x.get(키)]
    t += list(x.get("B라벨") or [])
    return t


def _왜한줄(x, 갈):
    if not 갈:
        return ""
    g = 갈[0]
    if g == "시장 급락":
        k = 지수이름.get(x.get("시장키"), "지수")
        v = x.get("시장지수낙20")
        return f"{k} 20일 {_퍼(v, 0)} 날" if v is not None else "지수가 크게 빠진 날"
    if g == "크게 빠짐":
        return f"혼자 20일 {_퍼(x.get('20일낙폭'), 0)}"
    if g == "섹터 6업종":
        return f"{x.get('섹터') or '업종'} 빠짐"
    if g == "변동성·자사주":
        return "흔들리는 장 · 자사주 매입"
    return g


def _팔(주):
    try:
        주 = float(주)
    except (TypeError, ValueError):
        return None
    return [int(주 * (1 + m[1] / 100) + .5) for m in R.몫들[:2]]


def _종목상자(x, 업, 상태, 보완=False):
    갈 = (["대형 · 주의" if x.get("보완규칙") == "대형" else "중형"] if 보완 else _갈래(x))
    표 = (갈[0] + (f" +{len(갈) - 1}" if len(갈) > 1 else "")) if 갈 else ""
    큰 = 보완 or (갈 and 갈[0] == "크게 빠짐")
    if 보완:
        왜 = (f"40일 {_퍼(x.get('40일낙폭'), 0)}" if x.get("보완규칙") == "대형"
              else f"{지수이름.get(x.get('시장키'), '지수')} 20일 {_퍼(x.get('시장지수낙20'), 0)} 날")
    else:
        왜 = _왜한줄(x, 갈)
    주 = x.get("주문가")
    팔 = _팔(주) if 주 else None
    몫1, 몫2 = (f"{R.몫들[0][0] * 100:g}%", f"{R.몫들[1][0] * 100:g}%")
    if 주:
        값 = f'<p class="pr"><small>주문가</small>{_원(주)}원</p>'
        칸 = (f'<div class="r"><small>{몫1} 팔 값</small><b>{_원(팔[0])}</b></div>'
             f'<div class="r"><small>{몫2} 팔 값</small><b>{_원(팔[1])}</b></div>')
    else:   # 08:55 전 — 주문가가 아직 없다
        a, b = R.매수범위(x.get("어제종가", 0) or 0)
        값 = f'<p class="pr"><small>전날 종가</small>{_원(x.get("어제종가"))}원</p>'
        칸 = f'<div class="r w2"><small>주문가가 들어올 자리 · {R.판정시각}에 확정</small><b>{_원(a)}~{_원(b)}</b></div>'
    if 보완:
        칸 += f'<div class="bl"><small>40일</small><b>{_퍼(x.get("40일낙폭"))}</b></div>'
    elif x.get("상대갭") is not None:
        밑 = bool(x.get("예상통과"))
        칸 += f'<div class="{"r" if 밑 else "bl"}"><small>상대갭 · {"문턱 밑" if 밑 else "문턱 위"}</small><b>{float(x["상대갭"]):+.2f}</b></div>'
    elif 주:
        칸 += '<div class="bl"><small>상대갭</small><b>—</b></div>'
    칸 += f'<div class="bl"><small>20일</small><b>{_퍼(x.get("20일낙폭"))}</b></div>'
    업이름 = (업.get(x.get("종목코드", "")) or {}).get("업종명") if isinstance(업.get(x.get("종목코드", "")), dict) else ""
    잉, 부 = x.get("잉여금비율"), x.get("부채비율")
    줄 = " · ".join(z for z in [
        업이름 or "", f"종가 {_원(x.get('어제종가'))}" if 주 else "", f"시총 {_억(x.get('시총억'))}",
        f"이익 {float(잉):.0f}%" if 잉 is not None else "", f"빚 {float(부):.0f}%" if 부 is not None else ""] if z)
    return (f'<div class="m stk"><div class="s1"><b>{_e(x.get("이름", ""))} <span class="cd">{_e(x.get("종목코드", ""))}</span>'
            f'<small class="why">' + (f'<span class="tag{" big" if 큰 else ""}">{_e(표)}</span>' if 표 else "")
            + f'<span class="wt">{_e(왜)}</span></small></b>{값}</div>'
            f'<div class="tg">{칸}</div><p class="sub2">{_e(줄)}</p></div>')


def _띠(q, d, n):
    import quant_cards as Q
    상태 = d.get("상태")
    목록 = d.get("목록") or []
    동 = q.get("동시호가") or {}
    날 = str(q.get("기록시각") or "")[:10]
    try:
        import datetime as _dt
        _d = _dt.date.fromisoformat(날)
        날글 = f"{_d.month}/{_d.day}({'월화수목금토일'[_d.weekday()]})"
    except ValueError:
        날글 = 날
    if 상태 == "buy":
        제 = f"{날글} 지정가 {len(목록)}개"
        때 = f"{R.판정시각} 확정"
    elif 상태 == "pre":
        제 = f"{날글} 볼 종목 {len(목록)}개"
        때 = f"{R.판정시각}에 확정"
    elif 상태 == "wait":
        제 = f"{날글} 살 것 없음"
        때 = f"{R.판정시각} 확정"
    else:
        제 = f"{날글} 후보 0개"
        때 = "08:00 기준"
    낙 = ((q.get("국면") or {}).get("지수낙폭") or {})
    왜값 = "—"
    for k in ("KOSPI", "KOSDAQ"):
        v = 낙.get(k) or [None, None]
        if v[0] is not None and v[0] <= R.지수낙20문턱:
            왜값 = f"{지수이름[k]} 20일 {_퍼(v[0], 0)}"
            break
    갈수 = {}
    for x in 목록:
        for g in _갈래(x)[:1]:
            갈수[g] = 갈수.get(g, 0) + 1
    왜라벨 = "왜 오늘"
    if 갈수:
        g0 = max(갈수, key=갈수.get)
        왜라벨 = f"왜 오늘 · {g0}"
        if 왜값 == "—":
            왜값 = f"{g0} {갈수[g0]}개"
    시장 = 동.get("예상시장갭")
    알림 = "".join(f'<p class="al">{_e(z)}</p>' for z in (d.get("알림말") or []))
    return (f'<div class="strip"><div class="st1"><b>{_e(제)}</b><span>{_e(때)} · @@PG@@</span></div>'
            f'<div class="st3"><span><i>{_e(왜라벨)}</i><b>{_e(왜값)}</b></span>'
            f'<span><i>시장 흐름</i><b>{_퍼(시장, 2) if 시장 is not None else R.판정시각 + "에"}</b></span>'
            f'<span><i>사는 문턱</i><b>시장 −{abs(R.상대갭문턱):g}%p</b></span></div>{알림}</div>')


def _카드(머리, 몸, 덧=""):
    return f'<div class="cw"><article class="c{(" " + 덧) if 덧 else ""}">{머리}{몸}</article></div>'


def _위(k, 제목=None, 작게=True):
    return (f'<div class="nh"><p class="k"><span>{_e(k)}</span><span>@@PG@@</span></p>'
            + (f'<h3 class="{"sm" if 작게 else ""}">{_e(제목)}</h3>' if 제목 else "") + '</div>')


def 덱(q, 보유):
    r"""새 카드 묶음 HTML (카드들만). 실패하면 예외를 그대로 던진다 — quant_cards 가 옛 화면으로 돌아간다"""
    import quant_cards as Q
    d = dict(Q._폰자료)
    상태 = d.get("상태")
    목록 = list(d.get("목록") or [])
    업 = Q._업종표()
    장 = []
    # ── 종목 장 (한 장에 셋 · 첫 장 위 띠) ──
    if 목록:
        for i in range(0, len(목록), 3):
            조각 = 목록[i:i + 3]
            머리 = (_띠(q, d, len(목록)) if i == 0 else
                   _위(f"{'살 종목' if 상태 == 'buy' else '볼 종목'} {i + 1}–{i + len(조각)} / {len(목록)}", "사는 값과 파는 값"))
            장.append(_카드(머리, '<div class="menu tight">' + "".join(_종목상자(x, 업, 상태) for x in 조각) + '</div>'))
    else:
        장.append(_카드(_띠(q, d, 0), '<div class="menu"><div class="m zero"><b>0개</b><p>조건을 통과한 종목이 없습니다. '
                     '규칙을 낮춰 억지로 후보를 만들지 않습니다. 이런 날은 열흘에 세 번쯤 있습니다.</p></div></div>'))
    # ── 보완 ──
    보, _, _ = Q._보완자료(q)
    for i in range(0, len(보), 3):
        조각 = 보[i:i + 3]
        머리 = (f'<div class="nh"><p class="k"><span>보완 후보 {len(보)} · 지금 규칙 주문과 따로</span><span>@@PG@@</span></p>'
               f'<p class="lead2"><b>대형</b> {R.보완대형["시총억"][0] / 10000:g}조↑·40일 {R.보완대형["낙40"]:g}% · '
               f'<b>중형</b> {R.보완중형["시총억"][0]:,}억~{R.보완중형["시총억"][1] / 10000:g}조·지수 20일 {R.보완중형["지수낙20"]:g}% · '
               f'시장보다 <b>{abs(R.보완상대갭):g}%p</b> 싸게 시작하면 삼 · 대형은 더 빠진 적 있음(2023 −86%)</p></div>')
        장.append(_카드(머리, '<div class="menu tight">' + "".join(_종목상자(x, 업, "buy", 보완=True) for x in 조각) + '</div>'))
    # ── 무엇을 노리나 ──
    s = Q._사례()
    도 = s.get("도달률") or s.get("승률")
    장.append(_카드(_위("이 규칙은 무엇을 노리나", "좋은 회사가 같이 빠진 날을 노립니다", 작게=False),
        '<div class="menu fill">'
        '<div class="m"><div class="step num"><b>①</b><span>시장이 통째로 크게 빠지거나 업종이 한꺼번에 빠지면, 튼튼한 회사도 <em>자기 잘못 없이</em> 같이 빠집니다.</span></div></div>'
        f'<div class="m"><div class="step num"><b>②</b><span>그런 회사는 제자리로 돌아오는 일이 많았습니다. 10년 동안 {s.get("전체건수", 0)}번 샀다면 <em>{도}%가 +{R.몫들[0][1]:g}%에 닿았습니다</em>.</span></div></div>'
        f'<div class="m"><div class="step num"><b>③</b><span>그래서 빠진 날 <em>더 싸게 시작할 때만</em> 사고, +{R.몫들[0][1]:g}%와 +{R.몫들[1][1]:g}%에 나눠 팝니다.</span></div></div>'
        '<div class="m hot"><b>사람이 고르지 않습니다</b><p>재무·주가·지수와 공시 몇 가지(자사주 매입 · 감자 · 유상증자)를 정해진 숫자로만 봅니다. 뉴스 내용이나 느낌은 쓰지 않고, 매일 똑같이 고릅니다.</p></div>'
        '</div>'))
    # ── 오늘 나온 길 (깔때기 — 기록에 있을 때만) ──
    깔 = q.get("깔때기") or {}
    n전 = 깔.get("전체")
    # ⚠️ 10/20 — 깔때기 숫자가 없는 날(10/20 전 기록)에도 기본 조건은 늘 보인다(없으면 「시총 300억」 이 화면 어디에도 없었다)
    줄들 = [("상장 종목 전부", 깔.get("전체"), ""), (f"시가총액 {R.시총하한억:,.0f}억 이상", 깔.get("시총"), ""),
          (f"하루 거래 {R.대금하한억:g}억 이상", 깔.get("대금"), ""),
          (f"쌓은 이익 {R.잉여금하한:g}% 이상 · 빚 {R.부채상한:g}% 이하 · 작년 흑자", 깔.get("재무"), ""),
          (f"상장 {R.상장최소거래일}거래일 이상 · 관리·우선주·스팩 뺌", 깔.get("기본문"), ""),
          ("오늘 크게 빠진 종목 · 갈래 넷 중 하나", 깔.get("갈래"), "hl"),
          ("시장보다 싸게 시작할 것 같은 순서로", len(목록) if n전 else None, "hl2")]
    if n전:
        fn = "".join(f'<div class="fn {c}"><span>{_e(x0)}</span><b>{_원(x1)}</b><i style="width:{max(1.2, (x1 or 0) / n전 * 100):.1f}%"></i></div>'
                     for x0, x1, c in 줄들 if x1 is not None)
        제목 = f"{n전:,}종목에서 {len(목록)}개가 남기까지"
    else:
        fn = "".join(f'<div class="fn {c}"><span>{_e(x0)}</span><b></b></div>' for x0, x1, c in 줄들[1:5])
        제목 = "이 조건을 모두 통과해야 후보"
    장.append(_카드(_위("어떻게 나왔나 · 전날 종가 기준" if n전 else "기본 조건 · 먼저 거르는 것", 제목, 작게=False),
        f'<div class="menu"><div class="m" style="gap:.55em">{fn}</div>'
        f'<p class="d">갈래 넷 = 크게 빠짐 · 시장 급락 · 변동성·자사주 · 섹터 {len(R.섹터규칙)}업종(뜻은 다음 장). 마지막에 지정가를 걸고, '
        f'9시 시가가 시장보다 {abs(R.상대갭문턱):g}%p 더 싸게 시작해야 실제로 삽니다.</p></div>'))
    # ── 갈래 넷 ──
    수 = {}
    for x in 목록:
        for g in _갈래(x):
            수[g] = 수.get(g, 0) + 1
    상한 = f"{R.시총상한억:,.0f}억 미만"
    갈들 = [("크게 빠짐", 상한, f"혼자 평소 흔들림 폭 아래(볼린저 −{abs(R.볼린저문턱):g}σ 아래)로 내려가고 20일 {abs(R.낙폭20문턱):g}% 넘게 빠진 종목"),
           ("시장 급락", 상한, f"지수가 20일 −{abs(R.지수낙20문턱):g}% 또는 60일 −{abs(R.지수낙60문턱):g}%인 날, 같이 빠진 종목"
                            f"(종목 볼린저 −{abs(R.시장볼문턱):g}σ · 20일 −{abs(R.시장낙20문턱):g}% · 60일 −{abs(R.시장낙60문턱):g}% 중 하나)"),
           ("변동성·자사주", 상한, f"지수가 크게 흔들리는 날(20일 변동성 {R.시장변동성문턱:g}% 이상), 최근 {R.자사주창일}거래일 안에 자사주를 산 회사"),
           (f"섹터 {len(R.섹터규칙)}업종", "크기 상한 없음", " · ".join(k.split("/")[0] for k in R.섹터규칙) + f"이 업종마다 정한 만큼 빠지면 · 하루 {R.섹터전용자리}자리 따로")]
    if not R.변동성자사주_켬:
        갈들 = [z for z in 갈들 if z[0] != "변동성·자사주"]
    br = "".join(f'<div class="m br"><div class="bh"><b>{x0}</b><span class="sz{" big" if x1 == "크기 상한 없음" else ""}">{x1}</span>'
                 f'<em>오늘 {수.get(x0 if not x0.startswith("섹터") else "섹터 6업종", 0)}</em></div><p>{_e(x2)}</p></div>' for x0, x1, x2 in 갈들)
    장.append(_카드(_위("갈래 넷 · 기본 조건을 먼저 통과한 뒤", "넷 중 하나에 걸리면 후보", 작게=False),
        f'<div class="menu tight">{br}</div><p class="foot">{R.시총상한억:,.0f}억 이상 큰 회사는 섹터 갈래와 보완 후보(중형·대형)로만 나옵니다.</p>'))
    # ── 사고 파는 법 ──
    a1, a2 = R.몫들[0], R.몫들[1]
    장.append(_카드(_위("어떻게 사고 파나", "걸어 두고, 나눠서 팝니다", 작게=False),
        '<div class="menu fill">'
        f'<div class="m"><div class="step r"><b>{R.판정시각}</b><span>주문가에 지정가 매수를 겁니다(하루 최대 {R.오늘최대종목(None)}개 + 섹터 {R.섹터전용자리}개). 9시 시가가 주문가 이하일 때만 체결됩니다</span></div>'
        '<div class="step r"><b>09:01</b><span>안 찬 주문은 반드시 취소합니다. 장중에 내려와서 사면 규칙이 아닙니다</span></div></div>'
        f'<div class="m"><div class="step"><b>체결 뒤</b><span>{a1[0] * 100:g}%는 +{a1[1]:g}%, {a2[0] * 100:g}%는 +{a2[1]:g}%에 매도 지정가를 걸어 둡니다</span></div>'
        f'<div class="step"><b>{a1[2]}일</b><span>+{a1[1]:g}%에 못 닿은 {a1[0] * 100:g}%는 그날 정리합니다</span></div>'
        f'<div class="step"><b>{a2[2]}일</b><span>+{a2[1]:g}%에 못 닿은 {a2[0] * 100:g}%도 그날 정리합니다</span></div></div>'
        '<div class="m hot"><b>손절은 없습니다</b><p>감자·유상증자 같은 악재 공시가 나오면 다음 날 시가에 팝니다.</p></div>'
        '</div>'))
    # ── 시험 ──
    줄, 날 = Q._시험표()
    if 줄:
        tt = "".join(f'<div class="ln"><b>{_e(a)}</b><em>{_e(b)}</em></div><p class="d">{_e(c)}</p>' for a, b, c in 줄)
        장.append(_카드(_위("어떤 시험을 거쳤나", "넣기 전에 이렇게 쟀습니다", 작게=False),
            f'<div class="menu"><div class="m tests">{tt}</div></div><p class="foot">시험 날짜 {_e(날)} · 규칙이 바뀌면 다시 잽니다</p>'))
    # ── 과거 성적 ──
    try:
        cap = json.load(io.open(os.path.join(Q._DATA, "rule-capital.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cap = {}
    끝 = cap.get("끝자산")
    종낙 = (cap.get("종가") or {}).get("계좌낙폭")
    칸 = [("해마다", _퍼(cap.get("연평균"))), (f"+{R.몫들[0][1]:g}% 닿음", f"{도}%"), ("한 번 평균", _퍼(s.get("평균"))),
         ("산 횟수", f"{s.get('전체건수', 0)}번"), ("최악 한 번", _퍼(s.get("가장나쁨"))), ("계좌 가장 깊이", _퍼(종낙) if 종낙 is not None else "—")]
    시작 = cap.get("시작자산") or 5e6
    장.append(_카드(_위(f"과거 성적 · {str(s.get('기간') or '')[:4]}년부터 · 컴퓨터 계산", f"{시작 / 1e4:,.0f}만 원이", 작게=False),
        f'<div class="menu"><div class="m"><p class="bigv">{(끝 or 0) / 1e8:.2f}<small>억</small></p>'
        f'<div class="six">' + "".join(f'<div><small>{a}</small><b>{b}</b></div>' for a, b in 칸) + '</div></div>'
        f'<p class="d">모두 {s.get("전체건수", 0)}번 샀고 {도}%가 +{R.몫들[0][1]:g}%에 닿았습니다. {_e(Q._볼린저주의[0])} — {_e(Q._볼린저주의[1])} {_e(Q._성적주의[1])} {_e(Q._성적주의[3])}</p></div>'))
    n = len(장)
    return "".join(h.replace("@@PG@@", f"{i}/{n}") for i, h in enumerate(장, 1))


def CSS(c1, c2):
    r"""시안(quant-homefit.html)과 같은 값 · #qt .qn34 아래로만"""
    p = "#qt .qn34"
    return ("<style>"
            f"{p}{{--bg:#EEF2F7;--ink:#1A2333;--sub:#5B6678;--blue:#2E5FB8;--red:#C8372D;--tile:#F4F6FA;--c1:{c1};--c2:{c2};padding:12px 0 6px}}"
            f"{p} .nrow{{display:flex;gap:14px;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scroll-padding-inline:16px;padding:0 16px 10px;scrollbar-width:none;-webkit-overflow-scrolling:touch}}"
            f"{p} .nrow::-webkit-scrollbar{{display:none}}"
            f"@media(min-width:900px){{{p} .nrow{{flex-wrap:wrap;justify-content:center;overflow:visible;scroll-snap-type:none}}}}"
            f"{p} .cw{{flex:0 0 min(400px,calc(100vw - 32px));container-type:inline-size;scroll-snap-align:start;scroll-snap-stop:always}}"
            f"@media(min-width:900px){{{p} .cw{{flex-basis:360px}}}}"
            f"{p} .c{{aspect-ratio:3/4;font-size:calc(100cqw / 22.5);border-radius:0;overflow:hidden;display:flex;flex-direction:column;font-feature-settings:'tnum';letter-spacing:-.01em;background:var(--bg);color:var(--ink);word-break:keep-all;line-height:1.5;box-sizing:border-box}}"
            f"{p} .c *{{margin:0;box-sizing:border-box}}"
            f"{p} .strip{{color:#F3F6FB;background:linear-gradient(180deg,var(--c1),var(--c2));padding:.65em 1.05em .6em;display:flex;flex-direction:column;gap:.25em;margin-bottom:.4em}}"
            f"{p} .st1{{display:flex;justify-content:space-between;align-items:baseline;gap:.5em;white-space:nowrap}}"
            f"{p} .st1 b{{font-size:1.15em;font-weight:800;letter-spacing:-.03em}}{p} .st1 span{{font-size:.7em;color:rgba(243,246,251,.75)}}"
            f"{p} .st3{{display:grid;grid-template-columns:1.35fr 1fr 1fr;gap:.35em}}"
            f"{p} .st3 span{{background:rgba(255,255,255,.12);border-radius:.25em;padding:.3em .55em;font-size:.66em;color:rgba(243,246,251,.8);display:flex;flex-direction:column;min-width:0;white-space:nowrap}}"
            f"{p} .st3 i{{font-style:normal}}{p} .st3 b{{color:#fff;font-size:1.3em;font-weight:800}}"
            f"{p} .al{{font-size:.7em;font-weight:700;background:rgba(255,255,255,.18);border-radius:.5em;padding:.25em .55em}}"
            f"{p} .nh{{padding:1.2em 1.15em .65em;display:flex;flex-direction:column;gap:.2em}}"
            f"{p} .nh .k{{font-size:.74em;color:var(--sub);font-weight:600;display:flex;justify-content:space-between;gap:.5em}}"
            f"{p} .nh h3{{font-size:1.35em;font-weight:800;letter-spacing:-.035em;line-height:1.3}}{p} .nh h3.sm{{font-size:1.05em}}"
            f"{p} .lead2{{font-size:.74em;color:var(--sub);line-height:1.45;margin-top:.15em}}{p} .lead2 b{{color:var(--ink)}}"
            f"{p} .menu{{padding:0 .9em .9em;display:flex;flex-direction:column;gap:.6em;flex:1;min-height:0}}{p} .menu.tight{{gap:.26em}}"
            f"{p} .m{{background:#fff;border-radius:.3em;padding:.72em .9em;box-shadow:0 1px 0 rgba(15,42,85,.08);display:flex;flex-direction:column;gap:.45em}}"
            f"{p} .m.stk{{padding:.45em .85em .42em;gap:.24em}}"
            f"{p} .s1{{display:flex;justify-content:space-between;align-items:flex-end;gap:.5em}}"
            f"{p} .s1>b{{flex:1;min-width:0;font-size:1.02em;font-weight:800;letter-spacing:-.03em;line-height:1.15;white-space:nowrap}}"
            f"{p} .s1 .cd{{font-size:.62em;font-weight:500;color:var(--sub);letter-spacing:0}}"
            f"{p} .why{{display:flex;align-items:center;gap:.4em;font-size:.76em;color:var(--sub);min-width:0;margin-top:.12em;font-weight:500;letter-spacing:0}}"
            f"{p} .why .wt{{white-space:nowrap}}"
            f"{p} .tag{{flex:none;white-space:nowrap;font-size:.95em;font-weight:800;border-radius:.25em;padding:.1em .55em;background:#E8EEF8;color:var(--blue)}}"
            f"{p} .tag.big{{background:#FBE9E7;color:var(--red)}}"
            f"{p} .s1 .pr{{font-size:1.3em;font-weight:800;letter-spacing:-.035em;line-height:1;text-align:right;white-space:nowrap}}"
            f"{p} .s1 .pr small{{display:block;font-size:.42em;font-weight:600;color:var(--sub);letter-spacing:0;margin-bottom:.2em}}"
            f"{p} .tg{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.3em}}"
            f"{p} .tg div{{border-top:1px solid #EDF0F5;padding:.12em 0 0;display:flex;flex-direction:column;min-width:0}}"
            f"{p} .tg .w2{{grid-column:span 2}}"
            f"{p} .tg small{{font-size:.62em;color:var(--sub);white-space:nowrap}}{p} .tg b{{font-size:.84em;font-weight:800;white-space:nowrap}}"
            f"{p} .tg .r b{{color:var(--red)}}{p} .tg .bl b{{color:var(--blue)}}"
            f"{p} .sub2{{font-size:.68em;color:var(--sub);line-height:1.4}}"
            f"{p} .step{{display:grid;grid-template-columns:3.3em 1fr;gap:.6em;align-items:baseline;font-size:.86em}}"
            f"{p} .step b{{font-weight:800;color:var(--blue)}}{p} .step.r b{{color:var(--red)}}{p} .step span{{line-height:1.5}}{p} .step em{{font-style:normal;font-weight:800}}"
            f"{p} .m.hot{{background:var(--ink);color:#fff}}{p} .m.hot b{{font-size:.92em}}{p} .m.hot p{{font-size:.82em;color:#AEB8C8;line-height:1.5}}"
            f"{p} .m.zero b{{font-size:3em;font-weight:800;line-height:1}}{p} .m.zero p{{font-size:.86em;color:var(--sub)}}"
            f"{p} .fn{{display:grid;grid-template-columns:1fr auto;gap:.15em .6em;font-size:.82em;align-items:baseline}}"
            f"{p} .fn span{{color:var(--sub);line-height:1.3}}{p} .fn b{{font-weight:800;font-size:1.1em}}"
            f"{p} .fn i{{grid-column:1/-1;height:.4em;border-radius:.2em;background:#C9D3E3;display:block}}"
            f"{p} .fn.hl span{{color:var(--ink);font-weight:700}}{p} .fn.hl i{{background:var(--blue)}}"
            f"{p} .fn.hl2 span{{color:var(--red);font-weight:800}}{p} .fn.hl2 b{{color:var(--red)}}{p} .fn.hl2 i{{background:var(--red)}}"
            f"{p} .d{{font-size:.76em;color:var(--sub);line-height:1.45;padding:0 .3em}}"
            f"{p} .m.br{{padding:.48em .85em;gap:.2em}}{p} .bh{{display:flex;align-items:baseline;gap:.5em;white-space:nowrap}}"
            f"{p} .bh b{{font-size:.98em;font-weight:800}}"
            f"{p} .bh .sz{{font-size:.68em;font-weight:700;color:var(--sub);background:var(--tile);border-radius:.25em;padding:.05em .5em}}"
            f"{p} .bh .sz.big{{color:var(--red);background:#FBE9E7}}{p} .bh em{{margin-left:auto;font-style:normal;font-size:.76em;font-weight:800;color:var(--blue)}}"
            f"{p} .m.br p{{font-size:.74em;color:var(--sub);line-height:1.4}}"
            f"{p} .ln{{display:flex;justify-content:space-between;align-items:baseline;gap:.6em}}{p} .ln b{{font-size:.94em;font-weight:800}}"
            f"{p} .ln em{{font-style:normal;font-size:.86em;font-weight:700;color:var(--blue);white-space:nowrap}}"
            f"{p} .m .d{{padding:0}}"
            f"{p} .menu.fill .m{{flex:1;justify-content:center}}{p} .step.num{{grid-template-columns:1.4em 1fr;gap:.5em;font-size:.92em}}"
            f"{p} .step.num b{{font-size:1.05em}}"
            f"{p} .m.tests{{gap:.28em;padding:.65em .85em}}{p} .m.tests .d{{font-size:.7em;line-height:1.35;margin-bottom:.15em}}{p} .m.tests .ln b{{font-size:.88em}}"
            f"{p} .bigv{{font-size:3.4em;font-weight:800;letter-spacing:-.05em;line-height:1}}{p} .bigv small{{font-size:.4em;color:var(--sub);margin-left:.15em}}"
            f"{p} .six{{display:grid;grid-template-columns:repeat(3,1fr);gap:.6em .5em}}{p} .six div{{display:flex;flex-direction:column}}"
            f"{p} .six small{{font-size:.72em;color:var(--sub)}}{p} .six b{{font-size:1.15em;font-weight:800}}"
            f"{p} .foot{{font-size:.72em;color:var(--sub);padding:0 1.2em 1.1em;margin-top:auto}}"
            # 10/20 사용자 「이렇게 할거면 배경색도 맞춰야할 것 같은데!」 — 퀀트 화면 바탕·날짜 줄을 홈 푸른 회색 계열로(새 카드가 나올 때만 · 옛 화면은 베이지 그대로)
            f"section#qt{{background:#E3E8EF;color:#1A2333}}"
            f"html:has(section#qt:not([hidden])),html:has(section#qt:not([hidden])) body{{background:#E3E8EF}}"
            f"section#qt .top{{background:#E3E8EF;border-bottom:1px solid #D3DAE4}}"
            f"section#qt .tbtn{{background:#fff;border-color:#D3DAE4;color:#5B6678}}"
            f"section#qt .tbtn:hover{{border-color:#2E5FB8;color:#1A2333}}"
            f"section#qt .top .now{{color:#1A2333}}"
            f"#qt.past .qn34{{display:none!important}}"
            f"@media(min-width:900px){{#qt .qhint{{display:none}}}}"
            "</style>")
