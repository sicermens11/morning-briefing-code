#!/usr/bin/env python3
r"""
plan_check.py — **「하기로 해놓고 안 한 것」을 잡는다** (2026-09-08 신설)

## 왜 만들었나
```
사용자: 「목록에서 빠져서 테스트해야 하는데 안 한 거 있는지 체크해봐.
        작업이 많고 복잡해지면서 너도 헷갈려 하는 것 같은데?
        이런 거 방지할 방법 없나?」
```
맞는 지적이다. 실제로 **「새로운 조합」이 가번호 150으로 계획에 있다가,
150번이 걷기검증에 붙으면서 목록에서 사라졌다.** 사용자가 물어서 알았다

## 무엇이 문제였나
```
계획은 AGENDA.md 에 **글로** 적혀 있었다 -> 사람이 눈으로 찾아야 한다
결과는 data/_labs 에 **파일로** 있다     -> 기계가 셀 수 있다
=> **둘을 맞춰보는 것이 없었다**
```

## 그래서 만든 것
```
docs/할일.md   에 「할 것」을 **한 줄씩 표로** 적는다 (기계가 읽을 수 있게)
이 스크립트가  그 표와 data/_labs 를 맞춰본다
=> 「예정인데 결과가 없는 것」과 「결과가 있는데 표에 없는 것」을 잡는다
```
⚠️ `lab_ledger.py` 와 다르다. 그건 **돌아간 시험**이 기록됐나를 본다.
   이건 **안 돌아간 시험**이 잊혔나를 본다

쓰는 법:
    python scripts\plan_check.py
    python scripts\plan_check.py --조용   (문제만)
"""
import io
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
할일 = os.path.join(_BASE, "docs", "할일.md")
_L = os.path.join(_BASE, "data", "_labs")

# | 상태 | 무엇 | 왜 | 결과파일 |
_줄 = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|"
                 r"\s*`?([^|`]*?)`?\s*\|\s*$")


def main():
    조용 = "--조용" in sys.argv
    if not os.path.exists(할일):
        print(f"⚠️ {할일} 이 없다 — 먼저 만들어야 한다")
        return 1
    줄들 = []
    for line in io.open(할일, encoding="utf-8"):
        m = _줄.match(line.rstrip("\n"))
        if not m:
            continue
        상태, 무엇, 왜, 파일 = m.groups()
        if 상태 in ("상태", "---", ":---") or 무엇 == "무엇":
            continue
        if set(상태) <= set("-: "):
            continue
        # ⚠️ 「갈래 | 개수 | 시험번호」 같은 **다른 표**가 섞여 든다.
        #    무엇 칸이 숫자뿐이면 시험이 아니다 (2026-09-09)
        if 무엇.strip().isdigit():
            continue
        줄들.append((상태, 무엇, 왜, 파일))

    있는파일 = set(os.listdir(_L)) if os.path.isdir(_L) else set()

    문제, 경고, 정상 = [], [], 0
    for 상태, 무엇, 왜, 파일 in 줄들:
        기 = 파일.replace("data/_labs/", "").strip()
        있 = 기 in 있는파일
        크 = os.path.getsize(os.path.join(_L, 기)) if 있 else 0
        # ⚠ 짧은 결과도 있다 (173차는 1,573바이트인데 완전하다).
        #    「죽었나」만 가린다 — 너무 높게 잡으면 멀젖한 경보가 난다
        찼 = 크 > 1000
        if "✅" in 상태:
            # 결과파일이 없는 줄은 「코드에 반영」 같은 일이다 — 파일을 안 남긴다
            if not 기:
                정상 += 1
            elif not 찼:
                문제.append(f"**{무엇}** — 끝났다고 적혀 있는데 "
                            f"{'결과가 비었다' if 있 else '결과 파일이 없다'}"
                            f" ({기 or '파일 안 적힘'})")
            else:
                정상 += 1
        elif "🔄" in 상태:
            경고.append(f"{무엇} — 도는 중")
        elif "⏸" in 상태:
            경고.append(f"{무엇} — 멈춤: {왜}")
        else:               # 예정
            if 찼:
                문제.append(f"**{무엇}** — 예정이라 적혀 있는데 "
                            f"**결과가 이미 있다** ({크:,}바이트). 표를 고쳐라")
            else:
                경고.append(f"{무엇} — 아직 안 함 ({왜})")

    # 표에 없는 결과 파일
    적힌 = {p.replace("data/_labs/", "").strip() for _, _, _, p in 줄들}
    # ⚠ 대장(docs/시험번호.md)에 이미 적힌 것은 뺀다 —
    #    그건 lab_ledger.py 가 본다. 여기서 또 외치면 진짜가 묻힌다
    _대장 = os.path.join(_BASE, "docs", "시험번호.md")
    if os.path.exists(_대장):
        _t = io.open(_대장, encoding="utf-8").read()
        적힌 |= set(re.findall(r"`data/_labs/([^`]+)`", _t))
    # ⚠ 번호 제도가 생기기 전(09-05 이전) 것은 본다 안 한다 —
    #    lab_ledger.py 와 같은 기준선이다
    _기준선 = "2026-09-05"
    남 = sorted(f for f in 있는파일
                if f.endswith(".txt") and not f.startswith("_")
                and f[:10] >= _기준선 and f not in 적힌)

    print("=" * 84)
    print("  하기로 해놓고 안 한 것 점검  (docs/할일.md ↔ data/_labs)")
    print("=" * 84)
    print(f"\n  적힌 줄 {len(줄들)}개 · 맞는 것 {정상}개 · "
          f"문제 {len(문제)}개 · 살펴볼 것 {len(경고)}개")

    if 문제:
        print(f"\n  ❌ **어긋난 것 {len(문제)}개**")
        for s in 문제:
            print(f"     · {s}")
    if 경고 and not 조용:
        print(f"\n  ⏳ 아직 안 한 것 · 도는 중 {len(경고)}개")
        for s in 경고:
            print(f"     · {s}")
    if 남 and not 조용:
        print(f"\n  ⚠️ **표에 없는 결과 파일 {len(남)}개** — 할일.md 에 넣어라")
        for f in 남[:20]:
            print(f"     · {f}")
        if len(남) > 20:
            print(f"     … 그 밖 {len(남)-20}개")
    if not 문제 and not 남:
        print("\n  ✅ 어긋난 것 없다")
    print("=" * 84)
    return 1 if 문제 else 0


if __name__ == "__main__":
    sys.exit(main())
