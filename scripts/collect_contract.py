#!/usr/bin/env python3
r"""
collect_contract.py — **계약·수주 공시의 「금액」을 받는다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 지금은 「단일판매·공급계약체결」을 **호재 공시 한 덩어리**로 본다.
   그런데 **15억 계약과 1조 계약은 완전히 다르다.**
   `계약금액 ÷ 시가총액` 이 진짜 신호 강도인데 한 번도 안 재봤다.

✅ **DART `document.xml`이 공시 원문을 ZIP으로 준다**(2026-09-01 확인).
   한 건 약 3KB. 정규식으로 계약금액을 뽑는다.
```
예: 네이블 2026-08-31 단일판매·공급계약 → 계약금액 1,567,139,040원 (15.7억)
```

⚠️⚠️ **DART 하루 한도 20,000회.** 계약·수주 공시가 **13,412건**이라 하루 안에 끝나지만
   다른 수집과 겹치면 넘긴다. 그래서 `--상한`으로 묶는다.
⚠️ 이어받는다. 이미 받은 접수번호는 건너뛴다.

저장: `data/contract/{YYYYMM}.json`  →  `{접수번호: {코드, 날짜, 금액, 매출대비, 상대}}`

쓰는 법:
    python scripts\collect_contract.py
    python scripts\collect_contract.py --확인
    python scripts\collect_contract.py --상한 13500
"""
import glob
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
OUT = os.path.join(_DATA, "contract")
LOG = os.path.join(_DATA, "_contract.log")
_쉼 = 0.02
# ⚠️⚠️ **2026-09-10 좁힘** (사용자 결정: 「진짜 계약만 + 자사주 따로」)
#    전: ("단일판매", "공급계약", "수주", **"계약체결"**)
#    「계약체결」이 **계약이 아닌 것**을 다 끌어왔다 (실측 · 금액 0건):
#        최대주주변경을수반하는주식담보제공계약체결   3,279건
#        최대주주변경을수반하는주식양수도계약체결     1,900건
#        유동성공급계약의체결/변경                  172건
#                                        합계 **5,351건 헛수고**
_계약 = ("단일판매", "공급계약", "수주")
# ⭐ **빼는 것** — 위 이름이 「공급계약」에도 걸리므로 따로 막는다
_제외 = ("최대주주변경", "유동성공급계약")
# ⭐ **자사주는 따로** (2026-09-10) — 금액이 1,189건 있어 값어치가 있지만
#    계약·수주와 **완전히 다른 재료**다. `data/buyback/` 에 따로 쌓는다
_자사주 = ("자기주식취득신탁",)
BUYBACK = os.path.join(_DATA, "buyback")

# ⚠️ 공시 서식이 여러 가지다. 넉넉히 여러 패턴을 본다.
_금액 = [
    re.compile(r"계약금액[^0-9\-]{0,40}([0-9,]{4,})"),
    re.compile(r"공급계약금액[^0-9\-]{0,40}([0-9,]{4,})"),
    re.compile(r"수주금액[^0-9\-]{0,40}([0-9,]{4,})"),
]
_비중 = re.compile(r"매출액\s*대비[^0-9\-]{0,40}([0-9.]{1,8})")


def 찍기(s):
    print(s, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(s + "\n")


자사주 = []          # ⭐ _대상() 이 채운다 (2026-09-10) — data/buyback/ 용


def _대상():
    """[(달, 접수번호, 코드, 날짜, 공시명)] — 계약·수주 공시만."""
    out = []
    for f in sorted(glob.glob(os.path.join(_DATA, "dart-daily", "*.json"))):
        d8 = os.path.basename(f)[:8]
        try:
            g = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        for x in (g.get("챙길공시") or []):
            nm = re.sub(r"\[[^\]]*\]", "", x.get("공시명") or "")
            rc, c = x.get("접수번호"), x.get("종목코드")
            if not (rc and c):
                continue
            # ⭐ 2026-09-10 — 자사주는 **따로** 담는다 (계약이 아니다)
            if any(k in nm for k in _자사주):
                자사주.append((d8[:6], str(rc), c, d8, nm[:40]))
                continue
            # ⭐ 계약이 아닌데 「계약」 글자가 든 것들을 막는다
            if any(k in nm for k in _제외):
                continue
            if not any(k in nm for k in _계약):
                continue
            out.append((d8[:6], str(rc), c, d8, nm[:40]))
    return out


class 한도초과(RuntimeError):
    r"""DART 하루 한도(20,000회)를 넘겼다 — **더 두드려봐야 소용없다**"""


def _뽑기(rc, key):
    u = f"https://opendart.fss.or.kr/api/document.xml?crtfc_key={key}&rcept_no={rc}"
    b = urllib.request.urlopen(u, timeout=30).read()
    if b[:2] != b"PK":
        # ⚠️⚠️ **2026-09-10 고침** — 전에는 여기서 조용히 `None, None` 을
        #    돌려줬다. 그러면 호출자가 **「성공」으로 세고 금액 없는 껍데기를
        #    저장**한다. 2026-09-10 00:37 에 「성공 13,500 · 금액 못 뽑음
        #    **13,500**」 이 그렇게 나왔다 — DART 한도가 초과됐는데도
        #    13,500번을 계속 두드린 것이다
        _s = b[:400].decode("utf-8", "replace")
        if "020" in _s or "한도" in _s:
            raise 한도초과("DART 020: 사용한도를 초과하였습니다")
        return None, None
    z = zipfile.ZipFile(io.BytesIO(b))
    _raw = z.read(z.namelist()[0])
    # ⚠️⚠️ **2026-09-11 고침** — DART 공시 원문은 **EUC-KR** 이다.
    #    전에는 `decode("utf-8","replace")` 로 읽어 **한글이 전부 깨졌고**,
    #    그래서 「계약금액」을 한 번도 못 찾았다.
    #    2026-09-11 00:16 밤샘: 「성공 5,000 · **금액 못 뽑음 5,000**」
    #    실측: <meta charset="euc-kr"> · 원본 b'µ¸¿òÃ¼' (= 굴림체)
    t = None
    for _enc in ("euc-kr", "cp949", "utf-8"):
        try:
            _try = _raw.decode(_enc)
        except (UnicodeDecodeError, LookupError):
            continue
        # 제대로 읽혔는지는 **한글이 나오는지**로 본다
        if "계약" in _try or "공시" in _try or "회사" in _try:
            t = _try
            break
    if t is None:
        t = _raw.decode("cp949", "replace")
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
    금 = None
    for pat in _금액:
        m = pat.search(t)
        if m:
            try:
                금 = int(m.group(1).replace(",", ""))
            except ValueError:
                금 = None
            if 금:
                break
    비 = None
    m = _비중.search(t)
    if m:
        try:
            비 = float(m.group(1))
        except ValueError:
            비 = None
    return 금, 비


def main():
    확인만 = "--확인" in sys.argv
    상한 = int(sys.argv[sys.argv.index("--상한") + 1]) if "--상한" in sys.argv else 10 ** 9
    key = config.get("DART_API_KEY")
    os.makedirs(OUT, exist_ok=True)
    대상 = _대상()
    받 = {}
    for f in glob.glob(os.path.join(OUT, "*.json")):
        try:
            받.update(json.load(io.open(f, encoding="utf-8-sig")).get("건", {}))
        except Exception:
            pass
    할것 = [x for x in 대상 if x[1] not in 받]
    찍기(f"  계약·수주 공시 {len(대상):,}건 · 이미 받음 {len(받):,} · 받을 것 {len(할것):,}")
    찍기(f"  상한 {상한:,}회 · 예상 약 {min(len(할것), 상한)*(_쉼+0.28)/60:.0f}분")
    if 확인만 or not 할것:
        찍기("  받을 것이 없다." if not 할것 else "  --확인 이라 받지 않았다.")
        return 0

    달별 = {}
    호출 = ok = 빈 = 실패 = 0
    for i, (달, rc, code, d8, nm) in enumerate(할것, 1):
        if 호출 >= 상한:
            찍기(f"  ⚠️ 상한 {상한:,}회 도달 — {i-1:,}건까지 하고 멈춘다 (다시 돌리면 이어받는다)")
            break
        try:
            금, 비 = _뽑기(rc, key)
            호출 += 1
            달별.setdefault(달, {})[rc] = {"코드": code, "날짜": d8,
                                           "금액": 금, "매출대비pct": 비, "공시명": nm}
            ok += 1
            빈 += 1 if 금 is None else 0
        except 한도초과 as e:
            # ⭐ **즉시 멈춘다** (2026-09-10). 한도가 넘으면 계속 두드려도
            #    껍데기만 쌓이고, **다른 수집(공시·임원·대량보유)이 굶는다**
            찍기(f"  ⚠️⚠️ **{e}** — {i-1:,}건까지 하고 **멈춘다**")
            찍기("     (자정에 리셋된다. 내일 이어받는다)")
            break
        except Exception:
            실패 += 1
        time.sleep(_쉼)
        if i % 1000 == 0:
            찍기(f"    {i:,}/{len(할것):,} — 성공 {ok:,} (금액없음 {빈:,}) 실패 {실패}")
            for 달, 표 in 달별.items():
                p = os.path.join(OUT, 달 + ".json")
                기존 = {}
                if os.path.exists(p):
                    try:
                        기존 = json.load(io.open(p, encoding="utf-8-sig")).get("건", {})
                    except Exception:
                        pass
                기존.update(표)
                io.open(p, "w", encoding="utf-8").write(
                    json.dumps({"달": 달, "건수": len(기존), "건": 기존}, ensure_ascii=False))
            달별 = {}
    for 달, 표 in 달별.items():
        p = os.path.join(OUT, 달 + ".json")
        기존 = {}
        if os.path.exists(p):
            try:
                기존 = json.load(io.open(p, encoding="utf-8-sig")).get("건", {})
            except Exception:
                pass
        기존.update(표)
        io.open(p, "w", encoding="utf-8").write(
            json.dumps({"달": 달, "건수": len(기존), "건": 기존}, ensure_ascii=False))
    찍기(f"  끝 — 성공 {ok:,} · 금액 못 뽑음 {빈:,} · 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
