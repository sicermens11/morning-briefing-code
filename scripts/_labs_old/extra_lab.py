#!/usr/bin/env python3
r"""
extra_lab.py — **받아놓고 한 번도 안 쓴 데이터 넷** (2026-09-02 · 40차)

⚠️⚠️ 사용자: *"테스트해서 유의미한 결과가 안 나오더라도 뭔가 발견한 게 있으면 좋은 거니까,
   그런 측면에서 테스트 많이 해"*
   → 받아만 놓고 **한 번도 안 쓴 데이터**부터 훑는다. 가장 큰 미탐색 영역이다.

## 넣는 것 넷
```
① 계약금액       contract  2024-01~2026-09 · 10,378건 · **매출대비%**가 있다
   ⚠️ 37차에서 「수주계약 대형 D+20·60일 +14.85%(승률 59%)」가 나왔는데
      지금은 **매출의 1%짜리와 50%짜리가 같은 취급**이다. 규모로 가른다
② 임원 자사주매매  dart-exec  2024-09~2026-09 (**2년뿐**) — 내부자 거래. 유명한 신호인데 안 썼다
③ 대주주 지분변동  dart-major 2024-09~2026-09 (2년)
④ 컨센서스       consensus  2024-01~2026-09 · 목표주가·투자의견
   → **목표주가 대비 현재가 괴리율**로 가른다
```

⚠️⚠️ **기간이 2~2.7년뿐이라 학습/검증 분리를 못 한다.** 전부 **예비 결과**다.
   그래도 방향과 표본 크기는 알 수 있고, 어느 쪽을 더 파야 하는지 정할 수 있다.
⚠️ 판정은 **절대 수익 + 승률**(35차 기준). 왕복비용 0.26% 차감.
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_진입들 = (1, 3, 10, 20)
_보유들 = (20, 60)
크기표 = [("소형", 0, 3e11), ("중형", 3e11, 1e12), ("대형", 1e12, 9e99)]


def _크기(시총):
    for 이름, a, b in 크기표:
        if a <= 시총 < b:
            return 이름
    return 크기표[-1][0]


def _숫(x):
    try:
        return float(str(x).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def main():
    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    날인덱스 = {d: i for i, d in enumerate(날)}
    print(f"  거래일 {len(날):,}", flush=True)

    def 인덱스(문자열):
        """'2024-09-03' 또는 '20240903' → 그날 이후 첫 거래일 인덱스."""
        s = str(문자열 or "").replace("-", "")
        if len(s) != 8:
            return None
        i = 날인덱스.get(s)
        if i is not None:
            return i
        for d in 날:
            if d >= s:
                return 날인덱스[d]
        return None

    사건 = {}      # 라벨 -> [(i, code, 크기)]

    def 담(라벨, i, code):
        if i is None or i < 250 or i + 1 + max(_진입들) + max(_보유들) >= len(날):
            return
        v = 주가[날[i]].get(code)
        if not v or v[1] < O._MIN_MC or v[2] < O._MIN_AMT:
            return
        사건.setdefault(라벨, []).append((i, code, _크기(v[1])))

    # ── ① 계약금액 ──
    n계약 = 0
    for f in sorted(glob.glob(os.path.join(O._DATA, "contract", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for _, v in (d.get("건") or {}).items():
            code, 날짜 = v.get("코드"), v.get("날짜")
            pct = _숫(v.get("매출대비pct"))
            if not code or pct is None:
                continue
            i = 인덱스(날짜)
            라 = ("계약 0~5%" if pct < 5 else "계약 5~15%" if pct < 15 else
                  "계약 15~30%" if pct < 30 else "계약 30~100%" if pct < 100 else
                  "계약 100%↑")
            담(라, i, code)
            담("계약 전체", i, code)
            n계약 += 1

    # ── ② 임원 자사주매매 ──
    n임원 = 0
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-exec", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        code = d.get("종목")
        묶 = {}
        for x in (d.get("이력") or []):
            증 = _숫(x.get("증감"))
            날짜 = x.get("접수일")
            if 증 is None or not 날짜:
                continue
            묶.setdefault(날짜, []).append((증, str(x.get("직위") or "")))
        for 날짜, a in 묶.items():
            합 = sum(x for x, _ in a)
            i = 인덱스(날짜)
            대표 = any(("대표" in p or "회장" in p or "사장" in p) for _, p in a)
            # ⚠️⚠️ **「가벼운 방법으로 충분한가」를 여기서 답한다** (사용자 질문).
            #   임원 소유보고는 매수·매도·상속·스톡옵션 행사·증여가 **같은 서식**으로 나온다.
            #   공시 목록만 받으면(가벼운 방법) 이게 다 섞인다.
            #   → 「방향 무시 전체」와 「순매수/순매도」를 **나란히 재서** 갈리는지 본다.
            #     크게 갈리면 문서 파싱(정확한 방법)이 필요하고, 안 갈리면 목록만으로 충분하다.
            담("임원 소유보고 전체(방향무시)", i, code)
            if 합 > 0:
                담("임원 순매수", i, code)
                if 대표:
                    담("임원 순매수(대표·회장)", i, code)
                if len(a) >= 3:
                    담("임원 순매수(3인↑)", i, code)
            elif 합 < 0:
                담("임원 순매도", i, code)
            n임원 += 1

    # ── ③ 대주주 지분변동 ──
    n대주 = 0
    for f in sorted(glob.glob(os.path.join(O._DATA, "dart-major", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        code = d.get("종목")
        for x in (d.get("이력") or []):
            지 = _숫(x.get("지분율"))
            직 = _숫(x.get("직전지분율"))
            i = 인덱스(x.get("접수일"))
            if 지 is None or 직 is None:
                continue
            n대주 += 1
            차 = 지 - 직
            if 차 >= 1.0:
                담("대주주 지분 +1%p↑", i, code)
            elif 차 <= -1.0:
                담("대주주 지분 −1%p↓", i, code)

    # ── ④ 컨센서스 ──
    n컨 = 0
    for f in sorted(glob.glob(os.path.join(O._DATA, "consensus", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for x in (d.get("리포트") or []):
            code = x.get("코드")
            목 = _숫(x.get("목표주가"))
            i = 인덱스(x.get("날짜"))
            if not code or i is None:
                continue
            n컨 += 1
            v = 주가[날[i]].get(code)
            if not v:
                continue
            담("리포트 전체", i, code)
            if 목 and 목 > 0:
                괴 = (목 / v[0] - 1) * 100
                라 = ("괴리 0%↓(목표가 아래)" if 괴 < 0 else
                      "괴리 0~20%" if 괴 < 20 else
                      "괴리 20~50%" if 괴 < 50 else "괴리 50%↑")
                담(라, i, code)
            의 = str(x.get("의견") or "")
            if "매수" in 의 or "Buy" in 의 or "BUY" in 의:
                담("의견 매수", i, code)
    print(f"  원자료: 계약 {n계약:,} · 임원 {n임원:,} · 대주주 {n대주:,} · 리포트 {n컨:,}",
          flush=True)
    print(f"  사건 {len(사건)}종 · 총 {sum(len(v) for v in 사건.values()):,}건", flush=True)

    def 성과(목록, 진입, 보유):
        a = []
        for (i, code, g) in 목록:
            j, e = i + 진입, i + 진입 + 보유
            if e >= len(날):
                continue
            m = 주가[날[j]].get(code)
            x = 주가[날[e]].get(code)
            if m and x:
                a.append((x[0] / m[0] - 1) * 100 - _비용)
        return a

    순서 = ["계약 전체", "계약 0~5%", "계약 5~15%", "계약 15~30%", "계약 30~100%",
            "계약 100%↑", "임원 소유보고 전체(방향무시)", "임원 순매수",
            "임원 순매수(대표·회장)", "임원 순매수(3인↑)",
            "임원 순매도", "대주주 지분 +1%p↑", "대주주 지분 −1%p↓",
            "리포트 전체", "의견 매수", "괴리 0%↓(목표가 아래)", "괴리 0~20%",
            "괴리 20~50%", "괴리 50%↑"]
    순서 = [x for x in 순서 if x in 사건]

    print(f"\n  ══ 전체 (크기 구분 없이) — 진입일 × 보유 (절대 수익 · 승률) ══")
    print("     ⚠️ **기간이 2~2.7년뿐이라 전부 예비 결과다**")
    for 보유 in _보유들:
        print(f"\n  ── {보유}일 보유 ──")
        print(f"    {'사건':<24}" + "".join(f"{'D+'+str(x):>16}" for x in _진입들)
              + f"{'표본':>9}")
        for 라 in 순서:
            목록 = 사건[라]
            if len(목록) < 200:
                continue
            줄 = []
            for 진입 in _진입들:
                a = 성과(목록, 진입, 보유)
                if len(a) < 150:
                    줄.append("-")
                    continue
                승 = sum(1 for x in a if x > 0) / len(a) * 100
                줄.append(f"{st.mean(a):+.2f}({승:.0f}%)")
            print(f"    {라:<24}" + "".join(f"{x:>16}" for x in 줄)
                  + f"{len(목록):>9,}")

    print(f"\n\n  ══ 크기별 최적 조합 ══")
    print(f"    {'사건':<24}{'크기':<6}{'진입':>7}{'보유':>7}{'평균':>9}"
          f"{'승률':>7}{'중앙값':>9}{'하위25%':>9}{'표본':>8}")
    for 라 in 순서:
        for g, _, _ in 크기표:
            목록 = [x for x in 사건[라] if x[2] == g]
            if len(목록) < 200:
                continue
            최고 = None
            for 진입 in _진입들:
                for 보유 in _보유들:
                    a = 성과(목록, 진입, 보유)
                    if len(a) < 150:
                        continue
                    m = st.mean(a)
                    if 최고 is None or m > 최고[0]:
                        최고 = (m, 진입, 보유, a)
            if not 최고:
                continue
            m, 진입, 보유, a = 최고
            a2 = sorted(a)
            승 = sum(1 for x in a2 if x > 0) / len(a2) * 100
            별 = "⭐" if (m > 0 and 승 >= 50) else ("  " if m > 0 else "❌")
            print(f"    {라:<24}{g:<6}{'D+'+str(진입):>7}{str(보유)+'일':>7}"
                  f"{m:>+8.2f}%{승:>6.0f}%{st.median(a2):>+8.2f}%"
                  f"{a2[len(a2)//4]:>+8.2f}%{len(a2):>8,}{별}")

    print("\n  읽는 법")
    print("    - ⚠️⚠️ **기간 2~2.7년. 학습/검증 분리를 못 했다. 전부 예비다**")
    print("    - 「계약 0~5%」와 「계약 30%↑」가 갈리면 **규모가 중요하다**는 뜻이다")
    print("    - 「임원 순매수」가 「순매도」보다 나으면 **내부자 신호가 있다**")
    print("    - 「괴리 50%↑」가 좋으면 목표주가가 쓸모 있고, 나쁘면 **증권사 낙관 편향**이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
