---
name: lab-results-must-persist
description: 시험 결과는 임시 폴더가 아니라 data/_labs/에 남긴다 — 대화가 요약돼도 숫자가 살아남게
metadata:
  type: feedback
---

시험·시뮬 결과는 **`data/_labs/YYYY-MM-DD_이름.txt`** 로 남긴다. 스크래치패드(Temp)에만 두지 않는다.

**Why:** 2026-09-03 사용자가 물었다 — *"대화 오래하면 메모리에서 사라지는데, 테스트 결과를
기억해서 나중에 보고하고 반영하는 거 문제없어?"* 확인해보니 **실제로 문제였다.**
시험 결과 85개(862KB)가 전부 `AppData\Local\Temp\claude\...\scratchpad\`에만 있었다.
Temp는 정리될 수 있고 **세션마다 경로가 다르다** — 다음 세션에서 못 찾는다.
대화가 길어지면 요약되면서 세부 숫자도 사라진다.

**How to apply:**
- 시험을 돌릴 때 출력을 `data/_labs/`로 바로 보낸다 (Temp를 거치지 않는다)
- 결론과 판정은 `AGENDA.md`에, **원본 표는 `data/_labs/`**에 — 둘 다 남긴다
- 새 세션을 열면 `AGENDA.md` 최근 부분과 `data/_labs/` 목록부터 본다
- 관련: [[briefing-pending-work]] · [[record-decisions-and-tasks]]
