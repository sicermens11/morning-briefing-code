#!/usr/bin/env python3
r"""
probe_exec.py — **임원매매(DART elestock)가 과거를 주나** 확인만 한다 (2026-09-09)

## 왜
```
우리가 받아둔 임원매매는 **2024년부터**뿐이다 (2024: 3,428 · 2025: 12,700 · 2026: 16,151)
collect_exec.py 설명에는 「corp_code 하나로 **전체 이력**을 준다」고 적혀 있다.
그런데 2010~2023이 없다 — **API가 안 주는 것인지, 우리가 못 받은 것인지** 모른다
```
⚠️ 조회만 한다. 아무것도 저장하지 않는다
⚠️ 키는 config 로만 읽는다 (secrets.json 을 직접 안 연다)

쓰는 법:
    python scripts\probe_exec.py
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    키 = config.get("DART_API_KEY")
    if not 키:
        print("⚠️ DART_API_KEY 가 없다")
        return 1

    # corp_code 표
    p = os.path.join(_BASE, "data", "dart-corpcode.json")
    if not os.path.exists(p):
        print(f"⚠️ {p} 가 없다")
        return 1
    표 = json.load(io.open(p, encoding="utf-8-sig"))

    def _코드(종목):
        v = 표.get(종목)
        if isinstance(v, dict):
            return v.get("corp_code") or v.get("고유번호")
        return v

    볼것 = (("005930", "삼성전자"), ("000660", "SK하이닉스"),
            ("035420", "NAVER"), ("000020", "동화약품"),
            ("307930", "컴퍼니케이"))
    print("=" * 76)
    print("  임원매매(elestock) 가 과거를 주나 — **조회만** 한다")
    print("=" * 76)
    for 종목, 이름 in 볼것:
        c = _코드(종목)
        if not c:
            print(f"  {이름:<10} corp_code 를 못 찾음")
            continue
        u = ("https://opendart.fss.or.kr/api/elestock.json?"
             + urllib.parse.urlencode({"crtfc_key": 키, "corp_code": c}))
        try:
            with urllib.request.urlopen(u, timeout=25) as f:
                d = json.loads(f.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  {이름:<10} ❌ {type(e).__name__}")
            continue
        상태 = d.get("status")
        줄 = d.get("list") or []
        날들 = sorted(str(r.get("rcept_dt") or "") for r in 줄 if r.get("rcept_dt"))
        if not 날들:
            print(f"  {이름:<10} status={상태} · {d.get('message','')[:40]} · 0건")
            continue
        import collections
        해 = collections.Counter(z[:4] for z in 날들)
        print(f"  {이름:<10} status={상태} · **{len(줄):,}건** · "
              f"{날들[0]} ~ {날들[-1]}")
        print(f"             해별: {dict(sorted(해.items()))}")

    print("\n" + "=" * 76)
    print("  읽는 법")
    print("    - 가장 오래된 날짜가 **2024년쯤**이면 API 가 최근 것만 준다")
    print("    - 2010년대가 나오면 **우리가 못 받은 것** — 다시 받으면 된다")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
