#!/usr/bin/env python3
"""
check_subject.py - Gmail 제목 통일형식 하드체크 (Windows 이식용, 2026-08-21 신설)

배경: 원본 SKILL.md(DECISIONS.md 132차)는 이 검증을 bash 한 줄로 했다.

    echo "$SUBJECT" | grep -qP '^📊 \\[\\d{4}-\\d{2}-\\d{2}\\(...\\)\\] 모닝 브리핑...'

Windows에는 bash도 grep도 없고, 무엇보다 이모지(📊)와 한글이 섞인 문자열을 PowerShell
명령행으로 넘기면 콘솔 코드페이지(cp949) 때문에 조용히 깨진다. "제목이 규칙을 어겼다"가
아니라 "검증기가 제목을 잘못 읽었다"로 실패하는 게 최악이라, 제목을 UTF-8 파일에 쓰고
경로만 넘기는 방식으로 바꿨다. 판정 정규식 자체는 원본과 글자 단위로 동일하다.

사용법:
    run-py.ps1 -Script check_subject.py -Args @('--file', 'C:\\...\\subject.txt')

출력(stdout): SUBJECT_OK 또는 SUBJECT_FORMAT_VIOLATION
              (읽기 실패 시 SUBJECT_CHECK_ERROR: <사유>)

⚠️ SUBJECT_FORMAT_VIOLATION이면 그 제목으로 create_draft를 호출하지 않는다.
   통일 형식을 다시 보고 고쳐 쓴 뒤 재검증 — 최대 2회. 상세는 SKILL.md STEP 6 참고.
"""
import re
import sys

# ^📊 [YYYY-MM-DD(요일)] 모닝 브리핑  (+ 선택적 " | 종목명등급 · 종목명등급")  (+ 선택적 " [suffix]")
#
# ⚠️ **`[코드]` 마커는 금지다. 있으면 실패다.** (2026-08-26 강제)
#    이력: 2026-08-21~08-25에 Cowork판과 병행 실행하는 동안 메일함에서 두 브리핑을 구분하려고
#    **필수**로 강제했다. 08-25에 Cowork를 수동 실행으로 전환하면서 SKILL.md에서 마커를 뺐지만,
#    정규식은 "있어도 통과"로 남기고 SKILL.md엔 "되살리려면 이렇게" 안내까지 남겼다.
#    **그래서 모델이 08-25·08-26 이틀 연속 마커를 도로 붙였고, 스스로 "[코드] 마커 정상"이라고
#    확인까지 했다** — daily-log 두 날의 "재시도/오류" 항목에 그 문장이 그대로 남아 있다.
#    ⇒ **"쓰지 않기로 한 것"을 통과시키는 검사는 검사가 아니다.** 되살릴 방법을 안내로 남겨두면
#      언젠가 되살아난다. 다시 병행할 일이 생기면 그때 이 파일을 고친다.
SUBJECT_RE = re.compile(
    r"^📊 \[\d{4}-\d{2}-\d{2}\([월화수목금토일]\)\] 모닝 브리핑( \|.+)?( \[.+\])?$"
)
BANNED_MARKER = re.compile(r"\[코드\]")


def main():
    argv = sys.argv[1:]
    if "--file" not in argv:
        print("SUBJECT_CHECK_ERROR: --file <경로> 인자가 필요함")
        return
    path = argv[argv.index("--file") + 1]
    try:
        # utf-8-sig: PowerShell이 붙이는 BOM을 제거한다. 남아 있으면 ^📊 앵커가 무조건 어긋난다.
        with open(path, "r", encoding="utf-8-sig") as fp:
            subject = fp.read().strip()
    except Exception as e:
        print(f"SUBJECT_CHECK_ERROR: 파일 읽기 실패({path}): {e}")
        return

    # ⚠️ 금지 마커를 **먼저** 본다. 형식 위반보다 구체적인 진단이라 먼저 알려주는 게 낫다.
    if BANNED_MARKER.search(subject):
        print("SUBJECT_BANNED_MARKER: 제목에 '[코드]' 마커가 있다. "
              "Cowork 병행 실행 시절의 잔재이며 2026-08-25에 폐지됐다. 제거하고 다시 확인할 것.")
        return
    print("SUBJECT_OK" if SUBJECT_RE.match(subject) else "SUBJECT_FORMAT_VIOLATION")


if __name__ == "__main__":
    main()
