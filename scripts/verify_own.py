#!/usr/bin/env python3
r"""
verify_own.py — **무리 전용 규칙 판(own_lab)이 설계대로 돌았나** 기계가 대조한다 (2026-09-30)

사용자: 「지금까지 했다고 해놓고 나중에 물어보면 그렇게 안했다고 … 이번 테스트도 그러지 않을 거란 보장이 어딨어?」
⇒ 내 요약 대신 **코드와 결과 파일에서 직접 센 값**. 하나라도 ❌ 면 「무리별 규칙을 쟀다」고 말하지 않는다.
⚠️ 9/30 독립 검사: 옛 판은 combo4 를 보고 있었다 — 이제 own_lab.py 와 그 결과를 본다

## 대조 (설계 docs/2026-09-30_무리전용_시험설계.md)
  ① 코드 — 무리 규칙 찾는 부분에 지금 규칙 값(문턱·매도 40:60·후보 120·하루 최대·_지금E·확정[) 이 없나
  ② 코드 — 미래를 보는 재료(실적공시전5·금통위변경전5·FOMC변경후*) 가 재료 목록에 없나
  ③ 결과 — 무리 · 사건 수 · 앞/뒤 나눔
  ④ 결과 — 쓴 재료 수 (「앞 기간 값이 적어 건너뜀」 몇 개인지 같이)
  ⑤ 결과 — 둘씩 AND 전수 · 셋 · 넷
  ⑥ 결과 — 돈 시뮬 (⑤절) 줄 수
  ⑦ 결과 — 파는 규칙 × 사는 문턱 × 순서 같이 (⑥절)
  ⑧ 결과 — OR (⑦절)
  ⑨ 결과 — 뒤 기간 확인 (⑧절) 줄 수 · 통과 수
  ⑩ 결과 — 끝까지 돌았나 (「[대조]」 줄 · Traceback 없음)
쓰는 법:  python scripts\verify_own.py <결과파일> …   (없으면 오늘 own_lab 결과 전부)
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_금지 = ("R.상대갭문턱", "R.몫들", "R.볼린저문턱", "R.낙폭20문턱", "R.후보수", "_지금E", "R.하루최대종목",
        "R.오늘최대종목", "확정[", "R.앞몫목표", "R.최대보유", "R.시총상한억", "R.시총하한억", "R.대금하한억")
_미래 = ("실적공시전5", "금통위변경전5", "FOMC변경후5", "FOMC변경후20")


def 코드검사():
    s = io.open(os.path.join(_B, "scripts", "own_lab.py"), encoding="utf-8-sig").read()
    a = s.find("#  무리 전용 규칙 — **앞 기간")
    뒤 = s[a:] if a >= 0 else ""
    뒤 = "\n".join(z for z in 뒤.splitlines() if not z.strip().startswith("#"))
    걸린 = [k for k in _금지 if k in 뒤]
    # 시뮬 기본값(_후보수) 은 own_lab 이 후보수 10**9 로 덮는지
    덮 = '"후보수": 10 ** 9' in s
    재목 = s[s.find("    재료들 = ("):s.find("+ tuple(_새재료)", s.find("    재료들 = ("))]
    미 = [k for k in _미래 if f'"{k}"' in 재목]
    return (a >= 0), 걸린, 덮, 미


def 판검사(p):
    s = io.open(p, encoding="utf-8", errors="replace").read()
    줄 = []

    def 찾(pat):
        m = re.search(pat, s)
        return m.group(1) if m else None
    무 = 찾(r"── 무리 전용 규칙 ── ([^\n]+)")
    사 = 찾(r"\n\s+사건 ([\d,]+건 \(앞 [\d,]+ · 뒤 [\d,]+\))")
    줄.append(("③ 무리·사건", bool(무 and 사), f"{무} · {사}" if 무 else "못 찾음"))
    재 = 찾(r"쓸 재료 (\d+)가지")
    건 = len(re.findall(r"앞 기간 값이 [\d,]+개뿐", s))
    줄.append(("④ 쓴 재료", bool(재), f"{재}가지 (앞 기간 자료 적어 건너뜀 {건})" if 재 else "못 찾음"))
    쌍 = 찾(r"② 둘씩 AND — 전수 ([\d,]+)쌍")
    셋 = 찾(r"③ 셋 — [^\n]*?([\d,]+)개")
    넷 = 찾(r"④ 넷 — [^\n]*?([\d,]+)개")
    줄.append(("⑤ AND 조합", bool(쌍), f"둘 {쌍}쌍 전수 · 셋 {셋} · 넷 {넷}"))
    o5 = s.find("  ⑤ 돈 ")
    o6 = s.find("  ⑥ 위 10개")
    n5 = len(re.findall(r"  (✅|❌)\s*$", s[o5:o6], re.M)) if (o5 >= 0 and o6 > o5) else 0
    줄.append(("⑥ 돈 시뮬", n5 > 0, f"조건 {n5}줄"))
    o7 = s.find("  ⑦ OR 로 묶기")
    n6 = len(re.findall(r"→ [\d,]+원 · 낙폭", s[o6:o7])) if (o6 >= 0 and o7 > o6) else 0
    줄.append(("⑦ 사고·팔기 같이", n6 > 0, f"{n6}줄 (파는 규칙 11 × 문턱 × 순서)"))
    o8 = s.find("  ⑧ **뒤 기간 확인**")
    n7 = len(re.findall(r"^\s+\+ ", s[o7:o8], re.M)) if (o7 >= 0 and o8 > o7) else 0
    줄.append(("⑧ OR", o7 >= 0, f"붙인 것 {n7}개" if o7 >= 0 else "절 없음"))
    o9 = s.find("  ⑨ **결론")
    구 = s[o8:o9] if (o8 >= 0 and o9 > o8) else ""
    n8 = len(re.findall(r"(✅ 통과|  ❌)\s*$", 구, re.M))
    통 = len(re.findall(r"✅ 통과\s*$", 구, re.M))
    줄.append(("⑨ 뒤 기간 확인", n8 > 0, f"{n8}줄 · 통과 {통}"))
    터 = re.search(r"Traceback|Error:", s)
    끝 = "  [대조] 무리" in s
    줄.append(("⑩ 끝까지", bool(끝 and not 터),
              ("터짐: " + s[터.start():터.start() + 150].replace("\n", " ")) if 터 else ("끝까지 돌았다" if 끝 else "끝 표시 없음")))
    return os.path.basename(p), 줄


def main():
    있, 걸린, 덮, 미 = 코드검사()
    print("=" * 100)
    print("  무리 전용 규칙 판(own_lab) — 설계대로 돌았나 (코드·결과 파일에서 직접 셈)")
    print("=" * 100)
    ok코드 = 있 and not 걸린 and 덮 and not 미
    print(f"  ① 무리 규칙 부분의 지금 규칙 값: {'없음 ✅' if not 걸린 else '❌ ' + ', '.join(걸린)} · "
          f"후보 120 을 10**9 로 덮음 {'✅' if 덮 else '❌'}")
    print(f"  ② 미래를 보는 재료: {'없음 ✅' if not 미 else '❌ ' + ', '.join(미)}")
    파일들 = sys.argv[1:] or sorted(glob.glob(os.path.join(_B, "data", "_labs", "2026-*_B1[5-9][0-9]_무리*.txt")))
    모두 = True
    for p in 파일들:
        이름, 줄 = 판검사(p)
        ok = all(z[1] for z in 줄)
        모두 = 모두 and ok
        print(f"\n  ── {이름}  {'✅ 전부' if ok else '❌ 빠진 것 있음'}")
        for 라, 됨, 값 in 줄:
            print(f"     {'✅' if 됨 else '❌'} {라:<14} {값}")
    print("\n" + ("  ✅ 전 판 통과" if (모두 and ok코드) else "  ❌ **통과 못 한 것이 있다 — 「무리별 규칙을 쟀다」고 말하지 않는다**"))
    return 0 if (모두 and ok코드) else 1


if __name__ == "__main__":
    sys.exit(main())
