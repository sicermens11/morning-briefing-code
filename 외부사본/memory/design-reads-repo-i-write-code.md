---
name: design-reads-repo-i-write-code
description: 클로드 디자인은 저장소를 **읽기만** 한다. 코드는 내가 고친다 — 달라진 건 디자인이 실제 값을 본다는 것뿐
metadata: 
  node_type: memory
  type: project
  originSessionId: 746aeb44-9d8e-447e-af4a-718406fc9f8d
  modified: 2026-09-11T13:37:57.161Z
---

2026-09-11 에 `https://github.com/sicermens11/morning-briefing-code` (public) 을 만들어
클로드 디자인에 연결했다. 역할은 **전과 같다**:

```
디자인   저장소를 **읽는다** · 실제 값을 보고 **지시서를 쓴다**
나       **코드를 고친다** · 반영하고 재서 보고한다
```

사용자 (원문):
> 「디자인은 저장소를 **읽기만** 해. 코드는 전과 똑같이 네가 고쳐.
>  달라진 건 디자인이 이제 실제 값을 보고 지시서를 쓴다는 것뿐이야.
>  **git pull 걱정 안 해도 돼.**」

⇒ 디자인이 저장소에 쓰지 않으므로 **충돌이 없다.** `git pull` 은 필요 없다.

## ⭐ 다만 **푸시는 내 몫**이다

디자인이 보는 것이 저장소다. 내가 코드를 고치고 **안 올리면 디자인은 옛 값**으로
지시서를 쓴다 — 오늘 왕복이 길어진 원인이 정확히 그거였다(어림값 대 실제값).

**How to apply:** 화면·조판 코드를 고치면 **커밋하고 밀어 올린다.** 특히
`scripts/build_cards.py` · `card_theme.py` · `build_site.py` · `rule_def.py` 와
결과물 `data/briefing-cards.html` · `data/briefing-site.html`.

## 저장소에 넣은 것 / 뺀 것

```
넣음  scripts/ · data/briefing-*.html(결과물) · data/*.json · forward-log.jsonl
      docs/ · 루트 md
뺌    data/secrets.json  ⚠️ public 이다. 열쇠는 무슨 일이 있어도 안 올린다
      KRX·DART 원자료 7.5GB (다시 받으면 된다)
      data/_labs 6.5MB — 디자인에겐 안 쓰인다. **백업은 따로 해야 한다**
```
⚠️ `design-share/` 는 작업 폴더 **밖**이라 저장소에 없다
   (`C:\Users\mrblue\Claude\design-share` — FINAL-CARDS · QUANT-DATA · 시안 html)

관련: [[measure-screen-dont-guess]] · [[claim-full-coverage-only-after-diff]]
