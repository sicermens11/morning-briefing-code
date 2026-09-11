#!/usr/bin/env python3
r"""
fetch_krx.py — 한국거래소 공식 일별매매정보를 받아 **우리 것으로 쌓는다**

⚠️⚠️ **왜 필요한가** (2026-08-28 신설).
   지금 시세·수급·재무가 **전부 네이버 한 곳**에서 온다. 네이버가 막히거나 형식을 바꾸면
   그날 브리핑이 통째로 흔들리고, 백테스트 수익률까지 같이 틀어진다. 실제로 2026-08-25에
   Exa 경유가 87자 응답에서 타임아웃을 내 컨센서스가 통째로 빠진 적이 있다.
   KRX는 **거래소가 직접 주는 공식값**이다. 대안을 하나 두는 것이 목적이다.

⚠️ **새 기능이 아니라 신뢰도다.** 여기서 얻는 값(종가·시가·고저·거래량·시총)은
   이미 네이버로 받고 있다. 다른 점은 **출처가 공식이고, 하루치 전종목이 한 번에 온다**는 것.
   전종목이 오므로 종목 수를 늘려도 호출이 안 는다 — 백테스트에 특히 좋다.

⚠️ **키는 `data\secrets.json`의 `KRX_API_KEY`.** 헤더 이름은 **`AUTH_KEY`**다.
   ⚠️⚠️ **인증키에 사용기간이 있다(1년).** 만료되면 어느 날 조용히 401이 되고,
      그때부터 KRX 폴백이 없는 상태로 돌아간다 — 네이버가 같이 막히면 그날 브리핑이
      통째로 흔들린다. **만료 두 달 전부터 아래 `_만료경고`가 실행할 때마다 찍는다.**
      갱신은 openapi.krx.co.kr 마이페이지에서 한다.
   ⚠️ 인증키 발급과 **서비스별 활용 신청은 별개**다. 키만 있고 신청을 안 하면
      `{"respMsg":"Unauthorized API Call"}`이 온다 — 키가 틀린 게 아니다.
      (키가 틀리면 `Unauthorized Key`가 온다. 두 메시지를 구분해야 헤맬 일이 없다.)

쓰는 법:
    python scripts\fetch_krx.py                      # 직전 거래일 받아 캐시
    python scripts\fetch_krx.py --date 20260827
    python scripts\fetch_krx.py --check              # 네이버 값과 대조(픽 종목만)
"""
import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(_BASE, "data", "krx-daily")
LOG = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
API = "https://data-dbg.krx.co.kr/svc/apis/sto"
# 유가증권·코스닥 둘 다 받아야 후보를 다 덮는다. 코넥스는 후보에 안 나온다.
MARKETS = (("KOSPI", "stk_bydd_trd"), ("KOSDAQ", "ksq_bydd_trd"))


# ⚠️ 인증키 사용기간(1년). 발급일을 여기 적어 두면 만료 두 달 전부터 경고한다.
#    ⚠️ API가 만료일을 안 알려주므로 **사람이 적어야 한다.** 갱신하면 이 날짜를 고친다.
KEY_ISSUED = "2026-08-28"
KEY_DAYS = 365


def _만료경고():
    try:
        d0 = datetime.strptime(KEY_ISSUED, "%Y-%m-%d")
        남음 = KEY_DAYS - (datetime.now() - d0).days
    except Exception:  # noqa: BLE001
        return None
    if 남음 <= 60:
        return (f"⚠️ KRX 인증키가 {남음}일 뒤 만료된다(발급 {KEY_ISSUED}). "
                f"openapi.krx.co.kr 마이페이지에서 갱신하고 fetch_krx.py의 "
                f"KEY_ISSUED를 고친다.")
    return None


def _get(path, basDd, key):
    r = urllib.request.Request(f"{API}/{path}?basDd={basDd}",
                               headers={"AUTH_KEY": key, "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=30) as res:
        d = json.loads(res.read().decode("utf-8"))
    for k, v in d.items():
        if isinstance(v, list):
            return v
    return []


def fetch(basDd, key=None):
    """그날 전종목. 이미 캐시에 있으면 그걸 쓴다(같은 날을 두 번 받지 않는다)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{basDd}.json")
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as fp:
            return json.load(fp), True

    key = key or config.get("KRX_API_KEY")
    if not key:
        raise RuntimeError("KRX_API_KEY가 없다. data\\secrets.json에 넣는다.")

    # ⚠️ **시장마다 따로 승인된다.** 유가증권만 승인되고 코스닥이 안 된 상태가 실제로
    #    있었다(2026-08-28). 하나가 401이어도 나머지는 받는다 — 반쪽이라도 있는 게 낫다.
    rows, 못받음 = {}, []
    for mkt, ep in MARKETS:
        try:
            got = _get(ep, basDd, key)
        except urllib.error.HTTPError as e:
            못받음.append(f"{mkt}({e.code})")
            continue
        for r in got:
            code = r.get("ISU_CD")
            if not code:
                continue
            rows[code] = {
                "이름": r.get("ISU_NM"), "시장": r.get("MKT_NM") or mkt,
                "종가": _n(r.get("TDD_CLSPRC")), "등락률": _n(r.get("FLUC_RT")),
                "시가": _n(r.get("TDD_OPNPRC")), "고가": _n(r.get("TDD_HGPRC")),
                "저가": _n(r.get("TDD_LWPRC")), "거래량": _n(r.get("ACC_TRDVOL")),
                "거래대금": _n(r.get("ACC_TRDVAL")), "시총": _n(r.get("MKTCAP")),
            }
    if not rows:
        raise RuntimeError("어느 시장도 못 받았다: " + ", ".join(못받음))
    out = {"기준일": basDd, "받은시각": datetime.now().isoformat(timespec="seconds"),
           "종목수": len(rows), "못받은시장": 못받음, "종목": rows}
    with io.open(path, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False)
    return out, False


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def close(code, basDd):
    """그날 그 종목의 종가. 캐시에 없으면 받아 온다."""
    d, _ = fetch(basDd)
    return ((d.get("종목") or {}).get(code) or {}).get("종가")


def _prev_bizday():
    """직전 평일. ⚠️ 휴장일은 못 가린다 — 그날은 API가 빈 배열을 준다."""
    d = datetime.now() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def check(basDd):
    r"""**네이버 값과 대조한다.** 두 출처가 어긋나면 그 자체가 신호다.

    ⚠️ 어느 쪽이 맞는지 이 스크립트는 판정하지 않는다. **다르다는 사실만 알린다** —
       둘 다 정상일 때도 액면분할·거래정지 같은 이유로 갈릴 수 있다.
    """
    d, _ = fetch(basDd)
    rows = [json.loads(l) for l in io.open(LOG, encoding="utf-8") if l.strip()]
    day = basDd[:4] + "-" + basDd[4:6] + "-" + basDd[6:]
    picks = next((o.get("picks") or [] for o in rows if o.get("date") == day), [])
    out = []
    for p in picks:
        krx = ((d.get("종목") or {}).get(p["code"]) or {}).get("종가")
        found = p.get("found_price")
        out.append({"code": p["code"], "name": p.get("name"),
                    "KRX종가": krx, "발굴가": found,
                    "일치": (krx is not None and found is not None
                            and abs(krx - found) < 1)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="YYYYMMDD (기본: 직전 평일)")
    ap.add_argument("--check", action="store_true", help="네이버 발굴가와 대조")
    a = ap.parse_args()
    basDd = a.date or _prev_bizday()
    try:
        d, cached = fetch(basDd)
    except urllib.error.HTTPError as e:
        body = e.read()[:120].decode("utf-8", "replace")
        힌트 = ("서비스 활용 신청이 안 됐다 — 인증키와 별개 절차다"
              if "API Call" in body else "인증키가 틀렸거나 헤더 이름이 다르다")
        print(json.dumps({"ok": False, "HTTP": e.code, "응답": body, "힌트": 힌트},
                         ensure_ascii=False))
        return 1
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "오류": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 1

    res = {"ok": True, "기준일": basDd, "종목수": d["종목수"], "캐시": cached}
    경고 = _만료경고()
    if 경고:
        res["경고"] = 경고
    if d.get("못받은시장"):
        res["못받은시장"] = d["못받은시장"]
    if a.check:
        res["대조"] = check(basDd)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
