#!/usr/bin/env python3
r"""
cut_compare.py — **자름 10 · 20 · 30 견주기** (2026-10-05) · 무리 43개 · 낙폭 체 없음
· 통과 수가 아니라 **뒤 기간 돈·낙폭**으로 본다 (10/3 할 일 「통과 수보다 뒤 기간 돈·낙폭으로 견준다」)
· 무리마다 ⑨ 결론의 통과 규칙(OR 묶음 뺌)과 「(참고) 이 무리 아무 날」 뒤 값을 읽는다
· 무리마다 **가장 좋은 통과 규칙 하나**(뒤 끝 자산 최대)를 고르면 그것도 사후 선택이다 → 중앙값·「아무 날 이긴 비율」을 같이 찍는다
· 결과는 data/_labs/<오늘>_자름견주기.txt
"""
import datetime
import glob
import io
import os
import re
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8")
_L = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "_labs")
_판 = {"10": "2026-10-03_B*_무리전용_*_자름10_낙폭체없음.txt",
       "20": "2026-10-02_B*_무리전용_*_자름20_낙폭체없음.txt",
       "30": "2026-10-04_B*_무리전용_*_자름30_낙폭체없음.txt"}
_밖 = io.open(os.path.join(_L, f"{datetime.date.today():%Y-%m-%d}_자름견주기.txt"), "w", encoding="utf-8")


def 찍기(s=""):
    print(s, flush=True)
    _밖.write(s + "\n")


def 읽기(p):
    s = io.open(p, encoding="utf-8", errors="replace").read()
    if "[대조] 무리" not in s:
        return None
    m = re.search(r"── 무리 전용 규칙 ── ([^\n]+)", s)
    무리 = m.group(1).strip() if m else os.path.basename(p)
    구 = s[s.find("⑨ **결론"):s.find("[대조] 무리")] if "⑨ **결론" in s else ""
    통 = []
    for z in re.finditer(r"\n\s+\[(.+?)\] · 앞 [^\n]*\n\s+뒤 \d{4}~: ([\d,]+)원 \(현금만 ([\d,]+)\) · 연 ([\-\d.]+)% · 낙폭 ([\-\d.]+)% · 1년 (\d+)번", 구):
        if z.group(1).startswith("OR "):
            continue
        통.append({"조건": z.group(1), "끝": int(z.group(2).replace(",", "")), "현금": int(z.group(3).replace(",", "")),
                  "낙": float(z.group(5)), "번": int(z.group(6))})
    아 = re.search(r"\(참고\) 이 무리 아무 날[^\n]*│\s+([\d,]+)\s+([\-\d.]+)%\s+([\-\d.]+)%\s+(\d+)번", s)
    아무 = {"끝": int(아.group(1).replace(",", "")), "낙": float(아.group(3)), "번": int(아.group(4))} if 아 else None
    return 무리, 통, 아무


def main():
    표 = {}
    for 자, pat in _판.items():
        파일들 = sorted(p for p in glob.glob(os.path.join(_L, pat)) if ".시간." not in p)
        표[자] = {}
        for p in 파일들:
            r = 읽기(p)
            if r:
                표[자][r[0]] = (r[1], r[2])
        찍기(f"자름 {자}: 파일 {len(파일들)}개 · 끝까지 간 무리 {len(표[자])}개")
    찍기("=" * 120)
    찍기("  ── 자름 10 · 20 · 30 — 뒤 기간(2019~) · 낙폭 체 없음 · 무리 43개 ──")
    찍기("     「아무 날 대비」 = 통과 규칙 뒤 끝 자산 ÷ 같은 무리 아무 날(문턱 안 봄 · 4자리) 뒤 끝 자산")
    찍기("     ⚠️ 무리별 1등은 뒤 기간을 보고 고른 것이라 부풀어 있다 — 「모든 통과 규칙」 줄이 덜 치우친 값")
    찍기("=" * 120)
    찍기(f"  {'자름':<6}{'통과 무리':>9}{'통과 규칙':>9}{'아무 날 이긴 규칙':>16}{'배수 중앙값':>11}{'낙폭 중앙값':>11}{'1년 기회 중앙값':>15}"
         f"{'무리 1등 배수 중앙값':>18}{'1등 낙폭 중앙값':>15}")
    for 자, 무리들 in 표.items():
        배, 낙, 번, 일배, 일낙 = [], [], [], [], []
        통무 = 0
        for 무리, (통, 아무) in 무리들.items():
            if not 통 or not 아무 or 아무["끝"] <= 0:
                continue
            통무 += 1
            for r in 통:
                배.append(r["끝"] / 아무["끝"])
                낙.append(r["낙"])
                번.append(r["번"])
            일 = max(통, key=lambda r: r["끝"])
            일배.append(일["끝"] / 아무["끝"])
            일낙.append(일["낙"])
        이김 = sum(1 for b in 배 if b > 1)
        중 = (lambda xs: statistics.median(xs) if xs else float("nan"))
        찍기(f"  {자:<6}{통무:>9}{len(배):>9}{f'{이김} ({이김 / len(배) * 100:.0f}%)' if 배 else '-':>16}{중(배):>10.2f}배{중(낙):>10.1f}%"
             f"{중(번):>14.0f}번{중(일배):>17.2f}배{중(일낙):>14.1f}%")
    찍기("")
    찍기("  무리별 1등 (뒤 끝 자산 ÷ 아무 날) — 세 자름 나란히")
    모든무리 = sorted(set().union(*[set(v) for v in 표.values()]))
    찍기(f"  {'무리':<30}" + "".join(f"{'자름 ' + 자:>22}" for 자 in 표))
    for 무리 in 모든무리:
        칸 = []
        for 자 in 표:
            통, 아무 = 표[자].get(무리, ([], None))
            if not 아무:
                칸.append(f"{'없음':>22}")
            elif not 통:
                칸.append(f"{'통과 0':>22}")
            else:
                일 = max(통, key=lambda r: r["끝"])
                칸.append(f"{일['끝'] / 아무['끝']:>8.2f}배 {일['낙']:>6.1f}% {len(통):>2}개")
        찍기(f"  {무리[:28]:<30}" + "".join(칸))
    찍기("  [대조] 자름 견주기 끝")
    _밖.close()


if __name__ == "__main__":
    sys.exit(main())
