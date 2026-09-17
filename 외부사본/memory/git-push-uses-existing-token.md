---
name: git-push-uses-existing-token
description: git push는 브라우저 OAuth 창을 띄운다 — secrets의 GITHUB_TOKEN으로 밀어라
metadata: 
  node_type: memory
  type: project
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-14T02:17:15.992Z
---

`morning-briefing-code`에 `git push` 하면 Git Credential Manager가 **브라우저
OAuth 창**을 띄우고 거기서 멈춘다(300초 넘게 사람을 기다린다). 그 창이 달라는 건
**Gists 읽기·쓰기 + 모든 public/private 저장소 + Workflow 파일 수정** — 저장소
하나에 밀어 넣는 데 필요한 것보다 훨씬 넓다.

**How to apply:** 이미 있는 fine-grained `GITHUB_TOKEN`(`config.get`으로 읽는다,
`data\secrets.json`을 직접 읽지 않는다)으로 민다.

```
git -c credential.helper= -c credential.interactive=never \
    push https://x-access-token:<토큰>@github.com/sicermens11/morning-briefing-code.git HEAD:main
```

토큰을 `.git/config`에 남기지 않으려고 remote 이름 대신 URL을 직접 넘긴다.
출력에서 토큰을 `***`로 지우고 찍는다. 파이썬으로 감싼 것이
`scratchpad/push_token.py`.

**Why:** 2026-09-14에 push가 이 창에서 멈춰 turn이 끊겼다. 저장소는 **public**이라
push 전 `git ls-files --cached | grep -c "secrets\.json"`가 0인지 본다 — `grep
secrets`만 하면 키가 없는 `scripts/check_secrets.py`가 걸려 헛경보가 난다.

[[briefing-pending-work]] · [[scheduled-task-checklist]]
