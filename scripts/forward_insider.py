#!/usr/bin/env python3
r"""
forward_insider.py — **임원·주요주주 여럿이 함께 산 종목 · 예측 기록** (2026-10-13)

사용자 10/13 「응」 — 내 물음: 「「임원 여럿이 함께 매수」를 예측 기록에 올릴까요? (화면엔 안 넣고 기록만 · 20건↑ 쌓이면 판단)」
근거: insider_cluster_lab.py (10/12) — 14일 안 3명↑ 매수: 시장 대비 20일 +4.34%(88건) · 60일 +13.48%(70건 · 61%) · 1년치뿐

· 신호: dart-exec 에서 보고일(접수일) 기준 14일 안에 서로 다른 사람 3명↑이 산(증감 > 0) 종목 · 시총 300억↑
· ⚠️ dart-exec 는 종목마다 6일에 한 번 새로 받는다(collect_exec --갱신일 6) — 늦게 알 수 있다
  ⇒ **알게 된 날(발견일)의 다음 거래일 종가에 산다**고 적는다(보고일 다음 날로 적으면 그땐 몰랐던 값을 쓴다)
· 시작: 2026-10-13 발견분부터 (그 전 것은 시험에서 잰 것)
· 같은 종목은 발견일 30일 안 다시 안 적는다
· 채점: 5·20·60거래일 뒤 종가 수익 − 같은 기간 시총 300억↑ 전체 평균(시장 대비) · 비용 0.26%
· 기록: data/forward-insider-log.jsonl (한 줄 = 한 신호 · 채점되면 그 줄을 고친다) · 화면엔 안 띄운다
쓰는 법: python scripts\forward_insider.py   (forward_daily 가 매일 부른다)
"""
import bisect
import datetime as dt
import glob
import io
import json
import os
import statistics as st
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

시작 = "20261013"
로그 = os.path.join(O._DATA, "forward-insider-log.jsonl")
사람수 = 3
창일 = 14
비용 = 0.26
지평 = (5, 20, 60)


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def 신호들():
    """종목별로 가장 최근 「14일 안 3명↑」 묶음의 마지막 보고일과 사람 수"""
    결과 = {}
    for f in glob.glob(os.path.join(O._DATA, "dart-exec", "*.json")):
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        code = j.get("종목") or os.path.basename(f)[:6]
        산 = sorted((str(z.get("접수일") or "").replace("-", ""), z.get("성명") or "") for z in (j.get("이력") or [])
                   if (_n(z.get("증감")) or 0) > 0 and z.get("접수일"))
        for k, (d8, _) in enumerate(산):
            d0 = (dt.date(int(d8[:4]), int(d8[4:6]), int(d8[6:])) - dt.timedelta(days=창일)).strftime("%Y%m%d")
            사람 = {p for (dd, p) in 산[: k + 1] if d0 < dd <= d8}
            if len(사람) >= 사람수:
                결과[code] = (d8, len(사람))
    return 결과


def main():
    오늘 = dt.date.today().strftime("%Y%m%d")
    옛 = [json.loads(z) for z in io.open(로그, encoding="utf-8")] if os.path.exists(로그) else []
    # ① 새 신호 — 보고일이 최근 30일 안이고, 같은 종목을 30일 안에 안 적었으면
    최근 = (dt.date.today() - dt.timedelta(days=30)).strftime("%Y%m%d")
    새 = 0
    for code, (d8, n) in sorted(신호들().items()):
        if d8 < 최근 or 오늘 < 시작:
            continue
        if any(r["종목"] == code and r["발견일"] >= 최근 for r in 옛):
            continue
        옛.append({"종목": code, "보고일": d8, "사람수": n, "발견일": 오늘, "매수일": None, "매수가": None, "채점": {}})
        새 += 1
    # ② 매수가·채점 — 수정 종가로
    주가 = O.수정주가(("시총",))
    날 = sorted(주가)
    채 = 0
    시장캐시 = {}

    def 시장(i, h):
        if (i, h) not in 시장캐시:
            a, b = 주가[날[i]], 주가[날[i + h]]
            rs = [b[c][0] / v[0] - 1 for c, v in a.items()
                  if v[0] and len(v) > 1 and v[1] and v[1] >= 300e8 and b.get(c) and b[c][0]]
            시장캐시[(i, h)] = st.mean(rs) * 100 if rs else None
        return 시장캐시[(i, h)]

    for r in 옛:
        i = bisect.bisect_right(날, r["발견일"])           # 발견일 다음 거래일
        if i >= len(날):
            continue
        v = 주가[날[i]].get(r["종목"])
        if not v or not v[0]:
            continue
        if r.get("매수일") is None:
            if len(v) > 1 and v[1] and v[1] < 300e8:
                r["매수일"], r["제외"] = 날[i], "시총 300억 미만"
                continue
            r["매수일"], r["매수가"] = 날[i], round(v[0], 2)
        if r.get("제외"):
            continue
        for h in 지평:
            k = f"D+{h}"
            if k in r["채점"] or i + h >= len(날):
                continue
            e = 주가[날[i + h]].get(r["종목"])
            m = 시장(i, h)
            if not e or not e[0] or m is None:
                continue
            수 = (e[0] / v[0] - 1) * 100 - 비용
            r["채점"][k] = {"수익": round(수, 2), "시장대비": round(수 - m, 2)}
            채 += 1
    with io.open(로그, "w", encoding="utf-8") as f:
        for r in 옛:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # ③ 한 줄 요약
    줄 = [f"임원 함께 매수 예측 기록 — 전체 {len(옛)}건 · 오늘 새로 {새}건 · 새로 채점 {채}칸"]
    for h in 지평:
        vs = [r["채점"][f"D+{h}"]["시장대비"] for r in 옛 if f"D+{h}" in r.get("채점", {})]
        if vs:
            줄.append(f"D+{h} {len(vs)}건 · 시장 대비 평균 {st.mean(vs):+.2f}% · 이긴 비율 {sum(1 for z in vs if z > 0) / len(vs) * 100:.0f}%")
    print(" · ".join(줄))
    print("[대조] 임원 함께 예측 기록 끝")


if __name__ == "__main__":
    main()
