r"""계획한 시험이 **코드에 절로 들어 있나**를 대조한다 (2026-09-11 신설).

왜 만들었나
-----------
사용자: 「야 왜 자꾸 물어볼때마다 테스트가 빠져있어」

빠진 것을 **물어볼 때마다 하나씩** 찾아내고 있었다. 전체를 대조한 적이 없었다:

```
9/11 저녁  「규모별 중앙갭」   -> 글로만 적혀 있고 절도 예약도 없었다
   그 다음 「후보 40개 자르기」 -> 목록에 엿새 있었는데 _후보수 가 상수라 못 돌았다
   그 다음 「매도」            -> SELL-PLAN 여섯 중 둘만 있었다
```

세 번 다 **사용자가 물어서** 드러났다. 이 파일이 그걸 대신 한다.

무엇을 재나
-----------
① `MASTER-STATUS.md` · `SELL-PLAN.md` · `COMBO-AUDIT-*.md` 에서 **차수**를 긁고
② `scripts/gate7_lab.py` 의 **절 머리글**에서 차수를 긁어
③ 계획에는 있는데 절이 없는 것을 찍는다

한계 (⚠️ 이것도 사각지대다)
--------------------------
차수 없이 글로만 적힌 계획은 못 잡는다. 그래서 ④ 로 **글로만 적힌 줄**도
따로 찍는다 — 사람이 봐야 하는 목록이다.
"""
import io
import os
import re
import sys

# ⚠️ PowerShell 화면이 cp949 면 「—」 한 글자에 죽는다 (gate7_lab 이 겪은 그것).
#    PYTHONIOENCODING 을 안 줘도 죽지 않게 여기서 막는다
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

계획파일 = ["MASTER-STATUS.md", "SELL-PLAN.md", "COMBO-AUDIT-2026-09-10.md"]
코드파일 = ["scripts/gate7_lab.py"]

# 「끝났다 / 기각」 처럼 **더 돌 필요가 없는** 줄은 뺀다
끝낸표시 = ("✅", "❌", "기각", "끝났다", "안 함", "이미 한 것")


def 읽기(p):
    try:
        return io.open(os.path.join(뿌리, p), encoding="utf-8", newline="").read()
    except OSError:
        return ""


def 절차수():
    """gate7_lab.py 안에 **절 머리글**로 들어 있는 차수."""
    있다 = set()
    for p in 코드파일:
        t = 읽기(p)
        # print("  123차 · ..." 꼴의 머리글만 센다 (주석·설명은 안 센다)
        for m in re.finditer(r'print\("\s{2,}(\d{2,3})차\s*·', t):
            있다.add(int(m.group(1)))
    return 있다


def 돈차수():
    """**이미 돌아서 결과가 남은** 차수.

    ⚠️ 계획 문서는 지나간 시험을 **근거로도** 적는다
       (「257차 증자 — 236차에서 0건」). 236차는 빠진 게 아니라 이미 돈 것이다.
       그래서 결과가 있는 차수는 빼야 가짜 경보가 안 난다.
    """
    돈 = set()
    for m in re.finditer(r"_(\d{2,3})차", " ".join(
            os.listdir(os.path.join(뿌리, "data", "_labs")))):
        돈.add(int(m.group(1)))
    for 줄 in 읽기("docs/시험번호.md").split("\n"):
        m = re.match(r"\|\s*(\d{2,3})(-\d)?\s*\|", 줄)
        if m:
            돈.add(int(m.group(1)))
    return 돈


def 계획차수():
    """계획 문서에서 **아직 안 끝난** 줄의 차수."""
    남 = {}
    글만 = []
    for p in 계획파일:
        for 줄 in 읽기(p).split("\n"):
            if not 줄.strip().startswith("|"):
                continue
            if any(z in 줄 for z in 끝낸표시):
                continue
            차 = re.findall(r"(\d{2,3})차", 줄)
            if 차:
                for c in 차:
                    남.setdefault(int(c), []).append((p, 줄.strip()[:110]))
            elif ("⏳" in 줄 or "📋" in 줄 or "🆕" in 줄):
                글만.append((p, 줄.strip()[:110]))
    return 남, 글만


def 본다():
    있다 = 절차수()
    돈 = 돈차수()
    남, 글만 = 계획차수()
    빠짐 = {c: v for c, v in 남.items() if c not in 있다 and c not in 돈}

    print("=" * 78)
    print("  시험 대조 — 계획한 것이 코드에 절로 들어 있나")
    print("=" * 78)
    print(f"\n  gate7_lab.py 절 {len(있다)}개: "
          + " ".join(f"{c}차" for c in sorted(있다)))

    if 빠짐:
        print(f"\n  🚨 **계획에는 있는데 절이 없는 것 {len(빠짐)}개**")
        for c in sorted(빠짐):
            for p, 줄 in 빠짐[c][:1]:
                print(f"     {c}차  ({p})")
                print(f"       {줄}")
    else:
        print("\n  ✅ 차수가 붙은 계획은 **전부** 절이 있다")

    if 글만:
        print(f"\n  ⚠️ **차수 없이 글로만 적힌 계획 {len(글만)}줄** — 사람이 봐야 한다")
        for p, 줄 in 글만[:20]:
            print(f"     ({p}) {줄}")

    print()
    return 1 if 빠짐 else 0


if __name__ == "__main__":
    sys.exit(본다())
