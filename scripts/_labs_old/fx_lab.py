#!/usr/bin/env python3
r"""
fx_lab.py — **달러·엔·금이 빠졌을 때 사면?** (2026-09-03 · 67차)

⚠️⚠️ **사용자 요청.**
   *"확장하면 달러/엔/금 하락 때 사는 것도 고려하고 있어. 지금 주식 브리핑이랑 조금 다른 얘기지만!
     반영하라는게 아니고 기술적으로만 확인하고 싶어."*
   → **반영하지 않는다. 기술적 확인만 한다.**

## 자료
```
USDKRW · JPYKRW   **4,130일(16.7년)**  data/fx-daily.json  ← 오늘 680일에서 늘렸다
금(KRX 일반상품)     **649일(2.6년)**    ⚠️ KRX가 2024-01-02 이전을 안 준다 → **판단 불가**
```

## 재는 것
```
A 그냥 들고 있기 (기준선) — 환율·금을 사서 들고 있으면 얼마?
B **빠졌을 때 산다**  볼린저 하단 · N일 하락 → 다음날 사서 D+20 · D+60 보유
C **올랐을 때 산다**  (한국 주식에선 실패했다)
D 문턱 훑기
E ⚠️ **환율은 「살 수 있는 것」이 아니다** — 실제로는 달러예금·환전·ETF다.
   비용 구조가 전혀 다르다. 이 시험은 **방향성만** 본다
```
⚠️⚠️ **환율의 성격이 주식과 다르다.**
   주식은 장기 우상향이 기본값이지만 **환율은 평균회귀**에 가깝다(무한히 오르내리지 않는다).
   그래서 「빠지면 산다」가 주식보다 잘 들을 수 있다 — 그게 진짜인지 본다.
⚠️ 판정: 절대 수익 · 다음날 매수 · **날짜 단위** · 연도별 3분의 2.
⚠️ 비용은 **0.5% 왕복**으로 잡는다 (환전 스프레드는 주식 수수료보다 훨씬 비싸다).
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.5      # ⚠️ 환전 스프레드. 주식(0.26%)보다 비싸다


def 재기(수, 이름, 년수, 폭=30):
    if len(수) < 20:
        print(f"    {이름:<{폭}}표본 {len(수)} — 부족")
        return None
    승 = sum(1 for _, x in 수 if x > 0) / len(수) * 100
    v = [x for _, x in 수]
    해 = {}
    for d, x in 수:
        해.setdefault(d[:4], []).append(x)
    전 = 플 = 0
    for y, arr in 해.items():
        if len(arr) < 5:
            continue
        전 += 1
        플 += 1 if st.mean(arr) > 0 else 0
    a = sorted(v)
    별 = "⭐" if (st.mean(v) > 0 and 승 >= 60 and 전 >= 8
                 and 플 / max(1, 전) >= 2 / 3) else "  "
    print(f"    {이름:<{폭}}{st.mean(v):>+8.2f}%{승:>7.1f}%{a[len(a)//4]:>+9.2f}%"
          f"{len(수)/max(0.1,년수):>7.0f}회{f'{플}/{전}':>8}{len(수):>7}{별}")
    return st.mean(v)


def main():
    try:
        환 = json.load(io.open(os.path.join(O._DATA, "fx-daily.json"),
                               encoding="utf-8-sig"))
    except Exception as e:
        print(f"  ⚠️ fx-daily.json을 못 읽는다: {e}")
        return 1

    def 숫(x):
        try:
            return float(str(x).replace(",", ""))
        except (TypeError, ValueError):
            return None

    계열 = {}
    for 이름 in ("USDKRW", "JPYKRW"):
        a = {d: 숫(v) for d, v in (환.get(이름) or {}).items() if 숫(v)}
        if len(a) > 500:
            계열[이름] = a
    # 금 (KRX 일반상품)
    금 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-extra",
                                           "일반상품", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        rows = (d.get("자료") or {}).get("gold_bydd_trd") or []
        if rows:
            v = 숫(rows[0].get("TDD_CLSPRC"))
            if v:
                금[d.get("기준일")] = v
    if len(금) > 300:
        계열["금(KRX)"] = 금

    print("  ══ 자료 ══")
    for n, a in 계열.items():
        k = sorted(a)
        print(f"    {n:<12}{k[0]} ~ {k[-1]} · {len(a):,}일 "
              f"({len(a)/245:.1f}년)"
              + ("   ⚠️ **2.6년뿐 — 판단 불가**" if len(a) < 1000 else ""))

    for 이름, a in 계열.items():
        k = sorted(a)
        v = [a[d] for d in k]
        년수 = len(k) / 245
        print(f"\n  ══════ {이름} ══════")
        # A 기준선
        해별 = {}
        for j in range(1, len(k)):
            해별.setdefault(k[j][:4], []).append(v[j] / v[j - 1] - 1)
        연 = ((v[-1] / v[0]) ** (1 / 년수) - 1) * 100
        최고, 낙폭 = v[0], 0.0
        for x in v:
            최고 = max(최고, x)
            낙폭 = min(낙폭, x / 최고 - 1)
        print(f"    A 그냥 들고 있기   연 {연:+.2f}% · 최대낙폭 {낙폭*100:.1f}% "
              f"· {v[0]:,.1f} → {v[-1]:,.1f}")

        머 = (f"    {'조합':<30}{'평균':>9}{'승률':>8}{'하위25%':>10}"
              f"{'연간':>8}{'연도별':>8}{'표본':>7}")
        for 보유 in (20, 60):
            print(f"\n    ── D+{보유} 보유 ──")
            print(머)
            # 기준선: 아무 날이나 사서 D+보유
            수 = [(k[i], (v[i + 보유] / v[i] - 1) * 100 - _비용)
                  for i in range(20, len(k) - 보유)]
            재기(수, "아무 날이나 산다 (기준선)", 년수)
            for 볼문, r문, 라 in ((-1.0, -3, "볼≤-1.0 · 20일 -3%↓"),
                                  (-1.5, -5, "볼≤-1.5 · 20일 -5%↓"),
                                  (-2.0, -5, "볼≤-2.0 · 20일 -5%↓"),
                                  (-1.0, -1, "볼≤-1.0 · 20일 -1%↓")):
                수 = []
                for i in range(20, len(k) - 보유):
                    s20 = st.mean(v[i - 19:i + 1])
                    sd = st.pstdev(v[i - 19:i + 1]) or 1e-9
                    볼 = (v[i] - s20) / (2 * sd)
                    r20 = (v[i] / v[i - 20] - 1) * 100
                    if 볼 <= 볼문 and r20 <= r문:
                        수.append((k[i], (v[i + 보유] / v[i] - 1) * 100 - _비용))
                재기(수, f"**빠졌을 때** {라}", 년수)
            for 볼문, r문, 라 in ((1.0, 3, "볼≥+1.0 · 20일 +3%↑"),
                                  (1.5, 5, "볼≥+1.5 · 20일 +5%↑")):
                수 = []
                for i in range(20, len(k) - 보유):
                    s20 = st.mean(v[i - 19:i + 1])
                    sd = st.pstdev(v[i - 19:i + 1]) or 1e-9
                    볼 = (v[i] - s20) / (2 * sd)
                    r20 = (v[i] / v[i - 20] - 1) * 100
                    if 볼 >= 볼문 and r20 >= r문:
                        수.append((k[i], (v[i + 보유] / v[i] - 1) * 100 - _비용))
                재기(수, f"올랐을 때 {라}", 년수)

    print("\n  읽는 법")
    print("    - **「빠졌을 때」가 기준선보다 나아야** 신호로 쓸 값어치가 있다")
    print("    - ⚠️ 환율은 **평균회귀**에 가깝다(무한히 오르내리지 않는다).")
    print("       그래서 「빠지면 산다」가 주식보다 잘 들을 수 있다")
    print("    - ⚠️⚠️ **환율은 「살 수 있는 것」이 아니다.** 실제로는 달러예금·환전·ETF다.")
    print("       비용 구조가 다르다 — 여기선 왕복 0.5%로 잡았다. 방향성만 본다")
    print("    - ⚠️ 금은 **2.6년뿐**이다(KRX가 2024-01-02 이전을 안 준다) → 판단 불가")
    return 0


if __name__ == "__main__":
    sys.exit(main())
