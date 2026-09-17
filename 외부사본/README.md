# 외부사본 — 프로젝트 폴더 **밖**에 있던 것의 사본

`scripts/sync_outside.py` 가 만든다. **손으로 고치지 않는다.**

## 왜 있나
아침 브리핑이 쓰는 스킬과 내(클로드) 메모리가 프로젝트 폴더 밖
`~\.claude\` 에 있다. PC 를 옮길 때 폴더만 복사하면 **이게 빠져서 브리핑이 안 돈다.**
그래서 여기에 사본을 두고 git 에 넣는다 (GitHub 백업까지 자동).

## 새 PC 에서 되돌리는 법
```
skills\  →  C:\Users\mrblue\.claude\skills
memory\  →  C:\Users\mrblue\.claude\projects\c--Users-mrblue-Claude-morning-breifing-code\memory
```
⚠️ 되돌리는 건 **사람이** 한다. 이 스크립트는 밖 → 안 한 방향뿐이다.

## 무엇이 들었나
- `skills\` — 스킬 — 08:02 브리핑·09:05 진입확인 본체. 되돌릴 곳: ~\.claude\skills\
- `memory\` — 메모리 — 규칙·약속·지난 실수. 되돌릴 곳: ~\.claude\projects\c--Users-mrblue-Claude-morning-breifing-code\memory\
