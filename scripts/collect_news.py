#!/usr/bin/env python3
r"""
collect_news.py — **종목별 뉴스 제목을 받는다 (네이버 금융)** (2026-09-03 신설)

⚠️⚠️ **빅카인즈가 막혔다.** OPEN API가 유료로 전환되어 신청 기능이 중단됐다
   (2026-09-03 사용자 확인). 대안을 찾았다.

## 왜 네이버 금융 종목뉴스인가 (2026-09-03 실측)
```
✅ `api.stock.naver.com/news/stock/{종목코드}`  **키가 필요 없다**
✅ 페이지를 넘기면 과거로 간다 (삼성전자 p1=20260903 · p50=20260901)
✅ 종목에 **정확히 붙어 있다** (검색어 매칭이 아니라 종목 페이지의 뉴스다)
❌ FMP 뉴스 = 402 유료 · 빅카인즈 = 유료 전환 · GDELT = 연결 실패
⚠️ 대형주는 뉴스가 많아 과거로 가려면 페이지가 많다
⭐ **우리 신호 종목은 소형주라 뉴스가 적다** — 훨씬 적은 페이지로 간다
```

## ⚠️ 무엇을 재려는 건가 — 73차에서 못 잰 부분
```
73차에서 잰 것   **거래대금 배수** = 「관심의 **양**」
                -> 급증할수록 나빴다 (10배 이상 -1.49% · 승률 41.3%)
73차에서 **못** 잰 것  **뉴스 내용이 호재냐 악재냐**
                -> 제목이 있어야 가를 수 있다. 그게 이 수집의 목적이다
```

⚠️ **본문은 안 받는다.** 제목만으로 충분하고, 본문은 저작권 문제가 있다.
⚠️ 요청 간격을 지킨다(0.3초). 한 곳을 몰아치지 않는다.

저장: `data/news/{종목코드}.json` → `{"종목":..., "뉴스": [{날짜, 제목, 언론사}]}`

쓰는 법:
    python scripts\collect_news.py --확인                 # 3종목 시험
    python scripts\collect_news.py --목록 신호종목         # 신호가 났던 종목만
    python scripts\collect_news.py --쪽 20                # 종목당 최대 20쪽
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "news")
LOG = os.path.join(_BASE, "data", "_news.log")
_H = {"User-Agent": "Mozilla/5.0"}
_쉼 = 0.3


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 한쪽(code, page):
    u = (f"https://api.stock.naver.com/news/stock/{code}"
         f"?pageSize=20&page={page}")
    with urllib.request.urlopen(urllib.request.Request(u, headers=_H),
                                timeout=25) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    out = []
    # ⚠️ 응답이 **[{items:[...]}, ...]** 꼴이다 (묶음의 배열)
    묶음들 = d if isinstance(d, list) else [d]
    for 묶 in 묶음들:
        for x in (묶.get("items") or []):
            t = (x.get("title") or "").strip()
            # HTML 엔티티를 되돌린다
            t = (t.replace("&quot;", '"').replace("&amp;", "&")
                  .replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&apos;", "'").replace("&#039;", "'"))
            t = re.sub(r"<[^>]+>", "", t)
            dtm = str(x.get("datetime") or "")
            if len(dtm) >= 8 and t:
                out.append({"날짜": dtm[:8], "시각": dtm[8:12],
                            "제목": t, "언론사": x.get("officeName")})
    return out


def 종목받기(code, 최대쪽):
    본 = {}
    빈쪽 = 0
    for p in range(1, 최대쪽 + 1):
        try:
            a = 한쪽(code, p)
        except urllib.error.HTTPError as e:
            if e.code in (429, 403):
                찍기(f"  ⚠️ {code} p{p}: HTTP {e.code} — 잠시 쉰다")
                time.sleep(5)
                continue
            break
        except Exception:
            break
        if not a:
            빈쪽 += 1
            if 빈쪽 >= 2:
                break
            continue
        빈쪽 = 0
        for x in a:
            본[(x["날짜"], x["시각"], x["제목"][:40])] = x
        time.sleep(_쉼)
    return sorted(본.values(), key=lambda z: (z["날짜"], z["시각"]))


def 신호종목목록():
    """pick_now가 뽑은 종목 전부. `picknow*` 파일을 모두 읽는다.
    ⚠️ 하루 2종목 상한을 푼 `_all` 판까지 읽어야 표본이 넓어진다 (30건 -> 134건)."""
    코드 = []
    for p in sorted(glob.glob(os.path.join(_BASE, "data", "_labs",
                                           "*picknow*.txt"))):
        for line in io.open(p, encoding="utf-8"):
            m = re.match(r"\s+(\d{8})\s+(\d{6})\s", line)
            if m:
                코드.append(m.group(2))
    return sorted(set(코드))


def 후보종목목록():
    r"""⭐ **forward-log 에 오른 종목** (2026-09-10 신설 · 사용자 결정 ㉡).

    ```
    전   `--밴드` 로 시총 500~2,000억 **2,410종목** 전부 -> 매일 **4시간**
    후   퀀트 후보로 **나온 종목만** -> 하루 40개 안팎 -> **몇 분**
    ```
    ⚠️ `신호종목목록()` 은 옛 `picknow*.txt` 를 읽어 **낡았다**.
       지금은 `record_pick.py` 가 `forward-log.jsonl` 에 후보를 쌓는다
    """
    로그 = os.path.join(_BASE, "data", "forward-log.jsonl")
    코드 = set()
    if not os.path.exists(로그):
        return []
    for line in io.open(로그, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        for 칸 in ("후보", "산것"):
            for h in (d.get(칸) or []):
                c = h.get("종목코드")
                if c:
                    코드.add(str(c))
    return sorted(코드)


def 밴드종목목록():
    r"""시총 500~2,000억에 **한 번이라도** 든 종목 (백테스트가 훑는 우주)"""
    import glob as _g
    밴드 = set()
    날들 = sorted(_g.glob(os.path.join(_BASE, "data", "krx-daily", "*.json")))
    # ⚠️ **매일 전부 훑는다** (2026-09-08 고침). 20일 간격 표본으로 하면
    #    2,700종목만 잡혀 **54종목(2%)을 놓친다**. 수집 대상은 한 번
    #    정하면 끝이라 시간을 더 써도 된다
    for p in 날들:
        try:
            주 = json.load(io.open(p, encoding="utf-8-sig")).get("종목") or {}
        except ValueError:
            continue
        for c, v in 주.items():
            try:
                m = float(v.get("시총") or 0)
            except (TypeError, ValueError):
                continue
            if 5e10 <= m < 2e11:
                밴드.add(c)
    return sorted(밴드)


def main():
    확인만 = "--확인" in sys.argv
    # 매일 돌 때 쓴다 — 이미 받은 종목에 **새 기사만 덧붙인다**
    갱신 = "--갱신" in sys.argv
    최대쪽 = int(sys.argv[sys.argv.index("--쪽") + 1]) if "--쪽" in sys.argv else 30
    # ⚠️ 비공식 API다. 너무 빨리 두드리면 막힌다 — 기본을 넉넉히 둔다
    쉼 = float(sys.argv[sys.argv.index("--쉼") + 1]) if "--쉼" in sys.argv else 0.35
    os.makedirs(OUT, exist_ok=True)
    # ⭐ **--후보** — forward-log 에 오른 종목만 (2026-09-10 · 사용자 결정 ㉡)
    if "--후보" in sys.argv:
        코드들 = 후보종목목록()
        찍기(f"  ⭐ **후보 종목만** 받는다 — {len(코드들):,}종목 "
             "(forward-log 누적)")
        if not 코드들:
            찍기("  ⚠️ forward-log 가 비었다. record_pick 을 먼저 돌려야 한다")
    elif "--밴드" in sys.argv:
        # ⚠️ 2026-09-07 신설. 그동안 **신호가 났던 종목만** 받아서 124개뿐이었다.
        #    그래서 「뉴스는 표본이 모자라 못 쓴다」고 적혀 있었는데,
        #    모자란 건 기간이 아니라 **종목 수**였고 그건 우리가 안 받아서였다
        코드들 = 밴드종목목록()
        찍기(f"  시총 500~2,000억에 한 번이라도 든 종목 {len(코드들)}개를 받는다")
    elif "--목록" in sys.argv:
        코드들 = 신호종목목록()
        찍기(f"  신호가 났던 종목 {len(코드들)}개를 받는다")
    else:
        코드들 = 신호종목목록()
    if 확인만:
        코드들 = 코드들[:3]
    if not 코드들:
        찍기("  받을 종목이 없다. --목록 신호종목 을 쓰거나 78차를 먼저 돌려야 한다")
        return 1
    찍기(f"===== 종목뉴스 수집 (네이버 금융) · {len(코드들)}종목 · 최대 {최대쪽}쪽 =====")
    ok = 빈 = 0
    for i, code in enumerate(코드들, 1):
        p = os.path.join(OUT, code + ".json")
        # ⚠️⚠️ **2026-09-07 고침.** 예전엔 파일이 있으면 통째로 건너뛰었다.
        #    그러면 매일 돌려도 **새 기사가 영영 안 쌓인다.**
        #    ⇒ `--갱신` 이면 이미 있는 것에 **덧붙인다**(날짜+제목으로 중복 제거)
        옛것 = []
        if os.path.exists(p):
            if not 갱신 and not 확인만:
                continue
            try:
                옛것 = (json.load(io.open(p, encoding="utf-8-sig"))
                        .get("뉴스") or [])
            except ValueError:
                옛것 = []
        time.sleep(쉼)
        a = 종목받기(code, 최대쪽)
        if a and 옛것:
            본것 = {(str(x.get("날짜")), str(x.get("제목"))[:60]) for x in a}
            for x in 옛것:
                열쇠 = (str(x.get("날짜")), str(x.get("제목"))[:60])
                if 열쇠 not in 본것:
                    a.append(x)
                    본것.add(열쇠)
            a.sort(key=lambda z: (str(z.get("날짜") or ""),
                                  str(z.get("시각") or "")), reverse=True)
        if a:
            io.open(p, "w", encoding="utf-8").write(json.dumps(
                {"종목": code, "받은날": dt.date.today().strftime("%Y%m%d"),
                 "건수": len(a), "뉴스": a}, ensure_ascii=False))
            ok += 1
            찍기(f"  {code}  {len(a):>4}건 · {a[0]['날짜']} ~ {a[-1]['날짜']}")
        else:
            빈 += 1
            찍기(f"  {code}  뉴스 없음")
    찍기(f"  끝 · 받음 {ok} · 빈 것 {빈}")
    if 확인만 and ok:
        d = json.load(io.open(os.path.join(OUT, 코드들[0] + ".json"),
                              encoding="utf-8-sig"))
        찍기("  시험 — 최근 제목 3개:")
        for x in d["뉴스"][-3:]:
            찍기(f"    {x['날짜']} [{x['언론사']}] {x['제목'][:52]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
