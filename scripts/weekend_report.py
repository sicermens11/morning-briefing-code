#!/usr/bin/env python3
r"""
weekend_report.py — **주말에 뭐가 나왔나 한 장으로** (2026-09-04 신설)

## 왜 만드나
```
주말에 시험 6개 + AutoSearch 5회가 돈다. 결과가 파일 일곱 군데에 흩어진다.
월요일 아침에 그걸 다 뒤지면 시간이 간다.
⇒ **한 장으로 모아준다.** 무엇이 나왔고 무엇이 실패했나
```
⚠️ **판정은 안 한다.** 「이건 채택하자」 같은 말은 사람이 결과를 보고 정한다.
   여기는 **무슨 일이 있었나**만 모은다.

쓰는 법:
    python scripts\weekend_report.py
    python scripts\weekend_report.py --날짜 2026-09-05
"""
import glob
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LABS = os.path.join(_BASE, "data", "_labs")


def 꼬리(p, n=6):
    try:
        줄 = [x.rstrip() for x in io.open(p, encoding="utf-8",
                                          errors="replace")]
    except Exception:
        return []
    return [x for x in 줄 if x.strip()][-n:]


def main():
    골날 = None
    if "--날짜" in sys.argv:
        골날 = sys.argv[sys.argv.index("--날짜") + 1]

    print("═" * 78)
    print("  주말에 뭐가 나왔나")
    print("═" * 78)

    # ── 1. 실행 로그 ──
    print("\n  ══ 1. 돌긴 돌았나 ══")
    for 이름, p in (("주말 시험", "_weekend.log"),
                    ("아침 준비", "_morning_prep.log"),
                    ("증자·감자 수집", "_capital.log")):
        f = os.path.join(_BASE, "data", p)
        if not os.path.exists(f):
            print(f"    ⚠️ {이름}: 로그가 없다 ({p})")
            continue
        줄 = 꼬리(f, 4)
        print(f"\n    ── {이름} ({p}) ──")
        for x in 줄:
            print(f"      {x[:120]}")

    # ── 2. 시험 결과 ──
    print("\n" + "═" * 78)
    print("  ══ 2. 시험 결과 ══")
    쓸 = sorted(glob.glob(os.path.join(_LABS, "2026-09-0[5-7]_*.txt")))
    if golf := (골날 and [x for x in 쓸 if 골날 in x]):
        쓸 = golf
    if not 쓸:
        print("    ⚠️ 주말 시험 결과 파일이 없다 — 예약이 안 돌았을 수 있다")
    for f in 쓸:
        b = os.path.basename(f)
        크 = os.path.getsize(f)
        try:
            t = io.open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        상 = "❌ Traceback" if "Traceback" in t else (
            "⚠️ 파싱 0건" if re.search(r"있는 종목 0개|파싱 결과가 0", t)
            else "✅")
        print(f"\n    ── {b}  ({크:,}자)  {상} ──")
        # ⭐가 붙은 줄과 「⇒」로 시작하는 결론 줄을 뽑는다
        고른 = [x.rstrip() for x in t.splitlines()
                if ("⭐" in x or x.strip().startswith("⇒")
                    or "**" in x) and len(x.strip()) > 8]
        if 고른:
            for x in 고른[:14]:
                print(f"      {x.strip()[:118]}")
            if len(고른) > 14:
                print(f"      … 외 {len(고른)-14}줄 (파일을 직접 보라)")
        else:
            for x in 꼬리(f, 6):
                print(f"      {x[:118]}")

    # ── 3. 격자 탐색 ──
    print("\n" + "═" * 78)
    print("  ══ 3. 주말 격자 탐색 (AutoSearch) ══")
    상위 = os.path.join(_BASE, "data", "_search", "상위.txt")
    결과 = os.path.join(_BASE, "data", "_search", "결과.jsonl")
    if os.path.exists(결과):
        n = sum(1 for x in io.open(결과, encoding="utf-8",
                                   errors="replace") if x.strip())
        print(f"    돌린 조합 **{n:,}개**")
    else:
        print("    ⚠️ 결과 파일이 없다 — AutoSearch가 안 돌았을 수 있다")
    if os.path.exists(상위):
        줄 = [x.rstrip() for x in io.open(상위, encoding="utf-8",
                                          errors="replace")]
        for x in 줄[:16]:
            print(f"    {x[:118]}")
        if len(줄) > 16:
            print(f"    … 외 {len(줄)-16}줄 → {상위}")
    else:
        print(f"    ⚠️ {상위} 없음")

    # ── 4. 예측 기록 ──
    print("\n" + "═" * 78)
    print("  ══ 4. 예측 기록 ══")
    LOG = os.path.join(_BASE, "data", "forward-log.jsonl")
    if os.path.exists(LOG):
        rs = []
        for x in io.open(LOG, encoding="utf-8"):
            x = x.strip()
            if x:
                try:
                    rs.append(json.loads(x))
                except Exception:
                    pass
        후 = sum(len(r.get("후보") or []) for r in rs)
        끝 = sum(1 for r in rs for x in (r.get("후보") or [])
                 if x.get("결과") is not None)
        삼 = sum(1 for r in rs for x in (r.get("후보") or [])
                 if x.get("규칙매수"))
        print(f"    기록한 날 {len(rs)}일 · 후보 {후}건 · "
              f"규칙이 사라고 한 것 {삼}건 · 결과 나온 것 **{끝}건**")
        if rs:
            마 = rs[-1]
            print(f"    마지막 기록 {마.get('기록시각','')} · "
                  f"신호기준일 {마.get('신호기준일','')} · "
                  f"후보 {마.get('후보수',0)}개")
    else:
        print("    ⚠️ forward-log.jsonl 없음")

    # ── 5. 브리핑 조각 ──
    print("\n" + "═" * 78)
    print("  ══ 5. 브리핑에 붙을 조각 ══")
    h = os.path.join(_BASE, "data", "today-rule.html")
    if os.path.exists(h):
        s = io.open(h, encoding="utf-8", errors="replace").read()
        m = re.search(r"오늘 볼 종목: ([^<]{0,60})", s)
        print(f"    today-rule.html {len(s):,}자 · "
              f"{m.group(1).strip() if m else '(못 읽음)'}")
    else:
        print("    ⚠️ today-rule.html 없음 — 브리핑에서 그 절이 빠진다")

    print("\n" + "═" * 78)
    print("  ⚠️ 여기는 **무슨 일이 있었나**만 모은 것이다.")
    print("     「이건 채택하자」는 판정은 결과를 직접 보고 정한다")
    print("═" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
