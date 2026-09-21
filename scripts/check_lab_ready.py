r"""Q절이 **밤새 돌다 죽지 않을지** 미리 본다 (2026-09-21 확장)

[[do-before-promising]] — 밤 판이 터지면 그 시간이 통째로 날아간다.
9/18 `_달력` vs `_달력P` NameError 로 6시간을 몰랐고,
9/21 13:59 `_c() got multiple values for argument '거름'` 로 SEAT 판이 죽었다.

보는 것 셋:
  ① 이름 — Q절이 읽는 이름이 그 자리에서 살아 있나
  ② 거름 겹침 — `_c(거름, ..., 거름=...)` 처럼 **거름을 두 번** 넘기나  ← 9/21 사고
  ③ 짝 안 맞는 풀기 — `for a, b in 목록` 인데 목록 원소가 셋인가         ← 9/21 사고
"""
import ast
import builtins
import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os as _os
_BASE = _os.path.dirname(_os.path.abspath(__file__))
P = _os.environ.get("LAB_FILE") or _os.path.join(_BASE, "gate7_lab.py")
src = io.open(P, encoding="utf-8-sig").read()
나무 = ast.parse(src)
줄들 = src.splitlines()

시작 = None
for i, z in enumerate(줄들):
    if "Q ⭐⭐⭐ **㉢·㉤ 문턱 다시**" in z and "print" in z:
        시작 = i + 1
        break
assert 시작, "Q절을 못 찾겠다"
print(f"Q절 — {시작}줄부터 파일 끝({len(줄들)})까지")


def 묶인이름(노드):
    out = set()
    for n in ast.walk(노드):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, ast.comprehension):
            for m in ast.walk(n.target):
                if isinstance(m, ast.Name):
                    out.add(m.id)
    return out


품은 = None
for n in ast.walk(나무):
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if n.lineno <= 시작 <= (n.end_lineno or 0):
            if 품은 is None or n.lineno > 품은.lineno:
                품은 = n
assert 품은
쓸수있는 = 묶인이름(품은) | 묶인이름(나무) | set(dir(builtins))

탈 = []

# ── ① 이름 ──
읽는 = {}
for n in ast.walk(품은):
    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and 시작 <= n.lineno:
        읽는.setdefault(n.id, n.lineno)
모름 = {k: v for k, v in 읽는.items() if k not in 쓸수있는}
print(f"① 읽는 이름 {len(읽는)}개 · 못 찾은 것 {len(모름)}개")
for k, v in sorted(모름.items(), key=lambda t: t[1]):
    탈.append(f"① {k} ({v}줄) 이 없다")

# ── ② 거름 겹침 — _c(첫인자, ..., 거름=...) ──
#    ⚠️ 9/21 13:59 에 이걸로 SEAT 판이 죽었다:
#       _c(_H, **dict(큰자리=1, 거름=...)) → 거름이 위치인자와 키워드로 둘
겹 = 0
for n in ast.walk(품은):
    if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_c"):
        continue
    if (n.lineno or 0) < 시작:
        continue
    위치 = len(n.args)
    키 = {k.arg for k in n.keywords if k.arg}
    if 위치 >= 1 and "거름" in 키:
        탈.append(f"② _c() 에 거름이 두 번 ({n.lineno}줄)")
        겹 += 1
    # **옵 처럼 펼치는 것은 이름으로 못 보므로, 그 딕셔너리에 거름이 들었는지 글로 본다
    for k in n.keywords:
        if k.arg is None and isinstance(k.value, ast.Name):
            이름 = k.value.id
            for z in 줄들[시작:]:
                if re.search(rf"{re.escape(이름)}\s*=.*거름\s*=", z) or \
                   re.search(rf"dict\([^)]*거름\s*=", z):
                    if 위치 >= 1:
                        탈.append(f"② _c(…, **{이름}) 인데 {이름} 안에 거름이 있다 ({n.lineno}줄)")
                        겹 += 1
                    break
print(f"② _c() 거름 겹침 {겹}곳")

# ── ③ 짝 안 맞는 풀기 — for a, b in 목록 인데 원소가 셋 ──
짝 = 0
for n in ast.walk(품은):
    if not (isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)):
        continue
    if (n.lineno or 0) < 시작:
        continue
    받는수 = len(n.target.elts)
    목록 = n.iter
    if isinstance(목록, ast.Name):
        # 그 이름이 어디서 만들어졌나 — 원소 길이가 다르면 잡는다
        for m in ast.walk(품은):
            if (isinstance(m, ast.Assign) and len(m.targets) == 1
                    and isinstance(m.targets[0], ast.Name)
                    and m.targets[0].id == 목록.id
                    and isinstance(m.value, (ast.List, ast.Tuple))):
                길이 = {len(e.elts) for e in m.value.elts if isinstance(e, ast.Tuple)}
                if 길이 and 받는수 not in 길이:
                    탈.append(f"③ {n.lineno}줄: {받는수}개로 푸는데 {목록.id} 원소는 {sorted(길이)}개")
                    짝 += 1
print(f"③ 짝 안 맞는 풀기 {짝}곳")

print()
if 탈:
    for z in 탈:
        print("   ❌", z)
    print("\n❌ 이대로 돌리면 죽는다")
    sys.exit(1)
print("✅ Q절 — 이름·거름 겹침·짝 풀기 전부 이상 없다")
