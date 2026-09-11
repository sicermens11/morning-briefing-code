#!/usr/bin/env python3
r"""
crash_days.py — **시장이 -10% 넘게 빠진 날이 1년에 며칠인가** (2026-09-09)

## 왜
```
170차에서 「시장이 -10%↓ 빠진 날만 산다」가 4관문을 통과했다 (네 구간 +19.6~34.0%p).
그런데 **그런 날이 1년에 며칠인지**를 안 세어봤다.
며칠 안 되면 「평소엔 아예 안 사는 규칙」이 된다 —
사용자 원칙 ④(매수 기회 포착이 먼저)와 정면으로 부딪친다
```

쓰는 법:
    python scripts\crash_days.py
"""
import collections
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402


def main():
    # 지수 읽기
    지수 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        하루 = {}
        for 이름, v in (d.get("지수") or {}).items():
            try:
                하루[이름] = float(str(v.get("종가")).replace(",", ""))
            except (TypeError, ValueError, AttributeError):
                pass
        if 하루:
            지수[d.get("기준일") or os.path.basename(f)[:8]] = 하루
    날 = sorted(지수)
    print(f"  지수 {len(날):,}일")

    for 이름 in ("코스닥", "코스피"):
        계 = [지수[d].get(이름) for d in 날]
        해별낙 = collections.defaultdict(list)
        for i in range(20, len(계)):
            a, b = 계[i - 20], 계[i]
            if not a or not b:
                continue
            해별낙[날[i][:4]].append((b / a - 1) * 100)
        print(f"\n  ══ {이름} 20일 낙폭 ══")
        print(f"  {'해':<8}{'거래일':>7}{'-5%↓':>8}{'-10%↓':>8}"
              f"{'-15%↓':>8}{'-20%↓':>8}{'가장나쁨':>10}")
        총 = collections.Counter()
        for 해 in sorted(해별낙):
            v = 해별낙[해]
            c5 = sum(1 for z in v if z <= -5)
            c10 = sum(1 for z in v if z <= -10)
            c15 = sum(1 for z in v if z <= -15)
            c20 = sum(1 for z in v if z <= -20)
            총["일"] += len(v)
            총["5"] += c5
            총["10"] += c10
            총["15"] += c15
            총["20"] += c20
            print(f"  {해:<8}{len(v):>7}{c5:>8}{c10:>8}{c15:>8}{c20:>8}"
                  f"{min(v):>9.1f}%")
        n = 총["일"] or 1
        print(f"  {'합':<8}{n:>7}{총['5']:>8}{총['10']:>8}"
              f"{총['15']:>8}{총['20']:>8}")
        print(f"  {'비율':<8}{'':>7}{총['5']/n*100:>7.1f}%{총['10']/n*100:>7.1f}%"
              f"{총['15']/n*100:>7.1f}%{총['20']/n*100:>7.1f}%")
        해수 = len(해별낙) or 1
        print(f"\n  ⇒ 1년 평균  -5%↓ **{총['5']/해수:.0f}일** · "
              f"-10%↓ **{총['10']/해수:.0f}일** · "
              f"-15%↓ {총['15']/해수:.0f}일 · -20%↓ {총['20']/해수:.0f}일")

    print("\n" + "=" * 78)
    print("  읽는 법")
    print("    - 「시장이 -10%↓ 빠진 날만 산다」면 **1년에 그 날수만큼만** 살 수 있다")
    print("    - 그 날들은 **몰려서 온다** (폭락은 며칠씩 이어진다)")
    print("      -> 어떤 해는 60일, 어떤 해는 0일일 수 있다")
    print("    - 문턱을 -5% 로 낮추면 날이 몇 배 되는지 같이 본다")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT") or "2026-09-09_178차_폭락일수.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
