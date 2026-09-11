#!/usr/bin/env python3
r"""
collect_fin.py — **연간 재무제표를 한 해치 받는다** (2026-09-01 신설)

⚠️⚠️ **왜 2023년치가 필요한가 — Piotroski F-Score 때문이다.**
   사용자 질문: *"뻔한 정답이 나왔다면, 굳이 우리 점수표가 아니라 검증된 점수표를 채용해도 되지 않아?"*
   → **부분 채용이 답이다.** 재무 부분은 **F-Score(1998년 발표, 40년 검증)**가
      우리 「재무취약(−2)」보다 근거가 훨씬 단단하다.
```
우리 재무취약   부채비율 200%+ 또는 순이익률 음수      항목 2개, 검증 0
F-Score       ROA·현금흐름·부채·유동비율·발생액…      항목 9개, 40년 검증
```
⚠️⚠️ **F-Score는 「전년 대비」 비교가 절반이다.** 그래서 Y년 점수를 내려면 **Y-1년**이 필요하다.
```
지금(2024·2025만)  F-Score(2025)만 가능 → **2026-04부터 약 100일**만 쓸 수 있다
2023을 받으면      F-Score(2024)도 가능 → **2025-04부터 약 350일**로 늘어난다
```

⚠️ `fnlttMultiAcnt.json`은 **corp_code 5개를 한 번에** 받는다 → 2,526종목이 약 505회.
⚠️ 이어받는다. 파일이 이미 있으면 안 받는다.

쓰는 법:
    python scripts\collect_fin.py --해 2023
    python scripts\collect_fin.py --해 2023 --확인
"""
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_dart as D  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
OUT = os.path.join(_DATA, "dart-fin")
CORP = os.path.join(_DATA, "dart-corpcode.json")
KRX = os.path.join(_DATA, "krx-daily")
LOG = os.path.join(_DATA, "_fin.log")
_쉼 = 0.05

# ⚠️ 기존 2024·2025 파일과 **같은 항목 이름**을 쓴다. 안 그러면 F-Score가 안 붙는다.
_항목 = ("유동자산", "비유동자산", "자산총계", "유동부채", "비유동부채", "부채총계",
         "자본금", "이익잉여금", "자본총계", "매출액", "영업이익",
         "법인세차감전 순이익", "당기순이익(손실)", "총포괄손익", "영업비용")


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def main():
    확인만 = "--확인" in sys.argv
    해 = sys.argv[sys.argv.index("--해") + 1] if "--해" in sys.argv else "2023"
    p = os.path.join(OUT, f"{해}.json")
    if os.path.exists(p):
        찍기(f"  {해}.json 이 이미 있다 — 받지 않는다.")
        return 0
    corp = json.load(io.open(CORP, encoding="utf-8-sig"))
    종목 = json.load(io.open(sorted(glob.glob(os.path.join(KRX, "*.json")))[-1],
                             encoding="utf-8-sig"))["종목"]
    쌍 = [(c, corp[c]["corp_code"]) for c in 종목 if c in corp]
    묶음 = [쌍[i:i + 5] for i in range(0, len(쌍), 5)]
    찍기(f"  {해}년 · 종목 {len(쌍):,} · 묶음 {len(묶음):,}회 "
         f"· 예상 약 {len(묶음)*(_쉼+0.3)/60:.0f}분")
    if 확인만:
        찍기("  --확인 이라 받지 않았다.")
        return 0

    out, ok, 실패 = {}, 0, 0
    역 = {v["corp_code"]: c for c, v in corp.items() if c in 종목}
    for i, 덩 in enumerate(묶음, 1):
        try:
            d = D.api("fnlttMultiAcnt.json",
                      corp_code=",".join(x[1] for x in 덩),
                      bsns_year=해, reprt_code="11011")
            for r in (d.get("list") or []):
                c = 역.get(r.get("corp_code"))
                nm = r.get("account_nm")
                if not c or nm not in _항목:
                    continue
                v = _n(r.get("thstrm_amount"))
                if v is not None:
                    out.setdefault(c, {})[nm] = v
            ok += 1
        except Exception:
            실패 += 1
        time.sleep(_쉼)
        if i % 100 == 0:
            찍기(f"    {i:,}/{len(묶음):,} — 종목 {len(out):,} 실패 {실패}")
    os.makedirs(OUT, exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    찍기(f"  끝 — {해}년 {len(out):,}종목 저장 · 묶음 성공 {ok:,} 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
