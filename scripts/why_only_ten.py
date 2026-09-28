r"""**대형주는 왜 11년에 10건뿐인가** — 문을 하나씩 세어 본다 (2026-09-28)

사용자: 「11년에 10건밖에 안 뜨는 이유는 뭐야?」

추측하지 않는다. 판 덤프(h_events.jsonl · 130,197건)를 흘려 읽으며
**띠마다 문을 하나씩 통과하는 수**를 센다. 어느 문에서 죽는지가 답이다.

문 차례 (실전과 같게)
  ① 사건이 있다            — 그 종목 그날 자료가 있다
  ② 재무 문                — 잉여금 ≥ 30% · 부채 ≤ 80% · 흑자
  ③ 대금 문                — 거래대금 ≥ 1억
  ④ 신호                   — 볼린저 ≤ -1.0σ **그리고** 20일 낙폭 ≤ -10%
  ⑤ 상대갭                 — 그날 후보들 중앙갭보다 3.5%p 더 빠졌다
  ⑥ 하루 자리              — 그날 6등 안에 든다

⚠️ 덤프는 **Ⓗ 를 통과한 것 위주**라 ①의 절대수는 전체가 아니다.
   그래도 **띠끼리 견주는 데는 쓸 수 있다** — 같은 잣대로 걸렀으니까.
⚠️ 메모리: 한 줄씩 읽는다. 2.2억 바이트를 통째로 안 올린다.
"""
import io
import json
import sys
from collections import defaultdict

sys.path.insert(0, r"C:\Users\mrblue\Claude\morning breifing_code\scripts")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import rule_def as R  # noqa: E402

길 = r"C:\Users\mrblue\Claude\morning breifing_code\data\_labs\h_events.jsonl"

띠들 = ("소형 300~2,000억", "중형 2,000억~1조", "대형 1조↑")


def 띠(시총):
    if 시총 is None:
        return None
    if 시총 < 300:
        return None
    if 시총 < 2000:
        return 띠들[0]
    if 시총 < 10000:
        return 띠들[1]
    return 띠들[2]


문이름 = ["① 사건", "② 재무 문", "③ 대금 문", "④ 신호(볼린저·20일낙폭)"]
셈 = {t: [0] * len(문이름) for t in 띠들}
날칸 = defaultdict(list)          # 인 -> [(띠, 갭, 시총)]  ⑤⑥ 용
종목 = {t: set() for t in 띠들}

줄수 = 0
for 줄 in io.open(길, encoding="utf-8"):
    줄수 += 1
    try:
        x = json.loads(줄)
    except ValueError:
        continue
    t = 띠(x.get("시총억"))
    if t is None:
        continue
    셈[t][0] += 1
    종목[t].add(x.get("code"))

    if not (x.get("잉여금") is not None and x["잉여금"] >= R.잉여금하한
            and x.get("부채") is not None and x["부채"] <= R.부채상한
            and x.get("흑자")):
        continue
    셈[t][1] += 1

    if not (x.get("대금억") is not None and x["대금억"] >= R.대금하한억):
        continue
    셈[t][2] += 1

    if not (x.get("볼린저") is not None and x["볼린저"] <= R.볼린저문턱
            and x.get("낙폭20") is not None and x["낙폭20"] <= R.낙폭20문턱):
        continue
    셈[t][3] += 1
    if x.get("갭") is not None:
        날칸[x["인"]].append((t, x["갭"], x.get("시총억")))

print(f"  덤프 {줄수:,}줄 · 띠에 든 것 {sum(z[0] for z in 셈.values()):,}건\n")
print(f"  {'문':<26}" + "".join(f"{t:>20}" for t in 띠들))
for i, 름 in enumerate(문이름):
    print(f"  {름:<26}" + "".join(f"{셈[t][i]:>20,}" for t in 띠들))
print(f"  {'남은 비율(①대비)':<26}"
      + "".join(f"{셈[t][3] / 셈[t][0] * 100 if 셈[t][0] else 0:>19.2f}%" for t in 띠들))
print(f"  {'서로 다른 종목':<26}" + "".join(f"{len(종목[t]):>20,}" for t in 띠들))

# ── ⑤ 상대갭 · ⑥ 하루 자리 ──
갭산 = {t: 0 for t in 띠들}
자리산 = {t: 0 for t in 띠들}
for 인, 벌 in 날칸.items():
    중앙 = sorted(z[1] for z in 벌)[len(벌) // 2]
    통과 = [z for z in 벌 if z[1] - 중앙 <= R.상대갭문턱]
    for t, _, _ in 통과:
        갭산[t] += 1
    for t, _, _ in sorted(통과, key=lambda z: z[1] - 중앙)[:R.하루최대종목]:
        자리산[t] += 1

print(f"  {'⑤ 상대갭 -3.5%p':<26}" + "".join(f"{갭산[t]:>20,}" for t in 띠들))
print(f"  {'⑥ 하루 ' + str(R.하루최대종목) + '자리 안':<26}"
      + "".join(f"{자리산[t]:>20,}" for t in 띠들))
print(f"  {'⇒ 1년에':<26}" + "".join(f"{자리산[t] / 11:>19.1f}건" for t in 띠들))

print("\n  ── 왜 죽나 — 문마다 얼마나 떨어지나 (앞 문 대비 남는 비율) ──")
print(f"  {'문':<26}" + "".join(f"{t:>20}" for t in 띠들))
_앞 = {t: 셈[t][0] for t in 띠들}
for i, 름 in enumerate(문이름[1:], 1):
    print(f"  {름:<26}" + "".join(
        f"{셈[t][i] / _앞[t] * 100 if _앞[t] else 0:>19.1f}%" for t in 띠들))
    _앞 = {t: 셈[t][i] for t in 띠들}
print(f"  {'⑤ 상대갭':<26}" + "".join(
    f"{갭산[t] / _앞[t] * 100 if _앞[t] else 0:>19.1f}%" for t in 띠들))
print(f"  {'⑥ 하루 자리':<26}" + "".join(
    f"{자리산[t] / 갭산[t] * 100 if 갭산[t] else 0:>19.1f}%" for t in 띠들))
