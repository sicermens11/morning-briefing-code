#!/usr/bin/env python3
r"""
trait_lab.py — **205차 · 종목 성격별 규칙** (2026-09-10 신설)

## 사용자 말 (그대로)
```
「내 말한 다양한 규칙을 만들어서 **규모나 섹터나, 종목에 맞춰서** 하고, 다음 많은 기회를 찾고」
```
=> 지금까지 **규모·섹터**만 쟀다. **종목**은 한 번도 안 했다.
   「둘 다」로 답하셔서 **성격별(205차)** 과 **개별 종목별(206차)** 을 차례로 한다

## 판정 기준 (먼저 밝힌다 — [[judge-criteria-need-user-check]])
```
① **최근 3년(2023~)에도 통하는가**   <- 204차에서 재료 대부분이 무너졌다. 첫 관문
② OR 로 더했을 때 **기회가 늘고**(100%↑) 승률이 **안 떨어지는가**(-0.5%p 이내)
③ **앞 8년에서 찾아 뒤 8년에** 통하는가  <- 203차 규모 규칙이 여기서 탈락했다
```

## ⚠️ 204차에서 알아낸 것 — 이 시험의 전제
```
지금 규칙 자체가 ~2022 **56.4%** -> 2023~ **53.0%** (-3.3%p)
재료별로는 더 심하다:
  낙20 -30%   63.0% -> **40.4%**  (-22.5%p)   <- 아무 날(43.5%)보다 나쁘다
  낙20 -20%   58.5% -> **43.0%**  (-15.5%p)
  볼120 -1.5σ 68.1% -> **52.6%**  (-15.5%p)
  낙60 -30%   60.0% -> **47.9%**  (-12.1%p)
  ⭐ **볼20 -1.5σ  52.0% -> 59.7%  (+7.7%p)**   <- 유일하게 좋아졌다
=> **「많이 빠진 것을 산다」가 최근에 안 통한다.** 깊을수록 더 나쁘다
   그래서 이 시험은 **최근 3년을 먼저 본다**
```

쓰는 법:
    python scripts\trait_lab.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_시작 = "20100104"
_최소 = 300


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = [d for d in sorted(주가) if d >= _시작]
    print(f"  거래일 {len(날):,}일 · {날[0]} ~ {날[-1]}", flush=True)

    계열, 있는날 = {}, {}
    for i, d in enumerate(날):
        for c, v in 주가[d].items():
            계열.setdefault(c, []).append(v)
            있는날.setdefault(c, []).append(i)

    print("  사건 만드는 중 (볼-0.5σ 또는 -5% 만)...", flush=True)
    사건 = []
    for c, vs in 계열.items():
        ii = 있는날[c]
        종 = [z[0] for z in vs]
        for k in range(120, len(vs)):
            시총억 = vs[k][1] / 1e8
            대금억 = vs[k][2] / 1e8
            if 시총억 < 100 or 대금억 < 1.0:
                continue
            c1 = 종[k]
            m20, sd20 = O.창평균표준(종, k, 20)
            볼20 = ((c1 - m20) / (2 * sd20)) if sd20 else None
            낙20 = (c1 / 종[k - 20] - 1) * 100
            # ⚠️ 램 — 만들 때부터 좁힌다
            if not ((볼20 is not None and 볼20 <= -0.5) or 낙20 <= -5):
                continue
            i = ii[k]
            j = i + 20
            if j >= len(날):
                continue
            끝 = 주가[날[j]].get(c)
            뒤 = (O.폐지손실 if not 끝 else (끝[0] / c1 - 1) * 100)
            m60, sd60 = O.창평균표준(종, k, 60)
            m120, sd120 = O.창평균표준(종, k, 120)
            # ⭐ 종목 성격 — 그 시점까지의 20일 하루 등락
            일 = []
            for z in range(k - 19, k + 1):
                앞 = 종[z - 1]
                if 앞 > 0:
                    일.append(종[z] / 앞 - 1)
            _, 일sd = O.빠른평균표준(일) if len(일) >= 15 else (0, 0)
            사건.append({
                "code": c, "해": 날[i][:4], "_인": i,
                "시총억": 시총억, "대금억": 대금억,
                "볼20": 볼20,
                "볼60": ((c1 - m60) / (2 * sd60)) if sd60 else None,
                "볼120": ((c1 - m120) / (2 * sd120)) if sd120 else None,
                "낙20": 낙20,
                "낙60": (c1 / 종[k - 60] - 1) * 100 if k >= 60 else None,
                "낙120": (c1 / 종[k - 120] - 1) * 100 if k >= 120 else None,
                "_20": 뒤,
                # ⭐ 성격 넷
                "변동": 일sd * (252 ** 0.5) * 100 if 일sd else None,
                "회전율": (대금억 / 시총억 * 100) if 시총억 > 0 else 0,
                "주가": c1,
            })
    print(f"  사건 {len(사건):,}건", flush=True)

    # ── 성격 칸 나누기 (그날 그 성격의 분위수로) ──
    성격들 = (("변동성", "변동"), ("거래대금", "대금억"),
              ("회전율", "회전율"), ("주가대", "주가"))
    for 라, k2 in 성격들:
        하루 = {}
        for x in 사건:
            if x.get(k2) is not None:
                하루.setdefault(x["_인"], []).append(x)
        for 칸 in 하루.values():
            if len(칸) < 9:
                for x in 칸:
                    x[f"칸_{라}"] = None
                continue
            칸.sort(key=lambda z: z[k2])
            n = len(칸)
            for j, x in enumerate(칸):
                x[f"칸_{라}"] = ("낮은 쪽" if j < n / 3
                                else ("가운데" if j < n * 2 / 3 else "높은 쪽"))
    print("  성격 넷을 셋씩 나눴다", flush=True)

    해수 = max(len({x["해"] for x in 사건}), 1)

    def 셈(칸, 최소=None):
        v = [z["_20"] for z in 칸 if z.get("_20") is not None]
        if len(v) < (최소 or _최소):
            return None
        return (len(v), len(v) / 해수,
                sum(1 for z in v if z > 0) / len(v) * 100, sum(v) / len(v))

    def 지금(x):
        return (x["볼20"] is not None and x["볼20"] <= -1.0
                and x["낙20"] <= -10.0 and 300 <= x["시총억"] < 2000)

    격자 = [(f"볼{bw}", bt, f"낙{nw}", nt)
            for bw in (20, 60, 120) for bt in (-0.5, -1.0, -1.5, -2.0)
            for nw in (20, 60, 120) for nt in (-5, -10, -20, -30)]

    def 맞나(x, 규):
        bk, bt, nk, nt = 규
        b, n = x.get(bk), x.get(nk)
        return (b is not None and b <= bt and n is not None and n <= nt)

    def 제일좋은(칸, 기회밑=None, 최소=None):
        좋 = None
        for 규 in 격자:
            추 = [x for x in 칸 if 맞나(x, 규)]
            r = 셈(추, 최소)
            if not r:
                continue
            if 기회밑 is not None and r[0] < 기회밑:
                continue
            if 좋 is None or r[2] > 좋[1][2]:
                좋 = (규, r)
        return 좋

    def 규글(규):
        bk, bt, nk, nt = 규
        return f"{bk}일 {bt:+.1f}σ · {nk}일 {nt}%"

    print("\n" + "=" * 104)
    print("  205차 · **종목 성격별 규칙**")
    print("  사용자: 「규모나 섹터나, **종목에 맞춰서** 하고, 다음 많은 기회를 찾고」")
    print("  ⚠️ 판정 기준 ① 최근 3년에도 통하나 ② OR 로 더해 기회가 느나"
          " ③ 앞에서 찾아 뒤에 통하나")
    print("=" * 104)

    머 = f"  {'':<34}{'건수':>9}{'1년에':>8}{'이김':>9}{'평균':>9}"

    def 줄(라, r, 꼬="", 폭=34):
        if not r:
            print(f"  {라:<{폭}}{'표본 부족':>28}")
            return
        print(f"  {라:<{폭}}{r[0]:>9,}{r[1]:>8.0f}{r[2]:>8.1f}%{r[3]:>+9.2f}{꼬}")

    지 = [x for x in 사건 if 지금(x)]
    지최근 = [x for x in 지 if x["해"] >= "2023"]
    r지, r지최 = 셈(지), 셈(지최근)
    print(f"\n  ── A 견줄 자리 ──")
    print(머)
    줄("지금 규칙 (전 기간)", r지)
    줄("지금 규칙 (**2023~**)", r지최)

    # ══ B 성격 칸마다 규칙 ══
    print("\n  ── B ⭐ **성격 칸마다 규칙** (재료는 둘, 창·문턱만) ──")
    print(f"  {'성격':<10}{'칸':<8}{'지금 규칙':<16}{'그 칸의 규칙':<26}"
          f"{'1년에':>7}{'이김':>8}{'기회':>7}")
    _칸규칙 = {}
    for 라, _ in 성격들:
        for 칸이름 in ("낮은 쪽", "가운데", "높은 쪽"):
            칸 = [x for x in 사건 if x.get(f"칸_{라}") == 칸이름]
            지칸 = [x for x in 칸 if 지금(x)]
            밑 = len(지칸)
            r0 = 셈(지칸)
            지말 = (f"1년 {r0[1]:.0f}개 {r0[2]:.0f}%" if r0 else "표본 부족")
            좋 = 제일좋은(칸, 기회밑=밑 * 0.5) if 밑 >= _최소 else None
            if not 좋:
                print(f"  {라:<10}{칸이름:<8}{지말:<16}{'없다':<26}")
                continue
            규, r = 좋
            _칸규칙[(라, 칸이름)] = 규
            print(f"  {라:<10}{칸이름:<8}{지말:<16}{규글(규):<26}"
                  f"{r[1]:>7.0f}{r[2]:>7.1f}%{r[0]/밑*100:>6.0f}%")

    # ══ C 최근 3년에도 통하나 ══
    print("\n  ── C ⭐⭐ **최근 3년(2023~)에도 통하나** ──")
    print("     ⚠️ 204차: 지금 규칙이 56.4% -> 53.0% · 낙20 -30% 는 63.0% -> **40.4%**")
    print(f"  {'성격':<10}{'칸':<8}{'그 칸의 규칙':<26}{'~2022':>9}{'2023~':>9}{'차이':>8}")
    _살아남음 = {}
    for (라, 칸이름), 규 in _칸규칙.items():
        칸 = [x for x in 사건 if x.get(f"칸_{라}") == 칸이름 and 맞나(x, 규)]
        r1 = 셈([x for x in 칸 if x["해"] <= "2022"], 100)
        r2 = 셈([x for x in 칸 if x["해"] >= "2023"], 100)
        if not r1 or not r2:
            print(f"  {라:<10}{칸이름:<8}{규글(규):<26}{'표본 부족':>26}")
            continue
        차 = r2[2] - r1[2]
        표 = "  ⭐" if 차 >= -2 else "  ⚠️"
        if 차 >= -2:
            _살아남음[(라, 칸이름)] = 규
        print(f"  {라:<10}{칸이름:<8}{규글(규):<26}"
              f"{r1[2]:>8.1f}%{r2[2]:>8.1f}%{차:>+7.1f}p{표}")
    print(f"\n     ⇒ **최근에도 살아남은 칸 {len(_살아남음)}개** / {len(_칸규칙)}개")

    # ══ D 앞에서 찾아 뒤에 ══
    print("\n  ── D ⭐⭐ **앞 8년에서 찾아 뒤 8년에** (과적합 확인) ──")
    가 = 날[len(날) // 2][:4]
    print(f"     앞 ~{가} · 뒤 {가}~")
    print(f"  {'성격':<10}{'칸':<8}{'앞에서 찾은 규칙':<26}{'앞':>9}{'뒤':>9}{'차이':>8}")
    _D통과 = {}
    for 라, _ in 성격들:
        for 칸이름 in ("낮은 쪽", "가운데", "높은 쪽"):
            칸앞 = [x for x in 사건
                    if x.get(f"칸_{라}") == 칸이름 and x["해"] < 가]
            칸뒤 = [x for x in 사건
                    if x.get(f"칸_{라}") == 칸이름 and x["해"] >= 가]
            밑앞 = len([x for x in 칸앞 if 지금(x)])
            if 밑앞 < 100:
                continue
            좋 = 제일좋은(칸앞, 기회밑=밑앞 * 0.5, 최소=100)
            if not 좋:
                continue
            규, r앞 = 좋
            r뒤 = 셈([x for x in 칸뒤 if 맞나(x, 규)], 100)
            if not r뒤:
                print(f"  {라:<10}{칸이름:<8}{규글(규):<26}{r앞[2]:>8.1f}%"
                      f"{'뒤 표본 부족':>18}")
                continue
            차 = r뒤[2] - r앞[2]
            표 = "  ✅" if 차 >= -3 else "  ❌"
            if 차 >= -3:
                _D통과[(라, 칸이름)] = 규
            print(f"  {라:<10}{칸이름:<8}{규글(규):<26}"
                  f"{r앞[2]:>8.1f}%{r뒤[2]:>8.1f}%{차:>+7.1f}p{표}")
    print(f"\n     ⇒ **앞뒤 검증 통과 {len(_D통과)}개**")

    # ══ E OR 로 더하면 ══
    print("\n  ── E ⭐⭐ **기존 OR 성격규칙** — 더하면 ──")
    print("     ⚠️ D 를 통과한 것만 더한다 (앞에서 찾아 뒤에 통한 것)")

    def 성격맞나(x, 표):
        for (라, 칸이름), 규 in 표.items():
            if x.get(f"칸_{라}") == 칸이름 and 맞나(x, 규):
                return True
        return False

    print(머)
    줄("기존 규칙만", r지)
    for 이름, 표 in (("D 통과분", _D통과), ("최근에도 살아남은 것", _살아남음)):
        if not 표:
            print(f"  {'기존 OR ' + 이름:<34}{'해당 없음':>28}")
            continue
        칸 = [x for x in 사건 if 지금(x) or 성격맞나(x, 표)]
        r = 셈(칸)
        꼬 = ""
        if r and r지:
            기 = r[0] / r지[0] * 100
            차 = r[2] - r지[2]
            꼬 = f"{기:>7.0f}%{차:>+7.1f}p" + ("  ⭐" if (기 >= 100 and 차 >= -0.5) else "")
        줄(f"⭐ 기존 OR {이름}", r, 꼬)
    # 최근 3년만 따로
    print()
    for 이름, 표 in (("D 통과분", _D통과),):
        if not 표:
            continue
        칸최 = [x for x in 사건
                if x["해"] >= "2023" and (지금(x) or 성격맞나(x, 표))]
        r = 셈(칸최)
        꼬 = ""
        if r and r지최:
            기 = r[0] / r지최[0] * 100
            차 = r[2] - r지최[2]
            꼬 = f"{기:>7.0f}%{차:>+7.1f}p" + ("  ⭐" if (기 >= 100 and 차 >= -0.5) else "")
        줄(f"**2023~** 기존 OR {이름}", r, 꼬)

    print("\n" + "=" * 104)
    print("  읽는 법")
    print("    - **C 가 첫 관문이다** — 최근 3년에 무너진 규칙은 지금 쓸 수 없다")
    print("    - D 는 과적합 확인이다. C 와 D 를 **둘 다** 통과해야 진짜다")
    print("    - E 의 ⭐ 는 **기회가 늘고 승률이 안 떨어진** 것이다")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "_labs",
                      os.environ.get("LAB_OUT")
                      or "2026-09-10_205차_종목성격별규칙.txt")

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
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
