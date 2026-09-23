r"""A4 — **판이 고른 것 vs 실전이 고른 것**을 대조한다 (2026-09-23 · 연휴 계획 A4)

왜 있나: 2026-09-22 에 **실전에만** 「2,000억 제외」한 줄이 남아 있었다.
판에는 없던 줄이라 대형 후보(클래시스 1조 9,929억)를 영영 못 볼 뻔했다.
사용자가 눈으로 잡았다 — 다음엔 기계가 잡게 한다.

쓰기:
    python scripts/diff_pick.py data/_labs/2026-09-25_B59_A4_판이고른것.txt

판 쪽: 그 파일의 `PICKLINE <날짜> <코드,코드,…>` 줄
실전 쪽: data/forward-log.jsonl 의 그 신호기준일 `후보`
⚠️ 둘 다 **상대갭 거르기 전** 목록이어야 맞는 견줌이다.
나가는 값: 어긋난 날이 있으면 1
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if len(sys.argv) < 2:
    print("판 결과 파일을 주세요. 예:")
    print("  python scripts/diff_pick.py data/_labs/2026-09-25_B59_A4_판이고른것.txt")
    raise SystemExit(2)

판길 = sys.argv[1]
if not os.path.isabs(판길):
    판길 = os.path.join(뿌리, 판길)
판 = {}
for 줄 in io.open(판길, encoding="utf-8", errors="replace"):
    z = 줄.strip()
    if not z.startswith("PICKLINE"):
        continue
    조각 = z.split()
    if len(조각) < 2:
        continue
    날 = 조각[1].replace("-", "")
    판[날] = set(조각[2].split(",")) if len(조각) > 2 else set()

실전 = {}
실전이름 = {}
for 줄 in io.open(os.path.join(뿌리, "data", "forward-log.jsonl"), encoding="utf-8-sig"):
    z = 줄.strip()
    if not z:
        continue
    try:
        d = json.loads(z)
    except ValueError:
        continue
    날 = str(d.get("신호기준일") or "").replace("-", "")
    후보 = d.get("후보") or []
    if not 날:
        continue
    실전[날] = {str(c.get("종목코드")) for c in 후보 if c.get("종목코드")}
    for c in 후보:
        실전이름[str(c.get("종목코드"))] = c.get("이름") or ""

겹치는날 = sorted(set(판) & set(실전))
print(f"A4 대조 — 판 {len(판)}일 · 실전 {len(실전)}일 · 겹치는 날 {len(겹치는날)}일")
if not 겹치는날:
    print("⚠️ 겹치는 날이 없다 — 판의 마지막 날이 실전 기록보다 앞선다.")
    print(f"   판:   {sorted(판)[-3:] if 판 else '없음'}")
    print(f"   실전: {sorted(실전)[-3:] if 실전 else '없음'}")
    raise SystemExit(0)

어긋남 = 0
for 날 in 겹치는날:
    a, b = 판[날], 실전[날]
    판만, 실전만 = a - b, b - a
    if not 판만 and not 실전만:
        print(f"   ✅ {날}  {len(a)}종목 그대로 같다")
        continue
    어긋남 += 1
    print(f"   ❌ {날}  판 {len(a)} · 실전 {len(b)}")
    if 판만:
        print(f"      판에만 있다 ({len(판만)}): "
              + ", ".join(f"{c}{'(' + 실전이름.get(c, '') + ')' if 실전이름.get(c) else ''}" for c in sorted(판만)[:15]))
    if 실전만:
        print(f"      실전에만 있다 ({len(실전만)}): "
              + ", ".join(f"{c}({실전이름.get(c, '')})" for c in sorted(실전만)[:15]))

if 어긋남:
    print(f"\n❌ 어긋난 날 {어긋남}개 — 판과 실전이 다른 규칙을 쓰고 있다는 뜻이다")
    print("   먼저 볼 것: rule_def.py 의 값 vs record_pick.py 안에 따로 박힌 조건")
else:
    print(f"\n✅ {len(겹치는날)}일 전부 같다 — 판과 실전이 같은 규칙을 쓴다")
raise SystemExit(1 if 어긋남 else 0)
