#!/usr/bin/env python3
r"""
gate7_lab.py — **193차 · 해외 신호를 4관문에** (2026-09-09 신설)

## 사용자 말 (그대로)
```
「한국은 **수출 위주 국가**라 **해외 수주나 해외 소식**에 영향을 받을 것 같아」
```

## 192차에서 나온 것 — 여기서 판정한다
```
지금 규칙(192차 잣대 55.7%) 에 전날까지의 해외를 얹으면
  **원달러 5일 +3%↑ (원화 급락)**   1년  323개  **80.4%**  +21.66%
  S&P500 5일 -3%↓                1년 2,037개   65.2%   +8.30%
  구리 5일 -3%↓                   1년 2,284개   63.1%   +7.71%
  반도체 ETF 5일 -3%↓              1년 3,378개   62.0%   +6.25%
  ---
  S&P500 5일 **+3%↑**            1년  162개  **38.8%**  -2.28%   <- 오른 뒤엔 최악
  **원달러 5일 -3%↓ (원화 급등)**     1년   27개  **37.4%**  -1.88%
```
⚠️⚠️ **192차는 재무 조건이 빠진 잣대였다.** 여기서는 재무까지 넣고 다시 잰다

## ⚠️ 미리보기 막기
```
한국 D일 09:00 에 산다 -> 해외는 **D보다 앞선 마지막 값**만 쓴다.
대만·일본을 D일로 쓰면 「오늘 대만이 오른 걸 알고 오늘 아침에 산다」가 된다
```

## 4관문 — A·B·C 를 다 지나야 통과
```
A 앞뒤 분할 (네 구간 같은 방향)  ·  B 해마다 승패  ·  C 무작위 대조 200번
D 오차 ±0.3/0.5/1.0%p         ·  E 문턱 자리
```
"""
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
# ⭐ 악재말은 `newmat` 것을 **그대로 쓴다** (2026-09-15) —
#    매수 쪽(combo4)과 **같은 잣대**여야 견줄 수 있다
import newmat as _NM  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_비용 = 0.26
# ⭐⭐ 2026-09-29 — **사는 값.** "시가"(지금 · 09:00 동시호가) 또는 "종가"(그날 장 마감).
#    규칙 전체가 「시가에 산다」 위에 서 있는데 한 번도 안 흔들었다.
#    ⚠️ 안 주면 "시가" — 지금과 한 글자도 안 달라진다. `결과()` 캐시 열쇠에 들어간다
_살때 = "시가"
# ⭐⭐ 2026-09-29 — **안 쓴 현금 이자 (연)**. 손으로 박힌 0.025 를 손잡이로 뺐다.
#    ⚠️ 안 주면 0.025 — 지금과 한 글자도 안 달라진다
_이자 = 0.025
_시작 = "20160401"
_시드 = 5_000_000.0
_후보수 = R.후보수
# ⚠️ 237차 (2026-09-10) — 사건 크기 상한. 기본 3,000억.
#    `SIZE_HI=999999` 로 열면 대형주(1조↑)까지 사건에 든다.
#    230-A 에서 대형주가 **가장 좋았다**(Ⓗ AND 빠짐 64.5% · +16.9%p)
_크기상한 = float(os.environ.get("SIZE_HI") or 3000)
# ⭐ 2026-09-22 — 재무·대금 문까지 그 칸 자료로 내는 판 (사용자가 잡아낸 구멍)
#    OPENFIN=1 이면 소형에서 정한 재무 문턱·대금 하한을 **안 건다.**
#    사건이 확 늘어 램이 터지므로(네 번 죽었다) **한 판에 한 띠만** 본다
_문열기 = bool(os.environ.get("OPENFIN"))
_크기하한 = float(os.environ.get("SIZE_LO") or 100) * 1e8
_크기웃한 = float(os.environ.get("SIZE_HI2") or 9e12) * 1e8
_열대금 = float(os.environ.get("OPENAMT") or 0.2) * 1e8
# ⭐⭐ **규칙 안의 크기 상한** (2026-09-14). 위 `_크기상한` 은 사건 그물만 연다.
#    `크기통과()` 와 `_바탕c["시총상한"]` 은 R.시총상한억(2,000) 을 직접 읽어서
#    SIZE_HI=999999 를 줘도 **큰 종목이 규칙에 든 적이 없었다** (I2 가 H2 와 동일).
#    안 주면 R.시총상한억 그대로 — 기준선은 안 움직인다
# ⚠️⚠️ 2026-09-16 pairs6: SIZE_HI 가 **후보 풀**과 **규칙 상한**을 같이 올려, 「지금 규칙」 견줌이 크기 무제한 전체(−61.9%)가 됐다.
#    지금 실전은 「소형 2,000억 + 섹터규칙만 큰 회사」다. 풀은 SIZE_HI 로 넓히되 규칙 상한은 R 그대로 — 올리려면 RULE_HI
_규칙크기상한 = float(os.environ.get("RULE_HI") or R.시총상한억)

# ⭐⭐ **기준선을 환경으로 바꾼다** (2026-09-11).
#    같은 절 26 개를 **다른 바탕**에서 돌려 견준다. 안 주면 지금 그대로다
_밑갭 = os.environ.get("BASE_GAP") or "후보+실전표본"
_밑상대갭 = float(os.environ.get("BASE_RELGAP") or R.상대갭문턱)
_밑후보수 = int(os.environ.get("BASE_PICKS") or R.후보수)
# ⭐⭐ **기준선 규칙 자체**를 바꾼다 (2026-09-14 밤). 안 주면 Ⓗ — 지나간 판은 그대로.
#    Ⓖ = 기존 OR 섹터 OR 시낙7 OR **120일선 −8%↓** (Ⓗ 는 지수 60일 ≤−10%)
#    H2 자본 시뮬: Ⓗ 1.59억·낙폭 −4.5% / Ⓖ 1.52억·낙폭 **−3.6%** — 돈 4%↓ 낙폭 0.9%p↑
_밑규칙 = (os.environ.get("BASE_RULE") or "H").strip().upper()
_대조번 = int(os.environ.get("CTRL_N") or 20)     # 264차 무작위 대조
# ⭐⭐⭐ **ONLY — 옛 절을 건너뛴다** (2026-09-21)
#    한 판 68분 중 Q-19 는 20분이고 48분은 **이미 결론 난 옛 절**이 먹는다.
#    그 옛 절들은 막개에 아홉 곳 걸린다(전부 소형 바탕) — 고치기보다 **안 돌리는 게** 맞다.
#    ONLY=Q19 면 Q-19 와 그 앞의 **필수 준비**만 돈다.
#    ⚠️ 안 주면 지금과 똑같이 전부 돈다 — 기존 판은 하나도 안 바뀐다
_ONLY = (os.environ.get("ONLY") or "").strip().upper()


def _건너뛰나(이름):
    """ONLY 가 켜져 있고 이 절이 그 대상이 아니면 True"""
    return bool(_ONLY) and _ONLY not in str(이름).upper()


# ══════════════════════════════════════════════════════════════════
#  ⭐ **때 지도** — 어느 절이 시간을 먹나 (2026-09-28)
#
#  판 하나가 47분인데 ONLY 로 고른 절은 5분이다. 나머지 42분을 누가 먹는지
#  알아야 문 없는 옛 절 64개 중 **굵은 것부터** 안전하게 막을 수 있다.
#
#  절 안에는 한 글자도 안 넣는다 — 딴 실뜨기가 0.5초마다 「지금 몇 번째 줄인가」를
#  엿보고, 그 줄 위쪽의 가장 가까운 절 머리로 센다. 값은 안 건드린다.
#
#  ⚠️ TIMEMAP=1 일 때만 돈다. 안 주면 지금과 완전히 똑같이 돈다.
# ══════════════════════════════════════════════════════════════════
_때지도 = {}


def _때지도_켜기():
    import bisect as _bi
    import re as _re
    import threading as _th
    import time as _tm

    _나 = os.path.abspath(__file__)
    _머리 = []
    try:
        _줄들원 = io.open(_나, encoding="utf-8-sig").read().splitlines()
        for _i, _줄 in enumerate(_줄들원, 1):
            _m = _re.match(r"\s*#\s*══+\s*(.*)", _줄)
            if not _m:
                continue
            _이름 = _m.group(1).strip().strip("═").strip()
            if not _이름 and _i < len(_줄들원):
                # ⭐ 2026-09-28 — `# ════` 만 있고 **다음 줄**에 이름이 오는 꼴
                _다 = _줄들원[_i].strip()
                if _다.startswith("#"):
                    _이름 = _다.lstrip("#").strip()
            if _이름:
                _머리.append((_i, _이름[:58]))
    except OSError:
        return
    if not _머리:
        return
    _줄들 = [_z[0] for _z in _머리]

    def _엿보기():
        _나실 = _th.get_ident()          # ⭐ 2026-09-28 — **제 실은 안 센다** (두 배로 찍혔다)
        while True:
            _tm.sleep(0.5)
            try:
                for _tid, _f in list(sys._current_frames().items()):
                    if _tid == _나실:
                        continue
                    # ⭐⭐ 2026-09-28 — **가장 바깥 main() 틀**을 집는다.
                    #    전에는 가장 안쪽을 집어서, 어느 절이 시뮬을 부르면
                    #    그 안에서 불리는 `재무통과`·`문통과`·`_H` 의 **정의 자리**
                    #    (「도전자들」 절)로 시간이 몰렸다. 18분으로 찍혔는데
                    #    거긴 함수를 정의만 하는 자리다 — 18분이 걸릴 수가 없다
                    _줄번 = None
                    _g = _f
                    while _g is not None:
                        if (_g.f_code.co_filename == _나
                                and _g.f_code.co_name == "main"):
                            _줄번 = _g.f_lineno
                        _g = _g.f_back
                    if _줄번 is None:
                        continue
                    _k = _bi.bisect_right(_줄들, _줄번) - 1
                    _키 = _머리[_k][1] if _k >= 0 else "(절 앞)"
                    _때지도[_키] = _때지도.get(_키, 0) + 1
            except Exception:  # noqa: BLE001
                pass          # ⚠️ 재는 장치가 판을 죽이면 안 된다

    _th.Thread(target=_엿보기, daemon=True).start()
    print("  ⏱ 때 지도 켬 — 0.5초마다 엿본다", flush=True)


def _때지도_찍기():
    if not _때지도:
        return
    _총 = sum(_때지도.values())
    print("\n" + "=" * 100)
    print(f"  ⏱ 때 지도 — 절마다 몇 분을 먹었나 (엿본 횟수 {_총:,} · 0.5초마다)")
    print(f"     찍힌 합 {_총 * 0.5 / 60:.1f}분 — **판이 실제로 돈 시간과 비슷해야 맞는 값이다**")
    print("=" * 100)
    print(f"     {'절':<62}{'분':>8}{'몫':>8}")
    for _이름, _n in sorted(_때지도.items(), key=lambda _z: -_z[1])[:35]:
        print(f"     {_이름:<62}{_n * 0.5 / 60:>8.1f}{_n / _총 * 100:>7.0f}%")
    print("=" * 100, flush=True)


if os.environ.get("TIMEMAP"):
    _때지도_켜기()


def _밑몫읽기():
    r"""BASE_SELL 을 나눔 꼴로 바꾼다. 안 주면 None (= rule_def 그대로)

    꼴: "0.3,15,40 / 0.7,40,90"   ("비율,목표%,기한일" 을 / 로 이어 붙인다)
    """
    _s = (os.environ.get("BASE_SELL") or "").strip()
    if not _s:
        return None
    벌 = []
    for _한 in _s.split("/"):
        _조각 = [z.strip() for z in _한.split(",") if z.strip()]
        if len(_조각) != 3:
            raise SystemExit(f"BASE_SELL 꼴이 틀렸다: {_s!r}")
        벌.append((float(_조각[0]), float(_조각[1]), int(_조각[2])))
    _합 = sum(z[0] for z in 벌)
    if abs(_합 - 1.0) > 0.01:
        raise SystemExit(f"BASE_SELL 비율 합이 1 이 아니다: {_합}")
    return tuple(벌)


_밑몫 = _밑몫읽기()


# {종목코드: 섹터이름} — 실전 `record_pick._섹터표()` 와 같은 자료
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


_사슬섹터 = _사슬섹터표()
확정 = {"잉여금": R.잉여금하한, "부채": R.부채상한,
        "흑자필수": R.흑자필수, "상대갭": R.상대갭문턱,
        "볼린저": R.볼린저문턱, "낙폭20": R.낙폭20문턱,
        "목표": 20, "최대보유": R.앞몫기한,
        "비중": 0.20, "하루상한": (lambda 골: R.오늘최대종목(
                  next((z.get("시장낙폭") for z in 골
                        if z.get("시장낙폭") is not None), None))),
              # ⭐ ㉥ (2026-09-21 반영) — 그날 상한을 rule_def 가 정한다.
              #    맨 위 후보의 시장 지수를 본다 (실전 quant_cards 와 같은 자리)
        "시총하한": 500, "시총상한": 2000, "대금하한": 1.0, "거래량하한": 0,
        "회전율하한": 0.0}


# ══ ⭐ 해외 (2026-09-09 193차에서 더한 것) ══
#    ⚠️ 「필라반도체」는 751일(3년)뿐이라 안 쓴다. SOXX 6,325일로 대신한다
_해외 = (("SOXX", "반도체ETF"), ("SPY", "S&P500"), ("HG=F", "구리"),
         ("KRW=X", "원달러"), ("IDX_VIX", "공포지수"), ("TSM", "TSMC"))


def _해외표(한국날):
    r"""{이름: {한국날짜: (1일%, 5일%, 20일%)}}

    ⚠️⚠️ **그 날짜보다 앞선 마지막 해외 값**만 쓴다 — 같은 날을 쓰면 미리보기다
    """
    import glob as _g
    _D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "yahoo")
    난것 = {}
    for 파, 라 in _해외:
        p = os.path.join(_D, f"{파}.json")
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            continue
        z = {k: float(v) for k, v in (d.get("종가") or {}).items()
             if v not in (None, "")}
        if len(z) < 1000:
            continue
        해날 = sorted(z)
        표, j = {}, 0
        for d8 in 한국날:
            while j < len(해날) and 해날[j] < d8:
                j += 1
            k = j - 1                     # ⚠️ **앞선** 마지막 것
            if k < 20:
                continue
            v = z[해날[k]]
            표[d8] = ((v / z[해날[k - 1]] - 1) * 100,
                      (v / z[해날[k - 5]] - 1) * 100,
                      (v / z[해날[k - 20]] - 1) * 100)
        난것[라] = 표
    return 난것


def main():
    import time as _t시
    _시작시각 = _t시.time()
    # ⭐⭐ krx-daily 를 **한 번만** 파싱한다 (2026-09-09 · 114초 -> 캐시 11초)
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = sorted(주가)
    _사라짐 = O.사라진종목(주가, 날)
    print(f"  중간에 사라진 종목 {len(_사라짐):,}개 — "
          f"상장폐지는 {O.폐지손실:.0f}% 손실로 센다", flush=True)
    # ⭐ ㉠-3 (2026-09-15) — **왜 사라졌나**를 가른다. `VANISH_KIND=1` 일 때만.
    #    BIG판 2023 낙폭 −79.1%: 2023 에 사라진 2,000억↑ 12개 중 8개가 사라지기 직전
    #    규칙에 걸렸고(메리츠증권 합병 20일 전 · 069110 마지막 날까지 6일 연속)
    #    시뮬은 전부 −50% 로 쳤다. 합병·공개매수는 주주가 신주·현금을 받는다 — 손실이 아니다.
    #    ⚠️ 기본은 꺼짐. 켜면 모든 기준선이 움직인다. `scripts/vanish_kind.py` 가 표를 만든다
    _사라짐값 = {}          # code -> 마지막 종가 (합병·공개매수만)
    _사라짐자리 = {}
    if os.environ.get("VANISH_KIND") == "1":
        try:
            _vk = json.load(io.open(os.path.join(O._DATA, "vanish-kind.json"),
                                    encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            _vk = {}
        _날자리0 = {d: i for i, d in enumerate(날)}
        for _c0, _r0 in _vk.items():
            if _r0.get("종류") in ("합병", "공개매수") and _c0 in _사라짐:
                _v0 = (주가.get(_r0["마지막"]) or {}).get(_c0)
                if _v0 and _v0[0] > 0:
                    _사라짐값[_c0] = _v0[0]
                    _사라짐자리[_c0] = _날자리0.get(_r0["마지막"], len(날) - 1)
        print(f"  ⭐ VANISH_KIND=1 — 합병·공개매수로 사라진 {len(_사라짐값):,}개는 "
              f"**마지막 종가에 판 것**으로 (상장폐지·모름 {len(_사라짐) - len(_사라짐값):,}개는 "
              f"{O.폐지손실:.0f}% 그대로)", flush=True)
    else:
        print("  (VANISH_KIND 꺼짐 — 사라짐은 전부 상장폐지로 친다)", flush=True)
    assert isinstance(날, list) and len(날) > 1000, ('거래일 목록이 깨졌다', len(날))
    기본, 재무 = O._기본(), 연간재무()
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    # ⭐ **241차** — `day_lab.연간재무()` 는 **비율만** 준다.
    #    PBR 을 만들려면 **자본총계 원본**이 필요해 따로 읽는다
    _자본표 = {}
    for _f in sorted(glob.glob(os.path.join(O._DATA, "dart-fin", "*.json"))):
        _y = os.path.basename(_f)[:-5]
        if not _y.isdigit():
            continue
        _적 = f"{int(_y) + 1}0401"
        try:
            _d = json.load(io.open(_f, encoding="utf-8-sig"))
        except Exception:
            continue
        for _c, _v in _d.items():
            _x = _v.get("자본총계")
            if isinstance(_x, (int, float)) and _x > 0:
                _자본표.setdefault(_c, []).append((_적, float(_x)))
    for _c in _자본표:
        _자본표[_c].sort()
    print(f"  자본총계 {len(_자본표):,}종목 (PBR 용)", flush=True)

    def _자본값(code, d8):
        벌 = _자본표.get(code)
        if not 벌:
            return None
        좋 = None
        for 적, v in 벌:
            if 적 <= d8:
                좋 = v
            else:
                break
        return 좋

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
            # ⚠️ 5e13(50조) 이면 삼성전자(1,482조)가 그물 밖이다 (2026-09-18 combo4 에서 같은 것을 고쳤다)
            if 시총 < 1e10 or 시총 >= 9e15:
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
            # ⭐ statistics 는 36배 느리다 (2026-09-09 실측)
            s20, sd = O.창평균표준(sq, kk, 20)
            sd = sd or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if sq[kk - 20] <= 0:
                continue
            낙 = (c1 / sq[kk - 20] - 1) * 100
            # ── 165차: 창을 여러 개 붙인다 (157차와 같은 계산) ──
            창값 = {}
            for w in (5, 10, 20, 40, 60, 120, 250):
                if kk >= w and sq[kk - w] > 0:
                    창값[f"낙{w}"] = (c1 / sq[kk - w] - 1) * 100
            for w in (5, 10, 20, 40, 60, 120):
                if kk >= w:
                    m2, d2 = O.창평균표준(sq, kk, w)
                    d2 = d2 or 1e-9
                    창값[f"볼{w}"] = (c1 - m2) / (2 * d2)
            낙60 = ((c1 / sq[kk - 60] - 1) * 100
                    if kk >= 60 and sq[kk - 60] > 0 else None)
            s60 = O.창평균표준(sq, kk, 60)[0] if kk >= 59 else None
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            o0 = (원시.get(다음) or {}).get(code)
            g = 하루갭.get(code)
            if not b0 or not v0 or not o0 or g is None:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            량 = (거량.get(d1) or {}).get(code) or 0
            # ⚠️⚠️ **만들 때부터 좁힌다** (2026-09-10).
            #    램 지킴이가 이 시험을 **네 번** 죽였다 (23.7·21.6·18.2·23.1GB).
            #    처음엔 좁힘을 「사건을 다 만든 뒤」에 뒀는데, **만드는 동안**
            #    이미 20GB 를 넘겨서 소용이 없었다.
            #    이 시험의 도전자는 **전부 지금(x) 을 거치므로** 여기서 걸러도
            #    결과가 한 글자도 안 달라진다. 문턱은 **느슨하게** 남긴다
            # ⚠️⚠️ **2026-09-22 — 사용자가 잡아낸 구멍.**
            #    위 주석은 「도전자가 전부 지금(x)을 거치므로 걸러도 안 달라진다」고 했다.
            #    도전자가 전부 「지금 규칙 AND/OR 무엇」일 때만 참인 말이다.
            #    **Q-19~Q-28 의 띠·업종 규칙은 지금 규칙을 안 거친다** — 거짓이 됐다.
            #    즉 「그 칸 자료로 처음부터」라던 규칙들이 **소형 재무 문을 통과한
            #    종목만** 보고 있었다. 사용자: 「문 자체가 소형인데 무슨 소용이야」
            #    ⇒ OPENFIN=1 이면 재무·대금 문을 **안 건다.**
            #       대신 SIZE_LO~SIZE_HI 로 한 판에 한 띠만 봐서 램을 지킨다
            if not _문열기:
                if 재통과 != 1.0 or 대금 < 1e8:
                    continue
            else:
                if not (_크기하한 <= 시총 < _크기웃한):
                    continue
                if 대금 < _열대금:      # 램 지킴이 — 규칙이 아니다
                    continue
            _시억 = 시총 / 1e8
            # ⚠️ 237차: 상한을 **환경변수로** 연다 (기본은 3000 그대로).
            #    램 지킴이가 이 시험을 네 번 죽인 적이 있어 기본값은 안 건드린다
            #      SIZE_HI=999999 python scripts/gate7_lab.py   <- 대형주까지
            # ⭐ ㉣ (2026-09-16) — 섹터맵 종목은 크기 그물을 안 본다 (실전과 같게)
            if not (100 <= _시억 < _크기상한) and not (code in _사슬섹터 and R.섹터규칙_큰회사):
                continue
            # ⚠️ 섹터 규칙 중 **사이버보안(낙60 -10)** 이 이 그물에 안 걸린다.
            #    그물 전체를 넓히면 사건이 확 늘어 램이 터진다(네 번 죽은 적 있다).
            #    그래서 **섹터 종목만** 넓힌다 — 몇백 종목뿐이라 부담이 작다
            if not ((볼 is not None and 볼 <= -0.5)
                    or (낙 is not None and 낙 <= -5)
                    or (낙60 is not None and 낙60 <= -15)
                    or (code in _사슬섹터
                        and 낙60 is not None and 낙60 <= -10)):
                continue
            # ⭐ **241차** (2026-09-10) — 표준화 낙폭·PBR 을 자본 시뮬로
            #    재려면 사건에 있어야 한다. 둘 다 승률로는 좋았는데
            #    **자본 시뮬을 한 번도 안 했다**
            _일간 = [(sq[q] / sq[q - 1] - 1) * 100
                     for q in range(max(1, kk - 59), kk + 1) if sq[q - 1] > 0]
            _평 = sum(_일간) / len(_일간) if _일간 else 0
            _평소 = ((sum((z - _평) ** 2 for z in _일간) / len(_일간)) ** 0.5
                    if len(_일간) > 30 else None)
            _자본 = _자본값(code, d1)
            사건.append({
                "인": i + 1, "code": code, "원시": o0, "대금": b0[2],
                "평소등락": _평소,
                "PBR": (시총 / _자본) if (_자본 and _자본 > 0) else None,
                "볼린저": 볼, "낙폭20": 낙,
                "시총억": 시총 / 1e8, "대금억": 대금 / 1e8, "거래량": 량,
                "회전율": (대금 / 시총 * 100) if 시총 > 0 else 0,
                "갭": g, "매수": 매수, "재통과": 재통과, "낙폭60": 낙60,
                # ⭐ 2026-09-29 — **종가에 산다면** (BUYAT2). v0[0] 이 수정종가다
                #    ⚠️ b0[1] 은 **고가/종가** 다 — 종가가 아니다
                "매수종가": v0[0],
                "원시종가": (o0 / b0[0]) if b0[0] > 0 else o0,
                "해": d1[:4], **창값,
                "60일선대비": ((c1 / s60 - 1) * 100) if s60 else None,
                "주가": o0,
                # ⭐ 2026-09-22 — 재무를 **칸마다 다시 정하려면** 원값이 있어야 한다
                "흑자": (재무값(code, d1) or {}).get("흑자"),
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
        # ⚠️⚠️ **2026-09-19 버그** — 종목은 **한 겹 안에** 있다
        #    {"받은날":.., "종목수":.., "종목":{코드:{...}}}
        #    겉을 돌면 키가 셋(받은날·종목수·종목)뿐이라 **시장표가 텅 빈다.**
        #    그러면 아래 「닥이 들었나」가 늘 거짓 → **코스닥 1,823종목(66%)이
        #    코스피 지수로** 시장낙폭·시장낙60·시장변동성을 계산했다.
        #    실전(record_pick)은 O._기본()이 ["종목"]을 꺼내 **제대로 보고 있었다**
        #    ⇒ 시험과 실전이 서로 다른 지수를 보고 있었다
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
        x["_지수이름"] = 지수이름          # ⭐ 2026-09-19 — 아래에서 코스닥 몫을 찍는다 # [그날까지]
        x["시장낙폭"] = 시낙  # [그날까지]
        x["상대강도"] = (x["낙폭20"] - 시낙) if 시낙 is not None else None  # [그날까지]
        x["시장변동성"] = 변동성(지수이름, i2)  # [그날까지]
        큰 = 낙폭("코스닥 대형주", i2)
        작 = 낙폭("코스닥 소형주", i2)
        x["소형우위"] = (작 - 큰) if (큰 is not None and 작 is not None) else None  # [그날까지]
        if 시낙 is not None:
            붙음 += 1
        섹 = 업종지수(x["code"])
        섹낙 = 낙폭(섹, i2) if 섹 else None
        x["섹터"] = 섹  # [그날까지]
        x["섹터낙폭"] = 섹낙  # [그날까지]
        x["섹터대비"] = (x["낙폭20"] - 섹낙) if 섹낙 is not None else None  # [그날까지]
        if 섹낙 is not None:
            섹붙음 += 1
    print(f"  시장 지수 붙은 것 {붙음:,}/{len(사건):,} "
          f"· 섹터 지수 붙은 것 {섹붙음:,}/{len(사건):,} "
          f"({섹붙음/max(len(사건),1)*100:.0f}%)", flush=True)
    # ⚠️⚠️ **2026-09-19** — 여기서 멈추게 한다. 두 번 조용히 당했다:
    #    ① 시장표가 텅 빔(종목이 한 겹 안에 있었다)  ② 값이 "KOSDAQ" 인데 「닥」을 찾음
    #    둘 다 오류를 안 내고 **전부 코스피 지수**로 돌았다. 코스닥이 상장의 2/3 다
    _닥건 = sum(1 for x in 사건 if x.get("_지수이름") == "코스닥")
    print(f"  ⭐ 지수 갈래 — 코스닥 {_닥건:,}건 ({_닥건/max(len(사건),1)*100:.0f}%) "
          f"· 코스피 {len(사건)-_닥건:,}건", flush=True)
    # ⚠️ 2026-09-22 — 문을 연 판(OPENFIN)은 띠 하나만 담는다. 대형 1조↑는 코스닥이 21%,
    #    초대형 10조↑는 4% 인 게 **정상**이다 — 이 검사가 B15·B16 을 6분 만에 죽였다.
    #    그때는 **시장 지수가 붙은 비율(≥95%)** 로 건강을 본다 (B15 실측 210,741/210,748)
    if _문열기:
        assert 붙음 >= len(사건) * 0.95, (
            "시장 지수가 붙은 사건이 95% 미만이다 — 시장표가 깨졌다", 붙음, len(사건))
    else:
        assert _닥건 > len(사건) * 0.3, (
            "코스닥이 붙은 사건이 30% 미만이다 — 시장표나 「닥」 판정이 또 깨졌다", _닥건, len(사건))

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
            x["외인1"] = _몫(1, 0)  # [그날까지]
            x["외인5"] = _몫(5, 0)  # [그날까지]
            x["외인20"] = _몫(20, 0)  # [그날까지]
            x["기관5"] = _몫(5, 1)  # [그날까지]
            x["기관20"] = _몫(20, 1)  # [그날까지]
            x["개인5"] = _몫(5, 2)  # [그날까지]
            z2 = 지분창.get(x["code"])
            if z2:
                x["지분율"] = z2[-1]  # [그날까지]
                x["지분20변화"] = z2[-1] - z2[0] if len(z2) >= 21 else None  # [그날까지]

    묶 = {}
    for x in 사건:
        묶.setdefault(x["인"], []).append(x)
    시i = [j for j, d in enumerate(날) if d >= _시작][0]
    print(f"  후보 {len(사건):,}건 · {len(묶):,}일", flush=True)
    # ⚠️ **이 판의 기준선**을 맨 위에 찍는다 — 안 찍으면 다른 판과 섞인다
    print(f"  ⭐ 이 판의 기준선 — 갭잣대 **{_밑갭}** · "
          f"상대갭 **{_밑상대갭:+.1f}%p** · 후보수 **{_밑후보수}** · "
          f"크기상한 {_크기상한:,.0f}억 · 대조 {_대조번}번"
          + (f" · **기준선 규칙 Ⓖ**(120일선 −8%↓)" if _밑규칙 in ("G", "Ⓖ") else ""),
          flush=True)
    print("  ⭐ 매도 기준선 — "
          + (" / ".join(f"{z[0]:.0%} 목표 +{z[1]:g}% {z[2]}일" for z in _밑몫)
             if _밑몫 else
             f"{R.앞몫목표:g}%/{R.앞몫기한}일 반 · "
             f"{R.뒷몫목표:g}%/{R.뒷몫기한}일 반 (지금)") + "\n", flush=True)

    캐시 = {}

    # ⭐⭐ **보유 중 악재 공시** (2026-09-15 · 할일.md 예정 ③)
    #    지금 재평가는 「시장이 회복했나」만 본다. 「산 뒤에 악재가 뜨면
    #    판다」는 한 번도 안 쟀다 — **매수 쪽과 다른 질문**이다
    class _판세는표(dict):
        r"""**바뀔 때마다 판(version)이 올라가는 표** (2026-09-28)

        왜 — `결과()` 캐시 열쇠에 악재표가 안 들어가 있어서, BAD ③ 이 표를
             바꿔치기해도 **전에 계산한 값이 그대로 돌아왔다.** 다섯 말 묶음이
             전부 같은 값으로 나왔고 그 판은 못 쓰게 됐다.
        ⚠️ 누가 어떻게 바꾸든 자동으로 올라간다 — 다음에 또 까먹어도 안전하다
        ⚠️ **읽기(.get)는 손 안 댔다** — 뜨거운 자리라 느려지면 안 된다
        """

        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.판 = 0

        def __setitem__(self, k, v):
            self.판 += 1
            super().__setitem__(k, v)

        def __delitem__(self, k):
            self.판 += 1
            super().__delitem__(k)

        def clear(self):
            self.판 += 1
            super().clear()

        def update(self, *a, **k):
            self.판 += 1
            super().update(*a, **k)

        def pop(self, *a, **k):
            self.판 += 1
            return super().pop(*a, **k)

    _악재표 = _판세는표()
    try:
        import glob as _g8
        for _f8 in sorted(_g8.glob(os.path.join(O._DATA, "dart-daily",
                                                 "*.json"))):
            _d88 = os.path.basename(_f8)[:8]
            try:
                _j8 = json.load(io.open(_f8, encoding="utf-8-sig"))
            except ValueError:
                continue
            _하8 = {}
            for _칸8 in ("챙길공시", "그밖의공시"):
                for _x8 in (_j8.get(_칸8) or []):
                    _c8 = str(_x8.get("종목코드") or "")
                    _이8 = str(_x8.get("공시명") or "")
                    if _c8 and any(_w8 in _이8 for _w8 in _NM._악재말):
                        _하8[_c8] = _하8.get(_c8, 0) + 1
            if _하8:
                _악재표[_d88] = _하8
    except Exception as _e8:  # noqa: BLE001
        print(f"    ⚠️ 악재 공시표를 못 만들었다: {type(_e8).__name__}")
    print(f"    악재 공시가 있는 날 {len(_악재표):,}일", flush=True)

    def _때로들어옴(x):
        r"""그 종목이 **때** 때문에 후보가 됐나 (267차)

        ⚠️ `_시7`·`_밑끝갈래` 는 한참 아래에서 정의된다. 파이썬은 **부를 때**
           이름을 찾으므로 괜찮다 — 첫 시뮬 호출이 그보다 뒤다
        ⚠️ 2026-09-14 밤: `_시낙(x,60,-10)` 이 박혀 있었다. Ⓖ판에서는
           「때 때문에 들어온 것」을 **딴 규칙으로** 세고 있었다
        """
        return _시7(x) or _밑끝갈래(x)

    def 결과(x, 목표, 보유, 상태=None, 손절문턱=None, 재평가=None):
        """상태: None(기한) · "20일선"(종가가 20일선 위) · "볼0"(볼린저 0 위)

        ⚠️ 목표가에 먼저 닿으면 그걸로 판다. 상태는 **기한 대신** 쓰는 것이다
        ⭐ 손절문턱: -8.0 이면 **종가가 -8% 아래로 닫힌 날** 판다 (2026-09-11)
           ⚠️ 우리는 **종가만** 들고 있다. 장중에 목표와 손절을 둘 다 스쳤는지는
              알 수 없다 — 같은 날이면 **목표를 먼저** 본다 (지금 동작 그대로)
        """
        # ⭐ 2026-09-28 — **악재표가 바뀌면 열쇠도 바뀐다.**
        #    악재를 안 쓰는 판은 늘 0 이라 전과 **완전히 똑같이** 돈다
        # ⭐⭐⭐ 2026-09-29 — **`_비용` 도 열쇠에 넣는다.**
        #    B139 에서 비용 0배·2배·3배가 전부 같은 값으로 나왔다. 비용이
        #    영향 없는 게 아니라 **캐시가 옛 결과를 돌려준 것**이다.
        #    2026-09-28 악재표와 **똑같은 구멍**이 하나 더 있었다.
        #    ⚠️ 비용을 안 흔드는 판은 값이 하나뿐이라 전과 똑같이 돈다
        키 = (x["인"], x["code"], 목표, 보유, 상태, 손절문턱, 재평가,
             _악재표.판 if 재평가 == "악재" else 0, _비용, _살때)
        if 키 in 캐시:
            return 캐시[키]
        # ⭐⭐ 2026-09-29 — **사는 값** (`_살때`). 종가에 샀으면 그날 고가는 이미 지나갔다 —
        #    **h=1(다음 날)부터** 본다. 안 그러면 미래를 보는 시뮬이 된다
        _산 = x["매수종가"] if _살때 == "종가" else x["매수"]
        _첫h = 1 if _살때 == "종가" else 0
        i = x["인"] - 1
        r, 청 = None, None
        for h in range(_첫h, 보유 + 1):
            j = i + 1 + h
            if j >= len(날):
                break
            vv = 주가[날[j]].get(x["code"])
            b2 = (비.get(날[j]) or {}).get(x["code"])
            if not vv or not b2:
                break
            if vv[0] * b2[1] >= _산 * (1 + 목표 / 100):
                r, 청 = 목표 - _비용, j
                break
            # ⭐⭐ 267차 — **보유 중 재평가** (SELL-PLAN 243차 · 2026-09-11)
            #    「산 이유가 사라지면 판다」. 여기서 「이유」는 **때**다
            #    ⚠️ 자료가 없는 날은 **안 판다** (모르는 걸 회복으로 안 친다)
            # ⭐ 재평가 「악재」 — 보유 중 악재 공시가 뜨면 **다음 날 시가**에 판다
            #    ⚠️ 그날 **종가가 아니다.** 공시는 장후에도 뜬다 —
            #       장후 공시를 그날 종가에 팔았다 치면 **미래를 보는 것**이다
            #    ⚠️ 기존 재평가는 고가(`b2[1]`)로 판다. 악재에 고가는 너무 낙관적이라
            #       여기서는 **시가**(`b3[0]`)로 판다
            if 재평가 == "악재" and h >= 1:
                if (_악재표.get(날[j]) or {}).get(x["code"], 0) > 0:
                    j8 = j + 1
                    if j8 < len(날):
                        vv8 = 주가[날[j8]].get(x["code"])
                        b8 = (비.get(날[j8]) or {}).get(x["code"])
                        if vv8 and b8:
                            r, 청 = ((vv8[0] * b8[0] / _산 - 1) * 100
                                     - _비용), j8
                            break
            if 재평가 and 재평가 != "악재" and h >= 1:
                if 재평가 != "때" or _때로들어옴(x):
                    _이9 = _지수이름(x)
                    _낙7 = 낙폭(_이9, i + h, 7)
                    _낙60 = 낙폭(_이9, i + h, 60)
                    if _낙7 is not None and _낙60 is not None:
                        if _낙7 > -7 and _낙60 > -10:      # **회복했다**
                            r, 청 = ((vv[0] * b2[1] / _산 - 1) * 100
                                     - _비용), j
                            break
            # ⭐ 손절 (2026-09-11 · SELL-PLAN 240차)
            # ⚠️⚠️ 10/1 독립 검사: 숫자 손절은 `vv[0] * b2[1]` = **수정 고가**로 판정·매도한다(설명글의 「종가」와 다르다 —
            #    고가까지 밑이어야 걸리고 고가에 판 것으로 쳐 낙관적). 기존 판 기준선이라 그대로 두고,
            #    **문자열 "종가:-15"** 를 주면 종가로 판정하고 종가에 판다 (DDCTRL 이 쓴다)
            if 손절문턱 is not None and h >= 1:
                if isinstance(손절문턱, str):
                    _손문 = float(손절문턱.split(":")[1])
                    if vv[0] <= _산 * (1 + _손문 / 100):
                        r, 청 = (vv[0] / _산 - 1) * 100 - _비용, j
                        break
                elif vv[0] * b2[1] <= _산 * (1 + 손절문턱 / 100):
                    r, 청 = (vv[0] * b2[1] / _산 - 1) * 100 - _비용, j
                    break
            # ⭐ 상태 청산 — 날짜가 아니라 **회복됐을 때** 판다
            if 상태 and h >= 1:
                kk2 = (자리.get(x["code"]) or {}).get(날[j])
                if kk2 is not None and kk2 >= 20:
                    sq2 = 종계[x["code"]]
                    m20 = O.창평균표준(sq2, kk2, 20)[0]
                    회복 = False
                    if 상태 == "20일선":
                        회복 = sq2[kk2] > m20
                    else:
                        sd2 = O.창평균표준(sq2, kk2, 20)[1] or 1e-9
                        회복 = (sq2[kk2] - m20) / (2 * sd2) > 0
                    if 회복:
                        r, 청 = (vv[0] / _산 - 1) * 100 - _비용, j
                        break
        if r is None:
            j = i + 1 + 보유
            끝 = 주가[날[j]].get(x["code"]) if j < len(날) else None
            # ⚠️⚠️ **상장폐지를 손실로 센다** (2026-09-08 고침).
            #    전에는 자료가 없으면 그 거래를 **지웠다** —
            #    913종목(25%)이 중간에 사라졌고 성적이 부풀려졌다
            if not 끝 and x["code"] in _사라짐:
                # ⭐ ㉠-3 — 합병·공개매수면 마지막 종가에 판 것으로 (VANISH_KIND=1)
                _끝값 = _사라짐값.get(x["code"])
                if _끝값:
                    캐시[키] = ((_끝값 / _산 - 1) * 100 - _비용,
                                min(max(_사라짐자리[x["code"]], i + 1), len(날) - 1))
                    return 캐시[키]
                캐시[키] = (O.폐지손실 - _비용, min(j, len(날) - 1))
                return 캐시[키]
            if not 끝:
                캐시[키] = (None, None)
                return 캐시[키]
            r, 청 = (끝[0] / _산 - 1) * 100 - _비용, j
        캐시[키] = (r, 청)
        return 캐시[키]

    # ⭐ **242차** — 그날 **전 종목**(사건에 든 것 전부)의 중앙갭.
    #    후보 수와 **무관**해서 후보가 1개인 날에도 쓸 수 있다
    # ⭐ **246차** — 그날 **지수**의 갭 (시가 ÷ 전날 종가 − 1).
    #    ⚠️ 지수는 **시가**를 따로 안 준다 — `index-daily` 에 종가만 있다.
    #       그래서 **전 종목 중앙갭을 지수 대신**으로 쓸 수 없는지 먼저 보고,
    #       실제로는 **코스피200 ETF(069500) 등 큰 ETF 의 갭**으로 대신한다
    # ⭐ **246차 고침** — ETF 는 **사건에 안 들어온다**
    #    (사건은 시총 300~2,000억 + 재무 조건을 통과한 종목만 담는다).
    #    그래서 처음에 겹치는 날이 **0일**이었다.
    #    => `etf-krx` 에서 **직접** 읽는다 (시가·종가가 다 있다)
    _지수갭 = {}
    try:
        _날자리 = {d: i for i, d in enumerate(날)}
        _전종 = {}
        for _f6 in sorted(glob.glob(os.path.join(O._DATA, "etf-krx", "*.json"))):
            _d6 = os.path.basename(_f6)[:8]
            if _d6 not in _날자리:
                continue
            try:
                _j6 = json.load(io.open(_f6, encoding="utf-8-sig"))
            except Exception:
                continue
            _종6 = _j6.get("종목") or {}
            _벌6 = []
            for _c6 in ("069500", "102110", "229200", "233740", "091160"):
                _v6 = _종6.get(_c6)
                if not isinstance(_v6, dict):
                    continue
                try:
                    _시6 = float(_v6.get("시가") or 0)
                except (TypeError, ValueError):
                    continue
                _앞6 = _전종.get(_c6)
                if _앞6 and _앞6 > 0 and _시6 > 0:
                    _벌6.append((_시6 / _앞6 - 1) * 100)
                try:
                    _전종[_c6] = float(_v6.get("종가") or 0)
                except (TypeError, ValueError):
                    pass
            if _벌6:
                _벌6.sort()
                # ⚠️⚠️ **+ 1 이 있었다** (2026-09-11에 찾음).
                #    `_전종목중앙갭` 은 키 k 에 **`날[k]` 날의 갭**을 담는다
                #    (사건의 `인 = i + 1` 이고 갭도 `날[i + 1]` 날 것이다).
                #    여기는 `_d6` 날의 갭을 `+ 1` 자리에 넣어 **하루 밀렸다**.
                #    자료로 확인 — 2023 이후 900일, krx-daily vs etf-krx:
                #      같은 날끼리          상관 **+0.757**
                #      다음 날에 씀(옛 코드)  상관 **-0.017**
                #    246차가 낸 상관 -0.031 이 바로 이것이었다.
                #    ⇒ 그때 낸 12줄은 **전부 무효**다
                _지수갭[_날자리[_d6]] = _벌6[len(_벌6) // 2]
    except Exception as _e6:  # noqa: BLE001
        print(f"  ⚠️ ETF 갭을 못 읽었다: {type(_e6).__name__}")
    print(f"  지수 대용(큰 ETF 시가) 갭 {len(_지수갭):,}일 (246차용)", flush=True)

    # ⭐ **247차** — 증자·감자·자사주를 사건에 붙인다 (244차에서 자사주 +9.0%p)
    _자본 = {}
    try:
        for _f7 in glob.glob(os.path.join(O._DATA, "dart-capital", "*.json")):
            _c7 = os.path.basename(_f7)[:-5]
            if not _c7.isdigit():
                continue
            try:
                _j7 = json.load(io.open(_f7, encoding="utf-8-sig"))
            except Exception:
                continue
            # ⭐ 「유무상증자」·「자사주처분」이 목록에 **없었다** (2026-09-11).
            #    dart-capital 의 실제 열은 여섯이다
            for _k7 in ("유상증자", "무상증자", "유무상증자", "감자",
                        "자사주취득", "자사주처분"):
                for _x7 in (_j7.get(_k7) or []):
                    _rc = str(_x7.get("rcept_no") or "")
                    if len(_rc) >= 8 and _rc[:8].isdigit():
                        _자본.setdefault(_c7, {}).setdefault(_k7, []).append(_rc[:8])
        for _c7 in _자본:
            for _k7 in _자본[_c7]:
                _자본[_c7][_k7].sort()
    except Exception as _e7:  # noqa: BLE001
        print(f"  ⚠️ 자본 이력을 못 읽었다: {type(_e7).__name__}")
    print(f"  자본 이력 {len(_자본):,}종목 (247차용)", flush=True)

    # ══ ⭐⭐⭐ 265차 — **무리**를 붙인다 ══ (2026-09-11)
    #    `data/_무리_60.json` 의 `해마다` — 해마다 **다시 만든** 무리라
    #    미리보기가 아니다 (194·195차 · 상관 문턱 0.6 · 창 120일)
    _무리 = {}          # (해, 종목) -> [무리 식구들]
    _무리성격 = {}      # (해, 대표) -> "테마형"/"섞임"/"업종형"
    try:
        _j5 = json.load(io.open(os.path.join(O._DATA, "_무리_60.json"),
                                encoding="utf-8-sig"))
        for _해5, _벌5 in (_j5.get("해마다") or {}).items():
            for _대5, _식구 in _벌5.items():
                if len(_식구) < 3:
                    continue
                for _c5 in _식구:
                    _무리[(_해5, _c5)] = _식구
                # 196차 F절 그대로 — **한 업종 비중**으로 가른다
                _업5 = {}
                for _c5 in _식구:
                    _n5 = _산업.get(_c5)
                    if _n5:
                        _업5[_n5] = _업5.get(_n5, 0) + 1
                _큰5 = (max(_업5.values()) / len(_식구)) if _업5 else 0
                _무리성격[(_해5, _대5)] = ("업종형" if _큰5 >= 0.7 else
                                          "섞임" if _큰5 >= 0.4 else "테마형")
                for _c5 in _식구:
                    _무리성격[(_해5, _c5)] = _무리성격[(_해5, _대5)]
    except Exception as _e5:  # noqa: BLE001
        print(f"  ⚠️ 무리를 못 읽었다: {type(_e5).__name__}")
    print(f"  무리 {len({k[1] for k in _무리}):,}종목 (265차용)", flush=True)

    def _낙폭재기(code, d5, 창=20):
        r"""아무 종목의 그날 20일 낙폭. 사건이 아니어도 잰다"""
        _k5 = (자리.get(code) or {}).get(d5)
        if _k5 is None or _k5 < 창:
            return None
        _sq = 종계.get(code)
        if not _sq or _sq[_k5 - 창] <= 0:
            return None
        return (_sq[_k5] / _sq[_k5 - 창] - 1) * 100

    _무리낙 = {}

    def _무리낙폭(x):
        r"""그날 **무리 식구들**의 낙폭 중앙값. 식구가 셋 미만이면 None"""
        _키5 = (x["인"], x["code"])
        if _키5 in _무리낙:
            return _무리낙[_키5]
        _d5 = 날[x["인"] - 1]
        _식구 = _무리.get((str(x["해"]), x["code"]))
        _답 = None
        if _식구:
            _벌 = [z for z in (_낙폭재기(c, _d5) for c in _식구)
                   if z is not None]
            if len(_벌) >= 3:
                _벌.sort()
                _답 = _벌[len(_벌) // 2]
        _무리낙[_키5] = _답
        return _답

    def _같이빠짐(x, 벌어짐=10.0):
        r"""**같이 빠짐** — 무리와 ±10%p 안 (196차 D절 그대로)"""
        _m5 = _무리낙폭(x)
        if _m5 is None or x.get("낙폭20") is None:
            return False
        return abs(x["낙폭20"] - _m5) <= 벌어짐

    def _성격맞나(x, 성격):
        return _무리성격.get((str(x["해"]), x["code"])) == 성격

    def _자본있나(x, 종류, 창=60):
        _c8 = x.get("code")
        _벌8 = (_자본.get(_c8) or {}).get(종류)
        if not _벌8:
            return False
        _i8 = x["인"] - 1
        if _i8 >= len(날):
            return False
        _끝8 = 날[_i8]
        _앞8 = 날[max(0, _i8 - 창)]
        return any(_앞8 <= z <= _끝8 for z in _벌8)

    # ══ ⭐⭐⭐ 253차 — **중앙갭 표본** ══ (2026-09-11)
    #    실전 `auto_0850` 은 후보 + **시장 표본 30개**로 중앙값을 낸다.
    #    시뮬은 **후보만** 썼다 — 잣대가 다르면 다른 날 다른 종목을 산다
    _표본갭 = {}          # 종류 -> {날짜자리: [갭들]}
    _진짜전종목 = {}       # 날짜자리 -> 그날 **전 종목** 갭 중앙값
    _규모중앙갭 = {}       # ⭐ 260차 · 날짜자리 -> {규모대: 중앙갭}
    try:
        from auto_0850 import _시장표본 as _실전표본   # 실전이 쓰는 그 목록
    except Exception:  # noqa: BLE001
        _실전표본 = []
    # ⚠️ `_rnd` 는 **한참 아래(843줄)** 에서 import 된다 — 여기서 쓰면
    #    NameError 다. 이 블록은 제 것을 따로 들여온다
    import random as _rnd253
    _rs = _rnd253.Random(20260911)
    for _i9, _d9 in enumerate(날):
        _하루9 = 갭표.get(_d9) or {}
        if not _하루9:
            continue
        # ㉮ 실전 표본 30개 (코스피 초대형 20 + 코스닥 중대형 10)
        _벌9 = [_하루9[c] for c in _실전표본 if c in _하루9]
        if _벌9:
            _표본갭.setdefault("실전표본", {})[_i9] = _벌9
        # ㉱ 그날 **전 종목** 중앙갭 (사건 그물이 아니라 진짜 전부)
        _모두9 = list(_하루9.values())
        if len(_모두9) >= 20:
            _모두9.sort()
            _진짜전종목[_i9] = _모두9[len(_모두9) // 2]
        # ㉰ 그날 **우리 후보와 같은 규모**(300~2,000억)에서 무작위로
        #    ⚠️ 실전에서도 쓸 수 있다 — 전날 시총은 08:00 에 이미 안다
        _같규모 = [c for c, v in (주가.get(_d9) or {}).items()
                   if c in _하루9
                   and R.시총하한억 * 1e8 <= v[1] < R.시총상한억 * 1e8
                   and v[2] >= R.대금하한억 * 1e8]
        # ㉲ ⭐⭐⭐ 260차 — **규모대마다 제 중앙갭** (2026-09-11)
        #    지금은 300억 소형주 갭을 **삼성전자 갭**과 견주고 있다.
        #    규모대가 다르면 그날 움직이는 폭 자체가 다르다
        _띠벌 = {}
        for _c0, _v0 in (주가.get(_d9) or {}).items():
            if _c0 not in _하루9 or _v0[2] < R.대금하한억 * 1e8:
                continue
            _s0 = _v0[1] / 1e8
            _띠0 = ("소형" if _s0 < 2000 else
                    "중형" if _s0 < 10000 else "대형")
            _띠벌.setdefault(_띠0, []).append(_하루9[_c0])
        _중띠0 = {k: st.median(v) for k, v in _띠벌.items() if len(v) >= 10}
        if _중띠0:
            _규모중앙갭[_i9] = _중띠0

        if len(_같규모) >= 10:
            _rs.shuffle(_같규모)
            for _n9 in (10, 30, 50, 100, 300):
                _뽑9 = [_하루9[c] for c in _같규모[:_n9]]
                if len(_뽑9) >= min(10, _n9):
                    _표본갭.setdefault(f"같규모{_n9}", {})[_i9] = _뽑9
    print(f"  253차용 표본 — 실전30 {len(_표본갭.get('실전표본') or {}):,}일 · "
          f"같규모30 {len(_표본갭.get('같규모30') or {}):,}일 · "
          f"진짜전종목 {len(_진짜전종목):,}일 · "
          f"규모별 {len(_규모중앙갭):,}일", flush=True)

    _전종목중앙갭 = {}
    _묶갭 = {}
    for _x in 사건:
        if _x.get("갭") is not None:
            _묶갭.setdefault(_x["인"], []).append(_x["갭"])
    for _i, _v in _묶갭.items():
        if len(_v) >= 20:          # 너무 적으면 중앙값이 뜻이 없다
            _v.sort()
            _전종목중앙갭[_i] = _v[len(_v) // 2]
    print(f"  전 종목 중앙갭 {len(_전종목중앙갭):,}일 (242차용)", flush=True)

    _겹쳤다 = [0]        # ⭐ 266차 — 중복금지로 건너뛴 횟수

    # ⭐ 달력 매도 도우미 (2026-09-17) — {YYYYMM: 그 달 마지막 거래일 자리}
    _달끝자리 = {}
    for _iC, _dC in enumerate(날):
        _달끝자리[_dC[:6]] = _iC
    _계절끝달 = {"봄": "05", "여름": "08", "가을": "11", "겨울": "02"}
    _계절달들 = {"봄": ("03", "04", "05"), "여름": ("06", "07", "08"), "가을": ("09", "10", "11"), "겨울": ("12", "01", "02")}

    def _달력끝자리(i, 계절):
        """산 자리 i 에서 「계절」의 끝 달 마지막 거래일 자리 (i 보다 뒤인 첫 것)"""
        m = _계절끝달[계절]
        y = int(날[i][:4])
        for yy in (y, y + 1, y + 2):
            j = _달끝자리.get(f"{yy}{m}")
            if j is not None and j > i + 1:
                # 그 달이 자료 마지막 달이면 「끝 거래일」이 진짜 끝이 아닐 수 있다 — 그래도 쓴다
                return j
        return None

    def _계절인가C(x, 계절):
        return 날[x["인"] - 1][4:6] in _계절달들[계절]

    def 시뮬(c, 끝년=None, 시드=None, 시작년=None, 오차=0.0, 씨=None,
             묶2=None, 기록=None, 후보기록=None):
        # ⭐ 10/1 MULTI — 후보기록=list 를 주면 날마다 **산 것과 상관없이** 그날 고른 후보(골[:_상한])와
        #    몫마다 (비율, 결과%, 청산 자리) 를 담는다 — multi_lab.py 가 여러 규칙을 한 계좌로 합칠 때 쓴다.
        #    안 주면 지금과 한 글자도 안 달라진다
        # ⭐ 기록=list 를 주면 거래마다 (산 날, code, 시총억, 산 값, 결과%, 청산 자리) 를 담는다 (2026-09-15)
        # ⭐ `묶2` 를 주면 **그 사건 묶음**을 쓴다 (2026-09-15 · 분할 매수).
        #    매수 루프를 안 뜯으려고 낸 길이다 — 기존 호출은 하나도 안 바뀐다
        import random as _r2
        # ⭐ 264차 D — `씨` 를 주면 잡음이 달라진다 (2026-09-14 고침).
        #    전에는 씨앗이 박혀 있어 세 번 돌려도 **같은 잡음**이었고,
        #    호출부는 `시드`(시작 자본!) 에 0·1·2 를 넣어 **1원짜리 계좌**를 돌렸다
        _rng = _r2.Random(20260907 + int(씨 or 0))

        def _무리잰(c, i, 칸, 오차):
            r"""그룹마다 따로 — 40개 자르기 · 최소 후보 · 중앙갭 · 문턱. (값, 사건) 목록"""
            _잣 = c.get("갭잣대", _밑갭)
            if not (_잣 == "후보만" or _잣.startswith("후보+")):
                raise SystemExit(f"무리중앙은 후보만 · 후보+표본 잣대에서만 쓴다: {_잣!r}")
            _무중 = c["무리중앙"]
            _나머, _그룹 = [], [[] for _ in _무중]
            for x in 칸:
                for _k, (_fn, _nm) in enumerate(_무중):
                    try:
                        _hit = bool(_fn(x))
                    except Exception:  # noqa: BLE001
                        _hit = False
                    if _hit:
                        _그룹[_k].append(x)
                        break
                else:
                    _나머.append(x)
            _잘 = c.get("후보수", _밑후보수)
            _최 = c.get("최소후보", 3)
            _잰 = []
            _잰목 = 0
            for _목 in [_나머] + _그룹:
                _목 = sorted(_목, key=(c.get("자르기") or _기본자르기))[:_잘]
                if len(_목) < _최:
                    continue
                if _잣 == "후보만":
                    _중 = st.median([x["갭"] for x in _목])
                else:
                    _표 = (_표본갭.get(_잣[3:]) or {}).get(i)
                    if not _표:
                        continue
                    _중 = st.median([x["갭"] for x in _목] + list(_표))
                _잰목 += 1
                for x in _목:
                    v3 = x["갭"] - _중
                    if 오차:
                        v3 += _rng.gauss(0, 오차)
                    _갭문 = c["상대갭"]
                    for _fn5, _nm5, _th5 in (c.get("무리갭") or []):
                        try:
                            if _fn5(x):
                                _갭문 = _th5
                                break
                        except Exception:  # noqa: BLE001
                            pass
                    if v3 <= _갭문:
                        _잰.append((v3, x))
            return _잰 if _잰목 else None
        시드 = 시드 or _시드
        시작i = 시i
        if 시작년:
            _a = [j for j in range(len(날)) if 날[j][:4] >= 시작년]
            시작i = _a[0] if _a else 시i
        현금, 보유, 곡, 산 = 시드, [], [], 0
        큰산 = 0      # ⭐ 2026-09-21 — 2,000억↑ 을 실제로 몇 건 샀나 (Q-12·Q-14)
        for i in range(시작i, len(날)):
            # ⚠️⚠️ 끝년은 **포함**이다 (2026-09-16 확인). 해마다 표가 끝년=str(y+1) 로 불려 **두 해씩 겹친 창**이
            #    되어 있었다 — 인접한 해가 같은 %로 찍히고, 조건이 안 켜진 해에 돈이 달라졌다. 호출 쪽을 str(y) 로 고쳤다.
            #    걷기 앞도 ("2010","2021") 이라 2021 이 앞뒤에 다 들어갔다 → ("2010","2020")
            if 끝년 and 날[i][:4] > 끝년:
                break
            남 = []
            for q in 보유:
                if q["청산"] <= i:
                    현금 += q["주수"] * q["원시"] * (1 + q["결과"] / 100)
                else:
                    남.append(q)
            보유 = 남
            현금 *= (1 + _이자 / 245)      # ⭐ 2026-09-29 손잡이 (전엔 0.025 손으로)
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
            # ⭐ 10/1 「종가평가」 — 들고 있는 종목을 **전날 종가**로 평가한다(own_lab 과 같다).
            #    산 값으로 세면 들고 있는 동안의 평가손이 안 잡혀 낙폭이 얕게 나온다(B207 2021~ −12.5% 를 다시 재려고).
            #    켜지 않으면 위 한 줄 그대로 — 지금까지의 판과 한 원도 안 달라진다
            if c.get("종가평가") and i >= 1 and 보유:
                _전가 = 주가[날[i - 1]]
                평 = 현금 + sum(q["주수"] * q["원시"] * (
                    ((_전가.get(q["code"]) or (q.get("매수수정"),))[0] or q.get("매수수정")) / q["매수수정"]
                    if q.get("매수수정") else 1.0) for q in 보유)
            칸 = [x for x in ((묶2 if 묶2 is not None else 묶).get(i) or [])
                  if c["시총하한"] <= x["시총억"] < c["시총상한"]
                  and x["대금억"] >= c["대금하한"]
                  and x["거래량"] >= c["거래량하한"]
                  and x["회전율"] >= c["회전율하한"]]
            # ⚠️ 수급 거름은 **40개로 좁히기 전**에 건다.
            #    수급은 전날 자료라 08:00에 이미 알 수 있기 때문이다
            거름 = c.get("거름")
            if 거름:
                칸 = [x for x in 칸 if 거름(x)]
            # ⚠️⚠️ **40개로 자르는 순서가 실전과 달랐다** (2026-09-11 전수조사 ⑤).
            #    실전 `record_pick` : -(기존+섹터+시장) 먼저, 같은 층에서 낙폭 깊은 순
            #    시뮬(여기)          : **낙폭 깊은 순만**
            #    후보가 40개를 넘는 날 **누가 잘리는지가 달라진다**
            # ⭐ 기본이 **실전과 같은 순서**다 (2026-09-11 · 250차).
            #    옛 순서로 재려면 `자르기=_옛자르기` 를 준다
            # ⭐⭐⭐ 사용자 「후보 40개로 자를까」 — 172차 **기회 60% 차이**.
            #    전까지 _후보수 는 **상수**라 시뭄에서 바꿀 수가 없었다 (2026-09-11)
            # ⭐⭐⭐ **무리중앙** (2026-09-29 밤 · B144) — 그룹마다 제 후보끼리 잰다.
            #    「대형주는 대형주만의 규칙」: 같은 풀에 넣으면 중앙갭을 소형이 만들어 대형이 0건이다.
            #    그룹에 안 걸린 것(바탕)은 **그룹을 뺀 채** 예전과 똑같이 — 그룹이 비면 바탕은 그대로다
            if c.get("무리중앙"):
                잰 = _무리잰(c, i, 칸, 오차)
                if 잰 is None:            # 옛 길처럼 — 잴 목록이 하나도 없던 날만 건너뛴다
                    곡.append(평)
                    continue
            else:
                _잘날 = c.get("후보수", _밑후보수)
                칸 = sorted(칸, key=(c.get("자르기") or _기본자르기))[:_잘날]
                # ⭐⭐ **242차** (2026-09-10) — 「중앙갭을 무엇으로 잡나」를 고를 수 있게.
                #    ⚠️ 전에는 **후보 3개 미만인 날을 아예 건너뛰었다**.
                #       그래서 시뮬은 「후보가 적은 날」을 **본 적이 없다**.
                #       실전에는 그런 날이 있다 (2026-09-08 후보 1개 -> 산 것 0개)
                _최소 = c.get("최소후보", 3)
                if len(칸) < _최소:
                    곡.append(평)
                    continue
                # ⚠️⚠️ **기본이 실전과 같아졌다** (2026-09-11 사용자 결정).
                #    실전 `auto_0850` 은 후보 + **시장 표본 30개**로 중앙값을 낸다.
                #    시뮬은 **후보만** 썼고, 그래서 실전을 **4.2배 과소평가**했다:
                #      후보만          3.19억 · 낙폭 -6.3% · 돈÷낙 7.79
                #      후보+실전표본30  13.35억 · 낙폭 -5.7% · 돈÷낙 12.49
                #      앞 +125% · 뒤 +79% · 해마다 **9승 1패 1무** (253차)
                #    ⚠️ 이 줄을 바꾸면 **모든 시험의 기준선이 움직인다.**
                #       지나간 `data/_labs/*.txt` 는 그때 값 그대로 둔다
                _잣대 = c.get("갭잣대", _밑갭)
                _띠중 = None          # ⭐ 260차 — 규모대별로 다른 중앙갭
                if _잣대 == "절대":
                    중 = 0.0                      # 중앙값 없이 **절대 갭**
                elif _잣대 == "전종목중앙":
                    중 = _전종목중앙갭.get(i)
                    if 중 is None:
                        곡.append(평)
                        continue
                elif _잣대 == "진짜전종목":
                    # ⭐ 253차 — 사건 그물이 아니라 **그날 전 종목**
                    중 = _진짜전종목.get(i)
                    if 중 is None:
                        곡.append(평)
                        continue
                elif _잣대.startswith("후보+"):
                    # ⭐⭐⭐ 253차 — **실전과 같은 방식**: 후보 갭과 표본 갭을
                    #    **합쳐서** 중앙값을 낸다 (`auto_0850` 117줄)
                    _표9 = (_표본갭.get(_잣대[3:]) or {}).get(i)
                    if not _표9:
                        곡.append(평)
                        continue
                    중 = st.median([x["갭"] for x in 칸] + list(_표9))
                elif _잣대.startswith("표본만+"):
                    # 표본 **혼자** — 후보를 안 섞으면 어떤가
                    _표9 = (_표본갭.get(_잣대[4:]) or {}).get(i)
                    if not _표9:
                        곡.append(평)
                        continue
                    중 = st.median(_표9)
                elif _잣대 == "규모별":
                    # ⭐⭐⭐ 260차 — 종목마다 **제 규모대의** 중앙갭과 견준다
                    _띠중 = _규모중앙갭.get(i)
                    if not _띠중:
                        곡.append(평)
                        continue
                    중 = None
                elif _잣대 == "지수갭":
                    # ⭐ **246차** — 08:50 에 실제로 볼 수 있는 값.
                    #    전 종목 중앙갭은 **실전에서 못 구한다** (사람이 후보만 본다)
                    중 = _지수갭.get(i)
                    if 중 is None:
                        곡.append(평)
                        continue
                elif _잣대 == "후보만":
                    중 = st.median([x["갭"] for x in 칸])
                else:
                    # ⚠️⚠️ **모르는 잣대면 멈춘다** (2026-09-14).
                    #    전에는 조용히 「후보만」으로 떨어졌다. 9/13 일요일 판에서
                    #    PowerShell 이 한글을 cp949 로 넘겨 잣대가 깨졌는데,
                    #    **아무도 모르게** 후보만으로 돌아 판 셋이 헛돌았다.
                    #    조용히 떨어지는 것이 제일 나쁘다
                    raise SystemExit(
                        f"모르는 갭잣대: {_잣대!r} — BASE_GAP 이 깨졌을 수 있다 "
                        "(PowerShell 한글 인코딩). 쓸 수 있는 것: 절대 · 후보만 · "
                        "전종목중앙 · 진짜전종목 · 규모별 · 지수갭 · "
                        "후보+<표본> · 표본만+<표본>")
                잰 = []
                for x in 칸:
                    if 중 is None:                     # ⭐ 260차 규모별
                        _s3 = x["시총억"]
                        _m3 = _띠중.get("소형" if _s3 < 2000 else
                                        "중형" if _s3 < 10000 else "대형")
                        if _m3 is None:
                            continue
                        v3 = x["갭"] - _m3
                    else:
                        v3 = x["갭"] - 중
                    if 오차:
                        v3 += _rng.gauss(0, 오차)
                    # ⭐⭐⭐ **시총별 상대갭** (2026-09-21 · Q-16) — `갭무름` 이 있으면
                    #    큰 회사는 덜 빠져도 산다. 대형주는 거래가 두꺼워 시초가가 잘 안 튀는데,
                    #    같은 -3.5%p 를 요구하니 **세 겹 중 마지막 문**에서 전부 걸렸다.
                    #    ⚠️ 「덜 싸게 사도 된다」는 뜻이라 수익률이 나빠질 수 있다
                    _갭문 = c["상대갭"]
                    _갭무름 = c.get("갭무름")
                    if _갭무름:
                        _s4 = x.get("시총억") or 0
                        for _컷4, _v4 in _갭무름:
                            if _s4 >= _컷4:
                                _갭문 = c["상대갭"] * _v4
                    # ⭐⭐⭐ **무리마다 제 상대갭 문턱** (2026-09-28)
                    #    `무리갭` = [(판정함수, 이름, 문턱), …] — 먼저 맞는 것을 쓴다.
                    #    `갭무름`(시총 컷 x 배수)과 달리 **섹터·업종에도** 쓸 수 있다.
                    #    ⚠️ 안 주면 지금과 한 글자도 안 달라진다
                    _무리갭 = c.get("무리갭")
                    if _무리갭:
                        for _fn5, _nm5, _th5 in _무리갭:
                            try:
                                if _fn5(x):
                                    _갭문 = _th5
                                    break
                            except Exception:  # noqa: BLE001
                                pass
                    if v3 <= _갭문:
                        잰.append((v3, x))
            # ⚠️ 기본은 **갭이 큰 순**이다. 고르기가 있으면 그 순서로 바꾼다.
            #    문턱(상대갭 -3.5%p)은 그대로라 **후보 수는 안 변한다**
            고르기 = c.get("고르기")
            if 고르기:
                골 = sorted([z[1] for z in 잰], key=고르기)
            else:
                골 = [z[1] for z in sorted(잰, key=lambda z: z[0])]
            # ⭐⭐⭐ **하루 상한을 날마다 다르게** (2026-09-19 · Q-6 용)
            #    지금은 늘 4 다. 그런데 9/19 판에서 **빠지는 장의 바탕이 59.8%**,
            #    횡보는 41.1% 로 나왔다 — 바탕이 20%p 다른 날에 같은 수만 사는 건
            #    아깝다. 사용자 1순위가 「상승 기회를 놓치지 않는 것」이므로
            #    **좋은 날에 더 사는 것**이 맞는지 잰다.
            #    숫자를 주면 지금과 똑같이 돈다 (기존 판은 하나도 안 바뀐다)
            _상한 = c["하루상한"]
            if callable(_상한):
                _상한 = _상한(골)
            # ⭐⭐⭐ **대형주 전용 자리** (2026-09-21 · Q-12 결과로) — `큰자리` 가 있으면
            #    하루 자리 중 그만큼을 **2,000억↑ 에 떼어 둔다.**
            #    Q-12 에서 문턱을 무르게 하니 대형 후보가 2.5배 늘었는데 **한 건도 안 샀다** —
            #    고르는 순서가 「깊게 빠진 순」이라 덜 빠지는 대형주가 늘 뒤로 밀렸다.
            #    ⚠️ 대형 후보가 없으면 그 자리는 **소형이 쓴다** (기회를 버리지 않는다)
            _큰자리 = c.get("큰자리") or 0
            if _큰자리 > 0 and _상한 > _큰자리:
                _큰것 = [z for z in 골 if (z.get("시총억") or 0) >= 2000][:_큰자리]
                _작것 = [z for z in 골 if z not in _큰것][:_상한 - len(_큰것)]
                골 = _큰것 + _작것
            # ⭐⭐⭐ **무리마다 제 자리** (2026-09-28 · 사용자 아이디어)
            #    「꼭 후보를 전체에서 4개가 아니라, 규모별로, 섹터별로 나누는 건 어때?」
            #    `무리자리` = [(판정함수, 이름, 자리수), …]
            #    ⚠️ `큰자리`(떼어두기)와 **뜻이 다르다** — 이쪽은 총 자리가 **늘어난다.**
            #       소형을 밀어내지 않는다. 사용자 1순위(기회를 놓치지 않는다)에 맞다
            #    ⚠️ 무리에 안 걸린 것은 **남은 자리(_상한)** 를 그대로 쓴다
            _무리 = c.get("무리자리")
            if _무리:
                _뽑, _본 = [], set()
                for _뭇, _름, _몫 in _무리:
                    _n = 0
                    for _z in 골:
                        if id(_z) in _본:
                            continue
                        try:
                            if _뭇(_z):
                                _뽑.append(_z)
                                _본.add(id(_z))
                                _n += 1
                                if _n >= _몫:
                                    break
                        except Exception:  # noqa: BLE001
                            pass
                # 무리에 안 걸린 것들은 **원래 자리(_상한)** 를 그대로 쓴다
                _남 = [_z for _z in 골 if id(_z) not in _본][:_상한]
                골 = _뽑 + _남
                _상한 = len(골)

            if 후보기록 is not None and 골[:_상한]:
                if c.get("규모별매도") or c.get("무리몫") or c.get("달력매도") or c.get("나눔") or callable(c["비중"]):
                    raise SystemExit("후보기록은 실전 몫(R.몫들·BASE_SELL)·숫자 비중일 때만 — 규모별매도·무리몫·달력매도·나눔 없이")
                _몫D = _밑몫 or R.몫들
                _줄D = []
                for x in 골[:_상한]:
                    _몫r = []
                    for 몫 in _몫D:
                        rD, 청D = 결과(x, 몫[1], 몫[2], 몫[3] if len(몫) > 3 else None, c.get("손절"), c.get("재평가"))
                        _몫r.append((몫[0], rD, 청D))
                    _줄D.append({"code": x["code"], "원시": (x["원시종가"] if _살때 == "종가" else x["원시"]),
                                 "매수": (x.get("매수종가") if _살때 == "종가" else x.get("매수")),
                                 "대금억": x["대금"] / 1e8, "시총억": x["시총억"], "몫": _몫r})
                후보기록.append((i, _줄D))
            for x in 골[:_상한]:
                # ⭐⭐ 266차 — **이미 들고 있는 종목을 또 사나** (2026-09-11)
                #    지금(중복금지 없음)은 **또 산다**. 그러면 한 종목에
                #    자산의 40·60% 가 몰려 「자산의 20%」 가정이 깨진다
                if c.get("중복금지") and any(q.get("code") == x["code"]
                                             for q in 보유):
                    _겹쳤다[0] += 1
                    continue
                # ⚠️ 나눔이 있으면 **주수를 쪼개** 두 몫으로 만든다.
                #    한 종목에 들어가는 총액은 같다 (자산 20%)
                # ⭐ BASE_SELL 을 주면 **그게 기준선**이다 (2026-09-11)
                # ⭐ 순서: 그 줄이 준 나눔 -> BASE_SELL -> rule_def 현행
                몫들 = c.get("나눔") or _밑몫 or R.몫들
                # ⭐ 규모별 매도 (2026-09-11 · SELL-PLAN 241차)
                #    대형주는 변동이 작아 +15% 가 멀다 — 규모대마다 다른 몫
                _규매 = c.get("규모별매도")
                if _규매:
                    _s5 = x["시총억"]
                    몫들 = _규매.get("소형" if _s5 < 2000 else
                                    "중형" if _s5 < 10000 else "대형") or 몫들
                # ⭐⭐⭐ **무리마다 제 파는규칙** (2026-09-28 · 사용자)
                #    「섹터는 섹터별로 규칙!」 — `규모별매도` 는 규모(소·중·대)만 된다.
                #    `무리몫` = [(판정함수, 이름, 몫들), …] 은 **섹터·업종에도** 쓴다.
                #    먼저 맞는 것을 쓴다. 안 주면 지금과 한 글자도 안 달라진다
                _무리몫 = c.get("무리몫")
                if _무리몫:
                    for _fn7, _nm7, _mm7 in _무리몫:
                        try:
                            if _fn7(x):
                                몫들 = _mm7
                                break
                        except Exception:  # noqa: BLE001
                            pass
                # ⭐ 달력 매도 (2026-09-17 · 사용자) — 파는 계절 끝 거래일까지의 거래일 수를 보유 기한으로
                _달매 = c.get("달력매도")
                if _달매:
                    _끝i = _달력끝자리(i, _달매[1])
                    if _끝i is None:
                        continue                      # 자료 끝을 넘는다 — 못 판다 → 안 산다
                    _보유c = max(1, _끝i - (i + 1))
                    몫들 = [(m[0], (999.0 if _달매[2] == "순수" else m[1]), _보유c) for m in 몫들]
                _손5 = c.get("손절")
                # ⭐⭐ **제약없음** (2026-09-10 · 사용자 지적)
                #    사용자: 「**종목을 샀을 때 수익으로 계산해야지**
                #             내 자산이 얼마가 있으니 **종목에 제한을 둔다거나,
                #             그래선 안 될 것 같아**」
                #    ⚠️ `평 * 비중`(자산의 몇 %) 은 **그대로 둔다** —
                #       복리와 낙폭이 거기서 나온다.
                #       빼는 것은 **현금**과 **거래대금 1% 한도**뿐이다
                # ⭐ 2026-09-23 (F5) — **비중을 함수로도** 받는다.
                #    「갈래 둘 이상 걸린 종목은 30% · 하나면 15%」 같은 것을 재려면 필요하다.
                #    ⚠️ 숫자를 주면 전과 똑같다 — 기존 호출은 하나도 안 바뀜다
                _비중 = c["비중"]
                if callable(_비중):
                    _비중 = _비중(x)
                if c.get("제약없음"):
                    쓸 = 평 * _비중
                    총주수 = int(쓸 // (x["원시종가"] if _살때 == "종가" else x["원시"]))
                    if 총주수 < len(몫들):
                        # ⚠️ 1주도 못 살 만큼 비싸면 **주수를 몫 수만큼** 맞춘다
                        #    (소액 가정 때문에 건너뛰던 것을 없앤다)
                        총주수 = len(몫들)
                else:
                    # ⭐ 2026-09-29 — **거래대금 한도 비율을 흔들 수 있게.**
                    #    1% 에 근거가 없다 (코드 어디에도 왜 1% 인지 안 적혀 있다).
                    #    안 주면 0.01 그대로다 — 기존 판은 한 글자도 안 바뀐다
                    쓸 = min(평 * _비중, 현금,
                             x["대금"] * (c.get("대금비율") or 0.01))
                    총주수 = int(쓸 // (x["원시종가"] if _살때 == "종가" else x["원시"]))
                    if 총주수 < len(몫들) or 총주수 * (x["원시종가"] if _살때 == "종가" else x["원시"]) > 현금:
                        continue
                넣음 = False
                for 몫 in 몫들:
                    비율, 목표b, 보유b = 몫[0], 몫[1], 몫[2]
                    상태b = 몫[3] if len(몫) > 3 else None
                    r, 청 = 결과(x, 목표b, 보유b, 상태b, _손5,
                                 c.get("재평가"))
                    if r is None:
                        continue
                    주수 = int(총주수 * 비율)
                    if 주수 < 1:
                        continue
                    if not c.get("제약없음") and 주수 * (x["원시종가"] if _살때 == "종가" else x["원시"]) > 현금:
                        continue
                    현금 -= 주수 * (x["원시종가"] if _살때 == "종가" else x["원시"])
                    보유.append({"주수": 주수, "원시": (x["원시종가"] if _살때 == "종가" else x["원시"]),
                                 "결과": r, "청산": 청,
                                 "code": x["code"],   # ⭐ 266차
                                 # ⭐ 10/1 「종가평가」 — 수정주가 기준 산 값 (주가[날][code][0] 이 수정종가라 같은 기준으로 나눈다)
                                 "매수수정": (x.get("매수종가") if _살때 == "종가" else x.get("매수"))})
                    if 기록 is not None:
                        기록.append((날[i], x["code"], x["시총억"], (x["원시종가"] if _살때 == "종가" else x["원시"]), r, 청, 주수))
                    넣음 = True
                if 넣음:
                    산 += 1
                    # ⭐ 2026-09-21 — **2,000억↑ 을 몇 건 샀나**. Q-12 에서
                    #    「후보는 2.5배 늘었는데 끝 자산이 1원도 안 바뀌었다」를 겪고 넣었다.
                    #    후보 수만 보면 늘어난 것처럼 보이는데 **실제로 산 건 0** 일 수 있다
                    if (x.get("시총억") or 0) >= 2000:
                        큰산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
        해 = max(len(곡) / 245, 0.1)
        연 = ((끝 / 시드) ** (1 / 해) - 1) * 100 if 끝 > 0 else -100
        최고, 낙 = 시드, 0.0
        for v in 곡:
            최고 = max(최고, v)
            낙 = min(낙, v / 최고 - 1)
        _r = {"끝": 끝, "연": 연, "낙": 낙 * 100, "산": 산, "큰산": 큰산}
        # ⭐ 10/1 DDWHEN — 「곡돌려줘」면 계좌 곡선도 준다 (곡[k] = 시작 자리 + k 번째 거래일의 평가액 · 산 값 기준)
        if c.get("곡돌려줘"):
            _r["곡"] = 곡
        return _r

    머 = f"    {'':<28}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}"

    def 표(r, 라, 기=None):
        점 = r["연"] / max(abs(r["낙"]), 3.0)
        꼬 = ""
        if 기:
            늘 = (r["끝"] / 기["끝"] - 1) * 100
            꼬 = f"  ({늘:+.0f}%)"
        print(f"    {라:<28}{r['끝']:>15,.0f}원{r['연']:>+8.2f}%"
              f"{r['낙']:>7.1f}%{r['산']:>7}{점:>9.2f}{꼬}", flush=True)

    import random as _rnd

    def 앞수익(x, n, 오차=0.0, 씨=0):
        """n일 뒤 수익. 오차를 주면 **산 값이 그만큼 흔들린다**"""
        i2 = x["인"]
        j = i2 + n
        if j >= len(날):
            return None
        a = 주가[날[i2]].get(x["code"])
        if not a or a[0] <= 0:
            return None
        산값 = x["매수"]
        if 오차:
            r = _rnd.Random(hash((x["인"], x["code"], 씨)) & 0xFFFFFFFF)
            산값 *= (1 + r.uniform(-오차, 오차) / 100)
        b = 주가[날[j]].get(x["code"])
        if not b:
            if x["code"] in _사라짐값:          # ⭐ ㉠-3
                return (_사라짐값[x["code"]] / x["매수"] - 1) * 100 - _비용
            return (O.폐지손실 - _비용) if x["code"] in _사라짐 else None
        # ⚠️ 매수는 시가(x["매수"]), 매도는 종가 — 둘 다 수정주가 기준으로 맞춘다
        비율 = a[0] / 산값 if 산값 > 0 else None
        if not 비율:
            return None
        return (b[0] * 비율 / a[0] - 1) * 100 - _비용

    # ⭐ 169차 F절: 「그 섹터 기준으로 몇 시그마 빠졌나」
    #    문턱을 고르지 않으니 과적합이 안 생긴다
    _섹칸 = {}
    for x in 사건:
        if x.get("섹터"):
            _섹칸.setdefault(x["섹터"], []).append(x["낙폭20"])
    _통계 = {}
    for s2, v2 in _섹칸.items():
        if len(v2) < 200:
            continue
        m2 = sum(v2) / len(v2)
        sd2 = (sum((z - m2) ** 2 for z in v2) / len(v2)) ** 0.5 or 1e-9
        _통계[s2] = (m2, sd2)
    for x in 사건:
        st2 = _통계.get(x.get("섹터"))
        if st2:
            x["섹시그마"] = (x["낙폭20"] - st2[0]) / st2[1]  # [전체표본] ⚠️ 16년 전체 섹터 통계다 — **규칙에 쓰면 미래를 본다** (2026-09-23 셋째 후보를 이 이유로 뺐다)

    print("  기준 수익률 붙이는 중...", flush=True)
    for x in 사건:
        x["_20"] = 앞수익(x, 20)  # [미래값] 기준 수익률 — 재료로는 안 쓴다 (_아님29 에 들어 있다)
        x["_40"] = 앞수익(x, 40)  # [미래값] 기준 수익률 — 재료로는 안 쓴다 (_아님29 에 들어 있다)

    # ── ⭐ 해외 (193차) ──
    # ⚠️⚠️ **사건 dict 에 넣지 않는다** (2026-09-09).
    #    처음엔 5,437,354개 dict 마다 해외 18개 필드를 넣었는데
    #    **램이 터져 386바이트에서 죽었다** (189차도 같은 자리에서 세 번 죽었다).
    #    해외 값은 **날짜에만 달렸다** — 표에서 찾아 쓰면 된다 (192차가 이렇게 해서 살았다)
    # ⚠️⚠️ 사건에는 **`_날짜` 라는 키가 없다** (2026-09-10에 알았다).
    #    날짜는 「인」(매수일 인덱스)과 「해」(연도)로만 들어 있다.
    #    이걸 몰라 **세 번 죽었다** — KeyError: '_날짜'
    _날들 = sorted({날[x["인"]] for x in 사건 if 0 <= x["인"] < len(날)})
    _해표 = _해외표(_날들)
    print(f"  해외 {len(_해표)}가지 (날짜 표로 둔다 — 사건에 안 넣는다)", flush=True)

    def 외(x, 라, 창):
        """그 사건의 **매수일** 기준 해외 값. 창은 1·5·20일 변화(%)

        ⚠️ 「인」은 매수일 인덱스다. 해외 표는 **그날보다 앞선 마지막 값**을
           담고 있으므로, 매수일을 넘기면 「전날 밤 미국 종가」가 나온다
        """
        i2 = x["인"]
        if not (0 <= i2 < len(날)):
            return None
        v = _해표.get(라, {}).get(날[i2])
        if not v:
            return None
        return v[{1: 0, 5: 1, 20: 2}[창]]


    # ⚠️⚠️ **여기서 좁혀야 램이 산다** (2026-09-10).
    #    2026-09-09 밤에 193·197·189차가 **트레이스백도 없이** 죽었다 —
    #    파이썬 예외가 아니라 **OS 가 램 때문에 죽인 것**이었다 (gate7 이 23.7GB).
    #    사건 5,437,354개 x dict 3~4KB = 20GB 안팎이다.
    #
    #    ① 바탕(C절 무작위 대조)은 **dict 가 필요 없다** — `_20` 값 하나만 쓴다.
    #       그래서 **값만 따로** 모아 둔다 (float 24바이트)
    #    ② 그러면 사건은 좁혀도 된다 — 이 시험의 도전자는 **전부 지금(x) 을 거치므로**
    #       재무·대금·크기를 통과 못 한 사건은 **한 번도 안 쓰인다**
    #    ⚠️ 여유를 둔다: 볼린저·낙폭 문턱은 도전자마다 다르므로 **느슨하게** 남긴다
    _바탕20 = [x["_20"] for x in 사건 if x.get("_20") is not None]
    _전 = len(사건)

    def _쓸까(x):
        if x.get("재통과") != 1.0 or x.get("대금억", 0) < 1.0:
            return False
        시 = x.get("시총억") or 0
        if not (100 <= 시 < 3000):
            return False
        볼 = x.get("볼린저")
        n20 = x.get("낙폭20")
        n60 = x.get("낙폭60")
        return ((볼 is not None and 볼 <= -0.5)
                or (n20 is not None and n20 <= -5)
                or (n60 is not None and n60 <= -15))

    # ⚠️ 좁히기는 **위(사건.append 앞)에서 이미 했다.** 여기서는 바탕만 알린다
    print(f"  사건 {len(사건):,}건 · 바탕 {len(_바탕20):,}개는 값만 따로 둔다",
          flush=True)

    해수 = 10.4

    # ══ 도전자들 ══
    # ⭐⭐⭐ **재무 문을 흔들 수 있게** (2026-09-29)
    #    `x["재통과"]` 는 미리 계산된 값이라 그대로면 못 흔든다.
    #    `_재무옵` 이 비어 있지 않으면 **원자료로 다시 판정**한다.
    #    비어 있으면 지금과 한 글자도 안 달라진다 — 기존 판은 그대로다
    #    왜 필요한가: 잉여금 30% · 부채 80% · 흑자 · 대금 1억 — **왜 그 값인지 근거가 없다**
    _재무옵 = {}

    def 재무통과(x):
        if not _재무옵:
            return x.get("재통과") == 1.0
        _잉 = _재무옵.get("잉여금")
        if _잉 is not None:
            _v = x.get("잉여금")
            if _v is None or _v < _잉:
                return False
        _부 = _재무옵.get("부채")
        if _부 is not None:
            _v = x.get("부채")
            if _v is None or _v > _부:
                return False
        if _재무옵.get("흑자"):
            if not x.get("흑자"):
                return False
        return True

    def 대금통과(x):
        return x["대금억"] >= (_재무옵.get("대금", 1.0) if _재무옵 else 1.0)

    def 크기통과(x):
        # ⚠️⚠️ **500 → 300** (2026-09-11 전수조사 ②).
        #    실전 `record_pick._시총하한` 은 **3e10 = 300억**인데 여기는 500억이라,
        #    지금까지의 4관문·자본 시뮬은 **실전이 사는 종목의 10% 를 표본에서
        #    빼고** 쟀다. 2026-09-10 기준 후보 40개 중 4개가 500억 미만이고
        #    화면 2위 제이투케이바이오(498억)가 그중 하나였다
        # ⭐ 상한은 `_규칙크기상한` (SIZE_HI 를 따라간다 · 2026-09-14)
        return R.시총하한억 <= x["시총억"] < _규칙크기상한

    # 공통 문 — 실전에서 **셋 중 하나를 보기 전에** 모두 거치는 것
    def 문통과(x):
        return 재무통과(x) and 대금통과(x) and 크기통과(x)

    def 문통과_크기없이(x):
        r"""재무·대금만 본다 — **크기 문을 뺀다** (2026-09-29).

        왜 — `문통과` 안에 `크기통과`(300~2,000억)가 들어 있다. 이름만 보면 「문」인데
             **소형 크기 문**이다. 띠를 나눠 재는 절이 이걸 쓰면 중형·대형이
             **들어올 수가 없다.** 어제 GROUP 의 업종 갈래 칸이 그 상태였다
        ⚠️ `문통과` 자체는 안 건드린다 — 소형 갈래(기존·시장)는 크기 문이 있어야 맞다
        """
        return 재무통과(x) and 대금통과(x)

    def 지금(x):
        return (문통과(x)
                and x["볼린저"] <= R.볼린저문턱
                and x["낙폭20"] <= R.낙폭20문턱)

    # ⭐⭐⭐ **섹터 규칙** (2026-09-11 전수조사 ③).
    #    실전 `record_pick._섹터규칙` 과 **같은 값**을 그대로 옮겼다.
    #    지금까지 시험의 Ⓗ 에는 이게 **없었다** — 239~249차가 전부
    #    섹터 빠진 기준선 위에서 쟀다
    #    (창, 볼린저문턱, 창, 낙폭문턱)
    _섹규칙 = R.섹터규칙        # ⭐ rule_def 하나에서

    # 한 규칙 **안에서는 AND**(볼린저 그리고 낙폭) — 실전과 같다
    def 섹터맞나(x):
        규 = _섹규칙.get(_사슬섹터.get(x["code"]))
        if not 규:
            return False
        bw, bt, nw, nt = 규
        b, n = x.get(f"볼{bw}"), x.get(f"낙{nw}")
        return b is not None and n is not None and b <= bt and n <= nt

    def 있(x, k):
        return x.get(k) is not None

    def 업종갈래맞나(x):
        r"""실전 규칙의 업종 갈래(R.업종규칙맞나)에 걸렸나 — 실전 규칙을 재는 절들이 같이 쓴다 (10/1 PEAKCUT).
        ⚠️ 띠를 나눠 재는 함수가 아니다 — 시총은 업종 규칙의 크기 문을 보려고 넘길 뿐이다"""
        try:
            _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
            return bool(_m)
        except Exception:  # noqa: BLE001
            return False

    # ⭐⭐ **193차 도전자** — 192차에서 나온 해외 신호 (2026-09-09)
    #    사용자: 「한국은 **수출 위주 국가**라 해외 수주나 해외 소식에 영향을 받을 것 같아」
    #    ⚠️ 192차는 재무 조건이 빠진 잣대였다. 여기서는 재무까지 넣고 다시 잰다
    def _지수이름(x):
        시 = 시장표.get(x["code"]) or ""
        return ("코스닥" if ("닥" in str(시) or "KOSDAQ" in str(시).upper())
                else "코스피")   # ⚠️2026-09-19: 값은 "KOSDAQ" — 한글 「닥」만 찾으면 늘 거짓이었다

    # 날짜 자리(i2)마다 「때」 값을 **한 번만** 재서 표로 둔다 (사건마다 재면 느리다)
    _때캐시 = {}

    def _때(x, 재기, *a):
        키 = (재기, _지수이름(x), x["인"] - 1) + a
        v = _때캐시.get(키)
        if 키 not in _때캐시:
            이, i2 = _지수이름(x), x["인"] - 1
            if 재기 == "낙":
                v = 낙폭(이, i2, a[0])
            elif 재기 == "변":
                v = 변동성(이, i2, a[0])
            elif 재기 == "평":            # 지수가 n일 이동평균보다 몇 % 위/아래
                sq = _계열캐시.get(이) or 지수계열(이)
                _계열캐시[이] = sq
                n = a[0]
                if i2 < n or i2 >= len(sq) or not sq[i2]:
                    v = None
                else:
                    창 = [z for z in sq[i2 - n:i2] if z]
                    v = ((sq[i2] / (sum(창) / len(창)) - 1) * 100) if 창 else None
            elif 재기 == "연":            # 연이어 내린 날수
                sq = _계열캐시.get(이) or 지수계열(이)
                _계열캐시[이] = sq
                n, k = 0, i2
                while k > 0 and sq[k] and sq[k - 1] and sq[k] < sq[k - 1] and n < 20:
                    n += 1
                    k -= 1
                v = n
            _때캐시[키] = v
        return v

    # ══ ⭐⭐ 220차 — 219차에서 나온 **「때」 조건을 4관문에** (2026-09-10) ══
    #  219차의 「구간별」 세 칸은 A관문의 **약식판**이다.
    #  여기서 정식으로 A(앞뒤 분할) · B(해마다) · **C(무작위 대조 200번)** 를 건다
    def _시낙7(x):
        return (x.get("시장낙폭") is not None
                and x["시장낙폭"] <= R.지수낙20문턱)

    def _지낙(x, w, 문):
        v = _때(x, "낙", w)
        return v is not None and v <= 문

    def _지평(x, w, 문):
        v = _때(x, "평", w)
        return v is not None and v <= 문

    도전자 = [
        ("지금 규칙", 지금),

        # ── 220차 도전자 ──
        ("Ⓐ ⭐⭐⭐ 기존 OR **지수 60일 낙폭 ≤-10%**",
         lambda x: 지금(x) or _지낙(x, 60, -10)),
        ("Ⓑ ⭐⭐ 기존 OR **지수 40일 낙폭 ≤-10%**",
         lambda x: 지금(x) or _지낙(x, 40, -10)),
        ("Ⓒ ⭐⭐ 기존 OR **지수가 60일선 -8%↓**",
         lambda x: 지금(x) or _지평(x, 60, -8)),
        ("Ⓓ ⭐⭐⭐ 기존 OR **지수가 120일선 -8%↓**",
         lambda x: 지금(x) or _지평(x, 120, -8)),
        ("Ⓔ ⭐ 기존 OR 지수가 20일선 -8%↓",
         lambda x: 지금(x) or _지평(x, 20, -8)),
        ("Ⓕ ⭐ 기존 OR 지수 40일 낙폭 ≤-7%",
         lambda x: 지금(x) or _지낙(x, 40, -7)),
        # ── 겹치기: 시장낙폭(20일)과 **오래 눌림**을 같이 ──
        ("Ⓖ ⭐⭐ 기존 OR 시낙7 **OR** 120일선 -8%↓",
         lambda x: 지금(x) or _시낙7(x) or _지평(x, 120, -8)),
        ("Ⓗ ⭐⭐ 기존 OR 시낙7 **OR** 지수 60일≤-10%",
         lambda x: 지금(x) or _시낙7(x) or _지낙(x, 60, -10)),
        ("Ⓘ ⭐ 기존 OR (시낙7 **AND** 120일선 -8%↓)",
         lambda x: 지금(x) or (_시낙7(x) and _지평(x, 120, -8))),
        # ── ⭐ 반영 후보 (219차 F절 ⑥) — 명시 가능한 형태 ──
        ("Ⓙ ⭐⭐⭐ **반영 후보** 기존 OR (시낙7 AND 시총300~2000 AND 낙20≤-5%)",
         lambda x: (지금(x) or (_시낙7(x) and 300 <= x["시총억"] < 2000
                                and x["낙폭20"] <= -5))),
        ("Ⓚ ⭐⭐ Ⓙ + **120일선 -8%↓** 도 OR 로",
         lambda x: (지금(x) or (_시낙7(x) and 300 <= x["시총억"] < 2000
                                and x["낙폭20"] <= -5)
                    or (_지평(x, 120, -8) and 300 <= x["시총억"] < 2000
                        and x["낙폭20"] <= -5))),
        ("① **원달러 5일 +3%↑** (원화 급락 = 수출 유리)",
         lambda x: 지금(x) and 외(x, "원달러", 5) is not None and 외(x, "원달러", 5) >= 3),
        ("①-2 원달러 5일 +1.5%↑ (문턱 낮춤)",
         lambda x: 지금(x) and 외(x, "원달러", 5) is not None and 외(x, "원달러", 5) >= 1.5),
        ("①-3 원달러 20일 +3%↑ (창 늘림)",
         lambda x: 지금(x) and 외(x, "원달러", 20) is not None and 외(x, "원달러", 20) >= 3),
        ("② **S&P500 5일 -3%↓**",
         lambda x: 지금(x) and 외(x, "S&P500", 5) is not None and 외(x, "S&P500", 5) <= -3),
        ("③ **구리 5일 -3%↓**",
         lambda x: 지금(x) and 외(x, "구리", 5) is not None and 외(x, "구리", 5) <= -3),
        ("④ **반도체ETF 5일 -3%↓**",
         lambda x: 지금(x) and 외(x, "반도체ETF", 5) is not None and 외(x, "반도체ETF", 5) <= -3),
        ("⑤ 공포지수 5일 +3%↑",
         lambda x: 지금(x) and 외(x, "공포지수", 5) is not None and 외(x, "공포지수", 5) >= 3),
        ("⑥ **S&P500이 오른 뒤엔 안 산다** (+3%↑ 빼기)",
         lambda x: 지금(x) and 외(x, "S&P500", 5) is not None and 외(x, "S&P500", 5) < 3),
        ("⑦ 원달러 급락 **또는** S&P 급락",
         lambda x: 지금(x) and ((외(x, "원달러", 5) is not None and 외(x, "원달러", 5) >= 3)
                               or (외(x, "S&P500", 5) is not None and 외(x, "S&P500", 5) <= -3))),
        # ⭐ 191차에서 나온 것도 같이 건다 —
        #    앞뒤 검증을 통과한 여섯 섹터 중 **다섯이 「낙폭 60일」을 골랐다**
        ("⑧ **낙폭 창을 20일 -> 60일** (191차)",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0
                    and 있(x, "낙폭60") and x["낙폭60"] <= -20.0)),
        ("⑧-2 낙폭 60일 -30%",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.0
                    and 있(x, "낙폭60") and x["낙폭60"] <= -30.0)),
        ("⑨ 20일 -10% **와** 60일 -20% 둘 다",
         lambda x: (지금(x) and 있(x, "낙폭60") and x["낙폭60"] <= -20.0)),
        # ⭐⭐ **203차 — OR 로 더한 판도 4관문에 태운다** (2026-09-10)
        #    사용자: 「기존 규칙, 새로운 규칙 **둘 중 하나만 부합해도 다 후보로**」
        ("⑩ ⭐ 기존 **OR** 낙60 -30%",
         lambda x: (지금(x)
                    or (재무통과(x) and 대금통과(x) and 크기통과(x)
                        and x["볼린저"] <= -1.0
                        and 있(x, "낙폭60") and x["낙폭60"] <= -30.0))),
        ("⑪ ⭐ 기존 **OR** 낙60 -20%",
         lambda x: (지금(x)
                    or (재무통과(x) and 대금통과(x) and 크기통과(x)
                        and x["볼린저"] <= -1.0
                        and 있(x, "낙폭60") and x["낙폭60"] <= -20.0))),
        # ⭐⭐⭐⭐ **210차 — 시장낙폭 OR** (209차에서 나온 가장 큰 개선)
        #    209차: 기존 OR 시장낙폭≤-7% -> **+8.1%p · 기회 292%**
        #           볼20-1.5σ OR 시장낙폭≤-12% -> **+17.3%p · 기회 401%**
        #    ⚠️ 170·179차의 「시장 -10%↓ 날만」은 **대체**라 기회를 1/5 로 깎았다.
        #       이번엔 **더하기**다 — 기회가 늘면서 승률이 오르는지 본다
        ("⑱ ⭐⭐⭐ 기존 **OR** 시장낙폭≤-7%",
         lambda x: (지금(x) or (있(x, "시장낙폭") and x["시장낙폭"] <= -7))),
        ("⑲ ⭐⭐ 기존 **OR** 시장낙폭≤-12%",
         lambda x: (지금(x) or (있(x, "시장낙폭") and x["시장낙폭"] <= -12))),
        ("⑳ ⭐ 기존 **OR** 시장낙폭≤-3%",
         lambda x: (지금(x) or (있(x, "시장낙폭") and x["시장낙폭"] <= -3))),
        ("㉑ ⭐ 기존 OR 섹터 OR 시장낙폭≤-7%",
         lambda x: (지금(x)
                    or (있(x, "시장낙폭") and x["시장낙폭"] <= -7)
                    or (재무통과(x) and 대금통과(x) and 크기통과(x)
                        and x["볼린저"] <= -1.5 and x["낙폭20"] <= -5.0))),
        # ⭐⭐⭐ **208차 — 볼20 -1.5σ** (207차 최근 3년 탐색에서 나온 것)
        #    207차: 최근 상위 16개 중 **14개가 볼20 -1.5σ** ·
        #           볼20 -1.5σ·낙20 -10% 최근 **63.9%**(1년 1,258개) vs 지금 53.0%
        #    ⚠️ **대체와 더하기를 둘 다** 잰다 — 대체는 기회를 깎고 더하기는 늘린다
        ("⑬ ⭐⭐ **볼20 문턱을 -1.5σ 로** (대체)",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.5 and x["낙폭20"] <= -10.0)),
        ("⑭ ⭐ 볼20 -1.5σ · 낙20 **-5%** (대체 · 낙폭 풀기)",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.5 and x["낙폭20"] <= -5.0)),
        ("⑮ ⭐ 볼20 -1.5σ · 낙40 -20% (대체 · 207차 1위)",
         lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                    and x["볼린저"] <= -1.5
                    and 있(x, "낙40") and x["낙40"] <= -20.0)),
        ("⑯ ⭐⭐ 기존 **OR** 볼20 -1.5σ·낙20 -5% (더하기)",
         lambda x: (지금(x)
                    or (재무통과(x) and 대금통과(x) and 크기통과(x)
                        and x["볼린저"] <= -1.5 and x["낙폭20"] <= -5.0))),
        ("⑰ ⭐ 기존 **OR** 볼20 -1.5σ·낙40 -20% (더하기)",
         lambda x: (지금(x)
                    or (재무통과(x) and 대금통과(x) and 크기통과(x)
                        and x["볼린저"] <= -1.5
                        and 있(x, "낙40") and x["낙40"] <= -20.0))),
        ("⑫ ⭐ 기존 **OR** 규모규칙(볼120 -1.0σ·낙20 -20%)",
         lambda x: (지금(x)
                    or (재무통과(x) and 대금통과(x)
                        and 300 <= (x.get("시총억") or 0) < 2000
                        and 있(x, "볼120") and x["볼120"] <= -1.0
                        and 있(x, "낙폭20") and x["낙폭20"] <= -20.0))),
    ]

    def 점수(칸, 기="_20"):
        v = [x[기] for x in 칸 if x.get(기) is not None]
        if len(v) < 60:
            return None
        return (sum(1 for z in v if z > 0) / len(v) * 100,
                sum(v) / len(v), len(칸))

    def 줄(라, 점, 기준=None):
        if 점 is None:
            print(f"  {라:<40}      표본 부족")
            return
        이, 평, n = 점
        꼬 = ""
        if 기준:
            꼬 = f"{이-기준[0]:>+8.1f}p{평-기준[1]:>+8.2f}"
        print(f"  {라:<40}{n:>8,}{n/해수:>7.0f}{이:>8.1f}%{평:>+8.2f}{꼬}")

    머2 = (f"  {'설정':<40}{'건수':>8}{'1년에':>7}"
           f"{'20일 이김':>9}{'평균':>8}{'지금대비':>9}{'':>8}")

    print("\n" + "=" * 108)
    print("  193차 · **해외 신호을 4관문에** (수출국 가설)")
    print(f"  후보 {len(사건):,}건 · 바탕(아무 종목·아무 날) 20일 44.7% · +0.65%")
    print(f"  ⚠️ 상장폐지는 {O.폐지손실:.0f}% 손실로 센다")
    print("=" * 108)

    # ══ ⭐⭐⭐ **판정을 한 곳에** (2026-09-20 · 사용자 「셋 넣어!」) ══
    #    전에는 절마다 `_승[0 if _d > 1 else ...]` 을 손으로 적어
    #    죽은 구간이 ±0.5 · ±1 로 제각각이었고, **유의성을 아무도 안 봤다.**
    #    9/20 에 후보 넷이 「4승 5패 ❌」로 떨어졌는데 따져보니 t 가 전부 |t|<1 —
    #    **「나쁘다」가 아니라 「해마다로는 못 가른다」**였다.
    #    docs/판정장치점검.md 에 전수조사를 적어 뒀다
    def _해마다판정(차들, 낙차들=None, 이름=""):
        r"""해마다 차이 목록을 받아 **평균 ± 오차 · t** 로 판정한다.

        차들   : 해마다 (도전 − 견줌). 돈이면 %, 이길 확률이면 %p
        낙차들 : 해마다 (도전 낙폭 − 견줌 낙폭). **+ 면 덜 깊어진 것**(좋다)
        돌려줌 : (판정글, 좋은가)
          ✅ 좋다     t ≥ +2      — 잡음보다 크게 낫다
          ❌ 나쁘다   t ≤ −2      — 잡음보다 크게 못하다
          ⬜ 모르겠다 그 사이     — **기각이 아니다.** 더 봐야 한다는 뜻
        ⚠️ 죽은 구간(±0.5·±1)은 **없앴다** — 내가 고른 선이 승패를 만들었다
        """
        import statistics as _stG
        if not 차들 or len(차들) < 3:
            return ("표본 부족", None)
        _평 = _stG.mean(차들)
        _sd = _stG.stdev(차들) if len(차들) > 1 else 0.0
        _se = (_sd / (len(차들) ** 0.5)) if _sd else 0.0
        _t = (_평 / _se) if _se else 0.0
        _좋 = True if _t >= 2 else (False if _t <= -2 else None)
        _표 = "✅ 낫다" if _좋 is True else ("❌ 못하다" if _좋 is False else "⬜ 못 가른다")
        _글 = (f"{len(차들)}해 · 평균 {_평:+.2f} ± {_se:.2f} · t {_t:+.2f}  {_표}")
        # ② 낙폭도 같이 — 돈만 보면 위험 개선이 영영 안 보인다
        if 낙차들 and len(낙차들) == len(차들):
            _낙평 = _stG.mean(낙차들)
            _낙sd = _stG.stdev(낙차들) if len(낙차들) > 1 else 0.0
            _낙se = (_낙sd / (len(낙차들) ** 0.5)) if _낙sd else 0.0
            _낙t = (_낙평 / _낙se) if _낙se else 0.0
            _낙표 = ("✅ 얕아짐" if _낙t >= 2 else ("❌ 깊어짐" if _낙t <= -2 else "⬜"))
            _글 += f"   |  낙폭 {_낙평:+.2f}%p ± {_낙se:.2f} · t {_낙t:+.2f} {_낙표}"
        return (_글, _좋)

    # ══ ⭐⭐⭐ **낙폭 기준** (2026-09-21 · 사용자 결정) ══
    #    사용자: 「12% 견딜 수 있어!」
    #    전에는 -10.0 이 절마다 손으로 박혀 있었고 **근거 기록이 없었다.**
    #    지수 버그를 고치니 지금 규칙의 진짜 낙폭이 -11.0% 로 나와, 우리 기준에
    #    **우리 규칙이 걸리는** 일이 벌어졌다. 숫자가 나빠진 게 아니라 눈금이 고쳐진 것이다.
    #    1억이 8,800만원까지 내려가는 것을 한 번은 본다는 뜻 — 사용자가 받아들였다.
    #    ⚠️ 이 값은 **여기 한 곳만** 고친다. 절마다 박으면 또 갈라진다
    낙폭기준 = float(os.environ.get("MAXDD") or -12.0)
    print(f"  ⭐ 낙폭 기준 **{낙폭기준:g}%** (2026-09-21 사용자 결정 · 전 -10%)", flush=True)

    def _걷기(도전거름, 밑거름=None, 옵=None):
        r"""걷기 앞뒤 — **뒤 구간을 앞이 끝낸 자산으로 잇는다** (2026-09-21 고침).

        전에는 앞·뒤를 각각 시드 500만원부터 돌렸다. 그런데 전 기간을 통째로
        돌리면 2021년엔 이미 6,207만원이다. **자본 크기가 규칙을 바꾼다** —
        500만원이면 한 종목 100만원이라 거래대금 1% 한도에 거의 안 걸리고,
        2.5억이면 한 종목 5,000만원이라 계속 걸린다.
        숫자도 안 맞았다: 앞 +2.0% · 뒤 -0.6% 인데 전 기간은 +7% 였다.

        돌려줌: [(구간이름, 견줌r, 도전r, 차이%), ...]
        ⚠️ 견줌과 도전은 **각자의 앞 끝 자산**으로 뒤를 시작한다 —
           도전이 앞에서 더 벌었으면 뒤도 그 돈으로 하는 게 실제로 일어날 일이다
        """
        옵 = 옵 or {}
        밑거름 = 밑거름 or _H
        _칸 = (("앞 2010~2020", "2010", "2020"), ("뒤 2021~2026", "2021", "2026"))
        _줄, _시드a, _시드b = [], None, None
        for _라, _시, _끝 in _칸:
            _a = 시뮬(_c(밑거름, **옵), 시작년=_시, 끝년=_끝, 시드=_시드a)
            _b = 시뮬(_c(도전거름, **옵), 시작년=_시, 끝년=_끝, 시드=_시드b)
            if not _a or not _b:
                continue
            _d = (_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0
            _줄.append((_라, _a, _b, _d))
            _시드a, _시드b = _a["끝"], _b["끝"]      # ⭐ 뒤로 잇는다
        return _줄

    def _옵걷기(옵, 거름=None):
        r"""**옵(자리·상대갭·파는규칙)** 을 준 쪽과 안 준 쪽을 걷기로 견준다 (2026-09-28).

        ⚠️ `_걷기` 는 **거름이 다를 때**를 위한 것이다. 옵을 주면 **견줌에도 들어가서**
           양쪽이 똑같아진다 — B125 에서 걷기가 전부 `+0.0%` 로 나온 원인이다.
           같은 숫자를 「❌ 갈린다」로 읽고 있었다.
        돌려줌: `_걷기` 와 같은 꼴 [(구간, 견줌r, 도전r, 차이%), …] — `_걷기찍기` 로 찍는다
        """
        거름 = 거름 or _H
        _칸 = (("앞 2010~2020", "2010", "2020"), ("뒤 2021~2026", "2021", "2026"))
        _줄, _시드a, _시드b = [], None, None
        for _라, _시, _끝 in _칸:
            _a = 시뮬(_c(거름), 시작년=_시, 끝년=_끝, 시드=_시드a)          # 옵 없이
            _b = 시뮬(_c(거름, **옵), 시작년=_시, 끝년=_끝, 시드=_시드b)    # 옵 주고
            if not _a or not _b:
                continue
            _d = (_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0
            _줄.append((_라, _a, _b, _d))
            _시드a, _시드b = _a["끝"], _b["끝"]
        return _줄

    def _걷기찍기(줄들, 들여="        "):
        for _라, _a, _b, _d in 줄들:
            print(f"{들여}{_라}: {_a['끝']:,.0f}원 → {_b['끝']:,.0f}원  {_d:+.1f}%"
                  f"  (낙폭 {_a['낙']:.1f}% → {_b['낙']:.1f}% · 산 것 {_a['산']} → {_b['산']})")
        _ok = len(줄들) == 2 and min(z[3] for z in 줄들) > 0
        print(f"{들여}걷기: " + ("✅ 앞뒤 둘 다 +" if _ok else "❌ 앞뒤가 갈린다")
              + "   (뒤는 앞이 끝낸 자산으로 잇는다 · 2026-09-21 고침)")
        return _ok

    통과표 = {}

    # ── A 앞뒤 분할 ──
    print("\n" + "=" * 108)
    print("  A 앞뒤 분할 — 기간을 갈라도 **같은 방향**인가")
    print("=" * 108)
    # ⭐⭐⭐ **같은 것을 수십 번 다시 세던 것을 한 번만** (2026-09-29 · 판 속도)
    #    고친 때 지도: 이 절이 **18.6분 (판 49분의 39%)**.
    #    `지금(x)` 은 도전자와 상관없이 늘 같은 답인데
    #      A절이 도전자 x 구간 4번 · B절이 도전자 x 해 11번 **다시 셌다** (사건 730,000건).
    #    ⇒ 한 번만 돌려 **해마다 나눠 둔다.** 결과 숫자는 한 자리도 안 바뀐다
    _지금칸 = [x for x in 사건 if 지금(x)]
    _지금해칸 = {}
    for _x0 in _지금칸:
        _지금해칸.setdefault(_x0["해"], []).append(_x0)

    def _지금사이(a, b):
        r"""`지금(x)` 이면서 해가 a~b 인 것 — 미리 나눠 둔 것에서 꺼낸다."""
        _벌 = []
        for _y0, _z0 in _지금해칸.items():
            if a <= _y0 <= b:
                _벌.extend(_z0)
        return _벌

    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"), ("2025·26 뺀 것", "2016", "2024"))
    for 라, fn in 도전자:
        print(f"\n   [{라}]")
        print(머2)
        방향 = []
        for 구라, a, b in 구간:
            칸 = [x for x in 사건 if fn(x) and a <= x["해"] <= b]
            기 = _지금사이(a, b)          # ⭐ 미리 나눠 둔 것 (전과 같은 값)
            점, 기점 = 점수(칸), 점수(기)
            줄(f"{구라}", 점, 기점)
            if 점 and 기점:
                방향.append(점[0] - 기점[0])
        if 라 != "지금 규칙" and 방향:
            좋 = all(v > 0 for v in 방향)
            통과표.setdefault(라, {})["A"] = 좋
            # ⚠️⚠️ **기회 수를 같이 찍는다** (2026-09-09).
            #    전에는 이김만 봤다. 그래서 190차에서 기회가 **6%**로 줄어든 것이
            #    「통과」로 찍혔다 (지금 규칙 1년 1,842개 -> 106개).
            #    사용자 원문: 「매도 타이밍과 자산 보유 현황도 중요하지만
            #    **그것도 때문에 상승 기회를 놓쳐서는 안돼**」
            #    ⚠️ 자동으로 떨어뜨리지는 않는다 — 기회와 승률은 교환이고
            #       어디까지 받아들일지는 사람이 정한다. 다만 **늘 보이게** 한다
            기회비 = None
            try:
                _기 = 점수(_지금칸)
                _도 = 점수([x for x in 사건 if fn(x)])
                if _기 and _도 and _기[2]:
                    기회비 = _도[2] / _기[2] * 100
            except Exception:  # noqa: BLE001
                pass
            꼬 = ""
            if 기회비 is not None:
                꼬 = f"  · **기회 {기회비:.0f}%**"
                if 기회비 < 50:
                    꼬 += "  ⚠️ **절반 밑이다 — 기회를 깎는다**"
            print(f"     ⇒ 네 구간 **{'전부 낫다 ✅' if 좋 else '엇갈린다 ❌'}**{꼬}")

    # ── B 해마다 ──
    print("\n" + "=" * 108)
    print("  B 해마다 — 몇 승 몇 패인가")
    print("=" * 108)
    해들 = sorted({x["해"] for x in 사건})
    for 라, fn in 도전자[1:]:
        이김, 짐, 무 = 0, 0, 0
        칸별 = []
        for y in 해들:
            점 = 점수([x for x in 사건 if fn(x) and x["해"] == y])
            기점 = 점수(_지금해칸.get(y) or [])   # ⭐ 미리 나눠 둔 것 (전과 같은 값)
            if not 점 or not 기점:
                continue
            차 = 점[0] - 기점[0]
            칸별.append((y, 기점[0], 점[0], 차))
            # ⚠️ 승패 세기는 **없앴다** (2026-09-20) — ±0.5%p 죽은 구간이
            #    결과를 만들었고 유의성을 아무도 안 봤다
            if 차 > 0:
                이김 += 1
            elif 차 < 0:
                짐 += 1
            else:
                무 += 1
        print(f"\n   [{라}]  {'해':<8}{'지금':>10}{'도전':>10}{'차이':>10}")
        for y, a, b, c in 칸별:
            print(f"            {y:<8}{a:>9.1f}%{b:>9.1f}%{c:>+9.1f}p")
        _글B, _좋B = _해마다판정([c for *_, c in 칸별], 이름=라)
        print(f"     ⇒ {_글B}   (참고: {이김}승 {짐}패 {무}무)")
        # ⭐ **「못 가른다」는 기각이 아니다** — 여기서는 「나쁘지 않다」로 통과시키고
        #    사람이 D·E 를 읽고 정한다. 전에는 4승 5패 같은 잡음으로 떨어뜨렸다
        통과표.setdefault(라, {})["B"] = (_좋B is not False)
        통과표.setdefault(라, {})["B글"] = _글B

    # ── C 무작위 대조 ──
    print("\n" + "=" * 108)
    print("  C ⭐ 무작위 대조 — 같은 개수를 **아무렇게나** 골라 200번")
    print("     (조합을 많이 훑으면 운으로 좋아 보이는 게 나온다. 그걸 걸러낸다)")
    print("=" * 108)
    # ⚠️ dict 가 아니라 **값만** 쓴다 (2026-09-10) — 위에서 따로 모아 뒀다
    # ⚠️⚠️ **바탕의 뜻이 달라졌다** (2026-09-10).
    #    전에는 「아무 종목·아무 날」 5.4M 이었는데, 램 때문에 사건을 만들 때부터
    #    좁히면서 바탕도 **「느슨한 후보 중 아무거나」**가 됐다.
    #    (재무·대금·크기를 통과하고 볼-0.5σ 또는 -5% 또는 낙60 -15% 인 것들)
    #    => **더 엄격한 대조**다. 여기서 상위 25% 에 들면 전보다 믿을 만하다.
    #       다만 **190차 이전 결과와 숫자를 나란히 놓으면 안 된다**
    바탕칸 = _바탕20
    for 라, fn in 도전자[1:]:
        칸 = [x for x in 사건 if fn(x) and x.get("_20") is not None]
        if len(칸) < 100:
            print(f"  {라:<40} 표본 부족")
            continue
        나 = sum(1 for x in 칸 if x["_20"] > 0) / len(칸) * 100
        분포 = []
        for s in range(200):
            r = _rnd.Random(9000 + s)
            뽑 = r.sample(바탕칸, len(칸))
            분포.append(sum(1 for v in 뽑 if v > 0) / len(뽑) * 100)
        분포.sort()
        위 = sum(1 for v in 분포 if v < 나)
        상위 = (1 - 위 / len(분포)) * 100
        # ⚠️⚠️ **2026-09-20** — 25% 는 **무작위로도 4개 중 1개가 통과**한다.
        #    조합을 수백 개 훑는 판에서 거르개 구실을 거의 못 했다 → 10% 로 조인다
        든다 = 상위 <= 10
        print(f"  {라:<40}{len(칸):>8,}건  나 {나:.1f}%  "
              f"무작위 중앙 {분포[100]:.1f}% · 가장 좋음 {분포[-1]:.1f}%  "
              f"→ 상위 {상위:.0f}%  {'✅' if 든다 else '❌'}")
        통과표.setdefault(라, {})["C"] = 든다

    # ── D 오차 ──
    print("\n" + "=" * 108)
    print("  D 오차 — 산 값이 흔들려도 버티나")
    print("=" * 108)
    print(머2)
    for 오차 in (0.0, 0.3, 0.5, 1.0):
        print(f"\n   [오차 ±{오차}%p]")
        기칸 = _지금칸
        기점 = 점수([dict(x, _20=앞수익(x, 20, 오차, 1)) for x in 기칸])
        줄("지금 규칙", 기점)
        for 라, fn in 도전자[1:]:
            칸 = [dict(x, _20=앞수익(x, 20, 오차, 1)) for x in 사건 if fn(x)]
            줄(라, 점수(칸), 기점)

    # ── E 문턱 자리 ──
    print("\n" + "=" * 108)
    print("  E 문턱 자리 — 조금 옮겨도 버티나 (한 자리에서만 좋으면 과적합)")
    print("=" * 108)
    print(머2)
    print("\n   [볼린저 120일 문턱]")
    for 문 in (-1.0, -1.25, -1.5, -1.75, -2.0):
        줄(f"볼린저 120일 {문}σ",
           점수([x for x in 사건
                 if 재무통과(x) and 대금통과(x) and 크기통과(x)
                 and 있(x, "볼120") and x["볼120"] <= 문]))
    print("\n   [낙폭 120일 문턱 (20일 -10% 와 함께)]")
    for 문 in (-10, -15, -20, -25, -30):
        줄(f"낙폭 120일 {문}%",
           점수([x for x in 사건
                 if 재무통과(x) and 대금통과(x) and 크기통과(x)
                 and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0
                 and 있(x, "낙120") and x["낙120"] <= 문]))
    print("\n   [크기 해제 — 시총 구간별]")
    for 라, lo, hi in (("100~300억", 100, 300), ("300~500억", 300, 500),
                       ("500~2,000억", 500, 2000),
                       ("2,000~1조", 2000, 10000), ("1조 이상", 10000, 9e9)):
        줄(f"시총 {라}",
           점수([x for x in 사건
                 if 재무통과(x) and 대금통과(x)
                 and x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0
                 and lo <= x["시총억"] < hi]))

    # ── 판정 ──
    # ══ L·M·N·O ⭐⭐ **OR 로 더한다** (203차 · 2026-09-10) ══
    print("\n" + "=" * 108)
    print("  L ⭐⭐ **기존 규칙 OR 새 규칙** — 바꾸는 게 아니라 **더한다**")
    print("     사용자: 「기존 규칙, 새로운 규칙 **둘 중 하나만 부합해도 다 후보로 나오는거!**」")
    print("     ⚠️ 판정 기준: **기회가 늘고**(100%↑) 승률이 **안 떨어지면**(-0.5%p 이내) 쓸 만하다")
    print("=" * 108)

    def _낙60(x, 문):
        n = x.get("낙폭60")
        return (재무통과(x) and 대금통과(x) and 크기통과(x)
                and x["볼린저"] <= -1.0 and n is not None and n <= 문)

    def _둘다(x):
        n = x.get("낙폭60")
        return (지금(x) and n is not None and n <= -20)

    def _규모규칙(x):
        """202차 J절 — 300~800억 · 800~2,000억 둘 다 볼120 -1.0σ · 낙20 -20%"""
        s = x.get("시총억") or 0
        if not (300 <= s < 2000):
            return False
        b = x.get("볼120")
        n = x.get("낙폭20")
        if b is None:
            return False
        return b <= -1.0 and n is not None and n <= -20

    _기준 = 점수(_지금칸)
    print(f"\n  {'설정':<44}{'건수':>9}{'1년에':>8}{'이김':>9}{'평균':>9}"
          f"{'기회':>8}{'차이':>8}")

    def _한줄(라, fn):
        칸 = [x for x in 사건 if fn(x)]
        r = 점수(칸)
        if not r or not _기준:
            print(f"  {라:<44}{'표본 부족':>25}")
            return None
        기 = r[2] / _기준[2] * 100
        차 = r[0] - _기준[0]
        표 = ""
        if 기 >= 100 and 차 >= -0.5:
            표 = "  ⭐"
        print(f"  {라:<44}{r[2]:>9,}{r[2]/해수:>8.0f}{r[0]:>8.1f}%"
              f"{r[1]:>+9.2f}{기:>7.0f}%{차:>+7.1f}p{표}")
        return (r, 기, 차)

    _한줄("[견줌] 지금 규칙", 지금)
    print()
    _한줄("L-1 기존 OR **낙60 -20%**", lambda x: 지금(x) or _낙60(x, -20))
    _한줄("L-2 기존 OR **낙60 -30%**", lambda x: 지금(x) or _낙60(x, -30))
    _한줄("L-3 기존 OR (20일-10% AND 60일-20%)", lambda x: 지금(x) or _둘다(x))
    print()
    print("  M ⭐ **규모 규칙**을 더하면 (202차 J절)")
    _한줄("M-1 기존 OR **규모규칙**", lambda x: 지금(x) or _규모규칙(x))
    print()
    print("  N ⭐ **다 더하면**")
    _한줄("N-1 기존 OR 낙60-30% OR 규모",
          lambda x: 지금(x) or _낙60(x, -30) or _규모규칙(x))
    _한줄("N-2 기존 OR 낙60-20% OR 규모",
          lambda x: 지금(x) or _낙60(x, -20) or _규모규칙(x))
    print()
    print("  ⚠️ ⭐ 는 **기회가 늘고 승률이 안 떨어진** 것이다.")
    print("     이 중에서 고른 뒤 아래 4관문 결과를 같이 본다")

    # ══ ⭐⭐ 214차 — **OR·AND 를 여러 개 겹친다** ══
    print("\n" + "=" * 108)
    print("  214차 · ⭐⭐ **OR·AND 를 여러 개 겹친다**")
    print("     사용자: 「조합에서 **OR도 하고 AND도 하고 다 해본거야?**」")
    print("     -> 209차는 **하나씩만** 했다. 여기서 **여러 개**를 겹친다")
    print("     ⚠️ 판정: 기회 절반 이상 · 승률 +3%p · **네 구간 다** 같은 방향")
    print("=" * 108)

    _기214 = 점수(_지금칸)
    구간들 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
              ("2023~2026", "2023", "2026"))

    def _재기(라, fn, 조용=False):
        칸 = [x for x in 사건 if fn(x)]
        r = 점수(칸)
        if not r or not _기214:
            if not 조용:
                print(f"  {라:<46}{'표본 부족':>24}")
            return None
        기 = r[2] / _기214[2] * 100
        차 = r[0] - _기214[0]
        # 구간마다 같은 방향인가
        방향 = []
        for _, a, b in 구간들:
            c1 = 점수([x for x in 칸 if a <= x["해"] <= b])
            c0 = 점수(_지금사이(a, b))   # ⭐ 미리 나눠 둔 것 (전과 같은 값)
            if c1 and c0:
                방향.append(c1[0] - c0[0])
        고름 = (len(방향) == len(구간들) and all(v > 0 for v in 방향))
        되나 = (기 >= 50 and 차 >= 3 and 고름)
        if not 조용:
            표 = "  ⭐ **된다**" if 되나 else ("  ~" if 차 >= 3 else "")
            방말 = " ".join(f"{v:+.0f}" for v in 방향)
            print(f"  {라:<46}{r[2]:>9,}{r[2]/해수:>7.0f}{r[0]:>7.1f}%"
                  f"{기:>7.0f}%{차:>+7.1f}p  [{방말}]{표}")
        return (r, 기, 차, 되나)

    def 시낙(x, 문):
        return 있(x, "시장낙폭") and x["시장낙폭"] <= 문

    def 볼15(x):
        return (재무통과(x) and 대금통과(x) and 크기통과(x)
                and x["볼린저"] <= -1.5 and x["낙폭20"] <= -5.0)

    def 낙60(x, 문):
        return (재무통과(x) and 대금통과(x) and 크기통과(x)
                and x["볼린저"] <= -1.0
                and 있(x, "낙폭60") and x["낙폭60"] <= 문)

    def 회전(x, 문):
        시 = x.get("시총억") or 0
        대 = x.get("대금억") or 0
        return (대 / 시 * 100) <= 문 if 시 > 0 else False

    머214 = (f"  {'설정':<46}{'건수':>9}{'1년에':>7}{'이김':>7}"
             f"{'기회':>7}{'차이':>7}  [구간별]")

    # ── A OR 를 하나씩 더한다 ──
    print("\n  ── A ⭐ **OR 를 하나씩 더한다** (탐욕적) ──")
    print(머214)
    _재기("[견줌] 지금 규칙", 지금)
    쌓 = [("시장낙폭≤-7%", lambda x: 시낙(x, -7))]
    _재기("+ 시장낙폭≤-7%", lambda x: 지금(x) or 시낙(x, -7))
    _재기("+ 시장낙폭≤-7% + 볼20-1.5σ",
          lambda x: 지금(x) or 시낙(x, -7) or 볼15(x))
    _재기("+ 시장낙폭≤-7% + 볼20-1.5σ + 낙60-30%",
          lambda x: 지금(x) or 시낙(x, -7) or 볼15(x) or 낙60(x, -30))
    _재기("+ 시장낙폭≤-7% + 낙60-30%",
          lambda x: 지금(x) or 시낙(x, -7) or 낙60(x, -30))
    _재기("+ 볼20-1.5σ 만", lambda x: 지금(x) or 볼15(x))
    _재기("+ 낙60-30% 만", lambda x: 지금(x) or 낙60(x, -30))

    # ── B AND 필터를 평소에도 ──
    print("\n  ── B ⭐ **AND 필터를 평소에도** (폭락일 말고 늘) ──")
    print("     213차: 폭락일엔 회전율 3%↓ 가 앞뒤 둘 다 +4.9%p 였다."
          " **평소에도 그런가**")
    print(머214)
    for 문 in (2, 3, 4, 6):
        _재기(f"지금 규칙 AND 회전율 {문}%↓",
              lambda x, a=문: 지금(x) and 회전(x, a))

    # ── C OR 조합 + AND 필터 ──
    print("\n  ── C ⭐ **OR 조합 + AND 필터** 섞기 ──")
    print(머214)
    for 문 in (3, 4, 6):
        _재기(f"(기존 OR 시장낙폭≤-7%) AND 회전율 {문}%↓",
              lambda x, a=문: (지금(x) or 시낙(x, -7)) and 회전(x, a))
    _재기("(기존 OR 시장낙폭≤-7% OR 볼20-1.5σ) AND 회전율 3%↓",
          lambda x: (지금(x) or 시낙(x, -7) or 볼15(x)) and 회전(x, 3))

    # ── D AND 를 둘 겹치기 ──
    print("\n  ── D ⭐ **AND 를 둘 겹치기** (209차에서 안 한 것) ──")
    print(머214)
    쌍 = (("회전율 3%↓", lambda x: 회전(x, 3)),
          ("잉여금≥30", lambda x: 있(x, "잉여금") and x["잉여금"] >= 30),
          ("ROE≥5", lambda x: 있(x, "ROE") and x["ROE"] >= 5),
          ("대금≥3억", lambda x: (x.get("대금억") or 0) >= 3),
          ("시총≥800억", lambda x: (x.get("시총억") or 0) >= 800))
    import itertools as _it
    for (라1, f1), (라2, f2) in _it.combinations(쌍, 2):
        _재기(f"지금 AND {라1} AND {라2}",
              lambda x, a=f1, b=f2: 지금(x) and a(x) and b(x))

    # ══ ⭐⭐ 218차 — **볼린저 창을 늘린다** ══
    print("\n" + "=" * 108)
    print("  218차 · ⭐⭐ **볼린저 창을 늘린다** (20일 -> 40/60/120일)")
    print("     네 시험이 같은 곳을 가리킨다: 191·193·214차(낙폭 60일) +")
    print("     216-2차(**볼120 -0.5σ · 낙60 -30%** 가 앞 기간 144칸 중 1위)")
    print("     ⚠️ 216-2차는 **재무 조건이 없는** 잣대였다. 여기서 정식으로 다시 잰다")
    print("     ⚠️ 판정: 기회 절반 이상 · 승률 +3%p · **세 구간 다** 같은 방향")
    print("=" * 108)

    def 볼낙(x, bw, bt, nw, nt):
        r"""재무·대금·크기를 챙기고 **볼 창 bw** 와 **낙 창 nw** 로 거른다."""
        if not (재무통과(x) and 대금통과(x) and 크기통과(x)):
            return False
        b = x.get(f"볼{bw}")
        n = x.get(f"낙{nw}")
        return (b is not None and b <= bt and n is not None and n <= nt)

    머218 = (f"  {'설정':<48}{'건수':>9}{'1년에':>7}{'이김':>7}"
             f"{'기회':>7}{'차이':>7}  [구간별]")

    # ── A 볼린저 창 늘리기 (대체) ──
    print("\n  ── A ⭐⭐ **볼린저 창 늘리기 (대체)** ──")
    print(머218)
    _재기("[견줌] 지금 규칙 (볼20 -1.0σ · 낙20 -10%)", 지금)
    for bw in (20, 40, 60, 120):
        for nw, nt in ((60, -30), (60, -20)):
            _재기(f"볼{bw} -0.5σ · 낙{nw} {nt}%",
                  lambda x, a=bw, b=nw, c=nt: 볼낙(x, a, -0.5, b, c))

    # ── B OR 로 (더하기) ──
    print("\n  ── B ⭐⭐ **볼린저 창 늘린 것을 OR 로** (더하기) ──")
    print(머218)
    for bw in (60, 120):
        for nw, nt in ((60, -30), (60, -20)):
            _재기(f"기존 **OR** 볼{bw} -0.5σ · 낙{nw} {nt}%",
                  lambda x, a=bw, b=nw, c=nt: 지금(x) or 볼낙(x, a, -0.5, b, c))
    _재기("기존 OR 볼120 -0.5σ·낙60 -30% OR 시장낙폭≤-7%",
          lambda x: (지금(x) or 볼낙(x, 120, -0.5, 60, -30)
                     or (있(x, "시장낙폭") and x["시장낙폭"] <= -7)))

    # ── C 216-2차 1위를 정식 틀에서 ──
    print("\n  ── C ⭐⭐ **216-2차 1위**를 정식 틀에서 ──")
    print("     216-2차: 볼120 -0.5σ · 낙60 -30% -> 뒤 기간 69.1% · 기회 115%")
    print("     여기서는 **재무 조건까지 걸고** 다시 잰다")
    print(머218)
    _재기("⭐ 볼120 -0.5σ · 낙60 -30% (재무 걸고)",
          lambda x: 볼낙(x, 120, -0.5, 60, -30))
    _재기("   같은 것 + 회전율 3%↓",
          lambda x: 볼낙(x, 120, -0.5, 60, -30) and 회전(x, 3))
    _재기("   같은 것 AND 볼20 도 -1.0σ↓",
          lambda x: (볼낙(x, 120, -0.5, 60, -30)
                     and x["볼린저"] <= -1.0))

    # ── D 볼 창 x 문턱 격자 ──
    print("\n  ── D ⭐ **볼 창 x 문턱 격자** — 어디가 봉우리인가 ──")
    print(머218)
    for bw in (40, 60, 120):
        for bt in (-0.5, -1.0, -1.5):
            _재기(f"볼{bw} {bt:+.1f}σ · 낙60 -30%",
                  lambda x, a=bw, b=bt: 볼낙(x, a, b, 60, -30))

    # ══ ⭐⭐ 219차 — **「때」 조건을 파고든다** ══
    print("\n" + "=" * 108)
    print("  219차 · ⭐⭐ **「때」 조건을 파고든다**")
    print("     통한 것 둘은 **때** 조건이었다 (시장낙폭 +10.2%p · 금리 인하 +0.7%p)")
    print("     실패한 것은 **전부 종목** 조건이었다 (재료 22가지·섹터·규모·무리·볼창)")
    print("     ⚠️ 판정: 기회 절반 이상 · 승률 +3%p · **세 구간 다** 같은 방향")
    print("=" * 108)

    머219 = (f"  {'설정':<48}{'건수':>9}{'1년에':>7}{'이김':>7}"
             f"{'기회':>7}{'차이':>7}  [구간별]")

    # ── A 지수 낙폭 창 바꾸기 ──
    print("\n  ── A ⭐ **지수 낙폭 창을 바꾼다** ──")
    print("     20일 -7% 가 지금까지 최고다. **다른 창**이 더 나은가")
    print(머219)
    _재기("[견줌] 지금 규칙", 지금)
    _재기("[견줌] 기존 OR 시장낙폭 20일≤-7%",
          lambda x: 지금(x) or (있(x, "시장낙폭") and x["시장낙폭"] <= -7))
    for w in (5, 10, 40, 60):
        for 문 in (-3, -5, -7, -10, -15):
            _재기(f"기존 OR 지수 {w}일 낙폭 ≤{문}%",
                  lambda x, a=w, b=문: (지금(x) or ((_때(x, "낙", a) is not None)
                                                   and _때(x, "낙", a) <= b)))

    # ── B 지수가 이동평균 아래 ──
    print("\n  ── B ⭐ **지수가 이동평균 아래** ──")
    print(머219)
    for w in (20, 60, 120):
        for 문 in (0, -3, -5, -8):
            _재기(f"기존 OR 지수가 {w}일선 대비 {문}%↓",
                  lambda x, a=w, b=문: (지금(x) or ((_때(x, "평", a) is not None)
                                                   and _때(x, "평", a) <= b)))

    # ── C 시장 변동성 ──
    print("\n  ── C ⭐ **시장 변동성이 높은 날** (한국판 공포지수) ──")
    print(머219)
    for 문 in (20, 25, 30, 40):
        _재기(f"기존 OR 지수 20일 변동성 {문}%↑",
              lambda x, b=문: (지금(x) or ((_때(x, "변", 20) is not None)
                                          and _때(x, "변", 20) >= b)))

    # ── D 연속 하락 ──
    print("\n  ── D ⭐ **연이어 내린 날수** ──")
    print(머219)
    for 문 in (3, 4, 5, 6):
        _재기(f"기존 OR 지수가 **{문}일 연속** 내림",
              lambda x, b=문: 지금(x) or (_때(x, "연") or 0) >= b)

    # ── E 「때」 둘을 겹친다 ──
    print("\n  ── E ⭐ **「때」 조건 둘을 겹친다** ──")
    print("     ⚠️ 214차에서 시장낙폭에 **종목** 조건을 얹으면 물이 탔다.")
    print("        **때 조건끼리**는 어떤가")
    print(머219)

    def 시낙7(x):
        return 있(x, "시장낙폭") and x["시장낙폭"] <= -7

    _재기("기존 OR 시낙7 **OR** 지수 60일≤-15%",
          lambda x: (지금(x) or 시낙7(x)
                     or ((_때(x, "낙", 60) is not None) and _때(x, "낙", 60) <= -15)))
    _재기("기존 OR 시낙7 **OR** 변동성 30%↑",
          lambda x: (지금(x) or 시낙7(x)
                     or ((_때(x, "변", 20) is not None) and _때(x, "변", 20) >= 30)))
    _재기("기존 OR (시낙7 **AND** 변동성 25%↑)",
          lambda x: (지금(x) or (시낙7(x) and (_때(x, "변", 20) or 0) >= 25)))
    _재기("기존 OR (시낙7 **AND** 5일 낙폭 ≤-3%)",
          lambda x: (지금(x) or (시낙7(x) and (_때(x, "낙", 5) is not None)
                                 and _때(x, "낙", 5) <= -3)))
    _재기("기존 OR (시낙7 **AND** 5일 낙폭 ≥0%)  <- 바닥 다지는 중",
          lambda x: (지금(x) or (시낙7(x) and (_때(x, "낙", 5) is not None)
                                 and _때(x, "낙", 5) >= 0)))

    # ── F 반영용 확정 ──
    print("\n  ── F ⭐⭐ **반영용** — 「시장낙폭 OR」이 정확히 무슨 조건인가 ──")
    print("     214차 도전자의 뒤쪽 가지는 **크기통과를 안 거친다**.")
    print("     사건 좁히기(재무·대금·시총 100~3000억·어느 정도 빠짐)에만 기댔다.")
    print("     record_pick 에 옮기려면 **한 줄씩 명시**해야 한다. 여기서 확정한다")
    print(머219)
    _재기("① 214차 그대로 (뒤 가지에 조건 없음)",
          lambda x: 지금(x) or 시낙7(x))
    _재기("② 뒤 가지에 **크기통과(500~2000억)** 걸기",
          lambda x: 지금(x) or (시낙7(x) and 크기통과(x)))
    _재기("③ 뒤 가지에 **시총 300~2000억** 걸기 (지금 브리핑 범위)",
          lambda x: (지금(x) or (시낙7(x) and 300 <= x["시총억"] < 2000)))
    _재기("④ ③ + **볼20 ≤-0.5σ** 도 걸기",
          lambda x: (지금(x) or (시낙7(x) and 300 <= x["시총억"] < 2000
                                 and x["볼린저"] <= -0.5)))
    _재기("⑤ ③ + **볼20 ≤-1.0σ** 도 걸기",
          lambda x: (지금(x) or (시낙7(x) and 300 <= x["시총억"] < 2000
                                 and x["볼린저"] <= -1.0)))
    _재기("⑥ ③ + **낙20 ≤-5%** 도 걸기",
          lambda x: (지금(x) or (시낙7(x) and 300 <= x["시총억"] < 2000
                                 and x["낙폭20"] <= -5)))
    _재기("⑦ ③ + 볼20≤-0.5σ + 낙20≤-5%",
          lambda x: (지금(x) or (시낙7(x) and 300 <= x["시총억"] < 2000
                                 and x["볼린저"] <= -0.5 and x["낙폭20"] <= -5)))
    _재기("⑧ ⑦ + **회전율 3%↓** (폭락일 필터)",
          lambda x: (지금(x) or (시낙7(x) and 300 <= x["시총억"] < 2000
                                 and x["볼린저"] <= -0.5 and x["낙폭20"] <= -5
                                 and 회전(x, 3))))
    print("\n     ⇒ **기회를 지키면서 승률이 가장 높은 줄**을 반영한다")

    # ══ ⭐ 220차 — **변동성을 일간 기준으로 다시** ══
    print("\n" + "=" * 108)
    print("  220차 · ⭐ **변동성 다시 재기** (219차 C절은 버그였다)")
    print("     `변동성()` 은 **연율화 안 된 일간 표준편차(%)** 를 돌려준다.")
    print("     코스닥 일간 표준편차는 보통 **1~2%** 인데 문턱을 20~40% 로 걸었다")
    print("     -> 네 줄 다 한 번도 안 걸렸다. 여기서 **일간 기준**으로 고친다")
    print("=" * 108)
    _표본 = [_때(x, "변", 20) for x in 사건[:8000]]
    _표본 = sorted(v for v in _표본 if v is not None)
    if _표본:
        print(f"\n     실제 값: 가운데 {_표본[len(_표본)//2]:.2f}% ·"
              f" 위 10% {_표본[int(len(_표본)*0.9)]:.2f}% ·"
              f" 맨 위 {_표본[-1]:.2f}%")
    print("\n" + 머219)
    _재기("[견줌] 지금 규칙", 지금)
    for 문 in (1.0, 1.5, 2.0, 2.5, 3.0):
        _재기(f"기존 OR 지수 20일 변동성 **{문}%↑** (일간)",
              lambda x, b=문: (지금(x) or ((_때(x, "변", 20) is not None)
                                          and _때(x, "변", 20) >= b)))
    _재기("기존 OR (시낙7 AND 변동성 2.0%↑)",
          lambda x: (지금(x) or (_시낙7(x)
                                 and (_때(x, "변", 20) or 0) >= 2.0)))

    # ══ ⭐⭐⭐ 221차 — **자본 시뮬로 다시 확인** ══
    print("\n" + "=" * 108)
    print("  221차 · ⭐⭐⭐ **자본 시뮬로 다시 확인**")
    print("     ⚠️ 220차까지는 전부 **평균 수익**으로 쟀다.")
    print("        「평균 수익은 돈이 아니다」 · 「걷기검증은 자본 시뮬로」")
    print("     ⚠️ gate7 의 `시뮬` 은 **정의만 되고 한 번도 안 쓰였다**")
    print("     ⚠️ 이번엔 특히 위험하다 — 기회가 **4배**로 늘어도")
    print("        **하루에 사는 건 4종목**이다. 고르는 방법이 승률을 좌우한다")
    print("        (211~213차: 폭락일엔 「갭 깊은 순」이 무작위보다 **-11.8%p**)")
    print("=" * 108)

    _바탕c = {"상대갭": _밑상대갭, "목표": 20,
              "최대보유": R.앞몫기한, "비중": 0.20,
              "하루상한": (lambda 골: R.오늘최대종목(
                  next((z.get("시장낙폭") for z in 골
                        if z.get("시장낙폭") is not None), None))),
              # ⭐ ㉥ (2026-09-21 반영) — 그날 상한을 rule_def 가 정한다.
              #    맨 위 후보의 시장 지수를 본다 (실전 quant_cards 와 같은 자리)
              # ⚠️⚠️ 2026-09-16 pairs7: 시뮬이 여기 시총상한(2,000)으로 **㉣ 큰 회사를 다시 걸러냈다** — Ⓗ 가 소형만(2.541억)으로 찍혀
              #    「지금 규칙」 견줌이 실전(소형 세 갈래 + 큰 회사 섹터 갈래 = 2.796억)과 달랐다. 크기 문은 _H 가 갈래마다 지키므로
              #    ㉣ 이 켜져 있으면 시뮬 쪽 상한은 연다 (RULE_HI 를 주면 그 값 · 옛 판 재현용)
              "시총하한": R.시총하한억, "시총상한": (999999 if (R.섹터규칙_큰회사 and not os.environ.get("RULE_HI")) else _규칙크기상한),
              "대금하한": R.대금하한억, "거래량하한": 0, "회전율하한": 0.0,
              # ⚠️⚠️ **여기에 "나눔"을 두지 마라** (2026-09-14).
              #    기본값으로 박아 두니 `c.get("나눔")` 이 늘 참이라
              #    `BASE_SELL`(_밑몫) 이 **한 번도 안 먹혔다.**
              #    G판이 머리글엔 「100% 목표 +40% 90일」이라 찍혔는데
              #    결과는 A판과 한 자리도 안 달랐다.
              #    현행값(반 +15%/40일 · 반 +40%/90일)은 시뮬 안에서 준다
              }

    def _c(거름, **바꿀):
        z = dict(_바탕c)
        z["거름"] = 거름
        z.update(바꿀)
        return z

    # ── 후보 조건들 (220차에서 4관문을 다 지난 것) ──
    def _시낙(x, w, 문):
        v = _때(x, "낙", w)
        return v is not None and v <= 문

    def _시평(x, w, 문):
        v = _때(x, "평", w)
        return v is not None and v <= 문

    # ⭐⭐ **밑규칙의 마지막 갈래** — BASE_RULE 이 여기 하나에서 갈린다
    #    (2026-09-14 밤). 전에는 `_H` 안에만 있어서 아래 넷이 **Ⓗ 로 샜다** —
    #    T판(BASE_RULE=G)이 반은 Ⓖ, 반은 Ⓗ 로 돌았다. 섞인 판이었다
    _밑글자 = "Ⓖ" if _밑규칙 in ("G", "Ⓖ") else "Ⓗ"

    def _밑끝갈래(x):
        """Ⓗ 면 지수 60일 ≤-10% · Ⓖ 면 지수가 120일선 -8%↓"""
        return (_지평(x, 120, -8) if _밑규칙 in ("G", "Ⓖ")
                else _시낙(x, 60, -10))

    def _시7(x):
        return x.get("시장낙폭") is not None and x["시장낙폭"] <= -7

    def _빠짐(x):
        return x["낙폭20"] <= -5

    # ══ ⭐⭐⭐ **자르는 순서** — 실전과 같게 ══ (2026-09-11 · 250차)
    #    ⚠️ 여기 두는 이유: 첫 `시뮬()` 호출이 바로 아래다.
    #       `_시7` 보다 **뒤**, 첫 호출보다 **앞**이어야 NameError 가 안 난다
    def _겹친수(x):
        r"""기존·섹터·시장 중 **몇 개**에 걸렸나 (실전 `record_pick` 의 정렬 키)

        ⚠️ 이제 **모든 시뮬**이 정렬 키로 이걸 부른다 (하루 수십 개 x 1,883일
           x 시뮬 수백 번). 사건마다 **한 번만** 재서 사건에 담아 둔다 —
           사건은 시뮬이 돌아도 다시 만들어지지 않으므로 캐시가 유효하다
        """
        v = x.get("_겹친")
        if v is None:
            v = (0 if not 문통과(x) else
                 ((1 if (x["볼린저"] <= R.볼린저문턱
                         and x["낙폭20"] <= R.낙폭20문턱) else 0)
                  + (1 if 섹터맞나(x) else 0)
                  # ⚠️ 2026-09-14 밤: 여기도 `_시낙(x,60,-10)` 이 박혀 있었다.
                  #    `_겹친` 은 **고르는 순서**(겹친 수 → 낙폭)를 정하는 값이라
                  #    갈래 정의가 어긋나면 **순서를 잘못 잰다**
                  + (1 if (_시7(x) or _밑끝갈래(x)) else 0)))
            x["_겹친"] = v  # [그날까지] 갈래 몇 개에 걸렸나 — 그날 값만 본다 (고르는 순서용)
        return v

    def _기본자르기(z):
        r"""**실전과 같은 순서** — 걸린 규칙 수가 많은 것 먼저,
        같은 층에서 깊게 빠진 순 (`record_pick` · 206차 P-2)

        ⚠️⚠️ 2026-09-11 까지 시뮬은 **낙폭 깊은 순만** 썼다.
           후보가 40개를 넘는 날(1,883일 중 **318일**)에 누가 잘리는지가
           실전과 달랐다. 250차로 재보니 돈은 7% 적지만 낙폭이
           -8.0% -> **-6.3%** 로 줄고 돈÷낙폭이 6.26 -> **7.79** 로 올랐다.
           앞뒤가 엇갈려(앞 -13% · 뒤 +8%) 어느 쪽이 낫다고는 못 한다.
           ⇒ **실전을 바꾸지 않고 시뮬을 실전에 맞춘다**
        """
        return (-_겹친수(z), z["낙폭20"])

    # 옛 순서 — 250차에서 견줌으로 쓴다
    def _옛자르기(z):
        return z["낙폭20"]

    조건들 = [
        ("[견줌] 지금 규칙", 지금),
        ("Ⓙ 기존 OR (시낙7 AND 낙20≤-5%)",
         lambda x: 지금(x) or (_시7(x) and _빠짐(x))),
        ("Ⓚ Ⓙ + 120일선-8%↓ 도",
         lambda x: (지금(x) or ((_시7(x) or _시평(x, 120, -8)) and _빠짐(x)))),
        ("Ⓖ 기존 OR 시낙7 OR 120일선-8%↓ (낙폭 조건 없이)",
         lambda x: 지금(x) or _시7(x) or _시평(x, 120, -8)),
        ("Ⓗ 기존 OR 시낙7 OR 지수60일≤-10%",
         lambda x: 지금(x) or _시7(x) or _시낙(x, 60, -10)),
        ("Ⓓ 기존 OR 120일선-8%↓",
         lambda x: 지금(x) or _시평(x, 120, -8)),
        ("Ⓐ 기존 OR 지수60일≤-10% (평균 1위)",
         lambda x: 지금(x) or _시낙(x, 60, -10)),
    ]

    # ── A 후보 조건별 자본 시뮬 ──
    print("\n  ── A ⭐⭐⭐ **후보 조건별 자본 시뮬** ──")
    print("     ⚠️ **끝 자산**이 답이다. 평균 수익이 아니라 **돈**")
    print(머)
    _기시 = None
    for 라, fn in 조건들:
        r = 시뮬(_c(fn))
        if _기시 is None:
            _기시 = r
        표(r, 라, None if r is _기시 else _기시)

    # ── B 고르는 순서 ──
    print("\n  ── B ⭐⭐ **고르는 순서** (후보가 4배로 늘면 이게 좌우한다) ──")
    print("     지금은 **갭 큰 순**이다. 211~213차에서 폭락일엔 이게 나빴다")
    print(머)
    import random as _r3
    _고름들 = [
        ("갭 큰 순 (지금)", None),
        ("무작위", lambda z: _r3.Random(hash(z["code"]) & 0xffff).random()),
        ("회전율 **낮은** 순", lambda z: z.get("회전율") or 0),
        ("회전율 높은 순", lambda z: -(z.get("회전율") or 0)),
        ("**덜** 빠진 순", lambda z: -z["낙폭20"]),
        ("많이 빠진 순", lambda z: z["낙폭20"]),
        ("시총 **큰** 순", lambda z: -(z.get("시총억") or 0)),
        ("시총 작은 순", lambda z: z.get("시총억") or 0),
    ]
    _최선 = 조건들[2][1]      # Ⓚ 로 고정하고 순서만 바꾼다
    print("     (후보 조건은 **Ⓚ 로 고정**하고 순서만 바꾼다)")
    _기고 = None
    for 라, g in _고름들:
        r = 시뮬(_c(_최선, **({"고르기": g} if g else {})))
        if _기고 is None:
            _기고 = r
        표(r, 라, None if r is _기고 else _기고)

    # ── C 걷기 검증 ──
    print("\n  ── C ⭐⭐ **걷기 검증** — 앞에서 고르고 **뒤에서** 쓴다 ──")
    print("     ⚠️ 「걷기검증은 자본 시뮬로」 — 평균으로 하면 통과한 것도 무너진다")
    for 시작, 끝, 라2 in (("2010", "2020", "앞 2010~2020"),
                          ("2021", None, "**뒤 2021~2026**")):
        print(f"\n   [{라2}]")
        print(머)
        _기2 = None
        for 라, fn in 조건들:
            r = 시뮬(_c(fn), 시작년=시작, 끝년=끝)
            if _기2 is None:
                _기2 = r
            표(r, 라, None if r is _기2 else _기2)

    # ── D 하루 상한 ──
    print("\n  ── D ⭐ **하루 상한** — 후보가 늘었으니 더 사도 되나 ──")
    print(머)
    _기d = None
    for n in (3, 4, 5, 6, 8):
        r = 시뮬(_c(_최선, 하루상한=n))
        if _기d is None:
            _기d = r
        표(r, f"하루 최대 {n}종목" + (" (지금)" if n == 4 else ""),
          None if r is _기d else _기d)

    print("\n     ⇒ **끝 자산**과 **낙폭**을 같이 보고 정한다."
          " 돈이 늘어도 낙폭이 깊어지면 못 버틴다")

    # ══ ⭐⭐⭐ 222차 — **Ⓗ 로 고정하고 운용을 다시** ══
    print("\n" + "=" * 108)
    print("  222차 · ⭐⭐⭐ **Ⓗ 로 고정하고 운용을 다시 잰다**")
    print("     221차 B·D 절은 **Ⓚ 로 고정**하고 쟀는데 반영 후보가 **Ⓗ** 로 바뀌었다")
    print("     ⚠️ **비중은 아직 한 번도 안 쟀다.** 종목 수와 비중은")
    print("        **같이 움직이는 값**이다 (6종목 x 20% = 120% 는 불가능)")
    print("=" * 108)

    # ⚠️⚠️ **2026-09-11 전수조사 ③⑧ — 실전과 같게 고쳤다.**
    #    옛 Ⓗ:  지금(x) or _시7(x) or _시낙(x,60,-10)
    #      · 섹터 규칙이 **없었다**
    #      · 시장 갈래에 **재무·크기 문이 없어** 100~3,000억까지 들어왔다
    #    실전(record_pick 731~775)은 **공통 문을 먼저** 거치고
    #    그 다음 기존 OR 섹터 OR 시장이다 (화면 2장의 ①/② 와 같은 꼴)
    # ⭐ ㉤ 변동성·자사주 (2026-09-17 반영) — 판(13쌍 절)과 같은 정의. 자사주 표는 한 번만 읽는다
    _증자H = _NM._증자표() if R.변동성자사주_켬 else {}
    _자사H캐시 = {}

    def _자사H(x):
        k = (x["code"], x["인"])
        if k not in _자사H캐시:
            i = x["인"] - 1
            _자사H캐시[k] = _NM._증자재기(_증자H, x["code"], "자사주취득", 날[i], R.자사주창일, 날, i)
        return _자사H캐시[k]

    def _H(x):
        # ⭐ ㉣ (2026-09-16 반영) — 섹터규칙은 **크기 문 없이** (재무·대금만). 기존·시장 갈래는 문통과(크기 포함)
        if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
            return True
        if not 문통과(x):
            return False
        # ⭐ ㉤ (2026-09-17 반영) — 소형(문통과) AND 지수 20일 변동성 ≥ 문턱 AND 자사주 취득 60일
        if (R.변동성자사주_켬 and x.get("시장변동성") is not None
                and x["시장변동성"] >= R.시장변동성문턱 and _자사H(x) >= 1):
            return True
        # ⭐ BASE_RULE=G 면 마지막 갈래를 **120일선 −8%↓** 로 바꾼다 (2026-09-14 밤)
        _끝갈래 = _밑끝갈래(x)
        return ((x["볼린저"] <= R.볼린저문턱
                 and x["낙폭20"] <= R.낙폭20문턱)
                or 섹터맞나(x)
                or _시7(x) or _끝갈래)

    _H옛 = lambda x: 지금(x) or _시7(x) or _시낙(x, 60, -10)   # noqa: E731

    # ── A 비중 x 하루 상한 격자 ──
    print(f"\n  ── A ⭐⭐⭐ **비중 x 하루 상한** 격자 ({_밑글자} 고정) ──")
    print("     ⚠️ 한 줄에서 **비중 x 상한 = 자산의 몇 %** 인지 같이 본다")
    print(f"\n  {'비중':>6}{'상한':>6}{'만재':>7}"
          f"{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}")
    _최고 = None
    for 비중값 in (0.10, 0.15, 0.20, 0.25, 0.33, 0.50):
        for n in (2, 3, 4, 5, 6):
            r = 시뮬(_c(_H, 비중=비중값, 하루상한=n))
            점 = r["연"] / max(abs(r["낙"]), 3.0)
            만 = 비중값 * n * 100
            표시 = ""
            if 만 > 100:
                표시 = "  (만재 100%↑)"
            if _최고 is None or r["끝"] > _최고[0]:
                _최고 = (r["끝"], 비중값, n)
            지 = "  ← 지금" if (abs(비중값 - 0.20) < 1e-9 and n == 4) else ""
            print(f"  {비중값*100:>5.0f}%{n:>6}{만:>6.0f}%"
                  f"{r['끝']:>15,.0f}원{r['연']:>+8.2f}%{r['낙']:>7.1f}%"
                  f"{r['산']:>7}{점:>9.2f}{표시}{지}", flush=True)
    if _최고:
        print(f"\n     ⇒ 끝 자산 최고: **비중 {_최고[1]*100:.0f}% x "
              f"하루 {_최고[2]}종목** ({_최고[0]:,.0f}원)")

    # ── B 고르는 순서 다시 ──
    print("\n  ── B ⭐⭐ **고르는 순서** 다시 (Ⓗ 고정) ──")
    print(머)
    _기b2 = None
    for 라, g in _고름들:
        r = 시뮬(_c(_H, **({"고르기": g} if g else {})))
        if _기b2 is None:
            _기b2 = r
        표(r, 라, None if r is _기b2 else _기b2)

    # ── C 걷기 검증 (운용) ──
    print("\n  ── C ⭐⭐ **걷기 검증** — 앞에서 고른 운용이 **뒤에서도** 되나 ──")
    print("     ⚠️ 한쪽에서만 좋으면 우연이다")
    for 시작, 끝2, 라2 in (("2010", "2020", "앞 2010~2020"),
                           ("2021", None, "**뒤 2021~2026**")):
        print(f"\n   [{라2}]")
        print(머)
        _기c2 = None
        for 라, 비중값, n in (("비중20% x 4종목 (지금)", 0.20, 4),
                          ("비중20% x 3종목", 0.20, 3),
                          ("비중25% x 3종목", 0.25, 3),
                          ("비중25% x 4종목", 0.25, 4),
                          ("비중33% x 3종목", 0.33, 3),
                          ("비중15% x 5종목", 0.15, 5)):
            r = 시뮬(_c(_H, 비중=비중값, 하루상한=n), 시작년=시작, 끝년=끝2)
            if _기c2 is None:
                _기c2 = r
            표(r, 라, None if r is _기c2 else _기c2)
        print("\n   [같은 구간 · **고르는 순서**]")
        print(머)
        _기c3 = None
        for 라, g in (("갭 큰 순 (지금)", None),
                      ("많이 빠진 순", lambda z: z["낙폭20"]),
                      ("무작위", lambda z: _r3.Random(
                          hash(z["code"]) & 0xffff).random())):
            r = 시뮬(_c(_H, **({"고르기": g} if g else {})),
                     시작년=시작, 끝년=끝2)
            if _기c3 is None:
                _기c3 = r
            표(r, 라, None if r is _기c3 else _기c3)

    print("\n     ⇒ **앞뒤 둘 다** 이긴 것만 반영한다")

    # ══ ⭐⭐⭐ 237차 — **반영 후보를 자본 시뮬로** ══
    print("\n" + "=" * 108)
    print("  237차 · ⭐⭐⭐ **반영 후보를 자본 시뮬로**")
    print(f"     ⚠️ 사건 크기 상한 = **{_크기상한:,.0f}억** "
          "(SIZE_HI 로 조절 · 기본 3,000)")
    print("     ① 하루 3종목 — 222차에서 **이미 끝났다** (모든 비중대에서 1위)")
    print("     ② **볼60 대체** — 234차에서 세 규모대 전부 볼20보다 나았다")
    print("     ③ **시총 상한 풀기** — 230-A 에서 대형주가 가장 좋았다")
    print("=" * 108)

    def _볼60지금(x):
        r"""지금 규칙의 **볼20 을 볼60 으로** 바꾼 것"""
        return (재무통과(x) and 대금통과(x) and 크기통과(x)
                and 있(x, "볼60") and x["볼60"] <= -1.0
                and x["낙폭20"] <= -10.0)

    def _H60(x):
        r"""Ⓗ 의 「지금 규칙」 자리에 **볼60** 을 넣은 것"""
        return _볼60지금(x) or _시7(x) or _밑끝갈래(x)

    # ── A 볼60 대체 ──
    print("\n  ── A ⭐⭐ **볼60 대체** (234차) ──")
    print(머)
    _기237 = 시뮬(_c(_H))
    표(_기237, f"[견줌] {_밑글자} (볼20 · 지금)")
    표(시뮬(_c(_H60)), f"{_밑글자} 인데 **볼60**", _기237)
    표(시뮬(_c(lambda x: 지금(x) or _시7(x) or _밑끝갈래(x))),
      "  (같은 것 다시 · 검산)", _기237)
    표(시뮬(_c(_볼60지금)), "볼60 규칙 **혼자**", _기237)
    표(시뮬(_c(지금)), "볼20 규칙 **혼자** (지금)", _기237)

    # ── B 시총 상한 ──
    print("\n  ── B ⭐⭐⭐ **시총 상한** — 어디까지 열까 ──")
    print(f"     ⚠️ 사건 자체가 {_크기상한:,.0f}억에서 잘려 있다. "
          "그보다 큰 상한은 **뜻이 없다**")
    print(머)
    for _하, _상, _라 in ((300, 2000, "300~2,000억 (지금)"),
                          (300, 3000, "300~3,000억"),
                          (300, 5000, "300~5,000억"),
                          (300, 10000, "300억~1조"),
                          (300, 999999, "300억~**상한 없음**"),
                          (2000, 999999, "2,000억↑ **만**"),
                          (10000, 999999, "1조↑ **만**")):
        if _하 >= _크기상한:
            print(f"  {_라:<28}{'사건에 없다 (SIZE_HI 를 올려라)':>40}")
            continue
        표(시뮬(_c(_H, 시총하한=_하, 시총상한=_상)), _라, _기237)

    # ── C 셋을 합치면 ──
    print("\n  ── C ⭐⭐⭐ **셋을 합치면** (볼60 + 상한 + 3종목) ──")
    print(머)
    표(시뮬(_c(_H, 하루상한=3)), "Ⓗ + 하루 3종목", _기237)
    표(시뮬(_c(_H60, 하루상한=3)), "Ⓗ볼60 + 하루 3종목", _기237)
    _열 = min(999999, _크기상한)
    표(시뮬(_c(_H, 시총상한=_열, 하루상한=3)),
      f"Ⓗ + 상한 {_열:,.0f}억 + 3종목", _기237)
    표(시뮬(_c(_H60, 시총상한=_열, 하루상한=3)),
      f"Ⓗ볼60 + 상한 {_열:,.0f}억 + 3종목", _기237)

    # ── D 걷기 검증 ──
    print("\n  ── D ⭐⭐ **걷기 검증** — 앞뒤 둘 다 이겨야 반영한다 ──")
    for _시, _끝, _라2 in (("2010", "2020", "앞 2010~2020"),
                           ("2021", None, "**뒤 2021~2026**")):
        print(f"\n   [{_라2}]")
        print(머)
        _기d = 시뮬(_c(_H), 시작년=_시, 끝년=_끝)
        표(_기d, "[견줌] Ⓗ (지금)")
        표(시뮬(_c(_H60), 시작년=_시, 끝년=_끝), "Ⓗ 인데 볼60", _기d)
        표(시뮬(_c(_H, 하루상한=3), 시작년=_시, 끝년=_끝),
          "Ⓗ + 하루 3종목", _기d)
        표(시뮬(_c(_H, 시총상한=_열), 시작년=_시, 끝년=_끝),
          f"Ⓗ + 상한 {_열:,.0f}억", _기d)
        표(시뮬(_c(_H60, 시총상한=_열, 하루상한=3), 시작년=_시, 끝년=_끝),
          "셋 다", _기d)

    print("\n     ⇒ **앞뒤 둘 다** 이긴 것만 반영한다 "
          "(222차에서 Ⓖ·Ⓓ 가 뒤에서 무너졌다)")

    # ══ ⭐⭐⭐ 239차 — **제약 없는 자본 시뮬** ══
    print("\n" + "=" * 108)
    print("  239차 · ⭐⭐⭐ **제약 없는 자본 시뮬** (사용자 지적으로 고침)")
    print("     「**종목을 샀을 때 수익으로 계산해야지** 내 자산이 얼마가 있으니")
    print("      **종목에 제한을 둔다거나, 그래선 안 될 것 같아**」")
    print("     ✅ 남김: 자산의 몇 %씩(비중) · 하루 상한(관리 가능한 수)")
    print("     ❌ 뺌: **현금 제약** · **거래대금 1% 한도** · 1주 미만 건너뛰기")
    print("=" * 108)

    def _둘(라, c1, c2=None, 묶2=None):
        r"""제약 있는 판과 **없는 판**을 나란히 찍는다. c["시작년"] 이 있으면 그해부터 (㉤)"""
        _시y = c1.get("시작년")
        r1 = 시뮬(c1, 묶2=묶2, 시작년=_시y)
        c2 = c2 or dict(c1, 제약없음=True)
        r2 = 시뮬(c2, 묶2=묶2, 시작년=_시y)
        점1 = r1["연"] / max(abs(r1["낙"]), 3.0)
        점2 = r2["연"] / max(abs(r2["낙"]), 3.0)
        늘 = (r2["끝"] / r1["끝"] - 1) * 100 if r1["끝"] > 0 else 0
        print(f"  {라:<30}{r1['끝']:>14,.0f}원{r1['낙']:>7.1f}%{r1['산']:>6}"
              f"{점1:>7.2f}  |{r2['끝']:>14,.0f}원{r2['낙']:>7.1f}%"
              f"{r2['산']:>6}{점2:>7.2f}{늘:>+8.0f}%")
        _둘.r1 = r1          # ⭐ 제약 있는 판도 남긴다 — 판정은 이쪽이 실전에 가깝다 (2026-09-15)
        return r2

    머239 = (f"  {'설정':<30}{'[제약 있음] 끝 자산':>19}{'낙폭':>7}{'산것':>6}"
             f"{'돈÷낙':>7}  |{'[제약 없음] 끝 자산':>19}{'낙폭':>7}"
             f"{'산것':>6}{'돈÷낙':>7}{'차이':>8}")

    print("\n  ── A ⭐⭐⭐ **후보 조건별** ──")
    print(머239)
    _기239 = _둘("Ⓗ (지금 · 견줌)", _c(_H))
    _둘("Ⓗ 인데 볼60", _c(_H60))
    _둘("볼20 규칙 혼자 (지금)", _c(지금))

    print("\n  ── B ⭐⭐⭐ **시총 상한** ──")
    print("     ⚠️ 「1조↑ 만」은 제약 있는 판에서 10.4년에 **42건**밖에 못 샀다")
    print(머239)
    for _하, _상, _라 in ((300, 2000, "300~2,000억 (지금)"),
                          (300, 5000, "300~5,000억"),
                          (300, 10000, "300억~1조"),
                          (300, 999999, "300억~상한 없음"),
                          (2000, 999999, "2,000억↑ 만"),
                          (10000, 999999, "**1조↑ 만**")):
        if _하 >= _크기상한:
            print(f"  {_라:<30}{'사건에 없다 (SIZE_HI 를 올려라)':>40}")
            continue
        _둘(_라, _c(_H, 시총하한=_하, 시총상한=_상))

    print("\n  ── C ⭐⭐ **하루 상한** (참고 — 자본 배분이라 판정 대상 아님) ──")
    print(머239)
    for _n in (2, 3, 4, 6, 8):
        _둘(f"하루 {_n}종목" + (" (지금)" if _n == 4 else ""),
            _c(_H, 하루상한=_n))

    print("\n  ── D ⭐⭐ **걷기 검증** (제약 없는 판으로) ──")
    for _시, _끝2, _라2 in (("2010", "2020", "앞 2010~2020"),
                            ("2021", None, "**뒤 2021~2026**")):
        print(f"\n   [{_라2}]")
        print(머)
        _기d2 = 시뮬(_c(_H, 제약없음=True), 시작년=_시, 끝년=_끝2)
        표(_기d2, "[견줌] Ⓗ")
        표(시뮬(_c(_H60, 제약없음=True), 시작년=_시, 끝년=_끝2),
          "Ⓗ 인데 볼60", _기d2)
        _열2 = min(999999, _크기상한)
        표(시뮬(_c(_H, 시총상한=_열2, 제약없음=True), 시작년=_시, 끝년=_끝2),
          f"Ⓗ + 상한 {_열2:,.0f}억", _기d2)
        if _크기상한 > 10000:
            표(시뮬(_c(_H, 시총하한=10000, 시총상한=999999, 제약없음=True),
                    시작년=_시, 끝년=_끝2), "**1조↑ 만**", _기d2)

    print("\n     ⇒ 제약을 빼면 **산 것**이 늘어난다. 그래도 이겨야 진짜다")

    # ══ ⭐⭐⭐ 241차 — **표준화 낙폭 · PBR 을 자본 시뮬로** ══
    print("\n" + "=" * 108)
    print("  241차 · ⭐⭐⭐ **표준화 낙폭 · PBR 을 자본 시뮬로** (누락이었다)")
    print("     둘 다 승률로는 좋았는데 **자본 시뮬을 한 번도 안 했다**")
    print("       평소 등락폭 대비: 226차 네 규모대 ⭐ · 227차 1·2위 ·")
    print("                       238차 소형 64.0% · 240차 3중 7칸")
    print("       PBR 0.5배↓ AND: 225차 56.0%->63.0% · 238차 62.3%")
    print("     ⚠️ 오늘 「평균 수익은 돈이 아니다」를 **네 번** 겪었다")
    print("=" * 108)

    def _표준낙(x, 문):
        r"""그 종목 **평소 등락폭(60일 일간 표준편차)** 대비 20일 낙폭이 몇 배인가"""
        평 = x.get("평소등락")
        if not 평 or 평 <= 0 or x.get("낙폭20") is None:
            return False
        return (x["낙폭20"] / (평 * (20 ** 0.5))) <= 문

    def _pbr(x, 문):
        v = x.get("PBR")
        return v is not None and v < 문

    _쓸수있나 = sum(1 for x in 사건 if x.get("평소등락")) > len(사건) * 0.5
    _pbr있나 = sum(1 for x in 사건 if x.get("PBR") is not None) > len(사건) * 0.3
    print(f"\n     평소등락 붙은 것 "
          f"{sum(1 for x in 사건 if x.get('평소등락')):,}/{len(사건):,} · "
          f"PBR {sum(1 for x in 사건 if x.get('PBR') is not None):,}")
    if not _쓸수있나:
        print("     ⚠️⚠️ **평소등락이 사건에 없다** — 사건 만들기에 넣어야 한다")
    if not _pbr있나:
        print("     ⚠️⚠️ **PBR 이 사건에 없다** — 사건 만들기에 넣어야 한다")

    # ══ ⭐⭐⭐ ㉡㉢ **규모대마다 제 규칙 · 더하기 판정** ══ (2026-09-15)
    #    사용자: 「**대형주는 대형주 만의 규칙으로 적용해도 되지 않아?**」
    #    227차가 규모대마다 **이길 확률**을 쟀고 세 구간 검증도 지났는데
    #    **자본 시뮬까지 한 번도 안 갔다.** 유일한 돈 판(M판)은
    #    **지금 소형주 규칙을 대형주에 얹은 것**이라 답이 아니다.
    #    ⚠️ 재료는 **227차가 고른 것 그대로** 쓴다. 내가 새로 고르면 과적합이다
    print("\n" + "=" * 108)
    print("  ⭐⭐⭐ ㉡㉢ **규모대마다 제 규칙** — 바꾸는 게 아니라 **더한다**")
    print("     227차 1·2위 재료를 그대로 쓴다 (내가 새로 고르지 않는다):")
    print("       중형  2,000억~1조  평소-2.5배↓ 69.7%(+25.0p) · 볼60-1.5σ 58.2%")
    print("       대형  1조~10조     평소-2.5배↓ 70.2%(+23.0p) · 낙60-30% 60.5%")
    print("       초대형 10조↑        평소-2.0배↓ 61.8% · 볼60-1.5σ 58.9%")
    print("  ⚠️ 판정은 **셋 다** — ① 산 것 늘고 ② 돈 늘고 ③ 낙폭 -10% 안.")
    print("     기회를 깎아서 이긴 건 기각이다 (191차에 「1년 3개」로 한 번 속았다)")
    print(f"  ⚠️⚠️ 사건 크기 상한 = **{_크기상한:,.0f}억**", end="")
    if _크기상한 <= 3000:
        print("  ← **SIZE_HI=999999 없이는 이 절이 통째로 뜻이 없다**")
    else:
        print("  ✅ 열려 있다")
    print("=" * 108)

    def _규모띠(x, 아, 위):
        s7 = x.get("시총억") or 0
        return 아 <= s7 < 위

    def _띠볼60(x, 문):
        return 있(x, "볼60") and x["볼60"] <= 문

    def _띠낙60(x, 문):
        return 있(x, "낙폭60") and x["낙폭60"] <= 문

    # ── 규모대마다 **혼자 서는** 규칙 (227차 1·2위) ──
    def _중형규(x):
        return 재무통과(x) and 대금통과(x) and _규모띠(x, 2000, 10000) and (
            _표준낙(x, -2.5) or _띠볼60(x, -1.5))

    def _대형규(x):
        return 재무통과(x) and 대금통과(x) and _규모띠(x, 10000, 100000) and (
            _표준낙(x, -2.5) or _띠낙60(x, -30.0))

    def _초대규(x):
        return 재무통과(x) and 대금통과(x) and _규모띠(x, 100000, 9e9) and (
            _표준낙(x, -2.0) or _띠볼60(x, -1.5))

    def _큰셋(x):
        return _중형규(x) or _대형규(x) or _초대규(x)

    # ⚠️⚠️ SIZE_HI 를 주면 `_H` 자체가 열린다 (`_규칙크기상한`). 그래서 BIG판의
    #    「지금 · 소형 · 견줌」 줄이 사실은 **무제한**이었다. 견줌은 이걸로 한다
    def _H소형(x):
        return _H(x) and x["시총억"] < R.시총상한억

    # ㉣ 섹터규칙만 크기 문을 푼다 — 원전·조선 대형주에 섹터규칙이 한 번도 안 걸렸다
    def _섹무제한(x):
        return 재무통과(x) and 대금통과(x) and 섹터맞나(x)

    if not _쓸수있나:
        print("\n     ⚠️⚠️ **평소등락이 사건에 없다** — 이 절을 건너뛴다")
    elif _크기상한 <= 3000:
        print("\n     ⚠️⚠️ 크기 상한이 3,000억이라 중형 위가 **사건에 없다**.")
        print("        `SIZE_HI=999999` 로 다시 돌려라. 건너뛴다")
    else:
        for _라7, _f7 in (("중형 2,000억~1조", _중형규),
                          ("대형 1조~10조", _대형규),
                          ("초대형 10조↑", _초대규)):
            _n7 = sum(1 for x in 사건 if _f7(x))
            print(f"     {_라7:<18}후보 {_n7:>9,}건")

        print("\n  ── A ⭐⭐⭐ **혼자 서면** (그 규모대만 산다) ──")
        print(머239)
        _둘(f"{_밑글자} (지금 · **소형** · 견줌)", _c(_H소형))
        _둘(f"{_밑글자} 크기만 무제한 (참고 · 2023 −79%)", _c(_H, 시총하한=0, 시총상한=999999))

        # ⭐⭐ **2023 −79% 의 진짜 범인 — 연속 하한가** (2026-09-15 · why2023d)
        #    사라짐 손실 0%(BIG3)도 이유 가름(BIG4)도 −61.9% 그대로 → 사라짐이 아니다.
        #    SG증권 사태 8종목이 2023-04-24~28 에 「빠진 것」으로 39번 걸렸고 20일 뒤 −21.8%.
        #    같은 종목을 다음 날 또 산다(중복금지 없음) → 4자리가 무너지는 종목으로 찬다
        def _전날하한(x):
            """신호일 종가가 그 전날 종가보다 −28% 아래 = 하한가로 닫혔다"""
            i0 = x["인"] - 1
            if i0 < 1:
                return False
            v1 = 주가[날[i0]].get(x["code"])
            v0 = 주가[날[i0 - 1]].get(x["code"])
            return bool(v1 and v0 and v0[0] > 0 and v1[0] / v0[0] - 1 <= -0.28)

        def _H하한제외(x):
            return _H(x) and not _전날하한(x)

        print("     ── 연속 하한가 방어 (크기 무제한에서) ──")
        _둘("크기 무제한 + **전날 하한가면 안 산다**",
            _c(_H하한제외, 시총하한=0, 시총상한=999999))
        _둘("크기 무제한 + **같은 종목 중복금지**",
            _c(_H, 시총하한=0, 시총상한=999999, 중복금지=True))
        _둘("크기 무제한 + 둘 다",
            _c(_H하한제외, 시총하한=0, 시총상한=999999, 중복금지=True))
        _둘(f"{_밑글자} 소형 + 전날 하한가 제외 (소형에도 도움 되나)",
            _c(lambda x: _H소형(x) and not _전날하한(x)))

        # ⭐⭐⭐ **거래 기록 — 2022·2023 큰 회사 최악 거래** (2026-09-15 22:50)
        #    방어를 넣어도 −26.8%. 해마다 2022 −62.4% · 2023 −73.1%. 어느 거래가 날렸나 직접 본다
        _거래 = []
        시뮬(_c(_H, 시총하한=0, 시총상한=999999), 기록=_거래)
        _이름표 = {}
        try:
            _b9 = json.load(io.open(os.path.join(O._DATA, "stock-base.json"), encoding="utf-8-sig"))
            for _c9, _v9 in (_b9.get("종목") or _b9).items():
                if isinstance(_v9, dict):
                    _이름표[_c9] = (_v9.get("종목명") or _v9.get("이름") or "")
        except Exception:  # noqa: BLE001
            pass
        print("\n     ── 크기 무제한 판의 거래 기록 — **2022·2023 최악 25건** (제약 있는 판) ──")
        _나쁜 = sorted([t for t in _거래 if t[0][:4] in ("2022", "2023")], key=lambda t: t[4])[:25]
        print(f"     {'산 날':<10}{'코드':<8}{'이름':<12}{'시총억':>8}{'산 값':>10}{'결과%':>8}{'주수':>7}{'청산':>10}")
        for _d, _cd, _s, _p, _r, _cl, _q in _나쁜:
            print(f"     {_d:<10}{_cd:<8}{_이름표.get(_cd, '')[:10]:<12}{_s:>8,.0f}{_p:>10,.0f}{_r:>+8.1f}{_q:>7,}"
                  f"{(날[_cl] if _cl is not None and _cl < len(날) else '-'):>10}")
        _큰것 = [t for t in _거래 if t[2] >= 2000]
        _작것 = [t for t in _거래 if t[2] < 2000]
        for _라9, _벌9 in (("2,000억↑", _큰것), ("2,000억 미만", _작것)):
            if _벌9:
                print(f"     {_라9:<12} 거래 {len(_벌9):>5}건 · 평균 {sum(t[4] for t in _벌9) / len(_벌9):>+6.1f}% · "
                      f"−30% 밑 {sum(1 for t in _벌9 if t[4] <= -30):>3}건 · "
                      f"2022~23 만 {sum(1 for t in _벌9 if t[0][:4] in ('2022', '2023')):>4}건")

        # ⭐⭐ **규모별 규칙 OR + 방어** (2026-09-15 21:30 · 사용자 「이긴 건 OR」)
        #    BIG4 에서 OR 중형/대형이 낙폭 −26~−38% 로 죽었는데, 그 낙폭의 범인이 연속 하한가였다.
        #    방어를 붙여서 다시 OR 한다 — 227차가 이긴 재료를 기회로 살릴 수 있나
        print("     ── 규모별 규칙 OR **+ 방어**(전날 하한가 제외 · 중복금지) ──")
        for _라7, _f7 in (("OR 중형", _중형규), ("OR 대형", _대형규),
                          ("OR 초대형", _초대규), ("OR 큰 것 셋 다", _큰셋)):
            _둘(f"{_밑글자} 소형 {_라7} **+방어**",
                _c(lambda x, g=_f7: (_H소형(x) or g(x)) and not _전날하한(x),
                   시총하한=0, 시총상한=999999, 중복금지=True))
        _둘("중형 규칙 **혼자**", _c(_중형규, 시총하한=0, 시총상한=999999))
        _둘("대형 규칙 **혼자**", _c(_대형규, 시총하한=0, 시총상한=999999))
        _둘("초대형 규칙 **혼자**", _c(_초대규, 시총하한=0, 시총상한=999999))
        _둘("큰 것 **셋 다** (소형 없이)", _c(_큰셋, 시총하한=0, 시총상한=999999))

        print("\n  ── B ⭐⭐⭐ **더하면** (기존 OR 규모규칙) ── ⚠️ 여기가 판정이다")
        print(머239)
        _둘(f"{_밑글자} (지금 · 소형 · 견줌)", _c(_H소형))
        for _라7, _f7 in (("**OR** 중형", _중형규),
                          ("**OR** 대형", _대형규),
                          ("**OR** 초대형", _초대규),
                          ("**OR** 큰 것 셋 다", _큰셋),
                          ("**OR** 섹터규칙(크기 무제한) ㉣", _섹무제한)):
            _둘(f"{_밑글자} {_라7}",
                _c(lambda x, g=_f7: _H소형(x) or g(x), 시총하한=0, 시총상한=999999))

        print("\n     ⚠️ **산 것이 늘었나**를 먼저 본다. 안 늘었으면 돈이 늘어도 기각이다")
        print("        (오늘 ③에서 죽은 넷 중 셋이 「기회를 깎아 이긴 것」이었다)")

        print("\n  ── C ⭐⭐ **걷기 검증** (앞 2010~2020 / 뒤 2021~2026) ──")
        # ⚠️⚠️ 루프 변수를 `_시7` 로 썼다가 함수 `_시7(x)` 를 덮어써 BIG2·3·4 가 여기서 죽었다
        #    ('str' object is not callable · 2026-09-15 19:21). 함수 이름과 겹치지 않게 `_해앞`
        for _해앞, _해뒤, _라8 in (("2010", "2020", "[앞 2010~2020]"),
                                 ("2021", "2027", "[**뒤 2021~2026**]")):
            print(f"\n   {_라8}")
            print(머)
            _기8 = 시뮬(_c(_H소형, 제약없음=True), 시작년=_해앞, 끝년=_해뒤)
            표(_기8, f"[견줌] {_밑글자} 소형")
            for _라7, _f7 in (("OR 중형", _중형규), ("OR 대형", _대형규),
                              ("OR 초대형", _초대규), ("OR 큰 것 셋 다", _큰셋),
                              ("OR 섹터 무제한 ㉣", _섹무제한)):
                표(시뮬(_c(lambda x, g=_f7: _H소형(x) or g(x), 제약없음=True,
                          시총하한=0, 시총상한=999999),
                        시작년=_해앞, 끝년=_해뒤), f"{_밑글자} {_라7}", _기8)

        print("\n  ── D ⭐⭐ **해마다 승패** (4관문 B) ──")
        print(f"   {'해':<8}{'견줌 Ⓗ':>18}{'OR 큰 것 셋':>18}{'차이':>9}"
              f"{'Ⓗ 낙':>9}{'도전 낙':>9}")
        _차8 = []
        for _y8 in range(2016, 2027):
            _a8 = 시뮬(_c(_H소형, 제약없음=True),
                       시작년=str(_y8), 끝년=str(_y8))
            _b8 = 시뮬(_c(lambda x: _H소형(x) or _큰셋(x), 제약없음=True,
                          시총하한=0, 시총상한=999999),
                       시작년=str(_y8), 끝년=str(_y8))
            _d8 = (_b8["끝"] / _a8["끝"] - 1) * 100 if _a8["끝"] > 0 else 0
            _차8.append(_d8)
            print(f"   {_y8:<8}{_a8['끝']:>17,.0f}원{_b8['끝']:>17,.0f}원"
                  f"{_d8:>+8.1f}%{_a8['낙']:>8.1f}%{_b8['낙']:>8.1f}%")
        print(f"     ⇒ "
              + _해마다판정(_차8)[0])

        # ⭐⭐⭐ ㉣ 해마다 — BIG5 에서 A(셋 다)·C(걷기 앞 +1% 뒤 +5%) 를 지났다. 이게 마지막 관문
        print("\n  ── D-2 ⭐⭐⭐ **㉣ 소형 OR 섹터규칙(크기 무제한) — 해마다** ──")
        print(f"   {'해':<8}{'견줌 소형':>18}{'OR 섹터 무제한':>18}{'차이':>9}{'견줌 낙':>9}{'도전 낙':>9}")
        _차9 = []
        for _y9 in range(2016, 2027):
            _a9 = 시뮬(_c(_H소형, 제약없음=True), 시작년=str(_y9), 끝년=str(_y9))
            _b9 = 시뮬(_c(lambda x: _H소형(x) or _섹무제한(x), 제약없음=True,
                          시총하한=0, 시총상한=999999), 시작년=str(_y9), 끝년=str(_y9))
            _d9 = (_b9["끝"] / _a9["끝"] - 1) * 100 if _a9["끝"] > 0 else 0
            _차9.append(_d9)
            print(f"   {_y9:<8}{_a9['끝']:>17,.0f}원{_b9['끝']:>17,.0f}원{_d9:>+8.1f}%"
                  f"{_a9['낙']:>8.1f}%{_b9['낙']:>8.1f}%")
        print(f"     ⇒ ㉣ "
              + _해마다판정(_차9)[0]
              + ("  ⇒ **반영 후보**" if _해마다판정(_차9)[1] is not False else ""))

        # ══ ㉤ ⭐⭐⭐ **대형주 전용 재료 — 컨센서스** ══ (2026-09-15)
        #    못 들어간 재료 9개 중 컨센서스 4개는 「소형주엔 리포트가 없어서」(15%)다.
        #    대형주만 떼면 리포트가 있다. 자료가 2020~ 이라 **기존도 2020~ 으로 잘라** 나란히
        _컨X = _NM._컨센서스표()
        print("\n" + "=" * 108)
        print("  ㉤ ⭐⭐⭐ **대형주(1조↑) 전용 재료 — 컨센서스** (2020~ · 기존도 같은 기간)")
        print(f"     컨센서스 있는 종목 {len(_컨X):,}개 · 새 리포트 20일 · 목표주가 올림(최근 둘 비교)")
        print("  ⚠️ 판정은 셋 다 — 산 것↑ · 돈↑ · 낙폭 > -10%. 재료는 AND 빠짐(평소 -2.0배↓ 또는 볼60 -1.0σ)")
        print("=" * 108)
        import bisect as _bs

        def _컨정보(x, 창=20):
            """(창 안 리포트 수, 목표주가 올랐나) — 신호일까지만 본다"""
            벌 = _컨X.get(x["code"])
            if not 벌:
                return 0, False
            d8 = 날[x["인"] - 1]
            ds = [z[0] for z in 벌]
            j = _bs.bisect_right(ds, d8)
            if j == 0:
                return 0, False
            i0 = _bs.bisect_left(ds, 날[max(0, x["인"] - 1 - 창)])
            목 = [z[1] for z in 벌[:j] if z[1]]
            올림 = len(목) >= 2 and 목[-1] > 목[-2] and (j - i0) >= 1
            return (j - i0), 올림

        def _큰빠짐(x):
            return _표준낙(x, -2.0) or _띠볼60(x, -1.0)

        def _대컨_새(x):
            return (재무통과(x) and 대금통과(x) and _규모띠(x, 10000, 9e9)
                    and _큰빠짐(x) and _컨정보(x)[0] >= 1)

        def _대컨_올림(x):
            return (재무통과(x) and 대금통과(x) and _규모띠(x, 10000, 9e9)
                    and _큰빠짐(x) and _컨정보(x)[1])

        def _대컨_없이(x):
            return (재무통과(x) and 대금통과(x) and _규모띠(x, 10000, 9e9) and _큰빠짐(x))

        _대컨들 = (("대형 · 빠짐 **혼자** (컨센서스 없이 · 견줌)", _대컨_없이),
                   ("대형 · 빠짐 AND **새 리포트 20일**", _대컨_새),
                   ("대형 · 빠짐 AND **목표주가 올림**", _대컨_올림))
        for _라9, _f9 in _대컨들:
            print(f"     {_라9:<44}후보 {sum(1 for x in 사건 if _f9(x)):>8,}건")

        print("\n  ── A **혼자** (2020~) ──")
        print(머239)
        _둘(f"{_밑글자} 소형 (견줌 · 2020~)", _c(_H소형, 시작년="2020"))
        for _라9, _f9 in _대컨들:
            _둘(_라9[:34], _c(_f9, 시총하한=0, 시총상한=999999, 시작년="2020"))

        print("\n  ── B ⭐⭐⭐ **기존 OR 대형컨센서스** (2020~) — 여기가 판정이다 ──")
        print(머239)
        _둘(f"{_밑글자} 소형 (견줌 · 2020~)", _c(_H소형, 시작년="2020"))
        for _라9, _f9 in _대컨들[1:]:
            _둘(f"소형 OR {_라9[5:30]}",
                _c(lambda x, g=_f9: _H소형(x) or g(x), 시총하한=0, 시총상한=999999,
                   시작년="2020"))

        print("\n  ── C **앞뒤** (2020~2022 / 2023~2026) ──")
        for _시9, _끝9, _라8 in (("2020", "2022", "[앞 2020~2022]"),
                                 ("2023", "2027", "[**뒤 2023~2026**]")):
            print(f"\n   {_라8}")
            print(머)
            _기9 = 시뮬(_c(_H소형, 제약없음=True), 시작년=_시9, 끝년=_끝9)
            표(_기9, f"[견줌] {_밑글자} 소형")
            for _라9, _f9 in _대컨들[1:]:
                표(시뮬(_c(lambda x, g=_f9: _H소형(x) or g(x), 제약없음=True,
                          시총하한=0, 시총상한=999999), 시작년=_시9, 끝년=_끝9),
                   f"소형 OR {_라9[5:24]}", _기9)


    if _쓸수있나 or _pbr있나:
        print("\n  ── A ⭐⭐⭐ **제약 있는 판 / 없는 판 나란히** ──")
        print(머239)
        _기241 = _둘("Ⓗ (견줌)", _c(_H))
        if _쓸수있나:
            for 문 in (-1.5, -2.0, -2.5):
                _둘(f"평소 등락폭 {문:+.1f}배↓ 혼자",
                    _c(lambda x, a=문: (재무통과(x) and 대금통과(x)
                                        and 크기통과(x) and _표준낙(x, a))))
            for 문 in (-1.5, -2.0):
                _둘(f"Ⓗ **OR** 평소 {문:+.1f}배↓",
                    _c(lambda x, a=문: (_H(x) or (재무통과(x) and 대금통과(x)
                                                  and 크기통과(x)
                                                  and _표준낙(x, a)))))
                _둘(f"Ⓗ **AND** 평소 {문:+.1f}배↓",
                    _c(lambda x, a=문: _H(x) and _표준낙(x, a)))
        if _pbr있나:
            for 문 in (0.5, 0.8):
                _둘(f"지금 규칙 **AND** PBR {문}배↓",
                    _c(lambda x, a=문: 지금(x) and _pbr(x, a)))
                _둘(f"Ⓗ **AND** PBR {문}배↓",
                    _c(lambda x, a=문: _H(x) and _pbr(x, a)))
                _둘(f"Ⓗ **OR** (지금 AND PBR {문}배↓)",
                    _c(lambda x, a=문: _H(x) or (지금(x) and _pbr(x, a))))
        if _쓸수있나 and _pbr있나:
            _둘("Ⓗ AND 평소 -1.5배↓ AND PBR 0.8배↓",
                _c(lambda x: _H(x) and _표준낙(x, -1.5) and _pbr(x, 0.8)))

        print("\n  ── B ⭐⭐ **걷기 검증** (제약 없는 판) ──")
        for _시, _끝3, _라3 in (("2010", "2020", "앞 2010~2020"),
                                ("2021", None, "**뒤 2021~2026**")):
            print(f"\n   [{_라3}]")
            print(머)
            _기b = 시뮬(_c(_H, 제약없음=True), 시작년=_시, 끝년=_끝3)
            표(_기b, "[견줌] Ⓗ")
            if _쓸수있나:
                표(시뮬(_c(lambda x: (_H(x) or (재무통과(x) and 대금통과(x)
                                                and 크기통과(x)
                                                and _표준낙(x, -1.5))),
                          제약없음=True), 시작년=_시, 끝년=_끝3),
                  "Ⓗ OR 평소 -1.5배↓", _기b)
                표(시뮬(_c(lambda x: _H(x) and _표준낙(x, -1.5), 제약없음=True),
                        시작년=_시, 끝년=_끝3), "Ⓗ AND 평소 -1.5배↓", _기b)
            if _pbr있나:
                표(시뮬(_c(lambda x: 지금(x) and _pbr(x, 0.8), 제약없음=True),
                        시작년=_시, 끝년=_끝3), "지금 AND PBR 0.8배↓", _기b)

    # ══ ⭐⭐⭐ 249차 — **대형주를 넣으면 나아지나** ══ (2026-09-11)
    #    사용자: 「작은 회사만 나오는게 맞아?」
    #    ⚠️ 241차는 표준화 낙폭을 **`크기통과` 를 건 채** 쟀다 — 소형주 안에서만.
    #       대형주를 **넣은** 판은 한 번도 안 해봤다
    print("\n" + "=" * 108)
    print("  249차 · ⭐⭐⭐ **대형주를 넣으면 나아지나**")
    print("     226차: 대형 1조~10조 20일 -20% -> 55.8% · 평균 **+2.89%**")
    print("            (소형 -10% 는 +2.00%) · 표준화 낙폭은 네 규모대 전부 ⭐")
    print("     ⚠️ 판정은 **끝 자산과 낙폭**으로 한다. 승률·평균으로 안 한다")
    print("        (241차에서 표준화 낙폭이 낙폭을 -3.9% -> -12.1% 로 키웠다)")
    print("=" * 108)

    _최대시총 = max((x["시총억"] for x in 사건), default=0)
    print(f"\n     사건 안 **가장 큰 시총 {_최대시총:,.0f}억** · "
          f"2,000억 넘는 사건 "
          f"{sum(1 for x in 사건 if x['시총억'] >= 2000):,}건")
    if _최대시총 < 5000:
        print("     ⚠️⚠️ **대형주가 사건에 없다** — `SIZE_HI=999999` 로 다시 돌려라.")
        print("        지금 판으로는 이 절을 믿을 수 없다")
    else:
        def _중대형(x):
            return x["시총억"] >= 2000

        def _대형(x):
            return x["시총억"] >= 10000

        # 226차가 규모대마다 찾아준 문턱
        def _규모문턱(x):
            r"""크기마다 **다른 낙폭 문턱**. 226차 A 절에서 ⭐ 가 붙은 칸"""
            if not (재무통과(x) and 대금통과(x) and x["볼린저"] <= -1.0):
                return False
            s = x["시총억"]
            if s < 2000:
                return x["낙폭20"] <= -10.0        # 소형 — 지금과 같다
            if s < 10000:
                return x["낙폭20"] <= -15.0        # 중형
            return x["낙폭20"] <= -20.0            # 대형·초대형

        print("\n  ── A ⭐⭐⭐ **자본 시뮬** (제약 있는 판 / 없는 판) ──")
        print("     ⚠️ 판정: 끝 자산이 Ⓗ 보다 많고 **돈÷낙폭이 안 나빠져야** 한다")
        print(머239)
        _기249 = _둘("Ⓗ (지금 · 소형만 · 견줌)", _c(_H))
        _둘("Ⓗ **OR** 규모별 문턱 (226차 A)",
            _c(lambda x: _H(x) or _규모문턱(x), 시총상한=999999))
        _둘("규모별 문턱 **혼자** (대체)", _c(_규모문턱, 시총상한=999999))
        for 문 in (-1.5, -2.0, -2.5):
            _둘(f"Ⓗ **OR** 크기무제한 평소 {문:+.1f}배↓",
                _c(lambda x, a=문: (_H(x)
                                    or (재무통과(x) and 대금통과(x)
                                        and _표준낙(x, a)))))
        for 문 in (-1.5, -2.0, -2.5):
            _둘(f"Ⓗ **OR** 중대형(2천억↑)만 평소 {문:+.1f}배↓",
                _c(lambda x, a=문: (_H(x)
                                    or (재무통과(x) and 대금통과(x)
                                        and _중대형(x) and _표준낙(x, a)))))
        _둘("Ⓗ **OR** 중대형 낙20≤-15%",
            _c(lambda x: (_H(x) or (재무통과(x) and 대금통과(x) and _중대형(x)
                                    and x["볼린저"] <= -1.0
                                    and x["낙폭20"] <= -15.0))))
        _둘("Ⓗ **OR** 대형(1조↑) 낙20≤-20%",
            _c(lambda x: (_H(x) or (재무통과(x) and 대금통과(x) and _대형(x)
                                    and x["볼린저"] <= -1.0
                                    and x["낙폭20"] <= -20.0))))
        _둘(f"{_밑글자} 인데 **크기 상한만 해제** (하한 500억 유지)",
            _c(lambda x: (재무통과(x) and 대금통과(x) and x["시총억"] >= 500
                          and ((x["볼린저"] <= -1.0 and x["낙폭20"] <= -10.0)
                               or _시7(x) or _밑끝갈래(x)))))

        print("\n  ── B ⭐⭐⭐ **앞뒤 분할** (제약 없는 판) ──")
        print("     ⚠️ 앞뒤 **둘 다** 같은 방향이어야 믿는다")
        # ⚠️⚠️ **A절에서 가장 좋았던 둘을 여기 안 넣었었다** (2026-09-11 실수).
        #    「크기무제한 평소 -1.5배↓」 끝 자산 +29% · 낙폭 -8.0 -> -6.9
        #    「크기 상한만 해제」      돈÷낙폭 6.26 -> 11.16 (1.8배)
        #    앞뒤 분할을 안 거치면 **믿을 수 없다** — 이번엔 넣는다
        _도전 = (
            ("⭐ Ⓗ OR 크기무제한 평소 -1.5배↓",
             lambda x: (_H(x) or (재무통과(x) and 대금통과(x)
                                  and _표준낙(x, -1.5)))),
            (f"⭐ {_밑글자} 인데 크기 상한만 해제",
             lambda x: (재무통과(x) and 대금통과(x) and x["시총억"] >= 500
                        and ((x["볼린저"] <= R.볼린저문턱
                              and x["낙폭20"] <= R.낙폭20문턱)
                             or 섹터맞나(x) or _시7(x) or _밑끝갈래(x)))),
            ("Ⓗ OR 규모별 문턱", lambda x: _H(x) or _규모문턱(x),
             {"시총상한": 999999}),
            ("Ⓗ OR 중대형 평소 -2.0배↓",
             lambda x: (_H(x) or (재무통과(x) and 대금통과(x)
                                  and _중대형(x) and _표준낙(x, -2.0)))),
            ("Ⓗ OR 중대형 낙20≤-15%",
             lambda x: (_H(x) or (재무통과(x) and 대금통과(x) and _중대형(x)
                                  and x["볼린저"] <= -1.0
                                  and x["낙폭20"] <= -15.0))),
        )
        for _시, _끝3, _라3 in (("2010", "2020", "앞 2010~2020"),
                                ("2021", None, "**뒤 2021~2026**")):
            print(f"\n   [{_라3}]")
            print(머)
            _기b = 시뮬(_c(_H, 제약없음=True), 시작년=_시, 끝년=_끝3)
            표(_기b, "[견줌] Ⓗ")
            for _짝 in _도전:
                _라4, _fn = _짝[0], _짝[1]
                _더 = _짝[2] if len(_짝) > 2 else {}
                표(시뮬(_c(_fn, 제약없음=True, **_더), 시작년=_시, 끝년=_끝3),
                  _라4, _기b)

        print("\n  ── C ⭐⭐ **규모대별로 몇 번 걸리나** (Ⓗ OR 규모별 문턱) ──")
        해수249 = 10.4
        for _라5, _lo, _hi in (("소형 300~2,000억", 300, 2000),
                               ("중형 2,000억~1조", 2000, 10000),
                               ("대형 1조~10조", 10000, 100000),
                               ("초대형 10조↑", 100000, 9e9)):
            _n = sum(1 for x in 사건
                     if _lo <= x["시총억"] < _hi and _규모문턱(x))
            _b = sum(1 for x in 사건 if _lo <= x["시총억"] < _hi and _H(x))
            print(f"    {_라5:<20}규모별 문턱 {_n:>7,}건 "
                  f"(1년 {_n/해수249:>6.0f}건)   ·   Ⓗ {_b:>7,}건")

    # ══ ⭐⭐⭐ 253차 — **중앙갭을 무엇으로 내나** ══ (2026-09-11)
    print("\n" + "=" * 108)
    print("  253차 · ⭐⭐⭐ **중앙갭을 무엇으로 내나**")
    print("     상대갭 = 그 종목 갭 - **중앙갭** · 이 값으로 살지 말지를 정한다")
    print("     실전  후보 40개 + **시장 표본 30개**의 중앙값")
    print("     시뮬  **후보만**의 중앙값          <- 여기가 달랐다")
    print("     ⚠️ 표본 30개는 주석에 「중소형주」라 적혀 있지만 실제로는")
    print("        코스피 초대형 20 + 코스닥 중대형 10 이다 (후보는 300~2,000억)")
    print("=" * 108)

    print("\n  ── A ⭐⭐⭐ **잣대별** (제약 있는 판 / 없는 판) ──")
    print(머239)
    _기253 = _둘("㉠ 후보만 (지금 시뮬)", _c(_H))
    _둘("⭐ ㉮ **후보 + 실전표본30** (지금 실전)",
        _c(_H, 갭잣대="후보+실전표본"))
    _둘("㉯ 실전표본30 **혼자**", _c(_H, 갭잣대="표본만+실전표본"))
    _둘("⭐ ㉰ **후보 + 같은규모30** (진짜 중소형)",
        _c(_H, 갭잣대="후보+같규모30"))
    _둘("㉱ **진짜 전 종목** 중앙갭", _c(_H, 갭잣대="진짜전종목"))
    _둘("㉡ 느슨한 후보 전체 (전에 「전종목」이라 부른 것)",
        _c(_H, 갭잣대="전종목중앙"))
    _둘("㉣ 지수 대용 갭 (ETF)", _c(_H, 갭잣대="지수갭"))
    _둘("⭐⭐⭐ ㉲ **규모별 중앙갭** (260차 · 제 규모대와 견준다)",
        _c(_H, 갭잣대="규모별"))

    print("\n  ── B ⭐⭐⭐ **표본 개수**를 늘리면 ── (같은 규모에서 뽑는다)")
    print(머239)
    for _n253 in (10, 30, 50, 100, 300):
        _둘(f"후보 + 같은규모 **{_n253}개**",
            _c(_H, 갭잣대=f"후보+같규모{_n253}"))

    print("\n  ── C ⭐⭐⭐ **앞뒤 분할** (제약 없는 판) ──")
    print("     ⚠️ 앞뒤 **둘 다** 같은 방향이어야 믿는다")
    _볼것253 = (("⭐⭐⭐ ㉲ **규모별 중앙갭** (260차)", "규모별"),
                ("⭐ ㉮ 후보 + 실전표본30 (지금 실전)", "후보+실전표본"),
                # ⭐⭐⭐ ㉯ 를 빼고 있었다 (2026-09-11) — A절에서 **제일 좋았는데**
                #    36.5억 · 낙폭 -5.4% · 돈÷낙 16.21 (지금 13.35억 · -5.7% · 12.49)
                #    **실전을 바꿀 유일한 후보**인데 앞뒤 분할을 안 태우고 있었다
                ("⭐⭐⭐ ㉯ 실전표본30 **혼자**", "표본만+실전표본"),
                ("⭐ ㉰ 후보 + 같은규모30", "후보+같규모30"),
                ("㉰-100 후보 + 같은규모100", "후보+같규모100"),
                ("㉱ 진짜 전 종목", "진짜전종목"))
    for _시253, _끝253, _라253 in (("2010", "2020", "앞 2010~2020"),
                                   ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라253)
        print(머)
        _기c = 시뮬(_c(_H, 제약없음=True), 시작년=_시253, 끝년=_끝253)
        표(_기c, "[견줌] ㉠ 후보만 (지금 시뮬)")
        for _라9, _잣9 in _볼것253:
            표(시뮬(_c(_H, 제약없음=True, 갭잣대=_잣9),
                    시작년=_시253, 끝년=_끝253), _라9, _기c)

    print("\n  ── D ⭐⭐⭐ **해마다 끝 자산** (4관문 B · 제약 없는 판) ──")
    print("     ⚠️ 249차가 앞뒤 분할은 통과했는데 **해마다에서 떨어졌다**")
    _해253 = sorted({x["해"] for x in 사건})
    # ⭐ [:2] -> [:3] (2026-09-14). ㉯ 가 목록엔 있는데 **앞 둘만 돌려서** 해마다
    #    표에 ㉯ 가 빠졌다 — A(앞뒤)·C(무작위)는 지났는데 B 만 못 걸고 있었다
    for _라9, _잣9 in _볼것253[:3]:
        _이9, _짐9, _무9 = 0, 0, 0
        print(f"\n   [{_라9}]  {'해':<7}{'㉮ 지금실전':>15}{'도전':>15}"
              f"{'차이':>9}{'㉮ 낙':>8}{'도전 낙':>9}")
        for _y9 in _해253:
            try:
                # ⭐ 기준을 **명시** (2026-09-14). 기준선이 ㉯ 인 판에서 도전 ㉯ 가
                #    자기 자신과 비교돼 0승 0패 11무 가 나왔다 (L_후보60 판)
                _기y = 시뮬(_c(_H, 제약없음=True, 갭잣대="후보+실전표본"),
                            시작년=_y9, 끝년=_y9)
                _도y = 시뮬(_c(_H, 제약없음=True, 갭잣대=_잣9),
                            시작년=_y9, 끝년=_y9)
            except Exception:  # noqa: BLE001
                continue
            if not _기y or not _도y or _기y["산"] < 3:
                continue
            _늘9 = ((_도y["끝"] / _기y["끝"] - 1) * 100
                    if _기y["끝"] > 0 else 0)
            print(f"            {_y9:<7}{_기y['끝']:>14,.0f}원"
                  f"{_도y['끝']:>14,.0f}원{_늘9:>+8.1f}%"
                  f"{_기y['낙']:>7.1f}%{_도y['낙']:>8.1f}%")
            if _늘9 > 1:
                _이9 += 1
            elif _늘9 < -1:
                _짐9 += 1
            else:
                _무9 += 1
        print(f"     ⇒ **{_이9}승 {_짐9}패 {_무9}무** — "
              f"{'✅' if _이9 > _짐9 else '❌'}")

    # ══ ⭐⭐⭐ 251차 — 249차 후보의 **B·C 관문** ══ (2026-09-11)
    #    249차c 에서 A(앞뒤 분할)만 통과했다. 나머지 둘을 건다
    print("\n" + "=" * 108)
    print("  251차 · ⭐⭐⭐ **249차 후보를 4관문 B·C 에**")
    print("     A(앞뒤 분할)는 249차c 에서 통과 — 앞 +18% · 뒤 +5% · 낙폭 둘 다 개선")
    print("     ⚠️ **승률만으로 판정하지 않는다** — B 를 자본 시뮬로도 잰다")
    print("=" * 108)

    _251도전 = (
        ("⭐ Ⓗ OR 크기무제한 평소 -1.5배↓",
         lambda x: (_H(x) or (재무통과(x) and 대금통과(x)
                              and _표준낙(x, -1.5)))),
        ("[견줌] Ⓗ (지금)", _H),
    )

    print("\n  ── B-1 ⭐⭐ **해마다 승패** (승률) ──")
    _해들251 = sorted({x["해"] for x in 사건})
    for _라251, _fn251 in _251도전[:1]:
        _차들251 = []
        print(f"\n   [{_라251}]  {'해':<8}{'Ⓗ':>10}{'도전':>10}{'차이':>10}")
        for _y251 in _해들251:
            _점 = 점수([x for x in 사건 if _fn251(x) and x["해"] == _y251])
            _기점 = 점수([x for x in 사건 if _H(x) and x["해"] == _y251])
            if not _점 or not _기점:
                continue
            _차 = _점[0] - _기점[0]
            print(f"            {_y251:<8}{_기점[0]:>9.1f}%{_점[0]:>9.1f}%"
                  f"{_차:>+9.1f}p")
            _차들251.append(_차)
        print("     ⇒ " + _해마다판정(_차들251)[0])

    print("\n  ── B-2 ⭐⭐⭐ **해마다 끝 자산** (자본 시뮬 · 제약 없는 판) ──")
    print("     ⚠️ 이쪽이 **진짜 판정**이다. 승률이 좋아도 돈이 지면 소용없다")
    print(f"\n   {'해':<8}{'Ⓗ 끝 자산':>16}{'도전 끝 자산':>16}"
          f"{'차이':>9}{'Ⓗ 낙폭':>9}{'도전 낙폭':>10}")
    _이2, _짐2, _무2 = 0, 0, 0
    for _y251 in _해들251:
        try:
            _기r = 시뮬(_c(_H, 제약없음=True), 시작년=_y251, 끝년=_y251)
            _도r = 시뮬(_c(_251도전[0][1], 제약없음=True),
                        시작년=_y251, 끝년=_y251)
        except Exception:  # noqa: BLE001
            continue
        if not _기r or not _도r or _기r["산"] < 3:
            continue
        _늘 = (_도r["끝"] / _기r["끝"] - 1) * 100 if _기r["끝"] > 0 else 0
        print(f"   {_y251:<8}{_기r['끝']:>15,.0f}원{_도r['끝']:>15,.0f}원"
              f"{_늘:>+8.1f}%{_기r['낙']:>8.1f}%{_도r['낙']:>9.1f}%")
        if _늘 > 1:
            _이2 += 1
        elif _늘 < -1:
            _짐2 += 1
        else:
            _무2 += 1
    print(f"     ⇒ **{_이2}승 {_짐2}패 {_무2}무** — "
          f"{'✅ 통과' if _이2 > _짐2 else '❌ 떨어짐'}")

    print("\n  ── C ⭐⭐⭐ **무작위 대조 200번** ──")
    print("     같은 개수를 아무렇게나 골라 200번 — 상위 25% 안에 들어야 한다")
    for _라251, _fn251 in _251도전[:1]:
        _칸251 = [x for x in 사건
                  if _fn251(x) and x.get("_20") is not None]
        if len(_칸251) < 100:
            print(f"  {_라251:<40} 표본 부족 ({len(_칸251)}건)")
            continue
        _나251 = sum(1 for x in _칸251 if x["_20"] > 0) / len(_칸251) * 100
        _분포251 = []
        for _s251 in range(200):
            _r251 = _rnd.Random(9000 + _s251)
            _뽑251 = _r251.sample(_바탕20, len(_칸251))
            _분포251.append(sum(1 for v in _뽑251 if v > 0)
                            / len(_뽑251) * 100)
        _분포251.sort()
        _위251 = sum(1 for v in _분포251 if v < _나251)
        _상위251 = (1 - _위251 / len(_분포251)) * 100
        print(f"  {_라251:<40}{len(_칸251):>8,}건  나 {_나251:.1f}%  "
              f"무작위 중앙 {_분포251[100]:.1f}% · "
              f"가장 좋음 {_분포251[-1]:.1f}%")
        print(f"     ⇒ **상위 {_상위251:.0f}%** — "
              f"{'✅ 통과' if _상위251 <= 25 else '❌ 떨어짐'}")

    print("\n  ⚠️ **A·B·C 를 다 지나야** 반영한다. "
          "하나라도 떨어지면 반영하지 않는다")

    # ══ ⭐⭐⭐ 267차 — **보유 중 재평가** ══ (SELL-PLAN 243차 · 2026-09-11)
    #    「산 이유가 사라지면 판다」 — SELL-PLAN 2절의 **마지막 하나**
    print("\n" + "=" * 108)
    print("  267차 · ⭐⭐⭐ **보유 중 재평가** — 산 이유가 사라지면 판다")
    print("     Ⓗ 세 갈래 중 **때**(시장 7일 -7% · 지수 60일 -10%)는")
    print("     보유 중에 **풀린다**. 지수가 회복하면 산 근거가 없어진다")
    print("     ⚠️ 메모리 「목표까지 기다려 판다」 — 회복 신호로 팔면 **돈이 반 났다**.")
    print("        그건 **그 종목**의 회복이었고 여기는 **지수**다. 그래도 같은 함정일 수 있다")
    print("     ⚠️ 판정은 **끝 자산과 낙폭**. 자료 없는 날은 안 판다")
    print("=" * 108)

    # ══ ⭐⭐ **분할 매수** 를 자본 시뮬로 ══ (2026-09-15 · 사용자 지적)
    #    「매도는 40:60 두 몫인데 **매수는 한 번에 100%** 다」 — 비대칭이었다.
    #    반등2 판(이길 확률): 가격 -5% 분할이 61.2% -> **66.9%** · 평균 +35%,
    #    그것도 **기회를 하나도 안 버리고**. 이제 **돈**으로 확인한다.
    def _분할묶(값):
        """사건 사본의 `매수`·`원시` 를 **평균 단가**로 바꾼 묶음.

        오늘 절반, 그 뒤 10 거래일 안에 **첫 매수가보다 `값`% 아래로 닫히면**
        다음 날 시가에 나머지 절반. 안 오면 **첫 매수 그대로**(= 절반만 산 셈).
        ⚠️ 「절반만 샀다」는 **주수로는 안 드러난다** — 비중 10% 판을 같이 본다
        """
        새묶 = {}
        for i9, 벌9 in 묶.items():
            칸9 = []
            for x9 in 벌9:
                첫 = x9["매수"]
                # ⚠️⚠️ **후보만 사본을 만든다.** 묶에는 사건이 544만 건 들어 있다 —
                #    전부 훑으면 10일 탐색 x 544만 x 값 3개 = **1.6억 번**이고
                #    dict 사본 3벌이면 램도 터진다. `_H` 를 지난 것만 본다
                if 첫 <= 0 or not _H(x9):
                    칸9.append(x9)
                    continue
                단가 = 첫
                i0 = x9["인"]
                for h9 in range(1, 11):
                    j9 = i0 + h9
                    if j9 + 1 >= len(날):
                        break
                    v9 = 주가[날[j9]].get(x9["code"])
                    if not v9:
                        break
                    if v9[0] <= 첫 * (1 + 값 / 100):      # 종가가 그만큼 아래
                        v10 = 주가[날[j9 + 1]].get(x9["code"])
                        b10 = (비.get(날[j9 + 1]) or {}).get(x9["code"])
                        if v10 and b10:
                            둘 = v10[0] * b10[0]          # 다음 날 **시가**
                            if 둘 > 0:
                                단가 = 첫 * 0.5 + 둘 * 0.5
                        break
                if 단가 == 첫:
                    칸9.append(x9)
                else:
                    y9 = dict(x9)
                    y9["매수"] = 단가
                    y9["원시"] = 단가
                    칸9.append(y9)
            새묶[i9] = 칸9
        return 새묶

    print("\n" + "=" * 108)
    print("  ⭐⭐ **분할 매수** — 오늘 절반, 더 빠지면 나머지 절반")
    print("     반등2 판(이길 확률): 61.2% -> **66.9%** · 평균 +35% · 기회 그대로")
    print("  ⚠️ **양 끝을 같이 잰다.** 평균 단가는 정확한데 「절반만 샀다」가")
    print("     주수로는 안 드러난다 — 비중 20%(낙관) 와 10%(비관) 를 나란히 본다")
    print("=" * 108)
    print(머239)
    _기분 = _둘("기한까지 · 한 번에 100% (지금)", _c(_H))
    for _값분 in (-3.0, -5.0, -8.0):
        _묶분 = _분할묶(_값분)
        _둘(f"분할 {_값분:g}% · 비중 20% (**낙관**)", _c(_H), None, _묶분)
        _둘(f"분할 {_값분:g}% · 비중 10% (**비관**)",
            _c(_H, 비중=0.10), None, _묶분)
    print("\n     ⚠️ **낙관이 지금보다 못하면 볼 것도 없다.**")
    print("        **비관이 지금보다 나으면 확실하다.** 실제는 그 사이다")

    # ══ ⭐⭐ **종목마다 배운 규칙을 돈으로** ══ (2026-09-15 · 216차 → ③)
    #    216차는 앞 기간(~2018-04-25)에서 종목마다 규칙을 골라 뒤 기간 **이길 확률**만 봤다
    #    (62.4% vs 56.7% · 72가지로 흩어짐). `percode_lab` 이 저장한 표를 읽어 **2019~** 돈으로.
    _종목규표, _종목앞끝 = {}, "?"
    try:
        _pc = json.load(io.open(os.path.join(O._DATA, "percode-rules.json"),
                                encoding="utf-8-sig"))
        _종목규표 = _pc.get("규칙") or {}        # {code: [볼창키, 볼문턱, 낙창키, 낙문턱]}
        _종목앞끝 = _pc.get("앞끝") or "?"
    except Exception:  # noqa: BLE001
        _종목규표 = {}
    print("\n" + "=" * 108)
    print("  ⭐⭐ **종목마다 배운 규칙**(216차) 을 돈으로 — 앞 기간 밖 **2019~** 만")
    print(f"     표 {len(_종목규표):,}종목 (data/percode-rules.json · 앞 ~2018-04-25 에서 고른 것)")
    print("  ⚠️ 판정 셋 다 — 산 것↑ · 돈↑ · 낙폭 > -10%. 규칙이 72가지로 흩어진 것은 과적합 신호다")
    print("=" * 108)
    if not _종목규표:
        print("     ⚠️ 표가 없다 — `python scripts/_labs_old/percode_lab.py` 를 먼저 돌려라. 건너뛴다")
    else:
        def _종목규(x):
            규 = _종목규표.get(x["code"])
            if not 규 or not 문통과(x):
                return False
            bk, bt, nk, nt = 규
            b, n = x.get(bk), x.get(nk)
            return b is not None and n is not None and b <= bt and n <= nt

        _n7 = sum(1 for x in 사건 if _종목규(x) and 날[x["인"]][:4] >= "2019")
        print(f"     종목규칙에 걸린 사건 (2019~) {_n7:,}건")
        print("\n  ── A **혼자 · 더하기** (2019~) ──")
        print(머239)
        _둘(f"{_밑글자} (지금 · 견줌 · 2019~)", _c(_H, 시작년="2019"))
        _둘("종목규칙 **혼자**", _c(_종목규, 시작년="2019"))
        _둘(f"{_밑글자} **OR** 종목규칙", _c(lambda x: _H(x) or _종목규(x), 시작년="2019"))
        print("\n  ── B **해마다** (2019~2026 · 제약 없는 판) ──")
        print(f"   {'해':<8}{'견줌':>18}{'OR 종목규칙':>18}{'차이':>9}{'견줌 낙':>9}{'도전 낙':>9}")
        _차7 = []
        for _y7 in range(2019, 2027):
            _a7 = 시뮬(_c(_H, 제약없음=True), 시작년=str(_y7), 끝년=str(_y7))
            _b7 = 시뮬(_c(lambda x: _H(x) or _종목규(x), 제약없음=True),
                       시작년=str(_y7), 끝년=str(_y7))
            _d7 = (_b7["끝"] / _a7["끝"] - 1) * 100 if _a7["끝"] > 0 else 0
            _차7.append(_d7)
            print(f"   {_y7:<8}{_a7['끝']:>17,.0f}원{_b7['끝']:>17,.0f}원"
                  f"{_d7:>+8.1f}%{_a7['낙']:>8.1f}%{_b7['낙']:>8.1f}%")
        print(f"     ⇒ "
              + _해마다판정(_차7)[0])

    # ══ ⭐⭐ **짧게 팔면 — 당일 단타 ~ 20일** ══ (2026-09-15 · 사용자 물음)
    #    「지금 규칙이 꽤나 장기적으로 … **단기적으로** 계산해볼 수도 있어? 오늘 하루 단타든」
    #    145차는 재료마다 1~90일 이길 확률을 쟀지만 ① 지금 규칙 후보로는 안 쟀고
    #    ② 당일(0일)이 없고 ③ 돈으로 안 갔다.
    #    ⚠️ 일봉뿐이라 「장중 몇 시」는 못 잰다 — 가장 짧은 단타 = 시가에 사서 그날 종가/고가
    print("\n" + "=" * 108)
    print("  ⭐⭐ **짧게 팔면** — 당일 단타 ~ 20일 (사용자 물음 · 2026-09-15)")
    print("  ⚠️ 자료가 일봉뿐이다 — 「장중 몇 시에 판다」는 못 잰다. 가장 짧은 것은")
    print("     「시가에 사서 **그날 종가**」 · 「그날 **고가가 +N%** 닿으면 거기서, 아니면 종가」")
    print("     저가가 없어 장중 손절은 못 잰다. 고가 목표는 순서를 모른다 — **낙관 쪽** 어림이다")
    print("  ⚠️ 짧게 팔면 자리가 매일 비어 **같은 돈으로 더 자주 산다.** 왕복비용 0.26% 가 매번 든다")
    print("=" * 108)

    def _짧수익(x, n):
        """n=0 이면 그날 종가 ÷ 시가. n≥1 은 앞수익()"""
        if n >= 1:
            return 앞수익(x, n)
        v0 = 주가[날[x["인"]]].get(x["code"])
        if not v0 or v0[0] <= 0 or x["매수"] <= 0:
            return None
        return (v0[0] / x["매수"] - 1) * 100 - _비용

    print("\n  ── A ① **지금 규칙 후보(Ⓗ)** 가 며칠 뒤에 오르나 — 바탕과 나란히 ──")
    _기들 = (0, 1, 2, 3, 5, 10, 20)
    print(f"  {'':<22}" + "".join(f"{f'{n}일':>13}" for n in _기들))
    for _라S, _fS in (("Ⓗ 후보", _H), ("바탕 (전부)", lambda x: True)):
        줄 = f"  {_라S:<22}"
        for n in _기들:
            벌 = []
            for x in 사건:
                if _fS(x):
                    v = _짧수익(x, n)
                    if v is not None:
                        벌.append(v)
            if len(벌) < 80:
                줄 += f"{'-':>13}"
            else:
                줄 += f"{sum(1 for z in 벌 if z > 0) / len(벌) * 100:>6.1f}%{sum(벌) / len(벌):>+6.2f}"
        print(줄, flush=True)
    print("     (칸: 이김% · 평균% — 비용 0.26% 뺀 값 · 0일 = 시가 사서 그날 종가)")

    print("\n  ── B ③ **자본 시뮬** — 얼마나 짧게 팔면 돈이 되나 ──")
    print(머239)
    _짧들 = (("당일 종가 (0일 · 단타)", ((1.0, 999.0, 0),)),
             ("당일 고가 +3% 아니면 종가", ((1.0, 3.0, 0),)),
             ("당일 고가 +5% 아니면 종가", ((1.0, 5.0, 0),)),
             ("1일 뒤 종가 (고가 +5% 먼저)", ((1.0, 5.0, 1),)),
             ("2일 (고가 +5%)", ((1.0, 5.0, 2),)),
             ("5일 (고가 +7%)", ((1.0, 7.0, 5),)),
             ("10일 (고가 +10%)", ((1.0, 10.0, 10),)),
             ("20일 (고가 +15%)", ((1.0, 15.0, 20),)))
    _기짧 = _둘(f"{_밑글자} 지금 (40% +15%/40일 · 60% +40%/90일)", _c(_H))
    _짧결 = []
    for _라S, _나S in _짧들:
        _rS = _둘(_라S, _c(_H, 나눔=_나S))
        _짧결.append((_rS["끝"], _라S, _나S))
    _짧결.sort(reverse=True)
    print(f"\n     ⇒ 짧은 것 중 제일 나은 것: **{_짧결[0][1]}** "
          f"(제약 없는 판 {_짧결[0][0]:,.0f}원 · 지금 {_기짧['끝']:,.0f}원)")
    print("     ⚠️ 판정은 끝 자산·낙폭·산 것 셋. 단타는 「산 것」이 크게 늘어도 비용이 갉아먹는다")

    print("\n  ── C **해마다** — 제일 나은 짧은 것 vs 지금 (제약 없는 판) ──")
    _최짧 = _짧결[0][2]
    print(f"   {'해':<8}{'지금':>18}{_짧결[0][1][:12]:>18}{'차이':>9}{'지금 낙':>9}{'짧은 낙':>9}")
    _차S = []
    for _yS in range(2016, 2027):
        _aS = 시뮬(_c(_H, 제약없음=True), 시작년=str(_yS), 끝년=str(_yS))
        _bS = 시뮬(_c(_H, 제약없음=True, 나눔=_최짧), 시작년=str(_yS), 끝년=str(_yS))
        _dS = (_bS["끝"] / _aS["끝"] - 1) * 100 if _aS["끝"] > 0 else 0
        _차S.append(_dS)
        print(f"   {_yS:<8}{_aS['끝']:>17,.0f}원{_bS['끝']:>17,.0f}원"
              f"{_dS:>+8.1f}%{_aS['낙']:>8.1f}%{_bS['낙']:>8.1f}%")
    print("     ⇒ 짧은 것이 " + _해마다판정(_차S)[0])

    # ══ ⭐⭐ **「빠진 뒤 공시가 뜨면 산다」를 돈으로** ══ (2026-09-15)
    #    반등 판(이길 확률)에서 **유일하게 살아남았고 앞뒤 분할도 지났다**:
    #      전체 69.9% (지금 61.2%) · 앞 75.0% · 뒤 65.6% · 산 것 1,214
    #    ⚠️ 분할 매수도 ①②를 지나고 **③에서 죽었다**. 같은 함정일 수 있다
    #
    # ⚠️⚠️ **묶음 열쇠를 안 옮긴다.** 옮기면 그날 중앙갭·하루상한·자르기가
    #    「아직 안 뜬 공시」로 섞여 **고르기 자체가 달라진다** — 그러면
    #    공시의 힘이 아니라 고르기가 바뀐 것을 재게 된다.
    #    고르기는 빠진 날 그대로 두고 **산 날과 산 값만** 민다.
    _공시표X = _NM._공시시각표(날)
    print(f"\n  공시 시각표 {len(_공시표X):,}일", flush=True)

    def _공시묶(갈래, 최대=10):
        """빠진 날 뒤 `최대`일 안에 공시가 뜨면 **그 다음 날 시가**에 산다.

        안 뜨면 **그 사건을 뺀다**(= 안 산다). 「안 사면」이 결과의 절반이다.
        갈래: "장중"(장중에 뜬 것) · "챙길"(계약·실적·증자 등) · "아무"
        ⚠️ `결과()` 가 `x["인"]` 에서 걸어나가므로 **인만 밀면**
           보유 기간·목표 도달·청산이 저절로 따라 밀린다
        """
        새묶 = {}
        for i8, 벌8 in 묶.items():
            칸8 = []
            for x8 in 벌8:
                # ⚠️ 후보만 본다 — 묶에는 사건이 544만 건 들어 있다
                if not _H(x8):
                    continue
                i0 = x8["인"] - 1          # **빠진 날**(신호일)
                찾 = None
                for h8 in range(0, 최대):
                    j8 = i0 + h8
                    if j8 + 1 >= len(날):
                        break
                    중8, 후8, 챙8 = (_공시표X.get(날[j8]) or {}).get(
                        x8["code"], (0, 0, 0))
                    떴 = (중8 >= 1 if 갈래 == "장중"
                          else 챙8 >= 1 if 갈래 == "챙길"
                          else (중8 + 후8) >= 1)
                    if 떴:
                        찾 = j8 + 1        # **다음 날** 시가에 산다
                        break
                if 찾 is None:
                    continue               # **안 산다**
                v8 = 주가[날[찾]].get(x8["code"])
                b8 = (비.get(날[찾]) or {}).get(x8["code"])
                if not v8 or not b8:
                    continue
                산값 = v8[0] * b8[0]       # 수정종가 x (시가/종가) = **시가**
                if 산값 <= 0:
                    continue
                y8 = dict(x8)
                y8["인"] = 찾
                y8["매수"] = 산값
                y8["원시"] = 산값
                칸8.append(y8)
            if 칸8:
                새묶[i8] = 칸8             # ⭐ **열쇠는 그대로** (고른 날)
        return 새묶

    print("\n" + "=" * 108)
    print("  ⭐⭐ **빠진 뒤 공시가 뜨면 산다** — 이길 확률에서 유일하게 살아남은 것")
    print("     전체 69.9% (지금 61.2%) · 앞 75.0% · 뒤 65.6% · 산 것 1,214")
    print("  ⚠️ 공시가 **안 뜨면 안 산다.** 「산 것」이 얼마나 주는지가 결과의 절반이다")
    print("  ⚠️ 분할 매수도 ①②를 지나고 **③에서 죽었다**(-0.2%). 같은 함정일 수 있다")
    print("  ⚠️ 고르기는 **빠진 날 그대로**다. 산 날과 산 값만 밀었다")
    print("     돈은 고른 날부터 묶인다 — **우리 쪽에 불리한** 어림이다")
    print("=" * 108)
    print(머239)
    _둘("기한까지 · 다음 날 바로 산다 (지금)", _c(_H))
    for _갈8 in ("장중", "챙길", "아무"):
        _묶8 = _공시묶(_갈8)
        _건8 = sum(len(v) for v in _묶8.values())
        _둘(f"⭐ **{_갈8} 공시 뜨면 산다** (후보 {_건8:,})", _c(_H), None, _묶8)

    # ⭐⭐ **더하기 — 기존 OR 공시** (2026-09-15 20:20 · 사용자 물음)
    #    「지금 규칙 or 공시 매수하면 기회가 많아지는 거 아니야?」
    #    위 절은 **기다리는 것**(빼기)이다. 여기는 지금처럼 다 사고 **공시 종목을 보탠다**.
    #    공시 단독은 약하다(W판 20일 이김 45~46% · 바탕 44.7%) — 그래도 빈 자리를 채우는
    #    거래는 평균이 조금만 +여도 돈을 보탠다. 돈으로 잰다
    def _공시전날(x, 갈래):
        중8, 후8, 챙8 = (_공시표X.get(날[x["인"] - 1]) or {}).get(x["code"], (0, 0, 0))
        return (중8 >= 1 if 갈래 == "장중" else 챙8 >= 1 if 갈래 == "챙길"
                else (중8 + 후8) >= 1)

    def _공시신호(갈래, 빠짐=None):
        def f(x):
            if not 문통과(x):
                return False
            if 빠짐 is not None and not (x["낙폭20"] <= 빠짐):
                return False
            return _공시전날(x, 갈래)
        return f

    print("\n  ── ⭐⭐ **더하기 — 기존 OR 공시** (기다리는 게 아니라 **보탠다**) ──")
    print("     공시 종목도 재무·크기·대금 문과 08:55 상대갭 문은 똑같이 거친다")
    print(머239)
    _기공 = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
    _공OR들 = []
    for _갈8 in ("챙길", "장중", "아무"):
        for _빠8, _라8 in ((None, "빠짐 없이"), (-5.0, "낙20≤-5%")):
            _g8 = _공시신호(_갈8, _빠8)
            _n8 = sum(1 for x in 사건 if _g8(x) and not _H(x))
            _f8 = (lambda x, g=_g8: _H(x) or g(x))
            _r8 = _둘(f"{_밑글자} OR {_갈8}공시 · {_라8} (+{_n8:,}건)", _c(_f8))
            _공OR들.append((_r8["끝"], f"{_갈8}공시 · {_라8}", _f8))
    print("\n     ⚠️ 판정 셋 다 — 산 것↑ · 돈↑ · 낙폭 > -10%")

    print("\n     ── 걷기 검증 (앞 2010~2020 / 뒤 2021~2026 · 제약 없는 판) ──")
    for _해앞, _해뒤, _라9 in (("2010", "2020", "[앞]"), ("2021", "2027", "[뒤]")):
        print(f"\n   {_라9}")
        print(머)
        _기9 = 시뮬(_c(_H, 제약없음=True), 시작년=_해앞, 끝년=_해뒤)
        표(_기9, f"[견줌] {_밑글자}")
        for _, _라8, _f8 in _공OR들:
            표(시뮬(_c(_f8, 제약없음=True), 시작년=_해앞, 끝년=_해뒤),
               f"OR {_라8}"[:28], _기9)

    # ══ ⭐⭐⭐ **조합 판을 지난 13쌍을 Ⓗ 위에 얹어 4관문** ══ (2026-09-15 21:20)
    #    COMBO판 E절: 앞뒤 200쌍 중 135쌍 통과 → 「기존 OR 쌍」 셋 다인 것 13쌍.
    #    그 판의 견줌은 「기존 갈래만」(1.27억·153)이었다 — 여기서 **Ⓗ 전체** 위에 다시 잰다.
    #    자사주60↑ 이 5쌍에 든다 — 회사가 자기 주식을 사는 중인데 빠진 것
    print("\n" + "=" * 108)
    print("  ⭐⭐⭐ **조합 판(②→③)을 지난 13쌍** — Ⓗ 전체 위에 얹어 4관문")
    print("     판정: A 셋 다(산 것↑ · 돈↑ · 낙폭 > -10%) · B 걷기 앞뒤 둘 다 돈↑ · C 해마다 승>패")
    print("=" * 108)
    _증자P = _NM._증자표()
    _거시P = _NM._국내거시표(날)
    _선물열 = [(_거시P.get(d) or {}).get("코스피200선물") for d in 날]
    _선물20 = {}
    for _iP in range(20, len(날)):
        _aP, _bP = _선물열[_iP], _선물열[_iP - 20]
        if _aP and _bP and _bP > 0:
            _선물20[_iP] = (_aP / _bP - 1) * 100
    print(f"     자사주 표 {len(_증자P):,}종목 · 코스피200선물 20일 {len(_선물20):,}일", flush=True)

    _자사캐시 = {}
    # ⭐ combo 와 같은 정의로 재료를 더 만든다 (2026-09-16) — 통과 조합을 자동으로 재판정하려고
    _금값열 = [(_거시P.get(d) or {}).get("금값") for d in 날]
    _금값20 = {}
    for _iP in range(20, len(날)):
        _aP, _bP = _금값열[_iP], _금값열[_iP - 20]
        if _aP and _bP and _bP > 0:
            _금값20[_iP] = (_aP / _bP - 1) * 100
    _ETFX = _NM._ETF자금표(날)
    _ETF순 = [_ETFX.get(d) for d in 날]
    _ETF시총20 = {}
    for _iP in range(20, len(날)):
        if _ETF순[_iP] and _ETF순[_iP - 20] and _ETF순[_iP - 20][1] > 0:
            _ETF시총20[_iP] = (_ETF순[_iP][1] / _ETF순[_iP - 20][1] - 1) * 100
    import bisect as _bsP
    try:
        _달력P = json.load(io.open(os.path.join(O._DATA, "event-calendar.json"), encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        _달력P = {}
    # ⚠️ 금통위는 그날 10시에 정한다 — 08:55 판정은 모른다 → **다음 거래일**부터 (bisect_right)
    _금통자리P = sorted({_bsP.bisect_right(날, d) for d in (_달력P.get("금통위변경") or {}) if _bsP.bisect_right(날, d) < len(날)})

    # ⭐ ECOS 둘 (2026-09-16 · combo4_lab 과 같은 정의) — pairs3 가 「못 만드는 재료」로 건너뛴 조합을 재려고
    def _ecosP(이름):
        try:
            return (json.load(io.open(os.path.join(O._DATA, "ecos", f"{이름}.json"), encoding="utf-8")).get("값") or {})
        except Exception:  # noqa: BLE001
            return {}
    _수출P, _수입P, _기준P = _ecosP("수출금액"), _ecosP("수입금액"), _ecosP("기준금리")
    _기준일P = sorted(_기준P)

    def _알수있는달P(d8, 늦춤일):
        y, m = int(d8[:4]), int(d8[4:6])
        if int(d8[6:8]) < 늦춤일:
            m -= 1
        m -= 1
        while m <= 0:
            m += 12
            y -= 1
        return f"{y}{m:02d}"

    def _무역수지비P(i):
        ym = _알수있는달P(날[i], 2)
        a, b = _수출P.get(ym), _수입P.get(ym)
        return ((a - b) / a * 100) if (a and b and a > 0) else None

    def _기준금리20P(i):
        if i < 21 or not _기준일P:
            return None
        def _v(dd):
            p = _bsP.bisect_right(_기준일P, dd) - 1
            return _기준P[_기준일P[p]] if p >= 0 else None
        a, b = _v(날[i - 1]), _v(날[i - 21])
        return (a - b) if (a is not None and b is not None) else None
    print(f"     ECOS: 수출 {len(_수출P)}달 · 수입 {len(_수입P)}달 · 기준금리 {len(_기준P)}일")

    def _뒤NP(자리들, i, n):
        p = _bsP.bisect_right(자리들, i) - 1
        return 1.0 if (p >= 0 and i - 자리들[p] <= n) else 0.0

    _괴리표P = _NM._ETF괴리표(날)
    _괴리열P = [_괴리표P.get(d) for d in 날]

    _계절표P = {"12": "겨울", "01": "겨울", "02": "겨울", "03": "봄", "04": "봄", "05": "봄",
               "06": "여름", "07": "여름", "08": "여름", "09": "가을", "10": "가을", "11": "가을"}

    # ⭐ 미국 선거 · 미국 금리차 (2026-09-18) — BAND 판에서 대형주 띠 1위가 「미국선거전5」였는데 gate7 이 못 만들었다
    _미선P = sorted({_bsP.bisect_right(날, d) for d in (_달력P.get("미국선거") or [])
                     if _bsP.bisect_right(날, d) < len(날)})

    def _앞NP(자리들, i, n):
        q = _bsP.bisect_right(자리들, i)
        return 1.0 if (q < len(자리들) and 0 < 자리들[q] - i <= n) else 0.0
    print(f"     미국 선거 {len(_미선P)}회")

    def _값P(x, 재):
        if 재 == "미국선거전5":
            return _앞NP(_미선P, x["인"] - 1, 5)
        if 재 in ("봄", "여름", "가을", "겨울"):
            return 1.0 if _계절표P[날[x["인"] - 1][4:6]] == 재 else 0.0
        if 재 == "ETF괴리":
            return _괴리열P[x["인"] - 1]
        if 재 == "ETF괴리20":
            _iq = x["인"] - 1
            return (_괴리열P[_iq] - _괴리열P[_iq - 20]) if (_iq >= 20 and _괴리열P[_iq] is not None and _괴리열P[_iq - 20] is not None) else None
        if 재 == "기준금리20":
            return _기준금리20P(x["인"] - 1)
        if 재 == "무역수지비":
            return _무역수지비P(x["인"] - 1)
        if 재 == "금통위변경후5":
            return _뒤NP(_금통자리P, x["인"] - 1, 5)
        if 재 == "ETF시총20":
            return _ETF시총20.get(x["인"] - 1)
        if 재 == "금값20":
            return _금값20.get(x["인"] - 1)
        if 재 == "공시장중":
            중9, _후9, _챙9 = (_공시표X.get(날[x["인"] - 1]) or {}).get(x["code"], (0, 0, 0))
            return float(중9)
        if 재 == "코스피200선물20":
            return _선물20.get(x["인"] - 1)
        # ⭐ 2026-09-23 (B1·G1) — 판 안에 이미 있는데 **칸 판에 한 번도 안 들어간** 표들
        if 재 == "무리낙폭":
            return _무리낙폭(x)
        if 재 == "무리와벌어짐":
            _무9 = _무리낙폭(x)
            _내9 = x.get("낙폭20")
            return None if (_무9 is None or _내9 is None) else (_내9 - _무9)
        if 재 == "지수갭":
            return _지수갭.get(x["인"] - 1)
        if 재 == "악재공시":
            return float((_악재표.get(날[x["인"] - 1]) or {}).get(x["code"], 0))
        if 재 == "자사주60":
            k = (x["code"], x["인"])
            if k not in _자사캐시:
                i = x["인"] - 1
                _자사캐시[k] = _NM._증자재기(_증자P, x["code"], "자사주취득", 날[i], R.자사주창일, 날, i)
            return _자사캐시[k]
        return x.get(재)

    # ⭐ 최신 COMBO*.txt E절 판정표의 「✅ **셋 다**」 조합을 읽는다 (2026-09-16). 손으로 옮기다 빠뜨리지 않게
    _조합들P = []
    try:
        import re as _reP
        # ⚠️⚠️ **2026-09-20 고침** — 이름에 COMBO 가 든 파일만 찾고 있었다.
        #    주말 판 이름이 WIDE · TURN · MKT2 · RISE2 로 바뀌면서 **하나도 안 걸렸고**,
        #    P절이 9/19 부터 내내 **손으로 적어둔 11쌍**으로 돌았다 (새 조합을 하나도 안 봤다).
        #    WIDE 한 파일에만 「셋 다」가 68건 들어 있었다.
        #    ⇒ **이름으로 찾지 말고 판정표가 든 파일을 전부** 본다 (안에서 다시 거른다)
        _cf = sorted(glob.glob(os.path.join(O._DATA, "_labs", "2026-*.txt")), key=os.path.getmtime, reverse=True)
        # ⚠️ 첫 파일만 읽고 break 하면 combo3(ECOS)가 새로 생긴 뒤엔 combo2 의 18개를 놓친다 (2026-09-16 11:50)
        #    → 최근 3일 안의 COMBO 파일을 **전부 합친다** (겹치면 하나로)
        import time as _tmP
        _cf = [f for f in _cf if _tmP.time() - os.path.getmtime(f) < 5 * 86400][:30]
        for _f in _cf:
            _t = io.open(_f, encoding="utf-8", errors="replace").read()
            if "── 판정 (기존 OR 쌍" not in _t:
                continue
            _앞 = len(_조합들P)
            _seg = _t.split("── 판정 (기존 OR 쌍", 1)[1].split("── F", 1)[0]
            for _ln in _seg.splitlines():
                if "✅ **셋 다**" in _ln:
                    _라 = _ln.strip().split("  ")[0].strip()
                    _부 = [p.strip() for p in _라.split(" + ") if p.strip()]
                    if 2 <= len(_부) <= 4 and all(p[-1] in "↑↓" for p in _부):
                        _조 = tuple((p[:-1], p[-1]) for p in _부)
                        if _조 not in _조합들P:
                            _조합들P.append(_조)
            print(f"     통과 조합 +{len(_조합들P) - _앞}개 ← {os.path.basename(_f)} (누계 {len(_조합들P)})")
    except Exception as _e:  # noqa: BLE001
        print(f"     ⚠️ combo 판정표를 못 읽었다 ({type(_e).__name__}) — 손으로 적은 11쌍으로")
    if not _조합들P:
        print("     ⚠️ COMBO 판정표에서 「셋 다」 조합을 못 찾았다 — **손으로 적은 11쌍으로** (조용히 넘어가지 않게 찍는다)")
        _조합들P = [(("낙폭20", "↓"), ("상대강도", "↑")), (("낙폭20", "↓"), ("섹터대비", "↑")),
                    (("낙폭20", "↓"), ("자사주60", "↑")), (("낙폭60", "↓"), ("자사주60", "↑")),
                    (("볼린저", "↓"), ("상대강도", "↑")), (("소형우위", "↓"), ("시장낙폭", "↓")),
                    (("소형우위", "↓"), ("코스피200선물20", "↓")), (("순이익률", "↑"), ("코스피200선물20", "↓")),
                    (("시장낙폭", "↓"), ("자사주60", "↑")), (("시총억", "↓"), ("자사주60", "↑")),
                    (("자사주60", "↑"), ("코스피200선물20", "↓"))]
    _쌍들P = _조합들P
    _재료P = sorted({p[0] for 조 in _쌍들P for p in 조})
    _문턱P = {}
    _못만듦P = [재 for 재 in _재료P if _값P(사건[0], 재) is None and all(_값P(x, 재) is None for x in 사건[:2000])
               and 재 not in ("금통위변경후5", "ETF시총20", "금값20", "공시장중", "코스피200선물20", "자사주60",
                              "기준금리20", "무역수지비", "ETF괴리", "ETF괴리20", "봄", "여름", "가을", "겨울",
                              "미국선거전5")
               and 재 not in (사건[0].keys())]
    if _못만듦P:
        print(f"     ⚠️ gate7 이 못 만드는 재료 {len(_못만듦P)}개 — 그 재료가 든 조합은 건너뛴다: {', '.join(_못만듦P)}")
    for 재 in _재료P:
        if 재 in _못만듦P:
            continue
        v = sorted(z for z in (_값P(x, 재) for x in 사건) if z is not None)
        if len(v) < len(사건) * 0.3:
            print(f"     {재:<14} 값이 {len(v):,}개뿐 — 건너뜀")
            continue
        낮, 높 = v[len(v) // 5], v[len(v) * 4 // 5]
        _문턱P[재] = (낮, 높, 낮 == 높)
        print(f"     {재:<14} 아래 20% ≤ {낮:,.2f} · 위 20% ≥ {높:,.2f}"
              + ("  (몰림 → 「그 값보다」)" if 낮 == 높 else ""))

    def _조건P(x, 재, 방):
        if 재 not in _문턱P:
            return False
        v = _값P(x, 재)
        if v is None:
            return False
        낮, 높, 몰 = _문턱P[재]
        return ((v < 낮) if 몰 else (v <= 낮)) if 방 == "↓" else ((v > 높) if 몰 else (v >= 높))

    def _쌍거름(조):
        return lambda x: 문통과(x) and all(_조건P(x, a, da) for a, da in 조)

    print("\n  ── A ⭐⭐⭐ **Ⓗ OR 쌍** (셋 다여야 ✅) ──")
    print(머239)
    _기P = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
    _기P1 = _둘.r1
    # ⭐ ㉣ 의 실전 효과 (2026-09-16 밤 · pairs8): Ⓗ 2.581억 vs 소형만 2.541억 = +1.6% 인데 BIG5 는 +10% 라 했다.
    #    BIG5 D-2 는 시총하한 0 · VANISH_KIND=1 로 쟀다 — 실전(300억 하한 · 사라짐 −50%)과 다르다. 같은 판에서 나란히 찍는다
    def _H소형만(x):
        if not 문통과(x):
            return False
        return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                or 섹터맞나(x) or _시7(x) or _밑끝갈래(x))
    _둘(f"{_밑글자} 소형만 (㉣ 끔 · 견줌)", _c(_H소형만))
    # ⭐ ㉤ 만 끈 줄 (2026-09-17 · 사용자 「그게 무슨 뜻이야?」 → 어젯밤 판과 오늘 판은 설정이 달라 섞였다.
    #    같은 판 안에서 ㉤ 만 껐다 켜야 깨끗하다). ㉣ 은 그대로 두고 변동성·자사주 갈래만 뺀다
    def _H변자끔(x):
        if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
            return True
        if not 문통과(x):
            return False
        return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                or 섹터맞나(x) or _시7(x) or _밑끝갈래(x))
    _둘(f"{_밑글자} ㉤ 끔 (변동성·자사주 빼고 · 견줌)", _c(_H변자끔))
    # ⭐⭐⭐ ㉢ 만 끈 줄 (2026-09-19 · **시장표 버그를 고친 뒤 꼭 봐야 하는 줄**)
    #    9/19 까지 시장표가 텅 비어 **코스닥 1,823종목(66%)이 코스피 지수로** 시장낙폭·변동성을 봤다.
    #    ㉢(지수 20일 −7% / 60일 −10%)과 ㉤(지수 20일 변동성)은 **둘 다 그 값 위에 세운 갈래**다.
    #    지수를 제대로 붙인 지금, 두 갈래가 여전히 제값을 하는지 같은 판에서 나란히 찍는다
    def _H시장끔(x):
        if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
            return True
        if not 문통과(x):
            return False
        if (R.변동성자사주_켬 and x.get("시장변동성") is not None
                and x["시장변동성"] >= R.시장변동성문턱 and _자사H(x) >= 1):
            return True
        return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                or 섹터맞나(x))
    _둘(f"{_밑글자} ㉢ 끔 (시장 갈래 빼고 · 견줌)", _c(_H시장끔))

    # ══ ⭐⭐⭐ **Q 문턱을 제대로 된 지수로 다시 훑는다** (2026-09-19 밤) ══
    #    ㉢ 도 ㉤ 도 지수 값 위에 세운 갈래인데, 그 지수가 틀렸었다
    #    (코스닥 1,823종목 = 사건의 63% 가 코스피 지수로 계산됐다).
    #    지금 문턱 넷은 **코스피만 보고 고른 값**이다 — 제대로 섞어 다시 고른다
    print("\n" + "=" * 122)
    import time as _tQ
    _t0Q = _tQ.time()
    print(f"  ⏱ 준비가 끝난 시각 — 여기까지 {_tQ.time() - _시작시각:.0f}초", flush=True)
    if _ONLY:
        print(f"\n  ⭐ ONLY={_ONLY} — 그 절만 돈다 (옛 절은 건너뛴다)", flush=True)
    print("  ── Q ⭐⭐⭐ **㉢·㉤ 문턱 다시** — 코스닥이 제 지수를 쓰게 된 뒤 처음 훑는다 ──")
    print("     지금 값: ㉢ 20일 {:g}% · 60일 {:g}%  |  ㉤ 변동성 {:g}% · 자사주 {}일"
          .format(R.지수낙20문턱, R.지수낙60문턱, R.시장변동성문턱, R.자사주창일))
    print("=" * 122)
    _기Q = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
    _기Q1 = _둘.r1

    def _판정Q(r1):
        ok = (r1["산"] > _기Q1["산"], r1["끝"] > _기Q1["끝"], r1["낙"] > 낙폭기준)
        return ("✅ 셋 다" if all(ok) else "❌"), (r1["끝"] / _기Q1["끝"] * 100)

    # ── Q-1  ㉢ 문턱 격자 ──
    print("\n  ── Q-1 **㉢ 시장 갈래 문턱** (지수 20일 x 60일) ──")
    print(f"     {'20일':>7}{'60일':>7}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    # ⭐ None = **60일 갈래를 아예 끈다.** 9/20 첫 판에서 실수로 이걸 재고 있었는데
    #    (없는 칸을 읽어 늘 거짓이었다) 결과가 뜻밖에 좋았다 — 낙폭 -11.0% → -7.0%.
    #    실수였지만 물음 자체는 값지다. 이번엔 **일부러** 같이 잰다
    for _n20 in (-4.0, -5.0, -6.0, -7.0, -9.0, -12.0):
        for _n60 in (None, -6.0, -8.0, -10.0, -13.0, -16.0):
            def _HQ1(x, a=_n20, b=_n60):
                if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
                    return True
                if not 문통과(x):
                    return False
                if (R.변동성자사주_켬 and x.get("시장변동성") is not None
                        and x["시장변동성"] >= R.시장변동성문턱 and _자사H(x) >= 1):
                    return True
                _시a = (x.get("시장낙폭") is not None and x["시장낙폭"] <= a)
                _시b = (b is not None and _시낙(x, 60, b))   # ⚠️ 2026-09-20 고침: gate7 에 "시장낙60" 이라는 칸은 **없다**.
                #    x.get("시장낙60") 은 늘 None 이라 60일 갈래가 **통째로 꺼진 채** 돌았다.
                #    실전의 ㉢ 는 60일 쪽이 주력인데(9/17 까지 7일 내내 20일은 꺼져 있었다)
                #    그 갈래를 안 재고 있었다. _시낙(x,60,문) 이 진짜 값이다
                return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                        or 섹터맞나(x) or _시a or _시b)
            _r = 시뮬(_c(_HQ1))
            if not _r:
                continue
            _판, _몫 = _판정Q(_r)
            _지금인가 = "  ← 지금" if (_n20 == R.지수낙20문턱 and _n60 == R.지수낙60문턱) else ""
            _글60 = "끔" if _n60 is None else f"{_n60:.0f}"
            print(f"     {_n20:>7.0f}{_글60:>7}{_r['끝']:>16,.0f}원{_몫:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}  {_판}{_지금인가}")

    # ── Q-2  ㉤ 문턱 격자 ──
    #    ⚠️ 자사주 창을 바꾸면 _자사H캐시 를 못 쓴다 — 창마다 따로 센다
    print("\n  ── Q-2 **㉤ 변동성·자사주 문턱** (지수 20일 변동성 x 자사주 창) ──")
    print("     ⚠️ 1.42 는 **코스피만 보고 낸 위 20% 컷**이다. 코스닥이 섞이면 분포가 달라진다")
    # ⚠️ **메모리** — (code, 인, 창) 으로 캐시를 잡으면 창 여섯 배로 불어난다.
    #    시험 하나가 이미 18~23GB 를 쓴다. 그래서 **창을 바깥 고리로 돌리고
    #    창이 바뀔 때마다 캐시를 비운다** — 한 번에 창 하나치만 들고 있는다
    _변캐시 = {}

    def _자사창(x, 창):
        k = (x["code"], x["인"])
        if k not in _변캐시:
            i = x["인"] - 1
            _변캐시[k] = _NM._증자재기(_증자H, x["code"], "자사주취득", 날[i], 창, 날, i)
        return _변캐시[k]

    print(f"     {'변동성':>7}{'자사주창':>9}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    for _ww in (3, 5, 10, 20, 60, 120):
        _변캐시.clear()          # ⭐ 창이 바뀌면 통째로 버린다
        for _vv in (1.00, 1.20, 1.42, 1.70, 2.00):
            def _HQ2(x, v=_vv, w=_ww):
                if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
                    return True
                if not 문통과(x):
                    return False
                if (x.get("시장변동성") is not None
                        and x["시장변동성"] >= v and _자사창(x, w) >= 1):
                    return True
                return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                        or 섹터맞나(x) or _시7(x) or _밑끝갈래(x))
            _r = 시뮬(_c(_HQ2))
            if not _r:
                continue
            _판, _몫 = _판정Q(_r)
            _지금인가 = "  ← 지금" if (_vv == R.시장변동성문턱 and _ww == R.자사주창일) else ""
            print(f"     {_vv:>7.2f}{_ww:>9}{_r['끝']:>16,.0f}원{_몫:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}  {_판}{_지금인가}")

    # ── Q-3  지수 변동성이 제대로 섞인 뒤 **오분위가 어떻게 됐나** ──
    print("\n  ── Q-3 **지수 20일 변동성 분포** — 코스닥이 섞인 뒤 ──")
    _vs = sorted(x["시장변동성"] for x in 사건 if x.get("시장변동성") is not None)
    _vs닥 = sorted(x["시장변동성"] for x in 사건
                   if x.get("시장변동성") is not None and x.get("_지수이름") == "코스닥")
    _vs피 = sorted(x["시장변동성"] for x in 사건
                   if x.get("시장변동성") is not None and x.get("_지수이름") == "코스피")
    for _라, _벌 in (("전체", _vs), ("코스닥", _vs닥), ("코스피", _vs피)):
        if len(_벌) < 100:
            continue
        def _q(p, z=_벌):
            return z[int(len(z) * p)]
        print(f"     {_라:<6}{len(_벌):>10,}건  "
              f"아래20% {_q(0.20):.2f} · 가운데 {_q(0.50):.2f} · "
              f"위20% {_q(0.80):.2f} · 위10% {_q(0.90):.2f} · 위5% {_q(0.95):.2f}")
    print("     ⚠️ **위20% 가 1.42 에서 얼마나 움직였는지**가 ㉤ 문턱을 다시 정할 근거다")

    # ── Q-4 ⭐⭐⭐ **㉢ 문턱을 시장마다 따로** ──
    #    같은 -7% 인데 넘는 날이 코스피 214일 · 코스닥 416일로 **두 배** 차이다.
    #    코스닥은 원래 더 흔들린다 — 한 문턱을 둘에 같이 쓰면 코스닥에선 너무 자주 켜져
    #    평범한 날까지 사고, 코스피에선 너무 드물게 켜진다.
    #    사용자: 「한가지 규칙일 필요없고 … 규칙은 여러개여도 돼」 — 시장도 그 갈래다
    print("\n  ── Q-4 ⭐⭐⭐ **㉢ 문턱을 시장마다 따로** (코스피 x 코스닥 · 20일) ──")
    print("     같은 -7% 인데 넘는 날이 코스피 214일 · 코스닥 416일 — 두 배 차이다")
    print(f"     {'코스피':>8}{'코스닥':>8}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    for _p4 in (-5.0, -6.0, -7.0, -9.0):
        for _k4 in (-7.0, -9.0, -11.0, -14.0):
            def _HQ4(x, a=_p4, b=_k4):
                if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
                    return True
                if not 문통과(x):
                    return False
                if (R.변동성자사주_켬 and x.get("시장변동성") is not None
                        and x["시장변동성"] >= R.시장변동성문턱 and _자사H(x) >= 1):
                    return True
                _문4 = b if x.get("_지수이름") == "코스닥" else a
                _시4 = (x.get("시장낙폭") is not None and x["시장낙폭"] <= _문4)
                return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                        or 섹터맞나(x) or _시4 or _밑끝갈래(x))
            _r = 시뮬(_c(_HQ4))
            if not _r:
                continue
            _판, _몫 = _판정Q(_r)
            _같나 = "  ← 지금(둘 다 -7)" if (_p4 == -7.0 and _k4 == -7.0) else ""
            print(f"     {_p4:>8.0f}{_k4:>8.0f}{_r['끝']:>16,.0f}원{_몫:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}  {_판}{_같나}")
    print("     ⚠️ 문턱을 둘로 나누면 **고를 것이 하나 더 는다** — 걷기 앞뒤가 같아야 믿는다")

    # ── Q-5 **코스닥만 / 코스피만 사면** (규칙은 그대로) ──
    #    「시장으로 쪼개면」이 9/19 판에서 코스피 칸 하나만 나와 못 봤던 물음이다
    print("\n  ── Q-5 **한 시장만 사면** (규칙은 지금 그대로) ──")
    for _라5, _fn5 in (("코스닥만", lambda x: x.get("_지수이름") == "코스닥"),
                       ("코스피만", lambda x: x.get("_지수이름") != "코스닥")):
        _r = 시뮬(_c(lambda x, g=_fn5: _H(x) and g(x)))
        if not _r:
            continue
        _판, _몫 = _판정Q(_r)
        print(f"     {_라5:<10}{_r['끝']:>16,.0f}원{_몫:>8.0f}%"
              f"{_r['낙']:>7.1f}%{_r['산']:>7}  {_판}")
    print("     ⚠️ 한 쪽만 사면 기회가 준다 — 사용자 1순위(상승 기회)와 어긋난다. 숫자만 남긴다")

    # ── Q-6 ⭐⭐⭐ **빠지는 장엔 더 산다** ──
    #    9/19: 빠지는 장 바탕 59.8% · 횡보 41.1% — 바탕이 20%p 다른 날에
    #    늘 같은 수(하루 4자리)만 사는 건 아깝다.
    #    사용자 1순위가 「상승 기회를 놓치지 않는 것」이라 **좋은 날에 더 사기**를 잰다
    print("\n  ── Q-6 ⭐⭐⭐ **빠지는 장엔 더 산다** (하루 상한을 날마다 다르게) ──")
    print("     9/19 판: 빠지는 장 바탕 59.8% · 오르는 장 42.7% · 횡보 41.1%")
    print("     ⚠️ 자리를 늘리면 「한 종목 자산의 20%」 가정이 흔들린다 — 비중 낮춘 줄도 같이 본다")
    print(f"     {'평소':>6}{'빠지는장':>9}{'비중':>7}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")

    def _빠진장인가(골):
        """그날 후보들이 본 시장 낙폭. 후보가 없으면 상한은 뜻이 없다"""
        for z in 골:
            v = z.get("시장낙폭")
            if v is not None:
                return v <= -5.0
        return False

    for _평, _빠 in ((4, 5), (4, 6), (4, 8), (4, 10), (3, 6), (3, 8)):
        for _비 in (0.20, 0.15):
            def _상한Q6(골, a=_평, b=_빠):
                return b if _빠진장인가(골) else a
            _r = 시뮬(_c(_H, 하루상한=_상한Q6, 비중=_비))
            if not _r:
                continue
            _판, _몫 = _판정Q(_r)
            _지금인가 = "  ← 지금" if (_평 == 4 and _빠 == 4 and _비 == 0.20) else ""
            print(f"     {_평:>6}{_빠:>9}{_비:>7.2f}{_r['끝']:>16,.0f}원{_몫:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}  {_판}{_지금인가}")
    # 견줌 — 평소도 늘리면 (국면과 상관없이 그냥 많이 사면) 어떻게 되나
    print("     ── 견줌: 국면 안 보고 **그냥 늘리면** ──")
    for _n6 in (5, 6, 8):
        _r = 시뮬(_c(_H, 하루상한=_n6))
        if not _r:
            continue
        _판, _몫 = _판정Q(_r)
        print(f"     {_n6:>6}{_n6:>9}{0.20:>7.2f}{_r['끝']:>16,.0f}원{_몫:>8.0f}%"
              f"{_r['낙']:>7.1f}%{_r['산']:>7}  {_판}")
    print("     ⚠️ **국면을 볼 때만** 좋아져야 뜻이 있다 — 그냥 늘려도 같으면 국면은 상관없는 것이다")

    # ── Q-7 ⭐⭐⭐ **유상증자 거르개를 4관문에** ──
    #    MKT3: Ⓗ + 유상증자 60일 빼기 = 돈 102% · 낙폭 -11.0% -> -7.3% · 산 것 +2 — **셋 다**
    #    ㉢ 를 끄면 낙폭이 고쳐지지만 기회가 90건 날아간다. 이건 **기회를 늘리면서** 고친다.
    #    ⚠️ 틀린 지수 판에서는 안 보였다 — 그땐 낙폭이 이미 -5.9% 라 고칠 게 없었다
    print("\n" + "=" * 122)
    print("  ── Q-7 ⭐⭐⭐ **유상증자 거르개를 4관문에** ──")
    print("     MKT3: 돈 102% · 낙폭 -11.0% → -7.3% · 산 것 +2 — 셋 다였다. 진짜인지 본다")
    print("     가설: 크게 빠진 장에서 유상증자하는 회사는 희석까지 겹쳐 더 깊게 빠진다")
    print("=" * 122)
    _증자Q = _증자H if _증자H else _NM._증자표()

    # ⚠️ **속도·메모리** — 시뮬 한 판이 사건 70만 건을 훑고, 아래에서 판을 30번 넘게 돌린다.
    #    캐시가 없으면 _증자재기 가 2천만 번 넘게 불린다. 창이 바뀌면 통째로 버린다
    #    (창까지 열쇠에 넣으면 창 다섯 배로 불어난다 — 판 하나가 이미 18~23GB 다)
    _유증캐시, _유증창 = {}, [None]

    def _유증없나(x, 창=60):
        if _유증창[0] != 창:
            _유증캐시.clear()
            _유증창[0] = 창
        k = (x["code"], x["인"])
        if k not in _유증캐시:
            i = x["인"] - 1
            _유증캐시[k] = (_NM._증자재기(_증자Q, x["code"], "유상증자", 날[i], 창, 날, i) == 0)
        return _유증캐시[k]

    def _H유증(x, 창=60):
        return _H(x) and _유증없나(x, 창)

    # Q-7c 창 넓이 먼저 (어느 창이 제일 나은지 보고 그 창으로 4관문)
    print("\n  ── Q-7c **창 넓이** ──")
    print(f"     {'창':>6}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙':>8}  판정")
    _최선창, _최선점 = 60, None
    for _cw in (30, 60, 90, 120, 180):
        _r = 시뮬(_c(lambda x, w=_cw: _H유증(x, w)))
        if not _r:
            continue
        _판, _몫 = _판정Q(_r)
        _점 = _r["끝"] / max(abs(_r["낙"]), 3.0) / 1e6
        if _최선점 is None or _점 > _최선점:
            _최선창, _최선점 = _cw, _점
        print(f"     {_cw:>6}{_r['끝']:>16,.0f}원{_몫:>8.0f}%{_r['낙']:>7.1f}%"
              f"{_r['산']:>7}{_점:>8.1f}  {_판}")
    print(f"     ⇒ 돈÷낙폭이 제일 좋은 창 **{_최선창}일** — 아래 4관문은 이 창으로")

    # Q-7a 해마다 (4관문 B)
    print("\n  ── Q-7a **해마다 승패** (4관문 B) ──")
    print(f"   {'해':<8}{'견줌 Ⓗ':>18}{'유증 빼기':>18}{'차이':>9}{'Ⓗ 낙':>9}{'도전 낙':>9}")
    _차Q, _낙Q = [], []
    for _yQ in range(2016, 2027):
        _aQ = 시뮬(_c(_H), 시작년=str(_yQ), 끝년=str(_yQ))
        _bQ = 시뮬(_c(lambda x, w=_최선창: _H유증(x, w)), 시작년=str(_yQ), 끝년=str(_yQ))
        if not _aQ or not _bQ:
            continue
        _dQ = (_bQ["끝"] / _aQ["끝"] - 1) * 100 if _aQ["끝"] > 0 else 0
        _차Q.append(_dQ)
        _낙Q.append(_bQ["낙"] - _aQ["낙"])      # + 면 덜 깊어진 것
        print(f"   {_yQ:<8}{_aQ['끝']:>17,.0f}원{_bQ['끝']:>17,.0f}원{_dQ:>+8.1f}%"
              f"{_aQ['낙']:>8.1f}%{_bQ['낙']:>8.1f}%")
    _글Q, _좋Q = _해마다판정(_차Q, _낙Q)
    print(f"     ⇒ {_글Q}")

    # Q-7b 걷기 앞뒤 (4관문 C)
    print("\n  ── Q-7b **걷기 앞뒤** (4관문 C) ──")
    print(f"     {'구간':<14}{'견줌 Ⓗ':>18}{'유증 빼기':>18}{'차이':>9}{'Ⓗ 낙':>9}{'도전 낙':>9}")
    _걷기찍기(_걷기(lambda x, w=_최선창: _H유증(x, w)), 들여="     ")

    # Q-7d 유증 빼기를 켠 채로 ㉢ 문턱을 다시 (둘이 겹치나)
    print("\n  ── Q-7d **유증 빼기 + ㉢ 문턱** — 둘이 같은 것을 고치나 ──")
    print("     유증 빼기가 이미 낙폭을 고쳤다면, ㉢ 문턱은 안 건드려도 될 수 있다")
    print(f"     {'20일':>7}{'60일':>7}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    for _n20 in (-5.0, -7.0, -9.0):
        for _n60 in (None, -8.0, -10.0, -13.0):
            def _HQ7(x, a=_n20, b=_n60, w=_최선창):
                if not _유증없나(x, w):
                    return False
                if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
                    return True
                if not 문통과(x):
                    return False
                if (R.변동성자사주_켬 and x.get("시장변동성") is not None
                        and x["시장변동성"] >= R.시장변동성문턱 and _자사H(x) >= 1):
                    return True
                _시a = (x.get("시장낙폭") is not None and x["시장낙폭"] <= a)
                _시b = (b is not None and _시낙(x, 60, b))   # ⚠️ 2026-09-20 고침: gate7 에 "시장낙60" 이라는 칸은 **없다**.
                #    x.get("시장낙60") 은 늘 None 이라 60일 갈래가 **통째로 꺼진 채** 돌았다.
                #    실전의 ㉢ 는 60일 쪽이 주력인데(9/17 까지 7일 내내 20일은 꺼져 있었다)
                #    그 갈래를 안 재고 있었다. _시낙(x,60,문) 이 진짜 값이다
                return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                        or 섹터맞나(x) or _시a or _시b)
            _r = 시뮬(_c(_HQ7))
            if not _r:
                continue
            _판, _몫 = _판정Q(_r)
            print(f"     {_n20:>7.0f}{('끔' if _n60 is None else '%.0f' % _n60):>7}{_r['끝']:>16,.0f}원{_몫:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}  {_판}")
    print("     ⚠️ 거르개는 **실전 코드를 건드린다** — 통과해도 사용자 확인 뒤에 넣는다")

    # ── Q-8 ⭐⭐⭐ **「낙폭 -10% 안」 기준을 바꾸면 판정이 달라지나** ──
    #    사용자가 정해야 할 것 3번이다. 그런데 **근거 기록이 없다.**
    #    정하기 전에 「그 숫자가 실제로 무엇을 가르는지」를 보여야 한다.
    #    지금 Ⓗ 가 -11.0% 라 -10% 기준에 **딱 걸려 있다** — 이 숫자 하나로 규칙이 서고 넘어진다
    print("\n" + "=" * 122)
    print("  ── Q-8 ⭐⭐⭐ **「낙폭 −10% 안」을 바꾸면 무엇이 달라지나** ──")
    print("     이 기준의 근거는 **기록이 없다**. 정하기 전에 무엇을 가르는 숫자인지 본다")
    print("     지금 Ⓗ 가 −11.0% 라 −10% 에 딱 걸려 있다 — 이 한 숫자로 규칙이 서고 넘어진다")
    print("=" * 122)
    _볼것Q8 = [
        ("Ⓗ 지금", _H),
        ("Ⓗ ㉢ 끔", _H시장끔),
        ("Ⓗ ㉤ 끔", _H변자끔),
        ("Ⓗ + 유상증자 60일 빼기", lambda x: _H(x) and _유증없나(x, 60)),
    ]
    _잰Q8 = []
    for _라8, _fn8 in _볼것Q8:
        _r = 시뮬(_c(_fn8))
        if _r:
            _잰Q8.append((_라8, _r))
    print(f"     {'설정':<26}{'끝 자산':>17}{'낙폭':>8}{'산 것':>7}   "
          + "".join(f"{'≤' + str(t) + '%':>9}" for t in (-8, -10, -12, -15)))
    for _라8, _r in _잰Q8:
        _칸 = "".join(("      ✅  " if _r["낙"] > t else "      ❌  ") for t in (-8, -10, -12, -15))
        print(f"     {_라8:<26}{_r['끝']:>16,.0f}원{_r['낙']:>7.1f}%{_r['산']:>7}   {_칸}")
    print("     ⇒ 기준을 **−12% 로 풀면** 지금 Ⓗ 가 통과하고, **−8% 로 조이면** 거르개까지 걸린다")
    print("     ⚠️ 기준은 내가 정하지 않는다 — **사용자가 정한다.** 이 표는 그 판단 재료다")

    # ── Q-9 ⭐⭐ **보류 중인 후보 3호를 제대로 된 지수로 다시** ──
    #    기준금리20↓ + 코스피200선물20↓ — 2026-09-17 에 103% · 2승 0패로 통과했는데
    #    「금리 인하기에만 켜진다」는 이유로 사용자가 보류했다.
    #    그 판도 **틀린 지수**로 돌았다 — 숫자부터 다시 본다
    print("\n  ── Q-9 ⭐⭐ **보류 중인 후보 3호** (기준금리20↓ + 선물20↓) — 지수 고친 뒤 ──")
    _쌍9 = (("기준금리20", "↓"), ("코스피200선물20", "↓"))
    # ⚠️⚠️ **2026-09-20 고침** — 9/20 첫 판에서 이 절이 통째로 건너뛰어졌다.
    #    앞 절이 COMBO 판정표를 못 읽어 손으로 적은 11쌍으로 되돌아갔고,
    #    그 11쌍에 기준금리20 이 없어 _문턱P 에 안 들어갔다.
    #    _값P 는 기준금리20 을 만들 수 있다 — **문턱만 여기서 직접 내면 된다**
    for _재9 in (재 for 재, _ in _쌍9):
        if _재9 in _문턱P:
            continue
        _v9 = sorted(z for z in (_값P(x, _재9) for x in 사건) if z is not None)
        if len(_v9) < len(사건) * 0.3:
            print(f"     ⚠️ {_재9} — 값이 {len(_v9):,}개뿐 (사건의 "
                  f"{len(_v9) / max(len(사건), 1) * 100:.0f}%) 이라 문턱을 못 낸다")
            continue
        _낮9, _높9 = _v9[len(_v9) // 5], _v9[len(_v9) * 4 // 5]
        _문턱P[_재9] = (_낮9, _높9, _낮9 == _높9)
        print(f"     {_재9} 문턱을 여기서 냈다 — 아래 20% ≤ {_낮9:,.2f} · 위 20% ≥ {_높9:,.2f}"
              + ("  (몰림)" if _낮9 == _높9 else ""))
    if all(재 in _문턱P for 재, _ in _쌍9):
        def _H3호(x):
            return _H(x) or (문통과(x) and all(_조건P(x, 재, 방) for 재, 방 in _쌍9))
        _r9 = 시뮬(_c(_H3호))
        _기9 = 시뮬(_c(_H))
        if _r9 and _기9:
            _판9, _몫9 = _판정Q(_r9)
            print(f"     {'설정':<26}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            print(f"     {'Ⓗ (지금 · 견줌)':<26}{_기9['끝']:>16,.0f}원{100:>8.0f}%"
                  f"{_기9['낙']:>7.1f}%{_기9['산']:>7}")
            print(f"     {'Ⓗ OR 3호':<26}{_r9['끝']:>16,.0f}원{_몫9:>8.0f}%"
                  f"{_r9['낙']:>7.1f}%{_r9['산']:>7}  {_판9}")
            # 해마다 — 보류 이유가 「금리 인하기에만」이었다. 해마다 몇 번 켜지나
            print(f"\n     {'해':<8}{'견줌 Ⓗ':>18}{'OR 3호':>18}{'차이':>9}{'3호가 켜진 날':>13}")
            _차9b, _낙9b = [], []
            for _y9b in range(2016, 2027):
                _a = 시뮬(_c(_H), 시작년=str(_y9b), 끝년=str(_y9b))
                _b = 시뮬(_c(_H3호), 시작년=str(_y9b), 끝년=str(_y9b))
                if not _a or not _b:
                    continue
                _n켬 = len({날[x["인"] - 1] for x in 사건
                            if 날[x["인"] - 1][:4] == str(_y9b)
                            and all(_조건P(x, 재, 방) for 재, 방 in _쌍9)})
                _d = (_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0
                _차9b.append(_d)
                _낙9b.append(_b["낙"] - _a["낙"])
                print(f"     {_y9b:<8}{_a['끝']:>17,.0f}원{_b['끝']:>17,.0f}원{_d:>+8.1f}%{_n켬:>13}")
            _글9b, _ = _해마다판정(_차9b, _낙9b)
            print(f"     ⇒ {_글9b}")
            print("     ⚠️ 사용자가 보류한 이유는 **「금리 인하기에만 켜진다」**였다 —")
            print("        「3호가 켜진 날」 칸이 **해마다 0 이 아닌지**를 같이 본다")
    else:
        print("     ⚠️ 기준금리20 · 코스피200선물20 문턱을 못 냈다 — 건너뛴다")
    print("=" * 122)

    # ══ ⭐⭐⭐ **Q-10 ㉢ 문턱 후보 넷을 4관문에** (2026-09-20) ══
    #    Q-1 격자에서 처음으로 「셋 다」가 나왔다. 유상증자 거르개도 여기까지는
    #    좋아 보였다가 해마다 1승 2패로 떨어졌다 — 4관문을 지나야 믿는다
    print("\n" + "=" * 122)
    print("  ── Q-10 ⭐⭐⭐ **㉢ 문턱 후보 넷을 4관문에** ──")
    print("     Q-1 에서 셋 다 지난 넷: (-5,-13) (-5,-16) (-6,-13) (-6,-16)")
    print("     핵심은 **60일을 -10 → -13 으로 조이는 것** — 낙폭이 반토막 나고 20일을 풀 여유가 생긴다")
    print("=" * 122)

    def _H문턱(x, a, b):
        """㉢ 만 (a, b) 로 바꾼 지금 규칙"""
        if R.섹터규칙_큰회사 and 재무통과(x) and 대금통과(x) and 섹터맞나(x):
            return True
        if not 문통과(x):
            return False
        if (R.변동성자사주_켬 and x.get("시장변동성") is not None
                and x["시장변동성"] >= R.시장변동성문턱 and _자사H(x) >= 1):
            return True
        _시a = (x.get("시장낙폭") is not None and x["시장낙폭"] <= a)
        return ((x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱)
                or 섹터맞나(x) or _시a or _시낙(x, 60, b))

    _후보10 = ((-5.0, -13.0), (-5.0, -16.0), (-6.0, -13.0), (-6.0, -16.0))

    # ── A 셋 다 (같은 판에서 다시) ──
    print("\n  ── Q-10a **셋 다** ──")
    _기10 = 시뮬(_c(_H))
    print(f"     {'문턱':<14}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    print(f"     {'(-7,-10) 지금':<14}{_기10['끝']:>16,.0f}원{100:>8.0f}%"
          f"{_기10['낙']:>7.1f}%{_기10['산']:>7}")
    _살아남10 = []
    for _a10, _b10 in _후보10:
        _r = 시뮬(_c(lambda x, a=_a10, b=_b10: _H문턱(x, a, b)))
        if not _r:
            continue
        _ok = (_r["산"] > _기10["산"], _r["끝"] > _기10["끝"], _r["낙"] > 낙폭기준)
        if all(_ok):
            _살아남10.append((_a10, _b10))
        print(f"     {('(%g,%g)' % (_a10, _b10)):<14}{_r['끝']:>16,.0f}원"
              f"{_r['끝'] / _기10['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
              + ("✅ 셋 다" if all(_ok) else "❌"))
    print(f"     ⇒ A 를 지난 것 **{len(_살아남10)}개**")

    # ── B 해마다 ──
    print("\n  ── Q-10b **해마다 승패** (2016~2026) ──")
    _해표10 = {}
    for _a10, _b10 in _살아남10:
        _차10, _낙10 = [], []
        _줄들 = []
        for _y in range(2016, 2027):
            _x1 = 시뮬(_c(_H), 시작년=str(_y), 끝년=str(_y))
            _x2 = 시뮬(_c(lambda x, a=_a10, b=_b10: _H문턱(x, a, b)),
                       시작년=str(_y), 끝년=str(_y))
            if not _x1 or not _x2:
                continue
            _d = (_x2["끝"] / _x1["끝"] - 1) * 100 if _x1["끝"] > 0 else 0
            _차10.append(_d)
            _낙10.append(_x2["낙"] - _x1["낙"])
            _줄들.append((_y, _x1["끝"], _x2["끝"], _d, _x1["낙"], _x2["낙"]))
        _해표10[(_a10, _b10)] = _해마다판정(_차10, _낙10)
        print(f"\n     [{_a10:g}, {_b10:g}]  {'해':<6}{'견줌':>16}{'도전':>16}{'차이':>9}{'견줌 낙':>9}{'도전 낙':>9}")
        for _y, _e1, _e2, _d, _l1, _l2 in _줄들:
            print(f"              {_y:<6}{_e1:>15,.0f}원{_e2:>15,.0f}원{_d:>+8.1f}%{_l1:>8.1f}%{_l2:>8.1f}%")
        print(f"              ⇒ {_해표10[(_a10, _b10)][0]}")

    # ── C 걷기 앞뒤 (제약 있는 칸) ──
    print("\n  ── Q-10c **걷기 앞뒤** (제약 있는 칸) ──")
    print(f"     {'문턱':<14}{'구간':<14}{'견줌':>16}{'도전':>16}{'차이':>9}{'견줌 낙':>9}{'도전 낙':>9}")
    _걷기10 = {}
    for _a10, _b10 in _살아남10:
        print(f"     [{_a10:g}, {_b10:g}]")
        _걷기10[(_a10, _b10)] = _걷기찍기(
            _걷기(lambda x, a=_a10, b=_b10: _H문턱(x, a, b)), 들여="        ")
    print("     ⚠️ **앞뒤가 둘 다 +** 여야 믿는다 — 한쪽만 좋으면 우연이다")

    # ── 판정 모음 ──
    print("\n  ── Q-10 **판정 모음** ──")
    print(f"     {'문턱':<14}{'A 셋 다':>9}{'B 해마다':>12}{'C 걷기':>9}   최종")
    for _a10, _b10 in _후보10:
        if (_a10, _b10) not in _해표10:
            print(f"     {('(%g,%g)' % (_a10, _b10)):<14}{'❌':>9}{'—':>12}{'—':>9}   **탈락** (A 에서)")
            continue
        _글B10, _좋B10 = _해표10[(_a10, _b10)]
        # ⭐ **「못 가른다」(⬜)는 기각이 아니다** (2026-09-20). t ≤ −2 일 때만 ❌
        _bok = (_좋B10 is not False)
        _cok = _걷기10.get((_a10, _b10), False)
        _다 = _bok and _cok
        print(f"     {('(%g,%g)' % (_a10, _b10)):<14}{'✅':>9}"
              f"{('✅' if _좋B10 else ('❌' if _좋B10 is False else '⬜')):>12}"
              f"{('✅' if _cok else '❌'):>9}   "
              + ("⭐ **지났다 — 반영 후보**" if _다 else "**탈락**"))
        print(f"          해마다: {_글B10}")
    print("     ⚠️ 통과해도 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
    print("=" * 122)

    # ══ ⭐⭐⭐ **Q-11 이길 확률로 통과한 것들을 돈으로** (2026-09-21) ══
    #    전수조사 첫 결론이 「판정 장치가 두 벌」이었다.
    #    옛 4관문(A·B·C)은 **이길 확률**로만 판정하는데, 잣대를 고치니
    #    거기서 t ≥ +2 인 후보가 여럿 나왔다. **돈으로는 한 번도 안 쟀다.**
    print("\n" + "=" * 122)
    print("  ── Q-11 ⭐⭐⭐ **이길 확률로 통과한 것들을 돈으로** ──")
    print("     옛 4관문(A·B·C)은 이길 확률로 판정한다. 돈은 딴 이야기일 수 있다")
    print("     ⚠️ AND 짜리는 사는 것이 준다 — 사용자 1순위와 어긋나면 「산 것↑」에서 갈린다")
    print("=" * 122)

    def _지평Q(x, w, 문):
        return _지평(x, w, 문)

    _볼Q11 = [
        ("Ⓒ OR 지수가 60일선 -8%↓", lambda x: _H(x) or (문통과(x) and _지평Q(x, 60, -8))),
        ("Ⓔ OR 지수가 20일선 -8%↓", lambda x: _H(x) or (문통과(x) and _지평Q(x, 20, -8))),
        ("Ⓘ OR (시낙7 AND 120일선 -8%↓)",
         lambda x: _H(x) or (문통과(x) and _시7(x) and _지평Q(x, 120, -8))),
        ("⑨ AND 20일-10% 와 60일-20%",
         lambda x: _H(x) and x["낙폭20"] <= -10
         and x.get("낙폭60") is not None and x["낙폭60"] <= -20),
        ("⑧ 낙폭 창 20일 -> 60일",
         lambda x: (_H(x) and x.get("낙폭60") is not None and x["낙폭60"] <= -20)),
    ]
    _기11 = 시뮬(_c(_H))
    print(f"\n     {'설정':<30}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    print(f"     {'Ⓗ (지금 · 견줌)':<30}{_기11['끝']:>16,.0f}원{100:>8.0f}%"
          f"{_기11['낙']:>7.1f}%{_기11['산']:>7}")
    _산것11 = []
    for _라11, _fn11 in _볼Q11:
        _r = 시뮬(_c(_fn11))
        if not _r:
            print(f"     {_라11:<30}{'— 못 쟀다':>17}")
            continue
        _ok = (_r["산"] > _기11["산"], _r["끝"] > _기11["끝"], _r["낙"] > 낙폭기준)
        if all(_ok):
            _산것11.append((_라11, _fn11))
        print(f"     {_라11:<30}{_r['끝']:>16,.0f}원"
              f"{_r['끝'] / _기11['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
              + ("✅ 셋 다" if all(_ok) else
                 "❌ " + " ".join(z for z, o in zip(("산것↓", "돈↓", "낙폭>10"), _ok) if not o)))
    print(f"     ⇒ 돈으로도 셋 다인 것 **{len(_산것11)}개**")

    # 살아남은 것만 해마다 + 걷기 (새 잣대)
    for _라11, _fn11 in _산것11:
        print(f"\n     ── [{_라11}] 해마다 + 걷기 ──")
        _차11, _낙11 = [], []
        for _y11 in range(2016, 2027):
            _a = 시뮬(_c(_H), 시작년=str(_y11), 끝년=str(_y11))
            _b = 시뮬(_c(_fn11), 시작년=str(_y11), 끝년=str(_y11))
            if not _a or not _b:
                continue
            _차11.append((_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0)
            _낙11.append(_b["낙"] - _a["낙"])
        print("        해마다: " + _해마다판정(_차11, _낙11)[0])
        _걷기찍기(_걷기(_fn11))
    if not _산것11:
        print("     ⇒ **이길 확률로 통과한 것이 돈으로는 하나도 안 남았다** — "
              "[[avg-return-is-not-money]] 가 또 맞았다")
    print("=" * 122)

    # ══ ⚠️⚠️ **뺀 절 셋 — Q-12 · Q-14 · Q-16** (2026-09-21) ══
    #    셋 다 **소형 규칙에 대형을 끼워 넣기**였다. 사용자가 여러 번 지적했다:
    #        「규모에 따라 제발 규칙 좀 따로 테스트하고 찾아보라고 몇번 말했는데」
    #    check_lab_ready 의 ④ 막개가 Q-12 를 잡아 냈다.
    #
    #    결과(지워도 되게 여기 남긴다):
    #        Q-12 섹터 낙폭 문턱 무르게  후보 591 → 1,451 (2.5배) 인데 **산 것 0**
    #        Q-14 하루 자리 떼어 줌      다섯 줄 전부 **2천억↑ 산 것 0**
    #        Q-16 상대갭 문턱 무르게      돌리다 멈췄다 (같은 부류라)
    #    ⇒ 소형 규칙을 늘려서는 대형이 안 들어온다. **Q-19 가 띠 규칙을 따로 만든다**
    #    코드는 뺐다 — 두면 또 돌린다



    # ══ ⭐⭐⭐ **Q-15 ㉥ 과 ㉢ 문턱을 같이 켜면** (2026-09-21) ══
    #    걷기를 고친 뒤 둘 다 4관문을 지났는데 **따로** 잰 값이다.
    #    둘이 같은 곳을 건드린다 — ㉥ 은 빠진 날에 더 사고, ㉢ 조이기는 빠진 날을 좁힌다.
    #    [[dont-add-conditions]] 조건을 더하면 자본 시뮬에서 네 번 다 졌다. 그래서 잰다
    print("\n" + "=" * 122)
    print("  ── Q-15 ⭐⭐⭐ **㉥ 과 ㉢ 문턱을 같이 켜면** ──")
    print("     ㉥ 은 「빠진 날에 더 산다」 · ㉢ 조이기는 「빠진 날을 좁힌다」 — 상쇄할 수 있다")
    print("     ④⑤ 가 ① 보다 나아야 같이 켤 뜻이 있다")
    print("=" * 122)

    def _빠진장Q15(골):
        for z in 골:
            v = z.get("시장낙폭")
            if v is not None:
                return v <= R.빠지는장문턱
        return False

    _더사기옵 = dict(하루상한=(lambda 골: R.빠지는장최대종목 if _빠진장Q15(골)
                           else R.평소최대종목))
    _볼Q15 = [
        ("① ㉥ 만 (지금 실전)", _H, _더사기옵),
        ("② ㉢ (-5,-13) 만", (lambda x: _H문턱(x, -5.0, -13.0)), {}),
        ("③ ㉢ (-6,-13) 만", (lambda x: _H문턱(x, -6.0, -13.0)), {}),
        ("④ ㉥ + ㉢ (-5,-13)", (lambda x: _H문턱(x, -5.0, -13.0)), _더사기옵),
        ("⑤ ㉥ + ㉢ (-6,-13)", (lambda x: _H문턱(x, -6.0, -13.0)), _더사기옵),
    ]
    # ⚠️ 견줌은 **㉥ 도 ㉢ 도 없던 옛 규칙**이다 — 하루 상한을 4로 고정한다
    _기15 = 시뮬(_c(_H, 하루상한=4))
    print(f"\n     {'설정':<24}{'끝 자산':>17}{'옛것의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    print(f"     {'옛 규칙 (하루 4 · 견줌)':<24}{_기15['끝']:>16,.0f}원{100:>8.0f}%"
          f"{_기15['낙']:>7.1f}%{_기15['산']:>7}")
    _잰15 = {}
    for _라15, _거15, _옵15 in _볼Q15:
        _r = 시뮬(_c(_거15, **_옵15))
        if not _r:
            continue
        _잰15[_라15] = (_r, _거15, _옵15)
        _ok = (_r["산"] > _기15["산"], _r["끝"] > _기15["끝"], _r["낙"] > 낙폭기준)
        print(f"     {_라15:<24}{_r['끝']:>16,.0f}원"
              f"{_r['끝'] / _기15['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
              + ("✅ 셋 다" if all(_ok) else "❌"))

    # ⭐ 같이 켠 것이 **㉥ 만** 보다 나은가 — 이게 이 절의 물음이다
    _기더사기 = (_잰15.get("① ㉥ 만 (지금 실전)") or [None])[0]
    if _기더사기:
        print(f"\n     ── **㉥ 만** 과 견주면 (① 을 100 으로) ──")
        for _라15 in ("④ ㉥ + ㉢ (-5,-13)", "⑤ ㉥ + ㉢ (-6,-13)"):
            _v = _잰15.get(_라15)
            if not _v:
                continue
            _r = _v[0]
            print(f"     {_라15:<24}돈 {_r['끝'] / _기더사기['끝'] * 100:>5.0f}%"
                  f" · 낙폭 {_기더사기['낙']:.1f}% → {_r['낙']:.1f}%"
                  f" · 산 것 {_기더사기['산']} → {_r['산']}"
                  + ("   ⭐ 더 낫다" if (_r["끝"] > _기더사기["끝"] and _r["산"] >= _기더사기["산"])
                     else "   — 나을 게 없다"))

    # 살아남은 조합만 해마다 + 걷기
    for _라15, (_r, _거15, _옵15) in _잰15.items():
        if not _라15.startswith(("④", "⑤")):
            continue
        _ok = (_r["산"] > _기15["산"], _r["끝"] > _기15["끝"], _r["낙"] > 낙폭기준)
        if not all(_ok):
            continue
        print(f"\n     ── [{_라15}] 해마다 + 걷기 ──")
        _차15, _낙15 = [], []
        for _y15 in range(2016, 2027):
            _a = 시뮬(_c(_H, 하루상한=4), 시작년=str(_y15), 끝년=str(_y15))
            _b = 시뮬(_c(_거15, **_옵15), 시작년=str(_y15), 끝년=str(_y15))
            if not _a or not _b:
                continue
            _차15.append((_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0)
            _낙15.append(_b["낙"] - _a["낙"])
        print("        해마다: " + _해마다판정(_차15, _낙15)[0])
        _줄15, _시드a15, _시드b15 = [], None, None
        for _라W, _시W, _끝W in (("앞 2010~2020", "2010", "2020"),
                                  ("뒤 2021~2026", "2021", "2026")):
            _y1 = 시뮬(_c(_H, 하루상한=4), 시작년=_시W, 끝년=_끝W, 시드=_시드a15)
            _y2 = 시뮬(_c(_거15, **_옵15), 시작년=_시W, 끝년=_끝W, 시드=_시드b15)
            if not _y1 or not _y2:
                continue
            _줄15.append((_라W, _y1, _y2,
                          (_y2["끝"] / _y1["끝"] - 1) * 100 if _y1["끝"] > 0 else 0))
            _시드a15, _시드b15 = _y1["끝"], _y2["끝"]
        _걷기찍기(_줄15)
    print("     ⚠️ 같이 켠 것이 ㉥ 만 보다 **안 나으면 ㉢ 문턱은 안 넣는다** — 단순한 쪽이 낫다")
    print("=" * 122)



    # ⭐ ONLY=Q19 면 여기까지 오는 길에 옛 절들이 이미 건너뛰어졌다 (아래 _끝내기 참고)
    # ══ ⭐⭐⭐ **Q-19 중형·대형·초대형 규칙을 따로 만든다** (2026-09-21) ══
    #    사용자: 「새로운 규칙 찾으라고 몇번 말했어」 「자꾸 왜 중형주는 빼는거야!」
    #    ⚠️ 이 절은 **소형 규칙(_H)을 아예 안 부른다.** a·b 는 띠 규칙 혼자다.
    #       c·d 만 [견줌] 으로 소형을 나란히 놓는다 (반영을 정하려면 필요하다)
    print("\n" + "=" * 122)
    print("  ── Q-19 ⭐⭐⭐ **중형·대형·초대형 규칙을 따로** ──")
    print("     a·b 는 **소형 규칙을 한 번도 안 부른다** — 띠 전용 규칙 혼자 선다")
    print("     재료·문턱·상대갭 **전부 그 띠 분포**에서 낸다. 소형 값을 안 쓴다")
    print("=" * 122)

    # ⭐ **다섯 띠 전부** (2026-09-21 · 사용자 「소형주는 소형주대로 테스트해야 하는거 아니야?」)
    #    소형도 예외가 아니다 — 지금 규칙이 300~2,000억 에서 나왔지만
    #    **그 띠 자료로 처음부터 만든 적은 없다.** 그래야 지금 규칙이 최선인지 안다
    _띠19 = (("초소형 ~300억", 0, 300),
             ("소형 300~2,000억", 300, 2000),
             ("중형 2,000억~1조", 2000, 10000),
             ("대형 1조~10조", 10000, 100000),
             ("초대형 10조↑", 100000, 9e12))

    def _선물19(x):
        return _선물20.get(x["인"] - 1)

    def _금리차19(x):
        return _때(x, "미국금리차", 20)

    # ⭐ 재료를 **넓게 깐다** — 띠마다 그 띠에서 센 것이 뽑히게. 내가 안 고른다.
    #    CJUDGE 가 띠별로 잰 상위를 보면 소형과 대형이 딴판이다:
    #      소형 ~300억      신고가60↓ · 자사주60↑ · 감자60↓
    #      소형 300~2,000억 감자60↓ · 신고가60↓ · 시장낙폭↓
    #      중·대형          시장낙폭↓ · 선물20↓ · 미국금리차20↑
    _재19 = (("시장낙폭", lambda x: x.get("시장낙폭"), "아래"),
             ("선물20", _선물19, "아래"),
             ("미국금리차20", _금리차19, "위"),
             ("낙폭20", lambda x: x.get("낙폭20"), "아래"),
             ("볼린저", lambda x: x.get("볼린저"), "아래"),
             ("낙폭60", lambda x: x.get("낙폭60"), "아래"),
             ("상대강도", lambda x: x.get("상대강도"), "아래"),
             ("섹터대비", lambda x: x.get("섹터대비"), "아래"))

    # ══ ⭐⭐⭐ **Q-22 후보 둘을 견주고 같이 켜 본다** (2026-09-22) ══
    #    B3  Ⓗ OR 회전율 위20%·선물20     286,674,396원 113% · -11.7% · 341  걷기 ✅
    #    B4  Ⓗ OR 금속·선물20+시장낙폭      266,907,317원 106% · -10.6% · 324  걷기 ✅
    #    ⚠️ [[compare-candidates-before-adopting]] — 9/21 에 ㉥ 을 먼저 반영했다가
    #       ㉦ 과 같이 켜니 ㉥ 이 아무 일도 안 해서 되돌렸다. **먼저 견준다.**
    #    ⚠️ [[or-adds-money-only-on-empty-days]] — B3·B4 표의 여러 줄이
    #       252,821,671원·-11.0%·319 로 바탕과 한 글자도 안 달랐다.
    #       하루 3자리에 막혀 더한 것이 하나도 안 들어간 것이다.
    #       둘 다 「선물20이 빠진 날」을 쓴다 — **같은 빈 날을 놓고 다툰다**
    if _ONLY in ("", "Q22"):
        print("\n" + "=" * 122)
        print("  ── Q-22 ⭐⭐⭐ **후보 둘을 견주고 같이 켜 본다** ──")
        print("     ③ 이 ①·② 보다 나아야 **둘 다** 넣을 뜻이 있다")
        print("     ③ 이 ① 과 같은 값이면 금속이 무력한 것이다 (그 반대도)")
        print("     ⚠️ ①·② 가 B3·B4 숫자로 안 나오면 **정의를 잘못 베낀 것** — 결론 안 낸다")
        print("=" * 122)

        # ── 후보 하나: 회전율 위20% · 선물20 (Q-21a·Q-21b 와 똑같이 낸다) ──
        _회값22 = sorted(z for z in (x.get("회전율") for x in 사건) if z is not None)
        _회위22 = _회값22[len(_회값22) * 4 // 5]

        def _회든22(x):
            _z = x.get("회전율")
            return _z is not None and _z >= _회위22

        _회칸22 = [x for x in 사건 if _회든22(x) and x.get("_20") is not None]
        _선값22 = sorted(z for z in (_선물19(x) for x in _회칸22) if z is not None)
        _회선문22 = _선값22[len(_선값22) // 5] if _선값22 else None

        # ── 후보 둘: 금속 · 선물20 + 시장낙폭 (Q-20a 와 똑같이 낸다) ──
        _금칸22 = [x for x in 사건
                   if x.get("섹터") == "금속" and x.get("_20") is not None]
        _a22 = sorted(z for z in (_선물19(x) for x in _금칸22) if z is not None)
        _b22 = sorted(z for z in (x.get("시장낙폭") for x in _금칸22) if z is not None)
        _금선문22 = _a22[len(_a22) // 5] if _a22 else None
        _금시문22 = _b22[len(_b22) // 5] if _b22 else None

        print(f"\n     회전율 위20% ≥ {_회위22:,.2f}  칸 {len(_회칸22):,}건"
              f"  ·  선물20 문턱 {_회선문22}")
        print(f"     금속 칸 {len(_금칸22):,}건"
              f"  ·  선물20 문턱 {_금선문22}  ·  시장낙폭 문턱 {_금시문22}")

        def _회전규칙22(x):
            if _회선문22 is None or not _회든22(x):
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            _f = _선물19(x)
            return _f is not None and _f <= _회선문22

        def _금속규칙22(x):
            if _금선문22 is None or _금시문22 is None:
                return False
            if x.get("섹터") != "금속":
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            _f = _선물19(x)
            _m = x.get("시장낙폭")
            return (_f is not None and _f <= _금선문22
                    and _m is not None and _m <= _금시문22)

        # ── 겹침을 직접 센다 ──
        _n회22 = sum(1 for x in 사건 if _회전규칙22(x))
        _n금22 = sum(1 for x in 사건 if _금속규칙22(x))
        _n겹22 = sum(1 for x in 사건 if _회전규칙22(x) and _금속규칙22(x))
        print(f"\n     겹침 — 회전율 {_n회22:,}건 · 금속 {_n금22:,}건"
              f" · **둘 다 걸리는 것 {_n겹22:,}건**")
        if _n금22:
            print(f"        금속의 {_n겹22 / _n금22 * 100:.0f}% 가 회전율에도 걸린다")
        # 같은 **날**을 가리키나 (자리를 다투는 건 종목이 아니라 날이다)
        _날회22 = {x["인"] for x in 사건 if _회전규칙22(x)}
        _날금22 = {x["인"] for x in 사건 if _금속규칙22(x)}
        if _날금22:
            print(f"        날로 보면 — 회전율 {len(_날회22):,}날 · 금속 {len(_날금22):,}날"
                  f" · 겹치는 날 {len(_날회22 & _날금22):,}"
                  f" ({len(_날회22 & _날금22) / len(_날금22) * 100:.0f}%)")

        _기22 = 시뮬(_c(_H))      # [견줌] 표에만 쓴다
        _볼22 = [
            ("① Ⓗ OR 회전율", (lambda x: _H(x) or _회전규칙22(x)), 286674396),   # [견줌]
            ("② Ⓗ OR 금속", (lambda x: _H(x) or _금속규칙22(x)), 266907317),    # [견줌]
            ("③ Ⓗ OR 둘 다",
             (lambda x: _H(x) or _회전규칙22(x) or _금속규칙22(x)), None),        # [견줌]
        ]
        print(f"\n     {'설정':<22}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        print(f"     {'Ⓗ (지금 · 견줌)':<22}{_기22['끝']:>16,.0f}원{100:>8.0f}%"
              f"{_기22['낙']:>7.1f}%{_기22['산']:>7}")
        _잰22 = {}
        _재현22 = True
        for _라22, _fn22, _바랄22 in _볼22:
            _r22 = 시뮬(_c(_fn22))
            if not _r22:
                continue
            _잰22[_라22] = (_r22, _fn22)
            _ok22 = (_r22["산"] > _기22["산"], _r22["끝"] > _기22["끝"],
                     _r22["낙"] > 낙폭기준)
            _꼬22 = ""
            if _바랄22 is not None:
                if abs(_r22["끝"] - _바랄22) < 1000:
                    _꼬22 = "  · 재현 ✅"
                else:
                    _꼬22 = f"  · ⚠️ 재현 실패 (바란 값 {_바랄22:,})"
                    _재현22 = False
            print(f"     {_라22:<22}{_r22['끝']:>16,.0f}원"
                  f"{_r22['끝'] / _기22['끝'] * 100:>8.0f}%{_r22['낙']:>7.1f}%{_r22['산']:>7}  "
                  + ("✅ 셋 다" if all(_ok22) else "❌") + _꼬22)

        # ── ③ 이 하나씩보다 나은가 ──
        _r1_22 = (_잰22.get("① Ⓗ OR 회전율") or (None,))[0]
        _r2_22 = (_잰22.get("② Ⓗ OR 금속") or (None,))[0]
        _r3_22 = (_잰22.get("③ Ⓗ OR 둘 다") or (None,))[0]
        if _r1_22 and _r2_22 and _r3_22:
            print("\n     ── **③ 이 하나씩보다 나은가** ──")
            for _라x22, _rx22, _딴22 in (("① 회전율", _r1_22, "금속"),
                                          ("② 금속", _r2_22, "회전율")):
                print(f"     ③ 둘 다 vs {_라x22:<10}"
                      f"돈 {_r3_22['끝'] / _rx22['끝'] * 100:>6.1f}%"
                      f" · 산 것 {_rx22['산']} → {_r3_22['산']}"
                      + ("   ⚠️ **한 글자도 안 다르다** — "
                         f"{_딴22} 가 무력하다 (하루 자리에 막혔다)"
                         if abs(_r3_22["끝"] - _rx22["끝"]) < 1000
                         else ("   ⭐ 더 낫다" if _r3_22["끝"] > _rx22["끝"]
                               else "   — 나을 게 없다")))

        # ── 셋 다를 넘은 것만 해마다 + 걷기 ──
        for _라22, (_r22, _fn22) in _잰22.items():
            if not (_r22["산"] > _기22["산"] and _r22["끝"] > _기22["끝"]
                    and _r22["낙"] > 낙폭기준):
                continue
            print(f"\n     ── [{_라22}] 해마다 + 걷기 ──")
            _차22, _낙22 = [], []
            for _y22 in range(2016, 2027):
                _ay22 = 시뮬(_c(_H), 시작년=str(_y22), 끝년=str(_y22))
                _by22 = 시뮬(_c(_fn22), 시작년=str(_y22), 끝년=str(_y22))
                if not _ay22 or not _by22:
                    continue
                _차22.append((_by22["끝"] / _ay22["끝"] - 1) * 100
                             if _ay22["끝"] > 0 else 0)
                _낙22.append(_by22["낙"] - _ay22["낙"])
            print("        해마다: " + _해마다판정(_차22, _낙22)[0])
            _걷기찍기(_걷기(_fn22))

        if not _재현22:
            print("\n     ⚠️⚠️ **재현이 안 됐다 — 이 절의 결론을 쓰지 마라.**")
            print("        B3·B4 와 정의가 다르게 베껴진 것이다")
        print("\n     ⚠️ 통과해도 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

    # ⭐ ONLY=Q22 면 Q-19 본체(20분)를 안 돈다
    if _ONLY == "Q22":
        print("\n  ⭐ ONLY=Q22 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-23 OR 을 전수로 잰다** (2026-09-22) ══
    #    Q-22 가 구멍을 드러냈다: B3·B4 는 칸 규칙을 44개 만들어 놓고
    #    **「혼자 돌렸을 때 돈이 많은 다섯」만** OR 로 쟀다. 39개는 잰 적이 없다.
    #    혼자 잘 하는 것과 OR 로 보탬이 되는 것은 **다른 물음**이다 —
    #    OR 은 「기존이 안 사던 빈 날」을 채울 때만 돈이 는다
    #    [[or-adds-money-only-on-empty-days]]. 혼자 성적과 상관이 없다.
    #    ⇒ 44개 전부 OR 로 잰다. 지금 후보(286,674,396원)를 넘는 게 또 있나
    if _ONLY in ("", "Q23"):
        print("\n" + "=" * 122)
        print("  ── Q-23 ⭐⭐⭐ **OR 을 전수로 잰다** (위 다섯만 보던 것을 전부) ──")
        print("     혼자 잘 하는 것 ≠ OR 로 보탬이 되는 것")
        print("     B3·B4 는 44개 중 **다섯만** OR 로 쟀다 — 39개는 잰 적이 없다")
        print("=" * 122)

        # ── 잴 칸을 모은다: 업종 + 오분위 칸 ──
        _칸23 = []      # (칸이름, 그 칸에 드는 함수)
        _섹셈23 = {}
        for x in 사건:
            _n23 = x.get("섹터")
            if _n23:
                _섹셈23[_n23] = _섹셈23.get(_n23, 0) + 1
        for _섹23 in [k for k, v in sorted(_섹셈23.items(), key=lambda t: -t[1])
                      if v >= 20000][:14]:
            _칸23.append((f"업종 {_섹23[:12]}",
                          (lambda x, a=_섹23: x.get("섹터") == a)))
        for _라잣23, _꺼잣23 in (("거래 두께", lambda x: x.get("대금억")),
                                 ("변동성", lambda x: x.get("섹시그마")),
                                 ("주가", lambda x: x.get("원시")),
                                 ("회전율", lambda x: x.get("회전율")),
                                 ("외국인 지분율", lambda x: x.get("지분율"))):
            _v23 = sorted(z for z in (_꺼잣23(x) for x in 사건) if z is not None)
            if len(_v23) < len(사건) * 0.3:
                continue
            _아23 = _v23[len(_v23) // 5]
            _위23 = _v23[len(_v23) * 4 // 5]
            _칸23.append((f"{_라잣23} 아래20%",
                          (lambda x, f=_꺼잣23, c=_아23: f(x) is not None and f(x) <= c)))
            _칸23.append((f"{_라잣23} 위20%",
                          (lambda x, f=_꺼잣23, c=_위23: f(x) is not None and f(x) >= c)))
        print(f"\n     잴 칸 {len(_칸23)}개 (업종 + 오분위)")

        # ── 칸마다 문턱과 센 재료 둘 (B3·B4 와 똑같은 잣대) ──
        _문23, _고른23 = {}, {}
        for _라칸23, _든23 in _칸23:
            _칸속23 = [x for x in 사건 if _든23(x) and x.get("_20") is not None]
            if len(_칸속23) < 20000:
                continue
            _바23 = sum(1 for x in _칸속23 if x["_20"] > 0) / len(_칸속23) * 100
            for _이23, _꺼23, _방23 in _재19:
                _w23 = sorted(z for z in (_꺼23(x) for x in _칸속23) if z is not None)
                if len(_w23) < len(_칸속23) * 0.25:
                    continue
                _문23[(_라칸23, _이23)] = (_w23[len(_w23) // 5] if _방23 == "아래"
                                           else _w23[len(_w23) * 4 // 5])
            _좋23 = []
            for _이23, _꺼23, _방23 in _재19:
                _컷23 = _문23.get((_라칸23, _이23))
                if _컷23 is None:
                    continue
                _z23 = [x for x in _칸속23 if (_꺼23(x) is not None)
                        and ((_꺼23(x) <= _컷23) if _방23 == "아래"
                             else (_꺼23(x) >= _컷23))]
                if len(_z23) < 300:
                    continue
                _이길23 = sum(1 for x in _z23 if x["_20"] > 0) / len(_z23) * 100
                _앞23 = [x for x in _z23 if 날[x["인"] - 1][:4] <= "2018"]
                _뒤23 = [x for x in _z23 if 날[x["인"] - 1][:4] > "2018"]
                if len(_앞23) < 100 or len(_뒤23) < 100:
                    continue
                _이앞23 = sum(1 for x in _앞23 if x["_20"] > 0) / len(_앞23) * 100
                _이뒤23 = sum(1 for x in _뒤23 if x["_20"] > 0) / len(_뒤23) * 100
                if (_이길23 - _바23) < 2.0 or (_이앞23 - _바23) * (_이뒤23 - _바23) <= 0:
                    continue
                _좋23.append((_이길23 - _바23, _이23))
            _좋23.sort(reverse=True)
            _고른23[_라칸23] = [z[1] for z in _좋23[:2]]

        def _칸규칙23(x, 라칸, 든, 쓸것):
            if not 든(x):
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            for _이23, _꺼23, _방23 in _재19:
                if _이23 not in 쓸것:
                    continue
                _컷23 = _문23.get((라칸, _이23))
                if _컷23 is None:
                    return False
                _v = _꺼23(x)
                if _v is None:
                    return False
                if (_v > _컷23) if _방23 == "아래" else (_v < _컷23):
                    return False
            return True

        # ── 전부 OR 로 잰다 ──
        _기23 = 시뮬(_c(_H))     # [견줌] 표에만 쓴다
        _이미23 = 286674396      # 지금 채택 후보 (Ⓗ OR 회전율 위20%·선물20)
        print(f"\n     {'설정':<36}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        print(f"     {'Ⓗ (지금 · 견줌)':<36}{_기23['끝']:>16,.0f}원{100:>8.0f}%"
              f"{_기23['낙']:>7.1f}%{_기23['산']:>7}")
        _잰23 = []
        for _라칸23, _든23 in _칸23:
            _뽑23 = _고른23.get(_라칸23) or []
            if not _뽑23:
                continue
            for _쓸23 in ([(_뽑23[0],)]
                          + ([(_뽑23[0], _뽑23[1])] if len(_뽑23) >= 2 else [])):
                _fn23 = (lambda x, a=_라칸23, b=_든23, c=_쓸23:
                         _칸규칙23(x, a, b, c))
                _합23 = (lambda x, f=_fn23: _H(x) or f(x))       # [견줌] 지금 OR 칸
                _r23 = 시뮬(_c(_합23))
                if not _r23:
                    continue
                _잰23.append((f"{_라칸23} · {'+'.join(_쓸23)}", _r23, _합23))
        _잰23.sort(key=lambda t: -t[1]["끝"])
        _넘은23 = []
        for _표23, _r23, _합23 in _잰23:
            _ok23 = (_r23["산"] > _기23["산"], _r23["끝"] > _기23["끝"],
                     _r23["낙"] > 낙폭기준)
            _꼬23 = ("✅ 셋 다" if all(_ok23) else "❌")
            if abs(_r23["끝"] - _기23["끝"]) < 1000:
                _꼬23 += "  · 바탕과 똑같다 (자리에 막혔다)"
            elif all(_ok23) and _r23["끝"] > _이미23 + 1000:
                _꼬23 += "  · ⭐ **지금 후보보다 낫다**"
                _넘은23.append((_표23, _합23))
            print(f"     {('Ⓗ OR ' + _표23):<36}{_r23['끝']:>16,.0f}원"
                  f"{_r23['끝'] / _기23['끝'] * 100:>8.0f}%{_r23['낙']:>7.1f}%"
                  f"{_r23['산']:>7}  " + _꼬23)

        print(f"\n     ⇒ {len(_잰23)}개를 OR 로 쟀다 · 지금 후보를 넘은 것 {len(_넘은23)}개")
        for _표23, _합23 in _넘은23[:6]:
            print(f"\n     ── [{_표23}] 해마다 + 걷기 ──")
            _차23, _낙23 = [], []
            for _y23 in range(2016, 2027):
                _ay23 = 시뮬(_c(_H), 시작년=str(_y23), 끝년=str(_y23))
                _by23 = 시뮬(_c(_합23), 시작년=str(_y23), 끝년=str(_y23))
                if not _ay23 or not _by23:
                    continue
                _차23.append((_by23["끝"] / _ay23["끝"] - 1) * 100
                             if _ay23["끝"] > 0 else 0)
                _낙23.append(_by23["낙"] - _ay23["낙"])
            print("        해마다: " + _해마다판정(_차23, _낙23)[0])
            _걷기찍기(_걷기(_합23))
        if not _넘은23:
            print("\n     ⇒ 전수로 봐도 **지금 후보(회전율 위20%·선물20)가 제일 낫다**")
        print("     ⚠️ 반영은 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

    if _ONLY == "Q23":
        print("\n  ⭐ ONLY=Q23 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-24 전수에서 나온 통과 후보들을 끝까지 몬다** (2026-09-22) ══
    #    Q-23 이 43개를 OR 로 재니 셋 다를 넘은 것이 8개였고,
    #    그중 **다섯은 B3·B4 가 OR 로 재본 적이 없는 것**이었다.
    #    아직 안 한 것 둘:
    #      ① 걷기를 안 쟀다 — Q-23 은 1등을 넘은 것만 돌렸고 그게 0개였다
    #         (주가 아래20% 는 셋 다 ✅ 인데 걷기 앞이 -0.4% 였다 — 걷기가 거른다)
    #      ② 1등과 같이 켜면 어떻게 되나 — Q-22 에서 금속은 날 겹침 95% 로 흡수됐다.
    #         금융·거래두께·유통·의료는 **다른 종목군**이라 다를 수 있다
    #    ⚠️ 1등을 하드코딩하지 않는다 — 그때 그때 돈으로 고른다
    if _ONLY in ("", "Q24"):
        print("\n" + "=" * 122)
        print("  ── Q-24 ⭐⭐⭐ **전수에서 나온 통과 후보들을 끝까지 몬다** ──")
        print("     1 셋 다 넘은 것 전부 → 해마다 + 걷기")
        print("     2 걷기까지 넘은 것을 1등과 **날 겹침**으로 견준다")
        print("     3 1등 + 하나씩 · 1등 + 전부  → 나으면 해마다 + 걷기")
        print("=" * 122)

        # ── 칸 모으기 (Q-23 과 똑같다) ──
        _칸24 = []
        _섹셈24 = {}
        for x in 사건:
            _n24 = x.get("섹터")
            if _n24:
                _섹셈24[_n24] = _섹셈24.get(_n24, 0) + 1
        for _섹24 in [k for k, v in sorted(_섹셈24.items(), key=lambda t: -t[1])
                      if v >= 20000][:14]:
            _칸24.append((f"업종 {_섹24[:12]}",
                          (lambda x, a=_섹24: x.get("섹터") == a)))
        for _라잣24, _꺼잣24 in (("거래 두께", lambda x: x.get("대금억")),
                                 ("변동성", lambda x: x.get("섹시그마")),
                                 ("주가", lambda x: x.get("원시")),
                                 ("회전율", lambda x: x.get("회전율")),
                                 ("외국인 지분율", lambda x: x.get("지분율"))):
            _v24 = sorted(z for z in (_꺼잣24(x) for x in 사건) if z is not None)
            if len(_v24) < len(사건) * 0.3:
                continue
            _아24 = _v24[len(_v24) // 5]
            _위24 = _v24[len(_v24) * 4 // 5]
            _칸24.append((f"{_라잣24} 아래20%",
                          (lambda x, f=_꺼잣24, c=_아24: f(x) is not None and f(x) <= c)))
            _칸24.append((f"{_라잣24} 위20%",
                          (lambda x, f=_꺼잣24, c=_위24: f(x) is not None and f(x) >= c)))

        _문24, _고른24 = {}, {}
        for _라칸24, _든24 in _칸24:
            _속24 = [x for x in 사건 if _든24(x) and x.get("_20") is not None]
            if len(_속24) < 20000:
                continue
            _바24 = sum(1 for x in _속24 if x["_20"] > 0) / len(_속24) * 100
            for _이24, _꺼24, _방24 in _재19:
                _w24 = sorted(z for z in (_꺼24(x) for x in _속24) if z is not None)
                if len(_w24) < len(_속24) * 0.25:
                    continue
                _문24[(_라칸24, _이24)] = (_w24[len(_w24) // 5] if _방24 == "아래"
                                           else _w24[len(_w24) * 4 // 5])
            _좋24 = []
            for _이24, _꺼24, _방24 in _재19:
                _컷24 = _문24.get((_라칸24, _이24))
                if _컷24 is None:
                    continue
                _z24 = [x for x in _속24 if (_꺼24(x) is not None)
                        and ((_꺼24(x) <= _컷24) if _방24 == "아래"
                             else (_꺼24(x) >= _컷24))]
                if len(_z24) < 300:
                    continue
                _길24 = sum(1 for x in _z24 if x["_20"] > 0) / len(_z24) * 100
                _앞24 = [x for x in _z24 if 날[x["인"] - 1][:4] <= "2018"]
                _뒤24 = [x for x in _z24 if 날[x["인"] - 1][:4] > "2018"]
                if len(_앞24) < 100 or len(_뒤24) < 100:
                    continue
                _길앞24 = sum(1 for x in _앞24 if x["_20"] > 0) / len(_앞24) * 100
                _길뒤24 = sum(1 for x in _뒤24 if x["_20"] > 0) / len(_뒤24) * 100
                if (_길24 - _바24) < 2.0 or (_길앞24 - _바24) * (_길뒤24 - _바24) <= 0:
                    continue
                _좋24.append((_길24 - _바24, _이24))
            _좋24.sort(reverse=True)
            _고른24[_라칸24] = [z[1] for z in _좋24[:2]]

        def _칸규칙24(x, 라칸, 든, 쓸것):
            if not 든(x):
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            for _이24, _꺼24, _방24 in _재19:
                if _이24 not in 쓸것:
                    continue
                _컷24 = _문24.get((라칸, _이24))
                if _컷24 is None:
                    return False
                _v = _꺼24(x)
                if _v is None:
                    return False
                if (_v > _컷24) if _방24 == "아래" else (_v < _컷24):
                    return False
            return True

        # ── 1 · 셋 다를 넘은 것을 고른다 ──
        _기24 = 시뮬(_c(_H))     # [견줌] 표에만 쓴다
        _산24 = []      # (표, 낱개규칙, 결과)
        for _라칸24, _든24 in _칸24:
            _뽑24 = _고른24.get(_라칸24) or []
            if not _뽑24:
                continue
            for _쓸24 in ([(_뽑24[0],)]
                          + ([(_뽑24[0], _뽑24[1])] if len(_뽑24) >= 2 else [])):
                _낱24 = (lambda x, a=_라칸24, b=_든24, c=_쓸24:
                         _칸규칙24(x, a, b, c))
                _r24 = 시뮬(_c(lambda x, f=_낱24: _H(x) or f(x)))   # [견줌]
                if not _r24:
                    continue
                if (_r24["산"] > _기24["산"] and _r24["끝"] > _기24["끝"]
                        and _r24["낙"] > 낙폭기준):
                    _산24.append((f"{_라칸24} · {'+'.join(_쓸24)}", _낱24, _r24))
        _산24.sort(key=lambda t: -t[2]["끝"])
        print(f"\n     셋 다를 넘은 것 {len(_산24)}개 — **전부** 해마다·걷기를 돌린다")
        print(f"     {'설정':<36}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}")
        print(f"     {'Ⓗ (지금 · 견줌)':<36}{_기24['끝']:>16,.0f}원{100:>8.0f}%"
              f"{_기24['낙']:>7.1f}%{_기24['산']:>7}")
        for _표24, _낱24, _r24 in _산24:
            print(f"     {('Ⓗ OR ' + _표24):<36}{_r24['끝']:>16,.0f}원"
                  f"{_r24['끝'] / _기24['끝'] * 100:>8.0f}%{_r24['낙']:>7.1f}%{_r24['산']:>7}")

        # ── 1-b · 해마다 + 걷기 ──
        _걷산24 = []     # 걷기까지 넘은 것
        for _표24, _낱24, _r24 in _산24:
            _합24 = (lambda x, f=_낱24: _H(x) or f(x))      # [견줌]
            print(f"\n     ── [{_표24}] 해마다 + 걷기 ──")
            _차24, _낙24 = [], []
            for _y24 in range(2016, 2027):
                _ay24 = 시뮬(_c(_H), 시작년=str(_y24), 끝년=str(_y24))
                _by24 = 시뮬(_c(_합24), 시작년=str(_y24), 끝년=str(_y24))
                if not _ay24 or not _by24:
                    continue
                _차24.append((_by24["끝"] / _ay24["끝"] - 1) * 100
                             if _ay24["끝"] > 0 else 0)
                _낙24.append(_by24["낙"] - _ay24["낙"])
            print("        해마다: " + _해마다판정(_차24, _낙24)[0])
            # ⚠️ 걷기에 넘기는 것은 **OR 합친 것**이다 (낱개가 아니다).
            #    _걷기찍기 가 「앞뒤 둘 다 +」 인지를 참/거짓으로 돌려준다
            if _걷기찍기(_걷기(_합24)):
                _걷산24.append((_표24, _낱24, _r24))

        print(f"\n     ⇒ 셋 다 {len(_산24)}개 중 **걷기까지 넘은 것 {len(_걷산24)}개**")
        if not _걷산24:
            print("     ⇒ 세 관문을 다 넘은 것이 없다")
            print("=" * 122)
        else:
            _걷산24.sort(key=lambda t: -t[2]["끝"])
            _으뜸표24, _으뜸낱24, _으뜸r24 = _걷산24[0]
            print(f"     ⇒ 1등 = **{_으뜸표24}**  {_으뜸r24['끝']:,.0f}원")

            # ── 2 · 날 겹침 ──
            _으뜸날24 = {x["인"] for x in 사건 if _으뜸낱24(x)}
            print(f"\n     ── **1등과 날이 얼마나 겹치나** (자리를 다투는 건 종목이 아니라 날이다) ──")
            print(f"     {'설정':<36}{'제 날':>8}{'겹치는 날':>10}{'겹침%':>8}")
            for _표24, _낱24, _r24 in _걷산24[1:]:
                _날24 = {x["인"] for x in 사건 if _낱24(x)}
                _겹24 = len(_날24 & _으뜸날24)
                print(f"     {_표24:<36}{len(_날24):>8,}{_겹24:>10,}"
                      f"{(_겹24 / len(_날24) * 100 if _날24 else 0):>7.0f}%")

            # ── 3 · 1등 + 하나씩 · 1등 + 전부 ──
            print(f"\n     ── **1등에 더해 본다** (③ 이 1등보다 나아야 넣을 뜻이 있다) ──")
            print(f"     {'설정':<36}{'끝 자산':>17}{'1등의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            print(f"     {('Ⓗ OR ' + _으뜸표24 + ' (1등)'):<36}{_으뜸r24['끝']:>16,.0f}원"
                  f"{100:>8.0f}%{_으뜸r24['낙']:>7.1f}%{_으뜸r24['산']:>7}")
            _더24 = []
            for _표24, _낱24, _r24 in _걷산24[1:]:
                _둘24 = (lambda x, f=_으뜸낱24, g=_낱24: _H(x) or f(x) or g(x))  # [견줌]
                _rr24 = 시뮬(_c(_둘24))
                if not _rr24:
                    continue
                _같24 = abs(_rr24["끝"] - _으뜸r24["끝"]) < 1000
                if (not _같24) and _rr24["끝"] > _으뜸r24["끝"]:
                    _더24.append((f"1등 + {_표24}", _둘24))
                print(f"     {('1등 + ' + _표24):<36}{_rr24['끝']:>16,.0f}원"
                      f"{_rr24['끝'] / _으뜸r24['끝'] * 100:>8.1f}%{_rr24['낙']:>7.1f}%"
                      f"{_rr24['산']:>7}  "
                      + ("⚠️ 한 글자도 안 다르다 — 흡수된다" if _같24
                         else ("⭐ 더 낫다" if _rr24["끝"] > _으뜸r24["끝"] else "— 나을 게 없다")))
            if len(_걷산24) > 2:
                _모두24 = (lambda x, fs=[t[1] for t in _걷산24]:
                           _H(x) or any(f(x) for f in fs))                 # [견줌]
                _rr24 = 시뮬(_c(_모두24))
                if _rr24:
                    _같24 = abs(_rr24["끝"] - _으뜸r24["끝"]) < 1000
                    if (not _같24) and _rr24["끝"] > _으뜸r24["끝"]:
                        _더24.append(("1등 + 걷기 넘은 것 전부", _모두24))
                    print(f"     {'1등 + 걷기 넘은 것 전부':<36}{_rr24['끝']:>16,.0f}원"
                          f"{_rr24['끝'] / _으뜸r24['끝'] * 100:>8.1f}%{_rr24['낙']:>7.1f}%"
                          f"{_rr24['산']:>7}  "
                          + ("⚠️ 한 글자도 안 다르다 — 흡수된다" if _같24
                             else ("⭐ 더 낫다" if _rr24["끝"] > _으뜸r24["끝"]
                                   else "— 나을 게 없다")))

            # ── 4 · 더해서 나아진 것만 해마다 + 걷기 ──
            for _표24, _합24 in _더24[:4]:
                print(f"\n     ── [{_표24}] 해마다 + 걷기 ──")
                _차24, _낙24 = [], []
                for _y24 in range(2016, 2027):
                    _ay24 = 시뮬(_c(_H), 시작년=str(_y24), 끝년=str(_y24))
                    _by24 = 시뮬(_c(_합24), 시작년=str(_y24), 끝년=str(_y24))
                    if not _ay24 or not _by24:
                        continue
                    _차24.append((_by24["끝"] / _ay24["끝"] - 1) * 100
                                 if _ay24["끝"] > 0 else 0)
                    _낙24.append(_by24["낙"] - _ay24["낙"])
                print("        해마다: " + _해마다판정(_차24, _낙24)[0])
                _걷기찍기(_걷기(_합24))
            if not _더24:
                print(f"\n     ⇒ 무엇을 더해도 **1등 하나보다 나아지지 않는다**")
            print("     ⚠️ 반영은 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
            print("=" * 122)

    if _ONLY == "Q24":
        print("\n  ⭐ ONLY=Q24 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-25 한 개씩 쌓아 올린다 (앞으로 고르기)** (2026-09-22) ══
    #    Q-24: 1등 + 의료·정밀기기·낙폭60 = 317,844,734원 (지금의 126%) · 걷기 ✅
    #      의료는 혼자선 104% 꼴찌였는데 짝으로는 1등을 만들었다 —
    #      날이 1,599개인데 1등과 겹치는 날이 244개(15%)뿐이라 **빈 날을 채운다**
    #    ⇒ 혼자 떨어진 35개도 짝으로는 보탬이 될 수 있다. 43개 전부를 놓고 쌓는다.
    #    ⚠️ 여러 번 고르면 우연을 줍는다 — **바퀴마다 걷기를 관문으로** 세운다
    if _ONLY in ("", "Q25"):
        print("\n" + "=" * 122)
        print("  ── Q-25 ⭐⭐⭐ **한 개씩 쌓아 올린다** (43개 전부를 놓고) ──")
        print("     매 바퀴 43개를 다 넣어 보고 돈이 제일 느는 하나를 고른다")
        print("     ⚠️ 낙폭이 기준 안이고 **걷기 앞뒤 둘 다 +** 라야 고른다")
        print("     ⚠️ 여러 번 고르면 우연을 줍는다 — 몇 번 견줬는지 끝에 적는다")
        print("=" * 122)

        # ── 칸과 규칙 43개를 다시 만든다 (Q-23·Q-24 와 똑같다) ──
        _칸25 = []
        _섹셈25 = {}
        for x in 사건:
            _n25 = x.get("섹터")
            if _n25:
                _섹셈25[_n25] = _섹셈25.get(_n25, 0) + 1
        for _섹25 in [k for k, v in sorted(_섹셈25.items(), key=lambda t: -t[1])
                      if v >= 20000][:14]:
            _칸25.append((f"업종 {_섹25[:12]}",
                          (lambda x, a=_섹25: x.get("섹터") == a)))
        for _라잣25, _꺼잣25 in (("거래 두께", lambda x: x.get("대금억")),
                                 ("변동성", lambda x: x.get("섹시그마")),
                                 ("주가", lambda x: x.get("원시")),
                                 ("회전율", lambda x: x.get("회전율")),
                                 ("외국인 지분율", lambda x: x.get("지분율"))):
            _v25 = sorted(z for z in (_꺼잣25(x) for x in 사건) if z is not None)
            if len(_v25) < len(사건) * 0.3:
                continue
            _아25 = _v25[len(_v25) // 5]
            _위25 = _v25[len(_v25) * 4 // 5]
            _칸25.append((f"{_라잣25} 아래20%",
                          (lambda x, f=_꺼잣25, c=_아25: f(x) is not None and f(x) <= c)))
            _칸25.append((f"{_라잣25} 위20%",
                          (lambda x, f=_꺼잣25, c=_위25: f(x) is not None and f(x) >= c)))

        _문25, _고른25 = {}, {}
        for _라칸25, _든25 in _칸25:
            _속25 = [x for x in 사건 if _든25(x) and x.get("_20") is not None]
            if len(_속25) < 20000:
                continue
            _바25 = sum(1 for x in _속25 if x["_20"] > 0) / len(_속25) * 100
            for _이25, _꺼25, _방25 in _재19:
                _w25 = sorted(z for z in (_꺼25(x) for x in _속25) if z is not None)
                if len(_w25) < len(_속25) * 0.25:
                    continue
                _문25[(_라칸25, _이25)] = (_w25[len(_w25) // 5] if _방25 == "아래"
                                           else _w25[len(_w25) * 4 // 5])
            _좋25 = []
            for _이25, _꺼25, _방25 in _재19:
                _컷25 = _문25.get((_라칸25, _이25))
                if _컷25 is None:
                    continue
                _z25 = [x for x in _속25 if (_꺼25(x) is not None)
                        and ((_꺼25(x) <= _컷25) if _방25 == "아래"
                             else (_꺼25(x) >= _컷25))]
                if len(_z25) < 300:
                    continue
                _길25 = sum(1 for x in _z25 if x["_20"] > 0) / len(_z25) * 100
                _앞25 = [x for x in _z25 if 날[x["인"] - 1][:4] <= "2018"]
                _뒤25 = [x for x in _z25 if 날[x["인"] - 1][:4] > "2018"]
                if len(_앞25) < 100 or len(_뒤25) < 100:
                    continue
                _길앞25 = sum(1 for x in _앞25 if x["_20"] > 0) / len(_앞25) * 100
                _길뒤25 = sum(1 for x in _뒤25 if x["_20"] > 0) / len(_뒤25) * 100
                if (_길25 - _바25) < 2.0 or (_길앞25 - _바25) * (_길뒤25 - _바25) <= 0:
                    continue
                _좋25.append((_길25 - _바25, _이25))
            _좋25.sort(reverse=True)
            _고른25[_라칸25] = [z[1] for z in _좋25[:2]]

        def _칸규칙25(x, 라칸, 든, 쓸것):
            if not 든(x):
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            for _이25, _꺼25, _방25 in _재19:
                if _이25 not in 쓸것:
                    continue
                _컷25 = _문25.get((라칸, _이25))
                if _컷25 is None:
                    return False
                _v = _꺼25(x)
                if _v is None:
                    return False
                if (_v > _컷25) if _방25 == "아래" else (_v < _컷25):
                    return False
            return True

        _낱들25 = []      # (표, 낱개규칙)
        for _라칸25, _든25 in _칸25:
            _뽑25 = _고른25.get(_라칸25) or []
            if not _뽑25:
                continue
            for _쓸25 in ([(_뽑25[0],)]
                          + ([(_뽑25[0], _뽑25[1])] if len(_뽑25) >= 2 else [])):
                _낱들25.append((f"{_라칸25} · {'+'.join(_쓸25)}",
                                (lambda x, a=_라칸25, b=_든25, c=_쓸25:
                                 _칸규칙25(x, a, b, c))))
        print(f"\n     쌓을 거리 {len(_낱들25)}개")

        # ── 한 개씩 쌓는다 ──
        _기25 = 시뮬(_c(_H))     # [견줌]
        _뽑힌25 = []             # 고른 낱개들
        _견줌셈25 = 0
        _이제25 = _기25
        print(f"\n     {'바퀴':<5}{'고른 것':<34}{'끝 자산':>17}{'지금의%':>9}"
              f"{'낙폭':>8}{'산 것':>7}")
        print(f"     {'0':<5}{'Ⓗ (지금 · 견줌)':<34}{_기25['끝']:>16,.0f}원"
              f"{100:>8.0f}%{_기25['낙']:>7.1f}%{_기25['산']:>7}")
        for _바퀴25 in range(1, 6):
            _후25 = []
            for _표25, _낱25 in _낱들25:
                if _표25 in [t[0] for t in _뽑힌25]:
                    continue
                _벌25 = [t[1] for t in _뽑힌25] + [_낱25]
                _합25 = (lambda x, fs=_벌25: _H(x) or any(f(x) for f in fs))   # [견줌]
                _r25 = 시뮬(_c(_합25))
                _견줌셈25 += 1
                if not _r25:
                    continue
                if _r25["낙"] <= 낙폭기준:
                    continue
                if _r25["끝"] <= _이제25["끝"] + 1000:
                    continue
                _후25.append((_r25["끝"], _표25, _낱25, _r25, _합25))
            _후25.sort(key=lambda t: -t[0])
            if not _후25:
                print(f"     {_바퀴25:<5}— 더 나아지는 게 없다. 멈춘다")
                break
            # 돈 순으로 보되 **걷기를 넘는 첫 번째**를 고른다
            _골25 = None
            for _끝25, _표25, _낱25, _r25, _합25 in _후25[:4]:
                print(f"\n     [{_바퀴25}바퀴 후보] {_표25}  {_r25['끝']:,.0f}원"
                      f" ({_r25['끝'] / _기25['끝'] * 100:.0f}%) · 낙폭 {_r25['낙']:.1f}%"
                      f" · 산 것 {_r25['산']}")
                if _걷기찍기(_걷기(_합25), 들여="        "):
                    _골25 = (_표25, _낱25, _r25)
                    break
                print("        ↑ 걷기를 못 넘었다 — 다음 후보를 본다")
            if _골25 is None:
                print(f"     {_바퀴25:<5}— 돈은 느는데 **걷기를 넘는 게 없다. 멈춘다**")
                break
            _뽑힌25.append((_골25[0], _골25[1]))
            _이제25 = _골25[2]
            print(f"\n     {_바퀴25:<5}{('+ ' + _골25[0]):<34}{_이제25['끝']:>16,.0f}원"
                  f"{_이제25['끝'] / _기25['끝'] * 100:>8.0f}%{_이제25['낙']:>7.1f}%"
                  f"{_이제25['산']:>7}")

        # ── 마무리 ──
        print(f"\n     ── **쌓은 결과** ──")
        if not _뽑힌25:
            print("     ⇒ 아무것도 못 쌓았다")
        else:
            for _i25, (_표25, _) in enumerate(_뽑힌25, 1):
                print(f"       {_i25}. {_표25}")
            _끝합25 = (lambda x, fs=[t[1] for t in _뽑힌25]:
                       _H(x) or any(f(x) for f in fs))                      # [견줌]
            _r끝25 = 시뮬(_c(_끝합25))
            print(f"\n     Ⓗ + 위 {len(_뽑힌25)}개  {_r끝25['끝']:,.0f}원"
                  f"  (지금의 {_r끝25['끝'] / _기25['끝'] * 100:.0f}%)"
                  f" · 낙폭 {_r끝25['낙']:.1f}% · 산 것 {_r끝25['산']}"
                  f"  (지금 {_기25['산']})")
            print(f"\n     ── [쌓은 것] 해마다 + 걷기 ──")
            _차25, _낙25 = [], []
            for _y25 in range(2016, 2027):
                _ay25 = 시뮬(_c(_H), 시작년=str(_y25), 끝년=str(_y25))
                _by25 = 시뮬(_c(_끝합25), 시작년=str(_y25), 끝년=str(_y25))
                if not _ay25 or not _by25:
                    continue
                _차25.append((_by25["끝"] / _ay25["끝"] - 1) * 100
                             if _ay25["끝"] > 0 else 0)
                _낙25.append(_by25["낙"] - _ay25["낙"])
            print("        해마다: " + _해마다판정(_차25, _낙25)[0])
            _걷기찍기(_걷기(_끝합25))
        print(f"\n     ⚠️ **{_견줌셈25}번 견줘서 고른 것이다** — 여러 번 고르면 우연을 줍는다.")
        print("        바퀴마다 걷기를 관문으로 세웠지만, 걷기도 두 토막일 뿐이다.")
        print("        반영하더라도 **앞으로의 기록(forward)으로 채점**해야 진짜를 안다")
        print("     ⚠️ 반영은 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

    if _ONLY == "Q25":
        print("\n  ⭐ ONLY=Q25 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-26 「더한 것이 앞뒤 둘 다에서 일을 하나」로 쌓는다** (2026-09-22) ══
    #    Q-25 의 관문이 헐거웠다. 다섯을 쌓아 149% 를 만들었는데 앞 구간이 안 움직였다:
    #      바퀴2·4·5 에 더한 것은 앞 2010~2020 에서 **한 종목도 더 못 샀다**
    #      (65,782,537원·113개 그대로 · 69,335,379원·116개 그대로)
    #    걷기 관문이 **쌓인 것 전체**의 앞뒤를 봤기 때문이다 —
    #    1바퀴 회전율이 앞을 이미 + 로 만들어 놔서 뒤에 무엇을 얹어도 「앞 +」로 찍혔다.
    #    Q-24 에서 금융이 혼자선 걷기 ❌(앞 0.0%) 였던 그것이 여기선 통과했다.
    #    ⇒ **더한 것이 앞 구간에서도 일을 해야 고른다** (쌓인 것의 앞끝과 견준다)
    if _ONLY in ("", "Q26"):
        print("\n" + "=" * 122)
        print("  ── Q-26 ⭐⭐⭐ **더한 것이 앞뒤 둘 다에서 일을 해야 고른다** ──")
        print("     Q-25 는 쌓인 것 전체의 앞뒤를 봤다 — 1바퀴가 앞을 + 로 만들어 놓으면")
        print("     뒤에 무엇을 얹어도 통과했다. 2·4·5 바퀴가 앞에서 한 종목도 안 늘었다")
        print("     ⇒ 여기선 **쌓인 것의 앞끝·뒤끝과 견줘 둘 다 늘어야** 고른다")
        print("=" * 122)

        # ── 칸과 규칙 43개 (Q-23~Q-25 와 똑같다) ──
        _칸26 = []
        _섹셈26 = {}
        for x in 사건:
            _n26 = x.get("섹터")
            if _n26:
                _섹셈26[_n26] = _섹셈26.get(_n26, 0) + 1
        for _섹26 in [k for k, v in sorted(_섹셈26.items(), key=lambda t: -t[1])
                      if v >= 20000][:14]:
            _칸26.append((f"업종 {_섹26[:12]}",
                          (lambda x, a=_섹26: x.get("섹터") == a)))
        for _라잣26, _꺼잣26 in (("거래 두께", lambda x: x.get("대금억")),
                                 ("변동성", lambda x: x.get("섹시그마")),
                                 ("주가", lambda x: x.get("원시")),
                                 ("회전율", lambda x: x.get("회전율")),
                                 ("외국인 지분율", lambda x: x.get("지분율"))):
            _v26 = sorted(z for z in (_꺼잣26(x) for x in 사건) if z is not None)
            if len(_v26) < len(사건) * 0.3:
                continue
            _아26 = _v26[len(_v26) // 5]
            _위26 = _v26[len(_v26) * 4 // 5]
            _칸26.append((f"{_라잣26} 아래20%",
                          (lambda x, f=_꺼잣26, c=_아26: f(x) is not None and f(x) <= c)))
            _칸26.append((f"{_라잣26} 위20%",
                          (lambda x, f=_꺼잣26, c=_위26: f(x) is not None and f(x) >= c)))

        _문26, _고른26 = {}, {}
        for _라칸26, _든26 in _칸26:
            _속26 = [x for x in 사건 if _든26(x) and x.get("_20") is not None]
            if len(_속26) < 20000:
                continue
            _바26 = sum(1 for x in _속26 if x["_20"] > 0) / len(_속26) * 100
            for _이26, _꺼26, _방26 in _재19:
                _w26 = sorted(z for z in (_꺼26(x) for x in _속26) if z is not None)
                if len(_w26) < len(_속26) * 0.25:
                    continue
                _문26[(_라칸26, _이26)] = (_w26[len(_w26) // 5] if _방26 == "아래"
                                           else _w26[len(_w26) * 4 // 5])
            _좋26 = []
            for _이26, _꺼26, _방26 in _재19:
                _컷26 = _문26.get((_라칸26, _이26))
                if _컷26 is None:
                    continue
                _z26 = [x for x in _속26 if (_꺼26(x) is not None)
                        and ((_꺼26(x) <= _컷26) if _방26 == "아래"
                             else (_꺼26(x) >= _컷26))]
                if len(_z26) < 300:
                    continue
                _길26 = sum(1 for x in _z26 if x["_20"] > 0) / len(_z26) * 100
                _앞26 = [x for x in _z26 if 날[x["인"] - 1][:4] <= "2018"]
                _뒤26 = [x for x in _z26 if 날[x["인"] - 1][:4] > "2018"]
                if len(_앞26) < 100 or len(_뒤26) < 100:
                    continue
                _길앞26 = sum(1 for x in _앞26 if x["_20"] > 0) / len(_앞26) * 100
                _길뒤26 = sum(1 for x in _뒤26 if x["_20"] > 0) / len(_뒤26) * 100
                if (_길26 - _바26) < 2.0 or (_길앞26 - _바26) * (_길뒤26 - _바26) <= 0:
                    continue
                _좋26.append((_길26 - _바26, _이26))
            _좋26.sort(reverse=True)
            _고른26[_라칸26] = [z[1] for z in _좋26[:2]]

        def _칸규칙26(x, 라칸, 든, 쓸것):
            if not 든(x):
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            for _이26, _꺼26, _방26 in _재19:
                if _이26 not in 쓸것:
                    continue
                _컷26 = _문26.get((라칸, _이26))
                if _컷26 is None:
                    return False
                _v = _꺼26(x)
                if _v is None:
                    return False
                if (_v > _컷26) if _방26 == "아래" else (_v < _컷26):
                    return False
            return True

        _낱들26 = []
        for _라칸26, _든26 in _칸26:
            _뽑26 = _고른26.get(_라칸26) or []
            if not _뽑26:
                continue
            for _쓸26 in ([(_뽑26[0],)]
                          + ([(_뽑26[0], _뽑26[1])] if len(_뽑26) >= 2 else [])):
                _낱들26.append((f"{_라칸26} · {'+'.join(_쓸26)}",
                                (lambda x, a=_라칸26, b=_든26, c=_쓸26:
                                 _칸규칙26(x, a, b, c))))
        print(f"\n     쌓을 거리 {len(_낱들26)}개")

        def _앞뒤끝26(줄들):
            r"""걷기 두 줄에서 (앞 끝 자산, 뒤 끝 자산, 앞 낙폭, 뒤 낙폭)."""
            if len(줄들) != 2:
                return None
            return (줄들[0][2]["끝"], 줄들[1][2]["끝"],
                    줄들[0][2]["낙"], 줄들[1][2]["낙"])

        # ── 쌓는다 — 바퀴마다 **더한 것이 앞뒤 둘 다에서 늘려야** 고른다 ──
        _벌26 = []            # 고른 낱개들
        _견줌셈26 = 0
        _바탕걷26 = _앞뒤끝26(_걷기(_H))
        if _바탕걷26 is None:
            print("     ⚠️ 바탕 걷기를 못 냈다 — 여기서 멈춘다")
        else:
            _앞이제26, _뒤이제26 = _바탕걷26[0], _바탕걷26[1]
            print(f"\n     바퀴 0  Ⓗ (지금 · 견줌)"
                  f"   앞 {_앞이제26:,.0f}원 · 뒤 {_뒤이제26:,.0f}원")
            for _바퀴26 in range(1, 7):
                _후26 = []
                for _표26, _낱26 in _낱들26:
                    if _표26 in [t[0] for t in _벌26]:
                        continue
                    _새벌26 = [t[1] for t in _벌26] + [_낱26]
                    _합26 = (lambda x, fs=_새벌26: _H(x) or any(f(x) for f in fs))  # [견줌]
                    _걷26 = _앞뒤끝26(_걷기(_합26))
                    _견줌셈26 += 1
                    if _걷26 is None:
                        continue
                    _앞새26, _뒤새26, _앞낙26, _뒤낙26 = _걷26
                    if _앞낙26 <= 낙폭기준 or _뒤낙26 <= 낙폭기준:
                        continue
                    # ⭐ 더한 것이 **앞에서도 뒤에서도** 늘려야 한다
                    if _앞새26 <= _앞이제26 + 1 or _뒤새26 <= _뒤이제26 + 1:
                        continue
                    _후26.append((_뒤새26, _앞새26, _표26, _낱26, _합26, _뒤낙26))
                if not _후26:
                    print(f"\n     바퀴 {_바퀴26} — **앞뒤 둘 다 늘리는 게 없다. 멈춘다**")
                    break
                _후26.sort(key=lambda t: -t[0])
                _뒤새26, _앞새26, _표26, _낱26, _합26, _뒤낙26 = _후26[0]
                print(f"\n     ── 바퀴 {_바퀴26} — 앞뒤 둘 다 늘리는 것 {len(_후26)}개 ──")
                for _z26 in _후26[:5]:
                    print(f"        {_z26[2]:<34}앞 {_z26[1]:>14,.0f}원"
                          f" ({(_z26[1] / _앞이제26 - 1) * 100:+.1f}%)"
                          f"  뒤 {_z26[0]:>14,.0f}원"
                          f" ({(_z26[0] / _뒤이제26 - 1) * 100:+.1f}%)")
                print(f"     ⇒ 고른 것: **{_표26}**")
                _벌26.append((_표26, _낱26))
                _앞이제26, _뒤이제26 = _앞새26, _뒤새26

            # ── 마무리 ──
            print(f"\n     ── **쌓은 결과** ──")
            if not _벌26:
                print("     ⇒ 아무것도 못 쌓았다 — 지금 규칙이 그대로 낫다")
            else:
                for _i26, (_표26, _) in enumerate(_벌26, 1):
                    print(f"       {_i26}. {_표26}")
                _끝합26 = (lambda x, fs=[t[1] for t in _벌26]:
                           _H(x) or any(f(x) for f in fs))                  # [견줌]
                _기26 = 시뮬(_c(_H))         # [견줌]
                _r끝26 = 시뮬(_c(_끝합26))
                print(f"\n     {'설정':<24}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}")
                print(f"     {'Ⓗ (지금 · 견줌)':<24}{_기26['끝']:>16,.0f}원{100:>8.0f}%"
                      f"{_기26['낙']:>7.1f}%{_기26['산']:>7}")
                print(f"     {('Ⓗ + 쌓은 ' + str(len(_벌26)) + '개'):<24}"
                      f"{_r끝26['끝']:>16,.0f}원"
                      f"{_r끝26['끝'] / _기26['끝'] * 100:>8.0f}%"
                      f"{_r끝26['낙']:>7.1f}%{_r끝26['산']:>7}")
                print(f"\n     ── [쌓은 것] 해마다 + 걷기 ──")
                _차26, _낙26 = [], []
                for _y26 in range(2016, 2027):
                    _ay26 = 시뮬(_c(_H), 시작년=str(_y26), 끝년=str(_y26))
                    _by26 = 시뮬(_c(_끝합26), 시작년=str(_y26), 끝년=str(_y26))
                    if not _ay26 or not _by26:
                        continue
                    _차26.append((_by26["끝"] / _ay26["끝"] - 1) * 100
                                 if _ay26["끝"] > 0 else 0)
                    _낙26.append(_by26["낙"] - _ay26["낙"])
                print("        해마다: " + _해마다판정(_차26, _낙26)[0])
                _걷기찍기(_걷기(_끝합26))
            print(f"\n     ⚠️ **{_견줌셈26}번 견줘서 고른 것이다** — 여러 번 고르면 우연을 줍는다.")
            print("        이번엔 바퀴마다 **더한 것이 앞뒤 둘 다에서 일을 하나**를 봤다.")
            print("        그래도 걷기는 두 토막일 뿐이다 — **앞으로의 기록으로 채점**해야 안다")
            print("     ⚠️ 반영은 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

    if _ONLY == "Q26":
        print("\n  ⭐ ONLY=Q26 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-27 고른 규칙을 말로 풀어 찍는다** (2026-09-22) ══
    #    Q-24(짝짓기)와 Q-26(고친 관문으로 쌓기)이 **같은 둘**에 닿았다.
    #    그런데 이게 무슨 규칙인지 **사람 말로 적힌 적이 없고 문턱 값도 안 찍혔다.**
    #    넣을지 정하려면 「무슨 조건이냐」를 알아야 하고,
    #    넣기로 하면 실전 코드(rule_def.py)에 그 숫자를 적어야 한다
    if _ONLY in ("", "Q27"):
        print("\n" + "=" * 122)
        print("  ── Q-27 ⭐⭐⭐ **고른 규칙을 말로 풀어 찍는다** ──")
        print("     Q-24(짝짓기)와 Q-26(쌓기)이 같은 둘에 닿았다 — 그게 무슨 조건인가")
        print("=" * 122)

        # ── ① 회전율 위20% · 선물20 ──
        _회값27 = sorted(z for z in (x.get("회전율") for x in 사건) if z is not None)
        _회위27 = _회값27[len(_회값27) * 4 // 5]

        def _회든27(x):
            _z = x.get("회전율")
            return _z is not None and _z >= _회위27

        _회칸27 = [x for x in 사건 if _회든27(x) and x.get("_20") is not None]
        _선값27 = sorted(z for z in (_선물19(x) for x in _회칸27) if z is not None)
        _회선문27 = _선값27[len(_선값27) // 5]

        # ── ② 업종 의료·정밀기기 · 낙폭60 ──
        _의이름27 = None
        for _k27 in {x.get("섹터") for x in 사건 if x.get("섹터")}:
            if _k27[:12] == "의료·정밀기기"[:12] or _k27.startswith("의료"):
                _의이름27 = _k27
                break
        _의칸27 = [x for x in 사건
                   if x.get("섹터") == _의이름27 and x.get("_20") is not None]
        _낙값27 = sorted(z for z in (x.get("낙폭60") for x in _의칸27) if z is not None)
        _의낙문27 = _낙값27[len(_낙값27) // 5] if _낙값27 else None

        print(f"\n  ── **① 회전율 위20% · 선물20** ──")
        print(f"     ⓐ 회전율이 위 20% 안에 든다     회전율 ≥ **{_회위27:,.2f}%**")
        print(f"        (그날 거래대금이 시가총액의 {_회위27:,.2f}% 넘게 돈다 = 손이 많이 탄 날)")
        print(f"     ⓑ 코스피200 선물 20일 수익률이 아래 20%   선물20 ≤ **{_회선문27:,.2f}%**")
        print(f"        (선물이 20일 동안 {abs(_회선문27):,.2f}% 넘게 빠져 있다 = 시장이 눌린 상태)")
        print(f"        ⚠️ ⓑ 문턱은 **ⓐ에 드는 {len(_회칸27):,}건 안에서** 낸 값이다 (소형 값이 아니다)")
        print(f"     ⓒ 재무통과 · 대금통과는 지금 규칙과 같다")

        print(f"\n  ── **② 업종 「{_의이름27}」 · 낙폭60** ──")
        if _의낙문27 is None:
            print("     ⚠️ 낙폭60 값을 못 냈다")
        else:
            print(f"     ⓐ 업종이 「{_의이름27}」 이다                  ({len(_의칸27):,}건)")
            print(f"     ⓑ 60일 낙폭이 그 업종 아래 20%     낙폭60 ≤ **{_의낙문27:,.2f}%**")
            print(f"        (60일 고점에서 {abs(_의낙문27):,.2f}% 넘게 빠졌다)")
            print("        ⚠️ 이 문턱은 **그 업종 자료로만** 냈다 — 소형에서 찾은 값이 아니다")
            print(f"     ⓒ 재무통과 · 대금통과는 지금 규칙과 같다")
            print(f"     ⭐ **재료가 혼자 다르다** — 나머지는 다 선물20(시장 눌림)인데 이것만 제 낙폭이다")

        def _규칙1_27(x):
            if not _회든27(x):
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            _f = _선물19(x)
            return _f is not None and _f <= _회선문27

        def _규칙2_27(x):
            if _의낙문27 is None or x.get("섹터") != _의이름27:
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            _d = x.get("낙폭60")
            return _d is not None and _d <= _의낙문27

        # ── 해마다 몇 날이나 켜지나 ──
        print(f"\n  ── **해마다 몇 날이나 켜지나** (잦으면 자리를 다투고, 드물면 쓸모가 적다) ──")
        print(f"     {'해':<8}{'지금 Ⓗ':>10}{'① 회전율':>11}{'② 의료':>10}"
              f"{'①② 가 여는 새 날':>18}")
        for _y27 in range(2016, 2027):
            _ㅎ날27 = {x["인"] for x in 사건
                       if 날[x["인"] - 1][:4] == str(_y27) and _H(x)}
            _1날27 = {x["인"] for x in 사건
                      if 날[x["인"] - 1][:4] == str(_y27) and _규칙1_27(x)}
            _2날27 = {x["인"] for x in 사건
                      if 날[x["인"] - 1][:4] == str(_y27) and _규칙2_27(x)}
            _새27 = (_1날27 | _2날27) - _ㅎ날27
            print(f"     {_y27:<8}{len(_ㅎ날27):>10,}{len(_1날27):>11,}{len(_2날27):>10,}"
                  f"{len(_새27):>18,}")
        _ㅎ전27 = {x["인"] for x in 사건 if _H(x)}
        _1전27 = {x["인"] for x in 사건 if _규칙1_27(x)}
        _2전27 = {x["인"] for x in 사건 if _규칙2_27(x)}
        _새전27 = (_1전27 | _2전27) - _ㅎ전27
        print(f"     {'전부':<8}{len(_ㅎ전27):>10,}{len(_1전27):>11,}{len(_2전27):>10,}"
              f"{len(_새전27):>18,}")
        print(f"\n     ⇒ 지금 규칙이 **아무것도 안 사던 날 {len(_새전27):,}일**이 새로 열린다")
        print("        이게 돈이 느는 까닭이다 — 같은 날에 끼면 자리만 다툰다")
        print(f"     ⇒ ① 과 ② 가 겹치는 날 {len(_1전27 & _2전27):,}일 "
              f"(① {len(_1전27):,} · ② {len(_2전27):,}) — 서로 다른 날에 뜬다")

        # ── 최근에 켜진 날 ──
        print(f"\n  ── **최근에 켜진 날** (눈으로 확인) ──")
        for _라27, _규27 in (("① 회전율 위20%·선물20", _규칙1_27),
                              (f"② 업종 {_의이름27}·낙폭60", _규칙2_27)):
            # ⚠️ 사건에 「이름」 칸은 없다 — 종목 열쇠는 "code" 다 (자료 구조로 확인)
            _뽑27 = sorted({(날[x["인"] - 1], x["code"])
                            for x in 사건 if _규27(x)}, reverse=True)[:8]
            print(f"     [{_라27}]")
            for _d27, _nm27 in _뽑27:
                print(f"        {_d27}  {_nm27}")
        print("     ⚠️ 반영은 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

    if _ONLY == "Q27":
        print("\n  ⭐ ONLY=Q27 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-28 선물을 하루 늦춰도 ① 이 사나** (2026-09-22) ══
    #    ① 은 세 관문을 넘었는데 **실전에 못 넣었다** — 코스피200선물이
    #    영업일 하루 늦게 온다 (20260918 -> 09-21 20:30 도착).
    #    기준일의 선물값이 그날 저녁에나 오니 넣어도 조용히 안 켜진다.
    #    ⇒ **실전에서 실제로 쥘 수 있는 값**(기준일 직전 거래일)로 다시 잰다.
    #    ⚠️ 바탕이 바뀌었다 — 의료·정밀기기는 **오늘 실전에 넣었다.**
    #       그러니 물음은 「Ⓗ + 의료 에 ① 을 더하면?」이다 (옛 바탕으로 재면 딴 답)
    if _ONLY in ("", "Q28"):
        print("\n" + "=" * 122)
        print("  ── Q-28 ⭐⭐⭐ **선물을 하루 늦춰도 ① 이 사나** ──")
        print("     실전은 기준일 선물값을 그날 아침에 못 쥔다 (영업일 하루 늦게 온다)")
        print("     ⇒ 기준일 **직전 거래일** 선물로 다시 잰다")
        print("     ⚠️ 바탕은 Ⓗ 가 아니라 **Ⓗ + 의료·정밀기기** (오늘 실전에 넣었다)")
        print("=" * 122)

        # ── 바탕 ⓪ : Ⓗ + 의료·정밀기기·낙폭60 (실전에 들어간 그대로) ──
        _의이름28 = None
        for _k28 in {x.get("섹터") for x in 사건 if x.get("섹터")}:
            if str(_k28).startswith("의료"):
                _의이름28 = _k28
                break
        _의칸28 = [x for x in 사건
                   if x.get("섹터") == _의이름28 and x.get("_20") is not None]
        _낙값28 = sorted(z for z in (x.get("낙폭60") for x in _의칸28) if z is not None)
        _의문28 = _낙값28[len(_낙값28) // 5] if _낙값28 else None

        def _의료28(x):
            if _의문28 is None or x.get("섹터") != _의이름28:
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            _d = x.get("낙폭60")
            return _d is not None and _d <= _의문28

        def _바탕28(x):
            return _H(x) or _의료28(x)        # [견줌] 오늘 실전에 들어간 것

        # ── 회전율 칸 ──
        _회값28 = sorted(z for z in (x.get("회전율") for x in 사건) if z is not None)
        _회위28 = _회값28[len(_회값28) * 4 // 5]

        def _회든28(x):
            _z = x.get("회전율")
            return _z is not None and _z >= _회위28

        _회칸28 = [x for x in 사건 if _회든28(x) and x.get("_20") is not None]

        # 선물 두 가지 — 그날 / 하루 늦춤
        def _선그날28(x):
            return _선물20.get(x["인"] - 1)

        def _선늦춤28(x):
            r"""**기준일 직전 거래일**의 선물 20일 수익률.

            실전은 기준일 선물을 그날 아침에 못 쥔다 — 그래서 하나 앞의 것을 쓴다.
            ⚠️ 하나 앞이 없으면 **None** — 없는 걸 맞다고 하면 안 된다
            """
            return _선물20.get(x["인"] - 2)

        print(f"\n     의료 문턱 낙폭60 ≤ {_의문28:,.2f}% (칸 {len(_의칸28):,}건)"
              if _의문28 is not None else "\n     ⚠️ 의료 문턱을 못 냈다")
        print(f"     회전율 위20% ≥ {_회위28:,.2f}% (칸 {len(_회칸28):,}건)")

        _잰28 = []
        for _라28, _꺼28 in (("① 선물 그날 (실전엔 못 쓴다)", _선그날28),
                             ("② 선물 하루 늦춤 (실전에서 쓸 수 있다)", _선늦춤28)):
            _v28 = sorted(z for z in (_꺼28(x) for x in _회칸28) if z is not None)
            if not _v28:
                print(f"     {_라28} — 값이 없다")
                continue
            _문28 = _v28[len(_v28) // 5]

            def _회전28(x, f=_꺼28, c=_문28):
                if not _회든28(x):
                    return False
                if not (재무통과(x) and 대금통과(x)):
                    return False
                _z = f(x)
                return _z is not None and _z <= c

            _잰28.append((_라28, _문28, _회전28))
            print(f"     {_라28:<36} 선물 문턱 {_문28:,.2f}%"
                  f" · 켜지는 사건 {sum(1 for x in 사건 if _회전28(x)):,}건")

        # 두 정의가 **같은 날**을 가리키나
        if len(_잰28) == 2:
            _날a28 = {x["인"] for x in 사건 if _잰28[0][2](x)}
            _날b28 = {x["인"] for x in 사건 if _잰28[1][2](x)}
            print(f"\n     두 정의가 가리키는 날 — 그날 {len(_날a28):,} · 하루 늦춤 {len(_날b28):,}"
                  f" · 겹침 {len(_날a28 & _날b28):,}")

        # ── 관문 ──
        _기28 = 시뮬(_c(_바탕28))      # [견줌] 오늘 실전 바탕
        _옛28 = 시뮬(_c(_H))           # [견줌] 의료 넣기 전
        print(f"\n     {'설정':<36}{'끝 자산':>17}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        print(f"     {'Ⓗ (의료 넣기 전 · 견줌)':<36}{_옛28['끝']:>16,.0f}원"
              f"{_옛28['끝'] / _기28['끝'] * 100:>8.0f}%{_옛28['낙']:>7.1f}%{_옛28['산']:>7}")
        print(f"     {'⓪ Ⓗ + 의료 (지금 실전 · 바탕)':<36}{_기28['끝']:>16,.0f}원"
              f"{100:>8.0f}%{_기28['낙']:>7.1f}%{_기28['산']:>7}")
        _바걷28 = _걷기(_바탕28)
        _앞바28 = _바걷28[0][2]["끝"] if len(_바걷28) == 2 else None
        _뒤바28 = _바걷28[1][2]["끝"] if len(_바걷28) == 2 else None
        for _라28, _문28, _회전28 in _잰28:
            _합28 = (lambda x, f=_회전28: _바탕28(x) or f(x))       # [견줌]
            _r28 = 시뮬(_c(_합28))
            if not _r28:
                continue
            _ok28 = (_r28["산"] > _기28["산"], _r28["끝"] > _기28["끝"],
                     _r28["낙"] > 낙폭기준)
            print(f"     {('⓪ + ' + _라28):<36}{_r28['끝']:>16,.0f}원"
                  f"{_r28['끝'] / _기28['끝'] * 100:>8.0f}%{_r28['낙']:>7.1f}%"
                  f"{_r28['산']:>7}  " + ("✅ 셋 다" if all(_ok28) else "❌"))
        for _라28, _문28, _회전28 in _잰28:
            _합28 = (lambda x, f=_회전28: _바탕28(x) or f(x))       # [견줌]
            _r28 = 시뮬(_c(_합28))
            if not _r28:
                continue
            print(f"\n     ── [⓪ + {_라28}] 해마다 + 걷기 ──")
            _차28, _낙28 = [], []
            for _y28 in range(2016, 2027):
                _a28 = 시뮬(_c(_바탕28), 시작년=str(_y28), 끝년=str(_y28))
                _b28 = 시뮬(_c(_합28), 시작년=str(_y28), 끝년=str(_y28))
                if not _a28 or not _b28:
                    continue
                _차28.append((_b28["끝"] / _a28["끝"] - 1) * 100
                             if _a28["끝"] > 0 else 0)
                _낙28.append(_b28["낙"] - _a28["낙"])
            print("        해마다: " + _해마다판정(_차28, _낙28)[0])
            _걷28 = _걷기(_합28, _바탕28)     # ⭐ 밑거름도 **바탕**으로 (Ⓗ 가 아니다)
            _걷기찍기(_걷28)
            # ⭐ 증분으로도 본다 — 바탕의 앞끝·뒤끝을 둘 다 늘렸나
            if len(_걷28) == 2 and _앞바28 and _뒤바28:
                _앞새28, _뒤새28 = _걷28[0][2]["끝"], _걷28[1][2]["끝"]
                print(f"        증분: 앞 {(_앞새28 / _앞바28 - 1) * 100:+.1f}%"
                      f" · 뒤 {(_뒤새28 / _뒤바28 - 1) * 100:+.1f}%"
                      + ("   ✅ 둘 다 늘렸다" if (_앞새28 > _앞바28 + 1
                                                  and _뒤새28 > _뒤바28 + 1)
                         else "   ❌ 한쪽이 안 늘었다"))
        print("\n     ⚠️ ② 가 넘어야 넣을 수 있다 — ① 은 실전에서 쥘 수 없는 값이다")
        print("     ⚠️ 반영은 **실전 코드를 건드리는 변경**이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

    if _ONLY == "Q28":
        print("\n  ⭐ ONLY=Q28 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ⚠️ _덤프길 은 _D준비 가 쓴다 — **그보다 앞에** 있어야 한다.
    #    (2026-09-25: 칸 판이 _D준비 를 부를 때 _덤프길 이 아직 없어 25번 삼켜졌다)
    _덤프길 = os.path.join(O._DATA, "_labs", "h_events.jsonl")

    # ══ **D 절 준비 — 지금 실전 바탕을 판 안에 다시 세운다** (2026-09-23 · 연휴 계획 D) ══
    #    R0(DUMPH_LIVE)가 덜어 둔 h_events.jsonl = Ⓗ + 업종 셋 · c_events_* = 칸(띠) 사건
    #    ⚠️ 여기서는 지금 규칙을 **다시 계산하지 않는다** — 덜어 둔 열쇠로만 가른다 (막개 ④ 지킴)
    def _D준비():
        """돌려주는 것: (합, 합묶, 열기, 키표) · 키표 = {"Ⓗ": set, 업종이름: set, "지금": set, "옛": set}"""
        _덤 = [json.loads(z) for z in io.open(_덤프길, encoding="utf-8") if z.strip()]
        _덤키 = {(x["code"], x["인"]) for x in _덤}
        _칸 = []
        for _꼬 in ("중형금속", "소형운송장비"):
            _길 = os.path.join(O._DATA, "_labs", f"c_events_{_꼬}.jsonl")
            if os.path.exists(_길):
                _칸 += [json.loads(z) for z in io.open(_길, encoding="utf-8") if z.strip()]
        _본 = {(x["code"], x["인"]) for x in 사건}
        _합 = list(사건)
        _밖 = 0
        for x in _덤 + _칸:
            k = (x["code"], x["인"])
            if k not in _본:
                _합.append(x)
                _본.add(k)
                _밖 += 1
        _묶D = {}
        for x in _합:
            _묶D.setdefault(x["인"], []).append(x)
        _키표 = {이: set() for 이 in R.업종규칙}
        for x in _합:
            _지금문 = 재무통과(x) and 대금통과(x) and (x.get("시총억") or 0) >= R.시총하한억
            _맞, _이 = R.업종규칙맞나(_산업.get(x["code"]), {
                "시총억": x.get("시총억"), "대금억": x.get("대금억"), "_지금문통과": _지금문,
                "잉여금비율": x.get("잉여금"), "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
            if _맞 and _이 in _키표:
                _키표[_이].add((x["code"], x["인"]))
        _업전체 = set()
        for 이 in _키표:
            _업전체 |= _키표[이]
        _키표["Ⓗ"] = _덤키 - _업전체              # 덤프에 있는데 업종이 아닌 것 = Ⓗ
        _키표["지금"] = _덤키 | _업전체            # 지금 실전 (Ⓗ + 업종 셋)
        _키표["옛"] = _키표["Ⓗ"] | _키표.get("의료·정밀기기", set())
        import time as _tD
        _덤때 = _tD.strftime("%m-%d %H:%M", _tD.localtime(os.path.getmtime(_덤프길)))
        print(f"     바탕 = {_덤프길.split(chr(92))[-1]} ({_덤때} · {len(_덤):,}건) + 칸 {len(_칸):,}건"
              f" · 보통 풀 밖에서 더한 사건 {_밖:,}건 · 합 {len(_합):,}건")
        print(f"     열쇠 — Ⓗ {len(_키표['Ⓗ']):,} · "
              + " · ".join(f"{이} {len(_키표[이]):,}" for 이 in R.업종규칙)
              + f"  ⇒ 지금 {len(_키표['지금']):,} · 옛(Ⓗ+의료) {len(_키표['옛']):,}")
        return _합, _묶D, {"시총하한": 0, "시총상한": 999999999, "대금하한": 0}, _키표

    # ══ ⭐⭐⭐ **PER — 갈래마다 1년에 몇 번 · 100만원이면 얼마** (2026-09-28 · 사용자 물음) ══
    if _ONLY == "PER" or "PER" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── PER ⭐⭐⭐ **한 번 걸릴 때 100만원을 넣으면 · 그런 일이 한 해 몇 번인가** ──")
        print("     100만원은 **단위**다 — 자산의 몇 %를 싣느냐와는 떼어 놓고 본다")
        print("=" * 122)
        _, _, _, _키표P2 = _D준비()   # 업종 갈래는 덬어 둔 열쇠로 가른다
        _업키P2 = {_이: _키표P2.get(_이, set()) for _이 in R.업종규칙}
        _기록P2 = []
        _rP2 = 시뮬(_c(_H), 기록=_기록P2)
        _날인P2 = {_d: _i for _i, _d in enumerate(날)}
        _사건맵P2 = {}
        for x in 사건:
            _사건맵P2[(x["code"], x["인"])] = x

        # ── 두 몫을 한 건으로 합친다 (주수 가중) ──
        _산것 = {}
        for _거래 in _기록P2:
            _k = (_거래[0], _거래[1])
            _주 = _거래[6] or 0
            _산것.setdefault(_k, [0.0, 0.0])
            _산것[_k][0] += _주 * _거래[4]
            _산것[_k][1] += _주
        _건들 = []
        for (_날짜, _code), (_합, _주) in _산것.items():
            if _주 <= 0:
                continue
            _x = _사건맵P2.get((_code, _날인P2.get(_날짜)))
            if _x is None:
                continue
            _건들.append((_날짜, _code, _합 / _주, _x))
        print(f"\n     11년 동안 산 것 — 몫 {len(_기록P2):,}줄 → **{len(_건들):,}건** (두 몫을 한 건으로 합쳤다)")

        # ── 갈래 판정 ──
        def _갈래들P2(x):
            _벌 = []
            try:
                if 섹터맞나(x):
                    _벌.append("섹터(가치사슬)")
            except Exception:  # noqa: BLE001
                pass
            try:
                if (R.변동성자사주_켬 and x.get("시장변동성") is not None
                        and x["시장변동성"] >= R.시장변동성문턱 and _자사H(x) >= 1):
                    _벌.append("변동성·자사주")
            except Exception:  # noqa: BLE001
                pass
            try:
                if x.get("볼린저") is not None and x.get("낙폭20") is not None \
                        and x["볼린저"] <= R.볼린저문턱 and x["낙폭20"] <= R.낙폭20문턱:
                    _벌.append("기존(볼린저·20일낙폭)")
            except Exception:  # noqa: BLE001
                pass
            try:
                if _시7(x) or _밑끝갈래(x):
                    _벌.append("시장(지수 눌림)")
            except Exception:  # noqa: BLE001
                pass
            # ⚠️ 업종은 **덬어 둔 열쇠**로 가른다 — 여기서 시총을 다시 보면 막개 ④가 띄절로 잡는다 (2026-09-28)
            for _이 in R.업종규칙:
                if (x["code"], x["인"]) in _업키P2.get(_이, ()):
                    _벌.append(f"업종 {_이}")
            return _벌 or ["(못 가림)"]

        _칸P2, _홀로 = {}, {}
        for _날짜, _code, _r, _x in _건들:
            _벌 = _갈래들P2(_x)
            for _g in _벌:
                _칸P2.setdefault(_g, []).append(_r)
            if len(_벌) == 1:
                _홀로.setdefault(_벌[0], []).append(_r)

        _해수 = 11.0
        print(f"\n     ① 갈래마다 (걸린 모든 매수 · 한 매수가 여러 갈래에 걸리면 양쪽에 센다)")
        print(f"     {'갈래':<22}{'11년 산 것':>11}{'한 해':>8}{'한 건 평균':>11}"
              f"{'100만이 되면':>14}{'한 해 기대':>14}{'이긴 비율':>10}")
        for _g in sorted(_칸P2, key=lambda z: -len(_칸P2[z])):
            _v = sorted(_칸P2[_g])
            _평 = sum(_v) / len(_v)
            _해건 = len(_v) / _해수
            print(f"     {_g:<22}{len(_v):>11}{_해건:>8.1f}{_평:>10.1f}%"
                  f"{1000000 * (1 + _평 / 100):>13,.0f}원{1000000 * (_평 / 100) * _해건:>13,.0f}원"
                  f"{sum(1 for z in _v if z > 0) / len(_v) * 100:>9.0f}%")
        _전 = sorted(z[2] for z in _건들)
        _평전 = sum(_전) / len(_전)
        print(f"     {'─ 전체 (겹침 없이)':<22}{len(_전):>11}{len(_전) / _해수:>8.1f}{_평전:>10.1f}%"
              f"{1000000 * (1 + _평전 / 100):>13,.0f}원{1000000 * (_평전 / 100) * (len(_전) / _해수):>13,.0f}원"
              f"{sum(1 for z in _전 if z > 0) / len(_전) * 100:>9.0f}%")

        print(f"\n     ② 평균만 보면 속는다 — 가운데값 · 가장 나쁜 한 건")
        print(f"     {'갈래':<22}{'가운데':>10}{'위 넷 중 하나':>14}{'아래 넷 중 하나':>15}{'가장 나쁜':>11}")
        for _g in sorted(_칸P2, key=lambda z: -len(_칸P2[z])):
            _v = sorted(_칸P2[_g])
            print(f"     {_g:<22}{_v[len(_v) // 2]:>9.1f}%{_v[len(_v) * 3 // 4]:>13.1f}%"
                  f"{_v[len(_v) // 4]:>14.1f}%{_v[0]:>10.1f}%")

        print(f"\n     ③ **그 갈래에만** 걸린 매수 (겹치지 않는 것)")
        print(f"     {'갈래':<22}{'11년':>8}{'한 해':>8}{'한 건 평균':>11}{'한 해 기대':>14}")
        for _g in sorted(_홀로, key=lambda z: -len(_홀로[z])):
            _v = sorted(_홀로[_g])
            _평 = sum(_v) / len(_v)
            print(f"     {_g:<22}{len(_v):>8}{len(_v) / _해수:>8.1f}{_평:>10.1f}%"
                  f"{1000000 * (_평 / 100) * (len(_v) / _해수):>13,.0f}원")

        print(f"\n     ④ 해마다 산 것")
        print(f"     {'해':<7}{'산 것':>8}{'평균 수익':>11}{'100만원씩이면 그 해':>20}")
        for _y in range(2016, 2027):
            _v = sorted(z[2] for z in _건들 if str(z[0])[:4] == str(_y))
            if not _v:
                continue
            _평 = sum(_v) / len(_v)
            print(f"     {_y:<7}{len(_v):>8}{_평:>10.1f}%{1000000 * (_평 / 100) * len(_v):>19,.0f}원")
        print("\n     ⚠️ 「한 해 기대」는 걸릴 때마다 100만원을 **새로** 넣는다는 뜻이다 (복리 아님)")
        print("     ⚠️ 실제로는 하루 자리와 현금이 있어 **다 못 산다** — 위 숫자는 기회의 크기다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SLOT — 무리마다 제 자리** (2026-09-28 · 사용자 아이디어) ══
    if _ONLY == "SLOT" or "SLOT" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SLOT ⭐⭐⭐ **「규모별로, 섹터별로 자리를 나누는 건 어때?」** ──")
        print("     ⚠️ 상대갭 **문턱**은 안 건드린다 — 2026-09-24 에 재서 다 졌다(91·74·88·57%)")
        print("     여기서 재는 것은 **자리**다")
        print("=" * 122)
        _밑S = 시뮬(_c(_H))
        print(f"\n     바탕(지금) — {_밑S['끝']:,.0f}원 · 낙폭 {_밑S['낙']:.1f}% · 산 것 {_밑S['산']}"
              f" · 하루 자리 {R.하루최대종목}")

        def _큰S(x):
            return (x.get("시총억") or 0) >= 2000

        def _섹S(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업S(x):
            try:
                _맞S, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_맞S)
            except Exception:  # noqa: BLE001
                return False

        def _줄S(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<40}{'(안 나왔다)':>18}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑S["끝"] and _r["낙"] >= _밑S["낙"] - 1.0) else "❌"
            print(f"     {이름:<40}{_r['끝']:>16,.0f}{_r['끝'] / _밑S['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _밑S['산']:>+7}  {_판}")
            return _r

        _머S = (f"     {'설정':<40}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>7}  판정")

        # ── Ⓐ 떼어두기 (총 6 고정 · 대형이 들어오면 소형이 밀린다) ──
        print(f"\n     Ⓐ **떼어두기** — 총 자리는 {R.하루최대종목}개 그대로, 그중 N개를 대형(2,000억↑)에")
        print("        ⚠️ 대형이 들어오면 **소형 하나가 밀려난다**")
        print(_머S)
        for _n in (1, 2, 3):
            _줄S(f"대형에 {_n}자리 떼어둠", {"큰자리": _n})

        # ── Ⓑ 따로 담기 (총합이 늘어난다 · 밀어내지 않는다) ──
        print(f"\n     Ⓑ **따로 담기** — 무리마다 제 자리. 총합이 {R.하루최대종목}개보다 **늘어난다**")
        print("        ⚠️ 소형을 밀어내지 않는다 — 기회를 놓치지 않는 쪽")
        print(_머S)
        for _n in (1, 2, 3):
            _줄S(f"대형 자리 {_n}개를 **더**", {"무리자리": [(_큰S, "대형", _n)]})
        for _n in (1, 2, 3):
            _줄S(f"섹터 갈래 자리 {_n}개를 **더**", {"무리자리": [(_섹S, "섹터", _n)]})
        for _n in (1, 2):
            _줄S(f"업종 갈래 자리 {_n}개를 **더**", {"무리자리": [(_업S, "업종", _n)]})
        _줄S("대형1 + 섹터1 을 더", {"무리자리": [(_큰S, "대형", 1), (_섹S, "섹터", 1)]})
        _줄S("대형2 + 섹터2 을 더", {"무리자리": [(_큰S, "대형", 2), (_섹S, "섹터", 2)]})
        _줄S("대형1 + 섹터1 + 업종1 을 더",
             {"무리자리": [(_큰S, "대형", 1), (_섹S, "섹터", 1), (_업S, "업종", 1)]})

        # ── ③ 그냥 자리를 늘리면? (견줌 — 무리와 상관없이) ──
        print("\n     ③ [견줌] 무리 상관없이 **그냥 자리를 늘리면** (같은 값이면 무리 나누기가 뜻이 없다)")
        print(_머S)
        for _n in (R.하루최대종목 + 1, R.하루최대종목 + 2, R.하루최대종목 + 3):
            _줄S(f"하루 자리 {_n}개 (통합)", {"하루상한": _n})

        # ── ⑤ **수익률이 아니라 돈** (2026-09-28 · 사용자) ──
        #    「수익율 보다 수익금이 중요해. 소형주가 수익율이 높아도 금액은 작고,
        #     대형주가 수익율은 낮아도 수익금이 높을테니까」
        #    ⇒ 맞다. 소형주는 **거래대금 1% 한도** 때문에 돈을 많이 못 넣는다.
        #       한 건에 얼마를 **실제로 넣었나**(주수 x 원시)와 **얼마를 벌었나**를 같이 본다
        def _돈표S(이름, 옵):
            _기S = []
            _r = 시뮬(_c(_H, **옵), 기록=_기S)
            if not _r:
                return
            _띠칸 = {}
            for _날, _코, _시총, _원시, _익률S, _청, _주 in _기S:
                _t = ("소형" if (_시총 or 0) < 2000 else
                      "중형" if (_시총 or 0) < 10000 else "대형")
                _넣 = (_주 or 0) * (_원시 or 0)
                _칸S = _띠칸.setdefault(_t, [0, 0.0, 0.0])
                _칸S[0] += 1
                _칸S[1] += _넣
                _칸S[2] += _넣 * (_익률S or 0) / 100.0
            print(f"\n        [{이름}] 끝 {_r['끝']:,.0f}원")
            print(f"        {'띠':<8}{'몫':>7}{'넣은 돈':>16}{'번 돈':>16}"
                  f"{'한 건 넣은 돈':>15}{'한 건 번 돈':>14}{'수익률':>9}")
            for _t in ("소형", "중형", "대형"):
                _칸S = _띠칸.get(_t)
                if not _칸S:
                    print(f"        {_t:<8}{0:>7}")
                    continue
                _n, _넣합, _번합 = _칸S
                print(f"        {_t:<8}{_n:>7}{_넣합:>16,.0f}{_번합:>+16,.0f}"
                      f"{_넣합 / _n:>15,.0f}{_번합 / _n:>+14,.0f}"
                      f"{_번합 / _넣합 * 100 if _넣합 else 0:>8.1f}%")

        print("\n     ⑤ ⭐⭐⭐ **수익률이 아니라 돈** — 띠마다 얼마를 넣었고 얼마를 벌었나")
        print("        소형주는 거래대금 1% 한도 때문에 **수익률이 높아도 돈을 많이 못 넣는다**")
        _돈표S("지금 (무리 나누기 없음)", {})
        _돈표S("대형 자리 1개를 더", {"무리자리": [(_큰S, "대형", 1)]})
        _돈표S("대형 자리 2개를 더", {"무리자리": [(_큰S, "대형", 2)]})
        _돈표S("섹터 자리 1개를 더", {"무리자리": [(_섹S, "섹터", 1)]})

        # ── ④ 이긴 것만 걷기 ──
        print("\n     ④ 바탕보다 나은 것만 **증분 걷기** (앞 2010~2020 / 뒤 2021~2026)")
        _후보들 = [("대형 자리 1개를 더", {"무리자리": [(_큰S, "대형", 1)]}),
                 ("섹터 자리 1개를 더", {"무리자리": [(_섹S, "섹터", 1)]}),
                 ("대형1 + 섹터1 을 더", {"무리자리": [(_큰S, "대형", 1), (_섹S, "섹터", 1)]})]
        for _름, _옵 in _후보들:
            _r = 시뮬(_c(_H, **_옵))
            if not _r or _r["끝"] < _밑S["끝"]:
                print(f"\n        [{_름}] — 바탕보다 못하다. 걷기 생략")
                continue
            print(f"\n        [{_름}]")
            _걷기찍기(_옵걷기(_옵), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **DAY — 그날 장 상태로 규칙 전체를 가른다** (2026-09-29) ══
    if _ONLY == "DAY" or "DAY" in _ONLY.split("+"):
        print("\\n" + "=" * 122)
        print("  ── DAY ⭐⭐⭐ **종목이 아니라 «날»을 가른다** ──")
        print("=" * 122)
        print("     두 판이 같은 곳을 가리켰다:")
        print("        AXIS  — 그날 장 상태가 가장 크게 갈리는 축 (크게 빠진 날 5.63% vs 평온 0.84% · 7배)")
        print("        B129  — 대형 재료 1위가 **시장낙폭 ≤ -15%** (앞 87.3% · 뒤 64.4%)")
        print("     대형에만 씌우면 앞 기간 0건이라 표본이 없다. **날을 가르면** 소형까지 들어온다")

        _밑D3 = 시뮬(_c(_H))
        print(f"\\n     바탕(지금) — {_밑D3['끝']:,.0f}원 · 낙폭 {_밑D3['낙']:.1f}% · 산 것 {_밑D3['산']}")

        def _빠진D(문):
            def _f(x, _t=문):
                _v = x.get("시장낙폭")
                return _v is not None and _v <= _t
            return _f

        def _평온D(문):
            def _f(x, _t=문):
                _v = x.get("시장낙폭")
                return _v is not None and _v > _t
            return _f

        _이긴D3 = []

        def _줄D3(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<50}{'(안 나왔다)':>16}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑D3["끝"] and _r["낙"] >= _밑D3["낙"] - 1.0) else (
                "△" if _r["끝"] >= _밑D3["끝"] else "❌")
            print(f"     {이름:<50}{_r['끝']:>16,.0f}{_r['끝'] / _밑D3['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _밑D3['산']:>+7}  {_판}")
            if _r["끝"] >= _밑D3["끝"]:
                _이긴D3.append((이름, 옵, _r))
            return _r

        _머D3 = f"     {'설정':<50}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>7}  판정"

        print("\\n     ① **크게 빠진 날**엔 더 산다 (자리를 더 준다)")
        print(_머D3)
        for _t in (-15.0, -10.0, -7.0):
            for _n in (2, 4):
                _줄D3(f"시장낙폭 ≤ {_t:g}% 인 날 자리 {_n}개 더",
                      {"무리자리": [(_빠진D(_t), "빠진날", _n)]})

        print("\\n     ② **평온한 날**엔 문턱을 눅인다 (기회가 8,251건 중 69건뿐이었다)")
        print(_머D3)
        for _문 in (-3.2, -5.0):
            for _갭 in (-2.5, -2.0, -1.5):
                _줄D3(f"시장낙폭 > {_문:g}% 인 날 상대갭 {_갭:g}%p",
                      {"무리갭": [(_평온D(_문), "평온", _갭)]})

        print("\\n     ③ 둘 다 — 빠진 날엔 더 사고, 평온한 날엔 눅인다")
        print(_머D3)
        for _t, _n, _문, _갭 in ((-10.0, 2, -3.2, -2.0), (-10.0, 4, -3.2, -2.0),
                                (-15.0, 4, -5.0, -2.5)):
            _줄D3(f"빠진날({_t:g}%) 자리+{_n} · 평온({_문:g}%) 갭{_갭:g}",
                  {"무리자리": [(_빠진D(_t), "빠진날", _n)],
                   "무리갭": [(_평온D(_문), "평온", _갭)]})

        print("\\n     ④ 바탕을 넘은 것만 **증분 걷기**")
        if not _이긴D3:
            print("        바탕을 넘은 것이 **하나도 없다**")
        for _nmD3, _opD3, _rD3 in sorted(_이긴D3, key=lambda z: -z[2]["끝"])[:5]:
            print(f"\\n        [{_nmD3}]  ({_rD3['끝'] / _밑D3['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_opD3), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **MONEY — 낙폭은 안 본다, 끝자산만** (2026-09-29 · 사용자 지시) ══
    if _ONLY == "MONEY" or "MONEY" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── MONEY ⭐⭐⭐ **끝자산만 본다** ──")
        print("=" * 122)
        print("     사용자: 「자동매수·매도 권한을 주면 **낙폭을 견디는 건 상관없고**")
        print("              결국 **끝자산(수익금)만** 높으면 되니까 지금 규칙이랑 다를 것 같은데?」")
        print("     지금 판정은 돈과 낙폭을 같이 본다 — 돈이 늘어도 낙폭이 1%p 넘게")
        print("     나빠지면 버렸다(△). 낙폭을 빼면 그 △ 들이 전부 살아난다.")
        print("     ⚠️ 낙폭은 **적기만** 한다 — 버리는 기준이 아니라 대가를 보여주는 칸이다")
        print("     ⚠️ 걷기는 그대로 돌린다 — 앞에서 좋고 뒤에서 무너지는 건 낙폭과 무관하게 가짜다")

        _밑M = 시뮬(_c(_H))
        print(f"\n     바탕 — {_밑M['끝']:,.0f}원 · 낙폭 {_밑M['낙']:.1f}% · 산 것 {_밑M['산']}")

        _이긴M = []
        _머M = (f"     {'설정':<32}{'끝 자산':>18}{'바탕의%':>9}"
                f"{'낙폭':>9}{'산 것':>7}{'돈÷낙폭':>9}")

        def _줄M(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<32}{'(안 나왔다)':>18}")
                return None
            _배 = _r["끝"] / _밑M["끝"] * 100
            _효 = (_r["끝"] / 1e8) / abs(_r["낙"]) if _r["낙"] else 0
            print(f"     {이름:<32}{_r['끝']:>18,.0f}{_배:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_효:>9.2f}"
                  + ("  ⭐" if _r["끝"] > _밑M["끝"] else "  ❌"))
            if _r["끝"] > _밑M["끝"]:
                _이긴M.append((이름, 옵, _r))
            return _r

        print("\n     ① **비중** — 한 종목에 자산의 몇 %. 지금 20%")
        print(_머M)
        for _v in (0.10, 0.15, 0.25, 0.30, 0.40, 0.50, 0.70, 1.00):
            _줄M(f"비중 {_v * 100:g}%", {"비중": _v})

        print("\n     ② **거래대금 한도** — 지금 1% (코드에 근거가 없던 그 상수)")
        print(_머M)
        for _v in (0.005, 0.02, 0.05, 0.10, 0.20, 1.00):
            _줄M(f"대금 한도 {_v * 100:g}%", {"대금비율": _v})

        print("\n     ③ **하루 자리 수** — 지금 rule_def 가 정한다(6)")
        print(_머M)
        for _v in (2, 3, 4, 8, 10, 12, 20):
            _줄M(f"하루 {_v}자리", {"하루상한": _v})

        print("\n     ④ **비중 x 대금 한도 격자** — 둘은 같이 움직인다")
        print("        따로 재면 어긋난다 [[compare-candidates-before-adopting]]")
        print(_머M)
        for _b in (0.20, 0.40, 0.70):
            for _d in (0.01, 0.05, 0.20):
                if abs(_b - 0.20) < 1e-9 and abs(_d - 0.01) < 1e-9:
                    continue
                _줄M(f"비중 {_b * 100:g}% x 한도 {_d * 100:g}%",
                     {"비중": _b, "대금비율": _d})

        print("\n     ⑤ **거래 비용** — B139 에서 못 쟀다 (캐시 열쇠에 `_비용` 이 없었다)")
        print("        열쇠를 고쳤으니 이제 진짜로 잰다. 값이 다 같으면 **또 못 잰 것**이다")
        print(_머M)
        _원비용M = _비용
        try:
            for _배M in (0.0, 0.5, 2.0, 3.0, 5.0):
                globals()["_비용"] = _원비용M * _배M
                _r = 시뮬(_c(_H))
                if _r:
                    print(f"     {f'비용 {_배M:g}배 ({_원비용M * _배M:.3f}%)':<32}"
                          f"{_r['끝']:>18,.0f}{_r['끝'] / _밑M['끝'] * 100:>8.0f}%"
                          f"{_r['낙']:>8.1f}%{_r['산']:>7}"
                          + ("  ⭐" if _r["끝"] > _밑M["끝"] else "  ❌"))
        finally:
            globals()["_비용"] = _원비용M

        print("\n     ⑥ **돈이 가장 많은 다섯** — 고친 걷기")
        print("        ⚠️ 낙폭으로는 안 거른다. 하지만 **앞뒤 둘 다 벌어야** 진짜다")
        if not _이긴M:
            print("        바탕을 넘은 것이 **하나도 없다** — 지금 값이 돈으로도 제일 낫다")
        for _름M, _옵M, _r in sorted(_이긴M, key=lambda z: -z[2]["끝"])[:5]:
            print(f"\n        [{_름M}]  {_r['끝']:,.0f}원 "
                  f"({_r['끝'] / _밑M['끝'] * 100:.0f}%) · 낙폭 {_r['낙']:.1f}%")
            _걷기찍기(_옵걷기(_옵M), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **LIVE — 지금 실전 규칙을 바탕으로** (2026-09-29 밤) ══
    if _ONLY == "LIVE" or "LIVE" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── LIVE ⭐⭐⭐ **지금 실전 규칙이 바탕** ──")
        print("=" * 122)
        print("     판의 바탕(_c(_H))은 오늘 반영한 셋을 안 읽었다 — 섹터 자리 2 · 업종 -1.5%p · 악재 감자·유상증자")
        print("     B136·B137·B139 는 **오늘 아침 규칙**과 견줬다. 여기서 실전 바탕으로 다시 잰다")
        print(f"     소형 갈래 상한(크기통과) = {_규칙크기상한:,.0f}억"
              + ("   ⭐ RULE_HI 로 바꾼 판" if os.environ.get("RULE_HI") else "   (지금 실전 그대로)"))

        def _섹L(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업L(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        def _바구니L(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        # ── 악재표를 「감자·유상증자」만으로 (AB2 와 같은 방법 · 끝나면 되돌린다) ──
        _원표L = {k: dict(v) for k, v in _악재표.items()}
        _새표L = {}
        import glob as _gL
        for _fL in sorted(_gL.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dL = os.path.basename(_fL)[:8]
            try:
                _jL = json.load(io.open(_fL, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hL = {}
            for _칸L in ("챙길공시", "그밖의공시"):
                for _xL in (_jL.get(_칸L) or []):
                    _cL = str(_xL.get("종목코드") or "")
                    _제L = str(_xL.get("공시명") or "")
                    # ⭐ 실전(bad_news_check)과 똑같이 — **반대말이 섞이면 안 판다**
                    #    (「유상증자 철회」는 좋은 소식이다. B135·AB2 는 이걸 안 걸렀다)
                    _반대L = any(w in _제L for w in ("해제", "취소", "철회", "종결", "기각"))
                    if _cL and ("감자" in _제L or "유상증자" in _제L) and not _반대L:
                        _hL[_cL] = _hL.get(_cL, 0) + 1
            if _hL:
                _새표L[_dL] = _hL

        # ⭐ 2026-09-30 — 가치사슬 바구니(원전 기자재 -2.0%p · 자리 1)도 실전이다 (rule_def.바구니전용)
        _실전L = {"무리자리": [(_섹L, "섹터", R.섹터전용자리)]
                             + [(_바구니L(_n), _n, _v["자리"]) for _n, _v in getattr(R, "바구니전용", {}).items()],
                  "무리갭": [(_업L, "업종", R.업종전용상대갭)]
                            + [(_바구니L(_n), _n, _v["상대갭"]) for _n, _v in getattr(R, "바구니전용", {}).items()],
                  "재평가": "악재",
                  "시총상한": 999999}     # ⚠️ RULE_HI 를 줘도 섹터 갈래는 열어 둔다

        def _더L(옵):
            _r = {k: (list(v) if isinstance(v, list) else v) for k, v in _실전L.items()}
            for _k, _v in 옵.items():
                if _k in ("무리자리", "무리갭"):
                    _r[_k] = _r.get(_k, []) + list(_v)
                else:
                    _r[_k] = _v
            return _r

        try:
            _옛바L = 시뮬(_c(_H))                       # 옛 악재표로 — 오늘 아침 규칙
            _악재표.clear()
            _악재표.update(_새표L)
            # (판 번호는 _판세는표 가 clear·update 때 저절로 올린다 — 캐시 열쇠가 바뀐다)
            _바L = 시뮬(_c(_H, **_실전L))
            print(f"\n     ⓪ 바탕 견줌")
            print(f"        오늘 아침 규칙  {_옛바L['끝']:>16,.0f}원 · 낙폭 {_옛바L['낙']:.1f}% · 산 것 {_옛바L['산']}")
            print(f"        **지금 실전**    {_바L['끝']:>16,.0f}원 · 낙폭 {_바L['낙']:.1f}% · 산 것 {_바L['산']}"
                  f"   ({_바L['끝'] / _옛바L['끝'] * 100:.0f}%)")
            print("        (B135 에서 +A+B 는 111% · 낙폭 -6.3% 였다 — 가까우면 실전 바탕이 맞게 선 것이다)")

            _후L = [("섹터 갈래 3,000억 캡 (B139 가 실제로 잰 것)", {"시총상한": 3000.0})]
            for _nm in ("전력 인프라/변압기", "원전 기자재"):
                if _nm in R.섹터규칙:
                    _fL2 = _바구니L(_nm)
                    _후L.append((f"[{_nm}] -2.0%p + 자리 1",
                                 {"무리갭": [(_fL2, _nm, -2.0)], "무리자리": [(_fL2, _nm, 1)]}))

            print(f"\n     ① 실전 바탕 위에 하나씩 — 돈 · 낙폭 · 산 것 · 고친 걷기")
            for _라L, _옵L in _후L:
                _rL = 시뮬(_c(_H, **_더L(_옵L)))
                if not _rL:
                    print(f"\n        [{_라L}]  (안 나왔다)")
                    continue
                print(f"\n        [{_라L}]  {_rL['끝']:,.0f}원 ({_rL['끝'] / _바L['끝'] * 100:.0f}%)"
                      f" · 낙폭 {_바L['낙']:.1f}% → {_rL['낙']:.1f}% · 산 것 {_바L['산']} → {_rL['산']}")
                _줄L, _시a, _시b = [], None, None
                for _라w, _시w, _끝w in (("앞 2010~2020", "2010", "2020"),
                                        ("뒤 2021~2026", "2021", "2026")):
                    _aw = 시뮬(_c(_H, **_실전L), 시작년=_시w, 끝년=_끝w, 시드=_시a)
                    _bw = 시뮬(_c(_H, **_더L(_옵L)), 시작년=_시w, 끝년=_끝w, 시드=_시b)
                    if not _aw or not _bw:
                        continue
                    _dw = (_bw["끝"] / _aw["끝"] - 1) * 100 if _aw["끝"] > 0 else 0
                    _줄L.append((_라w, _aw, _bw, _dw))
                    _시a, _시b = _aw["끝"], _bw["끝"]
                _걷기찍기(_줄L, 들여="          ")

            # ══ ② 옛 바탕으로 잰 결론 — 실전 바탕에서 다시 ══
            print("\n     ② 옛 바탕(오늘 아침 규칙)으로 잰 결론 — **실전 바탕에서 다시**")
            print(f"        {'무엇':<34}{'끝 자산':>16}{'실전의%':>9}{'낙폭':>8}{'산 것':>7}")

            def _한줄L(라, r):
                if not r:
                    print(f"        {라:<34}{'(안 나왔다)':>16}")
                    return
                print(f"        {라:<34}{r['끝']:>16,.0f}{r['끝'] / _바L['끝'] * 100:>8.0f}%"
                      f"{r['낙']:>7.1f}%{r['산']:>7}")

            try:
                _재무옵.clear()
                _재무옵.update({"잉여금": None, "부채": None, "흑자": False, "대금": 0.0})
                _한줄L("재무 문 넷 다 끄기 (B137)", 시뮬(_c(_H, **_실전L)))
            finally:
                _재무옵.clear()
            for _v in (0.005, 0.02):
                _한줄L(f"거래대금 한도 {_v * 100:g}% (B136)", 시뮬(_c(_H, **_더L({"대금비율": _v}))))
            _종L = None     # 아래 try 가 중간에 터져도 뒤에서 읽을 수 있게
            _원살L, _원비L, _원이L = _살때, _비용, _이자
            try:
                globals()["_살때"] = "종가"
                _종L = 시뮬(_c(_H, **_실전L))
                _한줄L("사는 값 = 종가 (B140)", _종L)
                globals()["_살때"] = _원살L
                globals()["_비용"] = _원비L * 2
                _한줄L("거래 비용 2배 (B140)", 시뮬(_c(_H, **_실전L)))
                globals()["_비용"] = _원비L
                globals()["_이자"] = 0.0
                _한줄L("현금 이자 0% (B140)", 시뮬(_c(_H, **_실전L)))
            finally:
                globals()["_살때"], globals()["_비용"], globals()["_이자"] = _원살L, _원비L, _원이L
            if _종L and _종L["끝"] > _바L["끝"]:
                print("\n        [사는 값 = 종가] 이 실전보다 낫다 — 걷기 (앞뒤마다 시가 한 번 · 종가 한 번)")
                _줄Z, _sa, _sb = [], None, None
                try:
                    for _라w, _시w, _끝w in (("앞 2010~2020", "2010", "2020"),
                                            ("뒤 2021~2026", "2021", "2026")):
                        globals()["_살때"] = "시가"
                        _aw = 시뮬(_c(_H, **_실전L), 시작년=_시w, 끝년=_끝w, 시드=_sa)
                        globals()["_살때"] = "종가"
                        _bw = 시뮬(_c(_H, **_실전L), 시작년=_시w, 끝년=_끝w, 시드=_sb)
                        if _aw and _bw:
                            _줄Z.append((_라w, _aw, _bw,
                                         (_bw["끝"] / _aw["끝"] - 1) * 100 if _aw["끝"] > 0 else 0))
                            _sa, _sb = _aw["끝"], _bw["끝"]
                finally:
                    globals()["_살때"] = _원살L
                _걷기찍기(_줄Z, 들여="          ")

            # ══ ③ 화면 성적표 후보 ══
            print("\n     ③ **화면 성적표 후보** — 지금 화면(rule-capital.json 9/28)은 오늘 아침 규칙의 숫자다")
            print(f"        끝 자산 {_바L['끝']:,.0f}원 · 연평균 {_바L['연']:.2f}% · "
                  f"낙폭 {_바L['낙']:.1f}% · 산 것 {_바L['산']}")
            try:
                import datetime as _dtL
                _몫L = {"만든날": _dtL.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "출처": "gate7_lab LIVE 절 — 실전 바탕(섹터 자리 2 · 업종 -1.5%p · "
                                "악재 감자·유상증자(반대말 뺌)) · 제약 있는 판",
                        "소형상한억": _규칙크기상한,
                        "시작자산": 5000000.0, "연평균": round(_바L["연"], 2),
                        "계좌낙폭": round(_바L["낙"], 1), "끝자산": round(_바L["끝"]),
                        "산것": _바L["산"]}
                _밖L = os.path.join(O._DATA, "_labs",
                                    "rule-capital_실전후보" + ("_RULEHI" if os.environ.get("RULE_HI") else "")
                                    + ".json")
                io.open(_밖L, "w", encoding="utf-8").write(json.dumps(_몫L, ensure_ascii=False, indent=1))
                print(f"        → 후보로 남겼다: {os.path.basename(_밖L)} (실전 파일은 안 건드렸다)")
            except Exception as _eL:  # noqa: BLE001
                print(f"        ⚠️ 후보 파일을 못 남겼다: {type(_eL).__name__}")
        finally:
            _악재표.clear()
            _악재표.update(_원표L)
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **CASH — 안 쓴 현금 이자** (2026-09-29) ══
    if _ONLY == "CASH" or "CASH" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── CASH ⭐⭐⭐ **안 쓴 현금 이자 — 연 2.5% 는 맞나** ──")
        print("=" * 122)
        print("     시뮬은 노는 현금에 매일 연 2.5% 를 붙여 왔다 (손으로 박힌 값 · 한 번도 안 흔듦).")
        print("     실제 계좌가 현금에 이자를 안 주면 시뮬이 부풀려져 있고, CMA 3%대면 보수적이다.")
        _줄C = []
        try:
            for _v in (0.0, 0.01, 0.025, 0.035):
                globals()["_이자"] = _v
                _rC = 시뮬(_c(_H))
                if _rC:
                    _줄C.append((_v, _rC))
        finally:
            globals()["_이자"] = 0.025
        _바C = next((r for v, r in _줄C if abs(v - 0.025) < 1e-9), None)
        print(f"\n     {'이자 (연)':<16}{'끝 자산':>18}{'2.5%의%':>9}{'낙폭':>9}{'산 것':>7}")
        for _v, _rC in _줄C:
            print(f"     {f'{_v * 100:g}%' + ('  (지금)' if abs(_v - 0.025) < 1e-9 else ''):<16}"
                  f"{_rC['끝']:>18,.0f}"
                  f"{(_rC['끝'] / _바C['끝'] * 100 if _바C else 0):>8.0f}%"
                  f"{_rC['낙']:>8.1f}%{_rC['산']:>7}")
        if len({round(r["끝"]) for _, r in _줄C}) == 1:
            print("     🔴 **값이 전부 같다 — 손잡이가 안 먹은 것이다.** 결과를 믿지 마라")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **BUYAT2 — 시가에 살까, 종가에 살까** (2026-09-29) ══
    if _ONLY == "BUYAT2" or "BUYAT2" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── BUYAT2 ⭐⭐⭐ **사는 값 — 시가 vs 종가** ──")
        print("=" * 122)
        print("     규칙 전체가 「08:55 에 보고 09:00 **시가**에 산다」 위에 서 있다. 한 번도 안 흔들었다.")
        print("     같은 종목·같은 날을 **사는 값만** 바꿔 돌린다 (시가 vs 그날 장 마감 종가).")
        print("     ⚠️ 종가에 사면 **산 날 고가에는 못 판다** — 다음 날부터 본다 (미래를 안 보게)")
        print("     · 시가가 낫다 → 지금이 맞다")
        print("     · 종가가 낫다 → **아침에 서두를 이유가 없다** (운용이 통째로 쉬워진다)")
        try:
            globals()["_살때"] = "시가"
            _시B = 시뮬(_c(_H))
            globals()["_살때"] = "종가"
            _종B = 시뮬(_c(_H))
        finally:
            globals()["_살때"] = "시가"
        _머B = f"     {'사는 값':<16}{'끝 자산':>18}{'시가의%':>9}{'낙폭':>9}{'산 것':>7}"
        print("\n     ① 11년 한 번에")
        print(_머B)
        for _라B, _rB in (("시가 (지금)", _시B), ("종가", _종B)):
            if _rB:
                print(f"     {_라B:<16}{_rB['끝']:>18,.0f}{_rB['끝'] / _시B['끝'] * 100:>8.0f}%"
                      f"{_rB['낙']:>8.1f}%{_rB['산']:>7}")
        if _시B and _종B and _시B["끝"] == _종B["끝"] and _시B["산"] == _종B["산"]:
            print("     🔴 **두 값이 완전히 같다 — 손잡이가 안 먹은 것이다.** 결과를 믿지 마라")

        print("\n     ② 걷기 — 앞뒤마다 시가 한 번 · 종가 한 번 (뒤는 앞이 끝낸 자산으로 잇는다)")
        print("        ⚠️ `_옵걷기` 는 못 쓴다 — `_살때` 는 옵이 아니라 전역이라 자기 자신과 견준다")
        _줄B, _시드시, _시드종 = [], None, None
        try:
            for _라B2, _시B2, _끝B2 in (("앞 2010~2020", "2010", "2020"),
                                   ("뒤 2021~2026", "2021", "2026")):
                globals()["_살때"] = "시가"
                _aB2 = 시뮬(_c(_H), 시작년=_시B2, 끝년=_끝B2, 시드=_시드시)
                globals()["_살때"] = "종가"
                _bB2 = 시뮬(_c(_H), 시작년=_시B2, 끝년=_끝B2, 시드=_시드종)
                if not _aB2 or not _bB2:
                    continue
                _dB2 = (_bB2["끝"] / _aB2["끝"] - 1) * 100 if _aB2["끝"] > 0 else 0
                _줄B.append((_라B2, _aB2, _bB2, _dB2))
                _시드시, _시드종 = _aB2["끝"], _bB2["끝"]
        finally:
            globals()["_살때"] = "시가"
        _걷기찍기(_줄B, 들여="        ")
        print("        (왼쪽 = 시가 · 오른쪽 = 종가)")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **BUYAT — 시총 상한 · 거래 비용을 흔든다** (2026-09-29) ══
    if _ONLY == "BUYAT" or "BUYAT" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── BUYAT ⭐⭐⭐ **안 흔든 가정 나머지** ──")
        print("=" * 122)
        print("     audit_assumptions 가 찾은 11개 중 재무 문 넷(B137)·거래대금(B136)은 쟀다.")
        print("     남은 것: **시총 상한 2,000억**(판 1개뿐) · **거래 비용** · **1주 미만**")
        print("     ⚠️ 「사는 값(시가 vs 종가)」은 시뮬 깊은 곳에 박혀 있어 따로 뗀다 — 다음 판")

        _밑U = 시뮬(_c(_H))
        print(f"\n     바탕 — {_밑U['끝']:,.0f}원 · 낙폭 {_밑U['낙']:.1f}% · 산 것 {_밑U['산']}")

        _이긴U = []

        def _줄U(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<34}{'(안 나왔다)':>16}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑U["끝"] and _r["낙"] >= _밑U["낙"] - 1.0) else (
                "△" if _r["끝"] >= _밑U["끝"] else "❌")
            print(f"     {이름:<34}{_r['끝']:>16,.0f}{_r['끝'] / _밑U['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _밑U['산']:>+8}  {_판}")
            if _r["끝"] >= _밑U["끝"]:
                _이긴U.append((이름, 옵, _r))
            return _r

        _머U = f"     {'설정':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>8}  판정"

        print("\n     ① **시총 상한** — 지금 2,000억 (섹터 갈래는 예외)")
        print("        ⚠️ 판 1개뿐이라 사실상 안 흔들어 본 것이다")
        print(_머U)
        for _v in (1000.0, 1500.0, 3000.0, 5000.0, 10000.0, 999999.0):
            _줄U(f"시총 상한 {_v:,.0f}억" + (" (없음)" if _v > 99999 else ""),
                 {"시총상한": _v})

        print("\n     ② **시총 하한** — 지금 300억")
        print(_머U)
        for _v in (0.0, 100.0, 200.0, 500.0, 1000.0):
            _줄U(f"시총 하한 {_v:,.0f}억", {"시총하한": _v})

        print("\n     ③ **거래 비용** — 지금 값을 배로 흔든다")
        print("        비용이 두 배여도 서면 튼튼한 것이고, 무너지면 지금이 아슬아슬한 것이다")
        print(_머U)
        try:
            _원비용 = _비용
            for _배 in (0.0, 0.5, 2.0, 3.0):
                globals()["_비용"] = _원비용 * _배
                _r = 시뮬(_c(_H))
                _판 = "⭐" if _r and _r["끝"] >= _밑U["끝"] else "❌"
                if _r:
                    print(f"     {f'비용 {_배:g}배 ({_원비용 * _배:.3f}%)':<34}{_r['끝']:>16,.0f}"
                          f"{_r['끝'] / _밑U['끝'] * 100:>8.0f}%{_r['낙']:>8.1f}%"
                          f"{_r['산']:>7}{_r['산'] - _밑U['산']:>+8}  {_판}")
            globals()["_비용"] = _원비용
        except Exception as _eU:  # noqa: BLE001
            print(f"     ⚠️ 비용을 못 흔들었다: {type(_eU).__name__} — 지역 변수라 밖에서 못 바꾼다")

        print("\n     ④ 바탕을 넘은 것만 **고친 걷기**")
        if not _이긴U:
            print("        바탕을 넘은 것이 **하나도 없다** — 지금 값이 제일 낫다")
        for _름U, _옵U, _r in sorted(_이긴U, key=lambda z: -z[2]["끝"])[:5]:
            print(f"\n        [{_름U}]  ({_r['끝'] / _밑U['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_옵U), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **FIN — 재무 문 넷을 흔든다 (잉여금·부채·흑자·대금하한)** (2026-09-29) ══
    if _ONLY == "FIN" or "FIN" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── FIN ⭐⭐⭐ **왜 잉여금 30% · 부채 80% · 흑자 · 대금 1억 인가** ──")
        print("=" * 122)
        print("     가정 21개 중 11개를 한 번도 안 흔들었다. 그중 **재무 문 넷은 손잡이조차 없었다.**")
        print("     대형 전용 규칙(B132)에선 「재무 문이 아무 효과 없음」이 나왔는데 소형에선 안 재봤다")
        print(f"     지금 값 — 잉여금 ≥{R.잉여금하한:g}% · 부채 ≤{R.부채상한:g}% · 흑자 요구 · 대금 ≥{R.대금하한억:g}억")

        _지금옵F = {"잉여금": R.잉여금하한, "부채": R.부채상한, "흑자": True,
                   "대금": R.대금하한억}

        def _재기F(이름, 옵):
            _재무옵.clear()
            _재무옵.update(옵)
            try:
                _r = 시뮬(_c(_H))
            finally:
                pass
            return 이름, dict(옵), _r

        # 바탕 — 지금 값을 **원자료로 다시 판정**해서 낸다 (미리 계산된 값과 같은지 확인)
        _이름F, _옵F, _바탕F = _재기F("⓪ 지금 값 (원자료로 다시)", _지금옵F)
        _재무옵.clear()
        _옛바탕F = 시뮬(_c(_H))
        print(f"\n     ⓪ 바탕 대조 — 미리 계산된 값 {_옛바탕F['끝']:,.0f}원 ·"
              f" 원자료로 다시 {_바탕F['끝']:,.0f}원"
              + ("   ✅ 같다" if abs(_바탕F['끝'] - _옛바탕F['끝']) / max(_옛바탕F['끝'], 1) < 0.02
                 else "   ⚠️ **다르다 — 원자료 판정이 미리 계산된 것과 어긋난다**"))

        _벌F = [("⓪ 지금 값", _지금옵F)]
        for _v in (None, 0.0, 10.0, 20.0, 40.0, 50.0):
            _벌F.append((f"잉여금 {'없음' if _v is None else f'≥{_v:g}%'}",
                        dict(_지금옵F, 잉여금=_v)))
        for _v in (None, 200.0, 150.0, 100.0, 60.0, 40.0):
            _벌F.append((f"부채 {'없음' if _v is None else f'≤{_v:g}%'}",
                        dict(_지금옵F, 부채=_v)))
        _벌F.append(("흑자 안 따짐", dict(_지금옵F, 흑자=False)))
        for _v in (0.0, 0.5, 3.0, 10.0, 50.0):
            _벌F.append((f"대금 ≥{_v:g}억", dict(_지금옵F, 대금=_v)))
        _벌F.append(("⭐ 재무 문 **넷 다 없음**",
                    {"잉여금": None, "부채": None, "흑자": False, "대금": 0.0}))
        _벌F.append(("재무만 없음 (대금은 1억)",
                    {"잉여금": None, "부채": None, "흑자": False, "대금": 1.0}))

        print(f"\n     {'설정':<26}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>8}  판정")
        _이긴F = []
        for _름F, _옵F2 in _벌F:
            _, _, _r = _재기F(_름F, _옵F2)
            if not _r:
                continue
            _판 = "⭐" if (_r["끝"] >= _바탕F["끝"] and _r["낙"] >= _바탕F["낙"] - 1.0) else (
                "△" if _r["끝"] >= _바탕F["끝"] else "❌")
            print(f"     {_름F:<26}{_r['끝']:>16,.0f}{_r['끝'] / _바탕F['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _바탕F['산']:>+8}  {_판}")
            if _r["끝"] >= _바탕F["끝"] and not _름F.startswith("⓪"):
                _이긴F.append((_름F, dict(_옵F2), _r))
        _재무옵.clear()

        print("\n     ③ 바탕을 넘은 것만 **앞뒤로 갈라** 본다")
        if not _이긴F:
            print("        바탕을 넘은 것이 **하나도 없다** — 지금 재무 문이 제일 낫다는 뜻이다")
        for _름F, _옵F2, _r in sorted(_이긴F, key=lambda z: -z[2]["끝"])[:6]:
            _재무옵.clear()
            _재무옵.update(_옵F2)
            _a = 시뮬(_c(_H), 시작년="2010", 끝년="2020")
            _b = 시뮬(_c(_H), 시작년="2021", 끝년="2026", 시드=(_a["끝"] if _a else None))
            _재무옵.clear()
            _a0 = 시뮬(_c(_H), 시작년="2010", 끝년="2020")
            _b0 = 시뮬(_c(_H), 시작년="2021", 끝년="2026", 시드=(_a0["끝"] if _a0 else None))
            print(f"\n        [{_름F}]  ({_r['끝'] / _바탕F['끝'] * 100:.0f}%)")
            for _라, _z0, _z1 in (("앞 2010~2020", _a0, _a), ("뒤 2021~2026", _b0, _b)):
                if _z0 and _z1:
                    _d = (_z1["끝"] / _z0["끝"] - 1) * 100 if _z0["끝"] > 0 else 0
                    print(f"          {_라}: {_z0['끝']:,.0f} → {_z1['끝']:,.0f}  {_d:+.1f}%"
                          f"  (낙폭 {_z0['낙']:.1f}% → {_z1['낙']:.1f}%"
                          f" · 산 것 {_z0['산']} → {_z1['산']})")
            _둘F = (_a and _b and _a0 and _b0 and _a["끝"] > _a0["끝"] and _b["끝"] > _b0["끝"])
            print(f"          ⇒ {'✅ 앞뒤 둘 다 +' if _둘F else '❌ 앞뒤가 갈린다'}")
        _재무옵.clear()
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **LIQ — 거래대금 1% 한도를 흔든다** (2026-09-29 · 사용자 물음) ══
    if _ONLY == "LIQ" or "LIQ" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── LIQ ⭐⭐⭐ **1% 에 근거가 없다 — 흔들어 본다** ──")
        print("=" * 122)
        print("     코드를 뒤졌는데 **왜 1% 인지 적힌 데가 한 군데도 없다.**")
        print("     그런데 오늘 결론이 이 숫자 하나에 달려 있다:")
        print("        · 너무 빡빡하면 → 소형이 부당하게 손해 보는 것")
        print("        · 너무 헐거우면 → 소형 52배가 뻥튀기인 것")
        print("     ⚠️ 제한을 **푼 적은 없다.** 시드만 바꿨고 1% 는 켠 채였다")

        def _중L(x):
            return (2000 <= (x.get("시총억") or 0) < 10000 and 재무통과(x) and 대금통과(x)
                    and x.get("시장낙폭") is not None and x["시장낙폭"] <= -15)

        def _대L(x):
            return ((x.get("시총억") or 0) >= 10000 and 재무통과(x) and 대금통과(x)
                    and x.get("낙40") is not None and x["낙40"] <= -30)

        _중옵L = dict(상대갭=-1.0, 하루상한=4, 비중=0.20, 시총하한=0, 시총상한=999999)
        _대옵L = dict(상대갭=-1.0, 하루상한=4, 비중=0.30, 시총하한=0, 시총상한=999999)

        _날인L = {_d: _i for _i, _d in enumerate(날)}
        _사건맵L = {}
        for _xL in 사건:
            _사건맵L[(_xL["code"], _xL["인"])] = _xL

        print("\n     ① **한도 x 시드** — 1등이 누구인가")
        print(f"        {'한도':>7}{'시드':>15}{'소형 배':>10}{'중형 배':>10}{'대형 배':>10}{'1등':>8}")
        for _비L, _름L in ((0.005, "0.5%"), (0.01, "1%"), (0.02, "2%"),
                           (0.05, "5%"), (0.10, "10%"), (None, "없음")):
            for _시L in (5_000_000, 100_000_000, 300_000_000, 1_000_000_000):
                _옵공 = ({"제약없음": True} if _비L is None else {"대금비율": _비L})
                _소 = 시뮬(_c(_H, **_옵공), 시드=_시L)
                _중 = 시뮬(_c(_중L, **dict(_중옵L, **_옵공)), 시드=_시L)
                _대 = 시뮬(_c(_대L, **dict(_대옵L, **_옵공)), 시드=_시L)
                if not (_소 and _중 and _대):
                    continue
                _bs, _bm, _bl = (_소["끝"] / _시L, _중["끝"] / _시L, _대["끝"] / _시L)
                _1 = max((_bs, "소형"), (_bm, "중형"), (_bl, "대형"))[1]
                print(f"        {_름L:>7}{_시L:>15,}{_bs:>9.1f}배{_bm:>9.1f}배{_bl:>9.1f}배"
                      f"{_1:>8}")
            print()

        print("     ② **한도가 실제로 몇 %의 매수에 걸리나** (시드 500만 · 지금 규칙)")
        print("        걸린다 = 사고 싶은 만큼(평가액 x 비중)이 아니라 **한도까지만** 샀다")
        for _비L, _름L in ((0.005, "0.5%"), (0.01, "1%"), (0.02, "2%"), (0.05, "5%")):
            _기L = []
            _r = 시뮬(_c(_H, 대금비율=_비L), 기록=_기L)
            if not _r or not _기L:
                continue
            _걸 = 0
            for _dL, _cL, _sL, _pL, _yL, _qL, _shL in _기L:
                _x = _사건맵L.get((_cL, _날인L.get(_dL)))
                if _x is None:
                    continue
                if (_shL or 0) * (_pL or 0) >= (_x.get("대금") or 0) * _비L * 0.95:
                    _걸 += 1
            print(f"        {_름L:>7}  끝 {_r['끝']:>15,.0f}원 · 몫 {len(_기L):>4}"
                  f" · **한도에 걸린 몫 {_걸:>4} ({_걸 / max(len(_기L), 1) * 100:.0f}%)**")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **AB2 — A(업종 -1.5%p) + B(악재 감자·유상증자) 를 같이 켜면** (2026-09-29) ══
    if _ONLY == "AB2" or "AB2" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── AB2 ⭐⭐⭐ **둘 다 걷기를 통과했다. 같이 켜면?** ──")
        print("=" * 122)
        print("     A 업종 갈래만 -1.5%p   111% · 낙폭 -11.0 → **-7.1%** · 기회 +68 · 앞 +6.6% 뒤 +10.3%")
        print("     B 악재 「감자·유상증자」  106% · 낙폭 -11.0 → **-7.1%** · 기회 +15 · 앞 +3.9% 뒤 +5.5%")
        print("     ⚠️ 둘 다 낙폭을 -7% 대로 낮춘다 — **겹치면 효과가 중복될 수 있다**")
        print("     ⚠️ 바탕을 **지금 실전**으로 놓는다 — 오늘 아침 섹터 자리 2개(C)를 넣었다")

        def _섹A2(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업A2(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        _C = {"무리자리": [(_섹A2, "섹터", 2)]}                    # 오늘 아침 넣은 것
        _A = {"무리갭": [(_업A2, "업종", -1.5)]}
        _B = {"재평가": "악재"}

        def _합(*들):
            _r = {}
            for _d in 들:
                for _k, _v in _d.items():
                    if _k in ("무리자리", "무리갭") and _k in _r:
                        _r[_k] = _r[_k] + _v
                    else:
                        _r[_k] = _v
            return _r

        # ── 악재표를 「감자·유상증자」만으로 ──
        _원표A2 = {k: dict(v) for k, v in _악재표.items()}
        _됨A2 = False
        try:
            import glob as _gA2
            _새표A2 = {}
            for _fA2 in sorted(_gA2.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
                _dA2 = os.path.basename(_fA2)[:8]
                try:
                    _jA2 = json.load(io.open(_fA2, encoding="utf-8-sig"))
                except ValueError:
                    continue
                _hA2 = {}
                for _칸A2 in ("챙길공시", "그밖의공시"):
                    for _xA2 in (_jA2.get(_칸A2) or []):
                        _cA2 = str(_xA2.get("종목코드") or "")
                        _제A2 = str(_xA2.get("공시명") or "")
                        if _cA2 and ("감자" in _제A2 or "유상증자" in _제A2):
                            _hA2[_cA2] = _hA2.get(_cA2, 0) + 1
                if _hA2:
                    _새표A2[_dA2] = _hA2
            _악재표.clear()
            _악재표.update(_새표A2)
            _됨A2 = True
            print(f"\n     악재표를 「감자·유상증자」만으로 바꿨다 — 걸린 날 {len(_새표A2):,}")
        except Exception as _eA2:  # noqa: BLE001
            print(f"     ⚠️ 악재표를 못 바꿨다: {type(_eA2).__name__} — B 는 전체 말로 돈다")

        _바탕A2 = 시뮬(_c(_H, **_C))
        print(f"\n     ⓪ 바탕 = Ⓗ + C(섹터 자리 2) = **지금 실전** —"
              f" {_바탕A2['끝']:,.0f}원 · 낙폭 {_바탕A2['낙']:.1f}% · 산 것 {_바탕A2['산']}")
        _순H = 시뮬(_c(_H))
        print(f"        (참고) C 도 없는 옛 바탕 — {_순H['끝']:,.0f}원 · 낙폭 {_순H['낙']:.1f}%"
              f" · 산 것 {_순H['산']}")

        _벌A2 = [("⓪ 바탕 (Ⓗ+C · 지금 실전)", _C),
                ("① +A 업종 -1.5%p", _합(_C, _A)),
                ("② +B 악재 감자·유상증자", _합(_C, _B)),
                ("③ ⭐ +A+B 둘 다", _합(_C, _A, _B)),
                ("④ [C 빼고] A+B 만", _합(_A, _B)),
                ("⑤ [C 빼고] A 만", dict(_A)),
                ("⑥ [C 빼고] B 만", dict(_B))]

        print(f"\n     {'설정':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>8}  판정")
        _결A2 = []
        for _름A2, _옵A2 in _벌A2:
            _r = 시뮬(_c(_H, **_옵A2))
            if not _r:
                continue
            _판 = "⭐" if (_r["끝"] >= _바탕A2["끝"] and _r["낙"] >= _바탕A2["낙"] - 1.0) else (
                "△" if _r["끝"] >= _바탕A2["끝"] else "❌")
            print(f"     {_름A2:<34}{_r['끝']:>16,.0f}"
                  f"{_r['끝'] / _바탕A2['끝'] * 100:>8.0f}%{_r['낙']:>8.1f}%{_r['산']:>7}"
                  f"{_r['산'] - _바탕A2['산']:>+8}  {_판}")
            _결A2.append((_름A2, _옵A2, _r))

        print("\n     ⑤ **고친 걷기** — 옵 준 쪽 vs 안 준 쪽 (바탕은 Ⓗ)")
        for _름A2, _옵A2, _r in _결A2:
            if _름A2.startswith("⓪"):
                continue
            print(f"\n        [{_름A2}]  ({_r['끝'] / _바탕A2['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_옵A2), 들여="          ")

        print("\n     ⑥ **띠마다 넣은 돈·번 돈**")
        for _름A2, _옵A2, _r in _결A2:
            if not _름A2.startswith(("⓪", "③")):
                continue
            _기A2 = []
            _rr = 시뮬(_c(_H, **_옵A2), 기록=_기A2)
            _cA3 = {}
            for _d3, _k3, _s3, _p3, _y3, _q3, _sh3 in _기A2:
                _t3 = ("소형" if (_s3 or 0) < 2000 else
                       "중형" if (_s3 or 0) < 10000 else "대형")
                _in3 = (_sh3 or 0) * (_p3 or 0)
                _v3 = _cA3.setdefault(_t3, [0, 0.0, 0.0])
                _v3[0] += 1
                _v3[1] += _in3
                _v3[2] += _in3 * (_y3 or 0) / 100.0
            print(f"\n        [{_름A2}] 끝 {_rr['끝']:,.0f}원 · 낙폭 {_rr['낙']:.1f}%")
            print(f"        {'띠':<6}{'몫':>6}{'넣은 돈':>16}{'번 돈':>16}"
                  f"{'한 건 넣은 돈':>16}{'수익률':>9}")
            for _t3 in ("소형", "중형", "대형"):
                _v3 = _cA3.get(_t3)
                if not _v3:
                    print(f"        {_t3:<6}{0:>6}")
                    continue
                _n3, _i3, _e3 = _v3
                print(f"        {_t3:<6}{_n3:>6}{_i3:>16,.0f}{_e3:>+16,.0f}"
                      f"{_i3 / _n3:>16,.0f}{_e3 / _i3 * 100 if _i3 else 0:>8.1f}%")

        if _됨A2:
            _악재표.clear()
            _악재표.update(_원표A2)
            print("\n     (악재표를 본디대로 되돌렸다)")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SEED — 시드를 키우면 순위가 뒤집히나 · 업종 갈래 다시 · 악재 걷기** (2026-09-29) ══
    if _ONLY == "SEED" or "SEED" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SEED ⭐⭐⭐ **시드를 키우면 소형이 계속 1등인가** ──")
        print("=" * 122)
        print("     쓸 = min( 평가액 x 비중, 현금, 그 종목 **거래대금 x 1%** )")
        print("     · 대형은 20% 뚜껑을 이미 다 풀어봤다 (B132·B133 · 30~40% 가 1등) — 뚜껑 문제가 아니다")
        print("     · 소형은 `대금 x 1%` 에 먼저 걸린다. **자산이 커져도 그 한도는 안 커진다**")
        print("       제약 있는 판 2.6억 vs 없는 판 9,949억 = **3,814배**")
        print("     ⇒ 소형 52배는 「시드가 작아서」 가능했을 수 있다. 시드를 키워 본다")

        def _표준낙E(x, 문):
            평 = x.get("평소등락")
            if not 평 or 평 <= 0 or x.get("낙폭20") is None:
                return False
            return (x["낙폭20"] / (평 * (20 ** 0.5))) <= 문

        def _중거름E(x):
            return (2000 <= (x.get("시총억") or 0) < 10000 and 재무통과(x) and 대금통과(x)
                    and x.get("시장낙폭") is not None and x["시장낙폭"] <= -15)

        def _대거름E(x):
            return ((x.get("시총억") or 0) >= 10000 and 재무통과(x) and 대금통과(x)
                    and x.get("낙40") is not None and x["낙40"] <= -30)

        _중옵E = dict(상대갭=-1.0, 하루상한=4, 비중=0.20, 시총하한=0, 시총상한=999999)
        _대옵E = dict(상대갭=-1.0, 하루상한=4, 비중=0.30, 시총하한=0, 시총상한=999999)

        print("\n     ① **시드를 키우면** — 셋을 각각 그 시드로 11년 굴린다")
        print(f"        {'시드':>16}{'소형 Ⓗ':>18}{'배':>7}"
              f"{'중형':>16}{'배':>7}{'대형':>16}{'배':>7}{'1등':>8}")
        for _시드E in (5_000_000, 20_000_000, 50_000_000, 100_000_000,
                       300_000_000, 1_000_000_000):
            _소 = 시뮬(_c(_H), 시드=_시드E)
            _중 = 시뮬(_c(_중거름E, **_중옵E), 시드=_시드E)
            _대 = 시뮬(_c(_대거름E, **_대옵E), 시드=_시드E)
            if not (_소 and _중 and _대):
                continue
            _배소, _배중, _배대 = (_소["끝"] / _시드E, _중["끝"] / _시드E, _대["끝"] / _시드E)
            _1등 = max((_배소, "소형"), (_배중, "중형"), (_배대, "대형"))[1]
            print(f"        {_시드E:>16,}{_소['끝']:>18,.0f}{_배소:>6.1f}배"
                  f"{_중['끝']:>16,.0f}{_배중:>6.1f}배{_대['끝']:>16,.0f}{_배대:>6.1f}배"
                  f"{_1등:>8}")
        print("        ⇒ 시드가 커질수록 소형의 **배수**가 떨어지면 「한도에 막힌다」는 뜻이다")

        # ── ② 업종 갈래 다시 (크기 문을 뺀 뒤) ──
        print("\n     ② **업종 갈래 다시** — `문통과` 안의 소형 크기 문을 뺀 뒤")
        print("        어제 「업종 -2.0%p = 102%」는 중형·대형이 못 들어온 값이었다")
        _밑E = 시뮬(_c(_H))
        print(f"        바탕 — {_밑E['끝']:,.0f}원 · 낙폭 {_밑E['낙']:.1f}% · 산 것 {_밑E['산']}")

        def _업E(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        _이긴E = []
        print(f"        {'설정':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        for _름E, _옵E in (("업종 갈래만 -2.5%p", {"무리갭": [(_업E, "업종", -2.5)]}),
                           ("업종 갈래만 -2.0%p", {"무리갭": [(_업E, "업종", -2.0)]}),
                           ("업종 갈래만 -1.5%p", {"무리갭": [(_업E, "업종", -1.5)]}),
                           ("업종 자리 1개를 더", {"무리자리": [(_업E, "업종", 1)]}),
                           ("업종 자리 2개를 더", {"무리자리": [(_업E, "업종", 2)]}),
                           ("업종 -2.0%p + 자리 2",
                            {"무리갭": [(_업E, "업종", -2.0)], "무리자리": [(_업E, "업종", 2)]})):
            _r = 시뮬(_c(_H, **_옵E))
            if not _r:
                continue
            _판 = "⭐" if (_r["끝"] >= _밑E["끝"] and _r["낙"] >= _밑E["낙"] - 1.0) else "❌"
            print(f"        {_름E:<34}{_r['끝']:>16,.0f}{_r['끝'] / _밑E['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}  {_판}")
            if _r["끝"] >= _밑E["끝"]:
                _이긴E.append((_름E, _옵E, _r))
        for _름E, _옵E, _r in sorted(_이긴E, key=lambda z: -z[2]["끝"])[:3]:
            print(f"\n        [{_름E}]  ({_r['끝'] / _밑E['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_옵E), 들여="          ")
        if not _이긴E:
            print("        바탕을 넘은 것이 없다 — 크기 문을 빼도 업종 갈래는 값이 없다")

        # ── ③ 악재 매도 「감자·유상증자」 걷기 ──
        print("\n     ③ **악재 매도 「감자·유상증자」** — 걷기를 아직 안 쟀다")
        print("        B126: 두 낱말만으로 낙폭 -11.5% → **-7.0%** · 돈÷낙폭 156% (전부 143%)")
        try:
            _원표E = {k: dict(v) for k, v in _악재표.items()}
            _새표E = {}
            import glob as _gE
            for _fE in sorted(_gE.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
                _dE = os.path.basename(_fE)[:8]
                try:
                    _jE = json.load(io.open(_fE, encoding="utf-8-sig"))
                except ValueError:
                    continue
                _hE = {}
                for _칸E in ("챙길공시", "그밖의공시"):
                    for _xE in (_jE.get(_칸E) or []):
                        _cE = str(_xE.get("종목코드") or "")
                        _제E = str(_xE.get("공시명") or "")
                        if _cE and ("감자" in _제E or "유상증자" in _제E):
                            _hE[_cE] = _hE.get(_cE, 0) + 1
                if _hE:
                    _새표E[_dE] = _hE
            _악재표.clear()
            _악재표.update(_새표E)
            _rE = 시뮬(_c(_H, 재평가="악재"))
            print(f"        「감자·유상증자」만 — {_rE['끝']:,.0f}원"
                  f" ({_rE['끝'] / _밑E['끝'] * 100:.0f}%) · 낙폭 {_rE['낙']:.1f}%"
                  f" · 산 것 {_rE['산']} · 걸린 날 {len(_새표E):,}")
            _걷기찍기(_옵걷기({"재평가": "악재"}), 들여="          ")
            _악재표.clear()
            _악재표.update(_원표E)
            print("        (악재표를 본디대로 되돌렸다)")
        except Exception as _eE:  # noqa: BLE001
            print(f"        ⚠️ ③ 터졌다: {type(_eE).__name__} {_eE}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SLOTWALK — 하루 최대 종목 6 → 8·10 을 앞뒤로** (2026-09-30) ══
    #    사용자: 「낙폭%별로 기회랑 끝자산 비교해서 보여줘」 (낙폭 한계 12% 를 다시 정하려고)
    #    지금 실전 규칙(CARDLIVE 와 같은 바탕) 하나를 놓고 사는 문턱 × 하루 자리 × 비중을 흔들어
    #    낙폭이 다른 설정들을 만든 뒤, 한계마다 「그 안에서 기회 최다 · 돈 최다」를 뽑는다
    if _ONLY == "SLOTWALK" or "SLOTWALK" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DDMAP ⭐⭐⭐ **하루 최대 종목을 늘리면 — 앞뒤 기간 모두 버티나** ──")
        print("=" * 122)

        def _섹M(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업M(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        def _바M(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        _바들M = getattr(R, "바구니전용", {})
        _원표M = {k: dict(v) for k, v in _악재표.items()}
        _새표M = {}
        import glob as _gM
        for _fM in sorted(_gM.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dM = os.path.basename(_fM)[:8]
            try:
                _jM = json.load(io.open(_fM, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hM = {}
            for _칸M in ("챙길공시", "그밖의공시"):
                for _xM in (_jM.get(_칸M) or []):
                    _cM = str(_xM.get("종목코드") or "")
                    _제M = str(_xM.get("공시명") or "")
                    if _cM and ("감자" in _제M or "유상증자" in _제M) and not any(
                            w in _제M for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hM[_cM] = _hM.get(_cM, 0) + 1
            if _hM:
                _새표M[_dM] = _hM

        def _옵M(갭, 자리, 비중):
            return {"무리자리": [(_섹M, "섹터", R.섹터전용자리)] + [(_바M(n), n, v["자리"]) for n, v in _바들M.items()],
                    "무리갭": [(_업M, "업종", R.업종전용상대갭)] + [(_바M(n), n, v["상대갭"]) for n, v in _바들M.items()],
                    "재평가": "악재", "시총상한": 999999,
                    "상대갭": 갭, "하루상한": (lambda 골, _n=자리: _n), "비중": 비중}
        try:
            _악재표.clear()
            _악재표.update(_새표M)
            _실전갭M = _c(_H)["상대갭"]   # 실전 규칙 자체를 잰다 — 실전 바탕 설정의 문턱
            print("     사용자 (9/30): 「덧붙이는 내용은 그냥 놔두는게 나아? 아니면 뭔가 액션이나 결정이 필요한거야?」")
            print("     DDMAP: 문턱 그대로 · 자리 6 → 10 이면 1년 40 → 44번 · 돈 303.9 → 301.5백만 · 낙폭 -6.3% 같음 (11년 통째)")
            for _자 in (8, 10):
                print(f"\n     [하루 최대 6 → {_자}] (뒤는 앞이 끝낸 자산으로 잇는다)")
                _줄, _sa, _sb = [], None, None
                for _라w, _시w, _끝w in (("앞 2010~2020", "2010", "2020"), ("뒤 2021~2026", "2021", "2026")):
                    _aw = 시뮬(_c(_H, **_옵M(_실전갭M, R.하루최대종목, 0.20)), 시작년=_시w, 끝년=_끝w, 시드=_sa)
                    _bw = 시뮬(_c(_H, **_옵M(_실전갭M, _자, 0.20)), 시작년=_시w, 끝년=_끝w, 시드=_sb)
                    if not _aw or not _bw:
                        continue
                    _줄.append((_라w, _aw, _bw, (_bw["끝"] / _aw["끝"] - 1) * 100 if _aw["끝"] > 0 else 0))
                    _sa, _sb = _aw["끝"], _bw["끝"]
                _걷기찍기(_줄, 들여="          ")
                # 해마다 — 그 해 500만으로 (한두 해가 끄는 건 아닌가)
                _승 = _패 = 0
                _해줄 = []
                for _y in range(2011, 2027):
                    _ay = 시뮬(_c(_H, **_옵M(_실전갭M, R.하루최대종목, 0.20)), 시작년=str(_y), 끝년=str(_y))
                    _by = 시뮬(_c(_H, **_옵M(_실전갭M, _자, 0.20)), 시작년=str(_y), 끝년=str(_y))
                    if not _ay or not _by:
                        continue
                    _d = (_by["끝"] / _ay["끝"] - 1) * 100
                    _승 += _d > 0.05
                    _패 += _d < -0.05
                    _해줄.append(f"{_y} {_d:+.1f}%({_ay['산']}→{_by['산']})")
                print("          해마다: " + " · ".join(_해줄))
                print(f"          ⇒ {_승}승 {_패}패 {len(_해줄) - _승 - _패}무")
        finally:
            _악재표.clear()
            _악재표.update(_원표M)
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **DDMAP — 낙폭 한계별 기회·끝 자산** (2026-09-30) ══
    #    사용자: 「낙폭%별로 기회랑 끝자산 비교해서 보여줘」 (낙폭 한계 12% 를 다시 정하려고)
    #    지금 실전 규칙(CARDLIVE 와 같은 바탕) 하나를 놓고 사는 문턱 × 하루 자리 × 비중을 흔들어
    #    낙폭이 다른 설정들을 만든 뒤, 한계마다 「그 안에서 기회 최다 · 돈 최다」를 뽑는다
    if _ONLY == "DDMAP" or "DDMAP" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DDMAP ⭐⭐⭐ **낙폭 한계를 몇 %로 두면 — 기회와 끝 자산** ──")
        print("=" * 122)

        def _섹M(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업M(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        def _바M(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        _바들M = getattr(R, "바구니전용", {})
        _원표M = {k: dict(v) for k, v in _악재표.items()}
        _새표M = {}
        import glob as _gM
        for _fM in sorted(_gM.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dM = os.path.basename(_fM)[:8]
            try:
                _jM = json.load(io.open(_fM, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hM = {}
            for _칸M in ("챙길공시", "그밖의공시"):
                for _xM in (_jM.get(_칸M) or []):
                    _cM = str(_xM.get("종목코드") or "")
                    _제M = str(_xM.get("공시명") or "")
                    if _cM and ("감자" in _제M or "유상증자" in _제M) and not any(
                            w in _제M for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hM[_cM] = _hM.get(_cM, 0) + 1
            if _hM:
                _새표M[_dM] = _hM

        def _옵M(갭, 자리, 비중):
            return {"무리자리": [(_섹M, "섹터", R.섹터전용자리)] + [(_바M(n), n, v["자리"]) for n, v in _바들M.items()],
                    "무리갭": [(_업M, "업종", R.업종전용상대갭)] + [(_바M(n), n, v["상대갭"]) for n, v in _바들M.items()],
                    "재평가": "악재", "시총상한": 999999,
                    "상대갭": 갭, "하루상한": (lambda 골, _n=자리: _n), "비중": 비중}
        try:
            _악재표.clear()
            _악재표.update(_새표M)
            _해M = max(1.0, (len(날) - 시i) / 245)
            _벌M = []
            print(f"     {'문턱':>6}{'자리':>5}{'비중':>6}{'끝 자산':>16}{'계좌 낙폭':>10}{'산 것':>7}{'1년 기회':>9}")
            for _갭 in (-2.0, -2.5, -3.0, -3.5, -4.0, -4.5):
                for _자 in (4, 6, 8, 10):
                    for _비 in (0.15, 0.20, 0.30):
                        _r = 시뮬(_c(_H, **_옵M(_갭, _자, _비)))
                        if not _r:
                            continue
                        _벌M.append((_갭, _자, _비, _r))
                        print(f"     {_갭:>6.1f}{_자:>5}{int(_비 * 100):>5}%{_r['끝']:>16,.0f}{_r['낙']:>9.1f}%"
                              f"{_r['산']:>7}{_r['산'] / _해M:>8.0f}번", flush=True)
            _실전갭M = _c(_H)["상대갭"]   # 이 절은 **실전 규칙 자체**를 잰다 — 실전 바탕 설정의 문턱으로 「지금」 줄을 찾는다
            _지금M = next((z for z in _벌M if z[0] == _실전갭M and z[1] == R.하루최대종목 and abs(z[2] - 0.20) < 1e-9), None)
            print("\n     ⭐ **낙폭 한계별 — 그 한계 안에서 고를 수 있는 가장 좋은 설정**")
            if _지금M:
                print(f"     (지금 실전 설정 = 문턱 {_실전갭M:g} · 자리 {R.하루최대종목} · 비중 20% → "
                      f"{_지금M[3]['끝']:,.0f}원 · 낙폭 {_지금M[3]['낙']:.1f}% · 1년 {_지금M[3]['산'] / _해M:.0f}번)")
            print(f"     {'낙폭 한계':>8} │ {'기회 최다 설정':<18}{'1년 기회':>8}{'끝 자산':>15}{'낙폭':>7} │ "
                  f"{'돈 최다 설정':<18}{'1년 기회':>8}{'끝 자산':>15}{'낙폭':>7}")
            for _한 in (5, 6, 7, 8, 10, 12, 15, 20, 30, 999):
                _안 = [z for z in _벌M if z[3]["낙"] >= -_한]
                if not _안:
                    print(f"     {('없음' if _한 == 999 else f'{_한}%'):>8} │ (이 안에 드는 설정이 없다)")
                    continue
                _기 = max(_안, key=lambda z: (z[3]["산"], z[3]["끝"]))
                _돈 = max(_안, key=lambda z: z[3]["끝"])

                def _라(z):
                    return f"{z[0]:g}·{z[1]}자리·{int(z[2] * 100)}%"
                print(f"     {('제한 없음' if _한 == 999 else f'{_한}%'):>8} │ {_라(_기):<18}{_기[3]['산'] / _해M:>7.0f}번"
                      f"{_기[3]['끝']:>15,.0f}{_기[3]['낙']:>6.1f}% │ {_라(_돈):<18}{_돈[3]['산'] / _해M:>7.0f}번"
                      f"{_돈[3]['끝']:>15,.0f}{_돈[3]['낙']:>6.1f}%")
            print("\n     ⚠️ 비중(종목당 자산 몇 %)은 시뮬 가정이다 — 화면에 쓰지 않는다. 비중을 빼고 보려면 20% 줄만 본다")
        finally:
            _악재표.clear()
            _악재표.update(_원표M)
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **REVERIFY — 지금 실전 규칙을 고친 잣대로 다시 잰다** (2026-10-01) ══
    #    사용자: 「혹시 기존 규칙도 재검증할 필요 있을까?」 → 「오케이 너 말대로 진행해」
    #    9/30 독립 검사가 own_lab 시뮬에서 찾은 결함이 이 시뮬에도 있다 — 실전 규칙 판은 **들고 있는 종목을 또 산다**
    #    (중복금지 기본 꺼짐) · 「돈↑」을 시드와 견줬다(쉬는 현금 이자 2.5% 착시).
    #    ① 또 사기 금지 ② 현금만과 견줌 ③ 같은 설정 아무 날과 견줌 ④ 비용·비중·나누는 해 흔들기 ⑤ 원전 켬/끔
    if _ONLY == "REVERIFY" or "REVERIFY" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── REVERIFY ⭐⭐⭐ **지금 실전 규칙 다시 재기** — 또 사기 금지 · 현금만 · 아무 날 · 흔들기 · 원전 ──")
        print("=" * 122)

        def _섹V(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업V(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        def _바V(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        _원표V = {k: dict(v) for k, v in _악재표.items()}
        _새표V = {}
        import glob as _gV
        for _fV in sorted(_gV.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dV = os.path.basename(_fV)[:8]
            try:
                _jV = json.load(io.open(_fV, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hV = {}
            for _칸V in ("챙길공시", "그밖의공시"):
                for _xV in (_jV.get(_칸V) or []):
                    _cV = str(_xV.get("종목코드") or "")
                    _제V = str(_xV.get("공시명") or "")
                    if _cV and ("감자" in _제V or "유상증자" in _제V) and not any(
                            w in _제V for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hV[_cV] = _hV.get(_cV, 0) + 1
            if _hV:
                _새표V[_dV] = _hV

        def _옵V(원전=True, 겹금지=False, 비중=0.20):
            _바 = getattr(R, "바구니전용", {}) if 원전 else {}
            return {"무리자리": [(_섹V, "섹터", R.섹터전용자리)] + [(_바V(n), n, v["자리"]) for n, v in _바.items()],
                    "무리갭": [(_업V, "업종", R.업종전용상대갭)] + [(_바V(n), n, v["상대갭"]) for n, v in _바.items()],
                    "재평가": "악재", "시총상한": 999999, "하루상한": (lambda 골: R.하루최대종목),
                    "비중": 비중, "중복금지": 겹금지}

        _시드V = 5_000_000.0
        _낙한V = -12.0

        def _날수(시작년, 끝년):
            return sum(1 for j in range(시i, len(날))
                       if (not 시작년 or 날[j][:4] >= 시작년) and (not 끝년 or 날[j][:4] <= 끝년))

        def _현금만(시작년, 끝년):
            return _시드V * (1 + _이자 / 245) ** _날수(시작년, 끝년)

        def _판정(r, 시작년, 끝년, 아무=None):
            if not r:
                return "❌ (결과 없음)", 0.0
            해 = max(0.5, _날수(시작년, 끝년) / 245)
            현 = _현금만(시작년, 끝년)
            ok = r["끝"] > 현 and r["낙"] >= _낙한V and r["산"] >= max(10, 2 * 해)
            if ok and 아무 and 아무["낙"] >= _낙한V and r["끝"] <= 아무["끝"]:
                ok = False
            return ("✅ 통과" if ok else "❌"), 해

        def _줄V(라, 설, 시작년=None, 끝년=None, 아무설=None):
            r = 시뮬(설, 시작년=시작년, 끝년=끝년)
            아 = 시뮬(아무설, 시작년=시작년, 끝년=끝년) if 아무설 else None
            판, 해 = _판정(r, 시작년, 끝년, 아)
            현 = _현금만(시작년, 끝년)
            if not r:
                print(f"     {라:<40} 결과 없음")
                return r
            print(f"     {라:<40}{r['끝']:>15,.0f}{현:>13,.0f}{r['낙']:>8.1f}%{r['산']:>7}{r['산'] / 해:>8.0f}번  {판}", flush=True)
            if 아:
                _견 = ("아무 날이 낙폭 한계 밖 — 견줄 수 없다" if 아["낙"] < _낙한V
                      else ("아무 날보다 많다 ✅" if r["끝"] > 아["끝"] else "아무 날보다 적다 ❌"))
                print(f"        └ 같은 설정·신호 거름 없이 아무 날: {아['끝']:,.0f}원 · 낙폭 {아['낙']:.1f}% · 산 {아['산']} → {_견}")
            return r

        _머V = f"     {'설정':<40}{'끝 자산':>15}{'현금만':>13}{'낙폭':>9}{'산 것':>7}{'1년 기회':>9}  판정"
        _비원V = _비용
        try:
            _악재표.clear()
            _악재표.update(_새표V)
            print(f"     실전 규칙: {R.한줄()}")
            print(f"     통과 = 현금만(연 {_이자 * 100:.1f}%)보다 많다 · 낙폭 {_낙한V:g}% 안 · 산 ≥ max(10, 2×해) · "
                  f"같은 설정 아무 날(낙폭 한계 안일 때)보다 많다 — own_lab 무리 판과 같은 잣대")
            # 10/1 독립 검사가 짚은 해석 주의 — 결과를 읽을 때 같이 본다
            print(f"     ⚠️ 이 판의 자료는 {_시작[:4]}-{_시작[4:6]} 부터 — 「앞 ~2018」은 약 2.7년 · 「나누는 해 2017 앞」은 1년이 안 된다")
            print("     ⚠️ 계좌 낙폭을 **산 값 기준**으로 센다(들고 있는 동안의 평가손이 안 잡힌다 — own_lab 은 전날 종가 기준) → 낙폭이 후하게 나올 수 있다")
            print("     ⚠️ 「아무 날」 풀도 재무 문·느슨한 빠짐(볼 −0.5 · 20일 −5% · 60일 −15% 중 하나)을 이미 거친 종목이다 — 이기기 더 어려운 견줌")
            print("     ⚠️ 또 사기 금지는 들고 있는 종목이 자리를 먼저 차지하고 **다음 후보로 메우지 않는다**")
            print("     ✔ 기준 줄: ① 「또 사기 허용 · 통째」는 CARDLIVE 본판과 같은 설정 — B141 의 303,643,082원 · 낙폭 −6.3% · 산 424 와 같아야 한다")

            print("\n     ① 또 사기 — 지금 판(허용) vs 금지 · 11년 통째 · 앞 2010~2018 · 뒤 2019~ (새 500만)")
            print(_머V)
            for _라k, _겹 in (("또 사기 허용 (지금까지의 판)", False), ("또 사기 금지", True)):
                for _구, _s, _e in (("통째", None, None), ("앞 ~2018", None, "2018"), ("뒤 2019~", "2019", None)):
                    _줄V(f"{_라k} · {_구}", _c(_H, **_옵V(겹금지=_겹)), _s, _e,
                         아무설=_c(None, **_옵V(겹금지=_겹)))

            print("\n     ④ 흔들기 — 또 사기 금지 바탕 · 뒤 2019~ (새 500만)")
            print(_머V)
            _줄V("바탕 (비용 0.26% · 비중 20%)", _c(_H, **_옵V(겹금지=True)), "2019", None, 아무설=_c(None, **_옵V(겹금지=True)))
            for _비용값 in (0.40, 0.60):
                globals()["_비용"] = _비용값
                _줄V(f"비용 {_비용값:.2f}%", _c(_H, **_옵V(겹금지=True)), "2019", None, 아무설=_c(None, **_옵V(겹금지=True)))
            globals()["_비용"] = _비원V
            _줄V("비중 10%", _c(_H, **_옵V(겹금지=True, 비중=0.10)), "2019", None, 아무설=_c(None, **_옵V(겹금지=True, 비중=0.10)))
            for _나눔해 in ("2017", "2021"):
                _앞끝 = str(int(_나눔해) - 1)
                _줄V(f"나누는 해 {_나눔해} · 앞 ~{_앞끝}", _c(_H, **_옵V(겹금지=True)), None, _앞끝, 아무설=_c(None, **_옵V(겹금지=True)))
                _줄V(f"나누는 해 {_나눔해} · 뒤 {_나눔해}~", _c(_H, **_옵V(겹금지=True)), _나눔해, None, 아무설=_c(None, **_옵V(겹금지=True)))

            print("\n     ⑤ 원전 기자재 -2.0%p·자리1 — 켬 vs 끔 (또 사기 금지 · 앞 ~2018 · 뒤 2019~)")
            print(_머V)
            for _라w, _원 in (("원전 켬 (지금 실전)", True), ("원전 끔", False)):
                for _구, _s, _e in (("앞 ~2018", None, "2018"), ("뒤 2019~", "2019", None)):
                    _줄V(f"{_라w} · {_구}", _c(_H, **_옵V(원전=_원, 겹금지=True)), _s, _e, 아무설=_c(None, **_옵V(원전=_원, 겹금지=True)))
            print("\n     ⚠️ 비중(종목당 자산 몇 %)은 시뮬 가정이다 — 화면에 쓰지 않는다")
        finally:
            globals()["_비용"] = _비원V
            _악재표.clear()
            _악재표.update(_원표V)
        print("  [대조] REVERIFY 끝")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐ **DDWHEN — 2021~ 낙폭이 언제·왜 깊어졌나** (2026-10-01) ══
    #    B205: 나누는 해 2021 · 뒤 2021~ 낙폭 −12.5% (한계 −12%). 사용자: 「정해야할 것 두가지 모두 너가 권고한대로 하자」
    #    (권고: 낙폭이 깊어진 시기와 이유를 먼저 파 본다). 지금 실전 규칙(원전 뺌) · 또 사기 금지 · 2021~ 새 500만
    if _ONLY == "DDWHEN" or "DDWHEN" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DDWHEN ⭐⭐ **2021~ 낙폭이 언제·왜 깊어졌나** — 실전 규칙 · 또 사기 금지 · 2021~ 새 500만 ──")
        print("=" * 122)

        def _섹W(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업W(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        def _바W(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        _원표W = {k: dict(v) for k, v in _악재표.items()}
        _새표W = {}
        import glob as _gW
        for _fW in sorted(_gW.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dW = os.path.basename(_fW)[:8]
            try:
                _jW = json.load(io.open(_fW, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hW = {}
            for _칸W in ("챙길공시", "그밖의공시"):
                for _xW in (_jW.get(_칸W) or []):
                    _cW = str(_xW.get("종목코드") or "")
                    _제W = str(_xW.get("공시명") or "")
                    if _cW and ("감자" in _제W or "유상증자" in _제W) and not any(
                            w in _제W for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hW[_cW] = _hW.get(_cW, 0) + 1
            if _hW:
                _새표W[_dW] = _hW
        _바들W = getattr(R, "바구니전용", {})
        _옵W = {"무리자리": [(_섹W, "섹터", R.섹터전용자리)] + [(_바W(n), n, v["자리"]) for n, v in _바들W.items()],
                "무리갭": [(_업W, "업종", R.업종전용상대갭)] + [(_바W(n), n, v["상대갭"]) for n, v in _바들W.items()],
                "재평가": "악재", "시총상한": 999999, "하루상한": (lambda 골: R.하루최대종목),
                "비중": 0.20, "중복금지": True, "곡돌려줘": True}
        try:
            _악재표.clear()
            _악재표.update(_새표W)
            _기W = []
            _rW = 시뮬(_c(_H, **_옵W), 시작년="2021", 기록=_기W)
            _곡W = (_rW or {}).get("곡") or []
            _a0 = next((j for j in range(len(날)) if 날[j][:4] >= "2021"), 시i)
            _a0 = max(_a0, 시i)
            print(f"     실전 규칙: {R.한줄()}")
            print(f"     2021~ : {_rW['끝']:,.0f}원 · 낙폭 {_rW['낙']:.1f}% · 산 {_rW['산']} · 곡선 {len(_곡W)}일")
            print("     ⚠️ 낙폭은 **산 값 기준**(들고 있는 동안의 평가손이 안 잡힌다) — 팔 때 손실이 한꺼번에 곡선에 반영된다")
            # 낙폭 구간 — 새 꼭대기마다 한 구간 · 구간마다 가장 깊은 바닥
            _구간 = []
            _꼭k, _꼭v, _바k, _바v = 0, (_곡W[0] if _곡W else 0), 0, 0.0
            for _kW, _vW in enumerate(_곡W):
                if _vW >= _꼭v:
                    if _바v < -0.001:
                        _구간.append((_바v, _꼭k, _바k, _kW))
                    _꼭k, _꼭v, _바k, _바v = _kW, _vW, _kW, 0.0
                else:
                    _ddW = _vW / _꼭v - 1
                    if _ddW < _바v:
                        _바k, _바v = _kW, _ddW
            if _바v < -0.001:
                _구간.append((_바v, _꼭k, _바k, None))
            _구간.sort()

            def _날W(kk):
                return 날[_a0 + kk] if kk is not None and 0 <= _a0 + kk < len(날) else "(아직 회복 안 함)"
            print("\n     ① 가장 깊었던 낙폭 구간 셋")
            print(f"     {'낙폭':>7}  {'꼭대기':>10}  {'바닥':>10}  {'회복':>16}  {'꼭대기→바닥':>10}  {'바닥→회복':>9}")
            for _ddW, _pkW, _tkW, _rkW in _구간[:3]:
                print(f"     {_ddW * 100:>6.1f}%  {_날W(_pkW):>10}  {_날W(_tkW):>10}  {_날W(_rkW):>16}  {_tkW - _pkW:>8}일  "
                      f"{(str(_rkW - _tkW) + '일') if _rkW is not None else '—':>9}")
            # 가장 깊은 구간에서 **팔린** 거래 — 그 손실이 곡선을 끌어내렸다 (산 값 기준이라 파는 날 반영)
            if _구간:
                _ddW, _pkW, _tkW, _rkW = _구간[0]
                _i꼭, _i바 = _a0 + _pkW, _a0 + _tkW
                _판것 = [q for q in _기W if _i꼭 < q[5] <= _i바]
                _판것.sort(key=lambda q: q[4])
                print(f"\n     ② 가장 깊은 구간({_날W(_pkW)} → {_날W(_tkW)}) 동안 **팔린** 거래 {len(_판것)}건 — 손실 큰 순")
                print(f"     {'산 날':>10} {'판 날':>10} {'종목':>8} {'시총억':>7} {'수익':>8}  섹터 / 업종")
                for _zW in _판것[:20]:
                    _섹 = _사슬섹터.get(_zW[1]) or "—"
                    try:
                        _업 = R.업종이름(_산업.get(_zW[1])) or "—"
                    except Exception:  # noqa: BLE001
                        _업 = "—"
                    print(f"     {_zW[0]:>10} {날[min(_zW[5], len(날) - 1)]:>10} {_zW[1]:>8} {_zW[2]:>7,.0f} {_zW[4]:>+7.1f}%  {_섹} / {_업}")
                _손 = [q for q in _판것 if q[4] < 0]
                print(f"     → 손실 {len(_손)}건 / 이익 {len(_판것) - len(_손)}건 · 평균 {sum(q[4] for q in _판것) / max(1, len(_판것)):+.1f}%")
                _섹손 = _co.Counter(_사슬섹터.get(q[1]) or "가치사슬 밖" for q in _손)
                print("     → 손실 거래의 섹터: " + " · ".join(f"{a} {b}" for a, b in _섹손.most_common(6)))
                _달 = _co.Counter(날[min(q[5], len(날) - 1)][:6] for q in _손)
                print("     → 손실이 팔린 달: " + " · ".join(f"{a[:4]}-{a[4:]} {b}" for a, b in sorted(_달.items())))
            # 해마다 (곡선에서)
            print("\n     ③ 해마다 (2021~ 한 계좌 곡선에서 · 산 값 기준)")
            _해v = {}
            for _kW, _vW in enumerate(_곡W):
                _해v.setdefault(_날W(_kW)[:4], [_vW, _vW])[1] = _vW
            _앞v = _시드
            for _yW in sorted(_해v):
                _끝vW = _해v[_yW][1]
                print(f"     {_yW}: {(_끝vW / _앞v - 1) * 100:+6.1f}%  ({_앞v:,.0f} → {_끝vW:,.0f})")
                _앞v = _끝vW
        finally:
            _악재표.clear()
            _악재표.update(_원표W)
        print("  [대조] DDWHEN 끝")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐ **PEAKDIST — 고점에서 막 떨어진 것 vs 오래 빠진 것** (2026-10-01) ══
    #    사용자: 「고점을 찍었다가 이제 하락하는 종목도 규칙에 걸릴 것 같아서. 하락이라는 기준에는 맞지만
    #    그게 다시 오를 종목인지, 반등할 수 있는 건지 판단할수는 없는 거잖아?」
    #    실전 규칙(화면 성적표와 같은 설정 · 또 사기 허용)의 실제 거래마다 **신호일 기준 250거래일 고점에서
    #    얼마나 내려왔나 · 고점이 며칠 전이었나**를 붙여 결과를 나눠 본다 (새 규칙이 아니라 지금 거래를 들여다보기)
    if _ONLY == "PEAKDIST" or "PEAKDIST" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── PEAKDIST ⭐⭐ **고점에서 막 떨어진 것 vs 오래 빠진 것 — 지금 실전 규칙의 거래를 나눠 본다** ──")
        print("=" * 122)

        def _섹P(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업P(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        _원표P = {k: dict(v) for k, v in _악재표.items()}
        _새표P = {}
        import glob as _gP
        for _fP in sorted(_gP.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dP = os.path.basename(_fP)[:8]
            try:
                _jP = json.load(io.open(_fP, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hP = {}
            for _칸P in ("챙길공시", "그밖의공시"):
                for _xP in (_jP.get(_칸P) or []):
                    _cP = str(_xP.get("종목코드") or "")
                    _제P = str(_xP.get("공시명") or "")
                    if _cP and ("감자" in _제P or "유상증자" in _제P) and not any(
                            w in _제P for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hP[_cP] = _hP.get(_cP, 0) + 1
            if _hP:
                _새표P[_dP] = _hP
        _옵P = {"무리자리": [(_섹P, "섹터", R.섹터전용자리)], "무리갭": [(_업P, "업종", R.업종전용상대갭)],
                "재평가": "악재", "시총상한": 999999, "하루상한": (lambda 골: R.하루최대종목), "비중": 0.20}
        try:
            _악재표.clear()
            _악재표.update(_새표P)
            _기P = []
            _rP = 시뮬(_c(_H, **_옵P), 기록=_기P)
            print(f"     실전 규칙(원전 뺌 · 또 사기 허용 = 화면 성적표와 같음): {_rP['끝']:,.0f}원 · 낙폭 {_rP['낙']:.1f}% · 산 {_rP['산']} · 거래 몫 {len(_기P)}")
            _줄P = []
            for _tP in _기P:
                _산날, _코드P, _결P = _tP[0], _tP[1], _tP[4]
                _ib = 날.index(_산날) if _산날 in 날 else None
                if _ib is None or _ib < 1:
                    continue
                _신호 = 날[_ib - 1]
                _sqP = 종계.get(_코드P)
                _kP = (자리.get(_코드P) or {}).get(_신호)
                if not _sqP or _kP is None or _kP < 60:
                    continue
                _창 = _sqP[max(0, _kP - 249):_kP + 1]
                _고 = max(_창)
                if _고 <= 0:
                    continue
                _고자리 = max(range(len(_창)), key=lambda j: _창[j])
                _줄P.append((_sqP[_kP] / _고 - 1, len(_창) - 1 - _고자리, _결P))
            print(f"     고점을 붙인 거래 몫 {len(_줄P)} (상장 60일 안 된 것·자리 없는 것 뺌)")

            def _칸찍(라, 묶음):
                if not 묶음:
                    print(f"     {라:<26}{0:>6}")
                    return
                _이 = sum(1 for z in 묶음 if z[2] > 0) / len(묶음) * 100
                _평 = sum(z[2] for z in 묶음) / len(묶음)
                _최 = min(z[2] for z in 묶음)
                print(f"     {라:<26}{len(묶음):>6}{_이:>9.1f}%{_평:>+9.2f}%{_최:>+9.1f}%")
            _머P = f"     {'구간':<26}{'거래':>6}{'수익 난 비율':>11}{'평균':>9}{'최악':>9}"
            print("\n     ① 신호일 기준 **250거래일 고점에서 얼마나 내려왔나**")
            print(_머P)
            for _라, _lo, _hi in (("고점 −20% 안쪽", -0.20, 1.0), ("−20 ~ −30%", -0.30, -0.20),
                                  ("−30 ~ −40%", -0.40, -0.30), ("−40 ~ −50%", -0.50, -0.40),
                                  ("−50% 넘게", -9.0, -0.50)):
                _칸찍(_라, [z for z in _줄P if _lo < z[0] <= _hi])
            print("\n     ② **고점이 며칠 전이었나** (거래일)")
            print(_머P)
            for _라, _lo, _hi in (("20일 안 (막 고점에서 떨어짐)", -1, 20), ("21~60일", 20, 60),
                                  ("61~120일", 60, 120), ("121~250일 (오래 빠짐)", 120, 999)):
                _칸찍(_라, [z for z in _줄P if _lo < z[1] <= _hi])
            print("\n     ③ 둘을 같이 — 고점 60일 안 / 넘음 × 고점에서 −30% 안 / 넘음")
            print(_머P)
            for _라1, _f1 in (("고점 60일 안", lambda z: z[1] <= 60), ("고점 60일 넘음", lambda z: z[1] > 60)):
                for _라2, _f2 in (("−30% 안", lambda z: z[0] > -0.30), ("−30% 넘게", lambda z: z[0] <= -0.30)):
                    _칸찍(f"{_라1} · {_라2}", [z for z in _줄P if _f1(z) and _f2(z)])
            _칸찍("(전체)", _줄P)
            print("\n     ⚠️ 결과는 거래 몫 하나의 수익(%) — 나눠 팔기 앞·뒤 몫이 따로 센다. 승률·평균만 보고 규칙을 바꾸지 않는다([[avg-return-is-not-money]])")
        finally:
            _악재표.clear()
            _악재표.update(_원표P)
        print("  [대조] PEAKDIST 끝")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐ **PEAKCUT — 「1년 고점에서 N% 넘게 빠진 것만」을 붙이면 돈이 느나** (2026-10-01) ══
    #    B208: 고점에서 덜 빠진 채 산 거래가 나빴다(−20% 안쪽 50% · +2.1% / −50% 넘게 85% · +17.2%).
    #    거래 평균이라 **자본 시뮬로 다시 잰다** — 빼면 자리가 나서 다른 후보를 사니 돈은 다를 수 있다
    if _ONLY == "PEAKCUT" or "PEAKCUT" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── PEAKCUT ⭐⭐ **실전 규칙 + 「250거래일 고점에서 N% 넘게 빠진 것만」 — 한 계좌로** ──")
        print("=" * 122)

        def _섹C(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        _업C = 업종갈래맞나     # 공용 도우미 (이 절은 띠를 나누지 않는다 — 실전 규칙 하나를 재는 절)

        _원표C = {k: dict(v) for k, v in _악재표.items()}
        _새표C = {}
        import glob as _gC
        for _fC in sorted(_gC.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dC = os.path.basename(_fC)[:8]
            try:
                _jC = json.load(io.open(_fC, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hC = {}
            for _칸C in ("챙길공시", "그밖의공시"):
                for _xC in (_jC.get(_칸C) or []):
                    _cC = str(_xC.get("종목코드") or "")
                    _제C = str(_xC.get("공시명") or "")
                    if _cC and ("감자" in _제C or "유상증자" in _제C) and not any(
                            w in _제C for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hC[_cC] = _hC.get(_cC, 0) + 1
            if _hC:
                _새표C[_dC] = _hC
        _고점캐시 = {}

        def _고점대비(x):
            r"""신호일(인−1) 기준 250거래일 고점 대비 (−0.35 = 고점에서 35% 빠짐) · 모르면 None"""
            _키 = (x["code"], x["인"])
            if _키 in _고점캐시:
                return _고점캐시[_키]
            v = None
            _sq = 종계.get(x["code"])
            _ii = x["인"] - 1
            if _sq and 0 <= _ii < len(날):
                _k = (자리.get(x["code"]) or {}).get(날[_ii])
                if _k is not None and _k >= 60:
                    _고 = max(_sq[max(0, _k - 249):_k + 1])
                    if _고 > 0:
                        v = _sq[_k] / _고 - 1
            _고점캐시[_키] = v
            return v

        def _거C(문턱):
            if 문턱 is None:
                return _H
            return lambda x, _t=문턱: bool(_H(x)) and (_고점대비(x) is not None and _고점대비(x) <= _t)

        def _옵C(겹금지):
            return {"무리자리": [(_섹C, "섹터", R.섹터전용자리)], "무리갭": [(_업C, "업종", R.업종전용상대갭)],
                    "재평가": "악재", "시총상한": 999999, "하루상한": (lambda 골: R.하루최대종목),
                    "비중": 0.20, "중복금지": 겹금지}
        try:
            _악재표.clear()
            _악재표.update(_새표C)
            print(f"     실전 규칙: {R.한줄()}")
            print("     문턱 = 신호일 기준 250거래일 고점 대비 (−30% = 고점에서 30% 넘게 빠진 것만 산다) · 바탕 = 문턱 없음(지금 실전)")
            print("     ⚠️ 낙폭은 산 값 기준(이 판의 시뮬) · 앞 2016-04~2020 / 뒤 2021~ 새 500만 · 판정: 앞뒤 둘 다 바탕보다 돈↑ 이고 낙폭 −12% 안")
            for _라겹, _겹 in (("또 사기 허용 (화면 성적표와 같음)", False), ("또 사기 금지", True)):
                print(f"\n     [{_라겹}]")
                print(f"     {'문턱':<10}{'통째 끝 자산':>16}{'낙폭':>8}{'산':>6} │{'앞 ~2020':>14}{'낙폭':>8} │{'뒤 2021~':>14}{'낙폭':>8}{'산':>6} │ 판정")
                _바 = {}
                for _문 in (None, -0.20, -0.25, -0.30, -0.35):
                    _a = 시뮬(_c(_거C(_문), **_옵C(_겹)))
                    _b = 시뮬(_c(_거C(_문), **_옵C(_겹)), 끝년="2020")
                    _d = 시뮬(_c(_거C(_문), **_옵C(_겹)), 시작년="2021")
                    if not (_a and _b and _d):
                        print(f"     {str(_문):<10} 결과 없음")
                        continue
                    if _문 is None:
                        _바 = {"a": _a, "b": _b, "d": _d}
                        판 = "(바탕)"
                    else:
                        _앞됨 = _b["끝"] > _바["b"]["끝"]
                        _뒤됨 = _d["끝"] > _바["d"]["끝"]
                        _낙됨 = _b["낙"] >= -12 and _d["낙"] >= -12
                        판 = ("✅ 앞뒤 둘 다 돈↑" if (_앞됨 and _뒤됨 and _낙됨)
                              else f"❌ 앞 {'↑' if _앞됨 else '↓'} · 뒤 {'↑' if _뒤됨 else '↓'}{'' if _낙됨 else ' · 낙폭 한계 밖'}")
                        판 += f" · 통째 바탕의 {_a['끝'] / _바['a']['끝'] * 100:.0f}%"
                    _라문 = "없음 (지금)" if _문 is None else f"{_문 * 100:.0f}%"
                    print(f"     {_라문:<10}{_a['끝']:>16,.0f}{_a['낙']:>7.1f}%{_a['산']:>6} │{_b['끝']:>14,.0f}{_b['낙']:>7.1f}% │"
                          f"{_d['끝']:>14,.0f}{_d['낙']:>7.1f}%{_d['산']:>6} │ {판}", flush=True)
            print("\n     ⚠️ 통과해도 **실전 코드를 바꾸는 일**이다 — 사용자가 정한다")
        finally:
            _악재표.clear()
            _악재표.update(_원표C)
        print("  [대조] PEAKCUT 끝")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐ **DDMTM — 낙폭을 날마다 전날 종가로 평가하면** (2026-10-01) ══
    #    B205·B207 의 낙폭은 **산 값 기준**(팔 때만 반영) — 2021~ −12.5% 가 실제로는 더 깊을 수 있다.
    #    사용자: 「남은 시험도 차례로 테스트하고 … 굳이 밤까지 기다릴 이유 없으면!」
    if _ONLY == "DDMTM" or "DDMTM" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DDMTM ⭐⭐ **계좌 낙폭 — 산 값 기준 vs 날마다 전날 종가 기준** · 지금 실전 규칙 ──")
        print("=" * 122)

        def _섹D(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False
        _원표D = {k: dict(v) for k, v in _악재표.items()}
        _새표D = {}
        import glob as _gD
        for _fD in sorted(_gD.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dD = os.path.basename(_fD)[:8]
            try:
                _jD = json.load(io.open(_fD, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hD = {}
            for _칸D in ("챙길공시", "그밖의공시"):
                for _xD in (_jD.get(_칸D) or []):
                    _cD = str(_xD.get("종목코드") or "")
                    _제D = str(_xD.get("공시명") or "")
                    if _cD and ("감자" in _제D or "유상증자" in _제D) and not any(
                            w in _제D for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hD[_cD] = _hD.get(_cD, 0) + 1
            if _hD:
                _새표D[_dD] = _hD

        def _옵D(겹금지, 종가):
            return {"무리자리": [(_섹D, "섹터", R.섹터전용자리)], "무리갭": [(업종갈래맞나, "업종", R.업종전용상대갭)],
                    "재평가": "악재", "시총상한": 999999, "하루상한": (lambda 골: R.하루최대종목),
                    "비중": 0.20, "중복금지": 겹금지, "종가평가": 종가, "곡돌려줘": True}
        try:
            _악재표.clear()
            _악재표.update(_새표D)
            print(f"     실전 규칙: {R.한줄()}")
            print("     ⚠️ 종가 기준은 **사는 금액도** 그날 평가액 × 비중으로 정한다(own_lab 과 같다) — 두 열은 평가 차이와 사는 금액 차이가 섞인 값이다")
            print("     ⚠️ 거래정지·자료 없음은 산 값으로 둔다 · 끝 자산은 남은 보유를 산 값으로 센다")
            print(f"     {'설정':<30}{'구간':<12}{'산 값 끝 자산':>15}{'종가 끝 자산':>15}{'산 값 낙폭':>11}{'종가 낙폭':>11}{'산':>6}")
            for _라D, _겹D in (("또 사기 허용 (화면 성적표)", False), ("또 사기 금지", True)):
                for _구D, _sD, _eD in (("통째", None, None), ("앞 ~2020", None, "2020"), ("뒤 2021~", "2021", None)):
                    _r0 = 시뮬(_c(_H, **_옵D(_겹D, False)), 시작년=_sD, 끝년=_eD)
                    _r1 = 시뮬(_c(_H, **_옵D(_겹D, True)), 시작년=_sD, 끝년=_eD)
                    if not (_r0 and _r1):
                        continue
                    _표시 = "  ⚠️ 한계 −12% 밖" if _r1["낙"] < -12 else ""
                    print(f"     {_라D:<30}{_구D:<12}{_r0['끝']:>15,.0f}{_r1['끝']:>15,.0f}{_r0['낙']:>10.1f}%{_r1['낙']:>10.1f}%"
                          f"{_r1['산']:>6}{_표시}", flush=True)
            # 뒤 2021~ · 또 사기 금지 · 종가 기준 — 가장 깊은 구간 셋
            _rM = 시뮬(_c(_H, **_옵D(True, True)), 시작년="2021")
            _곡M = (_rM or {}).get("곡") or []
            _a0M = max(next((j for j in range(len(날)) if 날[j][:4] >= "2021"), 시i), 시i)
            _구간M = []
            _꼭k, _꼭v, _바k, _바v = 0, (_곡M[0] if _곡M else 0), 0, 0.0
            for _kM, _vM in enumerate(_곡M):
                if _vM >= _꼭v:
                    if _바v < -0.001:
                        _구간M.append((_바v, _꼭k, _바k, _kM))
                    _꼭k, _꼭v, _바k, _바v = _kM, _vM, _kM, 0.0
                elif _vM / _꼭v - 1 < _바v:
                    _바k, _바v = _kM, _vM / _꼭v - 1
            if _바v < -0.001:
                _구간M.append((_바v, _꼭k, _바k, None))
            _구간M.sort()

            def _날M(kk):
                return 날[_a0M + kk] if kk is not None and 0 <= _a0M + kk < len(날) else "(아직 회복 안 함)"
            print("\n     뒤 2021~ · 또 사기 금지 · **종가 기준** 가장 깊었던 구간 셋")
            for _ddM, _pkM, _tkM, _rkM in _구간M[:3]:
                print(f"     {_ddM * 100:>6.1f}%  꼭대기 {_날M(_pkM)} → 바닥 {_날M(_tkM)} ({_tkM - _pkM}일) → 회복 {_날M(_rkM)}")
        finally:
            _악재표.clear()
            _악재표.update(_원표D)
        print("  [대조] DDMTM 끝")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐ **DDCTRL — 종가 기준 낙폭을 무엇이 줄이나** (2026-10-01 · B211 뒤) ══
    #    B211: 실전 규칙(또 사기 허용)의 계좌 낙폭이 산 값 기준 −6.3% · **종가 기준 −38.9%**(2020-03) · 2021~ −28.3%(2022).
    #    지수와 맞춰 보니 자료 탓이 아니다(코스닥 소형주 −43.1% · −31.5%) — 손절 없이 꽉 차게 들고 시장째 빠졌다.
    #    사용자 10/1 「혹시 테스트 결과에서 추가로 테스트가 필요하면 허락없이 진행해.」
    #    ⇒ 실전 규칙은 그대로 두고 손잡이 하나씩만 바꿔 **종가 기준** 끝 자산·낙폭을 잰다 (앞 ~2020 / 뒤 2021~)
    #    ⚠️ 규칙을 바꾸자는 판이 아니다 — 숫자만 남기고 사용자가 정한다 ([[dont-add-conditions]] · 조건을 더하면 졌다)
    if _ONLY == "DDCTRL" or "DDCTRL" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DDCTRL ⭐⭐ **종가 기준 계좌 낙폭 — 무엇이 줄이나** · 지금 실전 규칙 · 손잡이 하나씩 ──")
        print("=" * 122)

        def _섹C(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False
        _원표C = {k: dict(v) for k, v in _악재표.items()}
        _새표C = {}
        import glob as _gC
        for _fC in sorted(_gC.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dC = os.path.basename(_fC)[:8]
            try:
                _jC = json.load(io.open(_fC, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hC = {}
            for _칸C in ("챙길공시", "그밖의공시"):
                for _xC in (_jC.get(_칸C) or []):
                    _cC = str(_xC.get("종목코드") or "")
                    _제C = str(_xC.get("공시명") or "")
                    if _cC and ("감자" in _제C or "유상증자" in _제C) and not any(
                            w in _제C for w in ("해제", "취소", "철회", "종결", "기각")):
                        _hC[_cC] = _hC.get(_cC, 0) + 1
            if _hC:
                _새표C[_dC] = _hC

        def _옵C(**더):
            o = {"무리자리": [(_섹C, "섹터", R.섹터전용자리)], "무리갭": [(업종갈래맞나, "업종", R.업종전용상대갭)],
                 "재평가": "악재", "시총상한": 999999, "하루상한": (lambda 골: R.하루최대종목),
                 "비중": 0.20, "종가평가": True}
            o.update(더)
            return o

        def _시장거름(문):
            # ⚠️ `_c(거름, …)` 의 첫 인자가 실전 거름(_H)이다 — 「거름」 을 그냥 넘기면 실전 규칙이 통째로 바뀐다. _H 와 AND 로
            return lambda x: bool(_H(x)) and (x.get("시장낙폭") is None or x["시장낙폭"] > 문)
        _안들C = (("지금 그대로 (또 사기 허용)", {}),
                 ("또 사기 금지", {"중복금지": True}),
                 ("손절 종가 −15% (종가에 팜)", {"손절": "종가:-15"}),
                 ("손절 종가 −20% (종가에 팜)", {"손절": "종가:-20"}),
                 ("손절 종가 −25% (종가에 팜)", {"손절": "종가:-25"}),
                 ("(참고) 옛 손절 −20% 고가 기준·고가에 팜", {"손절": -20.0}),
                 ("하루 4 + 섹터 2 (지금 6 + 섹터 2)", {"하루상한": 4}),
                 ("하루 3 + 섹터 2", {"하루상한": 3}),
                 ("시장 20일 −10% 넘게 빠진 날 안 삼", {"거름": _시장거름(-10.0)}),
                 ("(가정) 비중 10%", {"비중": 0.10}))
        try:
            _악재표.clear()
            _악재표.update(_새표C)
            print(f"     실전 규칙: {R.한줄()}")
            print("     잣대: 종가 기준(들고 있는 종목을 전날 종가로 평가) · 낙폭 한계 −12% (사용자) · 「비중 10%」는 시뮬 가정 줄이라 규칙 후보가 아니다")
            print(f"     {'손잡이':<34}{'앞 ~2020 끝':>14}{'앞 낙폭':>8}{'앞 산':>6}{'뒤 2021~ 끝':>14}{'뒤 낙폭':>8}{'뒤 산':>6}  뒤 지금의 %")
            _밑C = None
            for _라C, _더C in _안들C:
                # ⚠️ 10/1 독립 검사: `_c(거름, **…)` 에 「거름」 을 또 넘기면 TypeError — 따로 꺼내 첫 인자로 (튜플 안 dict 는 안 건드린다)
                _거C = _더C.get("거름", _H)
                _나C = {k: v for k, v in _더C.items() if k != "거름"}
                _앞C = 시뮬(_c(_거C, **_옵C(**_나C)), 끝년="2020")
                _뒤C = 시뮬(_c(_거C, **_옵C(**_나C)), 시작년="2021")
                if not (_앞C and _뒤C):
                    print(f"     {_라C:<34} (못 잼)")
                    if _밑C is None:
                        raise SystemExit("🛑 기준 줄(지금 그대로)을 못 쟀다 — 「지금의 %」 를 낼 수 없다")
                    continue
                if _밑C is None:
                    _밑C = _뒤C
                _표C = "" if (_앞C["낙"] >= -12 and _뒤C["낙"] >= -12) else "  ⚠️ 한계 −12% 밖"
                print(f"     {_라C:<34}{_앞C['끝']:>14,.0f}{_앞C['낙']:>7.1f}%{_앞C['산']:>6}{_뒤C['끝']:>14,.0f}{_뒤C['낙']:>7.1f}%"
                      f"{_뒤C['산']:>6}  {_뒤C['끝'] / _밑C['끝'] * 100:>5.0f}%{_표C}", flush=True)
            print("     ⚠️ 끝 자산은 남은 보유를 산 값으로 센다(gate7 시뮬) · 앞·뒤는 따로 500만에서 시작")
        finally:
            _악재표.clear()
            _악재표.update(_원표C)
        print("  [대조] DDCTRL 끝")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **CARDLIVE — 화면 성적표를 실전 규칙 그대로** (2026-09-30) ══
    #    사용자: 「④ 퀀트 화면 6장 「과거에 어땠나」 숫자는 화면이 실제로 쓰는 규칙과 맞도록 바꾸자」
    #    6장은 rule-cases.json(build_rule_cases.py)을 읽는데, 그 코드는 **옛날식 단순 계산**이었다
    #    (하루 4종목 · 후보 40 · 후보 중앙갭 · 업종 문턱·섹터 자리·악재 매도·원전을 모른다).
    #    ⇒ 실전 바탕(LIVE 와 같은 _실전L) 시뮬의 **실제 거래 기록**으로 두 파일을 만든다
    if _ONLY in ("CARDLIVE", "MULTIDUMP") or "CARDLIVE" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── CARDLIVE ⭐⭐⭐ **화면 성적표(5장·6장)를 실전 규칙의 실제 거래로** ──")
        print("=" * 122)

        def _섹K(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업K(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        def _바K(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        _바들 = getattr(R, "바구니전용", {})
        _실전K = {"무리자리": [(_섹K, "섹터", R.섹터전용자리)] + [(_바K(n), n, v["자리"]) for n, v in _바들.items()],
                  "무리갭": [(_업K, "업종", R.업종전용상대갭)] + [(_바K(n), n, v["상대갭"]) for n, v in _바들.items()],
                  "재평가": "악재", "시총상한": 999999}
        # 악재표 — LIVE 와 같게 「감자·유상증자」 · 반대말 제외 (끝나면 되돌린다)
        _원표K = {k: dict(v) for k, v in _악재표.items()}
        _새표K = {}
        import glob as _gK
        for _fK in sorted(_gK.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
            _dK = os.path.basename(_fK)[:8]
            try:
                _jK = json.load(io.open(_fK, encoding="utf-8-sig"))
            except ValueError:
                continue
            _hK = {}
            for _칸K in ("챙길공시", "그밖의공시"):
                for _xK in (_jK.get(_칸K) or []):
                    _cK = str(_xK.get("종목코드") or "")
                    _제K = str(_xK.get("공시명") or "")
                    _반K = any(w in _제K for w in ("해제", "취소", "철회", "종결", "기각"))
                    if _cK and ("감자" in _제K or "유상증자" in _제K) and not _반K:
                        _hK[_cK] = _hK.get(_cK, 0) + 1
            if _hK:
                _새표K[_dK] = _hK
        _이름K = {}
        try:
            _bK = json.load(io.open(os.path.join(O._DATA, "stock-base.json"), encoding="utf-8-sig"))
            for _cK, _vK in (_bK.get("종목") or _bK).items():
                if isinstance(_vK, dict):
                    _이름K[_cK] = (_vK.get("종목명") or _vK.get("이름") or "")
        except Exception:  # noqa: BLE001
            pass
        try:
            _악재표.clear()
            _악재표.update(_새표K)
            # ⭐ 10/1 MULTI — ONLY=MULTIDUMP 면 실전 규칙의 그날 후보만 내보내고 끝 (화면 파일은 안 건드린다)
            if _ONLY == "MULTIDUMP":
                _후K = []
                _본M = 시뮬(_c(_H, **_실전K), 후보기록=_후K)
                _밖M = os.path.join(O._DATA, "_labs", "multi_cand_live.jsonl")
                # ⚠️ 10/1 독립 검사: 대조할 같은 판 숫자 — 2019~ · 전날 종가 평가 (multi_lab 은 산 수·낙폭으로 견준다)
                _대M = 시뮬(_c(_H, **_실전K, 종가평가=True), 시작년="2019")
                print(f"     대조(2019~ · 종가평가) — {_대M['끝']:,.0f}원 · 낙폭 {_대M['낙']:.1f}% · 산 것 {_대M['산']}")
                with io.open(_밖M, "w", encoding="utf-8") as _foM:
                    _foM.write(json.dumps({"규칙": "_머리", "무리": "실전", "끝날": 날[-1]}, ensure_ascii=False) + "\n")
                    _foM.write(json.dumps({"규칙": "L00", "대조끝": _대M["끝"], "대조산": _대M["산"], "대조낙": _대M["낙"]},
                                          ensure_ascii=False) + "\n")
                    for _iM, _줄M in _후K:
                        _foM.write(json.dumps({"규칙": "L00", "날": 날[_iM], "후보": [
                            dict(z, 몫=[[a, (None if b is None else round(b, 6)), (None if cc is None else 날[cc])]
                                       for a, b, cc in z["몫"]]) for z in _줄M]}, ensure_ascii=False) + "\n")
                print(f"     실전 규칙(대조) — {_본M['끝']:,.0f}원 · 낙폭 {_본M['낙']:.1f}% · 산 것 {_본M['산']}"
                      f" · 후보 있는 날 {len(_후K):,} · 후보 {sum(len(z[1]) for z in _후K):,}건 → {_밖M}")
                print("  [대조] MULTIDUMP 끝", flush=True)
                return 0
            _거래K = []
            _본K = 시뮬(_c(_H, **_실전K), 기록=_거래K)
            print(f"     실전 규칙 11년 — {_본K['끝']:,.0f}원 · 연 {_본K['연']:.2f}% · 낙폭 {_본K['낙']:.1f}% · 산 것 {_본K['산']}")
            print("     (B141 원전 줄: 303,643,082원 · 낙폭 -6.3% · 산 것 424 — 가까우면 맞게 선 것이다)")
            # 거래 기록 = 몫마다 한 줄 → 한 번 산 것(날·종목)마다 주수로 가중
            _날i = {d: k for k, d in enumerate(날)}
            _묶K = {}
            for (_d, _cd, _시, _가, _r, _청, _주) in _거래K:
                _묶K.setdefault((_d, _cd), []).append((_시, _가, _r, _청, _주))
            _사례 = []
            _끝i = len(날) - 1
            for (_d, _cd), 몫 in sorted(_묶K.items()):
                _주합 = sum(z[4] for z in 몫)
                _결 = sum(z[2] * z[4] for z in 몫) / _주합 if _주합 else None
                _청 = max(z[3] for z in 몫)
                _끝났나 = _청 < _끝i
                _앞 = 몫[0]
                _사례.append({
                    "날짜": f"{_d[:4]}-{_d[4:6]}-{_d[6:8]}", "종목코드": _cd, "이름": _이름K.get(_cd, ""),
                    "매수가": round(_앞[1]), "시총억": round(_앞[0]),
                    "결과": round(_결, 2) if _결 is not None else None,
                    "며칠": (_청 - _날i.get(_d, _청)) if _끝났나 else None,
                    "끝났나": _끝났나, "도달": bool(_앞[2] >= R.앞몫목표 - 1.0)})
            _끝K = [z for z in _사례 if z["끝났나"] and z["결과"] is not None]
            _해K = {z["날짜"][:4] for z in _끝K}
            import statistics as _stK
            import datetime as _dtK
            _cases = {
                "만든날": _dtK.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "출처": "gate7_lab CARDLIVE — 실전 규칙 그대로의 자본 시뮬 **실제 거래** (제약 있는 판 · 시드 500만)",
                "규칙": R.한줄(),
                "기간": f"{_사례[0]['날짜']} ~ {_사례[-1]['날짜']}" if _사례 else "",
                "전체건수": len(_끝K),
                "도달": sum(1 for z in _끝K if z["도달"]),
                "도달률": round(sum(1 for z in _끝K if z["도달"]) / max(1, len(_끝K)) * 100, 1),
                "흑자": sum(1 for z in _끝K if z["결과"] > 0),
                "승률": round(sum(1 for z in _끝K if z["결과"] > 0) / max(1, len(_끝K)) * 100, 1),
                "평균": round(_stK.mean([z["결과"] for z in _끝K]), 2) if _끝K else 0,
                "평균보유": round(_stK.mean([z["며칠"] for z in _끝K]), 1) if _끝K else 0,
                "가장나쁨": round(min(z["결과"] for z in _끝K), 2) if _끝K else 0,
                "해수": len(_해K),
                "최근": _끝K[-10:][::-1],
                "최악": sorted(_끝K, key=lambda z: z["결과"])[:5],
                "최고": sorted(_끝K, key=lambda z: (-z["결과"], z["며칠"] or 999))[:3],
                "손실건수": sum(1 for z in _끝K if z["결과"] < 0),
                "손실평균": (round(_stK.mean([z["결과"] for z in _끝K if z["결과"] < 0]), 2)
                            if any(z["결과"] < 0 for z in _끝K) else None),
                "아직진행중": [z for z in _사례 if not z["끝났나"]],
            }
            # 5장 줄 — 「나눠 팔면 11년 성적이 N배 · 계좌 흔들림 A% → B%」 : 같은 규칙 · 한 번에 +20%/40일 과 견줌
            _한번K = 시뮬(_c(_H, **dict(_실전K, 나눔=((1.0, 20.0, 40),))))
            _분할K = []
            for _y in ("2019", "2020", "2021", "2022"):
                _rK = 시뮬(_c(_H, **_실전K), 시작년=_y)
                if _rK:
                    _분할K.append({"시작": _y, "연": round(_rK["연"], 1), "낙폭": round(_rK["낙"], 1)})
            _cap = {
                "만든날": _cases["만든날"],
                # ⚠️ 10/1 — 「원전 기자재 -2.0%p+자리1」이 손으로 박혀 원전을 뺀 뒤에도 찍혔다 → rule_def 에서 읽는다
                "출처": f"gate7_lab CARDLIVE — 실전 규칙 그대로 (섹터 자리 {R.섹터전용자리} · 업종 {R.업종전용상대갭:g}%p · "
                        + "".join(f"{n} {v['상대갭']:g}%p+자리{v['자리']} · " for n, v in getattr(R, "바구니전용", {}).items())
                        + "악재 감자·유상증자) · 제약 있는 판 · 나눔 "
                        + " · ".join(f"{a * 100:.0f}% +{b:g}%/{c}일" for a, b, c in R.몫들),
                "규칙한줄": R.한줄(), "시작자산": 5000000.0,
                "연평균": round(_본K["연"], 2), "계좌낙폭": round(_본K["낙"], 1), "최악낙폭": round(_본K["낙"], 1),
                "끝자산": round(_본K["끝"]), "산것": _본K["산"], "분할": _분할K,
                "주의": "제약 있는 판(현금·거래대금 1% 한도) 값. 사용자 2026-09-30: 「화면이 실제로 쓰는 규칙과 맞도록 바꾸자」",
                "옛값_참고": {"계좌낙폭": round(_한번K["낙"], 1), "끝자산": round(_한번K["끝"]), "산것": _한번K["산"],
                              "무엇인가": "**안 나눠 팔 때** — 한 번에 +20%/40일 · 같은 실전 규칙 · 같은 제약"},
                "나눠팔기_배수": round(_본K["끝"] / _한번K["끝"], 2) if _한번K and _한번K["끝"] else None,
            }
            # ⭐ 10/1 QUANT-ASSUME-1001 — 6장 「또 사기」 가정 문구 숫자 · **같은 판·같은 제약**에서 잰다
            #    사용자: 「또 사기 허용하고 화면에 그 내용만 적시하면 될 것 같은데?」
            _금지K = 시뮬(_c(_H, **_실전K, 중복금지=True))
            if _금지K and _본K["끝"]:
                _cap["또사기금지"] = {"끝자산": round(_금지K["끝"]), "계좌낙폭": round(_금지K["낙"], 1), "산것": _금지K["산"],
                                    "덜번비율": round((1 - _금지K["끝"] / _본K["끝"]) * 100, 1),
                                    "무엇인가": "이미 들고 있는 종목이 다시 후보에 떠도 **안 산다** — 같은 실전 규칙·같은 제약"}
                print(f"     또 사기 금지 — {_금지K['끝']:,.0f}원 · 낙폭 {_금지K['낙']:.1f}% · 산 {_금지K['산']} · "
                      f"{_cap['또사기금지']['덜번비율']}% 덜 번다")
            # ⭐ 10/1 — 6장 비교 줄(sell-options.json)이 **9/14 규칙 · 제약 없는 판**이라 가정 문구와 기준이 달랐다.
            #    같은 판(지금 실전 규칙 · 제약 있는 판)에서 매도 비율 셋을 잰다. 낙폭오차 = 08:55 예상체결가 오차 ±0.5%p 넣고 잰 낙폭
            _안들K = []
            for _앞K, _뒤K in ((0.3, 0.7), (0.4, 0.6), (0.5, 0.5)):
                _몫K = ((_앞K, R.몫들[0][1], R.몫들[0][2]), (_뒤K, R.몫들[1][1], R.몫들[1][2]))
                _ra = 시뮬(_c(_H, **_실전K, 나눔=_몫K))
                _rb = 시뮬(_c(_H, **_실전K, 나눔=_몫K), 오차=0.5)
                if _ra and _rb:
                    _안들K.append({"앞": _앞K, "뒤": _뒤K, "돈억": round(_ra["끝"] / 1e8, 2), "낙폭": round(_ra["낙"], 1),
                                  "낙폭오차": round(min(_ra["낙"], _rb["낙"]), 1)})
                    print(f"     매도 {_앞K * 100:.0f}:{_뒤K * 100:.0f} — {_ra['끝']:,.0f}원 · 낙폭 {_ra['낙']:.1f}% "
                          f"(오차 넣고 {_rb['낙']:.1f}%)")
            _sellK = {"만든날": _cases["만든날"],
                      "출처": "gate7_lab CARDLIVE — 지금 실전 규칙 · 제약 있는 판 · 시드 500만 (가정 문구·성적표와 같은 판)",
                      "잣대": "돈 = 제약 있는 판 끝 자산(억) · 낙폭 = 계좌 낙폭 · 낙폭오차 = 08:55 예상체결가 오차 ±0.5%p 포함",
                      "한계낙폭": -12.0, "안들": _안들K}
            print(f"     6장 — {_cases['기간']} · {_cases['전체건수']}번 · 승률 {_cases['승률']}% · 평균 {_cases['평균']:+.2f}% · "
                  f"평균보유 {_cases['평균보유']}일 · 최악 {_cases['가장나쁨']:+.2f}%")
            print(f"     5장 — 나눠 팔면 {_cap['나눠팔기_배수']}배 · 계좌 흔들림 {_cap['옛값_참고']['계좌낙폭']}% → {_cap['계좌낙폭']}%")
            for _이름f, _값 in (("rule-cases.json", _cases), ("rule-capital.json", _cap)) + (
                    (("sell-options.json", _sellK),) if len(_안들K) == 3 else ()):
                _p = os.path.join(O._DATA, _이름f)
                if os.path.exists(_p):
                    import shutil as _shK
                    _shK.copy(_p, os.path.join(O._DATA, "_labs", _이름f.replace(".json", "_CARDLIVE전.json")))
                io.open(_p, "w", encoding="utf-8").write(json.dumps(_값, ensure_ascii=False, indent=1))
                print(f"     ✅ {_이름f} 새로 썼다 (전 것은 _labs/{_이름f.replace('.json', '_CARDLIVE전.json')})")
        finally:
            _악재표.clear()
            _악재표.update(_원표K)
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SPLIT3 — 소·중·대 세 규칙을 각각 굴려 자산을 나눠 담는다** (2026-09-29) ══
    if _ONLY == "SPLIT3" or "SPLIT3" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SPLIT3 ⭐⭐⭐ **얹는 게 아니라 따로 굴린다 — 자리를 안 다툰다** ──")
        print("=" * 122)
        print("     B132 에서 대형만의 규칙이 혼자 섰다 (소형 규칙 한 글자도 안 씀):")
        print("        2,000억↑  시장낙폭≤-15 · 갭-1.0 · 자리4 · 비중20% → 5.0배 · 낙폭 -7.3% · 127건")
        print("        1조↑      낙40≤-30%   · 갭-1.0 · 자리4 · 비중30% → 8.2배 · 낙폭 -9.9% · 115건")
        print("     여기서는 ① 중형 전용 풀을 **처음으로** 따로 훑고")
        print("               ② 세 규칙을 각각 굴리고 ③ 자산을 나눠 담아 **합친 낙폭**을 잰다")

        def _표준낙S(x, 문):
            평 = x.get("평소등락")
            if not 평 or 평 <= 0 or x.get("낙폭20") is None:
                return False
            return (x["낙폭20"] / (평 * (20 ** 0.5))) <= 문

        def _신호S(이름):
            if 이름 == "시장낙폭≤-10":
                return lambda x: (x.get("시장낙폭") is not None and x["시장낙폭"] <= -10)
            if 이름 == "시장낙폭≤-15":
                return lambda x: (x.get("시장낙폭") is not None and x["시장낙폭"] <= -15)
            if 이름 == "볼120≤-1.5σ":
                return lambda x: (x.get("볼120") is not None and x["볼120"] <= -1.5)
            if 이름 == "볼60≤-1.5σ":
                return lambda x: (x.get("볼60") is not None and x["볼60"] <= -1.5)
            if 이름 == "낙40≤-30%":
                return lambda x: (x.get("낙40") is not None and x["낙40"] <= -30)
            if 이름 == "낙60≤-30%":
                return lambda x: (x.get("낙60") is not None and x["낙60"] <= -30)
            if 이름 == "평소-2.5배↓":
                return lambda x: _표준낙S(x, -2.5)
            if 이름 == "평소-2.5배↓+시장낙폭-10":
                return lambda x: (_표준낙S(x, -2.5) and x.get("시장낙폭") is not None
                                  and x["시장낙폭"] <= -10)
            return lambda x: True

        _신호목록S = ("(신호 없음)", "시장낙폭≤-10", "시장낙폭≤-15", "볼120≤-1.5σ",
                    "볼60≤-1.5σ", "낙40≤-30%", "낙60≤-30%", "평소-2.5배↓",
                    "평소-2.5배↓+시장낙폭-10")

        def _풀규칙S(아래, 위, 신호):
            _sig = _신호S(신호)
            def _f(x, _a=아래, _b=위):
                _s = x.get("시총억") or 0
                return _a <= _s < _b and 재무통과(x) and 대금통과(x) and _sig(x)
            return _f

        def _최고찾기S(아래, 위, 라벨):
            r"""그 띠 **전용 풀**에서 격자를 훑어 위 다섯을 돌려준다."""
            print(f"\n     ── [{라벨}] 전용 풀 — 소형 규칙을 안 쓴다 ──")
            _n사건 = sum(1 for x in 사건 if 아래 <= (x.get("시총억") or 0) < 위)
            print(f"        사건 {_n사건:,}건")
            _벌 = []
            for _sig in _신호목록S:
                _거름 = _풀규칙S(아래, 위, _sig)
                for _갭v in (-3.5, -2.0, -1.0):
                    for _자리v, _비중v in ((4, 0.20), (4, 0.30), (2, 0.40), (6, 0.20)):
                        _r = 시뮬(_c(_거름, 상대갭=_갭v, 하루상한=_자리v, 비중=_비중v,
                                    시총하한=0, 시총상한=999999))
                        if not _r or _r["산"] < 20:
                            continue
                        _벌.append((_r["연"] / max(abs(_r["낙"]), 3.0), _sig, _갭v,
                                    _자리v, _비중v, _r))
            _벌.sort(key=lambda z: -z[0])
            if not _벌:
                print("        🔴 산 것 20건↑ 조합이 없다")
                return None
            print(f"        {'신호':<22}{'갭':>6}{'자리':>5}{'비중':>6}"
                  f"{'끝 자산':>15}{'배':>7}{'연평균':>8}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}")
            for _점, _sig, _갭v, _자리v, _비중v, _r in _벌[:5]:
                print(f"        {_sig:<22}{_갭v:>6.1f}{_자리v:>5}{_비중v:>6.0%}"
                      f"{_r['끝']:>15,.0f}{_r['끝'] / _시드:>6.1f}배{_r['연']:>7.1f}%"
                      f"{_r['낙']:>7.1f}%{_r['산']:>7}{_점:>9.2f}")
            _점, _sig, _갭v, _자리v, _비중v, _r = _벌[0]
            _거름 = _풀규칙S(아래, 위, _sig)
            _옵 = dict(상대갭=_갭v, 하루상한=_자리v, 비중=_비중v, 시총하한=0, 시총상한=999999)
            _a = 시뮬(_c(_거름, **_옵), 시작년="2010", 끝년="2020")
            _b = 시뮬(_c(_거름, **_옵), 시작년="2021", 끝년="2026",
                      시드=(_a["끝"] if _a else None))
            print(f"        앞뒤로 갈라 — 앞 연 {(_a['연'] if _a else 0):>5.1f}%"
                  f" (낙폭 {(_a['낙'] if _a else 0):>5.1f}% · {(_a['산'] if _a else 0)}건)"
                  f"  ·  뒤 연 {(_b['연'] if _b else 0):>5.1f}%"
                  f" (낙폭 {(_b['낙'] if _b else 0):>5.1f}% · {(_b['산'] if _b else 0)}건)"
                  f"   {'✅ 둘 다' if (_a and _b and _a['연'] > 0 and _b['연'] > 0) else '❌ 갈린다'}")
            return (_거름, _옵, _r, f"{_sig} · 갭{_갭v:g} · 자리{_자리v} · 비중{_비중v:.0%}")

        # ① 중형 전용 (처음이다) · 대형 전용
        _중S = _최고찾기S(2000.0, 10000.0, "중형 2,000억~1조")
        _대S = _최고찾기S(10000.0, 9.9e9, "대형 1조↑")

        # ② 소형 규칙 제 몫
        _소S = 시뮬(_c(_H))
        print(f"\n     ── [소형] 지금 규칙 Ⓗ ──")
        print(f"        {_소S['끝']:,.0f}원 · {_소S['끝'] / _시드:.1f}배 · 연 {_소S['연']:.1f}%"
              f" · 낙폭 {_소S['낙']:.1f}% · 산 것 {_소S['산']}")

        # ③ 자산을 나눠 담는다 — **합친 낙폭**까지
        print("\n     ③ ⭐⭐⭐ **자산을 나눠 담으면** — 얹는 게 아니라 따로 굴린다")
        print("        ⚠️ 끝 자산만 더하면 안 된다. **날마다 합쳐 낙폭을 다시 잰다**")
        if not (_중S and _대S):
            print("        🔴 중형·대형 중 규칙이 안 선 것이 있다 — 나눠 담기 생략")
        else:
            print(f"        {'소:중:대':<12}{'끝 자산':>16}{'배':>7}{'연평균':>8}"
                  f"{'합친 낙폭':>10}{'소형만 대비':>11}")
            for _소몫, _중몫, _대몫 in ((1.0, 0.0, 0.0), (0.8, 0.1, 0.1), (0.7, 0.2, 0.1),
                                      (0.6, 0.2, 0.2), (0.5, 0.3, 0.2), (0.4, 0.3, 0.3)):
                _곡들 = []
                _끝합 = 0.0
                for _몫, _거름, _옵 in ((_소몫, _H, {}),
                                       (_중몫, _중S[0], _중S[1]),
                                       (_대몫, _대S[0], _대S[1])):
                    if _몫 <= 0:
                        continue
                    _r = 시뮬(_c(_거름, **_옵), 시드=_시드 * _몫)
                    if not _r:
                        continue
                    _끝합 += _r["끝"]
                    _곡들.append((_몫, _r))
                if not _곡들:
                    continue
                # 합친 낙폭 — 몫을 가중해 대충 잰다 (곡선을 안 남기므로 상한으로 본다)
                _낙합 = sum(_몫 * abs(_r["낙"]) for _몫, _r in _곡들) / sum(
                    _몫 for _몫, _ in _곡들)
                _해수S = 11.0
                _연합 = ((_끝합 / _시드) ** (1 / _해수S) - 1) * 100
                print(f"        {_소몫:.0%}:{_중몫:.0%}:{_대몫:.0%}      "
                      f"{_끝합:>16,.0f}{_끝합 / _시드:>6.1f}배{_연합:>7.1f}%"
                      f"{-_낙합:>9.1f}%{_끝합 / _소S['끝'] * 100:>10.0f}%")
            print("        ⚠️ 「합친 낙폭」은 몫으로 가중한 **어림값**이다 —")
            print("           셋이 같은 날 함께 빠지지 않으면 실제로는 이보다 **작다**")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **BIGONLY — 대형주만의 독립 규칙 (`_H` 를 한 번도 안 쓴다)** (2026-09-29) ══
    if _ONLY == "BIGONLY" or "BIGONLY" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── BIGONLY ⭐⭐⭐ **대형주는 대형주만의 규칙 — 소형 규칙을 안 쓴다** ──")
        print("=" * 122)
        print("     여기서는 **여덟 층 전부**를 대형 자료 위에서 새로 세운다.")
        print("     ⚠️ 소형과 안 섞이면 하루 후보가 전부 대형이라 **중앙갭도 대형이 만든다** —")
        print("        그래서 상대갭을 넘을 수 있다 (B73 에서 37건이 사졌다)")

        for _컷B2, _름B2 in ((2000.0, "2,000억↑"), (10000.0, "1조↑")):
            print("\n" + "─" * 110)
            print(f"  ══ 풀 = 시총 {_름B2} (소형이 **아예 없다**) ══")
            print("─" * 110)

            # ── ① 재료풀 + ② 문 (대형에서 다시 고른다) ──
            def _큰풀(x, _c3=_컷B2):
                return (x.get("시총억") or 0) >= _c3

            _풀 = [x for x in 사건 if _큰풀(x)]
            print(f"     ① 풀 — 사건 {len(_풀):,}건 · 종목 {len({x['code'] for x in _풀}):,}")

            def _문B2(잉=None, 부=None, 대금=None):
                def _f(x, _a=잉, _b=부, _d=대금):
                    if not _큰풀(x):
                        return False
                    if _a is not None and not (x.get("잉여금") is not None
                                               and x["잉여금"] >= _a):
                        return False
                    if _b is not None and not (x.get("부채") is not None
                                               and x["부채"] <= _b):
                        return False
                    if _d is not None and not (x.get("대금억") is not None
                                               and x["대금억"] >= _d):
                        return False
                    return True
                return _f

            print(f"     ② 문 — 대형에서 다시 고른다 (지금 값 잉여금≥{R.잉여금하한:g} · 부채≤{R.부채상한:g} · 대금≥{R.대금하한억:g})")
            print(f"        {'문':<34}{'남는 사건':>10}{'20일 이김':>10}{'평균 수익':>10}")
            for _름, _잉, _부, _대 in (("(문 없음)", None, None, None),
                                     ("지금 값 그대로", R.잉여금하한, R.부채상한, R.대금하한억),
                                     ("잉여금만 ≥30", 30.0, None, None),
                                     ("부채만 ≤80", None, 80.0, None),
                                     ("대금 ≥50억", None, None, 50.0),
                                     ("대금 ≥200억", None, None, 200.0),
                                     ("잉여금≥50 · 부채≤60", 50.0, 60.0, None)):
                _fn = _문B2(_잉, _부, _대)
                _v = [x["_20"] for x in _풀 if _fn(x) and x.get("_20") is not None]
                if len(_v) < 100:
                    print(f"        {_름:<34}{len(_v):>10,}   표본 부족")
                    continue
                print(f"        {_름:<34}{len(_v):>10,}"
                      f"{sum(1 for z in _v if z > 0) / len(_v) * 100:>9.1f}%"
                      f"{sum(_v) / len(_v):>+10.2f}")

            # ── ③ 신호 — B129 가 대형에서 찾은 것들 ──
            def _신호B2(이름):
                if 이름 == "시장낙폭≤-10":
                    return lambda x: (x.get("시장낙폭") is not None and x["시장낙폭"] <= -10)
                if 이름 == "시장낙폭≤-15":
                    return lambda x: (x.get("시장낙폭") is not None and x["시장낙폭"] <= -15)
                if 이름 == "볼120≤-1.5σ":
                    return lambda x: (x.get("볼120") is not None and x["볼120"] <= -1.5)
                if 이름 == "볼60≤-1.5σ":
                    return lambda x: (x.get("볼60") is not None and x["볼60"] <= -1.5)
                if 이름 == "낙40≤-30%":
                    return lambda x: (x.get("낙40") is not None and x["낙40"] <= -30)
                if 이름 == "60일선≤-20%":
                    return lambda x: (x.get("60일선대비") is not None and x["60일선대비"] <= -20)
                # ⭐ 2026-09-29 — **연휴 227차에서 대형 1위였던 재료.** 빠뜨렸었다.
                #    「그 종목 평소 등락폭 대비 20일 낙폭이 몇 배인가」 — 절대 % 가 아니라
                #    **그 종목 기준**이라 덜 움직이는 대형에도 통한다
                #      중형 평소-2.5배↓ 69.7%(+25.0p) · 대형 **70.2%(+23.0p)** · 초대형 -2.0배↓ 61.8%
                if 이름 == "평소-2.0배↓":
                    return lambda x: _표준낙(x, -2.0)
                if 이름 == "평소-2.5배↓":
                    return lambda x: _표준낙(x, -2.5)
                if 이름 == "평소-3.0배↓":
                    return lambda x: _표준낙(x, -3.0)
                if 이름 == "평소-2.5배↓+시장낙폭-10":
                    return lambda x: (_표준낙(x, -2.5) and x.get("시장낙폭") is not None
                                      and x["시장낙폭"] <= -10)
                if 이름 == "평소-2.5배↓+볼120-1.5σ":
                    return lambda x: (_표준낙(x, -2.5) and x.get("볼120") is not None
                                      and x["볼120"] <= -1.5)
                return lambda x: True

            _신호들 = ("(신호 없음)", "시장낙폭≤-10", "시장낙폭≤-15", "볼120≤-1.5σ",
                     "볼60≤-1.5σ", "낙40≤-30%", "60일선≤-20%",
                     # ⭐ 연휴 227차 대형 1위 — 빠뜨렸던 것
                     "평소-2.0배↓", "평소-2.5배↓", "평소-3.0배↓",
                     "평소-2.5배↓+시장낙폭-10", "평소-2.5배↓+볼120-1.5σ")

            def _띠규칙B2(신호, 잉=None, 부=None, 대금=None):
                _문 = _문B2(잉, 부, 대금)
                _sig = _신호B2(신호)
                def _f(x):
                    return _문(x) and _sig(x)
                return _f

            # ── ④~⑧ 혼자 서나 (소형 없이 그 규칙만으로 자본 시뮬) ──
            print("\n     ③~⑧ ⭐⭐⭐ **혼자 선다** — 소형 없이 이 규칙만으로 11년 굴린다")
            print("        상대갭은 **대형 후보들끼리의 중앙값**으로 잰다 (소형과 안 섞인다)")
            print(f"        {'신호':<16}{'상대갭':>8}{'자리':>5}{'비중':>6}"
                  f"{'끝 자산':>16}{'배':>7}{'연평균':>8}{'낙폭':>8}{'산 것':>7}")
            _최고B2 = []
            for _sig in _신호들:
                _거름 = _띠규칙B2(_sig, R.잉여금하한, R.부채상한, R.대금하한억)
                for _갭v in (-3.5, -2.0, -1.0):
                    for _자리v, _비중v in ((4, 0.20), (4, 0.30), (2, 0.40), (6, 0.20)):
                        _r = 시뮬(_c(_거름, 상대갭=_갭v, 하루상한=_자리v, 비중=_비중v,
                                    시총하한=0, 시총상한=999999))
                        if not _r or _r["산"] < 20:
                            continue
                        _배 = _r["끝"] / _시드
                        _최고B2.append((_r["끝"], _sig, _갭v, _자리v, _비중v, _r))
                        if _배 >= 2.0:
                            print(f"        {_sig:<16}{_갭v:>8.1f}{_자리v:>5}{_비중v:>6.0%}"
                                  f"{_r['끝']:>16,.0f}{_배:>6.1f}배{_r['연']:>7.1f}%"
                                  f"{_r['낙']:>7.1f}%{_r['산']:>7}")
            _최고B2.sort(key=lambda z: -z[0])
            if not _최고B2:
                print("        🔴 산 것이 20건을 넘는 조합이 하나도 없다 — 이 풀로는 규칙이 안 선다")
                continue
            print(f"\n     ⭐ 위 다섯 (산 것 20건↑ · 시드 {_시드:,.0f}원)")
            print(f"        {'신호':<16}{'상대갭':>8}{'자리':>5}{'비중':>6}"
                  f"{'끝 자산':>16}{'배':>7}{'연평균':>8}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>9}")
            for _끝, _sig, _갭v, _자리v, _비중v, _r in _최고B2[:5]:
                print(f"        {_sig:<16}{_갭v:>8.1f}{_자리v:>5}{_비중v:>6.0%}"
                      f"{_끝:>16,.0f}{_끝 / _시드:>6.1f}배{_r['연']:>7.1f}%"
                      f"{_r['낙']:>7.1f}%{_r['산']:>7}"
                      f"{_r['연'] / max(abs(_r['낙']), 3.0):>9.2f}")

            # ── 앞뒤로 갈라도 서나 ──
            print("\n     ⑨ 위 셋을 **앞뒤로 갈라** 본다 (한쪽만이면 잡음이다)")
            for _끝, _sig, _갭v, _자리v, _비중v, _r in _최고B2[:3]:
                _거름 = _띠규칙B2(_sig, R.잉여금하한, R.부채상한, R.대금하한억)
                _옵 = dict(상대갭=_갭v, 하루상한=_자리v, 비중=_비중v,
                          시총하한=0, 시총상한=999999)
                _a = 시뮬(_c(_거름, **_옵), 시작년="2010", 끝년="2020")
                _b = 시뮬(_c(_거름, **_옵), 시작년="2021", 끝년="2026",
                          시드=(_a["끝"] if _a else None))
                print(f"\n        [{_sig} · 갭{_갭v:g} · 자리{_자리v} · 비중{_비중v:.0%}]")
                for _라, _z in (("앞 2010~2020", _a), ("뒤 2021~2026", _b)):
                    if _z:
                        print(f"          {_라}: {_z['끝']:>15,.0f}원 · 연 {_z['연']:>6.1f}%"
                              f" · 낙폭 {_z['낙']:>6.1f}% · 산 것 {_z['산']:>4}")
                    else:
                        print(f"          {_라}: (안 나왔다)")
                _둘다B2 = (_a and _b and _a["연"] > 0 and _b["연"] > 0)
                print(f"          ⇒ {'✅ 앞뒤 둘 다 벌었다' if _둘다B2 else '❌ 한쪽이 무너진다'}")

        # ⚠️ 여기에 있던 「소형 규칙과 합치기」 덩어리를 **들어냈다** (2026-09-29).
        #    사용자: 「대형주는 대형주만의 규칙」 — 열 번 넘게 들은 말이다.
        #    이 절은 `_H`(소형 규칙)를 **코드에서 한 번도 안 쓴다.** 그게 이 절의 전부다.
        #    합치는 이야기는 대형 규칙이 **혼자 선 다음에** 따로 한다
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **NOGAP — 대형에서 상대갭 문을 아예 없애면** (2026-09-28 · 사용자 물음) ══
    if _ONLY == "NOGAP" or "NOGAP" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── NOGAP ⭐⭐⭐ **「왜 대형 쪽은 뭐가 하나도 안 나오지?」 — 문 하나에서 전멸한다** ──")
        print("=" * 122)
        print("     11년치를 문마다 세어 보면")
        print("        문                소형        중형     대형 1조↑")
        print("        ④ 신호          25,708      476        **93**   (18.4% — 소형 20.5% 와 비슷)")
        print("        ⑤ 상대갭 -3.5%p    521       13         **0**   ← 한 번도 못 넘었다")
        print("     상대갭 = 「예상 시초가가 **그날 후보 중앙값보다** 3.5%p 더 빠졌나」.")
        print("     소형은 거래가 얇아 동시호가에 크게 튄다. 대형은 두꺼워 안 움직인다.")
        print("     중앙값은 후보 대부분인 **소형이 만든다** ⇒ 대형은 구조적으로 못 넘는다.")
        print("     ⚠️ GROUP 에선 -1.0%p 까지만 풀어 봤다. **아예 없애 보지 않았다** — 여기서 한다")

        _밑N = 시뮬(_c(_H))
        print(f"\n     바탕(지금) — {_밑N['끝']:,.0f}원 · 낙폭 {_밑N['낙']:.1f}% · 산 것 {_밑N['산']}")

        def _대N(x):
            return (x.get("시총억") or 0) >= 10000

        def _큰N(x):
            return (x.get("시총억") or 0) >= 2000

        def _중N(x):
            return 2000 <= (x.get("시총억") or 0) < 10000

        _이긴N = []

        def _줄N(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<48}{'(안 나왔다)':>16}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑N["끝"] and _r["낙"] >= _밑N["낙"] - 1.0) else (
                "△" if _r["끝"] >= _밑N["끝"] else "❌")
            print(f"     {이름:<48}{_r['끝']:>16,.0f}{_r['끝'] / _밑N['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _밑N['산']:>+7}  {_판}")
            if _r["끝"] >= _밑N["끝"]:
                _이긴N.append((이름, 옵, _r))
            return _r

        _머N = f"     {'설정':<48}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>7}  판정"

        # ── ① 문을 끝까지 연다 ──
        print("\n     ① **대형(1조↑) 상대갭 문을 끝까지 연다** (자리는 지금 그대로)")
        print(_머N)
        for _t in (-0.5, 0.0, 1.0, 2.0, 99.0):
            _라 = ("문 없음 (신호만 보고 산다)" if _t >= 99 else f"{_t:+g}%p")
            _줄N(f"대형 1조↑ : {_라}", {"무리갭": [(_대N, "대형", _t)]})

        # ── ② 문을 열고 자리도 준다 ──
        print("\n     ② 문을 열고 **대형 전용 자리도** 준다 (소형을 안 밀어낸다)")
        print(_머N)
        for _t in (0.0, 2.0, 99.0):
            for _n in (1, 2):
                _라 = ("문 없음" if _t >= 99 else f"{_t:+g}%p")
                _줄N(f"대형 1조↑ : {_라} + 자리 {_n}",
                     {"무리갭": [(_대N, "대형", _t)], "무리자리": [(_대N, "대형", _n)]})

        # ── ③ 2,000억↑ 로 넓히면 ──
        print("\n     ③ **2,000억↑** 로 넓히면 (중형까지 같이)")
        print(_머N)
        for _t in (-1.0, 0.0, 2.0):
            _줄N(f"2천억↑ : {_t:+g}%p", {"무리갭": [(_큰N, "2천억↑", _t)]})
            _줄N(f"2천억↑ : {_t:+g}%p + 자리 2",
                 {"무리갭": [(_큰N, "2천억↑", _t)], "무리자리": [(_큰N, "2천억↑", 2)]})

        # ── ④ 중형만 끝까지 ──
        print("\n     ④ **중형(2천억~1조)** 만 끝까지 (GROUP 에선 -1.5%p 가 107% 였다)")
        print(_머N)
        for _t in (-1.0, -0.5, 0.0, 2.0):
            _줄N(f"중형 : {_t:+g}%p", {"무리갭": [(_중N, "중형", _t)]})

        # ── ⑤ 돈으로 — 띠마다 ──
        print("\n     ⑤ ⭐⭐⭐ **수익률이 아니라 돈** — 이긴 것들의 띠별 넣은 돈·번 돈")

        def _돈N(이름, 옵):
            _기N = []
            _r = 시뮬(_c(_H, **옵), 기록=_기N)
            if not _r:
                return
            _cN = {}
            for _dN, _kN, _sN, _pN, _yN, _qN, _shN in _기N:
                _tN = ("소형" if (_sN or 0) < 2000 else
                       "중형" if (_sN or 0) < 10000 else "대형")
                _inN = (_shN or 0) * (_pN or 0)
                _vN = _cN.setdefault(_tN, [0, 0.0, 0.0])
                _vN[0] += 1
                _vN[1] += _inN
                _vN[2] += _inN * (_yN or 0) / 100.0
            print(f"\n        [{이름}] 끝 {_r['끝']:,.0f}원 · 낙폭 {_r['낙']:.1f}%")
            print(f"        {'띠':<6}{'몫':>6}{'넣은 돈':>16}{'번 돈':>16}"
                  f"{'한 건 넣은 돈':>16}{'한 건 번 돈':>15}{'수익률':>9}")
            for _tN in ("소형", "중형", "대형"):
                _vN = _cN.get(_tN)
                if not _vN:
                    print(f"        {_tN:<6}{0:>6}")
                    continue
                _nN, _iN, _eN = _vN
                print(f"        {_tN:<6}{_nN:>6}{_iN:>16,.0f}{_eN:>+16,.0f}"
                      f"{_iN / _nN:>16,.0f}{_eN / _nN:>+15,.0f}"
                      f"{_eN / _iN * 100 if _iN else 0:>8.1f}%")

        _돈N("지금 (아무것도 안 함)", {})
        for _nmN, _opN, _rN in sorted(_이긴N, key=lambda z: -z[2]["끝"])[:4]:
            _돈N(_nmN, _opN)

        # ── ⑥ 이긴 것만 걷기 ──
        print("\n     ⑥ 바탕을 넘은 것만 **증분 걷기** (앞 2010~2020 / 뒤 2021~2026)")
        if not _이긴N:
            print("        바탕을 넘은 것이 **하나도 없다.**")
            print("        ⇒ 문을 아예 없애도 대형은 값이 없다 —")
            print("           「대형주는 이 방식(빠진 것을 산다)에 안 맞는다」고 못 박으면 된다")
        for _nmN, _opN, _rN in sorted(_이긴N, key=lambda z: -z[2]["끝"])[:5]:
            print(f"\n        [{_nmN}]  ({_rN['끝'] / _밑N['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_opN), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **DIG — 대형 건이 반도체 특수인가 · 반도체는 왜 돈이 주나 · 고친 걷기** (2026-09-28) ══
    if _ONLY == "DIG" or "DIG" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DIG ⭐⭐⭐ **퇴근 전 물음 둘을 판다 + B125 승자를 고친 걷기로 다시** ──")
        print("=" * 122)
        _밑D2 = 시뮬(_c(_H))
        print(f"     바탕(지금) — {_밑D2['끝']:,.0f}원 · 낙폭 {_밑D2['낙']:.1f}% · 산 것 {_밑D2['산']}")

        _이름D = {}
        try:
            _bD = json.load(io.open(os.path.join(O._DATA, "stock-base.json"), encoding="utf-8-sig"))
            for _cD, _vD in (_bD.get("종목") or _bD).items():
                if isinstance(_vD, dict):
                    _이름D[_cD] = (_vD.get("종목명") or _vD.get("이름") or "")
        except Exception:  # noqa: BLE001
            pass

        def _섹D(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _중D(x):
            return 2000 <= (x.get("시총억") or 0) < 10000

        def _대D(x):
            return (x.get("시총억") or 0) >= 10000

        def _바구니D(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        _반D = next((k for k in R.섹터규칙 if "반도체" in k), None)
        _승자D = [
            ("섹터 갈래만 -1.5%p", {"무리갭": [(_섹D, "섹터", -1.5)]}),
            ("섹터 자리 2개를 더", {"무리자리": [(_섹D, "섹터", 2)]}),
            ("중형만 -1.5%p", {"무리갭": [(_중D, "중형", -1.5)]}),
            ("대형만 -1.5%p", {"무리갭": [(_대D, "대형", -1.5)]}),
        ]
        for _nm in ("휴머노이드/로봇", "전력 인프라/변압기", "원전 기자재"):
            if _nm in R.섹터규칙:
                _f = _바구니D(_nm)
                _승자D.append((f"[{_nm}] -2.0%p + 자리 1",
                               {"무리갭": [(_f, _nm, -2.0)], "무리자리": [(_f, _nm, 1)]}))

        # ══ ① 고친 걷기 ══
        print("\n     ① ⭐⭐⭐ **고친 걷기** — B125 의 걷기는 자기 자신과 견줘서 전부 +0.0% 였다")
        print("        이번엔 **옵을 준 쪽 vs 안 준 쪽**을 견준다 (_옵걷기)")
        for _nmD, _옵D in _승자D:
            _r = 시뮬(_c(_H, **_옵D))
            if not _r:
                continue
            print(f"\n        [{_nmD}]  전체 {_r['끝'] / _밑D2['끝'] * 100:.0f}%"
                  f" · 낙폭 {_r['낙']:.1f}% · 산 것 {_r['산']}")
            _걷기찍기(_옵걷기(_옵D), 들여="          ")

        # ══ ② 대형·중형으로 산 것이 정확히 무엇인가 ══
        print("\n     ② ⭐⭐⭐ **대형·중형으로 산 것이 무엇인가** — 2024~2026 반도체 특수인가?")
        for _nmD, _옵D in _승자D[:4]:
            _기D = []
            _r = 시뮬(_c(_H, **_옵D), 기록=_기D)
            _큰거래 = [z for z in _기D if (z[2] or 0) >= 2000]
            if not _큰거래:
                print(f"\n        [{_nmD}] — 2,000억↑ 로 산 것이 **없다**")
                continue
            print(f"\n        [{_nmD}] — 2,000억↑ 거래 {len(_큰거래)}몫")
            print(f"        {'산 날':<11}{'코드':<8}{'이름':<14}{'시총억':>9}"
                  f"{'넣은 돈':>14}{'수익':>8}{'번 돈':>14}{'섹터':<16}")
            for _d, _c0, _시총, _원시, _익, _청, _주 in sorted(_큰거래):
                _넣 = (_주 or 0) * (_원시 or 0)
                print(f"        {str(_d):<11}{_c0:<8}{_이름D.get(_c0, '')[:12]:<14}"
                      f"{(_시총 or 0):>9,.0f}{_넣:>14,.0f}{(_익 or 0):>+7.1f}%"
                      f"{_넣 * (_익 or 0) / 100:>+14,.0f}  {str(_사슬섹터.get(_c0) or '-')[:14]:<16}")

        # ══ ③ 해마다 ══
        print("\n     ③ **해마다** — 큰 것으로 산 게 어느 해에 몰려 있나")
        for _nmD, _옵D in _승자D[:2]:
            _기D = []
            시뮬(_c(_H, **_옵D), 기록=_기D)
            print(f"\n        [{_nmD}]")
            print(f"        {'해':<7}{'큰 것 몫':>9}{'큰 것 번 돈':>16}{'전체 몫':>9}{'전체 번 돈':>16}")
            for _y in range(2016, 2027):
                _벌 = [z for z in _기D if str(z[0])[:4] == str(_y)]
                _큰 = [z for z in _벌 if (z[2] or 0) >= 2000]
                _돈큰 = sum((z[6] or 0) * (z[3] or 0) * (z[4] or 0) / 100 for z in _큰)
                _돈전 = sum((z[6] or 0) * (z[3] or 0) * (z[4] or 0) / 100 for z in _벌)
                if not _벌:
                    continue
                print(f"        {_y:<7}{len(_큰):>9}{_돈큰:>+16,.0f}{len(_벌):>9}{_돈전:>+16,.0f}")

        # ══ ④ 2024~2026 을 빼면 ══
        print("\n     ④ ⭐⭐ **2024~2026 을 빼고** 다시 — 반도체 특수를 빼도 남나")
        print(f"        {'설정':<34}{'2016~2023 끝':>18}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}")
        _밑23 = 시뮬(_c(_H), 끝년="2023")
        if _밑23:
            print(f"        {'[견줌] 지금 규칙':<34}{_밑23['끝']:>18,.0f}{100:>8.0f}%"
                  f"{_밑23['낙']:>8.1f}%{_밑23['산']:>7}")
            for _nmD, _옵D in _승자D:
                _r = 시뮬(_c(_H, **_옵D), 끝년="2023")
                if not _r:
                    continue
                _판 = "⭐" if _r["끝"] >= _밑23["끝"] else "❌"
                print(f"        {_nmD[:32]:<34}{_r['끝']:>18,.0f}"
                      f"{_r['끝'] / _밑23['끝'] * 100:>8.0f}%{_r['낙']:>8.1f}%{_r['산']:>7}  {_판}")

        # ══ ⑤ 반도체는 왜 돈이 주나 ══
        if _반D:
            print(f"\n     ⑤ ⭐⭐⭐ **[{_반D}] 는 왜 67% 인가** — 수익이 나쁜가, 아니면 자리·현금을 먹는가")
            _f반 = _바구니D(_반D)
            _옵반 = {"무리갭": [(_f반, _반D, -2.0)], "무리자리": [(_f반, _반D, 1)]}
            _기반 = []
            _r반 = 시뮬(_c(_H, **_옵반), 기록=_기반)
            _기밑 = []
            시뮬(_c(_H), 기록=_기밑)
            if _r반:
                _산반 = [z for z in _기반 if _사슬섹터.get(z[1]) == _반D]
                print(f"        끝 {_r반['끝']:,.0f}원 ({_r반['끝'] / _밑D2['끝'] * 100:.0f}%)"
                      f" · 낙폭 {_r반['낙']:.1f}% · 몫 {len(_기반)} (바탕 {len(_기밑)})")
                print(f"\n        ㉮ **반도체로 산 것 자체**가 나쁜가")
                if _산반:
                    _v = [z[4] for z in _산반]
                    _넣 = sum((z[6] or 0) * (z[3] or 0) for z in _산반)
                    _번 = sum((z[6] or 0) * (z[3] or 0) * (z[4] or 0) / 100 for z in _산반)
                    print(f"           반도체 몫 {len(_산반)} · 평균 수익 {sum(_v) / len(_v):+.1f}%"
                          f" · 이긴 비율 {sum(1 for z in _v if z > 0) / len(_v) * 100:.0f}%")
                    print(f"           넣은 돈 {_넣:,.0f} · 번 돈 {_번:+,.0f}"
                          f" · 가장 나쁜 {min(_v):+.1f}%")
                    print(f"        {'산 날':<11}{'코드':<8}{'이름':<14}{'시총억':>9}"
                          f"{'넣은 돈':>14}{'수익':>8}")
                    for _d, _c0, _시총, _원시, _익, _청, _주 in sorted(_산반)[:15]:
                        print(f"           {str(_d):<11}{_c0:<8}{_이름D.get(_c0, '')[:12]:<14}"
                              f"{(_시총 or 0):>9,.0f}{(_주 or 0) * (_원시 or 0):>14,.0f}"
                              f"{(_익 or 0):>+7.1f}%")
                else:
                    print("           반도체로 산 것이 **없다** — 그러면 원인은 밀어내기다")
                print(f"\n        ㉯ **남을 밀어냈나** — 바탕과 견줘 사라진 매수")
                _열밑 = {(z[0], z[1]) for z in _기밑}
                _열반 = {(z[0], z[1]) for z in _기반}
                _사라짐 = _열밑 - _열반
                _새로 = _열반 - _열밑
                print(f"           바탕에 있다가 **사라진 매수 {len(_사라짐)}건** · 새로 생긴 것 {len(_새로)}건")
                _잃 = [z for z in _기밑 if (z[0], z[1]) in _사라짐]
                if _잃:
                    _v2 = [z[4] for z in _잃]
                    _돈2 = sum((z[6] or 0) * (z[3] or 0) * (z[4] or 0) / 100 for z in _잃)
                    print(f"           사라진 것들의 평균 수익 {sum(_v2) / len(_v2):+.1f}%"
                          f" · 그것들이 벌었던 돈 {_돈2:+,.0f}")
                    print("           ⇒ **이 돈을 못 벌게 된 것이 손실의 원인**이라면 「밀어내기」다")
                print(f"\n        ㉰ 고친 걷기")
                _걷기찍기(_옵걷기(_옵반), 들여="           ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **BIGSEARCH — 대형주 자료로 규칙을 처음부터 찾는다** (2026-09-28 · 사용자 물음) ══
    if _ONLY == "BIGSEARCH" or "BIGSEARCH" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── BIGSEARCH ⭐⭐⭐ **「대형주만의 규칙은 못 찾은 거네?」 — 맞다. 여기서 찾는다** ──")
        print("=" * 122)
        print("     지금까지 한 것은 전부 **소형 규칙을 대형에 끼워 넣기**였다:")
        print("        · 크기 문만 열었다 (섹터규칙_큰회사)  · 소형 문턱에 배수만 곱했다 (갭무름)")
        print("        · 소형 규칙이 부른 대형에게 자리·문턱만 달리 줬다 (무리자리·무리갭)")
        print("     볼린저 -1σ · 20일 낙폭 -10% · 상대갭 -3.5%p 는 **전부 소형 자료로 고른 값**이다.")
        print("     대형 자료로 「무엇이 대형주의 상승을 앞서 알리나」를 훑은 적이 **한 번도 없다**.")

        _큰컷B = 2000.0

        def _큰터B(x):
            return (재무통과(x) and 대금통과(x)
                    and (x.get("시총억") or 0) >= _큰컷B)

        _큰칸B = [x for x in 사건 if _큰터B(x) and x.get("_20") is not None]
        if len(_큰칸B) < 500:
            print(f"\n     🔴 대형 표본이 {len(_큰칸B)}건뿐이다 — 훑을 수 없다")
        else:
            _앞해B = {"2016", "2017", "2018", "2019", "2020"}
            _앞B = [x for x in _큰칸B if str(x.get("해")) in _앞해B]
            _뒤B = [x for x in _큰칸B if str(x.get("해")) not in _앞해B]

            def _바탕B(칸):
                _v = [x["_20"] for x in 칸]
                if not _v:
                    return (0.0, 0.0, 0)
                return (sum(1 for z in _v if z > 0) / len(_v) * 100,
                        sum(_v) / len(_v), len(_v))

            _전바B, _앞바B, _뒤바B = _바탕B(_큰칸B), _바탕B(_앞B), _바탕B(_뒤B)
            print(f"\n     ① **대형만의 바탕** (시총 {_큰컷B:,.0f}억↑ · 재무·대금 문만 통과 · 신호 조건 없음)")
            print(f"        {'':<14}{'표본':>9}{'20일 이김':>11}{'평균 수익':>11}")
            for _라B, _bB in (("전체 11년", _전바B), ("앞 2016~2020", _앞바B), ("뒤 2021~2026", _뒤바B)):
                print(f"        {_라B:<14}{_bB[2]:>9,}{_bB[0]:>10.1f}%{_bB[1]:>+10.2f}")
            print("        ⚠️ 이 바탕은 **대형만의 것**이다 — 소형 바탕과 견주면 안 된다 (다른 무리다)")

            # ── ② 재료 하나씩 격자로 ──
            def _재보기B(fn):
                _a = [x["_20"] for x in _앞B if fn(x)]
                _b = [x["_20"] for x in _뒤B if fn(x)]
                if len(_a) < 40 or len(_b) < 40:
                    return None
                _ai = sum(1 for z in _a if z > 0) / len(_a) * 100
                _bi = sum(1 for z in _b if z > 0) / len(_b) * 100
                _ap, _bp = sum(_a) / len(_a), sum(_b) / len(_b)
                return (_ai, _ap, len(_a), _bi, _bp, len(_b))

            def _문턱fnB(칸이름, 문):
                def _f(x, _k=칸이름, _t=문):
                    _v = x.get(_k)
                    return _v is not None and _v <= _t
                return _f

            def _위fnB(칸이름, 문):
                def _f(x, _k=칸이름, _t=문):
                    _v = x.get(_k)
                    return _v is not None and _v >= _t
                return _f

            _후보B = []
            for _w in (5, 10, 20, 40, 60, 120):
                for _t in (-0.5, -1.0, -1.5, -2.0):
                    _후보B.append((f"볼{_w} ≤ {_t:g}σ", _문턱fnB(f"볼{_w}", _t)))
            for _w in (5, 10, 20, 40, 60, 120, 250):
                for _t in (-5.0, -10.0, -15.0, -20.0, -30.0):
                    _후보B.append((f"낙{_w} ≤ {_t:g}%", _문턱fnB(f"낙{_w}", _t)))
            for _k, _ts in (("외인20", (-2.0, -1.0, 1.0, 2.0)), ("기관20", (-2.0, -1.0, 1.0, 2.0)),
                            ("외인5", (-1.0, 1.0)), ("기관5", (-1.0, 1.0)),
                            ("PBR", (0.5, 0.8, 1.2)), ("ROE", (3.0, 8.0, 15.0)),
                            ("상대강도", (-20.0, -10.0, 10.0)), ("섹터대비", (-10.0, -5.0, 5.0)),
                            ("60일선대비", (-20.0, -10.0, -5.0)), ("시장낙폭", (-15.0, -10.0, -5.0)),
                            ("회전율", (0.3, 1.0)), ("영업이익률", (5.0, 10.0))):
                for _t in _ts:
                    _후보B.append((f"{_k} ≤ {_t:g}", _문턱fnB(_k, _t)))
                    _후보B.append((f"{_k} ≥ {_t:g}", _위fnB(_k, _t)))

            print(f"\n     ② 재료 **{len(_후보B)}가지**를 훑는다 — 기간을 갈라 **앞뒤 둘 다** 바탕보다 나은 것만")
            _산것B = []
            for _라B, _fnB in _후보B:
                _r = _재보기B(_fnB)
                if not _r:
                    continue
                _ai, _ap, _an, _bi, _bp, _bn = _r
                if _ai > _앞바B[0] and _bi > _뒤바B[0] and _ap > _앞바B[1] and _bp > _뒤바B[1]:
                    _산것B.append((min(_ai - _앞바B[0], _bi - _뒤바B[0]), _라B, _fnB, _r))
            _산것B.sort(key=lambda z: -z[0])
            print(f"        ⇒ **{len(_산것B)}가지**가 앞뒤 둘 다 넘었다 (훑은 것 {len(_후보B)})")
            print(f"        {'재료':<22}{'앞 표본':>8}{'앞 이김':>9}{'앞 수익':>9}"
                  f"{'뒤 표본':>8}{'뒤 이김':>9}{'뒤 수익':>9}{'약한 쪽':>9}")
            for _d, _라B, _fnB, _r in _산것B[:18]:
                _ai, _ap, _an, _bi, _bp, _bn = _r
                print(f"        {_라B:<22}{_an:>8,}{_ai:>8.1f}%{_ap:>+9.2f}"
                      f"{_bn:>8,}{_bi:>8.1f}%{_bp:>+9.2f}{_d:>+8.1f}p")
            if not _산것B:
                print("        🔴 **앞뒤 둘 다 넘은 재료가 하나도 없다** — 대형에는 이 재료들로 규칙이 안 선다")

            # ── ③ 둘씩 겹쳐 ──
            _쌍B = []
            for _i in range(min(6, len(_산것B))):
                for _j in range(_i + 1, min(8, len(_산것B))):
                    _d1, _n1, _f1, _ = _산것B[_i]
                    _d2, _n2, _f2, _ = _산것B[_j]

                    def _둘fn(x, _a=_f1, _b=_f2):
                        return _a(x) and _b(x)

                    _r = _재보기B(_둘fn)
                    if not _r:
                        continue
                    _ai, _ap, _an, _bi, _bp, _bn = _r
                    if _ai > _앞바B[0] and _bi > _뒤바B[0] and _ap > _앞바B[1] and _bp > _뒤바B[1]:
                        _쌍B.append((min(_ai - _앞바B[0], _bi - _뒤바B[0]),
                                    f"{_n1} + {_n2}", _둘fn, _r))
            _쌍B.sort(key=lambda z: -z[0])
            if _쌍B:
                print(f"\n     ③ 둘씩 겹친 것 — 앞뒤 둘 다 넘은 **{len(_쌍B)}쌍**")
                print(f"        {'재료 둘':<42}{'앞 표본':>8}{'앞 이김':>9}"
                      f"{'뒤 표본':>8}{'뒤 이김':>9}{'약한 쪽':>9}")
                for _d, _라B, _fnB, _r in _쌍B[:10]:
                    print(f"        {_라B:<42}{_r[2]:>8,}{_r[0]:>8.1f}%"
                          f"{_r[5]:>8,}{_r[3]:>8.1f}%{_d:>+8.1f}p")

            # ── ④ 돈으로 — Ⓗ 위에 OR 로 얹고 대형에 제 문턱·제 자리 ──
            print("\n     ④ ⭐⭐⭐ **돈으로** — Ⓗ 위에 OR 로 얹는다")
            print("        ⚠️ 대형에 **제 문턱(-2.0%p)과 제 자리(2개)** 를 같이 준다 —")
            print("           안 그러면 무엇을 찾아도 상대갭 -3.5 에서 전멸한다 (11년 93건 → 0건)")
            _밑B = 시뮬(_c(_H))
            print(f"        바탕(지금) — {_밑B['끝']:,.0f}원 · 낙폭 {_밑B['낙']:.1f}% · 산 것 {_밑B['산']}")

            def _큰무리B(x):
                return (x.get("시총억") or 0) >= _큰컷B

            _옵B = {"무리갭": [(_큰무리B, "대형", -2.0)],
                   "무리자리": [(_큰무리B, "대형", 2)]}
            print(f"\n        {'얹은 것':<44}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            _r0 = 시뮬(_c(_H, **_옵B))
            if _r0:
                print(f"        {'[견줌] 아무것도 안 얹고 문턱·자리만':<44}{_r0['끝']:>16,.0f}"
                      f"{_r0['끝'] / _밑B['끝'] * 100:>8.0f}%{_r0['낙']:>8.1f}%{_r0['산']:>7}")
            _이긴B = []
            for _d, _라B, _띠규칙B, _r in (_쌍B[:5] + _산것B[:8]):
                # _띠규칙B = **이 띠(대형) 자료로 이 절이 직접 찾아낸 규칙**이다.
                #    소형 값을 가져다 쓴 것이 아니다 — 그게 이 절의 존재 이유다
                def _얹B(x, _f=_띠규칙B):
                    if _큰터B(x) and _f(x):
                        return True
                    return _H(x)          # [견줌] Ⓗ 위에 OR 로만 더한다 (바탕은 소형 그대로 둔다)
                _rr = 시뮬(_c(_얹B, **_옵B))
                if not _rr:
                    continue
                _판B = "⭐" if (_rr["끝"] >= _밑B["끝"] and _rr["낙"] >= _밑B["낙"] - 1.0) else (
                    "△" if _rr["끝"] >= _밑B["끝"] else "❌")
                print(f"        {_라B[:42]:<44}{_rr['끝']:>16,.0f}"
                      f"{_rr['끝'] / _밑B['끝'] * 100:>8.0f}%{_rr['낙']:>8.1f}%{_rr['산']:>7}  {_판B}")
                if _rr["끝"] >= _밑B["끝"]:
                    _이긴B.append((_라B, _얹B, _rr))

            # ── ⑤ 증분 걷기 ──
            print("\n     ⑤ 바탕을 넘은 것만 **증분 걷기** (앞 2010~2020 / 뒤 2021~2026)")
            if not _이긴B:
                print("        바탕을 넘은 것이 **하나도 없다.**")
                print("        ⇒ 대형 자료로 처음부터 찾아도 돈이 안 는다 —")
                print("           그러면 「대형주는 이 방식(빠진 것을 산다)에 안 맞는다」고 못 박으면 된다")
            for _라B, _fnB, _rr in sorted(_이긴B, key=lambda z: -z[2]["끝"])[:5]:
                print(f"\n        [{_라B[:60]}]  ({_rr['끝'] / _밑B['끝'] * 100:.0f}%)")
                _걷기찍기(_걷기(_fnB, 옵=_옵B), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **AXIS — 규모·섹터 말고 다른 축으로 가른다** (2026-09-28 · 사용자 물음) ══
    if _ONLY == "AXIS" or "AXIS" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── AXIS ⭐⭐⭐ **「규모별, 섹터별 말고 또 구분해서 테스트해볼만한게 있나?」** ──")
        print("=" * 122)
        print("     덤프 130,197건을 가름마다 세어 보니 규모·섹터보다 **더 크게 갈리는 축**이 있었다")
        print("     (잣대 = 신호를 통과한 것 중 몇 %가 상대갭 문을 넘나 — 대형이 93건→0건이던 그 문)")
        print("        ① 그날 장 상태  크게 빠진 날 5.63% · 나머지 0.64~0.84%  → 7배 (**날**을 가른다)")
        print("        ② 주가          3,535원 아래 3.67% · 10,070원 위 0.98% → 3.7배 (호가 단위)")
        print("        ③ 코스피/코스닥  코스닥 1년 20.0건 · 코스피 3.3건        → 6배")

        _밑A = 시뮬(_c(_H))
        print(f"\n     바탕(지금) — {_밑A['끝']:,.0f}원 · 낙폭 {_밑A['낙']:.1f}% · 산 것 {_밑A['산']}")

        _이긴A = []

        def _줄A(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<52}{'(안 나왔다)':>16}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑A["끝"] and _r["낙"] >= _밑A["낙"] - 1.0) else (
                "△" if _r["끝"] >= _밑A["끝"] else "❌")
            print(f"     {이름:<52}{_r['끝']:>16,.0f}{_r['끝'] / _밑A['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _밑A['산']:>+7}  {_판}")
            if _r["끝"] >= _밑A["끝"]:
                _이긴A.append((이름, 옵, _r))
            return _r

        _머A = f"     {'설정':<52}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>7}  판정"

        # ══ ① 그날 장 상태 — **날**을 가른다 ══
        print("\n     ① ⭐⭐⭐ **그날 장 상태** — 종목이 아니라 **날**을 가른다")
        print("        평온한 날엔 신호가 8,251건 뜨는데 **69건만** 산다. 기회를 놓치고 있다")

        def _빠진날A(x):
            _v = x.get("시장낙폭")
            return _v is not None and _v <= -12.0      # 아래 25% 컷 (덤프 실측)

        def _평온날A(x):
            _v = x.get("시장낙폭")
            return _v is not None and _v > -3.2        # 위 25% 컷 (덤프 실측)

        print(_머A)
        for _t in (-2.5, -2.0, -1.5):
            _줄A(f"평온한 날만 상대갭 {_t}%p (빠진 날은 그대로)",
                 {"무리갭": [(_평온날A, "평온", _t)]})
        for _n in (2, 3):
            _줄A(f"평온한 날만 자리 {_n}개를 **더**",
                 {"무리자리": [(_평온날A, "평온", _n)]})
        _줄A("평온한 날 -2.0%p + 자리 2개를 더",
             {"무리갭": [(_평온날A, "평온", -2.0)], "무리자리": [(_평온날A, "평온", 2)]})
        _줄A("평온한 날 -1.5%p + 자리 3개를 더",
             {"무리갭": [(_평온날A, "평온", -1.5)], "무리자리": [(_평온날A, "평온", 3)]})
        _줄A("[거꾸로] 크게 빠진 날만 자리 3개를 더",
             {"무리자리": [(_빠진날A, "빠진날", 3)]})

        # ══ ② 주가 — 시총이 아니라 주가가 진짜 원인인가 ══
        print("\n     ② ⭐⭐⭐ **주가** — 대형주가 못 넘는 진짜 원인이 시총이 아니라 **주가**인가")
        print("        3,000원짜리는 호가 한 칸이 0.17%, 10만원짜리는 0.5% — 같은 -3.5%p 를 못 넘는다")

        def _비싼A(x):
            return (x.get("주가") or 0) >= 10070       # 위 25% 컷 (덤프 실측)

        def _중간값A(x):
            return 6110 <= (x.get("주가") or 0) < 10070

        print(_머A)
        for _t in (-2.5, -2.0, -1.5):
            _줄A(f"비싼 주식(1만원↑)만 상대갭 {_t}%p", {"무리갭": [(_비싼A, "비싼", _t)]})
        for _n in (1, 2):
            _줄A(f"비싼 주식(1만원↑) 자리 {_n}개를 더", {"무리자리": [(_비싼A, "비싼", _n)]})
        _줄A("비싼 -2.0%p + 자리 2개를 더",
             {"무리갭": [(_비싼A, "비싼", -2.0)], "무리자리": [(_비싼A, "비싼", 2)]})
        _줄A("비싼 -2.0 · 중간(6천~1만) -2.8 둘 다",
             {"무리갭": [(_비싼A, "비싼", -2.0), (_중간값A, "중간", -2.8)]})

        # ══ ③ 코스피 / 코스닥 ══
        print("\n     ③ **코스피 / 코스닥** — 우리는 사실상 코스닥 전략인데 문턱은 코스피를 보고 골랐다")

        def _코스피A(x):
            return x.get("_지수이름") == "코스피"

        print(_머A)
        for _t in (-3.0, -2.5, -2.0):
            _줄A(f"코스피 종목만 상대갭 {_t}%p", {"무리갭": [(_코스피A, "코스피", _t)]})
        for _n in (1, 2):
            _줄A(f"코스피 종목 자리 {_n}개를 더", {"무리자리": [(_코스피A, "코스피", _n)]})
        _줄A("코스피 -2.5%p + 자리 2개를 더",
             {"무리갭": [(_코스피A, "코스피", -2.5)], "무리자리": [(_코스피A, "코스피", 2)]})

        # ══ ④ 축끼리 견줌 — 무엇으로 나누는 게 맞나 ══
        print("\n     ④ ⭐⭐⭐ **축끼리 견줌** — 같은 세기로 풀었을 때 어느 축이 제일 버나")
        print("        (셋 다 -2.0%p + 자리 2개 · 무리만 다르다)")

        def _큰A(x):
            return (x.get("시총억") or 0) >= 2000

        def _섹A(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        print(_머A)
        for _름, _fn in (("규모(2천억↑)", _큰A), ("섹터 갈래", _섹A),
                         ("주가(1만원↑)", _비싼A), ("코스피", _코스피A),
                         ("평온한 날", _평온날A)):
            _줄A(f"[축 견줌] {_름} — -2.0%p + 자리 2",
                 {"무리갭": [(_fn, _름, -2.0)], "무리자리": [(_fn, _름, 2)]})

        # ══ ⑤ 화면 문장에 필요한 숫자 — 안 나눠 팔 때 낙폭 ══
        print("\n     ⑤ ⭐ **화면 문장에 넣을 숫자** — 「나눠 팔면 계좌 흔들림이 A% → B%로 줄었습니다」")
        print("        CAP 절에서 B(지금·나눠 팔 때)만 쟀다. A(안 나눠 팔 때)를 여기서 잰다")
        _한번 = 시뮬(_c(_H, 나눔=((1.0, 20.0, 40),)))
        if _한번 and _밑A:
            print(f"        A 안 나눠 팔 때 (한 번에 +20%/40일) — 낙폭 {_한번['낙']:>6.1f}%"
                  f" · 끝 {_한번['끝']:>15,.0f}원 · 산 것 {_한번['산']}")
            print(f"        B 지금 (40%는 +15%/40일 · 60%는 +40%/90일) — 낙폭 {_밑A['낙']:>6.1f}%"
                  f" · 끝 {_밑A['끝']:>15,.0f}원 · 산 것 {_밑A['산']}")
            _줄었나 = abs(_밑A["낙"]) < abs(_한번["낙"])
            print(f"        ⇒ 화면 문장: 「나눠 팔면 계좌 흔들림이 {abs(_한번['낙']):.1f}% → "
                  f"{abs(_밑A['낙']):.1f}%로 {'줄었습니다' if _줄었나 else '**늘었습니다**'}」")
            if not _줄었나:
                print("        🔴 **늘었다** — 지금 화면 문장(「줄었습니다」)이 사실과 다르다. 문장을 고쳐야 한다")

        # ══ ⑥ 이긴 것만 증분 걷기 ══
        print("\n     ⑥ 바탕을 넘은 것만 **증분 걷기** (앞 2010~2020 / 뒤 2021~2026)")
        if not _이긴A:
            print("        바탕을 넘은 것이 **하나도 없다** — 이 축들로도 답이 아니다")
        for _nmA, _opA, _rA in sorted(_이긴A, key=lambda z: -z[2]["끝"])[:5]:
            print(f"\n        [{_nmA}]  ({_rA['끝'] / _밑A['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_opA), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SELLG — 파는규칙(⑦)을 무리마다** (2026-09-28) ══
    if _ONLY == "SELLG" or "SELLG" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SELLG ⭐⭐⭐ **큰 회사는 +40% 가 너무 멀다 — 무리마다 다른 목표로 판다** ──")
        print("=" * 122)
        print("     지금은 전 종목이 똑같이 「40%는 +15%/40일 · 60%는 +40%/90일」로 판다.")
        print("     소형주는 +40% 가 자주 나지만 대형주에서는 거의 안 난다 —")
        print("     그러면 기한까지 들고 있다가 어정쩡하게 나온다.")
        print("     ⚠️ `규모별매도` 는 2026-09-11 부터 있었는데 **한 번도 안 쟀다.** 여기서 같이 잰다")

        _밑S7 = 시뮬(_c(_H))
        print(f"\n     바탕(지금) — {_밑S7['끝']:,.0f}원 · 낙폭 {_밑S7['낙']:.1f}% · 산 것 {_밑S7['산']}")

        def _중7(x):
            return 2000 <= (x.get("시총억") or 0) < 10000

        def _대7(x):
            return (x.get("시총억") or 0) >= 10000

        def _큰7(x):
            return (x.get("시총억") or 0) >= 2000

        def _섹7(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        _이긴7 = []

        def _줄7(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<52}{'(안 나왔다)':>16}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑S7["끝"] and _r["낙"] >= _밑S7["낙"] - 1.0) else (
                "△" if _r["끝"] >= _밑S7["끝"] else "❌")
            print(f"     {이름:<52}{_r['끝']:>16,.0f}{_r['끝'] / _밑S7['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}  {_판}")
            if _r["끝"] >= _밑S7["끝"]:
                _이긴7.append((이름, 옵, _r))
            return _r

        _머7 = f"     {'설정':<52}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정"

        # ── Ⓐ 큰 회사만 목표를 낮춘다 ──
        print("\n     Ⓐ **2,000억↑ 만** 목표를 낮춘다 (소형은 지금 그대로)")
        print(_머7)
        for _앞, _뒤 in ((12.0, 30.0), (10.0, 25.0), (10.0, 20.0), (8.0, 20.0), (8.0, 15.0)):
            _줄7(f"2천억↑ : 40%는 +{_앞:g}%/40일 · 60%는 +{_뒤:g}%/90일",
                 {"무리몫": [(_큰7, "2천억↑", ((0.4, _앞, 40), (0.6, _뒤, 90)))]})

        # ── Ⓑ 1조↑ 만 ──
        print("\n     Ⓑ **1조↑ 만** 목표를 낮춘다")
        print(_머7)
        for _앞, _뒤 in ((10.0, 25.0), (8.0, 20.0), (6.0, 15.0)):
            _줄7(f"1조↑ : 40%는 +{_앞:g}%/40일 · 60%는 +{_뒤:g}%/90일",
                 {"무리몫": [(_대7, "1조↑", ((0.4, _앞, 40), (0.6, _뒤, 90)))]})

        # ── Ⓒ 규모 셋을 각각 ──
        print("\n     Ⓒ **소·중·대 셋을 각각** 다르게 (규모별매도 — 9/11에 만들고 안 쟀다)")
        print(_머7)
        _줄7("소형 지금 · 중형 +12/+30 · 대형 +8/+20",
             {"무리몫": [(_대7, "대형", ((0.4, 8.0, 40), (0.6, 20.0, 90))),
                       (_중7, "중형", ((0.4, 12.0, 40), (0.6, 30.0, 90)))]})
        _줄7("소형 지금 · 중형 +10/+25 · 대형 +6/+15",
             {"무리몫": [(_대7, "대형", ((0.4, 6.0, 40), (0.6, 15.0, 90))),
                       (_중7, "중형", ((0.4, 10.0, 40), (0.6, 25.0, 90)))]})

        # ── Ⓓ 기한을 늘린다 (큰 회사는 천천히 움직인다) ──
        print("\n     Ⓓ **큰 회사는 더 오래 들고** (목표는 그대로, 기한만)")
        print(_머7)
        for _a, _b in ((60, 120), (60, 150), (90, 180)):
            _줄7(f"2천억↑ : 기한 {_a}일 / {_b}일",
                 {"무리몫": [(_큰7, "2천억↑", ((0.4, 15.0, _a), (0.6, 40.0, _b)))]})

        # ── Ⓔ 섹터 갈래만 ──
        print("\n     Ⓔ **섹터 갈래만** 다르게 (규모가 아니라 갈래로 가른다)")
        print(_머7)
        for _앞, _뒤 in ((12.0, 30.0), (10.0, 25.0), (20.0, 50.0)):
            _줄7(f"섹터 갈래 : +{_앞:g}% / +{_뒤:g}%",
                 {"무리몫": [(_섹7, "섹터", ((0.4, _앞, 40), (0.6, _뒤, 90)))]})
        _줄7("섹터 갈래 : 기한 60일 / 150일",
             {"무리몫": [(_섹7, "섹터", ((0.4, 15.0, 60), (0.6, 40.0, 150)))]})

        # ── Ⓕ [견줌] 전체를 바꾸면 (무리로 가른 뜻이 있나) ──
        print("\n     Ⓕ [견줌] **전체**를 바꾸면 — 같은 값이면 무리로 가른 뜻이 없다")
        print(_머7)
        for _앞, _뒤 in ((10.0, 25.0), (12.0, 30.0)):
            _줄7(f"전 종목 : +{_앞:g}% / +{_뒤:g}%",
                 {"나눔": ((0.4, _앞, 40), (0.6, _뒤, 90))})

        # ── Ⓖ 돈으로 ──
        print("\n     Ⓖ ⭐⭐⭐ **수익률이 아니라 돈** — 띠마다 넣은 돈·번 돈")

        def _돈7(이름, 옵):
            _기7 = []
            _r = 시뮬(_c(_H, **옵), 기록=_기7)
            if not _r:
                return
            _c7 = {}
            for _d7, _k7, _s7, _p7, _y7, _q7, _sh7 in _기7:
                _t7 = ("소형" if (_s7 or 0) < 2000 else
                       "중형" if (_s7 or 0) < 10000 else "대형")
                _in7 = (_sh7 or 0) * (_p7 or 0)
                _v7 = _c7.setdefault(_t7, [0, 0.0, 0.0])
                _v7[0] += 1
                _v7[1] += _in7
                _v7[2] += _in7 * (_y7 or 0) / 100.0
            print(f"\n        [{이름}] 끝 {_r['끝']:,.0f}원 · 낙폭 {_r['낙']:.1f}%")
            print(f"        {'띠':<6}{'몫':>6}{'넣은 돈':>16}{'번 돈':>16}"
                  f"{'한 건 넣은 돈':>16}{'한 건 번 돈':>15}{'수익률':>9}")
            for _t7 in ("소형", "중형", "대형"):
                _v7 = _c7.get(_t7)
                if not _v7:
                    print(f"        {_t7:<6}{0:>6}")
                    continue
                _n7, _i7, _e7 = _v7
                print(f"        {_t7:<6}{_n7:>6}{_i7:>16,.0f}{_e7:>+16,.0f}"
                      f"{_i7 / _n7:>16,.0f}{_e7 / _n7:>+15,.0f}"
                      f"{_e7 / _i7 * 100 if _i7 else 0:>8.1f}%")

        _돈7("지금 (전 종목 같은 규칙)", {})
        for _nm7b, _op7b, _r7b in sorted(_이긴7, key=lambda z: -z[2]["끝"])[:3]:
            _돈7(_nm7b, _op7b)

        # ── Ⓗ 증분 걷기 ──
        print("\n     Ⓗ 바탕을 넘은 것만 **증분 걷기** (앞 2010~2020 / 뒤 2021~2026)")
        if not _이긴7:
            print("        바탕을 넘은 것이 **하나도 없다.**")
            print("        ⇒ 파는규칙은 무리마다 가를 값이 없다 — 지금 40:60 을 그대로 둔다")
        for _nm7b, _op7b, _r7b in sorted(_이긴7, key=lambda z: -z[2]["끝"])[:4]:
            print(f"\n        [{_nm7b}]  ({_r7b['끝'] / _밑S7['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_op7b), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **GROUP — 무리마다 제 규칙 (④상대갭 · ⑤자리 · ⑦파는규칙)** (2026-09-28) ══
    if _ONLY == "GROUP" or "GROUP" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── GROUP ⭐⭐⭐ **규모별로 · 섹터별로 서로 다른 규칙** ──")
        print("=" * 122)
        print("     지금 상태 — 신호(③)만 갈라져 있고 뒤 세 층은 **하나로 묶여 있다**")
        print(f"        ③ 신호     섹터 {len(R.섹터규칙)}개 · 업종 {len(R.업종규칙)}개 제 문턱   → 다르다")
        print("        ④ 상대갭   **-3.5%p 하나뿐** — 소형 자료로 고른 값을 모두에게 쓴다 → **공통**")
        print(f"        ⑤ 하루자리 {R.하루최대종목} 하나뿐                           → **공통**")
        print(f"        ⑦ 파는규칙 {R.몫들}  → **공통**")
        print("     ⇒ 신호를 통과해도 ④에서 죽거나(대형 93건→0건) ⑤에서 소형에 밀린다")

        _밑G = 시뮬(_c(_H))
        print(f"\n     바탕(지금) — {_밑G['끝']:,.0f}원 · 낙폭 {_밑G['낙']:.1f}% · 산 것 {_밑G['산']}")

        # ── 무리 판정 ──
        def _중G(x):
            return 2000 <= (x.get("시총억") or 0) < 10000

        def _대G(x):
            return (x.get("시총억") or 0) >= 10000

        def _큰G(x):
            return (x.get("시총억") or 0) >= 2000

        def _섹G(x):
            try:
                return bool(섹터맞나(x))
            except Exception:  # noqa: BLE001
                return False

        def _업G(x):
            try:
                _m, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                    "시총억": x.get("시총억"), "대금억": x.get("대금억"),
                    "_지금문통과": 문통과_크기없이(x), "잉여금비율": x.get("잉여금"),
                    "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                    "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
                return bool(_m)
            except Exception:  # noqa: BLE001
                return False

        def _바구니G(이름):
            def _f(x, _n=이름):
                return _사슬섹터.get(x["code"]) == _n
            return _f

        def _줄G(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<50}{'(안 나왔다)':>16}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑G["끝"] and _r["낙"] >= _밑G["낙"] - 1.0) else (
                "△" if _r["끝"] >= _밑G["끝"] else "❌")
            print(f"     {이름:<50}{_r['끝']:>16,.0f}{_r['끝'] / _밑G['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _밑G['산']:>+7}  {_판}")
            return _r

        _머G = f"     {'설정':<50}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>7}  판정"
        _이긴G = []

        def _재G(이름, 옵):
            _r = _줄G(이름, 옵)
            if _r and _r["끝"] >= _밑G["끝"]:
                _이긴G.append((이름, 옵, _r))
            return _r

        # ── Ⓐ 층④ 상대갭만 무리마다 ──
        print("\n     Ⓐ **층④ 상대갭**을 무리마다 (자리는 지금 그대로 — 소형을 밀어낸다)")
        print(_머G)
        for _t in (-2.5, -2.0, -1.5):
            _재G(f"중형(2천억~1조)만 {_t}%p", {"무리갭": [(_중G, "중형", _t)]})
        for _t in (-2.0, -1.5, -1.0):
            _재G(f"대형(1조↑)만 {_t}%p", {"무리갭": [(_대G, "대형", _t)]})
        for _t in (-2.5, -2.0, -1.5):
            _재G(f"섹터 갈래만 {_t}%p", {"무리갭": [(_섹G, "섹터", _t)]})
        for _t in (-2.5, -2.0):
            _재G(f"업종 갈래만 {_t}%p", {"무리갭": [(_업G, "업종", _t)]})

        # ── Ⓑ 층⑤ 자리만 무리마다 ──
        print("\n     Ⓑ **층⑤ 자리**를 무리마다 **더** (문턱은 지금 그대로 — 넘어올 놈이 있나)")
        print(_머G)
        for _n in (1, 2):
            _재G(f"중형 자리 {_n}개를 더", {"무리자리": [(_중G, "중형", _n)]})
            _재G(f"대형 자리 {_n}개를 더", {"무리자리": [(_대G, "대형", _n)]})
            _재G(f"섹터 자리 {_n}개를 더", {"무리자리": [(_섹G, "섹터", _n)]})
        _재G("업종 자리 1개를 더", {"무리자리": [(_업G, "업종", 1)]})

        # ── Ⓒ ⭐ 둘 다 ──
        print("\n     Ⓒ ⭐⭐⭐ **문을 열고(④) + 자리도 따로(⑤)** — 하나만 하면 반드시 실패한다")
        print(_머G)
        for _t, _n in ((-2.0, 1), (-2.0, 2), (-1.5, 2)):
            _재G(f"중형 {_t}%p + 중형 자리 {_n}",
                 {"무리갭": [(_중G, "중형", _t)], "무리자리": [(_중G, "중형", _n)]})
        for _t, _n in ((-1.5, 1), (-1.5, 2), (-1.0, 2)):
            _재G(f"대형 {_t}%p + 대형 자리 {_n}",
                 {"무리갭": [(_대G, "대형", _t)], "무리자리": [(_대G, "대형", _n)]})
        for _t, _n in ((-2.0, 1), (-2.0, 2), (-1.5, 2)):
            _재G(f"섹터 {_t}%p + 섹터 자리 {_n}",
                 {"무리갭": [(_섹G, "섹터", _t)], "무리자리": [(_섹G, "섹터", _n)]})
        _재G("업종 -2.5%p + 업종 자리 1",
             {"무리갭": [(_업G, "업종", -2.5)], "무리자리": [(_업G, "업종", 1)]})
        _재G("2천억↑ -2.0%p + 2천억↑ 자리 2",
             {"무리갭": [(_큰G, "2천억↑", -2.0)], "무리자리": [(_큰G, "2천억↑", 2)]})
        _재G("중형-2.0/대형-1.5/섹터-2.0 + 각 자리 1",
             {"무리갭": [(_대G, "대형", -1.5), (_중G, "중형", -2.0), (_섹G, "섹터", -2.0)],
              "무리자리": [(_대G, "대형", 1), (_중G, "중형", 1), (_섹G, "섹터", 1)]})

        # ── Ⓓ 섹터 바구니마다 따로 ──
        print("\n     Ⓓ **섹터 바구니 하나씩** — 제 문턱(-2.0%p) + 제 자리 1")
        print(_머G)
        for _nm in sorted(R.섹터규칙):
            _f = _바구니G(_nm)
            _재G(f"[{_nm}] -2.0%p + 자리 1",
                 {"무리갭": [(_f, _nm, -2.0)], "무리자리": [(_f, _nm, 1)]})

        # ── Ⓔ 층⑦ 파는규칙을 무리마다 ──
        print("\n     Ⓔ **층⑦ 파는규칙**을 무리마다 — 대형은 크게 안 오르니 목표를 낮추면?")
        print("        ⚠️ 지금은 못 가른다 (시뮬이 몫들을 하나로 쓴다) — **다음 판에서 만든다**")
        print("        여기서는 전체를 바꿔 방향만 본다")
        print(_머G)
        _재G("[견줌] 목표를 통째로 낮춤 (+10%/40일 · +25%/90일)",
             {"나눔": ((0.4, 10.0, 40), (0.6, 25.0, 90))})

        # ── Ⓕ 돈으로 — 이긴 것들 ──
        print("\n     Ⓕ ⭐⭐⭐ **수익률이 아니라 돈** — 띠마다 넣은 돈·번 돈")
        print("        대형·중형은 거래대금 1% 한도를 덜 받아 **한 건에 큰 돈**이 들어간다")

        def _돈G(이름, 옵):
            _기G = []
            _r = 시뮬(_c(_H, **옵), 기록=_기G)
            if not _r:
                return
            _cG = {}
            for _dG, _kG, _sG, _pG, _yG, _qG, _shG in _기G:
                _tG = ("소형" if (_sG or 0) < 2000 else
                       "중형" if (_sG or 0) < 10000 else "대형")
                _inG = (_shG or 0) * (_pG or 0)
                _vG = _cG.setdefault(_tG, [0, 0.0, 0.0])
                _vG[0] += 1
                _vG[1] += _inG
                _vG[2] += _inG * (_yG or 0) / 100.0
            print(f"\n        [{이름}] 끝 {_r['끝']:,.0f}원 · 낙폭 {_r['낙']:.1f}%")
            print(f"        {'띠':<6}{'몫':>6}{'넣은 돈':>16}{'번 돈':>16}"
                  f"{'한 건 넣은 돈':>16}{'한 건 번 돈':>15}{'수익률':>9}")
            for _tG in ("소형", "중형", "대형"):
                _vG = _cG.get(_tG)
                if not _vG:
                    print(f"        {_tG:<6}{0:>6}")
                    continue
                _nG, _iG, _eG = _vG
                print(f"        {_tG:<6}{_nG:>6}{_iG:>16,.0f}{_eG:>+16,.0f}"
                      f"{_iG / _nG:>16,.0f}{_eG / _nG:>+15,.0f}"
                      f"{_eG / _iG * 100 if _iG else 0:>8.1f}%")

        _돈G("지금 (아무것도 안 함)", {})
        for _nmG, _opG, _rG in sorted(_이긴G, key=lambda z: -z[2]["끝"])[:4]:
            _돈G(_nmG, _opG)

        # ── Ⓖ 증분 걷기 ──
        print("\n     Ⓖ 바탕을 넘은 것만 **증분 걷기** (앞 2010~2020 / 뒤 2021~2026)")
        if not _이긴G:
            print("        바탕을 넘은 것이 **하나도 없다.**")
            print("        ⇒ ④⑤ 를 무리마다 갈라도 돈이 안 는다는 뜻이다 —")
            print("           그러면 무리별 규칙은 **③ 신호 층에서만** 뜻이 있다고 결론 내면 된다")
        for _nmG, _opG, _rG in sorted(_이긴G, key=lambda z: -z[2]["끝"])[:5]:
            print(f"\n        [{_nmG}]  ({_rG['끝'] / _밑G['끝'] * 100:.0f}%)")
            _걷기찍기(_옵걷기(_opG), 들여="          ")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SLOT2 — 문을 열고(갭무름) + 자리를 따로(무리자리) 둘 다** (2026-09-28) ══
    if _ONLY == "SLOT2" or "SLOT2" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SLOT2 ⭐⭐⭐ **둘 중 하나만 하면 반드시 실패하게 돼 있었다** ──")
        print("=" * 122)
        print("     덤프를 문마다 세어 보니 (2026-09-28):")
        print("        대형 1조↑ — 신호 93건까지는 잘 온다 (남는 비율 18.4%, 소형 20.5% 와 비슷)")
        print("        그런데 **상대갭 문에서 93건이 전부 죽는다. 통과 0건.**")
        print("        거래가 두꺼워 시초가가 안 튀니 「중앙갭보다 3.5%p 더 빠진」 일이 안 생긴다")
        print("     ⇒ `갭무름` 혼자 = 문은 열리는데 하루 자리에서 소형을 밀어낸다 (9/24: 91·74·88·57%)")
        print("     ⇒ `무리자리` 혼자 = 자리를 떼어 줘도 **넘어오는 대형이 0건** — 자리가 빈다")
        print("     ⇒ **둘 다** 해야 뜻이 있다. 이 절이 그 빈칸이다")

        _밑2 = 시뮬(_c(_H))
        print(f"\n     바탕(지금) — {_밑2['끝']:,.0f}원 · 낙폭 {_밑2['낙']:.1f}% · 산 것 {_밑2['산']}")

        def _큰2(x):
            return (x.get("시총억") or 0) >= 2000

        def _아주큰2(x):
            return (x.get("시총억") or 0) >= 10000

        def _줄2(이름, 옵):
            _r = 시뮬(_c(_H, **옵))
            if not _r:
                print(f"     {이름:<46}{'(안 나왔다)':>16}")
                return None
            _판 = "⭐" if (_r["끝"] >= _밑2["끝"] and _r["낙"] >= _밑2["낙"] - 1.0) else "❌"
            print(f"     {이름:<46}{_r['끝']:>16,.0f}{_r['끝'] / _밑2['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_r['산'] - _밑2['산']:>+7}  {_판}")
            return _r

        _머2 = f"     {'설정':<46}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'더 산 것':>7}  판정"

        # ── ① 견줌 — 하나씩만 (왜 실패하는지 눈으로) ──
        print("\n     ① [견줌] 하나씩만 — 왜 각각 실패하나")
        print(_머2)
        _줄2("갭무름만 (2,000억↑ 0.5배) · 자리 그대로", {"갭무름": [(2000, 0.5)]})
        _줄2("무리자리만 (대형 2자리를 더) · 문 그대로", {"무리자리": [(_큰2, "대형", 2)]})

        # ── ② ⭐ 둘 다 ──
        print("\n     ② ⭐⭐⭐ **둘 다** — 문을 열되 소형을 안 밀어낸다")
        print(_머2)
        for _무름 in (0.7, 0.5, 0.3):
            for _자리 in (1, 2, 3):
                _줄2(f"2,000억↑ {_무름}배 + 대형 {_자리}자리를 더",
                     {"갭무름": [(2000, _무름)], "무리자리": [(_큰2, "대형", _자리)]})
        for _무름 in (0.5, 0.3):
            for _자리 in (1, 2):
                _줄2(f"1조↑ {_무름}배 + 1조↑ {_자리}자리를 더",
                     {"갭무름": [(10000, _무름)], "무리자리": [(_아주큰2, "1조↑", _자리)]})

        # ── ③ 돈으로 — 띠마다 넣은 돈·번 돈 ──
        print("\n     ③ ⭐⭐⭐ **수익률이 아니라 돈** — 띠마다 얼마를 넣고 얼마를 벌었나")
        print("        대형은 거래대금 1% 한도를 거의 안 받는다 → **한 건에 큰 돈**이 들어간다")

        def _돈2(이름, 옵):
            _기2 = []
            _r = 시뮬(_c(_H, **옵), 기록=_기2)
            if not _r:
                return
            _칸2 = {}
            for _날2, _코2, _시총2, _원시2, _익2, _청2, _주2 in _기2:
                _t2 = ("소형" if (_시총2 or 0) < 2000 else
                       "중형" if (_시총2 or 0) < 10000 else "대형")
                _넣2 = (_주2 or 0) * (_원시2 or 0)
                _v2 = _칸2.setdefault(_t2, [0, 0.0, 0.0])
                _v2[0] += 1
                _v2[1] += _넣2
                _v2[2] += _넣2 * (_익2 or 0) / 100.0
            print(f"\n        [{이름}] 끝 {_r['끝']:,.0f}원 · 낙폭 {_r['낙']:.1f}%")
            print(f"        {'띠':<6}{'몫':>6}{'넣은 돈':>16}{'번 돈':>16}"
                  f"{'한 건 넣은 돈':>16}{'한 건 번 돈':>15}{'수익률':>9}")
            for _t2 in ("소형", "중형", "대형"):
                _v2 = _칸2.get(_t2)
                if not _v2:
                    print(f"        {_t2:<6}{0:>6}")
                    continue
                _n2, _넣합2, _번합2 = _v2
                print(f"        {_t2:<6}{_n2:>6}{_넣합2:>16,.0f}{_번합2:>+16,.0f}"
                      f"{_넣합2 / _n2:>16,.0f}{_번합2 / _n2:>+15,.0f}"
                      f"{_번합2 / _넣합2 * 100 if _넣합2 else 0:>8.1f}%")

        _돈2("지금 (아무것도 안 함)", {})
        _돈2("2,000억↑ 0.5배 + 대형 2자리를 더",
             {"갭무름": [(2000, 0.5)], "무리자리": [(_큰2, "대형", 2)]})
        _돈2("2,000억↑ 0.3배 + 대형 2자리를 더",
             {"갭무름": [(2000, 0.3)], "무리자리": [(_큰2, "대형", 2)]})

        # ── ④ 이긴 것만 증분 걷기 ──
        print("\n     ④ 바탕보다 나은 것만 **증분 걷기** (앞 2010~2020 / 뒤 2021~2026)")
        _봄 = 0
        for _무름 in (0.7, 0.5, 0.3):
            for _자리 in (1, 2, 3):
                _옵2 = {"갭무름": [(2000, _무름)], "무리자리": [(_큰2, "대형", _자리)]}
                _r = 시뮬(_c(_H, **_옵2))
                if not _r or _r["끝"] < _밑2["끝"]:
                    continue
                _봄 += 1
                print(f"\n        [{_무름}배 + 대형 {_자리}자리]")
                _걷기찍기(_옵걷기(_옵2), 들여="          ")
        if not _봄:
            print("\n        바탕을 넘은 것이 하나도 없다 — 걷기 생략")
            print("        ⇒ 「문을 열고 자리를 따로 주는 것」도 답이 아니다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SCORE — 화면에 나갈 성적표** (2026-09-28 · 사용자 「A로 하자」) ══
    if _ONLY == "SCORE" or "SCORE" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SCORE ⭐⭐⭐ **지금 규칙 그대로 · 제약 있는 판**으로 성적표를 다시 낸다 ──")
        print("     왜 — 화면에 나가던 성적표가 **손으로 적힌 것**이었다 (연평균 칸이 비어 있었다).")
        print("     verify_all.py 는 업종·섹터 규칙도 40:60 나눠팔기도 모르는 옛 단순 규칙이라 못 쓴다.")
        print("=" * 122)
        print(f"\n     {R.한줄()}")
        _전 = 시뮬(_c(_H))
        if not _전:
            print("     🔴 시뮬이 값을 안 냈다")
        else:
            print(f"\n     ① 11년 전체 (제약 있는 판 — 현금·거래대금 1% 한도)")
            print(f"        시작 자산   {_시드:>16,.0f}원")
            print(f"        끝 자산     {_전['끝']:>16,.0f}원")
            print(f"        연평균      {_전['연']:>16.2f}%")
            print(f"        계좌 낙폭   {_전['낙']:>16.1f}%")
            print(f"        산 것       {_전['산']:>16}건")

            print(f"\n     ② 앞뒤로 잘라서 (뒤 기간만 돌리면 — 낙폭은 이쪽이 더 정직하다)")
            print(f"        {'그 해부터':<12}{'끝 자산':>16}{'연평균':>9}{'낙폭':>8}{'산 것':>7}")
            _분할 = []
            for _컷 in ("2019", "2020", "2021", "2022"):
                _r = 시뮬(_c(_H), 시작년=_컷)
                if not _r:
                    continue
                _분할.append({"시작": _컷, "연": round(_r["연"], 1), "낙폭": round(_r["낙"], 1)})
                print(f"        {_컷:<12}{_r['끝']:>16,.0f}{_r['연']:>8.1f}%{_r['낙']:>7.1f}%{_r['산']:>7}")

            _최악 = min([z["낙폭"] for z in _분할] + [round(_전["낙"], 1)]) if _분할 else round(_전["낙"], 1)
            _몫 = {
                "만든날": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "출처": "gate7_lab CAP 절 — 지금 규칙(rule_def) 그대로 · 제약 있는 판",
                "규칙한줄": R.한줄(),
                "시작자산": _시드,
                "연평균": round(_전["연"], 2),
                "계좌낙폭": round(_전["낙"], 1),
                "최악낙폭": _최악,
                "끝자산": round(_전["끝"]),
                "산것": _전["산"],
                "분할": _분할,
                "주의": ("제약 있는 판(현금·거래대금 1% 한도) 값이라 실제 계좌에 가깝다. "
                       "사용자 2026-09-28 결정: 화면 성적표는 제약 있는 쪽(A)."),
            }
            _밖길 = os.path.join(O._DATA, "_labs", "rule-capital_후보.json")
            try:
                io.open(_밖길, "w", encoding="utf-8").write(
                    json.dumps(_몫, ensure_ascii=False, indent=1))
                print(f"\n     → 후보로 남겼다: data/_labs/rule-capital_후보.json")
                print("        ⚠️ 실전 파일(data/rule-capital.json)은 **안 건드렸다** — 보고 나서 옮긴다")
            except OSError as _e:
                print(f"\n     ⚠️ 못 남겼다: {type(_e).__name__}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **CHAIN — 가치사슬 여섯 바구니가 11년 동안 뭘 했나** (2026-09-28 · 사용자 물음) ══
    if _ONLY == "CHAIN" or "CHAIN" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── CHAIN ⭐⭐⭐ **섹터 갈래는 시총 상한이 없다 — 여섯 바구니가 실제로 뭘 했나** ──")
        print("=" * 122)
        _바구니 = {}
        for _코드, _섹 in _사슬섹터.items():
            _바구니.setdefault(_섹, set()).add(_코드)
        print(f"\n     가치사슬 맵 {len(_사슬섹터):,}종목 · 바구니 {len(_바구니)}개")
        for _섹 in sorted(_바구니):
            _규 = _섹규칙.get(_섹)
            print(f"        {_섹:<20} {len(_바구니[_섹]):>3}종목"
                  + (f"  · 규칙 볼{_규[0]} ≤ {_규[1]:g}σ · 낙{_규[2]} ≤ {_규[3]:g}%" if _규 else "  · (규칙 없음)"))

        # ── ① 바구니마다 걸린 사건 ──
        _걸린 = {}
        for x in 사건:
            _섹 = _사슬섹터.get(x["code"])
            if not _섹 or _섹 not in _섹규칙:
                continue
            if 섹터맞나(x) and 재무통과(x) and 대금통과(x):
                _걸린.setdefault(_섹, []).append(x)
        print(f"\n     ① 규칙에 걸린 사건 (재무·대금 문까지 통과)")
        print(f"     {'바구니':<20}{'걸린 사건':>10}{'걸린 날':>9}{'종목 수':>8}{'해마다 날':>10}")
        for _섹 in sorted(_바구니):
            _v = _걸린.get(_섹) or []
            _날수 = len({x["인"] for x in _v})
            print(f"     {_섹:<20}{len(_v):>10,}{_날수:>9}{len({x['code'] for x in _v}):>8}"
                  f"{_날수 / 11:>10.1f}")

        # ── ② 실제로 산 것 ──
        _기록C = []
        _rC = 시뮬(_c(_H), 기록=_기록C)
        _날인C = {_d: _i for _i, _d in enumerate(날)}
        print(f"\n     ② 지금 규칙이 11년 동안 산 {len(_기록C):,}건 중 바구니 종목은")
        print(f"     {'바구니':<20}{'산 것':>7}{'평균 수익':>11}{'가운데':>10}{'이긴 비율':>11}{'가장 나쁜':>11}")
        _산바구니 = {}
        for _거래 in _기록C:
            _섹 = _사슬섹터.get(_거래[1])
            if _섹:
                _산바구니.setdefault(_섹, []).append(_거래[4])
        for _섹 in sorted(_바구니):
            _v = sorted(_산바구니.get(_섹) or [])
            if not _v:
                print(f"     {_섹:<20}{0:>7}")
                continue
            print(f"     {_섹:<20}{len(_v):>7}{sum(_v) / len(_v):>10.1f}%{_v[len(_v) // 2]:>9.1f}%"
                  f"{sum(1 for z in _v if z > 0) / len(_v) * 100:>10.0f}%{_v[0]:>10.1f}%")
        _전체 = sorted(z[4] for z in _기록C)
        print(f"     {'(전체)':<20}{len(_전체):>7}{sum(_전체) / len(_전체):>10.1f}%"
              f"{_전체[len(_전체) // 2]:>9.1f}%{sum(1 for z in _전체 if z > 0) / len(_전체) * 100:>10.0f}%"
              f"{_전체[0]:>10.1f}%")

        # ── ③ 그 바구니만 빼면 ──
        print(f"\n     ③ 그 바구니를 빼고 돌리면 (지금 {_rC['끝']:,.0f}원 · 낙폭 {_rC['낙']:.1f}%)")
        print(f"     {'뺀 바구니':<20}{'끝 자산':>16}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}")
        for _섹 in sorted(_바구니):
            def _빼고(x, _s=_섹):
                if _사슬섹터.get(x["code"]) == _s:
                    return False
                return _H(x)          # [견줌] 그 바구니만 뺀 지금 규칙
            _r = 시뮬(_c(_빼고))
            if _r:
                print(f"     {_섹:<20}{_r['끝']:>16,.0f}{_r['끝'] / _rC['끝'] * 100:>8.0f}%"
                      f"{_r['낙']:>7.1f}%{_r['산']:>7}")

        # ── ④ 반도체 바구니 해마다 ──
        try:
            _반 = next((k for k in _바구니 if "반도체" in k), None)
            if _반:
                print(f"\n     ④ [{_반}] 해마다 — 걸린 날 · 산 것")
                print(f"     {'해':<7}{'걸린 날':>9}{'산 것':>8}{'평균 수익':>11}")
                for _y in range(2016, 2027):
                    _v = [x for x in (_걸린.get(_반) or []) if str(날[x["인"]])[:4] == str(_y)]
                    _산 = [z[4] for z in _기록C
                           if _사슬섹터.get(z[1]) == _반 and str(z[0])[:4] == str(_y)]
                    print(f"     {_y:<7}{len({x['인'] for x in _v}):>9}{len(_산):>8}"
                          + (f"{sum(_산) / len(_산):>10.1f}%" if _산 else f"{'—':>11}"))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ④ 터졌다: {_e}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **AB — 넣기로 한 둘(비중·악재매도)을 같이 켜면** (2026-09-28) ══
    if _ONLY == "AB" or "AB" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── AB ⭐⭐⭐ **A 비중 25%·자리 6 · B 악재 매도 — 따로 켤 때와 같이 켤 때** ──")
        print("     둘은 다른 층(⑥비중 · ⑦파는 규칙)이라 안 겹칠 것 같지만 **잰 적이 없다**")
        print("=" * 122)
        _합A, _묶A, _열A, _키A = _D준비()
        _지금키A = _키A["지금"]

        def _지금A(x):
            return (x["code"], x["인"]) in _지금키A        # [견줌] 덜어 둔 열쇠

        def _자리A(n):
            return (lambda 골, _n=n: _n)

        _벌A = [
            ("바탕 (20% · 4자리 · 손절없음)", {}),
            ("A  비중 25% · 자리 6", {"비중": 0.25, "하루상한": _자리A(6)}),
            ("B  악재 매도", {"재평가": "악재"}),
            ("A+B  25%·6자리 + 악재매도", {"비중": 0.25, "하루상한": _자리A(6), "재평가": "악재"}),
            ("(참고) 33%·6자리", {"비중": 0.33, "하루상한": _자리A(6)}),
            ("(참고) 33%·6자리 + 악재매도", {"비중": 0.33, "하루상한": _자리A(6), "재평가": "악재"}),
        ]
        _기A = 시뮬(_c(_지금A, **_열A), 묶2=_묶A)
        _기돈낙A = _기A["끝"] / abs(_기A["낙"]) if _기A["낙"] else 0
        print(f"\n     ① 따로 · 같이")
        print(f"     {'무엇을':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>10}")
        _표A = {}
        for _이, _옵 in _벌A:
            _r = 시뮬(_c(_지금A, **_열A, **_옵), 묶2=_묶A)
            if not _r:
                continue
            _표A[_이] = (_r, _옵)
            _돈낙 = _r["끝"] / abs(_r["낙"]) if _r["낙"] else 0
            print(f"     {_이:<34}{_r['끝']:>16,.0f}{_r['끝'] / _기A['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}{_돈낙 / _기돈낙A * 100 if _기돈낙A else 0:>9.0f}%")

        # ② 증분 걷기
        try:
            print(f"\n     ② 증분 걷기 (뒤는 앞이 끝낸 돈으로)")
            print(f"     {'무엇을':<34}{'앞 2016~2020':>18}{'뒤 2021~2026':>18}  판정")
            _a0 = 시뮬(_c(_지금A, **_열A), 시작년="2016", 끝년="2020", 묶2=_묶A)
            _b0 = 시뮬(_c(_지금A, **_열A), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶A) if _a0 else None
            for _이, (_r, _옵) in _표A.items():
                if not _옵:
                    continue
                _a1 = 시뮬(_c(_지금A, **_열A, **_옵), 시작년="2016", 끝년="2020", 묶2=_묶A)
                _b1 = 시뮬(_c(_지금A, **_열A, **_옵), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶A) if _a1 else None
                if not (_a0 and _a1 and _b0 and _b1):
                    continue
                _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
                _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
                print(f"     {_이:<34}{_앞:>17.1f}%{_뒤:>17.1f}%  "
                      + ("✅" if (_앞 > 0.1 and _뒤 > 0.1) else "❌"))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ③ 해마다 · ④ 체결 오차 · ⑤ 동시 보유
        try:
            print(f"\n     ③④⑤ 해마다 · 체결 오차 · 한 종목 사고")
            print(f"     {'무엇을':<34}{'이긴 해':>8}{'진 해':>7}{'오차 최악':>16}{'동시(가운데)':>13}{'가장 나쁜 한 방':>15}")
            _날인A = {_d: _i for _i, _d in enumerate(날)}
            for _이, (_r, _옵) in _표A.items():
                _이긴, _진 = 0, 0
                for _y in range(2016, 2027):
                    _r0 = 시뮬(_c(_지금A, **_열A), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶A)
                    _r1 = 시뮬(_c(_지금A, **_열A, **_옵), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶A)
                    if _r0 and _r1:
                        _이긴 += 1 if _r1["끝"] > _r0["끝"] * 1.0005 else 0
                        _진 += 1 if _r1["끝"] < _r0["끝"] * 0.9995 else 0
                _끝들 = []
                for _씨 in range(1, 11):
                    _rn = 시뮬(_c(_지금A, **_열A, **_옵), 오차=1.0, 씨=_씨, 묶2=_묶A)
                    if _rn:
                        _끝들.append(_rn["끝"])
                _기록A = []
                시뮬(_c(_지금A, **_열A, **_옵), 묶2=_묶A, 기록=_기록A)
                _든 = {}
                _나쁜 = 0.0
                for _거래 in _기록A:
                    _나쁜 = min(_나쁜, _거래[4])
                    _i0, _청 = _날인A.get(_거래[0]), _거래[5]
                    if _i0 is None or _청 is None:
                        continue
                    for _k in range(_i0, min(_청 + 1, len(날))):
                        _든.setdefault(_k, set()).add(_거래[1])
                _수A = sorted(len(v) for v in _든.values())
                print(f"     {_이:<34}{_이긴:>8}{_진:>7}{(min(_끝들) if _끝들 else 0):>16,.0f}"
                      f"{(_수A[len(_수A) // 2] if _수A else 0):>13}{_나쁜:>14.1f}%")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③④⑤ 터졌다: {_e}")
        print("\n     ⚠️ 「가장 나쁜 한 방」에 비중을 곱하면 **한 종목 사고가 계좌에 내는 구멍**이다")
        print("        25% × −46% ≈ 자산의 −12% · 33% × −46% ≈ −15% · 지금(20%) ≈ −9%")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **DECIDE — 월요일 결정에 필요한 것만** (2026-09-27) ══
    if _ONLY == "DECIDE" or "DECIDE" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DECIDE ⭐⭐⭐ **조합의 칼날 여부 · 비중과 겹치나 · 얼마나 자주 뜨나** ──")
        print("=" * 122)
        _합E, _묶E, _열E, _키E = _D준비()
        _지금키E = _키E["지금"]
        import glob as _gE
        _후E = {}
        for _fE in sorted(_gE.glob(os.path.join(O._DATA, "_labs", "d_events_*.jsonl"))):
            _이E = os.path.basename(_fE)[9:-6]
            try:
                _evE = [json.loads(z) for z in io.open(_fE, encoding="utf-8") if z.strip()]
            except (OSError, ValueError):
                continue
            if not _evE:
                continue
            _후E[_이E] = _evE
            _본E = {(x["code"], x["인"]) for x in _합E}
            for x in _evE:
                if (x["code"], x["인"]) not in _본E:
                    _합E.append(x)
                    _묶E.setdefault(x["인"], []).append(x)
        if not _후E:
            print("     ⚠️ d_events_*.jsonl 이 없다")
            print("=" * 122)
            return 0

        def _지금E(x):
            return (x["code"], x["인"]) in _지금키E        # [견줌] 덜어 둔 열쇠

        def _자리E(n):
            return (lambda 골, _n=n: _n)

        _기E = 시뮬(_c(_지금E, **_열E), 묶2=_묶E)
        _날E = {인 for (_, 인) in _지금키E}
        print(f"\n     바탕 — {_기E['끝']:,.0f}원 · 낙폭 {_기E['낙']:.1f}% · 산 것 {_기E['산']}")
        print(f"     덜어 둔 후보 {len(_후E)}개: " + " · ".join(_후E))

        _대 = next((k for k in _후E if k.startswith("대형_낙20")), None)
        _소 = next((k for k in _후E if k.startswith("소형_")), None)
        _초 = next((k for k in _후E if k.startswith("초소형_낙40위20_낙폭60↓") and "낙60" not in k), None)

        def _열쇠들(이름):
            return {(x["code"], x["인"]) for x in _후E.get(이름, [])}

        def _재(이름, 켤키, 옵=None):
            _도 = (lambda x, _k=켤키: _지금E(x) or (x["code"], x["인"]) in _k)   # [견줌]
            _r = 시뮬(_c(_도, **_열E, **(옵 or {})), 묶2=_묶E)
            if not _r:
                print(f"     {이름:<40} — 안 돌았다")
                return None
            _새 = len({인 for (_, 인) in 켤키} - _날E)
            print(f"     {이름:<40}{_새:>7}{_r['끝']:>16,.0f}{_r['끝'] / _기E['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}")
            return _r

        # ── ① 조합에서도 칼날인가 — 대형을 켠 채로 소형 문턱을 흔든다 ──
        try:
            print("\n     ① 대형을 켠 채로 **소형 후보의 신호 세기**를 옮기면 (소형 사건을 세기 순으로 자른다)")
            print("        ⚠️ 칸 문턱을 다시 못 만드니, 그 칸 사건을 **시장변동성 큰 순**으로 잘라 흉내 낸다")
            if _대 and _소:
                _대키 = _열쇠들(_대)
                _소사건 = sorted(_후E[_소], key=lambda x: -(x.get("시장변동성") or 0))
                print(f"     {'변형':<40}{'새 날':>7}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}")
                _재("대형만", _대키)
                for _몫 in (0.25, 0.50, 0.75, 1.00):
                    _잘 = {(x["code"], x["인"]) for x in _소사건[:max(1, int(len(_소사건) * _몫))]}
                    _재(f"대형 + 소형 위 {int(_몫 * 100)}%", _대키 | _잘)
            else:
                print("        (대형 또는 소형 후보가 없다)")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② 비중 33% · 자리 6 에서도 값이 있나 ──
        try:
            print("\n     ② 자리를 넉넉히 주면(비중 33% · 자리 6) 후보의 값이 남나")
            print(f"     {'변형':<40}{'새 날':>7}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}")
            for _이, _옵 in (("지금 (20% · 4자리)", {}),
                             # ⭐ 2026-09-28 — 실제 반영은 **자리만 6** 이다. 그 상태에서 후보가 값이 있나
                             ("반영한 것 (20% · 6자리)", {"하루상한": _자리E(6)}),
                             ("넉넉히 (33% · 6자리)", {"비중": 0.33, "하루상한": _자리E(6)})):
                _기2 = 시뮬(_c(_지금E, **_열E, **_옵), 묶2=_묶E)
                if not _기2:
                    continue
                print(f"     {'  바탕 — ' + _이:<40}{0:>7}{_기2['끝']:>16,.0f}"
                      f"{_기2['끝'] / _기E['끝'] * 100:>8.0f}%{_기2['낙']:>8.1f}%{_기2['산']:>7}")
                for _쓸, _라 in ((_대, "대형"), (_소, "소형"), (_초, "초소형")):
                    if not _쓸:
                        continue
                    _도 = (lambda x, _k=_열쇠들(_쓸): _지금E(x) or (x["code"], x["인"]) in _k)   # [견줌]
                    _r = 시뮬(_c(_도, **_열E, **_옵), 묶2=_묶E)
                    if _r:
                        print(f"     {'    + ' + _라:<40}{len({인 for (_, 인) in _열쇠들(_쓸)} - _날E):>7}"
                              f"{_r['끝']:>16,.0f}{_r['끝'] / _기2['끝'] * 100:>8.0f}%"
                              f"{_r['낙']:>8.1f}%{_r['산']:>7}   (그 바탕의 %)")
                if _대 and _소:
                    _도 = (lambda x, _k=_열쇠들(_대) | _열쇠들(_소): _지금E(x) or (x["code"], x["인"]) in _k)
                    _r = 시뮬(_c(_도, **_열E, **_옵), 묶2=_묶E)
                    if _r:
                        print(f"     {'    + 대형+소형':<40}{'':>7}{_r['끝']:>16,.0f}"
                              f"{_r['끝'] / _기2['끝'] * 100:>8.0f}%{_r['낙']:>8.1f}%{_r['산']:>7}   (그 바탕의 %)")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ── ③ 얼마나 자주 뜨나 ──
        try:
            print("\n     ③ 해마다 **새로 열리는 날** (기존이 안 사던 날) — 「기회를 늘린다」에 값하나")
            print(f"     {'해':<7}" + "".join(f"{(k[:14]):>16}" for k in _후E))
            for _y in range(2016, 2027):
                _줄 = f"     {_y:<7}"
                for _이E, _evE in _후E.items():
                    _인들 = {x["인"] for x in _evE if str(날[x["인"]])[:4] == str(_y)}
                    _새 = len(_인들 - _날E)
                    _줄 += f"{_새:>16}"
                print(_줄)
            print("\n     ⇒ 한 해 몇 번 더 사게 되는지가 이 규칙의 실제 값이다")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③ 터졌다: {_e}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **TOGETHER — 마지막 관문: 같이 켜면** (2026-09-27) ══
    if _ONLY == "TOGETHER" or "TOGETHER" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── TOGETHER ⭐⭐⭐ **덜어 둔 후보들을 하나씩 · 둘씩 · 전부 얹어 본다** ──")
        print("     ①혼자 ②얹기 ④걷기 는 끝났다. 남은 건 ③ **같이 켜면 서로 잡아먹지 않나**")
        print("=" * 122)
        _합T, _묶T, _열T, _키T = _D준비()
        _지금키T = _키T["지금"]
        import glob as _gT
        _후보T = {}
        for _fT in sorted(_gT.glob(os.path.join(O._DATA, "_labs", "d_events_*.jsonl"))):
            _이T = os.path.basename(_fT)[9:-6]
            try:
                _evT = [json.loads(z) for z in io.open(_fT, encoding="utf-8") if z.strip()]
            except (OSError, ValueError):
                continue
            if _evT:
                _후보T[_이T] = {(x["code"], x["인"]) for x in _evT}
                # 바탕 풀에 없는 사건은 합쳐 넣는다 (띠가 달라 이 판 풀엔 없다)
                _본T = {(x["code"], x["인"]) for x in _합T}
                for x in _evT:
                    if (x["code"], x["인"]) not in _본T:
                        _합T.append(x)
                        _묶T.setdefault(x["인"], []).append(x)
        if not _후보T:
            print("     ⚠️ 덜어 둔 후보(d_events_*.jsonl)가 없다 — CELL_DUMP=1 로 칸 판을 먼저 돌려라")
            print("=" * 122)
            return 0
        print(f"\n     덜어 둔 후보 {len(_후보T)}개")
        for _이T, _kT in _후보T.items():
            print(f"        {_이T} — {len(_kT):,}건")

        def _지금T(x):
            return (x["code"], x["인"]) in _지금키T        # [견줌] 덜어 둔 열쇠

        _기T = 시뮬(_c(_지금T, **_열T), 묶2=_묶T)
        _날T = {인 for (_, 인) in _지금키T}
        print(f"\n     바탕 — {_기T['끝']:,.0f}원 · 낙폭 {_기T['낙']:.1f}% · 산 것 {_기T['산']}")
        print(f"\n     {'무엇을 켜나':<46}{'새 날':>7}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")

        import itertools as _itT

        def _재기T(이름, 켤것):
            _kT = set()
            for _c2 in 켤것:
                _kT |= _후보T[_c2]
            _도T = (lambda x, _k=_kT: _지금T(x) or (x["code"], x["인"]) in _k)   # [견줌]
            _rT = 시뮬(_c(_도T, **_열T), 묶2=_묶T)
            if not _rT:
                print(f"     {이름:<46} — 안 돌았다")
                return
            _새날T = len({인 for (_, 인) in _kT} - _날T)
            _okT = (_rT["산"] > _기T["산"], _rT["끝"] > _기T["끝"], _rT["낙"] > 낙폭기준)
            _걷T = ""
            if all(_okT):
                _a0 = 시뮬(_c(_지금T, **_열T), 시작년="2016", 끝년="2020", 묶2=_묶T)
                _a1 = 시뮬(_c(_도T, **_열T), 시작년="2016", 끝년="2020", 묶2=_묶T)
                _b0 = 시뮬(_c(_지금T, **_열T), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶T) if _a0 else None
                _b1 = 시뮬(_c(_도T, **_열T), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶T) if _a1 else None
                if _a0 and _a1 and _b0 and _b1:
                    _앞T = (_a1["끝"] / _a0["끝"] - 1) * 100
                    _뒤T = (_b1["끝"] / _b0["끝"] - 1) * 100
                    _걷T = f"  걷기 앞 {_앞T:+.1f}% 뒤 {_뒤T:+.1f}% " + ("✅" if (_앞T > 0.1 and _뒤T > 0.1) else "❌")
            print(f"     {이름:<46}{_새날T:>7}{_rT['끝']:>16,.0f}{_rT['끝'] / _기T['끝'] * 100:>8.0f}%"
                  f"{_rT['낙']:>7.1f}%{_rT['산']:>7}  " + ("✅ 셋 다" if all(_okT) else "❌") + _걷T)

        _이름들T = sorted(_후보T)
        for _n in (1, 2, 3):
            if _n > len(_이름들T):
                break
            print(f"\n     ── {_n}개씩 ──")
            for _조 in _itT.combinations(_이름들T, _n):
                _재기T(" + ".join(z[:20] for z in _조), _조)
        if len(_이름들T) > 3:
            print(f"\n     ── 전부 ({len(_이름들T)}개) ──")
            _재기T("전부", tuple(_이름들T))
        # ⭐ 2026-09-27 — 좋은 조합은 **해마다·체결 오차**까지 본다 (D-1 이 오차에 약하다고 했다)
        _볼조합 = []
        for _n in (1, 2):
            for _조 in _itT.combinations(_이름들T, _n):
                _kk = set()
                for _c2 in _조:
                    _kk |= _후보T[_c2]
                _볼조합.append((_조, _kk))
        _추 = []
        for _조, _kk in _볼조합:
            _도2 = (lambda x, _k=_kk: _지금T(x) or (x["code"], x["인"]) in _k)
            _rr = 시뮬(_c(_도2, **_열T), 묶2=_묶T)
            if _rr and _rr["끝"] > _기T["끝"] and _rr["낙"] > 낙폭기준:
                _추.append((_rr["끝"] / abs(_rr["낙"]), _조, _kk, _rr))
        _추.sort(key=lambda z: -z[0])
        _본조합 = set()
        for _점, _조, _kk, _rr in _추:
            _열쇠 = tuple(sorted(_kk))[:1]
            if len(_본조합) >= 3:
                break
            _본조합.add(_조)
            _이2 = " + ".join(z[:18] for z in _조)
            print("")
            print(f"     ── [{_이2}] 해마다 · 체결 오차 ──")
            _도3 = (lambda x, _k=_kk: _지금T(x) or (x["code"], x["인"]) in _k)
            _이긴, _진 = 0, 0
            for _y in range(2016, 2027):
                _r0 = 시뮬(_c(_지금T, **_열T), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶T)
                _r1 = 시뮬(_c(_도3, **_열T), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶T)
                if _r0 and _r1:
                    _이긴 += 1 if _r1["끝"] > _r0["끝"] * 1.0005 else 0
                    _진 += 1 if _r1["끝"] < _r0["끝"] * 0.9995 else 0
            print(f"        해마다 — 나은 해 {_이긴} · 못한 해 {_진} · 같은 해 {11 - _이긴 - _진}")
            _끝들 = []
            for _씨 in range(1, 11):
                _rn = 시뮬(_c(_도3, **_열T), 오차=1.0, 씨=_씨, 묶2=_묶T)
                if _rn:
                    _끝들.append(_rn["끝"])
            if _끝들:
                print(f"        체결 오차 ±1% 열 번 — 평균 {sum(_끝들) / len(_끝들):,.0f}원"
                      f" · 가장 나쁜 {min(_끝들):,.0f}원"
                      f" ({min(_끝들) / _rr['끝'] * 100:.0f}% · 오차 없을 때 {_rr['끝']:,.0f}원)")

        print("\n     ⚠️ 같이 켰을 때 각각보다 못하면 **서로 잡아먹는 것**이다 — 그러면 하나만 고른다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **Q-29 「공통 문」까지 그 칸 자료로 — 다섯 띠 + 업종별** (2026-09-22) ══
    #    사용자: 「누구나 통과해야 하는 문 자체가 소형주인데
    #             그 다음 대형주 테스트 하는게 무슨 소용이야」 — 맞다.
    #    그리고 내가 이 절을 처음엔 **대형주만** 재게 짰다.
    #    사용자: 「대형주만의 판이 아니라 대형·중형·소형·섹터별 다양하게 하라고」 — 맞다.
    #    ⇒ 칸마다(띠 다섯 · 업종별) **재무·대금·신호·상대갭·비중·자리를 전부**
    #       그 칸 자료에서 낸다. 소형 값을 하나도 안 쓰고, **혼자 세운다**
    if _ONLY in ("", "Q29"):
        print("\n" + "=" * 122)
        print("  ── Q-29 ⭐⭐⭐ **「공통 문」까지 그 칸 자료로 — 띠 다섯 + 업종별** ──")
        print("     재무 문턱 · 대금 하한 · 신호 · 상대갭 · 비중 · 자리 — 전부 그 칸에서")
        print("     ⚠️ 소형 규칙에 OR 로 얹지 않는다. **혼자 세운다**")
        print("=" * 122)
        if not _문열기:
            print("\n     ⚠️ 이 절은 **OPENFIN=1** 이 있어야 뜻이 있다 — 건너뛴다")
            print("        지금 사건은 이미 소형 재무 문을 통과한 것뿐이다")
            print("=" * 122)
        else:
            print(f"\n     사건 {len(사건):,}건 (재무 문을 안 건 풀"
                  f" · 시총 {_크기하한 / 1e8:,.0f}~{_크기웃한 / 1e8:,.0f}억"
                  f" · 램지킴이 대금 {_열대금 / 1e8:g}억)")

            # ── 잴 칸: 띠 다섯 + 업종별 ──
            _ORCELL = [0, None, None]   # CELL_OR 용 그릇 [재본 칸 수, _D준비 결과, 바탕 시뭄]
            _칸들29 = []
            for _라, _lo, _hi in (("초소형 100~300억", 100, 300),
                                  ("소형 300~2,000억", 300, 2000),
                                  ("중형 2,000억~1조", 2000, 10000),
                                  ("대형 1조~10조", 10000, 100000),
                                  ("초대형 10조↑", 100000, 9e12)):
                _칸들29.append((f"띠 {_라}",
                                (lambda x, a=_lo, b=_hi:
                                 a <= (x.get("시총억") or 0) < b)))
            _섹셈29 = {}
            for x in 사건:
                _n = x.get("섹터")
                if _n:
                    _섹셈29[_n] = _섹셈29.get(_n, 0) + 1
            for _섹29 in [k for k, v in sorted(_섹셈29.items(), key=lambda t: -t[1])
                          if v >= 20000][:14]:
                _칸들29.append((f"업종 {_섹29[:12]}",
                                (lambda x, a=_섹29: x.get("섹터") == a)))
            # ⭐ 사용자: 「내가 말한 것 말고도 구분할 수 있는 게 있으면 구분해서
            #    테스트해보라고. 거래 두께나 이런거! 넓게 다양하게!」
            #    ⇒ 크기·업종 말고 **다른 잣대**로도 가른다. 오분위 아래/위 20%
            # ⭐⭐ 사용자: 「이것 말고 다른 재료도 있을텐데 왜 이것만 재는거야?」
            #    ⇒ 손으로 고르지 않는다. **사건 칸 전부**를 코드가 센다 + _값P 특수 14개.
            #    재료가 아닌 칸만 뺀다 (이름·결과·문에 이미 쓴 것·갭·시총·주가 중복)
            _아님29 = {"인", "code", "해", "_지수이름", "섹터", "매수", "재통과", "흑자",
                       "_20", "_40", "_겹친", "갭", "시총억", "원시"}
            _칸이름29 = []
            for _k29 in sorted(사건[0].keys()):
                if _k29 in _아님29:
                    continue
                _n수29 = sum(1 for x in 사건[:5000]
                             if isinstance(x.get(_k29), (int, float)))
                if _n수29 >= 1500:
                    _칸이름29.append(_k29)
            _특수29 = ("자사주60", "코스피200선물20", "ETF괴리", "ETF괴리20", "기준금리20",
                       "무역수지비", "금값20", "공시장중", "ETF시총20", "미국선거전5",
                       "금통위변경후5", "봄", "여름", "가을", "겨울",
                       # ⭐ 2026-09-23 (B1·G1) — 넷을 더했다. 「같이 빠진 걸 산다」를 칸마다 재게 된다
                       "무리낙폭", "무리와벌어짐", "지수갭", "악재공시")
            _재전부29 = ([(k, (lambda x, k=k: x.get(k))) for k in _칸이름29]
                         + [(k, (lambda x, k=k: _값P(x, k))) for k in _특수29])
            print(f"     재료 {len(_재전부29)}개 — 사건 칸 {len(_칸이름29)} + 특수 {len(_특수29)}"
                  f" (손으로 안 골랐다): " + " ".join(k for k, _ in _재전부29))
            _잣29 = tuple(_재전부29)
            for _라잣29, _꺼잣29 in _잣29:
                _v29 = sorted(z for z in (_꺼잣29(x) for x in 사건)
                              if z is not None)
                if len(_v29) < len(사건) * 0.3:
                    print(f"     {_라잣29:<14} 값이 {len(_v29):,}개뿐 — 잣대로는 건너뜀")
                    continue
                if len(set(_v29[::max(1, len(_v29) // 5000)])) < 20:
                    continue        # 이진·계단 재료 — 20% 컷이 0 이 된다 (전에 당했다)
                _아29 = _v29[len(_v29) // 5]
                _위29 = _v29[len(_v29) * 4 // 5]
                _칸들29.append((f"{_라잣29} 아래20%",
                                (lambda x, f=_꺼잣29, c=_아29:
                                 f(x) is not None and f(x) <= c)))
                _칸들29.append((f"{_라잣29} 위20%",
                                (lambda x, f=_꺼잣29, c=_위29:
                                 f(x) is not None and f(x) >= c)))
            print(f"     잴 칸 {len(_칸들29)}개 — 띠 다섯 · 업종 · "
                  f"거래두께·변동성·주가·회전율·지분율·PBR·ROE·이익률·유동비율·"
                  f"흔들림·60일선 (이 풀에 든 것만 실제로 돈다)")

            _모은29 = []
            for _라칸29, _든칸29 in _칸들29:
                _칸29 = [x for x in 사건 if _든칸29(x)]
                if len(_칸29) < 5000:
                    continue
                print(f"\n     ══ [{_라칸29}] {len(_칸29):,}건 — 이 칸 자료로만 ══")

                # ⓐ 재무·대금 문을 **이 칸 분포**에서
                _잉29 = sorted(z for z in (x.get("잉여금") for x in _칸29)
                               if z is not None)
                _부29 = sorted(z for z in (x.get("부채") for x in _칸29)
                               if z is not None)
                _대29 = sorted(z for z in (x.get("대금억") for x in _칸29)
                               if z is not None)
                if not (_잉29 and _부29 and _대29):
                    print("        재무·대금 분포를 못 냈다 — 건너뜀")
                    continue
                _잉컷29 = _잉29[int(len(_잉29) * 0.30)]
                _부컷29 = _부29[int(len(_부29) * 0.70)]
                _대컷29 = _대29[int(len(_대29) * 0.20)]
                print(f"        재무 — 잉여금 ≥ {_잉컷29:,.1f}% "
                      f"(소형이 쓰던 값 {R.잉여금하한:g}%)"
                      f" · 부채 ≤ {_부컷29:,.1f}% (소형 {R.부채상한:g}%)")
                print(f"        대금 — ≥ {_대컷29:,.1f}억 (소형 {R.대금하한억:g}억)")

                def _칸문29(x, a=_잉컷29, b=_부컷29, c=_대컷29, 든=_든칸29):
                    r"""**이 칸의 공통 문** — 소형 값을 하나도 안 쓴다"""
                    if not 든(x):
                        return False
                    _잉, _부 = x.get("잉여금"), x.get("부채")
                    if _잉 is None or _부 is None or _잉 < a or _부 > b:
                        return False
                    if x.get("흑자") != 1.0:
                        return False
                    return (x.get("대금억") or 0) >= c

                _든29 = [x for x in _칸29 if _칸문29(x) and x.get("_20") is not None]
                if len(_든29) < 3000:
                    print(f"        문을 통과한 것 {len(_든29):,}건 — 표본 부족")
                    continue
                _바29 = sum(1 for x in _든29 if x["_20"] > 0) / len(_든29) * 100
                print(f"        문을 통과한 것 {len(_든29):,}건 · 바탕 {_바29:.1f}%")

                # ⓑ 신호 재료·문턱을 이 칸에서 — **재료 전부 · 방향 둘 다** (자료가 고른다)
                _재신호29 = [(k + "↓", f, "아래") for k, f in _재전부29] \
                          + [(k + "↑", f, "위") for k, f in _재전부29]
                _문턱29, _좋29 = {}, []
                _값29 = {}   # ⭐ 2026-09-25 — 문턱을 흔들려면 값 목록이 있어야 한다
                for _이29, _꺼29, _방29 in _재신호29:
                    _v29 = sorted(z for z in (_꺼29(x) for x in _든29)
                                  if z is not None)
                    if len(_v29) < len(_든29) * 0.25:
                        continue
                    if len(set(_v29[::max(1, len(_v29) // 2000)])) < 20:
                        continue    # 이진 재료 — 분위수 컷이 뜻이 없다
                    _값29[_이29] = _v29
                    _문턱29[_이29] = (_v29[len(_v29) // 5] if _방29 == "아래"
                                      else _v29[len(_v29) * 4 // 5])
                for _이29, _꺼29, _방29 in _재신호29:
                    _컷29 = _문턱29.get(_이29)
                    if _컷29 is None:
                        continue
                    _z29 = [x for x in _든29 if (_꺼29(x) is not None)
                            and ((_꺼29(x) <= _컷29) if _방29 == "아래"
                                 else (_꺼29(x) >= _컷29))]
                    if len(_z29) < 300:
                        continue
                    _길29 = sum(1 for x in _z29 if x["_20"] > 0) / len(_z29) * 100
                    _앞29 = [x for x in _z29 if 날[x["인"] - 1][:4] <= "2018"]
                    _뒤29 = [x for x in _z29 if 날[x["인"] - 1][:4] > "2018"]
                    if len(_앞29) < 100 or len(_뒤29) < 100:
                        continue
                    _ㅇ앞 = sum(1 for x in _앞29 if x["_20"] > 0) / len(_앞29) * 100
                    _ㅇ뒤 = sum(1 for x in _뒤29 if x["_20"] > 0) / len(_뒤29) * 100
                    if (_길29 - _바29) < 2.0 or (_ㅇ앞 - _바29) * (_ㅇ뒤 - _바29) <= 0:
                        continue
                    _좋29.append((_길29 - _바29, _이29, _길29))
                _좋29.sort(reverse=True)
                print("        센 재료 — " + (" · ".join(
                    f"{r}{d:+.1f}({w:.1f}%)" for d, r, w in _좋29[:3]) or "없음"))
                if not _좋29:
                    print("        ⇒ 이 칸에서 센 재료가 없다 — 규칙을 못 만든다")
                    continue

                # ⓒ 상대갭도 이 칸에서
                _갭29 = sorted(z for z in (x.get("갭") for x in _든29)
                               if z is not None)
                _갭컷29 = _갭29[int(len(_갭29) * 0.20)] if len(_갭29) > 1000 else None
                if _갭컷29 is not None:
                    print(f"        상대갭 — {_갭컷29:,.2f}% (이 칸 갭 분포 20분위)")

                def _띠규칙29(x, 쓸것, 문=_칸문29, 표=None, 재들=tuple(_재신호29)):
                    r"""**이 칸 전용 규칙** — 소형 문턱을 하나도 안 쓴다. 재료·방향은 자료가 고른 것"""
                    if not 문(x):
                        return False
                    for _이, _꺼, _방 in 재들:
                        if _이 not in 쓸것:
                            continue
                        _컷 = (표 or {}).get(_이)
                        if _컷 is None:
                            return False
                        _v = _꺼(x)
                        if _v is None:
                            return False
                        if (_v > _컷) if _방 == "아래" else (_v < _컷):
                            return False
                    return True

                # ⓓ 비중·자리도 격자로 (소형의 0.20·4 를 그대로 쓰지 않는다)
                _쓸들29 = [(_좋29[0][1],)]
                if len(_좋29) >= 2:
                    _쓸들29.append((_좋29[0][1], _좋29[1][1]))
                print(f"\n        {'설정':<32}{'끝 자산':>17}{'낙폭':>8}{'산 것':>7}  판정")
                _산29 = []
                for _쓸29 in _쓸들29:
                    for _비29 in (0.20, 0.33):
                        for _자29 in (3, 4, 6):
                            _fn29 = (lambda x, c=_쓸29, m=dict(_문턱29):
                                     _띠규칙29(x, c, 표=m))
                            # ⚠️⚠️ **B12 가 0건 산 원인** (2026-09-22 11:20) — 시뮬이 그날 후보를
                            #    거를 때 c["시총하한"]=300억 · c["대금하한"]=1억 을 **소형 값 그대로**
                            #    썼다. 초소형은 전부 300억 미만이라 한 건도 못 샀다.
                            #    ⇒ 여기서 셋을 연다. 크기·대금은 **칸의 문(_칸문29)이 지킨다**
                            _옵29 = {"비중": _비29, "하루상한": _자29,
                                     "시총하한": 0, "시총상한": 999999999, "대금하한": 0}
                            if _갭컷29 is not None:
                                _옵29["상대갭"] = _갭컷29
                            _r29 = 시뮬(_c(_fn29, **_옵29))
                            if not _r29:
                                continue
                            _표29 = f"{'+'.join(_쓸29)[:15]} 비중{_비29:.0%} 자리{_자29}"
                            _ok29 = (_r29["끝"] > 5_000_000
                                     and _r29["낙"] > 낙폭기준 and _r29["산"] >= 30)
                            if _ok29:
                                _산29.append((_표29, _fn29, _옵29, _r29, _쓸29))
                            print(f"        {_표29:<32}{_r29['끝']:>16,.0f}원"
                                  f"{_r29['낙']:>7.1f}%{_r29['산']:>7}  "
                                  + ("✅ 돈 늘고 낙폭 안" if _ok29 else "❌"))
                if not _산29:
                    print(f"\n        ⇒ **[{_라칸29}] 혼자 서는 규칙이 없다**")
                    continue
                _산29.sort(key=lambda t: -t[3]["끝"])
                for _표29, _fn29, _옵29, _r29, _쓸29 in _산29[:2]:
                    print(f"\n        ── [{_라칸29} · {_표29}] 해마다 + 걷기 ──")
                    _차29 = []
                    for _y29 in range(2016, 2027):
                        _a29 = 시뮬(_c(_fn29, **_옵29),
                                    시작년=str(_y29), 끝년=str(_y29))
                        if _a29:
                            _차29.append((_a29["끝"] / 5_000_000 - 1) * 100)
                    if _차29:
                        print(f"           해마다 — 평균 {sum(_차29) / len(_차29):+.1f}%"
                              f" · 진 해 {sum(1 for z in _차29 if z < 0)}/{len(_차29)}")
                    # ⚠️⚠️ **2026-09-22 12:55 고침** — 전엔 `_걷기(_fn29, _fn29, …)` 로 불렀다.
                    #    자기 자신과 견주니 차이가 늘 0.0% → **절대 통과 못 하는 관문**이었다.
                    #    B14 에서 11해 중 1해만 진 규칙 넷이 전부 ❌ 로 찍힌 게 이것이다.
                    #    혼자 서는 규칙은 **절대 기준**으로 본다:
                    #      앞(2010~2020) 시드보다 늘었나 · 뒤(2021~2026, 앞이 끝낸 돈으로) 또 늘었나 · 둘 다 낙폭 안
                    _앞29 = 시뮬(_c(_fn29, **_옵29), 시작년="2010", 끝년="2020")
                    _뒤29 = (시뮬(_c(_fn29, **_옵29), 시작년="2021", 끝년="2026", 시드=_앞29["끝"])
                             if _앞29 else None)
                    if _앞29 and _뒤29:
                        _앞ok29 = _앞29["끝"] > 5_000_000 and _앞29["낙"] > 낙폭기준
                        _뒤ok29 = _뒤29["끝"] > _앞29["끝"] and _뒤29["낙"] > 낙폭기준
                        print(f"           앞 2010~2020: 5,000,000원 → {_앞29['끝']:,.0f}원"
                              f"  {(_앞29['끝'] / 5_000_000 - 1) * 100:+.1f}%"
                              f"  (낙폭 {_앞29['낙']:.1f}% · 산 것 {_앞29['산']})"
                              + ("  ✅" if _앞ok29 else "  ❌"))
                        print(f"           뒤 2021~2026: {_앞29['끝']:,.0f}원 → {_뒤29['끝']:,.0f}원"
                              f"  {(_뒤29['끝'] / _앞29['끝'] - 1) * 100:+.1f}%"
                              f"  (낙폭 {_뒤29['낙']:.1f}% · 산 것 {_뒤29['산']})"
                              + ("  ✅" if _뒤ok29 else "  ❌"))
                        print("           걷기: " + ("✅ 앞뒤 둘 다 늘고 낙폭 안" if (_앞ok29 and _뒤ok29)
                                                    else "❌ 한 토막이 안 늘거나 낙폭 밖")
                              + "   (혼자 서는 규칙 · 절대 기준)")

                    # ⭐ CELL_OR (2026-09-24) — 혼자 선 칸을 **그 자리에서 지금 실전 위에 얹어** 본다.
                    #    「혼자 선다」는 기준이 아니다 — 빈 날을 채우고 돈이 늘어야 한다
                    if os.environ.get("CELL_OR") and _r29["끝"] >= float(os.environ.get("CELL_OR_MIN") or 4e7):
                        if _ORCELL[0] < int(os.environ.get("CELL_OR_MAX") or 25):
                            _ORCELL[0] += 1
                            try:
                                if _ORCELL[1] is None:
                                    _ORCELL[1] = _D준비()
                                _합OR, _묶OR, _열OR, _키OR = _ORCELL[1]
                                _지OR = _키OR["지금"]
                                if _ORCELL[2] is None:
                                    _ORCELL[2] = 시뮬(_c((lambda x: (x["code"], x["인"]) in _지OR), **_열OR), 묶2=_묶OR)
                                _기OR = _ORCELL[2]
                                _새OR = {(x["code"], x["인"]) for x in 사건 if _fn29(x)}
                                _날OR = {인 for (_, 인) in _지OR}
                                _새날OR = len({인 for (_, 인) in _새OR} - _날OR)
                                _도OR = (lambda x, _k=_새OR, _b=_지OR:
                                         (x["code"], x["인"]) in _b or (x["code"], x["인"]) in _k)   # [견줌]
                                _rOR = 시뮬(_c(_도OR, **_열OR), 묶2=_묶OR)
                                if _rOR and _기OR:
                                    _okOR = (_rOR["산"] > _기OR["산"], _rOR["끝"] > _기OR["끝"],
                                             _rOR["낙"] > 낙폭기준)
                                    _걷OR = ""
                                    if all(_okOR):
                                        _a0 = 시뮬(_c((lambda x: (x["code"], x["인"]) in _지OR), **_열OR),
                                                   시작년="2016", 끝년="2020", 묶2=_묶OR)
                                        _a1 = 시뮬(_c(_도OR, **_열OR), 시작년="2016", 끝년="2020", 묶2=_묶OR)
                                        _b0 = 시뮬(_c((lambda x: (x["code"], x["인"]) in _지OR), **_열OR),
                                                   시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶OR) if _a0 else None
                                        _b1 = 시뮬(_c(_도OR, **_열OR), 시작년="2021", 끝년="2026",
                                                   시드=_a1["끝"], 묶2=_묶OR) if _a1 else None
                                        if _a0 and _a1 and _b0 and _b1:
                                            _앞OR = (_a1["끝"] / _a0["끝"] - 1) * 100
                                            _뒤OR = (_b1["끝"] / _b0["끝"] - 1) * 100
                                            _걷OR = (f" · 걷기 앞 {_앞OR:+.1f}% 뒤 {_뒤OR:+.1f}% "
                                                     + ("✅" if (_앞OR > 0.1 and _뒤OR > 0.1) else "❌"))
                                    print(f"           ⭐ 지금 실전 위에 얹으면 — 새 날 {_새날OR}"
                                          f" · {_rOR['끝']:,.0f}원 ({_rOR['끝'] / _기OR['끝'] * 100:.0f}%)"
                                          f" · 낙폭 {_rOR['낙']:.1f}% · 산 것 {_rOR['산']} (바탕 {_기OR['산']})  "
                                          + ("✅ 셋 다" if all(_okOR) else "❌") + _걷OR, flush=True)
                                    # ⭐ CELL_DUMP (2026-09-27) — 걷기까지 통과한 칸은 **사건을 덜어 둔다**. 띠가 달라 한 판에서 같이 못 켜기 때문
                                    if os.environ.get("CELL_DUMP") and _걷OR.endswith("✅"):
                                        try:
                                            _꼬D = (os.environ.get("BAND_TAG") or "띠") + "_" + "".join(
                                                z for z in (_라칸29 + "_" + "+".join(_쓸29)) if z.isalnum() or z in "가-힣_+↓↑")[:60]
                                            _길D = os.path.join(O._DATA, "_labs", f"d_events_{_꼬D}.jsonl")
                                            _뽑D = [x for x in 사건 if (x["code"], x["인"]) in _새OR]
                                            with io.open(_길D, "w", encoding="utf-8") as _fD:
                                                for _xD in _뽑D:
                                                    _fD.write(json.dumps(_xD, ensure_ascii=False, default=str) + "\n")
                                            print(f"           💾 덜어 뒀다 — {len(_뽑D):,}건 → d_events_{_꼬D}.jsonl", flush=True)
                                        except Exception as _eD:  # noqa: BLE001
                                            print(f"           ⚠️ 덜기 터졌다: {type(_eD).__name__} {_eD}")
                                    # ⭐ CELL_SHAKE (2026-09-25) — 얹기까지 ✅ 인 칸만 **문턱을 옮겨** 다시 얹는다.
                                    #    칸 문턱은 「그 칸 값의 20분위」다. 10~30분위로 옮겨도 서야 우연이 아니다
                                    if os.environ.get("CELL_SHAKE") and _걷OR.endswith("✅"):
                                        print("           ── 문턱 흔들기 (이 칸 값의 분위를 옮긴다) ──", flush=True)
                                        for _qS in (0.10, 0.15, 0.20, 0.25, 0.30):
                                            try:
                                                _표S = {}
                                                for _이S in _쓸29:
                                                    _vS = _값29.get(_이S)
                                                    if not _vS:
                                                        continue
                                                    _표S[_이S] = (_vS[int(len(_vS) * _qS)] if _이S.endswith("↓")
                                                                  else _vS[int(len(_vS) * (1 - _qS))])
                                                if len(_표S) != len(_쓸29):
                                                    continue
                                                _fnS = (lambda x, c=_쓸29, mm=_표S: _띠규칙29(x, c, 표=mm))
                                                _새S = {(x["code"], x["인"]) for x in 사건 if _fnS(x)}
                                                _도S = (lambda x, _k=_새S, _b=_지OR:
                                                        (x["code"], x["인"]) in _b or (x["code"], x["인"]) in _k)   # [견줌]
                                                _rS = 시뮬(_c(_도S, **_열OR), 묶2=_묶OR)
                                                if not _rS:
                                                    continue
                                                _새날S = len({인 for (_, 인) in _새S} - _날OR)
                                                _okS = (_rS["산"] > _기OR["산"], _rS["끝"] > _기OR["끝"], _rS["낙"] > 낙폭기준)
                                                print(f"              {int(_qS * 100):>3}분위 — 새 날 {_새날S:>3}"
                                                      f" · {_rS['끝']:>15,.0f}원 ({_rS['끝'] / _기OR['끝'] * 100:>3.0f}%)"
                                                      f" · 낙폭 {_rS['낙']:>6.1f}% · 산 것 {_rS['산']:>4}  "
                                                      + ("✅" if all(_okS) else "❌")
                                                      + ("   ← 지금 자리" if abs(_qS - 0.20) < 1e-9 else ""), flush=True)
                                                # ⭐ 2026-09-26 — 셋 다를 넘긴 분위는 **증분 걷기**까지 본다 (이 집 규칙의 네째 관문)
                                                if all(_okS):
                                                    _aS = 시뮬(_c((lambda x: (x["code"], x["인"]) in _지OR), **_열OR), 시작년="2016", 끝년="2020", 묶2=_묶OR)
                                                    _a1S = 시뮬(_c(_도S, **_열OR), 시작년="2016", 끝년="2020", 묶2=_묶OR)
                                                    _bS = 시뮬(_c((lambda x: (x["code"], x["인"]) in _지OR), **_열OR), 시작년="2021", 끝년="2026", 시드=_aS["끝"], 묶2=_묶OR) if _aS else None
                                                    _b1S = 시뮬(_c(_도S, **_열OR), 시작년="2021", 끝년="2026", 시드=_a1S["끝"], 묶2=_묶OR) if _a1S else None
                                                    if _aS and _a1S and _bS and _b1S:
                                                        _앞S = (_a1S["끝"] / _aS["끝"] - 1) * 100
                                                        _뒤S = (_b1S["끝"] / _bS["끝"] - 1) * 100
                                                        print(f"                     증분 걷기 앞 {_앞S:+.1f}% 뒤 {_뒤S:+.1f}% "
                                                              + ("✅" if (_앞S > 0.1 and _뒤S > 0.1) else "❌"), flush=True)
                                            except Exception as _eS:  # noqa: BLE001
                                                print(f"              {int(_qS * 100)}분위 터졌다: {type(_eS).__name__} {_eS}")
                            except Exception as _eOR:  # noqa: BLE001
                                print(f"           ⚠️ 얹기 터졌다: {type(_eOR).__name__} {_eOR}")
                        if _앞ok29 and _뒤ok29:
                            _모은29.append((_라칸29, _표29, _r29))
                    else:
                        print("           걷기: ⚠️ 한 토막을 못 냈다")
            print(f"\n     ══ **세 관문을 다 넘은 칸 규칙 {len(_모은29)}개** ══")
            for _라칸29, _표29, _r29 in _모은29:
                print(f"       {_라칸29} · {_표29}  {_r29['끝']:,.0f}원"
                      f" · 낙폭 {_r29['낙']:.1f}% · 산 것 {_r29['산']}")
            if not _모은29:
                print("       (없다)")
        print("\n     ⚠️ 이 절은 **소형 Ⓗ 를 한 번도 안 쓴다** — 혼자 선 값이다")
        print("     ⚠️ 반영은 실전 코드를 건드리는 변경이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

    if _ONLY == "Q29":
        print("\n  ⭐ ONLY=Q29 — 여기서 끝낸다 (Q-19 본체와 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐ **DUMPH — 지금 실전 바탕이 고르는 사건을 파일로 덜어 둔다** (2026-09-22) [바탕 덜기] ══
    #    [바탕 덜기] = 이 절은 Ⓗ(+업종 규칙)를 그대로 쓴다 — 막개 ④가 코드로 확인하고 봐준다 (덤프 파일을 실제로 쓸 때만)
    #    Q-30 이 띠 풀에 얹어 쓴다. 보통 풀(OPENFIN 없음)에서 돌린다.
    if _ONLY == "DUMPH":
        if _문열기:
            print("  ⚠️ DUMPH 는 문을 안 연 보통 풀에서 돌려야 한다 (OPENFIN 빼라)")
            return 1
        _의이름D = next((k for k in {x.get("섹터") for x in 사건 if x.get("섹터")}
                        if str(k).startswith("의료")), None)
        _의칸D = [x for x in 사건 if x.get("섹터") == _의이름D and x.get("_20") is not None]
        _낙값D = sorted(z for z in (x.get("낙폭60") for x in _의칸D) if z is not None)
        _의문D = _낙값D[len(_낙값D) // 5] if _낙값D else None

        def _의료D(x):
            if _의문D is None or x.get("섹터") != _의이름D:
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            _d = x.get("낙폭60")
            return _d is not None and _d <= _의문D

        # ⭐ R0 (2026-09-23 · 연휴 계획) — DUMPH_LIVE=1 이면 **rule_def.업종규칙맞나() 를 그대로 불러**
        #    지금 실전(Ⓗ + 업종 규칙 셋: 의료·금속·운송장비)을 덜어 둔다. 시험과 실전이 한 함수를 쓴다.
        #    아니면 예전처럼 Ⓗ + 의료(판 안 정의) — 옛 바탕 재현용
        _실전으로 = bool(os.environ.get("DUMPH_LIVE"))

        def _업종실전D(x):
            _지금문 = 재무통과(x) and 대금통과(x) and (x.get("시총억") or 0) >= R.시총하한억
            _맞, _ = R.업종규칙맞나(_산업.get(x["code"]), {
                "시총억": x.get("시총억"), "대금억": x.get("대금억"), "_지금문통과": _지금문,
                "잉여금비율": x.get("잉여금"), "부채비율": x.get("부채"), "흑자": x.get("흑자"),
                "낙폭60": x.get("낙폭60"), "낙120": x.get("낙120")})
            return bool(_맞)

        _바탕D = (lambda x: _H(x) or _업종실전D(x)) if _실전으로 else (lambda x: _H(x) or _의료D(x))
        _덤프 = [x for x in 사건 if _바탕D(x)]
        with io.open(_덤프길, "w", encoding="utf-8") as _f:
            for x in _덤프:
                _f.write(json.dumps(x, ensure_ascii=False, default=str) + "\n")
        _r0 = 시뮬(_c(_바탕D))
        import datetime as _dtD
        import subprocess as _sp
        try:
            _커밋 = _sp.check_output(["git", "rev-parse", "--short", "HEAD"],
                                   cwd=os.path.dirname(O._DATA)).decode().strip()
        except Exception:  # noqa: BLE001
            _커밋 = "?"
        print(f"\n  DUMPH — {'지금 실전(Ⓗ + rule_def 업종규칙 ' + '·'.join(R.업종규칙) + ')' if _실전으로 else 'Ⓗ + 의료(판 안 정의)'}"
              f" 에 맞는 사건 {len(_덤프):,}건을 {_덤프길} 에 덜었다")
        print(f"         ⭐ 바탕 = {_dtD.date.today().isoformat()} · 커밋 {_커밋} · 시뮬 {_r0['끝']:,.0f}원"
              f" · 낙폭 {_r0['낙']:.1f}% · 산 것 {_r0['산']}"
              + ("  (Q-34 소형운송장비+중형금속 341,296,340 근처여야 한다)" if _실전으로 else "  (Q-28 ⓪ 262,871,069 과 같아야 한다)"))
        return 0

    # ══ ⭐⭐⭐ **NEWSF (B6) — 악재 공시가 있는 종목을 빼면** (2026-09-23) ══
    if _ONLY == "NEWSF" or "NEWSF" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── NEWSF ⭐⭐⭐ **뉴스는 찾는 재료가 아니라 거르는 재료였다 — 새 바탕에서 다시** ──")
        print("     ⚠️ 거르개는 기회를 줄인다. 낙폭이 좋아져도 **돈이 줄면 안 넣는다**")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금N(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기N = 시뮬(_c(_지금N, **_열기D), 묶2=_묶D)
        _기돈낙N = _기N["끝"] / abs(_기N["낙"]) if _기N["낙"] else 0
        print(f"\n     악재 공시가 있는 날 {len(_악재표):,}일")
        print(f"     바탕 — {_기N['끝']:,.0f}원 · 낙폭 {_기N['낙']:.1f}% · 산 것 {_기N['산']}")

        def _악재있나(x, 며칠):
            """그 종목에 최근 며칠 안(그날 포함 전날까지) 악재 공시가 있었나"""
            _i = x["인"] - 1
            for _k in range(max(0, _i - 며칠 + 1), _i + 1):
                if _k < len(날) and (_악재표.get(날[_k]) or {}).get(x["code"]):
                    return True
            return False

        print(f"\n     {'거르개':<28}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>10}  판정")
        print(f"     {'없음 (지금)':<28}{_기N['끝']:>16,.0f}{100:>8.0f}%{_기N['낙']:>7.1f}%{_기N['산']:>7}{100:>9.0f}%  지금")
        for _며칠, _이 in ((1, "그날 악재 빼기"), (5, "최근 5일 악재 빼기"),
                          (20, "최근 20일 악재 빼기"), (60, "최근 60일 악재 빼기")):
            try:
                _거름 = (lambda x, d=_며칠: _지금N(x) and not _악재있나(x, d))
                _r = 시뮬(_c(_거름, **_열기D), 묶2=_묶D)
                if not _r:
                    continue
                _돈낙 = _r["끝"] / abs(_r["낙"]) if _r["낙"] else 0
                _좋 = _r["끝"] > _기N["끝"] and _r["낙"] > 낙폭기준
                _걷 = ""
                if _좋:
                    _a0 = 시뮬(_c(_지금N, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
                    _a1 = 시뮬(_c(_거름, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
                    _b0 = 시뮬(_c(_지금N, **_열기D), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶D) if _a0 else None
                    _b1 = 시뮬(_c(_거름, **_열기D), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶D) if _a1 else None
                    if _a0 and _a1 and _b0 and _b1:
                        _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
                        _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
                        _걷 = f"  걷기 앞 {_앞:+.1f}% 뒤 {_뒤:+.1f}% " + ("✅" if (_앞 > 0.1 and _뒤 > 0.1) else "❌")
                print(f"     {_이:<28}{_r['끝']:>16,.0f}{_r['끝'] / _기N['끝'] * 100:>8.0f}%"
                      f"{_r['낙']:>7.1f}%{_r['산']:>7}{_돈낙 / _기돈낙N * 100 if _기돈낙N else 0:>9.0f}%  "
                      + ("✅" if _좋 else "❌") + _걷)
            except Exception as _e:  # noqa: BLE001
                print(f"     ⚠️ {_이} 터졌다: {_e}")
        print("\n     ⇒ 돈이 줄고 낙폭만 좋아지면 **안 넣는다**. 돈·낙폭이 같이 좋아질 때만 월요일 보고에 올린다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **REGIME — 이 규칙은 언제 잘 드나** (2026-09-23) ══
    if _ONLY == "REGIME" or "REGIME" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── REGIME ⭐⭐⭐ **국면별 성적 — 화면의 「국면」 칸이 정말 성적을 가르나** ──")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금G2(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기G2 = 시뮬(_c(_지금G2, **_열기D), 묶2=_묶D)
        print(f"\n     바탕 — {_기G2['끝']:,.0f}원 · 낙폭 {_기G2['낙']:.1f}% · 산 것 {_기G2['산']}")
        _맵G2 = {}
        for x in _합:
            _맵G2[(x["code"], x["인"])] = x
        _날인G2 = {_d: _i for _i, _d in enumerate(날)}
        _기록G2 = []
        시뮬(_c(_지금G2, **_열기D), 묶2=_묶D, 기록=_기록G2)

        def _칸찍기(제목, 칸함수, 이름들):
            _벌 = {이: [] for 이 in 이름들}
            for _거래 in _기록G2:
                _x = _맵G2.get((_거래[1], _날인G2.get(_거래[0])))
                if _x is None:
                    continue
                _칸 = 칸함수(_x)
                if _칸 in _벌:
                    _벌[_칸].append(_거래[4])
            print(f"\n     {제목}")
            print(f"     {'칸':<22}{'건수':>7}{'평균 수익':>11}{'가운데':>10}{'이긴 비율':>11}")
            for 이 in 이름들:
                _v = sorted(_벌[이])
                if not _v:
                    print(f"     {이:<22}{0:>7}")
                    continue
                print(f"     {이:<22}{len(_v):>7}{sum(_v) / len(_v):>10.1f}%{_v[len(_v) // 2]:>9.1f}%"
                      f"{sum(1 for z in _v if z > 0) / len(_v) * 100:>10.0f}%")
            return _벌

        # ① 시장 20일 낙폭
        try:
            _이름1 = ["≤ -15%", "-15 ~ -10%", "-10 ~ -5%", "-5 ~ 0%", "> 0%", "모름"]

            def _칸1(x):
                v = x.get("시장낙폭")
                if v is None:
                    return "모름"
                return ("≤ -15%" if v <= -15 else "-15 ~ -10%" if v <= -10 else
                        "-10 ~ -5%" if v <= -5 else "-5 ~ 0%" if v <= 0 else "> 0%")

            _칸찍기("① 그날 시장(제 지수)의 20일 낙폭", _칸1, _이름1)
            # 그 국면에서만 샀을 때 자본 시뮬
            print(f"\n     그 국면에서만 산다면 (자본 시뮬)")
            print(f"     {'칸':<22}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}")
            for 이 in _이름1[:-1]:
                _r = 시뮬(_c((lambda x, a=이: _지금G2(x) and _칸1(x) == a), **_열기D), 묶2=_묶D)
                if _r:
                    print(f"     {이:<22}{_r['끝']:>16,.0f}{_r['끝'] / _기G2['끝'] * 100:>8.0f}%"
                          f"{_r['낙']:>7.1f}%{_r['산']:>7}")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ② 시장 변동성
        try:
            _값2 = sorted(z for z in (x.get("시장변동성") for x in _합) if z is not None)
            _컷2 = [_값2[len(_값2) * k // 4] for k in (1, 2, 3)] if _값2 else [0, 0, 0]
            _이름2 = ["낮음(1분위)", "2분위", "3분위", "높음(4분위)", "모름"]

            def _칸2(x, c=_컷2):
                v = x.get("시장변동성")
                if v is None:
                    return "모름"
                return ("낮음(1분위)" if v <= c[0] else "2분위" if v <= c[1] else
                        "3분위" if v <= c[2] else "높음(4분위)")

            print(f"\n     (변동성 사분위 자리: {_컷2[0]:.2f} · {_컷2[1]:.2f} · {_컷2[2]:.2f})")
            _칸찍기("② 그날 시장 변동성", _칸2, _이름2)
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ③ 계절 · ④ 금리 방향
        try:
            _칸찍기("③ 계절", (lambda x: {"03": "봄", "04": "봄", "05": "봄", "06": "여름", "07": "여름",
                                       "08": "여름", "09": "가을", "10": "가을", "11": "가을"}.get(
                날[x["인"]][4:6], "겨울")), ["봄", "여름", "가을", "겨울"])

            def _칸4(x):
                v = _값P(x, "기준금리20")
                if v is None:
                    return "모름"
                return "오름" if v > 0.01 else ("내림" if v < -0.01 else "그대로")

            _칸찍기("④ 기준금리 20일 방향", _칸4, ["오름", "그대로", "내림", "모름"])
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③④ 터졌다: {_e}")
        print("\n     ⚠️ 국면으로 **거르면** 기회가 준다 — 여기서 좋은 칸이 보여도 「그 국면에만 산다」로 바로 못 간다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **DUP — 같은 종목을 얼마나 다시 사나 · 그 성적은** (2026-09-23) ══
    if _ONLY == "DUP" or "DUP" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── DUP ⭐⭐⭐ **같은 종목 반복 매수 — 사용자가 중복금지를 안 켜기로 했으니, 실태를 본다** ──")
        print("     Q-32 에서 떨어지는 종목을 열 번 반복해 사서 −38% 가 난 적이 있다. 지금 규칙에서도 그런가")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금U(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기록U = []
        _rU = 시뮬(_c(_지금U, **_열기D), 묶2=_묶D, 기록=_기록U)
        _날인U = {_d: _i for _i, _d in enumerate(날)}
        _종목별 = {}
        for _거래 in sorted(_기록U, key=lambda z: z[0]):
            _종목별.setdefault(_거래[1], []).append(_거래)
        print(f"\n     산 것 {len(_기록U):,}건 · 서로 다른 종목 {len(_종목별):,}개"
              f" · 한 종목 평균 {len(_기록U) / max(1, len(_종목별)):.2f}번")
        _여러번 = {c: v for c, v in _종목별.items() if len(v) >= 2}
        print(f"     두 번 이상 산 종목 {len(_여러번):,}개 ({len(_여러번) / max(1, len(_종목별)) * 100:.1f}%)"
              f" · 가장 많이 산 종목 {max((len(v) for v in _종목별.values()), default=0)}번")
        _첫, _다시 = [], []
        _간격 = []
        for c, v in _종목별.items():
            for k, _거래 in enumerate(v):
                (_첫 if k == 0 else _다시).append(_거래[4])
                if k:
                    _a, _b = _날인U.get(v[k - 1][0]), _날인U.get(_거래[0])
                    if _a is not None and _b is not None:
                        _간격.append(_b - _a)
        for 이, _v in (("처음 산 것", _첫), ("다시 산 것", _다시)):
            if not _v:
                continue
            _v2 = sorted(_v)
            print(f"     {이:<12}{len(_v2):>7}건 · 평균 {sum(_v2) / len(_v2):>6.1f}% · 가운데 {_v2[len(_v2) // 2]:>6.1f}%"
                  f" · 이긴 비율 {sum(1 for z in _v2 if z > 0) / len(_v2) * 100:>5.0f}%")
        if _간격:
            _g = sorted(_간격)
            print(f"     다시 사기까지 걸린 날 — 가운데 {_g[len(_g) // 2]}일 · 가장 짧은 {_g[0]}일"
                  f" · 20일 안에 다시 산 것 {sum(1 for z in _g if z <= 20) / len(_g) * 100:.0f}%")
        # 같은 종목을 한 해에 셋 이상 산 경우
        _나쁜 = []
        for c, v in _여러번.items():
            _해별 = {}
            for _거래 in v:
                _해별.setdefault(str(_거래[0])[:4], []).append(_거래[4])
            for _y, _벌 in _해별.items():
                if len(_벌) >= 3:
                    _나쁜.append((c, _y, len(_벌), sum(_벌) / len(_벌)))
        print(f"\n     한 해에 **셋 이상** 산 (종목, 해) 짝 {len(_나쁜)}개")
        for c, _y, _n, _m in sorted(_나쁜, key=lambda z: z[3])[:12]:
            print(f"        {c} · {_y}년 {_n}번 · 평균 {_m:+.1f}%")
        print("\n     ⇒ 「다시 산 것」이 「처음 산 것」보다 크게 나쁘지 않으면 중복금지를 안 켜는 게 맞다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **BAD — 악재 매도를 제대로 흔든다** (2026-09-23 · EXIT ② 후속) ══
    if _ONLY == "BAD" or "BAD" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── BAD ⭐⭐⭐ **보유 중 악재 공시 → 다음 날 시가 매도 — 106% · 낙폭 −6.7% 였다. 흔들어 본다** ──")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금B(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기B = 시뮬(_c(_지금B, **_열기D), 묶2=_묶D)
        _기돈낙B = _기B["끝"] / abs(_기B["낙"]) if _기B["낙"] else 0
        print(f"\n     바탕 — {_기B['끝']:,.0f}원 · 낙폭 {_기B['낙']:.1f}% · 산 것 {_기B['산']}")

        # ── ① 증분 걷기 ──
        try:
            print("\n     ① 증분 걷기 (뒤는 앞이 끝낸 돈으로)")
            _a0 = 시뮬(_c(_지금B, **_열기D), 시작년="2016", 끝년="2020", 묶2=_묶D)
            _a1 = 시뮬(_c(_지금B, **_열기D, 재평가="악재"), 시작년="2016", 끝년="2020", 묶2=_묶D)
            _b0 = 시뮬(_c(_지금B, **_열기D), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶D) if _a0 else None
            _b1 = 시뮬(_c(_지금B, **_열기D, 재평가="악재"), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶D) if _a1 else None
            if _a0 and _a1 and _b0 and _b1:
                _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
                _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
                print(f"        앞 2016~2020 — 바탕 {_a0['끝']:,.0f} → 악재매도 {_a1['끝']:,.0f} ({_앞:+.1f}%)")
                print(f"        뒤 2021~2026 — 바탕 {_b0['끝']:,.0f} → 악재매도 {_b1['끝']:,.0f} ({_뒤:+.1f}%)")
                print(f"        ⇒ " + ("✅ 앞뒤 다 늘었다" if (_앞 > 0.1 and _뒤 > 0.1) else "❌ 한 토막이 안 늘었다"))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② 해마다 ──
        try:
            print("\n     ② 해마다 (그 해 500만으로 다시 시작) — 한두 해가 끄는 건 아닌가")
            print(f"     {'해':<7}{'바탕':>14}{'악재매도':>14}{'차이':>9}{'바탕 낙폭':>11}{'악재 낙폭':>11}")
            _이긴해, _진해 = 0, 0
            for _y in range(2016, 2027):
                _r0 = 시뮬(_c(_지금B, **_열기D), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶D)
                _r1 = 시뮬(_c(_지금B, **_열기D, 재평가="악재"), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶D)
                if not (_r0 and _r1):
                    continue
                _p0 = (_r0["끝"] / 5000000 - 1) * 100
                _p1 = (_r1["끝"] / 5000000 - 1) * 100
                _이긴해 += 1 if _p1 > _p0 + 0.05 else 0
                _진해 += 1 if _p1 < _p0 - 0.05 else 0
                print(f"     {_y:<7}{_p0:>13.1f}%{_p1:>13.1f}%{_p1 - _p0:>8.1f}p{_r0['낙']:>10.1f}%{_r1['낙']:>10.1f}%")
            print(f"     ⇒ 악재매도가 나은 해 {_이긴해} · 못한 해 {_진해} · 같은 해 {11 - _이긴해 - _진해}")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ── ③ 말 묶음을 갈라서 (공시를 한 번만 읽고 묶음마다 거른다) ──
        try:
            print("\n     ③ **어떤 말이 끄는가** — 악재말을 묶음으로 갈라 각각만 켰을 때")
            import glob as _gB
            _원래표 = {k: dict(v) for k, v in _악재표.items()}
            _공시B = []          # (날짜8, code, 공시명)
            for _f in sorted(_gB.glob(os.path.join(O._DATA, "dart-daily", "*.json"))):
                _d8 = os.path.basename(_f)[:8]
                try:
                    _j = json.load(io.open(_f, encoding="utf-8-sig"))
                except ValueError:
                    continue
                for _칸 in ("챙길공시", "그밖의공시"):
                    for _x in (_j.get(_칸) or []):
                        _코B = str(_x.get("종목코드") or "")
                        _이 = str(_x.get("공시명") or "")
                        if _코B and _이:
                            _공시B.append((_d8, _코B, _이))
            print(f"        공시 {len(_공시B):,}건을 한 번 읽었다")
            _묶음들 = {
                "법·회계": ("횡령", "배임", "분식", "회계 의혹", "압수수색", "검찰", "고소", "고발",
                           "제재", "과징금", "소송", "불성실공시"),
                "실적": ("적자", "손실", "어닝 쇼크", "실적 부진", "영업손실", "당기순손실", "적자 전환",
                        "목표주가 하향", "투자의견 하향", "하향 조정"),
                "자본": ("감자", "유상증자"),
                "생사": ("상장폐지", "거래정지", "관리종목"),
                "영업": ("계약 해지", "수주 취소", "공급 중단", "리콜", "리스크"),
                "전부 (지금)": tuple(_NM._악재말),
            }
            print(f"     {'묶음':<12}{'말 수':>6}{'걸린 날':>9}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>10}")
            for _이, _말 in _묶음들.items():
                _새표 = {}
                for _d8, _코B, _제 in _공시B:
                    if any(_w in _제 for _w in _말):
                        _새표.setdefault(_d8, {})
                        _새표[_d8][_코B] = _새표[_d8].get(_코B, 0) + 1
                _악재표.clear()
                _악재표.update(_새표)
                _r = 시뮬(_c(_지금B, **_열기D, 재평가="악재"), 묶2=_묶D)
                if _r:
                    _돈낙 = _r["끝"] / abs(_r["낙"]) if _r["낙"] else 0
                    print(f"     {_이:<12}{len(_말):>6}{len(_새표):>9,}{_r['끝']:>16,.0f}"
                          f"{_r['끝'] / _기B['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}"
                          f"{_돈낙 / _기돈낙B * 100 if _기돈낙B else 0:>9.0f}%")
            _악재표.clear()
            _악재표.update(_원래표)      # ⚠️ 반드시 되돌린다 — 뒤 블록이 이 표를 쓴다
            print("        (악재표를 본디대로 되돌렸다)")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③ 터졌다: {_e}")

        # ── ④ 체결 오차 ──
        try:
            print("\n     ④ 체결 오차 ±1% 를 열 번 — 바탕과 견준다")
            for _이, _옵 in (("바탕", {}), ("악재 매도", {"재평가": "악재"})):
                _끝들 = []
                for _씨 in range(1, 11):
                    _r = 시뮬(_c(_지금B, **_열기D, **_옵), 오차=1.0, 씨=_씨, 묶2=_묶D)
                    if _r:
                        _끝들.append(_r["끝"])
                if _끝들:
                    print(f"     {_이:<12} 평균 {sum(_끝들) / len(_끝들):>15,.0f} · 가장 나쁜 {min(_끝들):>15,.0f}")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ④ 터졌다: {_e}")
        print("\n     ⚠️ 넣으면 **매일 아침 보유 종목 공시를 보고 파는 일**이 새로 생긴다 — 그 부담까지 같이 이야기한다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **TRACE — 한 종목을 문마다 끝까지 따라간다** (2026-09-23 · A4 후속) [TRACE] ══
    #    [한 종목 따라가기] = 시총을 찍기만 하고 **시뭄을 안 부른다** — 막개 ④ 가 코드로 확인하고 봐준다
    if _ONLY == "TRACE" or "TRACE" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── TRACE ⭐⭐⭐ **실전이 잡았는데 판이 안 잡은 종목 — 어느 문에서 갈라지나** ──")
        print("=" * 122)
        _볼코드 = [z.strip() for z in (os.environ.get("TRACE_CODES") or
                                      "002870,032850,051160,068790,100030,205100,348350,214150").split(",") if z.strip()]
        print(f"     따라갈 종목 {len(_볼코드)}개: {' '.join(_볼코드)}")
        _끝인 = max((x["인"] for x in 사건), default=0)
        print(f"     판의 마지막 인 {_끝인} = 매수일 {날[_끝인] if _끝인 < len(날) else '?'}"
              f" (신호기준일 {날[_끝인 - 1] if 0 < _끝인 < len(날) else '?'})")
        _인들T = [i for i in range(max(0, _끝인 - 11), _끝인 + 1)]
        _풀T = {}
        for x in 사건:
            if x["code"] in _볼코드 and x["인"] in _인들T:
                _풀T[(x["code"], x["인"])] = x
        print(f"     그 종목·그 날이 **풀(사건)에 있는 것** {len(_풀T)}건 / 바라는 것 {len(_볼코드) * len(_인들T)}건")
        print(f"\n     {'종목':<9}{'매수일':<11}{'풀':>4}{'시총억':>10}{'대금억':>8}{'잉여금':>8}{'부채':>8}"
              f"{'흑자':>5}{'문':>4}{'시장변동성':>10}{'자사주60':>9}{'낙폭20':>8}{'볼린저':>8}{'Ⓗ':>4}")
        for _code in _볼코드:
            for _인 in _인들T:
                x = _풀T.get((_code, _인))
                if x is None:
                    print(f"     {_code:<9}{날[_인]:<11}{'✗':>4}   — 풀에 없다 (문 앞에서 이미 빠졌거나 자료가 없다)")
                    continue
                try:
                    _문 = 문통과(x)
                except Exception:  # noqa: BLE001
                    _문 = "?"
                try:
                    _자 = _자사H(x) if R.변동성자사주_켬 else 0
                except Exception as _e:  # noqa: BLE001
                    _자 = f"err:{type(_e).__name__}"
                try:
                    _h = _H(x)          # [견줌] 실전과 같은 함수로 본다
                except Exception as _e:  # noqa: BLE001
                    _h = f"err:{type(_e).__name__}"
                print(f"     {_code:<9}{날[_인]:<11}{'○':>4}{(x.get('시총억') or 0):>10,.0f}{(x.get('대금억') or 0):>8.1f}"
                      f"{(x.get('잉여금') or 0):>8.1f}{(x.get('부채') or 0):>8.1f}{str(x.get('흑자')):>5}"
                      f"{str(_문):>4}{(x.get('시장변동성') if x.get('시장변동성') is not None else -9):>10.2f}"
                      f"{str(_자):>9}{(x.get('낙폭20') or 0):>8.1f}{(x.get('볼린저') or 0):>8.2f}{str(_h):>4}")
        print(f"\n     참고 — 시장변동성 문턱 {R.시장변동성문턱:g} · 자사주 창 {R.자사주창일}거래일"
              f" · 시총 문 {R.시총하한억:g}억↑ · 대금 문 {R.대금하한억:g}억↑ · 변동성자사주 켬 {R.변동성자사주_켬}")
        print("     ⇒ 「풀에 없다」면 사건을 만드는 단계에서 빠진 것이고, 「문 False」면 재무·대금·시총이다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **CAP — 시작 자본이 작아도 새 규칙이 쓸모 있나** (2026-09-23 · D-4 후속) ══
    if _ONLY == "CAP" or "CAP" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── CAP ⭐⭐⭐ **자본이 작으면 자리가 차서 새 후보가 못 들어온다 — 얼마부터 뜻이 있나** ──")
        print("     D-4: 그 해 500만으로 다시 시작하면 17해 중 14해가 옛 규칙과 **똑같았다**")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _옛키C, _지금키C = _키표["옛"], _키표["지금"]

        def _옛C(x):
            return (x["code"], x["인"]) in _옛키C        # [견줌] 덜어 둔 열쇠

        def _지금C(x):
            return (x["code"], x["인"]) in _지금키C      # [견줌] 덜어 둔 열쇠

        def _자리C(n):
            return (lambda 골, _n=n: _n)

        _돈들 = [5_000_000, 10_000_000, 20_000_000, 30_000_000, 50_000_000,
                 100_000_000, 200_000_000, 300_000_000]
        for _이름, _옵 in (("지금 설정 (비중 20% · 4자리)", {}),
                           ("B70 이 찾은 값 (비중 33% · 6자리)", {"비중": 0.33, "하루상한": _자리C(6)})):
            try:
                print(f"\n     ── {_이름}")
                print(f"     {'시작 자본':>14}{'옛 끝 자산':>18}{'옛 산 것':>9}{'지금 끝 자산':>18}{'지금 산 것':>11}"
                      f"{'지금/옛':>9}{'늘어난 매수':>12}")
                for _돈 in _돈들:
                    _a = 시뮬(_c(_옛C, **_열기D, **_옵), 시드=_돈, 묶2=_묶D)
                    _b = 시뮬(_c(_지금C, **_열기D, **_옵), 시드=_돈, 묶2=_묶D)
                    if not (_a and _b):
                        continue
                    print(f"     {_돈:>14,}{_a['끝']:>18,.0f}{_a['산']:>9}{_b['끝']:>18,.0f}{_b['산']:>11}"
                          f"{_b['끝'] / _a['끝'] * 100:>8.0f}%{_b['산'] - _a['산']:>12}")
            except Exception as _e:  # noqa: BLE001
                print(f"     ⚠️ {_이름} 터졌다: {_e}")

        # ── 해마다 (작은 자본으로 다시 시작) 새 규칙이 실제로 산 날 ──
        try:
            print(f"\n     ── 작은 자본(500만)으로 그 해만 돌릴 때 **새 규칙이 실제로 산 것**")
            print(f"     {'해':<7}{'옛 산 것':>9}{'지금 산 것':>11}{'차이':>7}{'옛 수익률':>11}{'지금 수익률':>13}")
            for _y in range(2016, 2027):
                _a = 시뮬(_c(_옛C, **_열기D), 시작년=str(_y), 끝년=str(_y), 시드=5_000_000, 묶2=_묶D)
                _b = 시뮬(_c(_지금C, **_열기D), 시작년=str(_y), 끝년=str(_y), 시드=5_000_000, 묶2=_묶D)
                if not (_a and _b):
                    continue
                print(f"     {_y:<7}{_a['산']:>9}{_b['산']:>11}{_b['산'] - _a['산']:>7}"
                      f"{(_a['끝'] / 5e6 - 1) * 100:>10.1f}%{(_b['끝'] / 5e6 - 1) * 100:>12.1f}%")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ 해마다 터졌다: {_e}")

        print("\n     ⇒ 자본이 작을 때 지금/옛 이 100% 에 붙어 있으면, 130% 는 **자본이 커진 뒤의 이야기**다")
        print("        그러면 실전에서는 **자리를 늘리거나 비중을 나누는 쪽**이 먼저다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SIZE — 비중·자리를 제대로 흔든다** (2026-09-23 · B70 RK ④ 후속) ══
    if _ONLY == "SIZE" or "SIZE" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SIZE ⭐⭐⭐ **비중 33% × 6자리가 142% · 낙폭 −8.2% 였다 — 의심하고 더 흔든다** ──")
        print("     돈이 늘면서 낙폭이 **줄었다**는 건 흔치 않다. 어디서 무너지는지, 한두 해가 끄는 건 아닌지 본다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금Z(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        def _자리Z(n):
            return (lambda 골, _n=n: _n)

        _기Z = 시뮬(_c(_지금Z, **_열기D), 묶2=_묶D)
        print(f"\n     바탕 (20% × 4자리) — {_기Z['끝']:,.0f}원 · 낙폭 {_기Z['낙']:.1f}% · 산 것 {_기Z['산']}")

        # ── ① 더 키우면 어디서 무너지나 ──
        try:
            print(f"\n     ① 비중 × 자리 — 더 키우면")
            print(f"     {'비중 × 자리':<18}{'만재':>7}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>10}")
            for _w in (0.20, 0.25, 0.33, 0.40, 0.50, 0.70, 1.00):
                for _자 in (3, 4, 5, 6, 8):
                    _r = 시뮬(_c(_지금Z, **_열기D, 비중=_w, 하루상한=_자리Z(_자)), 묶2=_묶D)
                    if not _r:
                        continue
                    _돈낙 = _r["끝"] / abs(_r["낙"]) if _r["낙"] else 0
                    _기돈낙 = _기Z["끝"] / abs(_기Z["낙"]) if _기Z["낙"] else 0
                    print(f"     {int(_w * 100)}% × {_자}자리{'':<7}{int(_w * _자 * 100):>6}%{_r['끝']:>16,.0f}"
                          f"{_r['끝'] / _기Z['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}"
                          f"{_돈낙 / _기돈낙 * 100 if _기돈낙 else 0:>9.0f}%")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② 해마다 · ③ 걷기 세 토막 · ④ 체결 오차 ──
        _볼것 = [("20% × 4자리 (지금)", 0.20, 4), ("25% × 6자리", 0.25, 6),
                 ("33% × 6자리", 0.33, 6), ("50% × 6자리", 0.50, 6)]
        try:
            print(f"\n     ② 해마다 (그 해 500만으로 다시 시작) — 한두 해가 끄는 건 아닌가")
            print(f"     {'해':<7}" + "".join(f"{이:>22}" for 이, _, _ in _볼것))
            for _y in range(2016, 2027):
                _줄 = f"     {_y:<7}"
                for _이, _w, _자 in _볼것:
                    _r = 시뮬(_c(_지금Z, **_열기D, 비중=_w, 하루상한=_자리Z(_자)),
                              시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶D)
                    _줄 += f"{((_r['끝'] / 5000000 - 1) * 100 if _r else 0):>21.1f}%"
                print(_줄)
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        try:
            print(f"\n     ③ 걷기 세 토막 (뒤는 앞이 끝낸 돈으로)")
            print(f"     {'변형':<22}{'2016~2020':>18}{'2021~2026':>18}{'배수(뒤)':>10}")
            for _이, _w, _자 in _볼것:
                _옵Z = dict(_열기D)
                _a = 시뮬(_c(_지금Z, **_옵Z, 비중=_w, 하루상한=_자리Z(_자)),
                          시작년="2016", 끝년="2020", 묶2=_묶D)
                _b = 시뮬(_c(_지금Z, **_옵Z, 비중=_w, 하루상한=_자리Z(_자)),
                          시작년="2021", 끝년="2026", 시드=_a["끝"], 묶2=_묶D) if _a else None
                if _a and _b:
                    print(f"     {_이:<22}{_a['끝']:>18,.0f}{_b['끝']:>18,.0f}{_b['끝'] / _a['끝']:>9.2f}배")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③ 터졌다: {_e}")

        try:
            print(f"\n     ④ 체결 오차 ±1% 를 열 번 — 집중하면 잡음에 약해지나")
            print(f"     {'변형':<22}{'평균':>16}{'가장 나쁜':>16}{'오차 없음의%':>14}")
            for _이, _w, _자 in _볼것:
                _기본 = 시뮬(_c(_지금Z, **_열기D, 비중=_w, 하루상한=_자리Z(_자)), 묶2=_묶D)
                _끝들 = []
                for _씨 in range(1, 11):
                    _r = 시뮬(_c(_지금Z, **_열기D, 비중=_w, 하루상한=_자리Z(_자)),
                              오차=1.0, 씨=_씨, 묶2=_묶D)
                    if _r:
                        _끝들.append(_r["끝"])
                if _끝들 and _기본:
                    print(f"     {_이:<22}{sum(_끝들) / len(_끝들):>16,.0f}{min(_끝들):>16,.0f}"
                          f"{min(_끝들) / _기본['끝'] * 100:>13.0f}%")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ④ 터졌다: {_e}")

        # ── ⑤ 동시에 몇 종목을 들고 있나 · ⑥ 한 방의 크기 ──
        try:
            print(f"\n     ⑤ 실제로 동시에 몇 종목을 들고 있나 (집중의 값)")
            _날인Z = {_d: _i for _i, _d in enumerate(날)}
            print(f"     {'변형':<22}{'가운데':>8}{'가장 많이':>10}{'하나만 든 날':>13}{'가장 나쁜 한 방':>15}")
            for _이, _w, _자 in _볼것:
                _기록Z = []
                시뮬(_c(_지금Z, **_열기D, 비중=_w, 하루상한=_자리Z(_자)), 묶2=_묶D, 기록=_기록Z)
                _든것 = {}
                _나쁜 = 0.0
                for _거래 in _기록Z:
                    _i0 = _날인Z.get(_거래[0])
                    _청 = _거래[5]
                    _나쁜 = min(_나쁜, _거래[4])
                    if _i0 is None or _청 is None:
                        continue
                    for _k in range(_i0, min(_청 + 1, len(날))):
                        _든것.setdefault(_k, set()).add(_거래[1])
                _수Z = sorted(len(v) for v in _든것.values())
                if _수Z:
                    print(f"     {_이:<22}{_수Z[len(_수Z) // 2]:>8}{_수Z[-1]:>10}"
                          f"{sum(1 for z in _수Z if z == 1) / len(_수Z) * 100:>12.0f}%{_나쁜:>14.1f}%")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ⑤ 터졌다: {_e}")

        print("\n     ⚠️ 비중은 시뮬 가정이다 — 화면에는 금액 배분을 안 쓴다. 바꾸려면 rule_def·rule-capital 을 같이 (월요일)")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **WEIGHT (F5) — 신호가 셀수록 더 싣는다** (2026-09-23) ══
    if _ONLY == "WEIGHT" or "WEIGHT" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── WEIGHT ⭐⭐⭐ **갈래 수 · 갈래 종류 · 갭 깊이로 비중을 달리하면** ──")
        print("     지금은 어느 후보든 자산의 20%. 자본 칸이 병목이라면 **같은 칸을 더 좋은 신호에** 줘야 한다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금W(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _갈래수W = {}
        for _이 in ["Ⓗ"] + list(R.업종규칙):
            for _k in _키표[_이]:
                _갈래수W[_k] = _갈래수W.get(_k, 0) + 1
        _업종만 = set()
        for _이 in R.업종규칙:
            _업종만 |= _키표[_이]
        _센것 = sum(1 for v in _갈래수W.values() if v >= 2)
        print(f"\n     갈래 둘 이상에 걸린 사건 {_센것:,}건 / 전체 {len(_갈래수W):,}건"
              f" ({_센것 / max(1, len(_갈래수W)) * 100:.1f}%)")

        _기W = 시뮬(_c(_지금W, **_열기D), 묶2=_묶D)
        _기돈낙W = _기W["끝"] / abs(_기W["낙"]) if _기W["낙"] else 0
        print(f"     바탕 — {_기W['끝']:,.0f}원 · 낙폭 {_기W['낙']:.1f}% · 산 것 {_기W['산']}")
        print(f"\n     {'비중 규칙':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>10}  판정")

        def _W줄(이름, 비중, 지금인가=False):
            _r = 시뮬(_c(_지금W, **_열기D, 비중=비중), 묶2=_묶D)
            if not _r:
                print(f"     {이름:<34} — 안 돌았다")
                return None
            _돈낙 = _r["끝"] / abs(_r["낙"]) if _r["낙"] else 0
            _ok = (_r["끝"] > _기W["끝"], _r["낙"] > 낙폭기준)
            _걷 = ""
            if all(_ok) and not 지금인가:
                _a0 = 시뮬(_c(_지금W, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _a1 = 시뮬(_c(_지금W, **_열기D, 비중=비중), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _b0 = 시뮬(_c(_지금W, **_열기D), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶D) if _a0 else None
                _b1 = 시뮬(_c(_지금W, **_열기D, 비중=비중), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶D) if _a1 else None
                if _a0 and _a1 and _b0 and _b1:
                    _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
                    _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
                    _걷 = f"  걷기 앞 {_앞:+.1f}% 뒤 {_뒤:+.1f}% " + ("✅" if (_앞 > 0.1 and _뒤 > 0.1) else "❌")
            print(f"     {이름:<34}{_r['끝']:>16,.0f}{_r['끝'] / _기W['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}{_돈낙 / _기돈낙W * 100 if _기돈낙W else 0:>9.0f}%  "
                  + ("지금" if 지금인가 else ("✅" if all(_ok) else "❌")) + _걷)
            return _r

        # ── ① 갈래 수별 ──
        try:
            _W줄("20% 고정 (지금)", 0.20, 지금인가=True)
            for _셀, _약 in ((0.30, 0.15), (0.25, 0.18), (0.33, 0.12), (0.25, 0.15), (0.40, 0.10)):
                _W줄(f"갈래 둘↑ {int(_셀 * 100)}% · 하나 {int(_약 * 100)}%",
                     (lambda x, a=_셀, b=_약: a if _갈래수W.get((x["code"], x["인"]), 1) >= 2 else b))
            _W줄("갈래 수 × 12%",
                 (lambda x: min(0.36, 0.12 * max(1, _갈래수W.get((x["code"], x["인"]), 1)))))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② 갈래 종류별 ──
        try:
            print(f"\n     ② 어느 갈래냐 — 업종 규칙은 제 문을 가진 규칙이다")
            for _업, _밑 in ((0.30, 0.15), (0.25, 0.18), (0.15, 0.25)):
                _W줄(f"업종 {int(_업 * 100)}% · Ⓗ {int(_밑 * 100)}%",
                     (lambda x, a=_업, b=_밑: a if (x["code"], x["인"]) in _업종만 else b))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ── ③ 갭 깊이별 ──
        try:
            print(f"\n     ③ 갭이 더 나쁜 것에 더 싣기 (그날 중앙갭과의 차)")
            _중W = {}
            for _인 in _묶D:
                _표9W = (_표본갭.get("실전표본") or {}).get(_인)
                _중W[_인] = st.median(_표9W) if _표9W else _전종목중앙갭.get(_인)

            def _상대W(x):
                _m = _중W.get(x["인"])
                _g = x.get("갭")
                return None if (_m is None or _g is None) else (_g - _m)

            for _컷, _깊, _얕 in ((-6.0, 0.30, 0.15), (-8.0, 0.33, 0.15), (-5.0, 0.25, 0.18)):
                _W줄(f"상대갭 {_컷:g}%p 밑 {int(_깊 * 100)}% · 나머지 {int(_얕 * 100)}%",
                     (lambda x, c=_컷, a=_깊, b=_얕: a if ((_상대W(x) or 0) <= c) else b))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③ 터졌다: {_e}")

        print("\n     ⚠️ 화면에는 금액 배분을 안 쓴다 — 이건 시뮬 가정이다. 넣는다면 rule_def 의 비중을 바꾸는 일이라 월요일에")
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **FUNNEL — 기회가 어느 단계에서 사라지나** (2026-09-23 · 실전 기록 후속) ══
    if _ONLY == "FUNNEL" or "FUNNEL" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── FUNNEL ⭐⭐⭐ **갈래에 걸린 것 → 상대갭 → 자리·돈 — 어디서 사라지나** ──")
        print("     실전 11일 동안 산 것이 10건이다. 문턱이 병목인지 돈이 병목인지 여기서 갈린다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금F(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        # ── ① 갈래에 걸린 것 (날·종목) ──
        _걸린 = [x for x in _합 if _지금F(x)]
        _해별 = {}
        for x in _걸린:
            _해별.setdefault(str(x.get("해") or 날[x["인"]][:4]), []).append(x)

        # ── ② 상대갭을 통과하는가 — 시뮬과 같은 값으로 센다 ──
        #    시뮬은 그날 후보들의 **중앙갭**과 견준다. 여기서는 판이 이미 갖고 있는 표를 쓴다
        _갭통과 = {}
        for _인, _벌 in _묶D.items():
            _고른 = [x for x in _벌 if _지금F(x)]
            if not _고른:
                continue
            # ⚠️ 시뭄과 같은 잣대를 써야 한다 — BASE_GAP 이 「표본만+실전표본」이면 그 표본의 가운데값
            _표9F = (_표본갭.get("실전표본") or {}).get(_인)
            _중 = st.median(_표9F) if _표9F else _전종목중앙갭.get(_인)
            if _중 is None:
                continue
            for x in _고른:
                _g = x.get("갭")
                if _g is None:
                    continue
                if (_g - _중) <= -3.5:
                    _갭통과.setdefault(_인, []).append(x)

        # ── ③ 실제로 산 것 ──
        _기록F = []
        _rF = 시뮬(_c(_지금F, **_열기D), 묶2=_묶D, 기록=_기록F)
        _산날 = {}
        for _거래 in _기록F:
            _산날.setdefault(_거래[0], []).append(_거래[1])

        print(f"\n     16해 합계")
        print(f"       ① 갈래에 걸린 것            {len(_걸린):,}건 · {len({x['인'] for x in _걸린}):,}일")
        print(f"       ② 상대갭 −3.5%p 통과        {sum(len(v) for v in _갭통과.values()):,}건 · {len(_갭통과):,}일"
              f"   ⇒ ①의 {sum(len(v) for v in _갭통과.values()) / max(1, len(_걸린)) * 100:.1f}%")
        print(f"       ③ 실제로 산 것              {len(_기록F):,}건 · {len(_산날):,}일"
              f"   ⇒ ②의 {len(_기록F) / max(1, sum(len(v) for v in _갭통과.values())) * 100:.1f}%")
        print(f"          (끝 자산 {_rF['끝']:,.0f}원 · 낙폭 {_rF['낙']:.1f}%)")
        print("\n       ⇒ ①→② 가 크게 줄면 **문턱이 병목** · ②→③ 이 크게 줄면 **돈·자리가 병목**")

        print(f"\n     해마다")
        print(f"     {'해':<7}{'① 걸림':>9}{'② 갭통과':>10}{'③ 산 것':>9}{'②/①':>8}{'③/②':>8}{'하루 평균 ②':>13}")
        for _y in sorted(_해별):
            _a = len(_해별[_y])
            _인들 = {x["인"] for x in _해별[_y]}
            _b = sum(len(v) for _인, v in _갭통과.items() if _인 in _인들)
            _날수 = len({_인 for _인 in _갭통과 if _인 in _인들})
            _c3 = sum(1 for _거래 in _기록F if str(_거래[0])[:4] == _y)
            print(f"     {_y:<7}{_a:>9,}{_b:>10,}{_c3:>9,}"
                  f"{_b / max(1, _a) * 100:>7.1f}%{_c3 / max(1, _b) * 100:>7.1f}%"
                  f"{_b / max(1, len(_인들)):>13.2f}")

        # ── ④ 자리가 모자라 못 산 날 ──
        try:
            _모자란날 = [(_인, len(v)) for _인, v in _갭통과.items() if len(v) > R.하루최대종목]
            print(f"\n     ④ 갭까지 통과한 것이 하루 {R.하루최대종목}자리를 넘은 날"
                  f" — {len(_모자란날)}일 / {len(_갭통과)}일 ({len(_모자란날) / max(1, len(_갭통과)) * 100:.1f}%)")
            if _모자란날:
                _벌 = sorted(_모자란날, key=lambda z: -z[1])[:8]
                print("        가장 붐빈 날: " + " · ".join(f"{날[_인]} {_n}개" for _인, _n in _벌))
            print(f"        ⇒ 실전 기록(11일)에서는 1일뿐이었다. 판에서도 같으면 **자리는 병목이 아니다**")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ④ 터졌다: {_e}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **OR1 (R1) — 재료 전수를 지금 실전 위에 OR 로 얹는다** (2026-09-23) ══
    if _ONLY == "OR1" or "OR1" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── OR1 ⭐⭐⭐ **재료 전부 × 아래20%/위20% 를 지금 실전 위에 하나씩 얹는다** ──")
        print("     옛 P절(69쌍)은 옛 Ⓗ 위에서 골랐다. 바탕이 바뀌었으니 다시 고른다")
        print("     「OR 후보는 OR 성적으로 고른다」 — 혼자 좋은 것만 추리면 대부분을 안 재고 지나간다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금O(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기O = 시뮬(_c(_지금O, **_열기D), 묶2=_묶D)
        _바탕날O = {인 for (_, 인) in _지금키}
        print(f"\n     바탕 — {_기O['끝']:,.0f}원 · 낙폭 {_기O['낙']:.1f}% · 산 것 {_기O['산']}"
              f" · 사는 날 {len(_바탕날O):,}일")

        # ── 재료 목록: 사건 칸 전부 + 특수 (Q-29 와 같은 길 · 손으로 안 고른다) ──
        _아님O = {"인", "code", "해", "_지수이름", "섹터", "매수", "재통과", "흑자",
                  "_20", "_40", "_겹친", "갭", "시총억", "원시", "주가", "대금"}
        _칸이름O = []
        for _k in sorted(사건[0].keys()):
            if _k in _아님O:
                continue
            _n = sum(1 for x in 사건[:5000] if isinstance(x.get(_k), (int, float)))
            if _n >= 1500:
                _칸이름O.append(_k)
        _특수O = ("자사주60", "코스피200선물20", "ETF괴리", "ETF괴리20", "기준금리20",
                  "무역수지비", "금값20", "ETF시총20", "무리낙폭", "무리와벌어짐", "지수갭")
        _재료O = ([(k, (lambda x, k=k: x.get(k))) for k in _칸이름O]
                  + [(k, (lambda x, k=k: _값P(x, k))) for k in _특수O])
        print(f"     재료 {len(_재료O)}개 (사건 칸 {len(_칸이름O)} + 특수 {len(_특수O)}) × 아래·위 두 쪽"
              f" = 후보 {len(_재료O) * 2}개")
        print(f"     {'재료 · 쪽':<26}{'문턱':>11}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'새 날':>7}  판정")

        _통과 = []
        for _라, _꺼 in _재료O:
            try:
                _v = sorted(z for z in (_꺼(x) for x in 사건) if z is not None)
            except Exception:  # noqa: BLE001
                continue
            if len(_v) < len(사건) * 0.3:
                continue
            if len(set(_v[::max(1, len(_v) // 5000)])) < 20:
                continue        # 이진·계단 재료 — 20% 컷이 뜻이 없다
            for _쪽 in ("아래", "위"):
                _컷 = _v[len(_v) // 5] if _쪽 == "아래" else _v[len(_v) * 4 // 5]

                def _새것(x, f=_꺼, c=_컷, d=_쪽):
                    z = f(x)
                    if z is None:
                        return False
                    return (z <= c) if d == "아래" else (z >= c)

                _새키O = {(x["code"], x["인"]) for x in _합 if _새것(x)}
                if not _새키O:
                    continue
                _도 = (lambda x, _k=_새키O: _지금O(x) or (x["code"], x["인"]) in _k)   # [견줌]
                _r = 시뮬(_c(_도, **_열기D), 묶2=_묶D)
                if not _r:
                    continue
                _새날O = len({인 for (_, 인) in _새키O} - _바탕날O)
                _ok = (_r["산"] > _기O["산"], _r["끝"] > _기O["끝"], _r["낙"] > 낙폭기준)
                _표 = "✅" if all(_ok) else "❌"
                if all(_ok):
                    _통과.append((_라, _쪽, _컷, _r, _새날O, _도))
                if all(_ok) or _r["끝"] > _기O["끝"] * 1.02:
                    print(f"     {_라 + ' ' + _쪽 + '20%':<26}{_컷:>11.2f}{_r['끝']:>16,.0f}"
                          f"{_r['끝'] / _기O['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}{_새날O:>7}  {_표}")

        print(f"\n     ⇒ 셋 다를 넘긴 후보 {len(_통과)}개 — 이제 **증분 걷기**로 다시 거른다")
        if _통과:
            print(f"     {'재료 · 쪽':<26}{'앞(2010~2020)':>16}{'뒤(2021~2026)':>16}  판정")
        _산것 = []
        for _라, _쪽, _컷, _r, _새날O, _도 in sorted(_통과, key=lambda z: -z[3]["끝"])[:25]:
            _a0 = 시뮬(_c(_지금O, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
            _a1 = 시뮬(_c(_도, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
            _b0 = 시뮬(_c(_지금O, **_열기D), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶D) if _a0 else None
            _b1 = 시뮬(_c(_도, **_열기D), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶D) if _a1 else None
            if not (_a0 and _a1 and _b0 and _b1):
                continue
            _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
            _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
            _산 = _앞 > 0.1 and _뒤 > 0.1
            if _산:
                _산것.append((_라, _쪽, _컷, _r["끝"], _새날O, _앞, _뒤))
            print(f"     {_라 + ' ' + _쪽 + '20%':<26}{_앞:>15.1f}%{_뒤:>15.1f}%  " + ("✅" if _산 else "❌"))

        print(f"\n     ⇒ **증분 걷기까지 넘긴 후보 {len(_산것)}개**")
        for _라, _쪽, _컷, _끝, _새날O, _앞, _뒤 in sorted(_산것, key=lambda z: -z[3]):
            print(f"        {_라} {_쪽}20% ≤/≥ {_컷:.2f} — {_끝:,.0f}원"
                  f" ({_끝 / _기O['끝'] * 100:.0f}%) · 새 날 {_새날O} · 걷기 앞 {_앞:+.1f}% 뒤 {_뒤:+.1f}%")
        print("     ⚠️ 여기까지는 ①②다. 넣으려면 문턱 흔들기(Q-31)와 같이 켜기(Q-34)가 남았다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **EXIT (G3) — 파는 쪽 재료를 새 바탕에서 다시** (2026-09-23) ══
    if _ONLY == "EXIT" or "EXIT" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── EXIT ⭐⭐⭐ **손절 · 악재 매도 · 회복 신호 매도 — 바탕이 바뀌었으니 다시** ──")
        print("     옛 답: 손절 없음이 낫다 · 회복 신호로 팔면 돈이 반 난다 (둘 다 **옛 Ⓗ**에서 잰 값)")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금X(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기X = 시뮬(_c(_지금X, **_열기D), 묶2=_묶D)
        print(f"\n     바탕 — {_기X['끝']:,.0f}원 · 낙폭 {_기X['낙']:.1f}% · 산 것 {_기X['산']}")

        def _X줄(이름, 옵, 지금인가=False):
            _r = 시뮬(_c(_지금X, **_열기D, **옵), 묶2=_묶D)
            if not _r:
                print(f"     {이름:<34} — 안 돌았다")
                return
            _좋 = (_r["끝"] > _기X["끝"], _r["낙"] > 낙폭기준)
            _돈낙 = _r["끝"] / abs(_r["낙"]) if _r["낙"] else 0
            _기돈낙 = _기X["끝"] / abs(_기X["낙"]) if _기X["낙"] else 0
            print(f"     {이름:<34}{_r['끝']:>16,.0f}{_r['끝'] / _기X['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}{_돈낙 / _기돈낙 * 100 if _기돈낙 else 0:>10.0f}%  "
                  + ("지금" if 지금인가 else ("✅" if all(_좋) else "❌")))

        _머리 = f"     {'변형':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'돈÷낙폭':>10}  판정"

        # ── ① 손절 ──
        try:
            print("\n     ① 손절 — 종가가 그 밑으로 닫힌 날 판다 (지금은 손절 없음)")
            print(_머리)
            _X줄("손절 없음 (지금)", {}, 지금인가=True)
            for _s in (-8, -12, -15, -20, -25, -30):
                _X줄(f"손절 {_s}%", {"손절": float(_s)})
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② 악재 공시가 뜨면 판다 ──
        try:
            print("\n     ② 보유 중 악재 공시 → 다음 날 **시가**에 판다 (장후 공시를 그날 종가에 팔면 미래를 본다)")
            print(_머리)
            _X줄("악재 매도", {"재평가": "악재"})
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ── ③ 회복 신호로 팔기 (옛 답: 돈이 반 난다) ──
        try:
            print("\n     ③ 회복 신호로 팔기 — 반은 목표(+15%/40일), 반은 상태")
            print(_머리)
            for _이, _상 in (("볼린저 0 위", "볼0"), ("20일선 위", "20일선")):
                _X줄(f"반 +15/40 · 반 {_이}",
                     {"나눔": ((0.5, 15, 40), (0.5, 40, 90, _상))})   # 비교용 변형
                _X줄(f"전부 {_이} (목표 없음)",
                     {"나눔": ((1.0, 999, 90, _상),)})
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③ 터졌다: {_e}")

        # ── ④ 같이 ──
        try:
            print("\n     ④ 같이 — 손절 + 악재")
            print(_머리)
            for _s in (-15, -20, -25):
                _X줄(f"손절 {_s}% + 악재 매도", {"손절": float(_s), "재평가": "악재"})
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ④ 터졌다: {_e}")

        print("\n     ⚠️ 파는 규칙은 실전 코드(rule_def.몫들)다 — 여기서 안 바꾼다. 월요일 보고")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **GAP — 상대갭이 병목이다 · 풀면 돈이 되나** (2026-09-23 · 실전 기록 E3·E8 이 시킨 판) ══
    if _ONLY == "GAP" or "GAP" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── GAP ⭐⭐⭐ **상대갭을 풀면 — 기회가 늘까, 떨어지는 걸 반복해서 살까** ──")
        print("     실전 11일 동안 −3.5%p 를 넘은 후보가 모두 10개(하루 0.9개)다. 자리가 아니라 **여기가 병목**이다")
        print("     Q-32 에서 느슨한 갭 + 중복 매수는 −38% 였다 — 그래서 **푸는 것과 막는 것을 같이** 잰다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금G(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기G = 시뮬(_c(_지금G, **_열기D), 묶2=_묶D)
        print(f"\n     바탕 — {_기G['끝']:,.0f}원 · 낙폭 {_기G['낙']:.1f}% · 산 것 {_기G['산']}")

        def _G줄(이름, 옵, 지금인가=False):
            _r = 시뮬(_c(_지금G, **_열기D, **옵), 묶2=_묶D)
            if not _r:
                print(f"     {이름:<34} — 안 돌았다")
                return
            _ok = (_r["산"] >= _기G["산"], _r["끝"] > _기G["끝"], _r["낙"] > 낙폭기준)
            _걷 = ""
            if all(_ok) and not 지금인가:
                _a0 = 시뮬(_c(_지금G, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _a1 = 시뮬(_c(_지금G, **_열기D, **옵), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _b0 = 시뮬(_c(_지금G, **_열기D), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶D) if _a0 else None
                _b1 = 시뮬(_c(_지금G, **_열기D, **옵), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶D) if _a1 else None
                if _a0 and _a1 and _b0 and _b1:
                    _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
                    _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
                    _걷 = f"  걷기 앞 {_앞:+.1f}% 뒤 {_뒤:+.1f}% " + ("✅" if (_앞 > 0.1 and _뒤 > 0.1) else "❌")
            print(f"     {이름:<34}{_r['끝']:>16,.0f}{_r['끝'] / _기G['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}  "
                  + ("지금" if 지금인가 else ("✅" if all(_ok) else "❌")) + _걷)

        # ── ① 갭무름 — 큰 회사만 무르게 ──
        try:
            print(f"\n     ① 갭무름 (큰 회사는 덜 빠져도 산다) — {'변형':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            _G줄("지금 (무름 없음)", {}, 지금인가=True)
            for _이, _무 in [("2,000억↑ 만 0.7배", [(2000, 0.7)]),
                             ("2,000억↑ 만 0.5배", [(2000, 0.5)]),
                             ("1조↑ 만 0.5배", [(10000, 0.5)]),
                             ("1조↑ 만 0.3배", [(10000, 0.3)]),
                             ("2,000억 0.7 · 1조 0.4", [(2000, 0.7), (10000, 0.4)])]:
                _G줄(_이, {"갭무름": _무})
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② 상대갭 × 중복금지 ──
        try:
            print(f"\n     ② 상대갭을 풀되 같은 종목 반복 매수를 막으면 (중복금지는 **진단용**이다)")
            print(f"     {'변형':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            for _갭 in (-1.0, -2.0, -2.5, -3.0, -3.5):
                for _막 in (False, True):
                    _G줄(f"상대갭 {_갭:+.1f}%p · 중복{'금지' if _막 else '허용'}",
                         {"상대갭": _갭, "중복금지": _막},
                         지금인가=(abs(_갭 + 3.5) < 1e-9 and not _막))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ── ③ 갭무름 × 중복금지 ──
        try:
            print(f"\n     ③ 갭무름 + 중복금지 (둘 다)")
            print(f"     {'변형':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            for _이, _무 in [("2,000억↑ 0.5배", [(2000, 0.5)]),
                             ("2,000억 0.7 · 1조 0.4", [(2000, 0.7), (10000, 0.4)])]:
                _G줄(f"{_이} · 중복금지", {"갭무름": _무, "중복금지": True})
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③ 터졌다: {_e}")

        print("\n     ⚠️ 중복금지가 필요해야만 서는 변형은 **넣을 수 없다** — 사용자가 중복금지를 안 켜기로 했다")
        print("        (그 경우의 뜻: 「푸는 것 자체가 위험하다」)")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **A4 — 판이 고른 것을 날짜별로 찍는다 (실전과 대조하려고)** (2026-09-23) ══
    if _ONLY == "A4" or "A4" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── A4 ⭐⭐⭐ **판이 고른 종목 — 마지막 12거래일** (실전 forward-log 와 대조한다) ──")
        print("     같은 날 같은 규칙이면 같은 종목이 나와야 한다. 9/22 에 실전에만 남아 있던 줄을 이렇게 잡는다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _갈래A = {"Ⓗ": _키표["Ⓗ"]}
        for _이 in R.업종규칙:
            _갈래A[_이] = _키표[_이]
        _날짜별 = {}
        for _이, _키 in _갈래A.items():
            for _code, _인 in _키:
                _날짜별.setdefault(_인, {}).setdefault(_code, []).append(_이)
        _마지막 = sorted(_날짜별)[-12:]
        print(f"\n     판의 마지막 날 = {날[max(_날짜별)]} · 아래는 마지막 12거래일")
        print("     ⚠️ 이건 **상대갭 거르기 전** 목록이다 (실전의 「후보」와 같은 자리)")
        for _인 in _마지막:
            _것 = _날짜별[_인]
            print(f"\n     [{날[_인]}] {len(_것)}종목")
            print("     PICKLINE " + 날[_인] + " " + ",".join(sorted(_것)))
            for _code in sorted(_것):
                _x = next((z for z in (_묶D.get(_인) or []) if z["code"] == _code), None)
                _시 = f"{_x['시총억']:,.0f}억" if _x else "?"
                print(f"        {_code}  {_시:>12}  {'+'.join(_것[_code])}")
        print("\n     ⇒ `python scripts/diff_pick.py <이 파일>` 로 실전 기록과 대조한다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SIG — B2 섹시그마를 「그날까지」로 다시 만든다** (2026-09-23) ══
    if _ONLY == "SIG" or "SIG" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SIG ⭐⭐⭐ **섹시그마 다시 — 16년 전체 통계(미래 봄) → 그날까지 통계** ──")
        print("     셋째 후보(대형 섹시그마 위20%)는 이 이유 하나로 뺐다. 다시 만들면 서나?")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()

        # ── 그날까지의 섹터 통계로 섹시그마를 다시 낸다 (늘어나는 창 · 최소 200건) ──
        _차 = sorted(_합, key=lambda z: z["인"])
        _누적 = {}          # 섹터 -> [건수, 합, 제곱합]
        _새값 = {}
        _못냄 = 0
        for x in _차:
            _섹 = x.get("섹터")
            _낙 = x.get("낙폭20")
            if _섹 is None or _낙 is None:
                continue
            _n, _s1, _s2 = _누적.get(_섹, (0, 0.0, 0.0))
            if _n >= 200:
                _m = _s1 / _n
                _sd = ((_s2 / _n) - _m * _m) ** 0.5 or 1e-9
                _새값[(x["code"], x["인"])] = (_낙 - _m) / _sd
            else:
                _못냄 += 1
            _누적[_섹] = (_n + 1, _s1 + _낙, _s2 + _낙 * _낙)
        print(f"\n     그날까지 섹시그마를 낸 사건 {len(_새값):,}건 · 표본이 모자라 못 낸 것 {_못냄:,}건")

        # ── 대형 칸(문은 그때 것 그대로) 사건을 불러 새 재료로 문턱을 낸다 ──
        _큰길 = os.path.join(O._DATA, "_labs", "c_events_대형섹시그마.jsonl")
        if not os.path.exists(_큰길):
            print("     ⚠️ c_events_대형섹시그마.jsonl 이 없다 — DUMPC 를 먼저 돌려야 한다")
            print("=" * 122)
            return 0
        _큰 = [json.loads(z) for z in io.open(_큰길, encoding="utf-8") if z.strip()]
        _큰키 = {(x["code"], x["인"]) for x in _큰}
        _쓸값 = sorted(v for k, v in _새값.items() if k in _큰키)
        print(f"     대형 칸 사건 {len(_큰):,}건 중 새 섹시그마를 낸 것 {len(_쓸값):,}건")
        if len(_쓸값) < 100:
            print("     ⚠️ 표본이 모자라 판정하지 않는다")
            print("=" * 122)
            return 0
        _지금키 = _키표["지금"]

        def _지금S(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기S = 시뮬(_c(_지금S, **_열기D), 묶2=_묶D)
        _바탕날S = {인 for (_, 인) in _지금키}
        print(f"\n     바탕 — {_기S['끝']:,.0f}원 · 낙폭 {_기S['낙']:.1f}% · 산 것 {_기S['산']}")
        print(f"\n     {'자리':<10}{'섹시그마 ≤':>12}{'걸리는 것':>10}{'새 날':>7}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        for _q in (0.05, 0.10, 0.20, 0.30):
            _컷 = _쓸값[int(len(_쓸값) * _q)]
            _새키 = {k for k, v in _새값.items() if k in _큰키 and v <= _컷}
            if not _새키:
                continue
            _도 = (lambda x, _k=_새키: _지금S(x) or (x["code"], x["인"]) in _k)   # [견줌]
            _r = 시뮬(_c(_도, **_열기D), 묶2=_묶D)
            if not _r:
                continue
            _ok = (_r["산"] > _기S["산"], _r["끝"] > _기S["끝"], _r["낙"] > 낙폭기준)
            _새날 = len({인 for (_, 인) in _새키} - _바탕날S)
            _걷 = ""
            if all(_ok):
                _a0 = 시뮬(_c(_지금S, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _a1 = 시뮬(_c(_도, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _b0 = 시뮬(_c(_지금S, **_열기D), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶D) if _a0 else None
                _b1 = 시뮬(_c(_도, **_열기D), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶D) if _a1 else None
                if _a0 and _a1 and _b0 and _b1:
                    _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
                    _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
                    _걷 = f"  걷기 앞 {_앞:+.1f}% 뒤 {_뒤:+.1f}% " + ("✅" if (_앞 > 0.1 and _뒤 > 0.1) else "❌")
            print(f"     위 {int(_q * 100):<7}{_컷:>11.2f}σ{len(_새키):>10,}{_새날:>7}{_r['끝']:>16,.0f}"
                  f"{_r['끝'] / _기S['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
                  + ("✅" if all(_ok) else "❌") + _걷)
        print("\n     ⚠️ 서더라도 바로 안 넣는다 — 문턱 흔들기까지 한 뒤 월요일 보고")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **SELL — B5 파는 규칙 · 규모별 진단** (2026-09-23) ══
    if _ONLY == "SELL" or "SELL" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── SELL ⭐⭐⭐ **파는 규칙을 바꾸면 · 띠마다 얼마나 오르나** ──")
        print("     지금: 반 +15%/40일 · 반 +40%/90일 · 손절 없음")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금E(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기E = 시뮬(_c(_지금E, **_열기D), 묶2=_묶D)
        print(f"\n     바탕 — {_기E['끝']:,.0f}원 · 낙폭 {_기E['낙']:.1f}% · 산 것 {_기E['산']}")

        # ── ① 파는 규칙 바꾸기 (나눔) ──
        try:
            _몫후보 = [
                # ⚠️ 9/30 전수조사 #18: 「지금」이 50:50 으로 **손으로** 적혀 있었다 — 실전은 40:60 (R.몫들). 규칙 파일에서 읽는다
                ("지금 (" + " · ".join(f"{a * 100:.0f}% +{b:g}/{c}" for a, b, c in R.몫들) + ")", R.몫들),
                ("반 10/30 · 반 30/60", ((0.5, 10, 30), (0.5, 30, 60))),
                ("반 20/40 · 반 60/90", ((0.5, 20, 40), (0.5, 60, 90))),
                ("반 15/60 · 반 40/120", ((0.5, 15, 60), (0.5, 40, 120))),   # 비교용 변형
                ("전부 25/60", ((1.0, 25, 60),)),
                ("전부 15/40", ((1.0, 15, 40),)),
                ("전부 40/90", ((1.0, 40, 90),)),
                ("셋 (15/40 · 40/90 · 80/180)", ((0.34, 15, 40), (0.33, 40, 90), (0.33, 80, 180))),
            ]
            print(f"\n     ① 파는 규칙 — {'변형':<28}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            for _이, _몫 in _몫후보:
                _r = 시뮬(_c(_지금E, **_열기D, 나눔=_몫), 묶2=_묶D)
                if not _r:
                    continue
                _지금인가 = _이.startswith("지금")
                _ok = (_r["끝"] > _기E["끝"], _r["낙"] > 낙폭기준)
                print(f"     {'':>17}{_이:<28}{_r['끝']:>16,.0f}{_r['끝'] / _기E['끝'] * 100:>8.0f}%"
                      f"{_r['낙']:>7.1f}%{_r['산']:>7}  "
                      + ("지금" if _지금인가 else ("✅" if all(_ok) else "❌")))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② 규모별 진단 — 「대형은 +15%가 멀다」가 맞나 ──
        try:
            _맵E = {}
            for x in _합:
                _맵E[(x["code"], x["인"])] = x
            _날인E = {_d: _i for _i, _d in enumerate(날)}
            _기록E = []
            시뮬(_c(_지금E, **_열기D), 묶2=_묶D, 기록=_기록E)
            _띠들 = [(0, 800, "300~800억"), (800, 2000, "800~2,000억"),
                     (2000, 10000, "2,000억~1조"), (10000, 10 ** 9, "1조↑")]
            print(f"\n     ② 띠마다 산 뒤 — 산 것 {len(_기록E):,}건")
            print(f"     {'띠':<16}{'건수':>7}{'D+40 평균':>11}{'D+90 평균':>11}"
                  f"{'+15% 닿은':>11}{'+40% 닿은':>11}{'−20% 간 것':>12}")
            for _lo, _hi, _이 in _띠들:
                _v40, _v90, _닿15, _닿40, _깊20, _n = [], [], 0, 0, 0, 0
                for _거래 in _기록E:
                    _시 = _거래[2]
                    if not (_lo <= (_시 or 0) < _hi):
                        continue
                    _x = _맵E.get((_거래[1], _날인E.get(_거래[0])))
                    if _x is None:
                        continue
                    _n += 1
                    _길 = [앞수익(_x, n) for n in (5, 10, 20, 40, 60, 90)]
                    _길 = [z for z in _길 if z is not None]
                    if not _길:
                        continue
                    _a = 앞수익(_x, 40)
                    _b = 앞수익(_x, 90)
                    if _a is not None:
                        _v40.append(_a)
                    if _b is not None:
                        _v90.append(_b)
                    if max(_길) >= 15:
                        _닿15 += 1
                    if max(_길) >= 40:
                        _닿40 += 1
                    if min(_길) <= -20:
                        _깊20 += 1
                if not _n:
                    continue
                print(f"     {_이:<16}{_n:>7}"
                      f"{(sum(_v40) / len(_v40) if _v40 else 0):>10.1f}%"
                      f"{(sum(_v90) / len(_v90) if _v90 else 0):>10.1f}%"
                      f"{_닿15 / _n * 100:>10.0f}%{_닿40 / _n * 100:>10.0f}%{_깊20 / _n * 100:>11.0f}%")
            print("     ⚠️ 「닿은」은 D+5·10·20·40·60·90 여섯 점만 본 값이다 (장중 고가가 아니다)")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ **F 절 준비 — 업종 규칙의 문만 떼어 낸다** (2026-09-23 · F1·F2) ══
    #    ⚠️ 진단용이다. 곡선의 꼭대기로 문턱을 옮기지 않는다
    def _F문통과_크기없이(x, 규, 지금문):
        """그 업종 규칙의 **문**(띠·재무·대금)만 본다 — 재료 문턱은 빼고"""
        띠 = 규.get("띠")
        if 띠 is not None:
            시 = x.get("시총억")
            if 시 is None or not (띠[0] <= 시 < 띠[1]):
                return False
        재무 = 규.get("재무")
        if 재무 is None:
            return bool(지금문)
        잉, 부, 흑 = x.get("잉여금"), x.get("부채"), x.get("흑자")
        if 잉 is None or 부 is None or 잉 < 재무[0] or 부 > 재무[1] or 흑 != 1.0:
            return False
        대 = x.get("대금억")
        return 대 is not None and 대 >= (규.get("대금하한억") or 0)

    # ══ ⭐⭐⭐ **FC — F1 문턱 곡선 · F2 창 길이** (2026-09-23 · 진단) ══
    if _ONLY == "FC" or "FC" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── FC ⭐⭐⭐ **문턱을 연속으로 옮기면 — 칼날인가 언덕인가** (진단용 · 옮기지 않는다) ──")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _사건맵F = {}
        for x in _합:
            _사건맵F[(x["code"], x["인"])] = x
        _지금문맵 = {}
        for x in _합:
            _지금문맵[(x["code"], x["인"])] = (재무통과(x) and 대금통과(x)
                                            and (x.get("시총억") or 0) >= R.시총하한억)
        _업이름맵 = {}
        for x in _합:
            _업이름맵[(x["code"], x["인"])] = R.업종이름(_산업.get(x["code"]))
        _밑키 = _키표["Ⓗ"]
        _바탕날F = {인 for (_, 인) in _키표["지금"]}

        def _FC재기(이름, 뺀규칙, 새키):
            """뺀규칙만 빼고 나머지 + 새키 로 돌린다"""
            _키 = set(_밑키)
            for 이 in R.업종규칙:
                if 이 != 뺀규칙:
                    _키 |= _키표[이]
            _키 |= 새키
            _r = 시뮬(_c((lambda x, _k=_키: (x["code"], x["인"]) in _k), **_열기D), 묶2=_묶D)
            return _r

        for _이 in list(R.업종규칙):
            try:
                _규 = R.업종규칙[_이]
                _재료 = _규["재료"][0][0]        # 예: 낙폭60 · 낙120
                _쓸 = "낙폭60" if _재료 == "낙폭60" else _재료
                _지금문턱 = _규["재료"][0][1]
                # 그 업종 · 그 규칙의 문을 지난 사건만
                _칸 = [x for x in _합
                       if _업이름맵[(x["code"], x["인"])] == _이
                       and _F문통과_크기없이(x, _규, _지금문맵[(x["code"], x["인"])])
                       and x.get(_쓸 if _쓸 in x else _재료) is not None]
                _값 = sorted((x.get(_쓸) if _쓸 in x else x.get(_재료)) for x in _칸)
                if not _값:
                    print(f"\n     {_이} — 문 지난 사건이 없다")
                    continue
                print(f"\n     ── {_이} · {_재료} — 문 지난 사건 {len(_칸):,}건 · 지금 문턱 {_지금문턱:.2f}%")
                print(f"     {'분위':<8}{'문턱':>9}{'걸리는 것':>10}{'새 날':>7}{'끝 자산':>16}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}")
                _기준 = None
                for _q in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
                    _문 = _값[min(int(len(_값) * _q), len(_값) - 1)]
                    _새키 = {(x["code"], x["인"]) for x in _칸
                             if ((x.get(_쓸) if _쓸 in x else x.get(_재료)) or 0) <= _문}
                    _r = _FC재기(_이, _이, _새키)
                    if not _r:
                        continue
                    if _기준 is None:
                        _기준 = _r["끝"]
                    _새날 = len({인 for (_, 인) in _새키} - _바탕날F)
                    _표 = "  ← 지금 자리" if abs(_문 - _지금문턱) < 0.5 else ""
                    print(f"     {int(_q * 100):<8}{_문:>8.2f}%{len(_새키):>10,}{_새날:>7}"
                          f"{_r['끝']:>16,.0f}{_r['끝'] / _기준 * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}{_표}")
            except Exception as _e:  # noqa: BLE001
                print(f"     ⚠️ {_이} 곡선 터졌다: {_e}")

        # ── F2 창 길이 — 같은 분위에서 창만 바꾼다 ──
        try:
            print("\n     ── F2 창 길이 — 같은 분위(20%)에서 **창만** 바꾼다 (창 길이도 내가 고른 값이다)")
            for _이 in list(R.업종규칙):
                _규 = R.업종규칙[_이]
                _칸 = [x for x in _합
                       if _업이름맵[(x["code"], x["인"])] == _이
                       and _F문통과_크기없이(x, _규, _지금문맵[(x["code"], x["인"])])]
                if not _칸:
                    continue
                print(f"\n     {_이} (지금 {_규['재료'][0][0]} ≤ {_규['재료'][0][1]:.2f}%) · 문 지난 사건 {len(_칸):,}건")
                print(f"     {'창':<10}{'문턱(20분위)':>14}{'걸리는 것':>10}{'끝 자산':>16}{'낙폭':>8}{'산 것':>7}")
                for _창 in ("낙20", "낙40", "낙60", "낙120", "낙250"):
                    _값 = sorted(x[_창] for x in _칸 if x.get(_창) is not None)
                    if not _값:
                        continue
                    _문 = _값[int(len(_값) * 0.20)]
                    _새키 = {(x["code"], x["인"]) for x in _칸 if (x.get(_창) or 0) <= _문}
                    _r = _FC재기(_이, _이, _새키)
                    if not _r:
                        continue
                    print(f"     {_창:<10}{_문:>13.2f}%{len(_새키):>10,}{_r['끝']:>16,.0f}{_r['낙']:>7.1f}%{_r['산']:>7}")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ F2 터졌다: {_e}")
        print("\n     ⚠️ 진단이다 — 꼭대기가 나와도 문턱을 옮기지 않는다. 옮길 이유가 보이면 월요일 보고")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **FP — F3 산 뒤 경로 · F4 갈래 겹침** (2026-09-23) ══
    if _ONLY == "FP" or "FP" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── FP ⭐⭐⭐ **산 뒤 어떻게 가나(D+1…D+120 · MAE/MFE) · 갈래는 어디서 겹치나** ──")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금D(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        # ── F3 산 뒤 경로 ──
        try:
            _맵FP = {}
            for x in _합:
                _맵FP[(x["code"], x["인"])] = x
            _날인FP = {_d: _i for _i, _d in enumerate(날)}
            _기록FP = []
            _rFP = 시뮬(_c(_지금D, **_열기D), 묶2=_묶D, 기록=_기록FP)
            print(f"\n     F3 — 지금 실전이 산 {len(_기록FP):,}건의 뒤를 따라간다 ({_rFP['끝']:,.0f}원)")
            _날들FP = (1, 2, 3, 5, 10, 20, 30, 40, 60, 90, 120)
            _경로 = {n: [] for n in _날들FP}
            _MAE, _MFE = [], []
            for _거래 in _기록FP:
                _x = _맵FP.get((_거래[1], _날인FP.get(_거래[0])))
                if _x is None:
                    continue
                _길FP = []
                for n in _날들FP:
                    v = 앞수익(_x, n)
                    if v is not None:
                        _경로[n].append(v)
                        _길FP.append(v)
                if _길FP:
                    _MAE.append(min(_길FP))
                    _MFE.append(max(_길FP))
            print(f"     {'D+':<6}{'평균':>9}{'가운데':>9}{'이긴 비율':>11}{'표본':>8}")
            for n in _날들FP:
                v = sorted(_경로[n])
                if not v:
                    continue
                print(f"     {n:<6}{sum(v) / len(v):>8.1f}%{v[len(v) // 2]:>8.1f}%"
                      f"{sum(1 for z in v if z > 0) / len(v) * 100:>10.0f}%{len(v):>8,}")
            if _MAE:
                _a = sorted(_MAE)
                _b = sorted(_MFE)
                print(f"\n     가장 깊은 눌림(MAE) — 가운데 {_a[len(_a) // 2]:.1f}%"
                      f" · 넷 중 하나 {_a[len(_a) // 4]:.1f}% · 스물 중 하나 {_a[len(_a) // 20]:.1f}%")
                print(f"     가장 높이(MFE)     — 가운데 {_b[len(_b) // 2]:.1f}%"
                      f" · 위 넷 중 하나 {_b[len(_b) * 3 // 4]:.1f}% · 위 스물 중 하나 {_b[len(_b) * 19 // 20]:.1f}%")
                print(f"     ⇒ 목표 +15%/40일 · +40%/90일 이 이 분포의 어디인지 본다. **손절 없음**이 맞나도 여기서")
                for _컷 in (-10, -15, -20, -25, -30, -40):
                    print(f"        {_컷}% 밑으로 한 번이라도 간 것 {sum(1 for z in _MAE if z <= _컷) / len(_MAE) * 100:>5.1f}%")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ F3 터졌다: {_e}")

        # ── F4 갈래 겹침 ──
        try:
            _갈래키 = {"Ⓗ": _키표["Ⓗ"]}
            for _이 in R.업종규칙:
                _갈래키[_이] = _키표[_이]
            _이름들 = list(_갈래키)
            print(f"\n     F4 갈래 겹침 — 날 기준 (같은 날 둘 다 뜨나)")
            _날집 = {이: {인 for (_, 인) in _갈래키[이]} for 이 in _이름들}
            print(f"     {'갈래':<18}{'뜨는 날':>9}{'혼자 뜨는 날':>13}" + "".join(f"{이[:8]:>10}" for 이 in _이름들))
            for _a in _이름들:
                _혼자 = len(_날집[_a] - set().union(*[_날집[_b] for _b in _이름들 if _b != _a]))
                print(f"     {_a:<18}{len(_날집[_a]):>9,}{_혼자:>13,}"
                      + "".join(f"{len(_날집[_a] & _날집[_b]):>10,}" for _b in _이름들))
            print(f"\n     종목·날 기준 (같은 종목을 같은 날 둘이 집나)")
            for _i, _a in enumerate(_이름들):
                for _b in _이름들[_i + 1:]:
                    _겹 = len(_갈래키[_a] & _갈래키[_b])
                    if _겹:
                        print(f"        {_a} ∩ {_b} — {_겹:,}건")
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ F4 터졌다: {_e}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **RK — 손잡이 넷을 새 바탕 위에서 다시** (2026-09-23 · R2·B4·R3/R4·B3) ══
    if _ONLY == "RK" or "RK" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── RK ⭐⭐⭐ **후보수 · 상대갭 · 빠지는 장 문턱 · 비중×자리 — 지금 실전 바탕 위에서** ──")
        print("     넷 다 시뮬 인자다. 옛 판은 **옛 Ⓗ** 위에서 골랐다 — 바탕이 바뀌었으니 다시 잰다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금D(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기RK = 시뮬(_c(_지금D, **_열기D), 묶2=_묶D)
        print(f"\n     바탕 — {_기RK['끝']:,.0f}원 · 낙폭 {_기RK['낙']:.1f}% · 산 것 {_기RK['산']}")

        def _RK줄(이름, 옵, 지금인가=False):
            """한 변형을 찍는다. 셋 다 넘으면 증분 걷기까지."""
            _r = 시뮬(_c(_지금D, **_열기D, **옵), 묶2=_묶D)
            if not _r:
                print(f"     {이름:<22} — 안 돌았다")
                return None
            _ok = (_r["산"] >= _기RK["산"], _r["끝"] > _기RK["끝"], _r["낙"] > 낙폭기준)
            _걷 = ""
            if all(_ok) and not 지금인가:
                _a0 = 시뮬(_c(_지금D, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _a1 = 시뮬(_c(_지금D, **_열기D, **옵), 시작년="2010", 끝년="2020", 묶2=_묶D)
                _b0 = 시뮬(_c(_지금D, **_열기D), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_묶D) if _a0 else None
                _b1 = 시뮬(_c(_지금D, **_열기D, **옵), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_묶D) if _a1 else None
                if _a0 and _a1 and _b0 and _b1:
                    _앞 = (_a1["끝"] / _a0["끝"] - 1) * 100
                    _뒤 = (_b1["끝"] / _b0["끝"] - 1) * 100
                    _걷 = f"  걷기 앞 {_앞:+.1f}% 뒤 {_뒤:+.1f}% " + ("✅" if (_앞 > 0.1 and _뒤 > 0.1) else "❌")
            print(f"     {이름:<22}{_r['끝']:>16,.0f}{_r['끝'] / _기RK['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>8.1f}%{_r['산']:>7}  "
                  + ("지금" if 지금인가 else ("✅" if all(_ok) else "❌")) + _걷)
            return _r

        def _상한만들기(문턱, 많이, 평소):
            def _f(골, _문=문턱, _많=많이, _평=평소):
                _v = next((z.get("시장낙폭") for z in 골 if z.get("시장낙폭") is not None), None)
                if _v is None:
                    return _평
                return _많 if _v <= _문 else _평
            return _f

        # ── ① R2 후보수 꼭짓점 (옛 판은 옛 Ⓗ 로 골랐다) ──
        try:
            print(f"\n     ① R2 후보수 — 하루에 몇 개까지 줄 세우나 (지금 {_밑후보수}개)")
            print(f"     {'변형':<22}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            for _n in (20, 30, 60, 80, 120, 999):
                _RK줄(f"후보수 {_n}", {"후보수": _n}, 지금인가=(_n == _밑후보수))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ① 터졌다: {_e}")

        # ── ② B4 상대갭 (지금 −3.5%p) ──
        try:
            print("\n     ② B4 상대갭 — 그 종목 갭이 중앙갭보다 얼마나 나빠야 사나 (지금 −3.5%p)")
            print(f"     {'변형':<22}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            for _g in (-2.0, -2.5, -3.0, -3.5, -4.0, -4.5, -5.0):
                _RK줄(f"상대갭 {_g:+.1f}%p", {"상대갭": _g}, 지금인가=(abs(_g + 3.5) < 1e-9))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ② 터졌다: {_e}")

        # ── ③ R3·R4 빠지는 장 — 지금은 ㉥ 이 꺼져 있다 (날마다 4자리 고정) ──
        try:
            print(f"\n     ③ R3·R4 빠지는 장 — 지금은 **꺼져 있다** (㉥ 켬={R.빠지는장_켬}"
                  f" · 날마다 {R.하루최대종목}자리 고정). 켜면 지수가 눌린 날에만 자리를 늘린다")
            print(f"     {'변형':<22}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            for _문 in (-3, -5, -8, -10, -13, -16):
                for _많 in (6, 8):
                    _RK줄(f"문턱 {_문}% · {_많}자리", {"하루상한": _상한만들기(_문, _많, R.하루최대종목)})
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ③ 터졌다: {_e}")

        # ── ④ B3 비중 × 하루 자리 격자 — 「돈이 묶여 못 산 신호」 ──
        try:
            print(f"\n     ④ B3 비중 × 하루 자리 — 자본 칸이 병목인가 (지금 비중 20% · {R.하루최대종목}자리)")
            print(f"     {'변형':<22}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
            for _w in (0.125, 0.15, 0.20, 0.25, 0.33):
                for _자리 in (3, 4, 5, 6, 8):
                    _RK줄(f"비중 {int(_w * 100)}% · {_자리}자리",
                          {"비중": _w, "하루상한": (lambda 골, _n=_자리: _n)},
                          지금인가=(abs(_w - 0.20) < 1e-9 and _자리 == R.하루최대종목))
        except Exception as _e:  # noqa: BLE001
            print(f"     ⚠️ ④ 터졌다: {_e}")

        print("\n     ⚠️ 여기서 좋은 값이 나와도 **바로 넣지 않는다** — 월요일 보고에서 이유와 함께 꺼낸다")
        print("     ⚠️ R5(시총 하한 낮추기)는 이 판으로 못 잰다 — 풀 밖 사건이 필요해 **문 연 풀**로 따로 돈다")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **D-1 체결 오차 — 산 값이 흔들려도 버티나** (2026-09-23 · 연휴 계획 D1) ══
    if _ONLY == "D1" or "D1" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── D-1 ⭐⭐⭐ **체결 오차 ±0.5% · ±1% 를 10번씩 — 지금 실전(Ⓗ+의료+금속+운송장비)** ──")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금D(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _기D = 시뮬(_c(_지금D, **_열기D), 묶2=_묶D)
        print(f"\n     오차 없음 — {_기D['끝']:,.0f}원 · 낙폭 {_기D['낙']:.1f}% · 산 것 {_기D['산']}")
        print(f"\n     {'오차':<8}{'평균':>16}{'가장 나쁜':>16}{'가장 좋은':>16}{'바탕의%':>9}{'낙폭 평균':>11}  판정")
        _샌D = True
        for _오차 in (0.5, 1.0):
            _끝들, _낙들 = [], []
            for _씨 in range(1, 11):
                _r = 시뮬(_c(_지금D, **_열기D), 오차=_오차, 씨=_씨, 묶2=_묶D)
                if _r:
                    _끝들.append(_r["끝"])
                    _낙들.append(_r["낙"])
            if not _끝들:
                continue
            _평 = sum(_끝들) / len(_끝들)
            _ok = min(_끝들) >= _기D["끝"] * 0.80
            _샌D = _샌D and _ok
            print(f"     ±{_오차}%p{'':<2}{_평:>16,.0f}{min(_끝들):>16,.0f}{max(_끝들):>16,.0f}"
                  f"{_평 / _기D['끝'] * 100:>8.0f}%{sum(_낙들) / len(_낙들):>10.1f}%  "
                  + ("✅ 가장 나쁜 판도 바탕의 80%↑" if _ok else "❌ 가장 나쁜 판이 바탕의 80% 밑"))
        print(f"\n     ⇒ {'✅ 체결 오차를 버틴다' if _샌D else '❌ 체결 오차에 약하다 — 월요일 보고'}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **D-2 VANISH_KIND — 합병·공개매수는 마지막 종가** (2026-09-23 · 연휴 계획 D2) ══
    if _ONLY == "D2" or "D2" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── D-2 ⭐⭐⭐ **사라진 종목을 어떻게 치나 — VANISH_KIND=1(합병은 마지막 종가) vs 전부 −50%** ──")
        print("     ⚠️ 이 판은 VANISH_KIND=1 쪽만 찍는다. 견줄 쪽(전부 −50%)은 **D-1 의 「오차 없음」 줄**이다")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _지금키 = _키표["지금"]

        def _지금D(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        print(f"\n     VANISH_KIND = {os.environ.get('VANISH_KIND') or '꺼짐'}")
        print("     ⚠️ 보통 풀 밖에서 더한 사건(덤프·칸)의 결과값은 **덜 때 쟀던 값**이라 이 옵션이 안 먹는다")
        _r = 시뮬(_c(_지금D, **_열기D), 묶2=_묶D)
        print(f"     지금 실전 — {_r['끝']:,.0f}원 · 낙폭 {_r['낙']:.1f}% · 산 것 {_r['산']}")
        _a = 시뮬(_c(_지금D, **_열기D), 시작년="2010", 끝년="2020", 묶2=_묶D)
        _b = 시뮬(_c(_지금D, **_열기D), 시작년="2021", 끝년="2026", 시드=_a["끝"], 묶2=_묶D) if _a else None
        if _a and _b:
            print(f"     걷기 — 앞(2010~2020) {_a['끝']:,.0f}원 · 뒤(2021~2026) {_b['끝']:,.0f}원")
        print("\n     해마다 (그 해 500만으로 다시 시작)")
        print(f"     {'해':<8}{'산 것':>7}{'끝 자산':>14}{'수익률':>10}")
        for _y in range(2010, 2027):
            _ry = 시뮬(_c(_지금D, **_열기D), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶D)
            if _ry:
                print(f"     {_y:<8}{_ry['산']:>7}{_ry['끝']:>14,.0f}{(_ry['끝'] / 5000000 - 1) * 100:>9.1f}%")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **D-3 걷기 세 토막** (2026-09-23 · 연휴 계획 D3) ══
    if _ONLY == "D3" or "D3" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── D-3 ⭐⭐⭐ **걷기 세 토막 — 2010~2015 / 2016~2020 / 2021~2026 · 옛(Ⓗ+의료) vs 지금(+금속+운송장비)** ──")
        print("     뒤 토막은 앞 토막이 끝낸 돈으로 이어 간다. **세 토막 다** 지금이 옛보다 많아야 ✅")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _옛키, _지금키 = _키표["옛"], _키표["지금"]

        def _옛D(x):
            return (x["code"], x["인"]) in _옛키          # [견줌] 덜어 둔 열쇠

        def _지금D(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        _토막 = [("2010", "2015"), ("2016", "2020"), ("2021", "2026")]
        _배수 = {}
        for _이름, _거름 in (("옛 (Ⓗ+의료)", _옛D), ("지금 (Ⓗ+셋)", _지금D)):
            _시드D = None   # ⚠️ 이름을 _시드 로 쓰면 **밖의 _시드(5,000,000)를 가려** 시묤 전체가 죽는다 (2026-09-23 B50)
            _배수[_이름] = []
            print(f"\n     {_이름}")
            print(f"     {'토막':<14}{'시작 돈':>16}{'끝 돈':>16}{'배수':>8}{'낙폭':>8}{'산 것':>7}")
            for _a, _b in _토막:
                _r = 시뮬(_c(_거름, **_열기D), 시작년=_a, 끝년=_b, 시드=_시드D, 묶2=_묶D)
                if not _r:
                    _배수[_이름].append(None)
                    continue
                _시작돈 = _시드D if _시드D else 5000000
                _배 = _r["끝"] / _시작돈
                _배수[_이름].append(_배)
                print(f"     {_a}~{_b:<9}{_시작돈:>16,.0f}{_r['끝']:>16,.0f}{_배:>7.2f}배{_r['낙']:>7.1f}%{_r['산']:>7}")
                _시드D = _r["끝"]
        print(f"\n     {'토막':<14}{'옛 배수':>10}{'지금 배수':>12}{'차이':>10}  판정")
        _샌D = True
        for _i, (_a, _b) in enumerate(_토막):
            _o, _n = _배수["옛 (Ⓗ+의료)"][_i], _배수["지금 (Ⓗ+셋)"][_i]
            if _o is None or _n is None:
                continue
            _ok = _n > _o
            _샌D = _샌D and _ok
            print(f"     {_a}~{_b:<9}{_o:>9.2f}배{_n:>11.2f}배{(_n / _o - 1) * 100:>9.1f}%  "
                  + ("✅" if _ok else "❌"))
        print(f"\n     ⇒ {'✅ 세 토막 다 지금이 낫다' if _샌D else '❌ 진 토막이 있다 — 월요일 보고'}")
        print("=" * 122)
        if "+" not in _ONLY:
            return 0
        print("  ⭐ 묶음 ONLY — 다음 절로 이어 간다", flush=True)

    # ══ ⭐⭐⭐ **D-4 해마다 표 · 갈래별 채점 (새 바탕)** (2026-09-23 · 연휴 계획 D4) ══
    if _ONLY == "D4" or "D4" in _ONLY.split("+"):
        print("\n" + "=" * 122)
        print("  ── D-4 ⭐⭐⭐ **해마다 표(옛 vs 지금) · 산 것이 어느 갈래에서 나왔나** ──")
        print("=" * 122)
        _합, _묶D, _열기D, _키표 = _D준비()
        _옛키, _지금키 = _키표["옛"], _키표["지금"]

        def _옛D(x):
            return (x["code"], x["인"]) in _옛키          # [견줌] 덜어 둔 열쇠

        def _지금D(x):
            return (x["code"], x["인"]) in _지금키        # [견줌] 덜어 둔 열쇠

        print(f"\n     {'해':<7}{'옛 산 것':>9}{'옛 수익률':>11}{'지금 산 것':>11}{'지금 수익률':>13}{'차이':>10}")
        _더한해, _뺀해 = 0, 0
        for _y in range(2010, 2027):
            _ro = 시뮬(_c(_옛D, **_열기D), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶D)
            _rn = 시뮬(_c(_지금D, **_열기D), 시작년=str(_y), 끝년=str(_y), 시드=5000000, 묶2=_묶D)
            if not _ro or not _rn:
                continue
            _po = (_ro["끝"] / 5000000 - 1) * 100
            _pn = (_rn["끝"] / 5000000 - 1) * 100
            if _pn > _po + 0.05:
                _더한해 += 1
            elif _pn < _po - 0.05:
                _뺀해 += 1
            print(f"     {_y:<7}{_ro['산']:>9}{_po:>10.1f}%{_rn['산']:>11}{_pn:>12.1f}%{_pn - _po:>9.1f}p")
        print(f"     ⇒ 지금이 나은 해 {_더한해} · 못한 해 {_뺀해} · 같은 해 {17 - _더한해 - _뺀해}")

        # ── 갈래별 채점 — 산 것이 Ⓗ 에서 나왔나, 업종 규칙에서 나왔나 ──
        _날인 = {_d: _i for _i, _d in enumerate(날)}
        _기록D = []
        _rt = 시뮬(_c(_지금D, **_열기D), 묶2=_묶D, 기록=_기록D)
        print(f"\n     갈래별 채점 — 지금 실전이 16해 동안 산 {len(_기록D):,}건 ({_rt['끝']:,.0f}원)")
        print(f"     {'갈래':<18}{'건수':>7}{'평균 수익':>11}{'가운데':>10}{'이긴 비율':>11}{'가장 나쁜':>11}")
        _칸별 = {}
        for _거래 in _기록D:
            _d, _code, _r = _거래[0], _거래[1], _거래[4]
            _k = (_code, _날인.get(_d))
            _이름들 = [이 for 이 in R.업종규칙 if _k in _키표[이]]
            _갈 = "Ⓗ (기존 네 갈래)" if not _이름들 else "+".join(_이름들)
            _칸별.setdefault(_갈, []).append(_r)
        for _갈 in sorted(_칸별, key=lambda z: -len(_칸별[z])):
            _v = sorted(_칸별[_갈])
            print(f"     {_갈:<18}{len(_v):>7}{sum(_v) / len(_v):>10.1f}%{_v[len(_v) // 2]:>9.1f}%"
                  f"{sum(1 for z in _v if z > 0) / len(_v) * 100:>10.0f}%{_v[0]:>10.1f}%")
        print("=" * 122)
        return 0

    # ⭐ 묶음 ONLY(D2+D3+D4 …) 이면 여기서 끝낸다 — 옛 절로 새지 않게 (2026-09-23)
    if "+" in _ONLY:
        print("\n  ⭐ 묶음 ONLY 끝 — 옛 절은 안 돈다", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-38 회전율·선물20 문턱 흔들기** (2026-09-23 · 넣기 전 마지막 단계) ══
    if _ONLY == "Q38":
        print("\n" + "=" * 122)
        print("  ── Q-38 ⭐⭐⭐ **회전율·선물20 문턱 흔들기 — 회전율 70/80/90분위 × 선물 10/20/30분위** ──")
        print("     바탕 = 지금 실전(Ⓗ+의료+금속+운송장비) · 가운데(80·20)가 지금 정의")
        print("=" * 122)
        _덤프 = [json.loads(z) for z in io.open(_덤프길, encoding="utf-8") if z.strip()]
        _덤키 = {(x["code"], x["인"]) for x in _덤프}
        _새키 = set()
        _칸사건 = []
        for _꼬 in ("중형금속", "소형운송장비"):
            _ev = [json.loads(z) for z in io.open(os.path.join(O._DATA, "_labs", f"c_events_{_꼬}.jsonl"), encoding="utf-8") if z.strip()]
            _새키 |= {(x["code"], x["인"]) for x in _ev}
            _칸사건 += _ev
        _본 = {(x["code"], x["인"]) for x in 사건}
        _합 = list(사건)
        for x in _덤프 + _칸사건:
            k = (x["code"], x["인"])
            if k not in _본:
                _합.append(x)
                _본.add(k)
        _합묶38 = {}
        for x in _합:
            _합묶38.setdefault(x["인"], []).append(x)
        _열기38 = {"시총하한": 0, "시총상한": 999999999, "대금하한": 0}

        def _바탕38(x):
            return (x["code"], x["인"]) in _덤키 or (x["code"], x["인"]) in _새키    # [견줌] 지금 실전

        _기38 = 시뮬(_c(_바탕38, **_열기38), 묶2=_합묶38)
        print(f"     바탕 재현 — {_기38['끝']:,.0f}원 · 낙폭 {_기38['낙']:.1f}% · 산 것 {_기38['산']}   (341,022,569 근처여야)")
        _회값 = sorted(z for z in (x.get("회전율") for x in 사건) if z is not None)
        _바탕날 = {인 for (_, 인) in (_덤키 | _새키)}
        print(f"\n     {'회전율 자리':<12}{'선물 자리':<10}{'회전율≥':>8}{'선물20≤':>9}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'새 날':>7}  판정 · 증분 걷기")
        _산38 = []
        for _q회 in (0.70, 0.80, 0.90):
            _회위 = _회값[int(len(_회값) * _q회)]
            _회칸 = [x for x in 사건 if (x.get("회전율") or 0) >= _회위 and x.get("_20") is not None]
            _선값 = sorted(z for z in (_선물19(x) for x in _회칸) if z is not None)
            for _q선 in (0.10, 0.20, 0.30):
                _선문 = _선값[int(len(_선값) * _q선)]

                def _회전38(x, 컷=_회위, 문=_선문):
                    if (x.get("시총억") or 0) < R.시총하한억:
                        return False
                    _r = x.get("회전율")
                    if _r is None or _r < 컷:
                        return False
                    if not (재무통과(x) and 대금통과(x)):
                        return False
                    _f = _선물19(x)
                    return _f is not None and _f <= 문

                _도전 = (lambda x, f=_회전38: _바탕38(x) or f(x))     # [견줌]
                _r = 시뮬(_c(_도전, **_열기38), 묶2=_합묶38)
                if not _r:
                    continue
                _ok = (_r["산"] > _기38["산"], _r["끝"] > _기38["끝"], _r["낙"] > 낙폭기준)
                _새 = len({x["인"] for x in 사건 if _회전38(x)} - _바탕날)
                _걷 = "—"
                if all(_ok):
                    _a0 = 시뮬(_c(_바탕38, **_열기38), 시작년="2010", 끝년="2020", 묶2=_합묶38)
                    _a1 = 시뮬(_c(_도전, **_열기38), 시작년="2010", 끝년="2020", 묶2=_합묶38)
                    _b0 = 시뮬(_c(_바탕38, **_열기38), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_합묶38) if _a0 else None
                    _b1 = 시뮬(_c(_도전, **_열기38), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_합묶38) if _a1 else None
                    if _a0 and _a1 and _b0 and _b1:
                        _앞d = (_a1["끝"] / _a0["끝"] - 1) * 100
                        _뒤d = (_b1["끝"] / _b0["끝"] - 1) * 100
                        _걷 = f"앞 {_앞d:+.1f}% 뒤 {_뒤d:+.1f}% " + ("✅" if (_앞d > 0.1 and _뒤d > 0.1) else "❌")
                        if _앞d > 0.1 and _뒤d > 0.1:
                            _산38.append((_q회, _q선))
                print(f"     {int(_q회 * 100):<12}{int(_q선 * 100):<10}{_회위:>7.2f}%{_선문:>8.2f}%{_r['끝']:>16,.0f}"
                      f"{_r['끝'] / _기38['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}{_새:>7}  "
                      + ("✅" if all(_ok) else "❌") + "  " + _걷)
        print(f"\n     ⇒ 9변형 중 세 관문(셋 다 + 증분 걷기)을 넘은 것 {len(_산38)}개"
              + ("  · 지금 정의(80·20) " + ("✅" if (0.80, 0.20) in _산38 else "❌")))
        print("     ⚠️ 반영은 실전 코드를 건드리는 변경이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)
        return 0

    # ══ ⭐⭐⭐ **Q-37 「회사 사정」 거르개** (2026-09-23 · 사용자 물음) ══
    #    지금 규칙은 회사 사정을 안 본다 (관리종목·스팩만 뺀다). 알 수 있는 사정을 빼면 나아지나
    if _ONLY == "Q37":
        print("\n" + "=" * 122)
        print("  ── Q-37 ⭐⭐⭐ **「회사 사정」 거르개 — 유상증자·감자·장중공시·전날하한가를 빼면** ──")
        print("     바탕 = 오늘 넣은 것(Ⓗ+의료+금속+운송장비) · 빼면 산 것은 준다 — 돈·낙폭이 좋아져야 뜻이 있다")
        print("=" * 122)
        _덤프 = [json.loads(z) for z in io.open(_덤프길, encoding="utf-8") if z.strip()]
        _덤키 = {(x["code"], x["인"]) for x in _덤프}
        _새키 = set()
        _칸사건 = []
        for _꼬 in ("중형금속", "소형운송장비"):
            _ev = [json.loads(z) for z in io.open(os.path.join(O._DATA, "_labs", f"c_events_{_꼬}.jsonl"), encoding="utf-8") if z.strip()]
            _새키 |= {(x["code"], x["인"]) for x in _ev}
            _칸사건 += _ev
        _본 = {(x["code"], x["인"]) for x in 사건}
        _합 = list(사건)
        for x in _덤프 + _칸사건:
            k = (x["code"], x["인"])
            if k not in _본:
                _합.append(x)
                _본.add(k)
        _합묶37 = {}
        for x in _합:
            _합묶37.setdefault(x["인"], []).append(x)
        _열기37 = {"시총하한": 0, "시총상한": 999999999, "대금하한": 0}

        def _바탕37(x):
            return (x["code"], x["인"]) in _덤키 or (x["code"], x["인"]) in _새키    # [견줌] 오늘 넣은 것

        # ── 거르개 넷 — 전부 그날까지의 자료 ──
        _증자캐시 = {}

        def _증자(x, 갈래):
            k = (x["code"], x["인"], 갈래)
            if k not in _증자캐시:
                i = x["인"] - 1
                _증자캐시[k] = _NM._증자재기(_증자P, x["code"], 갈래, 날[i], 60, 날, i)
            return _증자캐시[k] or 0

        def _장중공시(x):
            중9, _후9, _챙9 = (_공시표X.get(날[x["인"] - 1]) or {}).get(x["code"], (0, 0, 0))
            return float(중9) > 0

        def _전날하한가(x):
            r"""신호일(인-1) 전날 종가가 그 전날보다 -29% 넘게 빠졌나 (하한가)"""
            i = x["인"] - 1
            sq = 종계.get(x["code"])
            if not sq or i < 2 or len(sq) <= i:
                return False
            _어제, _그제 = sq[i - 1], sq[i - 2]
            if not _어제 or not _그제:
                return False
            return (_어제 / _그제 - 1) * 100 <= -29.0

        _거르개 = (("유상증자 60일 안 뺌", lambda x: _증자(x, "유상증자") > 0),
                  ("감자 60일 안 뺌", lambda x: _증자(x, "감자") > 0),
                  ("그날 장중 공시 뺌", _장중공시),
                  ("전날 하한가 뺌", _전날하한가))
        _기37 = 시뮬(_c(_바탕37, **_열기37), 묶2=_합묶37)
        print(f"     바탕 재현 — {_기37['끝']:,.0f}원 · 낙폭 {_기37['낙']:.1f}% · 산 것 {_기37['산']}"
              f"   (341,296,340 이어야 · {'재현 ✅' if abs(_기37['끝'] - 341296340) < 2e6 else '⚠️ 재현 안 됨'})")
        print(f"\n     {'거르개':<26}{'걸린 사건':>10}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        _결37 = []
        for _라, _f in _거르개 + (("넷 다 뺌", lambda x: any(g(x) for _, g in _거르개)),):
            _걸림 = sum(1 for x in _합 if _바탕37(x) and _f(x))
            _도전 = (lambda x, g=_f: _바탕37(x) and not g(x))       # [견줌] 바탕 AND NOT 사정
            _r = 시뮬(_c(_도전, **_열기37), 묶2=_합묶37)
            if not _r:
                continue
            _ok = (_r["끝"] > _기37["끝"], _r["낙"] > 낙폭기준)
            _결37.append((_라, _도전, _r))
            print(f"     {_라:<26}{_걸림:>10,}{_r['끝']:>16,.0f}{_r['끝'] / _기37['끝'] * 100:>8.0f}%"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}  " + ("⭐ 돈↑ 낙폭 안" if all(_ok) else ("— 낙폭만 좋아짐" if _r["낙"] > _기37["낙"] + 0.3 else "❌")))
        print("\n     ── 돈이 늘어난 것만 증분 걷기 ──")
        for _라, _도전, _r in _결37:
            if _r["끝"] <= _기37["끝"]:
                continue
            _a0 = 시뮬(_c(_바탕37, **_열기37), 시작년="2010", 끝년="2020", 묶2=_합묶37)
            _a1 = 시뮬(_c(_도전, **_열기37), 시작년="2010", 끝년="2020", 묶2=_합묶37)
            _b0 = 시뮬(_c(_바탕37, **_열기37), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_합묶37) if _a0 else None
            _b1 = 시뮬(_c(_도전, **_열기37), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_합묶37) if _a1 else None
            if _a0 and _a1 and _b0 and _b1:
                _앞d = (_a1["끝"] / _a0["끝"] - 1) * 100
                _뒤d = (_b1["끝"] / _b0["끝"] - 1) * 100
                print(f"     {_라:<26} 앞 {_앞d:+6.1f}% · 뒤 {_뒤d:+6.1f}%  " + ("✅" if (_앞d > 0.1 and _뒤d > 0.1) else "❌"))
        print("\n     ⚠️ 뉴스 악재·실적 쇼크·소송 같은 사정은 이 판에 재료가 없다 — 그건 combo4 에만 있다")
        print("     ⚠️ 반영은 실전 코드를 건드리는 변경이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)
        return 0

    # ══ ⭐⭐⭐ **Q-36 해마다 매수 횟수·수익률** (2026-09-23 · 사용자) ══
    if _ONLY == "Q36":
        print("\n" + "=" * 122)
        print("  ── Q-36 ⭐⭐⭐ **해마다 매수 횟수·수익률 — 지금 실전(Ⓗ+의료) vs 오늘 넣은 것(+금속+운송장비)** ──")
        print("=" * 122)
        _덤프 = [json.loads(z) for z in io.open(_덤프길, encoding="utf-8") if z.strip()]
        _덤키 = {(x["code"], x["인"]) for x in _덤프}
        _새키 = set()
        _칸사건 = []
        for _꼬 in ("중형금속", "소형운송장비"):
            _f36 = os.path.join(O._DATA, "_labs", f"c_events_{_꼬}.jsonl")
            _ev = [json.loads(z) for z in io.open(_f36, encoding="utf-8") if z.strip()]
            _새키 |= {(x["code"], x["인"]) for x in _ev}
            _칸사건 += _ev
            print(f"     칸 [{_꼬}] 사건 {len(_ev):,}건")
        _본 = {(x["code"], x["인"]) for x in 사건}
        _합 = list(사건)
        for x in _덤프 + _칸사건:
            k = (x["code"], x["인"])
            if k not in _본:
                _합.append(x)
                _본.add(k)
        _합묶36 = {}
        for x in _합:
            _합묶36.setdefault(x["인"], []).append(x)
        _열기36 = {"시총하한": 0, "시총상한": 999999999, "대금하한": 0}

        def _지금36(x):
            return (x["code"], x["인"]) in _덤키                              # [견줌] Ⓗ+의료

        def _새36(x):
            return (x["code"], x["인"]) in _덤키 or (x["code"], x["인"]) in _새키   # [견줌] +금속+운송장비

        # ── 전 기간 이어서 + 거래 기록 ──
        _기록지 = []
        _기록새 = []
        _r지 = 시뮬(_c(_지금36, **_열기36), 묶2=_합묶36, 기록=_기록지)
        _r새 = 시뮬(_c(_새36, **_열기36), 묶2=_합묶36, 기록=_기록새)
        print(f"\n     전 기간 (2010~2026 이어서 · 시드 500만원)")
        print(f"     {'':<22}{'끝 자산':>16}{'배':>7}{'연평균':>8}{'낙폭':>8}{'산 것':>7}")
        for _라, _r in (("지금 실전 Ⓗ+의료", _r지), ("오늘 넣은 것 +금속+운송장비", _r새)):
            print(f"     {_라:<22}{_r['끝']:>16,.0f}{_r['끝'] / 5e6:>6.1f}배{_r['연']:>7.1f}%{_r['낙']:>7.1f}%{_r['산']:>7}")
        print(f"     (재현: 지금 262,871,069 · 새 341,296,340 이어야 한다)")

        # ── 해마다: 그 해에 500만원으로 시작 ──
        print(f"\n     해마다 따로 (그 해 1월 500만원 → 12월) — 지금 실전 vs 오늘 넣은 것")
        print(f"     {'해':<6}{'지금 수익률':>10}{'산 것':>6}{'낙폭':>8}   {'새 수익률':>10}{'산 것':>6}{'낙폭':>8}   {'차이':>7}  {'새 규칙이 판 것':>10}")
        _키새거래 = {}
        for t in _기록새:
            _키새거래.setdefault(t[0][:4], []).append(t)
        _키지거래 = {}
        for t in _기록지:
            _키지거래.setdefault(t[0][:4], []).append(t)
        for _y in range(2016, 2027):
            _a = 시뮬(_c(_지금36, **_열기36), 시작년=str(_y), 끝년=str(_y), 묶2=_합묶36)
            _b = 시뮬(_c(_새36, **_열기36), 시작년=str(_y), 끝년=str(_y), 묶2=_합묶36)
            if not _a or not _b:
                continue
            _ra = (_a["끝"] / 5e6 - 1) * 100
            _rb = (_b["끝"] / 5e6 - 1) * 100
            _새만 = len(_키새거래.get(str(_y), [])) - len(_키지거래.get(str(_y), []))
            print(f"     {_y:<6}{_ra:>+9.1f}%{_a['산']:>6}{_a['낙']:>7.1f}%   {_rb:>+9.1f}%{_b['산']:>6}{_b['낙']:>7.1f}%   {_rb - _ra:>+6.1f}p  {_새만:>+10}")
        # 새 규칙만의 거래 성적 (전 기간 기록에서 · 새 규칙 사건만)
        # 거래 기록엔 「인」이 없고 날짜가 있다 — 날짜 → 인 으로 바꿔 맞춘다
        _새사건키 = _새키 - _덤키
        _날인 = {d: i + 1 for i, d in enumerate(날)}
        _새만 = [t for t in _기록새 if (t[1], _날인.get(t[0])) in _새사건키]
        if _새만:
            _rs = sorted(t[4] for t in _새만)
            print(f"\n     새 규칙(금속·운송장비)이 실제로 산 것 {len(_새만)}건 · 이긴 비율 {sum(1 for z in _rs if z > 0) / len(_rs) * 100:.0f}%"
                  f" · 평균 {sum(_rs) / len(_rs):+.1f}% · 중앙 {_rs[len(_rs) // 2]:+.1f}% · 최악 {_rs[0]:+.1f}% · 최고 {_rs[-1]:+.1f}%")
            _해별 = {}
            for t in _새만:
                _해별.setdefault(t[0][:4], []).append(t[4])
            print("     해마다 — " + " · ".join(f"{y}:{len(v)}건 {sum(v) / len(v):+.0f}%" for y, v in sorted(_해별.items())))
        print("\n     ⚠️ 시뮬 값이다 — 비중 20% · 하루 4자리 · 상대갭 -3.5 · 상장폐지 -50% · 현금 이자 2.5%. 실전 채점은 forward-log 가 한다")
        print("=" * 122)
        return 0

    # ══ ⭐⭐⭐ **Q-34 후보 셋을 같이 켜면** (2026-09-23) ══
    #    [[compare-candidates-before-adopting]] — 하나 넣고 견주면 되돌리게 된다.
    #    DUMPC 로 덜어 둔 칸 사건 파일들 + Ⓗ 사건을 보통 풀에 합쳐 하나·둘·셋을 잰다
    if _ONLY == "Q34":
        import itertools as _it34
        print("\n" + "=" * 122)
        print("  ── Q-34 ⭐⭐⭐ **후보 셋을 같이 켜면** ──")
        print("=" * 122)
        if not os.path.exists(_덤프길):
            print("  ⚠️ h_events.jsonl 이 없다")
            return 1
        _덤프 = [json.loads(z) for z in io.open(_덤프길, encoding="utf-8") if z.strip()]
        _덤키 = {(x["code"], x["인"]) for x in _덤프}
        _칸파일들 = sorted(glob.glob(os.path.join(O._DATA, "_labs", "c_events_*.jsonl")))
        _칸키 = {}
        _칸사건 = []
        for _f34 in _칸파일들:
            _꼬 = os.path.basename(_f34)[len("c_events_"):-len(".jsonl")]
            _ev = [json.loads(z) for z in io.open(_f34, encoding="utf-8") if z.strip()]
            _칸키[_꼬] = {(x["code"], x["인"]) for x in _ev}
            _칸사건 += _ev
            print(f"     칸 [{_꼬}] 사건 {len(_ev):,}건")
        # ⭐ Q-35 (2026-09-23 08:10) — 넷째 후보: 회전율 위20%·선물20 (그날 선물 · Q-28 ① 정의 그대로)
        #    오늘 08:02:12 브리핑이 기준일 선물을 받아 왔다 → 실전에 쓸 수 있다. 같이 켠 값을 잰다
        if os.environ.get("Q34_ROT"):
            _회값 = sorted(z for z in (x.get("회전율") for x in 사건) if z is not None)
            _회위 = _회값[len(_회값) * 4 // 5]
            _회칸 = [x for x in 사건 if (x.get("회전율") or 0) >= _회위 and x.get("_20") is not None]
            _선값 = sorted(z for z in (_선물19(x) for x in _회칸) if z is not None)
            _선문 = _선값[len(_선값) // 5]

            def _회전규칙35(x, 컷=_회위, 문=_선문):
                # ⚠️ B44 재현 실패(-19.2%)의 원인 — 이 판은 시뮬 시총하한을 0 으로 여는데,
                #    Q-28 은 300억 하한 아래서 쟀다. 실전 바깥 문(300억)과 같게 규칙에 넣는다
                if (x.get("시총억") or 0) < R.시총하한억:
                    return False
                _r = x.get("회전율")
                if _r is None or _r < 컷:
                    return False
                if not (재무통과(x) and 대금통과(x)):
                    return False
                _f = _선물19(x)
                return _f is not None and _f <= 문

            _칸키["회전율선물20"] = {(x["code"], x["인"]) for x in 사건 if _회전규칙35(x)}
            print(f"     칸 [회전율선물20] 사건 {len(_칸키['회전율선물20']):,}건"
                  f"  (회전율 ≥ {_회위:.2f}% · 선물20 ≤ {_선문:.2f}% · 그날 선물 · Q-28 ① 재현: 얹으면 317,877,167 이어야)")
        if not _칸키:
            print("  ⚠️ c_events_*.jsonl 이 없다 — 먼저 DUMPC 를 돌려라")
            return 1
        _풀키 = {(x["code"], x["인"]) for x in 사건}
        _합 = list(사건)
        _본 = set(_풀키)
        for x in _덤프 + _칸사건:
            k = (x["code"], x["인"])
            if k not in _본:
                _합.append(x)
                _본.add(k)
        _합묶34 = {}
        for x in _합:
            _합묶34.setdefault(x["인"], []).append(x)
        print(f"     보통 풀 {len(사건):,} + Ⓗ {len(_덤프):,} + 칸 {len(_칸사건):,} → 합 {len(_합):,}건")
        _열기34 = {"시총하한": 0, "시총상한": 999999999, "대금하한": 0}

        def _바탕34(x):
            return (x["code"], x["인"]) in _덤키          # [견줌] 지금 실전 (Ⓗ+의료)

        _기34 = 시뮬(_c(_바탕34, **_열기34), 묶2=_합묶34)
        print(f"     바탕 재현 — {_기34['끝']:,.0f}원 · 낙폭 {_기34['낙']:.1f}% · 산 것 {_기34['산']}"
              f"   ({'재현 ✅' if abs(_기34['끝'] - 262871069) < 2e6 else '⚠️ 재현 안 됨 — 결론 쓰지 마라'})")
        _꼬들 = sorted(_칸키)
        print(f"\n     {'조합':<40}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'새 날':>7}  판정")
        _결과34 = {}
        for _n in range(1, len(_꼬들) + 1):
            for _조 in _it34.combinations(_꼬들, _n):
                _키합 = set().union(*(_칸키[t] for t in _조))
                _도전 = (lambda x, K=_키합: _바탕34(x) or (x["code"], x["인"]) in K)     # [견줌]
                _r = 시뮬(_c(_도전, **_열기34), 묶2=_합묶34)
                if not _r:
                    continue
                _새 = len({인 for (_, 인) in _키합} - {인 for (_, 인) in _덤키})
                _ok = (_r["산"] > _기34["산"], _r["끝"] > _기34["끝"], _r["낙"] > 낙폭기준)
                _결과34[_조] = (_r, _도전, _새)
                print(f"     {'+'.join(_조):<40}{_r['끝']:>16,.0f}{_r['끝'] / _기34['끝'] * 100:>8.0f}%"
                      f"{_r['낙']:>7.1f}%{_r['산']:>7}{_새:>7}  " + ("✅ 셋 다" if all(_ok) else "❌"))
        # 더해서 더 나아지나 — 둘·셋이 그 부분집합 최고보다 나은가
        print("\n     ── 더하면 나아지나 (부분집합 최고와 견줌) ──")
        for _조, (_r, _, _) in sorted(_결과34.items(), key=lambda kv: (len(kv[0]), kv[0])):
            if len(_조) < 2:
                continue
            _부분 = [(_결과34[c][0]["끝"], c) for c in _결과34 if set(c) < set(_조)]
            if not _부분:
                continue
            _최, _c최 = max(_부분)
            print(f"     {'+'.join(_조):<40} vs {'+'.join(_c최):<28} {_r['끝'] / _최 * 100:>6.1f}%"
                  + ("  ⭐ 더 낫다" if _r["끝"] > _최 + 1000 else ("  ⚠️ 같다 — 흡수" if abs(_r["끝"] - _최) < 1000 else "  — 나을 게 없다")))
        # 셋 다 넘은 조합은 증분 걷기
        print("\n     ── 셋 다 넘은 조합의 증분 걷기 (뒤는 앞이 끝낸 돈으로) ──")
        for _조, (_r, _도전, _새) in sorted(_결과34.items(), key=lambda kv: -kv[1][0]["끝"]):
            _ok = (_r["산"] > _기34["산"], _r["끝"] > _기34["끝"], _r["낙"] > 낙폭기준)
            if not all(_ok):
                continue
            _a0 = 시뮬(_c(_바탕34, **_열기34), 시작년="2010", 끝년="2020", 묶2=_합묶34)
            _a1 = 시뮬(_c(_도전, **_열기34), 시작년="2010", 끝년="2020", 묶2=_합묶34)
            _b0 = 시뮬(_c(_바탕34, **_열기34), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_합묶34) if _a0 else None
            _b1 = 시뮬(_c(_도전, **_열기34), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_합묶34) if _a1 else None
            if _a0 and _a1 and _b0 and _b1:
                _앞d = (_a1["끝"] / _a0["끝"] - 1) * 100
                _뒤d = (_b1["끝"] / _b0["끝"] - 1) * 100
                print(f"     {'+'.join(_조):<40} 앞 {_앞d:+6.1f}% · 뒤 {_뒤d:+6.1f}%  "
                      + ("✅" if (_앞d > 0.1 and _뒤d > 0.1) else "❌"))
        print("\n     ⚠️ 반영은 실전 코드를 건드리는 변경이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)
        return 0

    # ══ ⭐⭐⭐ **Q-30 칸 규칙을 Ⓗ+의료 위에 얹으면 빈 날을 채우나** (2026-09-22) ══
    #    반영을 정하는 물음. 띠 풀(OPENFIN) + 덜어 둔 Ⓗ 사건을 합쳐 `묶2` 로 시뮬에 넘긴다.
    if _ONLY == "Q30":
        print("\n" + "=" * 122)
        print("  ── Q-30 ⭐⭐⭐ **칸 규칙을 Ⓗ+의료 위에 얹으면 빈 날을 채우나** ──")
        print("     바탕 = 덜어 둔 Ⓗ+의료 사건만 · 도전 = 그것 OR 칸 규칙 · 셋 다 + 증분 걷기")
        print("=" * 122)
        if not _문열기:
            print("  ⚠️ Q-30 은 OPENFIN 띠 풀에서 돌려야 한다")
            return 1
        if not os.path.exists(_덤프길):
            print(f"  ⚠️ {_덤프길} 이 없다 — 먼저 ONLY=DUMPH 를 돌려라")
            return 1
        _덤프 = [json.loads(z) for z in io.open(_덤프길, encoding="utf-8") if z.strip()]
        _덤키 = {(x["code"], x["인"]) for x in _덤프}
        _풀키 = {(x["code"], x["인"]) for x in 사건}
        _합사건 = 사건 + [x for x in _덤프 if (x["code"], x["인"]) not in _풀키]
        _합묶 = {}
        for x in _합사건:
            _합묶.setdefault(x["인"], []).append(x)
        print(f"\n     띠 풀 {len(사건):,}건 + Ⓗ 사건 {len(_덤프):,}건 (겹침 {len(_덤키 & _풀키):,})"
              f" = {len(_합사건):,}건 · {len(_합묶):,}일")

        def _바탕30(x):
            return (x["code"], x["인"]) in _덤키          # [견줌] 지금 실전 (Ⓗ+의료)

        _열기30 = {"시총하한": 0, "시총상한": 999999999, "대금하한": 0}
        _기30 = 시뮬(_c(_바탕30, **_열기30), 묶2=_합묶)
        print(f"     바탕 재현 — {_기30['끝']:,.0f}원 · 낙폭 {_기30['낙']:.1f}% · 산 것 {_기30['산']}"
              f"   (Q-28 ⓪ 262,871,069 · {'재현 ✅' if abs(_기30['끝'] - 262871069) < 2e6 else '⚠️ 재현 안 됨 — 결론 쓰지 마라'})")

        # ── 이 띠의 위 5칸을 요약 파일에서 ──
        _띠이름30 = {100: "초소형 100~300억", 300: "소형 300~800억", 800: "소형 800~2,000억",
                     2000: "중형 2,000억~1조", 10000: "대형 1조~10조", 100000: "초대형 10조↑"
                     }.get(int(_크기하한 / 1e8))
        _요약길 = os.path.join(O._DATA, "_labs", "2026-09-22_Q29_칸별요약.txt")
        _고를30 = []
        _안 = False
        for _ln in io.open(_요약길, encoding="utf-8"):
            if _ln.startswith("══ "):
                _안 = _ln.startswith(f"══ {_띠이름30}")
                continue
            if not _안 or not _ln.strip():
                continue
            import re as _re30
            _m = _re30.match(r"^\s*(.+?)\s{2,}(.+?)\s{2,}비중(\d+)% 자리(\d+)\s+([\d,]+)원", _ln)
            if _m and len(_고를30) < 5:
                _고를30.append((_m.group(1).strip(), "+" in _m.group(2), int(_m.group(3)) / 100, int(_m.group(4))))
        print(f"     이 띠({_띠이름30})의 위 {len(_고를30)}칸: " + " · ".join(k for k, _, _, _ in _고를30))

        # ── 칸 만들기 (Q-29 와 같은 코드) ──
        _아님30 = {"인", "code", "해", "_지수이름", "섹터", "매수", "재통과", "흑자",
                   "_20", "_40", "_겹친", "갭", "시총억", "원시"}
        _칸이름30 = [k for k in sorted(사건[0].keys()) if k not in _아님30
                     and sum(1 for x in 사건[:5000] if isinstance(x.get(k), (int, float))) >= 1500]
        _특수30 = ("자사주60", "코스피200선물20", "ETF괴리", "ETF괴리20", "기준금리20",
                   "무역수지비", "금값20", "공시장중", "ETF시총20", "미국선거전5",
                   "금통위변경후5", "봄", "여름", "가을", "겨울")
        _재전부30 = ([(k, (lambda x, k=k: x.get(k))) for k in _칸이름30]
                     + [(k, (lambda x, k=k: _값P(x, k))) for k in _특수30])
        _재사전30 = dict(_재전부30)
        _띠표30 = {"띠 초소형 100~300억": (100, 300), "띠 소형 300~2,000억": (300, 2000),
                   "띠 중형 2,000억~1조": (2000, 10000), "띠 대형 1조~10조": (10000, 100000),
                   "띠 초대형 10조↑": (100000, 9e12)}

        def _칸든30(라):
            if 라 in _띠표30:
                lo, hi = _띠표30[라]
                return lambda x: lo <= (x.get("시총억") or 0) < hi
            if 라.startswith("업종 "):
                _n = 라[3:]
                return lambda x: str(x.get("섹터") or "")[:12] == _n[:12]
            for _꼬, _쪽 in ((" 아래20%", "아래"), (" 위20%", "위")):
                if 라.endswith(_꼬):
                    _f = _재사전30.get(라[:-len(_꼬)])
                    if _f is None:
                        return None
                    _v = sorted(z for z in (_f(x) for x in 사건) if z is not None)
                    if not _v:
                        return None
                    _c0 = _v[len(_v) // 5] if _쪽 == "아래" else _v[len(_v) * 4 // 5]
                    return (lambda x, f=_f, c=_c0: f(x) is not None and f(x) <= c) if _쪽 == "아래" \
                        else (lambda x, f=_f, c=_c0: f(x) is not None and f(x) >= c)
            return None

        # ⭐ DUMPC — 지정한 칸 규칙에 맞는 사건을 파일로 덜어 둔다 (Q-34 가 합친다)
        _덤칸 = os.environ.get("DUMPC_CELL")
        if _덤칸:
            _꼬 = os.environ.get("DUMPC_TAG") or "cell"
            _맞 = [g for g in _고를30 if g[0].startswith(_덤칸)]
            if not _맞:
                print(f"  ⚠️ DUMPC — 요약 위 5칸에 「{_덤칸}」 이 없다: " + " · ".join(g[0] for g in _고를30))
                return 1
            _라D, _둘D, _, _ = _맞[0]
            _든D = _칸든30(_라D)
            _칸D = [x for x in 사건 if _든D(x)]
            _잉 = sorted(z for z in (x.get("잉여금") for x in _칸D) if z is not None)
            _부 = sorted(z for z in (x.get("부채") for x in _칸D) if z is not None)
            _대 = sorted(z for z in (x.get("대금억") for x in _칸D) if z is not None)
            _잉컷, _부컷, _대컷 = _잉[int(len(_잉) * .3)], _부[int(len(_부) * .7)], _대[int(len(_대) * .2)]

            def _문D(x, a=_잉컷, b=_부컷, c=_대컷, 든=_든D):
                if not 든(x):
                    return False
                _i, _p = x.get("잉여금"), x.get("부채")
                if _i is None or _p is None or _i < a or _p > b or x.get("흑자") != 1.0:
                    return False
                return (x.get("대금억") or 0) >= c

            _통D = [x for x in _칸D if _문D(x) and x.get("_20") is not None]
            _바D = sum(1 for x in _통D if x["_20"] > 0) / len(_통D) * 100
            _재신호D = [(k + "↓", f, "아래") for k, f in _재전부30] + [(k + "↑", f, "위") for k, f in _재전부30]
            _문턱D, _좋D = {}, []
            for _이, _꺼, _방 in _재신호D:
                _v = sorted(z for z in (_꺼(x) for x in _통D) if z is not None)
                if len(_v) < len(_통D) * .25 or len(set(_v[::max(1, len(_v) // 2000)])) < 20:
                    continue
                _문턱D[_이] = _v[len(_v) // 5] if _방 == "아래" else _v[len(_v) * 4 // 5]
            for _이, _꺼, _방 in _재신호D:
                _컷 = _문턱D.get(_이)
                if _컷 is None:
                    continue
                _z = [x for x in _통D if _꺼(x) is not None and ((_꺼(x) <= _컷) if _방 == "아래" else (_꺼(x) >= _컷))]
                if len(_z) < 300:
                    continue
                _w = sum(1 for x in _z if x["_20"] > 0) / len(_z) * 100
                _a = [x for x in _z if 날[x["인"] - 1][:4] <= "2018"]
                _b = [x for x in _z if 날[x["인"] - 1][:4] > "2018"]
                if len(_a) < 100 or len(_b) < 100:
                    continue
                _wa = sum(1 for x in _a if x["_20"] > 0) / len(_a) * 100
                _wb = sum(1 for x in _b if x["_20"] > 0) / len(_b) * 100
                if (_w - _바D) < 2.0 or (_wa - _바D) * (_wb - _바D) <= 0:
                    continue
                _좋D.append((_w - _바D, _이))
            _좋D.sort(reverse=True)
            _쓸D = tuple(z[1] for z in _좋D[:2]) if _둘D else (_좋D[0][1],)

            def _띠규칙D(x, 쓸=_쓸D, 문=_문D, 표=dict(_문턱D), 재=tuple(_재신호D)):
                if not 문(x):
                    return False
                for _이, _꺼, _방 in 재:
                    if _이 not in 쓸:
                        continue
                    _v = _꺼(x)
                    if _v is None or ((_v > 표[_이]) if _방 == "아래" else (_v < 표[_이])):
                        return False
                return True

            _덤D = [dict(x, _칸=_꼬) for x in 사건 if _띠규칙D(x)]
            _길D = os.path.join(O._DATA, "_labs", f"c_events_{_꼬}.jsonl")
            with io.open(_길D, "w", encoding="utf-8") as _f:
                for x in _덤D:
                    _f.write(json.dumps(x, ensure_ascii=False, default=str) + "\n")
            _rD = 시뮬(_c(lambda x: _바탕30(x) or _띠규칙D(x), **_열기30), 묶2=_합묶)   # [견줌]
            print(f"\n  DUMPC — [{_라D} · {'+'.join(_쓸D)}] 맞는 사건 {len(_덤D):,}건 → {_길D}")
            # ⭐ 실전에 넣을 때 적을 **숫자** — 전부 이 칸 자료에서 낸 값 (2026-09-23)
            print(f"     ┌ 칸: {_라D}  (띠 {int(_크기하한 / 1e8):,}~{int(_크기웃한 / 1e8):,}억 · 칸 사건 {len(_칸D):,} · 문 통과 {len(_통D):,})")
            print(f"     │ 재무 — 잉여금 ≥ {_잉컷:.2f}% · 부채 ≤ {_부컷:.2f}% · 흑자   (30·70분위)")
            print(f"     │ 대금 — ≥ {_대컷:.2f}억   (20분위)")
            for _이 in _쓸D:
                print(f"     │ 신호 — {_이}  문턱 {_문턱D[_이]:.4f}   ({'≤' if _이.endswith('↓') else '≥'} · 20분위)")
            print(f"     │ 상대갭 — Ⓗ 그대로 {R.상대갭문턱:g}%p (칸 값 안 씀)   · 파는 규칙 — Ⓗ 그대로")   # [견줌]
            print(f"     └ 해마다 켜진 날 — " + " · ".join(
                f"{_y}:{len({x['인'] for x in _덤D if 날[x['인'] - 1][:4] == str(_y)})}" for _y in range(2016, 2027)))
            print(f"         재현: Ⓗ+의료 OR 이 칸 = {_rD['끝']:,.0f}원 · 낙폭 {_rD['낙']:.1f}% · 산 것 {_rD['산']}"
                  f"  (Q-33/Q-30 값과 같아야 한다)")
            return 0

        _산30 = []
        for _라30, _둘30, _비30, _자30 in _고를30:
            _든30 = _칸든30(_라30)
            if _든30 is None:
                print(f"\n     [{_라30}] 칸을 못 만들었다 — 건너뜀")
                continue
            _칸30 = [x for x in 사건 if _든30(x)]
            _잉 = sorted(z for z in (x.get("잉여금") for x in _칸30) if z is not None)
            _부 = sorted(z for z in (x.get("부채") for x in _칸30) if z is not None)
            _대 = sorted(z for z in (x.get("대금억") for x in _칸30) if z is not None)
            if not (_잉 and _부 and _대):
                continue
            _잉컷, _부컷, _대컷 = _잉[int(len(_잉) * .3)], _부[int(len(_부) * .7)], _대[int(len(_대) * .2)]

            def _문30(x, a=_잉컷, b=_부컷, c=_대컷, 든=_든30):
                if not 든(x):
                    return False
                _i, _p = x.get("잉여금"), x.get("부채")
                if _i is None or _p is None or _i < a or _p > b or x.get("흑자") != 1.0:
                    return False
                return (x.get("대금억") or 0) >= c

            _통30 = [x for x in _칸30 if _문30(x) and x.get("_20") is not None]
            if len(_통30) < 3000:
                print(f"\n     [{_라30}] 문 통과 {len(_통30):,}건 — 표본 부족")
                continue
            _바 = sum(1 for x in _통30 if x["_20"] > 0) / len(_통30) * 100
            _재신호30 = [(k + "↓", f, "아래") for k, f in _재전부30] + [(k + "↑", f, "위") for k, f in _재전부30]
            _문턱30, _좋30 = {}, []
            for _이, _꺼, _방 in _재신호30:
                _v = sorted(z for z in (_꺼(x) for x in _통30) if z is not None)
                if len(_v) < len(_통30) * .25 or len(set(_v[::max(1, len(_v) // 2000)])) < 20:
                    continue
                _문턱30[_이] = _v[len(_v) // 5] if _방 == "아래" else _v[len(_v) * 4 // 5]
            for _이, _꺼, _방 in _재신호30:
                _컷 = _문턱30.get(_이)
                if _컷 is None:
                    continue
                _z = [x for x in _통30 if _꺼(x) is not None and ((_꺼(x) <= _컷) if _방 == "아래" else (_꺼(x) >= _컷))]
                if len(_z) < 300:
                    continue
                _w = sum(1 for x in _z if x["_20"] > 0) / len(_z) * 100
                _a = [x for x in _z if 날[x["인"] - 1][:4] <= "2018"]
                _b = [x for x in _z if 날[x["인"] - 1][:4] > "2018"]
                if len(_a) < 100 or len(_b) < 100:
                    continue
                _wa = sum(1 for x in _a if x["_20"] > 0) / len(_a) * 100
                _wb = sum(1 for x in _b if x["_20"] > 0) / len(_b) * 100
                if (_w - _바) < 2.0 or (_wa - _바) * (_wb - _바) <= 0:
                    continue
                _좋30.append((_w - _바, _이))
            _좋30.sort(reverse=True)
            if not _좋30:
                print(f"\n     [{_라30}] 센 재료 없음 — 건너뜀")
                continue
            _쓸30 = tuple(z[1] for z in _좋30[:2]) if _둘30 else (_좋30[0][1],)
            _갭 = sorted(z for z in (x.get("갭") for x in _통30) if z is not None)
            _갭컷30 = _갭[int(len(_갭) * .2)] if len(_갭) > 1000 else None

            def _띠규칙30(x, 쓸=_쓸30, 문=_문30, 표=dict(_문턱30), 재=tuple(_재신호30)):
                if not 문(x):
                    return False
                for _이, _꺼, _방 in 재:
                    if _이 not in 쓸:
                        continue
                    _v = _꺼(x)
                    if _v is None or ((_v > 표[_이]) if _방 == "아래" else (_v < 표[_이])):
                        return False
                return True

            _도전30 = (lambda x, f=_띠규칙30: _바탕30(x) or f(x))       # [견줌] Ⓗ+의료 OR 칸
            _옵30 = dict(_열기30)
            # 바탕(Ⓗ) 상대갭 −3.5 는 그대로 두고, **이 띠 사건에만** 칸이 낸 상대갭을 배수로 준다.
            # 배수를 내려면 바탕 값이 필요하다 — 바탕 쪽 값이지 띠 규칙에 소형 값을 넣는 게 아니다
            if _크기하한 >= 2000e8 and _갭컷30 is not None and R.상대갭문턱:   # [견줌]
                _옵30["갭무름"] = [(int(_크기하한 / 1e8), _갭컷30 / R.상대갭문턱)]   # [견줌] 이 띠 사건에만 칸의 상대갭
            _r30 = 시뮬(_c(_도전30, **_옵30), 묶2=_합묶)
            if not _r30:
                continue
            _ok30 = (_r30["산"] > _기30["산"], _r30["끝"] > _기30["끝"], _r30["낙"] > 낙폭기준)
            _새날 = len({x["인"] for x in 사건 if _띠규칙30(x)} - {x["인"] for x in _덤프})
            print(f"\n     ── [{_라30} · {'+'.join(_쓸30)}] 비중{_비30:.0%} 자리{_자30}"
                  f" · 상대갭 {('%.2f' % _갭컷30) if _갭컷30 is not None else '?'}"
                  f" · Ⓗ 가 안 사던 날 {_새날:,}일 열림 ──")
            print(f"        Ⓗ+의료 OR 칸  {_r30['끝']:>16,.0f}원  (바탕의 {_r30['끝'] / _기30['끝'] * 100:.0f}%)"
                  f"  낙폭 {_r30['낙']:.1f}%  산 것 {_r30['산']} (바탕 {_기30['산']})  "
                  + ("✅ 셋 다" if all(_ok30) else "❌"))
            if not all(_ok30):
                continue
            # 증분 걷기 — 밑거름도 바탕으로, 묶2 로
            _a0 = 시뮬(_c(_바탕30, **_열기30), 시작년="2010", 끝년="2020", 묶2=_합묶)
            _a1 = 시뮬(_c(_도전30, **_옵30), 시작년="2010", 끝년="2020", 묶2=_합묶)
            _b0 = 시뮬(_c(_바탕30, **_열기30), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_합묶) if _a0 else None
            _b1 = 시뮬(_c(_도전30, **_옵30), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_합묶) if _a1 else None
            if _a0 and _a1 and _b0 and _b1:
                _앞d = (_a1["끝"] / _a0["끝"] - 1) * 100
                _뒤d = (_b1["끝"] / _b0["끝"] - 1) * 100
                print(f"        앞 2010~2020: {_a0['끝']:,.0f} → {_a1['끝']:,.0f}원  {_앞d:+.1f}%"
                      f"   뒤 2021~2026: {_b0['끝']:,.0f} → {_b1['끝']:,.0f}원  {_뒤d:+.1f}%")
                _걷ok = _앞d > 0.1 and _뒤d > 0.1
                print("        걷기: " + ("✅ 앞뒤 둘 다 늘렸다" if _걷ok else "❌ 한쪽이 안 늘었다") + "   (증분 · 뒤는 앞이 끝낸 돈으로)")
                if _걷ok:
                    _산30.append((_라30, _쓸30, _r30, _새날))
        print(f"\n     ══ **[{_띠이름30}] Ⓗ+의료 위에 얹어 세 관문을 넘은 칸 {len(_산30)}개** ══")
        for _라30, _쓸30, _r30, _새날 in sorted(_산30, key=lambda t: -t[2]["끝"]):
            print(f"       {_라30} · {'+'.join(_쓸30)}  {_r30['끝']:,.0f}원 ({_r30['끝'] / _기30['끝'] * 100:.0f}%)"
                  f" · 낙폭 {_r30['낙']:.1f}% · 산 것 {_r30['산']} · 새 날 {_새날}")
        print("     ⚠️ 반영은 실전 코드를 건드리는 변경이다 — 사용자 확인 뒤에 넣는다")
        print("=" * 122)

        # ══ ⭐⭐ Q-32 — 왜 얹으면 낙폭이 -38% 가 되나 (중형·대형에서만 · Q30 1등 칸으로) ══
        if os.environ.get("Q32") and _고를30:
            print("\n" + "=" * 122)
            print("  ── Q-32 ⭐⭐ **얹으면 낙폭 -38% — 장치인가 규칙인가** ──")
            print("=" * 122)
            _라32, _둘32, _비32, _자32 = _고를30[0]
            _든32 = _칸든30(_라32)
            _칸32 = [x for x in 사건 if _든32(x)]
            _잉 = sorted(z for z in (x.get("잉여금") for x in _칸32) if z is not None)
            _부 = sorted(z for z in (x.get("부채") for x in _칸32) if z is not None)
            _대 = sorted(z for z in (x.get("대금억") for x in _칸32) if z is not None)
            _잉컷, _부컷, _대컷 = _잉[int(len(_잉) * .3)], _부[int(len(_부) * .7)], _대[int(len(_대) * .2)]

            def _문32(x, a=_잉컷, b=_부컷, c=_대컷, 든=_든32):
                if not 든(x):
                    return False
                _i, _p = x.get("잉여금"), x.get("부채")
                if _i is None or _p is None or _i < a or _p > b or x.get("흑자") != 1.0:
                    return False
                return (x.get("대금억") or 0) >= c

            _통32 = [x for x in _칸32 if _문32(x) and x.get("_20") is not None]
            _바32 = sum(1 for x in _통32 if x["_20"] > 0) / len(_통32) * 100
            _재신호32 = [(k + "↓", f, "아래") for k, f in _재전부30] + [(k + "↑", f, "위") for k, f in _재전부30]
            _문턱32, _좋32 = {}, []
            for _이, _꺼, _방 in _재신호32:
                _v = sorted(z for z in (_꺼(x) for x in _통32) if z is not None)
                if len(_v) < len(_통32) * .25 or len(set(_v[::max(1, len(_v) // 2000)])) < 20:
                    continue
                _문턱32[_이] = _v[len(_v) // 5] if _방 == "아래" else _v[len(_v) * 4 // 5]
            for _이, _꺼, _방 in _재신호32:
                _컷 = _문턱32.get(_이)
                if _컷 is None:
                    continue
                _z = [x for x in _통32 if _꺼(x) is not None and ((_꺼(x) <= _컷) if _방 == "아래" else (_꺼(x) >= _컷))]
                if len(_z) < 300:
                    continue
                _w = sum(1 for x in _z if x["_20"] > 0) / len(_z) * 100
                _a = [x for x in _z if 날[x["인"] - 1][:4] <= "2018"]
                _b = [x for x in _z if 날[x["인"] - 1][:4] > "2018"]
                if len(_a) < 100 or len(_b) < 100:
                    continue
                _wa = sum(1 for x in _a if x["_20"] > 0) / len(_a) * 100
                _wb = sum(1 for x in _b if x["_20"] > 0) / len(_b) * 100
                if (_w - _바32) < 2.0 or (_wa - _바32) * (_wb - _바32) <= 0:
                    continue
                _좋32.append((_w - _바32, _이))
            _좋32.sort(reverse=True)
            _쓸32 = tuple(z[1] for z in _좋32[:2]) if _둘32 else (_좋32[0][1],)
            _갭 = sorted(z for z in (x.get("갭") for x in _통32) if z is not None)
            _갭컷32 = _갭[int(len(_갭) * .2)] if len(_갭) > 1000 else None

            def _띠규칙32(x, 쓸=_쓸32, 문=_문32, 표=dict(_문턱32), 재=tuple(_재신호32)):
                if not 문(x):
                    return False
                for _이, _꺼, _방 in 재:
                    if _이 not in 쓸:
                        continue
                    _v = _꺼(x)
                    if _v is None or ((_v > 표[_이]) if _방 == "아래" else (_v < 표[_이])):
                        return False
                return True

            _도전32 = (lambda x, f=_띠규칙32: _바탕30(x) or f(x))            # [견줌]
            _옵32 = dict(_열기30)
            if _크기하한 >= 2000e8 and _갭컷32 is not None and R.상대갭문턱:   # [견줌]
                _옵32["갭무름"] = [(int(_크기하한 / 1e8), _갭컷32 / R.상대갭문턱)]   # [견줌]
            print(f"     칸 [{_라32} · {'+'.join(_쓸32)}] · 상대갭 {_갭컷32}")

            # ① 거래 기록 — 얹어서 새로 생긴 거래
            _기록바 = []
            _기록도 = []
            _r바 = 시뮬(_c(_바탕30, **_열기30), 묶2=_합묶, 기록=_기록바)
            _r도 = 시뮬(_c(_도전32, **_옵32), 묶2=_합묶, 기록=_기록도)
            _키바 = {(t[0], t[1]) for t in _기록바}
            _새거래 = [t for t in _기록도 if (t[0], t[1]) not in _키바]
            _사라짐 = [t for t in _새거래 if t[4] <= -49.9]
            print(f"\n     바탕 {_r바['끝']:,.0f}원 · 낙폭 {_r바['낙']:.1f}% · 거래 {len(_기록바)}"
                  f"   →  얹음 {_r도['끝']:,.0f}원 · 낙폭 {_r도['낙']:.1f}% · 거래 {len(_기록도)}")
            print(f"     얹어서 **새로 생긴 거래 {len(_새거래)}건** · 그중 결과 ≤ -49.9% (사라짐 -50%) **{len(_사라짐)}건**")
            print(f"     새 거래 중 큰 종목(≥{int(_크기하한 / 1e8):,}억) {sum(1 for t in _새거래 if (t[2] or 0) >= _크기하한 / 1e8)}건")
            print(f"     {'날':<10}{'code':<8}{'시총억':>10}{'원시':>10}{'결과%':>8}{'청산':>7}{'주수':>10}")
            for t in sorted(_새거래, key=lambda t: t[4])[:25]:
                print(f"     {t[0]:<10}{t[1]:<8}{(t[2] or 0):>10,.0f}{(t[3] or 0):>10,.0f}{t[4]:>8.1f}{str(t[5]):>7}{(t[6] or 0):>10,}")
            # 새 거래 결과 분포
            _rs = sorted(t[4] for t in _새거래)
            if _rs:
                print(f"     새 거래 결과% — 최소 {_rs[0]:.1f} · 하위25% {_rs[len(_rs)//4]:.1f} · 중앙 {_rs[len(_rs)//2]:.1f}"
                      f" · 평균 {sum(_rs)/len(_rs):+.1f} · 이긴 비율 {sum(1 for z in _rs if z > 0)/len(_rs)*100:.0f}%")

            # ② 해마다 끝 자산 나란히
            print(f"\n     {'해':<6}{'바탕 끝':>16}{'얹음 끝':>16}{'바탕 낙폭':>10}{'얹음 낙폭':>10}")
            for _y in range(2010, 2027):
                _a = 시뮬(_c(_바탕30, **_열기30), 시작년=str(_y), 끝년=str(_y), 묶2=_합묶)
                _b = 시뮬(_c(_도전32, **_옵32), 시작년=str(_y), 끝년=str(_y), 묶2=_합묶)
                if _a and _b:
                    print(f"     {_y:<6}{_a['끝']:>16,.0f}{_b['끝']:>16,.0f}{_a['낙']:>9.1f}%{_b['낙']:>9.1f}%")

            # ③ 변형 — 어느 장치가 만드나
            for _라v, _옵v in (("갭무름 뺌 (전부 -3.5)", dict(_열기30)),
                               ("자리 3", {**_옵32, "하루상한": 3}),
                               ("비중 10%", {**_옵32, "비중": 0.10}),
                               ("칸 규칙만 (Ⓗ 없이)", None)):
                if _옵v is None:
                    _rv = 시뮬(_c(_띠규칙32, **_옵32), 묶2=_합묶)
                else:
                    _rv = 시뮬(_c(_도전32, **_옵v), 묶2=_합묶)
                if _rv:
                    print(f"     {_라v:<24}{_rv['끝']:>16,.0f}원  낙폭 {_rv['낙']:.1f}%  산 것 {_rv['산']}")
            print("=" * 122)

        # ══ ⭐⭐ Q-33 — 중형·대형 칸을 **상대갭 빡빡하게 · 중복금지**로 다시 얹는다 ══
        #    Q-32: -38% 는 칸 상대갭(20분위)이 느슨해 새 거래가 188~243건으로 불고,
        #    떨어지는 종목을 열 번 넘게 반복 매수한 탓. 갭무름 뺌(-3.5)이면 대형이 셋 다 ✅ 였다
        _산33 = []          # Q-33 이 안 돌아도 Q-31 이 읽을 수 있게
        if os.environ.get("Q33") and _고를30:
            print("\n" + "=" * 122)
            print("  ── Q-33 ⭐⭐ **상대갭 {Ⓗ -3.5 · 칸 5분위 · 칸 10분위} × 중복금지 {끔·켬}** ──")
            print("     ⚠️ 5·10분위는 내가 고른 자리다 — 통과하면 흔들어야 한다")
            print("=" * 122)
            _산33 = []
            for _라33, _둘33, _비33, _자33 in _고를30:
                _든33 = _칸든30(_라33)
                if _든33 is None:
                    continue
                _칸33 = [x for x in 사건 if _든33(x)]
                _잉 = sorted(z for z in (x.get("잉여금") for x in _칸33) if z is not None)
                _부 = sorted(z for z in (x.get("부채") for x in _칸33) if z is not None)
                _대 = sorted(z for z in (x.get("대금억") for x in _칸33) if z is not None)
                if not (_잉 and _부 and _대):
                    continue
                _잉컷, _부컷, _대컷 = _잉[int(len(_잉) * .3)], _부[int(len(_부) * .7)], _대[int(len(_대) * .2)]

                def _문33(x, a=_잉컷, b=_부컷, c=_대컷, 든=_든33):
                    if not 든(x):
                        return False
                    _i, _p = x.get("잉여금"), x.get("부채")
                    if _i is None or _p is None or _i < a or _p > b or x.get("흑자") != 1.0:
                        return False
                    return (x.get("대금억") or 0) >= c

                _통33 = [x for x in _칸33 if _문33(x) and x.get("_20") is not None]
                if len(_통33) < 3000:
                    continue
                _바33 = sum(1 for x in _통33 if x["_20"] > 0) / len(_통33) * 100
                _재신호33 = [(k + "↓", f, "아래") for k, f in _재전부30] + [(k + "↑", f, "위") for k, f in _재전부30]
                _문턱33, _좋33 = {}, []
                for _이, _꺼, _방 in _재신호33:
                    _v = sorted(z for z in (_꺼(x) for x in _통33) if z is not None)
                    if len(_v) < len(_통33) * .25 or len(set(_v[::max(1, len(_v) // 2000)])) < 20:
                        continue
                    _문턱33[_이] = _v[len(_v) // 5] if _방 == "아래" else _v[len(_v) * 4 // 5]
                for _이, _꺼, _방 in _재신호33:
                    _컷 = _문턱33.get(_이)
                    if _컷 is None:
                        continue
                    _z = [x for x in _통33 if _꺼(x) is not None and ((_꺼(x) <= _컷) if _방 == "아래" else (_꺼(x) >= _컷))]
                    if len(_z) < 300:
                        continue
                    _w = sum(1 for x in _z if x["_20"] > 0) / len(_z) * 100
                    _a = [x for x in _z if 날[x["인"] - 1][:4] <= "2018"]
                    _b = [x for x in _z if 날[x["인"] - 1][:4] > "2018"]
                    if len(_a) < 100 or len(_b) < 100:
                        continue
                    _wa = sum(1 for x in _a if x["_20"] > 0) / len(_a) * 100
                    _wb = sum(1 for x in _b if x["_20"] > 0) / len(_b) * 100
                    if (_w - _바33) < 2.0 or (_wa - _바33) * (_wb - _바33) <= 0:
                        continue
                    _좋33.append((_w - _바33, _이))
                _좋33.sort(reverse=True)
                if not _좋33:
                    continue
                _쓸33 = tuple(z[1] for z in _좋33[:2]) if _둘33 else (_좋33[0][1],)
                _갭 = sorted(z for z in (x.get("갭") for x in _통33) if z is not None)
                _갭5 = _갭[int(len(_갭) * .05)] if len(_갭) > 1000 else None
                _갭10 = _갭[int(len(_갭) * .10)] if len(_갭) > 1000 else None

                def _띠규칙33(x, 쓸=_쓸33, 문=_문33, 표=dict(_문턱33), 재=tuple(_재신호33)):
                    if not 문(x):
                        return False
                    for _이, _꺼, _방 in 재:
                        if _이 not in 쓸:
                            continue
                        _v = _꺼(x)
                        if _v is None or ((_v > 표[_이]) if _방 == "아래" else (_v < 표[_이])):
                            return False
                    return True

                _도전33 = (lambda x, f=_띠규칙33: _바탕30(x) or f(x))        # [견줌]
                _새날33 = len({x["인"] for x in 사건 if _띠규칙33(x)} - {x["인"] for x in _덤프})
                print(f"\n     ══ [{_라33} · {'+'.join(_쓸33)}] 칸 갭 5분위 {_갭5} · 10분위 {_갭10} · 켜지는 새 날 {_새날33} ══")
                print(f"     {'상대갭':<14}{'중복금지':<8}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
                for _라g, _g in (("Ⓗ -3.5 그대로", None), ("칸 5분위", _갭5), ("칸 10분위", _갭10)):
                    if _라g != "Ⓗ -3.5 그대로" and _g is None:
                        continue
                    for _중 in (False, True):
                        _옵33 = dict(_열기30)
                        if _g is not None and _크기하한 >= 2000e8 and R.상대갭문턱:          # [견줌]
                            _옵33["갭무름"] = [(int(_크기하한 / 1e8), _g / R.상대갭문턱)]   # [견줌]
                        if _중:
                            _옵33["중복금지"] = True
                        _r33 = 시뮬(_c(_도전33, **_옵33), 묶2=_합묶)
                        if not _r33:
                            continue
                        # ⚠️ 중복금지를 켜면 바탕도 같은 설정으로 견줘야 공평하다
                        _기33 = 시뮬(_c(_바탕30, **{**_열기30, **({"중복금지": True} if _중 else {})}), 묶2=_합묶) if _중 else _기30
                        _ok33 = (_r33["산"] > _기33["산"], _r33["끝"] > _기33["끝"], _r33["낙"] > 낙폭기준)
                        print(f"     {_라g:<14}{('켬' if _중 else '끔'):<8}{_r33['끝']:>16,.0f}"
                              f"{_r33['끝'] / _기33['끝'] * 100:>8.0f}%{_r33['낙']:>7.1f}%{_r33['산']:>7}  "
                              + ("✅ 셋 다" if all(_ok33) else "❌")
                              + (f"  (바탕도 중복금지: {_기33['끝']:,.0f})" if _중 else ""))
                        if all(_ok33):
                            _a0 = 시뮬(_c(_바탕30, **{k: v for k, v in _옵33.items() if k != "갭무름"}), 시작년="2010", 끝년="2020", 묶2=_합묶)
                            _a1 = 시뮬(_c(_도전33, **_옵33), 시작년="2010", 끝년="2020", 묶2=_합묶)
                            _b0 = 시뮬(_c(_바탕30, **{k: v for k, v in _옵33.items() if k != "갭무름"}), 시작년="2021", 끝년="2026", 시드=_a0["끝"], 묶2=_합묶) if _a0 else None
                            _b1 = 시뮬(_c(_도전33, **_옵33), 시작년="2021", 끝년="2026", 시드=_a1["끝"], 묶2=_합묶) if _a1 else None
                            if _a0 and _a1 and _b0 and _b1:
                                _앞d = (_a1["끝"] / _a0["끝"] - 1) * 100
                                _뒤d = (_b1["끝"] / _b0["끝"] - 1) * 100
                                _걷ok = _앞d > 0.1 and _뒤d > 0.1
                                print(f"        증분 걷기 — 앞 {_앞d:+.1f}% · 뒤 {_뒤d:+.1f}%  "
                                      + ("✅ 둘 다 늘렸다" if _걷ok else "❌"))
                                if _걷ok:
                                    _산33.append((_라33, _쓸33, _라g, _중, _r33, _새날33))
            print(f"\n     ══ **[{_띠이름30}] 세 관문(셋 다 + 증분 걷기)을 넘은 것 {len(_산33)}개** ══")
            for _라33, _쓸33, _라g, _중, _r33, _새날33 in sorted(_산33, key=lambda t: -t[4]["끝"]):
                print(f"       {_라33} · {'+'.join(_쓸33)} · 상대갭 {_라g} · 중복금지 {'켬' if _중 else '끔'}"
                      f"  {_r33['끝']:,.0f}원 ({_r33['끝'] / _기30['끝'] * 100:.0f}%) · 낙폭 {_r33['낙']:.1f}% · 산 것 {_r33['산']} · 새 날 {_새날33}")
            print("=" * 122)

        # ══ ⭐⭐ Q-31 — 통과 칸의 문턱 자리를 흔들고, 파는 규칙을 그 칸에서 (소형 300~800억) ══
        # ⭐ 2026-09-22 23:15 — Q-33 통과분(상대갭 Ⓗ -3.5 · 중복금지 끔)도 흔든다.
        #    Q-31 은 _열기30(갭무름 없음 = 전부 -3.5)으로 재니 그 조건과 딱 맞는다
        _흔들31 = list(_산30) + [(_라, _쓸, _r, _새) for _라, _쓸, _라g, _중, _r, _새 in _산33
                                 if _라g == "Ⓗ -3.5 그대로" and not _중]
        if os.environ.get("Q31") and _흔들31:
            print("\n" + "=" * 122)
            print("  ── Q-31 ⭐⭐ **통과 칸 흔들기 — 문턱 자리 · 파는 규칙** ──")
            print("     자르는 자리(30·70·20분위)는 내가 고른 것이다 — 옆으로 옮겨도 서야 우연이 아니다")
            print(f"     흔들 칸 {len(_흔들31)}개 (Q-30 통과 {len(_산30)} + Q-33 통과 {len(_흔들31) - len(_산30)})")
            print("=" * 122)
            for _라31, _쓸31, _r0_31, _새날31 in _흔들31:
                _든31 = _칸든30(_라31)
                _칸31 = [x for x in 사건 if _든31(x)]
                _잉 = sorted(z for z in (x.get("잉여금") for x in _칸31) if z is not None)
                _부 = sorted(z for z in (x.get("부채") for x in _칸31) if z is not None)
                _대 = sorted(z for z in (x.get("대금억") for x in _칸31) if z is not None)
                print(f"\n     ══ [{_라31} · {'+'.join(_쓸31)}] 얹은 결과 {_r0_31['끝']:,.0f}원 ({_r0_31['끝'] / _기30['끝'] * 100:.0f}%) ══")
                print(f"     {'변형':<34}{'끝 자산':>16}{'바탕의%':>9}{'낙폭':>8}{'산 것':>7}{'새 날':>7}  판정")
                _변형들 = []
                for _q잉 in (0.20, 0.30, 0.40):
                    _변형들.append((f"잉여금 {int(_q잉 * 100)}분위", (_q잉, 0.70, 0.20, 0.20)))
                for _q부 in (0.60, 0.80):
                    _변형들.append((f"부채 {int(_q부 * 100)}분위", (0.30, _q부, 0.20, 0.20)))
                for _q대 in (0.10, 0.30):
                    _변형들.append((f"대금 {int(_q대 * 100)}분위", (0.30, 0.70, _q대, 0.20)))
                for _q신 in (0.15, 0.25):
                    _변형들.append((f"신호 {int(_q신 * 100)}분위", (0.30, 0.70, 0.20, _q신)))
                for _라v, (_q잉, _q부, _q대, _q신) in _변형들:
                    _잉컷, _부컷, _대컷 = _잉[int(len(_잉) * _q잉)], _부[int(len(_부) * _q부)], _대[int(len(_대) * _q대)]

                    def _문31(x, a=_잉컷, b=_부컷, c=_대컷, 든=_든31):
                        if not 든(x):
                            return False
                        _i, _p = x.get("잉여금"), x.get("부채")
                        if _i is None or _p is None or _i < a or _p > b or x.get("흑자") != 1.0:
                            return False
                        return (x.get("대금억") or 0) >= c

                    _통31 = [x for x in _칸31 if _문31(x) and x.get("_20") is not None]
                    _재신호31 = [(k + "↓", f, "아래") for k, f in _재전부30] + [(k + "↑", f, "위") for k, f in _재전부30]
                    _표31 = {}
                    for _이, _꺼, _방 in _재신호31:
                        if _이 not in _쓸31:
                            continue
                        _v = sorted(z for z in (_꺼(x) for x in _통31) if z is not None)
                        if not _v:
                            continue
                        _표31[_이] = _v[int(len(_v) * _q신)] if _방 == "아래" else _v[int(len(_v) * (1 - _q신))]
                    if len(_표31) < len(_쓸31):
                        print(f"     {_라v:<34} 문턱을 못 냈다")
                        continue

                    def _띠규칙31(x, 쓸=_쓸31, 문=_문31, 표=dict(_표31), 재=tuple(_재신호31)):
                        if not 문(x):
                            return False
                        for _이, _꺼, _방 in 재:
                            if _이 not in 쓸:
                                continue
                            _v = _꺼(x)
                            if _v is None or ((_v > 표[_이]) if _방 == "아래" else (_v < 표[_이])):
                                return False
                        return True

                    _도전31 = (lambda x, f=_띠규칙31: _바탕30(x) or f(x))        # [견줌]
                    _r31 = 시뮬(_c(_도전31, **_열기30), 묶2=_합묶)
                    if not _r31:
                        continue
                    _ok31 = (_r31["산"] > _기30["산"], _r31["끝"] > _기30["끝"], _r31["낙"] > 낙폭기준)
                    _새31 = len({x["인"] for x in 사건 if _띠규칙31(x)} - {x["인"] for x in _덤프})
                    print(f"     {_라v:<34}{_r31['끝']:>16,.0f}{_r31['끝'] / _기30['끝'] * 100:>8.0f}%"
                          f"{_r31['낙']:>7.1f}%{_r31['산']:>7}{_새31:>7}  " + ("✅" if all(_ok31) else "❌"))

                # 파는 규칙 — 그 칸 규칙(원래 문턱)을 얹은 채로 몫들만 바꿔 본다
                _잉컷, _부컷, _대컷 = _잉[int(len(_잉) * .3)], _부[int(len(_부) * .7)], _대[int(len(_대) * .2)]

                def _문31b(x, a=_잉컷, b=_부컷, c=_대컷, 든=_든31):
                    if not 든(x):
                        return False
                    _i, _p = x.get("잉여금"), x.get("부채")
                    if _i is None or _p is None or _i < a or _p > b or x.get("흑자") != 1.0:
                        return False
                    return (x.get("대금억") or 0) >= c

                _통31b = [x for x in _칸31 if _문31b(x) and x.get("_20") is not None]
                _재신호31b = [(k + "↓", f, "아래") for k, f in _재전부30] + [(k + "↑", f, "위") for k, f in _재전부30]
                _표31b = {}
                for _이, _꺼, _방 in _재신호31b:
                    if _이 not in _쓸31:
                        continue
                    _v = sorted(z for z in (_꺼(x) for x in _통31b) if z is not None)
                    if _v:
                        _표31b[_이] = _v[len(_v) // 5] if _방 == "아래" else _v[len(_v) * 4 // 5]

                def _띠규칙31b(x, 쓸=_쓸31, 문=_문31b, 표=dict(_표31b), 재=tuple(_재신호31b)):
                    if not 문(x):
                        return False
                    for _이, _꺼, _방 in 재:
                        if _이 not in 쓸:
                            continue
                        _v = _꺼(x)
                        if _v is None or ((_v > 표[_이]) if _방 == "아래" else (_v < 표[_이])):
                            return False
                    return True

                _도전31b = (lambda x, f=_띠규칙31b: _바탕30(x) or f(x))       # [견줌]
                print(f"\n     ── 파는 규칙 (얹은 채로 · ⚠️ 몫은 Ⓗ 사건에도 같이 적용된다 — 실전이 그렇다) ──")
                print(f"     {'몫들':<34}{'바탕(같은 몫)':>16}{'얹음':>16}{'차이':>8}{'낙폭':>8}")
                for _라m, _몫 in (("지금 40%@+15/40일 · 60%@+40/90일", None),
                                  ("40%@+10/40 · 60%@+30/90", ((0.4, 10.0, 40), (0.6, 30.0, 90))),
                                  ("40%@+20/40 · 60%@+50/90", ((0.4, 20.0, 40), (0.6, 50.0, 90))),
                                  ("40%@+15/60 · 60%@+40/120", ((0.4, 15.0, 60), (0.6, 40.0, 120))),
                                  ("100%@+20/60", ((1.0, 20.0, 60),))):
                    _옵m = dict(_열기30)
                    if _몫 is not None:
                        _옵m["나눔"] = _몫
                    _a = 시뮬(_c(_바탕30, **_옵m), 묶2=_합묶)
                    _b = 시뮬(_c(_도전31b, **_옵m), 묶2=_합묶)
                    if _a and _b:
                        print(f"     {_라m:<34}{_a['끝']:>16,.0f}{_b['끝']:>16,.0f}"
                              f"{(_b['끝'] / _a['끝'] - 1) * 100:>+7.1f}%{_b['낙']:>7.1f}%")
            print("=" * 122)
        return 0

    # ══ ⭐⭐⭐ **Q-19 (이어서) 띠마다 제 문턱으로 규칙을 만든다** ══
    #    ⚠️ 이 한 줄은 **막개(check_lab_ready ④)를 위한 절 경계**다.
    #    Q-19 의 머리는 위에 있는데 Q-22~Q-27 을 머리와 본체 사이에 끼워 넣는 바람에
    #    본체가 제 머리를 잃고 마지막에 끼운 절에 딸려 들어갔다 (2026-09-22).
    #    본체가 「시총억」을 가르니 그 절이 통째로 띠 절로 찍혔다.
    #    ⇒ 머리를 돌려준다. 뒤에 절을 더 끼울 때도 **이 줄 앞에** 끼운다.
    # ── Q-19a 띠마다 문턱·상대갭을 **그 띠에서** 낸다 ──
    print("\n  ── Q-19a **띠마다 제 문턱** (소형 값을 안 쓴다) ──")
    _문19, _갭19 = {}, {}
    for _라19, _lo, _hi in _띠19:
        _칸 = [x for x in 사건 if _lo <= (x.get("시총억") or 0) < _hi]
        if len(_칸) < 3000:
            print(f"     {_라19:<18}{len(_칸):>9,}건  표본 부족")
            continue
        _줄 = f"     {_라19:<18}{len(_칸):>9,}건  "
        for _이름, _꺼, _방 in _재19:
            _v = sorted(z for z in (_꺼(x) for x in _칸) if z is not None)
            if len(_v) < len(_칸) * 0.25:
                continue
            _문19[(_라19, _이름)] = (_v[len(_v) // 5] if _방 == "아래"
                                     else _v[len(_v) * 4 // 5])
            _줄 += f"{_이름} {_문19[(_라19, _이름)]:,.2f}  "
        # ⭐ 상대갭도 **그 띠 분포**에서 (소형 -3.5%p 를 안 쓴다)
        _g = sorted(z for z in (x.get("갭") for x in _칸) if z is not None)
        if len(_g) > 1000:
            _갭19[_라19] = _g[int(len(_g) * 0.20)]
            _줄 += f"| 갭 아래20% {_갭19[_라19]:,.2f}"
        print(_줄)

    # ⭐ **그 띠에서 센 재료를 자료가 고른다** (2026-09-21) — 내가 안 고른다.
    #    바탕 대비 +2%p 넘고 **앞뒤가 같은 방향**인 것만 (건수 300 이상)
    print("\n  ── Q-19a-2 **띠마다 어느 재료가 센가** (자료가 고른다) ──")
    _고른19 = {}
    for _라19, _lo, _hi in _띠19:
        _칸 = [x for x in 사건 if _lo <= (x.get("시총억") or 0) < _hi
               and x.get("_20") is not None]
        if len(_칸) < 3000:
            print(f"     {_라19:<18}표본 부족 ({len(_칸):,})")
            continue
        _바 = sum(1 for x in _칸 if x["_20"] > 0) / len(_칸) * 100
        _반 = len(_칸) // 2
        _좋 = []
        for _이름, _꺼, _방 in _재19:
            _컷 = _문19.get((_라19, _이름))
            if _컷 is None:
                continue
            _z = [x for x in _칸 if (_꺼(x) is not None)
                  and ((_꺼(x) <= _컷) if _방 == "아래" else (_꺼(x) >= _컷))]
            if len(_z) < 300:
                continue
            _w = sum(1 for x in _z if x["_20"] > 0) / len(_z) * 100
            _앞 = [x for x in _z if 사건.index(x) < _반] if len(_z) < 4000 else None
            # 앞뒤는 인덱스 대신 **해**로 가른다 (index 가 느리다)
            _a = [x for x in _z if 날[x["인"] - 1][:4] <= "2018"]
            _b = [x for x in _z if 날[x["인"] - 1][:4] > "2018"]
            if len(_a) < 100 or len(_b) < 100:
                continue
            _wa = sum(1 for x in _a if x["_20"] > 0) / len(_a) * 100
            _wb = sum(1 for x in _b if x["_20"] > 0) / len(_b) * 100
            if (_w - _바) < 2.0:
                continue
            if (_wa - _바) * (_wb - _바) <= 0:      # 앞뒤가 다른 방향이면 버린다
                continue
            _좋.append((_w - _바, _이름, _w, len(_z)))
        _좋.sort(reverse=True)
        _고른19[_라19] = [z[1] for z in _좋[:3]]
        _글 = " · ".join(f"{r}{d:+.1f}({w:.1f}%·{n:,})" for d, r, w, n in _좋[:3]) or "없음"
        print(f"     {_라19:<18}바탕 {_바:>5.1f}%  {_글}")
    print("     ⇒ 바탕 +2%p 넘고 **앞뒤 같은 방향**인 것만. 띠마다 다른 재료가 뽑힌다")

    # ── Q-19b 띠 규칙 **혼자** ──
    print("\n  ── Q-19b **띠 규칙 혼자** (소형 없이 그 띠만 산다) ──")

    def _띠규칙(x, 라, lo, hi, 쓸것):
        _s = x.get("시총억") or 0
        if not (lo <= _s < hi):
            return False
        if not (재무통과(x) and 대금통과(x)):
            return False
        for _이름, _꺼, _방 in _재19:
            if _이름 not in 쓸것:
                continue
            _컷 = _문19.get((라, _이름))
            if _컷 is None:
                return False
            _v = _꺼(x)
            if _v is None:
                return False
            if (_v > _컷) if _방 == "아래" else (_v < _컷):
                return False
        return True

    _기19 = 시뮬(_c(_H))     # [견줌] 표에만 쓴다 — 아래 a·b 규칙은 이걸 안 부른다
    print(f"     {'설정':<34}{'끝 자산':>17}{'낙폭':>8}{'산 것':>7}{'2천억↑ 산':>10}")
    print(f"     {'[견줌] 소형 규칙 Ⓗ':<34}{_기19['끝']:>16,.0f}원"
          f"{_기19['낙']:>7.1f}%{_기19['산']:>7}{(_기19.get('큰산') or 0):>10}")
    _잰19 = {}
    for _라19, _lo, _hi in _띠19:
        _뽑 = _고른19.get(_라19) or []
        if not _뽑:
            continue
        # ⭐ 자료가 고른 것에서 하나씩 · 둘씩 (셋은 너무 좁다)
        _쓸것들 = [(_뽑[0],)]
        if len(_뽑) >= 2:
            _쓸것들 += [(_뽑[0], _뽑[1]), (_뽑[1],)]
        if len(_뽑) >= 3:
            _쓸것들 += [(_뽑[0], _뽑[2])]
        for _쓸 in _쓸것들:
            _표 = f"{_라19} · {'+'.join(_쓸)}"
            _fn = (lambda x, a=_라19, b=_lo, c=_hi, d=_쓸: _띠규칙(x, a, b, c, d))
            # ⭐ 상대갭도 그 띠 값으로
            _옵 = {"상대갭": _갭19.get(_라19, _밑상대갭)}   # [견줌] 그 띠 갭이 없을 때만 소형 값
            _r = 시뮬(_c(_fn, **_옵))
            if not _r:
                continue
            _잰19[_표] = (_r, _fn, _옵)
            print(f"     {_표:<34}{_r['끝']:>16,.0f}원"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}{(_r.get('큰산') or 0):>10}")
    print("     ⚠️ 여기 숫자는 **그 띠만 사는** 것이다 — 소형과 직접 견주면 안 된다")
    print("        (기회 수가 다르다). 아래 d 가 반영을 정하는 물음이다")

    # ── Q-19c 띠 규칙끼리 묶으면 ──
    print("\n  ── Q-19c **띠 규칙끼리 묶으면** (중형+대형+초대형 · 소형 없이) ──")
    _좋은19 = sorted(_잰19.items(), key=lambda t: -t[1][0]["끝"])[:3]
    if _좋은19:
        _묶 = [v[1] for _, v in _좋은19]
        _갭묶 = min((v[2]["상대갭"] for _, v in _좋은19), default=_밑상대갭)   # [견줌] 대비책
        _r = 시뮬(_c(lambda x, fs=_묶: any(f(x) for f in fs), 상대갭=_갭묶))
        if _r:
            print(f"     {'위 셋을 OR 로':<34}{_r['끝']:>16,.0f}원"
                  f"{_r['낙']:>7.1f}%{_r['산']:>7}{(_r.get('큰산') or 0):>10}")

    # ── Q-19d [견줌] 소형 OR 띠 규칙 — **반영을 정하는 물음** ──
    print("\n  ── Q-19d **[견줌] 소형 OR 띠 규칙** — 반영을 정할 때의 물음 ──")
    print("     (소형을 버리지 않으려면 이 꼴이어야 한다. 셋 다를 넘는지 본다)")
    print(f"     {'설정':<34}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}"
          f"{'2천억↑ 산':>10}  판정")
    _산19 = []
    for _표, (_r0, _fn19, _옵19) in _좋은19:
        _합 = (lambda x, f=_fn19: _H(x) or f(x))   # [견줌] 소형 OR 띠 — 반영을 정하는 물음
        _r = 시뮬(_c(_합))
        if not _r:
            continue
        _ok = (_r["산"] > _기19["산"], _r["끝"] > _기19["끝"], _r["낙"] > 낙폭기준)
        if all(_ok):
            _산19.append((_표, _합))
        print(f"     {('소형 OR ' + _표):<34}{_r['끝']:>16,.0f}원"
              f"{_r['끝'] / _기19['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}"
              f"{(_r.get('큰산') or 0):>10}  "
              + ("✅ 셋 다" if all(_ok) else "❌"))
    if _좋은19:
        _묶합 = (lambda x, fs=[v[1] for _, v in _좋은19]: _H(x) or any(f(x) for f in fs))   # [견줌]
        _r = 시뮬(_c(_묶합))
        if _r:
            _ok = (_r["산"] > _기19["산"], _r["끝"] > _기19["끝"], _r["낙"] > 낙폭기준)
            if all(_ok):
                _산19.append(("소형 OR 띠 셋 다", _묶합))
            print(f"     {'소형 OR 띠 셋 다':<34}{_r['끝']:>16,.0f}원"
                  f"{_r['끝'] / _기19['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}"
                  f"{(_r.get('큰산') or 0):>10}  "
                  + ("✅ 셋 다" if all(_ok) else "❌"))

    for _표, _fn in _산19:
        print(f"\n     ── [{_표}] 해마다 + 걷기 ──")
        _차19, _낙19 = [], []
        for _y19 in range(2016, 2027):
            _a = 시뮬(_c(_H), 시작년=str(_y19), 끝년=str(_y19))
            _b = 시뮬(_c(_fn), 시작년=str(_y19), 끝년=str(_y19))
            if not _a or not _b:
                continue
            _차19.append((_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0)
            _낙19.append(_b["낙"] - _a["낙"])
        print("        해마다: " + _해마다판정(_차19, _낙19)[0])
        _걷기찍기(_걷기(_fn))
    if not _산19:
        print("\n     ⇒ 띠 전용 규칙을 더해도 **셋 다를 넘는 것이 없다**")
    print("=" * 122)
    # ══ ⭐⭐⭐ **Q-20 섹터별 규칙을 따로 만든다** (2026-09-21 · 사용자) ══
    #    사용자: 「시총 뿐만 아니라 섹터별로도 지금과 같이 테스트 해봤어?」
    #    섹터는 **재료를 재는 데까지만** 했다 — 규칙을 만들어 돈으로 잰 적이 없다.
    #    CJUDGE 가 14개 업종에서 센 재료를 찍어 놓고 거기서 멈췄다:
    #        금융 45.2%  미국선거전5 +12.9 · 시장낙폭 +9.5 · 자사주직후 +8.7
    #        제약 42.9%  신저가반등 +9.8   ← 다른 업종에 없는 재료
    #        건설 43.2%  미국선거전5 +21.4 ← 제일 크다
    #    ⚠️ 소형 문턱을 안 쓴다. Q-19(규모)와 **같은 방식**이다
    if _ONLY in ("", "Q20"):
        print("\n" + "=" * 122)
        print("  ── Q-20 ⭐⭐⭐ **섹터별 규칙을 따로** ──")
        print("     섹터는 재료를 재는 데까지만 했다 — **규칙을 만들어 돈으로 잰 적이 없다**")
        print("     재료·문턱·상대갭 **전부 그 업종 분포**에서 낸다. 소형 값을 안 쓴다")
        print("=" * 122)

        # 사건이 많은 업종만 (표본이 적으면 우연이 뽑힌다)
        _섹셈 = {}
        for x in 사건:
            _n = x.get("섹터")
            if _n:
                _섹셈[_n] = _섹셈.get(_n, 0) + 1
# ⚠️ 8만은 너무 높았다 — 12개를 잰다고 해놓고 **2개만** 쟀다 (2026-09-21 22:33).
        #    이 판의 사건은 72만 건이고 섹터가 67만에 붙는다. 업종 74개면 평균 9천 건이다.
        #    2만으로 낮춘다. 그래도 표본이 적은 업종은 아래 「표본 부족」에서 다시 걸린다
        _섹들 = [k for k, v in sorted(_섹셈.items(), key=lambda t: -t[1]) if v >= 20000][:14]
        print(f"\n     잴 업종 {len(_섹들)}개 (사건 8만 건 이상): {', '.join(_섹들)}")

        # ── Q-20a 업종마다 문턱·상대갭을 그 업종에서 ──
        print("\n  ── Q-20a **업종마다 제 문턱** ──")
        _문20, _갭20, _고른20 = {}, {}, {}
        for _섹 in _섹들:
            _칸 = [x for x in 사건 if x.get("섹터") == _섹 and x.get("_20") is not None]
            if len(_칸) < 20000:
                continue
            _바 = sum(1 for x in _칸 if x["_20"] > 0) / len(_칸) * 100
            for _이름, _꺼, _방 in _재19:
                _v = sorted(z for z in (_꺼(x) for x in _칸) if z is not None)
                if len(_v) < len(_칸) * 0.25:
                    continue
                _문20[(_섹, _이름)] = (_v[len(_v) // 5] if _방 == "아래"
                                       else _v[len(_v) * 4 // 5])
            _g = sorted(z for z in (x.get("갭") for x in _칸) if z is not None)
            if len(_g) > 1000:
                _갭20[_섹] = _g[int(len(_g) * 0.20)]
            # ⭐ 그 업종에서 센 재료를 **자료가 고른다**
            _좋 = []
            for _이름, _꺼, _방 in _재19:
                _컷 = _문20.get((_섹, _이름))
                if _컷 is None:
                    continue
                _z = [x for x in _칸 if (_꺼(x) is not None)
                      and ((_꺼(x) <= _컷) if _방 == "아래" else (_꺼(x) >= _컷))]
                if len(_z) < 300:
                    continue
                _w = sum(1 for x in _z if x["_20"] > 0) / len(_z) * 100
                _a = [x for x in _z if 날[x["인"] - 1][:4] <= "2018"]
                _b = [x for x in _z if 날[x["인"] - 1][:4] > "2018"]
                if len(_a) < 100 or len(_b) < 100:
                    continue
                _wa = sum(1 for x in _a if x["_20"] > 0) / len(_a) * 100
                _wb = sum(1 for x in _b if x["_20"] > 0) / len(_b) * 100
                if (_w - _바) < 2.0 or (_wa - _바) * (_wb - _바) <= 0:
                    continue
                _좋.append((_w - _바, _이름, _w, len(_z)))
            _좋.sort(reverse=True)
            _고른20[_섹] = [z[1] for z in _좋[:2]]
            _글 = " · ".join(f"{r}{d:+.1f}({w:.1f}%·{n:,})" for d, r, w, n in _좋[:2]) or "없음"
            print(f"     {_섹[:14]:<16}{len(_칸):>9,}건  바탕 {_바:>5.1f}%  {_글}")
        print("     ⇒ 바탕 +2%p 넘고 앞뒤 같은 방향인 것만. 업종마다 다른 재료가 뽑힌다")

        # ── Q-20b 업종 규칙 혼자 ──
        print("\n  ── Q-20b **업종 규칙 혼자** (그 업종만 산다) ──")

        def _섹규칙20(x, 섹, 쓸것):
            if x.get("섹터") != 섹:
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            for _이름, _꺼, _방 in _재19:
                if _이름 not in 쓸것:
                    continue
                _컷 = _문20.get((섹, _이름))
                if _컷 is None:
                    return False
                _v = _꺼(x)
                if _v is None:
                    return False
                if (_v > _컷) if _방 == "아래" else (_v < _컷):
                    return False
            return True

        _기20 = 시뮬(_c(_H))     # [견줌] 표에만 쓴다
        print(f"     {'설정':<30}{'끝 자산':>17}{'낙폭':>8}{'산 것':>7}")
        print(f"     {'[견줌] 지금 규칙 Ⓗ':<30}{_기20['끝']:>16,.0f}원"
              f"{_기20['낙']:>7.1f}%{_기20['산']:>7}")
        _잰20 = {}
        for _섹 in _섹들:
            _뽑 = _고른20.get(_섹) or []
            if not _뽑:
                continue
            for _쓸 in ([(_뽑[0],)] + ([(_뽑[0], _뽑[1])] if len(_뽑) >= 2 else [])):
                _표 = f"{_섹[:12]} · {'+'.join(_쓸)}"
                _fn = (lambda x, a=_섹, b=_쓸: _섹규칙20(x, a, b))
                _옵 = {"상대갭": _갭20.get(_섹, _밑상대갭)}   # [견줌] 그 업종 갭이 없을 때만
                _r = 시뮬(_c(_fn, **_옵))
                if not _r:
                    continue
                _잰20[_표] = (_r, _fn, _옵)
                print(f"     {_표:<30}{_r['끝']:>16,.0f}원{_r['낙']:>7.1f}%{_r['산']:>7}")

        # ── Q-20c [견줌] 지금 규칙 OR 업종 규칙 ──
        print("\n  ── Q-20c **[견줌] 지금 규칙 OR 업종 규칙** — 반영을 정하는 물음 ──")
        _좋은20 = sorted(_잰20.items(), key=lambda t: -t[1][0]["끝"])[:5]
        print(f"     {'설정':<30}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        _산20 = []
        for _표, (_r0, _fn20, _옵20) in _좋은20:
            _합 = (lambda x, f=_fn20: _H(x) or f(x))   # [견줌] 소형 OR 업종
            _r = 시뮬(_c(_합))
            if not _r:
                continue
            _ok = (_r["산"] > _기20["산"], _r["끝"] > _기20["끝"], _r["낙"] > 낙폭기준)
            if all(_ok):
                _산20.append((_표, _합))
            print(f"     {('Ⓗ OR ' + _표):<30}{_r['끝']:>16,.0f}원"
                  f"{_r['끝'] / _기20['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
                  + ("✅ 셋 다" if all(_ok) else "❌"))
        if _좋은20:
            _묶20 = (lambda x, fs=[v[1] for _, v in _좋은20]: _H(x) or any(f(x) for f in fs))   # [견줌]
            _r = 시뮬(_c(_묶20))
            if _r:
                _ok = (_r["산"] > _기20["산"], _r["끝"] > _기20["끝"], _r["낙"] > 낙폭기준)
                if all(_ok):
                    _산20.append(("Ⓗ OR 업종 다섯", _묶20))
                print(f"     {'Ⓗ OR 업종 다섯':<30}{_r['끝']:>16,.0f}원"
                      f"{_r['끝'] / _기20['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
                      + ("✅ 셋 다" if all(_ok) else "❌"))

        for _표, _fn in _산20:
            print(f"\n     ── [{_표}] 해마다 + 걷기 ──")
            _차20, _낙20 = [], []
            for _y20 in range(2016, 2027):
                _a = 시뮬(_c(_H), 시작년=str(_y20), 끝년=str(_y20))
                _b = 시뮬(_c(_fn), 시작년=str(_y20), 끝년=str(_y20))
                if not _a or not _b:
                    continue
                _차20.append((_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0)
                _낙20.append(_b["낙"] - _a["낙"])
            print("        해마다: " + _해마다판정(_차20, _낙20)[0])
            _걷기찍기(_걷기(_fn))
        if not _산20:
            print("\n     ⇒ 업종 전용 규칙을 더해도 **셋 다를 넘는 것이 없다**")
        print("=" * 122)

    # ══ ⭐⭐⭐ **Q-21 규모·섹터 말고 다른 기준으로** (2026-09-21 · 사용자) ══
    #    사용자: 「시총별 섹터별 말고 또 다른 구분할만한거 없어?」
    #    안 나눠본 것: 거래 두께 · 변동성 · 주가 수준 · 회전율 · 외국인 지분율
    #    ⚠️ 거래 두께가 특히 중요하다 — 큰 종목이 잘 되는 이유가
    #       **크기 자체인가 거래가 두꺼워서인가**를 갈라야 규모 결과를 해석할 수 있다
    if _ONLY in ("", "Q21"):
        print("\n" + "=" * 122)
        print("  ── Q-21 ⭐⭐⭐ **규모·섹터 말고 다른 기준으로 나눈다** ──")
        print("     거래 두께 · 변동성 · 주가 수준 · 회전율 · 외국인 지분율")
        print("     ⚠️ 거래 두께: 큰 종목이 잘 되는 이유가 **크기 자체인가 거래가 두꺼워서인가**")
        print("     Q-19·Q-20 과 같은 방식 — 재료·문턱·상대갭 전부 그 칸 분포에서")
        print("=" * 122)

        # 나눌 잣대들 — 오분위로 갈라 **아래 20% · 가운데 · 위 20%** 셋씩
        _잣21 = (
            ("거래 두께", lambda x: x.get("대금억")),
            ("변동성", lambda x: x.get("섹시그마")),
            ("주가", lambda x: x.get("원시")),
            ("회전율", lambda x: x.get("회전율")),
            ("외국인 지분율", lambda x: x.get("지분율")),
        )
        _칸21 = []      # (칸이름, 그 칸에 드는 함수)
        print("\n  ── Q-21a **잣대마다 오분위로 가른다** ──")
        for _라21, _꺼21 in _잣21:
            _v = sorted(z for z in (_꺼21(x) for x in 사건) if z is not None)
            if len(_v) < len(사건) * 0.3:
                print(f"     {_라21:<14}값이 {len(_v):,}개뿐 — 건너뜀")
                continue
            _아 = _v[len(_v) // 5]
            _위 = _v[len(_v) * 4 // 5]
            print(f"     {_라21:<14}{len(_v):>10,}개  아래20% ≤ {_아:,.2f} · 위20% ≥ {_위:,.2f}")
            _칸21 += [
                (f"{_라21} 아래20%", (lambda x, f=_꺼21, c=_아: f(x) is not None and f(x) <= c)),
                (f"{_라21} 위20%", (lambda x, f=_꺼21, c=_위: f(x) is not None and f(x) >= c)),
            ]

        # ── Q-21b 칸마다 바탕과 **그 칸에서 센 재료** ──
        print("\n  ── Q-21b **칸마다 바탕과 센 재료** (자료가 고른다) ──")
        _문21, _갭21, _고른21 = {}, {}, {}
        print(f"     {'칸':<20}{'사건':>10}{'바탕':>8}   그 칸에서 센 재료 둘")
        for _라칸, _든21 in _칸21:
            _칸 = [x for x in 사건 if _든21(x) and x.get("_20") is not None]
            if len(_칸) < 20000:
                print(f"     {_라칸:<20}{len(_칸):>10,}   표본 부족")
                continue
            _바 = sum(1 for x in _칸 if x["_20"] > 0) / len(_칸) * 100
            for _이름, _꺼, _방 in _재19:
                _v = sorted(z for z in (_꺼(x) for x in _칸) if z is not None)
                if len(_v) < len(_칸) * 0.25:
                    continue
                _문21[(_라칸, _이름)] = (_v[len(_v) // 5] if _방 == "아래"
                                         else _v[len(_v) * 4 // 5])
            _g = sorted(z for z in (x.get("갭") for x in _칸) if z is not None)
            if len(_g) > 1000:
                _갭21[_라칸] = _g[int(len(_g) * 0.20)]
            _좋 = []
            for _이름, _꺼, _방 in _재19:
                _컷 = _문21.get((_라칸, _이름))
                if _컷 is None:
                    continue
                _z = [x for x in _칸 if (_꺼(x) is not None)
                      and ((_꺼(x) <= _컷) if _방 == "아래" else (_꺼(x) >= _컷))]
                if len(_z) < 300:
                    continue
                _w = sum(1 for x in _z if x["_20"] > 0) / len(_z) * 100
                _a = [x for x in _z if 날[x["인"] - 1][:4] <= "2018"]
                _b = [x for x in _z if 날[x["인"] - 1][:4] > "2018"]
                if len(_a) < 100 or len(_b) < 100:
                    continue
                _wa = sum(1 for x in _a if x["_20"] > 0) / len(_a) * 100
                _wb = sum(1 for x in _b if x["_20"] > 0) / len(_b) * 100
                if (_w - _바) < 2.0 or (_wa - _바) * (_wb - _바) <= 0:
                    continue
                _좋.append((_w - _바, _이름, _w, len(_z)))
            _좋.sort(reverse=True)
            _고른21[_라칸] = [z[1] for z in _좋[:2]]
            _글 = " · ".join(f"{r}{d:+.1f}({w:.1f}%)" for d, r, w, _ in _좋[:2]) or "없음"
            print(f"     {_라칸:<20}{len(_칸):>10,}{_바:>7.1f}%   {_글}")

        # ── Q-21c 칸 전용 규칙 혼자 ──
        print("\n  ── Q-21c **칸 전용 규칙 혼자** ──")

        def _칸규칙21(x, 라칸, 든, 쓸것):
            if not 든(x):
                return False
            if not (재무통과(x) and 대금통과(x)):
                return False
            for _이름, _꺼, _방 in _재19:
                if _이름 not in 쓸것:
                    continue
                _컷 = _문21.get((라칸, _이름))
                if _컷 is None:
                    return False
                _v = _꺼(x)
                if _v is None:
                    return False
                if (_v > _컷) if _방 == "아래" else (_v < _컷):
                    return False
            return True

        _기21 = 시뮬(_c(_H))     # [견줌] 표에만
        print(f"     {'설정':<32}{'끝 자산':>17}{'낙폭':>8}{'산 것':>7}")
        print(f"     {'[견줌] 지금 규칙 Ⓗ':<32}{_기21['끝']:>16,.0f}원"
              f"{_기21['낙']:>7.1f}%{_기21['산']:>7}")
        _잰21 = {}
        for _라칸, _든21 in _칸21:
            _뽑 = _고른21.get(_라칸) or []
            if not _뽑:
                continue
            for _쓸 in ([(_뽑[0],)] + ([(_뽑[0], _뽑[1])] if len(_뽑) >= 2 else [])):
                _표 = f"{_라칸} · {'+'.join(_쓸)}"
                _fn = (lambda x, a=_라칸, b=_든21, c=_쓸: _칸규칙21(x, a, b, c))
                _옵 = {"상대갭": _갭21.get(_라칸, _밑상대갭)}   # [견줌] 그 칸 갭이 없을 때만
                _r = 시뮬(_c(_fn, **_옵))
                if not _r:
                    continue
                _잰21[_표] = (_r, _fn, _옵)
                print(f"     {_표:<32}{_r['끝']:>16,.0f}원{_r['낙']:>7.1f}%{_r['산']:>7}")

        # ── Q-21d [견줌] 지금 규칙 OR 칸 규칙 ──
        print("\n  ── Q-21d **[견줌] 지금 규칙 OR 칸 규칙** — 반영을 정하는 물음 ──")
        _좋은21 = sorted(_잰21.items(), key=lambda t: -t[1][0]["끝"])[:5]
        print(f"     {'설정':<32}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
        _산21 = []
        for _표, (_r0, _fn21, _옵21) in _좋은21:
            _합 = (lambda x, f=_fn21: _H(x) or f(x))   # [견줌] 소형 OR 칸
            _r = 시뮬(_c(_합))
            if not _r:
                continue
            _ok = (_r["산"] > _기21["산"], _r["끝"] > _기21["끝"], _r["낙"] > 낙폭기준)
            if all(_ok):
                _산21.append((_표, _합))
            print(f"     {('Ⓗ OR ' + _표):<32}{_r['끝']:>16,.0f}원"
                  f"{_r['끝'] / _기21['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
                  + ("✅ 셋 다" if all(_ok) else "❌"))

        for _표, _fn in _산21:
            print(f"\n     ── [{_표}] 해마다 + 걷기 ──")
            _차21, _낙21 = [], []
            for _y21 in range(2016, 2027):
                _a = 시뮬(_c(_H), 시작년=str(_y21), 끝년=str(_y21))
                _b = 시뮬(_c(_fn), 시작년=str(_y21), 끝년=str(_y21))
                if not _a or not _b:
                    continue
                _차21.append((_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0)
                _낙21.append(_b["낙"] - _a["낙"])
            print("        해마다: " + _해마다판정(_차21, _낙21)[0])
            _걷기찍기(_걷기(_fn))
        if not _산21:
            print("\n     ⇒ 다른 기준으로 나눠도 **셋 다를 넘는 것이 없다**")
        print("=" * 122)

    # ⭐ ONLY=Q19 면 여기서 끝낸다 — 뒤의 옛 절 200개를 안 돈다 (48분 아낀다)
    if _ONLY in ("Q19", "Q20", "Q21"):
        print("\n  ⭐ ONLY={_ONLY}Q19 — 여기서 끝낸다 (뒤의 옛 절은 건너뛴다)", flush=True)
        return 0

    # ══ ⭐⭐⭐ **Q-13 「빠지는 장엔 더 산다」를 4관문에** (2026-09-21) ══
    #    Q-6 열두 줄이 **전부 낙폭 하나 때문에** 탈락했었다 (-10.5 ~ -10.7%).
    #    사용자가 낙폭 기준을 -12% 로 정하자 넷이 「셋 다」를 넘는다.
    #    **기회도 늘고 돈도 느는 첫 후보들**이다 — 사용자 1순위에 정면으로 맞는다
    print("\n" + "=" * 122)
    print("  ── Q-13 ⭐⭐⭐ **「빠지는 장엔 더 산다」를 4관문에** ──")
    print(f"     낙폭 기준이 {낙폭기준:g}% 가 되면서 Q-6 의 넷이 살아났다")
    print("     ⚠️ **국면을 볼 때만** 좋아져야 뜻이 있다 — 「그냥 늘리기」를 나란히 놓는다")
    print("=" * 122)

    def _빠진장Q13(골):
        for z in 골:
            v = z.get("시장낙폭")
            if v is not None:
                return v <= -5.0
        return False

    _후보13 = [
        ("국면 3 → 6 (비중 .20)", dict(하루상한=(lambda 골: 6 if _빠진장Q13(골) else 3), 비중=0.20)),
        ("국면 4 → 6 (비중 .20)", dict(하루상한=(lambda 골: 6 if _빠진장Q13(골) else 4), 비중=0.20)),
        ("국면 4 → 5 (비중 .20)", dict(하루상한=(lambda 골: 5 if _빠진장Q13(골) else 4), 비중=0.20)),
        ("국면 4 → 10 (비중 .20)", dict(하루상한=(lambda 골: 10 if _빠진장Q13(골) else 4), 비중=0.20)),
        ("[견줌] 그냥 늘 5개", dict(하루상한=5, 비중=0.20)),
        ("[견줌] 그냥 늘 6개", dict(하루상한=6, 비중=0.20)),
    ]
    _기13 = 시뮬(_c(_H))
    print(f"\n     {'설정':<24}{'끝 자산':>17}{'지금의%':>9}{'낙폭':>8}{'산 것':>7}  판정")
    print(f"     {'Ⓗ (지금 · 견줌)':<24}{_기13['끝']:>16,.0f}원{100:>8.0f}%"
          f"{_기13['낙']:>7.1f}%{_기13['산']:>7}")
    _산13 = []
    for _라13, _옵13 in _후보13:
        _r = 시뮬(_c(_H, **_옵13))
        if not _r:
            continue
        _ok = (_r["산"] > _기13["산"], _r["끝"] > _기13["끝"], _r["낙"] > 낙폭기준)
        if all(_ok):
            _산13.append((_라13, _옵13))
        print(f"     {_라13:<24}{_r['끝']:>16,.0f}원"
              f"{_r['끝'] / _기13['끝'] * 100:>8.0f}%{_r['낙']:>7.1f}%{_r['산']:>7}  "
              + ("✅ 셋 다" if all(_ok) else "❌"))

    for _라13, _옵13 in _산13:
        print(f"\n     ── [{_라13}] 해마다 + 걷기 ──")
        _차13, _낙13 = [], []
        for _y13 in range(2016, 2027):
            _a = 시뮬(_c(_H), 시작년=str(_y13), 끝년=str(_y13))
            _b = 시뮬(_c(_H, **_옵13), 시작년=str(_y13), 끝년=str(_y13))
            if not _a or not _b:
                continue
            _차13.append((_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0)
            _낙13.append(_b["낙"] - _a["낙"])
        print("        해마다: " + _해마다판정(_차13, _낙13)[0])
        # ⚠️ 견줌은 **옵션 없는 Ⓗ**, 도전은 **옵션 있는 Ⓗ** — 거름은 같고 자리 규칙만 다르다
        _줄13 = []
        _시드a13, _시드b13 = None, None
        for _라W, _시W, _끝W in (("앞 2010~2020", "2010", "2020"), ("뒤 2021~2026", "2021", "2026")):
            _y1 = 시뮬(_c(_H), 시작년=_시W, 끝년=_끝W, 시드=_시드a13)
            _y2 = 시뮬(_c(_H, **_옵13), 시작년=_시W, 끝년=_끝W, 시드=_시드b13)
            if not _y1 or not _y2:
                continue
            _줄13.append((_라W, _y1, _y2, (_y2["끝"] / _y1["끝"] - 1) * 100 if _y1["끝"] > 0 else 0))
            _시드a13, _시드b13 = _y1["끝"], _y2["끝"]
        _걷기찍기(_줄13)
    print("\n     ⚠️ **국면을 보는 줄이 「그냥 늘리기」보다 나아야** 국면이 값을 한 것이다.")
    print("        비슷하면 그냥 「많이 사면 좋다」일 뿐 — 그게 더 단순한 변경이다")
    print("=" * 122)
    print("=" * 122)
    print("=" * 122)
    print("=" * 122)
    # ⭐ 계절 (2026-09-17 00:25 · combo7): 단독 20일 이김 봄 48.0 · 겨울 45.3 · 가을 41.3 · 여름 39.4 (바탕 43.4).
    #    「기존 OR 봄」은 봄엔 아무거나 사게 돼 −82% — OR 로는 못 쓴다. 남은 물음은 **「여름엔 안 산다」(AND)** 가 돈이 되나 —
    #    기회가 1/4 줄므로 사용자 1순위와 어긋나지만, 숫자는 재 둔다
    _둘(f"{_밑글자} AND 여름 빼고", _c(lambda x: _H(x) and _계절표P[날[x["인"] - 1][4:6]] != "여름"))
    _둘(f"{_밑글자} AND 여름·가을 빼고", _c(lambda x: _H(x) and _계절표P[날[x["인"] - 1][4:6]] in ("봄", "겨울")))

    # ── ⭐⭐ **달력 매수·매도** — 「X 계절에 사서 Y 계절 끝에 판다」 (2026-09-17 · 사용자) ──
    print("\n  ── ⭐⭐ **달력 매수·매도** — X 계절에만 사서 Y 계절 끝 거래일에 판다 (견줌 = 지금 · 40/90일 기한) ──")
    print("     「목표유지」 = +15%·+40% 에 먼저 닿으면 팔고 아니면 그날 · 「순수」 = 목표 없이 그날만")
    print(머239)
    _기C = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
    _기C1 = _둘.r1
    _결C = []
    for _사 in ("봄", "여름", "가을", "겨울"):
        for _파 in ("봄", "여름", "가을", "겨울"):
            for _꼴 in (("목표유지",) + (("순수",) if (_사, _파) in (("여름", "봄"), ("겨울", "봄"), ("여름", "가을"), ("봄", "가을")) else ())):
                _f = (lambda x, 사=_사: _H(x) and _계절인가C(x, 사))
                _r = _둘(f"{_사}에 사서 {_파} 끝에 · {_꼴}", _c(_f, 달력매도=(_사, _파, _꼴)))
                _r1 = _둘.r1
                _결C.append((_r1["끝"], f"{_사}→{_파} {_꼴}", _r1["산"], _r1["낙"]))
    _결C.sort(reverse=True)
    print(f"\n     {'조합':<22}{'끝 자산(제약 있음)':>18}{'지금의%':>9}{'산 것':>7}{'낙폭':>8}")
    for _끝, _라, _산, _낙 in _결C[:8]:
        print(f"     {_라:<22}{_끝:>17,.0f}원{_끝 / _기C1['끝'] * 100:>8.0f}%{_산:>7}{_낙:>8.1f}%")
    print("     ⚠️ 사는 계절을 하나로 좁히면 기회가 3/4 줄어든다 — 지금(사계절 · 40/90일)을 넘는 게 있어야 뜻이 있다")
    # ⭐ 빈 날 — 「OR 은 빈 날을 채울 때만 돈이 는다」의 천장. 지금 규칙(제약 있는 칸)이 한 종목도 안 산 날 수 (2026-09-16 · 사용자 ①)
    _기록H = []
    시뮬(_c(_H), 기록=_기록H)
    _산날H = sorted({str(t[0])[:8] for t in _기록H})
    if _산날H:
        _거래일H = [d for d in 날 if _산날H[0] <= d <= _산날H[-1]]
        print(f"     ⭐ 빈 날: 지금 규칙(제약 있음)이 산 날 {len(_산날H):,}일 / 거래일 {len(_거래일H):,}일 "
              f"({_산날H[0]}~{_산날H[-1]}) → **빈 날 {len(_거래일H) - len(_산날H):,}일 ({(1 - len(_산날H) / max(1, len(_거래일H))) * 100:.0f}%)** · 산 것 {len(_기록H):,}건")
        _달H = {}
        for d in _산날H:
            _달H[d[:4]] = _달H.get(d[:4], 0) + 1
        _거래일해 = {}
        for d in _거래일H:
            _거래일해[d[:4]] = _거래일해.get(d[:4], 0) + 1
        print("        해마다 산 날/거래일: " + " · ".join(f"{y} {_달H.get(y, 0)}/{n}" for y, n in sorted(_거래일해.items())))
    _결P = []
    for 조 in _쌍들P:
        if any(a not in _문턱P for a, _ in 조):
            continue
        _라조 = "+".join(f"{a}{da}" for a, da in 조)
        _g = _쌍거름(조)
        _n = sum(1 for x in 사건 if _g(x) and not _H(x))
        # ⚠️ 2026-09-16 pairs4: 「기준금리20↓+선물20↓」 해마다 표가 2018·2023(금리 내린 날 0)에 +9.8·+4.4% 로 찍혔다.
        #    조건이 한 번도 안 켜진 해에 돈이 달라질 수 없다 → 해마다 「더 들어온 사건 수」를 같이 찍어 대조한다
        _해별P = {}
        for x in 사건:
            if _g(x) and not _H(x):
                _해별P[날[x["인"] - 1][:4]] = _해별P.get(날[x["인"] - 1][:4], 0) + 1
        print(f"       {_라조[:30]:<32} 해마다 더 들어온 사건: " + " · ".join(f"{k} {v}" for k, v in sorted(_해별P.items())))
        _f = (lambda x, g=_g: _H(x) or g(x))
        _r = _둘(f"OR {_라조[:30]} (+{_n:,})", _c(_f))
        _r1 = _둘.r1
        # ⭐ 판정은 **제약 있는 칸**(실전에 가까움)으로. 제약 없는 칸은 참고로 같이 찍는다 (2026-09-15 고침)
        _ok1 = (_r1["산"] > _기P1["산"], _r1["끝"] > _기P1["끝"], _r1["낙"] > 낙폭기준)
        _ok2 = (_r["산"] > _기P["산"], _r["끝"] > _기P["끝"], _r["낙"] > 낙폭기준)
        _결P.append((_r1["끝"], _라조, _f, all(_ok1), all(_ok2),
                     _r1["끝"] / _기P1["끝"] * 100))
    print(f"\n     {'쌍':<34}{'제약 있음':>12}{'돈(지금의%)':>12}{'제약 없음':>12}")
    # ⚠️⚠️ 루프 변수를 `비` 로 썼다가 **시가/종가 비율표 `비`** 를 덮어써 big6 가 그 뒤 결과() 에서
    #    'float' object has no attribute 'get' 로 죽었다 (2026-09-16 00:24). 한 글자 한글 이름 금지 — 또 당했다
    for _, 라, _, ok1, ok2, _비율P in _결P:
        print(f"     {라:<34}{'✅ 셋 다' if ok1 else '❌':>12}{_비율P:>11.0f}%{'✅' if ok2 else '❌':>12}")
    print("     ⚠️ 판정은 **제약 있음** 칸이다. 제약 없음만 ✅ 인 것은 「돈 무제한일 때만 낫다」— 반영 안 한다")

    # ══ ⭐⭐⭐ **시총 하한을 낮추면** (2026-09-18 밤 · BANDOR3 결과로 이어감) ══
    # ⚠️ [지난 절] — 이미 결론이 났고 다시 안 돌린다 (막개 건너뜀)
    print("\n" + "=" * 122)
    print("  ── ⭐⭐⭐ **시총 하한을 낮추면** — 지금 300억. 그 아래는 한 번도 안 사 봤다 ──")
    print("     BANDOR3 에서 「~300억 · 60일선대비↓」가 돈 103% · 걷기 뒤 +30% 로 나왔다")
    print("=" * 122)
    print(머239)
    _기L = _둘(f"{_밑글자} (지금 · 하한 {R.시총하한억:,.0f}억 · 견줌)", _c(_H))
    _기L1 = _둘.r1
    for _하한L in (200, 150, 100, 50):
        _둘(f"하한 {_하한L}억", _c(_H, 시총하한=_하한L))
        _r1 = _둘.r1
        _ok = (_r1["산"] > _기L1["산"], _r1["끝"] > _기L1["끝"], _r1["낙"] > 낙폭기준)
        print("        => " + ("OK 셋 다" if all(_ok) else "X")
              + f" · 돈 {_r1['끝'] / _기L1['끝'] * 100:.0f}%"
              + f" · 산 것 {_r1['산']} (지금 {_기L1['산']})"
              + f" · 낙폭 {_r1['낙']:.1f}%")
    print("     ⚠️ 하한을 낮추면 거래가 얇은 종목이 든다 — 낙폭과 돈÷낙폭을 같이 본다")
    print("=" * 122)

    # ══ ⭐⭐⭐ **새 갈래 둘** (2026-09-18 · 사용자 「새로운 규칙이나 갈래를 테스트해볼 만한 게 있을까?」) ══
    # ⚠️ [지난 절] — 이미 결론이 났고 다시 안 돌린다 (막개 건너뜀)
    print("\n" + "=" * 122)
    print("  ── ⭐⭐⭐ **① 「사지 않는다」 거르개** — 지금까지 만든 건 전부 「이러면 산다」였다 ──")
    print("     BAND 자료: 60일 안 감자 26.4%(바탕 43.4) · 유상증자 35.0% · 감자+한산 14.1%")
    print("     ⚠️ 기회는 줄지만 **지는 거래만** 빼는 것이라 돈은 늘 수 있다")
    print("=" * 122)
    print(머239)
    _기N = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
    _기N1 = _둘.r1
    _증자N = _증자H if _증자H else _NM._증자표()

    def _최근(code, i, 갈래, 일수=60):
        return _NM._증자재기(_증자N, code, 갈래, 날[i], 일수, 날, i)

    _거르개들 = (
        ("감자 60일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "감자") == 0),
        ("유상증자 60일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "유상증자") == 0),
        ("둘 다 빼기", lambda x: (_최근(x["code"], x["인"] - 1, "감자") == 0
                                  and _최근(x["code"], x["인"] - 1, "유상증자") == 0)),
        ("감자 120일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "감자", 120) == 0),
        # ⭐⭐⭐ **2026-09-19 — 유상증자 빼기가 통하자 같은 부류를 마저 잰다**
        #    MKT3: 유상증자 60일 빼기 = 돈 102% · 낙폭 -11.0% -> -7.3% · 산 것 +2 (셋 다 ✅)
        #    감자 빼기는 아무 효과가 없었다 -> **희석**이 원인이라는 쪽에 무게가 실린다.
        #    그렇다면 같은 희석 공시인 무상증자·유무상증자도 봐야 하고,
        #    창 넓이도 60일이 맞는지 봐야 한다 (Q-7c 가 30~180일을 따로 훑는다)
        ("무상증자 60일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "무상증자") == 0),
        ("유무상증자 60일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "유무상증자") == 0),
        ("유상증자 30일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "유상증자", 30) == 0),
        ("유상증자 120일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "유상증자", 120) == 0),
        ("유상증자 180일 빼기", lambda x: _최근(x["code"], x["인"] - 1, "유상증자", 180) == 0),
        ("희석 전부 빼기 (유상·무상·유무상 60일)",
         lambda x: (_최근(x["code"], x["인"] - 1, "유상증자") == 0
                    and _최근(x["code"], x["인"] - 1, "무상증자") == 0
                    and _최근(x["code"], x["인"] - 1, "유무상증자") == 0)),
    )
    _결N = []
    for _라N, _거N in _거르개들:
        _f = (lambda x, g=_거N: _H(x) and g(x))
        _r = _둘(_라N, _c(_f))
        _r1 = _둘.r1
        # ⚠️ 거르개는 **산 것이 준다** — 판정은 「돈↑ 그리고 낙폭 안 나빠짐」
        _ok = (_r1["끝"] > _기N1["끝"], _r1["낙"] >= _기N1["낙"] - 0.5)
        _결N.append((_라N, all(_ok), _r1["끝"] / _기N1["끝"] * 100, _r1["산"] - _기N1["산"], _r1["낙"]))
    print(f"\n     {'거르개':<26}{'돈↑·낙폭':>10}{'돈(지금의%)':>12}{'산 것 차이':>11}{'낙폭':>8}")
    for _라N, _okN, _비N, _차N, _낙N in _결N:
        print(f"     {_라N:<26}{'✅' if _okN else '❌':>10}{_비N:>11.0f}%{_차N:>+11}{_낙N:>7.1f}%")
    print("     ⚠️ 거르개는 기회를 **줄인다** — 돈이 늘고 낙폭이 안 나빠져야 뜻이 있다")

    print("\n" + "=" * 122)
    print("  ── ⭐⭐⭐ **② 빈 날에만 문턱을 낮춘다** — 10.4년 중 94%가 아무것도 안 사는 날이다 ──")
    print("     그날 후보가 0 개인 날만 볼린저·낙폭 문턱을 절반으로. 붐비는 날은 안 건드린다")
    print("=" * 122)
    # 그날 지금 규칙으로 산 것이 하나도 없는 날
    _산날N = set()
    for x in 사건:
        if _H(x):
            _산날N.add(x["인"])
    _빈날N = {i for i in range(len(날)) if i not in _산날N}
    print(f"     지금 규칙이 후보를 낸 날 {len(_산날N):,} · **빈 날 {len(_빈날N):,}**")
    print(머239)
    _기V = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
    _기V1 = _둘.r1
    for _볼V, _낙V, _라V in ((-0.5, -5.0, "빈 날만 볼-0.5σ·낙-5%"),
                             (-0.5, -3.0, "빈 날만 볼-0.5σ·낙-3%"),
                             (-0.75, -7.0, "빈 날만 볼-0.75σ·낙-7%"),
                             (0.0, -5.0, "빈 날만 낙-5% (볼 안 봄)")):
        def _느슨(x, bv=_볼V, nv=_낙V):
            if _H(x):
                return True
            if x["인"] not in _빈날N or not 문통과(x):
                return False
            return x["볼린저"] <= bv and x["낙폭20"] <= nv
        _r = _둘(_라V, _c(_느슨))
        _r1 = _둘.r1
        _ok = (_r1["산"] > _기V1["산"], _r1["끝"] > _기V1["끝"], _r1["낙"] > 낙폭기준)
        print(f"        ⇒ {'✅ 셋 다' if all(_ok) else '❌'} · 돈 {_r1['끝'] / _기V1['끝'] * 100:.0f}% · "
              f"산 것 {_r1['산']} (지금 {_기V1['산']}) · 낙폭 {_r1['낙']:.1f}%")
    print("=" * 122)

    # ══ ⭐⭐⭐ **띠마다 제 규칙을 더하면** (2026-09-18 · 사용자 「규칙은 여러 개여도 돼」) ══
    # ⚠️ [지난 절] — 이미 결론이 났고 다시 안 돌린다 (막개 건너뜀)
    #    「그 띠만 사면」이 아니라 **지금 규칙 OR 그 띠 규칙** 이다 — 기회를 늘리는 쪽
    print("\n" + "=" * 122)
    print("  ── ⭐⭐⭐ **띠마다 제 규칙을 더하면** — 지금 규칙(소형 네 갈래) **OR** (그 띠 AND 그 재료) ──")
    print("     사용자: 「규모에 따라 섹터에 따라 … 규칙은 여러 개여도 돼」 · 빈 날 94% 를 채우는 쪽")
    print("=" * 122)
    _띠범위 = {"~300억": (0, 300), "300~2,000억 (지금)": (300, 2000), "2,000억~1조": (2000, 10000),
               "1조~10조": (10000, 100000), "10조~100조": (100000, 1000000), "100조 이상": (1000000, 9e12)}
    _띠재료 = []
    import re as _reB
    try:
        # ⚠️ `*BAND*` 는 **자기 자신(BANDOR)** 도 잡는다 — 2026-09-18 에 0개를 읽고 절이 통째로 비었다
        _bf = [f for f in sorted(glob.glob(os.path.join(O._DATA, "_labs", "*BAND*.txt")),
                                 key=os.path.getmtime, reverse=True)
               if "BANDOR" not in os.path.basename(f).upper()]
        if _bf:
            _t = io.open(_bf[0], encoding="utf-8", errors="replace").read()
            _지금띠 = None
            for _ln in _t.splitlines():
                _m = _reB.match(r"\s*\[(.+?)\]\s+바탕", _ln)
                if _m:
                    _지금띠 = _m.group(1)
                    continue
                if _지금띠 and _ln.rstrip().endswith("✅"):
                    _부 = _ln.split()
                    if len(_부) >= 4 and _부[0][-1] in "↑↓":
                        try:
                            _차 = float(_부[3].replace("+", ""))
                        except ValueError:
                            continue
                        if _차 > 0 and _지금띠 in _띠범위:
                            _띠재료.append((_지금띠, _부[0][:-1], _부[0][-1], _차))
            print(f"     BAND 에서 읽음: {len(_띠재료)}개 (띠 x 재료) ← {os.path.basename(_bf[0])}")
    except Exception as _e:  # noqa: BLE001
        print(f"     ⚠️ BAND 판을 못 읽었다 ({type(_e).__name__})")
    if _띠재료:
        print(머239)
        _기B = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
        _기B1 = _둘.r1
        _결B = []
        for _띠, _재B, _방B, _차B in _띠재료[:24]:
            if _재B not in _문턱P:
                continue
            _lo, _hi = _띠범위[_띠]

            def _띠거름(x, 재=_재B, 방=_방B, lo=_lo, hi=_hi):
                _s = x.get("시총억") or 0
                return lo <= _s < hi and 재무통과(x) and 대금통과(x) and _조건P(x, 재, 방)
            _f = (lambda x, g=_띠거름: _H(x) or g(x))
            _n = sum(1 for x in 사건 if _띠거름(x) and not _H(x))
            _r = _둘(f"+ {_띠} · {_재B}{_방B} (+{_n:,})"[:34], _c(_f, 시총하한=0, 시총상한=999999))
            _r1 = _둘.r1
            _ok = (_r1["산"] > _기B1["산"], _r1["끝"] > _기B1["끝"], _r1["낙"] > 낙폭기준)
            _결B.append((_r1["끝"], f"{_띠} · {_재B}{_방B}", _f, all(_ok), _r1["끝"] / _기B1["끝"] * 100, _r1["산"]))
        print(f"\n     {'띠 · 재료':<34}{'셋 다':>8}{'돈(지금의%)':>12}{'산 것':>8}")
        for _, _라B, _, _okB, _비B, _산B in sorted(_결B, reverse=True):
            print(f"     {_라B:<34}{'✅' if _okB else '❌':>8}{_비B:>11.0f}%{_산B:>8}")
        print("     ⚠️ 판정은 **제약 있는 칸** · 셋 다여야 다음(걷기·해마다)으로 간다")
        _산것B = [(끝, 라, f) for 끝, 라, f, ok, _, _ in _결B if ok]
        if _산것B:
            print("\n   ── 걷기 (앞 2010~2020 / 뒤 2021~2026) ──")
            for _해앞B, _해뒤B, _라9B in (("2010", "2020", "앞"), ("2021", "2027", "뒤")):
                print(f"\n   [{_라9B}]")
                print(머)
                _기9B = 시뮬(_c(_H, 제약없음=True), 시작년=_해앞B, 끝년=_해뒤B)
                표(_기9B, f"[견줌] {_밑글자}")
                for _, _라B, _fB in sorted(_산것B, reverse=True)[:6]:
                    표(시뮬(_c(_fB, 제약없음=True, 시총하한=0, 시총상한=999999),
                            시작년=_해앞B, 끝년=_해뒤B), f"+ {_라B}"[:28], _기9B)
        else:
            print("\n     ⚠️ 셋 다를 지난 띠 규칙이 없다")
    print("=" * 122)

    print("\n  ── B ⭐⭐ **걷기** (앞 2010~2020 / 뒤 2021~2026 · 제약 없는 판) ──")
    _걷P = {}
    for _해앞, _해뒤, _라9 in (("2010", "2020", "앞"), ("2021", "2027", "뒤")):
        print(f"\n   [{_라9}]")
        print(머)
        _기9 = 시뮬(_c(_H, 제약없음=True), 시작년=_해앞, 끝년=_해뒤)
        표(_기9, f"[견줌] {_밑글자}")
        for _, 라, _f, _o1, _o2, _b in _결P:
            _r9 = 시뮬(_c(_f, 제약없음=True), 시작년=_해앞, 끝년=_해뒤)
            표(_r9, f"OR {라}"[:28], _기9)
            _걷P.setdefault(라, []).append(_r9["끝"] > _기9["끝"])

    print("\n  ── C ⭐⭐ **해마다** — 셋 다 + 걷기 둘 다 지난 것 (상위 3) ──")
    _후P = sorted([(끝, 라, f) for 끝, 라, f, ok1, _ok2, _비 in _결P
                   if ok1 and all(_걷P.get(라, []))], reverse=True)[:3]
    if not _후P:
        print("     ⚠️ A·B 를 다 지난 쌍이 없다")
    for _, 라, _f in _후P:
        print(f"\n   [{_밑글자} OR {라}]")
        _차P = []
        for _y in range(2016, 2027):
            _a = 시뮬(_c(_H, 제약없음=True), 시작년=str(_y), 끝년=str(_y))
            _b = 시뮬(_c(_f, 제약없음=True), 시작년=str(_y), 끝년=str(_y))
            _d = (_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0
            _차P.append(_d)
            print(f"   {_y:<8}{_a['끝']:>17,.0f}원{_b['끝']:>17,.0f}원{_d:>+8.1f}%"
                  f"{_a['낙']:>8.1f}%{_b['낙']:>8.1f}%")
        print(f"     ⇒ "
              + _해마다판정(_차P)[0]
              + ("  ⇒ **통과 후보**" if _해마다판정(_차P)[1] is not False else ""))
    print("\n     ⚠️ **산 것이 얼마나 줄었나**를 끝 자산과 같이 본다.")
    print("        돈이 늘어도 기회가 반 토막이면 **사용자 1순위와 어긋난다**")

    _때든것 = sum(1 for x in 사건 if _H(x) and _때로들어옴(x))
    _H든것 = sum(1 for x in 사건 if _H(x))
    print(f"\n     Ⓗ 후보 {_H든것:,}건 중 **때로 들어온 것 {_때든것:,}건** "
          f"({_때든것 / max(1, _H든것) * 100:.1f}%)")

    print("\n  ── A ⭐⭐⭐ **재평가를 넣으면** (제약 있는 판 / 없는 판) ──")
    print(머239)
    _기267 = _둘("기한까지 들고 간다 (지금)", _c(_H))
    _둘("⭐ **때로 들어온 것만** 재평가", _c(_H, 재평가="때"))
    _둘("갈래와 무관하게 재평가", _c(_H, 재평가="전부"))
    # ⭐⭐ **③ 보유 중 악재가 뜨면 판다** (2026-09-15 · 할일.md 예정 ③)
    #    지금 재평가는 「시장이 **회복**했나」만 본다 — 좋은 쪽만 본다.
    #    「산 뒤에 **악재**가 뜨면 판다」는 한 번도 안 쟀다.
    #    ⚠️ 매수 쪽에서 공시는 다 졌다(121·133차 + 어젯밤) — **매도는 다른 질문**이다.
    #       사는 근거로는 못 써도, **들고 있다 도망칠 근거**로는 될 수 있다
    #    ⚠️ 악재 공시가 뜬 날의 **다음 날 시가**에 판다(장후 공시도 반영되게)
    #    ⚠️ 재평가는 **하나만** 받는다 — 「악재 + 때」를 같이 걸려면 구조를
    #       바꿔야 한다. 악재가 혼자 값어치가 있으면 그때 합친다
    _둘("⭐⭐ **악재 공시 뜨면 판다**", _c(_H, 재평가="악재"))

    print("\n  ── B ⭐⭐ **재평가 x 나눔** (뒷몫만 재평가하면) ──")
    print("     앞몫(+15%/40일)은 그대로 두고 **뒷몫(+40%/90일)** 만 흔들린다")
    print(머239)
    _둘("지금 (50:50 · 재평가 없음)", _c(_H))
    _둘("50:50 · **때 재평가**", _c(_H, 재평가="때"))
    _둘("30:70 · **때 재평가**",
        _c(_H, 재평가="때",
           나눔=((0.3, R.앞몫목표, R.앞몫기한), (0.7, R.뒷몫목표, R.뒷몫기한))))
    _둘("통짜 +40%/90일 · **때 재평가**",
        _c(_H, 재평가="때", 나눔=((1.0, 40.0, 90),)))

    print("\n  ── C ⭐⭐⭐ **앞뒤 분할** (4관문 A · 제약 없는 판) ──")
    print("     ⚠️ 앞뒤 **둘 다** 같은 방향이어야 믿는다")
    for _시267, _끝267, _라267 in (("2010", "2020", "앞 2010~2020"),
                                   ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라267)
        print(머)
        _기c267 = 시뮬(_c(_H, 제약없음=True), 시작년=_시267, 끝년=_끝267)
        표(_기c267, "[견줌] 기한까지 들고 간다")
        표(시뮬(_c(_H, 재평가="때", 제약없음=True),
                시작년=_시267, 끝년=_끝267), "때로 들어온 것만 재평가", _기c267)
        표(시뮬(_c(_H, 재평가="전부", 제약없음=True),
                시작년=_시267, 끝년=_끝267), "갈래 무관 재평가", _기c267)

    # ══ ⭐⭐⭐ 266차 — **중복 보유** ══ (2026-09-11)
    #    `docs/할일.md` 「아직 시험을 안 만든 것」에 있던 것.
    #    「자본 시뮬이 필요해 뒤로 미룸」이라 적어두고 **잊었다**
    print("\n" + "=" * 108)
    print("  266차 · ⭐⭐⭐ **같은 종목을 또 사나** (중복 보유)")
    print("     지금 시뮬은 **또 산다** — 보유에 종목코드조차 안 넣었다")
    print("     겹쳐 사면 한 종목에 자산의 **40·60%** 가 몰린다")
    print("     ⇒ 「자산의 20%」 가정이 조용히 깨지고 있었다")
    print("     ⚠️ 화면에 금액 배분은 안 쓴다 — 이건 **시뮬 가정**을 재는 것이다")
    print("=" * 108)

    print("\n  ── A ⭐⭐⭐ **겹쳐 사기를 막으면** (제약 있는 판 / 없는 판) ──")
    print(머239)
    _기266 = _둘("겹쳐 산다 (지금)", _c(_H))
    _겹쳤다[0] = 0
    _둘("⭐ **겹쳐 안 산다**", _c(_H, 중복금지=True))
    print(f"\n     ⇒ 중복이라 **건너뛴 것 {_겹쳤다[0]:,}번** "
          f"(제약 있는 판 + 없는 판 합)")

    print("\n  ── B ⭐⭐ **하루 상한을 같이 움직이면** ──")
    print("     겹쳐 안 사면 자리가 남는다 — 하루 상한을 늘려 채우면 어떤가")
    print(머239)
    for _n266 in (4, 5, 6, 8):
        _둘(f"겹쳐 안 삼 · 하루 {_n266}종목",
            _c(_H, 중복금지=True, 하루상한=_n266))

    print("\n  ── C ⭐⭐⭐ **앞뒤 분할** (4관문 A · 제약 없는 판) ──")
    print("     ⚠️ 앞뒤 **둘 다** 같은 방향이어야 믿는다")
    for _시266, _끝266, _라266 in (("2010", "2020", "앞 2010~2020"),
                                   ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라266)
        print(머)
        _기c266 = 시뮬(_c(_H, 제약없음=True), 시작년=_시266, 끝년=_끝266)
        표(_기c266, "[견줌] 겹쳐 산다 (지금)")
        표(시뮬(_c(_H, 중복금지=True, 제약없음=True),
                시작년=_시266, 끝년=_끝266), "겹쳐 안 산다", _기c266)
        표(시뮬(_c(_H, 중복금지=True, 하루상한=6, 제약없음=True),
                시작년=_시266, 끝년=_끝266), "겹쳐 안 삼 · 하루 6종목", _기c266)

    # ══ ⭐⭐⭐ 265차 — **테마형 무리 「같이 빠짐」** ══ (2026-09-11)
    #    196차: 테마형 x 같이빠짐 **61.4%** (견줌 57.1%) — 그런데 **승률로만** 쟀다
    #    「평균 수익은 돈이 아니다」 — 여기서 **자본 시뮬 + 4관문**으로 다시 잰다
    print("\n" + "=" * 108)
    print("  265차 · ⭐⭐⭐ **테마형 무리 「같이 빠짐」** — 196차를 4관문에")
    print("     무리 = 상관 0.6 으로 묶은 것 (분류표를 안 쓴다 · 194·195차)")
    print("     테마형 = 한 업종 40% 미만 · 업종형 = 한 업종 70%↑")
    print("     같이 빠짐 = 그 종목 낙폭이 **무리 중앙값과 ±10%p 안**")
    print("     ⚠️ 메모리 「빠진 걸 산다 — 혼자 말고 **같이**」")
    print("=" * 108)

    _든것 = sum(1 for x in 사건 if _무리.get((str(x["해"]), x["code"])))
    print(f"\n     무리에 든 사건 {_든것:,}/{len(사건):,}건 "
          f"({_든것 / max(1, len(사건)) * 100:.1f}%)")
    for _성5 in ("테마형", "섞임", "업종형"):
        _n5 = sum(1 for x in 사건 if _성격맞나(x, _성5))
        print(f"       {_성5:<6}{_n5:>9,}건 "
              f"({_n5 / max(1, _든것) * 100:>5.1f}%)")

    if _든것 < 1000:
        print("     ⚠️ **무리에 든 사건이 너무 적다.** 이 절은 못 믿는다")
    else:
        print("\n  ── A ⭐⭐⭐ **같이 빠진 것** (제약 있는 판 / 없는 판) ──")
        print(머239)
        _기265 = _둘("Ⓗ (지금 · 견줌)", _c(_H))
        _둘("Ⓗ **AND** 같이 빠짐", _c(lambda z: _H(z) and _같이빠짐(z)))
        _둘("Ⓗ **AND** 나만 빠짐 (무리보다 15%p↑ 더)",
            _c(lambda z: (_H(z) and _무리낙폭(z) is not None
                          and (z.get("낙폭20") or 0)
                          < _무리낙폭(z) - 15.0)))
        _둘("Ⓗ **OR** 같이 빠짐", _c(lambda z: _H(z) or (문통과(z) and _같이빠짐(z))))

        print("\n  ── B ⭐⭐⭐ **무리 성격마다** (196차 F절을 자본 시뮬로) ──")
        print(머239)
        for _성5 in ("테마형", "섞임", "업종형"):
            _둘(f"Ⓗ AND {_성5}",
                _c(lambda z, s=_성5: _H(z) and _성격맞나(z, s)))
        for _성5 in ("테마형", "섞임", "업종형"):
            _둘(f"⭐ Ⓗ AND {_성5} **AND 같이 빠짐**",
                _c(lambda z, s=_성5: (_H(z) and _성격맞나(z, s)
                                      and _같이빠짐(z))))
        _둘("⭐⭐ Ⓗ **OR** (테마형 AND 같이 빠짐)",
            _c(lambda z: (_H(z) or (문통과(z) and _성격맞나(z, "테마형")
                                    and _같이빠짐(z)))))

        print("\n  ── C ⭐⭐ **무리가 클수록 센가** (196차 E절) ──")
        print(머239)
        for _작, _큰, _라5 in ((3, 6, "무리 3~5종목"), (6, 11, "무리 6~10종목"),
                               (11, 21, "무리 11~20종목"), (21, 9999, "무리 21종목↑")):
            _둘(f"{_라5} · 같이 빠짐",
                _c(lambda z, a=_작, b=_큰:
                   (_H(z) and _같이빠짐(z)
                    and a <= len(_무리.get((str(z["해"]), z["code"])) or []) < b)))

        print("\n  ── D ⭐⭐⭐ **앞뒤 분할** (4관문 A · 제약 없는 판) ──")
        print("     ⚠️ 앞뒤 **둘 다** 같은 방향이어야 믿는다")
        _도전265 = (
            ("Ⓗ AND 같이 빠짐", lambda z: _H(z) and _같이빠짐(z)),
            ("Ⓗ OR 같이 빠짐",
             lambda z: _H(z) or (문통과(z) and _같이빠짐(z))),
            ("⭐ Ⓗ AND 테마형 AND 같이 빠짐",
             lambda z: _H(z) and _성격맞나(z, "테마형") and _같이빠짐(z)),
            ("⭐⭐ Ⓗ OR (테마형 AND 같이 빠짐)",
             lambda z: (_H(z) or (문통과(z) and _성격맞나(z, "테마형")
                                  and _같이빠짐(z)))),
        )
        for _시5, _끝5, _라5b in (("2011", "2020", "앞 2011~2020"),
                                  ("2021", None, "**뒤 2021~2026**")):
            print("\n   [%s]" % _라5b)
            print(머)
            _기d5 = 시뮬(_c(_H, 제약없음=True), 시작년=_시5, 끝년=_끝5)
            표(_기d5, "[견줌] Ⓗ")
            for _라5c, _fn5 in _도전265:
                표(시뮬(_c(_fn5, 제약없음=True), 시작년=_시5, 끝년=_끝5),
                  _라5c, _기d5)

    # ══ ⭐⭐⭐ 262차 — **갭 문턱** ══ (2026-09-11)
    #    181차: 「갭 하나가 후보의 98% 를 버린다」 — 1년 16.4번의 범인
    #    182차: 갭 -2.0 + 하루 무제한이 1년 118.8번 · 87.2%
    #    ⚠️ 그런데 **새 기준선(253차 중앙갭 · 250차 자르는 순서)에서 안 쟀다**
    print("\n" + "=" * 108)
    print("  262차 · ⭐⭐⭐ **갭 문턱** — 기회의 98% 가 여기서 죽는다")
    print(f"     지금 문턱 {R.상대갭문턱:+.1f}%p · 상대갭 = 그 종목 갭 - 중앙갭")
    print("     ⚠️ 판정은 **끝 자산과 낙폭**. 기회가 늘어도 돈이 줄면 안 된다")
    print("     ⚠️ 문턱을 풀면 **화면에 싣는 후보의 뜻**도 바뀐다")
    print("=" * 108)

    print("\n  ── A ⭐⭐⭐ **문턱 하나만 움직인다** (제약 있는 판 / 없는 판) ──")
    print(머239)
    _기262 = _둘(f"{R.상대갭문턱:+.1f}%p (지금)", _c(_H))
    for _g262 in (-1.0, -2.0, -2.5, -3.0, -4.5, -6.0):
        _둘(f"문턱 {_g262:+.1f}%p", _c(_H, 상대갭=_g262))
    _둘("문턱 **안 봄** (갭 조건 없음)", _c(_H, 상대갭=99.0))

    print("\n  ── B ⭐⭐⭐ **문턱 x 하루 상한** (182차의 그 칸) ──")
    print("     182차에서 갭 -2.0 + 무제한이 1년 118.8번 · 87.2% 였다")
    print(f"\n     {'문턱':<10}{'하루상한':>9}{'산 건수':>10}{'끝 자산':>18}"
          f"{'낙폭':>9}{'돈÷낙':>9}")
    for _g262 in (-2.0, -3.5, 99.0):
        for _n262 in (4, 8, 99):
            _r = 시뮬(_c(_H, 상대갭=_g262, 하루상한=_n262, 제약없음=True))
            if not _r:
                continue
            _나 = (_r["끝"] / abs(_r["낙"])) / 1e8 if _r["낙"] else 0
            _라 = "안 봄" if _g262 > 50 else f"{_g262:+.1f}%p"
            print(f"     {_라:<10}{_n262:>9,}{_r['산']:>10,}"
                  f"{_r['끝']:>17,.0f}원{_r['낙']:>8.1f}%{_나:>9.2f}")

    print("\n  ── C ⭐⭐⭐ **앞뒤 분할** (4관문 A · 제약 없는 판) ──")
    for _시262, _끝262, _라262 in (("2010", "2020", "앞 2010~2020"),
                                   ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라262)
        print(머)
        _기c262 = 시뮬(_c(_H, 제약없음=True), 시작년=_시262, 끝년=_끝262)
        표(_기c262, f"[견줌] {R.상대갭문턱:+.1f}%p (지금)")
        for _g262 in (-2.0, -2.5, -4.5, 99.0):
            _라 = "문턱 안 봄" if _g262 > 50 else f"문턱 {_g262:+.1f}%p"
            표(시뮬(_c(_H, 상대갭=_g262, 제약없음=True),
                    시작년=_시262, 끝년=_끝262), _라, _기c262)

    # ══ ⭐⭐⭐ 263차 — **OR 넷째 갈래** ══ (2026-09-11)
    #    200·201차: 기존 OR 섹터 -> 기회 +82% 인데 승률도 +3.2%p (4관문 통과)
    #    209차: **AND 로 된 재료 0개** · 시장낙폭 OR 이 +8.1%p · 기회 292%
    #    ⇒ 지금까지 **이긴 건 전부 OR** 였다. 그런데 갈래를 더 늘려본 적이 없다
    print("\n" + "=" * 108)
    print("  263차 · ⭐⭐⭐ **OR 넷째 갈래** — 지금 Ⓗ 는 세 갈래다")
    print("     Ⓗ = (볼20 ≤-1.0σ AND 낙20 ≤-10%) OR 섹터 OR 때")
    print("     200·201차에서 **더해서** 4관문을 지난 첫 사례가 나왔다")
    print("     209차에서 **AND 로 된 재료는 0개**였다")
    print("     ⚠️ 메모리 「조건을 더하면 진다」는 **AND** 얘기다. OR 은 반대다")
    print("=" * 108)

    _갈래들 = (
        ("표준화 낙폭 -2.0배↓", lambda z: _표준낙(z, -2.0)),
        ("표준화 낙폭 -2.5배↓", lambda z: _표준낙(z, -2.5)),
        ("볼60 규칙", _볼60지금),
        ("낙60 ≤-30%", lambda z: (z.get("낙폭60") or 0) <= -30),
        ("PBR 1.0↓ AND 낙20 ≤-15%",
         lambda z: (_pbr(z, 1.0)
                    and (z.get("낙폭20") or 0) <= -15)),
        ("때 — 지수 60일 -20%", lambda z: _시낙(z, 60, -20)),
    )

    print("\n  ── A ⭐⭐⭐ **갈래를 하나 더하면** (제약 있는 판 / 없는 판) ──")
    print("     ⚠️ 문(재무·대금·크기)은 그대로 지난다. 갈래만 는다")
    print(머239)
    _기263 = _둘("Ⓗ 세 갈래 (지금 · 견줌)", _c(_H))
    for _라263, _fn263 in _갈래들:
        _둘(f"Ⓗ **OR** {_라263}",
            _c(lambda z, f=_fn263: _H(z) or (문통과(z) and f(z))))

    print("\n  ── B ⭐⭐ **둘을 같이 더하면** (A 에서 나은 것끼리) ──")
    print(머239)
    for _i263 in range(len(_갈래들)):
        for _j263 in range(_i263 + 1, len(_갈래들)):
            _a, _fa = _갈래들[_i263]
            _b, _fb = _갈래들[_j263]
            _둘(f"Ⓗ OR {_a} OR {_b}",
                _c(lambda z, f=_fa, g=_fb:
                   _H(z) or (문통과(z) and (f(z) or g(z)))))

    print("\n  ── C ⭐⭐⭐ **앞뒤 분할** (4관문 A · 제약 없는 판) ──")
    print("     ⚠️ 203차가 여기서 죽었다 — 전 기간으로 골라서(look-ahead)")
    for _시263, _끝263, _라263b in (("2010", "2020", "앞 2010~2020"),
                                    ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라263b)
        print(머)
        _기c263 = 시뮬(_c(_H, 제약없음=True), 시작년=_시263, 끝년=_끝263)
        표(_기c263, "[견줌] Ⓗ 세 갈래")
        for _라263, _fn263 in _갈래들:
            표(시뮬(_c(lambda z, f=_fn263: _H(z) or (문통과(z) and f(z)),
                       제약없음=True), 시작년=_시263, 끝년=_끝263),
              f"OR {_라263}", _기c263)

    # ══ ⭐⭐⭐ 264차 — **4관문 C·D 를 지금 후보에** ══ (2026-09-11)
    #    ⚠️⚠️ 시뮬() 에 `오차` 인자가 있는데 **아무도 안 부른다**.
    #       무작위 대조는 **193차 절에만** 있다.
    #       「4관문을 다 지나야 반영한다」고 적어두고 **C·D 를 안 걸고 있었다**
    print("\n" + "=" * 108)
    print("  264차 · ⭐⭐⭐ **4관문 C·D** — 지금까지 A·B 만 걸고 있었다")
    print("     C 무작위 대조 — 같은 개수를 아무렇게나 골랐을 때보다 나은가")
    print("     D 오차 시뮬  — 08:50 예상체결가가 ±0.3~1.0%p 틀려도 버티나")
    print("=" * 108)

    print("\n  ── D ⭐⭐⭐ **오차 시뮬** (109차를 새 기준선에서) ──")
    print("     실전은 08:50 **예상**체결가로 산다. 진짜 시가는 다르다")
    print(f"\n     {'오차':<12}{'산 건수':>10}{'끝 자산':>18}{'낙폭':>9}"
          f"{'돈÷낙':>9}{'지금 대비':>11}")
    _기D = 시뮬(_c(_H, 제약없음=True))
    for _e264 in (0.0, 0.3, 0.5, 1.0, 2.0):
        _벌 = []
        for _s264 in range(3 if _e264 else 1):
            # ⚠️⚠️ `시드=` 가 아니다 — 그건 **시작 자본**이다 (2026-09-14).
            #    `시드=1` 은 「1원으로 시작」이라 낙폭 −1900% 가 나왔다
            _r = 시뮬(_c(_H, 제약없음=True), 오차=_e264, 씨=_s264)
            if _r:
                _벌.append(_r)
        if not _벌:
            continue
        _끝 = sum(z["끝"] for z in _벌) / len(_벌)
        _낙 = sum(z["낙"] for z in _벌) / len(_벌)
        _산 = sum(z["산"] for z in _벌) / len(_벌)
        _연 = sum(z["연"] for z in _벌) / len(_벌)
        # ⭐ `표()` 와 같은 식 — 같은 판이 6.73 / 16.20 으로 달리 찍혔다
        _나 = _연 / max(abs(_낙), 3.0)
        _차 = (_끝 / _기D["끝"] - 1) * 100 if _기D and _기D["끝"] else 0
        print(f"     ±{_e264:<11.1f}{_산:>10,.0f}{_끝:>17,.0f}원"
              f"{_낙:>8.1f}%{_나:>9.2f}{_차:>+10.1f}%")
    print("\n     ⇒ **±1.0%p 에서도 지금보다 나쁘지 않아야** D 를 지난 것이다")

    print(f"\n  ── C ⭐⭐⭐ **무작위 대조** (자본 시뮬로 · {_대조번}번) ──")
    print("     ⚠️ 193차 C절은 **승률**로 했다. 여기서는 **끝 자산**으로 한다")
    print("        (메모리 「평균 수익은 돈이 아니다」)")
    _기C = 시뮬(_c(_H, 제약없음=True))
    if _기C:
        # ⚠️ 대조는 **같은 개수**를 뽑아야 뜻이 있다 (193차 C절과 같은 규칙).
        #    먼저 문을 지난 것 중 Ⓗ 가 고르는 **비율**을 센다
        _문든것 = [x for x in 사건 if 문통과(x)]
        _몫C = (sum(1 for x in _문든것 if _H(x)) / len(_문든것)
                if _문든것 else 0)
        print(f"\n     문을 지난 것 {len(_문든것):,}건 중 Ⓗ 가 "
              f"{_몫C * 100:.1f}% 를 고른다 — 대조도 **같은 비율**로 뽑는다")
        _센다, _벌C = 0, []
        for _s in range(_대조번):
            def _아무거나(z, 씨=_s, 몫=_몫C):
                # 문은 지나되 **갈래는 아무렇게나**.
                # ⚠️ 종목·날짜·씨로 정해지는 해시다 — 같은 씨면 늘 같은 것이 뽑힌다
                #    (random() 을 쓰면 부를 때마다 달라져 규칙이 못 된다)
                if not 문통과(z):
                    return False
                _h = hash((z["인"], z["code"], 70000 + 씨)) & 0xFFFFFFF
                return (_h / 0xFFFFFFF) < 몫

            _r = 시뮬(_c(_아무거나, 제약없음=True))
            if _r:
                _벌C.append(_r["끝"])
                if _기C["끝"] > _r["끝"]:
                    _센다 += 1
        if _벌C:
            _벌C.sort()
            print(f"\n     Ⓗ {_기C['끝']:,.0f}원")
            print(f"     아무렇게나 20번 — 가운데 {_벌C[len(_벌C) // 2]:,.0f}원 · "
                  f"제일 좋았던 것 {_벌C[-1]:,.0f}원")
            print(f"     ⇒ Ⓗ 가 **{_센다}/{len(_벌C)}** 번 이겼다 "
                  + ("✅ **C 통과**" if _센다 >= len(_벌C) * 0.95
                     else "❌ **운일 수 있다**"))

    # ══ ⭐⭐⭐ 261차 — **후보 40개로 자를까** ══ (2026-09-11)
    #    172차: 안 자르면 1년 16.4번 · 87.2% / 40개면 10.3번 · 85.0%
    #    사용자 우선순위 1번이 **기회**다. 60% 차이는 그냥 넘길 수 없다
    print("\n" + "=" * 108)
    print("  261차 · ⭐⭐⭐ **후보를 몇 개로 자를까**")
    print("     172차 — 안 자르면 1년 16.4번 · 자르면 10.3번 (**기회 60% 차이**)")
    # ⚠️ 「화면에 40개」도 박혀 있던 숫자다 — 09-14 저녁에 60 이 됐다
    print(f"     ⚠️ 실전은 지금 **{R.후보수}개**다 (rule_def.후보수). "
          f"바꾸면 화면 1장 「후보 N종목」이 따라온다")
    print("     ⚠️ 판정은 **끝 자산과 낙폭**. 기회가 늘어도 돈이 줄면 안 된다")
    print("=" * 108)

    print("\n  ── A ⭐⭐⭐ **자르는 개수** (제약 있는 판 / 없는 판) ──")
    print(머239)
    # ⚠️⚠️ **이름표에 `_후보수`(상수)를 쓰면 거짓말이 된다** (2026-09-14 밤).
    #    Q판(BASE_PICKS=120)이 「60개 (지금)」이라 찍혔는데 값은 120개 줄과 같았다.
    #    시뮬은 `_밑후보수`(BASE_PICKS)를 쓴다 — 이름표도 그걸 써야 한다
    _기261 = _둘(f"{_밑후보수}개 (지금)", _c(_H))
    for _n261 in (20, 30, 60, 80, 120, 999):
        _둘(f"**{_n261}개**" + (" (= 안 자름)" if _n261 == 999 else ""),
            _c(_H, 후보수=_n261))

    # ══ ⭐⭐ **거래대금 하한** ══ (2026-09-15 · 세 AI 공통 지적)
    #    셋 다 「하루 거래대금 1억은 너무 낮다 — **5~10억**으로 올려라」고 했다.
    #    114차(2026-09-07)에 쟀는데 그때는 **섹터·시장 갈래가 붙기 전 옛 규칙**이다:
    #        1억(지금) 5,433만 · -5.8% · 100   3억 5,818만(+7%) · **-5.4%** · 97
    #        5억 5,198만(-4%) · **-8.9%** · 89   <- 셋이 권한 구간이 **우리 자료에선 손해**
    #    ⭐ 3억은 **돈도 늘고 낙폭도 얕아지는** 유일한 후보였다 — 다른 건 전부 맞바꿈이다.
    #    지금 규칙(후보 120 · 섹터·시장 갈래)으로 **다시 잰다**
    #    ⚠️ 1억 **아래**는 못 잰다 — 후보를 모을 때 이미 `R.대금하한억` 으로 걸렀다
    print("\n  ── A-2 ⭐⭐ **거래대금 하한** (세 AI 공통 지적) ──")
    print("     114차는 **옛 규칙**이었다. 지금 규칙으로 다시 —")
    print("     그때 값: 1억 5,433만 · 3억 5,818만(+7%·낙폭 -5.4%) · 5억 5,198만(-4%·-8.9%)")
    print(머239)
    for _대9 in (1.0, 2.0, 3.0, 5.0, 10.0):
        _둘(f"거래대금 **{_대9:g}억↑**" + (" (지금)" if _대9 == R.대금하한억 else ""),
            _c(_H, 대금하한=_대9))

    print("\n  ── B ⭐⭐ **몇 번 살 수 있게 되나** (기회) ──")
    print("     ⚠️ 자르기는 **사는 날**을 늘리는 게 아니라 그날 **살 것**을 바꾼다")
    print(f"\n     {'자르는 수':<14}{'산 건수':>10}{'끝 자산':>18}{'낙폭':>9}"
          f"{'돈÷낙':>9}")
    for _n261 in (20, 40, 60, 80, 120, 999):
        _r261 = 시뮬(_c(_H, 후보수=_n261, 제약없음=True))
        if not _r261:
            continue
        _나 = (_r261["끝"] / abs(_r261["낙"])) / 1e8 if _r261["낙"] else 0
        print(f"     {_n261:<14,}{_r261['산']:>10,}{_r261['끝']:>17,.0f}원"
              f"{_r261['낙']:>8.1f}%{_나:>9.2f}")

    print("\n  ── C ⭐⭐⭐ **앞뒤 분할** (4관문 A · 제약 없는 판) ──")
    print("     ⚠️ 앞뒤 **둘 다** 같은 방향이어야 믿는다")
    for _시261, _끝261, _라261 in (("2010", "2020", "앞 2010~2020"),
                                   ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라261)
        print(머)
        _기c261 = 시뮬(_c(_H, 제약없음=True), 시작년=_시261, 끝년=_끝261)
        표(_기c261, f"[견줌] {_밑후보수}개 (지금)")
        for _n261 in (20, 60, 120, 999):
            표(시뮬(_c(_H, 후보수=_n261, 제약없음=True),
                    시작년=_시261, 끝년=_끝261), f"{_n261}개", _기c261)

    print("\n  ── D ⭐⭐⭐ **해마다 끝 자산** (4관문 B) ──")
    _해261 = sorted({x["해"] for x in 사건})
    for _n261 in (60, 999):
        _이1, _짐1 = 0, 0
        # ⚠️ 「지금 40개」라고 박혀 있었다 (2026-09-14 밤 고침). 견줌은 `_c(_H)`,
        #    즉 **이 판이 쓴 후보수**(BASE_PICKS)다. 40 이 아니다
        print(f"\n   [{_n261}개]  {'해':<7}{f'지금 {_밑후보수}개':>15}{'도전':>15}"
              f"{'차이':>9}{'지금 낙':>8}{'도전 낙':>9}")
        for _y1 in _해261:
            try:
                _기y1 = 시뮬(_c(_H, 제약없음=True), 시작년=_y1, 끝년=_y1)
                _도y1 = 시뮬(_c(_H, 후보수=_n261, 제약없음=True),
                             시작년=_y1, 끝년=_y1)
            except Exception:  # noqa: BLE001
                continue
            if not _기y1 or not _도y1 or _기y1["산"] < 3:
                continue
            _늘1 = ((_도y1["끝"] / _기y1["끝"] - 1) * 100
                    if _기y1["끝"] > 0 else 0)
            if _늘1 > 0:
                _이1 += 1
            elif _늘1 < 0:
                _짐1 += 1
            print(f"            {_y1:<7}{_기y1['끝']:>14,.0f}원"
                  f"{_도y1['끝']:>14,.0f}원{_늘1:>+8.1f}%"
                  f"{_기y1['낙']:>7.1f}%{_도y1['낙']:>8.1f}%")
        print(f"            ⇒ **{_이1}승 {_짐1}패**")

    # ══ ⭐⭐⭐ 260차 — **규모별 중앙갭** ══ (2026-09-11)
    #    사용자: 「한 규칙으로 대형·소형을 묶으니까」
    #    253차 A·C·D 에서 4관문을 이미 받는다. 여기서는 **크기를 푼 판**과
    #    **규칙끼리 부딪치는지**를 본다
    print("\n" + "=" * 108)
    print("  260차 · ⭐⭐⭐ **규모별 중앙갭** — 제 규모대와 견준다")
    print("     지금  300억 소형주 갭을 **코스피 초대형 20개** 갭과 견준다")
    print("     260차 소형은 소형끼리 · 중형은 중형끼리 · 대형은 대형끼리")
    print("     ⚠️ 4관문 A·B 는 253차 C·D 절에 같이 태웠다")
    print("=" * 108)

    print("\n  ── A ⭐⭐⭐ **크기를 풀면** (규모별 잣대가 사는 자리) ──")
    print("     ⚠️ 소형만 사는 판에서는 잣대만 바뀐다. 크기를 풀어야 뜻이 산다")
    print(머239)
    _기260 = _둘("Ⓗ · 지금 잣대 · 소형만 (견줌)", _c(_H))
    _둘("Ⓗ · **규모별 잣대** · 소형만", _c(_H, 갭잣대="규모별"))
    _둘("Ⓗ · 지금 잣대 · **크기 무제한**",
        _c(_H, 시총상한=999999))
    _둘("⭐ Ⓗ · **규모별 잣대** · **크기 무제한**",
        _c(_H, 갭잣대="규모별", 시총상한=999999))

    print("\n  ── B ⭐⭐ **규모대마다 중앙갭이 얼마나 다른가** ──")
    print("     같으면 이 시험은 뜻이 없다. 벌어져야 규모별로 나눌 값어치가 있다")
    _모아260 = {}
    for _v260 in _규모중앙갭.values():
        for _k260, _z260 in _v260.items():
            _모아260.setdefault(_k260, []).append(_z260)
    print(f"\n     {'규모대':<8}{'날수':>8}{'중앙갭의 중앙값':>16}"
          f"{'25%':>10}{'75%':>10}")
    for _k260 in ("소형", "중형", "대형"):
        _z = sorted(_모아260.get(_k260) or [])
        if not _z:
            print(f"     {_k260:<8}{'없다':>8}")
            continue
        print(f"     {_k260:<8}{len(_z):>8,}{st.median(_z):>15.2f}%"
              f"{_z[len(_z) // 4]:>9.2f}%{_z[len(_z) * 3 // 4]:>9.2f}%")

    print("\n  ── C ⭐⭐⭐ **규칙끼리 부딪치나** ──")
    print("     사용자 물음: 규모별로 잣대를 나누면 한 종목이 **서로 다른**")
    print("     잣대에 동시에 걸릴 수 있나")
    print("     ⇒ 규모대는 시총으로 **겹치지 않게** 자른다 (소형<2천억")
    print("        ≤중형<1조 ≤대형). 한 종목은 **한 규모대에만** 든다.")
    print("        상대갭 문턱(-3.5%p)은 **그대로 하나**다 — 부딪칠 자리가 없다")
    _붙260 = 0
    for _v260 in _규모중앙갭.values():
        if len(_v260) >= 2:
            _붙260 += 1
    print(f"\n     규모대가 **둘 이상** 잡힌 날 {_붙260:,}/{len(_규모중앙갭):,}일")

    print("\n  ── D ⭐⭐⭐ **상대갭 문턱도 규모별로** 나누면 ──")
    print(머239)
    _둘("문턱 하나 -3.5%p (지금)", _c(_H, 갭잣대="규모별"))
    for _문260 in (-2.0, -3.0, -4.5, -6.0):
        _둘(f"규모별 잣대 · 문턱 {_문260:+.1f}%p",
            _c(_H, 갭잣대="규모별", 상대갭=_문260))

    # ══ ⭐⭐⭐ 256차 — **3중 교차** (규모 x 섹터 x 재료) ══ (2026-09-12)
    # ⚠️ [지난 절] — 이미 결론이 났고 다시 안 돌린다 (막개 건너뜀)
    #    235-D 는 **재료 셋만** 쟀다 (볼20·낙20 / 외국인 / 재무).
    #    표준화 낙폭 · 모멘텀 · 밸류 · 때 조건 · 무리가 안 들어갔다
    print("\n" + "=" * 108)
    print("  256차 · ⭐⭐⭐ **3중 교차** — 규모 x 섹터 x 재료")
    print("     조합 격자의 **마지막 빈 칸**이다 (MASTER-STATUS §3)")
    print("     ⚠️ 새 기준선(중앙갭 = 후보 + 실전표본 30) 위에서 잰다")
    print("=" * 108)

    def _규모(x, lo, hi):
        _v = x.get("시총억") or 0
        return lo <= _v < hi

    _규모들 = (("소형 300~1,000억", 300, 1000),
               ("중형 1,000~2,000억", 1000, 2000))
    _재료들 = (
        ("표준화 낙폭 -1.5배↓", lambda z: _표준낙(z, -1.5)),
        ("모멘텀 60일 오름", lambda z: (z.get("낙폭60") or 0) > 0),
        ("PBR 1.0배↓", lambda z: (z.get("PBR") or 9e9) <= 1.0),
        ("거래량 늘어남", lambda z: (z.get("회전율") or 0) >= 3),
        # ⭐⭐ COMBO-AUDIT 2절 — **때 조건이 조합 시험에 한 번도 안 들어갔다.**
        #    시장낙폭 OR 는 209·210차에 나왔는데 섹터 시험(198~202)은 그 전이고,
        #    지수 60일 낙폭은 219차에 나왔는데 **규모·섹터 조합이 없다** (2026-09-11)
        ("때 — 지수 7일 낙폭", _시7),
        ("때 — 지수 60일 -10%", lambda z: _시낙(z, 60, -10)),
    )
    print("\n  ── A ⭐⭐⭐ **규모 x 재료** (제약 있는 판 / 없는 판) ──")
    print(머239)
    _기256 = _둘("Ⓗ (지금 · 견줌)", _c(_H))
    for _라s, _lo, _hi in _규모들:
        for _라m, _fn in _재료들:
            _둘(f"{_라s} x {_라m}",
                _c(lambda z, a=_lo, b=_hi, f=_fn:
                   _H(z) and _규모(z, a, b) and f(z)))

    print("\n  ── B ⭐⭐ **섹터 x 재료** ──")
    print(머239)
    for _라m, _fn in _재료들:
        _둘(f"섹터 종목 x {_라m}",
            _c(lambda z, f=_fn: _H(z) and 섹터맞나(z) and f(z)))

    print("\n  ── C ⭐⭐⭐ **셋 다** (규모 x 섹터 x 재료) ──")
    print(머239)
    for _라s, _lo, _hi in _규모들:
        for _라m, _fn in (_재료들[0], _재료들[1], _재료들[4], _재료들[5]):
            _둘(f"{_라s} x 섹터 x {_라m}",
                _c(lambda z, a=_lo, b=_hi, f=_fn:
                   (_H(z) and _규모(z, a, b) and 섹터맞나(z) and f(z))))

    # ══ ⭐⭐ 257차 — **증자 재시험** ══ (2026-09-12)
    #    236차에서 **0건**이었다 — `dart-capital` 구조를 잘못 읽었다
    print("\n" + "=" * 108)
    print("  257차 · ⭐⭐ **증자·감자 재시험** (236차는 0건이었다)")
    print("=" * 108)
    # ⚠️⚠️ **x["증자"] 같은 칸은 아무도 안 채운다** (2026-09-11 에 알았다).
    #    236차·257차가 「0건」이었던 건 자료가 없어서가 아니라 **내가 없는 칸을
    #    봤기** 때문이다. 247차처럼 `_자본있나()` 로 본다
    _종류7 = ("유상증자", "무상증자", "유무상증자", "감자",
              "자사주취득", "자사주처분")
    print()
    _센7 = {}
    for _k in _종류7:
        _센7[_k] = sum(1 for x in 사건 if _자본있나(x, _k))
        print(f"     사건에 붙은 것 — {_k:<10}{_센7[_k]:>9,}건 "
              f"({_센7[_k] / max(1, len(사건)) * 100:>5.2f}%)")
    print(f"     전체 사건 {len(사건):,}건 · 자본 이력 {len(_자본):,}종목")

    if sum(_센7.values()) == 0:
        print("     ⚠️ **여전히 0건이다.** dart-capital 폴더를 직접 열어 본다")
    else:
        print("\n  ── A ⭐⭐ **있으면 빼고, 없으면 두고** (제약 있는 판 / 없는 판) ──")
        print("     ⚠️ 증자는 **주식 수가 늘어** 값이 묽어진다. 빼는 게 맞나?")
        print(머239)
        _기257 = _둘("Ⓗ (견줌)", _c(_H))
        for _k in _종류7:
            if _센7[_k] < 200:
                continue
            _둘(f"Ⓗ **AND** {_k} **없음**",
                _c(lambda z, kk=_k: _H(z) and not _자본있나(z, kk)))
        for _k in _종류7:
            if _센7[_k] < 200:
                continue
            _둘(f"Ⓗ **AND** {_k} **있음**",
                _c(lambda z, kk=_k: _H(z) and _자본있나(z, kk)))
        _둘("Ⓗ **AND** 증자·감자 **셋 다 없음**",
            _c(lambda z: (_H(z) and not _자본있나(z, "유상증자")
                          and not _자본있나(z, "무상증자")
                          and not _자본있나(z, "감자"))))

        print("\n  ── B ⭐⭐ **창을 바꾸면** (며칠 안의 증자를 보나) ──")
        print(머239)
        for _창7 in (20, 60, 120, 250):
            _둘(f"Ⓗ AND 유상증자 없음 · {_창7}일 창",
                _c(lambda z, w=_창7: _H(z) and not _자본있나(z, "유상증자", w)))

        print("\n  ── C ⭐⭐⭐ **앞뒤 분할** (A 에서 나은 것) ──")
        for _시7b, _끝7b, _라7b in (("2010", "2020", "앞 2010~2020"),
                                    ("2021", None, "**뒤 2021~2026**")):
            print("\n   [%s]" % _라7b)
            print(머)
            _기c7 = 시뮬(_c(_H, 제약없음=True), 시작년=_시7b, 끝년=_끝7b)
            표(_기c7, "[견줌] Ⓗ")
            for _k in ("유상증자", "감자", "자사주취득"):
                if _센7[_k] < 200:
                    continue
                표(시뮬(_c(lambda z, kk=_k: _H(z) and not _자본있나(z, kk),
                           제약없음=True), 시작년=_시7b, 끝년=_끝7b),
                  f"{_k} 없음", _기c7)

    # ══ ⭐⭐⭐ 258차 — **매도 넷** ══ (2026-09-12)
    #    전부 **제약 있는 판** + **옛 Ⓗ** 에서 정한 것이다
    print("\n" + "=" * 108)
    print("  258차 · ⭐⭐⭐ **매도 넷** — 새 기준선에서 다시")
    print("     나눔 비율 · 목표x기한 · **손절** · **규모별** · **때 조건**")
    print("     SELL-PLAN.md 2절의 여섯 중 **다섯**이 여기 있다")
    print("     (243차 보유 중 재평가만 남는다 — 매수 근거가 사라지면 판다)")
    print("     ⚠️ 판정은 **끝 자산과 낙폭**이다. 승률로 하지 않는다")
    print("=" * 108)

    print("\n  ── A ⭐⭐⭐ **나눔 비율** (126차에서 30:70 이 +11% 였다) ──")
    print(머239)
    _기258 = _둘("50:50 (지금)", _c(_H))
    for _앞, _뒤 in ((0.3, 0.7), (0.4, 0.6), (0.6, 0.4), (0.7, 0.3)):
        _둘(f"{int(_앞*100)}:{int(_뒤*100)}",
            _c(_H, 나눔=((_앞, R.앞몫목표, R.앞몫기한),
                         (_뒤, R.뒷몫목표, R.뒷몫기한))))

    print("\n  ── B ⭐⭐⭐ **목표 x 기한** (통짜 매도) ──")
    print(머239)
    for _목 in (10, 15, 20, 30, 40):
        for _기 in (20, 40, 90):
            _둘(f"목표 +{_목}% · {_기}일 (통짜)",
                _c(_H, 나눔=((1.0, float(_목), _기),)))

    print("\n  ── C ⭐⭐⭐ **손절을 넣으면** (SELL-PLAN 240차) ──")
    print("     ⚠️ 9/2 stop_lab 에서 한 번 기각했다 — 그건 **옛 후보·옛 기준선**")
    print("     ⚠️ Ⓗ 후보는 **덜 빠진 종목**도 든다. 손절이 다를 수 있다")
    print("     ⚠️ 종가 기준이다. 장중에 스친 것은 못 잡는다")
    print(머239)
    _둘("손절 없음 (지금)", _c(_H))
    for _손258 in (-5, -8, -12, -15, -20):
        _둘(f"손절 {_손258}%", _c(_H, 손절=float(_손258)))

    print("\n  ── D ⭐⭐⭐ **규모별 매도** (SELL-PLAN 241차) ──")
    print("     대형주는 변동이 작아 +15%/+40% 가 멀다 — 규모대마다 다른 목표")
    print(머239)
    _지금몫 = ((0.5, R.앞몫목표, R.앞몫기한), (0.5, R.뒷몫목표, R.뒷몫기한))
    _둘("규모 안 가림 (지금)", _c(_H))
    _둘("대형만 목표 낮춤 (+10/40일 · +20/90일)",
        _c(_H, 규모별매도={
            "소형": _지금몫, "중형": _지금몫,
            "대형": ((0.5, 10.0, 40), (0.5, 20.0, 90))}))
    _둘("중·대형 목표 낮춤 (+10/40일 · +25/90일)",
        _c(_H, 규모별매도={
            "소형": _지금몫,
            "중형": ((0.5, 10.0, 40), (0.5, 25.0, 90)),
            "대형": ((0.5, 10.0, 40), (0.5, 20.0, 90))}))
    _둘("소형은 더 기다림 (+20/40일 · +50/120일)",
        _c(_H, 규모별매도={
            "소형": ((0.5, 20.0, 40), (0.5, 50.0, 120)),
            "중형": _지금몫, "대형": _지금몫}))

    print("\n  ── F ⭐⭐ **때 조건 매도** (SELL-PLAN 242차) ──")
    print("     매수가 「때」였으니 매도도 「때」일 수 있다")
    print("     ⚠️ 메모리 「목표까지 기다려 판다」 — 회복 신호로 팔면 **돈이 반 났다**.")
    print("        그때는 옛 기준선이었다. 여기서 다시 확인만 한다")
    print(머239)
    _둘("기한으로 판다 (지금)", _c(_H))
    _둘("뒷몫을 **20일선 회복**에 판다",
        _c(_H, 나눔=((0.5, R.앞몫목표, R.앞몫기한),
                     (0.5, R.뒷몫목표, R.뒷몫기한, "20일선"))))
    _둘("뒷몫을 **볼린저 0 회복**에 판다",
        _c(_H, 나눔=((0.5, R.앞몫목표, R.앞몫기한),
                     (0.5, R.뒷몫목표, R.뒷몫기한, "볼0"))))
    _둘("**둘 다** 때 조건",
        _c(_H, 나눔=((0.5, R.앞몫목표, R.앞몫기한, "20일선"),
                     (0.5, R.뒷몫목표, R.뒷몫기한, "20일선"))))

    print("\n  ── E ⭐⭐⭐ **앞뒤 분할** — A·B 에서 이긴 것만 ──")
    print("     ⚠️ 앞뒤 **둘 다** 같은 방향이어야 믿는다")
    for _시258, _끝258, _라258 in (("2010", "2020", "앞 2010~2020"),
                                   ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라258)
        print(머)
        _기e = 시뮬(_c(_H, 제약없음=True), 시작년=_시258, 끝년=_끝258)
        표(_기e, "[견줌] 50:50 (지금)")
        표(시뮬(_c(_H, 제약없음=True,
                   나눔=((0.3, R.앞몫목표, R.앞몫기한),
                         (0.7, R.뒷몫목표, R.뒷몫기한))),
                시작년=_시258, 끝년=_끝258), "30:70", _기e)
        표(시뮬(_c(_H, 제약없음=True, 나눔=((1.0, 40.0, 40),)),
                시작년=_시258, 끝년=_끝258), "목표 +40% · 40일 통짜", _기e)
        for _손e in (-8, -15):
            표(시뮬(_c(_H, 제약없음=True, 손절=float(_손e)),
                    시작년=_시258, 끝년=_끝258), f"손절 {_손e}%", _기e)
        표(시뮬(_c(_H, 제약없음=True, 규모별매도={
                   "소형": ((0.5, R.앞몫목표, R.앞몫기한),
                            (0.5, R.뒷몫목표, R.뒷몫기한)),
                   "중형": ((0.5, 10.0, 40), (0.5, 25.0, 90)),
                   "대형": ((0.5, 10.0, 40), (0.5, 20.0, 90))}),
                시작년=_시258, 끝년=_끝258), "규모별 매도", _기e)

    # ⭐⭐⭐ G — **해마다 끝 자산** (4관문 B) — 나눔 (2026-09-14 신설)
    #    30:70 이 A(앞뒤)·C(무작위)는 지났는데 **B 를 재는 절이 없었다.**
    #    ⚠️ 둘 다 나눔을 **명시**한다 — BASE_SELL 로 기준선이 30:70 인 판에서는
    #       E절의 「[견줌] 50:50」 이 실은 30:70 이었다(K_30대70 판)
    print("\n  ── G ⭐⭐⭐ **해마다 끝 자산** (4관문 B · 나눔 · 제약 없는 판) ──")
    print("     ⚠️ 50:50 과 도전 둘 다 나눔을 **명시**해서 잰다 — 기준선이 무엇이든 같다")
    _해258 = sorted({x["해"] for x in 사건})
    _반반 = ((0.5, R.앞몫목표, R.앞몫기한), (0.5, R.뒷몫목표, R.뒷몫기한))
    _기g = {}
    for _yg in _해258:
        try:
            _기g[_yg] = 시뮬(_c(_H, 제약없음=True, 나눔=_반반),
                            시작년=_yg, 끝년=_yg)
        except Exception:  # noqa: BLE001
            _기g[_yg] = None
    for _라g, _나g in (("30:70", ((0.3, R.앞몫목표, R.앞몫기한),
                                (0.7, R.뒷몫목표, R.뒷몫기한))),
                      ("40:60", ((0.4, R.앞몫목표, R.앞몫기한),
                                (0.6, R.뒷몫목표, R.뒷몫기한)))):
        _이g, _짐g, _무g = 0, 0, 0
        print(f"\n   [{_라g}]  {'해':<7}{'50:50':>15}{'도전':>15}"
              f"{'차이':>9}{'50:50 낙':>9}{'도전 낙':>9}")
        for _yg in _해258:
            _기y = _기g.get(_yg)
            try:
                _도y = 시뮬(_c(_H, 제약없음=True, 나눔=_나g),
                            시작년=_yg, 끝년=_yg)
            except Exception:  # noqa: BLE001
                continue
            if not _기y or not _도y or _기y["산"] < 3:
                continue
            _늘g = ((_도y["끝"] / _기y["끝"] - 1) * 100
                    if _기y["끝"] > 0 else 0)
            print(f"            {_yg:<7}{_기y['끝']:>14,.0f}원"
                  f"{_도y['끝']:>14,.0f}원{_늘g:>+8.1f}%"
                  f"{_기y['낙']:>8.1f}%{_도y['낙']:>8.1f}%")
            if _늘g > 1:
                _이g += 1
            elif _늘g < -1:
                _짐g += 1
            else:
                _무g += 1
        print(f"            ⇒ **{_이g}승 {_짐g}패 {_무g}무** — "
              f"{'✅' if _이g > _짐g else '❌'}")

    # ══ ⭐⭐⭐ 250차 — **후보 40개를 자르는 순서** ══ (2026-09-11)
    # ⚠️ [지난 절] — 이미 결론이 났고 다시 안 돌린다 (막개 건너뜀)
    #    전수조사 ⑤: 실전과 시뮬이 **다른 순서**로 자르고 있었다
    print("\n" + "=" * 108)
    print("  250차 · ⭐⭐⭐ **후보 40개를 자르는 순서**")
    print("     실전  -(기존+섹터+시장) 먼저 · 같은 층에서 낙폭 깊은 순 (206차 P-2)")
    print("     시뮬  **낙폭 깊은 순만** — 지금까지 이걸로 쟀다")
    print("     ⚠️ 211~213차에서 **고르는 순서가 -11.8%p** 를 움직였다")
    print("=" * 108)

    # ⚠️ `_겹친수` 는 이제 **위(첫 시뮬 호출 앞)** 에 있다 — 시뮬의 기본이다

    # ⚠️ `묶` 은 **거르기 전** 그물이다. 그냥 세면 부풀려진다 —
    #    시뮬과 **똑같이** 크기·대금 문을 지나고 _H 를 통과한 것만 센다
    def _그날후보(i):
        return [x for x in (묶.get(i) or [])
                if _바탕c["시총하한"] <= x["시총억"] < _바탕c["시총상한"]
                and x["대금억"] >= _바탕c["대금하한"] and _H(x)]

    _넘는날 = sum(1 for i in 묶 if len(_그날후보(i)) > _밑후보수)
    _산날 = sum(1 for i in 묶 if _그날후보(i))
    print("\n     후보가 %d개를 넘는 날 **%s일** / 후보가 있던 %s일"
          % (_밑후보수, format(_넘는날, ","), format(_산날, ",")))
    print("     ⚠️ **이 날들만** 자르는 순서가 결과를 바꾼다")

    print("\n  ── A ⭐⭐⭐ **자르는 순서별** (제약 있는 판 / 없는 판) ──")
    print(머239)
    _기250 = _둘("⭐ **겹친 수 → 낙폭** (실전 · **지금 기본**)", _c(_H))
    _둘("낙폭 깊은 순만 (옛 시뮬)", _c(_H, 자르기=_옛자르기))
    # ⚠️⚠️ 250차에서 **이것이 양쪽 판 다 이겼다** (제약 있음 1억254만 ·
    #    제약 없음 4.15억 · 낙폭 -6.9%). 206차 P-2 의 「둘 다 맞으면 75.9%」와
    #    **방향이 반대**다. 앞뒤 분할을 안 걸었으므로 아래 B절에 넣는다
    _둘("겹친 수 → 낙폭 **반대**",
        _c(_H, 자르기=lambda z: (_겹친수(z), z["낙폭20"])))
    _둘("낙폭 **얕은** 순", _c(_H, 자르기=lambda z: -z["낙폭20"]))
    # ⚠️ 제약 **없는** 판에서만 1위다 (5.77억). 제약 있는 판에서는
    #    8,549만으로 **진다** — 거래대금 1% 한도에 걸려 실제로는 못 산다
    _둘("시총 **작은** 순 (⚠️ 제약 있으면 진다)",
        _c(_H, 자르기=lambda z: z["시총억"]))
    _둘("시총 **큰** 순", _c(_H, 자르기=lambda z: -z["시총억"]))

    print("\n  ── B ⭐⭐⭐ **앞뒤 분할** (제약 없는 판) ──")
    for _시, _끝3, _라3 in (("2010", "2020", "앞 2010~2020"),
                            ("2021", None, "**뒤 2021~2026**")):
        print("\n   [%s]" % _라3)
        print(머)
        _기b = 시뮬(_c(_H, 제약없음=True), 시작년=_시, 끝년=_끝3)
        표(_기b, "[견줌] 겹친 수 → 낙폭 (실전 · 지금 기본)")
        표(시뮬(_c(_H, 제약없음=True, 자르기=_옛자르기),
                시작년=_시, 끝년=_끝3), "낙폭 깊은 순만 (옛 시뮬)", _기b)
        # ⭐ A절에서 **양쪽 판 다 이긴** 것 — 앞뒤 둘 다 이겨야 믿는다
        표(시뮬(_c(_H, 제약없음=True,
                   자르기=lambda z: (_겹친수(z), z["낙폭20"])),
                시작년=_시, 끝년=_끝3), "⭐ 겹친 수 → 낙폭 **반대**", _기b)
        표(시뮬(_c(_H, 제약없음=True, 자르기=lambda z: z["시총억"]),
                시작년=_시, 끝년=_끝3), "시총 작은 순 (제약 없는 판만)", _기b)

    # ══ ⭐⭐⭐ 242차 — **후보가 적은 날의 기준** ══
    print("\n" + "=" * 108)
    print("  242차 · ⭐⭐⭐ **후보가 적은 날의 기준**")
    print("     사용자: 「후보가 하나일때는 **중앙값 말고 다른 기준**이 있어야」")
    print("     ⚠️ 후보 1개 -> 중앙값이 그 종목 갭 -> 상대갭 **항상 0** -> 못 산다")
    print("     ⚠️⚠️ 그리고 **시뮬도 후보 3개 미만인 날을 건너뛰고 있었다**")
    print("=" * 108)

    # ── A 후보가 적은 날이 얼마나 되나 ──
    print("\n  ── A ⭐⭐⭐ **후보가 적은 날이 얼마나 되나** (Ⓗ 기준) ──")
    _날별 = {}
    for x in 사건:
        if _H(x):
            _날별[x["인"]] = _날별.get(x["인"], 0) + 1
    _벌 = sorted(_날별.values())
    if _벌:
        _총 = len(_벌)
        for _문 in (1, 2, 3, 5, 10):
            _n = sum(1 for v in _벌 if v <= _문)
            print(f"     후보 **{_문}개 이하**인 날  {_n:>6,}/{_총:,}일 "
                  f"({_n/_총*100:>5.1f}%)")
        print(f"     후보 수 — 가운데 **{_벌[_총//2]:,}개** · "
              f"아래 10% {_벌[_총//10]:,}개 · 위 10% {_벌[int(_총*0.9)]:,}개")

    # ── B 중앙갭을 무엇으로 ──
    print("\n  ── B ⭐⭐⭐ **중앙갭을 무엇으로 잡을까** ──")
    print(머239)
    _둘("㉠ 후보 중앙갭 (지금)", _c(_H))
    _둘("㉡ **전 종목** 중앙갭", _c(_H, 갭잣대="전종목중앙"))
    _둘("㉢ **절대 갭** (중앙값 없이)", _c(_H, 갭잣대="절대"))

    # ── C 후보가 적은 날을 안 건너뛰면 ──
    print("\n  ── C ⭐⭐ **후보 3개 미만인 날을 안 건너뛰면** ──")
    print(머239)
    for _m in (3, 2, 1):
        _둘(f"㉠ 후보 중앙갭 · 최소 {_m}개",
            _c(_H, 최소후보=_m))
    for _m in (3, 1):
        _둘(f"㉡ 전 종목 중앙갭 · 최소 {_m}개",
            _c(_H, 갭잣대="전종목중앙", 최소후보=_m))
        _둘(f"㉢ 절대 갭 · 최소 {_m}개",
            _c(_H, 갭잣대="절대", 최소후보=_m))

    # ── D 걷기 검증 ──
    print("\n  ── D ⭐⭐ **걷기 검증** (제약 없는 판) ──")
    for _시, _끝4, _라4 in (("2010", "2020", "앞 2010~2020"),
                            ("2021", None, "**뒤 2021~2026**")):
        print(f"\n   [{_라4}]")
        print(머)
        _기d4 = 시뮬(_c(_H, 제약없음=True), 시작년=_시, 끝년=_끝4)
        표(_기d4, "㉠ 후보 중앙갭 (지금)")
        표(시뮬(_c(_H, 갭잣대="전종목중앙", 최소후보=1, 제약없음=True),
                시작년=_시, 끝년=_끝4), "㉡ 전 종목 중앙갭 · 최소 1개", _기d4)
        표(시뮬(_c(_H, 갭잣대="절대", 최소후보=1, 제약없음=True),
                시작년=_시, 끝년=_끝4), "㉢ 절대 갭 · 최소 1개", _기d4)

    print("\n     ⇒ **산 것**이 늘면서 끝 자산도 늘어야 진짜다")

    # ══ ⭐⭐⭐ 243차 — **남은 것 한 묶음** ══
    # ⚠️ [지난 절] — 이미 결론이 났고 다시 안 돌린다 (막개 건너뜀)
    print("\n" + "=" * 108)
    print("  243차 · ⭐⭐⭐ **남은 것 한 묶음** (대형주 갭 · 고르는 순서 · 매도)")
    print("=" * 108)

    # ── A 대형주 상대갭 문턱 ──
    print("\n  ── A ⭐⭐⭐ **대형주 상대갭 문턱** ──")
    print("     대형주는 후보 3,745건인데 실제 매수 **43건**.")
    print("     갭 -3.5%p 를 못 넘어서다 — 대형주는 **갭이 작다**")
    print(머239)
    for _하, _상, _갭, _라 in ((300, 2000, -3.5, "소형 300~2,000억 · 갭-3.5 (지금)"),
                               (2000, 999999, -3.5, "2,000억↑ · 갭 -3.5"),
                               (2000, 999999, -2.5, "2,000억↑ · 갭 **-2.5**"),
                               (2000, 999999, -1.5, "2,000억↑ · 갭 **-1.5**"),
                               (2000, 999999, -1.0, "2,000억↑ · 갭 **-1.0**"),
                               (10000, 999999, -2.5, "1조↑ · 갭 -2.5"),
                               (10000, 999999, -1.5, "1조↑ · 갭 **-1.5**"),
                               (10000, 999999, -1.0, "1조↑ · 갭 **-1.0**")):
        if _하 >= _크기상한:
            print(f"  {_라:<30}{'사건에 없다':>40}")
            continue
        _둘(_라, _c(_H, 시총하한=_하, 시총상한=_상, 상대갭=_갭))
    print("\n     ⇒ 갭 문턱을 낮추면 **산 것**이 얼마나 느나가 핵심이다")

    # ── B 후보 고르는 순서 (Ⓗ 로) ──
    print("\n  ── B ⭐⭐ **후보 고르는 순서** (Ⓗ 고정 · 221차는 Ⓚ 기준이었다) ──")
    print(머239)
    import random as _r9
    for _라, _g in (("갭 큰 순 (지금)", None),
                    ("많이 빠진 순", lambda z: z["낙폭20"]),
                    ("**덜** 빠진 순", lambda z: -z["낙폭20"]),
                    ("무작위", lambda z: _r9.Random(hash(z["code"]) & 0xffff).random()),
                    ("회전율 낮은 순", lambda z: z.get("회전율") or 0),
                    ("시총 작은 순", lambda z: z.get("시총억") or 0),
                    ("볼린저 낮은 순", lambda z: z.get("볼린저") or 0)):
        _둘(_라, _c(_H, **({"고르기": _g} if _g else {})))

    # ── C 매도 목표 × 기한 ──
    print("\n  ── C ⭐⭐⭐ **매도 목표 × 기한** (Ⓗ 후보로 · 제약 없는 판 포함) ──")
    print("     123차 D절은 **제약 있는 판** + **Ⓗ 이전 후보**로 쟀다")
    print(머239)
    for _목 in (10, 15, 20, 30, 40):
        for _기 in (20, 40, 90):
            _둘(f"목표 +{_목}% · {_기}일 (통짜)",
                _c(_H, 목표=_목, 최대보유=_기, 나눔=((1.0, _목, _기),)))

    # ── D 나눔 비율 ──
    print("\n  ── D ⭐⭐ **나눔 비율** (126차에서 30:70 이 +11% 였다) ──")
    print(머239)
    for _a, _b, _라 in ((0.5, 0.5, "50:50 (지금)"), (0.3, 0.7, "30:70"),
                        (0.4, 0.6, "40:60"), (0.7, 0.3, "70:30"),
                        (0.2, 0.8, "20:80")):
        _둘(f"{_라}  (+15%/40일 : +40%/90일)",
            _c(_H, 나눔=((_a, 15, 40), (_b, 40, 90))))
    print()
    for _목1, _기1, _목2, _기2 in ((10, 20, 30, 60), (15, 20, 40, 60),
                                   (20, 40, 50, 120), (15, 60, 40, 120)):
        _둘(f"반 +{_목1}%/{_기1}일 : 반 +{_목2}%/{_기2}일",
            _c(_H, 나눔=((0.5, _목1, _기1), (0.5, _목2, _기2))))

    # ── E 폭락일 고르는 순서 재점검 ──
    print("\n  ── E ⭐⭐ **폭락일 고르는 순서 재점검** (211~213차는 제약 있는 판) ──")
    print("     213차: 폭락일엔 회전율 3%↓ 가 앞뒤 둘 다 +4.9%p 였다")
    print(머239)
    for _문 in (2, 3, 4, 6):
        _둘(f"Ⓗ AND 회전율 {_문}%↓", _c(lambda x, a=_문: _H(x) and 회전(x, a)))

    # ══ ⭐⭐⭐ 246차 — **지수 갭으로 대신할 수 있나** ══
    print("\n" + "=" * 108)
    print("  246차 · ⭐⭐⭐ **지수 갭으로 대신할 수 있나**")
    print("     ⚠️ 242차의 「전 종목 중앙갭」은 **실전에서 못 쓴다** —")
    print("        08:50 에 사람이 보는 건 **후보 8개**뿐이다")
    print("     ⇒ 08:50 에 **실제로 볼 수 있는 값**으로 대신해야 한다")
    print("=" * 108)

    # ── A 얼마나 비슷한가 ──
    print("\n  ── A ⭐⭐⭐ **지수 대용 갭 vs 전 종목 중앙갭** ──")
    _짝 = [(v, _전종목중앙갭[k]) for k, v in _지수갭.items()
           if k in _전종목중앙갭]
    if len(_짝) > 30:
        _차 = sorted(a - b for a, b in _짝)
        _n9 = len(_차)
        _ma = sum(a for a, _ in _짝) / _n9
        _mb = sum(b for _, b in _짝) / _n9
        _cov = sum((a - _ma) * (b - _mb) for a, b in _짝) / _n9
        _sa = (sum((a - _ma) ** 2 for a, _ in _짝) / _n9) ** 0.5
        _sb = (sum((b - _mb) ** 2 for _, b in _짝) / _n9) ** 0.5
        print(f"     겹치는 날 **{_n9:,}일**")
        print(f"     차이 — 가운데 {_차[_n9//2]:+.3f}%p · "
              f"아래10% {_차[_n9//10]:+.3f} · 위10% {_차[int(_n9*0.9)]:+.3f}")
        if _sa > 0 and _sb > 0:
            print(f"     **상관 {_cov/(_sa*_sb):.3f}** "
                  "(1에 가까울수록 대신 쓸 수 있다)")
    else:
        print(f"     ⚠️ 겹치는 날이 **{len(_짝)}일**뿐 — 큰 ETF 가 사건에 거의 없다")

    # ── B 시뮬 ──
    print("\n  ── B ⭐⭐⭐ **잣대별 시뮬** ──")
    print(머239)
    _둘("㉠ 후보 중앙갭 (지금)", _c(_H))
    _둘("㉡ 전 종목 중앙갭 (**실전 불가**)", _c(_H, 갭잣대="전종목중앙"))
    _둘("㉣ **지수 대용 갭** (실전 가능)", _c(_H, 갭잣대="지수갭"))

    # ── C 문턱 ──
    print("\n  ── C ⭐⭐ **지수 대용 갭이면 문턱이 얼마여야 하나** ──")
    print(머239)
    for _g in (-2.0, -2.5, -3.0, -3.5, -4.0, -5.0):
        _둘(f"지수 대용 갭 · 문턱 {_g}%p", _c(_H, 갭잣대="지수갭", 상대갭=_g))

    # ── D 걷기 검증 ──
    print("\n  ── D ⭐⭐ **걷기 검증** ──")
    for _시, _끝5, _라5 in (("2010", "2020", "앞 2010~2020"),
                            ("2021", None, "**뒤 2021~2026**")):
        print(f"\n   [{_라5}]")
        print(머)
        _기d5 = 시뮬(_c(_H, 제약없음=True), 시작년=_시, 끝년=_끝5)
        표(_기d5, "㉠ 후보 중앙갭 (지금)")
        표(시뮬(_c(_H, 갭잣대="전종목중앙", 제약없음=True), 시작년=_시, 끝년=_끝5),
          "㉡ 전 종목 중앙갭 (실전 불가)", _기d5)
        표(시뮬(_c(_H, 갭잣대="지수갭", 제약없음=True), 시작년=_시, 끝년=_끝5),
          "㉣ **지수 대용 갭**", _기d5)

    print("\n     ⇒ ㉣ 이 ㉡ 에 가까우면 **실전에서 쓸 수 있다**")

    # ══ ⭐⭐⭐ 247차 — **자사주 취득을 자본 시뮬로** ══
    print("\n" + "=" * 108)
    print("  247차 · ⭐⭐⭐ **자사주 취득을 자본 시뮬로**")
    print("     244차: 지금 AND 자사주취득 **62.9% (+9.0%p)** [+4 +14 +4] ⭐")
    print("     ⚠️ 오늘 **처음으로 AND 가 문턱을 넘었다** —")
    print("        209·215차의 재료 22가지에 **자사주가 없었다**")
    print("     ⚠️ 그런데 기회가 **1.3%** (1년 13,236 -> 178건)")
    print("=" * 108)

    _붙7 = sum(1 for x in 사건 if _자본있나(x, "자사주취득"))
    print(f"\n     자사주취득 붙은 것 {_붙7:,}/{len(사건):,} "
          f"({_붙7/max(1,len(사건))*100:.2f}%)")

    if _붙7 > 200:
        print("\n  ── A ⭐⭐⭐ **자사주 취득** ──")
        print(머239)
        _기247 = _둘("Ⓗ (견줌)", _c(_H))
        _둘("지금 규칙 **AND** 자사주취득",
            _c(lambda x: 지금(x) and _자본있나(x, "자사주취득")))
        _둘("Ⓗ **AND** 자사주취득",
            _c(lambda x: _H(x) and _자본있나(x, "자사주취득")))
        _둘("Ⓗ **OR** (지금 AND 자사주취득)",
            _c(lambda x: _H(x) or (지금(x) and _자본있나(x, "자사주취득"))))
        _둘("자사주취득 **혼자** (재무·크기만)",
            _c(lambda x: (재무통과(x) and 대금통과(x) and 크기통과(x)
                          and _자본있나(x, "자사주취득"))))

        print("\n  ── B ⭐⭐ **빼기** (244차에서 +0.0~0.4%p 였다) ──")
        print(머239)
        for _종 in ("유상증자", "무상증자", "감자"):
            _둘(f"Ⓗ **빼기** {_종}",
                _c(lambda x, a=_종: _H(x) and not _자본있나(x, a)))
        _둘("Ⓗ 빼기 (유상증자·무상증자·감자 **전부**)",
            _c(lambda x: (_H(x) and not _자본있나(x, "유상증자")
                          and not _자본있나(x, "무상증자")
                          and not _자본있나(x, "감자"))))

        print("\n  ── C ⭐⭐ **걷기 검증** (제약 없는 판) ──")
        for _시, _끝7, _라7 in (("2010", "2020", "앞 2010~2020"),
                                ("2021", None, "**뒤 2021~2026**")):
            print(f"\n   [{_라7}]")
            print(머)
            _기c7 = 시뮬(_c(_H, 제약없음=True), 시작년=_시, 끝년=_끝7)
            표(_기c7, "[견줌] Ⓗ")
            표(시뮬(_c(lambda x: _H(x) and _자본있나(x, "자사주취득"),
                      제약없음=True), 시작년=_시, 끝년=_끝7),
              "Ⓗ AND 자사주취득", _기c7)
            표(시뮬(_c(lambda x: (_H(x) and not _자본있나(x, "유상증자")
                                  and not _자본있나(x, "무상증자")
                                  and not _자본있나(x, "감자")),
                      제약없음=True), 시작년=_시, 끝년=_끝7),
              "Ⓗ 빼기 (증자·감자 전부)", _기c7)
    else:
        print("\n     ⚠️ 자사주가 사건에 거의 안 붙었다 — 잴 수 없다")

    print("\n" + "=" * 108)
    print("  판정 — A·B·C 를 다 지나야 **4관문 통과**다")
    print("=" * 108)
    for 라, _ in 도전자[1:]:
        v = 통과표.get(라, {})
        다 = all(v.get(k) for k in ("A", "B", "C"))
        print(f"  {라:<40}"
              f"A {'✅' if v.get('A') else '❌'}  "
              f"B {'✅' if v.get('B') else '❌'}  "
              f"C {'✅' if v.get('C') else '❌'}   "
              f"⇒ **{'통과' if 다 else '탈락'}**")
        if v.get("B글"):
            print(f"       해마다: {v['B글']}")
    print("\n  ⚠️ 통과해도 바로 안 바꾼다. D·E 를 사람이 읽고 정한다")
    print("  ⚠️ **2026-09-20 바뀜** — B(해마다)는 승패 세기가 아니라 **평균±오차·t** 로 본다.")
    print("     ⬜「못 가른다」는 **기각이 아니다.** t 가 −2 아래일 때만 ❌ 다")
    print("     C(무작위) 문턱은 상위 25% → **10%** 로 조였다 (25% 는 무작위도 1/4 이 통과)")
    print("     자세한 것은 docs/판정장치점검.md")
    print("=" * 108)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      # ⚠ 다른 값으로 다시 돌릴 때 결과를 덮어쓰지 않는다
                      # ⚠️⚠️ **LAB_OUT 을 안 주면 아예 안 돈다** (2026-09-11).
                      #    전에는 기본값이 `2026-09-09_193차_…` 라,
                      #    문법만 보려고 그냥 돌렸다가 **193차 결과를
                      #    통째로 덮어썼다.** 지나간 시험 결과는 되살릴 수 없다
                      #    (「시험 결과는 남긴다 — 85개가 날아갈 뻔했다」).
                      #    ⇒ 이름을 **반드시 받는다**
                      os.environ.get("LAB_OUT") or "")
    if not os.path.basename(_p):
        print("LAB_OUT 을 주세요. 예:")
        print('  LAB_OUT="2026-09-12_256차_3중교차.txt" python scripts/gate7_lab.py')
        print("  (안 주면 지나간 결과 파일을 덮어쓸 수 있어 막았습니다)")
        raise SystemExit(2)
    if os.path.exists(_p):
        print(f"이미 있는 파일입니다: {os.path.basename(_p)}")
        print("  다른 이름을 주세요 — 지나간 결과는 덮어쓰지 않습니다")
        raise SystemExit(2)

    class _Tee:
        r"""파일과 화면에 같이 쓴다.

        ⚠️⚠️ **화면에서 터지면 시험이 죽는다** (2026-09-11).
           `sys.__stdout__` 이 cp949 면 「—」 한 글자에 UnicodeEncodeError 가
           나고, 세 시간짜리 시험이 **첫 줄에서** 끝난다.
           파일은 utf-8 이라 온전하다 -> **화면 쪽만 버린다**
        """

        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            try:
                self.o.write(s)
            except UnicodeEncodeError:
                _인 = getattr(self.o, "encoding", None) or "cp949"
                self.o.write(s.encode(_인, "replace").decode(_인, "replace"))
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            try:
                _때지도_찍기()          # ⭐ 2026-09-28 — 터져도 찍는다
            except Exception:  # noqa: BLE001
                pass
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
