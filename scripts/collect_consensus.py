#!/usr/bin/env python3
r"""
collect_consensus.py — **애널리스트 목표주가·투자의견을 과거로 받는다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 점수표의 `조건부-C`가 **가장 큰 감점**을 준다:
```
목표주가 상향(신규커버리지+매수의견 포함)   +1
목표주가 하향 또는 매도의견              **−2**
투자의견 강등(매수→중립 등, 30일 이내)     **−1**
```
그런데 **과거 컨센서스 히스토리가 없어서 소급 검증이 아예 불가능**했다.
FMP `historical-grades`는 상위 요금제에서 막혔고(2026-09-01 확인),
네이버는 스냅샷만 준다.

✅ **한경컨센서스(consensus.hankyung.com)가 목록에 「적정가격」과 「투자의견」을 그대로 준다.**
   날짜 범위(`sdate`·`edate`)로 과거를 부를 수 있고 **2020년까지 간다**(확인함).
```
작성일 · 제목(종목명+코드) · 적정가격 · 투자의견 · 작성자 · 증권사
2026-08-31 | SK(034730) … | 800,000 | 매수 | 최관순 | SK증권
```
한 달 약 335건 · 17쪽. 2024-01~현재 32개월이면 **약 550회 · 5분**.

⚠️ **월 단위로 저장한다** — 중간에 끊겨도 그 달까지는 남는다.
⚠️ 이미 받은 달은 건너뛴다(이어받기).

저장: `data/consensus/{YYYYMM}.json`

쓰는 법:
    python scripts\collect_consensus.py
    python scripts\collect_consensus.py --확인
    python scripts\collect_consensus.py --부터 202401 --까지 202608
"""
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "consensus")
LOG = os.path.join(_BASE, "data", "_consensus.log")

URL = "https://consensus.hankyung.com/analysis/list?skinType=business"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "https://consensus.hankyung.com/"}
_쉼 = 0.25
_행 = re.compile(r"<tr[^>]*>((?:\s*<td.*?</td>\s*){4,})</tr>", re.S)
_칸 = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_코드 = re.compile(r"\((\d{6})\)")


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def _글(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def _돈(x):
    x = re.sub(r"[^\d]", "", x or "")
    return int(x) if x else None


def 쪽(sd, ed, p):
    u = f"{URL}&sdate={sd}&edate={ed}&now_page={p}"
    s = urllib.request.urlopen(urllib.request.Request(u, headers=H),
                               timeout=30).read().decode("utf-8", "replace")
    out = []
    for tr in _행.findall(s):
        c = [_글(x) for x in _칸.findall(tr)]
        if len(c) < 6 or not re.match(r"\d{4}-\d{2}-\d{2}", c[0]):
            continue
        m = _코드.search(c[1])
        out.append({"날짜": c[0], "코드": m.group(1) if m else None,
                    "제목": c[1][:120], "목표주가": _돈(c[2]),
                    "의견": c[3] or None, "작성자": c[4] or None,
                    "증권사": c[5] or None})
    return out


def 달들(부터, 까지):
    a = dt.date(int(부터[:4]), int(부터[4:]), 1)
    b = dt.date(int(까지[:4]), int(까지[4:]), 1)
    out = []
    while a <= b:
        out.append(a.strftime("%Y%m"))
        a = dt.date(a.year + (a.month == 12), a.month % 12 + 1, 1)
    return out


def main():
    확인만 = "--확인" in sys.argv
    부터 = sys.argv[sys.argv.index("--부터") + 1] if "--부터" in sys.argv else "202401"
    까지 = sys.argv[sys.argv.index("--까지") + 1] if "--까지" in sys.argv else dt.date.today().strftime("%Y%m")
    os.makedirs(OUT, exist_ok=True)
    받 = {os.path.basename(f)[:-5] for f in os.listdir(OUT) if f.endswith(".json")} \
        if os.path.isdir(OUT) else set()
    할것 = [m for m in 달들(부터, 까지) if m not in 받]
    찍기(f"  {부터}~{까지} · 이미 받음 {len(받)}달 · 받을 것 {len(할것)}달 "
         f"· 예상 약 {len(할것)*17*(_쉼+0.35)/60:.0f}분")
    if 확인만 or not 할것:
        찍기("  받을 것이 없다." if not 할것 else "  --확인 이라 받지 않았다.")
        return 0

    총 = 0
    for mi, m in enumerate(할것, 1):
        sd = f"{m[:4]}-{m[4:]}-01"
        말 = dt.date(int(m[:4]) + (m[4:] == "12"), int(m[4:]) % 12 + 1, 1) - dt.timedelta(days=1)
        ed = 말.strftime("%Y-%m-%d")
        모 = []
        실패 = False
        for p in range(1, 80):
            r = None
            # ⚠️⚠️ **오류 나면 쉬었다 다시 해본다** (2026-09-09 고침).
            #    전에는 한 번 틀리면 바로 break 하고 **0건으로 저장**해서,
            #    다음엔 「이미 받음」으로 건너뛰었다.
            #    -> **빈 파일 38개(2020-11~2023-12)** 가 그렇게 생겼다
            for 다시 in range(3):
                try:
                    r = 쪽(sd, ed, p)
                    break
                except Exception as e:  # noqa: BLE001
                    if 다시 == 2:
                        찍기(f"    ⚠️ {m} {p}쪽: {type(e).__name__} — 세 번 틀렸다")
                        실패 = True
                    else:
                        time.sleep(3 * (다시 + 1))
            if 실패 or not r:
                break
            모 += r
            time.sleep(_쉼)
        # ⚠️⚠️ **오류로 0건이면 저장하지 않는다.**
        #    빈 파일을 남기면 다음에 영영 안 받는다
        if 실패 and not 모:
            찍기(f"  [{mi}/{len(할것)}] {m} — ❌ 못 받았다 (빈 파일을 안 남긴다)")
            continue
        io.open(os.path.join(OUT, m + ".json"), "w", encoding="utf-8").write(
            json.dumps({"달": m, "건수": len(모), "리포트": 모}, ensure_ascii=False))
        총 += len(모)
        찍기(f"  [{mi}/{len(할것)}] {m} — {len(모)}건 (누적 {총:,})")
    찍기(f"  끝 — 총 {총:,}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
