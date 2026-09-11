#!/usr/bin/env python3
r"""
big_lab.py — **99차. 보조 전략을 하이닉스 말고 다른 대형주로도** (2026-09-04 새벽)

## 93차가 알려준 것
```
미국 반도체 아무거나 -2%↓ -> 다음날 **SK하이닉스** 매수 · 10일 보유
   5일 +1.13% · 10일 +2.01% · 승률 58.8% · **10/11해**
   삼성전자는 안 됐다 (+0.43% · 6/11해)
⇒ 자산 1억부터 값을 한다 (90차·93차)
```

## 여기서 재는 것
```
A ⭐ **다른 대형주도 되나** — 반도체 소재·장비·부품 대형주 전부
B ⭐ **ETF로 하면** — KODEX 반도체 등. 개별 종목 위험을 피할 수 있다
C 미국 신호 종류별 — 어느 미국 종목이 어느 한국 대형주를 끄나
D 보유일 (5·10·15·20일)
E ⭐⭐ **여러 종목에 나눠 사면** — 하이닉스 하나에 몰지 않고
F ⚠️ 2025·26 제외 · 연도별
```
⚠️ 판정: 평균·승률·**연도별 3분의 2**. 자본 시뮬은 93차에서 이미 했다
⚠️ 시차: 미국 T-1일 밤 종가 = 한국 T일 새벽 06:00 확정 -> 08:00 브리핑이 안다
"""
import bisect
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_비용 = 0.26
_시작 = "20160401"
_YH = os.path.join(O._DATA, "yahoo")
_ETF = os.path.join(O._DATA, "etf-krx")

미국 = (("NVDA", "엔비디아"), ("AMAT", "어플라이드"), ("LRCX", "램리서치"),
        ("SOXX", "반도체지수"), ("KLAC", "KLA"), ("WDC", "웨스턴디지털"),
        ("MU", "마이크론"), ("ASML", "ASML"))

# 한국 대형·중견주 (반도체·전자 축)
대상 = (
    ("000660", "SK하이닉스"), ("005930", "삼성전자"),
    ("009150", "삼성전기"), ("011070", "LG이노텍"),
    ("042700", "한미반도체"), ("000990", "DB하이텍"),
    ("402340", "SK스퀘어"), ("058470", "리노공업"),
    ("240810", "원익IPS"), ("039030", "이오테크닉스"),
    ("036930", "주성엔지니어링"), ("056190", "에스에프에이"),
    ("064760", "티씨케이"), ("357780", "솔브레인"),
    ("005290", "동진쎄미켐"), ("131970", "두산테스나"),
)
# 반도체 ETF 후보
ETF후보 = (("091160", "KODEX 반도체"), ("091230", "TIGER 반도체"),
           ("117460", "KODEX 에너지화학"), ("305720", "KODEX 2차전지"))


def main():
    미등 = {}
    for 심, 이름 in 미국:
        p = os.path.join(_YH, 심 + ".json")
        if not os.path.exists(p):
            continue
        종 = json.load(io.open(p, encoding="utf-8-sig")).get("종가") or {}
        k = sorted(종)
        e = {}
        for j in range(1, len(k)):
            pv = 종[k[j - 1]]
            if pv:
                e[k[j]] = (종[k[j]] / pv - 1) * 100
        미등[심] = (이름, e, sorted(e))

    주가 = O.수정주가(())
    날 = sorted(주가)
    날인 = {d: i for i, d in enumerate(날)}
    기본 = O._기본()
    있 = [(c, n) for c, n in 대상 if c in 기본]
    없 = [n for c, n in 대상 if c not in 기본]
    if 없:
        print(f"  ⚠️ 못 찾은 종목: {', '.join(없)}")
    코드 = {c for c, _ in 있}
    비 = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        for c, v in d["종목"].items():
            if c not in 코드:
                continue
            try:
                종c = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종c
                if 종c <= 0 or 시 <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = 시 / 종c

    # ── ETF (별도 자료) ──
    etf값, etf시 = {}, {}
    파일 = sorted(glob.glob(os.path.join(_ETF, "*.json")))
    쓸etf = []
    if 파일:
        표 = {}
        for f in 파일[::20]:
            try:
                d = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:
                continue
            종 = d.get("종목") or {}
            for c, n in ETF후보:
                if c in 종:
                    표[c] = 표.get(c, 0) + 1
        쓸etf = [(c, n) for c, n in ETF후보 if 표.get(c, 0) > 50]
        for f in 파일:
            try:
                d = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:
                continue
            d8 = d.get("기준일") or os.path.basename(f)[:8]
            종 = d.get("종목") or {}
            for c, n in 쓸etf:
                v = 종.get(c)
                if not v:
                    continue
                try:
                    종c = float(v.get("종가") or 0)
                    시 = float(v.get("시가") or 0) or 종c
                except (TypeError, ValueError):
                    continue
                if 종c > 0 and 시 > 0:
                    etf값.setdefault(c, {})[d8] = 종c
                    etf시.setdefault(c, {})[d8] = 시
    print(f"  한국 {len(있)}종목 · ETF {len(쓸etf)}개 "
          f"({', '.join(n for _, n in 쓸etf)})", flush=True)

    쓸 = {}
    for 심, (이름, e, ks) in 미등.items():
        t = {}
        for d in 날:
            j = bisect.bisect_left(ks, d)
            if j == 0:
                continue
            전 = ks[j - 1]
            try:
                if (dt.datetime.strptime(d, "%Y%m%d")
                        - dt.datetime.strptime(전, "%Y%m%d")).days > 5:
                    continue
            except Exception:
                pass
            t[d] = e[전]
        쓸[심] = t

    선 = {}
    for c, n in 있:
        선[c] = {d: 주가[d][c][0] for d in 날 if 주가[d].get(c)}
    쓸날 = [d for d in 날 if d >= _시작]
    print(f"  {len(쓸날):,}일 · 미국 {len(미등)}종목\n", flush=True)

    def 날뽑(심들, 문=-2.0):
        """심들 중 **하나라도** 문턱 아래면 신호 (93차 C: 강도는 상관없다)"""
        out = []
        for d in 쓸날:
            for 심 in 심들:
                v = (쓸.get(심) or {}).get(d)
                if v is not None and v <= 문:
                    out.append(d)
                    break
        return out

    def 사기(날들, c, 보유일=10, 값=None, 시비=None):
        s = 값 if 값 is not None else 선.get(c)
        결, 해 = [], {}
        if not s:
            return 결, 해
        ks = sorted(s)
        for d in 날들:
            if 시비 is not None:
                시 = 시비.get(d)
                v0 = s.get(d)
                if not 시 or not v0:
                    continue
                매수 = 시
                j = bisect.bisect_left(ks, d)
                if j + 보유일 - 1 >= len(ks):
                    continue
                v1 = s[ks[j + 보유일 - 1]]
            else:
                i = 날인.get(d)
                b = (비.get(d) or {}).get(c)
                v0 = s.get(d)
                if i is None or not b or not v0:
                    continue
                매수 = v0 * b
                j = i + 보유일 - 1
                if j >= len(날) or not s.get(날[j]):
                    continue
                v1 = s[날[j]]
            r = (v1 / 매수 - 1) * 100 - _비용
            결.append(r)
            해.setdefault(d[:4], []).append(r)
        return 결, 해

    def 보고(결, 해, 라, 날수, 폭=22, 최대표본=None):
        """⚠️ 2026-09-04 고침: 평균만 돌려주면 표본이 짧은 종목이 1위가 된다.
        (SK스퀘어가 2021년 상장인데 4/6해로 1위였다)
        이제 **(평균, 25·26제외 평균, 연도별통과, 표본충분)**을 함께 돌려준다"""
        if len(결) < 40:
            print(f"    {라:<{폭}}{len(결):>6}건  표본 부족")
            return None
        전 = 플 = 0
        for y, a in 해.items():
            if len(a) < 5:
                continue
            전 += 1
            플 += 1 if st.mean(a) > 0 else 0
        승 = sum(1 for r in 결 if r > 0) / len(결) * 100
        빼 = [r for y in 해 if y < "2025" for r in 해[y]]
        빼평 = st.mean(빼) if 빼 else 0.0
        연통 = (전 >= 9 and 플 / 전 >= 2 / 3)
        표충 = (최대표본 is None or len(결) >= 최대표본 * 0.8)
        별 = "⭐" if (연통 and st.mean(결) > 0.5) else "  "
        경 = ""
        if not 표충:
            경 = " ⚠️표본짧음"
        elif 전 < 9:
            경 = " ⚠️해적음"
        elif 빼평 <= 0.1:
            경 = " ⚠️25·26덕"
        print(f"    {라:<{폭}}{날수:>6}일{len(결):>7}건{st.mean(결):>+9.2f}%"
              f"{st.median(결):>+9.2f}%{승:>7.1f}%{f'{플}/{전}':>7}"
              f"{빼평:>+9.2f}%{별}{경}")
        return {"평균": st.mean(결), "제외평균": 빼평, "연통": 연통,
                "표충": 표충, "표본": len(결), "전": 전, "플": 플}

    머 = (f"    {'종목':<22}{'날':>7}{'표본':>7}{'평균':>10}{'중앙':>9}"
          f"{'승률':>7}{'연도별':>7}{'25·26제외':>10}")

    모두 = 날뽑(list(미등))
    print(f"  ══ A ⭐ **미국 반도체 아무거나 −2%↓ → 각 한국 종목 (10일)** ══")
    print(f"     신호일 {len(모두):,}일 / {len(쓸날):,}일 "
          f"({len(모두)/len(쓸날)*100:.0f}%)")
    print(머)
    # 먼저 가장 긴 표본이 몇 건인지 알아둔다 (표본 길이 판정용)
    최대 = 0
    미리 = {}
    for c, n in 있:
        결, 해 = 사기(모두, c)
        미리[c] = (결, 해)
        최대 = max(최대, len(결))
    순, 탈락 = [], []
    for c, n in 있:
        결, 해 = 미리[c]
        m = 보고(결, 해, n, len(모두), 최대표본=최대)
        if m is None:
            continue
        # ⚠️ 세 관문을 다 통과한 것만 순위에 올린다
        if m["연통"] and m["표충"] and m["제외평균"] > 0.1:
            순.append((m["제외평균"], m["평균"], c, n))
        else:
            까 = ("표본 짧음" if not m["표충"] else
                  ("연도별 미달" if not m["연통"] else "2025·26 덕"))
            탈락.append((n, 까, m["제외평균"]))
    순.sort(reverse=True)
    print("")
    print(f"    ── ⭐ **세 관문 통과** (연도별 9해 이상 · 표본 8할 이상 · "
          f"2025·26 제외해도 흑자) ──")
    print(f"      {'종목':<16}{'25·26제외':>10}{'전체평균':>10}")
    for 제, 평, c, n in 순:
        print(f"      {n:<16}{제:>+9.2f}%{평:>+9.2f}%")
    if 탈락:
        print(f"\n    ── 떨어진 것 ──")
        for n, 까, 제 in 탈락:
            print(f"      {n:<16}{까:<12}(25·26제외 {제:+.2f}%)")

    if 쓸etf:
        print(f"\n  ══ B ⭐ **ETF로 하면** (개별 종목 위험을 피한다) ══")
        print(머)
        for c, n in 쓸etf:
            결, 해 = 사기(모두, c, 값=etf값.get(c), 시비=etf시.get(c))
            보고(결, 해, n, len(모두))

    print(f"\n  ══ C **어느 미국 종목이 어느 한국 종목을 끄나** ══")
    print(f"    {'미국 → 한국':<30}{'표본':>7}{'평균':>10}{'승률':>7}{'연도별':>7}")
    상위 = [c for _, _, c, _ in 순[:5]]
    이름표 = dict(있)
    for 심, (이름, _, _) in 미등.items():
        날들 = 날뽑([심])
        for c in 상위[:3]:
            결, 해 = 사기(날들, c)
            if len(결) < 40:
                continue
            전 = 플 = 0
            for y, a in 해.items():
                if len(a) >= 5:
                    전 += 1
                    플 += 1 if st.mean(a) > 0 else 0
            승 = sum(1 for r in 결 if r > 0) / len(결) * 100
            별 = "⭐" if (전 >= 9 and 플 / 전 >= 2 / 3) else ""
            print(f"    {f'{이름} → {이름표[c]}':<30}{len(결):>6}건"
                  f"{st.mean(결):>+9.2f}%{승:>6.1f}%{f'{플}/{전}':>7}{별}")

    print(f"\n  ══ D **며칠 들고 있나** (상위 3종목) ══")
    print(f"    {'종목 · 보유일':<22}{'날':>7}{'표본':>7}{'평균':>10}{'중앙':>9}"
          f"{'승률':>7}{'연도별':>7}{'25·26제외':>10}")
    for 제, 평, c, n in 순[:3]:
        for h in (5, 10, 15, 20):
            결, 해 = 사기(모두, c, 보유일=h)
            보고(결, 해, f"{n} {h}일", len(모두))

    print(f"\n  ══ E ⭐⭐ **여러 종목에 나눠 사면** ══")
    print("     하이닉스 하나에 몰지 않고 상위 N개에 똑같이 나눠 산다")
    print(f"    {'몇 종목에':<22}{'날':>7}{'표본':>7}{'평균':>10}{'중앙':>9}"
          f"{'승률':>7}{'연도별':>7}{'25·26제외':>10}")
    print(f"     ⚠️ **세 관문을 통과한 {len(순)}종목 안에서만** 고른다")
    for N in (1, 2, 3, 5, 8):
        if N > len(순):
            break
        고 = [c for _, _, c, _ in 순[:N]]
        합, 해 = [], {}
        for d in 모두:
            벌 = []
            for c in 고:
                결, _ = 사기([d], c)
                if 결:
                    벌.append(결[0])
            if 벌:
                m = st.mean(벌)
                합.append(m)
                해.setdefault(d[:4], []).append(m)
        보고(합, 해, f"상위 {N}종목", len(모두))

    print("\n  읽는 법")
    print("    - **연도별 3분의 2**와 **25·26제외**를 둘 다 넘어야 진짜다")
    print("    - E에서 나눠 사도 성적이 안 떨어지면 **위험만 줄인 것**이라 좋다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
