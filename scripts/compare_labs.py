#!/usr/bin/env python3
r"""
compare_labs.py — **판 여럿의 자본 시뮬을 한 표로** (2026-09-14 밤 신설)

## 왜
판을 하나씩 열어 눈으로 견주다 보니 숫자가 섞인다. L판을 「82.6억」이라 적었다가
다른 절의 숫자였던 적도 있다. 판마다 **같은 자리**(A절 후보 조건별 자본 시뮬)를
뽑아 나란히 놓는다.

## ⚠️ 무엇을 보나
```
끝 자산    ⭐ 이게 답이다. 평균 수익이 아니라 **돈**  [[avg-return-is-not-money]]
낙폭       **-10% 가 한계**. 오차 ±0.5 를 얹어서 본다
산 것      ⭐ 사용자 1순위는 **상승 기회 포착**이다.
           「적게 사서 승률이 올랐다」를 승리로 세지 않는다
```

쓰는 법:
    python scripts\compare_labs.py                     # 오늘 판 전부
    python scripts\compare_labs.py 2026-09-14_P 2026-09-14_N2
"""
import io
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LABS = os.path.join(_BASE, "data", "_labs")

# A절 표의 한 줄: 이름 … 147,600,219원 +38.21% -6.5% 186 5.85  (+33%)
_줄 = re.compile(
    r"^\s{4}(?P<이름>.+?)\s{2,}"
    r"(?P<끝>[\d,]+)원\s+"
    r"(?P<연>[+-][\d.]+)%\s+"
    r"(?P<낙>[+-][\d.]+)%\s+"
    r"(?P<산>[\d,]+)\s+"
    r"(?P<돈낙>[\d.]+)")


def 읽기(경로):
    """A절 「후보 조건별 자본 시뮬」 표만 뽑는다"""
    안에 = False
    벌 = []
    기준선 = ""
    for 줄 in io.open(경로, encoding="utf-8", errors="replace"):
        if "이 판의 기준선" in 줄:
            기준선 = 줄.strip().lstrip("⭐ ")
        if "후보 조건별 자본 시뮬" in 줄:
            안에 = True
            continue
        if 안에:
            # 다음 절(── B …)을 만나면 끝
            if 줄.startswith("  ──") or 줄.startswith("=" * 10):
                break
            m = _줄.match(줄.rstrip())
            if m:
                벌.append({
                    "이름": re.sub(r"\s+", " ", m.group("이름")).strip(),
                    "끝": int(m.group("끝").replace(",", "")),
                    "연": float(m.group("연")),
                    "낙": float(m.group("낙")),
                    "산": int(m.group("산").replace(",", "")),
                    "돈낙": float(m.group("돈낙"))})
    return 기준선, 벌


def 이름줄이기(s):
    """긴 설명을 앞 글자로 — 표가 안 무너지게"""
    s = re.sub(r"\(.*?\)", "", s).strip()
    return s[:34]


def main():
    고른것 = sys.argv[1:]
    파일들 = sorted(f for f in os.listdir(_LABS) if f.endswith(".txt"))
    if 고른것:
        파일들 = [f for f in 파일들 if any(g in f for g in 고른것)]
    else:
        파일들 = [f for f in 파일들 if f.startswith("2026-09-14_")]
    판들 = []
    for f in 파일들:
        기준선, 벌 = 읽기(os.path.join(_LABS, f))
        if 벌:
            판들.append((f[:-4], 기준선, 벌))
    if not 판들:
        print("  A절 자본 시뮬이 든 판이 없다")
        return 1

    print("=" * 118)
    print("  판 나란히 보기 — A절 **후보 조건별 자본 시뮬**")
    print("  ⚠️ 끝 자산이 답이다 · 낙폭 -10% 가 한계(오차 ±0.5) · 산 것이 **기회**다")
    print("=" * 118)
    for 이름, 기준선, _ in 판들:
        print(f"    {이름:<44}{기준선[:66]}")

    # 판마다 같은 줄 이름을 맞춰 놓는다
    줄이름 = []
    for _, _, 벌 in 판들:
        for r in 벌:
            n = 이름줄이기(r["이름"])
            if n not in 줄이름:
                줄이름.append(n)

    for n in 줄이름:
        print(f"\n  [{n}]")
        print(f"    {'판':<40}{'끝 자산':>16}{'연평균':>9}"
              f"{'낙폭':>8}{'산 것':>7}{'돈÷낙':>8}   견줌")
        밑 = None
        for 판, _, 벌 in 판들:
            r = next((z for z in 벌 if 이름줄이기(z["이름"]) == n), None)
            if not r:
                continue
            if 밑 is None:
                밑 = r
                차 = "⭐ 밑"
            else:
                돈 = (r["끝"] / 밑["끝"] - 1) * 100
                기 = (r["산"] / 밑["산"] - 1) * 100 if 밑["산"] else 0
                차 = f"돈 {돈:+.0f}% · 기회 {기:+.0f}%"
            한계 = " ⚠️한계밖" if r["낙"] - 0.5 <= -10.0 else ""
            print(f"    {판:<40}{r['끝']:>15,}원{r['연']:>8.1f}%"
                  f"{r['낙']:>7.1f}%{r['산']:>7,}{r['돈낙']:>8.2f}   {차}{한계}")
    print("\n" + "=" * 118)
    print("  ⚠️ 낙폭은 **오차 ±0.5 를 얹어서** 한계를 본다 — -9.5% 면 이미 한계다")
    print("  ⚠️ 「적게 사서 승률이 올랐다」는 승리가 아니다. **산 것**을 같이 본다")
    print("=" * 118)
    return 0


if __name__ == "__main__":
    sys.exit(main())
