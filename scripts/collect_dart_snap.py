#!/usr/bin/env python3
r"""
collect_dart_snap.py — **DART 사업보고서 항목을 전 종목 소급 수집** (2026-09-01 신설)

⚠️⚠️ **`elestock`·`majorstock`과 다르다.** 그 둘은 `rcept_dt`가 있어 **날짜 단위 이벤트**지만,
   여기 항목들은 **사업보고서 기준 = 연 단위 스냅샷**이다. "그 해에 어땠나"만 안다.
   ⚠️ 그래서 **look-ahead를 조심해야 한다** — 2024 사업보고서는 2025년 3~4월에 나온다.
      쓰려면 **다음 해 4월부터** 적용한다(연간 재무에 이미 쓰는 규칙과 같다).

**받는 것**
```
자기주식   tesstkAcqsDspsSttus  ⭐⭐⭐ 자사주 취득·처분. 자사주 매입은 알려진 강한 신호
소액주주   mrhlSttus            ⭐⭐  유통물량 비율. 물량이 적으면 변동성이 크다
증자감자   irdsSttus            ⭐   `강화-CAP`의 유상증자를 **공시 텍스트가 아니라 데이터로**
배당      alotMatter           🔸
```

⚠️⚠️ **DART 하루 한도 20,000회.** 한 항목당 2,650종목 × 2년 = 5,300회다.
   `--상한`으로 이번 실행의 호출 수를 묶을 수 있다. 넘기면 **다음날 아침 브리핑이 DART를 못 부른다.**

⚠️ 이어받는다. 이미 받은 (항목, 종목)은 건너뛴다.

저장: `data/dart-snap/{항목}/{종목코드}.json`

쓰는 법:
    python scripts\collect_dart_snap.py --항목 자기주식
    python scripts\collect_dart_snap.py --항목 자기주식 --확인
    python scripts\collect_dart_snap.py --항목 소액주주 --상한 4000
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
CORP = os.path.join(_DATA, "dart-corpcode.json")
OUTB = os.path.join(_DATA, "dart-snap")
LOG = os.path.join(_DATA, "_dartsnap.log")

항목표 = {
    "자기주식": "tesstkAcqsDspsSttus",
    "소액주주": "mrhlSttus",
    "증자감자": "irdsSttus",
    "배당": "alotMatter",
    "최대주주": "hyslrSttus",
}
해 = ("2024", "2025")          # ⚠️ 2026 사업보고서는 아직 안 나온다
# ⚠️ 2026-09-01 PC 과부하는 **사용자의 대용량 복사** 탓이었다(사용자 확인).
#    수집 부하가 원인이 아니어서 쉼을 줄였다 — 항목당 약 4분 빨라진다.
_쉼 = 0.02


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


def main():
    확인만 = "--확인" in sys.argv
    이름 = sys.argv[sys.argv.index("--항목") + 1] if "--항목" in sys.argv else None
    상한 = int(sys.argv[sys.argv.index("--상한") + 1]) if "--상한" in sys.argv else 10 ** 9
    if 이름 not in 항목표:
        찍기(f"  --항목 이 필요하다. 고를 수 있는 것: {' · '.join(항목표)}")
        return 1
    ep = 항목표[이름]
    OUT = os.path.join(OUTB, 이름)
    os.makedirs(OUT, exist_ok=True)

    종목 = json.load(io.open(sorted(glob.glob(os.path.join(KRX, "*.json")))[-1],
                             encoding="utf-8-sig"))["종목"]
    corp = json.load(io.open(CORP, encoding="utf-8-sig"))
    받 = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(OUT, "*.json"))}
    # ⭐ **--갱신일 N** (2026-09-09) — 파일이 N일보다 오래됐으면 다시 받는다.
    #    ⚠️ 없으면 **종목 단위**로 영영 건너뛴다 (임원매매가 8일 멈춘 그 병).
    #    사업보고서는 연 1회지만 **3~4월 갱신을 놓치면 안 된다**
    _갱신일 = 0
    if "--갱신일" in sys.argv:
        _갱신일 = int(sys.argv[sys.argv.index("--갱신일") + 1])
    if _갱신일 > 0:
        import time as _time
        _낡음 = _time.time() - _갱신일 * 86400
        받 = {c for c in 받
              if os.path.exists(os.path.join(OUT, f"{c}.json"))
              and os.path.getmtime(os.path.join(OUT, f"{c}.json")) >= _낡음}
    할것 = [(c, corp[c]["corp_code"]) for c in 종목 if c in corp and c not in 받]

    찍기(f"  [{이름}] 전 종목 {len(종목):,} · 이미 받음 {len(받):,} · 받을 것 {len(할것):,}")
    찍기(f"  예상 호출 {len(할것)*len(해):,}회 (상한 {상한:,}) "
         f"· 예상 시간 약 {min(len(할것)*len(해), 상한)*(_쉼+0.25)/60:.0f}분")
    if 확인만 or not 할것:
        찍기("  받을 것이 없다." if not 할것 else "  --확인 이라 받지 않았다.")
        return 0

    호출 = ok = 빈 = 실패 = 0
    for i, (code, cc) in enumerate(할것, 1):
        if 호출 + len(해) > 상한:
            찍기(f"  ⚠️ 상한 {상한:,}회에 닿았다. {i-1:,}종목까지 하고 멈춘다 "
                 f"(다시 돌리면 이어받는다)")
            break
        모 = {}
        for y in 해:
            try:
                d = D.api(ep + ".json", corp_code=cc, bsns_year=y, reprt_code="11011")
                호출 += 1
                모[y] = (d.get("list") or []) if d.get("status") == "000" else []
            except Exception:
                실패 += 1
                모[y] = []
            time.sleep(_쉼)
        io.open(os.path.join(OUT, code + ".json"), "w", encoding="utf-8").write(
            json.dumps({"종목": code, "항목": 이름, "해별": 모}, ensure_ascii=False))
        ok += 1
        빈 += 1 if not any(모.values()) else 0
        if i % 250 == 0:
            찍기(f"    {i:,}/{len(할것):,} — 호출 {호출:,} 성공 {ok:,} "
                 f"(자료없음 {빈:,}) 실패 {실패}")
    찍기(f"  [{이름}] 끝 — 종목 {ok:,} · 호출 {호출:,} · 자료없음 {빈:,} · 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
