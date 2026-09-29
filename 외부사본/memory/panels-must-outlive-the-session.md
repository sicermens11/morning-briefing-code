---
name: panels-must-outlive-the-session
description: 판을 배경 셸의 자식으로 띄우면 세션이 끊길 때 같이 죽는다 — Start-Process 로 떼어 띄운다
metadata:
  node_type: memory
  type: feedback
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-29T07:24:56.364Z
---

**긴 판(gate7 등)은 `Start-Process` 로 세션에서 **떼어** 띄운다.**
배경 Bash 셸 안에서 `powershell ... queue_bNNN.ps1` 로 띄우면 **그 셸의 자식**이 되고,
세션이 끝나거나 배경 작업이 정리될 때 **판까지 같이 죽는다.**

**Why:** 2026-09-29. B139(BUYAT)를 「B138 끝나면 이어서」 배경 셸로 물려 놨다.
세션이 압축되며 배경 셸 다섯이 전부 정리됐고, **B139도 같이 죽었다.**
기본 32절을 43분 돌고 **정작 재려던 BUYAT 절 직전에** 끊겼다 —
결과 파일 127KB 가 남아 있어서 겉보기엔 «끝난 판»처럼 보였다.
로그 마지막 줄이 「시작」이고 「끝」이 없는 것으로만 알 수 있었다.

**띄우는 법:**
```powershell
Start-Process -FilePath 'powershell.exe' `
  -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','scripts\queue_bNNN.ps1' `
  -WorkingDirectory 'C:\Users\mrblue\Claude\morning breifing_code' -WindowStyle Hidden
```
감시(배경 Bash)는 죽어도 된다 — **판만 살아 있으면 된다.**

**How to apply:**
· 「끝났나」는 파일 크기가 아니라 **로그의 `===== queue_bNNN 끝 =====`** 로 본다
· ONLY 절이 안 보이면 **안 돈 것**이다. 기본 절은 ONLY 와 무관하게 늘 먼저 돈다
  (B139 는 32절을 다 돌고도 BUYAT 을 못 찍었다)
· 다시 돌릴 땐 지난 결과 파일 이름을 바꿔 둔다 — 큐가 덮어쓰기를 거부한다
  (`_중단됨_...` 처럼 왜 중단됐는지까지 이름에 적는다)
· 관련: [[lab-results-must-persist]] · [[do-before-promising]] ·
  [[machine-memory-limits]] · [[assert-only-after-checking]]
