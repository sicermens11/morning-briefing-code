#!/usr/bin/env python3
r"""
auto_search.py — **사람 없이 도는 자동 조합 탐색기** (2026-09-03 신설)

⚠️⚠️ **사용자 요청.**
   *"금요일 퇴근 이후 금토일 종일 PC가 돌아가도록 켜놓고 갈건데
     그때 너가 자체적으로 필요한 테스트 시뮬레이션을 했으면 좋겠어서야"*

⚠️ **나는 대화 세션에서만 동작한다.** 사용자가 없으면 새 시험을 만들거나 판단할 수 없다.
   ⇒ 대신 **조건 격자를 미리 정의해 전수/무작위 탐색**하는 것은 자동으로 된다.
      결과를 파일로 쌓아두면 **월요일에 내가 읽고 판정**한다.

## ⚠️⚠️ 다중검정 위험 — 이게 이 파일의 가장 중요한 주의사항
```
수천 개를 보면 **우연히 좋은 게 반드시 나온다.**
84차에서 「100~200개」로도 본페로니 문턱이 3.03이었다. 수천 개면 훨씬 높다.
⇒ 그래서 **모든 조합에 세 판을 다 잰다**:
   ① 10.4년 전체
   ② 8.8년 (2025·26 제외)  ← 오늘 여기서 결론이 세 번 뒤집혔다
   ③ 걷기검증 (그 해 이전만 보고 재무 문턱을 정한다)
   **셋 다 통과한 것만** 후보로 남긴다
⇒ 월요일에 **순열검정(84차 B)**으로 최종 확인한다
```

## 탐색 격자
```
재무   잉여금 0/20/30/40/50/60 x 부채 60/80/100/120 x 흑자 필수/무관
기술   상대갭 -2/-3/-4/-5 x 볼린저 -0.7/-1.0/-1.3 x 20일 -5/-10/-15/-20
크기   시총상한 1000/2000/3000/5000억
매도   목표 +10/15/20/25/30 x 최대보유 20/30/40/60
운용   비중 10/15/20/25% x 하루 1/2/3종목
시장   미국조건 없음/-0.5%↓ x 시장갭 없음/-0.3%↓
```
⇒ 전수는 수십만 개다. **무작위 표본**으로 돈다 (`--개수`로 조절).

저장: `data/_search/결과.jsonl` (한 줄에 한 조합) · 이어받기 가능
      `data/_search/상위.txt` (사람이 읽을 표 · 주기적으로 갱신)

쓰는 법:
    python scripts\auto_search.py --개수 3000
    python scripts\auto_search.py --개수 99999 --시간 3600   # 1시간만
"""
import glob
import io
import json
import os
import random
import statistics as st
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
from day_lab import 연간재무  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "_search")
_비용 = 0.26
_시작 = "20160401"

격자 = {
    "잉여금": [0, 20, 30, 40, 50, 60],
    "부채": [60, 80, 100, 120],
    "흑자필수": [True, False],
    "상대갭": [-2, -3, -4, -5],
    "볼린저": [-0.7, -1.0, -1.3],
    "낙폭20": [-5, -10, -15, -20],
    "시총상한": [1000, 2000, 3000, 5000],
    "목표": [10, 15, 20, 25, 30],
    "최대보유": [20, 30, 40, 60],
    "비중": [0.10, 0.15, 0.20, 0.25],
    "하루상한": [1, 2, 3, 4],   # ⚠️ 94b에서 **4종목이 최선**이었다 (빠져 있었다)
    "미국조건": [None, -0.5],
    "시장갭조건": [None, -0.3],
}


def main():
    개수 = int(sys.argv[sys.argv.index("--개수") + 1]) if "--개수" in sys.argv else 2000
    제한시간 = (int(sys.argv[sys.argv.index("--시간") + 1])
                if "--시간" in sys.argv else 0)
    시작시각 = time.time()
    os.makedirs(OUT, exist_ok=True)
    결과파일 = os.path.join(OUT, "결과.jsonl")
    본것 = set()
    if os.path.exists(결과파일):
        for line in io.open(결과파일, encoding="utf-8"):
            try:
                본것.add(json.loads(line)["키"])
            except Exception:
                continue
    print(f"  이미 본 조합 {len(본것):,}개 · 이번에 {개수:,}개 더", flush=True)

    print("  자료 읽는 중...", flush=True)
    주가 = O.수정주가(("시총", "거래대금"))
    날 = sorted(주가)
    기본, 재무 = O._기본(), 연간재무()
    날인 = {d: i for i, d in enumerate(날)}
    종계, 자리 = {}, {}
    for d in 날:
        for c, v in 주가[d].items():
            종계.setdefault(c, []).append(v[0])
            자리.setdefault(c, {})[d] = len(종계[c]) - 1
    비, 갭표, 시장갭, 앞종 = {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "krx-daily", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8-sig"))
        d8 = d["기준일"]
        하루 = {}
        for c, v in d["종목"].items():
            try:
                종 = float(v["종가"])
                시 = float(v.get("시가") or 0) or 종
                고 = float(v.get("고가") or 0) or 종
                if min(종, 시, 고) <= 0:
                    continue
            except (TypeError, ValueError, KeyError):
                continue
            비.setdefault(d8, {})[c] = (시 / 종, 고 / 종)
            p = 앞종.get(c)
            앞종[c] = 종
            if p and p > 0:
                g = (시 / p - 1) * 100
                if abs(g) <= 32:
                    하루[c] = g
        갭표[d8] = 하루
        if len(하루) >= 100:
            시장갭[d8] = st.median(list(하루.values()))
    try:
        spy = json.load(io.open(os.path.join(O._DATA, "yahoo", "SPY.json"),
                                encoding="utf-8-sig"))["종가"]
    except Exception:
        spy = {}
    sk = sorted(spy)
    미맵 = {}
    import datetime as dt
    for d in 날:
        앞 = [x for x in sk if x < d]
        if len(앞) < 2:
            continue
        전 = max(앞)
        앞2 = [x for x in sk if x < 전]
        if not 앞2 or not spy[max(앞2)]:
            continue
        try:
            if (dt.datetime.strptime(d, "%Y%m%d")
                    - dt.datetime.strptime(전, "%Y%m%d")).days > 4:
                continue
        except Exception:
            pass
        미맵[d] = (spy[전] / spy[max(앞2)] - 1) * 100

    def 재무값(code, d8):
        줄 = 재무.get(code)
        if not 줄:
            return None
        m = None
        for 적용, v in 줄:
            if 적용 <= d8:
                m = v
            else:
                break
        return m

    # ⚠️⚠️ **후보를 한 번만 모은다.** 조건은 뒤에서 건다.
    #   가장 느슨한 조건(상대갭 -2 · 볼 -0.7 · 20일 -5 · 시총 5000억)으로 모아
    #   더 센 조건은 그 부분집합이 된다
    print("  후보 모으는 중 (한 번만 · 몇 분 걸린다)...", flush=True)
    후보 = []
    for i, d1 in enumerate(날):
        if i < 260 or i + 61 >= len(날):
            continue
        다음 = 날[i + 1]
        if 다음 < _시작:
            continue
        시갭 = 시장갭.get(다음)
        if 시갭 is None:
            continue
        하루갭 = 갭표.get(다음) or {}
        for code, v in 주가[d1].items():
            c1, 시총, 대금 = v
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT or 시총 >= 5e11:
                continue
            g = 하루갭.get(code)
            if g is None or (g - 시갭) > -2:
                continue
            fm = 재무값(code, d1)
            if not fm:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if (("관리종목" in 부) or ("SPAC" in 부)
                    or (bb.get("증권구분") not in (None, "주권"))):
                continue
            k = (자리.get(code) or {}).get(d1)
            if k is None or k < 250:
                continue
            sq = 종계[code]
            s20 = st.mean(sq[k - 19:k + 1])
            sd = st.pstdev(sq[k - 19:k + 1]) or 1e-9
            볼 = (c1 - s20) / (2 * sd)
            if 볼 > -0.7 or sq[k - 20] <= 0:
                continue
            r20 = (c1 / sq[k - 20] - 1) * 100
            if r20 > -5:
                continue
            b0 = (비.get(다음) or {}).get(code)
            v0 = 주가[다음].get(code)
            if not b0 or not v0:
                continue
            매수 = v0[0] * b0[0]
            if 매수 <= 0:
                continue
            # 60일치 (종가, 고가) 경로 — 최대보유 60까지 쓸 수 있게
            길 = []
            ok = True
            for h in range(0, 61):
                j = i + 1 + h
                if j >= len(날):
                    ok = False
                    break
                dd = 날[j]
                vv = 주가[dd].get(code)
                bb2 = (비.get(dd) or {}).get(code)
                if not vv or not bb2:
                    ok = False
                    break
                길.append((vv[0], vv[0] * bb2[1]))
            if not ok:
                continue
            후보.append({
                "날": 다음, "code": code, "매수": 매수, "길": 길,
                "상대갭": g - 시갭, "시장갭": 시갭, "볼린저": 볼,
                "낙폭20": r20, "시총": 시총 / 1e8, "대금": 대금,
                "미국": 미맵.get(다음), "i": i + 1,
                "잉여금": fm.get("잉여금비율"), "부채": fm.get("부채비율"),
                "흑자": fm.get("흑자")})
        if i % 700 == 0:
            print(f"    {i}/{len(날)}일 · 후보 {len(후보):,}", flush=True)
    print(f"  후보 {len(후보):,}건 확보. 이제 조합을 훑는다\n", flush=True)

    # 걷기검증용: 해마다 그 이전 자료로 재무 문턱을 뽑는다
    해들 = sorted({x["날"][:4] for x in 후보})
    걷기문턱 = {}
    for y in 해들:
        앞 = [x for x in 후보 if x["날"][:4] < y]
        잉 = sorted(x["잉여금"] for x in 앞 if x["잉여금"] is not None)
        부 = sorted(x["부채"] for x in 앞 if x["부채"] is not None)
        if len(잉) >= 200 and len(부) >= 200:
            걷기문턱[y] = (잉[len(잉) // 2], 부[len(부) // 2])

    def 돌리기(c, 끝날, 걷기=False):
        """한 조합을 자본 시뮬로 돌린다."""
        현금, 보유, 기록 = 5_000_000.0, [], []
        날별 = {}
        for x in 후보:
            if 걷기:
                t = 걷기문턱.get(x["날"][:4])
                if not t:
                    continue
                잉문, 부문 = t
            else:
                잉문, 부문 = c["잉여금"], c["부채"]
            if (x["잉여금"] or -9e9) < 잉문 or (x["부채"] or 9e9) > 부문:
                continue
            if c["흑자필수"] and x["흑자"] != 1.0:
                continue
            if x["상대갭"] > c["상대갭"] or x["볼린저"] > c["볼린저"]:
                continue
            if x["낙폭20"] > c["낙폭20"] or x["시총"] >= c["시총상한"]:
                continue
            if c["미국조건"] is not None:
                m = x["미국"]
                if m is None or m > c["미국조건"]:
                    continue
            if c["시장갭조건"] is not None and x["시장갭"] >= c["시장갭조건"]:
                continue
            날별.setdefault(x["날"], []).append(x)
        if not 날별:
            return None
        for d in [z for z in 날 if _시작 <= z <= 끝날]:
            i = 날인[d]
            남 = []
            for 청산i, 금, r in 보유:
                if 청산i <= i:
                    현금 += 금 * (1 + r / 100)
                else:
                    남.append((청산i, 금, r))
            보유 = 남
            평가 = 현금 + sum(금 for _, 금, _ in 보유)
            for x in sorted(날별.get(d) or [],
                            key=lambda z: z["상대갭"])[:c["하루상한"]]:
                r, h = None, c["최대보유"]
                for hh, (종2, 고2) in enumerate(x["길"][:c["최대보유"] + 1], 0):
                    if 고2 >= x["매수"] * (1 + c["목표"] / 100):
                        r, h = c["목표"] - _비용, max(1, hh)
                        break
                if r is None:
                    끝 = x["길"][min(c["최대보유"], len(x["길"])) - 1][0]
                    r = (끝 / x["매수"] - 1) * 100 - _비용
                쓸 = min(평가 * c["비중"], x["대금"] * 0.01)
                if 쓸 < 10_000 or 쓸 > 현금:
                    continue
                현금 -= 쓸
                보유.append((min(x["i"] + h, len(날) - 1), 쓸, r))
            기록.append((d, 평가))
        if len(기록) < 200:
            return None
        마지막 = 기록[-1][1]
        해 = len(기록) / 245
        연 = ((마지막 / 5_000_000.0) ** (1 / 해) - 1) * 100 if 마지막 > 0 else -100
        최고, 낙폭 = 5_000_000.0, 0.0
        for _, v in 기록:
            최고 = max(최고, v)
            낙폭 = min(낙폭, v / 최고 - 1)
        해별 = {}
        for d, v in 기록:
            해별.setdefault(d[:4], []).append(v)
        플 = 전 = 0
        for y in sorted(해별):
            a = 해별[y]
            if len(a) < 60:
                continue
            전 += 1
            플 += 1 if a[-1] > a[0] else 0
        return {"연": 연, "낙폭": 낙폭 * 100, "플": 플, "전": 전,
                "신호일": len(날별)}

    rng = random.Random()
    fp = io.open(결과파일, "a", encoding="utf-8")
    돈것 = 0
    통과 = 0
    for _ in range(개수):
        if 제한시간 and (time.time() - 시작시각) > 제한시간:
            print(f"  ⏱ 제한시간 {제한시간}초 도달 — 멈춘다")
            break
        c = {k: rng.choice(v) for k, v in 격자.items()}
        키 = "|".join(f"{k}={c[k]}" for k in sorted(c))
        if 키 in 본것:
            continue
        본것.add(키)
        a = 돌리기(c, "20260902")
        if not a or a["신호일"] < 30:
            continue
        b = 돌리기(c, "20241230")
        w = 돌리기(c, "20260902", 걷기=True)
        돈것 += 1
        # ⚠️ **세 판을 다 통과한 것만** 후보로 센다
        ok = (a and b and w
              and a["연"] > 0 and b["연"] > 0 and w["연"] > 0
              and a["플"] / max(1, a["전"]) >= 2 / 3
              and b["플"] / max(1, b["전"]) >= 2 / 3
              and w["플"] / max(1, w["전"]) >= 2 / 3)
        if ok:
            통과 += 1
        fp.write(json.dumps({
            "키": 키, "조건": c, "통과": ok,
            "전체": a, "제외판": b, "걷기": w}, ensure_ascii=False) + "\n")
        fp.flush()
        if 돈것 % 50 == 0:
            print(f"    {돈것:,}개 돌림 · 세 판 통과 {통과:,}개 "
                  f"({time.time()-시작시각:.0f}초)", flush=True)
    fp.close()
    print(f"\n  끝 · {돈것:,}개 돌림 · 세 판 통과 {통과:,}개")

    # ── 상위 목록 만들기 ──
    전부 = []
    for line in io.open(결과파일, encoding="utf-8"):
        try:
            전부.append(json.loads(line))
        except Exception:
            continue
    좋 = [x for x in 전부 if x.get("통과")]
    # ⚠️⚠️ **낙폭까지 보고 정렬한다** (2026-09-03 95b에서 배운 것)
    #    걷기검증 연평균만으로 줄 세우면 **공격적인 조합이 위로 온다.**
    #    95b: 돈만 보고 문턱을 고르니 뒤 기간 연 +1.4% · 낙폭 -38.5%였고,
    #         낙폭도 같이 보니 같은 분할에서 연 +22.9% · 낙폭 -16.8%가 됐다.
    #    ⇒ 「걷기검증 연평균 ÷ 낙폭」으로 줄 세운다 (낙폭 3% 미만은 3%로 본다)
    def 점수(x):
        연 = x["걷기"]["연"]
        낙 = abs(x["전체"]["낙폭"]) or 3.0
        return 연 / max(낙, 3.0)
    for x in 좋:
        x["점수"] = 점수(x)
    좋.sort(key=lambda x: -x["점수"])
    p = os.path.join(OUT, "상위.txt")
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(f"자동 탐색 결과 · 총 {len(전부):,}개 중 세 판 통과 {len(좋):,}개\n")
        f.write("⚠️ **걷기검증 연평균 ÷ 낙폭** 순 (95b에서 배운 것 — 돈만 보면"
                " 공격적인 게 위로 온다)\n")
        f.write("⚠️ **다중검정 위험** — 월요일에 순열검정으로 확인해야 한다\n\n")
        f.write("⚠️⚠️ **이 표는 전종목중앙갭 계열이다 — 실전에서 못 하는 규칙이다.**\n")
        f.write("   08:50에는 **후보 40개 예상체결가만** 보인다. 시장 전체 중앙갭은 낼 수 없다\n")
        f.write("   ⇒ 여기서 고른 것은 **scripts/crosscheck_lab.py 로 다시 재야** 한다\n")
        f.write(f"{'순':>4} {'점수':>6} {'걷기연%':>8} {'전체연%':>8} "
                f"{'제외판연%':>9} {'낙폭%':>7} {'연도별':>8} {'신호일':>7}"
                f"  조건\n")
        for n, x in enumerate(좋[:200], 1):
            c = x["조건"]
            간 = (f"잉{c['잉여금']}부{c['부채']}"
                  f"{'흑' if c['흑자필수'] else ''} "
                  f"갭{c['상대갭']}볼{c['볼린저']}20일{c['낙폭20']} "
                  f"시총{c['시총상한']} 목표{c['목표']}보유{c['최대보유']} "
                  f"비중{int(c['비중']*100)}%x{c['하루상한']}"
                  f"{' 미국' if c['미국조건'] else ''}"
                  f"{' 시장갭' if c['시장갭조건'] else ''}")
            f.write(f"{n:>4} {x['점수']:>6.2f} {x['걷기']['연']:>+8.2f} "
                    f"{x['전체']['연']:>+8.2f} "
                    f"{x['제외판']['연']:>+9.2f} {x['전체']['낙폭']:>7.1f} "
                    f"{x['전체']['플']}/{x['전체']['전']:<6} "
                    f"{x['전체']['신호일']:>7}  {간}\n")
    print(f"  상위 목록 → {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
