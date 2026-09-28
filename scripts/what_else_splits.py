r"""**규모·섹터 말고 또 무엇으로 나눌 만한가** — 재서 고른다 (2026-09-28)

사용자: 「규모별, 섹터별 말고 또 구분해서 테스트해볼만한게 있나?」

후보를 늘어놓기만 하면 뜻이 없다. **어떤 가름이 실제로 갈리는지**를 잰다.
잣대는 대형주에서 쓴 것과 같다 — **문마다 몇 %가 살아남나.**
특히 ⑤ 상대갭에서 **한쪽이 전멸하면** 그 가름은 「규칙이 한쪽만 보고 있다」는 뜻이다
(대형 1조↑ 가 93건 → 0건이었던 것처럼).

가름 후보 (사건에 든 58칸에서 고른 것)
  ① 시장          코스피 / 코스닥      — 문턱 -7% 는 코스피만 보고 골랐다
  ② 평소등락      그 종목이 평소 몇 % 움직이나 — **-3.5%p 를 똑같이 요구하는 게 맞나**
  ③ 대금          거래대금 — 1% 한도에 직접 걸리는 값 (시총보다 곧다)
  ④ 회전율        손바뀜
  ⑤ 주가          호가 단위가 다르다 (천원짜리 vs 십만원짜리)
  ⑥ PBR          싼가 비싼가
  ⑦ ROE          잘 버나
  ⑧ 시장낙폭      **그날 장이 어땠나** (종목이 아니라 **날**을 가른다)
  ⑨ 소형우위      그날 소형이 셌나

⚠️ 덤프는 Ⓗ 를 통과한 것 위주다 — 절대수가 아니라 **띠끼리 견주는 데** 쓴다.
⚠️ 메모리: 한 줄씩 읽는다.
"""
import io
import json
import sys
from collections import defaultdict

sys.path.insert(0, r"C:\Users\mrblue\Claude\morning breifing_code\scripts")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import rule_def as R  # noqa: E402

길 = r"C:\Users\mrblue\Claude\morning breifing_code\data\_labs\h_events.jsonl"

수칸 = ["평소등락", "대금억", "회전율", "주가", "PBR", "ROE", "시장낙폭", "소형우위"]

# ── 1차: 사분위 컷을 낸다 ──
모음 = {k: [] for k in 수칸}
줄수 = 0
for 줄 in io.open(길, encoding="utf-8"):
    줄수 += 1
    if 줄수 % 3:                      # 컷만 낼 거라 3줄에 하나면 충분하다
        continue
    try:
        x = json.loads(줄)
    except ValueError:
        continue
    for k in 수칸:
        v = x.get(k)
        if isinstance(v, (int, float)):
            모음[k].append(float(v))

컷 = {}
for k, v in 모음.items():
    if len(v) < 100:
        continue
    v.sort()
    컷[k] = [v[len(v) // 4], v[len(v) // 2], v[len(v) * 3 // 4]]
print(f"  덤프 {줄수:,}줄 · 사분위 컷을 냈다\n")
for k in 수칸:
    if k in 컷:
        print(f"     {k:<10} 25% {컷[k][0]:>10.2f} · 50% {컷[k][1]:>10.2f} · 75% {컷[k][2]:>10.2f}")


def 띠이름(k, v):
    if v is None or k not in 컷:
        return None
    c = 컷[k]
    return ("1 아래25%" if v < c[0] else "2 25~50%" if v < c[1]
            else "3 50~75%" if v < c[2] else "4 위25%")


# ── 2차: 가름마다 문을 센다 ──
가름들 = ["시장"] + 수칸
셈 = {g: defaultdict(lambda: [0, 0]) for g in 가름들}    # [사건, 신호]
날칸 = defaultdict(list)

for 줄 in io.open(길, encoding="utf-8"):
    try:
        x = json.loads(줄)
    except ValueError:
        continue
    표 = {"시장": x.get("_지수이름")}
    for k in 수칸:
        표[k] = 띠이름(k, x.get(k))
    for g in 가름들:
        if 표[g] is not None:
            셈[g][표[g]][0] += 1

    if not (x.get("잉여금") is not None and x["잉여금"] >= R.잉여금하한
            and x.get("부채") is not None and x["부채"] <= R.부채상한 and x.get("흑자")
            and x.get("대금억") is not None and x["대금억"] >= R.대금하한억
            and x.get("볼린저") is not None and x["볼린저"] <= R.볼린저문턱
            and x.get("낙폭20") is not None and x["낙폭20"] <= R.낙폭20문턱):
        continue
    for g in 가름들:
        if 표[g] is not None:
            셈[g][표[g]][1] += 1
    if x.get("갭") is not None:
        날칸[x["인"]].append((표, x["갭"]))

# ── ⑤ 상대갭 · ⑥ 자리 ──
갭산 = {g: defaultdict(int) for g in 가름들}
자리산 = {g: defaultdict(int) for g in 가름들}
for 인, 벌 in 날칸.items():
    중 = sorted(z[1] for z in 벌)[len(벌) // 2]
    통과 = [z for z in 벌 if z[1] - 중 <= R.상대갭문턱]
    for 표, _ in 통과:
        for g in 가름들:
            if 표[g] is not None:
                갭산[g][표[g]] += 1
    for 표, _ in sorted(통과, key=lambda z: z[1] - 중)[:R.하루최대종목]:
        for g in 가름들:
            if 표[g] is not None:
                자리산[g][표[g]] += 1

print("\n" + "=" * 104)
print("  가름마다 — 문을 하나씩 지나면 얼마나 남나  (⑤에서 한쪽이 0 이면 그 가름이 뜻있다)")
print("=" * 104)
for g in 가름들:
    띠 = sorted(셈[g])
    if len(띠) < 2:
        continue
    print(f"\n  ── {g} ──")
    print(f"     {'띠':<12}{'① 사건':>12}{'④ 신호':>11}{'⑤ 상대갭':>11}{'⑥ 자리':>9}"
          f"{'④→⑤ 남는 비율':>16}{'1년에':>9}")
    for t in 띠:
        n, sig = 셈[g][t]
        gp, sl = 갭산[g][t], 자리산[g][t]
        print(f"     {t:<12}{n:>12,}{sig:>11,}{gp:>11,}{sl:>9,}"
              f"{(gp / sig * 100 if sig else 0):>15.2f}%{sl / 11:>8.1f}")
