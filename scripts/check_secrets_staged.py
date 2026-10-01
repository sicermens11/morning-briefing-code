r"""커밋하려는 것에 비밀이 섞였나 (pre-commit 훅이 부른다 · 2026-09-23)

⚠️ 값은 절대 안 찍는다 — 파일 이름과 줄 번호만 말한다.
나가는 값: 1 이면 커밋이 막힌다
"""
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

위험한이름 = re.compile(r"secrets|credential|(^|[/_-])tokens?\.|api[-_]?key|\.pem$|\.p12$|id_rsa", re.I)
위험한값 = [
    (re.compile(r"\b[0-9a-f]{40}\b"), "40자리 hex (DART 열쇠 꼴)"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "sk- 로 시작하는 열쇠"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "GitHub 토큰"),
    (re.compile(r"\bAKIA[0-9A-Z]{12,}"), "AWS 열쇠"),
    (re.compile(r"(?i)\"?(appkey|appsecret|app_secret|password|passwd|secret)\"?\s*[:=]\s*\"?[A-Za-z0-9/+=_-]{16,}"),
     "설정에 긴 비밀값"),
]


def 껍질(명령):
    return subprocess.run(명령, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


파일들 = [z for z in 껍질(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]).splitlines() if z.strip()]
# ⚠️ 검사기 자신은 이름에 secrets 가 들어 있다 — 제가 제발을 물면 아무것도 못 올린다 (2026-09-23)
봐줄길 = {"scripts/check_secrets_staged.py", "scripts/install_hooks.py",
          "scripts/check_secrets.py", ".gitignore"}
# ⭐ 10/1 사용자 「오케이 너 권고대로 진행하자」 — 이름 규칙만 봐주고 **내용 검사는 계속** 하는 파일.
#    push_token.py 는 열쇠를 config 에서 읽기만 한다(코드에 열쇠 없음). 이름의 「_token.」 때문에 막혔다.
#    통째로 건너뛰는 「봐줄길」과 다르다 — 누가 이 파일에 열쇠를 적으면 여전히 막힌다
이름만봐줌 = {"scripts/push_token.py"}
막음 = []
for f in 파일들:
    if f in 봐줄길:
        continue
    if 위험한이름.search(f) and f not in 이름만봐줌:
        막음.append((f, 0, "파일 이름이 비밀처럼 생겼다"))
        continue
    글 = 껍질(["git", "show", f":{f}"])
    if not 글 or len(글) > 4_000_000:
        continue
    for 번, 줄 in enumerate(글.splitlines(), 1):
        if len(줄) > 4000:
            continue
        for 꼴, 왜 in 위험한값:
            if 꼴.search(줄):
                막음.append((f, 번, 왜))
                break

if 막음:
    print("❌ 커밋을 막았다 — 비밀이 섞였을 수 있다 (저장소는 **공개**다)")
    for f, 번, 왜 in 막음[:20]:
        print(f"   {f}" + (f":{번}" if 번 else "") + f"  — {왜}")
    print("   ⚠️ 값은 여기 안 찍는다. 해당 줄을 직접 확인해라")
    print("   정말 괜찮으면: git commit --no-verify")
    raise SystemExit(1)
raise SystemExit(0)
