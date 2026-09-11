#!/usr/bin/env python3
r"""
field_audit.py — **우리가 가진 정보를 다 세고, 무엇을 시험했나 대조한다** (2026-09-04)

⚠️ 사용자 질문: *"우리 100여가지 정보 중에 다 한번이라도 테스트 해본거야?"*
   → **짐작하지 말고 실제로 센다.**

## 하는 일
```
1. data/ 아래 모든 자료의 **필드 이름**을 전부 뽑는다
2. scripts/*_lab.py 를 뒤져 **어떤 필드가 실제로 쓰였나** 찾는다
3. 「가진 것」과 「써본 것」을 대조해 **안 써본 것**을 목록으로 낸다
```
⚠️ 「썼다」의 뜻: lab 스크립트 어딘가에 그 필드 이름이 나온다는 것.
   진지하게 검증했다는 뜻은 아니다. **하한선**이다.
"""
import collections
import glob
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")


def 필드뽑기(폴더, 최대=40):
    """폴더 안 파일들을 훑어 (경로, 필드) 쌍을 뽑는다"""
    out = collections.defaultdict(set)
    g = sorted(glob.glob(os.path.join(_DATA, 폴더, "**", "*.json"),
                         recursive=True))
    if not g:
        p = os.path.join(_DATA, 폴더)
        if os.path.isfile(p):
            g = [p]
        elif os.path.isfile(p + ".json"):
            g = [p + ".json"]
    if not g:
        return out, 0
    본 = g[::max(1, len(g) // 최대)][:최대] + [g[-1]]
    for f in 본:
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        def 파(o, 길="", 깊=0):
            if 깊 > 3:
                return
            if isinstance(o, dict):
                for k, v in list(o.items())[:80]:
                    # 종목코드·날짜처럼 값이 키인 것은 건너뛴다
                    # ⚠️ **값이 키인 것**은 필드가 아니다 (2026-09-04 고침)
                    #    종목코드(6자리)·날짜(8자리)·**접수번호(14자리)**·
                    #    티커(영문 대문자)를 필드로 세면 6,823개가 나와 쓸모없다
                    ks2 = str(k)
                    if (ks2.isdigit() and len(ks2) >= 6) or                             re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,6}", ks2) or                             re.fullmatch(r"(19|20)\d\d", ks2):
                        파(v, 길, 깊 + 1)
                        continue
                    out[길 or "(최상위)"].add(k)
                    if isinstance(v, (dict, list)):
                        파(v, (길 + "." + k) if 길 else k, 깊 + 1)
            elif isinstance(o, list) and o:
                파(o[0], 길, 깊)
        파(d)
    return out, len(g)


def main():
    # ── 1. 가진 것 ──
    폴더들 = []
    for name in sorted(os.listdir(_DATA)):
        p = os.path.join(_DATA, name)
        if os.path.isdir(p) and not name.startswith("_"):
            폴더들.append(name)
        elif name.endswith(".json") and not name.startswith("_"):
            폴더들.append(name[:-5])
    가진 = {}
    print("═" * 78)
    print("  1) 우리가 가진 자료")
    print("═" * 78)
    총필드 = set()
    for 폴 in 폴더들:
        표, n = 필드뽑기(폴)
        if not 표:
            continue
        벌 = set()
        for 길, ks in 표.items():
            for k in ks:
                벌.add(f"{폴}:{k}")
        가진[폴] = 벌
        총필드 |= 벌
        키목 = sorted({k for ks in 표.values() for k in ks})
        print(f"    {폴:<18}{n:>6}파일  필드 {len(키목):>3}개  "
              f"{', '.join(키목[:8])}{' …' if len(키목) > 8 else ''}")
    print(f"\n    ⇒ **전체 필드 {len(총필드)}개** (폴더 {len(가진)}개)")

    # ── 2. 써본 것 ──
    쓴 = set()
    쓴파일 = collections.defaultdict(set)
    for f in sorted(glob.glob(os.path.join(_BASE, "scripts", "*.py"))):
        b = os.path.basename(f)
        if not (b.endswith("_lab.py") or b in
                ("record_pick.py", "build_rule_cases.py", "auto_search.py",
                 "verify_all.py", "why_not.py")):
            continue
        try:
            src = io.open(f, encoding="utf-8-sig").read()
        except Exception:
            continue
        for 필 in 총필드:
            폴, k = 필.split(":", 1)
            # 필드 이름이 따옴표 안에 나오는지
            if (f'"{k}"' in src) or (f"'{k}'" in src):
                쓴.add(필)
                쓴파일[필].add(b)

    print("\n" + "═" * 78)
    print("  2) 시험 코드에 실제로 나온 필드")
    print("═" * 78)
    print(f"    **{len(쓴)}개 / {len(총필드)}개**  "
          f"({len(쓴)/max(1,len(총필드))*100:.0f}%)")
    print("    ⚠️ 「나왔다」는 것이지 「제대로 검증했다」는 뜻은 아니다")

    # ── 3. 안 써본 것 ──
    안쓴 = 총필드 - 쓴
    print("\n" + "═" * 78)
    print(f"  3) ⚠️ **한 번도 안 써본 필드 {len(안쓴)}개**")
    print("═" * 78)
    묶 = collections.defaultdict(list)
    for 필 in sorted(안쓴):
        폴, k = 필.split(":", 1)
        묶[폴].append(k)
    for 폴 in sorted(묶, key=lambda z: -len(묶[z])):
        ks = sorted(묶[폴])
        print(f"\n    ── {폴} ({len(ks)}개) ──")
        for i in range(0, len(ks), 6):
            print("       " + " · ".join(ks[i:i + 6]))

    # ── 4. 써본 것 요약 ──
    print("\n" + "═" * 78)
    print(f"  4) 써본 필드 {len(쓴)}개 (어느 시험에서)")
    print("═" * 78)
    묶2 = collections.defaultdict(list)
    for 필 in sorted(쓴):
        폴, k = 필.split(":", 1)
        묶2[폴].append(k)
    for 폴 in sorted(묶2, key=lambda z: -len(묶2[z])):
        print(f"    {폴:<18}{len(묶2[폴]):>3}개  "
              f"{', '.join(sorted(묶2[폴])[:10])}"
              f"{' …' if len(묶2[폴]) > 10 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
