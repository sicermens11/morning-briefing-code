r"""A1 — **로그 전수: 터졌는데 성공이라고 끝난 곳**을 찾는다 (2026-09-23 · 연휴 계획 A1)

왜 있나: 파이썬은 터져도 파워셸의 `try` 가 삼키면 rc=0 으로 끝난다.
그러면 사슬은 계속 돌고, 아무도 안 읽는 로그에만 Traceback 이 남는다.
「점검기의 소음이 실패를 숨긴다」 — 그래서 **문제만** 찍는다.

무엇을 보나
  · run-logs/*.log  (판 사슬 · 브리핑)
  · data/_*.log     (수집기)
  찾는 말: Traceback · MemoryError · ❌ · 터졌다 · 실패 · Error:
  그 로그가 「끝」·「완료」·「✅」로 닫혔으면 **조용한 실패**로 본다 (더 나쁘다)

쓰기: python scripts/check_runlogs.py [며칠]   (기본 14일)
나가는 값: 조용한 실패가 있으면 1
"""
import io
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
며칠 = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 14
한도 = time.time() - 며칠 * 86400

# ⚠️ 「❌」는 이 집에서 **판정 기호**다 (「→ 탈락」). 나쁜 말로 잡으면 소음이 실패를 숨긴다
나쁜말 = re.compile(r"Traceback|MemoryError|터졌다|[A-Za-z]*Error|실패했|코드 1 —|exit=1")
봐줄말 = re.compile(r"실패 0|오류 0|Error: 0|없음|취소|잡았다|건너뛴|❌ 다|기각이 아니")
닫는말 = re.compile(r"끝 =====|===== .*끝|완료|✅|성공")

방들 = [os.path.join(뿌리, "run-logs"), os.path.join(뿌리, "data")]
파일들 = []
for 방 in 방들:
    if not os.path.isdir(방):
        continue
    for 이름 in os.listdir(방):
        if not 이름.endswith(".log"):
            continue
        길 = os.path.join(방, 이름)
        try:
            if os.path.getmtime(길) >= 한도:
                파일들.append(길)
        except OSError:
            pass

조용한실패, 그냥실패, 본수 = [], [], 0
for 길 in sorted(파일들, key=os.path.getmtime, reverse=True):
    try:
        줄들 = io.open(길, encoding="utf-8-sig", errors="replace").read().splitlines()
    except OSError:
        continue
    본수 += 1
    꼬리 = 줄들[-400:]
    나쁜 = [(번, z.strip()) for 번, z in enumerate(꼬리, len(줄들) - len(꼬리) + 1)
            if 나쁜말.search(z) and not 봐줄말.search(z)]
    if not 나쁜:
        continue
    닫힘 = any(닫는말.search(z) for z in 꼬리[-12:])
    보임 = os.path.relpath(길, 뿌리)
    (조용한실패 if 닫힘 else 그냥실패).append((보임, 나쁜[:3], len(나쁜),
                                             time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(길)))))

if 조용한실패:
    print(f"❌ 터졌는데 성공처럼 닫힌 로그 {len(조용한실패)}개 — 아무도 모르고 지나간 것들")
    for 보임, 몇, 수, 때 in 조용한실패:
        print(f"   {보임}  ({때} · 나쁜 줄 {수}개)")
        for 번, z in 몇:
            print(f"      {번}: {z[:130]}")
if 그냥실패:
    print(f"\n⚠️ 터진 채로 끝난 로그 {len(그냥실패)}개 (적어도 닫히진 않았다)")
    for 보임, 몇, 수, 때 in 그냥실패[:12]:
        print(f"   {보임}  ({때} · {수}개)  {몇[0][1][:100] if 몇 else ''}")
if not 조용한실패 and not 그냥실패:
    print(f"✅ A1 — 최근 {며칠}일 로그 {본수}개, 조용한 실패 없다")
else:
    print(f"\n   (최근 {며칠}일 로그 {본수}개를 봤다)")
raise SystemExit(1 if 조용한실패 else 0)
