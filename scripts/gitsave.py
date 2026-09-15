#!/usr/bin/env python3
r"""
gitsave.py — **커밋이 됐는지 확인하고** 올린다 (2026-09-15 신설)

## 왜
2026-09-15 새벽에 `git commit` 이 **네 번 조용히 안 됐다.**
파일도 `git add` 도 멀쩡했는데 커밋만 안 생겼고, 아무 소리도 안 났다.
아침에 `git log` 를 보고서야 알았다 — 여섯 시간치 작업이 커밋 없이 떠 있었다.

```
git commit -q -F -   <- 메시지를 stdin 으로 넘긴다
```
백그라운드 작업이 도는 중에 stdin 이 비면 **빈 메시지**가 되고,
git 은 빈 메시지를 거부한다. `-q` 와 파이프 때문에 그 소리가 묻혔다.

⇒ 메시지를 **파일**로 넘기고, 커밋 **전후의 HEAD 를 견줘** 진짜 됐는지 본다.
   안 됐으면 **소리친다.** 조용히 넘어가지 않는다.

## 쓰는 법
```
python scripts\gitsave.py 메시지파일.txt            # 커밋만
python scripts\gitsave.py 메시지파일.txt --올림      # 커밋 + push
```
⚠️ 무엇을 커밋할지는 **먼저 `git add`** 로 정해 둔다. 여기서 add 하지 않는다 —
   무엇이 올라가는지 모르고 올리는 일이 없게.
⚠️ 저장소가 **public** 이다. 올리기 전에 `secrets.json` 이 목록에 있는지 본다
   (`grep secrets` 만 하면 키가 없는 `check_secrets.py` 가 걸려 헛경보다)
"""
import os
import subprocess
import sys

_뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _git(*인자, 받기=True):
    r = subprocess.run(["git", *인자], cwd=_뿌리, capture_output=받기,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    쪽지 = os.path.abspath(sys.argv[1])
    if not os.path.exists(쪽지):
        print(f"⚠️ 메시지 파일이 없다: {쪽지}")
        return 1

    # ── ① 올라갈 것이 있나 ──────────────────────────────────
    _, 담긴것, _ = _git("diff", "--cached", "--name-only")
    if not 담긴것:
        print("⚠️ **담긴 것이 없다** — 먼저 `git add` 해라. 커밋하지 않는다")
        return 1
    줄들 = 담긴것.splitlines()
    print(f"  담긴 것 {len(줄들)}개")
    for z in 줄들[:12]:
        print(f"    {z}")
    if len(줄들) > 12:
        print(f"    … 그리고 {len(줄들) - 12}개 더")

    # ── ② 비밀이 섞였나 (저장소가 public 이다) ──────────────
    _, 다들, _ = _git("ls-files", "--cached")
    샌것 = [z for z in 다들.splitlines() if "secrets.json" in z]
    if 샌것:
        print(f"\n🚨 **secrets.json 이 목록에 있다 — 멈춘다**: {샌것}")
        return 1
    print("  secrets.json 없음 ✅")

    # ── ③ 커밋 — **전후 HEAD 를 견준다** ────────────────────
    _, 앞HEAD, _ = _git("rev-parse", "HEAD")
    코드, 나온, 샌 = _git("commit", "-F", 쪽지)
    _, 뒤HEAD, _ = _git("rev-parse", "HEAD")
    if 뒤HEAD == 앞HEAD:
        # ⚠️ 여기가 새벽에 조용히 지나간 자리다
        print(f"\n🚨 **커밋이 안 됐다** (HEAD 가 그대로 {앞HEAD[:7]})")
        print(f"   git 이 한 말: {(나온 + ' ' + 샌).strip()[:300]}")
        print("   ⚠️ 담긴 것은 그대로 있다 — 다시 시도해도 안 잃는다")
        return 1
    print(f"\n  ✅ 커밋됨 {앞HEAD[:7]} → {뒤HEAD[:7]}")
    print(f"     {나온.splitlines()[0] if 나온 else ''}")

    # ── ④ 올림 ──────────────────────────────────────────────
    if "--올림" not in sys.argv:
        print("  (올리지 않았다 — `--올림` 을 주면 push 한다)")
        return 0
    밀기 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "scripts", "push_token.py")
    밀기 = os.path.normpath(밀기)
    if not os.path.exists(밀기):
        print("  ⚠️ push_token.py 가 없다 — 손으로 올려라")
        return 1
    r = subprocess.run([sys.executable, 밀기], cwd=_뿌리)
    if r.returncode != 0:
        print("  🚨 **push 가 안 됐다**")
        return 1
    # push 가 정말 됐나 — 원격 참조로 확인한다
    _git("fetch", "-q", "origin")
    _, 견줌, _ = _git("status", "-sb")
    첫 = 견줌.splitlines()[0] if 견줌 else ""
    if "ahead" in 첫:
        print(f"  🚨 **아직 안 올라간 것이 있다**: {첫}")
        return 1
    print(f"  ✅ 원격과 같다 — {첫}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
