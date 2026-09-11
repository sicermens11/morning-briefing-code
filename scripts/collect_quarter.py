#!/usr/bin/env python3
r"""
collect_quarter.py — **분기 재무를 DART에서 길게 받는다** (2026-09-07 신설)

## 왜
```
지금 재무 조건(잉여금비율·부채비율·흑자)은 **연간**이다.
연간 재무는 사업보고서(3월)에 나오니 **1년에 한 번** 갱신된다
-> 최악의 경우 **15개월 묵은 재무**로 오늘 살 종목을 고른다
가진 분기 자료(naver-quarter)는 **종목당 5분기뿐**이라 긴 검증이 안 된다
```
⇒ 2026-09-07 API 전수 조사에서 `fnlttMultiAcnt`(다중회사 주요계정)가
  **분기별로 열린다**는 걸 확인했다. 2015~2025 분기 전부 받는다

## 비용 (실측)
```
다중회사 API는 **한 번에 5종목**까지다
  (2종목 60줄 · 5종목 150줄 · 10·20·50종목도 150줄 = 5개가 상한)
2,663종목 ÷ 5 = 533묶음 × 11해 × 4분기 = **약 23,452회**
DART 하루 한도 **20,000회** -> 이틀에 나눠 받는다 (이어받기 됨)
```
⚠️⚠️ **공시 백필·증자감자 수집과 같은 날 돌리면 한도가 터진다.**

## 받는 것
```
reprt_code  11013=1분기 · 11012=반기 · 11014=3분기 · 11011=사업보고서
저장        data/quarter-fin/{해}_{분기}.json
            {"해":.., "분기":.., "종목수":.., "종목": {코드: {항목: 값}}}
```

쓰는 법:
    python scripts\collect_quarter.py              # 안 받은 것부터 이어서
    python scripts\collect_quarter.py --확인       # 한 묶음만 시험
    python scripts\collect_quarter.py --상한 5000  # 이번엔 5,000회만
"""
import datetime as dt
import glob
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
OUT = os.path.join(_DATA, "quarter-fin")
LOG = os.path.join(_DATA, "_quarter.log")

_해들 = [str(y) for y in range(2015, 2027)]
_분기 = (("11013", "1분기"), ("11012", "반기"),
         ("11014", "3분기"), ("11011", "사업"))
_묶음 = 5          # ⚠️ 실측 상한. 늘려도 5개까지만 돌아온다
_쉼 = 0.06
_기본상한 = 19000  # 하루 한도 20,000 에서 여유를 둔다


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def 받을종목():
    r"""시총 500~2,000억에 **한 번이라도** 든 종목.

    ⚠️ 「지금 밴드에 있는 것」이 아니라 「한 번이라도 있었던 것」이다 —
       백테스트는 과거를 훑으므로 그때 밴드에 있었으면 필요하다
    """
    밴드 = set()
    날들 = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
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
    return 밴드


def 코드표():
    p = os.path.join(_DATA, "dart-corpcode.json")
    d = json.load(io.open(p, encoding="utf-8-sig"))
    return {c: (v.get("corp_code") or "") for c, v in d.items()
            if isinstance(v, dict) and v.get("corp_code")}


def 부르기(key, 묶, 해, rc):
    q = urllib.parse.urlencode({"crtfc_key": key, "corp_code": ",".join(묶),
                                "bsns_year": 해, "reprt_code": rc})
    u = f"https://opendart.fss.or.kr/api/fnlttMultiAcnt.json?{q}"
    try:
        with urllib.request.urlopen(u, timeout=25) as f:
            return json.loads(f.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"status": "ERR", "message": type(e).__name__}


def main():
    key = config.get("DART_API_KEY")
    if not key:
        찍기("⚠️ DART_API_KEY 가 없다")
        return 1
    상한 = _기본상한
    if "--상한" in sys.argv:
        상한 = int(sys.argv[sys.argv.index("--상한") + 1])
    시험 = "--확인" in sys.argv

    os.makedirs(OUT, exist_ok=True)
    찍기("===== 분기 재무 수집 시작 =====")
    밴드 = 받을종목()
    표 = 코드표()
    쓸것 = [(c, 표[c]) for c in sorted(밴드) if c in 표]
    찍기(f"  밴드 종목 {len(밴드):,} · corp_code 있는 것 {len(쓸것):,}")

    할일 = []
    for 해 in _해들:
        for rc, 이름 in _분기:
            p = os.path.join(OUT, f"{해}_{이름}.json")
            이미 = {}
            if os.path.exists(p):
                try:
                    이미 = (json.load(io.open(p, encoding="utf-8-sig"))
                            .get("종목") or {})
                except ValueError:
                    이미 = {}
            남 = [x for x in 쓸것 if x[0] not in 이미]
            if 남:
                할일.append((해, rc, 이름, p, 이미, 남))
    총 = sum((len(x[5]) + _묶음 - 1) // _묶음 for x in 할일)
    찍기(f"  할 것 {len(할일)}칸 · 호출 약 {총:,}회 "
         f"· 이번에 최대 {상한:,}회")
    if 시험:
        할일 = 할일[:1]
        상한 = 3

    # ⚠️⚠️ **없는 분기에 526회씩 헛부르면 안 된다** (2026-09-07 실측).
    #    2015년은 사업보고서만 있고 분기는 없다. 2026년은 반기까지다.
    #    ⇒ 칸마다 **삼성전자+하이닉스로 한 번 찔러보고** 비면 통째로 건너뛴다
    _찔러 = ["00126380", "00164779"]

    쓴횟수, 한도끝 = 0, False
    for 해, rc, 이름, p, 이미, 남 in 할일:
        if 한도끝 or 쓴횟수 >= 상한:
            break
        미리 = 부르기(key, _찔러, 해, rc)
        쓴횟수 += 1
        if str(미리.get("status")) == "020":
            찍기("  ⚠️⚠️ DART 하루 한도를 다 썼다 — 멈춘다")
            break
        if not (미리.get("list") or []):
            찍기(f"  [{해} {이름}] **그 분기 자료가 아예 없다** — 건너뛴다")
            with io.open(p, "w", encoding="utf-8") as f:
                json.dump({"해": 해, "분기": 이름, "종목수": 0,
                           "없는분기": True,
                           "받은날": dt.date.today().strftime("%Y%m%d"),
                           "종목": {c: {} for c, _ in 쓸것}},
                          f, ensure_ascii=False)
            continue
        찍기(f"  [{해} {이름}] 남은 종목 {len(남):,}")
        새것 = dict(이미)
        for i in range(0, len(남), _묶음):
            if 쓴횟수 >= 상한:
                break
            묶 = 남[i:i + _묶음]
            r = 부르기(key, [x[1] for x in 묶], 해, rc)
            쓴횟수 += 1
            상태 = str(r.get("status", ""))
            if 상태 == "020":
                찍기("  ⚠️⚠️ DART 하루 한도를 다 썼다 — 멈춘다. "
                     "내일 다시 돌리면 이어받는다")
                한도끝 = True
                break
            거꾸로 = {v: k for k, v in 묶}
            for row in (r.get("list") or []):
                cc = row.get("corp_code")
                코드 = 거꾸로.get(cc)
                if not 코드:
                    continue
                항 = row.get("account_nm")
                값 = row.get("thstrm_amount")
                if 항 is None:
                    continue
                try:
                    값 = float(str(값).replace(",", "")) if 값 not in (None, "", "-") else None
                except ValueError:
                    값 = None
                새것.setdefault(코드, {})[항] = 값
            # 자료가 없는 회사도 「받아봤다」로 남긴다 — 안 그러면 영원히 다시 부른다
            for 코드, _ in 묶:
                새것.setdefault(코드, {})
            time.sleep(_쉼)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump({"해": 해, "분기": 이름, "종목수": len(새것),
                       "받은날": dt.date.today().strftime("%Y%m%d"),
                       "종목": 새것}, f, ensure_ascii=False)
        찍기(f"    저장 {os.path.basename(p)} · 종목 {len(새것):,} "
             f"· 누적 호출 {쓴횟수:,}")
    찍기(f"===== 끝 · 이번에 {쓴횟수:,}회 호출 "
         f"{'· 한도 소진' if 한도끝 else ''} =====")
    남은 = 총 - 쓴횟수
    if 남은 > 0:
        찍기(f"  ⚠️ 아직 약 {남은:,}회 남았다 — 내일 다시 돌리면 이어받는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
