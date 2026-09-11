#!/usr/bin/env python3
r"""
omni_lab.py — **전방위 검증: 한 번 읽고 모든 것을 잰다** (2026-09-01 신설)

⚠️⚠️ **왜 하나로 합쳤나.** 검증할 축이 13개인데 따로 돌리면 **648일치를 13번 읽는다.**
   2026-09-01에 PC가 과부하로 얼어붙은 적이 있다. 한 번만 읽는다.

⚠️⚠️ **표를 메모리에 안 든다.** 648일 × 2,766종목 × 지평 3개 = **537만 행**이다.
   전부 들면 몇 GB다. **조건별 합계만 누적한다**(`_통`) — 메모리가 조건 수에 비례한다.

**네 겹 규칙**([[finish-data-before-concluding]])
```
① 초과수익률로        **실제 지수**(index-daily) 대비. 종목이 속한 시장(코스피/코스닥)으로
② 국면 갈라서         시장 상승일 / 하락일
③ 표본 밝히고         n을 항상 같이 쓴다. _MIN 미만은 "—"
④ 여러 지평          D+1 · D+5 · D+20
```

⚠️ **오염 제거**: 관리종목 · SPAC · 2024년 이후 신규상장 · 리츠/외국주권/예탁증권.
   이걸 안 빼면 **부실주의 급등락이 결과를 흔든다**.

⚠️ **look-ahead 방지**
```
분기재무   분기 종료 후 45일이 지나야 쓴다 (2025Q1 → 2025-05-15부터)
연간재무   다음 해 4월부터
컨센서스   리포트 **다음 거래일**부터
공시시각   그날 장 마감 후 공시는 **다음 거래일** 판단 재료
```

쓰는 법:
    python scripts\omni_lab.py             # 전부
    python scripts\omni_lab.py --축 재무    # 한 축만
"""
import datetime as dt
import glob
import io
import json
import os
import re
import statistics as st
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_H = (1, 5, 20)
_MIN = 100                      # 이 미만이면 "—". 축이 많아 문턱을 높였다
_MIN_MC = 5e10                  # 500억. 초소형은 호가가 튀어 결과를 흔든다
_MIN_AMT = 1e8                  # 하루 1억. 거래가 없는 종목 제외


# ────────────────────────────── 읽기 ──────────────────────────────
def _주가():
    """⚠️⚠️ **딕셔너리로 들지 않는다.** 648일 × 2,766종목 = 179만 개인데
       파이썬 딕셔너리 오버헤드 때문에 **2~3GB**가 된다 —
       2026-09-01에 PC가 과부하로 얼어붙은 적이 있다.
       **필요한 5개만 튜플**로 든다: (종가, 시총, 거래대금, 등락률, 시장)
    """
    표 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
                하루[c] = (종, float(v.get("시총") or 0), float(v.get("거래대금") or 0),
                           float(v.get("등락률") or 0),
                           1 if "KOSDAQ" in str(v.get("시장", "")).upper() else 0)
            except (TypeError, ValueError, KeyError):
                continue
        표[d["기준일"]] = 하루
    return 표


def 수정주가(항목=("시총", "거래대금")):
    r"""**수정주가 표** — {날: {코드: (수정종가, *항목값들)}}

    ⚠️⚠️⚠️ **2026-09-02 발견: KRX 종가는 수정주가가 아니다.**
    액면분할·액면병합·무상증자 권리락이 **종가에 반영돼 있지 않다.**
    반면 KRX가 같이 주는 **등락률은 조정을 반영한 실제 수익률**이다. 실측:
    ```
    20100113 012170  종가 90 → 4,590 = 계산상 **+5000%** · KRX 등락률 **−15.0%**
    20100112 066670  종가 6,760 → 3,520 = −47.9%       · KRX 등락률 −2.22%
    20100127 000590  종가 68,000 → 45,350 = −33.3%     · KRX 등락률 +14.96%
    ```
    오염은 4,749건 / 9,219,967 = **0.052%**로 극히 적은데,
    평균 일간수익률을 **종가기반 +0.8186% vs 등락률 +0.7626%**로 벌려놨다.
    **차이 +0.056%p/일 = 연 +13.7%p.** +5000% 하나가 평균을 통째로 흔든다.

    → 그래서 **등락률을 누적해 수정종가 계열을 다시 만든다.**
      수정종가[k] = 수정종가[k-1] × (1 + 등락률[k]/100)
    ⚠️ 등락률이 없는 날은 종가 변화로 잇되, ±32%를 넘으면(가격제한 초과 = 조정일)
      **수익률 0**으로 본다. 한국 가격제한은 ±30%다.
    ⚠️ **시총·거래대금은 원본 그대로** 쓴다(그날의 실제 값이 맞다).
    """
    표 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                if 종 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            등 = v.get("등락률")
            try:
                등 = float(등) if 등 not in (None, "") else None
            except (TypeError, ValueError):
                등 = None
            # ⚠️ **등락률 자체가 잘못 들어간 종목이 있다** (2026-09-02 발견).
            #    008080은 2013년 한 해 수익률이 **+326,026%**로 찍혀 전종목 평균을
            #    +337.6%로 만들었다(중앙값은 −2.0%였다). 047940은 등락률 163.16이었다.
            #    한국 가격제한은 ±30%(2015-06-15 이전 ±15%)다. **±31%를 넘으면 못 믿는다.**
            if 등 is not None and abs(등) > 31.0:
                등 = None
            벌 = []
            for k in 항목:
                try:
                    벌.append(float(v.get(k) or 0))
                except (TypeError, ValueError):
                    벌.append(0.0)
            하루[c] = (종, 등, tuple(벌))
        표[d["기준일"]] = 하루
    날 = sorted(표)
    앞원, 앞수 = {}, {}
    out = {}
    for d in 날:
        하루 = {}
        for c, (종, 등, 벌) in 표[d].items():
            p, s = 앞원.get(c), 앞수.get(c)
            if p is None or s is None:
                수 = 종                      # 첫 등장은 원가로 시작한다
            elif 등 is not None:
                수 = s * (1 + 등 / 100.0)
            else:
                r = 종 / p - 1 if p > 0 else 0.0
                수 = s * (1 + (0.0 if abs(r) > 0.32 else r))
            if 수 <= 0:
                수 = s if s and s > 0 else 종
            앞원[c], 앞수[c] = 종, 수
            하루[c] = (수,) + 벌
        out[d] = 하루
    return out


def _지수():
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "index-daily", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        z = d.get("지수") or {}
        a, b = (z.get("코스피") or {}).get("종가"), (z.get("코스닥") or {}).get("종가")
        if a and b:
            표[d["기준일"]] = {"KOSPI": a, "KOSDAQ": b,
                               "업종": {k: v.get("종가") for k, v in z.items()
                                        if v.get("종가")}}
    return 표


def _수급():
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "flow-daily", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        표[d["기준일"]] = d.get("종목") or {}
    return 표


def _환율():
    try:
        return json.load(io.open(os.path.join(_DATA, "fx-daily.json"),
                                 encoding="utf-8-sig")).get("USDKRW") or {}
    except Exception:
        return {}


def _기본():
    try:
        return json.load(io.open(os.path.join(_DATA, "stock-base.json"),
                                 encoding="utf-8-sig"))["종목"]
    except Exception:
        return {}


_호재 = ("단일판매", "공급계약", "수주", "자기주식취득", "무상증자", "실적", "흑자",
         "특허", "임상", "승인", "계약체결", "투자유치", "배당")
_악재 = ("유상증자", "전환사채", "신주인수권", "감자", "적자", "소송", "횡령", "배임",
         "상장폐지", "관리종목", "불성실공시", "영업정지", "회생")


def _성격(n):
    n = re.sub(r"\[[^\]]*\]", "", n or "")
    if any(k in n for k in _악재):
        return "악재"
    return "호재" if any(k in n for k in _호재) else "중립"


def _공시(날들):
    """{날짜: {코드: {성격들, 가장늦은분}}} — dart-daily + kind-time을 합친다."""
    시각 = {}
    for f in glob.glob(os.path.join(_DATA, "kind-time", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        시각[d["기준일"]] = d.get("시각") or {}
    out = {}
    for d8 in 날들:
        p = os.path.join(_DATA, "dart-daily", f"{d8}.json")
        if not os.path.exists(p):
            continue
        try:
            g = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:
            continue
        t = 시각.get(d8) or {}
        표 = {}
        for x in (g.get("챙길공시") or []):
            c = x.get("종목코드") or x.get("stock_code")
            if not c:
                continue
            hhmm = t.get(x.get("접수번호") or x.get("rcept_no"))
            분 = (int(hhmm[:2]) * 60 + int(hhmm[3:])) if hhmm else None
            e = 표.setdefault(c, {"성격": set(), "분": []})
            e["성격"].add(_성격(x.get("공시명") or x.get("report_nm")))
            if 분 is not None:
                e["분"].append(분)
        out[d8] = {c: {"성격": v["성격"], "분": (max(v["분"]) if v["분"] else None)}
                   for c, v in 표.items()}
    return out


def _분기재무():
    """{코드: [(적용시작일, {지표: 값})]} — ⚠️ 분기말+45일부터 쓴다(look-ahead 방지)."""
    def num(x):
        try:
            return float(str(x).replace(",", "").replace("%", ""))
        except (TypeError, ValueError):
            return None
    out = {}
    for f in glob.glob(os.path.join(_DATA, "naver-quarter", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        기간, 값 = d.get("분기") or [], d.get("값") or {}
        줄 = []
        for i, q in enumerate(기간):
            # ⚠️ 네이버는 "2025.06." 꼴로 준다(2026-09-01 확인). 숫자만 뽑는다.
            m = re.match(r"(\d{4})\D*(\d{2})", str(q) or "")
            if not m:
                continue
            y, mm = int(m.group(1)), int(m.group(2))
            if not (1 <= mm <= 12):
                continue
            적용 = (dt.date(y, mm, 1) + dt.timedelta(days=75)).strftime("%Y%m%d")
            줄.append((적용, {k: num(v[i]) for k, v in 값.items()
                              if isinstance(v, list) and i < len(v)}))
        if 줄:
            out[d["종목"]] = sorted(줄)
    return out


def _이벤트(폴더, 키="접수일"):
    """{코드: {날짜(YYYYMMDD)}} — 임원·대량보유처럼 rcept_dt가 있는 것."""
    out = {}
    for f in glob.glob(os.path.join(_DATA, 폴더, "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        s = {str(r.get(키)) for r in (d.get("이력") or []) if r.get(키)}
        if s:
            out[d["종목"]] = s
    return out


def _스냅(항목):
    """{코드: {해: [행…]}} — 사업보고서 연 스냅샷.
    ⚠️ **look-ahead**: 2024 사업보고서는 2025년 3~4월에 나온다 → **다음 해 4월부터** 쓴다.
    ⚠️ 필드 이름을 아직 실물로 못 봤다(2026-09-01 밤 기준 미수집). 그래서 여기서는
       **「그 해에 기록이 있나(건수>0)」**만 본다 — 필드명을 몰라도 안 깨진다.
    """
    out = {}
    for f in glob.glob(os.path.join(_DATA, "dart-snap", 항목, "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        해별 = d.get("해별") or {}
        표 = {y: len(v or []) for y, v in 해별.items()}
        if any(표.values()):
            out[d["종목"]] = 표
    return out


def _쓸수있는해(d8):
    """⚠️ 그 날짜에 **이미 공시된** 사업보고서의 사업연도. 4월 이전이면 2년 전 것."""
    y, m = int(d8[:4]), int(d8[4:6])
    return str(y - 1) if m >= 4 else str(y - 2)


def _fscore():
    """{코드: {적용시작일: 점수}} — **Piotroski F-Score(반쪽 7개)**.

    ⚠️⚠️ 사용자 질문에서 나왔다: *"검증된 점수표를 채용해도 되지 않아?"*
       → 재무 부분은 **F-Score(1998년, 40년 검증)**가 우리 「재무취약(−2)」보다 근거가 단단하다.
       우리 것은 항목 2개(부채비율·순이익률)에 검증 0이다.

    ⚠️ **9개 중 7개만 낸다.** `영업현금흐름`이 dart-fin에 없어 2개(현금흐름·발생액)를 못 쓴다.
    ```
    ① ROA>0  ② ROA 증가  ③ 부채비율 감소  ④ 유동비율 증가
    ⑤ 신주발행 없음(자본금 안 늘었나)  ⑥ 매출총이익률 증가  ⑦ 자산회전율 증가
    ```
    ⚠️ **look-ahead**: Y년 사업보고서는 Y+1년 3~4월에 나온다 → **Y+1년 4월부터** 쓴다.
    """
    해별 = {}
    for f in glob.glob(os.path.join(_DATA, "dart-fin", "*.json")):
        y = os.path.basename(f)[:-5]
        if not y.isdigit():
            continue
        try:
            해별[y] = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            pass
    해들 = sorted(해별)
    out = {}
    for i in range(1, len(해들)):
        전, 올 = 해별[해들[i - 1]], 해별[해들[i]]
        적용 = f"{int(해들[i]) + 1}0401"        # ⚠️ 다음 해 4월부터
        for c, a in 올.items():
            b = 전.get(c)
            if not b:
                continue
            def g(d, k):
                v = d.get(k)
                return v if isinstance(v, (int, float)) and v != 0 else None
            자산, 자산b = g(a, "자산총계"), g(b, "자산총계")
            순, 순b = a.get("당기순이익(손실)"), b.get("당기순이익(손실)")
            부, 부b = a.get("부채총계"), b.get("부채총계")
            유자, 유자b = a.get("유동자산"), b.get("유동자산")
            유부, 유부b = g(a, "유동부채"), g(b, "유동부채")
            매, 매b = a.get("매출액"), b.get("매출액")
            영비, 영비b = a.get("영업비용"), b.get("영업비용")
            자본, 자본b = a.get("자본금"), b.get("자본금")
            if 자산 is None or 자산b is None or 순 is None or 순b is None:
                continue
            점 = 0
            roa, roab = 순 / 자산, 순b / 자산b
            점 += 1 if roa > 0 else 0                                  # ①
            점 += 1 if roa > roab else 0                               # ②
            if 부 is not None and 부b is not None:
                점 += 1 if (부 / 자산) < (부b / 자산b) else 0           # ③
            if None not in (유자, 유자b, 유부, 유부b):
                점 += 1 if (유자 / 유부) > (유자b / 유부b) else 0        # ④
            if 자본 is not None and 자본b is not None:
                점 += 1 if 자본 <= 자본b else 0                         # ⑤
            if None not in (매, 매b, 영비, 영비b) and 매 and 매b:
                점 += 1 if ((매 - 영비) / 매) > ((매b - 영비b) / 매b) else 0   # ⑥
            if 매 is not None and 매b is not None:
                점 += 1 if (매 / 자산) > (매b / 자산b) else 0            # ⑦
            out.setdefault(c, {})[적용] = 점
    return out


def _계약():
    """{접수번호: {코드, 날짜, 금액}} → {날짜: {코드: 금액}} 로 뒤집는다.
    ⚠️ 아직 수집 전이면 빈 표다 → 해당 축은 «—»로 나온다."""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "contract", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for rc, v in (d.get("건") or {}).items():
            if v.get("금액") and v.get("날짜") and v.get("코드"):
                표.setdefault(v["날짜"], {})
                표[v["날짜"]][v["코드"]] = max(표[v["날짜"]].get(v["코드"], 0), v["금액"])
    return 표


def _컨센():
    """{코드: {날짜: 방향}} — 같은 증권사 직전 목표주가 대비."""
    리 = []
    for f in sorted(glob.glob(os.path.join(_DATA, "consensus", "*.json"))):
        리 += json.load(io.open(f, encoding="utf-8-sig"))["리포트"]
    리.sort(key=lambda r: r["날짜"])
    직전, out = {}, {}
    for r in 리:
        c, s, t = r.get("코드"), r.get("증권사"), r.get("목표주가")
        if not c or not s:
            continue
        앞 = 직전.get((c, s))
        if t:
            직전[(c, s)] = t
        if 앞 and t:
            방 = "상향" if t > 앞 * 1.01 else ("하향" if t < 앞 * 0.99 else "유지")
            out.setdefault(c, {})[r["날짜"].replace("-", "")] = 방
    return out


# ────────────────────────────── 축 정의 ──────────────────────────────
# (축이름, 라벨, 판정함수)  판정이 None이면 그 행은 어느 칸에도 안 들어간다
def _축들():
    A = []

    def add(축, 라벨, fn):
        A.append((축, 라벨, fn))

    # ── 1. 갭 ──
    add("갭", "공시 있음", lambda x: x["공시"])
    add("갭", "갭① 장 마감 후", lambda x: x["분"] is not None and x["분"] >= 930)
    add("갭", "갭① 장중", lambda x: x["분"] is not None and x["분"] < 930)
    add("갭", "호재+장후", lambda x: "호재" in x["성격"] and x["분"] is not None and x["분"] >= 930)
    add("갭", "호재+장중", lambda x: "호재" in x["성격"] and x["분"] is not None and x["분"] < 930)
    add("갭", "[①④] 호재+장후+무반응", lambda x: "호재" in x["성격"] and x["분"] is not None
        and x["분"] >= 930 and x["무반응"])
    add("갭", "[①③④] +수급", lambda x: "호재" in x["성격"] and x["분"] is not None
        and x["분"] >= 930 and x["무반응"] and x["갭3"])
    add("갭", "[①④] 정상종목만", lambda x: "호재" in x["성격"] and x["분"] is not None
        and x["분"] >= 930 and x["무반응"] and not x["더럽"])
    add("갭", "[①③④] 정상종목만", lambda x: "호재" in x["성격"] and x["분"] is not None
        and x["분"] >= 930 and x["무반응"] and x["갭3"] and not x["더럽"])

    # ── 2. 갭③ 수급 단독 ──
    add("수급", "외인·기관 동반매수", lambda x: x["갭3"])
    add("수급", "외인만 순매수", lambda x: x["외"] is not None and x["외"] > 0 and not x["갭3"])
    add("수급", "기관만 순매수", lambda x: x["기"] is not None and x["기"] > 0 and not x["갭3"])
    add("수급", "둘 다 순매도", lambda x: x["외"] is not None and x["기"] is not None
        and x["외"] < 0 and x["기"] < 0)
    add("수급", "호재 + 동반매수", lambda x: "호재" in x["성격"] and x["갭3"])
    add("수급", "호재 + 동반매수 없음", lambda x: "호재" in x["성격"] and not x["갭3"])

    # ── 3. 분기재무 (⚠️ 분기말+75일부터 적용) ──
    def q(k):
        return lambda x: x["재무"].get(k)
    add("재무", "순이익률 음수", lambda x: (q("순이익률")(x) or 0) < 0 if q("순이익률")(x) is not None else None)
    add("재무", "순이익률 10%↑", lambda x: q("순이익률")(x) >= 10 if q("순이익률")(x) is not None else None)
    add("재무", "부채비율 200%↑", lambda x: q("부채비율")(x) >= 200 if q("부채비율")(x) is not None else None)
    add("재무", "부채비율 100%↓", lambda x: q("부채비율")(x) < 100 if q("부채비율")(x) is not None else None)
    add("재무", "당좌비율 100%↓", lambda x: q("당좌비율")(x) < 100 if q("당좌비율")(x) is not None else None)
    add("재무", "당좌비율 200%↑", lambda x: q("당좌비율")(x) >= 200 if q("당좌비율")(x) is not None else None)
    add("재무", "ROE 15%↑", lambda x: q("ROE")(x) >= 15 if q("ROE")(x) is not None else None)
    add("재무", "ROE 음수", lambda x: q("ROE")(x) < 0 if q("ROE")(x) is not None else None)
    add("재무", "PER 10배↓", lambda x: 0 < q("PER")(x) <= 10 if q("PER")(x) is not None else None)
    add("재무", "PER 30배↑", lambda x: q("PER")(x) >= 30 if q("PER")(x) is not None else None)
    add("재무", "PBR 1배↓", lambda x: 0 < q("PBR")(x) <= 1 if q("PBR")(x) is not None else None)
    add("재무", "재무취약(스킬규칙)", lambda x: (
        None if q("부채비율")(x) is None and q("순이익률")(x) is None
        else ((q("부채비율")(x) or 0) >= 200 or (q("순이익률")(x) or 0) < 0)))

    # ── 4. 임원·대량보유 ──
    add("지분", "임원 신고 30일내", lambda x: x["임원30"])
    add("지분", "임원 신고 없음", lambda x: not x["임원30"])
    add("지분", "5% 신고 30일내", lambda x: x["대량30"])
    add("지분", "호재 + 임원 신고", lambda x: "호재" in x["성격"] and x["임원30"])

    # ── 5. 컨센서스 ──
    add("컨센", "목표주가 상향", lambda x: x["컨센"] == "상향")
    add("컨센", "목표주가 하향", lambda x: x["컨센"] == "하향")
    add("컨센", "목표주가 유지", lambda x: x["컨센"] == "유지")

    # ── 6. 크기·유동성 ──
    add("크기", "시총 3천억↓", lambda x: x["시총"] < 3e11)
    add("크기", "시총 3천억~1조", lambda x: 3e11 <= x["시총"] < 1e12)
    add("크기", "시총 1조↑", lambda x: x["시총"] >= 1e12)
    add("크기", "거래대금 10억↓", lambda x: x["대금"] < 1e9)
    add("크기", "거래대금 100억↑", lambda x: x["대금"] >= 1e10)

    # ── 7. 오염 ──
    add("오염", "관리종목·SPAC·신규·리츠", lambda x: x["더럽"])
    add("오염", "정상 종목", lambda x: not x["더럽"])

    # ── 8. 기술 (⚠️ 전에는 단순평균 시장으로 쟀다. 실제 지수로 다시) ──
    add("기술", "당일 급등 5%↑", lambda x: x["등락"] >= 5)
    add("기술", "당일 급락 5%↓", lambda x: x["등락"] <= -5)
    add("기술", "무반응 1%미만", lambda x: x["무반응"])

    # ── 9. 사업보고서 (⚠️ 다음 해 4월부터 적용) ──
    add("보고서", "자사주 취득 기록 있음", lambda x: (x["자사주해"] or 0) > 0
        if x["자사주해"] is not None else None)
    add("보고서", "자사주 기록 없음", lambda x: (x["자사주해"] or 0) == 0
        if x["자사주해"] is not None else None)
    add("보고서", "증자·감자 기록 있음", lambda x: (x["증감해"] or 0) > 0
        if x["증감해"] is not None else None)
    add("보고서", "호재 + 자사주 취득", lambda x: "호재" in x["성격"] and (x["자사주해"] or 0) > 0
        if x["자사주해"] is not None else None)

    # ── 10. **Piotroski F-Score (검증된 점수표)** vs 우리 재무취약
    add("F-Score", "6~7점 (튼튼)", lambda x: x["F"] >= 6 if x["F"] is not None else None)
    add("F-Score", "4~5점 (보통)", lambda x: 4 <= x["F"] <= 5 if x["F"] is not None else None)
    add("F-Score", "0~3점 (부실)", lambda x: x["F"] <= 3 if x["F"] is not None else None)
    add("F-Score", "호재 + 6점↑", lambda x: ("호재" in x["성격"] and x["F"] >= 6)
        if x["F"] is not None else None)
    add("F-Score", "호재 + 3점↓", lambda x: ("호재" in x["성격"] and x["F"] <= 3)
        if x["F"] is not None else None)

    # ── 11. 계약 규모 (계약금액 ÷ 시총) ──
    add("계약규모", "시총 1%↓ 소형계약", lambda x: x["계약비"] < 1
        if x["계약비"] is not None else None)
    add("계약규모", "시총 1~5%", lambda x: 1 <= x["계약비"] < 5
        if x["계약비"] is not None else None)
    add("계약규모", "시총 5~20%", lambda x: 5 <= x["계약비"] < 20
        if x["계약비"] is not None else None)
    add("계약규모", "시총 20%↑ 대형계약", lambda x: x["계약비"] >= 20
        if x["계약비"] is not None else None)

    # ── 12. 요일 ──
    for i, 요 in enumerate("월화수목금"):
        add("요일", f"{요}요일", (lambda k: (lambda x: x["요일"] == k))(i))

    # ── 13. 환율 국면 ──
    add("환율", "원/달러 상승일", lambda x: x["환"] is not None and x["환"] > 0)
    add("환율", "원/달러 하락일", lambda x: x["환"] is not None and x["환"] <= 0)
    add("환율", "호재+환율상승", lambda x: "호재" in x["성격"] and x["환"] is not None and x["환"] > 0)
    add("환율", "호재+환율하락", lambda x: "호재" in x["성격"] and x["환"] is not None and x["환"] <= 0)
    return A


# ────────────────────────────── 본체 ──────────────────────────────
def main():
    고른축 = sys.argv[sys.argv.index("--축") + 1] if "--축" in sys.argv else None
    print("  자료 읽는 중…", flush=True)
    주가 = _주가()
    날 = sorted(주가)
    지수, 수급, 환율, 기본 = _지수(), _수급(), _환율(), _기본()
    공시 = _공시(날)
    재무 = _분기재무()
    임원 = _이벤트("dart-exec")
    대량 = _이벤트("dart-major")
    컨센 = _컨센()
    계약 = _계약()
    fsc = _fscore()
    자사주 = _스냅("자기주식")
    소액 = _스냅("소액주주")
    증감 = _스냅("증자감자")
    print(f"  주가 {len(날)}일 · 지수 {len(지수)} · 수급 {len(수급)} · 공시 {len(공시)} "
          f"· 분기재무 {len(재무):,} · 임원 {len(임원):,} · 대량 {len(대량):,} "
          f"· 컨센 {len(컨센):,} · 환율 {len(환율)}", flush=True)
    print(f"  계약금액 {sum(len(v) for v in 계약.values()):,}건 "
          f"· F-Score {len(fsc):,}종목", flush=True)
    print(f"  자사주 {len(자사주):,} · 소액주주 {len(소액):,} · 증자감자 {len(증감):,}"
          + ("   ⚠️ 아직 수집 전이면 0이고 해당 축은 «—»로 나온다" if not 자사주 else ""),
          flush=True)

    축들 = [a for a in _축들() if not 고른축 or a[0] == 고른축]
    # 통계 누적: (축, 라벨, 국면, 지평) → [합, 개수]
    통 = {}

    def 담(키, v):
        s = 통.setdefault(키, [0.0, 0])
        s[0] += v
        s[1] += 1

    자리 = {d: i for i, d in enumerate(날)}
    행수 = 0
    for i, d1 in enumerate(날):
        s1 = 주가[d1]
        a = 지수.get(d1)
        if not a:
            continue
        # 그날 쓸 수 있는 지평만
        지평 = []
        for h in _H:
            j = i + h
            if j < len(날) and 지수.get(날[j]):
                지평.append((h, 날[j], 지수[날[j]]))
        if not 지평:
            continue
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        해 = _쓸수있는해(d1)
        요일 = dt.date(int(d1[:4]), int(d1[4:6]), int(d1[6:])).weekday()
        # 환율 등락(전 거래일 대비)
        환 = None
        if d1 in 환율 and i > 0 and 날[i - 1] in 환율:
            환 = 환율[d1] / 환율[날[i - 1]] - 1

        for code, v1 in s1.items():
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            f = fl.get(code) or {}
            외, 기 = f.get("외국인"), f.get("기관")
            r = ds.get(code) or {}
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            # ⚠️ 분기재무는 **적용시작일이 지난 것 중 가장 최근**만 쓴다(look-ahead 방지)
            fin = {}
            for 적용, 값 in (재무.get(code) or []):
                if 적용 <= d1:
                    fin = 값
                else:
                    break
            # 30일 이내 신고가 있었나
            def 최근(집):
                if not 집:
                    return False
                k = 자리.get(d1, 0)
                구간 = set(날[max(0, k - 20):k + 1])
                return bool(집 & 구간)
            x = {
                "공시": bool(r), "성격": r.get("성격", set()), "분": r.get("분"),
                "무반응": abs(등락) < 1, "등락": 등락, "시총": 시총, "대금": 대금,
                "외": 외, "기": 기,
                "갭3": (외 is not None and 기 is not None and 외 > 0 and 기 > 0),
                "더럽": (("관리종목" in 부) or ("SPAC" in 부)
                         or (str(bb.get("상장일") or "") > "20240101")
                         or (bb.get("증권구분") not in (None, "주권"))),
                "재무": fin,
                "임원30": 최근(임원.get(code)), "대량30": 최근(대량.get(code)),
                "컨센": (컨센.get(code) or {}).get(d1),
                "환": 환,
                "자사주해": (자사주.get(code) or {}).get(해),
                "소액해": (소액.get(code) or {}).get(해),
                "증감해": (증감.get(code) or {}).get(해),
                "요일": 요일,
                # ⚠️ 계약금액 ÷ 시총 (%) — 「15억 계약」과 「1조 계약」을 가른다
                "계약비": (((계약.get(d1) or {}).get(code) or 0) / 시총 * 100
                           if (계약.get(d1) or {}).get(code) and 시총 > 0 else None),
                "F": max([v for 적, v in (fsc.get(code) or {}).items() if 적 <= d1],
                         default=None),
            }
            # 축 판정을 한 번만 하고 지평마다 재사용
            맞 = []
            for 축, 라벨, fn in 축들:
                try:
                    t = fn(x)
                except Exception:
                    t = None
                if t:
                    맞.append((축, 라벨))
            if not 맞:
                continue
            for h, d2, b in 지평:
                v2 = 주가[d2].get(code)
                if not v2:
                    continue
                시장 = b[장] / a[장] - 1
                초과 = ((v2[0] / c1 - 1) - 시장) * 100
                국면 = "상승" if 시장 > 0 else "하락"
                행수 += 1
                for 축, 라벨 in 맞:
                    담((축, 라벨, "전체", h), 초과)
                    담((축, 라벨, 국면, h), 초과)
        if i % 100 == 0:
            print(f"    {i}/{len(날)}일 · 누적 관측 {행수:,}", flush=True)

    print(f"\n  총 관측 {행수:,}건 · 문턱 n≥{_MIN}\n", flush=True)
    순 = []
    for 축, 라벨, _ in 축들:
        if (축, 라벨) not in [(a, b) for a, b, _ in 축들]:
            continue
        if (축, 라벨) in 순:
            continue
        순.append((축, 라벨))
    현축 = None
    for 축, 라벨 in 순:
        if 축 != 현축:
            현축 = 축
            print(f"\n  ══════ {축} ══════")
            print(f"    {'조건':<24}{'국면':<5}{'D+1':>16}{'D+5':>16}{'D+20':>16}")
        for 국면 in ("전체", "상승", "하락"):
            칸 = []
            for h in _H:
                s = 통.get((축, 라벨, 국면, h))
                칸.append(f"{s[0]/s[1]:+.3f} (n={s[1]:,})" if s and s[1] >= _MIN else "—")
            if all(c == "—" for c in 칸):
                continue
            print(f"    {라벨 if 국면=='전체' else '':<24}{국면:<5}{칸[0]:>16}{칸[1]:>16}{칸[2]:>16}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ⚠️ 상장폐지되면 정리매매에서 크게 잃는다. 실제 -70~95%가 흔하지만
#    **보수적으로 -50%** 로 잡는다. 안 세는 것보다는 낫고 과하지도 않다
# ⚠ -90% 로 돌려보려면 환경변수 POLESON 을 준다 (167차 민감도)
#    실제 정리매매는 -70~95% 가 흔하다. 기본값은 보수적으로 -50%
폐지손실 = float(os.environ.get("POLESON") or -50.0)


def 사라진종목(주가, 날, 여유=30):
    r"""중간에 **영영 사라진** 종목 -> 마지막 등장일.

    ⚠️⚠️ **2026-09-08 신설.** 시뮬이 「자료가 없으면 그 거래를 지우는」
       식이라 **상장폐지 손실이 통째로 빠져 있었다.**
       실측: 3,678종목 중 913개(25%)가 중간에 사라졌고,
       그중 455개가 사라지기 전 90일에 10% 넘게 빠졌다 —
       **우리 규칙이 사고 싶어 하는 바로 그 모습**이다
    """
    마지막 = {}
    for d in 날:
        for c in 주가.get(d, {}):
            마지막[c] = d
    if not 날:
        return {}
    자름 = 날[-여유] if len(날) > 여유 else 날[-1]
    return {c: d for c, d in 마지막.items() if d < 자름}


# ══════════════════════════════════════════════════════════════════════
#  ⭐ **빠른 길** (2026-09-09 신설) — 기존 함수는 그대로 두고 **더한 것**이다
#     사용자: 「비효율적인 부분 너가 여러 분야에 걸쳐 한번 조사해봐」
# ══════════════════════════════════════════════════════════════════════

def 빠른평균표준(칸):
    r"""평균과 표준편차를 **한 번에** 낸다.

    ⚠️⚠️ `statistics.mean` + `statistics.pstdev` 는 **36배 느리다** (실측).
       st.mean+st.pstdev  16.5초 / 20만 회
       이 함수          0.5초 / 20만 회
       시험 하나(5.4M 사건)에서 **7분 -> 10초**
    """
    n = len(칸)
    if not n:
        return 0.0, 0.0
    m = 0.0
    for z in 칸:
        m += z
    m /= n
    v = 0.0
    for z in 칸:
        d = z - m
        v += d * d
    sd = (v / n) ** 0.5
    # ⚠⚠ **「0이면」이 아니라 「0에 가까우면」으로 막는다 (2026-09-09).
    #    statistics 는 분수로 셀셔 값이 같으면 표준편차가 **정확히 0**이다.
    #    직접 계산은 9.1e-13 같은 짜꿔기가 남아 `or 1e-9` 방어가 안 걸린다.
    #    -> 24,000회 중 36건(0.15%)에서 볼린저가 0.0 vs 0.5 로 갈렸다
    #    (판정에는 영향 없었지만 같은 값이 나와야 옥으로 견줄 수 있다)
    return m, (sd if sd >= 1e-9 else 0.0)


def 창평균표준(계열, 끝, 길이):
    r"""계열[끝-길이+1 : 끝+1] 의 (평균, 표준편차). 자르기도 안 한다"""
    시 = 끝 - 길이 + 1
    if 시 < 0 or 끝 >= len(계열):
        return None, None
    m = 0.0
    for i in range(시, 끝 + 1):
        m += 계열[i]
    m /= 길이
    v = 0.0
    for i in range(시, 끝 + 1):
        d = 계열[i] - m
        v += d * d
    sd = (v / 길이) ** 0.5
    return m, (sd if sd >= 1e-9 else 0.0)


_캐시폴더 = os.path.join(_DATA, "_cache")


def krx한번읽기(캐시쓰기=True):
    r"""**krx-daily 를 한 번만 파싱**해서 시험에 필요한 것을 다 만든다.

    돌려주는 것:
    ```
    주가   {날: {코드: (수정종가, 시총, 거래대금)}}    <- 수정주가()와 같다
    비     {날: {코드: (시가/종가, 고가/종가, 거래대금)}}
    갭표   {날: {코드: 갭%}}
    원시   {날: {코드: 원본 시가}}
    거량   {날: {코드: 거래량}}
    ```
    ⚠️⚠️ **전에는 같은 파일을 두 번 파싱했다** (실측 52초 + 62초 = 114초).
       lab 166개 중 **136개**가 그랬다. 한 번 읽으면 절반이다
    ⚠️ 캐시(pickle)를 쓰면 **3초**로 줄어든다 — 15배.
       krx-daily 의 마지막 파일 이름과 개수가 바뀌면 저절로 다시 만든다
    """
    import pickle
    파일들 = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    if not 파일들:
        return {}, {}, {}, {}, {}
    도장 = f"{len(파일들)}_{os.path.basename(파일들[-1])}"
    캐시 = os.path.join(_캐시폴더, f"krx_{도장}.pkl")
    if 캐시쓰기 and os.path.exists(캐시):
        try:
            with open(캐시, "rb") as f:
                return pickle.load(f)
        except Exception:  # noqa: BLE001
            pass

    주가, 비, 갭표, 원시, 거량 = {}, {}, {}, {}, {}
    앞종, 앞수정 = {}, {}
    for f in 파일들:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        d8 = d.get("기준일") or os.path.basename(f)[:8]
        하루갭 = {}
        for c, v in (d.get("종목") or {}).items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                량 = float(v.get("거래량") or 0)
                시총 = float(v.get("시총") or 0)   # ⚠ 원래 함수와 같은 키를 쓴다
            except (TypeError, ValueError, KeyError):
                continue
            if min(종c, 시, 고) <= 0:
                continue
            # ── 수정종가: 등락률을 누적한다 (수정주가()와 같은 규칙) ──
            try:
                등 = v.get("등락률")
                등 = float(등) if 등 not in (None, "") else None
            except (TypeError, ValueError):
                등 = None
            # ⚠⚠ **등락률 자체가 잘못 들어간 종목이 있다** (2026-09-02 발견).
            #    008080은 2013년 수익률이 **+326,026%** 로 찍혀
            #    전종목 평균을 +337.6% 로 만들었다.
            #    한국 가격제한은 ±30% — **±31%를 넘으면 못 믿는다**
            #    ⚠ 이 줄을 빼먹고 검증했다가 값이 갈렸다 (2026-09-09)
            if 등 is not None and abs(등) > 31.0:
                등 = None
            p종 = 앞종.get(c)
            p수 = 앞수정.get(c)
            if p수 is None:
                수정 = 종c
            elif 등 is not None:
                수정 = p수 * (1 + 등 / 100)
            elif p종 and p종 > 0:
                r = 종c / p종 - 1
                수정 = p수 * (1 + (r if abs(r) <= 0.32 else 0))
            else:
                수정 = p수
            # ⚠ 수정가가 0 이하면 앞 값으로 되돌린다 (원래 함수와 같게)
            if 수정 <= 0:
                수정 = p수 if (p수 and p수 > 0) else 종c
            앞수정[c] = 수정
            주가.setdefault(d8, {})[c] = (수정, 시총, 거)
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            거량.setdefault(d8, {})[c] = 량
            if p종 and p종 > 0:
                g = (시 / p종 - 1) * 100
                if abs(g) <= 32:
                    하루갭[c] = g
            앞종[c] = 종c
        갭표[d8] = 하루갭
    낸것 = (주가, 비, 갭표, 원시, 거량)
    if 캐시쓰기:
        try:
            os.makedirs(_캐시폴더, exist_ok=True)
            # 낡은 캐시는 지운다
            for 옛 in glob.glob(os.path.join(_캐시폴더, "krx_*.pkl")):
                if 옛 != 캐시:
                    os.remove(옛)
            with open(캐시, "wb") as f:
                pickle.dump(낸것, f, protocol=5)
        except Exception:  # noqa: BLE001
            pass
    return 낸것
