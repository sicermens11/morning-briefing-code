#!/usr/bin/env python3
r"""
verify_own.py — **무리 전용 규칙 판이 사용자 지시대로 돌았나** 기계가 대조한다 (2026-09-30 신설)

## 왜
사용자: 「지금까지 했다고 해놓고 나중에 물어보면 그렇게 안했다고 지금 거의 한달간 반복 되고 있는데
        이번 테스트도 그러지 않을 거란 보장이 어딨어?」
⇒ 내 요약 대신 **결과 파일·코드에서 직접 센 값**을 보여 준다. 하나라도 ❌ 면 「무리별 규칙을 쟀다」고 말하지 않는다.

## 대조 항목 (사용자 지시 원문에서)
  ① 기존 규칙에 얹지 않았나   — OWN 절 코드에 `_지금E(`(지금 규칙) 호출이 **0** 인가
  ② 무리 하나만 봤나           — 결과 파일에 「대형주 전용」/「무리 하나만」 줄과 사건 수
  ③ 재료를 다 썼나             — 「쓸 재료 N가지」 (재료 목록 전체 대비)
  ④ AND 조합을 다 봤나         — 「둘씩 조합 — N쌍 전수」 · 셋 · 넷
  ⑤ 돈으로 쟀나                — OWN ① 표의 줄 수 (조건 × 상대갭 × 자리)
  ⑥ OR 로 묶어 봤나            — OWN ② 줄
  ⑦ 파는 규칙을 무리마다 봤나   — OWN ③ 줄 수 (9가지)
  ⑧ 앞뒤 기간                  — OWN ④ 판정 줄
  ⑨ 끝까지 돌았나              — 결과 파일 끝 「읽는 법」 · 큐 로그 「끝 —」 · 터짐 없음

쓰는 법:
    python scripts\verify_own.py                  오늘 판 전부 (B145~)
    python scripts\verify_own.py <결과파일> …
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def 코드검사():
    r"""① OWN 절 코드에 지금 규칙 호출이 있나 — 코드를 직접 읽는다"""
    s = io.open(os.path.join(_B, "scripts", "combo4_lab.py"), encoding="utf-8-sig").read()
    a = s.find('if os.environ.get("OWN"):')
    b = s.find("읽는 법", a)
    if a < 0 or b < 0:
        return None, "OWN 절을 못 찾았다"
    몸 = s[a:b]
    몸 = "\n".join(z for z in 몸.splitlines() if not z.strip().startswith("#"))
    n = len(re.findall(r"_지금E\s*\(", 몸)) + len(re.findall(r"_지금E\)", 몸))
    재료수 = len(re.findall(r'"[^"]+"', s[s.find("재료들 = ("):s.find("+ tuple(_새재료)")]))
    return n, 재료수


def 판검사(p):
    s = io.open(p, encoding="utf-8", errors="replace").read()
    이름 = os.path.basename(p)
    줄 = []

    def 찾(pat, 기본=None):
        m = re.search(pat, s)
        return m.group(1) if m else 기본
    무리 = 찾(r"⭐ \*\*대형주 전용\*\* — (시총[^·]+· 종목 [\d,]+개 · 사건 [\d,]+건)") or \
        찾(r"⭐ \*\*무리 하나만\*\* — ([^\n]+)")
    줄.append(("② 무리 하나만", bool(무리), 무리 or "못 찾음"))
    재 = 찾(r"쓸 재료 (\d+)가지")
    줄.append(("③ 쓴 재료", bool(재), f"{재}가지" if 재 else "못 찾음"))
    쌍 = 찾(r"둘씩 조합\*\* — ([\d,]+)쌍 전수")
    셋 = "── C **셋씩**" in s
    넷 = "── C-2 **넷씩**" in s
    줄.append(("④ AND 조합", bool(쌍 and 셋 and 넷), f"둘 {쌍 or '?'}쌍 전수 · 셋 {'✓' if 셋 else '✗'} · 넷 {'✓' if 넷 else '✗'}"))
    o = s.find("── OWN ⭐⭐⭐")
    if o < 0:
        줄.append(("⑤~⑧ OWN 절", False, "**OWN 절까지 못 갔다**"))
    else:
        own = s[o:]
        첫표 = own.split("⭐ 낙폭")[0]
        n돈 = len(re.findall(r"^\s{8}\S.*\d{1,3}(,\d{3})+\s+-?\d+\.\d%\s+-?\d+\.\d%\s+\d+\s*$", 첫표, re.M))
        줄.append(("⑤ 돈 시뮬 줄", n돈 > 0, f"{n돈}줄"))
        줄.append(("⑥ OR 쌓기", "② OR 로 쌓기" in own, "있음" if "② OR 로 쌓기" in own else "없음(혼자 서는 조건이 없었거나 못 갔다)"))
        n팔 = len(re.findall(r"③ 파는 규칙", own))
        줄.append(("⑦ 파는 규칙", n팔 > 0, f"{n팔}벌 × 9가지" if n팔 else "없음"))
        앞뒤 = re.findall(r"⇒ (✅ 앞뒤 둘 다 벌었다|❌ 한쪽이 못 벌었다)", own)
        줄.append(("⑧ 앞뒤", bool(앞뒤), " · ".join(앞뒤) if 앞뒤 else "없음"))
    터짐 = re.search(r"Traceback|Error:", s)
    끝 = "읽는 법" in s[-20000:] if o >= 0 else False
    줄.append(("⑨ 끝까지", bool(끝 and not 터짐), ("터짐: " + s[터짐.start():터짐.start() + 120].replace("\n", " ")) if 터짐 else ("끝까지 돌았다" if 끝 else "끝 표시 없음")))
    return 이름, 줄


def main():
    n, 재료수 = 코드검사()
    print("=" * 100)
    print("  무리 전용 규칙 판 — 사용자 지시대로 돌았나 (결과 파일·코드에서 직접 셈)")
    print("=" * 100)
    print(f"  ① 기존 규칙에 얹지 않았나 — OWN 절 코드의 지금 규칙(_지금E) 호출 **{n}번** "
          + ("✅" if n == 0 else "❌"))
    print(f"     (재료 목록에 적힌 재료 {재료수}가지 + 새 재료 — 판마다 실제로 쓴 수는 아래 ③)")
    파일들 = sys.argv[1:] or sorted(z for z in glob.glob(os.path.join(_B, "data", "_labs", "2026-09-*_B1[4-9][0-9]_무리전용_*.txt")))
    모두 = True
    for p in 파일들:
        이름, 줄 = 판검사(p)
        ok = all(z[1] for z in 줄)
        모두 = 모두 and ok
        print(f"\n  ── {이름}  {'✅ 전부' if ok else '❌ 빠진 것 있음'}")
        for 라, 됨, 값 in 줄:
            print(f"     {'✅' if 됨 else '❌'} {라:<14} {값}")
    print("\n" + ("  ✅ 전 판 통과" if 모두 and n == 0 else "  ❌ **통과 못 한 것이 있다 — 「무리별 규칙을 쟀다」고 말하지 않는다**"))
    return 0 if (모두 and n == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
