#!/usr/bin/env python3
r"""
night_0904.py — **09-04 새벽 01:10~08:00 자동 테스트 묶음** (2026-09-03 짬)

⚠️ 사용자 지적: *"보여준 예약에 테스트 일정은 없는데, 9/4 01:00~08:00 동안 테스트는 없어?"*
   맞다. 00:05 공시 · 00:35 업종 · 01:00 증자감자까지만 있고 **7시간이 비어 있었다.**

## 이 시각에 무엇을 하나
```
01:10  96차  브리핑용 **확률표** — 금리 국면 × 조건 개수별 도달률
02:10  97차  **새로 받은 자료**로 다시 훑기 (공시 900일 · 업종 · 증자감자)
04:10  98차  **낙폭까지 보고** 문턱 고르기 — 95b B를 넓혀서 최종 확정
06:10  99차  보조 전략 최종 — 하이닉스 말고 **다른 대형주**도
```
⚠️ 08:00 브리핑과 겹치지 않게 07:30에는 끝낸다.
⚠️ 하나가 죽어도 다음이 돌도록 **각각 따로** 잡는다.
⚠️ 결과는 `data/_labs/`에 남기고 로그는 `data/_night0904.log`에 쌓는다

쓰는 법:
    python scripts\night_0904.py            (전부 차례로)
    python scripts\night_0904.py --하나 96   (하나만)
"""
import datetime as dt
import io
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_night0904.log")
LABS = os.path.join(_BASE, "data", "_labs")

# ⚠️ **순서는 가치 순이다.** 08:00 브리핑과 겹치면 안 되므로
#    뒤로 밀리는 것이 덜 중요한 것이어야 한다.
#    97차는 자정 수집(00:05~01:00)이 끝나야 하므로 어차피 뒤가 낫다.
#    01:15 시작 · 시간 상한을 다 쓰면 07:15에 끝난다
차수 = (
    ("96", "prob2_lab.py", "브리핑용 확률표 (금리 국면 · 한국 금리 · 보정 확인)", 3600),
    ("98", "robust_lab.py", "낙폭까지 보고 문턱 고르기 (최종 확정)", 7200),
    ("99", "big_lab.py", "보조 전략 — 하이닉스 말고 다른 대형주도", 4800),
    ("97", "sweep2_lab.py", "새 자료로 다시 훑기 (공시·업종·증자감자)", 6000),
)


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def main():
    골 = None
    if "--하나" in sys.argv:
        골 = sys.argv[sys.argv.index("--하나") + 1]
    os.makedirs(LABS, exist_ok=True)
    찍기(f"===== 09-04 새벽 자동 테스트 시작 (고른 것: {골 or '전부'}) =====")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for 번, 파일, 무엇, 제한 in 차수:
        if 골 and 번 != 골:
            continue
        p = os.path.join(_BASE, "scripts", 파일)
        if not os.path.exists(p):
            찍기(f"  ⚠️ {번}차 {파일} 없음 — 건너뜀")
            continue
        나 = os.path.join(LABS, f"2026-09-04_{번}.txt")
        찍기(f"  {번}차 시작 — {무엇}")
        시 = dt.datetime.now()
        try:
            with io.open(나, "w", encoding="utf-8") as fp:
                r = subprocess.run([sys.executable, p], stdout=fp,
                                   stderr=subprocess.STDOUT, env=env,
                                   timeout=제한, cwd=_BASE)
            걸 = (dt.datetime.now() - 시).total_seconds() / 60
            찍기(f"  {번}차 끝 — 코드 {r.returncode} · {걸:.1f}분 · {나}")
        except subprocess.TimeoutExpired:
            찍기(f"  ⚠️ {번}차 시간 초과 ({제한/60:.0f}분) — 다음으로 넘어간다")
        except Exception as e:
            찍기(f"  ⚠️ {번}차 실패 {type(e).__name__} {str(e)[:80]}")
    찍기("===== 끝 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
