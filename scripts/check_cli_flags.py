r"""A3 — **없는 옵션을 넘기는 곳**을 전수로 찾는다 (2026-09-23 · 연휴 계획 A3)

왜 있나: `collect_krx_extra.py --최근 3` 이 **2주 동안 없는 옵션**이었다.
파이썬은 모르는 인자를 조용히 무시한다 → 매일 아침 16분을 헛돌았고,
브리핑에 그 줄을 옮기다 우연히 걸렸다. 우연에 기대지 않으려고 이 검사기를 만든다.

무엇을 하나:
  ① .ps1 · .py · .md 에서 `... scripts/xxx.py --옵션 ...` 꼴을 전부 찾는다
  ② 그 xxx.py 안에 그 옵션 글자가 **있는지** 본다 (argparse 든 sys.argv 든 글자는 남는다)
  ③ 없으면 ❌ — 파일·줄번호·옵션을 찍는다

조용하다: 이상 없으면 한 줄만 찍는다 (「점검기의 소음이 실패를 숨긴다」).
나가는 값: 이상 있으면 1
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
스크립트방 = os.path.join(뿌리, "scripts")

# `python ... scripts\foo.py` 또는 `scripts/foo.py` 뒤에 오는 것을 본다
부름 = re.compile(r"(?:scripts[\\/])([A-Za-z0-9_]+\.py)((?:\s+(?:--?[^\s\"']+|\"[^\"]*\"|'[^']*'|[^\s\"'|;)&]+))*)")
옵션뽑기 = re.compile(r"(?<![\w-])(--[A-Za-z0-9가-힣_-]+)")

# 봐주는 것 — 파이썬 제 옵션이거나, 값이 아니라 설명인 자리
봐줌 = {"--help", "--version", "--"}
볼파일 = []
for 방, _, 것들 in os.walk(뿌리):
    if any(z in 방 for z in (".git", "node_modules", "_labs", "run-logs", "__pycache__")):
        continue
    for 이름 in 것들:
        if 이름 == "check_cli_flags.py":   # 제 설명문의 보기(xxx.py)를 제가 잎지 않게
            continue
        if 이름.endswith((".ps1", ".py", ".md", ".bat", ".cmd")):
            볼파일.append(os.path.join(방, 이름))

본문 = {}


def 대상글(파일이름):
    """scripts/<이름> 의 글을 한 번만 읽어 둔다. 없으면 None"""
    if 파일이름 not in 본문:
        길 = os.path.join(스크립트방, 파일이름)
        try:
            본문[파일이름] = io.open(길, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            본문[파일이름] = None
    return 본문[파일이름]


걸림, 본곳, 없는스크립트 = [], 0, []
for 길 in 볼파일:
    try:
        줄들 = io.open(길, encoding="utf-8-sig", errors="replace").read().splitlines()
    except OSError:
        continue
    보임 = os.path.relpath(길, 뿌리)
    for 번, 줄 in enumerate(줄들, 1):
        벗 = 줄.strip()
        for m in 부름.finditer(줄):
            대상, 꼬리 = m.group(1), m.group(2) or ""
            옵션들 = [z for z in 옵션뽑기.findall(꼬리) if z not in 봐줌]
            if not 옵션들:
                continue
            글 = 대상글(대상)
            if 글 is None:
                없는스크립트.append((보임, 번, 대상))
                continue
            본곳 += 1
            for 옵 in 옵션들:
                # 주석 안의 예시도 실제로 돌 수 있는 글이라 똑같이 본다 (전에 브리핑 줄을 주석에서 옮겼다)
                if 옵 not in 글:
                    걸림.append((보임, 번, 대상, 옵, 벗[:96]))

if 걸림:
    print(f"❌ 없는 옵션을 넘기는 곳 {len(걸림)}곳")
    for 보임, 번, 대상, 옵, 벗 in 걸림:
        print(f"   {보임}:{번}  →  {대상} 에 `{옵}` 가 없다")
        print(f"      {벗}")
if 없는스크립트:
    print(f"⚠️ 가리키는 스크립트가 없는 곳 {len(없는스크립트)}곳")
    for 보임, 번, 대상 in 없는스크립트[:20]:
        print(f"   {보임}:{번}  →  scripts/{대상} 없음")
if not 걸림 and not 없는스크립트:
    print(f"✅ A3 — 옵션 {본곳}곳 전부 대상 스크립트에 있다")
raise SystemExit(1 if (걸림 or 없는스크립트) else 0)
