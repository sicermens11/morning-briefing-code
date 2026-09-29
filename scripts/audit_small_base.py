#!/usr/bin/env python3
# ⚠️ docstring 은 r""" (raw) — 윈도 경로의 `\u` 가 유니코드 이스케이프로 해석되면 파일이 깨진다.
r"""audit_small_base.py — **띠 절에 소형 규칙이 섞였나 전수 조사** (2026-09-29 신설)

## 왜 있나
사용자: 「내가 지적 한거 말고도 대형이나 중형 테스트에 소형 규칙을 적용한 거 없는지
        전수 조사하고 테스트 필요하면 바로 걸어」

막개(check_lab_ready) ④가 「띠를 나눠 재는 절에서 소형 바탕을 쓰나」를 본다.
그런데 **예외 구멍이 넷** 있다:
    [견줌] + 띠 전용 규칙 · [지난 절] · [TRACE] · [바탕 덜기]
2026-09-28~29 에 내가 그 구멍(특히 `[견줌]`)으로 **여러 번 빠져나갔다.**
막개는 「걸리지 않았다」만 말하고 **「구멍으로 나갔다」는 말 안 한다.**

⇒ 이 조사기는 **구멍으로 나간 절을 전부 드러낸다.** 봐주지 않는다.

## 무엇을 보나
  ① `_ONLY` 절마다 — 띠(시총)를 나누나 · 소형 바탕(`_H(` · `R.볼린저문턱` · `R.낙폭20문턱`
     · `R.상대갭문턱` · `_밑상대갭` · `문통과(`)을 쓰나 · **어느 구멍으로 나갔나**
  ② 그 절이 **실제로 돌아간 결과 파일**이 있나 (data/_labs)
  ③ 한 줄 판정 — 🔴 다시 해야 한다 / ⚠️ 견줌으로만 썼다 / ✅ 깨끗하다

⚠️ `문통과(` 도 소형 바탕이다 — 안에 `크기통과`(300~2,000억)가 들어 있다.
   막개 ④ 목록엔 없어서 지금까지 안 걸렸다.

쓰기: python scripts/audit_small_base.py
나가는 값: 🔴 가 하나라도 있으면 1
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_여기 = os.path.dirname(os.path.abspath(__file__))
_뿌리 = os.path.dirname(_여기)
_랩 = os.path.join(_뿌리, "data", "_labs")

src = io.open(os.path.join(_여기, "gate7_lab.py"), encoding="utf-8-sig").read()
줄들 = src.splitlines()

# 소형 바탕 — 막개 ④ 목록 + **막개가 빠뜨린 `문통과(`**
소형바탕 = {
    "_H(": "_H(x) — 지금 소형 규칙",
    "문통과(": "문통과(x) — 안에 크기통과(300~2,000억)가 있다  ⚠️ 막개 ④가 안 보는 것",
    "R.볼린저문턱": "R.볼린저문턱 — 소형에서 고른 값",
    "R.낙폭20문턱": "R.낙폭20문턱 — 소형에서 고른 값",
    "R.상대갭문턱": "R.상대갭문턱 — 소형에서 고른 값",
    "_밑상대갭": "_밑상대갭 — 소형에서 고른 값",
}
구멍 = ("[견줌]", "[지난 절]", "[TRACE]", "[바탕 덜기]")

# ── 절 경계: `_ONLY == "X"` 로 나눈다 ──
절 = []
for m in re.finditer(r'_ONLY == "([A-Z0-9_-]+)"', src):
    _줄번 = src[:m.start()].count("\n") + 1
    절.append((m.group(1), _줄번))
절.sort(key=lambda z: z[1])

# 결과 파일에 그 절이 찍혔나
_결과 = {}
for f in glob.glob(os.path.join(_랩, "*.txt")):
    try:
        g = io.open(f, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    for h in set(re.findall(r"^\s*── ([A-Z0-9_-]+) [⭐ ]", g, re.M)):
        _결과.setdefault(h, []).append(os.path.basename(f)[:30])

# ⭐ 2026-09-29 — `--절 A,B` 를 주면 **그 절만** 본다. 큐 스크립트가 판을 띄우기 **전에**
#    이걸 부르고, 오염됐으면 판을 안 띄운다. **내 재량이 아니다**
_고른절 = None
if "--절" in sys.argv:
    _i = sys.argv.index("--절")
    if _i + 1 < len(sys.argv):
        _고른절 = {z.strip().upper() for z in re.split(r"[,+]", sys.argv[_i + 1]) if z.strip()}

print("=" * 104)
print("  띠 절에 소형 규칙이 섞였나 — 전수 조사 (막개 ④의 **예외 구멍**까지 본다)"
      + (f"   [고른 절: {' · '.join(sorted(_고른절))}]" if _고른절 else ""))
print("=" * 104)

나쁨, 경고, 깨끗 = [], [], []
for i, (이름, 시작) in enumerate(절):
    끝 = 절[i + 1][1] - 1 if i + 1 < len(절) else len(줄들)
    몸 = 줄들[시작 - 1:끝]
    코드 = [z for z in 몸 if not z.lstrip().startswith("#")]
    if _고른절 is not None and 이름.upper() not in _고른절:
        continue
    # 띠를 나누는 절인가
    if not any("시총억" in z for z in 코드):
        continue
    걸림, 쓴구멍 = [], set()
    for z in 코드:
        for 표, 왜 in 소형바탕.items():
            if 표 in z:
                걸림.append((왜, z.strip()[:70]))
                for _g in 구멍:
                    if _g in z:
                        쓴구멍.add(_g)
    _판 = _결과.get(이름) or []
    if not 걸림:
        깨끗.append((이름, len(_판)))
    elif 쓴구멍:
        경고.append((이름, 걸림, sorted(쓴구멍), _판))
    else:
        나쁨.append((이름, 걸림, [], _판))

print(f"\n  띠를 나누는 절 {len(나쁨) + len(경고) + len(깨끗)}개"
      f" — 🔴 {len(나쁨)} · ⚠️ {len(경고)} · ✅ {len(깨끗)}")

if 나쁨:
    print("\n  🔴 **소형 바탕을 쓰는데 아무 표시도 없다** (막개가 왜 안 걸렸는지 봐야 한다)")
    for 이름, 걸림, _, 판 in 나쁨:
        print(f"     [{이름}]  돌아간 판 {len(판)}개")
        for 왜, 줄 in 걸림[:3]:
            print(f"        · {왜}")
            print(f"          {줄}")

if 경고:
    print("\n  ⚠️ **구멍으로 빠져나간 절** — 소형 바탕을 쓰는데 표시를 붙여 막개를 통과했다")
    for 이름, 걸림, 구, 판 in 경고:
        print(f"\n     [{이름}]  구멍 {' '.join(구)}  ·  돌아간 판 {len(판)}개"
              + (f"  ({' · '.join(판[-2:])})" if 판 else ""))
        _본 = set()
        for 왜, 줄 in 걸림:
            if 왜 in _본:
                continue
            _본.add(왜)
            print(f"        · {왜}")
            print(f"          {줄}")

if 깨끗:
    print("\n  ✅ 띠를 나누면서 소형 바탕을 **안 쓰는** 절")
    print("     " + " · ".join(f"{이름}({n}판)" for 이름, n in 깨끗))

print("\n" + "=" * 104)
print("  ⚠️ ⚠️ 표시가 붙었다고 괜찮은 게 아니다 — 「그 무리만의 규칙」을 재는 절이라면")
print("     견줌으로라도 소형 바탕을 깔면 **결과가 소형 규칙에 묶인다.** 다시 해야 한다")
print("=" * 104)
# ⚠️ `--절` 로 불렀을 때는 **⚠️ 도 실패**로 친다 — 큐가 이걸 보고 판을 안 띄운다
raise SystemExit(1 if (나쁨 or (_고른절 is not None and 경고)) else 0)
