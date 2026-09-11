#!/usr/bin/env python3
r"""
run_queue2.py — **시험을 하나씩 차례로 돌린다** (2026-09-08 신설)

## 왜 하나씩인가
```
157차가 램을 **10.8GB** 쥔다. 둘을 같이 돌리면 조용히 죽는다.
실제로 오늘 19:00 저녁 수집이 그렇게 밀려나 죽었다 (종료코드 0xC000013A)
144차도 같은 이유로 두 번 죽었다
```

## 규칙 (메모리 lab-results-must-persist · scheduled-task-checklist)
```
· 결과는 Temp가 아니라 **data/_labs/** 에 남긴다
· 결과가 500바이트 미만이면 **「죽었을 수 있다」**로 적는다
· 앞 시험이 죽어도 **다음 것을 계속 돌린다**
· 진행은 data/_labs/_queue.log 에 남는다
```

쓰는 법:
    python scripts\run_queue2.py            # 처음부터
    python scripts\run_queue2.py --기다림 13848   # 그 프로세스 끝나고 시작
"""
import os
import subprocess
import sys
import time

S = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(S)
L = os.path.join(BASE, "data", "_labs")
LOG = os.path.join(L, "_queue.log")

차례 = [
    (158, "delist_lab.py", "2026-09-08_158차_상장폐지영향.txt",
     "상장폐지를 손실로 세면 성적이 얼마나 내려가나 · 시총대별 노출"),
    (153, "chance_lab.py", "2026-09-08_153차_기회표.txt",
     "⚠️ `비` 이름 충돌로 B·C절을 못 봤다. 고치고 다시"),
    (156, "reach_lab.py", "2026-09-08_156차_도달률.txt",
     "「며칠 안에 몇 % 닿나」 — 매도 안내의 근거"),
    (160, "pick_lab2.py", "2026-09-08_160차_후보수와갭기준.txt",
     "좁힌 것 ①② — 후보 40개 · 갭 기준 중앙값"),
    (161, "entry2_lab.py", "2026-09-08_161차_국면지수와매수시각.txt",
     "좁힌 것 ③④ — 시장 지수 코스닥만 · 매수 09:00 시가만"),
    (162, "filter2_lab.py", "2026-09-08_162차_재무주기와관리종목.txt",
     "좁힌 것 ⑤⑥ — 재무 연간만 · 관리종목 그냥 제외"),
]


def 찍기(s):
    line = f"{time.strftime('%m-%d %H:%M:%S')}  {s}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def 살아있나(pid):
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                       capture_output=True, text=True, errors="ignore")
    return str(pid) in (r.stdout or "")


def main():
    if "--기다림" in sys.argv:
        pid = int(sys.argv[sys.argv.index("--기다림") + 1])
        찍기(f"===== pid {pid} 가 끝나기를 기다린다 =====")
        while 살아있나(pid):
            time.sleep(60)
        찍기("  끝남 — 60초 쉬고 시작")
        time.sleep(60)
    찍기(f"===== 줄서기 시작 · {len(차례)}개 =====")
    for n, 스, 결, 설 in 차례:
        p = os.path.join(L, 결)
        if os.path.exists(p) and os.path.getsize(p) > 20000:
            찍기(f"  {n}차 건너뜀 — 이미 결과가 있다 ({os.path.getsize(p):,}바이트)")
            continue
        찍기(f"\n▶ **{n}차** {스}  — {설}")
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, os.path.join(S, 스)],
                               cwd=BASE)
            코드 = r.returncode
        except Exception as e:  # noqa: BLE001
            코드 = -1
            찍기(f"  ⚠️ 못 돌렸다: {type(e).__name__} {e}")
        분 = (time.time() - t0) / 60
        크 = os.path.getsize(p) if os.path.exists(p) else 0
        말 = f"  {n}차 끝 · {분:.0f}분 · 종료코드 {코드} · 결과 {크:,}바이트"
        if 크 < 500:
            말 += "  ❌ **비었다 — 죽었을 수 있다**"
        elif 코드 != 0:
            말 += "  ⚠️ 종료코드가 0이 아니다"
        찍기(말)
    찍기("\n===== 줄서기 끝 =====")
    for n, _, 결, _ in 차례:
        p = os.path.join(L, 결)
        크 = os.path.getsize(p) if os.path.exists(p) else 0
        찍기(f"  {n}차  {크:>10,}바이트  {'✅' if 크 > 5000 else '❌'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
