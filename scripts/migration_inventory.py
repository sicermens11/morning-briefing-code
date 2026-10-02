#!/usr/bin/env python3
r"""
migration_inventory.py — **PC 옮기기 목록을 지금 상태로 다시 뽑는다** (2026-10-02)

사용자: 「지금 기준이랑 나중이랑 체크리스트가 달라지지 않을려나」 — 손으로 적은 목록은 낡는다
⇒ 옮기기 직전에 이걸 돌리면 그 시점 목록이 나온다 → data/옮기기_현황.md (docs/옮기기_체크리스트.md 는 「왜·어떻게」 만)

뽑는 것: ① git 에 안 올라가는 폴더·파일과 크기(.gitignore 기준 · `git status --ignored`) ② 그중 「다시 못 받는」 표시
         ③ 예약 작업(Windows 작업 스케줄러 · 마이크로소프트·업데이트 것 뺌) ④ 작업 메모리 폴더 파일 수
         ⑤ Windows 전용 코드 규모(.ps1 · Win32_ · C:\Users 경로) ⑥ 파이썬 패키지 목록(requirements 후보)
"""
import datetime
import glob
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 그날그날 모아 과거를 다시 못 받는 것 — 새로 생기면 여기 더한다 (모르는 폴더는 「확인 필요」 로 찍힌다)
못받음 = {"data/minute", "data/orderbook-antc", "data/news", "data/dart-snap", "data/kind-time", "data/consensus"}
받음 = {"data/krx-daily", "data/krx-extra", "data/flow-daily", "data/etf-krx", "data/dart-daily", "data/quarter-fin",
        "data/index-daily", "data/yahoo", "data/dart-capital", "data/naver-quarter", "data/dart-exec", "data/us-symbols",
        "data/dart-major", "data/dart-fin", "data/contract", "data/fred", "data/etf-daily", "data/_cache", "data/_search"}


def 크기(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    t = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            try:
                t += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return t


def 사람(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def main():
    줄 = [f"# 옮기기 현황 — {datetime.datetime.now():%Y-%m-%d %H:%M} 에 뽑음", "",
         "> `python scripts/migration_inventory.py` 로 다시 뽑는다 · 왜·어떻게는 docs/옮기기_체크리스트.md", ""]
    o = subprocess.run(["git", "-C", _B, "status", "--ignored", "--porcelain"], capture_output=True, text=True, encoding="utf-8").stdout
    빠짐 = sorted({l[3:].strip().strip('"').rstrip("/") for l in o.splitlines() if l.startswith("!!")})
    줄 += ["## ① GitHub 에 안 올라가는 것", "", "| 경로 | 크기 | 다시 받나 |", "|---|---|---|"]
    합 = 0
    for p in 빠짐:
        if "__pycache__" in p or p.endswith(".pyc"):
            continue
        n = 크기(os.path.join(_B, p))
        합 += n
        만들어짐 = p.endswith((".html", ".pkl", ".bak")) or "skills/" in p or "\\354\\231\\270" in p
        표 = ("❌ **다시 못 받는다 — 꼭 가져간다**" if p in 못받음 else
              ("다시 받는다(시간 걸림)" if p in 받음 else
               ("🔒 비밀 — 손으로" if "secret" in p else
                ("돌리면 다시 생긴다 — 안 가져가도 됨" if 만들어짐 else "⚠️ 확인 필요(새로 생긴 것)"))))
        줄.append(f"| `{p}` | {사람(n)} | {표} |")
    줄 += ["", f"합계 {사람(합)}", ""]
    # ── C:\Users\mrblue\Claude 폴더 전체 (사용자 10/2 「이 폴더 전체를 봐줬으면 좋겠어.」) ── 읽기만 · 비밀 파일은 이름만
    위 = os.path.dirname(_B)
    줄 += [f"## ①-2 `{위}` 전체 — 저장소 밖 폴더", "", "| 폴더 | 크기 | 파일 | GitHub | 가져가기 |", "|---|---|---|---|---|"]
    for d in sorted(os.listdir(위)):
        p = os.path.join(위, d)
        if not os.path.isdir(p) or os.path.abspath(p) == os.path.abspath(_B):
            continue
        n = 크기(p)
        f수 = sum(len(fs) for _, _, fs in os.walk(p))
        깃 = "있음" if os.path.isdir(os.path.join(p, ".git")) else "**없음**"
        비밀 = [f for f in os.listdir(p) if f.startswith(".env") and f != ".env.example"]
        노드 = os.path.isdir(os.path.join(p, "node_modules"))
        말 = ("통째 복사" + (f" · 🔒 {', '.join(비밀)} 는 비밀 — 손으로" if 비밀 else "")
              + (" · node_modules 는 빼고(npm install 로 다시)" if 노드 else ""))
        줄.append(f"| `{d}` | {사람(n)} | {f수} | {깃} | {말} |")
    줄.append("")
    mem = glob.glob(os.path.expanduser(r"~/.claude/projects/c--Users-mrblue-Claude-morning-breifing-code/memory/*.md"))
    줄 += ["## ② 저장소 밖", "", f"- 작업 메모리 `~/.claude/projects/c--Users-mrblue-Claude-morning-breifing-code/memory/` — **{len(mem)}개**",
           "- Cowork `C:\\Users\\mrblue\\Claude\\Templates\\` · `Scheduled\\` (수정 금지 폴더 — 통째 복사)", ""]
    try:
        t = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-ScheduledTask | ? { $_.TaskPath -notlike '\\Microsoft*' -and $_.TaskName -notmatch 'OneDrive|Adobe|SoftLanding|User_Feed' } | "
                            "% { $_.TaskName + '|' + $_.State }"], capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
        작업 = [l.split("|") for l in t.splitlines() if "|" in l]
        줄 += [f"## ③ 예약 작업 {len(작업)}개 (새 PC 에서 다시 만든다)", "", " · ".join(f"{a}({b})" for a, b in 작업), ""]
    except Exception as e:  # noqa: BLE001
        줄 += ["## ③ 예약 작업", "", f"- 못 읽음: {e}", ""]
    ps1 = glob.glob(os.path.join(_B, "scripts", "*.ps1"))
    코드 = glob.glob(os.path.join(_B, "scripts", "*.py")) + ps1
    win, 경로 = 0, 0
    for f in 코드:
        try:
            s = io.open(f, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        win += ("Win32_" in s or "Get-CimInstance" in s)
        경로 += ("C:\\Users" in s or "C:/Users" in s)
    줄 += ["## ④ 맥으로 갈 때 바꿀 코드 규모", "", f"- PowerShell 스크립트 {len(ps1)}개 · Win32_/CimInstance 쓰는 파일 {win}개 · `C:\\Users` 경로 박힌 파일 {경로}개", ""]
    pk = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, encoding="utf-8").stdout.split()
    io.open(os.path.join(_B, "data", "requirements-snapshot.txt"), "w", encoding="utf-8").write("\n".join(pk) + "\n")
    줄 += ["## ⑤ 파이썬", "", f"- {sys.version.split()[0]} · 패키지 {len(pk)}개 → `data/requirements-snapshot.txt` (새 PC 에서 `pip install -r`)", ""]
    밖 = os.path.join(_B, "data", "옮기기_현황.md")
    io.open(밖, "w", encoding="utf-8").write("\n".join(줄) + "\n")
    print("\n".join(줄))
    return 0


if __name__ == "__main__":
    sys.exit(main())
