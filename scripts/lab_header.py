#!/usr/bin/env python3
r"""
lab_header.py — **시험이 스스로 「무엇을 안 봤는지」 밝히게 한다** (2026-09-10 신설)

## 왜 만드나
```
사용자: 「AI가 보통 뭐 전부 조사해달라고 하면 **초반 두개 찾아보고 맞으면
        다 맞다고 한다**는 경향이 있다고 하던데 딱 그런 케이스네」

2026-09-10 하루에 **다섯 번** 걸렸다. 전부 사용자가 물어서 발견됐다:
  · 「재료 22가지를 다 봤다」   -> 내가 떠올린 22가지였다 (모멘텀·밸류 빠짐)
  · 「모멘텀 실패」            -> 300~2,000억만 보고 있었다
  · gate7/gate8 이 **오르는 종목을 데이터에서부터 뺐다** (시험 11개 영향)
  · 222차는 「completed」인데 실은 **exit=1** 로 죽어 있었다
  · 226·228·225차는 **절 일부만 읽고** 보고했다
```

## 이 파일이 하는 일
```
시험 결과 파일 **맨 위에** 「이 시험이 무엇을 봤고 **무엇을 안 봤는지**」를 찍는다
=> 나중에 결과만 봐도 「전체」라고 잘못 말할 수 없다
```

쓰는 법 (각 lab 의 main() 첫머리에서):
    import lab_header as LH
    LH.찍기(
        차수="230차", 이름="분기 재무",
        크기="시총 300억 이상 (상한 없음)",
        방향="안 걸었음 — 오르는 종목도 담는다",
        기간="2016-01-01 ~",
        재료=["매출 성장률", "영업이익 성장률"],
        안본것=["ETF", "증자", "공시 시각"],
    )
"""
import io
import json
import os
import sys

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data")

# ⚠️ 자료 폴더와 **실제로 쓴 재료**를 대조하는 표.
#    새 자료가 생기면 여기에 더한다. 안 그러면 「다 봤다」를 또 하게 된다
_자료 = {
    "krx-daily": "주가·시총·거래대금",
    "index-daily": "지수 71개",
    "flow-daily": "외국인·기관·개인 순매수 · 외국인지분율",
    "dart-daily": "공시",
    "kind-time": "공시 시각",
    "etf-krx": "ETF 1,168종목",
    "dart-capital": "유상증자·무상증자",
    "naver-quarter": "분기 재무",
    "dart-major": "5% 대량보유",
    "dart-exec": "임원 매매",
    "news": "뉴스",
    "contract": "계약 공시",
    "yahoo": "해외 (S&P·구리·SOXX·원달러)",
    "consensus": "컨센서스 (목표주가·의견)",
    "quarter-fin": "분기 재무 (DART)",
    "dart-fin": "연간 재무",
    "fred": "금리",
}


def 자료현황():
    r"""{폴더: 파일수} — 짐작하지 않고 **실제로 센다**."""
    out = {}
    for k in _자료:
        p = os.path.join(_DATA, k)
        try:
            out[k] = len(os.listdir(p))
        except OSError:
            out[k] = 0
    return out


def 찍기(차수, 이름, 크기, 방향, 기간, 재료, 안본것=None, 견줌=None,
         판정=None):
    r"""시험 맨 위에 **무엇을 안 봤는지**를 찍는다.

    크기 · 방향 · 기간을 **반드시** 적는다. 하나라도 빠지면 시끄럽게 알린다.
    """
    print("=" * 100)
    print(f"  {차수} · {이름}")
    print("=" * 100)
    print("  ⚠️ **이 시험이 보는 범위** — 여기 없는 것은 **안 본 것**이다")
    print(f"     크기   {크기}")
    print(f"     방향   {방향}")
    print(f"     기간   {기간}")
    if 견줌:
        print(f"     견줌   {견줌}")
    if 판정:
        print(f"     판정   {판정}")
    print(f"\n     재료 {len(재료)}가지: " + " · ".join(재료))

    현황 = 자료현황()
    쓴폴더 = set()
    for r in 재료:
        for k, v in _자료.items():
            if any(w and w in r for w in v.split(" · ")) or k in r:
                쓴폴더.add(k)
    안쓴 = [(k, 현황[k], _자료[k]) for k in _자료
            if k not in 쓴폴더 and 현황[k] > 0]
    if 안쓴:
        print(f"\n  ⚠️ **이 시험이 안 쓴 자료 {len(안쓴)}개** "
              "(자료는 있는데 재료로 안 넣은 것)")
        for k, n, 설명 in sorted(안쓴, key=lambda z: -z[1]):
            print(f"       {k:<16}{n:>7,}개   {설명}")
    if 안본것:
        print(f"\n  ⚠️ **알면서 뺀 것**: " + " · ".join(안본것))
    print("=" * 100 + "\n", flush=True)


def 끝맺기(된것수, 전체수, 읽을것=None):
    r"""시험 끝에 **결과를 다 읽었는지** 스스로 묻게 한다."""
    print("\n" + "=" * 100)
    print(f"  ⚠️ **읽기 전에**: 이 파일은 절이 여러 개다. "
          f"**전부 읽고** 보고해야 한다")
    print(f"     된 것 {된것수} / 잰 것 {전체수}")
    if 읽을것:
        print("     절: " + " · ".join(읽을것))
    print("     (2026-09-10 에 226·228·225차를 **절 일부만 읽고** 보고했다)")
    print("=" * 100)


if __name__ == "__main__":
    print("  자료 현황 (실제로 센 것)")
    현황 = 자료현황()
    for k, n in sorted(현황.items(), key=lambda z: -z[1]):
        print(f"    {k:<16}{n:>7,}개   {_자료[k]}")
    print(f"\n  합계 {sum(현황.values()):,}개 파일 · 폴더 {len(현황)}개")
