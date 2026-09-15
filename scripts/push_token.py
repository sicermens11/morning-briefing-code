r"""토큰으로 push 한다 — **브라우저 창 없이** (2026-09-14).

`git push` 가 자격 증명을 못 찾아 Git Credential Manager 가 브라우저 OAuth 를
띄웠다. 그 창은 **Gists 읽기·쓰기 + 모든 public/private 저장소 + Workflow** 를
달라고 한다. 필요한 건 저장소 하나에 밀어 넣는 것뿐이다.

이미 있는 fine-grained `GITHUB_TOKEN` 을 쓴다.

⚠️ 규칙:
  · `data\secrets.json` 을 직접 읽지 않는다 — `config.py` 로만 읽는다
  · 토큰을 화면·명령 기록에 남기지 않는다 — 출력에서 지우고, URL 을
    `.git/config` 에 저장하지 않는다(remote 이름 대신 URL 을 직접 넘긴다)
  · `credential.helper=` 를 비워 **GCM 이 다시 안 뜨게** 한다
"""
import os
import re
import subprocess
import sys

뿌리 = r"C:\Users\mrblue\Claude\morning breifing_code"
sys.path.insert(0, os.path.join(뿌리, "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import config  # noqa: E402

토큰 = config.get("GITHUB_TOKEN")
if not 토큰:
    print("GITHUB_TOKEN 이 없다 — scripts/check_secrets.py 로 확인해라")
    raise SystemExit(1)

주소 = f"https://x-access-token:{토큰}@github.com/sicermens11/morning-briefing-code.git"
명령 = ["git", "-c", "credential.helper=", "-c", "credential.interactive=never",
        "push", 주소, "HEAD:main"]

환경 = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
r = subprocess.run(명령, cwd=뿌리, env=환경, capture_output=True, timeout=600)


def 지움(b):
    t = b.decode("utf-8", "replace")
    t = t.replace(토큰, "***")
    # 혹시 다른 꼴로 새어 나오면 그것도 지운다
    return re.sub(r"(gh[pousr]_|github_pat_)[A-Za-z0-9_]+", r"\1***", t)


print(지움(r.stdout))
print(지움(r.stderr))
print("끝났나:", "예" if r.returncode == 0 else f"아니 (코드 {r.returncode})")
