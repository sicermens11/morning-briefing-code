#!/usr/bin/env python3
r"""
backfill_dart_old.py — **공시·연간재무를 2010년까지 받는다** (2026-09-02 신설)

⚠️⚠️ **2026-09-02에 밝혀진 것**: KRX·DART·KIND·네이버 전부 **2010년까지 준다.**
   그전에는 「2024-01이 한계」라고 **확인 없이 믿고** 있었고, 모든 실험이 그 위에 서 있었다.
   → 표본이 **2.6년 → 16.7년**으로 늘어난다. 2020 코로나 폭락·2022 약세장이 들어온다.

**받는 것**
```
연간재무   2015~2022 (2023·2024·2025는 이미 있다)
          ⚠️ 2013은 status=013으로 없다 → **2015가 한계**
          연도당 530묶음 × 8년 = 약 4,240회
공시       거래일당 **5~6회**(실측) · 약 3,450일 → 약 **19,000회**
          ⚠️ 처음엔 3회로 잘못 추정했다. 2010년 493건/일에 실제 5회였다
```

⚠️⚠️ **DART 하루 한도 20,000회.** 둘 합쳐 약 23,000회라 **이틀에 나눠야 한다.**
   `--상한`으로 묶어 **아침 08:00 브리핑 몫(약 500회)을 반드시 남긴다.**

⚠️ 이어받는다. 이미 있는 날/연도는 건너뛴다. 몇 번을 돌려도 안전하다.

쓰는 법:
    python scripts\backfill_dart_old.py --상한 18000
"""
import datetime as dt
import glob
import io
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_dart as D  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
LOG = os.path.join(_DATA, "_dartold.log")
_쉼 = 0.02
_공시회 = 6          # ⚠️ 실측 5~6회. 보수적으로 6으로 센다


def 찍기(s):
    line = f"{dt.datetime.now():%H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def main():
    상한 = int(sys.argv[sys.argv.index("--상한") + 1]) if "--상한" in sys.argv else 18000
    호출 = 0
    찍기(f"===== 시작 · 상한 {상한:,}회 =====")

    # ── ① 연간재무 (가볍고 값어치 크다. 먼저) ──
    for y in [str(x) for x in range(2015, 2023)]:
        p = os.path.join(_DATA, "dart-fin", f"{y}.json")
        if os.path.exists(p):
            continue
        if 호출 + 530 > 상한:
            찍기(f"⚠️ 상한 도달 — 재무 {y}년부터는 다음 실행에")
            return 0
        찍기(f"[재무] {y}년 시작")
        # ⚠️ os.system 은 공백 있는 경로 + 한글 인자를 못 다룬다(2026-09-02 실패했다).
        #    subprocess 로 인자를 리스트로 넘긴다.
        r = subprocess.run(
            [sys.executable, os.path.join(_BASE, "scripts", "collect_fin.py"), "--해", y],
            cwd=_BASE, env=dict(os.environ, PYTHONIOENCODING="utf-8"),
            capture_output=True)
        호출 += 530
        됐 = os.path.exists(p)
        찍기(f"[재무] {y}년 끝 (exit={r.returncode}) "
             f"{'✅' if 됐 else '❌ 파일이 안 생겼다'} · 누적 약 {호출:,}")

    # ── ② 공시 ──
    날 = sorted(os.path.basename(f)[:-5]
                for f in glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    받 = {os.path.basename(f)[:-5]
          for f in glob.glob(os.path.join(_DATA, "dart-daily", "*.json"))}
    할 = [d for d in 날 if d not in 받]
    찍기(f"[공시] 거래일 {len(날):,} · 이미 {len(받):,} · 받을 것 {len(할):,}")
    os.makedirs(os.path.join(_DATA, "dart-daily"), exist_ok=True)
    ok = 실패 = 0
    for i, d8 in enumerate(할, 1):
        if 호출 + _공시회 > 상한:
            찍기(f"⚠️ 상한 {상한:,} 도달 — {i-1:,}일까지 (다시 돌리면 이어받는다)")
            break
        try:
            g = D.disclosures(d8)
            호출 += _공시회
            io.open(os.path.join(_DATA, "dart-daily", f"{d8}.json"), "w",
                    encoding="utf-8").write(json.dumps(
                        {"기준일": d8, "전체건수": g.get("전체건수"),
                         "챙길공시": g.get("챙길공시") or [],
                         "정보성건수": g.get("정보성건수"),
                         # >>> 2026-09-03 추가. 버리면 다시 받는 수밖에 없다
                         "그밖의공시": g.get("그밖의공시") or []}, ensure_ascii=False))
            ok += 1
        except Exception:
            실패 += 1
            호출 += _공시회
        time.sleep(_쉼)
        if i % 200 == 0:
            찍기(f"  [공시] {i:,}/{len(할):,} — 받음 {ok:,} 실패 {실패} · 누적 약 {호출:,}")
    찍기(f"[공시] 끝 — 받음 {ok:,} 실패 {실패} · 총 약 {호출:,}회")
    남 = len(할) - ok - 실패
    찍기(f"===== 끝 · 아직 남은 공시 {남:,}일 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
