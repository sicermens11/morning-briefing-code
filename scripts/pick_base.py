r"""토요일 판 일곱을 읽고 **이긴 기준선**을 뽑는다 (2026-09-11 신설).

사용자: 「내가 토요일 결과를 볼 수 없으니까 지금 짜두고 **토요일에 사람이 안 봐도
        일요일이 이어지게** 해」

## 어떻게 고르나 (내가 정한 게 아니라 `TEST-ORDER.md` 3절 그대로)
```
① **끝 자산**과 **낙폭**으로 판정한다 (승률·평균 수익 아님)
② **제약 없는 판**으로 본다
③ 돈÷낙폭이 견줌보다 나빠지면 안 된다
```
판마다 바탕이 다르므로 **같은 자리의 같은 줄**을 견준다 —
256차 A절의 `Ⓗ (지금 · 견줌)` 한 줄이다. 그 줄은 **그 판의 기준선으로 돌린 Ⓗ**다.

## 내놓는 것
`BASE_GAP=... BASE_RELGAP=... BASE_PICKS=...` 꼴 한 줄 (없으면 빈 줄).
`weekend_sunday.ps1` 이 그걸 받아 일요일 판을 돈다.
"""
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAB = os.path.join(뿌리, "data", "_labs")

# 「Ⓗ (지금 · 견줌)   1억원  -4.5%  164  8.61 | 13억원  -5.7%  183  12.49  +789%」
# ⚠️⚠️ **제약 있는 판도 읽는다** (2026-09-12).
#    전에는 오른쪽(제약 없는 판)만 봤다. 그랬더니 갭 문턱을 푼 D판이
#    **1조5,518억**(복리 폭발)으로 1등이 됐는데, 제약 있는 판에서는
#    1.04억 · 낙폭 -16.8% 로 **지금보다 전부 나빴다.**
#    `TEST-ORDER.md` 3절은 「제약 없는 판을 **같이** 본다」이지 「그것만」이 아니다
줄꼴 = re.compile(
    r"Ⓗ \(지금 · 견줌\)\s+(?P<끝1>[\d,]+)원\s+(?P<낙1>-?[\d.]+)%"
    r"\s+(?P<산1>[\d,]+)\s+(?P<나1>[\d.]+)"
    r"\s*\|\s*(?P<끝>[\d,]+)원\s+(?P<낙>-?[\d.]+)%\s+(?P<산>[\d,]+)\s+(?P<나>[\d.]+)")
기준꼴 = re.compile(
    r"이 판의 기준선 — 갭잣대 \*\*(?P<갭>[^*]+)\*\* · 상대갭 \*\*(?P<상>[-\d.]+)%p\*\*"
    r" · 후보수 \*\*(?P<후>\d+)\*\* · 크기상한 (?P<크>[\d,]+)억")


def 읽기(경로):
    t = io.open(경로, encoding="utf-8", errors="replace").read()
    m1, m2 = 기준꼴.search(t), 줄꼴.search(t)
    if not (m1 and m2):
        return None
    return {
        "파일": os.path.basename(경로),
        "갭잣대": m1.group("갭").strip(),
        "상대갭": float(m1.group("상")),
        "후보수": int(m1.group("후")),
        "크기상한": float(m1.group("크").replace(",", "")),
        "끝": float(m2.group("끝").replace(",", "")),
        "낙": float(m2.group("낙")),
        "산": int(m2.group("산").replace(",", "")),
        "나": float(m2.group("나")),
        # 제약 **있는** 판 (현금·거래대금 1% 한도가 걸린 판) — 실전에 가깝다
        "끝1": float(m2.group("끝1").replace(",", "")),
        "낙1": float(m2.group("낙1")),
        "나1": float(m2.group("나1")),
    }


def 고른다(무늬):
    벌 = [z for z in (읽기(p) for p in sorted(glob.glob(
        os.path.join(_LAB, 무늬)))) if z]
    if not 벌:
        print("# 읽을 결과가 없다: " + 무늬, file=sys.stderr)
        return ""
    # 견줌 = 「지금 기준선」 판 (A). 없으면 크기상한이 기본(3,000)인 것
    기 = next((z for z in 벌 if "A_" in z["파일"]), None) or 벌[0]
    print(f"# 판 {len(벌)}개", file=sys.stderr)
    for z in sorted(벌, key=lambda q: -q["끝1"]):
        print(f"#   {z['파일']:<34}"
              f"제약있음 {z['끝1']:>16,.0f}원 낙 {z['낙1']:>6.1f}% "
              f"돈÷낙 {z['나1']:>6.2f}  |  "
              f"제약없음 {z['끝']:>18,.0f}원 낙 {z['낙']:>6.1f}% "
              f"돈÷낙 {z['나']:>6.2f}", file=sys.stderr)
    print(f"# 견줌: {기['파일']} 제약있음 {기['끝1']:,.0f}원 "
          f"낙 {기['낙1']:.1f}% 돈÷낙 {기['나1']:.2f} | "
          f"제약없음 {기['끝']:,.0f}원", file=sys.stderr)

    # ⚠️⚠️ **제약 있는 판과 없는 판 둘 다**에서 이겨야 한다 (2026-09-12).
    #    한쪽만 보면 복리가 터진 판이 1등이 된다 — D판이 그랬다
    # ⚠️ 여유를 **내가 만들지 않는다** — 끝 자산이 더 많고 돈÷낙폭이 안 나빠진 것
    붙 = [z for z in 벌
          if z is not 기
          and z["끝"] > 기["끝"] and z["나"] >= 기["나"]
          and z["끝1"] > 기["끝1"] and z["나1"] >= 기["나1"]]
    if not 붙:
        print("# ⇒ 둘 다 이긴 판이 없다. **기준선을 안 바꾼다**", file=sys.stderr)
        return ""
    # **제약 있는 판**의 끝 자산으로 줄 세운다 — 실전에 가까운 쪽이다
    이긴 = max(붙, key=lambda z: z["끝1"])
    print(f"# ⇒ **{이긴['파일']}** 제약있음 {이긴['끝1']:,.0f}원 "
          f"낙 {이긴['낙1']:.1f}% 돈÷낙 {이긴['나1']:.2f} | "
          f"제약없음 {이긴['끝']:,.0f}원", file=sys.stderr)
    벌2 = [f"BASE_GAP={이긴['갭잣대']}",
           f"BASE_RELGAP={이긴['상대갭']:g}",
           f"BASE_PICKS={이긴['후보수']}"]
    if 이긴["크기상한"] > 50000:
        벌2.append("SIZE_HI=999999")
    return " ".join(벌2)


if __name__ == "__main__":
    무늬 = sys.argv[1] if len(sys.argv) > 1 else "2026-09-12_*.txt"
    print(고른다(무늬))
