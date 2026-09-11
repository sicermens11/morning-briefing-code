#!/usr/bin/env python3
r"""
paper_trade.py — **가상매매로 규칙 성적을 잰다** (2026-09-01 신설)

⚠️⚠️ **왜 만들었나.** 사용자 제안:
   *"최우선매수·매수권고가 나오면 10만원씩 매수, 1주당 10만원 이상인 종목은 1주 매수라는
     규칙을 세워서 가상으로 해보는 것도 괜찮지 않아?"*
   맞다. 그리고 **3개월 기다릴 필요가 없다** — 픽 기록·주가가 다 있어서 **소급된다.**

⚠️ **실제 매매 기록을 안 봐도 된다.** 2026-08-31에 "매매 기록은 보유 비율보다 민감하다"고
   기각했는데, 가상매매는 그 결정을 건드리지 않는다. **금액도 화면에 안 나간다** — 비율만 낸다.

**규칙** (전부 바꿀 수 있다. 아래 상수)
    사는 날   픽 날짜 당일 09:00 **시가**.  발굴가가 전 거래일 종가임을 확인했다(2026-09-01).
    파는 날   D+5 거래일 **종가**
    수량      10만원 ÷ 시가 (버림). 시가가 10만원을 넘으면 **1주**
    손절      보유 중 **저가**가 손절가 이하로 내려가면 그날 손절가에 판다
              손절가가 없는 옛 픽은 −7%로 가정한다 ⚠️ **가정이다** (실제 픽의 손절폭은 −0.7~−8%)
    비용      살 때 0.015% · 팔 때 0.015% + 증권거래세 0.18%

⚠️⚠️ **초과수익률로도 잰다.** 절대 수익은 시장이 올라서 난 것일 수 있다.
   [[finish-data-before-concluding]]의 네 겹 규칙 중 ①②를 지킨다.

쓰는 법:
    python scripts\paper_trade.py              # 실제 픽 19건
    python scripts\paper_trade.py --손절없이
    python scripts\paper_trade.py --보유 10
"""
import argparse
import io
import json
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KRX = os.path.join(_BASE, "data", "krx-daily")
LOG = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")

원금 = 100_000        # 한 종목에 넣는 돈
보유 = 5              # 거래일
기본손절 = -0.07      # 손절가가 기록에 없는 옛 픽에 쓰는 가정
살때비용 = 0.00015
팔때비용 = 0.00015 + 0.0018   # 수수료 + 증권거래세

_캐시 = {}


def 날들():
    return sorted(f[:-5] for f in os.listdir(KRX) if f.endswith(".json"))


def 하루(d):
    if d not in _캐시:
        try:
            _캐시[d] = json.load(io.open(os.path.join(KRX, d + ".json"),
                                        encoding="utf-8"))["종목"]
        except Exception:
            _캐시[d] = {}
    return _캐시[d]


def 코스피지수(d):
    """전 종목 시총가중 등락률 — 지수 대신 쓴다."""
    s = 하루(d)
    무게 = 값 = 0.0
    for v in s.values():
        w = v.get("시총") or 0
        if w and v.get("등락률") is not None:
            무게 += w
            값 += w * v["등락률"]
    return 값 / 무게 if 무게 else 0.0


def 한건(code, 픽날, 목록, 손절가, 보유일, 손절쓰나, 담는법="1주라도"):
    """한 종목을 사서 파는 것을 흉내낸다. 못 하면 None."""
    if 픽날 not in 목록:
        return None
    i = 목록.index(픽날)
    앞 = 목록[i:i + 보유일 + 1]
    if len(앞) < 보유일 + 1:
        return None                      # 아직 파는 날이 안 왔다
    산다 = 하루(앞[0]).get(code)
    if not 산다 or not 산다.get("시가"):
        return None
    매수가 = 산다["시가"]
    if 담는법 == "건너뛴다" and 매수가 > 원금:
        return {"건너뜀": True, "code": code, "이름": "", "매수가": 매수가}
    if 담는법 == "쪼갠다":
        수량 = 원금 / 매수가            # 소수점 매수 가정 ⚠️ 국내주식은 대부분 안 된다
    else:
        수량 = max(1, int(원금 // 매수가))
    투입 = 매수가 * 수량 * (1 + 살때비용)

    컷 = 손절가 if 손절가 else 매수가 * (1 + 기본손절)
    매도가, 사유 = None, ""
    for d in 앞[1:]:
        v = 하루(d).get(code)
        if not v:
            continue
        if 손절쓰나 and v.get("저가") and v["저가"] <= 컷:
            매도가, 사유 = 컷, "손절"
            break
    if 매도가 is None:
        끝 = 하루(앞[-1]).get(code)
        if not 끝 or not 끝.get("종가"):
            return None
        매도가, 사유 = 끝["종가"], "만기"

    회수 = 매도가 * 수량 * (1 - 팔때비용)
    시장 = sum(코스피지수(d) for d in 앞[1:])
    수익률 = (회수 - 투입) / 투입 * 100
    return {"code": code, "픽날": 픽날, "매수가": 매수가, "수량": 수량,
            "매도가": 매도가, "사유": 사유, "투입": 투입, "회수": 회수,
            "수익률": round(수익률, 2), "시장": round(시장, 2),
            "초과": round(수익률 - 시장, 2), "건너뜀": False}


def 픽읽기(등급들):
    out = []
    for l in io.open(LOG, encoding="utf-8-sig"):
        if not l.strip():
            continue
        d = json.loads(l)
        for p in (d.get("picks") or []):
            if p.get("grade") in 등급들:
                out.append((d["date"].replace("-", ""), p["code"], p["name"],
                            p["grade"], p.get("stop_loss")))
    return out


def 돌리기(등급들, 보유일, 손절쓰나, 담는법="1주라도"):
    목록 = 날들()
    결과 = []
    건너뜀 = []
    for 날, code, 이름, 등급, 손절 in 픽읽기(등급들):
        r = 한건(code, 날, 목록, 손절, 보유일, 손절쓰나, 담는법)
        if r is None:
            건너뜀.append((날, 이름, "파는 날이 아직"))
            continue
        if r.get("건너뜀"):
            건너뜀.append((날, 이름, "1주가 10만원을 넘는다"))
            continue
        r["이름"], r["등급"] = 이름, 등급
        결과.append(r)
    return 결과, 건너뜀


def 표(결과, 건너뜀, 제목):
    print(f"\n{'='*74}\n{제목}\n{'='*74}")
    if not 결과:
        print("  성적을 낼 수 있는 건이 없다.")
    else:
        print(f"  {'픽날':10s}{'종목':16s}등급 {'수량':>6s}{'수익률':>9s}{'시장':>8s}{'초과':>8s}  사유")
        for r in 결과:
            print(f"  {r['픽날']:10s}{r['이름'][:14]:16s}{r['등급']}  {r['수량']:>6.2f}"
                  f"{r['수익률']:>8.2f}%{r['시장']:>7.2f}%{r['초과']:>+8.2f}  {r['사유']}")
        투 = sum(r["투입"] for r in 결과)
        회 = sum(r["회수"] for r in 결과)
        평 = sum(r["수익률"] for r in 결과) / len(결과)
        초 = sum(r["초과"] for r in 결과) / len(결과)
        승 = sum(1 for r in 결과 if r["수익률"] > 0)
        손 = sum(1 for r in 결과 if r["사유"] == "손절")
        print(f"\n  {len(결과)}건 · 승률 {승}/{len(결과)} ({승/len(결과)*100:.0f}%) · 손절 {손}건")
        print(f"  평균 수익률 {평:+.2f}%  ·  평균 초과 {초:+.2f}%p")
        print(f"  전체 {(회-투)/투*100:+.2f}%   ⚠️ 금액은 안 적는다 — 비율만 본다")
    if 건너뜀:
        print(f"\n  · 아직 못 재는 것 {len(건너뜀)}건: " +
              ", ".join(f"{n}" for _, n, _ in 건너뜀[:8]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--보유", type=int, default=보유)
    ap.add_argument("--손절없이", action="store_true")
    ap.add_argument("--등급", default="🔴🟢")
    a = ap.parse_args()
    등급들 = set(a.등급) if a.등급 != "전부" else {"🔴", "🟢", "🟡"}

    for 손절쓰나, 라벨 in ((True, "손절 넣음"), (False, "손절 없음")):
        if a.손절없이 and 손절쓰나:
            continue
        r, s = 돌리기(등급들, a.보유, 손절쓰나)
        표(r, s, f"가상매매 · {''.join(sorted(등급들))} · D+{a.보유} · {라벨}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
