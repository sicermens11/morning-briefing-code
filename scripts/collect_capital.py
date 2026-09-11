#!/usr/bin/env python3
r"""
collect_capital.py — **증자·감자·자사주 결정을 16.7년치 받는다** (2026-09-03 신설)

⚠️⚠️ **사용자 질문에서 나왔다.** *"증자감자는 수집예정이야?"* → **수집기가 아예 없었다.**

⚠️ 지금까지는 `dart-daily`의 **공시 제목**만 봤다(정규식 `유상증자|감자|…`).
   제목만으로는 **규모를 모른다** — 「유상증자 1%」와 「유상증자 50%」가 같이 세어졌다.
   이 API는 **주식수·금액·비율**을 준다.

**받는 것** (DART 주요사항보고서 5종)
```
piicDecsn     유상증자 결정      ⚠️ 악재 — 29차에서 t=−3.0 ~ −7.7
fricDecsn     무상증자 결정      🔸 보통 호재
pifricDecsn   유무상증자 결정
crDecsn       감자 결정         ⚠️ 악재
tsstkAqDecsn  자기주식취득 결정   ⭐ 유일한 호재 (55차 t=6.8)
tsstkDpDecsn  자기주식처분 결정   ⚠️ 악재
```
⚠️ **기간 인자가 16.7년을 한 번에 받는다** (2026-09-03 실측 — 삼성전자 자사주취득 15건).
   ⇒ 종목당 1회 × 6종 = **2,766 × 6 = 약 1만 7천 회.** 하루 한도(20,000) 안이다.
   ⚠️⚠️ **그래도 공시 백필(09-04 00:05)과 같은 날 돌리면 한도가 터진다.** 그 뒤에 돌린다.

⚠️ 이어받는다. 종목 파일이 이미 있으면 건너뛴다.
⚠️ `013 조회된 데이타가 없습니다`는 **정상**이다 — 그 종목이 안 한 것뿐이다. 빈 것으로 저장한다.

저장: `data/dart-capital/{종목코드}.json`
```
{"종목": "005930", "corp": "00126380", "받은날": "20260904",
 "유상증자": [...], "무상증자": [...], "감자": [...], "자사주취득": [...], …}
```

쓰는 법:
    python scripts\collect_capital.py
    python scripts\collect_capital.py --확인          # 1종목만 시험
    python scripts\collect_capital.py --상한 5000     # 호출 수 상한
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import fetch_dart as D  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "dart-capital")
LOG = os.path.join(_BASE, "data", "_capital.log")
_쉼 = 0.06

종류 = (("유상증자", "piicDecsn"), ("무상증자", "fricDecsn"),
        ("유무상증자", "pifricDecsn"), ("감자", "crDecsn"),
        ("자사주취득", "tsstkAqDecsn"), ("자사주처분", "tsstkDpDecsn"))


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 한번(ep, corp, key):
    q = urllib.parse.urlencode({"crtfc_key": key, "corp_code": corp,
                                "bgn_de": "20100101",
                                "end_de": dt.date.today().strftime("%Y%m%d")})
    u = f"https://opendart.fss.or.kr/api/{ep}.json?{q}"
    req = urllib.request.Request(u, headers=D.H if hasattr(D, "H") else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    st = d.get("status")
    if st == "000":
        return d.get("list") or [], None
    if st == "013":            # ⚠️ 「데이터 없음」은 정상이다
        return [], None
    return [], f"{st} {(d.get('message') or '')[:40]}"


def main():
    확인만 = "--확인" in sys.argv
    상한 = int(sys.argv[sys.argv.index("--상한") + 1]) if "--상한" in sys.argv else 19000
    key = config.require("DART_API_KEY")
    맵 = D.load_corpcode()
    os.makedirs(OUT, exist_ok=True)
    받 = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(OUT, "*.json"))}
    # ⭐⭐ **--갱신일 N** (2026-09-09 신설) — 파일이 N일보다 오래됐으면 **다시 받는다**.
    #    ⚠️ 이게 없으면 **종목 단위**로 「이미 받았으면 건너뛴다」라서,
    #       전 종목이 한 번 받아진 뒤로는 **새 자료가 생겨도 영영 안 받는다.**
    #       임원매매·5%보유가 이 병으로 2026-09-01 이후 8일간 멈춰 있었다
    _갱신일 = 0
    if "--갱신일" in sys.argv:
        _갱신일 = int(sys.argv[sys.argv.index("--갱신일") + 1])
    if _갱신일 > 0:
        import time as _time
        _낡음 = _time.time() - _갱신일 * 86400
        받 = {c for c in 받
              if os.path.exists(os.path.join(OUT, f"{c}.json"))
              and os.path.getmtime(os.path.join(OUT, f"{c}.json")) >= _낡음}

    # ⚠️ krx-daily 최근 파일에 있는 종목만 — 상장폐지된 것까지 받을 필요는 없다…
    #    가 아니라, **과거 시험에 쓰려면 폐지된 것도 필요하다.** corpcode 전체를 쓴다.
    할것 = [c for c in sorted(맵) if c not in 받]
    찍기(f"===== 증자·감자·자사주 수집 =====")
    찍기(f"  대상 {len(맵):,}종목 · 이미 받은 것 {len(받):,} · 할 것 {len(할것):,}")
    찍기(f"  호출 예상 {len(할것)*len(종류):,}회 (상한 {상한:,}) "
         f"· 예상 {len(할것)*len(종류)*(_쉼+0.12)/60:.0f}분")
    if 확인만:
        할것 = 할것[:1]

    호출 = ok = 빈 = 실패 = 0
    for i, code in enumerate(할것, 1):
        if 호출 + len(종류) > 상한:
            찍기(f"  ⚠️ 상한 {상한:,}회에 도달 — 여기서 멈춘다. 다시 돌리면 이어받는다")
            break
        corp = (맵[code] or {}).get("corp_code")
        if not corp:
            continue
        rec = {"종목": code, "corp": corp,
               "받은날": dt.date.today().strftime("%Y%m%d")}
        문제 = None
        for 이름, ep in 종류:
            try:
                lst, err = 한번(ep, corp, key)
            except urllib.error.HTTPError as e:
                lst, err = [], f"HTTP {e.code}"
            except Exception as e:
                lst, err = [], type(e).__name__
            호출 += 1
            rec[이름] = lst
            if err:
                문제 = err
            time.sleep(_쉼)
        if 문제 and all(not rec.get(n) for n, _ in 종류):
            실패 += 1
            if 실패 <= 5:
                찍기(f"  ⚠️ {code} 실패: {문제}")
            # ⚠️⚠️ 한도 초과(020)면 **더 돌려도 소용없다.** 멈춘다
            if str(문제).startswith("020"):
                찍기("  ⚠️⚠️ DART 하루 한도를 다 썼다 — 멈춘다. 내일 다시 돌리면 이어받는다")
                break
            continue
        건 = sum(len(rec.get(n) or []) for n, _ in 종류)
        io.open(os.path.join(OUT, code + ".json"), "w",
                encoding="utf-8").write(json.dumps(rec, ensure_ascii=False))
        if 건:
            ok += 1
        else:
            빈 += 1
        if i % 200 == 0:
            찍기(f"    {i}/{len(할것)} · 있음 {ok:,} · 빈 것 {빈:,} · 호출 {호출:,}")
    찍기(f"  끝 · 있음 {ok:,}종목 · 빈 것 {빈:,} · 실패 {실패} · 호출 {호출:,}회")
    if 확인만 and 할것:
        p = os.path.join(OUT, 할것[0] + ".json")
        if os.path.exists(p):
            d = json.load(io.open(p, encoding="utf-8-sig"))
            찍기("  시험 결과: " + " · ".join(
                f"{n} {len(d.get(n) or [])}건" for n, _ in 종류))
    return 0


if __name__ == "__main__":
    sys.exit(main())
