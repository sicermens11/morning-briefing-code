#!/usr/bin/env python3
r"""
collect_minute.py — **후보 종목의 그날 1분봉을 모은다** (2026-09-16 신설 · 사용자 「앞으로 모을지 정하실 것은 모으자!」)

## 왜
```
모든 규칙이 일봉과 08:55 한 점으로 판정한다. 「09:30 에 사면」「장중 −5% 면 판다」는
분봉 없이는 못 잰다. 과거 분봉은 어디서도 안 준다(네이버는 최근 7거래일뿐 · 09-16 확인)
⇒ 오늘부터 매일 남기면 반년 뒤 답이 나온다
```
## 무엇을
```
종목 = 오늘 forward-log 후보(규칙매수 포함) + 산것 + 섹터 브리핑 픽 + 표본(자동)
출처 = 네이버 fchart 1분봉 (timeframe=minute · 공개 API · 사용자 결정 「네이버 유지」)
저장 = data/minute/{YYYYMMDD}.json   {code: [[HHMM, 시가, 고가, 저가, 종가, 거래량], …]}
```
⚠️ 조회만 한다 · 하루 한 번(저녁) · 종목당 1회 · 0.2초 간격
⚠️ 네이버가 최근 7거래일치를 주므로, 빠진 날이 있으면 **그 날짜도 같이 채운다** (멱등)

쓰는 법:
    python scripts\collect_minute.py            오늘(과 빠진 최근 며칠)
    python scripts\collect_minute.py --보기     종목 수만
"""
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "minute")
LOGF = os.path.join(_BASE, "data", "_minute.log")
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOGF, "a", encoding="utf-8") as fp:
            fp.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass


def _종목들():
    codes = {}
    p = os.path.join(_BASE, "data", "forward-log.jsonl")
    if os.path.exists(p):
        rows = []
        for z in io.open(p, encoding="utf-8"):
            try:
                rows.append(json.loads(z))
            except ValueError:
                pass
        for r in rows[-2:]:                       # 오늘·어제 줄
            for x in (r.get("후보") or []):
                codes[x.get("종목코드")] = "후보"
            for x in (r.get("산것") or []):
                c = x.get("종목코드") or x.get("code")
                if c:
                    codes[c] = "산것"
            for c in ((r.get("동시호가") or {}).get("자동") or {}):
                codes.setdefault(c, "표본")
    p2 = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
    if os.path.exists(p2):
        last = None
        for z in io.open(p2, encoding="utf-8"):
            if z.strip():
                last = z
        if last:
            try:
                for x in (json.loads(last).get("picks") or []):
                    if x.get("code"):
                        codes[x["code"]] = "섹터픽"
            except ValueError:
                pass
    codes.pop(None, None)
    return codes


def _분봉(code):
    u = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=minute&count=3000&requestType=0"
    r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=15).read().decode("euc-kr", "replace")
    out = {}
    # ⚠️ 1분봉은 시·고·저가 null 이고 **종가·거래량만** 온다 (09-16 실측: "202609080900|null|null|null|271500|286916")
    def _n(z):
        return None if z in ("null", "") else float(z)
    for m in re.finditer(r'data="(\d{8})(\d{4})\|([\d.]+|null)\|([\d.]+|null)\|([\d.]+|null)\|([\d.]+|null)\|([\d.]+|null)"', r):
        d8, hm, o, h, l, c, v = m.groups()
        out.setdefault(d8, []).append([hm, _n(o), _n(h), _n(l), _n(c), _n(v)])
    return out


def main():
    보기만 = "--보기" in sys.argv
    codes = _종목들()
    찍기(f"===== 분봉 수집 — 종목 {len(codes)}개 =====")
    if 보기만 or not codes:
        찍기("  " + ", ".join(f"{k} {v}" for k, v in sorted({v: 0 for v in codes.values()}.items())) if codes else "  종목 없음")
        return 0
    os.makedirs(OUT, exist_ok=True)
    날별 = {}
    for f in os.listdir(OUT):
        if f.endswith(".json"):
            try:
                날별[f[:8]] = json.load(io.open(os.path.join(OUT, f), encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
    ok = 실패 = 0
    새 = {}
    for i, (code, 왜) in enumerate(sorted(codes.items()), 1):
        try:
            표 = _분봉(code)
        except Exception as e:  # noqa: BLE001
            실패 += 1
            찍기(f"    ⚠️ {code} 실패 {type(e).__name__}")
            continue
        for d8, bars in 표.items():
            if code not in 날별.get(d8, {}):
                날별.setdefault(d8, {})[code] = bars
                새[d8] = 새.get(d8, 0) + 1
        ok += 1
        time.sleep(0.2)
    for d8, n in sorted(새.items()):
        with io.open(os.path.join(OUT, f"{d8}.json"), "w", encoding="utf-8") as fp:
            json.dump(날별[d8], fp, ensure_ascii=False)
    찍기(f"  끝 — 성공 {ok} · 실패 {실패} · 새로 채운 것 " + (" · ".join(f"{d} {n}종목" for d, n in sorted(새.items())) or "없음"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
