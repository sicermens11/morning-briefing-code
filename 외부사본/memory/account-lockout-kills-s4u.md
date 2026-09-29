---
name: account-lockout-kills-s4u
description: "윈도 계정이 잠기면 S4U 예약은 시작도 못 한다 (오류 2147944309 = 1909). 9/29 밤 반복 잠김, 원인 미확정"
metadata:
  node_type: memory
  type: project
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-29T11:50:34.576Z
---

**계정 mrblue 가 잠기면 S4U 예약(아침 브리핑 08:02 · 08:55 기록 등 14개)은 시작도 못 한다.**
작업 스케줄러 기록에 104 「LogonUserS4U 실패」 + 101 오류 2147944309(= 1909 계정 잠김)가 남는다.
Interactive 예약(DataGapFill 등)은 사용자가 로그인해 있으면 돈다.

**Why:** 2026-09-29 19:00 저녁 수집이 이것으로 통째로 빠졌다. 20:00 에는 풀렸다가 20:45 다시 잠김 — 반복.
잠금 정책은 10분 안에 10번 틀리면 10분 잠금. 원격 데스크톱은 꺼져 있고 445 만 열려 있다.
실패 로그인 감사가 꺼져 있고 관리자 권한이 없어 **누가 틀리는지 못 봤다.**

**How to apply:**
- 예약이 「돌았다는 기록 없이」 비면 먼저 `Get-WinEvent TaskScheduler/Operational` 에서 101/104 를 본다
- 잠김 확인은 PowerShell `net user mrblue` 의 「Account active」 (bash 에선 안 읽혔다)
- 원인 찾기는 관리자 창에서 `auditpol /set /subcategory:"Logon" /failure:enable` 후 보안 기록 4625
- 관련: [[scheduled-task-checklist]] · [[checker-noise-hides-failures]]
