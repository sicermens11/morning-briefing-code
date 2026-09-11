#!/usr/bin/env python3
r"""
field_count.py — **정보의 「종류」가 몇 가지인지 제대로 센다** (2026-09-07 신설)

## 왜 field_audit 로 안 되나
```
field_audit 는 「필드 949개」라고 한다. 그런데 그 안에는
  etf-krx 57개    = 0004G0 · 0008E0 …   ← **ETF 종목코드**다
  index-daily 78개 = 건설 · 금융 · 기계·장비 … ← **업종 이름**이다
  krx-daily 18개   = 00104K · 37550K …   ← **종목코드**다
  snapshots 256개  = 우리가 **만든** 브리핑 결과물이지 수집한 자료가 아니다
⇒ 「몇 가지 정보를 갖고 있나」를 물으면 저 숫자로 답하면 안 된다
```

## 그래서 이렇게 센다
```
① 우리가 **받아온** 폴더만 본다 (만든 결과물·설정·열쇠는 뺀다)
② 키가 **코드**로 보이면 뺀다 (005930 · 0004G0 · 00104K 꼴)
③ 남은 것이 **정보의 종류**다. 폴더별로 세고, 써봤나 대조한다
```
⚠️ ②의 판정: 6자리이고 숫자가 섞였고 한글이 없으면 코드로 본다.
   업종 이름(건설·금융)은 한글이라 살아남는다 — 그건 진짜 정보다

쓰는 법:
    python scripts\field_count.py
"""
import glob
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")

# 우리가 **만든** 것 — 수집한 자료가 아니다
_만든것 = {"snapshots", "card-copy", "briefings", "rule-cases", "rule-capital",
           "rule-frequency", "portfolio", "secrets", "overseas-sector",
           "orderbook-today", "industry", "_labs", "_bak", "_test", "_search",
           "SKILL-backups", "dart-corpcode", "sec-tickers", "us-symbols"}

_코드꼴 = re.compile(r"^[0-9A-Z]{6}$")


def 코드인가(k):
    r"""이름이 아니라 **갈래표**인 키면 True — 그 층은 건너뛰고 아래를 본다.

    ⚠️ 2026-09-07: 처음엔 6자리 코드만 걸렀더니 **날짜 키**가 정보로 셌다.
       fred 26,364 · yahoo 8,248 · kind-time 4,148 이 전부 날짜·공시번호였다
       ⇒ 6자리 넘는 **순수 숫자**도 갈래표로 본다 (19540701 · 20100104000001)
    """
    if k.isdigit() and len(k) >= 6:
        return True
    if not _코드꼴.match(k):
        return False
    return any(c.isdigit() for c in k)


def 키모으기(d, 깊이=0, 나온것=None):
    """파일 한 개에서 **필드 이름**만 뽑는다 (값이 코드로 갈리는 층은 건너뛴다)"""
    나온것 = 나온것 if 나온것 is not None else set()
    if 깊이 > 3 or not isinstance(d, (dict, list)):
        return 나온것
    if isinstance(d, list):
        for v in d[:3]:
            키모으기(v, 깊이 + 1, 나온것)
        return 나온것
    for k, v in d.items():
        if 코드인가(str(k)):
            # 코드로 갈리는 층 — 이름은 버리고 **그 아래**를 본다
            키모으기(v, 깊이 + 1, 나온것)
            continue
        나온것.add(str(k))
        if isinstance(v, (dict, list)):
            키모으기(v, 깊이 + 1, 나온것)
    return 나온것


def 써본것():
    """시험·수집 코드에 실제로 나온 낱말"""
    글 = []
    for p in glob.glob(os.path.join(_BASE, "scripts", "*.py")):
        try:
            글.append(io.open(p, encoding="utf-8").read())
        except Exception:
            pass
    return "\n".join(글)


def main():
    코드글 = 써본것()
    폴더들 = sorted(n for n in os.listdir(_DATA)
                    if os.path.isdir(os.path.join(_DATA, n))
                    and n not in _만든것)
    전체, 쓴것 = set(), set()
    줄 = []
    for 이름 in 폴더들:
        fs = sorted(glob.glob(os.path.join(_DATA, 이름, "**", "*.json"),
                              recursive=True))
        if not fs:
            continue
        키 = set()
        맛 = fs[:4] + fs[len(fs) // 2:len(fs) // 2 + 2] + fs[-4:]
        for f in 맛:
            try:
                키 |= 키모으기(json.load(io.open(f, encoding="utf-8-sig")))
            except Exception:
                pass
        # 살림살이용 키는 정보가 아니다
        키 -= {"기준일", "종목", "종목수", "건수", "받은날", "달", "해별",
               "이력", "값", "종류", "출처", "만든날", "심볼", "코드", "날짜"}
        if not 키:
            continue
        썼 = {k for k in 키 if k in 코드글}
        전체 |= {(이름, k) for k in 키}
        쓴것 |= {(이름, k) for k in 썼}
        줄.append((이름, sorted(키), sorted(썼)))

    줄.sort(key=lambda z: -len(z[1]))
    print("=" * 92)
    print("  수집한 정보의 **종류**가 몇 가지인가")
    print("  (종목코드·ETF코드는 뺐다. 우리가 만든 결과물도 뺐다)")
    print("=" * 92)
    print(f"\n  {'폴더':<16}{'종류':>5}{'써봤다':>7}{'안 써봤다':>9}   무엇")
    print("  " + "-" * 88)
    for 이름, 키, 썼 in 줄:
        안 = [k for k in 키 if k not in 썼]
        미리 = " · ".join(안[:5]) if 안 else "(다 써봤다)"
        print(f"  {이름:<16}{len(키):>5}{len(썼):>7}{len(안):>9}   {미리[:46]}")
    print("  " + "-" * 88)
    print(f"  {'합계':<16}{len(전체):>5}{len(쓴것):>7}"
          f"{len(전체) - len(쓴것):>9}")
    비 = len(쓴것) / len(전체) * 100 if 전체 else 0
    print(f"\n  ⇒ 정보 종류 **{len(전체)}가지** 중 **{len(쓴것)}가지({비:.0f}%)**를 써봤다")
    print(f"     안 써본 것 **{len(전체) - len(쓴것)}가지**")
    print("\n" + "=" * 92)
    print("  ⚠️ 「써봤다」는 스크립트에 그 이름이 나온다는 뜻이다.")
    print("     제대로 검증했다는 뜻이 아니다 — **하한선**이다")
    print("=" * 92)

    if "--안써본것" in sys.argv:
        print("\n  ── 안 써본 것 전부 ──")
        for 이름, 키, 썼 in 줄:
            안 = [k for k in 키 if k not in 썼]
            if 안:
                print(f"\n    [{이름}] {len(안)}가지")
                for i in range(0, len(안), 6):
                    print("      " + " · ".join(안[i:i + 6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
