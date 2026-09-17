---
name: plan-must-be-a-table
description: 계획을 글로 적으면 사라진다. docs/할일.md 표에 적고 plan_check.py가 맞춰본다
metadata:
  type: feedback
---

계획을 AGENDA 본문에 글로 적으면 **잊힌다.** 「새로운 조합」 시험이 가번호 150으로
계획에 있다가, 150번이 걷기검증에 붙으면서 목록에서 사라졌다. 사용자가 물어서 알았다.

**Why:** 기록은 45만 자다. 사람도 나도 거기서 「아직 안 한 것」을 눈으로 못 찾는다.
결과 파일은 기계가 셀 수 있는데, 계획은 셀 수 없는 꼴이었다.

**How to apply:** 할 일은 `docs/할일.md` 표에 한 줄로 적는다 (상태·무엇·왜·결과파일).
`scripts/plan_check.py` 가 표와 `data/_labs` 를 맞춰보고, selfcheck E-2 절이
하루 세 번 자동으로 돌린다. 계획을 말로만 하지 않는다.
[[lab-results-must-persist]] [[record-decisions-and-tasks]]
