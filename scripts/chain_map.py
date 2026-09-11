#!/usr/bin/env python3
r"""
chain_map.py — **가치사슬 14섹터**를 종목코드로 바꾼다 (2026-09-09 신설)

## 왜 만드나
```
사용자: 「반도체 뿐만 아니라 **AI, 조선, 방산** 등등 여러 섹터들도 특징이 있을 것 같은데!」

그런데 지금 시험이 쓰는 industry.json 은 **표준산업분류**라서:
  업종 63개 · 종목 3,988개
  「조선」 없음 · 「방산」 없음 · 「반도체」 없음 · 「2차전지」 없음
  반도체는 **「전자부품·통신장비」 496개**에 뭉쳐 있고
  조선은 「기계·장비」·「1차금속」에 흩어져 있다

⚠️⚠️ 그래서 **180차의 「업종마다 다르게 할 만한 결과 없음」을 못 믿는다.**
   업종이 달라서 차이가 없었던 게 아니라, **분류가 뭉개져서 못 본 것**일 수 있다

한편 `data/value-chain-map.md` 에는 사용자가 찾는 그 분류가 이미 있다 —
  조선 기자재 · 조선 본선 · 방산 · 원전 기자재 · 전력 인프라/변압기 ·
  2차전지 소부장 · 휴머노이드/로봇 · 바이오 CDMO · 의료기기/디지털헬스 ·
  사이버보안 · **AI 소프트웨어** · 우주/스페이스X · **반도체/HBM 소부장** · 해운
```

## ⚠️ 이 분류의 한계 — 결과를 읽을 때 반드시 같이 본다
```
맵은 **2026년 지금** 기준으로 짠 것이다. 16.7년 전 구성이 아니다.
=> 「지금 조선 대장인 걸 아는 채로 2010년을 본다」 (look-ahead)
   · 조선·방산처럼 얼굴이 안 바뀌는 산업은 덜 심하다
   · AI 소프트웨어처럼 최근에 생긴 무리는 **최근 몇 해만** 봐야 한다
   · 망해서 빠진 종목이 맵에 없다 (살아남은 것만 본다 = 성적이 부풀 수 있다)
```

쓰는 법:
    python scripts\chain_map.py           # 섹터마다 몇 종목이 코드로 잡히나
    from chain_map import 섹터표          # {코드: 섹터이름}
"""
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAP = os.path.join(_BASE, "data", "value-chain-map.md")
_BASE_JSON = os.path.join(_BASE, "data", "stock-base.json")

# ⚠️ 맵은 **정식 사명**을, KRX 는 **약칭**을 쓴다 (2026-09-01 전수 대조에서 확인).
#    이걸 안 맞추면 그 종목이 통째로 빠진다
_다른이름 = {
    "엘에스일렉트릭": "LS ELECTRIC",
    "휴니드테크놀러지스": "휴니드",
    # ⚠️ LIG디펜스앤에어로스페이스 · 파수AI · 한컴 은 **KRX 도 새 이름을 쓴다**.
    # 옛 이름으로 되돌렸다가 셋 다 못 찾았다 (2026-09-09). 바꾸지 않는다
    "SFA넥셀": "SFA반도체",
}
# ⚠️ 비상장이라 코드가 없는 것 — **오류가 아니다** (맵에 그렇게 적혀 있다)
_비상장 = {"파나시아", "HD현대삼호", "HD현대로보틱스", "롯데바이오로직스",
           "마이허브", "SK쉴더스", "마인즈랩", "업스테이지"}


def _이름표():
    """{종목이름: 코드}. 이름이 겹치면 시총이 큰 쪽을 쓴다"""
    d = json.load(io.open(_BASE_JSON, encoding="utf-8-sig"))
    z = d.get("종목") or d
    표 = {}
    for c, v in z.items():
        나 = (v.get("이름") or v.get("종목명") or "") if isinstance(v, dict) else str(v)
        if 나:
            표.setdefault(나, c)
            # 띄어쓰기·점을 뺀 것도 같이 넣는다 (LS ELECTRIC ↔ LSELECTRIC)
            납 = re.sub(r"[\s.·\-]", "", 나)
            표.setdefault(납, c)
    return 표


def 읽기():
    """{섹터이름: [(종목이름, 코드 또는 None), ...]}"""
    글 = io.open(_MAP, encoding="utf-8").read()
    이름표 = _이름표()
    나온것, 지금 = {}, None
    for 줄 in 글.splitlines():
        m = re.match(r"^###\s+(.+?)\s*(?:\(.*\))?\s*$", 줄)
        if m:
            지금 = m.group(1).strip()
            나온것.setdefault(지금, [])
            continue
        if 지금 is None or "OR" not in 줄:
            continue
        # `"가 OR 나 OR 다 [이슈 키워드]"` 꼴에서 종목만 뽑는다
        본 = 줄.strip().strip("`").strip('"')
        본 = re.sub(r"\[.*?\]", "", 본)
        for 나 in [z.strip() for z in 본.split(" OR ")]:
            나 = 나.strip('`" ')
            if not 나 or len(나) > 20:
                continue
            키 = _다른이름.get(나, 나)
            코 = 이름표.get(키) or 이름표.get(re.sub(r"[\s.·\-]", "", 키))
            if (나, 코) not in 나온것[지금]:
                나온것[지금].append((나, 코))
    return {k: v for k, v in 나온것.items() if v}


def 섹터표():
    """{코드: 섹터이름} — 시험에서 바로 쓴다.

    ⚠️ 한 종목이 두 섹터에 있으면 **먼저 나온 섹터**로 둔다
    """
    표 = {}
    for 섹, 들 in 읽기().items():
        for _, c in 들:
            if c and c not in 표:
                표[c] = 섹
    return 표


def main():
    나온것 = 읽기()
    print("=" * 78)
    print("  가치사슬 맵 — 섹터마다 몇 종목이 코드로 잡히나")
    print("=" * 78)
    총, 총코드, 못찾음 = 0, 0, []
    for 섹, 들 in 나온것.items():
        코 = [c for _, c in 들 if c]
        총 += len(들)
        총코드 += len(코)
        빠 = [나 for 나, c in 들 if not c and 나 not in _비상장]
        못찾음 += [(섹, 나) for 나 in 빠]
        꼬 = f"   ⚠️ 못 찾음 {len(빠)}" if 빠 else ""
        print(f"  {섹:<22}{len(코):>3}종목{꼬}")
    print("-" * 78)
    print(f"  섹터 {len(나온것)} · 이름 {총} · **코드로 잡힌 것 {총코드}**"
          f" · 비상장 {총 - 총코드 - len(못찾음)}")
    if 못찾음:
        print(f"\n  ⚠️ 코드를 못 찾은 {len(못찾음)}개 — 이름이 다를 수 있다:")
        for 섹, 나 in 못찾음:
            print(f"     {섹:<22}{나}")
    else:
        print("\n  ✅ 비상장 말고는 다 찾았다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
