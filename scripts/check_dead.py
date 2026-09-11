r"""쓰이는 파일과 **안 쓰이는 파일**을 가른다 (2026-09-11 신설).

사용자: 「3주간 테스트하면서 일시적으로 작성한 파일이나, 합쳐서 더 효율적인
        파일이 있는지 확인해줘. 불필요하면 삭제하려고!」

어떻게 가르나
-------------
① **뿌리**: 예약 작업이 직접 부르는 파일 + 브리핑 스킬이 부르는 파일
② 거기서 `import` 를 타고 내려가 **닿는 것**을 전부 모은다
③ 닿지 않는 것 = **시험용 일회성**일 가능성이 높다

⚠️ 「안 닿는다」가 「지워도 된다」는 아니다. 시험 결과의 **재현 근거**다.
   지우기 전에 사람이 본다. 이 파일은 **목록만** 만든다 — 아무것도 안 지운다
"""
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

뿌리폴더 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
스 = os.path.join(뿌리폴더, "scripts")

# ── ① 예약 작업이 직접 부르는 것 (Get-ScheduledTask 로 뽑아 적었다) ──
예약 = [
    "auto_search.py", "collect_capital.py", "collect_consensus_slow.py",
    "backfill_dart_old.py", "collect_dart_snap.py", "collect_evening.py",
    "fetch_antc.py", "morning_prep.py", "collect_industry.py",
    "when_krx2.py", "morning_krx.py", "collect_overnight.py",
    "selfcheck.py", "weekend_labs.py", "gate7_lab.py",
    "auto_0850.py", "build_site.py", "build_cards.py", "record_pick.py",
    "how_often.py", "rule_align.py", "build_rule_cases.py", "bought.py",
    "rule_def.py", "check_layout.py", "check_gaps.py", "check_secrets.py",
    "check_tests.py", "check_dead.py", "verify_all.py", "config.py",
]


def 이름들(t):
    """그 파일이 import 하거나 문자열로 부르는 .py 이름."""
    난다 = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", t, re.M):
        난다.add(m.group(1) + ".py")
    for m in re.finditer(r"([A-Za-z_][\w]*\.py)", t):
        난다.add(m.group(1))
    return 난다


전부 = {f for f in os.listdir(스) if f.endswith(".py")}

# ⚠️⚠️ **.ps1 을 안 따라가면 살아 있는 걸 죽었다고 찍는다** (2026-09-11).
#    첫 판에서 `fetch_market.py` · `check_copy.py` 를 「안 닿음」으로 찍었는데
#    실은 `run-py.ps1` · `publish_pages.ps1` 이 부르고 있었다.
#    브리핑은 **ps1 -> py** 로 돌아간다. ps1 도 뿌리로 넣는다
씨 = list(예약)
for 폴더 in (스, 뿌리폴더, os.path.join(뿌리폴더, "..", "Templates", "scripts"),
             os.path.join(뿌리폴더, "..", "Scheduled")):
    if not os.path.isdir(폴더):
        continue
    for f in os.listdir(폴더):
        if not f.endswith((".ps1", ".md")):
            continue
        try:
            t = io.open(os.path.join(폴더, f), encoding="utf-8-sig",
                        errors="replace").read()
        except OSError:
            continue
        씨.extend(g for g in 이름들(t) if g in 전부)

닿음, 볼것 = set(), [f for f in 씨 if f in 전부]
while 볼것:
    f = 볼것.pop()
    if f in 닿음:
        continue
    닿음.add(f)
    try:
        t = io.open(os.path.join(스, f), encoding="utf-8-sig",
                    errors="replace").read()
    except OSError:
        continue
    for g in 이름들(t):
        if g in 전부 and g not in 닿음:
            볼것.append(g)

안닿음 = sorted(전부 - 닿음)


def 잰다(f):
    p = os.path.join(스, f)
    return os.path.getsize(p), os.path.getmtime(p)


print("=" * 76)
print("  쓰이는 파일 / 안 쓰이는 파일")
print("=" * 76)
print(f"\n  scripts/*.py {len(전부)}개")
print(f"    쓰인다 (예약에서 닿음)   {len(닿음):>4}개")
print(f"    안 닿는다               {len(안닿음):>4}개   "
      f"{sum(잰다(f)[0] for f in 안닿음) / 1024:,.0f} KB")

묶 = {}
for f in 안닿음:
    키 = ("_lab" if "_lab" in f else
          "check/verify" if f.startswith(("check_", "verify_")) else
          "peek/보기" if f.startswith(("peek", "show", "look", "see")) else
          "collect/fetch" if f.startswith(("collect_", "fetch_")) else
          "그 밖")
    묶.setdefault(키, []).append(f)

for 키 in sorted(묶, key=lambda k: -len(묶[k])):
    벌 = 묶[키]
    print(f"\n  [{키}] {len(벌)}개 "
          f"({sum(잰다(f)[0] for f in 벌) / 1024:,.0f} KB)")
    몇 = len(벌) if "--전체" in sys.argv else 6
    for f in sorted(벌, key=lambda z: 잰다(z)[1])[:몇]:
        크, _ = 잰다(f)
        print(f"      {f:<38}{크 / 1024:>7,.0f} KB")
    if len(벌) > 몇:
        print(f"      … 그 밖 {len(벌) - 몇}개   (--전체 로 다 본다)")

print("\n  ⚠️ 「안 닿는다」 != 「지워도 된다」 — 시험 결과의 재현 근거다.")
print("     지우기 전에 사람이 본다. 이 파일은 아무것도 안 지운다\n")
