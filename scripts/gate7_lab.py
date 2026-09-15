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
_시작 = "20160401"
_시드 = 5_000_000.0
_후보수 = R.후보수
# ⚠️ 237차 (2026-09-10) — 사건 크기 상한. 기본 3,000억.
#    `SIZE_HI=999999` 로 열면 대형주(1조↑)까지 사건에 든다.
#    230-A 에서 대형주가 **가장 좋았다**(Ⓗ AND 빠짐 64.5% · +16.9%p)
_크기상한 = float(os.environ.get("SIZE_HI") or 3000)
# ⭐⭐ **규칙 안의 크기 상한** (2026-09-14). 위 `_크기상한` 은 사건 그물만 연다.
#    `크기통과()` 와 `_바탕c["시총상한"]` 은 R.시총상한억(2,000) 을 직접 읽어서
#    SIZE_HI=999999 를 줘도 **큰 종목이 규칙에 든 적이 없었다** (I2 가 H2 와 동일).
#    안 주면 R.시총상한억 그대로 — 기준선은 안 움직인다
_규칙크기상한 = float(os.environ.get("SIZE_HI") or R.시총상한억)

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
        "비중": 0.20, "하루상한": R.하루최대종목,
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
            if 시총 < 1e10 or 시총 >= 5e13:
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
            if 재통과 != 1.0 or 대금 < 1e8:
                continue
            _시억 = 시총 / 1e8
            # ⚠️ 237차: 상한을 **환경변수로** 연다 (기본은 3000 그대로).
            #    램 지킴이가 이 시험을 네 번 죽인 적이 있어 기본값은 안 건드린다
            #      SIZE_HI=999999 python scripts/gate7_lab.py   <- 대형주까지
            if not (100 <= _시억 < _크기상한):
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
                "해": d1[:4], **창값,
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
        for c2, v2 in _sb.items():
            if isinstance(v2, dict) and v2.get("시장"):
                시장표[c2] = str(v2["시장"])

    붙음, 섹붙음 = 0, 0
    for x in 사건:
        i2 = x["인"] - 1
        시장 = 시장표.get(x["code"]) or ""
        지수이름 = "코스닥" if "닥" in 시장 else "코스피"
        시낙 = 낙폭(지수이름, i2)
        x["시장낙폭"] = 시낙
        x["상대강도"] = (x["낙폭20"] - 시낙) if 시낙 is not None else None
        x["시장변동성"] = 변동성(지수이름, i2)
        큰 = 낙폭("코스닥 대형주", i2)
        작 = 낙폭("코스닥 소형주", i2)
        x["소형우위"] = (작 - 큰) if (큰 is not None and 작 is not None) else None
        if 시낙 is not None:
            붙음 += 1
        섹 = 업종지수(x["code"])
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
            z2 = 지분창.get(x["code"])
            if z2:
                x["지분율"] = z2[-1]
                x["지분20변화"] = z2[-1] - z2[0] if len(z2) >= 21 else None

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
    _악재표 = {}
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
        키 = (x["인"], x["code"], 목표, 보유, 상태, 손절문턱, 재평가)
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
                            r, 청 = ((vv8[0] * b8[0] / x["매수"] - 1) * 100
                                     - _비용), j8
                            break
            if 재평가 and 재평가 != "악재" and h >= 1:
                if 재평가 != "때" or _때로들어옴(x):
                    _이9 = _지수이름(x)
                    _낙7 = 낙폭(_이9, i + h, 7)
                    _낙60 = 낙폭(_이9, i + h, 60)
                    if _낙7 is not None and _낙60 is not None:
                        if _낙7 > -7 and _낙60 > -10:      # **회복했다**
                            r, 청 = ((vv[0] * b2[1] / x["매수"] - 1) * 100
                                     - _비용), j
                            break
            # ⭐ 손절 (2026-09-11 · SELL-PLAN 240차)
            if 손절문턱 is not None and h >= 1:
                if vv[0] * b2[1] <= x["매수"] * (1 + 손절문턱 / 100):
                    r, 청 = (vv[0] * b2[1] / x["매수"] - 1) * 100 - _비용, j
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
                        r, 청 = (vv[0] / x["매수"] - 1) * 100 - _비용, j
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
                    캐시[키] = ((_끝값 / x["매수"] - 1) * 100 - _비용,
                                min(max(_사라짐자리[x["code"]], i + 1), len(날) - 1))
                    return 캐시[키]
                캐시[키] = (O.폐지손실 - _비용, min(j, len(날) - 1))
                return 캐시[키]
            if not 끝:
                캐시[키] = (None, None)
                return 캐시[키]
            r, 청 = (끝[0] / x["매수"] - 1) * 100 - _비용, j
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

    def 시뮬(c, 끝년=None, 시드=None, 시작년=None, 오차=0.0, 씨=None,
             묶2=None, 기록=None):
        # ⭐ 기록=list 를 주면 거래마다 (산 날, code, 시총억, 산 값, 결과%, 청산 자리) 를 담는다 (2026-09-15)
        # ⭐ `묶2` 를 주면 **그 사건 묶음**을 쓴다 (2026-09-15 · 분할 매수).
        #    매수 루프를 안 뜯으려고 낸 길이다 — 기존 호출은 하나도 안 바뀐다
        import random as _r2
        # ⭐ 264차 D — `씨` 를 주면 잡음이 달라진다 (2026-09-14 고침).
        #    전에는 씨앗이 박혀 있어 세 번 돌려도 **같은 잡음**이었고,
        #    호출부는 `시드`(시작 자본!) 에 0·1·2 를 넣어 **1원짜리 계좌**를 돌렸다
        _rng = _r2.Random(20260907 + int(씨 or 0))
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
            평 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
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
                if v3 <= c["상대갭"]:
                    잰.append((v3, x))
            # ⚠️ 기본은 **갭이 큰 순**이다. 고르기가 있으면 그 순서로 바꾼다.
            #    문턱(상대갭 -3.5%p)은 그대로라 **후보 수는 안 변한다**
            고르기 = c.get("고르기")
            if 고르기:
                골 = sorted([z[1] for z in 잰], key=고르기)
            else:
                골 = [z[1] for z in sorted(잰, key=lambda z: z[0])]
            for x in 골[:c["하루상한"]]:
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
                _손5 = c.get("손절")
                # ⭐⭐ **제약없음** (2026-09-10 · 사용자 지적)
                #    사용자: 「**종목을 샀을 때 수익으로 계산해야지**
                #             내 자산이 얼마가 있으니 **종목에 제한을 둔다거나,
                #             그래선 안 될 것 같아**」
                #    ⚠️ `평 * 비중`(자산의 몇 %) 은 **그대로 둔다** —
                #       복리와 낙폭이 거기서 나온다.
                #       빼는 것은 **현금**과 **거래대금 1% 한도**뿐이다
                if c.get("제약없음"):
                    쓸 = 평 * c["비중"]
                    총주수 = int(쓸 // x["원시"])
                    if 총주수 < len(몫들):
                        # ⚠️ 1주도 못 살 만큼 비싸면 **주수를 몫 수만큼** 맞춘다
                        #    (소액 가정 때문에 건너뛰던 것을 없앤다)
                        총주수 = len(몫들)
                else:
                    쓸 = min(평 * c["비중"], 현금, x["대금"] * 0.01)
                    총주수 = int(쓸 // x["원시"])
                    if 총주수 < len(몫들) or 총주수 * x["원시"] > 현금:
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
                    if not c.get("제약없음") and 주수 * x["원시"] > 현금:
                        continue
                    현금 -= 주수 * x["원시"]
                    보유.append({"주수": 주수, "원시": x["원시"],
                                 "결과": r, "청산": 청,
                                 "code": x["code"]})   # ⭐ 266차
                    if 기록 is not None:
                        기록.append((날[i], x["code"], x["시총억"], x["원시"], r, 청, 주수))
                    넣음 = True
                if 넣음:
                    산 += 1
            곡.append(평)
        끝 = 현금 + sum(q["주수"] * q["원시"] for q in 보유)
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
            x["섹시그마"] = (x["낙폭20"] - st2[0]) / st2[1]

    print("  기준 수익률 붙이는 중...", flush=True)
    for x in 사건:
        x["_20"] = 앞수익(x, 20)
        x["_40"] = 앞수익(x, 40)

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
    def 재무통과(x):
        return x.get("재통과") == 1.0

    def 대금통과(x):
        return x["대금억"] >= 1.0

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

    # ⭐⭐ **193차 도전자** — 192차에서 나온 해외 신호 (2026-09-09)
    #    사용자: 「한국은 **수출 위주 국가**라 해외 수주나 해외 소식에 영향을 받을 것 같아」
    #    ⚠️ 192차는 재무 조건이 빠진 잣대였다. 여기서는 재무까지 넣고 다시 잰다
    def _지수이름(x):
        시 = 시장표.get(x["code"]) or ""
        return "코스닥" if "닥" in 시 else "코스피"

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

    통과표 = {}

    # ── A 앞뒤 분할 ──
    print("\n" + "=" * 108)
    print("  A 앞뒤 분할 — 기간을 갈라도 **같은 방향**인가")
    print("=" * 108)
    구간 = (("2016~2019", "2016", "2019"), ("2020~2022", "2020", "2022"),
            ("2023~2026", "2023", "2026"), ("2025·26 뺀 것", "2016", "2024"))
    for 라, fn in 도전자:
        print(f"\n   [{라}]")
        print(머2)
        방향 = []
        for 구라, a, b in 구간:
            칸 = [x for x in 사건 if fn(x) and a <= x["해"] <= b]
            기 = [x for x in 사건 if 지금(x) and a <= x["해"] <= b]
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
                _기 = 점수([x for x in 사건 if 지금(x)])
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
            기점 = 점수([x for x in 사건 if 지금(x) and x["해"] == y])
            if not 점 or not 기점:
                continue
            차 = 점[0] - 기점[0]
            칸별.append((y, 기점[0], 점[0], 차))
            if 차 > 0.5:
                이김 += 1
            elif 차 < -0.5:
                짐 += 1
            else:
                무 += 1
        print(f"\n   [{라}]  {'해':<8}{'지금':>10}{'도전':>10}{'차이':>10}")
        for y, a, b, c in 칸별:
            print(f"            {y:<8}{a:>9.1f}%{b:>9.1f}%{c:>+9.1f}p")
        print(f"     ⇒ **{이김}승 {짐}패 {무}무**")
        통과표.setdefault(라, {})["B"] = 이김 > 짐

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
        든다 = 상위 <= 25
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
        기칸 = [x for x in 사건 if 지금(x)]
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

    _기준 = 점수([x for x in 사건 if 지금(x)])
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

    _기214 = 점수([x for x in 사건 if 지금(x)])
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
            c0 = 점수([x for x in 사건 if 지금(x) and a <= x["해"] <= b])
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
              "하루상한": R.하루최대종목,
              "시총하한": R.시총하한억, "시총상한": _규칙크기상한,
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
            x["_겹친"] = v
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
    def _H(x):
        if not 문통과(x):
            return False
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
        for _해앞, _해뒤, _라8 in (("2010", "2021", "[앞 2010~2020]"),
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
        _승8 = [0, 0, 0]
        for _y8 in range(2016, 2027):
            _a8 = 시뮬(_c(_H소형, 제약없음=True),
                       시작년=str(_y8), 끝년=str(_y8 + 1))
            _b8 = 시뮬(_c(lambda x: _H소형(x) or _큰셋(x), 제약없음=True,
                          시총하한=0, 시총상한=999999),
                       시작년=str(_y8), 끝년=str(_y8 + 1))
            _d8 = (_b8["끝"] / _a8["끝"] - 1) * 100 if _a8["끝"] > 0 else 0
            _승8[0 if _d8 > 1 else 1 if _d8 < -1 else 2] += 1
            print(f"   {_y8:<8}{_a8['끝']:>17,.0f}원{_b8['끝']:>17,.0f}원"
                  f"{_d8:>+8.1f}%{_a8['낙']:>8.1f}%{_b8['낙']:>8.1f}%")
        print(f"     ⇒ **{_승8[0]}승 {_승8[1]}패 {_승8[2]}무** — "
              + ("✅" if _승8[0] > _승8[1] else "❌"))

        # ⭐⭐⭐ ㉣ 해마다 — BIG5 에서 A(셋 다)·C(걷기 앞 +1% 뒤 +5%) 를 지났다. 이게 마지막 관문
        print("\n  ── D-2 ⭐⭐⭐ **㉣ 소형 OR 섹터규칙(크기 무제한) — 해마다** ──")
        print(f"   {'해':<8}{'견줌 소형':>18}{'OR 섹터 무제한':>18}{'차이':>9}{'견줌 낙':>9}{'도전 낙':>9}")
        _승9 = [0, 0, 0]
        for _y9 in range(2016, 2027):
            _a9 = 시뮬(_c(_H소형, 제약없음=True), 시작년=str(_y9), 끝년=str(_y9 + 1))
            _b9 = 시뮬(_c(lambda x: _H소형(x) or _섹무제한(x), 제약없음=True,
                          시총하한=0, 시총상한=999999), 시작년=str(_y9), 끝년=str(_y9 + 1))
            _d9 = (_b9["끝"] / _a9["끝"] - 1) * 100 if _a9["끝"] > 0 else 0
            _승9[0 if _d9 > 1 else 1 if _d9 < -1 else 2] += 1
            print(f"   {_y9:<8}{_a9['끝']:>17,.0f}원{_b9['끝']:>17,.0f}원{_d9:>+8.1f}%"
                  f"{_a9['낙']:>8.1f}%{_b9['낙']:>8.1f}%")
        print(f"     ⇒ ㉣ **{_승9[0]}승 {_승9[1]}패 {_승9[2]}무** — "
              + ("✅ **4관문(A·B·C) 통과 — 반영 후보**" if _승9[0] > _승9[1] else "❌"))

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
        _이, _짐, _무 = 0, 0, 0
        print(f"\n   [{_라251}]  {'해':<8}{'Ⓗ':>10}{'도전':>10}{'차이':>10}")
        for _y251 in _해들251:
            _점 = 점수([x for x in 사건 if _fn251(x) and x["해"] == _y251])
            _기점 = 점수([x for x in 사건 if _H(x) and x["해"] == _y251])
            if not _점 or not _기점:
                continue
            _차 = _점[0] - _기점[0]
            print(f"            {_y251:<8}{_기점[0]:>9.1f}%{_점[0]:>9.1f}%"
                  f"{_차:>+9.1f}p")
            if _차 > 0.5:
                _이 += 1
            elif _차 < -0.5:
                _짐 += 1
            else:
                _무 += 1
        print(f"     ⇒ **{_이}승 {_짐}패 {_무}무** — "
              f"{'✅ 통과' if _이 > _짐 else '❌ 떨어짐'}")

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
        _승7 = [0, 0, 0]
        for _y7 in range(2019, 2027):
            _a7 = 시뮬(_c(_H, 제약없음=True), 시작년=str(_y7), 끝년=str(_y7 + 1))
            _b7 = 시뮬(_c(lambda x: _H(x) or _종목규(x), 제약없음=True),
                       시작년=str(_y7), 끝년=str(_y7 + 1))
            _d7 = (_b7["끝"] / _a7["끝"] - 1) * 100 if _a7["끝"] > 0 else 0
            _승7[0 if _d7 > 1 else 1 if _d7 < -1 else 2] += 1
            print(f"   {_y7:<8}{_a7['끝']:>17,.0f}원{_b7['끝']:>17,.0f}원"
                  f"{_d7:>+8.1f}%{_a7['낙']:>8.1f}%{_b7['낙']:>8.1f}%")
        print(f"     ⇒ **{_승7[0]}승 {_승7[1]}패 {_승7[2]}무** — "
              + ("✅" if _승7[0] > _승7[1] else "❌"))

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
    _승S = [0, 0, 0]
    for _yS in range(2016, 2027):
        _aS = 시뮬(_c(_H, 제약없음=True), 시작년=str(_yS), 끝년=str(_yS + 1))
        _bS = 시뮬(_c(_H, 제약없음=True, 나눔=_최짧), 시작년=str(_yS), 끝년=str(_yS + 1))
        _dS = (_bS["끝"] / _aS["끝"] - 1) * 100 if _aS["끝"] > 0 else 0
        _승S[0 if _dS > 1 else 1 if _dS < -1 else 2] += 1
        print(f"   {_yS:<8}{_aS['끝']:>17,.0f}원{_bS['끝']:>17,.0f}원"
              f"{_dS:>+8.1f}%{_aS['낙']:>8.1f}%{_bS['낙']:>8.1f}%")
    print(f"     ⇒ 짧은 것이 **{_승S[0]}승 {_승S[1]}패 {_승S[2]}무** — "
          + ("✅" if _승S[0] > _승S[1] else "❌"))

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
    for _해앞, _해뒤, _라9 in (("2010", "2021", "[앞]"), ("2021", "2027", "[뒤]")):
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

    def _값P(x, 재):
        if 재 == "코스피200선물20":
            return _선물20.get(x["인"] - 1)
        if 재 == "자사주60":
            k = (x["code"], x["인"])
            if k not in _자사캐시:
                i = x["인"] - 1
                _자사캐시[k] = _NM._증자재기(_증자P, x["code"], "자사주취득", 날[i], 60, 날, i)
            return _자사캐시[k]
        return x.get(재)

    _쌍들P = (("낙폭20", "↓", "상대강도", "↑"), ("낙폭20", "↓", "섹터대비", "↑"),
              ("낙폭20", "↓", "자사주60", "↑"), ("낙폭60", "↓", "자사주60", "↑"),
              ("볼린저", "↓", "상대강도", "↑"), ("소형우위", "↓", "시장낙폭", "↓"),
              ("소형우위", "↓", "코스피200선물20", "↓"), ("순이익률", "↑", "코스피200선물20", "↓"),
              ("시장낙폭", "↓", "자사주60", "↑"), ("시총억", "↓", "자사주60", "↑"),
              ("자사주60", "↑", "코스피200선물20", "↓"))
    _재료P = sorted({z[0] for z in _쌍들P} | {z[2] for z in _쌍들P})
    _문턱P = {}
    for 재 in _재료P:
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

    def _쌍거름(a, da, b, db):
        return lambda x: 문통과(x) and _조건P(x, a, da) and _조건P(x, b, db)

    print("\n  ── A ⭐⭐⭐ **Ⓗ OR 쌍** (셋 다여야 ✅) ──")
    print(머239)
    _기P = _둘(f"{_밑글자} (지금 · 견줌)", _c(_H))
    _결P = []
    for a, da, b, db in _쌍들P:
        if a not in _문턱P or b not in _문턱P:
            continue
        _g = _쌍거름(a, da, b, db)
        _n = sum(1 for x in 사건 if _g(x) and not _H(x))
        _f = (lambda x, g=_g: _H(x) or g(x))
        _r = _둘(f"OR {a}{da}+{b}{db} (+{_n:,})", _c(_f))
        _ok = (_r["산"] > _기P["산"], _r["끝"] > _기P["끝"], _r["낙"] > -10.0)
        _결P.append((_r["끝"], f"{a}{da}+{b}{db}", _f, all(_ok)))
    print(f"\n     {'쌍':<34}{'판정':>10}")
    for _, 라, _, ok in _결P:
        print(f"     {라:<34}{'✅ 셋 다' if ok else '❌':>10}")

    print("\n  ── B ⭐⭐ **걷기** (앞 2010~2020 / 뒤 2021~2026 · 제약 없는 판) ──")
    _걷P = {}
    for _해앞, _해뒤, _라9 in (("2010", "2021", "앞"), ("2021", "2027", "뒤")):
        print(f"\n   [{_라9}]")
        print(머)
        _기9 = 시뮬(_c(_H, 제약없음=True), 시작년=_해앞, 끝년=_해뒤)
        표(_기9, f"[견줌] {_밑글자}")
        for _, 라, _f, _ in _결P:
            _r9 = 시뮬(_c(_f, 제약없음=True), 시작년=_해앞, 끝년=_해뒤)
            표(_r9, f"OR {라}"[:28], _기9)
            _걷P.setdefault(라, []).append(_r9["끝"] > _기9["끝"])

    print("\n  ── C ⭐⭐ **해마다** — 셋 다 + 걷기 둘 다 지난 것 (상위 3) ──")
    _후P = sorted([(끝, 라, f) for 끝, 라, f, ok in _결P
                   if ok and all(_걷P.get(라, []))], reverse=True)[:3]
    if not _후P:
        print("     ⚠️ A·B 를 다 지난 쌍이 없다")
    for _, 라, _f in _후P:
        print(f"\n   [{_밑글자} OR {라}]")
        _승P = [0, 0, 0]
        for _y in range(2016, 2027):
            _a = 시뮬(_c(_H, 제약없음=True), 시작년=str(_y), 끝년=str(_y + 1))
            _b = 시뮬(_c(_f, 제약없음=True), 시작년=str(_y), 끝년=str(_y + 1))
            _d = (_b["끝"] / _a["끝"] - 1) * 100 if _a["끝"] > 0 else 0
            _승P[0 if _d > 1 else 1 if _d < -1 else 2] += 1
            print(f"   {_y:<8}{_a['끝']:>17,.0f}원{_b['끝']:>17,.0f}원{_d:>+8.1f}%"
                  f"{_a['낙']:>8.1f}%{_b['낙']:>8.1f}%")
        print(f"     ⇒ **{_승P[0]}승 {_승P[1]}패 {_승P[2]}무** — "
              + ("✅ **4관문 통과 후보**" if _승P[0] > _승P[1] else "❌"))
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
    print("\n  ⚠️ 통과해도 바로 안 바꾼다. D·E 를 사람이 읽고 정한다")
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
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
