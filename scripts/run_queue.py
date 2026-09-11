#!/usr/bin/env python3
r"""
run_queue.py — **시험을 차례로 하나씩 돌린다** (2026-09-08 신설)

## 왜
```
09-08에 144차와 145차를 같이 띄웠더니 **144차가 메모리 부족으로 조용히 죽었다.**
결과 파일이 0바이트인 걸 나중에야 알았다.
시험 하나가 6GB를 쓰기도 한다 — **같이 돌리면 안 된다**
```

## 하는 일
```
목록에 적힌 시험을 **하나씩 차례로** 돌린다
  · 앞 것이 끝나야 다음 것을 시작한다
  · 결과 파일이 **비어 있으면 「죽었다」로 적는다** (조용히 넘어가지 않는다)
  · 로그: data/_queue.log
```

쓰는 법:
    python scripts\run_queue.py
    python scripts\run_queue.py --목록          # 무엇이 돌 건지만 보기
"""
import datetime as dt
import io
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_queue.log")
_LABS = os.path.join(_BASE, "data", "_labs")

# (차수, 스크립트, 결과파일이름, 무엇을 하나)
차례 = [
    (144, "solo_lab.py", "2026-09-08_144차_단독재료.txt",
     "재료 16개를 각각 **축으로** 놓고 규칙을 짠다 (우리 조건 없이)"),
    (146, "pair_lab.py", "2026-09-08_146차_신호별매도.txt",
     "신호마다 파는 시점을 따로 정한다 (145차: 신호별로 기간이 다르다)"),
    (147, "gate4_lab.py", "2026-09-08_147차_국면낙폭관문.txt",
     "「시장 -10%↓면 낙폭 -5%」에 4관문 (142차 B절이 두 기간 다 이겼다)"),
    (149, "rebound_lab.py", "2026-09-08_149차_급등되돌림.txt",
     "「이유 없이 빠진 것」과 「3배 급등 뒤 되돌리는 것」을 가른다 (아이크래프트)"),
    (148, "one_lab.py", "2026-09-08_148차_단일매도격자.txt",
     "하나로 다 팔까 나눠 팔까 — 139차 격자에 비율 1.0 이 없었다"),
    (150, "walk3_lab.py", "2026-09-08_150차_걷기검증.txt",
     "⭐ 지금 규칙 **전체**를 걷기 검증 — 그 해 이전만 보고 문턱을 정해 그 해를 산다"),
    (151, "limit_lab.py", "2026-09-08_151차_지정가매수.txt",
     "⭐ 예상체결가에 지정가로 걸면 — 지금 시뮬이 실제보다 낙관적인 걸 고친다"),
    (152, "window_lab.py", "2026-09-08_152차_창훑기.txt",
     "낙폭·볼린저 **창**을 다 훑는다 (5~250일) — 창은 한 번도 안 봤다"),
]


def 찍기(s):
    line = f"{dt.datetime.now():%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main():
    if "--목록" in sys.argv:
        for n, s, o, 뭐 in 차례:
            있 = "✅" if os.path.exists(os.path.join(_BASE, "scripts", s)) \
                else "❌ 없음"
            print(f"  {n}차  {s:<18}{있:<8}{뭐}")
        return 0

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    찍기(f"===== 줄 서서 돌리기 시작 · {len(차례)}개 =====")
    for n, 스, 결과, 뭐 in 차례:
        p = os.path.join(_BASE, "scripts", 스)
        out = os.path.join(_LABS, 결과)
        if not os.path.exists(p):
            찍기(f"  ⚠️ {n}차 {스} — **스크립트가 없다.** 건너뛴다")
            continue
        if os.path.exists(out) and os.path.getsize(out) > 500:
            찍기(f"  · {n}차 — 이미 결과가 있다. 건너뛴다")
            continue
        찍기(f"  ▶ {n}차 {스} 시작 — {뭐}")
        시 = dt.datetime.now()
        try:
            with io.open(out, "w", encoding="utf-8") as f:
                r = subprocess.run([sys.executable, p], stdout=f,
                                   stderr=subprocess.STDOUT,
                                   timeout=10800, env=env, cwd=_BASE)
            초 = (dt.datetime.now() - 시).total_seconds()
            크 = os.path.getsize(out)
            if 크 < 500:
                찍기(f"  ❌ {n}차 — **결과가 비었다({크}바이트).** "
                     f"죽었을 수 있다 (코드 {r.returncode})")
            else:
                찍기(f"  ✅ {n}차 끝 ({초/60:.0f}분 · {크:,}바이트)")
        except subprocess.TimeoutExpired:
            찍기(f"  ❌ {n}차 — 3시간을 넘겨 멈췄다")
        except Exception as e:  # noqa: BLE001
            찍기(f"  ❌ {n}차 — {type(e).__name__} {str(e)[:80]}")
    찍기("===== 다 돌렸다 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
