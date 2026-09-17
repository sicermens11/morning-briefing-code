#!/usr/bin/env python3
r"""
sync_outside.py — **프로젝트 폴더 밖에 있던 것을 안으로 복사한다** (2026-09-17 신설)

## 왜
```
사용자: 「나중에 옮기기 편하게 폴더 하나에 잘 정리되어 있으면 좋을 것 같은데!」

찾아보니 **아침 브리핑이 반드시 필요로 하는 것이 프로젝트 폴더 밖에 있었다.**
  C:\Users\mrblue\.claude\skills\            스킬 4개 (728KB)
      morning-sector-briefing   ← 08:02 아침 브리핑 본체. **없으면 브리핑이 안 돈다**
      entry-check               ← 09:05 진입 확인
      value-chain-map-updater · weekly-action-review
  C:\Users\mrblue\.claude\projects\…\memory\  메모리 50개 (240KB)
      ← 없으면 다음 세션의 내가 규칙·약속·지난 실수를 통째로 잊는다

둘 다 합쳐 1MB 도 안 되는데, PC 가 바뀌면 **이것만 빠져서 브리핑이 안 돈다.**
그래서 프로젝트 안 `외부사본\` 으로 복사해 두고 git 에 넣는다 (GitHub 백업까지 자동).
```
## 무엇을
```
외부사본\skills\   ← ~\.claude\skills\ 통째로
외부사본\memory\   ← ~\.claude\projects\{이 프로젝트}\memory\ 통째로
외부사본\README.md ← 새 PC 에서 어디로 되돌리는지
```
⚠️ **되돌리는 건 사람이 한다.** 이 스크립트는 **밖 → 안** 한 방향으로만 복사한다.
   (안 → 밖으로 덮으면 최신 스킬을 옛 사본으로 날릴 수 있다)

쓰는 법:
    python scripts\sync_outside.py          복사한다
    python scripts\sync_outside.py --보기    뭐가 다른지만 본다
"""
import filecmp
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_홈 = os.path.expanduser("~")
_밖 = os.path.join(_홈, ".claude")
_안 = os.path.join(_BASE, "외부사본")
_프로젝트키 = "c--Users-mrblue-Claude-morning-breifing-code"

_짝 = [
    ("skills", os.path.join(_밖, "skills"),
     "스킬 — 08:02 브리핑·09:05 진입확인 본체. 되돌릴 곳: ~\\.claude\\skills\\"),
    ("memory", os.path.join(_밖, "projects", _프로젝트키, "memory"),
     "메모리 — 규칙·약속·지난 실수. 되돌릴 곳: ~\\.claude\\projects\\"
     + _프로젝트키 + "\\memory\\"),
]


def _다른것(원본, 사본):
    """(새로 생김, 바뀜, 원본에서 사라짐) 파일 목록"""
    새, 바뀜, 사라짐 = [], [], []
    원본파일 = set()
    for 뿌리, _, 들 in os.walk(원본):
        for f in 들:
            p = os.path.join(뿌리, f)
            상대 = os.path.relpath(p, 원본)
            원본파일.add(상대)
            q = os.path.join(사본, 상대)
            if not os.path.exists(q):
                새.append(상대)
            elif not filecmp.cmp(p, q, shallow=False):
                바뀜.append(상대)
    if os.path.isdir(사본):
        for 뿌리, _, 들 in os.walk(사본):
            for f in 들:
                상대 = os.path.relpath(os.path.join(뿌리, f), 사본)
                if 상대 not in 원본파일:
                    사라짐.append(상대)
    return 새, 바뀜, 사라짐


def main():
    보기만 = "--보기" in sys.argv
    print("===== 밖에 있던 것을 안으로 =====")
    모두바뀜 = 0
    for 이름, 원본, 설명 in _짝:
        사본 = os.path.join(_안, 이름)
        if not os.path.isdir(원본):
            print(f"  ⚠️ {이름}: 원본이 없다 — {원본}")
            continue
        새, 바뀜, 사라짐 = _다른것(원본, 사본)
        n = len(새) + len(바뀜) + len(사라짐)
        모두바뀜 += n
        if n == 0:
            print(f"  ✅ {이름}: 그대로 ({sum(len(x[2]) for x in os.walk(원본)):,}개)")
            continue
        print(f"  ⬛ {이름}: 새 {len(새)} · 바뀜 {len(바뀜)} · 밖에서 지워짐 {len(사라짐)}")
        for 상대 in (새 + 바뀜)[:6]:
            print(f"       · {상대}")
        if 보기만:
            continue
        # ⚠️ 통째로 다시 만든다 — 밖에서 지워진 파일이 사본에 남지 않게
        if os.path.isdir(사본):
            shutil.rmtree(사본)
        shutil.copytree(원본, 사본)
        print(f"     → 복사했다 ({이름})")

    if 보기만:
        print("  (--보기 라 복사하지 않았다)")
        return 0

    os.makedirs(_안, exist_ok=True)
    io.open(os.path.join(_안, "README.md"), "w", encoding="utf-8").write(
        "# 외부사본 — 프로젝트 폴더 **밖**에 있던 것의 사본\n\n"
        "`scripts/sync_outside.py` 가 만든다. **손으로 고치지 않는다.**\n\n"
        "## 왜 있나\n"
        "아침 브리핑이 쓰는 스킬과 내(클로드) 메모리가 프로젝트 폴더 밖\n"
        "`~\\.claude\\` 에 있다. PC 를 옮길 때 폴더만 복사하면 **이게 빠져서 브리핑이 안 돈다.**\n"
        "그래서 여기에 사본을 두고 git 에 넣는다 (GitHub 백업까지 자동).\n\n"
        "## 새 PC 에서 되돌리는 법\n```\n"
        + "\n".join(f"{이름}\\  →  {원본}" for 이름, 원본, _ in _짝)
        + "\n```\n⚠️ 되돌리는 건 **사람이** 한다. 이 스크립트는 밖 → 안 한 방향뿐이다.\n\n"
        "## 무엇이 들었나\n"
        + "\n".join(f"- `{이름}\\` — {설명}" for 이름, _, 설명 in _짝) + "\n")
    print(f"  ✅ 끝 — 바뀐 것 {모두바뀜}개 · {_안}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
