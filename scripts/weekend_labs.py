#!/usr/bin/env python3
r"""
weekend_labs.py — **주말 자동 검증 묶음** (2026-09-05 토요일 04:00)

## 왜 04:00인가
```
00:10  CapitalResume0905 이 증자·감자 나머지 988종목을 받는다 (약 3시간, 망 작업)
       -> 03:10쯤 끝난다
04:00  **자료가 다 찬 뒤에** 재판정한다
⚠️ 00:05부터 AutoSearch가 CPU를 쓰고 있다. 이건 격자 탐색이라 겹쳐도 된다
   (둘 다 느려질 뿐 결과는 같다)
```

## 도는 것 (차례대로)
```
① 증자·감자 재판정      자료 3,000 -> 3,988종목(100%)으로 97차를 다시
                       ⚠️ 97c에서 「이겼다」 -> 97d에서 자사주처분 넣으니 「졌다」
                          자료가 75%였다. 100%로 다시 재야 확정된다
② 규칙 사례 갱신        build_rule_cases.py — 브리핑에 나가는 표를 새로
③ 최종 통합 재검증      verify_all.py — 규칙이 그대로인지 확인
④ 자체 점검            selfcheck.py
```
⚠️ 하나가 죽어도 다음을 돈다. 결과는 `data/_labs/2026-09-05_*.txt`에 남는다

쓰는 법:
    python scripts\weekend_labs.py
로그: `data/_weekend.log`
"""
import datetime as dt
import io
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_weekend.log")
LABS = os.path.join(_BASE, "data", "_labs")

차례 = (
    ("증자감자재판정", "sweep2_lab.py", "자료 100%로 97차 다시", 5400),
    ("안써본자료훑기", "untested_lab.py",
     "증자 크기 · 업종지수 · 외국인지분율 (927개 중 616개가 미사용)", 7200),
    ("흐름모양", "shape_lab.py",
     "얼마나 빠졌나가 아니라 **어떻게** 빠졌나 (연속하락·가속·60일·120일)", 7200),
    ("사례갱신", "build_rule_cases.py", "브리핑 표를 새로", 3600),
    ("통합재검증", "verify_all.py", "규칙이 그대로인지", 7200),
    ("자체점검", "selfcheck.py", "자료·예약·문법·함정", 1800),
)


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as fp:
            fp.write(line + "\n")
    except Exception:
        pass


def 성한가(나):
    """결과 파일 하나가 온전한가"""
    if not os.path.exists(나) or os.path.getsize(나) < 2048:
        return False
    try:
        t = io.open(나, encoding="utf-8", errors="replace").read()
    except Exception:
        return False
    if "Traceback" in t:
        return False
    # 끝맺음: 마지막 400자 안에 구분선이나 「끝」이 있어야 온전히 끝난 것
    끝 = t[-400:]
    return ("═" in 끝 or "끝" in 끝 or "⇒" in 끝)


def 이미끝났나(이름):
    r"""이 단계가 이미 제대로 끝났나 — **이어 돌기용** (2026-09-04 신설)

    ⚠️ 왜 만드나: **2026-09-01 18:09에 PC가 비정상 종료됐다** (Kernel-Power 41).
       주말 시험은 6개가 최대 6시간을 돈다. 4번째에서 PC가 죽으면
       예약은 「돌았다」로 치고 넘어가고, **앞의 3개까지 다시 돌려야 했다**
    ⇒ 결과 파일이 **성하게 남아 있으면 건너뛴다.** 죽은 지점부터 이어진다

    성하다 = ① 파일이 있고 ② 2KB 넘고 ③ Traceback이 없고
             ④ **끝맺음 줄이 있다** (중간에 끊긴 게 아니다)

    ⚠️⚠️ **오늘 날짜만 보면 안 된다.** 토요일 04:00에 돌다 죽고
       일요일 04:00(예비)에 다시 돌면, 파일 이름이 `2026-09-06_…`이라
       토요일의 `2026-09-05_…`를 **못 찾고 전부 다시 돈다**
    ⇒ **최근 3일치를 다 본다.** 성한 게 하나라도 있으면 끝난 것으로 친다
    """
    오 = dt.date.today()
    for d in range(3):
        날 = (오 - dt.timedelta(days=d)).strftime("%Y-%m-%d")
        p = os.path.join(LABS, f"{날}_{이름}.txt")
        if 성한가(p):
            return p
    return None


def main():
    os.makedirs(LABS, exist_ok=True)
    오늘 = dt.date.today().strftime("%Y-%m-%d")
    이어 = "--처음부터" not in sys.argv
    찍기(f"===== 주말 검증 묶음 시작 ({오늘}) "
         f"{'· 이어 돌기' if 이어 else '· 처음부터'} =====")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    실패 = 0
    for 이름, 파일, 무엇, 제한 in 차례:
        p = os.path.join(_BASE, "scripts", 파일)
        if not os.path.exists(p):
            찍기(f"  ⚠️ {이름}: {파일} 없음 — 건너뜀")
            실패 += 1
            continue
        나 = os.path.join(LABS, f"{오늘}_{이름}.txt")
        옛 = 이미끝났나(이름) if 이어 else None
        if 옛:
            찍기(f"  ⏭ {이름} 건너뜀 — 결과가 이미 성하게 있다 "
                 f"({os.path.basename(옛)} · {os.path.getsize(옛):,}자). "
                 f"다시 돌리려면 --처음부터")
            continue
        찍기(f"  {이름} 시작 — {무엇}")
        시 = dt.datetime.now()
        try:
            with io.open(나, "w", encoding="utf-8") as fp:
                r = subprocess.run([sys.executable, p], stdout=fp,
                                   stderr=subprocess.STDOUT, env=env,
                                   timeout=제한, cwd=_BASE)
            분 = (dt.datetime.now() - 시).total_seconds() / 60
            찍기(f"  {이름} 끝 — 코드 {r.returncode} · {분:.1f}분 · {나}")
            if r.returncode != 0:
                실패 += 1
        except subprocess.TimeoutExpired:
            실패 += 1
            찍기(f"  ⚠️ {이름} 시간 초과 ({제한/60:.0f}분)")
        except Exception as e:
            찍기(f"  ⚠️ {이름} 실패 {type(e).__name__} {str(e)[:80]}")
            실패 += 1
    찍기(f"===== 끝 · 실패 {실패}건 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
