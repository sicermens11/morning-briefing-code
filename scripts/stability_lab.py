#!/usr/bin/env python3
r"""
stability_lab.py — **신호가 시간이 지나도 사나 · 기술지표 전체 검증** (2026-09-01 신설)

⚠️⚠️⚠️ **가장 중요한 질문: 이 신호가 「지금도」 사는가.**
   규칙이 2024엔 좋고 2026엔 나쁘면 **이미 죽은 신호**다. 그런데 지금까지
   **어느 시험도 시간에 따라 갈라 보지 않았다** — 전 기간을 뭉쳐 하나의 평균을 냈다.
```
반기별로 가른다   2024상 · 2024하 · 2025상 · 2025하 · 2026상 · 2026하
신호가 살아 있으면  반기마다 부호가 같아야 한다
최근 반기에서 죽었으면  **이미 알려져서 사라진 것**일 수 있다
```

⚠️⚠️ **기술지표를 처음으로 전부 넣는다.** `compute_ta.py`에 12개 이상이 있는데
   `omni_lab`엔 급등·급락·무반응 3개뿐이었다.
   ⚠️ **여기서는 네트워크를 안 쓰고 `krx-daily`로 직접 계산**한다 — 과거 소급이 목적이라
      그날그날의 값이 필요하기 때문이다.
```
20일선·60일선 이격 · RSI14 · ATR14(변동성) · 볼린저 위치 · 거래량비율(20일 평균 대비)
· 52주 신고가 돌파 · 상대강도(20일, 시장 대비) · 연속 상승일
```

⚠️ 매수 D+1 종가(look-ahead 회피) · 실제 지수 대비 초과수익 · 표본 명시.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 5, 20)
_MIN = 80


def _반기(d8):
    y, m = d8[:4], int(d8[4:6])
    return f"{y}{'상' if m <= 6 else '하'}"


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    print(f"  기술지표를 krx-daily로 직접 계산한다 (네트워크 안 씀)", flush=True)

    # 종목별 종가 시계열을 한 번 만든다 (지표 계산용)
    계 = {}
    for d in 날:
        for c, v in 주가[d].items():
            계.setdefault(c, []).append((d, v[0], v[3]))     # (날, 종가, 등락률)
    자리 = {c: {d: i for i, (d, _, _) in enumerate(v)} for c, v in 계.items()}
    print(f"  종목 {len(계):,}개 시계열 준비", flush=True)

    통 = {}

    def 담(축, 라, 반, h, v):
        s = 통.setdefault((축, 라, 반, h), [0.0, 0])
        s[0] += v
        s[1] += 1

    for i, d1 in enumerate(날):
        if i + 1 >= len(날):
            break
        a0 = 지수.get(날[i + 1])
        if not a0:
            continue
        반 = _반기(d1)
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        # 시장 20일 수익률(상대강도 기준)
        시20 = None
        if i >= 20 and 지수.get(날[i - 20]):
            시20 = 지수[d1]["KOSPI"] / 지수[날[i - 20]]["KOSPI"] - 1

        for code, v1 in s1.items():
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            매수v = 주가[날[i + 1]].get(code)
            if 매수v is None:
                continue
            seq = 계.get(code)
            k = (자리.get(code) or {}).get(d1)
            if seq is None or k is None or k < 60:
                continue
            종가들 = [x[1] for x in seq[max(0, k - 250):k + 1]]
            등락들 = [x[2] for x in seq[max(0, k - 20):k + 1]]
            if len(종가들) < 60:
                continue
            s20 = st.mean(종가들[-20:])
            s60 = st.mean(종가들[-60:])
            이격20 = (c1 / s20 - 1) * 100
            이격60 = (c1 / s60 - 1) * 100
            # RSI14
            변 = [종가들[j] - 종가들[j - 1] for j in range(len(종가들) - 14, len(종가들))]
            상 = st.mean([max(0, x) for x in 변]) or 1e-9
            하 = st.mean([max(0, -x) for x in 변]) or 1e-9
            rsi = 100 - 100 / (1 + 상 / 하)
            # 볼린저 위치
            sd = st.pstdev(종가들[-20:]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            # 변동성(20일 등락 표준편차)
            변동 = st.pstdev(등락들) if len(등락들) >= 5 else 0
            # 52주 신고가 대비
            고 = max(종가들)
            신고 = c1 >= 고 * 0.999
            # 상대강도(20일)
            rs = None
            if 시20 is not None and len(종가들) > 20:
                rs = (c1 / 종가들[-21] - 1) - 시20
            # 연속 상승
            연 = 0
            for x in reversed(등락들):
                if x > 0:
                    연 += 1
                else:
                    break

            라벨 = [
                ("20일선", "위 5%↑" if 이격20 >= 5 else ("아래 5%↓" if 이격20 <= -5 else "±5% 안")),
                ("60일선", "위" if 이격60 > 0 else "아래"),
                ("RSI14", "70↑ 과매수" if rsi >= 70 else ("30↓ 과매도" if rsi <= 30 else "30~70")),
                ("볼린저", "상단 밖" if 볼 >= 1 else ("하단 밖" if 볼 <= -1 else "밴드 안")),
                ("변동성", "높음(3%↑)" if 변동 >= 3 else ("낮음(1%↓)" if 변동 < 1 else "보통")),
                ("신고가", "52주 신고가" if 신고 else "아님"),
                ("연속상승", f"{min(연,4)}일" if 연 <= 4 else "5일↑"),
            ]
            if rs is not None:
                라벨.append(("상대강도20", "시장 대비 강함" if rs > 0.05 else
                             ("약함" if rs < -0.05 else "비슷")))
            r = ds.get(code) or {}
            if "호재" in r.get("성격", set()):
                라벨.append(("신호", "호재 공시"))
                if r.get("분") is not None and r["분"] >= 930:
                    라벨.append(("신호", "갭① 호재+장후"))
                    if abs(등락) < 1:
                        라벨.append(("신호", "갭①④ +무반응"))
            f = fl.get(code) or {}
            if (f.get("외국인") or 0) > 0 and (f.get("기관") or 0) > 0:
                라벨.append(("신호", "갭③ 수급"))

            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            매수가 = 매수v[0]
            for h in _H:
                j = i + 1 + h
                if j >= len(날) or not 지수.get(날[j]):
                    continue
                vv = 주가[날[j]].get(code)
                if not vv:
                    continue
                초 = ((vv[0] / 매수가 - 1) - (지수[날[j]][장] / a0[장] - 1)) * 100
                for 축, 라 in 라벨:
                    담(축, 라, "전체", h, 초)
                    담(축, 라, 반, h, 초)
        if i % 100 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    반기들 = sorted({b for _, _, b, _ in 통 if b != "전체"})
    축들 = []
    for a, b, _, _ in 통:
        if (a, b) not in 축들:
            축들.append((a, b))
    현 = None
    for 축, 라 in 축들:
        if 축 != 현:
            현 = 축
            print(f"\n  ══════ {축} ══════")
            print(f"    {'':<18}{'구간':<8}" + "".join(f"{'D+'+str(h):>15}" for h in _H))
        for 반 in ["전체"] + 반기들:
            칸 = []
            for h in _H:
                s = 통.get((축, 라, 반, h))
                칸.append(f"{s[0]/s[1]:+.2f}({s[1]:,})" if s and s[1] >= _MIN else "—")
            if all(c == "—" for c in 칸):
                continue
            print(f"    {라 if 반=='전체' else '':<18}{반:<8}"
                  + "".join(f"{c:>15}" for c in 칸))
    print("\n  ⚠️⚠️ **반기마다 부호가 뒤집히면 그 신호는 못 쓴다.**")
    print("     특히 **최근 반기(2026상·2026하)에서 죽었으면 이미 알려져 사라진 것**일 수 있다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
