#!/usr/bin/env python3
r"""
one_stock.py — **종목 하나만 떼어 본다** (2026-09-17 신설)

## 왜
```
사용자: 「삼성전자, SK하이닉스 전용 규칙 같은 것도 물어본 것 같은데?」

216차(개별 종목별)는 1,798 종목에 각각 규칙을 배워 **평균**으로 판정했다 —
앞 81.0% → 뒤 62.4% (과적합). 그런데 **개별 종목으로는 62%가 이겼다.**
평균이 무너졌다고 그 안의 큰 종목도 무너졌다는 뜻은 아니다.
대형주는 매일 거래되고 성질이 안정적이라 오히려 될 수도 있다 — 그걸 이름으로 확인한 적이 없다.
```
## 무엇을
```
data\percode-rules.json 에 종목마다 앞 기간에서 배운 규칙이 있다 (1,799 종목).
그 규칙을 **뒤 기간**에 적용해서 종목 하나하나의 성적을 낸다:
   걸린 횟수 · 20일 이김% · 평균 · 그 종목의 바탕(아무 날 샀을 때)과의 차이
⚠️ 「이길 확률」까지다. 한 종목만으로는 돈(③) 시뮬이 뜻이 없다(하루 4종목 상한과 안 맞는다)
```
쓰는 법:
    python scripts\one_stock.py 005930 000660 068270 329180
    python scripts\one_stock.py --큰것 20        시총 큰 20종목
"""
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import omni_lab as O  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_규칙파일 = os.path.join(_BASE, "data", "percode-rules.json")


def main():
    argv = sys.argv[1:]
    try:
        j = json.load(io.open(_규칙파일, encoding="utf-8-sig"))
    except OSError:
        print("⚠️ data\\percode-rules.json 이 없다 — percode_lab.py 를 먼저 돌려라")
        return 1
    앞끝, 규칙들 = j["앞끝"], j["규칙"]

    print("자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총",))
    날 = sorted(주가)
    기본 = O._기본()
    자리 = {}
    종계 = {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1

    if "--큰것" in argv:
        n = int(argv[argv.index("--큰것") + 1])
        끝 = 날[-1]
        코드들 = [c for c, _ in sorted(((c, v[1]) for c, v in 주가[끝].items()),
                                       key=lambda t: -t[1])[:n] if c in 규칙들]
    else:
        코드들 = [a for a in argv if a.isdigit() or (len(a) == 6)]
    if not 코드들:
        print("⚠️ 종목코드를 달라 (예: 005930 000660)")
        return 1

    print(f"\n  앞 기간 ~{앞끝} 에서 배운 규칙을 **뒤 기간**에 적용한다 "
          f"(뒤 {앞끝}~{날[-1]} · 거래일 {sum(1 for d in 날 if d > 앞끝):,})")
    print(f"\n  {'종목':<16}{'규칙':<30}{'걸림':>6}{'20일 이김':>10}{'평균':>8}"
          f"{'그 종목 바탕':>13}{'차이':>8}   판정")
    for code in 코드들:
        규 = 규칙들.get(code)
        이름 = (기본.get(code) or {}).get("이름", code)
        if not 규:
            print(f"  {이름[:14]:<16}{'— 앞 기간에 60번 못 걸려 규칙이 없다':<30}")
            continue
        bw, bt, nw, nt = 규[0], 규[1], 규[2], 규[3]
        bw = int(str(bw).replace("볼", ""))
        nw = int(str(nw).replace("낙", ""))
        sq = 종계.get(code) or []
        자 = 자리.get(code) or {}
        걸림, 모두 = [], []
        for d in 날:
            if d <= 앞끝:
                continue
            k = 자.get(d)
            if k is None or k < max(bw, nw, 20) or k + 21 >= len(sq):
                continue
            뒤값 = (sq[k + 20] / sq[k] - 1) * 100
            모두.append(뒤값)
            창 = sq[k - bw + 1:k + 1]
            m, sd = st.mean(창), (st.pstdev(창) or 1e-9)
            볼 = (sq[k] - m) / (2 * sd)
            if sq[k - nw] <= 0:
                continue
            낙 = (sq[k] / sq[k - nw] - 1) * 100
            if 볼 <= bt and 낙 <= nt:
                걸림.append(뒤값)
        if len(모두) < 100:
            print(f"  {이름[:14]:<16}{'— 뒤 기간 자료가 모자라다':<30}")
            continue
        바탕 = sum(1 for z in 모두 if z > 0) / len(모두) * 100
        라규 = f"볼{bw} {bt:g}σ · 낙{nw} {nt:g}%"
        if not 걸림:
            print(f"  {이름[:14]:<16}{라규:<30}{0:>6}{'—':>10}{'—':>8}{바탕:>12.1f}%{'—':>8}   "
                  f"뒤 기간에 **한 번도 안 걸림**")
            continue
        이김 = sum(1 for z in 걸림 if z > 0) / len(걸림) * 100
        차 = 이김 - 바탕
        판 = ("✅ 그 종목 바탕보다 나음" if 차 >= 5 and len(걸림) >= 20 else
              "⚠️ 표본 적음" if len(걸림) < 20 else
              "❌ 바탕과 같거나 못함")
        print(f"  {이름[:14]:<16}{라규:<30}{len(걸림):>6}{이김:>9.1f}%{st.mean(걸림):>+8.2f}"
              f"{바탕:>12.1f}%{차:>+8.1f}   {판}")
    print("\n  ⚠️ 「이길 확률」까지다 — 한 종목만으로는 돈 시뮬이 뜻이 없다(하루 4종목 상한과 안 맞는다)")
    print("  ⚠️ 앞 기간에서 **고른** 규칙이다. 뒤에서도 좋아야 믿는다 (216차 평균은 앞 81.0% → 뒤 62.4%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
