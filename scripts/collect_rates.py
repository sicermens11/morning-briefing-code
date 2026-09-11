#!/usr/bin/env python3
r"""
collect_rates.py — **금리·거시 (FRED · 키 불필요)** (2026-09-03 신설)

⚠️⚠️ **사용자 지목.** *"금리는 필요하지 않아? 국채금리, 중앙은행 금리!
   지금 한참 금리 인상으로 화제니까 미국의 FOMC, 고용발표 등등"*

## 지금까지 뭘 놓쳤나
```
✅ 재본 것    미국 국채 **하루 변동**
             -> 변화율로 재서 **가짜**였고(88차), bp로 다시 재도 약했다(88b)
❌ 안 재본 것  **금리 수준** (2%일 때와 5%일 때 시장이 다르다)
             **인상/인하 국면**  ← 지금 화제인 그것
             **한국 기준금리·국고채**
             **한미 금리차** (외국인 자금이 여기 반응한다)
             **장단기 역전** (10년물 < 2년물 = 침체 신호)
             **FOMC 결정일 · 고용발표일** 자체
⇒ 하루 변동은 잡음이지만 **국면**은 다른 이야기다
```

⚠️ **FRED는 한 번 실패했다가 두 번째에 열렸다.** 일시적 장애였다.
   「두세 곳 두드리고 없다고 하기」를 다섯 번 했다. 한 번 실패로 결론내지 않는다.

## 받는 것
```
미국 정책금리  DFF(일별 1954~) · DFEDTARU/DFEDTARL(목표 상·하단 2008~)
              ⇒ **목표금리가 바뀐 날 = 인상·인하 결정일**
미국 국채     DGS1MO DGS3MO DGS1 DGS2 DGS5 DGS10 DGS30 (1976~)
장단기 역전    T10Y2Y · T10Y3M    ← **침체 신호**
위험선호      BAMLH0A0HYM2 (하이일드 스프레드)  ← 겁먹으면 벌어진다
한국          IRLTLT01KRM156N(장기금리 월별 2000~) · IR3TIB01KRM156N(3개월 1991~)
미국 고용·물가  UNRATE(실업률) · PAYEMS(비농업고용) · CPIAUCSL · CPILFESL
```
⚠️ **시차** — 미국 지표는 발표 시각이 한국 밤~새벽이라 다음 거래일부터 쓴다.
   FRED 날짜는 **관측일**이지 발표일이 아니다. 월별 지표는 **다음 달**부터 써야
   안전하다 (91차에서 그렇게 처리한다)

저장: `data/fred/{시리즈}.json` -> `{"시리즈":.., "값": {YYYYMMDD: 값}}`
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "fred")
LOG = os.path.join(_BASE, "data", "_fred.log")
_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

목록 = (
    # ── 미국 정책금리 ──
    ("DFF", "미국 기준금리(실효)", "일별"),
    ("DFEDTARU", "연준 목표 상단", "일별"),
    ("DFEDTARL", "연준 목표 하단", "일별"),
    ("DFEDTAR", "연준 목표(옛)", "일별"),
    # ── 미국 국채 ──
    ("DGS1MO", "미국 1개월", "일별"), ("DGS3MO", "미국 3개월", "일별"),
    ("DGS1", "미국 1년", "일별"), ("DGS2", "미국 2년⭐", "일별"),
    ("DGS5", "미국 5년", "일별"), ("DGS10", "미국 10년⭐", "일별"),
    ("DGS30", "미국 30년", "일별"),
    # ── 장단기 역전 (침체 신호) ──
    ("T10Y2Y", "장단기차 10Y-2Y⭐", "일별"),
    ("T10Y3M", "장단기차 10Y-3M⭐", "일별"),
    # ── 위험선호 ──
    ("BAMLH0A0HYM2", "하이일드 스프레드⭐", "일별"),
    ("VIXCLS", "VIX(참고)", "일별"),
    ("DTWEXBGS", "달러인덱스(광의)", "일별"),
    # ── 한국 ──
    ("IRLTLT01KRM156N", "한국 장기금리⭐", "월별"),
    ("IR3TIB01KRM156N", "한국 3개월⭐", "월별"),
    ("KORCPIALLMINMEI", "한국 CPI", "월별"),
    # ── 미국 고용·물가 (사용자가 「고용발표」 언급) ──
    ("UNRATE", "미국 실업률", "월별"),
    ("PAYEMS", "미국 비농업고용⭐", "월별"),
    ("CPIAUCSL", "미국 CPI", "월별"),
    ("CPILFESL", "미국 근원CPI", "월별"),
)


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 받(sid, 시도=4):
    """⚠️⚠️ FRED는 **빨리 두드리면 막는다.**
    2026-09-03 실측: 6번 연속 성공 -> 그 뒤 전부 TimeoutError·ConnectionReset.
    그래서 사이를 크게 벌리고, 실패하면 더 크게 벌려 다시 두드린다."""
    u = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    마지막 = None
    for t in range(시도):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(u, headers=_H), timeout=45) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            마지막 = e
            time.sleep(30 * (t + 1))    # 30초 -> 60 -> 90
    raise 마지막


def main():
    심들 = 목록
    if "--시리즈" in sys.argv:
        골 = [s.strip() for s in
              sys.argv[sys.argv.index("--시리즈") + 1].split(",")]
        심들 = tuple((s, "", "") for s in 골)
    os.makedirs(OUT, exist_ok=True)
    찍기(f"===== FRED 금리·거시 · {len(심들)}개 =====")
    ok = 실패 = 0
    난 = []
    for sid, 이름, 주기 in 심들:
        try:
            t = 받(sid)
        except Exception as e:
            실패 += 1
            난.append(f"{이름 or sid}({sid})")
            찍기(f"  ⚠️ {sid:<18}{이름:<20}{type(e).__name__} {str(e)[:50]}")
            continue
        값 = {}
        for 줄 in t.splitlines()[1:]:
            부 = 줄.split(",")
            if len(부) < 2:
                continue
            d, v = 부[0].strip(), 부[1].strip()
            if v in ("", ".", "NA"):
                continue      # ⚠️ FRED는 휴일을 "."으로 준다
            try:
                값[d.replace("-", "")] = float(v)
            except ValueError:
                continue
        if not 값:
            실패 += 1
            난.append(f"{이름 or sid}({sid}) 값 없음")
            찍기(f"  ⚠️ {sid:<18}{이름:<20}값이 하나도 없다")
            continue
        p = os.path.join(OUT, sid + ".json")
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"시리즈": sid, "이름": 이름, "주기": 주기,
             "받은날": dt.date.today().strftime("%Y%m%d"), "값": 값},
            ensure_ascii=False))
        k = sorted(값)
        ok += 1
        찍기(f"  {sid:<18}{이름:<20}{주기:<5}{k[0]} ~ {k[-1]} · "
             f"{len(값):,}개")
        time.sleep(20)    # ⚠️ 막히지 않게 크게 쉰다
    찍기(f"  끝 · 받음 {ok} · 실패 {실패}")
    if 난:
        찍기("  ⚠️ 못 받은 것: " + " / ".join(난))
    return 0


if __name__ == "__main__":
    sys.exit(main())
