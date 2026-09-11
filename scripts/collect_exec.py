#!/usr/bin/env python3
r"""
collect_exec.py — **임원·주요주주 자사주 매매를 전 종목 소급 수집** (2026-09-01 신설)

⚠️⚠️ **왜 받나.** 점수표의 `강화-D1`이 **±2점**짜리다:
```
한국 임원 자사주매수(30일 이내)      +2
대표이사·등기임원 대량매도(30일 이내) −2
```
등급을 실제로 가르는 항목인데, **과거 데이터가 없어서 소급 검증이 안 됐다.**
이걸 받으면 「저장된 데이터로 다시 계산되는 점수 항목」이 **6개 → 7개**가 된다.

✅ **DART `elestock.json`은 corp_code 하나로 그 회사 「전체 이력」을 준다.**
   날짜별로 부를 필요가 없다 → **종목당 1회, 총 2,766회**로 끝난다.
   (수급이 19만 회였던 것과 비교하면 아주 가볍다)

⚠️ **이어받는다.** 이미 받은 종목은 건너뛴다. 죽어도 다시 돌리면 된다.
⚠️ **호출 사이 쉰다** — 2026-09-01에 PC가 과부하로 얼어붙은 적이 있다.

저장: `data/dart-exec/{종목코드}.json`

쓰는 법:
    python scripts\collect_exec.py            # 안 받은 것만
    python scripts\collect_exec.py --확인       # 몇 개 남았는지만
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
KRX = os.path.join(_DATA, "krx-daily")
OUT = os.path.join(_DATA, "dart-exec")
LOG = os.path.join(_DATA, "_exec.log")
CORP = os.path.join(_DATA, "dart-corpcode.json")

_쉼 = 0.02          # DART는 분당 제한이 있다. 넉넉히 쉰다


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def main():
    확인만 = "--확인" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    최신 = sorted(glob.glob(os.path.join(KRX, "*.json")))[-1]
    종목 = json.load(io.open(최신, encoding="utf-8-sig"))["종목"]
    corp = json.load(io.open(CORP, encoding="utf-8-sig"))
    받 = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(OUT, "*.json"))}
    # ⭐⭐ **--갱신일 N** (2026-09-09 신설) — 파일이 N일보다 오래됐으면 **다시 받는다**.
    #    ⚠️ 이게 없어서 2026-09-01 이후 **8일간 한 건도 갱신되지 않았다.**
    #       종목 단위로 「이미 받았으면 건너뛴다」라서, 2,650종목이 다 받아진 뒤로는
    #       새 매매가 생겨도 영영 안 받았다 (소급 수집용으로 만든 탓이다).
    #    저녁 수집이 주 1회 부르므로 **--갱신일 6** 이면 매주 전체가 갱신된다
    _갱신일 = 0
    if "--갱신일" in sys.argv:
        _갱신일 = int(sys.argv[sys.argv.index("--갱신일") + 1])
    if _갱신일 > 0:
        import time as _time
        _낡음 = _time.time() - _갱신일 * 86400
        받 = {c for c in 받
              if os.path.getmtime(os.path.join(OUT, f"{c}.json")) >= _낡음}

    # ⚠️ corp_code가 없는 종목은 DART에 없다(스팩·리츠 일부). 건너뛴다.
    할것 = [(c, corp[c]["corp_code"]) for c in 종목
            if c in corp and c not in 받]
    없음 = [c for c in 종목 if c not in corp]

    찍기(f"  전 종목 {len(종목):,} · 이미 받음 {len(받):,} · "
         f"corp_code 없음 {len(없음):,} · 받을 것 {len(할것):,}")
    찍기(f"  예상 시간 약 {len(할것) * (_쉼 + 0.25) / 60:.0f}분")
    if 확인만 or not 할것:
        찍기("  받을 것이 없다." if not 할것 else "  --확인 이라 받지 않았다.")
        return 0

    ok = 빈 = 실패 = 0
    for i, (code, cc) in enumerate(할것, 1):
        try:
            # ⚠️ `executive_stock`은 최신 12건만 준다. 소급이 목적이라 **전부** 받는다.
            d = D.api("elestock.json", corp_code=cc)
            if d.get("status") == "013":
                rows = []
            elif d.get("status") != "000":
                raise RuntimeError(f"DART {d.get('status')}")
            else:
                rows = d.get("list") or []
            잘 = [{"접수일": r.get("rcept_dt"), "성명": r.get("repror"),
                   "직위": r.get("isu_exctv_ofcps"),
                   "등기": r.get("isu_exctv_rgist_at"),
                   "주요주주": r.get("isu_main_shrholdr"),
                   "변동후": r.get("sp_stock_lmp_cnt"),
                   "증감": r.get("sp_stock_lmp_irds_cnt"),
                   "사유": r.get("sp_stock_lmp_irds_rson")} for r in rows]
            io.open(os.path.join(OUT, code + ".json"), "w", encoding="utf-8").write(
                json.dumps({"종목": code, "건수": len(잘), "이력": 잘}, ensure_ascii=False))
            ok += 1
            빈 += 1 if not 잘 else 0
        except Exception as e:
            실패 += 1
            if 실패 <= 3:
                찍기(f"    ⚠️ {code}: {type(e).__name__} {e}")
        time.sleep(_쉼)
        if i % 200 == 0:
            찍기(f"    {i:,}/{len(할것):,} — 성공 {ok:,} (이력없음 {빈:,}) 실패 {실패}")
    찍기(f"  끝 — 성공 {ok:,} · 이력없음 {빈:,} · 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
