#!/usr/bin/env python3
r"""
fetch_antc.py — **08:50 예상체결가를 NH API로 받아 자동 기록** (2026-09-07 신설)

## 왜
```
08:50 예상체결가를 매일 남겨야 상대갭 문턱(-3.5 vs -3.0)을 정할 수 있다 (20건 필요).
그런데 08:50에 사람이 책상 앞에 없다. 손으로 적는 방식은 며칠 안에 끊긴다
⇒ NH API 로 받아 record_pick 에 그대로 넘긴다
```

## 어디서 오나 (2026-09-07 실측으로 확인)
```
/krstock/quote/v1/currentPrice   {iem_cd: 종목코드, market_cd: "KRX"}
  Output_2.antc_cnpr        **예상체결가**   ← 이것
  Output_2.antc_vol         예상 체결량
  Output_2.cncc_aspr_code   동시호가 구분
장중에는 antc_cnpr 이 0 이다. **08:30~09:00에만 값이 들어온다**
```
⚠️⚠️ **조회만 한다. 주문 API는 절대 부르지 않는다.**
⚠️ 후보 수만큼 호출한다 (보통 5~40회). 하루 한 번이라 부담은 작다

쓰는 법:
    python scripts\fetch_antc.py            받아서 record_pick 에 넘긴다
    python scripts\fetch_antc.py --보기만    받아서 보여주기만 한다
로그: `data/_antc.log`
"""
import datetime as dt
import io
import json
import os
import subprocess
import sys
import time

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "forward-log.jsonl")
기록 = os.path.join(_BASE, "data", "_antc.log")


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(기록, "a", encoding="utf-8") as fp:
            fp.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass


def 예상체결가(code):
    """(예상체결가, 예상체결량, 동시호가구분) — 못 받으면 (None, None, None)"""
    from nhplug import call
    d = call("/krstock/quote/v1/currentPrice",
             {"iem_cd": code, "market_cd": "KRX"})
    o2 = d.get("Output_2") or {}
    try:
        가 = float(o2.get("antc_cnpr") or 0)
    except (TypeError, ValueError):
        가 = 0.0
    return (가 if 가 > 0 else None,
            o2.get("antc_vol"), o2.get("cncc_aspr_code"))


def main():
    보기만 = "--보기만" in sys.argv
    이제 = dt.datetime.now()
    때 = 이제.strftime("%H:%M")
    찍기(f"===== 예상체결가 받기 시작 ({때}) =====")
    if not ("08:30" <= 때 <= "09:00"):
        찍기(f"  ⚠️ 지금은 동시호가 시간이 아니다 (08:30~09:00). "
             f"예상체결가가 0으로 온다")

    if not os.path.exists(LOG):
        찍기("  ⚠️ forward-log.jsonl 이 없다")
        return 1
    줄 = []
    for x in io.open(LOG, encoding="utf-8"):
        x = x.strip()
        if x:
            try:
                줄.append(json.loads(x))
            except ValueError:
                pass
    if not 줄:
        찍기("  ⚠️ 기록이 비어 있다")
        return 1
    후보 = (줄[-1].get("후보") or [])
    if not 후보:
        찍기("  ⬛ 오늘 후보가 없다 — 받을 것도 없다 (규칙상 흔한 일이다)")
        return 0

    import fetch_portfolio as F
    F._env()

    찍기(f"  후보 {len(후보)}개에서 예상체결가를 받는다")
    모 = []
    빈 = 0
    for x in 후보:
        code = x["종목코드"]
        try:
            가, 량, 구분 = 예상체결가(code)
        except Exception as e:  # noqa: BLE001
            찍기(f"    ⚠️ {x['이름'][:12]}({code}) 실패 "
                 f"{type(e).__name__} {str(e)[:60]}")
            continue
        if 가 is None:
            빈 += 1
            찍기(f"    · {x['이름'][:12]}({code}) 예상체결가 없음 "
                 f"(동시호가 시간이 아니거나 거래 정지)")
            continue
        갭 = (가 / x["어제종가"] - 1) * 100 if x.get("어제종가") else None
        찍기(f"    · {x['이름'][:12]}({code}) 전날 {x['어제종가']:,}원 → "
             f"예상 {가:,.0f}원 ({갭:+.2f}%)" if 갭 is not None else
             f"    · {x['이름'][:12]}({code}) 예상 {가:,.0f}원")
        모.append(f"{code}={가:.0f}")
        time.sleep(0.2)          # ⚠️ 호출 간격을 둔다

    if not 모:
        찍기(f"  ⚠️ **하나도 못 받았다** (빈 값 {빈}개). "
             f"08:30~09:00에 다시 돌려라")
        return 1
    찍기(f"  받은 것 {len(모)}개 / 후보 {len(후보)}개")

    if 보기만:
        찍기(f"  (--보기만 이라 기록하지 않는다)  {','.join(모)}")
        return 0

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, os.path.join(_BASE, "scripts", "record_pick.py"),
         "--동시호가", ",".join(모)],
        capture_output=True, env=env, cwd=_BASE)
    나 = r.stdout.decode("utf-8", errors="replace")
    for L in 나.splitlines()[-14:]:
        if L.strip():
            찍기(f"    {L.rstrip()}")

    # ── ⭐ **웹을 다시 올린다** (2026-09-07 신설) ──
    #    기존 브리핑이 09:05 판정을 띠로 다시 올리는 것과 같은 방식이다
    #    (run-skill.ps1:162 -> publish_pages.ps1 -> _entry_band).
    #    이게 있어야 **사용자가 따로 확인할 것이 없다** — 브리핑만 보면 된다
    if r.returncode == 0:
        찍기("  웹 재게시 중 (08:50 확정을 화면에 올린다)...")
        p2 = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", os.path.join(_BASE, "scripts", "publish_pages.ps1")],
            capture_output=True, env=env, cwd=_BASE, timeout=900)
        꼬 = p2.stdout.decode("utf-8", errors="replace")
        올 = [L for L in 꼬.splitlines() if "index.html" in L or "github.io" in L]
        for L in 올[-2:]:
            찍기(f"    {L.strip()[:150]}")
        if p2.returncode != 0:
            찍기(f"  ⚠️ 재게시 실패 (코드 {p2.returncode})")
    찍기(f"===== 끝 · 코드 {r.returncode} =====")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
