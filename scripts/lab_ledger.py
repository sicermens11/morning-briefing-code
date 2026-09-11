#!/usr/bin/env python3
r"""
lab_ledger.py — **기록 안 된 시험을 잡는다** (2026-09-07 신설)

## 왜
```
사용자 질문: 「기록 안 된 거는 어떻게 할 거야? 기록 못 하는 거야?」
오늘만 **두 번** 밀렸다:
  ① 108차 이후 번호가 스물아홉 개 동안 안 붙었다
  ② 123·125차는 결과 파일만 있고 AGENDA 에 한 줄도 없었다
```
⚠️ 「다음부터 잘 적겠다」는 약속으로는 또 밀린다. **기계가 잡아야 한다.**

## 하는 일
```
data/_labs/*.txt 를 훑어
  ① 이름이 `YYYY-MM-DD_N차_이름.txt` 꼴인가          (번호가 붙었나)
  ② 그 번호가 docs/시험번호.md 에 있나                (대장에 있나)
  ③ 그 번호가 AGENDA.md 에 있나                      (본문에 있나)
셋 중 하나라도 없으면 **빠진 것**으로 찍는다
```
⚠️ 결과 파일 자체는 안 지운다 — 자료는 살아 있다.
   빠진 건 **이야기(왜 그랬나)**지 숫자가 아니다

쓰는 법:
    python scripts\lab_ledger.py            # 빠진 것 보기
    python scripts\lab_ledger.py --조용     # 빠진 개수만 (selfcheck 용)
"""
import glob
import io
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LABS = os.path.join(_BASE, "data", "_labs")
_대장 = os.path.join(_BASE, "docs", "시험번호.md")
_아젠다 = os.path.join(_BASE, "AGENDA.md")
_기준선 = "2026-09-05"   # 이 날부터 N차 이름 규칙을 쓴다
_이름꼴 = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d+)차_(.+)\.txt$")


def 읽기(p):
    try:
        return io.open(p, encoding="utf-8").read()
    except Exception:  # noqa: BLE001
        return ""


def 훑기():
    대장글, 아젠다글 = 읽기(_대장), 읽기(_아젠다)
    번호없음, 대장없음, 본문없음, 정상 = [], [], [], []
    for p in sorted(glob.glob(os.path.join(_LABS, "*.txt"))):
        이름 = os.path.basename(p)
        if 이름.startswith("_"):        # _quarter_run 같은 작업 로그는 뺀다
            continue
        # ⚠️ **기준선**: 2026-09-05 이전은 옛 방식(AGENDA 본문에 이름으로만)이다.
        #    167개를 소급해 번호 매기는 건 과하다 — 그때 것은 넘어간다
        if 이름[:10] < _기준선:
            continue
        m = _이름꼴.match(이름)
        if not m:
            번호없음.append(이름)
            continue
        n = m.group(2)
        if f"| {n} |" not in 대장글:
            대장없음.append((n, 이름))
        elif f"{n}차" not in 아젠다글 and f"| {n} |" not in 아젠다글:
            본문없음.append((n, 이름))
        else:
            정상.append(n)
    return 번호없음, 대장없음, 본문없음, 정상


def main():
    조용 = "--조용" in sys.argv
    번호없음, 대장없음, 본문없음, 정상 = 훑기()
    빠짐 = len(번호없음) + len(대장없음) + len(본문없음)
    if 조용:
        print(f"기록 안 된 시험 {빠짐}건 "
              f"(번호없음 {len(번호없음)} · 대장없음 {len(대장없음)} "
              f"· 본문없음 {len(본문없음)}) · 정상 {len(정상)}")
        return 1 if 빠짐 else 0

    print("=" * 84)
    print("  시험 기록 점검  (data/_labs 와 docs/시험번호.md · AGENDA.md 대조)")
    print("=" * 84)
    print(f"\n  정상 {len(정상)}건 · **빠진 것 {빠짐}건**")
    if 번호없음:
        print(f"\n  ⚠️ 이름에 차수가 없다 ({len(번호없음)}건)")
        print("     → `YYYY-MM-DD_N차_이름.txt` 로 바꿔야 나중에 찾을 수 있다")
        for x in 번호없음[:20]:
            print(f"       {x}")
        if len(번호없음) > 20:
            print(f"       … 그 밖 {len(번호없음)-20}건")
    if 대장없음:
        print(f"\n  ❌ docs/시험번호.md 에 없다 ({len(대장없음)}건)")
        for n, x in 대장없음:
            print(f"       {n}차  {x}")
    if 본문없음:
        print(f"\n  ❌ AGENDA.md 에 한 줄도 없다 ({len(본문없음)}건)")
        print("     → 숫자는 파일에 살아 있지만 **왜 그랬나가 없다**")
        for n, x in 본문없음:
            print(f"       {n}차  {x}")
    if not 빠짐:
        print("\n  ✅ 다 적혀 있다")
    print("\n" + "=" * 84)
    return 1 if 빠짐 else 0


if __name__ == "__main__":
    sys.exit(main())
