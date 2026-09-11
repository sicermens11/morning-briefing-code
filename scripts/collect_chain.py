#!/usr/bin/env python3
r"""
collect_chain.py — **글로벌 반도체 밸류체인 전수** (Yahoo Finance) (2026-09-03 신설)

⚠️⚠️ **사용자 지목.**
   *"밸류체인맵 이미 갖고 있지만, 글로벌하게 더 넓은 범위로, 탄탄하게 자세히
     꼼꼼히 조사해보자."*

## 왜 미국만으로는 부족한가
```
한국 장비주의 진짜 상대는 **미국이 아니라 일본**인 경우가 많다
   도쿄일렉트론(8035.T)  세계 3위 장비. **원익IPS·주성엔지니어링과 같은 걸 판다**
   어드반테스트(6857.T)  테스터 1위. **테스·유니셈과 직결**
   신에츠(4063.T)·SUMCO(3436.T)  웨이퍼 1·2위. **SK실트론의 상대**
   레이저텍(6920.T)     EUV 검사 독점. **파크시스템스·넥스틴의 상대**

유럽도 빠져 있었다
   ASM인터내셔널(ASM.AS)  ALD 1위. **원익IPS·주성엔지니어링의 직접 경쟁자**
   BESI(BESI.AS)        후공정 본더. **한미반도체의 **직접 경쟁자**** ⭐⭐
   인피니언(IFX.DE)      전력반도체
```
⭐⭐ **BESI는 한미반도체의 직접 경쟁자다.** HBM 본더 시장을 둘이 나눈다.
   이건 지수로는 절대 안 보이는 관계다.

## ⚠️⚠️ 시차를 반드시 지킨다 (브리핑은 한국 08:00)
```
✅ 당일 새벽 값을 쓸 수 있다
   미국(새벽 06:00) · 유럽(새벽 01:00)
⚠️ **하루 늦게** 써야 한다 — 한국과 같은 시간대라 아직 안 끝났다
   일본(15:00) · 대만(13:30) · 중국(15:00) · 홍콩(16:00)
⇒ 일본·대만 종목은 **T-1일 종가**만 T일 브리핑에 쓸 수 있다
```

## ⚠️ 환율 주의
```
일본 종목은 **엔화**, 유럽은 **유로**로 매겨진다.
등락률만 쓰면 환율 영향이 섞인다.
⇒ 상관을 잴 때는 **현지 통화 등락률**이 그 나라 업황을 더 잘 나타낸다고 보고
   그대로 쓴다. 다만 **환율 변동이 큰 날**은 따로 표시해 확인한다
```

저장: `data/yahoo/{심볼}.json` (`.`은 `_`로 바꿔 파일명으로 쓴다)
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

# (심볼, 이름, 나라, 밸류체인 위치, 시차)
#   시차 "당일" = T일 새벽에 확정 → T일 브리핑에 쓸 수 있다
#   시차 "하루" = 한국과 같은 시간대 → T-1일 값만 쓸 수 있다
목록 = (
    # ══ 일본 — 한국 장비·소재주의 **진짜 상대** ══
    ("8035.T", "도쿄일렉트론⭐", "일본", "장비", "하루"),
    ("6857.T", "어드반테스트⭐", "일본", "장비-테스터", "하루"),
    ("6920.T", "레이저텍⭐", "일본", "장비-검사", "하루"),
    ("7735.T", "스크린홀딩스", "일본", "장비-세정", "하루"),
    ("6146.T", "디스코⭐", "일본", "장비-절단", "하루"),
    ("6501.T", "히타치", "일본", "장비", "하루"),
    ("4063.T", "신에츠화학⭐", "일본", "소재-웨이퍼", "하루"),
    ("3436.T", "SUMCO⭐", "일본", "소재-웨이퍼", "하루"),
    ("4183.T", "미쓰이화학", "일본", "소재", "하루"),
    ("6963.T", "로옴", "일본", "설계-전력", "하루"),
    ("6723.T", "르네사스", "일본", "설계-MCU", "하루"),
    ("6762.T", "TDK", "일본", "부품", "하루"),
    ("6981.T", "무라타", "일본", "부품-MLCC", "하루"),
    # ══ 대만 — 한국과 산업 구조가 가장 비슷하다 ══
    ("2330.TW", "TSMC(대만상장)⭐", "대만", "파운드리", "하루"),
    ("2454.TW", "미디어텍⭐", "대만", "설계", "하루"),
    ("2317.TW", "폭스콘", "대만", "조립", "하루"),
    ("3711.TW", "ASE⭐", "대만", "후공정", "하루"),
    ("2303.TW", "UMC(대만상장)", "대만", "파운드리", "하루"),
    ("3034.TW", "노바텍", "대만", "설계-디스플레이", "하루"),
    ("2408.TW", "난야테크⭐", "대만", "메모리", "하루"),
    ("3037.TW", "유니마이크론", "대만", "부품-기판", "하루"),
    # ══ 유럽 — ⭐ 새벽 01:00에 끝난다. **당일 쓸 수 있다** ══
    ("ASM.AS", "ASM인터내셔널⭐", "네덜란드", "장비-ALD", "당일"),
    ("BESI.AS", "BESI⭐⭐", "네덜란드", "장비-본더", "당일"),
    ("IFX.DE", "인피니언", "독일", "설계-전력", "당일"),
    ("AMS.SW", "ams오스람", "스위스", "설계-센서", "당일"),
    ("SOI.PA", "소이텍", "프랑스", "소재-웨이퍼", "당일"),
    # ══ 중국 ══
    ("0981.HK", "SMIC⭐", "중국", "파운드리", "하루"),
    ("1347.HK", "화훙반도체", "중국", "파운드리", "하루"),
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
    meta = res[0].get("meta") or {}
    ts = res[0].get("timestamp") or []
    q = ((res[0].get("indicators") or {}).get("quote") or [{}])[0]
    cl = q.get("close") or []
    종 = {}
    for i, t in enumerate(ts):
        c = cl[i] if i < len(cl) else None
        if c is None:
            continue
        # ⚠️ 아시아·유럽은 현지 장 마감 시각이라 UTC 날짜가 하루 밀릴 수 있다.
        #    거래소 시간대로 되돌려 날짜를 잡는다
        오프 = meta.get("gmtoffset") or 0
        d8 = dt.datetime.fromtimestamp(t + 오프, dt.UTC).strftime("%Y%m%d")
        종[d8] = float(c)
    return 종, meta.get("currency") or ""


def main():
    os.makedirs(OUT, exist_ok=True)
    찍기(f"===== 글로벌 반도체 밸류체인 · {len(목록)}종목 =====")
    ok = 실패 = 0
    난 = []
    for 심, 이름, 나라, 위치, 시차 in 목록:
        p = os.path.join(OUT, 심.replace(".", "_").replace("^", "IDX_")
                         + ".json")
        옛 = {}
        if os.path.exists(p):
            try:
                옛 = json.load(io.open(p, encoding="utf-8-sig"))
            except Exception:
                옛 = {}
        try:
            종, 통화 = 받(심)
        except urllib.error.HTTPError as e:
            실패 += 1
            난.append(f"{이름}({심}) HTTP {e.code}")
            찍기(f"  ⚠️ {심:<10}{이름:<16}HTTP {e.code}")
            time.sleep(2)
            continue
        except Exception as e:
            실패 += 1
            난.append(f"{이름}({심}) {type(e).__name__}")
            찍기(f"  ⚠️ {심:<10}{이름:<16}{type(e).__name__} {str(e)[:60]}")
            time.sleep(2)
            continue
        if not 종:
            실패 += 1
            난.append(f"{이름}({심}) 빈 응답")
            찍기(f"  ⚠️ {심:<10}{이름:<16}빈 응답")
            continue
        옛종 = 옛.get("종가") or {}
        옛종.update(종)
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"심볼": 심, "이름": 이름, "나라": 나라, "위치": 위치,
             "시차": 시차, "통화": 통화, "갈래": "밸류체인",
             "받은날": dt.date.today().strftime("%Y%m%d"),
             "종가": 옛종}, ensure_ascii=False))
        k = sorted(옛종)
        ok += 1
        찍기(f"  {심:<10}{이름:<16}{나라:<6}{위치:<14}{시차}  "
             f"{k[0]} ~ {k[-1]} · {len(옛종):,}일 · {통화}")
        time.sleep(0.5)
    찍기(f"  끝 · 받음 {ok} · 실패 {실패}")
    if 난:
        찍기("  ⚠️ 못 받은 것: " + " / ".join(난))
    return 0


if __name__ == "__main__":
    sys.exit(main())
