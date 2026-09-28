#!/usr/bin/env python3
# ⚠️ docstring 은 r""" (raw) — 윈도 경로의 `\u` 가 유니코드 이스케이프로 해석되면 파일이 깨진다.
r"""rule_ledger.py — **규칙 대장** · 「무엇이 무리마다 갈라졌고, 무엇을 이미 쟀나」 (2026-09-28 신설)

## 왜 만드나
사용자 (2026-09-28): 「아니 왜 자꾸 번복이 일어나지? 헛돌고 있는거 아니야?」

맞다. 2026-09-28 하루에 **일곱 번** 말을 뒤집었다. 세어 보면 원인이 하나다 —
**전부 「기억으로 말하고, 곧바로 파일을 열어 보니 틀렸던 것」**이다:

  ① 「판 47분 중 42분이 밑준비」        → 아니었다 (때 지도)
  ② 「도전자들이 18분 먹는다」           → 재는 장치가 잘못 귀속한 것
  ③ 「대형주 문을 열까가 결정거리」       → **이미 열려 있었다** (27cd314)
  ④ 「휴장일에 브리핑이 돌았다」          → 브리핑은 멈췄다. 다른 둘이 돌았다
  ⑤ 「대형 전용 규칙을 한 번도 안 찾았다」 → **연휴에 찾았다** (B73·B82·B87·BAND5…)
  ⑥ 「수익률만 봤다」                   → 끝 자산은 처음부터 돈이었다
  ⑦ 「EntryCheck1220 이 정리 안 됐다」   → 8/28 에 이유를 적고 끈 것

일곱 다 **묻는 순간 자료에 답이 있었다.** 기억에 기대서 생긴 일이다.
[[ledger-answers-coverage]] 와 같은 처방을 쓴다 — **사람이 아니라 코드가 답한다.**

## 무엇에 답하나
  ① 지금 **실전(rule_def)** 에서 여덟 층 중 무엇이 무리마다 갈라져 있나
  ② 판(gate7_lab)에 **손잡이가 있나** · **쓰는 절이 있나** · **실제로 돌린 판이 있나**
     ⚠️ 만들어만 놓고 아무 절도 안 쓰는 손잡이가 오늘만 셋 나왔다
        (`큰자리` · `규모별매도` · `_건너뛰나`)
  ③ 무리(대형·중형·섹터·업종·날·주가·시장)마다 **어느 판이 이미 쟀나**

쓰기: python scripts/rule_ledger.py [--자세히]
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_여기 = os.path.dirname(os.path.abspath(__file__))
_뿌리 = os.path.dirname(_여기)
_랩 = os.path.join(_뿌리, "data", "_labs")
자세히 = "--자세히" in sys.argv

sys.path.insert(0, _여기)
import rule_def as R  # noqa: E402

_랩소스 = io.open(os.path.join(_여기, "gate7_lab.py"), encoding="utf-8-sig").read()
_실전소스 = "\n".join(
    io.open(os.path.join(_여기, f), encoding="utf-8-sig").read()
    for f in ("record_pick.py", "rule_def.py") if os.path.exists(os.path.join(_여기, f)))

print("=" * 96)
print("  규칙 대장 — 무엇이 무리마다 갈라졌고, 무엇을 이미 쟀나")
print("=" * 96)

# ══ ① 실전에서 갈라진 층 ══
층 = [
    ("① 재료풀", "공통", "같은 자료를 본다 — 가를 이유가 없다"),
    ("② 문(재무·대금·크기)", "반쯤",
     "섹터 갈래만 크기 상한 없음" if R.섹터규칙_큰회사 else "전부 공통"),
    ("③ 신호", "갈라짐",
     "섹터 {}개 · 업종 {}개가 제 문턱".format(len(R.섹터규칙), len(R.업종규칙))),
    ("④ 상대갭", "공통", "{:g}%p 하나뿐 — 소형 자료로 고른 값".format(R.상대갭문턱)),
    ("⑤ 하루 자리", "공통", "{}개 하나뿐".format(R.하루최대종목)),
    ("⑥ 비중", "공통", "시뮬 가정이다 — 화면에 안 쓴다"),
    ("⑦ 파는 규칙", "공통", "{} 하나뿐".format(R.몫들)),
    ("⑧ 판정 잣대", "공통", "돈(끝 자산)으로 잰다"),
]
print("\n① **실전(rule_def)** — 여덟 층 중 무리마다 갈라진 것")
print("   {:<22}{:<9}{}".format("층", "무리마다", "지금"))
for 이름, 상태, 설명 in 층:
    표 = {"갈라짐": "✅ 갈라짐", "반쯤": "△ 반쯤", "공통": "— 공통"}[상태]
    print("   {:<22}{:<9}{}".format(이름, 표, 설명))

# ══ ② 판의 손잡이 ══
손잡이 = {
    "큰자리": "④⑤ 대형에 자리를 떼어둔다 (총 자리는 그대로)",
    "갭무름": "④ 시총 컷마다 상대갭 문턱에 배수",
    "무리갭": "④ 무리마다 제 상대갭 문턱 (섹터·업종에도)",
    "무리자리": "⑤ 무리마다 제 자리 (총합이 는다)",
    "무리몫": "⑦ 무리마다 제 파는 규칙 (섹터·업종에도)",
    "규모별매도": "⑦ 소·중·대마다 제 파는 규칙",
    "제약없음": "현금·거래대금 한도를 뺀다",
    "재평가": "보유 중 다시 본다 (악재 매도 포함)",
}
# 절마다 어떤 손잡이를 쓰나
절들 = []
for m in re.finditer(r'_ONLY == "([A-Z0-9_-]+)"', _랩소스):
    절들.append((m.group(1), m.start()))
절들.sort(key=lambda z: z[1])


def _쓰는절(키):
    벌 = []
    for i, (이름, 자리) in enumerate(절들):
        끝 = 절들[i + 1][1] if i + 1 < len(절들) else len(_랩소스)
        if '"' + 키 + '"' in _랩소스[자리:끝]:
            벌.append(이름)
    return 벌


def _돌린판(키):
    벌 = []
    for f in sorted(glob.glob(os.path.join(_랩, "*.txt"))):
        try:
            if 키 in io.open(f, encoding="utf-8", errors="replace").read():
                벌.append(os.path.basename(f)[:34])
        except OSError:
            pass
    return 벌


print("\n② **판(gate7_lab)의 손잡이** — 만들었나 · 쓰는 절이 있나 · 실제로 돌린 판이 있나")
print("   {:<12}{:<8}{:<26}{}".format("손잡이", "시뮬에", "쓰는 절", "돌린 판"))
죽은것 = []
for 키, 설명 in 손잡이.items():
    있나 = 'c.get("' + 키 + '")' in _랩소스
    절 = _쓰는절(키)
    판 = _돌린판(키)
    if 있나 and not 절:
        죽은것.append(키)
    print("   {:<12}{:<8}{:<26}{}".format(
        키, "✅" if 있나 else "—",
        (" · ".join(절)[:24] or "🔴 아무 절도 안 쓴다"),
        ("{}개".format(len(판)) if 판 else "🔴 없다")))
    if 자세히:
        print("      ↳ {}".format(설명))
        if 판:
            print("      ↳ {}".format(" · ".join(판[-3:])))
if 죽은것:
    print("   ⚠️ **만들고 아무 절도 안 쓰는 손잡이** — {}".format(" · ".join(죽은것)))
    print("      (오늘만 셋이었다: 큰자리 · 규모별매도 · _건너뛰나)")

# ══ ③ 무리마다 어느 판이 쟀나 ══
무리말 = {
    "대형": ("대형", "1조↑", "2,000억↑"),
    "중형": ("중형",),
    "소형": ("소형",),
    "섹터 갈래": ("섹터규칙", "섹터 갈래", "가치사슬"),
    "업종 갈래": ("업종규칙", "업종 갈래"),
    "그날 장 상태": ("시장낙폭", "빠지는장", "평온한 날"),
    "주가(호가)": ("주가 ", "호가 단위"),
    "코스피/코스닥": ("코스피", "코스닥"),
}
print("\n③ **무리마다 어느 판이 그것을 주제로 쟀나** (파일 이름 · 절 머리글 기준)")
print("   {:<14}{:>7}   {}".format("무리", "전용 판", "가장 최근 셋"))
_모든판 = sorted(glob.glob(os.path.join(_랩, "*.txt")), key=os.path.getmtime)
_글캐시 = {}
for f in _모든판:
    try:
        _글캐시[f] = io.open(f, encoding="utf-8", errors="replace").read()
    except OSError:
        _글캐시[f] = ""

# ⚠️ 낱말이 **아무 데나** 나오면 270개로 찍힌다 — 소음이 실패를 숨긴다
#    ([[checker-noise-hides-failures]]). 「그 무리를 **주제로** 삼은 판」만 센다:
#      · 파일 이름에 그 말이 있거나
#      · **절 머리글**(── XXX ⭐)에 그 말이 있는 판
_머리줄 = {}
for f in _모든판:
    _머리줄[f] = "\n".join(z for z in _글캐시[f].splitlines()
                          if "── " in z and "⭐" in z)
#    ⚠️ **둘을 나눠 센다.** 절 머리글은 문 없는 옛 절이 매 판 돌아서 늘 100개가 넘는다 —
#       그건 「그 무리를 주제로 판을 걸었다」가 아니다. **전용 판**(파일 이름)이 진짜 신호다
for 이름, 말들 in 무리말.items():
    전용 = [os.path.basename(f)[:30] for f in _모든판
            if any(w in os.path.basename(f) for w in 말들)]
    절로 = [f for f in _모든판 if any(w in _머리줄[f] for w in 말들)]
    print("   {:<14}{:>7}   {}".format(
        이름, len(전용),
        (" · ".join(전용[-3:]) if 전용 else "🔴 전용 판이 **없다**")
        + ("   (절로만 다룬 판 {}개)".format(len(절로)) if 절로 else "")))

print("\n" + "=" * 96)
print("  ⚠️ 이 표에 있는 것을 **기억으로 말하지 않는다.** 물으면 이 대장을 돌린다")
print("=" * 96)
