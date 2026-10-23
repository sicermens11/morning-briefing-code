#!/usr/bin/env python3
r"""
kis_compare_antc.py — **08:56 한국투자증권 예상체결가를 받아 NH 값과 나란히 적는다** (2026-10-22 신설 · 조회만)

왜: 지금 08:55 판정은 NH 예상체결가로 한다. 자동매매를 한국투자증권으로 옮기려면 두 값이 같은지 **확인차** 한두 번 본다.
    같으면 그다음엔 안 한다(KIS 하나로 갈지 정한다). 사용자 10/22 「가(권고)로 하자」.
⚠️ 조회만 · 주문 없음 · forward-log 는 읽기만(쓰지 않는다) · 휴장일엔 아무것도 안 한다
출력: data/kis-antc/YYYYMMDD_HHMM.json (KIS 원본 output2 그대로 — 칸 이름 확인용) · data/_kis_compare.log (NH 대 KIS 한 줄씩)

10/23 고침: 첫날은 08:56:00 에 forward-log 를 읽었는데 08:55 판정이 08:57:16 에야 적혀 NH 값이 0개였다.
    뒤늦게 맞춰 보니 같은 값 57% · 그런데 **두 곳이 값을 받은 시각이 1~4분 떨어져** 있어 동시호가 중 값이 움직인 것과 구별이 안 됐다.
    → 이제 ① 08:55 판정(fetch_antc)이 NH 부르기를 다 끝낼 때까지 기다리고(실전 판정과 NH 호출이 겹치지 않게)
       ② 종목마다 **NH 와 KIS 를 잇달아**(1초 안) 불러 같은 순간 값을 견준다 · 08:59:50 에 멈춘다(09:00 이면 예상가가 0)
"""
import datetime as dt
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_B, "scripts"))
_LOG = os.path.join(_B, "data", "_kis_compare.log")
_ANTC = os.path.join(_B, "data", "_antc.log")


def 적기(s):
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    with io.open(_LOG, "a", encoding="utf-8") as f:
        f.write(줄 + "\n")


def _판정끝났나(오늘):
    """오늘 08:55 받기 시작 뒤 「웹 재게시」 또는 「===== 끝」 줄이 있으면 NH 부르기가 끝난 것"""
    try:
        줄 = io.open(_ANTC, encoding="utf-8").read().splitlines()
    except OSError:
        return False
    켜짐 = False
    for z in 줄:
        if not z.startswith(오늘):
            continue
        if "받기 시작 (08:55)" in z:
            켜짐 = True
        elif 켜짐 and ("웹 재게시" in z or "===== 끝" in z):
            return True
    return False


def _nh(code):
    if not os.environ.get("NHPLUG_APP_KEY"):   # 10/23 시험에서 222개 전부 [auth] — 열쇠를 환경변수로 먼저 넣는다(fetch_portfolio 와 같은 방식)
        from fetch_portfolio import _env
        _env()
    from nhplug import call
    o2 = (call("/krstock/quote/v1/currentPrice", {"iem_cd": code, "market_cd": "KRX"}).get("Output_2") or {})
    try:
        return float(o2.get("antc_cnpr") or 0)
    except (TypeError, ValueError):
        return 0.0


def main():
    from krx_calendar import 장서는날
    선다, 왜 = 장서는날()
    if not 선다:
        적기(f"휴장 — 안 한다 ({왜})")
        return 0
    import kis_api
    오늘 = dt.date.today().isoformat()
    멈출때 = dt.datetime.combine(dt.date.today(), dt.time(8, 59, 50))
    if os.environ.get("KIS_COMPARE_TEST"):   # 장 밖 시험용 — 15초만 돌린다(예상가는 0 으로 나온다)
        멈출때 = dt.datetime.now() + dt.timedelta(seconds=15)
    while not _판정끝났나(오늘) and dt.datetime.now() < dt.datetime.combine(dt.date.today(), dt.time(8, 59, 0)):
        time.sleep(3)
    if not _판정끝났나(오늘):
        적기("08:59 까지 08:55 판정이 안 끝났다 — 실전과 겹치지 않게 안 한다")
        return 1
    줄들 = [json.loads(z) for z in io.open(os.path.join(_B, "data", "forward-log.jsonl"), encoding="utf-8") if z.strip()]
    끝 = 줄들[-1]
    if str(끝.get("기록시각") or "")[:10] != 오늘:
        적기(f"오늘 기록이 아직 없다(마지막 {str(끝.get('기록시각'))[:10]}) — 안 한다")
        return 1
    동 = 끝.get("동시호가") or {}
    NH판정 = {}
    for k in ("종목별", "보완종목별"):
        for c, v in (동.get(k) or {}).items():
            if v.get("예상시가"):
                NH판정[c] = float(v["예상시가"])
    후보 = [(x["종목코드"], x.get("이름", "")) for x in (끝.get("후보") or [])] + \
           [(x["종목코드"], x.get("이름", "")) for x in (끝.get("보완후보") or [])]
    본 = set()
    후보 = [z for z in 후보 if not (z[0] in 본 or 본.add(z[0]))]
    k = kis_api.KIS("모의")
    적기(f"===== 시작 · 후보 {len(후보)}개 · 08:55 판정 NH 값 {len(NH판정)}개 · 종목마다 NH·KIS 잇달아 · 08:59:50 멈춤 =====")
    원본, 차이들, 받음, 실패 = {}, [], 0, 0
    for c, 이름 in 후보:
        if dt.datetime.now() >= 멈출때:
            적기(f"  ⏹ 08:59:50 — 여기서 멈춘다(받은 {받음} · 남은 {len(후보) - 받음 - 실패})")
            break
        try:
            t0 = time.time()
            nh = _nh(c)
            r = k.예상체결(c)
            간격 = time.time() - t0
        except Exception as e:  # noqa: BLE001
            실패 += 1
            적기(f"  ✗ {이름} {c}: {str(e)[:80]}")
            continue
        받음 += 1
        예 = r.get("예상") or {}
        원본[c] = {"이름":이름, "예상": 예, "NH": nh, "간격초": round(간격, 2)}
        try:
            kis = float(예.get("antc_cnpr") or 0)
        except (TypeError, ValueError):
            kis = 0.0
        if nh and kis:
            d = (kis / nh - 1) * 100
            차이들.append(abs(d))
            적기(f"  {이름:<10} NH {nh:>10,.0f}  KIS {kis:>10,.0f}  차이 {d:+.2f}%  ({간격:.1f}초)")
        else:
            적기(f"  {이름:<10} NH {nh if nh else '없음':>10}  KIS {kis if kis else '없음':>10}")
    os.makedirs(os.path.join(_B, "data", "kis-antc"), exist_ok=True)
    out = os.path.join(_B, "data", "kis-antc", f"{dt.datetime.now():%Y%m%d_%H%M}.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump({"받은때": dt.datetime.now().isoformat(timespec="seconds"), "NH판정": NH판정, "KIS": 원본}, f, ensure_ascii=False, indent=1)
    if 차이들:
        같음 = sum(1 for z in 차이들 if z < 0.005)
        적기(f"===== 끝 · 받음 {받음} · 실패 {실패} · 둘 다 있는 것 {len(차이들)} · 같은 값 {같음} ({같음 / len(차이들) * 100:.0f}%) · 차이 평균 {sum(차이들) / len(차이들):.3f}% · 최대 {max(차이들):.2f}% · 0.5% 넘는 것 {sum(1 for z in 차이들 if z > 0.5)} → {out} =====")
    else:
        적기(f"===== 끝 · 받음 {받음} · 실패 {실패} · 견줄 값 없음 → {out} =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
