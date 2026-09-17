---
name: no-heredoc-for-python
description: 셸 heredoc으로 파이썬 코드를 넘기면 백슬래시가 깨진다 — 네 번 당했다. 예외 없이 금지
metadata:
  type: feedback
---

셸 heredoc(`python - <<'PY'`)으로 파이썬 코드를 넘기면 **백슬래시가 한 겹 벗겨진다.**
따옴표로 감싸도(`<<'PY'`) 막지 못했다.

```
sector2_lab · merge_lab   `\n`이 진짜 개행이 되어 f-string이 깨짐
prob2_lab                 같은 이유로 SyntaxError
sweep2_lab                `scripts\peek.py`가 `\p` SyntaxWarning
⇒ 2026-09-04 하루에만 **네 번**. 매번 "이번엔 괜찮겠지" 하고 썼다
```

**Why:** 중간 셸 계층이 백슬래시를 한 번 더 처리한다. 무엇이 처리하는지 매번 다르고,
짧은 조각에서는 안 나타나다가 긴 코드나 경로 문자열에서 터진다.

**How to apply — 예외 없이:**
- 파이썬 코드는 **Write 도구로 파일에 쓴다.** 한 줄짜리도.
- 기존 파일 일부만 고칠 때: ① 새 조각을 scratchpad에 Write ②
  `python -c "..."` (한 줄, 백슬래시 없음)로 splice.
- 단순 문자열 치환은 **sed**를 쓴다. heredoc보다 안전하다.
- heredoc은 **백슬래시·따옴표가 하나도 없는** 조회용 코드에만.
- 편집 뒤 반드시 `python -W error::SyntaxWarning -c "import ast,io;
  ast.parse(...)"`로 확인한다. 평범한 `ast.parse`는 SyntaxWarning을 놓친다.

[[report-fix-with-problem]] [[verify-data-shape-first]]
