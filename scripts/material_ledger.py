#!/usr/bin/env python3
r"""
material_ledger.py — **재료 대장** · 「수집한 것 중 안 잰 게 있나」를 사람이 아니라 코드가 답한다 (2026-09-15 신설)

## 왜
사용자 (2026-09-15 23:25): 「내가 수집할 게 더 없는지, 수집한 거 중에 테스트 안 한 건 없는지 **항상 물어보는데 왜 계속 나오지?**」
오늘 하루에 네 번 나왔다 — 16년짜리 재료 셋 · 저가 필드 · fred 금리 · RSI/MACD.
원인은 게으름이 아니라 **구조**다:
  ① 재고(docs/자료재고.md)는 손으로 적어 얼어붙고, 「시험이 읽나」를 대조하는 코드가 없었다
  ② 판마다 사건 dict 를 따로 만들어 새 재료가 한 판에만 들어간다 (RSI 는 combo4 에만)
  ③ 수집 → 필드 → 재료 → ①단독 → ②앞뒤/종목분할 → ③돈 → ④4관문 — 여섯 단계인데 **한 표에 없다.**
     그래서 물어볼 때마다 다른 단계의 구멍이 나온다
  ④ rule_align 은 실전만 본다 — 시험 판의 「지금」이 낡아도 아무도 모른다

## 무엇을 하나 (전부 자동 · 손으로 적는 숫자 없음)
  A 자료 폴더마다   파일 수 · 첫 레코드 필드 · **시험 코드가 그 폴더/필드를 읽나**
  B 재료마다       ① 단독(A절)  ② 앞뒤(B-2) / 종목분할(B-3)  ③ 돈(E절 OR 셋 다)  ④ gate7 에 있나
  맨 위에          **안 읽는 필드** · **①에 없는 재료** · **①만 있고 ③ 못 간 재료** 를 먼저 찍는다
결과 → docs/재료대장.md  (매일 아침 확인 목록에서 이걸 먼저 본다)

쓰는 법:
    python scripts\material_ledger.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_S = os.path.join(_BASE, "scripts")
_OUT = os.path.join(_BASE, "docs", "재료대장.md")
_판들 = ("newmat.py", "combo4_lab.py", "gate7_lab.py", "omni_lab.py", "day_lab.py", "rebound_lab.py")
_안봄 = ("_labs", "_test", "_bak", "_bak_20260911_design", "_backup_consensus", "_cache", "_search",
        "briefings", "card-copy", "snapshots", "SKILL-backups", "__pycache__")
_일반필드 = {"기준일", "종목", "종목수", "이름", "종목명", "받은날", "코드", "날짜", "값", "항목", "항목수", "해", "분기",
            "자료", "만든날", "출처", "전체건수", "정보성건수"}


def _코드():
    return {n: io.open(os.path.join(_S, n), encoding="utf-8-sig").read() for n in _판들
            if os.path.exists(os.path.join(_S, n))}


def _첫레코드(폴더):
    """폴더의 첫 json 에서 (최상위 키, 한 단계 안 레코드 키)"""
    fs = sorted(glob.glob(os.path.join(폴더, "*.json"))) or sorted(glob.glob(os.path.join(폴더, "*", "*.json")))
    if not fs:
        return [], []
    try:
        j = json.load(io.open(fs[-1], encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return [], []
    top = sorted(j.keys()) if isinstance(j, dict) else []
    inner = []
    if isinstance(j, dict):
        for v in j.values():
            if isinstance(v, dict) and v:
                w = next(iter(v.values()))
                if isinstance(w, dict):
                    inner = sorted(w.keys())
                    break
            if isinstance(v, list) and v and isinstance(v[0], dict):
                inner = sorted(v[0].keys())
                break
    return top, inner


def A_자료(코드):
    줄 = []
    안읽는필드 = []
    for d in sorted(os.listdir(_DATA)):
        p = os.path.join(_DATA, d)
        if not os.path.isdir(p) or d in _안봄 or d.startswith("_"):
            continue
        n = sum(len(fs) for _, _, fs in os.walk(p))
        읽는판 = [k[:-3] for k, s in 코드.items() if (f'"{d}"' in s or f"'{d}'" in s or f"/{d}/" in s)]
        top, inner = _첫레코드(p)
        필드 = [f for f in inner if f not in _일반필드]
        안씀 = [f for f in 필드 if not any(f'"{f}"' in s or f"'{f}'" in s or f'["{f}"]' in s for s in 코드.values())]
        if 읽는판 and 안씀:
            안읽는필드.append((d, 안씀))
        줄.append(f"| `{d}` | {n:,} | {'✅ ' + ' '.join(읽는판) if 읽는판 else '❌ **안 읽음**'} | "
                  f"{', '.join(필드[:10]) or '-'} | {('**' + ', '.join(안씀) + '**') if 안씀 else ('-' if 읽는판 else '')} |")
    return 줄, 안읽는필드


def _최신결과(패턴):
    fs = sorted(glob.glob(os.path.join(_DATA, "_labs", 패턴)), key=os.path.getmtime, reverse=True)
    for f in fs:
        s = io.open(f, encoding="utf-8", errors="replace").read()
        if "읽는 법" in s:                         # 끝까지 돈 것만
            return f, s
    return None, ""


def B_재료(코드):
    f, s = _최신결과("2026-*COMBO*.txt")
    if not s:
        f, s = _최신결과("2026-*W_*.txt")
    재료 = []
    m = re.search(r"붙은 재료 \d+가지: (.+)", s)
    if m:
        재료 += [z.strip() for z in m.group(1).split(",")]
    c4 = 코드.get("combo4_lab.py", "")
    m2 = re.search(r"재료들 = \((.*?)\) \+ tuple\(_새재료\)", c4, flags=re.S)
    if m2:
        재료 = [z for z in re.findall(r'"([^"]+)"', m2.group(1))] + [r for r in 재료 if r not in re.findall(r'"([^"]+)"', m2.group(1))]
    본것 = set()
    재료 = [r for r in 재료 if not (r in 본것 or 본것.add(r))]

    def 단독(r):
        rows = re.findall(rf"^  {re.escape(r)}([↑↓]) +([\d,]+) +[\d,]+ +([\d.]+)% +[+\-][\d.]+ +([\d.]+)%", s, flags=re.M)
        if not rows:
            if re.search(rf"^    {re.escape(r)} +값이 [\d,]+개뿐 — 건너뜀", s, flags=re.M):
                return "건너뜀(30%↓)"
            return "❌ 없음"
        best = max(float(z[3]) for z in rows)
        return f"{best:.1f}%"

    def 앞뒤(r):
        rows = [ln for ln in s.splitlines() if re.match(rf"^  {re.escape(r)}[↑↓] \+ |^  \S+ \+ {re.escape(r)}[↑↓] ", ln)]
        if not rows:
            return "-"
        if any("✅" in ln for ln in rows):
            return "✅"
        if any("한쪽 표본" in ln for ln in rows):
            return "앞 0건"
        return "❌"

    def 종목분할(r):
        if "B-3" not in s:
            return "-"
        seg = s.split("B-3", 1)[1].split("── C", 1)[0]
        rows = [ln for ln in seg.splitlines() if re.match(rf"^  {re.escape(r)}[↑↓]", ln)]
        if not rows:
            return "-"
        return "✅" if any("✅" in ln for ln in rows) else "❌"

    def 돈(r):
        if "── E" not in s:
            return "-"
        seg = s.split("── E", 1)[1]
        rows = [ln for ln in seg.splitlines() if re.escape(r) in re.escape(ln) and ("셋 다" in ln or "⚠️" in ln)]
        if not rows:
            return "-"
        return "✅ 셋 다" if any("셋 다" in ln for ln in rows) else "❌"

    g7 = 코드.get("gate7_lab.py", "")
    줄, 안잰, 못간 = [], [], []
    for r in 재료:
        a, b, c, d = 단독(r), 앞뒤(r), 종목분할(r), 돈(r)
        e = "✅" if (f'"{r}"' in g7 or f'x["{r}"]' in g7 or f"'{r}'" in g7) else "-"
        if a == "❌ 없음":
            안잰.append(r)
        elif a not in ("건너뜀(30%↓)",) and d == "-" and b in ("✅", "-") and c in ("✅", "-"):
            try:
                if float(a.rstrip("%")) >= 47.7:
                    못간.append(r)
            except ValueError:
                pass
        줄.append(f"| {r} | {a} | {b} | {c} | {d} | {e} |")
    return (f or "?"), 줄, 안잰, 못간


def main():
    코드 = _코드()
    A줄, 안읽는필드 = A_자료(코드)
    결과파일, B줄, 안잰, 못간 = B_재료(코드)
    out = []
    out.append(f"# 재료 대장 — {dt.datetime.now():%Y-%m-%d %H:%M} (코드가 만든다 · 손으로 고치지 않는다)\n")
    out.append("> 「수집한 것 중 안 잰 게 있나」에 대한 답은 **이 파일 맨 위**다. 매일 아침 확인 목록에서 먼저 본다.\n")
    out.append("## 🔴 맨 위 — 구멍\n")
    out.append(f"- **시험이 안 읽는 필드**: " + ("; ".join(f"`{d}` → {', '.join(f)}" for d, f in 안읽는필드) if 안읽는필드 else "없음"))
    out.append(f"- **① 단독조차 안 잰 재료**: " + (", ".join(안잰) if 안잰 else "없음"))
    out.append(f"- **① 에서 바탕+3%p 넘겼는데 ③ 돈으로 못 간 재료**: " + (", ".join(못간) if 못간 else "없음"))
    out.append("")
    out.append("## A 자료 — 폴더 · 파일 수 · 시험이 읽나 · 레코드 필드 · **안 읽는 필드**\n")
    out.append("| 폴더 | 파일 | 읽는 판 | 필드 (앞 10) | 안 읽는 필드 |\n|---|---|---|---|---|")
    out += A줄
    out.append("")
    out.append(f"## B 재료 — 최신 판 `{os.path.basename(결과파일)}` 기준\n")
    out.append("| 재료 | ① 단독 20일 이김(최고) | ② 앞뒤 | ② 종목분할 | ③ 돈(기존 OR) | ④ gate7 |\n|---|---|---|---|---|---|")
    out += B줄
    out.append("")
    out.append("## 읽는 법\n- ① 「❌ 없음」= 재료로 만들었는데 오분위에 못 올라감 · 「건너뜀」= 값이 30% 미만\n"
               "- ② 앞뒤 「앞 0건」= 자료가 최근에만 있어 종목분할로 봐야\n- ③ 「-」= 돈으로 안 넘김 (②를 못 지났거나 단독 바탕+3 미달)\n"
               "- ④ gate7 에 이름이 있으면 자본 시뮬·4관문 판에 든 것")
    io.open(_OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out[:8]))
    print(f"\n  자료 {len(A줄)}폴더 · 재료 {len(B줄)}개 → {_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
