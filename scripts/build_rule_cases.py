#!/usr/bin/env python3
r"""
build_rule_cases.py — **규칙이 최근에 가리킨 것들을 뽑아 둔다** (2026-09-04 신설)

## 왜 만드나
```
브리핑에 「이 규칙이 최근에 가리킨 10개가 어떻게 됐나」를 표로 싣는다 (사례제).
   ① 확률을 설명할 필요가 없다 — 「10개 중 8개」는 그냥 읽힌다
   ② **검증 가능하다** — 종목명·날짜가 있어 직접 차트를 열어볼 수 있다
   ③ ⭐ **형식을 안 바꾸고 백테스트 -> 실전으로 넘어간다**
      예측 기록이 쌓이면 같은 자리에 실전 사례가 들어간다
   ④ 나쁜 사례가 표에 그냥 보인다
```
⚠️ 백테스트 전체를 도는 무거운 작업이라 **매일 돌리지 않는다.**
   한 달에 한 번(또는 규칙이 바뀔 때) 돌려서 캐시를 갱신한다.

## 확정 규칙 (98·101·104·108차)
```
잉여금비율 >=30% · 부채비율 <=80% · 흑자 · 시총 2,000억 아래
볼린저 -1.0σ · 20일 낙폭 -10% · 관리종목·SPAC 제외
상대갭 -3.5%p 아래 (**후보 40개 중앙갭** 대비 — 08:50에 그것만 보인다) · **시가 매수만** (장중 매수는 108차에서 기각)
절반 +15%·40일 / 절반 +40%·90일 지정가 · 손절 없음 · 자산 20%씩 · 하루 4종목
```

저장: `data/rule-cases.json`
쓰는 법:
    python scripts\build_rule_cases.py
    python scripts\build_rule_cases.py --개수 20
"""
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
# ⭐⭐⭐ **규칙은 `rule_def.py` 한 곳에만** (2026-09-11)
import rule_def as R  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "rule-cases.json")
_비용 = 0.26
# ⭐⭐ **2026-09-09 반영** — record_pick.py 와 같은 규칙이어야 성적이 맞는다
#    ① 시총 하한 500억 -> **300억** (158·165·167차)
#    ② **두 창 함께** — 20일 -10% 그리고 **120일 -20%** (165차 4관문 통과)
_시총하한 = R.시총하한억 * 1e8
# ⚠⚠ **두 창 함께를 꺼둔다** (2026-09-09).
#    165차 4관문은 통과했지만 **사는 횟수가 1년 10.3번 -> 5.9번**로 줄었다.
#    사용자 원칙 ④ 「매수 기회 포착이 먼저」에 어깋난다 — 되돌렸다
#    (승률은 85.0% -> 89.2% 로 올랐지만 기회가 43% 줄었다)
#    켜려면: NAK120=-20 을 준다
import os as _os
_낙120문턱 = float(_os.environ.get("NAK120") or 9999)
_시작 = "20160401"
# ⚠️ 2026-09-07 나눠팔기로 바뀜 — 여기서는 **앞 몫(+15%·40일)** 기준으로
#    사례를 만든다. 뒤 몫(+40%·90일)은 더 오래 걸려 최근 사례가 덜 쌓인다
_목표 = R.앞몫목표        # 앞 몫
_뒤목표 = R.뒷몫목표      # 뒤 몫 (124차 나눠팔기)
_뒤최대보유 = R.뒷몫기한
_최대보유 = R.앞몫기한
# ⭐ 147차 — 시장이 -10%↓ 빠진 날엔 낙폭 문턱을 -5%로 (2026-09-08)
# ⚠️⚠️ **2026-09-11** — 아래 둘은 147차판이고 **쓰이지도 않았다.**
#    실전(record_pick)의 Ⓗ 시장 규칙으로 갈아탄다
_시장문턱 = -10.0        # (안 쓴다 · 기록용)
_낙폭느슨 = -5.0         # (안 쓴다 · 기록용)

# ⭐⭐⭐ **실전과 같은 세 갈래** (2026-09-11 전수조사 ④).
#    전에는 성적표가 **「기존」 하나만** 재고 있었다 —
#    섹터는 파일에 한 글자도 없었고, 시장 규칙은 정의만 되고 안 쓰였다
_지수낙20문턱 = R.지수낙20문턱
_지수낙60문턱 = R.지수낙60문턱
_시장볼문턱 = R.시장볼문턱
_시장낙20문턱 = R.시장낙20문턱
_시장낙60문턱 = R.시장낙60문턱
# (창, 볼린저문턱, 창, 낙폭문턱) — `record_pick._섹터규칙` 과 **같은 값**
_섹규칙 = R.섹터규칙        # ⭐ rule_def 하나에서


def _사슬섹터표():
    try:
        from chain_map import 읽기 as _맵읽기
        난것 = {}
        for s, 들 in _맵읽기().items():
            for _, c in 들:
                if c and c not in 난것:
                    난것[c] = s
        return 난것
    except Exception:  # noqa: BLE001
        return {}


def _지수낙폭표():
    """{날짜: {"KOSPI": (낙20, 낙60), "KOSDAQ": (…)}}"""
    import glob as _g
    계 = {"KOSPI": [], "KOSDAQ": []}
    날들 = []
    for f in sorted(_g.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        날 = d.get("기준일") or os.path.basename(f)[:8]
        v = d.get("지수") or {}
        try:
            kp = float(str((v.get("코스피") or {}).get("종가")).replace(",", ""))
            kq = float(str((v.get("코스닥") or {}).get("종가")).replace(",", ""))
        except (TypeError, ValueError):
            continue
        날들.append(날)
        계["KOSPI"].append(kp)
        계["KOSDAQ"].append(kq)
    표 = {}
    for i, 날 in enumerate(날들):
        칸 = {}
        for k, xs in 계.items():
            n20 = ((xs[i] / xs[i - 20] - 1) * 100
                   if i >= 20 and xs[i - 20] > 0 else None)
            n60 = ((xs[i] / xs[i - 60] - 1) * 100
                   if i >= 60 and xs[i - 60] > 0 else None)
            칸[k] = (n20, n60)
        표[날] = 칸
    return 표
# ⚠ 환경변수로 바꿀 수 있게 한다 (2026-09-09 · 172차 후보수 시험)
# ⭐⭐ **자르지 않는다** (172차 · 2026-09-09 반영)
#    40개 → 1년 10.3번·85.0%  ·  자르지 않음 → **16.4번·87.2%**
# ⚠️⚠️ **99999 -> 40** (2026-09-11 전수조사 ⑬).
#    172차에서 「자르지 않는 쪽이 낫다」(16.4번·87.2% vs 40개 10.3번·85.0%)가
#    나와 여기만 99999 로 두었는데, **실전 `record_pick._후보수` 는 40** 이다.
#    성적표는 **실전이 하는 것**을 재야 한다. 「자르지 않으면 더 낫다」는
#    별개 과제로 남긴다 (그건 실전을 바꿔야 하는 이야기다)
_후보수 = int(_os.environ.get("HUBO") or R.후보수)
# ⭐⭐ **174차: 후보가 적은 날 어떻게 할까** (2026-09-09)
#    _적은수 미만이면 상대갭 기준을 바꾼다.
#    "건너뜀"(지금) · "시장중앙"(그날 전 종목 중앙갭) · "절대갭"(전날 종가 대비)
_적은수 = int(_os.environ.get("JEOKEUN") or 3)
# ⭐ 187차: 고르는 순서 (PICK)
_고르는법 = _os.environ.get("PICK") or "상대갭"
_고르기표 = {
    "상대갭": lambda z: z["상대갭"],                 # 지금 — 더 눌린 것부터
    "상대갭반대": lambda z: -z["상대갭"],             # 덜 눌린 것부터
    "시총작은": lambda z: z["시총억"],                # ⭐ 작은 것부터
    "시총큰": lambda z: -z["시총억"],
    "낙폭깊은": lambda z: z["20일낙폭"],
    "낙폭얕은": lambda z: -z["20일낙폭"],
    "무작위": lambda z: hash((z["날짜"], z["종목코드"])) & 0xFFFF,
}


def _고르기(z):
    return _고르기표.get(_고르는법, _고르기표["상대갭"])(z)
_적은날 = _os.environ.get("JEOKEUNWAY") or "건너뜀"
# ⚠ 「절대갭」은 문턱이 다르다. 상대갭 -3.5%p 는 「남들보다」지만
#    절대갭 -3.5% 는 「전날 종가보다」라 훨씬 드물다
_절대문턱 = float(_os.environ.get("GAPABS") or -3.5)
# ⭐ 171차: 볼린저 창을 **둘** 쓰면 (BOLL2=60 이면 「20일 **또는** 60일」)
#    ⚠️ 둘 다 요구하면(AND) 기회가 줄지만, **둘 중 하나면(OR) 늘어난다**
_볼창2 = int(_os.environ.get("BOLL2") or 0)
# ⭐ 171-2차: **AND** — 20일과 N일을 **둘 다** 넘어야 한다
#    (사용자: 「볼린저는 OR 가 아니라 **AND** 를 테스트해보기로 한 거 아니였어?」)
_볼창2A = int(_os.environ.get("BOLL2AND") or 0)
_볼문턱2 = float(_os.environ.get("BOLL2T") or -1.5)
# ⭐⭐ **갭 문턱과 하루 상한을 환경변수로** (181차 · 2026-09-09)
#    깔때기를 세보니 **갭 하나가 1년 2,361개를 47개로 줄인다**(2.0%).
#    「1년 16.4번밖에 못 산다」의 진짜 원인이 여기였다
_섹터맵 = _사슬섹터표()
_지수표 = _지수낙폭표()

확정 = {"갭": float(_os.environ.get("GAP") or R.상대갭문턱),
        "볼": R.볼린저문턱, "낙": R.낙폭20문턱, "시총": R.시총상한억 * 1e8,
        "종목수": int(_os.environ.get("MAXBUY") or 4)}

# ⭐⭐⭐ **177차: 무리(그룹)마다 다른 문턱** (2026-09-09)
#    사용자: 「꼭 한 가지 규칙으로만 적용하는 게 아니라
#            **규모별/섹터별로 규칙을 다양하게** 적용해도 된다」
#    169차가 「이길 확률」로는 쟀지만 **실제 사는 횟수**로는 안 쟀다
#
#    GROUP=규모   -> 소형/중형/대형마다 볼린저·낙폭 문턱을 달리
#    GROUP=업종σ  -> 그 업종의 낙폭 분포로 **표준화** (169차 F절)
#                   「-10%」가 아니라 「그 업종 기준 -1.5σ」로 본다
_무리 = _os.environ.get("GROUP") or ""
# 규모별 문턱: (시총하한억, 시총상한억, 볼문턱, 낙문턱)
_규모표 = {
    "기본": ((300, 700, -1.0, -10.0), (700, 1500, -1.0, -10.0),
             (1500, 2000, -1.0, -10.0)),
    # 소형은 원래 많이 움직인다 -> 더 깊게 요구, 대형은 덜 움직인다 -> 느슨하게
    "움직임맞춤": ((300, 700, -1.0, -15.0), (700, 1500, -1.0, -10.0),
                   (1500, 2000, -1.0, -7.0)),
    "반대": ((300, 700, -1.0, -7.0), (700, 1500, -1.0, -10.0),
             (1500, 2000, -1.0, -15.0)),
    "소형만": ((300, 700, -1.0, -10.0),),
    "중대형만": ((700, 2000, -1.0, -10.0),),
}
_규모안 = _os.environ.get("GROUPWAY") or "기본"
_업종시그마 = float(_os.environ.get("SECSIG") or -1.5)


def main():
    개수 = 30
    if "--개수" in sys.argv:
        개수 = int(sys.argv[sys.argv.index("--개수") + 1])

    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)   # ⚠️ 상장폐지를 손실로 센다
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — 상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
    기본, 재무 = O._기본(), 연간재무()
    # ⭐ 177차: 업종 (industry.json — 표준산업분류)
    _업종 = {}
    _ip = os.path.join(O._DATA, "industry.json")
    if os.path.exists(_ip):
        for _c, _v in json.load(io.open(_ip, encoding="utf-8-sig")).items():
            if isinstance(_v, dict) and _v.get("업종명"):
                _업종[_c] = str(_v["업종명"])
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종, 원시 = {}, {}, {}, {}, {}
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
                if min(종c, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종c, 고 / 종c, 거)
            원시.setdefault(d8, {})[c] = 시
            pv = 앞종.get(c)
            앞종[c] = 종c
            if pv and pv > 0:
                g = (시 / pv - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))

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

    # ⭐ 177차: 업종마다 **평소 낙폭이 얼마나 되나**를 먼저 낸다 (169차 F절)
    #    ⚠️ 반도체가 -10% 빠진 것과 음식료가 -10% 빠진 것은 같은 일이 아니다
    _업통계 = {}
    if _무리 == "업종σ":
        _모음 = {}
        for d1 in 날[260:]:
            for code, v in 주가[d1].items():
                업 = _업종.get(code)
                kk = (자리.get(code) or {}).get(d1)
                if not 업 or kk is None or kk < 250:
                    continue
                sq = 종계[code]
                if sq[kk - 20] <= 0:
                    continue
                _모음.setdefault(업, []).append((v[0] / sq[kk - 20] - 1) * 100)
        for 업, vv in _모음.items():
            if len(vv) < 500:
                continue
            m3 = sum(vv) / len(vv)
            s3 = (sum((z - m3) ** 2 for z in vv) / len(vv)) ** 0.5 or 1e-9
            _업통계[업] = (m3, s3)
        print(f"  업종 {len(_업통계)}개의 평소 낙폭을 냈다", flush=True)

    사건 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 1 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < _시총하한 or 대금 < O._MIN_AMT or 시총 >= 확정["시총"]:
                continue
            g = 하루갭.get(code)
            # ⚠️⚠️ **여기서 갭을 걸지 않는다** (2026-09-07 고침).
            #    08:00에는 갭이 없다. 후보 40개를 먼저 고르고,
            #    08:50에 **그 40개 안에서** 중앙갭을 내야 실전과 같다
            if g is None:
                continue
            fm = 재무값(code, d1)
            if not (fm and fm.get("잉여금비율", -9e9) >= 30
                    and fm.get("부채비율", 9e9) <= 80 and fm.get("흑자") == 1.0):
                continue
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
            볼20 = (c1 - s20) / (2 * sd)
            볼통과 = 볼20 <= 확정["볼"]
            # ⭐ 171차: 「20일 **또는** N일」 — 둘 중 하나만 넘으면 후보다.
            #    둘 다 요구하면(AND) 기회가 줄고, 둘 중 하나면(OR) **늘어난다**
            볼N = None
            # ⭐ AND — 둘 다 넘어야 한다 (기회를 깎는 쪽)
            if _볼창2A:
                if kk < _볼창2A:
                    continue
                mA = st.mean(sq[kk - _볼창2A + 1:kk + 1])
                sdA = st.pstdev(sq[kk - _볼창2A + 1:kk + 1]) or 1e-9
                if (c1 - mA) / (2 * sdA) > _볼문턱2:
                    continue
            if _볼창2 and kk >= _볼창2:
                mN = st.mean(sq[kk - _볼창2 + 1:kk + 1])
                sdN = st.pstdev(sq[kk - _볼창2 + 1:kk + 1]) or 1e-9
                볼N = (c1 - mN) / (2 * sdN)
                볼통과 = 볼통과 or (볼N <= _볼문턱2)
            # ⚠️ 기본 모드에서는 **아래 세 갈래 안에서** 볼통과를 본다.
            #    여기서 먼저 걸러 버리면 섹터·시장 갈래가 죽는다
            if sq[kk - 20] <= 0 or (_무리 and not 볼통과):
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            # ⭐⭐⭐ **177차: 무리마다 다른 문턱** (2026-09-09)
            if _무리 == "규모":
                시총억2 = 시총 / 1e8
                맞 = None
                for lo2, hi2, 볼2, 낙2 in _규모표[_규모안]:
                    if lo2 <= 시총억2 < hi2:
                        맞 = (볼2, 낙2)
                        break
                if 맞 is None:      # 그 무리에 안 들면 안 산다
                    continue
                if 볼20 > 맞[0] or 낙 > 맞[1]:
                    continue
            elif _무리 == "업종σ":
                # 169차 F절 — 「그 업종 기준으로 몇 시그마 빠졌나」.
                # ⚠️ 문턱을 고르지 않으므로 **과적합이 안 생긴다**
                업 = _업종.get(code)
                통 = _업통계.get(업) if 업 else None
                if not 통:
                    continue
                if (낙 - 통[0]) / 통[1] > _업종시그마:
                    continue
            else:
                # ⭐⭐⭐ **실전과 같은 세 갈래** (2026-09-11 전수조사 ④)
                낙60 = ((c1 / sq[kk - 60] - 1) * 100
                        if kk >= 60 and sq[kk - 60] > 0 else None)
                _기존맞나 = bool(볼통과 and 낙 <= 확정["낙"])
                # 섹터 — 한 규칙 **안에서는 AND**(볼린저 그리고 낙폭)
                _섹맞나 = False
                _규 = _섹규칙.get(_섹터맵.get(code))
                if _규 and kk >= max(_규[0], _규[2]):
                    bw, bt, nw, nt = _규
                    _mb = st.mean(sq[kk - bw + 1:kk + 1])
                    _sb = st.pstdev(sq[kk - bw + 1:kk + 1]) or 1e-9
                    _볼s = (c1 - _mb) / (2 * _sb)
                    _낙s = ((c1 / sq[kk - nw] - 1) * 100
                            if sq[kk - nw] > 0 else None)
                    _섹맞나 = bool(_낙s is not None
                                   and _볼s <= bt and _낙s <= nt)
                # 시장 — 지수가 눌린 날, 그 종목이 조금만 빠져 있어도
                _키 = ("KOSDAQ" if ("닥" in 부 or "KOSDAQ" in 부
                                    or "닥" in str(bb.get("시장") or ""))
                       else "KOSPI")
                _지 = (_지수표.get(d1) or {}).get(_키) or (None, None)
                _때맞나 = ((_지[0] is not None and _지[0] <= _지수낙20문턱)
                           or (_지[1] is not None and _지[1] <= _지수낙60문턱))
                _빠졌나 = (볼20 <= _시장볼문턱 or 낙 <= _시장낙20문턱
                           or (낙60 is not None and 낙60 <= _시장낙60문턱))
                if not (_기존맞나 or _섹맞나 or (_때맞나 and _빠졌나)):
                    continue
            # ⭐⭐ **두 창 함께** (165차 4관문 통과 · 2026-09-09 반영)
            #    20일만 빠진 것은 잠깐 흔들린 것일 수 있다.
            #    **120일도 빠져 있어야** 진짜 눌린 것이다
            낙120 = ((c1 / sq[kk - 120] - 1) * 100
                     if kk >= 120 and sq[kk - 120] > 0 else None)
            if 낙120 is None or 낙120 > _낙120문턱:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            if not b0 or not v0 or not o0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            # ⚠️⚠️ **두 몫을 합쳐 낸다** (2026-09-08 고침).
            #    전에는 앞 몫(+15%·40일)만 계산해서 화면의 최근 10건이
            #    **전부 +14.7%** 로 똑같이 나왔다 — 규칙의 절반만 보여준 것이다
            def _한몫(목표, 최대):
                """(수익%, 며칠, 끝났나)"""
                for h2 in range(0, 최대 + 1):
                    j2 = i + 1 + h2
                    if j2 >= len(날):
                        return None, None, False
                    vv2 = 주가[날[j2]].get(code)
                    b3 = (비.get(날[j2]) or {}).get(code)
                    if not vv2 or not b3:
                        break
                    if vv2[0] * b3[1] >= 매수 * (1 + 목표 / 100):
                        return 목표 - _비용, max(1, h2), True
                j2 = i + 1 + 최대
                if j2 >= len(날):
                    return None, None, False
                끝2 = 주가[날[j2]].get(code)
                # ⚠️⚠️ **상장폐지를 손실로 센다** (2026-09-08 고침)
                if not 끝2 and code in _사라짐:
                    return O.폐지손실 - _비용, 최대, True
                if not 끝2:
                    return None, None, True
                return (끝2[0] / 매수 - 1) * 100 - _비용, 최대, True

            앞r, 앞d, 앞끝 = _한몫(_목표, _최대보유)
            뒤r, 뒤d, 뒤끝 = _한몫(_뒤목표, _뒤최대보유)
            끝났나 = bool(앞끝 and 뒤끝)
            if 앞r is None or 뒤r is None:
                결과, 며칠 = None, None
            else:
                # ⚠️⚠️ **비율을 손으로 적지 않는다** (2026-09-14 저녁).
                #    `0.5 * 앞r + 0.5 * 뒤r` 로 박혀 있어 rule_def.몫들 을 40:60 으로
                #    바꿔도 성적표는 50:50 그대로였다 — 「가장 좋았던 셋」이 +27.24% 로
                #    안 움직여서 잡았다. rule_align 이 이 꼴을 되살아남으로 잡는다
                결과 = R.몫들[0][0] * 앞r + R.몫들[1][0] * 뒤r
                며칠 = max(앞d or 0, 뒤d or 0)
            사건.append({
                "날짜": f"{다음[:4]}-{다음[4:6]}-{다음[6:]}",
                "종목코드": code, "이름": bb.get("이름", ""),
                "매수가": round(o0), "_갭": g, "_시장갭": 시갭,
                "상대갭": None,   # 아래에서 후보중앙갭으로 다시 낸다
                "20일낙폭": round(낙, 1), "시총억": round(시총 / 1e8),
                "결과": (round(결과, 2) if 결과 is not None else None),
                "며칠": 며칠, "끝났나": 끝났나,
                # 「도달」 = **앞 몫이 +15%에 닿았나** (뒤 몫은 90일까지 간다)
                "도달": bool(앞r is not None
                             and 앞r > _목표 - _비용 - 1e-9),
            })

    # ⚠️⚠️ **실전 절차 그대로** (2026-09-07 고침)
    #    1) 08:00 — 20일 낙폭 깊은 순 **40개**를 브리핑에 싣는다
    #    2) 08:50 — **그 40개 예상체결가**의 중앙값을 낸다 (시장 전체가 아니다)
    #    3) 09:00 — 중앙값보다 3.5%p 더 빠진 것만 최대 4종목
    #    전에는 2)를 **시장 전체 중앙갭**으로 해서, 브리핑에 나가는 성적이
    #    **실행할 수 없는 규칙**의 것이었다
    묶 = {}
    for x in 사건:
        묶.setdefault(x["날짜"], []).append(x)
    산것 = []
    for d, 칸 in 묶.items():
        앞 = sorted(칸, key=lambda z: z["20일낙폭"])[:_후보수]
        if not 앞:
            continue
        # ⚠️⚠️⚠️ **후보가 적은 날은 이 기준이 작동하지 않았다** (173차 · 2026-09-09).
        #    상대갭 = 그 종목 갭 − **후보들 갭의 중앙값**
        #    후보 1개 -> 중앙값 = 자기 자신 -> 상대갭 = **언제나 0** -> 절대 못 산다
        #    실측: 후보 1개인 날이 **17.6%**(1년 43일), 3개 이하가 66.4%
        #    전에는 `if len(앞) < 3: continue` 로 **아예 건너뛰었다**
        #
        #    ⇒ 174차: 후보가 _적은수 미만이면 **다른 기준**을 쓴다
        #       (사용자: 「후보가 1개일 때는 **다른 기준으로 적용**해야 하는 거 아니야?」)
        if len(앞) >= _적은수:
            중 = st.median([z["_갭"] for z in 앞])
            기준이름 = "후보중앙"
        elif _적은날 == "건너뜀":
            continue
        elif _적은날 == "시장중앙":
            중 = 앞[0]["_시장갭"]          # 그날 **전 종목** 갭 중앙값
            기준이름 = "시장중앙"
        else:                              # "절대갭" — 기준을 0으로 (전날 종가 대비)
            #    ⚠ 문턱을 따로 쓴다 — 상대갭과 뜻이 다르다
            중 = 0.0 - (_절대문턱 - 확정["갭"])
            기준이름 = "절대갭"
        골 = []
        for z in 앞:
            z["상대갭"] = round(z["_갭"] - 중, 2)
            z["갭기준"] = 기준이름
            if z["상대갭"] <= 확정["갭"]:
                골.append(z)
        # ⭐⭐ **187차: 4종목을 무엇으로 고를까** (2026-09-09)
        #    182차에서 **하루 상한을 풀수록 승률이 올랐다** —
        #    지금 「상대갭 깊은 순」으로 고르는 게 **틀렸다**는 뜻이다.
        #    184·177·158차는 **작은 종목이 잘 오른다**고 가리킨다
        산것.extend(sorted(골, key=_고르기)[:확정["종목수"]])
    for x in 산것:
        x.pop("_갭", None)
        x.pop("_시장갭", None)
    산것.sort(key=lambda z: z["날짜"])
    끝난 = [x for x in 산것 if x["끝났나"] and x["결과"] is not None]

    도 = sum(1 for x in 끝난 if x["도달"])
    플 = sum(1 for x in 끝난 if x["결과"] > 0)
    묶2 = {}
    for x in 끝난:
        묶2.setdefault(x["날짜"][:4], []).append(x["결과"])
    나온 = {
        "만든날": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # ⚠️⚠️ **손으로 적지 않는다** (2026-09-11 전수조사 ①).
        #    전에는 "+20% 지정가 · 최대 D+40" 이라고 박혀 있었는데
        #    실제 계산은 **반 +15%(40일) · 반 +40%(90일)** 이었다.
        #    ⇒ 위의 상수에서 **만들어** 쓴다. 계산이 바뀌면 문구도 따라온다
        "규칙": R.한줄(),
        "기간": f"{산것[0]['날짜']} ~ {산것[-1]['날짜']}" if 산것 else "",
        "전체건수": len(끝난),
        "도달": 도, "도달률": round(도 / max(1, len(끝난)) * 100, 1),
        "흑자": 플, "승률": round(플 / max(1, len(끝난)) * 100, 1),
        "평균": round(st.mean([x["결과"] for x in 끝난]), 2) if 끝난 else 0,
        "평균보유": round(st.mean([x["며칠"] for x in 끝난]), 1) if 끝난 else 0,
        "가장나쁨": round(min(x["결과"] for x in 끝난), 2) if 끝난 else 0,
        "해수": len(묶2),
        "최근": 끝난[-개수:][::-1],           # 최신이 위
        # 최근 10건이 우연히 다 좋으면 100%로 읽힌다.
        # 나쁜 사례를 반드시 같이 보여주려고 따로 담는다
        "최악": sorted(끝난, key=lambda z: z["결과"])[:5],
        # ⭐ 퀀트 4장 「가장 좋았던 셋」 (2026-09-14 · QUANT-FINAL 6절 1)
        #    ⚠️ 동률이 많다 — 반 +15%·반 +40% 가 다 닿으면 누구나 +27.24% 다.
        #       같은 수익률이면 **빨리 낸 쪽**(며칠 적은 순)을 앞에 둔다
        "최고": sorted(끝난, key=lambda z: (-z["결과"], z["며칠"] or 999))[:3],
        # ⭐ 「손실 거래 평균」 (QUANT-FINAL 6절 2) — 손실이 없으면 화면이 비운다.
        #    지어내지 않는다: 건수가 0이면 None
        "손실건수": sum(1 for x in 끝난 if x["결과"] < 0),
        "손실평균": (round(st.mean([x["결과"] for x in 끝난 if x["결과"] < 0]), 2)
                    if any(x["결과"] < 0 for x in 끝난) else None),
        "아직진행중": [x for x in 산것 if not x["끝났나"]],
    }
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(나온, ensure_ascii=False, indent=1))
    print(f"  ✅ {OUT}")
    print(f"     전체 {len(끝난)}건 · {나온['기간']} · {나온['해수']}개 해")
    print(f"     도달률 {나온['도달률']}% · 승률 {나온['승률']}% · "
          f"평균 {나온['평균']:+.2f}% · 평균보유 {나온['평균보유']}일")
    print(f"     가장 나쁨 {나온['가장나쁨']:+.2f}%")
    print(f"\n  ── 최근 10건 ──")
    print(f"    {'날짜':<12}{'종목':<14}{'매수가':>9}{'결과':>9}{'보유':>7}")
    for x in 나온["최근"][:10]:
        print(f"    {x['날짜']:<12}{x['이름'][:13]:<14}{x['매수가']:>9,}"
              f"{x['결과']:>+8.1f}%{x['며칠']:>6}일")
    if 나온["아직진행중"]:
        print(f"\n    (아직 안 끝난 것 {len(나온['아직진행중'])}건은 뺐다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
