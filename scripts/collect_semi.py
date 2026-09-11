#!/usr/bin/env python3
r"""
collect_semi.py — **미국 반도체 개별종목** (Yahoo Finance) (2026-09-03 신설)

⚠️⚠️ **사용자 지목.** 목적이 분명해서 받는다 (「있으니까」가 아니라)
   *"미국 개별 반도체 종목이랑 한국 반도체 개별종목과의 연관관계도 테스트해보면
     좋을 것 같아. 직접 계약 관계, 투자 관계, 벨류체인 등등이 있으니까"*

## 왜 지수로는 안 되나
```
SOXX(반도체 지수)는 **30개를 뭉갠 값**이다.
그런데 실제 연결은 **종목 대 종목**이다:
   마이크론(MU)  ↔ SK하이닉스     메모리 **직접 경쟁·같은 사이클**
   엔비디아(NVDA) ↔ SK하이닉스     HBM을 **엔비디아가 사 간다**
   TSMC(TSM)    ↔ 삼성전자       파운드리 **직접 경쟁**
   AMAT·LRCX·KLA ↔ 원익IPS·주성엔지니어링  **같은 장비를 판다**
   ASML         ↔ 국내 장비 전반   **노광 독점 · 투자 사이클의 머리**
⇒ 지수로 뭉개면 이 결이 안 보인다
```

## 받는 것 (28종목)
```
설계·종합  NVDA AMD INTC QCOM AVGO TXN ADI MRVL NXPI ON MCHP STM ARM
메모리    MU WDC STX          ← ⭐ 하이닉스와 **같은 사이클**
파운드리   TSM GFS UMC        ← ⭐ 삼성과 **직접 경쟁**
장비      AMAT LRCX KLAC ASML TER ONTO ACLS  ← ⭐ 국내 장비주의 **선행**
소재      ENTG MKSI
```
⚠️ 시차: 미국 T-1일 밤 종가는 한국 T일 **새벽 06:00** 확정 → 08:00 브리핑이 안다

저장: `data/yahoo/{심볼}.json` (기존 지표와 같은 자리·같은 꼴)
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
OUT = os.path.join(_BASE, "data", "yahoo")
LOG = os.path.join(_BASE, "data", "_yahoo.log")
_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

반도체 = (
    # ── 메모리 (⭐ SK하이닉스와 같은 사이클) ──
    ("MU", "마이크론⭐"), ("WDC", "웨스턴디지털"), ("STX", "씨게이트"),
    # ── 파운드리 (⭐ 삼성전자와 직접 경쟁) ──
    ("TSM", "TSMC⭐"), ("UMC", "UMC"), ("GFS", "글로벌파운드리"),
    # ── 설계·종합 ──
    ("NVDA", "엔비디아⭐"), ("AMD", "AMD"), ("INTC", "인텔"),
    ("QCOM", "퀄컴"), ("AVGO", "브로드컴"), ("TXN", "TI"),
    ("ADI", "아나로그디바이스"), ("MRVL", "마벨"), ("NXPI", "NXP"),
    ("ON", "온세미"), ("MCHP", "마이크로칩"), ("STM", "ST마이크로"),
    ("ARM", "ARM"),
    # ── 장비 (⭐ 국내 장비주의 선행) ──
    ("AMAT", "어플라이드⭐"), ("LRCX", "램리서치⭐"), ("KLAC", "KLA⭐"),
    ("ASML", "ASML⭐"), ("TER", "테라다인"), ("ONTO", "온투이노베이션"),
    ("ACLS", "액셀리스"),
    # ── 소재 ──
    ("ENTG", "엔테그리스"), ("MKSI", "MKS인스트루먼트"),
)


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 받(심볼, 부터년=1995):
    p1 = int(dt.datetime(부터년, 1, 1).timestamp())
    p2 = int(dt.datetime.now().timestamp())
    u = (f"https://query2.finance.yahoo.com/v8/finance/chart/{심볼}"
         f"?period1={p1}&period2={p2}&interval=1d")
    with urllib.request.urlopen(urllib.request.Request(u, headers=_H),
                                timeout=40) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        raise RuntimeError(str((d.get("chart") or {}).get("error"))[:120])
    ts = res[0].get("timestamp") or []
    q = ((res[0].get("indicators") or {}).get("quote") or [{}])[0]
    cl = q.get("close") or []
    vol = q.get("volume") or []
    종, 량 = {}, {}
    for i, t in enumerate(ts):
        c = cl[i] if i < len(cl) else None
        if c is None:
            continue
        d8 = dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y%m%d")
        종[d8] = float(c)
        v = vol[i] if i < len(vol) else None
        if v is not None:
            량[d8] = float(v)
    # ⚠️⚠️ **가장 최근 일봉이 비어 있는 일이 잦다** (2026-09-04 실측)
    #    Yahoo가 일봉을 확정하기 전에는 close가 None이다.
    #    그런데 meta에는 마감가가 이미 들어 있다.
    #    ⇒ 이걸 안 채우면 **아침 브리핑에서 「어젯밤 미국」을 못 쓴다.**
    #       보조 전략이 통째로 못 돈다
    #    ⚠️ 장중(REGULAR·PRE)이면 그건 종가가 아니라 현재가라 **쓰지 않는다**
    meta = res[0].get("meta") or {}
    상태 = str(meta.get("marketState") or "").upper()
    끝값 = meta.get("regularMarketPrice")
    끝시 = meta.get("regularMarketTime")
    if 끝값 and 끝시 and 상태 in ("CLOSED", "POST", "POSTPOST", "PREPRE", ""):
        d8 = dt.datetime.fromtimestamp(int(끝시), dt.UTC).strftime("%Y%m%d")
        if d8 not in 종:
            종[d8] = float(끝값)
    return 종, 량


def main():
    심볼들 = 반도체
    if "--심볼" in sys.argv:
        골 = [s.strip().upper()
              for s in sys.argv[sys.argv.index("--심볼") + 1].split(",")]
        심볼들 = tuple((s, "") for s in 골)
    os.makedirs(OUT, exist_ok=True)
    찍기(f"===== 미국 반도체 개별 · {len(심볼들)}종목 =====")
    ok = 실패 = 0
    for 심, 이름 in 심볼들:
        p = os.path.join(OUT, 심.replace("^", "IDX_") + ".json")
        옛 = {}
        if os.path.exists(p):
            try:
                옛 = json.load(io.open(p, encoding="utf-8-sig"))
            except Exception:
                옛 = {}
        try:
            종, 량 = 받(심)
        except urllib.error.HTTPError as e:
            실패 += 1
            찍기(f"  ⚠️ {심}: HTTP {e.code}")
            time.sleep(2)
            continue
        except Exception as e:
            실패 += 1
            찍기(f"  ⚠️ {심}: {type(e).__name__} {str(e)[:80]}")
            time.sleep(2)
            continue
        if not 종:
            실패 += 1
            찍기(f"  ⚠️ {심}: 빈 응답")
            continue
        옛종 = 옛.get("종가") or {}
        옛종.update(종)
        옛량 = 옛.get("거래량") or {}
        옛량.update(량)
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"심볼": 심, "이름": 이름 or 옛.get("이름", ""), "갈래": "반도체개별",
             "받은날": dt.date.today().strftime("%Y%m%d"),
             "종가": 옛종, "거래량": 옛량}, ensure_ascii=False))
        k = sorted(옛종)
        ok += 1
        찍기(f"  {심:<7}{이름:<18}{k[0]} ~ {k[-1]} · {len(옛종):,}일")
        time.sleep(0.5)
    찍기(f"  끝 · 받음 {ok} · 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
