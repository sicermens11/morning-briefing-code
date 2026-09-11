#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
monday_permtest.py — **AutoSearch 상위 순열검정 (날짜를 뒤섞음, 84차 B 방식)** (2026-09-07)

⚠️ 만든 이유
    schedule-weekend.ps1 / auto_search.py 의 경고:
    "다중검정 위험 — 월요일에 순열검정으로 확인해야 한다"
    AGENDA.md: "월요일 최우선 과제: AutoSearch 상위에 순열검정.
    verify_all.py:268 에 씨앗 고정된 무작위 300개 검정이 이미 있다.
    그런데 그건 고정 규칙 하나만 검사한다."
    ⇒ 이 스크립트는 **AutoSearch 상위 표(상위.txt)의 1~3위 조합**에
      **같은 방법(84차 B: 실제 거래를 그대로 두고 진입 날짜만 무작위로 재배정)**을 적용한다.

방법 (84차 B 그대로)
    1. 조합 c 로 「전체 기간」(20160401~20260902) 을 실제로 돌려
       실제 거래 목록(어떤 날 인덱스에, 얼마짜리 수익률로, 며칠 들고 있었는지, 대금상한)을 그대로 뽑는다.
    2. **같은 거래들**을 그대로 두고, **진입 날짜만** 원래 후보가 있었던 날짜 풀에서
       무작위로 재배정한다 (몇 번을 며칠에 샀는지는 바뀌지만 「어떤 종목·몇 %」는 그대로).
    3. 이걸 500번 반복해 최종자산 분포를 만들고,
       **p = (셔플 결과가 실제 결과 이상인 비율)** 을 낸다.
    ⚠️ 이건 「언제 사느냐」가 유의한지를 검정한다 ("어떤 종목이냐"는 그대로 두므로).
       다중검정(격자 231,714개 자체의 과적합) 검정은 아니다 — 그건 별도로 더 큰 작업이 필요하다.

결과: data/_search/순열검정.txt · data/_search/순열검정.json
"""
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
DATA = os.path.join(_BASE, "data")
OUT = os.path.join(DATA, "_search")
_비용 = 0.26
_시작 = "20160401"
_시드 = 5_000_000.0
_N순열 = 500
_시드값 = 20260907


def log(f, s=""):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    로그경로 = os.path.join(OUT, "순열검정.txt")
    logf = io.open(로그경로, "w", encoding="utf-8")
    log(logf, f"===== 월요일 순열검정 시작 {time.strftime('%Y-%m-%d %H:%M:%S')} =====")

    # ── 상위 후보 3개 뽑기 (결과.jsonl 다시 채점) ──
    결과파일 = os.path.join(OUT, "결과.jsonl")

    def 점수(x):
        연 = x["걷기"]["연"]
        낙 = abs(x["전체"]["낙폭"]) or 3.0
        return 연 / max(낙, 3.0)

    좋 = []
    with io.open(결과파일, encoding="utf-8") as f:
        for line in f:
            try:
                x = json.loads(line)
            except Exception:
                continue
            if x.get("통과"):
                x["점수"] = 점수(x)
                좋.append(x)
    좋.sort(key=lambda x: -x["점수"])
    후보순위 = 좋[:3]
    log(logf, f"  결과.jsonl {len(좋):,}개 통과 중 상위 3개로 검정\n")

    # ── 자료 읽기 (auto_search.py 와 동일) ──
    log(logf, "  자료 읽는 중...")
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
    import glob
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
        spy = json.load(io.open(os.path.join(O._DATA, "us-daily", "SPY.json"),
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

    log(logf, "  후보 모으는 중 (한 번만 · 몇 분 걸린다)...")
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
    log(logf, f"  후보 {len(후보):,}건 확보\n")

    def 돌리기_기록(c, 끝날):
        """실제 auto_search.py 돌리기()와 같은 로직 + 거래 목록도 기록한다."""
        현금, 보유, 기록 = 5_000_000.0, [], []
        날별 = {}
        for x in 후보:
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
        거래목록 = []
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
                청산i = min(x["i"] + h, len(날) - 1)
                보유.append((청산i, 쓸, r))
                거래목록.append({"i": i, "r": r, "h": h, "대금상한": x["대금"] * 0.01})
            기록.append((d, 평가))
        마지막 = (현금 + sum(금 for _, 금, _ in 보유)) if 기록 else _시드
        return {"최종": 마지막, "거래": 거래목록, "신호일수": len(날별),
                "날별키": sorted(날인[d] for d in 날별)}

    def 순열(c, 실제, N=_N순열, seed=_시드값):
        rng = random.Random(seed)
        거래 = 실제["거래"]
        풀 = 실제["날별키"]
        if not 거래 or not 풀:
            return []
        분포 = []
        끝i = 날인[[z for z in 날 if _시작 <= z][0]]
        시작i = 끝i
        for _ in range(N):
            표본 = rng.sample(풀, min(len(거래), len(풀)))
            배정 = list(zip(표본, 거래))
            배정딕 = {}
            for di, tr in 배정:
                배정딕.setdefault(di, []).append(tr)
            현금, 보유 = _시드, []
            for i in range(시작i, len(날)):
                남 = []
                for 청산i, 금, r in 보유:
                    if 청산i <= i:
                        현금 += 금 * (1 + r / 100)
                    else:
                        남.append((청산i, 금, r))
                보유 = 남
                평가 = 현금 + sum(금 for _, 금, _ in 보유)
                for tr in (배정딕.get(i) or [])[:c["하루상한"]]:
                    쓸 = min(평가 * c["비중"], tr["대금상한"])
                    if 쓸 < 10_000 or 쓸 > 현금:
                        continue
                    현금 -= 쓸
                    보유.append((min(i + tr["h"], len(날) - 1), 쓸, tr["r"]))
            마지막 = 현금 + sum(금 for _, 금, _ in 보유)
            분포.append(마지막)
        return 분포

    끝날 = "20260902"
    전체결과 = []
    for rank, x in enumerate(후보순위, 1):
        c = x["조건"]
        log(logf, f"  ── {rank}위 조합 실제 거래 재현 중 ──")
        log(logf, f"     조건: {c}")
        실제 = 돌리기_기록(c, 끝날)
        log(logf, f"     실제 최종자산 {실제['최종']:,.0f}원 · "
                   f"거래 {len(실제['거래'])}건 · 신호일 {실제['신호일수']}일")
        log(logf, f"     순열 {_N순열}회 도는 중 (씨앗 {_시드값})...")
        t1 = time.time()
        분포 = 순열(c, 실제)
        if 분포:
            분포.sort()
            p = sum(1 for v in 분포 if v >= 실제["최종"]) / len(분포)
            log(logf, f"     셔플 최악 {분포[0]:,.0f}원 · 중앙 {분포[len(분포)//2]:,.0f}원 · "
                       f"최고 {분포[-1]:,.0f}원 ({time.time()-t1:.0f}초)")
            log(logf, f"     ⭐ 실제 {실제['최종']:,.0f}원 → **p = {p:.4f}**"
                       f"{'  (p<0.05, 유의)' if p < 0.05 else '  (p>=0.05, 유의하지 않음)'}")
        else:
            p = None
            log(logf, "     ⚠️ 순열 실패 (거래 또는 날짜 풀 없음)")
        전체결과.append({
            "순위": rank, "조건": c, "실제최종": 실제["최종"],
            "거래수": len(실제["거래"]), "신호일수": 실제["신호일수"],
            "p값": p,
            "셔플최악": 분포[0] if 분포 else None,
            "셔플중앙": 분포[len(분포)//2] if 분포 else None,
            "셔플최고": 분포[-1] if 분포 else None,
        })
        log(logf, "")

    log(logf, f"===== 끝 · 총 {time.time()-t0:.0f}초 =====")
    with io.open(os.path.join(OUT, "순열검정.json"), "w", encoding="utf-8") as f:
        json.dump({"만든날": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "N순열": _N순열, "씨앗": _시드값, "결과": 전체결과},
                   f, ensure_ascii=False, indent=1)
    logf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
