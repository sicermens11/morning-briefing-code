#!/usr/bin/env python3
r"""
morning_extra.py — **ETF·주식선물·국고채를 아침에 받는다** (2026-09-10 신설)

## 사용자가 바로잡은 기준 (원문)
```
「브리핑 시간 설정에 중요한 건, claude 브리핑을 피하는게 먼저가 아니라
  **장 시작하기 전에 충분한 정보를 제공하는 거고, 정보를 충분히 수집한 뒤의 시간**이야.」
```

## 왜 아침으로 옮겼나 — **저녁엔 그날 자료가 없다**
```
실측 (when_krx2 · 2026-09-10):
  08:00:44   KRX 종가 · 지수
  **08:10:44   ETF · 주식선물(유가) · 선물 · 국고채**   <- 수집이 여기서 끝난다

그런데 이것들을 **저녁 19:00** 에 받고 있었다. 그 시각엔 그날 자료가 없어서
**하루 늦은 것**을 받는다 — 실제로 `krx-extra` 최신이 **20260908**(이틀 전)이었다.
⚠️⚠️ `record_pick`(퀀트 후보)이 **etf-krx 를 읽는다.** 낡으면 후보가 틀어진다
```

## 아침 순서
```
07:52  KRX 종가·지수 (재시도)      -> 08:00:44 도착
08:11  **여기** — ETF·주식선물·국고채
08:12  브리핑 시작 -> 퀀트 08:15 -> 먼저 게시 08:16 -> claude -> 08:44 최종
08:50  동시호가 확인    09:00  매수
```

쓰는 법:
    python scripts\morning_extra.py
"""
import datetime as dt
import io
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_morning_extra.log")

할것 = (
    ("ETF(KRX)", "collect_krx_etf.py", []),
    ("주식선물·국고채(KRX)", "collect_krx_extra.py", ["--최근", "10"]),
)


def 찍기(s):
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(줄 + "\n")
    except OSError:
        pass


def main():
    찍기("===== 아침 ETF·파생 받기 (도착 실측 08:10) =====")
    실패 = 0
    for 라, 파, 인자 in 할것:
        p = os.path.join(_BASE, "scripts", 파)
        if not os.path.exists(p):
            찍기(f"  ⚠️ {라:<20}{파} 가 없다")
            실패 += 1
            continue
        환 = dict(os.environ, PYTHONIOENCODING="utf-8")
        try:
            # ⚠️ 하위를 **별도 프로세스 그룹**에 둔다 — 저녁 수집이 하위의
            #    Ctrl+C 에 같이 죽은 적이 있다 (2026-09-09 19:00)
            플 = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            r = subprocess.run([sys.executable, p] + 인자, cwd=_BASE, env=환,
                               capture_output=True, timeout=900, creationflags=플)
            꼬 = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()
            찍기(f"  {라:<20}{(꼬[-1].strip()[:90] if 꼬 else f'코드 {r.returncode}')}")
        except Exception as e:  # noqa: BLE001
            찍기(f"  ⚠️ {라:<20}실패: {type(e).__name__} {str(e)[:60]}")
            실패 += 1
    찍기(f"===== 끝 · 실패 {실패}건 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
