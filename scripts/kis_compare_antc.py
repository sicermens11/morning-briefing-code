#!/usr/bin/env python3
r"""
kis_compare_antc.py — **08:56 한국투자증권 예상체결가를 받아 NH 값과 나란히 적는다** (2026-10-22 신설 · 조회만)

왜: 지금 08:55 판정은 NH 예상체결가로 한다. 자동매매를 한국투자증권으로 옮기려면 두 값이 같은지 **확인차** 한두 번 본다.
    같으면 그다음엔 안 한다(KIS 하나로 갈지 정한다). 사용자 10/22 「가(권고)로 하자」.
⚠️ 조회만 · 주문 없음 · forward-log 는 읽기만(쓰지 않는다) · 휴장일엔 아무것도 안 한다
출력: data/kis-antc/YYYYMMDD_HHMM.json (KIS 원본 output2 그대로 — 칸 이름 확인용) · data/_kis_compare.log (NH 대 KIS 한 줄씩)
"""
import datetime as dt
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_B, "scripts"))
_LOG = os.path.join(_B, "data", "_kis_compare.log")


def 적기(s):
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄)
    with io.open(_LOG, "a", encoding="utf-8") as f:
        f.write(줄 + "\n")


def main():
    from krx_calendar import 장서는날
    선다, 왜 = 장서는날()
    if not 선다:
        적기(f"휴장 — 안 한다 ({왜})")
        return 0
    import kis_api
    줄들 = [json.loads(z) for z in io.open(os.path.join(_B, "data", "forward-log.jsonl"), encoding="utf-8") if z.strip()]
    끝 = 줄들[-1]
    오늘 = dt.date.today().isoformat()
    if str(끝.get("기록시각") or "")[:10] != 오늘:
        적기(f"오늘 기록이 아직 없다(마지막 {str(끝.get('기록시각'))[:10]}) — 안 한다")
        return 1
    동 = 끝.get("동시호가") or {}
    NH = {}
    for k in ("종목별", "보완종목별"):
        for c, v in (동.get(k) or {}).items():
            if v.get("예상시가"):
                NH[c] = float(v["예상시가"])
    후보 = [(x["종목코드"], x.get("이름", "")) for x in (끝.get("후보") or [])] + \
           [(x["종목코드"], x.get("이름", "")) for x in (끝.get("보완후보") or [])]
    본 = set()
    후보 = [z for z in 후보 if not (z[0] in 본 or 본.add(z[0]))]
    k = kis_api.KIS("모의")
    적기(f"===== 시작 · 후보 {len(후보)}개 · NH 예상가 있는 것 {len(NH)}개 =====")
    원본, 차이들, 받음, 실패 = {}, [], 0, 0
    for c, 이름 in 후보:
        try:
            r = k.예상체결(c)
        except Exception as e:  # noqa: BLE001
            실패 += 1
            적기(f"  ✗ {이름} {c}: {str(e)[:80]}")
            continue
        받음 += 1
        예 = r.get("예상") or {}
        원본[c] = {"이름": 이름, "예상": 예, "호가_키": list((r.get("호가") or {}).keys())[:40]}
        try:
            kis = float(예.get("antc_cnpr") or 0)
        except (TypeError, ValueError):
            kis = 0.0
        nh = NH.get(c)
        if nh and kis:
            d = (kis / nh - 1) * 100
            차이들.append(abs(d))
            적기(f"  {이름:<10} NH {nh:>10,.0f}  KIS {kis:>10,.0f}  차이 {d:+.2f}%")
        else:
            적기(f"  {이름:<10} NH {nh if nh else '없음':>10}  KIS {kis if kis else '없음':>10}")
    os.makedirs(os.path.join(_B, "data", "kis-antc"), exist_ok=True)
    out = os.path.join(_B, "data", "kis-antc", f"{dt.datetime.now():%Y%m%d_%H%M}.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump({"받은때": dt.datetime.now().isoformat(timespec="seconds"), "NH": NH, "KIS": 원본}, f, ensure_ascii=False, indent=1)
    if 차이들:
        적기(f"===== 끝 · 받음 {받음} · 실패 {실패} · 둘 다 있는 것 {len(차이들)} · 차이 평균 {sum(차이들) / len(차이들):.3f}% · 최대 {max(차이들):.2f}% · 0.5% 넘는 것 {sum(1 for z in 차이들 if z > 0.5)} → {out} =====")
    else:
        적기(f"===== 끝 · 받음 {받음} · 실패 {실패} · 견줄 값 없음 → {out} =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
