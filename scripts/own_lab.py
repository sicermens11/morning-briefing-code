#!/usr/bin/env python3
r"""
own_lab.py — **무리 전용 규칙** (2026-09-30 · 설계 docs/2026-09-30_무리전용_시험설계.md)

## 사용자
「기존 규칙 말고, 대형주, 중형주, 소형주, 섹터별 등등에 따라 매수 규칙, 매도 규칙 각자의 규칙을 갖는 거에 대해
 모든 재료를 활용해서 … 규칙에 and, or를 붙여봤는지부터 … 기존 규칙에 얹어서가 아니라 새로운 규칙을 찾는」
「매수 기회 먼저」 · 「(종목별도) 넣는다」 · 「낙폭 한계는 12% 그대로」

## combo4_lab 과 다른 점 (9/30 독립 검사가 찾은 12가지를 고쳤다)
· 지금 규칙(rule_def 의 문턱·재무 문·크기 문·매도 40:60·후보 120)을 **안 쓴다** — 돈 시뮬 범위도 그 무리
· 무리: OWN_KIND=규모(BIG_LO/BIG_HI) · 업종(OWN_VALUE=업종지수 이름) · 섹터(가치사슬 이름) · 종목(코드들)
· 2010년부터 · **앞 기간(~2018)에서 찾고 뒤 기간(2019~)에서 확인** · 오분위 문턱도 앞 기간 값으로만
· 자료가 없는 해(자료 시작 전)는 0 이 아니라 **없음** — 그 해엔 그 재료로 안 산다
· 재료 추가: 밸류에이션(이익·순자산·매출 수익률) · 수익률 120·250일 · 해외 동종(yahoo 분류별)
· 돈으로 넘기는 조건을 이김 z 와 20일 평균 **둘 다**로 추린다
· 사는 문턱 × 하루 자리 × 파는 규칙(11가지 · 손절·20일선 회복 포함) × 줄 세우는 순서를 **무리마다** 찾는다
· 순위 = 통과(돈↑·낙폭 한계 안) 중 **1년 기회** 많은 순
쓰는 법 (큐 스크립트가 환경변수로 준다):
    OWN_KIND=규모 BIG_LO=10000 python scripts\own_lab.py
    OWN_KIND=업종 OWN_VALUE=금속 python scripts\own_lab.py
    OWN_KIND=섹터 OWN_VALUE=방산 python scripts\own_lab.py
"""
from array import array as _array   # ⭐ 자리들을 4바이트로
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402
import newmat  # noqa: E402   ⭐ 2026-09-14 — 안 써본 재료 넷
import rule_def as R  # noqa: E402   ⭐ 2026-09-15 — 「지금 규칙」 값을 여기서만 읽는다

_비용 = 0.26
_시작 = os.environ.get("OWN_START") or "20100104"     # 2010 부터 (combo4 는 2016-04 부터였다)
_분할 = os.environ.get("OWN_SPLIT") or "20190101"     # 앞 = 찾기 · 뒤 = 확인
_낙한 = float(os.environ.get("MAXDD") or -12.0)       # 사용자 9/21 「12% 견딜 수 있어!」 · 9/30 「12% 그대로」
_무리종류 = os.environ.get("OWN_KIND") or "규모"
_무리값 = os.environ.get("OWN_VALUE") or ""
_시드 = 5_000_000.0
# ⭐⭐ **대형주 전용 판** (2026-09-17 · 사용자 「대형주는 그것만의 규칙을 찾아보면 되는 거 아닌가?」)
#    BIG_LO=2000 이면 사건을 **시총 2,000억 이상**으로 좁힌다 — 승률·바탕·돈이 전부 대형주 기준이 된다.
#    안 주면 전과 똑같다(100억~50조). ⚠️ 돈 시뮬 범위도 같이 따라간다 (아래 _밑E · _지금E)
_BIG_LO = float(os.environ.get("BIG_LO") or 0)
_BIG_HI = float(os.environ.get("BIG_HI") or 0)
_사건시총하한 = (_BIG_LO * 1e8) if _BIG_LO else 1e10
# ⚠️⚠️ 2026-09-18: 상한이 5e13(**50조**)이라 **삼성전자(1,482조)가 그물 밖**이었다 —
#    BAND 판의 「100조 이상」 띠가 0건으로 나온 원인이다. 9e15(90경)로 열어 상한을 없앤다
_사건시총상한 = (_BIG_HI * 1e8) if _BIG_HI else 9e15
# ⚠️ 9/30 13:05 대기열이 무리 값을 빠뜨려 **전 종목**으로 돌았다 — 메모리 15GB·여유 5.6GB 까지 갔다.
#    무리를 안 주면 돌지 않는다 (전 종목을 정말 돌리려면 OWN_ALL=1)
if not os.environ.get("OWN_ALL") and (
        (_무리종류 == "규모" and not (_BIG_LO or _BIG_HI)) or (_무리종류 != "규모" and not _무리값)):
    print(f"🛑 무리가 비었다 — OWN_KIND={_무리종류!r} OWN_VALUE={_무리값!r} BIG_LO={_BIG_LO} BIG_HI={_BIG_HI} · 돌지 않는다")
    sys.exit(3)
_후보수 = R.후보수        # ⭐ 40 이 얼어 있었다 (2026-09-15 · 사용자 「나중에 결정된 게 반영 안 된 거 없어?」)
확정 = {"잉여금": 30, "부채": 80, "흑자필수": True, "상대갭": R.상대갭문턱,
        "볼린저": -1.0, "낙폭20": -10, "목표": 20, "최대보유": 40,
        "비중": 0.20, "하루상한": (lambda 골: R.오늘최대종목(
                  next((z.get("시장낙폭") for z in 골
                        if z.get("시장낙폭") is not None), None))),
              # ⭐ ㉥ (2026-09-21 반영) — 그날 상한을 rule_def 가 정한다.
              #    맨 위 후보의 시장 지수를 본다 (실전 quant_cards 와 같은 자리)
        "시총하한": 500, "시총상한": 2000, "대금하한": 1.0, "거래량하한": 0,
        "회전율하한": 0.0}


def main():
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)   # ⚠️ 상장폐지를 손실로 센다
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — 상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
    # ⚠️ 짧은 한글 이름 덮어쓰기로 하루에 다섯 번 당했다 — 훑기 전에 못 박는다
    assert isinstance(날, list) and len(날) > 1000, ('거래일 목록이 깨졌다', len(날))
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    대금계 = {}      # ⭐ 거래대금 계열 (2026-09-18)
    # ⭐ 공시 직후용 표 (2026-09-18 밤) — 자사주60 은 60일 누적이라 「어제 났다」가 묻힌다
    _증자표2 = newmat._증자표()
    _임원표 = {}
    for _f9 in glob.glob(os.path.join(O._DATA, "dart-exec", "*.json")):
        try:
            _j9 = json.load(io.open(_f9, encoding="utf-8-sig"))
        except ValueError:
            continue
        _ds9 = sorted(str(z.get("접수일") or "").replace("-", "") for z in (_j9.get("이력") or [])
                      if z.get("접수일") and str(z.get("증감") or "").lstrip("-").replace(",", "").isdigit()
                      and not str(z.get("증감") or "").startswith("-"))
        if _ds9:
            _임원표[os.path.basename(_f9)[:-5]] = _ds9
    print(f"    공시 직후용 — 증자·자사주 {len(_증자표2):,}종목 · 임원 매수 {len(_임원표):,}종목", flush=True)

    def _증자재기(code, i, 갈래, 일수):
        return newmat._증자재기(_증자표2, code, 갈래, 날[i], 일수, 날, i)
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            대금계.setdefault(c, []).append(v[2])      # ⭐ 거래대금 계열 (2026-09-18 · 거래량바닥용)
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 앞종, 원시, 거량 = {}, {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                고 = float(v.get("고가") or 0) or 종c
                거 = float(v.get("거래대금") or 0)
                량 = float(v.get("거래량") or 0)
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            거량.setdefault(d8, {})[c] = 량
            p = 앞종.get(c)
            앞종[c] = 종c
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
    # ⭐ own_lab — 그날 **시장 전체** 시가 갭의 중앙값 (08:55 표본 30 이 재려는 값)
    _시장중앙 = {d: st.median(list(v.values())) for d, v in 갭표.items() if len(v) >= 30}

    def 재무값(code, d8):
        줄 = 재무.get(code)
        if not 줄:
            return None
        m = None
        for 적용, v in 줄:
            if 적용 <= d8:
                m = v
            else:
                break
        return m

    print("  후보 모으는 중 (크기 조건도 느슨하게)...", flush=True)
    # ⭐ **기술지표 다섯** — 종가만으로 계산 (2026-09-15 · 사용자 「RSI MACD 는 반영됐어?」)
    #    9/2 combo3 에서 RSI≤30 을 옛 기준선에 AND 로만 봤고(68.0% · 16/16) 지금 판엔 없었다.
    #    MACD 는 한 번도 없었다. 종목마다 한 번 계산해 array('f') 에 둔다 — 신호일 kk 까지만 본다
    자리_날 = {d: i for i, d in enumerate(날)}
    print("  기술지표(RSI·MACD·스토캐스틱) 계산 중...", flush=True)
    _TA = {"RSI14": {}, "RSI변화5": {}, "MACD히스토": {}, "MACD골든5": {}, "스토K14": {}}
    _nan = float("nan")
    for _c, _sq in 종계.items():
        _n = len(_sq)
        _rsi = _array("f", [_nan] * _n)
        _hist = _array("f", [_nan] * _n)
        _gold = _array("f", [0.0] * _n)
        _sto = _array("f", [_nan] * _n)
        _dr = _array("f", [_nan] * _n)
        _au = _ad = None
        _e12 = _e26 = _sig = None
        _prev_diff = None
        _cross = []                    # 골든크로스 난 자리들
        for k in range(_n):
            c = _sq[k]
            if k >= 1 and _sq[k - 1] > 0:
                ch = c - _sq[k - 1]
                g, l = (ch if ch > 0 else 0.0), (-ch if ch < 0 else 0.0)
                if _au is None:
                    _au, _ad = g, l
                else:
                    _au += (g - _au) / 14.0
                    _ad += (l - _ad) / 14.0
                if k >= 14:
                    _rsi[k] = 100.0 if _ad == 0 else 100.0 - 100.0 / (1.0 + _au / _ad)
            # MACD
            if _e12 is None:
                _e12 = _e26 = c
            else:
                _e12 += (c - _e12) * (2.0 / 13.0)
                _e26 += (c - _e26) * (2.0 / 27.0)
            _m = _e12 - _e26
            if _sig is None:
                _sig = _m
            else:
                _sig += (_m - _sig) * (2.0 / 10.0)
            _diff = _m - _sig
            if k >= 33 and c > 0:
                _hist[k] = _diff / c * 100.0
                if _prev_diff is not None and _prev_diff <= 0 < _diff:
                    _cross.append(k)
                while _cross and _cross[0] < k - 4:
                    _cross.pop(0)
                _gold[k] = 1.0 if _cross else 0.0
            _prev_diff = _diff
            # 스토캐스틱 (종가로)
            if k >= 13:
                _w = _sq[k - 13:k + 1]
                _hi, _lo = max(_w), min(_w)
                _sto[k] = ((c - _lo) / (_hi - _lo) * 100.0) if _hi > _lo else 50.0
            if k >= 19 and _rsi[k] == _rsi[k] and _rsi[k - 5] == _rsi[k - 5]:
                _dr[k] = _rsi[k] - _rsi[k - 5]
        _TA["RSI14"][_c] = _rsi
        _TA["RSI변화5"][_c] = _dr
        _TA["MACD히스토"][_c] = _hist
        _TA["MACD골든5"][_c] = _gold
        _TA["스토K14"][_c] = _sto
    print(f"    {len(종계):,}종목 · 다섯 지표", flush=True)

    def _ta(이름, code, kk):
        a = _TA[이름].get(code)
        if a is None or kk >= len(a):
            return None
        v = a[kk]
        return None if v != v else float(v)

    # ⭐ **수집됐는데 안 쓴 재료** (2026-09-15 22:00 · 사용자 물음)
    #    krx-daily 「저가」 는 16년치가 있는데 시험 어디에도 안 썼다(비 = 시가/종가·고가/종가만).
    #    fred 미국 금리 셋은 실전 국면에만 쓰고 시험엔 없었다. 여기서 여섯을 만든다
    import bisect as _bs
    _꼬리, _양봉 = {}, {}      # ⭐ 반등 신호 (2026-09-18 · 사용자 「반등 신호를 포착해서 사기」)
    print("  저가·고가·시가(krx-daily 원본) 다시 읽는 중 — 진폭·시가 위치·아래꼬리·양봉...", flush=True)
    _진폭 = {c: _array("f", [float("nan")] * len(q)) for c, q in 종계.items()}
    _시위 = {c: _array("f", [float("nan")] * len(q)) for c, q in 종계.items()}
    for _f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        _d8 = os.path.basename(_f)[:8]
        if _d8 not in 자리_날:
            continue
        try:
            _j = json.load(io.open(_f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        for _c, _v in (_j.get("종목") or {}).items():
            _k = (자리.get(_c) or {}).get(_d8)
            if _k is None:
                continue
            try:
                _hi, _lo, _op, _cl = (float(_v.get("고가") or 0), float(_v.get("저가") or 0),
                                      float(_v.get("시가") or 0), float(_v.get("종가") or 0))
            except (TypeError, ValueError):
                continue
            if _cl > 0 and _hi >= _lo > 0:
                _진폭[_c][_k] = (_hi - _lo) / _cl * 100.0
                if _hi > _lo and _op > 0:
                    _시위[_c][_k] = (_op - _lo) / (_hi - _lo)
                    # ⭐ 반등 신호 (2026-09-18) — 아래꼬리는 **종가** 기준 (시가위치와 다르다)
                    _꼬리.setdefault(_c, {})[_k] = (_cl - _lo) / (_hi - _lo)
                if _op > 0:
                    _양봉.setdefault(_c, {})[_k] = 1.0 if _cl > _op else 0.0

    def _진폭14(code, kk):
        a = _진폭.get(code)
        if a is None or kk < 13:
            return None
        w = [z for z in a[kk - 13:kk + 1] if z == z]
        return (sum(w) / len(w)) if len(w) >= 10 else None

    def _당일(표, code, kk):
        a = 표.get(code)
        if a is None or kk >= len(a):
            return None
        v = a[kk]
        return None if v != v else float(v)

    # 미국 금리 (fred · 일별 · 1954~) — 날짜 자리마다 「그날 또는 그 전 마지막 값」
    def _fred(이름):
        try:
            j = json.load(io.open(os.path.join(O._DATA, "fred", f"AV_{이름}.json"), encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            return [None] * len(날)
        v = j.get("값") or {}
        ks = sorted(k for k in v if isinstance(v.get(k), (int, float)))
        out = []
        for d in 날:
            p = _bs.bisect_right(ks, d) - 1
            out.append(float(v[ks[p]]) if p >= 0 else None)
        return out
    _us10, _us2 = _fred("DGS10"), _fred("DGS2")
    _금리차 = [(a - b) if (a is not None and b is not None) else None for a, b in zip(_us10, _us2)]

    def _변화20(열, i):
        if i < 20 or 열[i] is None or 열[i - 20] is None:
            return None
        return 열[i] - 열[i - 20]
    print(f"    진폭·시가위치 {len(_진폭):,}종목 · 미국 금리 {sum(1 for z in _us10 if z is not None):,}일", flush=True)

    # ⭐ **사건 전후 재료** (2026-09-15 22:45 · 사용자 「실적발표 정책발표 경제지표 전후 테스트한 적 있나?」)
    #    한 번도 안 쟀다. 자료 한계: 실적 공시는 dart-daily 에 걸러져 있고(있는 것만),
    #    금통위·FOMC·CPI 일정은 없다 → FOMC 는 FEDFUNDS 0.10%p 변경일을 대용으로. 「발표 전」은 고정 달력만
    print("  사건 전후(실적 공시 · 실적 시즌 · FOMC 변경) 표 만드는 중...", flush=True)
    _실적일 = {}                                   # code -> 정렬된 날짜8 목록
    for _f in sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
        _d8 = os.path.basename(_f)[:8]
        if _d8 not in 자리_날:
            continue
        try:
            _j = json.load(io.open(_f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        for _k in ("챙길공시", "그밖의공시"):
            for _x in (_j.get(_k) or []):
                _c = str(_x.get("종목코드") or "")
                # ⚠️ "실적" 만 보면 「증권발행실적보고서」(21,404건) 가 다 잡힌다 — **「(잠정)실적」** 만
                if _c and "(잠정)실적" in str(_x.get("공시명") or ""):
                    _실적일.setdefault(_c, []).append(_d8)
    for _c in _실적일:
        _실적일[_c] = sorted(set(_실적일[_c]))
    # ⭐ collect_earnings_dates.py 가 만든 표(2010~ 촘촘)가 있으면 **그것을 우선** 쓴다 (2026-09-15 23:10)
    _손익일 = {}
    try:
        _ej = json.load(io.open(os.path.join(O._DATA, "earnings-dates.json"), encoding="utf-8-sig"))
        _n0 = sum(len(v) for v in _실적일.values())
        for _c, _벌 in (_ej.get("종목") or {}).items():
            for _d8, _종 in _벌:
                if _d8 not in 자리_날:
                    continue
                (_실적일 if _종 == "잠정실적" else _손익일).setdefault(_c, []).append(_d8)
        for _표 in (_실적일, _손익일):
            for _c in _표:
                _표[_c] = sorted(set(_표[_c]))
        print(f"    earnings-dates.json: 잠정실적 {sum(len(v) for v in _실적일.values()):,}건 "
              f"(파일 훑기 {_n0:,}) · 손익구조 {sum(len(v) for v in _손익일.values()):,}건", flush=True)
    except Exception as _e:  # noqa: BLE001
        print(f"    earnings-dates.json 없음/못 읽음 ({type(_e).__name__}) — dart-daily 훑기만 쓴다", flush=True)

    def _실적후(code, i, n=5, 표=None):
        ds = (표 if 표 is not None else _실적일).get(code)
        if not ds:
            return 0.0
        시작 = 날[max(0, i - n)]
        import bisect as _b2
        return 1.0 if _b2.bisect_right(ds, 날[i]) - _b2.bisect_left(ds, 시작) >= 1 else 0.0

    def _실적시즌(d8):
        """정기공시 마감(3/31 · 5/15 · 8/14 · 11/14) 앞 10 달력일 — 고정 달력이라 앞을 안 본다"""
        md = d8[4:]
        return 1.0 if (("0321" <= md <= "0331") or ("0505" <= md <= "0515")
                       or ("0804" <= md <= "0814") or ("1104" <= md <= "1114")) else 0.0

    _fomc = set()
    try:
        _jf = json.load(io.open(os.path.join(O._DATA, "fred", "AV_FEDFUNDS.json"), encoding="utf-8-sig"))
        _vf = _jf.get("값") or {}
        _kf = sorted(k for k in _vf if isinstance(_vf.get(k), (int, float)))
        _pv = None
        for _k in _kf:
            if _pv is not None and abs(_vf[_k] - _pv) >= 0.10:
                _fomc.add(_k)
            _pv = _vf[_k]
    except Exception:  # noqa: BLE001
        pass
    _fomc자리 = sorted(자리_날[d] for d in _fomc if d in 자리_날)

    def _fomc후(i, n):
        import bisect as _b2
        p = _b2.bisect_right(_fomc자리, i) - 1
        return 1.0 if (p >= 0 and i - _fomc자리[p] <= n) else 0.0
    # ⭐ 실제 일정 (data/event-calendar.json · 2026-09-15 수집) — FOMC 회의 · 미국 CPI · 금통위 변경일
    #    미국 날짜는 현지 발표일 → 한국 시장엔 **다음 거래일** 반영 (+1)
    def _달력자리(날짜들, 미국=True):
        import bisect as _b2
        out = []
        for d in 날짜들:
            p = _b2.bisect_right(날, d) if 미국 else _b2.bisect_left(날, d)   # 미국: d 다음 거래일
            if p < len(날):
                out.append(p)
        return sorted(set(out))
    _달력 = {}
    try:
        _달력 = json.load(io.open(os.path.join(O._DATA, "event-calendar.json"), encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        _달력 = {}
    _fomc회의자리 = _달력자리(_달력.get("FOMC") or [], 미국=True)
    _cpi자리 = _달력자리(_달력.get("미국CPI") or [], 미국=True)
    # ⚠️ 금통위는 그날 10시에 정한다 — 08:55 판정은 모른다 → **다음 거래일**부터 (미국=True 와 같은 처리 · 2026-09-16 고침)
    _금통자리 = _달력자리(sorted((_달력.get("금통위변경") or {}).keys()), 미국=True)
    _고용자리 = _달력자리(_달력.get("미국고용") or [], 미국=True)
    # 국내 지표는 정확한 날짜를 아직 못 모았다 → **고정 달력 근사** (앞을 안 본다). 내일 보도자료 목록으로 바꾼다
    _월첫자리 = sorted({i for i, d in enumerate(날) if i == 0 or 날[i - 1][:6] != d[:6]})   # 그 달 첫 거래일

    def _국내CPI주간(d8):
        return 1.0 if "01" <= d8[6:8] <= "06" else 0.0

    def _뒤N(자리들, i, n):
        import bisect as _b2
        p = _b2.bisect_right(자리들, i) - 1
        return 1.0 if (p >= 0 and i - 자리들[p] <= n) else 0.0

    # ⭐ 사건 **앞** 창 (2026-09-16 · 사용자 「전후로 다 테스트 했어?」 — 「후」만 있었다)
    def _앞N(자리들, i, n):
        import bisect as _b2
        q = _b2.bisect_right(자리들, i)          # 다음 사건 자리 (i 당일은 뒤 쪽으로)
        return 1.0 if (q < len(자리들) and 0 < 자리들[q] - i <= n) else 0.0

    def _실적전(code, i, n=5):
        """⚠️ 실전 불가 — 소형주는 공시 날짜를 미리 모른다. 「발표 앞에서 움직이나」를 보는 용도"""
        ds = _실적일.get(code)
        if not ds:
            return 0.0
        import bisect as _b2
        q = _b2.bisect_right(ds, 날[i])
        return 1.0 if (q < len(ds) and ds[q] <= 날[min(len(날) - 1, i + n)]) else 0.0
    _월끝자리 = sorted({i for i, d in enumerate(날) if i + 1 < len(날) and 날[i + 1][:6] != d[:6]})   # 그 달 마지막 거래일
    # ⭐ 선거·월드컵·올림픽 (2026-09-16 · 사용자 「선거나 월드컵 특수같은 건 계산하기 어렵겠지?」 — 계산은 쉽고 표본이 적다)
    _선거자리 = _달력자리(_달력.get("선거") or [], 미국=False)          # 투표일(휴장) 다음 거래일부터 「후」
    _미선거자리 = _달력자리(_달력.get("미국선거") or [], 미국=True)       # 현지 투표일 → 한국 다음 거래일 (사용자 「미국 선거 영향도」)
    # ⭐ 계절 (2026-09-16 밤 · combo5 H절: 봄(3~5월) 강세 · 여름(6~8월) 약세가 업종을 안 가리고 나왔다 → 시장 재료로 잰다)
    _계절표 = {"12": "겨울", "01": "겨울", "02": "겨울", "03": "봄", "04": "봄", "05": "봄",
              "06": "여름", "07": "여름", "08": "여름", "09": "가을", "10": "가을", "11": "가을"}
    # ⭐ 오름 전환 도우미 (2026-09-18) — 종계[code] 는 그 종목의 종가 계열, 자리[code][날짜] 가 자리
    def _시세(x):
        _k = (자리.get(x["code"]) or {}).get(날[x["인"] - 1])
        return (종계.get(x["code"]), _k)

    def _신고가(x, n):
        sq, k = _시세(x)
        if not sq or k is None or k < n:
            return None
        return 1.0 if sq[k] >= max(sq[k - n + 1:k + 1]) else 0.0

    def _평(sq, k, n):
        return sum(sq[k - n + 1:k + 1]) / n

    def _선돌파(x, n):
        sq, k = _시세(x)
        if not sq or k is None or k < n + 1:
            return None
        오늘 = sq[k] > _평(sq, k, n)
        어제 = sq[k - 1] > _평(sq, k - 1, n)
        return 1.0 if (오늘 and not 어제) else 0.0

    def _정배열(x, 전환):
        sq, k = _시세(x)
        if not sq or k is None or k < 61:
            return None
        def _맞나(kk):
            return _평(sq, kk, 5) > _평(sq, kk, 20) > _평(sq, kk, 60)
        오늘 = _맞나(k)
        if not 전환:
            return 1.0 if 오늘 else 0.0
        return 1.0 if (오늘 and not _맞나(k - 1)) else 0.0

    def _낙폭둔화(x):
        """5일 낙폭 − 20일 낙폭. 양수면 **덜 빠지는 중**"""
        sq, k = _시세(x)
        if not sq or k is None or k < 21 or sq[k - 5] <= 0 or sq[k - 20] <= 0:
            return None
        return (sq[k] / sq[k - 5] - 1) * 100 - (sq[k] / sq[k - 20] - 1) * 100

    def _볼(sq, k):
        m = sum(sq[k - 19:k + 1]) / 20
        import statistics as _st2
        sd = _st2.pstdev(sq[k - 19:k + 1]) or 1e-9
        return (sq[k] - m) / (2 * sd)

    def _볼린저회복(x):
        """오늘 볼린저 − 어제 볼린저. 양수면 **하단에서 올라오는 중**"""
        sq, k = _시세(x)
        if not sq or k is None or k < 21:
            return None
        return _볼(sq, k) - _볼(sq, k - 1)

    def _하락끊김(x):
        """어제 종가 > 그저께 종가 (연속 하락이 끊겼다)"""
        sq, k = _시세(x)
        if not sq or k is None or k < 2 or sq[k - 1] <= 0:
            return None
        return 1.0 if sq[k] > sq[k - 1] else 0.0

    def _외인전환10(x):
        """어제 외국인이 샀는데 **그 앞 10일**은 팔았다 (5일짜리와 견주려고)"""
        return x.get("외인전환10값")

    def _밴드수축(x):
        """20일 밴드 폭 / 60일 평균 폭. **낮을수록 조용했다** — 벌어지기 직전"""
        sq, k = _시세(x)
        if not sq or k is None or k < 61:
            return None
        import statistics as _st3
        def _폭(kk, n):
            _창 = sq[kk - n + 1:kk + 1]
            _m = sum(_창) / n
            return (_st3.pstdev(_창) * 4 / _m * 100) if _m > 0 else None
        _지 = _폭(k, 20)
        _앞들 = [z for z in (_폭(k - j, 20) for j in range(0, 60, 5)) if z]
        if _지 is None or len(_앞들) < 6:
            return None
        _평 = sum(_앞들) / len(_앞들)
        return (_지 / _평) if _평 > 0 else None

    def _신저가반등(x):
        """250일 최저를 찍고 어제 올라왔나"""
        sq, k = _시세(x)
        if not sq or k is None or k < 251:
            return None
        _저 = min(sq[k - 250:k])
        return 1.0 if (sq[k - 1] <= _저 * 1.005 and sq[k] > sq[k - 1]) else 0.0

    def _연속하락(x):
        """며칠 내리 빠졌나 (어제까지)"""
        sq, k = _시세(x)
        if not sq or k is None or k < 12:
            return None
        n = 0
        for j in range(k, k - 10, -1):
            if sq[j] < sq[j - 1]:
                n += 1
            else:
                break
        return float(n)

    def _되돌림(x):
        """(오늘 − 20일 최저) / (20일 최고 − 20일 최저). 0 이면 바닥, 1 이면 꼭대기"""
        sq, k = _시세(x)
        if not sq or k is None or k < 21:
            return None
        _창 = sq[k - 19:k + 1]
        _lo, _hi = min(_창), max(_창)
        return ((sq[k] - _lo) / (_hi - _lo)) if _hi > _lo else None

    def _공시직후(x, 갈래, 일수=5):
        """그 공시가 최근 `일수` 거래일 안에 났나 (60일 누적과 다르다)"""
        return _증자재기(x["code"], x["인"] - 1, 갈래, 일수)

    def _임원직후(x, 일수=5):
        _ds = (_임원표 or {}).get(x["code"])
        if not _ds:
            return 0.0
        i = x["인"] - 1
        _시작 = 날[max(0, i - 일수)]
        import bisect as _b9
        return float(_b9.bisect_right(_ds, 날[i]) - _b9.bisect_left(_ds, _시작))

    def _거래량깨움(x):
        """어제 거래대금 / 20일 평균. **2배 넘으면 잠에서 깬 것** (거래량바닥의 반대쪽)"""
        _d = 대금계.get(x["code"])
        if not _d:
            return None
        _k = _시세(x)[1]
        if _k is None or _k < 20:
            return None
        _앞 = _d[_k - 19:_k]
        _평 = sum(_앞) / len(_앞) if _앞 else 0
        return (_d[_k] / _평) if _평 > 0 else None

    def _거래량바닥(x):
        """어제 거래대금 / 20일 평균. **낮을수록 투매가 끝난 것**"""
        _d = 대금계.get(x["code"])
        if not _d:
            return None
        _k = _시세(x)[1]
        if _k is None or _k < 20:
            return None
        _앞 = _d[_k - 19:_k + 1]
        _평 = sum(_앞) / len(_앞) if _앞 else 0
        return (_d[_k] / _평) if _평 > 0 else None

    def _계절인가(x, 이름):
        return 1.0 if _계절표[날[x["인"] - 1][4:6]] == 이름 else 0.0
    def _기간안(구간들, d8):
        return 1.0 if any(a <= d8 <= b for a, b in 구간들) else 0.0
    _월드컵 = [tuple(z) for z in (_달력.get("월드컵") or [])]
    _올림픽 = [tuple(z) for z in (_달력.get("올림픽") or [])]
    print(f"    실적 공시 있는 종목 {len(_실적일):,} · FOMC 변경일(대용) {len(_fomc자리)}일 · "
          f"달력: FOMC 회의 {len(_fomc회의자리)} · CPI {len(_cpi자리)} · 금통위 변경 {len(_금통자리)}", flush=True)

    # ⭐ 무리 — 사건을 만들 때부터 그 무리만 (메모리도 지킨다)
    _허용 = None
    _크기하한 = _사건시총하한
    if _무리종류 == "업종":
        _ind = json.load(io.open(os.path.join(O._DATA, "industry.json"), encoding="utf-8-sig"))
        _허용 = {c for c, v in _ind.items() if isinstance(v, dict) and R.업종이름(v.get("업종명")) == _무리값}
    elif _무리종류 == "섹터":
        from chain_map import 읽기 as _맵읽기
        _허용 = {c for s, 들 in _맵읽기().items() if s == _무리값 for _, c in 들 if c}
    elif _무리종류 == "종목":
        _허용 = {z.strip() for z in _무리값.split(",") if z.strip()}
    if _허용 is not None:
        _크기하한 = 0.0
        _있는 = {c for d in 날[-5:] for c in 주가[d]}
        _없는 = sorted(c for c in _허용 if all(c not in 주가[d] for d in 날[-260:]))
        print(f"  ⭐ 무리 {_무리종류} = {_무리값} · 종목 {len(_허용):,}개 (크기 하한 없음)"
              + (f" · ⚠️ 주가 자료에 없는 종목 {len(_없는)}개: {', '.join(_없는)}" if _없는 else ""), flush=True)
        if not _허용:
            raise SystemExit(f"무리 {_무리종류}={_무리값} 에 종목이 없다 — 이름을 확인하라")
    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            # ⚠️ **크기 조건을 여기서 걸지 않는다** — 훑을 대상이기 때문이다.
            #    아주 작은 것(100억)과 아주 큰 것(50조)만 잘라 낸다
            if 시총 < _크기하한 or 시총 >= _사건시총상한:
                continue
            if _허용 is not None and code not in _허용:
                continue
            fm = 재무값(code, d1) or {}
            재통과 = 1.0 if (
                fm.get("잉여금비율", -9e9) >= 확정["잉여금"]
                and fm.get("부채비율", 9e9) <= 확정["부채"]
                and fm.get("흑자") == 1.0) else 0.0
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            kk = (자리.get(code) or {}).get(d1)
            if kk is None or kk < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[kk - 19:kk + 1])
            sd = st.pstdev(sq[kk - 19:kk + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            낙60 = ((c1 / sq[kk - 60] - 1) * 100
                    if kk >= 60 and sq[kk - 60] > 0 else None)
            s60 = st.mean(sq[kk - 59:kk + 1]) if kk >= 59 else None
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            g = 하루갭.get(code)
            if not b0 or not v0 or not o0 or g is None:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            g = (매수 / c1 - 1) * 100 if c1 > 0 else g     # ⭐ own_lab — 수정 가격 기준 갭 (권리락 가짜 갭 없앰)
            량 = (거량.get(d1) or {}).get(code) or 0
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "볼린저": 볼, "낙폭20": 낙,
                # ⚠️ 새 재료 30개는 여기 **안 넣는다** — 5.4M dict × 30 = MemoryError (2026-09-15 23:44).
                #    오분위 때 `_계산재료` 로 그때그때 만든다. 값은 같다
                "시총억": 시총 / 1e8, "대금억": 대금 / 1e8, "거래량": 량,
                "회전율": (대금 / 시총 * 100) if 시총 > 0 else 0,
                "갭": g, "매수": 매수, "재통과": 재통과, "낙폭60": 낙60,
                "60일선대비": ((c1 / s60 - 1) * 100) if s60 else None,
                "주가": o0,
                "잉여금": (재무값(code, d1) or {}).get("잉여금비율"),
                "부채": (재무값(code, d1) or {}).get("부채비율"),
                "ROE": (재무값(code, d1) or {}).get("ROE"),
                "영업이익률": (재무값(code, d1) or {}).get("영업이익률"),
                "순이익률": (재무값(code, d1) or {}).get("순이익률"),
                "유동비율": (재무값(code, d1) or {}).get("유동비율")})
    # ══ 지수 붙이기 ══ (2026-09-07 신설)
    print("  지수 읽는 중...", flush=True)
    지수 = {}          # 날짜 -> {지수이름: 종가}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d2 = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하루 = {}
        for 이름2, v2 in (d2.get("지수") or {}).items():
            try:
                하루[이름2] = float(str(v2.get("종가")).replace(",", ""))
            except (TypeError, ValueError, AttributeError):
                pass
        if 하루:
            지수[d2.get("기준일") or os.path.basename(f)[:8]] = 하루
    print(f"    지수 {len(지수):,}일", flush=True)

    def 지수계열(이름2):
        """날 순서대로 늘어놓은 종가 (없는 날은 None)"""
        return [(지수.get(d) or {}).get(이름2) for d in 날]

    _계열캐시 = {}

    def 낙폭(이름2, i2, n=20):
        """i2 자리에서 n일 전 대비 몇 % 인가"""
        sq = _계열캐시.get(이름2)
        if sq is None:
            sq = 지수계열(이름2)
            _계열캐시[이름2] = sq
        if i2 < n or i2 >= len(sq):
            return None
        a, b = sq[i2 - n], sq[i2]
        if not a or not b:
            return None
        return (b / a - 1) * 100

    def 변동성(이름2, i2, n=20):
        sq = _계열캐시.get(이름2)
        if sq is None:
            sq = 지수계열(이름2)
            _계열캐시[이름2] = sq
        if i2 < n or i2 >= len(sq):
            return None
        칸 = [x for x in sq[i2 - n:i2 + 1] if x]
        if len(칸) < n * 0.8:
            return None
        일간 = [(칸[j] / 칸[j - 1] - 1) * 100 for j in range(1, len(칸))
                if 칸[j - 1]]
        return st.pstdev(일간) if len(일간) > 3 else None

    # ── 업종 매핑 (표준산업분류 63종 -> 코스닥 업종지수 20종) ──
    # ⚠️ 손으로 이은 표다. 매핑률을 아래에서 찍는다
    _업종map = {
        "식료품": "음식료·담배", "음료": "음식료·담배", "담배": "음식료·담배",
        "섬유제품": "섬유·의류", "의복": "섬유·의류", "가죽·가방·신발": "섬유·의류",
        "펄프·종이": "종이·목재", "목재": "종이·목재", "가구": "종이·목재",
        "화학": "화학", "고무·플라스틱": "화학", "코크스·석유정제": "화학",
        "의약품": "제약",
        "비금속광물": "비금속",
        "1차금속": "금속", "금속가공": "금속",
        "기계·장비": "기계·장비",
        "전자부품·통신장비": "전기전자", "전기장비": "전기전자",
        "반도체": "전기전자",
        "의료·정밀·광학": "의료·정밀기기",
        "자동차": "운송장비·부품", "자동차부품": "운송장비·부품",
        "기타운송장비": "운송장비·부품", "선박": "운송장비·부품",
        "도매": "유통", "소매": "유통", "상품중개": "유통",
        "종합건설": "건설", "전문건설": "건설", "건설": "건설",
        "육상운송": "운송·창고", "수상운송": "운송·창고",
        "항공운송": "운송·창고", "창고·운송서비스": "운송·창고",
        "통신": "통신", "우편·통신": "통신",
        "금융": "금융", "금융지원": "금융", "보험": "금융",
        "연구개발": "일반서비스", "전문서비스": "일반서비스",
        "사업지원": "일반서비스", "교육": "일반서비스",
        "출판": "출판·매체복제", "영상·오디오": "오락·문화",
        "컴퓨터프로그래밍": "IT 서비스", "정보서비스": "IT 서비스",
        "기타제조": "기타제조",
    }
    _산업 = {}
    _ip = os.path.join(O._DATA, "industry.json")
    if os.path.exists(_ip):
        for c2, v2 in json.load(io.open(_ip, encoding="utf-8-sig")).items():
            if isinstance(v2, dict):
                _산업[c2] = str(v2.get("업종명") or "")

    def 업종지수(code):
        나 = _산업.get(code) or ""
        if 나 in _업종map:
            return _업종map[나]
        for k, v in _업종map.items():
            if k and (k in 나 or 나 in k):
                return v
        return None

    시장표 = {}
    _sp = os.path.join(O._DATA, "stock-base.json")
    if os.path.exists(_sp):
        _sb = json.load(io.open(_sp, encoding="utf-8-sig"))
        # ⚠️⚠️ **2026-09-19 버그** — 종목은 한 겹 안에 있다 (gate7_lab 같은 자리 참고)
        #    겉을 돌면 시장표가 텅 비어 **코스닥 1,823종목이 코스피 지수로** 계산됐다.
        #    9/19 「시장으로 쪼개면」에서 코스피 칸 하나만 나온 것도 이 탓이다
        _sb = _sb.get("종목") or _sb
        for c2, v2 in _sb.items():
            if isinstance(v2, dict) and v2.get("시장"):
                시장표[c2] = str(v2["시장"])
    print(f"    시장표 — {len(시장표):,}종목 "
          f"(코스닥 {sum(1 for z in 시장표.values() if 'KOSDAQ' in z or '닥' in z):,})", flush=True)

    붙음, 섹붙음 = 0, 0
    for x in 사건:
        i2 = x["인"] - 1
        시장 = 시장표.get(x["code"]) or ""
        지수이름 = ("코스닥" if ("닥" in str(시장) or "KOSDAQ" in str(시장).upper())
                   else "코스피")   # ⚠️2026-09-19: 값은 "KOSDAQ" — 한글 「닥」만 찾으면 늘 거짓이었다
        시낙 = 낙폭(지수이름, i2)
        x["시장낙폭"] = 시낙
        x["시장낙60"] = 낙폭(지수이름, i2, 60)     # ⭐ 지금 규칙의 시장 갈래(지수 60일)용
        x["상대강도"] = (x["낙폭20"] - 시낙) if 시낙 is not None else None
        x["시장변동성"] = 변동성(지수이름, i2)
        큰 = 낙폭("코스닥 대형주", i2)
        작 = 낙폭("코스닥 소형주", i2)
        x["소형우위"] = (작 - 큰) if (큰 is not None and 작 is not None) else None
        if 시낙 is not None:
            붙음 += 1
        섹 = 업종지수(x["code"])
        x["섹터이름"] = 섹 or "없음"          # ⭐ 쪼개서 재기용 (2026-09-18)
        x["시장이름"] = ("코스닥"
                       if "KOSDAQ" in str(시장표.get(x["code"]) or "").upper()
                       or "닥" in str(시장표.get(x["code"]) or "")
                       else "코스피")   # ⚠️2026-09-19: 값은 "KOSDAQ" — 한글 「닥」만 찾으면 늘 거짓이었다
        섹낙 = 낙폭(섹, i2) if 섹 else None
        x["섹터"] = 섹
        x["섹터낙폭"] = 섹낙
        x["섹터대비"] = (x["낙폭20"] - 섹낙) if 섹낙 is not None else None
        if 섹낙 is not None:
            섹붙음 += 1
    print(f"  시장 지수 붙은 것 {붙음:,}/{len(사건):,} "
          f"· 섹터 지수 붙은 것 {섹붙음:,}/{len(사건):,} "
          f"({섹붙음/max(len(사건),1)*100:.0f}%)", flush=True)

    # ── 수급 붙이기 (flow-daily) ──
    import collections as _co
    print("  수급 붙이는 중...", flush=True)

    def _수(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).replace(",", "").replace("%", "").strip()
        try:
            return float(s)
        except ValueError:
            return None

    쓸코드 = {x["code"] for x in 사건}
    사건별 = {}
    for x in 사건:
        사건별.setdefault(x["인"] - 1, []).append(x)
    창 = {}
    지분창 = {}
    for i2, d2 in enumerate(날):
        p2 = os.path.join(O._DATA, "flow-daily", d2 + ".json")
        하루수급 = {}
        if os.path.exists(p2):
            try:
                하루수급 = (json.load(io.open(p2, encoding="utf-8-sig"))
                             .get("종목") or {})
            except ValueError:
                하루수급 = {}
        for code in 쓸코드:
            r2 = 하루수급.get(code)
            if not r2:
                continue
            종2 = _수(r2.get("종가"))
            if not 종2:
                continue
            창.setdefault(code, _co.deque(maxlen=20)).append(
                ((_수(r2.get("외국인")) or 0) * 종2,
                 (_수(r2.get("기관")) or 0) * 종2,
                 (_수(r2.get("개인")) or 0) * 종2))
            지2 = _수(r2.get("외국인지분율"))
            if 지2 is not None:
                지분창.setdefault(code, _co.deque(maxlen=21)).append(지2)
        for x in 사건별.get(i2, []):
            q2 = 창.get(x["code"])
            시총원 = x["시총억"] * 1e8
            if not q2 or 시총원 <= 0:
                continue

            def _몫(n, 자리, q2=q2, 시총원=시총원):
                return sum(z[자리] for z in list(q2)[-n:]) / 시총원 * 100
            x["외인1"] = _몫(1, 0)
            x["외인5"] = _몫(5, 0)
            x["외인20"] = _몫(20, 0)
            x["기관5"] = _몫(5, 1)
            x["기관20"] = _몫(20, 1)
            x["개인5"] = _몫(5, 2)
            # ⭐ **막 켜진 신호** (2026-09-18 · 사용자 「앞으로 오르기 시작할 것 같은 신호」)
            #    지금 재료는 전부 「지난 N일 동안 얼마나」(상태)다 — 「어제 처음 사기 시작했다」(전환)가 없었다
            _lst = list(q2)
            if len(_lst) >= 6:
                _어제외 = _lst[-1][0]
                _앞5외 = sum(z[0] for z in _lst[-6:-1])
                _어제기 = _lst[-1][1]
                _앞5기 = sum(z[1] for z in _lst[-6:-1])
                x["외인전환"] = 1.0 if (_어제외 > 0 and _앞5외 < 0) else 0.0
                x["기관전환"] = 1.0 if (_어제기 > 0 and _앞5기 < 0) else 0.0
                x["수급동시전환"] = 1.0 if (x["외인전환"] and x["기관전환"]) else 0.0
            if len(_lst) >= 11:
                # ⭐ 창 10일짜리 (2026-09-18 밤) — 5일이 맞는지 견주려고
                x["외인전환10값"] = 1.0 if (_lst[-1][0] > 0 and sum(z[0] for z in _lst[-11:-1]) < 0) else 0.0
            z2 = 지분창.get(x["code"])
            if z2:
                x["지분율"] = z2[-1]
                # ⭐ 외국인 지분율이 20일 최저에서 올라오기 시작했나
                if len(z2) >= 21:
                    _저 = min(list(z2)[:-1])
                    x["지분율바닥"] = 1.0 if (z2[-1] > _저 and abs(list(z2)[-2] - _저) < 1e-9) else 0.0
                x["지분20변화"] = z2[-1] - z2[0] if len(z2) >= 21 else None

    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건 · {len(묶):,}일\n", flush=True)
    # ⭐ 돈 시뮬 범위 = **그 무리** (규모면 그 띠 · 업종·섹터·종목이면 크기 제한 없음)
    _돈하한 = (_BIG_LO if (_무리종류 == "규모" and _BIG_LO) else 0.0)
    _돈상한 = (_BIG_HI if (_무리종류 == "규모" and _BIG_HI) else 9e12)
    _무리글 = (f"규모 {_BIG_LO:,.0f}억~{(format(_BIG_HI, ',.0f') + '억') if _BIG_HI else '(상한 없음)'}"
             if _무리종류 == "규모" else f"{_무리종류} = {_무리값}")

    캐시 = {}

    def 결과(x, 목표, 보유, 상태=None):
        """상태: None(기한) · "20일선"(종가가 20일선 위) · "볼0"(볼린저 0 위)

        ⚠️ 목표가에 먼저 닿으면 그걸로 판다. 상태는 **기한 대신** 쓰는 것이다
        """
        키 = (x["인"], x["code"], 목표, 보유, 상태)
        if 키 in 캐시:
            return 캐시[키]
        i = x["인"] - 1
        r, 청 = None, None
        for h in range(0, 보유 + 1):
            j = i + 1 + h
            if j >= len(날):
                break
            vv = 주가[날[j]].get(x["code"])
            b2 = (비.get(날[j]) or {}).get(x["code"])
            if not vv or not b2:
                break
            if vv[0] * b2[1] >= x["매수"] * (1 + 목표 / 100):
                r, 청 = 목표 - _비용, j
                break
            # ⭐ 손절 (own_lab) — 「손절-8」 이면 종가가 산 값보다 8% 넘게 빠진 날 그 종가에 판다
            if 상태 and str(상태).startswith("손절") and h >= 1:
                if (vv[0] / x["매수"] - 1) * 100 <= float(str(상태)[2:]):
                    r, 청 = (vv[0] / x["매수"] - 1) * 100 - _비용, j
                    break
            # ⭐ 상태 청산 — 날짜가 아니라 **회복됐을 때** 판다
            if 상태 in ("20일선", "볼0") and h >= 1:
                kk2 = (자리.get(x["code"]) or {}).get(날[j])
                if kk2 is not None and kk2 >= 20:
                    sq2 = 종계[x["code"]]
                    m20 = st.mean(sq2[kk2 - 19:kk2 + 1])
                    회복 = False
                    if 상태 == "20일선":
                        회복 = sq2[kk2] > m20
                    else:
                        sd2 = st.pstdev(sq2[kk2 - 19:kk2 + 1]) or 1e-9
                        회복 = (sq2[kk2] - m20) / (2 * sd2) > 0
                    if 회복:
                        r, 청 = (vv[0] / x["매수"] - 1) * 100 - _비용, j
                        break
        if r is None:
            j = i + 1 + 보유
            끝 = 주가[날[j]].get(x["code"]) if j < len(날) else None
            # ⚠️⚠️ **상장폐지를 손실로 센다** (2026-09-08 고침).
            #    전에는 자료가 없으면 그 거래를 **지웠다** —
            #    913종목(25%)이 중간에 사라졌고 성적이 부풀려졌다
            if not 끝 and x["code"] in _사라짐:
                캐시[키] = (O.폐지손실 - _비용, min(j, len(날) - 1))
                return 캐시[키]
            if not 끝:
                캐시[키] = (None, None)
                return 캐시[키]
            r, 청 = (끝[0] / x["매수"] - 1) * 100 - _비용, j
        캐시[키] = (r, 청)
        return 캐시[키]

    def 시뮬(c, 끝년=None, 시드=None, 시작년=None, 오차=0.0):
        import random as _r2
        _rng = _r2.Random(20260907)
        시드 = 시드 or _시드
        시작i = 시i
        if 시작년:
            _a = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = _a[0] if _a else 시i
        현금, 보유, 곡, 산 = 시드, [], [], 0
        for i in range(시작i, len(날)):
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["청산"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + 0.025 / 245)
            # ⭐ own_lab — 들고 있는 종목을 **전날 종가**로 평가한다 (산 값으로 세면 계좌 낙폭이 실제보다 얕다)
            _전 = 주가[날[i - 1]] if i >= 1 else {}
            평 = 현금 + sum(q["주수"] * q["원시"] * ((_전.get(q["code"]) or (q["매수수정"],))[0] / q["매수수정"])
                          for q in 보유)
            칸 = [x for x in (묶.get(i) or [])
                  if c["시총하한"] <= x["시총억"] < c["시총상한"]
                  and x["대금억"] >= c["대금하한"]
                  and x["거래량"] >= c["거래량하한"]
                  and x["회전율"] >= c["회전율하한"]]
            # ⚠️ 수급 거름은 **40개로 좁히기 전**에 건다.
            #    수급은 전날 자료라 08:00에 이미 알 수 있기 때문이다
            거름 = c.get("거름")
            if 거름:
                칸 = [x for x in 칸 if 거름(x)]
            # ⭐ own_lab — 후보를 20일 낙폭 순으로 자르지 않는다 (지금 규칙의 구조였다)
            if c.get("후보수", _후보수) < len(칸):
                칸 = sorted(칸, key=lambda z: z["낙폭20"])[:c.get("후보수", _후보수)]
            if len(칸) < c.get("최소", 3):
                곡.append(평)
                continue
            중 = (_시장중앙.get(날[i], 0.0) if c.get("갭기준", "시장") == "시장"
                 else st.median([x["갭"] for x in 칸]))
            잰 = []
            for x in 칸:
                v3 = x["갭"] - 중
                if 오차:
                    v3 += _rng.gauss(0, 오차)
                if v3 <= c["상대갭"]:
                    잰.append((v3, x))
            # ⚠️ 기본은 **갭이 큰 순**이다. 고르기가 있으면 그 순서로 바꾼다.
            #    문턱(상대갭 -3.5%p)은 그대로라 **후보 수는 안 변한다**
            고르기 = c.get("고르기")
            if 고르기:
                골 = sorted([z[1] for z in 잰], key=고르기)
            else:
                골 = ([z[1] for z in sorted(잰, key=lambda z: -(z[1].get("대금억") or 0))]
                      if c.get("줄") == "대금" else [z[1] for z in sorted(잰, key=lambda z: z[0])])
            # ⚠️⚠️ 2026-09-30 — `하루상한` 이 **함수**일 수 있다 (9/21 ㉥ 반영 때 _밑E 가 lambda 로 바뀜).
            #    여기서 그대로 자르다 TypeError 로 B145~B153 아홉 판이 전부 E절에서 죽었다
            _상한 = c["하루상한"]
            if callable(_상한):
                _상한 = _상한(골)
            for x in 골[:_상한]:
                # ⚠️ 나눔이 있으면 **주수를 쪼개** 두 몫으로 만든다.
                #    한 종목에 들어가는 총액은 같다 (자산 20%)
                몫들 = c.get("나눔") or ((1.0, c["목표"], c["최대보유"]),)
                쓸 = min(평 * c["비중"], 현금, (x.get("대금억") or 0) * 1e8 * 0.01)   # 신호일 거래대금 (사는 날 것은 장 끝나야 안다)
                총주수 = int(쓸 // x["원시"])
                if 총주수 < len(몫들) or 총주수 * x["원시"] > 현금:
                    continue
                넣음 = False
                for 몫 in 몫들:
                    비율, 목표b, 보유b = 몫[0], 몫[1], 몫[2]
                    상태b = 몫[3] if len(몫) > 3 else None
                    r, 청 = 결과(x, 목표b, 보유b, 상태b)
                    if r is None:
                        continue
                    주수 = int(총주수 * 비율)
                    if 주수 < 1 or 주수 * x["원시"] > 현금:
                        continue
                    현금 -= 주수 * x["원시"]
                    보유.append({"주수": 주수, "원시": x["원시"],
                                 "결과": r, "청산": 청, "code": x["code"], "매수수정": x["매수"]})
                    넣음 = True
                if 넣음:
                    산 += 1
            곡.append(평)
        _막 = 주가[날[min(i, len(날) - 1)]] if 보유 else {}
        끝 = 현금 + sum(q["주수"] * q["원시"] * ((_막.get(q["code"]) or (q["매수수정"],))[0] / q["매수수정"])
                       for q in 보유)
        해 = max(len(곡) / 245, 0.1)
        연 = ((끝 / 시드) ** (1 / 해) - 1) * 100 if 끝 > 0 else -100
        최고, 낙 = 시드, 0.0
        for v in 곡:
            최고 = max(최고, v)
            낙 = min(낙, v / 최고 - 1)
        return {"끝": 끝, "연": 연, "낙": 낙 * 100, "산": 산}

    머 = f"    {'':<28}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}"

    def 표(r, 라, 기=None):
        점 = r["연"] / max(abs(r["낙"]), 3.0)
        꼬 = ""
        if 기:
            늘 = (r["끝"] / 기["끝"] - 1) * 100
            꼬 = f"  ({늘:+.0f}%)"
        print(f"    {라:<28}{r['끝']:>15,.0f}원{r['연']:>+8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}{꼬}", flush=True)

    def 앞수익(x, n):
        i2 = x["인"]
        j = i2 + n
        if j >= len(날):
            return None
        a = 주가[날[i2]].get(x["code"])
        b = 주가[날[j]].get(x["code"])
        if not a or a[0] <= 0:
            return None
        if not b:
            return (O.폐지손실 - _비용) if x["code"] in _사라짐 else None
        return (b[0] / a[0] - 1) * 100 - _비용

    기간들 = (5, 20, 40)
    print("  기간별 수익률 붙이는 중...", flush=True)
    for x in 사건:
        for n in 기간들:
            x[f"_{n}"] = 앞수익(x, n)
    # ⚠️ **박아 두면 안 된다** — `--최근N년` 으로 기간을 자를 때 안 따라온다.
    #    2026-09-15 새벽: S2판(1년)이 1,979건을 「1년에 **190**」이라 찍었다.
    #    10.4 로 나눴기 때문이다 — 실제로는 1,979 다. **10.4배 작게** 나왔다.
    #    「1년에 몇 개」는 사용자 1순위 잣대(**기회**)라 그냥 둘 수 없다.
    #    아래 `_최근년` 을 읽은 뒤 다시 계산한다 (여기 값은 자르기 전 기본)
    해수 = 10.4

    # ⭐⭐⭐ **최근 1년만** (2026-09-14) — 뉴스는 약 1년치뿐이라 10.4년 사건에
    #    붙이면 오분위가 통째로 건너뛴다. 이 선택지에서만 뉴스가 재진다
    # ⭐ --최근N년 (2026-09-14 밤 일반화). dart-snap 은 2024~2025 두 해뿐이라
    #    10.4년 사건에 붙이면 19% 로 오분위(30% 문턱)가 건너뛴다 — 2년 판이 필요하다
    # ⚠️⚠️ **`_a[3:-1]` 이 범인이었다** (2026-09-15 새벽).
    #    `--최근` 은 `-`,`-`,`최`,`근` **네 글자**다. 셋으로 잘라 「근1」이 되고
    #    `int("근1")` 이 터지는데 그걸 `pass` 로 삼켜 `_최근년 = 0` 으로 남았다.
    #    ⇒ **S판(1년)도 U판(2년)도 전체 10.4년으로 돌았다.** 출력에
    #    「최근 N년만」 줄이 아예 없는 게 증거였다
    #    ⇒ 글자 수를 박지 않고 `len(_앞)` 으로 자른다.
    #      그리고 **조용히 넘기지 않는다** — `pass` 가 이 버그를 숨겼다
    _최근년 = 0
    _앞 = "--최근"
    for _a in sys.argv:
        if _a.startswith(_앞) and _a.endswith("년"):
            try:
                _최근년 = int(_a[len(_앞):-1])
            except ValueError:
                raise SystemExit(
                    f"\n⚠️ `{_a}` 에서 햇수를 못 읽었다 — 판을 안 돌린다."
                    f"\n   `--최근1년` `--최근2년` 처럼 써라\n")
    if _최근년 and 날:
        _자른 = len(날) - 245 * _최근년
        _전 = len(사건)
        사건 = [x for x in 사건 if x["인"] >= _자른]
        # ⭐ **해수도 같이 줄인다** (2026-09-15 새벽). 안 그러면 「1년에 몇 개」가
        #    10.4 로 나뉘어 **10.4배 작게** 나온다 — 기회를 못 알아본다
        해수 = float(_최근년)
        print(f"  ⭐ **최근 {_최근년}년만** — 사건 {_전:,} → {len(사건):,}건 "
              f"({날[max(0, _자른)]} ~ {날[-1]}) · 해수 10.4 → {해수:g}", flush=True)

    # ⭐⭐⭐ **안 써본 재료 넷** (2026-09-14 · field_audit 에서 「한 번도 안 씀」).
    #    ⭐⭐ 2026-09-14 밤에 둘을 더했다 — **분기 재무(11.5년)** 와
    #       **단일종목선물(16년)**. 둘 다 자료는 처음부터 있었는데
    #       `docs/자료재고.md` 가 하위 폴더를 합쳐 세는 바람에 **눈에 안 띄었다**
    #    사용자: 「기존 규칙에 얹는 게 아니라 **단독 재료로서의 효과**와
    #             다른 재료와의 **다양한 조합**일 때 효과를 측정해야 해」
    #    ⇒ 이름만 늘리면 아래 A(하나씩)·B(둘씩 전수)·C(셋씩)가 그대로 재 준다
    print("\n  ⭐ 안 써본 재료 붙이는 중 (공시시각 · 임원 · 대주주 · 뉴스 · 컨센서스 ·"
          " 증자 · ETF · 거시 · 배당 · ⭐분기재무 · ⭐단일종목선물)...", flush=True)
    _새재료 = newmat.붙이기(사건, 날, 뉴스포함=True)
    print(f"    붙은 재료 {len(_새재료)}가지: {', '.join(_새재료)}", flush=True)
    # ⭐⭐ own_lab 새 재료 — 밸류에이션 · 긴 흐름 · 해외 동종 (9/10 사용자 「왜 모멘틈, 밸류에이션이 빠진 거야?」)
    _원재무 = {}
    for _fF in sorted(glob.glob(os.path.join(O._DATA, "dart-fin", "*.json"))):
        _yF = os.path.basename(_fF)[:-5]
        if not _yF.isdigit():
            continue
        _적F = f"{int(_yF) + 1}0401"          # Y년 재무는 Y+1년 4월부터 쓴다 (day_lab 과 같다)
        try:
            _dF = json.load(io.open(_fF, encoding="utf-8-sig"))
        except ValueError:
            continue
        for _cF, _vF in _dF.items():
            def _gF(k, _v=_vF):
                z = _v.get(k)
                return float(z) if isinstance(z, (int, float)) else None
            _원재무.setdefault(_cF, []).append((_적F, _gF("당기순이익(손실)"), _gF("자본총계"), _gF("매출액")))
    for _cF in _원재무:
        _원재무[_cF].sort()

    def _원값(code, d8):
        m = None
        for z in (_원재무.get(code) or []):
            if z[0] <= d8:
                m = z
            else:
                break
        return m

    def _가치(x, k):
        w = _원값(x["code"], 날[x["인"] - 1])
        시 = (x.get("시총억") or 0) * 1e8
        if not w or not 시 or w[k] is None:
            return None
        return w[k] / 시 * 100

    def _긴흐름(x, n):
        kk = (자리.get(x["code"]) or {}).get(날[x["인"] - 1])
        if kk is None or kk < n:
            return None
        sq = 종계[x["code"]]
        return (sq[kk] / sq[kk - n] - 1) * 100 if sq[kk - n] > 0 else None

    # 해외 동종 — yahoo 분류마다 5일·20일 평균 수익률 (그날 종가까지 · 한국 다음 날 시가 전에 안다)
    import bisect as _bsY
    _분류값 = {}
    for _fY in glob.glob(os.path.join(O._DATA, "yahoo", "*.json")):
        try:
            _jY = json.load(io.open(_fY, encoding="utf-8-sig"))
        except ValueError:
            continue
        _심Y = str(_jY.get("심볼") or os.path.basename(_fY)[:-5])
        _분Y = str(_jY.get("갈래") or "")
        if not _분Y:
            _분Y = ("지수" if _심Y.startswith("IDX_") else "원자재" if _심Y.endswith("=F")
                    else "환율" if (_심Y.endswith("=X") or _심Y.startswith("DX")) else
                    "채권" if _심Y in ("BND", "EMB", "HYG", "IEF", "JNK", "LQD", "SHY", "TIP", "TLT") else
                    "미국ETF" if _심Y in ("DIA", "IWM", "QQQ", "SPY", "XLK", "SMH", "SOXX", "GLD") else "기타")
        _종Y = _jY.get("종가") or {}
        if not isinstance(_종Y, dict) or len(_종Y) < 300:
            continue
        _ds = sorted(_종Y)
        _vs = [float(_종Y[d]) for d in _ds]
        _분류값.setdefault(_분Y, []).append((_ds, _vs))
    _해외재료 = []
    _해외표 = {}
    for _분Y, 목록 in _분류값.items():
        for n in (5, 20):
            이름 = f"해외{_분Y}{n}"
            날들 = sorted({d for ds, _ in 목록 for d in ds})
            평 = []
            for d in 날들:
                합 = 셈 = 0
                for ds, vs in 목록:
                    p = _bsY.bisect_right(ds, d) - 1
                    if p >= n and vs[p - n] > 0:
                        합 += (vs[p] / vs[p - n] - 1) * 100
                        셈 += 1
                평.append(합 / 셈 if 셈 else None)
            _해외표[이름] = (날들, 평)
            _해외재료.append(이름)
    print(f"    ⭐ 해외 동종 — 분류 {len(_분류값)}개 → 재료 {len(_해외재료)}가지", flush=True)

    def _해외(x, 이름):
        ds, vs = _해외표[이름]
        p = _bsY.bisect_right(ds, 날[x["인"] - 1]) - 1
        return vs[p] if p >= 0 else None

    # ══ 재료 목록 ══
    재료들 = ("볼린저", "낙폭20", "낙폭60", "60일선대비", "갭",
              "RSI14", "RSI변화5", "MACD히스토", "MACD골든5", "스토K14",     # ⭐ 기술지표 (2026-09-15)
              "진폭14", "당일진폭", "시가위치",                                # ⭐ 저가 (안 쓰던 필드)
              "미국10년20", "미국금리차", "미국금리차20",                      # ⭐ fred (안 쓰던 폴더)
              "실적공시후5", "실적시즌",          # ⭐ 사건 전후 (처음)
              "실적공시후1", "실적공시후20", "손익구조후5",                        # ⭐ earnings-dates.json
              "FOMC회의후5", "미국CPI후3", "금통위변경후5",                       # ⭐ 실제 일정 (event-calendar)
              "미국고용후3", "국내CPI주간", "수출발표후2",                          # ⭐ 고용(실제) · 국내(고정 달력 근사)
              "FOMC회의전5", "미국CPI전3", "미국고용전3",           # ⭐ 사건 **앞** 창 (2026-09-16)
              "수출발표전2",                                        # ⚠️ 실적공시전5 는 실전 불가(날짜를 미리 모름)
              "미국CPI전5", "미국고용전5", "수출발표전5",                            # ⭐ 사용자 「5일 이내 범위면 좋은 것 같은데?」 — 앞 창 전부 5일로
              "선거전5", "선거후5", "월드컵중", "올림픽중",                          # ⭐ 특수 (표본 적음 · 선거 13 · 월드컵 5 · 올림픽 4)
              "미국선거전5", "미국선거후5",                                       # ⭐ 미국 대선4·중간선거4
              "ETF괴리", "ETF괴리20",                                             # ⭐ ETF NAV 괴리율 (시장 재료 · 2026-09-16)
              "봄", "여름", "가을", "겨울",
              "신고가60", "20일선돌파", "60일선돌파", "정배열", "정배열전환",   # ⭐ 오르기 시작하는 것 (2026-09-18)
              "양봉어제", "아래꼬리", "낙폭둔화", "볼린저회복", "하락끊김", "거래량바닥",  # ⭐ 반등 신호 (2026-09-18)
              "외인전환", "기관전환", "수급동시전환", "지분율바닥",                    # ⭐ 막 켜진 신호 (2026-09-18)
              "거래량깨움",
              "밴드수축", "신저가반등", "연속하락", "되돌림",                    # ⭐ 전환 낌새 더 (2026-09-18 밤)
              "자사주직후", "임원매수직후",
              # ⭐ 창을 3일·10일로도 (2026-09-18 밤 · 사용자 「애매한 기준」 5번 — 5일은 내가 정한 값이다)
              "자사주직후3", "자사주직후10", "임원매수직후3", "임원매수직후10", "외인전환10",                                         # ⭐ 계절 (combo5 H절 뒤 · 2026-09-16 밤)
              "수출YoY", "수입YoY", "무역수지비", "국내CPI_YoY", "기준금리20",         # ⭐ ECOS (수출 주도국 · 처음)
              "시총억", "대금억", "거래량", "회전율",
              "잉여금", "부채", "ROE", "영업이익률", "순이익률", "유동비율",
              "시장낙폭", "상대강도", "시장변동성", "소형우위",
              "섹터낙폭", "섹터대비",
              "외인1", "외인5", "외인20", "기관5", "기관20", "개인5",
              "지분율", "지분20변화",
              "이익수익률", "순자산수익률", "매출수익률", "수익률120", "수익률250") + tuple(_새재료) + tuple(_해외재료)

    print("\n" + "=" * 122)
    print("  163차 · 재료 **단독**과 **새 조합** — 우리 규칙을 안 깔고 처음부터")
    print("  ⚠️ 상장폐지는 -50% 손실로 센다")
    print("=" * 122)

    # ══ 오분위 자르기 ══
    print("\n  재료를 오분위로 자르는 중...", flush=True)
    조건 = {}          # 이름 -> 그 조건을 만족하는 사건 자리들(set)
    쓸재료 = []
    # ⭐ dict 에 안 넣은 재료 30개 — 여기서 함수로 만든다 (2026-09-16 · MemoryError 고침)
    #    x["인"]-1 = 신호일 자리 i · kk = 그 종목 종가열 자리
    def _kk(x):
        return (자리.get(x["code"]) or {}).get(날[x["인"] - 1])

    def _dict계산(이름, f):
        def g(x):
            kk = _kk(x)
            return None if kk is None else f(x["code"], kk)
        return g
    # ⭐ ECOS (2026-09-16 · 사용자 키) — 월 자료는 발표일 뒤부터, 일별 금리는 다음 거래일부터
    def _ecos(이름):
        try:
            return (json.load(io.open(os.path.join(O._DATA, "ecos", f"{이름}.json"), encoding="utf-8")).get("값") or {})
        except Exception:  # noqa: BLE001
            return {}
    _수출, _수입, _cpi, _기준 = _ecos("수출금액"), _ecos("수입금액"), _ecos("소비자물가"), _ecos("기준금리")

    def _월YoY(표, ym):
        a, b = 표.get(ym), 표.get(f"{int(ym[:4]) - 1}{ym[4:]}")
        return ((a / b - 1) * 100) if (a and b and b > 0) else None

    def _알수있는달(d8, 늦춤일):
        """d8 에 알 수 있는 「가장 최근 완결 달」 — 그 달 늦춤일 이후면 전달, 아니면 전전달"""
        y, m = int(d8[:4]), int(d8[4:6])
        if int(d8[6:8]) < 늦춤일:
            m -= 1
        m -= 1                      # 전달 자료
        while m <= 0:
            m += 12
            y -= 1
        return f"{y}{m:02d}"

    def _수출YoY(x):
        return _월YoY(_수출, _알수있는달(날[x["인"] - 1], 2))
    def _수입YoY(x):
        return _월YoY(_수입, _알수있는달(날[x["인"] - 1], 2))
    def _무역수지비(x):
        ym = _알수있는달(날[x["인"] - 1], 2)
        a, b = _수출.get(ym), _수입.get(ym)
        return ((a - b) / a * 100) if (a and b and a > 0) else None
    def _cpiYoY(x):
        return _월YoY(_cpi, _알수있는달(날[x["인"] - 1], 7))
    _기준일들 = sorted(_기준)
    # ⭐ ETF NAV 괴리율 (2026-09-16 · 사용자 「왜 테스트 안 했지?」) — 날짜 표로만
    _괴리표 = newmat._ETF괴리표(날)
    _괴리열 = [_괴리표.get(d) for d in 날]
    print(f"    ETF 괴리율 {len(_괴리표):,}일", flush=True)

    def _ETF괴리(x):
        return _괴리열[x["인"] - 1]

    def _ETF괴리20(x):
        i = x["인"] - 1
        a, b = _괴리열[i], (_괴리열[i - 20] if i >= 20 else None)
        return (a - b) if (a is not None and b is not None) else None
    def _기준금리20(x):
        import bisect as _b3
        i = x["인"] - 1
        d, d20 = 날[i - 1] if i >= 1 else None, 날[i - 21] if i >= 21 else None
        if not d or not d20:
            return None
        def _v(dd):
            p = _b3.bisect_right(_기준일들, dd) - 1
            return _기준[_기준일들[p]] if p >= 0 else None
        a, b = _v(d), _v(d20)
        return (a - b) if (a is not None and b is not None) else None
    print(f"    ECOS: 수출 {len(_수출)}달 · 수입 {len(_수입)}달 · CPI {len(_cpi)}달 · 기준금리 {len(_기준)}일", flush=True)

    _계산재료 = {
        "ETF괴리": _ETF괴리, "ETF괴리20": _ETF괴리20,
        "수출YoY": _수출YoY, "수입YoY": _수입YoY, "무역수지비": _무역수지비,
        "국내CPI_YoY": _cpiYoY, "기준금리20": _기준금리20,
        "RSI14": _dict계산("RSI14", lambda c, kk: _ta("RSI14", c, kk)),
        "RSI변화5": _dict계산("RSI변화5", lambda c, kk: _ta("RSI변화5", c, kk)),
        "MACD히스토": _dict계산("MACD히스토", lambda c, kk: _ta("MACD히스토", c, kk)),
        "MACD골든5": _dict계산("MACD골든5", lambda c, kk: _ta("MACD골든5", c, kk)),
        "스토K14": _dict계산("스토K14", lambda c, kk: _ta("스토K14", c, kk)),
        "진폭14": _dict계산("진폭14", lambda c, kk: _진폭14(c, kk)),
        "당일진폭": _dict계산("당일진폭", lambda c, kk: _당일(_진폭, c, kk)),
        "시가위치": _dict계산("시가위치", lambda c, kk: _당일(_시위, c, kk)),
        "미국10년20": lambda x: _변화20(_us10, x["인"] - 1),
        "미국금리차": lambda x: _금리차[x["인"] - 1],
        "미국금리차20": lambda x: _변화20(_금리차, x["인"] - 1),
        "실적공시후5": lambda x: _실적후(x["code"], x["인"] - 1, 5),
        "실적공시후1": lambda x: _실적후(x["code"], x["인"] - 1, 1),
        "실적공시후20": lambda x: _실적후(x["code"], x["인"] - 1, 20),
        "손익구조후5": lambda x: _실적후(x["code"], x["인"] - 1, 5, _손익일),
        "실적시즌": lambda x: _실적시즌(날[x["인"] - 1]),
        "FOMC변경후5": lambda x: _fomc후(x["인"] - 1, 5),
        "FOMC변경후20": lambda x: _fomc후(x["인"] - 1, 20),
        "FOMC회의후5": lambda x: _뒤N(_fomc회의자리, x["인"] - 1, 5),
        "미국CPI후3": lambda x: _뒤N(_cpi자리, x["인"] - 1, 3),
        "금통위변경후5": lambda x: _뒤N(_금통자리, x["인"] - 1, 5),
        "미국고용후3": lambda x: _뒤N(_고용자리, x["인"] - 1, 3),
        "국내CPI주간": lambda x: _국내CPI주간(날[x["인"] - 1]),
        "수출발표후2": lambda x: _뒤N(_월첫자리, x["인"] - 1, 2),
        "FOMC회의전5": lambda x: _앞N(_fomc회의자리, x["인"] - 1, 5),
        "미국CPI전3": lambda x: _앞N(_cpi자리, x["인"] - 1, 3),
        "미국고용전3": lambda x: _앞N(_고용자리, x["인"] - 1, 3),
        "금통위변경전5": lambda x: _앞N(_금통자리, x["인"] - 1, 5),
        "수출발표전2": lambda x: 1.0 if (_월끝자리 and _앞N(_월끝자리, x["인"] - 2, 2)) else 0.0,
        "실적공시전5": lambda x: _실적전(x["code"], x["인"] - 1, 5),
        "미국CPI전5": lambda x: _앞N(_cpi자리, x["인"] - 1, 5),
        "미국고용전5": lambda x: _앞N(_고용자리, x["인"] - 1, 5),
        "수출발표전5": lambda x: 1.0 if (_월끝자리 and _앞N(_월끝자리, x["인"] - 2, 5)) else 0.0,
        "선거전5": lambda x: _앞N(_선거자리, x["인"] - 1, 5),
        "선거후5": lambda x: _뒤N(_선거자리, x["인"] - 1, 5),
        "월드컵중": lambda x: _기간안(_월드컵, 날[x["인"] - 1]),
        "올림픽중": lambda x: _기간안(_올림픽, 날[x["인"] - 1]),
        "미국선거전5": lambda x: _앞N(_미선거자리, x["인"] - 1, 5),
        "미국선거후5": lambda x: _뒤N(_미선거자리, x["인"] - 1, 5),
        # ⭐ **오르기 시작하는 것** (2026-09-18 · 사용자 「빠진 걸 재고 있는데 오르기 시작하는 건?」)
        #    지금 재료는 전부 「이미 올랐다」다 — 전환점(돌파·정배열 전환)은 하나도 없었다
        # ⭐ **반등 신호 포착** (2026-09-18) — 전날 종가까지로만 계산한다. 하루도 안 늦는다
        # ⭐ 막 켜진 신호 중 계산이 필요한 둘 (2026-09-18)
        "거래량깨움": _거래량깨움,
        # ⭐ 전환 낌새 더 여섯 (2026-09-18 밤 · 사용자 「테스트 해볼 수 있는 건 다 해봐」)
        "밴드수축": _밴드수축,
        "신저가반등": _신저가반등,
        "연속하락": _연속하락,
        "되돌림": _되돌림,
        "자사주직후": lambda x: _공시직후(x, "자사주취득"),
        "임원매수직후": lambda x: _임원직후(x),
        # ⭐ 같은 신호를 3일·10일 창으로도 (2026-09-18 밤) — 5일이 맞는지 재 본 적이 없다
        "자사주직후3": lambda x: _공시직후(x, "자사주취득", 3),
        "자사주직후10": lambda x: _공시직후(x, "자사주취득", 10),
        "임원매수직후3": lambda x: _임원직후(x, 3),
        "임원매수직후10": lambda x: _임원직후(x, 10),
        "외인전환10": _외인전환10,
        "양봉어제": lambda x: (_양봉.get(x["code"]) or {}).get(_시세(x)[1]),
        "아래꼬리": lambda x: (_꼬리.get(x["code"]) or {}).get(_시세(x)[1]),
        "낙폭둔화": _낙폭둔화,
        "볼린저회복": _볼린저회복,
        "하락끊김": _하락끊김,
        "거래량바닥": _거래량바닥,
        "신고가60": lambda x: _신고가(x, 60),
        "20일선돌파": lambda x: _선돌파(x, 20),
        "60일선돌파": lambda x: _선돌파(x, 60),
        "정배열": lambda x: _정배열(x, 0),
        "정배열전환": lambda x: _정배열(x, 1),
        "봄": lambda x: _계절인가(x, "봄"), "여름": lambda x: _계절인가(x, "여름"),
        "가을": lambda x: _계절인가(x, "가을"), "겨울": lambda x: _계절인가(x, "겨울"),
    }
    _계산재료.update({
        "이익수익률": lambda x: _가치(x, 1), "순자산수익률": lambda x: _가치(x, 2),
        "매출수익률": lambda x: _가치(x, 3),
        "수익률120": lambda x: _긴흐름(x, 120), "수익률250": lambda x: _긴흐름(x, 250)})
    for _이름Y in _해외재료:
        _계산재료[_이름Y] = (lambda x, _n=_이름Y: _해외(x, _n))
    # ⭐⭐ own_lab — **앞 기간 값으로만 문턱** · **자료 시작 전 해는 없음**
    _해들 = [날[x["인"] - 1][:4] for x in 사건]
    _앞여부 = [날[x["인"] - 1] < _분할 for x in 사건]
    _앞총 = sum(_앞여부)
    _건너뜀 = []
    _늦게시작 = (set(_새재료) | {"임원매수직후", "임원매수직후3", "임원매수직후10", "자사주직후", "자사주직후3",
                               "자사주직후10", "이익수익률", "순자산수익률", "매출수익률",
                               "외인1", "외인5", "외인20", "기관5", "기관20", "개인5", "지분율", "지분20변화"})
    for 재 in 재료들:
        if 재 in _계산재료:
            _f재 = _계산재료[재]
            v = [_f재(x) for x in 사건]
        else:
            v = [x.get(재) for x in 사건]
        # ① 자료가 **시작되기 전** 해는 없음 — 해마다 「0 이 아닌 값」 비율이 가장 많은 해의 10% 밑인 해가
        #    **처음부터 이어지면** 그 해들은 자료가 없었던 것이다 (임원 자료는 2024~ 뿐 · 0 으로 채워져 있었다)
        _해합 = {}
        for i2, z in enumerate(v):
            a2 = _해합.setdefault(_해들[i2], [0, 0])
            a2[0] += 1
            if z is not None and z != 0:
                a2[1] += 1
        _비 = {h: t[1] / t[0] for h, t in _해합.items() if t[0]}
        _최비 = max(_비.values()) if _비 else 0
        _빈해 = set()
        for h in sorted(_비):
            if _최비 > 0 and _비[h] < _최비 * 0.1:
                _빈해.add(h)
            else:
                break
        if 재 not in _늦게시작:
            _빈해 = set()
        if _빈해:
            v = [None if _해들[i2] in _빈해 else z for i2, z in enumerate(v)]
            print(f"    {재:<12} {min(_빈해)}~{max(_빈해)} 자료 없음 → 0 이 아니라 「없음」", flush=True)
        # ② 문턱은 **앞 기간 값으로만** (미래를 안 본다)
        가 = sorted(z for i2, z in enumerate(v) if z is not None and _앞여부[i2])
        if len(가) < max(300, _앞총 * 0.05):
            print(f"    {재:<12} 앞 기간 값이 {len(가):,}개뿐 — 이 무리에서는 앞에서 찾을 수 없다 (건너뜀)")
            _건너뜀.append(재)
            continue
        낮 = 가[len(가) // 5]
        높 = 가[len(가) * 4 // 5]
        # ⚠️⚠️ **값이 한 곳에 몰린 재료**를 막는다 (2026-09-14 밤).
        #    흑자전환·수주건수·유상증자처럼 **0 이 대부분**인 재료는
        #    20% 자리도 0, 80% 자리도 0 이라 아래·위가 **둘 다 「전부」**가 된다.
        #    아무것도 안 가르면서 조건 목록에 들어가 조합을 수천 개 부풀리고,
        #    정작 뜻 있는 갈래(**흑자전환 = 1**)는 사라진다
        #    ⇒ 문턱이 겹치면 「그 값보다 큰가/작은가」로 가른다
        _몰렸나 = (낮 == 높)
        # ⭐⭐ **set → int 비트마스크** (2026-09-14 밤 · MemoryError 고침).
        #    조건 110개 × set(108만) = 7GB 였다. 비트마스크면 110 × 136KB = 15MB.
        #    담는 그릇만 바뀌고 **값은 하나도 안 바뀐다**
        # ⚠️⚠️ **`아래 |= 1 << i2` 를 쓰면 안 된다** (2026-09-14 밤 · 25GB 사고).
        #    파이썬 int 는 불변이라 그 한 줄이 **136KB 짜리 int 를 새로 만든다.**
        #    108만 번 돌면 가비지가 쌓여 **램이 25GB** 까지 치솟았다(여유 1.8GB).
        #    ⇒ `bytearray` 에 **제자리로** 비트를 세우고 마지막에 한 번만 int 로.
        _바이트 = (len(사건) + 7) // 8
        _아래b = bytearray(_바이트)
        _위b = bytearray(_바이트)
        _아래수 = _위수 = 0
        for i2, z in enumerate(v):
            if z is None:
                continue
            if (z < 낮) if _몰렸나 else (z <= 낮):
                _아래b[i2 >> 3] |= 1 << (i2 & 7)
                _아래수 += 1
            if (z > 높) if _몰렸나 else (z >= 높):
                _위b[i2 >> 3] |= 1 << (i2 & 7)
                _위수 += 1
        아래 = int.from_bytes(_아래b, "little")
        위 = int.from_bytes(_위b, "little")
        # ⚠️ 조건 하나가 사건의 **절반**을 넘으면 오분위가 아니다 — 안 쓴다
        _절반 = len(사건) * 6 // 10       # 앞 기간 문턱이라 전체에선 절반을 조금 넘을 수 있다
        if 500 < _아래수 <= _절반:
            조건[f"{재}↓"] = 아래
        if 500 < _위수 <= _절반:
            조건[f"{재}↑"] = 위
        if _몰렸나:
            print(f"    {재:<12} 값이 한 곳에 몰렸다 — "
                  f"「{낮:g} 보다 큰가」로 가른다 (위 {_위수:,}건)")
        쓸재료.append(재)
    if _BIG_LO:
        _큰것 = sorted({x["code"] for x in 사건})
        print(f"    ⭐ **대형주 전용** — 시총 {_BIG_LO:,.0f}억 이상 · 종목 {len(_큰것):,}개 · 사건 {len(사건):,}건", flush=True)
    print(f"    쓸 재료 {len(쓸재료)}가지 · 조건 {len(조건)}개"
          f" (각각 아래 20% / 위 20%)", flush=True)

    수익 = {기: [x.get(f"_{기}") for x in 사건] for 기 in 기간들}

    # ⭐ 비트마스크에서 자리를 뽑는 표 (바이트 하나에 8자리)
    _비트표 = [[i for i in range(8) if (b >> i) & 1] for b in range(256)]
    _자리수 = len(사건)

    def _자리뽑기(m):
        """비트마스크 → 사건 자리들 (`array("i")`)

        ⚠️⚠️ **list 로 주면 안 된다** (2026-09-15 새벽 · S판 MemoryError).
           109만 자리를 파이썬 list[int] 로 담으면 **~40MB** 다.
           쌍 5,565개를 훑으며 매번 만들고 버리니 램이 버티지 못했다.
           `array("i")` 는 4바이트씩 — **4.4MB** 로 1/9 이다
        """
        out = _array("i")
        bs = m.to_bytes((_자리수 + 7) // 8, "little")
        for bi, b in enumerate(bs):
            if b:
                base = bi * 8
                out.extend(base + i for i in _비트표[b])
        return out

    def 재기(m):
        """(건수, {기간: (이김%, 평균)}) — `m` 은 **비트마스크**다

        ⚠️ 중간 리스트 `v` 를 **안 만든다** (2026-09-15 새벽).
           기간 3개 x 109만 짜리 리스트를 쌍마다 만들고 버렸다.
           훑으면서 바로 더한다 — **값은 하나도 안 바뀐다**
        """
        자리들 = _자리뽑기(m) if isinstance(m, int) else m
        n = len(자리들)
        낸 = {}
        for 기 in 기간들:
            arr = 수익[기]
            센것 = 이긴것 = 0
            합 = 0.0
            for i2 in 자리들:
                z = arr[i2]
                if z is None:
                    continue
                센것 += 1
                합 += z
                if z > 0:
                    이긴것 += 1
            if 센것 < 80:
                낸[기] = None
                continue
            낸[기] = (이긴것 / 센것 * 100, 합 / 센것)
        return n, 낸

    def 줄내기(라, n, 낸):
        줄 = f"  {라:<44}{n:>9,}{n/해수:>7.0f}"
        for 기 in 기간들:
            if 낸.get(기) is None:
                줄 += f"{'-':>9}{'-':>8}"
            else:
                줄 += f"{낸[기][0]:>8.1f}%{낸[기][1]:>+8.2f}"
        return 줄

    머2 = (f"  {'설정':<44}{'건수':>9}{'1년에':>7}"
           f"{'5일 이김':>9}{'평균':>8}{'20일 이김':>10}{'평균':>8}"
           f"{'40일 이김':>10}{'평균':>8}")

    # ══════════════════════════════════════════════════════════════════════
    #  무리 전용 규칙 — **앞 기간(~2018)에서 찾고, 뒤 기간(2019~)에서 확인한다**
    #  설계: docs/2026-09-30_무리전용_시험설계.md · 지금 규칙(rule_def 의 문턱·문·매도)을 **안 쓴다**
    # ══════════════════════════════════════════════════════════════════════
    import math as _m

    def _마스크거름(m):
        바 = m.to_bytes((_자리수 + 7) // 8, "little")

        def _f(x):
            _k = x.get("_i")
            return 0 if _k is None else (바[_k >> 3] >> (_k & 7)) & 1
        return _f

    for _i2, _x in enumerate(사건):
        _x["_i"] = _i2
    _앞b = bytearray((len(사건) + 7) // 8)
    for _i2, _x in enumerate(사건):
        if 날[_x["인"] - 1] < _분할:
            _앞b[_i2 >> 3] |= 1 << (_i2 & 7)
    앞마 = int.from_bytes(_앞b, "little")
    _앞수 = 앞마.bit_count()
    _첫날 = min((날[x["인"] - 1] for x in 사건), default=_시작)
    _앞해 = max(0.5, sum(1 for d in 날 if _첫날 <= d < _분할) / 245)
    _뒤해 = max(0.5, sum(1 for d in 날 if d >= _분할) / 245)
    _분할년 = _분할[:4]
    _앞끝년 = str(int(_분할년) - 1)
    _n0, _낸0 = 재기(앞마)
    바20 = _낸0[20][0] if _낸0.get(20) else 45.0
    _최소n = max(60, _앞수 // 500)
    print("\n" + "=" * 122)
    print(f"  ── 무리 전용 규칙 ── {_무리글}")
    print(f"     사건 {len(사건):,}건 (앞 {_앞수:,} · 뒤 {len(사건) - _앞수:,}) · 종목 {len({x['code'] for x in 사건}):,} · "
          f"앞 {_시작[:4]}~{_앞끝년} ({_앞해:.1f}년) · 뒤 {_분할년}~ ({_뒤해:.1f}년)")
    print(f"     앞 기간 바탕(이 무리 아무 날) 20일 이김 {바20:.1f}% · 조합 최소 건수 {_최소n}")
    print(f"     지금 규칙 안 씀 · 낙폭 한계 {_낙한:g}% (사용자) · 순위 = 1년 기회 먼저 (사용자)")
    print("=" * 122, flush=True)

    def _z(p, p0, n):
        if not n or p0 <= 0 or p0 >= 100:
            return None
        q = p0 / 100
        return (p / 100 - q) / _m.sqrt(q * (1 - q) / n)

    def _앞점(m):
        n, 낸 = 재기(m & 앞마)
        if n < _최소n or not 낸.get(20):
            return None
        w, avg = 낸[20]
        return (_z(w, 바20, n) or 0.0, w, n, avg)

    # ── ① 하나 · 둘 · 셋 · 넷 — 앞 기간으로만 줄 세운다 (이김 z 와 20일 평균 둘 다) ──
    이름들 = sorted(조건)
    단 = []
    for 라 in 이름들:
        s = _앞점(조건[라])
        if s:
            단.append((라, *s))
    print(f"\n  ① 하나씩 — 잰 조건 {len(단)}개 (앞 기간 {_최소n}건 이상)", flush=True)
    쌍 = []
    _쌍잰 = 0
    for a in range(len(이름들)):
        for b in range(a + 1, len(이름들)):
            라1, 라2 = 이름들[a], 이름들[b]
            if 라1[:-1] == 라2[:-1]:
                continue
            m = 조건[라1] & 조건[라2] & 앞마
            if m.bit_count() < _최소n:
                continue
            _쌍잰 += 1
            s = _앞점(m)
            if s:
                쌍.append((f"{라1} + {라2}", *s))
    print(f"  ② 둘씩 AND — 전수 {_쌍잰:,}쌍 잼 (같은 재료 위·아래 짝만 뺌)", flush=True)

    def _위(목록, k):
        by_z = sorted(목록, key=lambda z: -z[1])[:k]
        by_a = sorted(목록, key=lambda z: -z[4])[:k]
        out, 본 = [], set()
        for z in by_z + by_a:
            if z[0] not in 본:
                본.add(z[0])
                out.append(z)
        return out
    _씨쌍 = [z[0] for z in _위(쌍, 60)]
    셋 = []
    for 라 in _씨쌍:
        부 = 라.split(" + ")
        m0 = 조건[부[0]] & 조건[부[1]] & 앞마
        for 라3 in 이름들:
            if 라3 in 부 or any(라3[:-1] == p[:-1] for p in 부):
                continue
            m = m0 & 조건[라3]
            if m.bit_count() < _최소n:
                continue
            s = _앞점(m)
            if s:
                셋.append((" + ".join(sorted(부 + [라3])), *s))
    셋 = list({z[0]: z for z in 셋}.values())
    print(f"  ③ 셋 — 위 쌍 {len(_씨쌍)}개에 하나씩 더해 {len(셋):,}개", flush=True)
    _씨셋 = [z[0] for z in _위(셋, 30)]
    넷 = []
    for 라 in _씨셋:
        부 = 라.split(" + ")
        m0 = 조건[부[0]] & 조건[부[1]] & 조건[부[2]] & 앞마
        for 라4 in 이름들:
            if 라4 in 부 or any(라4[:-1] == p[:-1] for p in 부):
                continue
            m = m0 & 조건[라4]
            if m.bit_count() < _최소n:
                continue
            s = _앞점(m)
            if s:
                넷.append((" + ".join(sorted(부 + [라4])), *s))
    넷 = list({z[0]: z for z in 넷}.values())
    print(f"  ④ 넷 — 위 셋 {len(_씨셋)}개에 하나씩 더해 {len(넷):,}개", flush=True)

    _k = int(os.environ.get("OWN_K") or 14)
    후보 = []
    for 목록, k in ((단, _k), (쌍, _k), (셋, _k // 2), (넷, _k // 3)):
        for z in _위(목록, k):
            if z[2] > 바20 and z[0] not in [q[0] for q in 후보]:
                후보.append(z)
    print(f"\n  돈으로 넘길 조건 {len(후보)}개 — 이김 z 위 · 20일 평균 위 (앞 기간 · 바탕보다 이긴 것만)")
    print(f"  {'조건':<60}{'앞 건수':>9}{'이김':>8}{'z':>7}{'20일 평균':>10}")
    for 라, zz, w, n, avg in 후보:
        print(f"  {라[:60]:<60}{n:>9,}{w:>7.1f}%{zz:>7.1f}{avg:>+9.2f}%")

    def _조건거름(라):
        부 = 라.split(" + ")
        m = 조건[부[0]]
        for p in 부[1:]:
            m &= 조건[p]
        return _마스크거름(m)

    _밑O = {"시총하한": _돈하한, "시총상한": _돈상한, "대금하한": 0.0, "거래량하한": 0, "회전율하한": 0.0,
            "상대갭": 99.0, "하루상한": 4, "비중": 0.20, "후보수": 10 ** 9, "최소": 1, "줄": "갭",
            "나눔": ((1.0, 10.0, 20),), "목표": 10.0, "최대보유": 20}
    팔기 = (("한 번에 +5%/10일", ((1.0, 5.0, 10),)),
            ("한 번에 +10%/20일", ((1.0, 10.0, 20),)),
            ("한 번에 +15%/40일", ((1.0, 15.0, 40),)),
            ("한 번에 +20%/60일", ((1.0, 20.0, 60),)),
            ("한 번에 +30%/90일", ((1.0, 30.0, 90),)),
            ("40:60 (+15/40 · +40/90)", ((0.4, 15.0, 40), (0.6, 40.0, 90))),
            ("50:50 (+10/30 · +30/90)", ((0.5, 10.0, 30), (0.5, 30.0, 90))),
            ("20일선 회복에 (최대 60일)", ((1.0, 999.0, 60, "20일선"),)),
            ("볼린저 0 회복에 (최대 60일)", ((1.0, 999.0, 60, "볼0"),)),
            ("+20%/60일 · 손절 -8%", ((1.0, 20.0, 60, "손절-8"),)),
            ("+30%/90일 · 손절 -12%", ((1.0, 30.0, 90, "손절-12"),)))
    _대표팔기 = (팔기[1], 팔기[3], 팔기[7])     # +10/20 · +20/60 · 20일선 회복 — 지금 규칙(40:60) 은 대표로 안 쓴다

    def _설정(거름, 갭, 자리, 팔, 줄="갭"):
        return dict(_밑O, 거름=거름, 상대갭=갭, 하루상한=자리, 나눔=팔[1],
                    목표=팔[1][0][1], 최대보유=max(z[2] for z in 팔[1]), 줄=줄)

    def _통과(r, 해):
        return bool(r) and r["끝"] > _시드 and r["낙"] >= _낙한 and r["산"] >= max(10, 2 * 해)

    def _순위(r, 해):
        return (1 if _통과(r, 해) else 0, r["산"] / 해 if r else 0, r["끝"] if r else 0)

    def _갭글(g):
        return "안 봄" if g > 50 else f"{g:g}%p"

    # ── ⑤ 돈 — 앞 기간 · 조건 × 사는 문턱 × 하루 자리 × 파는 규칙(대표 둘) ──
    print(f"\n  ⑤ 돈 (앞 {_시작[:4]}~{_앞끝년}) — 조건 × 사는 문턱(안 봄·-1·-2·-3.5·-5) × 하루 자리(2·4·6·10) × 파는 규칙 대표 둘", flush=True)
    print(f"  {'조건':<44}{'문턱':>7}{'자리':>5}  {'파는 규칙':<24}{'끝 자산':>14}{'낙폭':>8}{'1년 기회':>9}  통과")
    _갭들 = (99.0, -1.0, -2.0, -3.5, -5.0)
    _자리들 = (2, 4, 6, 10)
    if os.environ.get("OWN_FAST"):
        _갭들, _자리들 = (99.0, -2.0), (4,)
    최고 = []
    for 라, *_ in 후보:
        거 = _조건거름(라)
        best = None
        for g in _갭들:
            for 자 in _자리들:
                for 팔 in _대표팔기:
                    r = 시뮬(_설정(거, g, 자, 팔), 끝년=_앞끝년)
                    if not r:
                        continue
                    if best is None or _순위(r, _앞해) > _순위(best[0], _앞해):
                        best = (r, g, 자, 팔)
        if best:
            r, g, 자, 팔 = best
            최고.append((라, 거, g, 자, 팔, r))
            print(f"  {라[:44]:<44}{_갭글(g):>7}{자:>5}  {팔[0][:24]:<24}{r['끝']:>14,.0f}{r['낙']:>7.1f}%"
                  f"{r['산'] / _앞해:>8.0f}번  {'✅' if _통과(r, _앞해) else '❌'}", flush=True)
    최고.sort(key=lambda z: _순위(z[5], _앞해), reverse=True)

    # ── ⑥ 파는 규칙 전부 · 줄 세우는 순서 — 위 10개 ──
    print(f"\n  ⑥ 위 10개 — 파는 규칙 {len(팔기)}가지 × 사는 문턱 {len(_갭들)} × 줄 세우는 순서 2 를 **같이** (앞 기간)", flush=True)
    정해진 = []
    for 라, 거, g0, 자, 팔, r0 in 최고[:10]:
        best = None
        for 팔2 in 팔기:
            for g in _갭들:
                for 줄 in ("갭", "대금"):
                    r = 시뮬(_설정(거, g, 자, 팔2, 줄), 끝년=_앞끝년)
                    if r and (best is None or _순위(r, _앞해) > _순위(best[0], _앞해)):
                        best = (r, 팔2, 줄, g)
        r, 팔2, 줄, g = best
        정해진.append((라, 거, g, 자, 팔2, 줄, r))
        print(f"  {라[:44]:<44} 문턱 {_갭글(g)} · 자리 {자} · {팔2[0]} · 순서 {줄} → "
              f"{r['끝']:,.0f}원 · 낙폭 {r['낙']:.1f}% · 1년 {r['산'] / _앞해:.0f}번 {'✅' if _통과(r, _앞해) else '❌'}", flush=True)

    # ── ⑦ OR 로 묶기 — 앞 기간 · 1년 기회가 늘고 통과를 지키면 더한다 (최대 5) ──
    print("\n  ⑦ OR 로 묶기 (앞 기간) — 기회가 늘고 통과(돈↑·낙폭 한계 안)를 지키면 더한다", flush=True)
    _OR목록 = []
    _OR결과 = None
    if 정해진:
        _g0, _자0, _팔0, _줄0 = 정해진[0][2], 정해진[0][3], 정해진[0][4], 정해진[0][5]
        _남 = list(정해진)
        while _남 and len(_OR목록) < 5:
            _best = None
            for 후 in _남:
                _fs = [q[1] for q in _OR목록] + [후[1]]
                r = 시뮬(_설정(lambda x, fs=_fs: any(f(x) for f in fs), _g0, _자0, _팔0, _줄0), 끝년=_앞끝년)
                if not _통과(r, _앞해):
                    continue
                if _OR결과 is not None and r["산"] <= _OR결과["산"]:
                    continue
                if _best is None or (r["산"], r["끝"]) > (_best[0]["산"], _best[0]["끝"]):
                    _best = (r, 후)
            if _best is None:
                break
            _OR목록.append((_best[1][0], _best[1][1]))
            _OR결과 = _best[0]
            _남.remove(_best[1])
            print(f"     + {_best[1][0][:60]}  → {_OR결과['끝']:,.0f}원 · 낙폭 {_OR결과['낙']:.1f}% · "
                  f"1년 {_OR결과['산'] / _앞해:.0f}번 (증분으로 골랐다)", flush=True)
    if not _OR목록:
        print("     (묶을 것이 없다 — 앞 기간에서 통과한 조건이 없다)")

    # ── ⑧ 뒤 기간 확인 — 앞에서 정한 그대로 (다시 고르지 않는다) ──
    print(f"\n  ⑧ **뒤 기간 확인** ({_분할년}~) — 앞에서 정한 규칙을 **그대로** 돌린다 · 새 500만으로 시작", flush=True)
    print(f"  {'규칙':<48}{'앞 1년 기회':>11}{'앞 끝 자산':>14}{'앞 낙폭':>8} │{'뒤 끝 자산':>14}{'뒤 연':>8}{'뒤 낙폭':>8}{'뒤 1년 기회':>11}  판정")
    결과들 = []
    _바탕r = 시뮬(dict(_밑O, 거름=None, 상대갭=99.0, 하루상한=4), 시작년=_분할년)
    검 = [(f"[{라[:40]}]", _설정(거, g, 자, 팔2, 줄), r) for 라, 거, g, 자, 팔2, 줄, r in 정해진[:5]]
    if len(_OR목록) >= 2:
        _fsF = [q[1] for q in _OR목록]
        검.append((f"[OR {len(_OR목록)}개 묶음]",
                   _설정(lambda x, fs=_fsF: any(f(x) for f in fs), _g0, _자0, _팔0, _줄0), _OR결과))
    for 라, 설, r앞 in 검:
        r뒤 = 시뮬(설, 시작년=_분할년)
        ok = _통과(r뒤, _뒤해)
        결과들.append((라, r앞, r뒤, ok, 설))
        print(f"  {라[:48]:<48}{r앞['산'] / _앞해:>10.0f}번{r앞['끝']:>14,.0f}{r앞['낙']:>7.1f}% │"
              f"{(r뒤 or {}).get('끝', 0):>14,.0f}{(r뒤 or {}).get('연', 0):>7.1f}%{(r뒤 or {}).get('낙', 0):>7.1f}%"
              f"{((r뒤 or {}).get('산', 0)) / _뒤해:>10.0f}번  {'✅ 통과' if ok else '❌'}", flush=True)
    if _바탕r:
        print(f"  {'(참고) 이 무리 아무 날 · 문턱 안 봄 · 4자리':<48}{'':>10} {'':>14}{'':>8} │"
              f"{_바탕r['끝']:>14,.0f}{_바탕r['연']:>7.1f}%{_바탕r['낙']:>7.1f}%{_바탕r['산'] / _뒤해:>10.0f}번")

    print("\n  ⑨ **결론 (이 무리)** — 뒤 기간 통과한 것 · 1년 기회 많은 순")
    _통 = sorted([z for z in 결과들 if z[3]], key=lambda z: -z[2]["산"])
    if not _통:
        print("     통과한 규칙이 없다 — 이 무리에는 (이 재료·이 방식으로) 혼자 서는 규칙이 없다")
    for 라, r앞, r뒤, ok, 설 in _통:
        _팔글 = next((p[0] for p in 팔기 if p[1] == 설["나눔"]), str(설["나눔"]))
        print(f"     {라} · 사는 문턱 {_갭글(설['상대갭'])} · 하루 {설['하루상한']}종목 · 순서 {설['줄']} · 파는 규칙 {_팔글}")
        print(f"        뒤 {_분할년}~: {r뒤['끝']:,.0f}원 · 연 {r뒤['연']:.1f}% · 낙폭 {r뒤['낙']:.1f}% · 1년 {r뒤['산'] / _뒤해:.0f}번")
    print(f"\n  [대조] 무리 {_무리글} · 사건 {len(사건):,} · 쓴 재료 {len(쓸재료)} · 조건 {len(조건)} · 둘씩 {_쌍잰:,}쌍 · "
          f"돈으로 간 조건 {len(후보)} · ⑤ 시뮬 {len(후보) * len(_갭들) * len(_자리들) * len(_대표팔기):,}번 · 뒤 확인 {len(결과들)}줄 · 끝")
    print("=" * 122, flush=True)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs", os.environ.get("LAB_OUT") or "own_lab.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        try:
            rc = main()
        except BaseException:
            import traceback
            traceback.print_exc(file=sys.stdout)
            sys.stdout.flush()
            raise
        finally:
            sys.stdout = sys.__stdout__
    sys.exit(rc or 0)
