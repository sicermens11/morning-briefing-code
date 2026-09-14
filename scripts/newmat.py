#!/usr/bin/env python3
r"""
newmat.py — **안 써본 재료 넷**을 사건에 붙인다 (2026-09-14 밤 신설)

## 왜
사용자: 「기존 규칙에 얹혀서 테스트 하는 게 아니라, **단독 재료로서의 효과**,
        다른 재료와의 **다양한 조합**일 때 효과를 측정해야 해」

163차(`combo4_lab.py`)가 정확히 그 틀이다 — 우리 규칙을 안 깔고 재료를 오분위로
잘라 A 하나씩 · B 둘씩(전수) · C 셋씩을 잰다. 거기에 **재료 이름만 늘리면**
새 재료도 단독·조합이 한 번에 재진다. 이 모듈이 그 재료를 만든다.

## 네 재료 (자료는 다 있는데 **한 번도 안 썼다** · field_audit 2026-09-14)
```
공시 시각    kind-time 4,110일 · 190만 건   장중에 뜬 공시 vs 장 끝난 뒤 뜬 공시
임원 매매    dart-exec 2,653종목            임원이 자기 회사 주식을 샀나
대주주 보고  dart-major 2,653종목           5% 이상 주주 지분율이 늘었나
뉴스 제목    news 2,418종목 · **1년치**      관심의 양 · 제목의 호재/악재 낱말
```

## ⚠️ 뉴스는 기간이 짧다
네이버 종목뉴스 API 가 **약 1년**만 준다(2026-09-14 실측). 10.4년 사건에 붙이면
90% 가 빈 값이라 `combo4_lab` 의 오분위가 **통째로 건너뛴다**.
⇒ 뉴스 재료는 `--최근1년` 으로 사건을 자른 판에서만 본다.

## 쓰는 법
```python
import newmat
붙은 = newmat.붙이기(사건, 날)        # 사건 dict 에 필드를 더한다. 붙은 재료 이름 목록을 준다
재료들 = 기존재료 + tuple(붙은)
```
"""
import bisect
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")

# ⚠️ 장 시간 (KRX 정규장). 15:30 뒤에 뜬 공시는 **다음 날** 값에 반영된다
_장시작, _장끝 = "09:00", "15:30"

# ⭐ 제목 낱말 — 뜻이 분명한 것만 고른다. 애매한 것(「전망」·「기대」)은 안 쓴다
_호재말 = ("수주", "계약 체결", "공급계약", "흑자전환", "최대 실적", "신고가",
          "자사주 취득", "무상증자", "특허", "임상 성공", "승인", "納品", "납품")
_악재말 = ("적자", "감자", "횡령", "배임", "상장폐지", "거래정지", "소송",
          "유상증자", "관리종목", "불성실공시", "손실", "리콜")


def _숫(s):
    """'10,149,093' → 10149093.0 · 빈 값이면 None"""
    if s is None:
        return None
    t = re.sub(r"[^\d.\-]", "", str(s))
    if not t or t in ("-", ".", "-."):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _날8(s):
    """'2026-08-25' → '20260825'"""
    return re.sub(r"[^\d]", "", str(s or ""))[:8]


# ── ① 공시 시각 ────────────────────────────────────────────────
def _공시시각표(날들):
    r"""날짜 -> {종목코드: (장중 건수, 장후 건수)}

    `dart-daily` 가 종목별 **접수번호**를 주고, `kind-time` 이 그 접수번호의 **시각**을 준다.
    둘을 이어야 「장중에 뜬 공시인가」를 알 수 있다 — 그동안 둘 다 있었는데 이은 적이 없다.
    """
    필요 = set(날들)
    표 = {}
    for f in sorted(glob.glob(os.path.join(_DATA, "dart-daily", "*.json"))):
        d8 = os.path.basename(f)[:8]
        if d8 not in 필요:
            continue
        try:
            dd = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        kt = os.path.join(_DATA, "kind-time", d8 + ".json")
        시각 = {}
        if os.path.exists(kt):
            try:
                시각 = (json.load(io.open(kt, encoding="utf-8-sig"))
                        .get("시각") or {})
            except ValueError:
                시각 = {}
        하루 = {}
        for 칸 in ("챙길공시", "그밖의공시"):
            for x in (dd.get(칸) or []):
                code = str(x.get("종목코드") or "")
                번호 = str(x.get("접수번호") or "")
                if not code or not 번호:
                    continue
                t = str(시각.get(번호) or "")
                중, 후 = 하루.get(code, (0, 0))
                if not t:
                    pass                      # 시각을 모르면 어느 쪽에도 안 센다
                elif _장시작 <= t <= _장끝:
                    중 += 1
                else:
                    후 += 1
                하루[code] = (중, 후)
        if 하루:
            표[d8] = 하루
    return 표


# ── ②③ 종목별 이력 (임원 매매 · 대주주 보고) ──────────────────
def _이력표(폴더, 값뽑기):
    """종목코드 -> (정렬된 날짜8 목록, 그 날의 값 목록)"""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, 폴더, "*.json")):
        code = os.path.basename(f)[:-5]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        벌 = []
        for x in (j.get("이력") or []):
            d8 = _날8(x.get("접수일"))
            v = 값뽑기(x)
            if len(d8) == 8 and v is not None:
                벌.append((d8, v))
        if 벌:
            벌.sort()
            표[code] = ([z[0] for z in 벌], [z[1] for z in 벌])
    return 표


def _최근합(표, code, 날짜8, 일수, 날들, 자리):
    r"""`자리`(날 배열 인덱스)에서 **거래일 기준 `일수`만큼 거슬러** 올라가 합친다.

    ⚠️ 달력 일수가 아니라 **거래일**이다 — 사건이 거래일 기준이라 맞춰야 한다.
    """
    t = 표.get(code)
    if not t:
        return None
    시작 = 날들[max(0, 자리 - 일수)]
    ds, vs = t
    i = bisect.bisect_left(ds, 시작)
    j = bisect.bisect_right(ds, 날짜8)
    if i >= j:
        return 0.0
    return sum(vs[i:j])


def _상장주식수():
    """종목코드 -> 상장주식수(float). 임원 매매를 종목 크기로 나누는 데 쓴다"""
    표 = {}
    p = os.path.join(_DATA, "stock-base.json")
    if not os.path.exists(p):
        return 표
    try:
        j = json.load(io.open(p, encoding="utf-8-sig"))
    except ValueError:
        return 표
    for c, v in (j.get("종목") or {}).items():
        n = _숫(v.get("상장주식수"))
        if n and n > 0:
            표[c] = n
    return 표


# ── ④ 뉴스 ────────────────────────────────────────────────────
def _뉴스표():
    """종목코드 -> (정렬된 날짜8, 호재점수, 악재점수) — 건수는 날짜 개수로 센다"""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "news", "*.json")):
        code = os.path.basename(f)[:-5]
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        벌 = []
        for x in (j.get("뉴스") or []):
            d8 = _날8(x.get("날짜"))
            if len(d8) != 8:
                continue
            제 = str(x.get("제목") or "")
            호 = sum(1 for w in _호재말 if w in 제)
            악 = sum(1 for w in _악재말 if w in 제)
            벌.append((d8, 호, 악))
        if 벌:
            벌.sort()
            표[code] = ([z[0] for z in 벌], [z[1] for z in 벌], [z[2] for z in 벌])
    return 표


def _뉴스재기(표, code, 날짜8, 일수, 날들, 자리):
    """(건수, 호재 수, 악재 수) — 없으면 None"""
    t = 표.get(code)
    if not t:
        return None
    시작 = 날들[max(0, 자리 - 일수)]
    ds, 호s, 악s = t
    i = bisect.bisect_left(ds, 시작)
    j = bisect.bisect_right(ds, 날짜8)
    return (j - i, sum(호s[i:j]), sum(악s[i:j]))


# ── 붙이기 ─────────────────────────────────────────────────────
def 붙이기(사건, 날들, 뉴스포함=True, 찍기=print):
    r"""사건 dict 에 새 재료를 더하고 **붙은 재료 이름 목록**을 돌려준다.

    사건은 `{"인": <날 배열 자리>, "code": ...}` 를 들고 있어야 한다.
    ⚠️ 「인」은 **매수일** 자리다(신호 다음 날). 재료는 **신호일(인-1)** 까지만 본다 —
       매수일 아침에 알 수 있는 것만 써야 앞을 훔쳐보지 않는다
    """
    붙은 = []
    if not 사건:
        return 붙은

    # ① 공시 시각
    찍기("    공시 시각(kind-time × dart-daily) 잇는 중...")
    공시 = _공시시각표(날들)
    if 공시:
        for x in 사건:
            i = x["인"] - 1                      # 신호일
            d8 = 날들[i] if 0 <= i < len(날들) else None
            중, 후 = (공시.get(d8) or {}).get(x["code"], (0, 0)) if d8 else (0, 0)
            x["공시장중"] = float(중)
            x["공시장후"] = float(후)
            x["공시건수"] = float(중 + 후)
        붙은 += ["공시장중", "공시장후", "공시건수"]
        찍기(f"      {len(공시):,}일 · 사건에 붙임")

    # ② 임원 매매 — 증감 주수를 **상장주식수 대비 %** 로
    #    ⚠️ 주수 그대로 두면 오분위 위 20% 를 대형주가 독식한다 —
    #       삼성전자 5,000주와 소형주 5,000주는 뜻이 다르다
    찍기("    임원 매매(dart-exec) 붙이는 중...")
    주식수 = _상장주식수()
    임원 = _이력표("dart-exec", lambda x: _숫(x.get("증감")))
    if 임원:
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if not d8:
                continue
            발 = 주식수.get(x["code"])
            for 일, 이름 in ((20, "임원매수율20"), (60, "임원매수율60")):
                v = _최근합(임원, x["code"], d8, 일, 날들, i)
                if v is not None and 발:
                    x[이름] = v / 발 * 100
                elif v is not None:
                    x[이름] = 0.0
        붙은 += ["임원매수율20", "임원매수율60"]
        찍기(f"      {len(임원):,}종목 · 상장주식수 {len(주식수):,}개로 정규화")

    # ③ 대주주 — 지분율 **증감** 합
    찍기("    대주주 보고(dart-major) 붙이는 중...")
    def _지분변화(x):
        # ⚠️⚠️ 「직전지분율」은 **이름이 잘못 붙은 것**이다 (2026-09-14 밤 발견).
        #    DART `stkrt_irds` 는 increase/decrease = **증감**이라 그대로 쓴다.
        #    「지분율 − 직전지분율」로 읽으면 20.08 − 0.00 이 매번 더해져
        #    대주주 변화가 **141%p** 로 나왔다 (collect_major.py 도 같이 고쳤다)
        v = _숫(x.get("증감지분율"))
        return v if v is not None else _숫(x.get("직전지분율"))
    대주주 = _이력표("dart-major", _지분변화)
    if 대주주:
        for x in 사건:
            i = x["인"] - 1
            d8 = 날들[i] if 0 <= i < len(날들) else None
            if d8:
                x["대주주변화60"] = _최근합(대주주, x["code"], d8, 60, 날들, i)
        붙은 += ["대주주변화60"]
        찍기(f"      {len(대주주):,}종목")

    # ④ 뉴스 — 1년치뿐이라 기본은 붙이되, 오분위에서 걸러진다
    if 뉴스포함:
        찍기("    뉴스(news) 붙이는 중...")
        뉴스 = _뉴스표()
        if 뉴스:
            for x in 사건:
                i = x["인"] - 1
                d8 = 날들[i] if 0 <= i < len(날들) else None
                if not d8:
                    continue
                a = _뉴스재기(뉴스, x["code"], d8, 5, 날들, i)
                b = _뉴스재기(뉴스, x["code"], d8, 20, 날들, i)
                if a:
                    x["뉴스5"], x["뉴스호재5"], x["뉴스악재5"] = (
                        float(a[0]), float(a[1]), float(a[2]))
                if b:
                    x["뉴스20"] = float(b[0])
            붙은 += ["뉴스5", "뉴스20", "뉴스호재5", "뉴스악재5"]
            찍기(f"      {len(뉴스):,}종목 (⚠️ 약 1년치 — 옛 사건은 빈 값)")
    return 붙은


if __name__ == "__main__":
    print(__doc__)
