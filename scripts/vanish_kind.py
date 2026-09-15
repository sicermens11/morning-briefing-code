#!/usr/bin/env python3
r"""
vanish_kind.py — **사라진 종목이 왜 사라졌나** (2026-09-15 신설 · ㉠-3)

## 왜
```
시뮬은 보유 중 자료가 끊기면 `_사라짐` 이면 **−50%** 로 친다 (2026-09-08 고침).
소형주는 맞다 — 사라짐 = 상장폐지·정리매매다.
대형주는 아니다 — **합병 · 주식교환 · 공개매수 · 지주회사 전환**이 대부분이고
그때 주주는 신주나 현금을 받는다. 손실이 아니라 흔히 **이익**이다.

BIG판(2026-09-15 · 크기 무제한): 2023 낙폭 −79.1% — 2023 에 사라진 2,000억↑ 12개 중
8개가 사라지기 직전 규칙에 걸렸다 (메리츠증권 합병 20일 전 · 069110 마지막 날까지 6일 연속).
```

## 무엇을 만드나
`data/vanish-kind.json`  —  종목코드 -> {마지막, 종류, 근거, 근거날}
```
  종류   상장폐지   「상장폐지」「정리매매」「상장폐지결정」        -> 시뮬은 −50% 그대로
        공개매수   「공개매수」「자진상장폐지」                   -> 마지막 종가로 판 것으로
        합병      「합병」「주식교환」「주식이전」「분할합병」        -> 마지막 종가로 판 것으로
        모름      아무 공시도 없다                             -> −50% 그대로 (모르면 나쁜 쪽)
```
마지막 등장일 앞 **120 거래일 ~ 뒤 30일** 의 dart 공시명을 본다. 여러 개면 **상장폐지 > 공개매수 > 합병** 순.
⚠️ 종목코드가 빈 공시가 많다 — 종목명으로도 맞춘다 (stock-base 이름표).

쓰는 법:
    python scripts\vanish_kind.py            -> data/vanish-kind.json + 규모대별 요약
"""
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import omni_lab as O  # noqa: E402

# ⚠️ 「상장폐지 **우려** 안내」「실질심사」는 경고지 결정이 아니다 — 오스템(048260)이 이걸로
#    상장폐지로 잡혔는데 실제는 공개매수였다. **결정·정리매매·승인**만 상장폐지로 본다
_말 = (("상장폐지", ("상장폐지결정", "상장폐지 결정", "정리매매", "상장폐지승인")),
       ("공개매수", ("공개매수", "자진상장폐지")),
       ("합병", ("분할합병", "주식교환", "주식이전", "합병")))
# ⚠️ 여러 개면 **원인**을 고른다 — 공개매수·합병 뒤에는 「상장폐지결정」이 **결과**로 따라온다.
#    오스템(048260): 공개매수(2023-01) → 상장폐지결정(2023-05). 주주는 공개매수가를 받았다
_순위 = {"공개매수": 0, "합병": 1, "상장폐지": 2}


def main():
    주가, 비, 갭표, 원시, 거량 = O.krx한번읽기()
    날 = sorted(주가)
    자리 = {d: i for i, d in enumerate(날)}
    사라짐 = O.사라진종목(주가, 날)
    print(f"  거래일 {len(날):,} · 사라진 종목 {len(사라짐):,}개", flush=True)

    이름 = {}
    try:
        _b = json.load(io.open(os.path.join(O._DATA, "stock-base.json"), encoding="utf-8-sig"))
        for c, v in (_b.get("종목") or _b).items():
            if isinstance(v, dict):
                n = (v.get("종목명") or v.get("이름") or "").strip()
                if n:
                    이름[c] = n
    except Exception:  # noqa: BLE001
        pass
    이름역 = {n: c for c, n in 이름.items() if n}

    # 종목마다 볼 날짜 창
    창 = {}
    for c, d in 사라짐.items():
        i = 자리.get(d, 0)
        시작 = 날[max(0, i - 120)]
        창[c] = (시작, d)
    끝날들 = sorted(사라짐.values())
    최소, 최대 = 날[max(0, 자리.get(끝날들[0], 0) - 120)], 끝날들[-1]

    # dart-daily 한 번 훑기
    후보 = {}      # code -> [(d8, 종류, 공시명)]
    파일들 = sorted(glob.glob(os.path.join(O._DATA, "dart-daily", "*.json")))
    n파일 = 0
    for f in 파일들:
        d8 = os.path.basename(f)[:8]
        if d8 < 최소:
            continue
        # 마지막 등장일 뒤 30 거래일까지만 본다 — 대략 45 달력일
        try:
            j = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        n파일 += 1
        for 칸 in ("챙길공시", "그밖의공시"):
            for x in (j.get(칸) or []):
                명 = str(x.get("공시명") or "")
                종류 = None
                for k, 말들 in _말:
                    if any(m in 명 for m in 말들):
                        종류 = k
                        break
                if not 종류:
                    continue
                code = str(x.get("종목코드") or "").strip()
                if not code:
                    code = 이름역.get(str(x.get("종목명") or "").strip(), "")
                if code not in 사라짐:
                    continue
                s, e = 창[code]
                if d8 < s:
                    continue
                if 자리.get(d8, len(날)) > 자리.get(e, 0) + 30 and d8 > e:
                    continue
                후보.setdefault(code, []).append((d8, 종류, 명[:60]))
    print(f"  dart-daily {n파일:,}개 훑음 · 공시가 걸린 종목 {len(후보):,}개", flush=True)

    표 = {}
    for c, d in 사라짐.items():
        벌 = 후보.get(c) or []
        if 벌:
            벌.sort(key=lambda z: (_순위[z[1]], z[0]))
            d8, 종류, 명 = 벌[0]
        else:
            d8, 종류, 명 = "", "모름", ""
        표[c] = {"마지막": d, "종류": 종류, "근거": 명, "근거날": d8,
                 "이름": 이름.get(c, "")}

    밖 = os.path.join(O._DATA, "vanish-kind.json")
    json.dump(표, io.open(밖, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"  ✅ {밖}\n")

    # ── 규모대별 요약 (사라지기 직전 시총) ──
    띠 = (("소형 <2,000억", 0, 2000), ("중형 2,000억~1조", 2000, 10000),
          ("대형 1조↑", 10000, 9e9))
    셈 = {라: {} for 라, _, _ in 띠}
    for c, r in 표.items():
        v = (주가.get(r["마지막"]) or {}).get(c)
        s = (v[1] / 1e8) if v else 0
        for 라, lo, hi in 띠:
            if lo <= s < hi:
                셈[라][r["종류"]] = 셈[라].get(r["종류"], 0) + 1
                break
    print("=" * 84)
    print("  ⭐ 사라진 이유 — 규모대별 (사라지기 직전 시총)")
    print("     소형은 상장폐지가 많아야 하고, 대형은 합병·공개매수가 많아야 말이 된다")
    print("=" * 84)
    print(f"  {'규모대':<18}{'상장폐지':>9}{'공개매수':>9}{'합병':>7}{'모름':>7}{'합':>7}")
    for 라, _, _ in 띠:
        z = 셈[라]
        print(f"  {라:<18}{z.get('상장폐지', 0):>9}{z.get('공개매수', 0):>9}"
              f"{z.get('합병', 0):>7}{z.get('모름', 0):>7}{sum(z.values()):>7}")

    print("\n  ── 2023 에 사라진 2,000억↑ (BIG판 −79% 의 용의자들) ──")
    for c, r in sorted(표.items(), key=lambda z: z[1]["마지막"]):
        if not ("20230101" <= r["마지막"] <= "20231231"):
            continue
        v = (주가.get(r["마지막"]) or {}).get(c)
        if not v or v[1] < 2000e8:
            continue
        print(f"    {c} {r['이름']:<14} {r['마지막']}  {v[1]/1e8:>8,.0f}억  "
              f"**{r['종류']}**  {r['근거날']} {r['근거']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
