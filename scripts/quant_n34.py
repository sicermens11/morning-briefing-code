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

_섹이름 = f"섹터 {len(R.섹터규칙)}업종"   # 10/21 점검: 「섹터 6업종」 을 손으로 적어 섹터 수가 바뀌면 「오늘 N」 이 0 이 될 뻔했다
갈래이름 = [("섹터규칙", _섹이름), ("기존규칙", "크게 빠짐"), ("시장규칙", "시장 급락"), ("변동성자사주", "변동성·자사주"), ("업종규칙", "업종")]
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
    if g == _섹이름:
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


# ⭐ 10/20 ① 후보 종목 소식 (사용자 「오케이 진행해」) — data/news/{코드}.json · 최근 5거래일쯤(7일) · 제목에 회사 이름이 「그대로」 있는 것만
#    이름 바로 뒤에 한글이 붙으면(「삼영」 → 「삼영검사엔지니어링」) 다른 회사로 보고 뺀다 · 조사(은는이가…)는 받는다
#    좋은 소식인지 나쁜 소식인지는 판단하지 않는다 — 제목만 보여 준다
_조사 = set("은는이가을를의에와과도로만")
_소식캐시 = {}


def _소식(code, 이름, 기준):
    if not code or not 이름:
        return []
    k = (code, 기준)
    if k in _소식캐시:
        return _소식캐시[k]
    out = []
    try:
        import datetime as _dt
        import re as _re
        d = json.load(io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "news", f"{code}.json"), encoding="utf-8-sig"))
        끝 = _dt.date.fromisoformat(기준)
        시작 = (끝 - _dt.timedelta(days=7)).strftime("%Y%m%d")
        본 = set()
        for it in (d.get("뉴스") or []):
            날 = str(it.get("날짜") or "")
            제 = str(it.get("제목") or "").strip()
            if not (len(날) == 8 and 시작 <= 날 <= 끝.strftime("%Y%m%d")) or not 제:
                continue
            ok = False
            for m in _re.finditer(_re.escape(이름), 제):
                뒤 = 제[m.end():m.end() + 1]
                if not 뒤 or not ("가" <= 뒤 <= "힣") or 뒤 in _조사:
                    ok = True
                    break
            if not ok or 제 in 본:
                continue
            본.add(제)
            out.append({"날": f"{int(날[4:6])}/{int(날[6:8])}", "제목": 제, "언론": it.get("언론사") or "", "키": 날 + str(it.get("시각") or "")})
        out.sort(key=lambda z: z["키"], reverse=True)
    except Exception:  # noqa: BLE001
        out = []
    _소식캐시[k] = out
    return out


def _종목상자(x, 업, 상태, 보완=False, 소식수=0):
    갈 = ([(("대형 · 주문 안 함" if not getattr(R, "보완대형주문", True) else "대형 · 주의") if x.get("보완규칙") == "대형" else "중형")] if 보완 else _갈래(x))
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
        a, b = R.매수범위(x.get("어제종가", 0) or 0, R.보완상대갭 if 보완 else None)   # 10/21 점검: 보완은 제 문턱(−1.0)
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
            + f'<span class="wt">{_e(왜)}</span>'
            + f'</small></b>{값}</div>'
            f'<div class="tg">{칸}</div><p class="sub2">' + (f'<span class="nw">소식 {소식수}</span> ' if 소식수 else '') + f'{_e(줄)}</p></div>')


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


def _비교(줄들):
    r"""⭐ 10/20 ③ 브리핑 추천 vs 퀀트 후보 — 같은 잣대: 그날 시가에 샀다고 보고 · 20일 안에 +15% 닿았나 · 20일 뒤 수익
    브리핑 = data/backtest-returns.jsonl (D20.실전 · D20.최고) · 퀀트 = forward-log 후보(중간성적 D+20 · 결과·며칠 · 체결)
    채점이 끝난(20일 지난) 것만 센다 — 채점 전 건수도 같이 돌려준다"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    br = []
    try:
        for z in io.open(os.path.join(base, "data", "backtest-returns.jsonl"), encoding="utf-8"):
            if z.strip():
                br.append(json.loads(z))
    except Exception:  # noqa: BLE001
        br = []
    def 통(rs):
        # (건수, 닿은 %, 20일 뒤 평균, 닿은 건수) — 10/21 닿은 건수를 더했다(20건 전엔 % 대신 건수로 보인다)
        rs = [r for r in rs if r[1] is not None]
        if not rs:
            return None
        k = sum(1 for r in rs if r[0])
        return (len(rs), k / len(rs) * 100, sum(r[1] for r in rs) / len(rs), k)
    # ⭐ 10/21 같은 날들 · 같은 비용 — 독립 점검 「기간(브리핑 7/29~ · 퀀트 9/4~)과 비용이 다르다」 → 사용자 「넷다 진행하자」
    #    퀀트 기록이 시작된 날부터만 · 브리핑 D20 「실전」(그날 시가 기준 · 비용 없음)에도 퀀트와 같은 0.26% 를 뺀다
    _시작들 = []
    for r in 줄들 or []:
        _m = str(r.get("매수일") or "")
        if len(_m) == 8 and _m.isdigit() and any((x.get("오늘산다") or x.get("규칙매수")) for x in r.get("후보") or []):
            _시작들.append(f"{_m[:4]}-{_m[4:6]}-{_m[6:8]}")
    시작날 = min(_시작들) if _시작들 else "9999-99-99"
    br = [r for r in br if str(r.get("날짜") or "") >= 시작날]
    b표 = [(bool((r.get("D20") or {}).get("최고") is not None and r["D20"]["최고"] >= 15),
            (None if (r.get("D20") or {}).get("실전") is None else r["D20"]["실전"] - 0.26)) for r in br]
    b전 = sum(1 for r in br if not (isinstance(r.get("D20"), dict) and r["D20"].get("실전") is not None))
    b코드 = {(str(r.get("날짜") or ""), str(r.get("코드") or "")): r for r in br}
    q체, q전, 둘 = [], [], []
    q대기 = 0
    for r in 줄들 or []:
        매 = str(r.get("매수일") or "")
        매 = f"{매[:4]}-{매[4:6]}-{매[6:8]}" if len(매) == 8 and 매.isdigit() else 매
        for x in r.get("후보") or []:
            if not (x.get("오늘산다") or x.get("규칙매수")):
                continue
            d20 = (x.get("중간성적") or {}).get("D+20")
            닿 = bool(x.get("결과") is not None and x["결과"] > 14 and x.get("며칠") is not None and x["며칠"] <= 20)   # 10/21 점검: 산 날 닿음(며칠 0)이 「or 99」 로 안 닿음이 됐다
            if d20 is None:
                q대기 += 1
                continue
            q전.append((닿, d20))
            if x.get("체결"):
                q체.append((닿, d20))
            bb = b코드.get((매, str(x.get("종목코드") or "")))
            if bb is not None:
                둘.append((닿, d20))
    return {"브리핑": 통(b표), "브리핑대기": b전, "퀀트체결": 통(q체), "퀀트전부": 통(q전), "퀀트대기": q대기, "둘다": 통(둘),
            "시작날": 시작날 if 시작날 != "9999-99-99" else ""}


비교최소 = 20   # 10/21 이만큼 모이기 전엔 % 대신 건수 — 「건수가 적을 땐 우연이 크다」 를 화면이 직접 지킨다


def _비교칸(t, 셀):
    r"""채점 한 줄의 세 칸(건수 · 닿음 · 20일 뒤) — 20건 전엔 「k건 닿음 · 20건까지 m건」"""
    if not t:
        return f'<td>0</td><td colspan="2" class="{셀}">채점 끝난 것 없음</td>'
    n, 퍼, 평, k = t
    if n < 비교최소:
        return (f'<td>{n}</td><td colspan="2" class="{셀}">{k}건 닿음 · {비교최소}건까지 {비교최소 - n}건'
                f'<small>평균은 {비교최소}건 모이면</small></td>')
    return (f'<td>{n}</td><td>{퍼:.0f}%</td><td class="{"pos" if 평 >= 0 else "neg"}">{_퍼(평)}</td>')


def 덱(q, 보유, 기록줄=None):
    r"""새 카드 묶음 HTML (카드들만). 실패하면 예외를 그대로 던진다 — quant_cards 가 옛 화면으로 돌아간다"""
    import quant_cards as Q
    d = dict(Q._폰자료)
    상태 = d.get("상태")
    목록 = list(d.get("목록") or [])
    업 = Q._업종표()
    장 = []
    기준 = str(q.get("기록시각") or "")[:10]
    보전체, _, _ = Q._보완자료(q)
    # 10/21 화면엔 보완 최대 R.보완화면최대(20일 낙폭 깊은 순) · 나머지는 개수만 — 기록·채점은 전부(사용자 「일단 권고대로하자」)
    보 = R.보완화면(보전체)   # 10/21 기록(record_pick 「화면」)과 같은 함수
    소식표 = {x.get("종목코드"): _소식(x.get("종목코드"), x.get("이름"), 기준) for x in 목록 + 보} if 기준 else {}
    # ── 종목 장 (한 장에 셋 · 첫 장 위 띠) ──
    if 목록:
        for i in range(0, len(목록), 3):
            조각 = 목록[i:i + 3]
            머리 = (_띠(q, d, len(목록)) if i == 0 else
                   _위(f"{'살 종목' if 상태 == 'buy' else '볼 종목'} {i + 1}–{i + len(조각)} / {len(목록)}", "사는 값과 파는 값"))
            장.append(_카드(머리, '<div class="menu tight">' + "".join(_종목상자(x, 업, 상태, 소식수=len(소식표.get(x.get("종목코드")) or [])) for x in 조각) + '</div>'))
    else:
        장.append(_카드(_띠(q, d, 0), '<div class="menu"><div class="m zero"><b>0개</b><p>조건을 통과한 종목이 없습니다. '
                     '규칙을 낮춰 억지로 후보를 만들지 않습니다. 이런 날은 열흘에 세 번쯤 있습니다.</p></div></div>'))
    # ── 보완 ──
    for i in range(0, len(보), 3):
        조각 = 보[i:i + 3]
        머리 = (f'<div class="nh"><p class="k"><span>보완 후보 {len(보전체)}{f" 중 {_보순말(보전체)} {len(보)}" if len(보전체) > len(보) else ""} · 지금 규칙 주문과 따로</span><span>@@PG@@</span></p>'
               f'<p class="lead2"><b>대형</b> {R.보완대형["시총억"][0] / 10000:g}조↑·40일 {R.보완대형["낙40"]:g}% · '
               f'<b>중형</b> {R.보완중형["시총억"][0]:,}억~{R.보완중형["시총억"][1] / 10000:g}조·지수 20일 {R.보완중형["지수낙20"]:g}% · '
               f'시장보다 <b>{abs(R.보완상대갭):g}%p</b> 싸게 시작하면 삼 · {"대형은 주문 안 함(10/22 · 11년 본전 · 보탬 없음)" if not getattr(R, "보완대형주문", True) else "대형은 더 빠진 적 있음(2023 −86%)"}</p></div>')
        장.append(_카드(머리, '<div class="menu tight">' + "".join(_종목상자(x, 업, "buy", 보완=True, 소식수=len(소식표.get(x.get("종목코드")) or [])) for x in 조각) + '</div>'))
    # ── 후보 종목 소식 — 규칙은 안 본다 · 참고만 (10/20 ① · 10/21 제목 바꿈) — 소식 있는 종목만 · 한 종목 2건까지 · 한 장에 종목 넷까지(넘치면 다음 장)
    있음 = [x for x in 목록 + 보 if 소식표.get(x.get("종목코드"))]
    없음 = [x.get("이름", "") for x in 목록 + 보 if not 소식표.get(x.get("종목코드"))]
    for i in range(0, len(있음), 3):
        조각 = 있음[i:i + 3]
        블록 = ""
        for x in 조각:
            ns = 소식표[x.get("종목코드")]
            갈 = (["대형 · 보완" if x.get("보완규칙") == "대형" else "중형 · 보완"] if x.get("보완규칙") else _갈래(x))
            블록 += (f'<div class="m ns"><div class="h"><b>{_e(x.get("이름", ""))}</b>'
                    + (f'<span class="tag{" big" if (x.get("보완규칙") or (갈 and 갈[0] == "크게 빠짐")) else ""}">{_e(갈[0])}</span>' if 갈 else "")
                    + f'<em>뉴스 {len(ns)}</em></div>'
                    + "".join(f'<div class="it"><i>{_e(n["날"])}</i><span>{_e(n["제목"])}<small> {_e(n["언론"])}</small></span></div>' for n in ns[:2])
                    + '</div>')
        끝장 = (i + 3 >= len(있음))
        장.append(_카드(_위(f"오늘 후보 종목 소식 · 최근 7일 · 제목에 회사 이름이 있는 것만", "규칙은 이 소식을 안 봅니다 · 참고만"),   # 10/21 사용자 「너권고대라하자」 — 「사기 전에 알아 둘 소식」 이 빼라는 뜻으로 읽혔다(우진엔텍)
            f'<div class="menu tight">{블록}'
            + (f'<p class="none">소식 없음 · {_e(" · ".join(없음))}</p>' if (끝장 and 없음) else "")
            + '</div>'))
    # ── 무엇을 노리나 ──
    s = Q._사례()
    도 = s.get("도달률") or s.get("승률")
    장.append(_카드(_위("이 규칙은 무엇을 노리나", "좋은 회사가 같이 빠진 날을 노립니다", 작게=False),
        '<div class="menu fill">'
        '<div class="m"><div class="step num"><b>①</b><span>시장이 통째로 크게 빠지거나 업종이 한꺼번에 빠지면, 튼튼한 회사도 <em>자기 잘못 없이</em> 같이 빠집니다.</span></div></div>'
        f'<div class="m"><div class="step num"><b>②</b><span>그런 회사는 제자리로 돌아오는 일이 많았습니다. 10년 동안 {s.get("전체건수", 0)}번 샀다면 <em>{도}%가 +{R.몫들[0][1]:g}%에 닿았습니다</em>.</span></div></div>'
        f'<div class="m"><div class="step num"><b>③</b><span>그래서 빠진 날 <em>더 싸게 시작할 때만</em> 사고, +{R.몫들[0][1]:g}%와 +{R.몫들[1][1]:g}%에 나눠 팝니다.</span></div></div>'
        '<div class="m hot"><b>사람이 고르지 않습니다</b><p>재무·주가·지수와 공시 몇 가지(자사주 매입 · 감자 · 유상증자)를 정해진 숫자로만 봅니다. 뉴스나 느낌은 쓰지 않습니다.</p></div>'
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
                 f'<em>오늘 {수.get(x0 if not x0.startswith("섹터") else _섹이름, 0)}</em></div><p>{_e(x2)}</p></div>' for x0, x1, x2 in 갈들)
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
        f'<p class="d">끝 자산은 남은 보유를 산 값으로 센 값입니다(다음 장 「해마다」는 매일 종가 평가라 조금 다릅니다). 모두 {s.get("전체건수", 0)}번 샀고 {도}%가 +{R.몫들[0][1]:g}%에 닿았습니다. {_e(Q._볼린저주의[0])} — {_e(Q._볼린저주의[1])} {_e(Q._성적주의[1])} {_e(Q._성적주의[3])}</p></div>'))
    # ── 해마다 어땠나 (10/21 사용자 「화면에 넣자.」) — data/rule-yearly.json(gate7 YEARLY) · 없으면 장을 안 만든다 ──
    y = _해마다()
    if y:
        줄 = "".join(f'<tr><td>{_e(z["해"])}{_e(_해꼬리(y, z))}</td><td class="{"pos" if z["수익"] >= 0 else "neg"}">{_퍼(z["수익"])}</td>'
                    f'<td>{z["산날"]}일</td><td>{z["오른달"]}/{z["달수"]}</td><td class="neg">{_퍼(z["나쁜달"])}</td></tr>' for z in y["해"])
        g = y.get("12달") or {}
        장.append(_카드(_위("해마다 어땠나 · 컴퓨터 계산 · 매일 종가로 평가", "1년씩 끊어 보면", 작게=False),
            '<div class="menu"><div class="m"><table class="vs yr"><thead><tr><th>해</th><th>수익</th><th>산 날</th><th>오른 달</th><th>가장 나쁜 달</th></tr></thead>'
            f'<tbody>{줄}</tbody></table></div>'
            + (f'<p class="d">아무 달에 시작해 1년 들고 있었다면 {g.get("번")}번 중 가장 나쁨 {_퍼(g.get("최악"))} · 가운데 {_퍼(g.get("가운데"))} · '
               f'잃은 번 {g.get("잃은")}(서로 겹치는 창) · 달 평균 {_퍼((y.get("달") or {}).get("평균"), 2)}(가운데 {_퍼((y.get("달") or {}).get("가운데"), 2)}) · '
               f'달 안에서 가장 깊이 {_퍼(y.get("낙폭"))} — 이 기간을 보고 맞춘 규칙이라 과거 시험이지 앞날 약속이 아닙니다.</p>' if g else "")
            + '</div>'))
    # ── 브리핑 추천 vs 퀀트 후보 (10/20 ③) ──
    try:
        v = _비교(기록줄)
    except Exception as _ex:  # noqa: BLE001
        print(f"  ⚠️ 브리핑 vs 퀀트 채점 실패: {type(_ex).__name__}: {_ex}")
        v = {}
    def 칸(이름, 설명, t):
        return f'<tr><td>{이름}<small>{설명}</small></td>{_비교칸(t, "few")}</tr>'
    장.append(_카드(_위("브리핑 추천 vs 퀀트 후보 · 같은 잣대로 채점", "어느 쪽이 더 맞았나", 작게=False),
        '<div class="menu"><div class="m"><table class="vs"><thead><tr><th>지난 기록</th><th>건수</th><th>20일 안 +15%</th><th>20일 뒤</th></tr></thead><tbody>'
        + 칸("브리핑 추천", "AI가 뉴스·수급으로", v.get("브리핑"))
        + 칸("퀀트 · 체결된 것", "시가가 주문가에 닿음", v.get("퀀트체결"))
        + 칸("퀀트 · 주문 전부", "체결 안 된 것까지", v.get("퀀트전부"))
        + 칸("둘 다 고른 종목", "같은 날 겹친 것", v.get("둘다"))
        + '</tbody></table>'
        f'<p class="d">{v.get("시작날") or "퀀트 기록 시작"}부터 같은 날들만 · 둘 다 비용 0.26% 뺌 · 20일이 지난 것만 셉니다. 채점 전 · 브리핑 {v.get("브리핑대기", 0)}건 · 퀀트 {v.get("퀀트대기", 0)}건. 건수가 적을 땐 우연이 큽니다.</p></div>'
        '<div class="m hot"><b>같은 잣대</b><p>둘 다 그날 시가에 샀다고 보고, 20일 안에 +15%에 닿았는지와 20일 뒤 수익으로 견줍니다.</p></div></div>'))
    n = len(장)
    return "".join(h.replace("@@PG@@", f"{i}/{n}") for i, h in enumerate(장, 1))


def _보순말(목록):
    r"""화면 보완 6개를 무슨 순서로 골랐나 — R.보완화면 과 같은 갈림(08:55 뒤 상대갭 · 그 전 20일 낙폭)"""
    return "싸게 시작할 순" if any(z.get("상대갭") is not None for z in (목록 or [])) else "20일 낙폭 깊은 순"


def _해마다():
    r"""data/rule-yearly.json (gate7 ONLY=YEARLY 가 쓴다) — 없거나 깨지면 None (칸을 안 만든다)"""
    try:
        y = json.load(io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rule-yearly.json"), encoding="utf-8"))
        return y if y.get("해") else None
    except Exception:  # noqa: BLE001
        return None


def _해꼬리(y, z):
    r"""첫 해·마지막 해는 일부만 — 「(4월~)」 「(~10/20)」"""
    a, b = (y.get("기간") or ["", ""])[:2]
    if z["해"] == a[:4] and a[4:6] != "01":
        return f" ({int(a[4:6])}월~)"
    if z["해"] == b[:4] and b[4:8] != "1231":
        return f" (~{int(b[4:6])}/{int(b[6:8])})"
    return ""


def _pc해마다():
    r"""PC 「해마다 어땠나」 — 해가 열(가로) · 수익 · 산 날 · 오른 달 · 가장 나쁜/좋은 달 (10/21 사용자 「화면에 넣자.」)"""
    y = _해마다()
    if not y:
        return ""
    hs = y["해"]
    머 = "".join(f'<th>{_e(z["해"])}<small>{_e(_해꼬리(y, z).strip(" ()")) or "&nbsp;"}</small></th>' for z in hs)
    def 줄(이름, f):
        return f'<tr><td class="l">{이름}</td>' + "".join(f(z) for z in hs) + '</tr>'
    g = y.get("12달") or {}
    dd = y.get("달") or {}
    return ('<div class="sec yr"><h2>해마다 어땠나 · 컴퓨터 계산 · 들고 있는 종목을 매일 종가로 평가</h2>'
            f'<table class="yt num"><tr><th class="l">해</th>{머}</tr>'
            + 줄("수익", lambda z: f'<td class="{"up" if z["수익"] >= 0 else "dn"}"><b>{_퍼(z["수익"])}</b></td>')
            + 줄("산 날", lambda z: f'<td>{z["산날"]}일</td>')
            + 줄("오른 달", lambda z: f'<td>{z["오른달"]}/{z["달수"]}</td>')
            + 줄("가장 나쁜 달", lambda z: f'<td class="dn">{_퍼(z["나쁜달"])}</td>')
            + 줄("가장 좋은 달", lambda z: f'<td class="up">{_퍼(z["좋은달"])}</td>')
            + '</table>'
            + (f'<p>아무 달에 시작해 <b>1년 들고 있었다면</b> {g.get("번")}번 중 가장 나쁨 <b>{_퍼(g.get("최악"))}</b> · 아래 10% {_퍼(g.get("아래10"))} · '
               f'가운데 <b>{_퍼(g.get("가운데"))}</b> · 위 10% {_퍼(g.get("위10"))} · 잃은 번 {g.get("잃은")}(달마다 민 창이라 서로 겹침 · 독립으로는 10개쯤) · '
               f'달로 보면 {dd.get("개수")}달 중 {dd.get("오른")}달 오름 · 달 평균 {_퍼(dd.get("평균"), 2)}(가운데 {_퍼(dd.get("가운데"), 2)}) · '
               f'가장 나쁜 달 {_퍼(dd.get("최악"))} · 달 안에서 가장 깊이 <b>{_퍼(y.get("낙폭"))}</b>. 사는 날이 1년에 며칠뿐이라 수익은 급락 뒤 몇 달에 몰립니다. '
               f'이 기간을 보고 맞춘 규칙이라 과거 시험이지 앞날 약속이 아닙니다.</p>' if g else "")
            + '</div>')


def _pc줄(x, i, 업, 보완=False, 소식수=0):
    r"""PC 한 표의 한 줄 — # · 종목 · 갈래 · 왜 · 주문가 · 팔 값 둘 · 상대갭(보완은 40일) · 20일 · 업종 · 시총 · 이익 · 빚 · 소식 · 코드
    10/21 사용자 「19에서 업종 · 시총 칸 나누는게 좋을 것 같은데」 → 「오케이 이렇게 바꾸자」"""
    갈 = ([(("대형 · 주문 안 함" if not getattr(R, "보완대형주문", True) else "대형 · 주의") if x.get("보완규칙") == "대형" else "중형")] if 보완 else _갈래(x))
    if 보완:
        왜 = (f"40일 {_퍼(x.get('40일낙폭'), 0)}" if x.get("보완규칙") == "대형"
              else f"{지수이름.get(x.get('시장키'), '지수')} 20일 {_퍼(x.get('시장지수낙20'), 0)} 날")
    else:
        왜 = _왜한줄(x, 갈)
    색 = (" r" if (보완 and x.get("보완규칙") == "대형") or (갈 and 갈[0] == "크게 빠짐") else (" o" if 보완 else ""))
    태 = (f'<span class="tg{색}">{_e(갈[0] + (f" +{len(갈) - 1}" if len(갈) > 1 else ""))}</span>' if 갈 else "")
    주 = x.get("주문가")
    if 주:
        팔 = _팔(주)
        값 = f'<td class="p">{_원(주)}</td><td class="up">{_원(팔[0])}</td><td class="up">{_원(팔[1])}</td>'
    else:   # 08:55 전 — 주문가가 아직 없다
        a, b = R.매수범위(x.get("어제종가", 0) or 0, R.보완상대갭 if 보완 else None)   # 10/21 점검: 보완은 제 문턱(−1.0)
        값 = (f'<td class="p">{_원(x.get("어제종가"))}<small>{_원(a)}~{_원(b)}</small></td>'
              '<td class="mu">—</td><td class="mu">—</td>')
    if 보완:
        v = x.get("40일낙폭")
        셋 = f'<td class="{"dn" if (v or 0) < 0 else "up"}">{_퍼(v)}</td>'
    elif x.get("상대갭") is not None:
        셋 = f'<td class="{"up" if x.get("예상통과") else "dn"}">{float(x["상대갭"]):+.2f}</td>'
    else:
        셋 = '<td class="mu">—</td>'
    v20 = x.get("20일낙폭")
    업이름 = (업.get(x.get("종목코드", "")) or {}).get("업종명") if isinstance(업.get(x.get("종목코드", "")), dict) else ""
    잉, 부 = x.get("잉여금비율"), x.get("부채비율")
    return (f'<tr><td>{i}</td><td class="n l">{_e(x.get("이름", ""))}</td><td class="l">{태}</td><td class="t l">{_e(왜)}</td>'
            f'{값}{셋}<td class="{"dn" if (v20 or 0) < 0 else "up"}">{_퍼(v20)}</td>'
            f'<td class="t l">{_e(업이름 or "—")}</td><td>{_억(x.get("시총억"))}</td>'
            f'<td>{f"{float(잉):.0f}%" if 잉 is not None else "—"}</td><td>{f"{float(부):.0f}%" if 부 is not None else "—"}</td>'
            f'<td>{f"<span class=nb>{소식수}</span>" if 소식수 else ""}</td><td class="l">{_e(x.get("종목코드", ""))}</td></tr>')


def PC(q, 보유, 기록줄=None):
    r"""⭐ PC 화면(1200px↑) — 10/21 두 번째 판: 한 표(시안 19) + 시간 순서(시안 16) + 설명 전부
    사용자 「PC화면 다시 봐꾸자 가독성이 안 좋은 것 같아」 → 시안 20개 → 「16,19 괜찮은 것 같다」 → 전체 페이지 시안
    https://claude.ai/artifact/XcuXg3k4v9K2yatzxkSD1A → 「오케이 이렇게 바꾸자」
    숫자는 덱() 과 같은 곳에서 — 터지면 quant_cards 가 이 판만 빼고 카드가 PC 에도 나온다"""
    import quant_cards as Q
    d = dict(Q._폰자료)
    상태 = d.get("상태")
    목록 = list(d.get("목록") or [])
    동 = q.get("동시호가") or {}
    업 = Q._업종표()
    기준 = str(q.get("기록시각") or "")[:10]
    보전체, _, _ = Q._보완자료(q)
    보 = R.보완화면(보전체)   # 10/21 기록(record_pick 「화면」)과 같은 함수
    소식표 = {x.get("종목코드"): _소식(x.get("종목코드"), x.get("이름"), 기준) for x in 목록 + 보} if 기준 else {}
    a1, a2 = R.몫들[0], R.몫들[1]
    몫1, 몫2 = f"{a1[0] * 100:g}", f"{a2[0] * 100:g}"
    # ── 맨 위 띠 ──
    try:
        import datetime as _dt
        _d = _dt.date.fromisoformat(기준)
        날글 = f"{_d.month}/{_d.day}({'월화수목금토일'[_d.weekday()]})"
    except ValueError:
        날글 = 기준
    제, 때 = {"buy": (f"{날글} 지정가 {len(목록)}개", f"{R.판정시각} 확정 · 09:01 안 찬 주문 취소"),
             "pre": (f"{날글} 볼 종목 {len(목록)}개", f"주문가는 {R.판정시각}에 확정"),
             "wait": (f"{날글} 살 것 없음", f"{R.판정시각} 확정")}.get(상태, (f"{날글} 후보 0개", "08:00 기준"))
    낙 = ((q.get("국면") or {}).get("지수낙폭") or {})
    왜값, 왜라벨 = "—", "왜 오늘"
    for k in ("KOSPI", "KOSDAQ"):
        v = 낙.get(k) or [None, None]
        if v[0] is not None and v[0] <= R.지수낙20문턱:
            왜값 = f"{지수이름[k]} 20일 {_퍼(v[0], 0)}"
            break
    갈수 = {}
    for x in 목록:
        for g in _갈래(x)[:1]:
            갈수[g] = 갈수.get(g, 0) + 1
    if 갈수:
        g0 = max(갈수, key=갈수.get)
        왜라벨 = f"왜 오늘 · {g0}"
        if 왜값 == "—":
            왜값 = f"{g0} {갈수[g0]}개"
    시장 = 동.get("예상시장갭")
    알림 = "".join(f'<p class="al">{_e(z)}</p>' for z in (d.get("알림말") or []))
    위 = (f'<div class="pt"><div class="tt"><b>{_e(제)}</b><span>{_e(때)}</span></div><div class="chips">'
         f'<div><span>{_e(왜라벨)}</span><b>{_e(왜값)}</b></div>'
         f'<div><span>시장 흐름(예상)</span><b>{_퍼(시장, 2) if 시장 is not None else R.판정시각 + "에"}</b></div>'
         f'<div><span>사는 문턱</span><b>시장 −{abs(R.상대갭문턱):g}%p</b></div>'
         + (f'<div><span>보완 후보</span><b>{len(보전체)}개 · 문턱 −{abs(R.보완상대갭):g}%p</b></div>' if 보전체 else "")
         + f'</div></div>{알림}')
    # ── 한 표 (오늘 주문 + 보완) ──
    값머리 = "주문가" if 상태 == "buy" else "전날 종가<small>주문가 자리</small>"
    머리 = (f'<tr><th>#</th><th class="l">종목</th><th class="l">갈래</th><th class="l">왜</th><th>{값머리}</th>'
           f'<th>{몫1}% 팔 값<small>+{a1[1]:g}%</small></th><th>{몫2}% 팔 값<small>+{a2[1]:g}%</small></th>'
           '<th>상대갭<small>보완은 40일</small></th><th>20일</th><th class="l">업종</th><th>시총</th>'
           '<th>이익<small>쌓은 이익</small></th><th>빚<small>부채</small></th><th>소식</th><th class="l">코드</th></tr>')
    주제목 = {"buy": f"오늘 주문 {len(목록)}", "pre": f"오늘 볼 종목 {len(목록)}", "wait": "오늘 살 것 없음"}.get(상태, "오늘 후보 0")
    표 = (f'<div class="sheet"><table class="num">{머리}'
         f'<tr class="grp"><td colspan="15">{_e(주제목)}<span>시가가 주문가 이하일 때만 체결</span></td></tr>')
    if 목록:
        표 += "".join(_pc줄(x, i, 업, 소식수=len(소식표.get(x.get("종목코드")) or [])) for i, x in enumerate(목록, 1))
    else:
        표 += ('<tr><td colspan="15" class="l t">조건을 통과한 종목이 없습니다. 규칙을 낮춰 억지로 후보를 만들지 않습니다. '
              '이런 날은 열흘에 세 번쯤 있습니다.</td></tr>')
    if 보:
        표 += (f'<tr class="grp"><td colspan="15">보완 후보 {len(보전체)}{f" 중 {_보순말(보전체)} {len(보)}" if len(보전체) > len(보) else ""}'
              f'<span>지금 규칙 주문과 따로 · 시장보다 {abs(R.보완상대갭):g}%p 싸게 열리면 삼 · {"대형은 주문 안 함(10/22 · 11년 본전 · 보탬 없음)" if not getattr(R, "보완대형주문", True) else "대형은 더 빠진 적 있음(2023 −86%)"}</span></td></tr>'
              + "".join(_pc줄(x, i, 업, 보완=True, 소식수=len(소식표.get(x.get("종목코드")) or [])) for i, x in enumerate(보, 1)))
    표 += ('</table><p class="foot">상대갭 = 9시 시가가 시장보다 얼마나 더 싸게 열릴지(08:55 예상) · '
          f'−{abs(R.상대갭문턱):g}보다 깊어야 체결 · 이익 = 쌓은 이익(잉여금) 비율 · 빚 = 부채 비율 · '
          '소식 = 최근 7일 제목에 회사 이름이 든 기사 수(규칙은 안 봄)</p></div>')
    # ── 시간 순서 ──
    순서 = ('<div class="tl"><h2>오늘 할 일 · 시간 순서</h2><div class="line">'
          f'<div class="st"><span class="t">{R.판정시각}</span><h3>위 표의 주문가로 지정가 매수를 겁니다</h3>'
          f'<p>하루 최대 {R.오늘최대종목(None)}개 + 섹터 {R.섹터전용자리}개 · 보완 후보는 지금 규칙과 따로입니다.</p></div>'
          f'<div class="st"><span class="t">09:00</span><h3>시가가 주문가 이하면 체결</h3>'
          f'<p>시장보다 {abs(R.상대갭문턱):g}%p(보완은 {abs(R.보완상대갭):g}%p) 더 싸게 열려야 삽니다. 안 열리면 안 삽니다.</p></div>'
          '<div class="st"><span class="t">09:01</span><h3>안 찬 주문은 반드시 취소</h3><p>장중에 내려와서 사면 규칙이 아닙니다.</p></div>'
          f'<div class="st"><span class="t">체결 뒤</span><h3>{몫1}%는 +{a1[1]:g}%, {몫2}%는 +{a2[1]:g}%에 매도 지정가</h3>'
          f'<p>값은 표의 「{몫1}% 팔 값 · {몫2}% 팔 값」 칸.</p></div>'
          f'<div class="st"><span class="t">{a1[2]}일</span><h3>+{a1[1]:g}%에 못 닿은 {몫1}%는 그날 정리</h3></div>'
          f'<div class="st"><span class="t">{a2[2]}일</span><h3>+{a2[1]:g}%에 못 닿은 {몫2}%도 그날 정리</h3>'
          '<p>손절은 없습니다. 감자·유상증자 같은 악재 공시가 나오면 다음 날 시가에 팝니다.</p></div></div></div>')
    # ── 세 칸: 무엇을 노리나 · 깔때기 · 사람이 고르지 않습니다 ──
    s = Q._사례()
    도 = s.get("도달률") or s.get("승률")
    노림 = ('<div class="sec steps"><h2>이 규칙은 무엇을 노리나</h2>'
          '<p><em>①</em>시장이 통째로 크게 빠지거나 업종이 한꺼번에 빠지면, 튼튼한 회사도 <b>자기 잘못 없이</b> 같이 빠집니다.</p>'
          f'<p><em>②</em>그런 회사는 제자리로 돌아오는 일이 많았습니다. 10년 동안 {s.get("전체건수", 0)}번 샀다면 <b>{도}%가 +{a1[1]:g}%에 닿았습니다.</b></p>'
          f'<p><em>③</em>그래서 빠진 날 <b>더 싸게 시작할 때만</b> 사고, +{a1[1]:g}%와 +{a2[1]:g}%에 나눠 팝니다.</p></div>')
    깔 = q.get("깔때기") or {}
    n전 = 깔.get("전체")
    깔줄 = [("상장 종목 전부", 깔.get("전체"), ""), (f"시가총액 {R.시총하한억:,.0f}억 이상", 깔.get("시총"), ""),
          (f"하루 거래 {R.대금하한억:g}억 이상", 깔.get("대금"), ""),
          (f"쌓은 이익 {R.잉여금하한:g}% · 빚 {R.부채상한:g}% 이하 · 흑자", 깔.get("재무"), ""),
          (f"상장 {R.상장최소거래일}거래일 · 관리·우선주·스팩 뺌", 깔.get("기본문"), ""),
          ("갈래 넷 중 하나", 깔.get("갈래"), "b"),
          ("시장보다 싸게 시작할 것 같은 순서로", len(목록) if n전 else None, "h")]
    if n전:
        fn = "".join(f'<div class="r {c}"><span>{_e(a)}</span><b class="num">{_원(b)}</b><i style="width:{max(1.0, (b or 0) / n전 * 100):.1f}%"></i></div>'
                     for a, b, c in 깔줄 if b is not None)
        깔제목 = f"{n전:,}종목에서 {len(목록)}개까지"
    else:
        fn = "".join(f'<div class="r"><span>{_e(a)}</span><b></b></div>' for a, _, _ in 깔줄[1:5])
        깔제목 = "이 조건을 모두 통과해야 후보"
    깔칸 = f'<div class="sec fn"><h2>{_e(깔제목)}</h2>{fn}</div>'
    사람 = ('<div class="sec dark"><h2>사람이 고르지 않습니다</h2>'
          '<p>재무·주가·지수와 공시 몇 가지(자사주 매입 · 감자 · 유상증자)를 정해진 숫자로만 봅니다. <b>뉴스나 느낌은 쓰지 않습니다.</b></p>'
          f'<p>{R.시총상한억:,.0f}억 이상 큰 회사는 섹터 갈래와 보완 후보(중형·대형)로만 나옵니다.</p></div>')
    # ── 두 칸: 갈래 넷 · 소식 ──
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
    갈칸 = ('<div class="sec br"><h2>갈래 넷 · 기본 조건을 먼저 통과한 뒤 하나에 걸리면 후보</h2>'
           + "".join(f'<div class="it"><div class="h"><b>{g}</b><span class="sz{" big" if c == "크기 상한 없음" else ""}">{c}</span>'
                     f'<em{" class=on" if 수.get(g if not g.startswith("섹터") else _섹이름) else ""}>오늘 {수.get(g if not g.startswith("섹터") else _섹이름, 0)}</em></div>{_e(t)}</div>'
                     for g, c, t in 갈들) + '</div>')
    있음 = [x for x in 목록 + 보 if 소식표.get(x.get("종목코드"))]
    없음 = [x.get("이름", "") for x in 목록 + 보 if not 소식표.get(x.get("종목코드"))]
    소블 = ""
    for x in 있음:
        ns = 소식표[x.get("종목코드")]
        갈 = (["대형 · 보완" if x.get("보완규칙") == "대형" else "중형 · 보완"] if x.get("보완규칙") else _갈래(x))
        색 = (" r" if (x.get("보완규칙") == "대형" or (갈 and 갈[0] == "크게 빠짐")) else (" o" if x.get("보완규칙") else ""))
        소블 += (f'<div class="it"><div class="h"><b>{_e(x.get("이름", ""))}</b>'
                + (f'<span class="tg{색}">{_e(갈[0])}</span>' if 갈 else "") + f'<em>뉴스 {len(ns)}</em></div>'
                + "".join(f'<p><i>{_e(n["날"])}</i>{_e(n["제목"])} <small>{_e(n["언론"])}</small></p>' for n in ns[:2]) + '</div>')
    소칸 = ('<div class="sec news"><h2>규칙은 이 소식을 안 봅니다 · 참고만</h2><span class="k">최근 7일 · 제목에 회사 이름이 있는 것만</span>'
           + 소블 + (f'<p class="none">소식 없음 · {_e(" · ".join(없음))}</p>' if 없음 else "") + '</div>')
    # ── 세 칸: 시험 · 과거 성적 · 브리핑 vs 퀀트 ──
    시줄, 시날 = Q._시험표()
    시칸 = ('<div class="sec tests"><h2>넣기 전에 이렇게 쟀습니다</h2>'
           + "".join(f'<div class="ln"><b>{_e(a)}</b><em>{_e(b)}</em></div><p>{_e(c)}</p>' for a, b, c in (시줄 or []))
           + f'<p class="when">시험 날짜 {_e(시날)} · 규칙이 바뀌면 다시 잽니다</p></div>') if 시줄 else '<div class="sec"></div>'
    try:
        cap = json.load(io.open(os.path.join(Q._DATA, "rule-capital.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cap = {}
    끝 = cap.get("끝자산")
    종낙 = (cap.get("종가") or {}).get("계좌낙폭")
    시작 = cap.get("시작자산") or 5e6
    여섯 = [("해마다", _퍼(cap.get("연평균"))), (f"+{a1[1]:g}% 닿음", f"{도}%"), ("한 번 평균", _퍼(s.get("평균"))),
           ("산 횟수", f"{s.get('전체건수', 0)}번"), ("최악 한 번", _퍼(s.get("가장나쁨"))), ("계좌 가장 깊이", _퍼(종낙) if 종낙 is not None else "—")]
    성칸 = (f'<div class="sec"><h2>과거 성적 · {str(s.get("기간") or "")[:4]}년부터 · 컴퓨터 계산</h2><span class="k">{시작 / 1e4:,.0f}만 원이 · 끝 자산은 남은 보유를 산 값으로 셈(아래 「해마다」는 매일 종가 평가)</span>'
           f'<div class="bigv num">{(끝 or 0) / 1e8:.2f}<small>억</small></div>'
           '<div class="six num">' + "".join(f'<div><span>{a}</span><b>{b}</b></div>' for a, b in 여섯) + '</div>'
           f'<p>{_e(Q._볼린저주의[0])} — {_e(Q._볼린저주의[1])} {_e(Q._성적주의[1])} {_e(Q._성적주의[3])}</p></div>')
    try:
        v = _비교(기록줄)
    except Exception as _ex:  # noqa: BLE001
        print(f"  ⚠️ PC 브리핑 vs 퀀트 채점 실패: {type(_ex).__name__}: {_ex}")
        v = {}

    def 비줄(이름, 설명, t):
        return f'<tr><td>{이름}<small>{설명}</small></td>{_비교칸(t, "few")}</tr>'
    비칸 = ('<div class="sec"><h2>브리핑 추천 vs 퀀트 · 같은 잣대</h2>'
           '<table class="vs num"><tr><th>지난 기록</th><th>건수</th><th>20일 안 +15%</th><th>20일 뒤</th></tr>'
           + 비줄("브리핑 추천", "AI가 뉴스·수급으로", v.get("브리핑"))
           + 비줄("퀀트 · 체결된 것", "시가가 주문가에 닿음", v.get("퀀트체결"))
           + 비줄("퀀트 · 주문 전부", "체결 안 된 것까지", v.get("퀀트전부"))
           + 비줄("둘 다 고른 종목", "같은 날 겹친 것", v.get("둘다"))
           + '</table>'
           f'<p>{v.get("시작날") or "퀀트 기록 시작"}부터 같은 날들만 · 둘 다 비용 0.26% 뺌 · 20일이 지난 것만 셉니다. '
           f'채점 전 · 브리핑 {v.get("브리핑대기", 0)}건 · 퀀트 {v.get("퀀트대기", 0)}건. 둘 다 그날 시가에 샀다고 보고 견줍니다.</p></div>')
    return (f'{위}{표}{순서}<div class="pg3">{노림}{깔칸}{사람}</div><div class="pg2">{갈칸}{소칸}</div>'
            f'<div class="pg3">{시칸}{성칸}{비칸}</div>{_pc해마다()}')


def PC_CSS(c1, c2):
    r"""PC 화면 — #qt .qpc 아래로만 · 1200px 이상에서 카드(.qn34)를 숨기고 이걸 보인다(이 CSS 가 없으면 카드가 PC 에 그대로)
    10/21 두 번째 판 — 시안 https://claude.ai/artifact/XcuXg3k4v9K2yatzxkSD1A 값 그대로"""
    p = "#qt .qpc"
    return ("<style>"
            f"{p}{{display:none;--ink:#151B26;--sub:#5E6878;--line:#D9DFE7;--up:#D0312D;--dn:#2459C4;--c1:{c1};--c2:{c2};"
            "max-width:1320px;margin:0 auto;padding:16px 24px 40px;color:var(--ink);word-break:keep-all;letter-spacing:-.01em}"
            "@media(min-width:1200px){#qt .qn34{display:none!important}#qt .qpc{display:block}}"
            "#qt.past .qpc{display:none!important}"
            f"{p} *{{box-sizing:border-box}}{p} h2,{p} h3,{p} p{{margin:0}}"
            f"{p} .num{{font-variant-numeric:tabular-nums}}{p} .up{{color:var(--up)}}{p} .dn{{color:var(--dn)}}{p} .mu{{color:var(--sub)}}"
            f"{p} .pt{{background:linear-gradient(90deg,var(--c1),var(--c2));color:#fff;display:flex;align-items:center;gap:22px;padding:18px 24px}}"
            f"{p} .pt .tt b{{display:block;font-size:26px;font-weight:900;white-space:nowrap;letter-spacing:-.02em}}"
            f"{p} .pt .tt span{{font-size:13px;color:rgba(255,255,255,.78)}}"
            f"{p} .chips{{display:flex;gap:10px;margin-left:auto}}{p} .chips div{{background:rgba(255,255,255,.13);padding:8px 14px;white-space:nowrap}}"
            f"{p} .chips span{{display:block;font-size:12px;color:rgba(255,255,255,.78)}}{p} .chips b{{font-size:17px;font-weight:800}}"
            f"{p} .al{{font-size:13px;font-weight:700;background:#FFF3D6;color:#8A5A00;padding:8px 14px}}"
            # 한 표
            f"{p} .sheet{{background:#fff;margin-top:14px;padding:16px 18px;font-size:15px}}"
            f"{p} .sheet table{{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',Consolas,'Pretendard Variable',Pretendard,monospace}}"
            f"{p} .sheet th,{p} .sheet td{{border:1px solid #E1E6ED;padding:8px 9px;text-align:right;white-space:nowrap}}"
            f"{p} .sheet th{{background:#EEF2F7;font-family:'Pretendard Variable',Pretendard,sans-serif;font-weight:700;font-size:12.5px;color:#3F4A5C}}"
            f"{p} .sheet th small,{p} .sheet td small{{display:block;font-weight:500;color:var(--sub);font-size:11px}}"
            f"{p} .sheet td.l,{p} .sheet th.l{{text-align:left}}"
            f"{p} .sheet tr:nth-child(even) td{{background:#FAFBFD}}"
            f"{p} .sheet td.n{{font-family:'Pretendard Variable',Pretendard,sans-serif;font-weight:800;font-size:15.5px}}"
            f"{p} .sheet td.t{{font-family:'Pretendard Variable',Pretendard,sans-serif;font-size:13.5px}}"
            f"{p} .sheet td.p{{font-weight:600;font-size:15.5px}}"
            f"{p} .sheet .grp td{{background:#1D2533!important;color:#fff;font-family:'Pretendard Variable',Pretendard,sans-serif;font-weight:700;text-align:left}}"
            f"{p} .sheet .grp td span{{font-weight:500;color:#AEB8C8;margin-left:10px}}"
            f"{p} .tg{{font-family:'Pretendard Variable',Pretendard,sans-serif;display:inline-block;font-size:12px;font-weight:700;padding:1px 7px;border-radius:3px;background:#E6EEFB;color:var(--dn);white-space:nowrap}}"
            f"{p} .tg.r{{background:#FDECEC;color:var(--up)}}{p} .tg.o{{background:#FFF0DE;color:#A85A00}}"
            f"{p} .nb{{font-family:'Pretendard Variable',Pretendard,sans-serif;font-size:12px;font-weight:700;color:#8A5A00;background:#FFF3D6;padding:1px 7px;border-radius:3px}}"
            f"{p} .sheet .foot{{font-size:14px;color:var(--sub);margin:10px 2px 0;line-height:1.6}}"
            # 시간 순서
            f"{p} .tl{{background:#fff;margin-top:14px;padding:24px 28px;font-size:16px}}"
            f"{p} .tl h2,{p} .sec h2{{font-size:19px;margin:0 0 16px;font-weight:800;color:var(--ink)}}"
            f"{p} .tl .line{{position:relative;padding-left:140px}}"
            f"{p} .tl .line::before{{content:'';position:absolute;left:110px;top:6px;bottom:6px;width:2px;background:var(--line)}}"
            f"{p} .tl .st{{position:relative;margin-bottom:18px}}{p} .tl .st:last-child{{margin-bottom:0}}"
            f"{p} .tl .st .t{{position:absolute;left:-140px;width:92px;text-align:right;font-weight:900;font-size:19px;color:var(--up)}}"
            f"{p} .tl .st::before{{content:'';position:absolute;left:-37px;top:7px;width:13px;height:13px;border-radius:50%;background:var(--up);border:3px solid #fff;box-shadow:0 0 0 1px var(--up)}}"
            f"{p} .tl .st h3{{font-size:17px;margin:0 0 3px}}{p} .tl .st p{{color:var(--sub);line-height:1.6}}"
            # 아래 칸들
            f"{p} .pg2{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:14px}}"
            f"{p} .pg3{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:14px}}"
            f"{p} .sec{{background:#fff;padding:22px 24px;font-size:15px;line-height:1.65;color:var(--sub)}}"
            f"{p} .sec .k{{display:block;font-size:12.5px;color:var(--sub);margin:-10px 0 10px}}{p} .sec b{{color:var(--ink)}}"
            f"{p} .sec.dark{{background:#1D2533;color:#C3CCDA}}{p} .sec.dark h2,{p} .sec.dark b{{color:#fff}}{p} .sec.dark p{{margin-bottom:10px}}"
            f"{p} .steps p{{margin:0 0 10px}}{p} .steps p em{{font-style:normal;font-weight:900;color:var(--dn);margin-right:8px}}"
            f"{p} .fn .r{{display:grid;grid-template-columns:1fr auto;gap:3px 10px;margin-bottom:8px;align-items:baseline}}"
            f"{p} .fn .r b{{font-weight:800;color:var(--ink)}}{p} .fn .r i{{grid-column:1/-1;height:6px;background:#CBD5E3;display:block}}"
            f"{p} .fn .r.b span{{color:var(--ink);font-weight:700}}{p} .fn .r.b i{{background:var(--dn)}}"
            f"{p} .fn .r.h span,{p} .fn .r.h b{{color:var(--up);font-weight:800}}{p} .fn .r.h i{{background:var(--up)}}"
            f"{p} .br .it,{p} .news .it{{border-top:1px solid #EDF0F5;padding:10px 0}}{p} .br .it:first-of-type,{p} .news .it:first-of-type{{border-top:0;padding-top:0}}"
            f"{p} .br .h,{p} .news .h{{display:flex;gap:8px;align-items:center}}{p} .br .h b{{font-size:16px}}{p} .news .h b{{font-size:15.5px}}"
            f"{p} .br .h em,{p} .news .h em{{margin-left:auto;font-style:normal}}{p} .br .h em{{font-weight:800;color:var(--dn)}}{p} .br .h em.on{{color:var(--up)}}{p} .news .h em{{font-size:12.5px}}"
            f"{p} .br .sz{{font-size:12px;font-weight:700;background:#F3F5F8;padding:1px 7px;border-radius:3px;color:var(--sub)}}{p} .br .sz.big{{background:#FDECEC;color:var(--up)}}"
            f"{p} .news p{{margin:4px 0 0;color:var(--ink)}}{p} .news p i{{font-style:normal;color:var(--sub);margin-right:6px}}{p} .news p small{{color:var(--sub)}}"
            f"{p} .news p.none{{font-size:13px;color:var(--sub);border-top:1px solid var(--line);padding-top:10px;margin-top:4px}}"
            f"{p} .tests .ln{{display:flex;justify-content:space-between;gap:10px;border-top:1px solid #EDF0F5;padding-top:8px;margin-top:8px}}"
            f"{p} .tests .ln:first-of-type{{border-top:0;margin-top:0;padding-top:0}}"
            f"{p} .tests .ln b{{font-size:15px}}{p} .tests .ln em{{font-style:normal;font-weight:800;color:var(--dn);white-space:nowrap}}"
            f"{p} .tests p{{margin:2px 0 0;font-size:13px}}{p} .tests p.when{{margin-top:10px}}"
            f"{p} .bigv{{font-size:46px;font-weight:900;color:var(--ink);letter-spacing:-.03em;line-height:1.1}}{p} .bigv small{{font-size:18px;color:var(--sub);margin-left:3px}}"
            f"{p} .six{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0}}{p} .six span{{display:block;font-size:12.5px}}{p} .six b{{font-size:18px}}"
            f"{p} .vs{{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:10px}}"
            f"{p} .vs th{{font-size:12.5px;font-weight:600;text-align:right;padding:6px 4px;border-bottom:1px solid var(--line);white-space:nowrap}}"
            f"{p} .vs th:first-child,{p} .vs td:first-child{{text-align:left}}"
            f"{p} .vs td{{padding:9px 4px;border-bottom:1px solid #EDF0F5;text-align:right;color:var(--ink);font-weight:700;white-space:nowrap}}"
            f"{p} .vs td small{{display:block;font-weight:500;color:var(--sub);font-size:12px}}"
            f"{p} .vs td.few{{color:var(--sub);font-weight:600;white-space:normal;line-height:1.4}}{p} .vs .pos{{color:var(--up)}}{p} .vs .neg{{color:var(--dn)}}"
            f"{p} .sec.yr{{margin-top:14px}}{p} .yt{{width:100%;border-collapse:collapse;font-size:14.5px;margin-bottom:12px}}"
            f"{p} .yt th{{font-size:13px;font-weight:700;color:var(--ink);text-align:right;padding:7px 6px;border-bottom:2px solid var(--ink);white-space:nowrap}}"
            f"{p} .yt th small{{display:block;font-weight:500;color:var(--sub);font-size:11px}}"
            f"{p} .yt td{{padding:8px 6px;text-align:right;border-bottom:1px solid #EDF0F5;white-space:nowrap;color:var(--ink)}}"
            f"{p} .yt td.l,{p} .yt th.l{{text-align:left;color:var(--sub);font-weight:600}}{p} .yt td.up{{color:var(--up)}}{p} .yt td.dn{{color:var(--dn)}}"
            "</style>")


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
            f"{p} .sub2{{font-size:.66em;color:var(--sub);line-height:1.4}}"
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
            f"{p} .vs{{width:100%;border-collapse:collapse;font-size:.8em}}{p} .vs th{{font-size:.82em;font-weight:600;color:var(--sub);text-align:right;padding:.3em .2em;border-bottom:1px solid #DCE2EA;white-space:nowrap}}"
            f"{p} .vs th:first-child,{p} .vs td:first-child{{text-align:left}}{p} .vs td{{padding:.5em .2em;text-align:right;border-bottom:1px solid #EDF0F5;font-weight:700;white-space:nowrap}}"
            f"{p} .vs td small{{display:block;font-weight:500;color:var(--sub);font-size:.8em}}{p} .vs .pos{{color:var(--red)}}{p} .vs .neg{{color:var(--blue)}}{p} .vs td.few{{color:var(--sub);font-weight:600;white-space:normal;line-height:1.35}}{p} .vs.yr{{font-size:.72em}}{p} .vs.yr th,{p} .vs.yr td{{padding:.21em .2em}}"   # 10/23 단서 한 줄 더 → 320폭 2px 잘림 → 표 줄 간격으로 벌었다(글은 안 깎는다)
            f"{p} .nw{{flex:none;white-space:nowrap;font-size:.9em;font-weight:800;border-radius:.2em;padding:0 .3em;background:#FFF3D6;color:#8A5A00}}"
            f"{p} .ns{{gap:.3em}}{p} .ns .h{{display:flex;align-items:baseline;gap:.45em;white-space:nowrap}}{p} .ns .h b{{font-size:.98em;font-weight:800}}"
            f"{p} .ns .h em{{margin-left:auto;font-style:normal;font-size:.7em;color:var(--sub)}}"
            f"{p} .ns .it{{display:grid;grid-template-columns:3.1em 1fr;gap:.45em;font-size:.76em;line-height:1.4}}{p} .ns .it i{{font-style:normal;color:var(--sub)}}"
            f"{p} .ns .it small{{color:var(--sub);font-size:.88em}}{p} .none{{font-size:.74em;color:var(--sub)}}"
            f"{p} .menu.fill{{gap:.48em}}{p} .menu.fill .m{{flex:1;justify-content:center}}{p} .step.num{{grid-template-columns:1.4em 1fr;gap:.5em;font-size:.92em}}"
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
