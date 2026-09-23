r"""E3·E8 — **실전 기록으로 상대갭과 자리를 검산한다** (2026-09-23 · 연휴 계획 E3·E8)

E3 상대갭 −3.5%p 가 실전에서 어떻게 걸리나 — 후보들의 상대갭 분포 · 날마다 몇 개가 통과하나
E8 자리가 묶이나 — 통과한 것이 하루 자리(rule_def.하루최대종목)보다 많은 날 비율

자료: data/forward-log.jsonl (하루 한 줄 · 후보 전부와 그날 값)
⚠️ 앞으로의 성적(D+5·D+20)은 아직 안 쌓였다 — 여기서는 **고르는 자리**만 본다.

쓰기: python scripts/forward_stats.py
"""
import io
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "scripts"))
import rule_def as R  # noqa: E402

줄들 = []
for z in io.open(os.path.join(뿌리, "data", "forward-log.jsonl"), encoding="utf-8-sig"):
    z = z.strip()
    if not z:
        continue
    try:
        줄들.append(json.loads(z))
    except ValueError:
        pass

print(f"E3·E8 — 실전 기록 {len(줄들)}일 "
      f"({줄들[0].get('신호기준일') if 줄들 else '?'} ~ {줄들[-1].get('신호기준일') if 줄들 else '?'})")
if len(줄들) < 15:
    print(f"⚠️ **표본이 얇다 ({len(줄들)}일).** 자리·문턱을 이 값으로 바꾸지 않는다")

문턱 = R.상대갭문턱
자리 = R.하루최대종목
print(f"   지금: 상대갭 {문턱:+.1f}%p · 하루 {자리}자리\n")
print(f"   {'기준일':<10}{'후보':>6}{'상대갭 있음':>12}{'문턱 통과':>10}{'가운데 상대갭':>14}{'가장 나쁜':>10}  자리")
묶인날, 잰날, 통과수들 = 0, 0, []
for d in 줄들:
    후보 = d.get("후보") or []
    갭들 = [c.get("상대갭") for c in 후보 if isinstance(c.get("상대갭"), (int, float))]
    if not 갭들:
        print(f"   {str(d.get('신호기준일')):<10}{len(후보):>6}{0:>12}{'—':>10}")
        continue
    잰날 += 1
    통과 = [z for z in 갭들 if z <= 문턱]
    통과수들.append(len(통과))
    묶임 = len(통과) > 자리
    묶인날 += 1 if 묶임 else 0
    print(f"   {str(d.get('신호기준일')):<10}{len(후보):>6}{len(갭들):>12}{len(통과):>10}"
          f"{st.median(갭들):>13.2f}%{min(갭들):>9.2f}%  "
          + ("❗ 자리 모자람" if 묶임 else "괜찮다"))

if 잰날:
    print(f"\n   ⇒ E8 자리 묶임 — {묶인날}/{잰날}일 ({묶인날 / 잰날 * 100:.0f}%) 에서 통과가 {자리}개를 넘었다")
    print(f"   ⇒ 문턱 통과 개수 — 가운데 {st.median(통과수들):.1f} · 가장 많은 날 {max(통과수들)}")
    if max(통과수들) <= 자리:
        print("      (지금 표본에서는 자리가 병목이 아니다 — 후보가 자리보다 적다)")
    # E3 — 문턱을 옮기면 통과가 몇 개로 바뀌나 (실전 기록 기준)
    print(f"\n   E3 상대갭 문턱을 옮기면 (실전 기록 {잰날}일)")
    print(f"   {'문턱':<10}{'통과 합계':>10}{'하루 평균':>10}{'자리 넘는 날':>13}")
    for 컷 in (-2.0, -2.5, -3.0, -3.5, -4.0, -4.5, -5.0):
        합, 넘 = 0, 0
        for d in 줄들:
            갭들 = [c.get("상대갭") for c in (d.get("후보") or [])
                    if isinstance(c.get("상대갭"), (int, float))]
            if not 갭들:
                continue
            _t = sum(1 for z in 갭들 if z <= 컷)
            합 += _t
            넘 += 1 if _t > 자리 else 0
        print(f"   {컷:+.1f}%p{'':<4}{합:>10}{합 / 잰날:>10.1f}{넘:>13}"
              + ("   ← 지금" if abs(컷 - 문턱) < 1e-9 else ""))
