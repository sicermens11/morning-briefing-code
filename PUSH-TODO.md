# 월요일 아침에 저장소로 — 한 번에 (2026-09-11 밤 기록)

> 사용자: 「나중에 테스트 끝나고 한 번에 올리자. 이거 기록했다가 나중에 얘기해줘」
> 사용자(고침): 「**월요일 아침에 저장소에 올릴 수 있는 거 다 올리는 게 낫겠네
>                월요일에 디자인 작업할 수 있으니까**」
>
> **언제** — **2026-09-14(월) 09:15 뒤** (아침 브리핑이 다 돈 뒤)
> **어디로** — https://github.com/sicermens11/morning-briefing-code

---

## 왜 월요일 아침인가

```
07:30 ~ 09:05  아침 예약이 돈다 -> **그날 카드·사이트가 새로 만들어진다**
09:15 이후     올린다 -> 디자인이 **월요일 실제 화면과 실제 값**으로 작업한다
```

일요일에 올리면 저장소에 **금요일 화면**이 남는다. 디자인은 실제 값을 보고
지시서를 쓰므로, **그날 것**이 들어가야 왕복이 안 생긴다.

---

## 올릴 것

| 무엇 | 디자인이 보나 |
|---|---|
| `data/briefing-cards.html` · `briefing-site.html` | ⭐ **본다** — 월요일 화면 |
| `scripts/build_cards.py` · `card_theme.py` · `build_site.py` · `rule_def.py` | ⭐ **본다** — 실제 값 |
| `data/forward-log.jsonl` · `data/*.json` | ⭐ **본다** — 후보 구조·규칙 |
| `scripts/pick_base.py` · `sunday_labs.ps1` | 안 봄 (시험 쪽) |
| `docs/시험번호.md` (+51줄) | 안 봄 |
| `data/_labs/2026-09-12_*.txt` · `2026-09-13_*.txt` | 안 봄 — 백업 겸 |
| `.gitignore` · `PUSH-TODO.md` · `MASTER-STATUS.md` | — |

---

## 할 일 (그대로 따라 하면 된다)

```
1. 아침 예약이 다 돈 것을 본다 (09:05 EntryCheck0905 까지)
2. git add -A
3. git ls-files --cached | grep secrets     <- **0 이어야 한다.** 저장소는 public
4. git commit -m "월요일 화면 · 주말 판 열 벌 · 시험 대장 51개"
5. git push
6. 디자인에 알린다 — 「월요일 값으로 갱신됐습니다」
```

⚠️ 3번을 건너뛰지 않는다. **public 저장소**다.

---

## ⚠️ 이건 월요일까지 안 기다린다

조판 코드를 **중간에 고치면 그때 바로** 올린다.

```
scripts/build_cards.py · card_theme.py · build_site.py · rule_def.py
data/briefing-cards.html · data/briefing-site.html
```

안 올리면 디자인이 **옛 값으로 지시서를 쓴다** — 2026-09-11 에 왕복이 길어진
원인이 정확히 그것이었다(28px·52px 같은 어림값).
