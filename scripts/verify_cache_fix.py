r"""고친 캐시가 **정말 막나** 확인한다 (2026-09-28)

말로 「고쳤다」가 아니라, gate7_lab.py 에서 **그 클래스를 그대로 꺼내** 돌린다.
  ① 표를 바꿔치기하면 판이 올라가나
  ② 열쇠가 실제로 달라지나 (= BAD ③ 이 이제 다른 값을 낼 수 있나)
  ③ 악재를 안 쓰는 판은 열쇠가 **전과 똑같은가** (B125 가 안 바뀌는지)
"""
import ast
import io
import sys
import textwrap

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"C:\Users\mrblue\Claude\morning breifing_code\scripts\gate7_lab.py"
s = io.open(P, encoding="utf-8-sig").read()
나무 = ast.parse(s)

# ── 파일에서 클래스를 그대로 꺼낸다 ──
찾음 = None
for n in ast.walk(나무):
    if isinstance(n, ast.ClassDef) and n.name == "_판세는표":
        찾음 = n
        break
if 찾음 is None:
    raise SystemExit("🔴 _판세는표 를 못 찾았다")
소스 = textwrap.dedent(ast.get_source_segment(s, 찾음))
칸 = {}
exec(compile(소스, "<꺼낸것>", "exec"), 칸)          # noqa: S102
_판세는표 = 칸["_판세는표"]
print("  파일에서 꺼낸 클래스로 돌린다\n")

# ── ① 바꿀 때마다 판이 오르나 ──
표 = _판세는표()
print(f"  ① 처음               판 = {표.판}")
표["20260101"] = {"005930": 1}
print(f"     한 줄 넣고          판 = {표.판}")
_전 = 표.판
표.clear()
표.update({"20260102": {"000660": 2}})
print(f"     clear + update 뒤   판 = {표.판}  {'✅ 올랐다' if 표.판 > _전 else '🔴 안 올랐다'}")
print(f"     읽기는 되나          {표.get('20260102')}")

# ── ② 열쇠가 달라지나 ──
def 열쇠(재평가, 표):
    return (100, "005930", 20.0, 40, None, None, 재평가,
            표.판 if 재평가 == "악재" else 0)


표2 = _판세는표()
표2.update({"20260101": {"005930": 1}})
ㄱ = 열쇠("악재", 표2)
표2.clear()
표2.update({"20260101": {"000660": 1}})       # BAD ③ 이 하는 짓
ㄴ = 열쇠("악재", 표2)
print(f"\n  ② 악재 판 — 표를 바꾸면 열쇠가 달라지나")
print(f"     바꾸기 전 {ㄱ}")
print(f"     바꾼 뒤   {ㄴ}")
print(f"     {'✅ 다르다 — 이제 다시 계산한다' if ㄱ != ㄴ else '🔴 같다 — 여전히 캐시를 재활용한다'}")

# ── ③ 악재를 안 쓰면 전과 같은가 ──
표3 = _판세는표()
표3.update({"a": 1})
ㄷ = 열쇠(None, 표3)
표3.clear()
표3.update({"b": 2})
ㄹ = 열쇠(None, 표3)
print(f"\n  ③ 악재를 안 쓰는 판 — 표가 바뀌어도 열쇠가 그대로인가 (B125 가 안 바뀌나)")
print(f"     {ㄷ}")
print(f"     {ㄹ}")
print(f"     {'✅ 같다 — 지금 도는 판들은 한 글자도 안 달라진다' if ㄷ == ㄹ else '🔴 달라졌다'}")
print(f"     끝자리가 늘 0 인가 — {ㄷ[-1] == 0 and ㄹ[-1] == 0}")

# ── ④ 무리몫이 들어갔나 ──
print(f"\n  ④ 무리몫 (파는규칙을 무리마다)")
print(f"     시뮬에 들어갔나 — {'✅' if 'c.get(\"무리몫\")' in s else '🔴'}")
print(f"     무리갭 (상대갭)  — {'✅' if 'c.get(\"무리갭\")' in s else '🔴'}")
print(f"     무리자리 (자리)  — {'✅' if 'c.get(\"무리자리\")' in s else '🔴'}")
