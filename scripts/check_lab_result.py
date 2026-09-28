#!/usr/bin/env python3
# ⚠️ docstring 은 r""" (raw) — 윈도 경로의 `\u` 가 유니코드 이스케이프로 해석되면 파일이 깨진다.
r"""check_lab_result.py — **판이 끝난 뒤 결과를 검산한다** (2026-09-28 신설)

## 왜 있나 — 막개(check_lab_ready)가 못 잡은 것이 있었다

사용자: 「내가 예전에 버그 오류 검사기 만들었던거 같은데 때 지도 오류 같은건 못 잡아?」

막개는 **돌리기 전 코드**를 본다 — 이름 겹침 · 안 풀린 짝 · 없는 값 · ONLY 이름 겹침.
그런데 2026-09-28 에 두 가지가 그물을 빠져나갔다. 둘 다 **코드는 멀쩡히 돌았다**:

  ① **때 지도가 엉뚱한 자리로 시간을 몰아줬다.**
     찍힌 합이 96.3분인데 판은 50분 돌았다 — 거의 정확히 두 배.
     오류도 안 나고 그럴듯한 표가 나왔다. 내가 손으로 합을 따져 보고서야 알았다.
  ② **절 이름이 겹쳐 두 절이 같이 돌았다** (`CAP`).
     결과 파일에 머리글이 두 번 찍혔는데 아무도 안 셌다.

⇒ 이 검사기는 **끝난 결과 파일**을 본다. 막개와 짝이다.
   막개 = 돌리기 **전** · 코드   /   여기 = 돌린 **뒤** · 결과

## 무엇을 보나
  ① **때 지도 합이 판이 돈 시간과 맞나** (0.75~1.25배)  — 재는 장치가 스스로 틀리는 것
  ② **절 머리글이 두 번 찍혔나**                        — 이름이 겹쳐 둘 다 돈 것
  ③ **ONLY 로 고른 절이 정말 찍혔나**                   — 오타로 아무 절도 안 돌았는데 rc=0
  ④ **삼켜진 예외**                                   — Traceback · 「⚠️ … 터졌다」
  ⑤ **결과가 너무 작나**                               — 2KB 아래면 준비하다 죽은 것

⚠️ 「점검기의 소음이 실패를 숨긴다」 — **문제만** 찍는다. 이상 없으면 한 줄로 끝낸다.
⚠️ ②는 gate7_lab 이 **실제로 쓰는 ONLY 이름만** 센다. 절 안의 소제목(── A ⭐)을 세면
   A·B·C·D 가 늘 여러 번 나와 소음이 된다 (첫 판에서 실제로 그랬다).

쓰기:
    python scripts/check_lab_result.py                     가장 최근 판
    python scripts/check_lab_result.py <결과파일.txt>       그 판
나가는 값: 문제가 있으면 1
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_랩 = os.path.join(_뿌리, "data", "_labs")
_로그 = os.path.join(_뿌리, "run-logs")


def _큐로그(결과길):
    r"""결과 파일 이름(2026-09-28_B124_…)에서 판 번호를 뽑아 그 큐 로그를 읽는다."""
    m = re.search(r"_B(\d+)_", os.path.basename(결과길))
    if not m:
        return None
    벌 = sorted(glob.glob(os.path.join(_로그, "queue_b" + m.group(1) + "_*.log")),
                key=os.path.getmtime, reverse=True)
    if not 벌:
        return None
    try:
        return io.open(벌[0], encoding="utf-8", errors="replace").read().replace("\x00", "")
    except OSError:
        return None


def _판이_돈_시간(결과길):
    r"""큐 로그 첫 줄과 끝 줄의 시각 차이를 분으로. 못 찾으면 None."""
    글 = _큐로그(결과길)
    if not 글:
        return None
    때 = re.findall(r"(\d\d)-(\d\d)\s+(\d\d):(\d\d)", 글)
    if len(때) < 2:
        return None
    앞 = int(때[0][2]) * 60 + int(때[0][3])
    뒤 = int(때[-1][2]) * 60 + int(때[-1][3])
    if 뒤 < 앞:                      # 자정을 넘었다
        뒤 += 24 * 60
    return 뒤 - 앞


def _ONLY이름들():
    r"""gate7_lab 이 실제로 쓰는 ONLY 이름들. 못 읽으면 빈 집합(그럼 ②③은 건너뛴다)."""
    try:
        g = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "gate7_lab.py"), encoding="utf-8-sig").read()
        return set(re.findall(r'_ONLY == "([A-Z0-9_-]+)"', g))
    except OSError:
        return set()


def _고른절(결과길, 태그들):
    r"""큐 로그의 「[B124] SLOT+CAP — …」 줄에서 이 판이 고른 절 이름을 읽는다."""
    if not 태그들:
        return []
    글 = _큐로그(결과길)
    if not 글:
        return []
    h = re.search(r"\[B\d+\]\s+([A-Z0-9_+-]+)\s+—", 글)
    if not h:
        return []
    return [z for z in h.group(1).split("+") if z in 태그들]


def 보기(길):
    글 = io.open(길, encoding="utf-8", errors="replace").read()
    탈 = []
    태그 = _ONLY이름들()

    # ── ① 때 지도 합이 판이 돈 시간과 맞나 ──
    합 = None
    m = re.search(r"엿본 횟수\s+([\d,]+)", 글)
    if m:
        합 = int(m.group(1).replace(",", "")) * 0.5 / 60
        실제 = _판이_돈_시간(길)
        if 실제 and 실제 > 0:
            배 = 합 / 실제
            if not 0.75 <= 배 <= 1.25:
                탈.append("① 때 지도가 **{:.1f}분**을 찍었는데 판은 **{}분** 돌았다 "
                          "({:.2f}배) — 재는 장치가 틀렸다".format(합, 실제, 배))
                if 배 > 1.75:
                    탈.append("   ↳ 두 배 가까우면 **재는 실이 저를 세고 있다**")
                elif 배 < 0.5:
                    탈.append("   ↳ 절반 아래면 **엿보기가 자주 놓치고 있다**")

    # ── ② 절 머리글이 두 번 찍혔나 (이름 겹침) ──
    #    ⚠️ 절 **안의 소제목**(── A ⭐ · ── B ⭐)을 세면 A·B·C·D 가 늘 여러 번 나와
    #       소음이 된다. gate7_lab 이 실제로 쓰는 **ONLY 이름만** 센다
    본것 = {}
    for h in re.findall(r"^\s*── ([A-Z0-9_-]+) [⭐ ]", 글, re.M):
        if h in 태그:
            본것[h] = 본것.get(h, 0) + 1
    겹 = ["{}({}번)".format(h, n) for h, n in 본것.items() if n > 1]
    if 겹:
        탈.append("② 절 머리글이 두 번 찍혔다 — " + " · ".join(겹)
                  + " ⇒ 같은 ONLY 이름을 쓰는 절이 둘 있다")

    # ── ③ ONLY 로 고른 절이 정말 찍혔나 ──
    고른 = _고른절(길, 태그)
    안찍힘 = [z for z in 고른 if z not in 본것]
    if 안찍힘:
        탈.append("③ ONLY 로 골랐는데 **안 찍힌 절** — " + " · ".join(안찍힘)
                  + " ⇒ 이름 오타거나 절이 없다 (판 하나를 헛돌렸다)")

    # ── ④ 삼켜진 예외 ──
    터짐 = [z for z in re.findall(r"^.*$", 글, re.M)
            if ("Traceback (most recent" in z)
            or ("터졌다" in z and "⚠️" in z)
            or re.match(r"\s*[A-Za-z]+Error:", z)]
    if 터짐:
        탈.append("④ 삼켜진 예외 {}줄 — 첫 줄: {}".format(len(터짐), 터짐[0].strip()[:90]))

    # ── ⑤ 결과가 너무 작나 ──
    크기 = os.path.getsize(길)
    if 크기 < 2048:
        탈.append("⑤ 결과가 {:,}바이트뿐이다 — 준비하다 죽었을 수 있다".format(크기))

    print("── {}  ({:,}B{})".format(
        os.path.basename(길), 크기,
        " · 때 지도 {:.1f}분".format(합) if 합 else ""))
    if not 탈:
        print("   ✅ 검산 이상 없다")
        return 0
    for z in 탈:
        print("   ❌ " + z)
    return 1


def main():
    벌 = [z for z in sys.argv[1:] if not z.startswith("-")]
    if not 벌:
        벌 = sorted(glob.glob(os.path.join(_랩, "2026-*.txt")),
                    key=os.path.getmtime, reverse=True)[:1]
    if not 벌:
        print("볼 결과 파일이 없다")
        return 0
    나쁨 = 0
    for 길 in 벌:
        if not os.path.exists(길):
            길 = os.path.join(_랩, 길)
        if not os.path.exists(길):
            print("❌ 없는 파일: " + 길)
            나쁨 = 1
            continue
        나쁨 |= 보기(길)
    return 나쁨


if __name__ == "__main__":
    raise SystemExit(main())
