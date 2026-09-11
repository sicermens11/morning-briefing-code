r"""258차 A·B 표에서 **이긴 매도 설정**을 뽑아 BASE_SELL 꼴로 찍는다.

사용자 (2026-09-11):
```
「258차 A·B 결과를 보고 이긴 비율로 나중에 돌리는 걸로 예약하자.
 이렇게 **결과에 따라 테스트가 필요하면 허락받지 말고 그냥 테스트해**」
```

사람이 결과를 볼 때까지 기다리지 않는다. A판이 끝나면 이 파일이 표를 읽고,
이긴 설정을 기준선으로 삼아 **판 G** 가 이어 돈다.

## 판정 (내가 정한 게 아니라 TEST-ORDER.md 3절 그대로)
```
① **끝 자산**이 지금보다 많아야 한다
② **돈÷낙폭**이 나빠지면 안 된다 (5% 까지만 봐준다)
③ **제약 없는 판**으로 본다
⚠️ 승률·평균 수익으로 판정하지 않는다
```
둘을 다 만족하는 게 없으면 **아무것도 안 바꾼다** (빈 줄을 찍는다).
그게 맞다 — 「뭐라도 골라야 한다」는 압박이 191차 「1년 3개」를 낳았다.

쓰는 법:
    python scripts/pick_sell.py data/_labs/2026-09-12_A_지금기준선.txt
    -> "0.3,15,40 / 0.7,40,90"   (또는 빈 줄)
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
import rule_def as R  # noqa: E402

# 「 라벨 ... 123,456원  -4.5%  164  8.61 | 987,654원  -5.7%  183  12.49  +789% 」
줄꼴 = re.compile(
    r"^\s{2}(?P<라>\S.*?)\s{2,}"
    r"(?P<끝1>[\d,]+)원\s+(?P<낙1>-?[\d.]+)%\s+(?P<산1>[\d,]+)\s+(?P<나1>[\d.]+)"
    r"\s*\|\s*"
    r"(?P<끝2>[\d,]+)원\s+(?P<낙2>-?[\d.]+)%\s+(?P<산2>[\d,]+)\s+(?P<나2>[\d.]+)")

비율꼴 = re.compile(r"^(\d{2}):(\d{2})$")
통짜꼴 = re.compile(r"목표 \+(\d+)% · (\d+)일 \(통짜\)")


def 읽기(경로):
    """258차 A·B 절의 줄만 모은다."""
    t = io.open(경로, encoding="utf-8", errors="replace").read()
    i = t.find("258차 · ")
    if i < 0:
        return None, []
    # ⚠️ 범위를 「── C ⭐」로만 자르면 **다음 절까지 읽는다** (2026-09-11 에 걸렸다).
    #    259차 파일에는 258차에 C절이 없어서 242차의 견줌을 집어 왔다.
    #    **다음 절 머리글**을 끝으로 삼는다
    j = len(t)
    다음 = re.compile(r"^\s{2}\d{2,3}차 · ", re.M).search(t, i + 20)
    if 다음:
        j = 다음.start()
    _c = t.find("── C ⭐", i)      # C절(손절)부터는 안 본다
    if 0 <= _c < j:
        j = _c
    견줌, 벌 = None, []
    for 줄 in t[i:j].split("\n"):
        m = 줄꼴.match(줄.rstrip())
        if not m:
            continue
        라 = m.group("라").strip()
        칸 = {"라": 라,
              "끝": float(m.group("끝2").replace(",", "")),
              "낙": float(m.group("낙2")),
              "나": float(m.group("나2"))}
        if "지금" in 라 or "견줌" in 라:
            if 견줌 is None:          # **첫 줄**이 견줌이다. 덮어쓰지 않는다
                견줌 = 칸
            continue
        벌.append(칸)
    return 견줌, 벌


def 꼴로(라):
    """표의 라벨을 BASE_SELL 꼴로. 못 바꾸면 None"""
    m = 비율꼴.match(라)
    if m:
        앞, 뒤 = int(m.group(1)) / 100, int(m.group(2)) / 100
        return (f"{앞:g},{R.앞몫목표:g},{R.앞몫기한} / "
                f"{뒤:g},{R.뒷몫목표:g},{R.뒷몫기한}")
    m = 통짜꼴.search(라)
    if m:
        return f"1.0,{int(m.group(1))},{int(m.group(2))}"
    return None


def 고른다(경로):
    견줌, 벌 = 읽기(경로)
    if not 견줌 or not 벌:
        print("", end="")
        print(f"# 258차 A·B 표를 못 읽었다: {os.path.basename(경로)}",
              file=sys.stderr)
        return ""
    벌 = [z for z in 벌 if 꼴로(z["라"])]
    # ① 끝 자산이 더 많고 ② 돈÷낙폭이 **안 나빠진** 것
    # ⚠️ 「5%까지 봐준다」 같은 여유를 **내가 만들지 않는다**.
    #    191차 「1년 3개」가 그렇게 결론을 뒤집었다 [[judge-criteria-need-user-check]]
    붙 = [z for z in 벌
          if z["끝"] > 견줌["끝"] and z["나"] >= 견줌["나"]]
    print(f"# 견줌 {견줌['라']} — {견줌['끝']:,.0f}원 · 낙 {견줌['낙']:.1f}% · "
          f"돈÷낙 {견줌['나']:.2f}", file=sys.stderr)
    print(f"# 잰 것 {len(벌)}개 · 둘 다 만족 {len(붙)}개", file=sys.stderr)
    if not 붙:
        print("# ⇒ 끝 자산과 낙폭을 **둘 다** 이긴 건 없다", file=sys.stderr)
        for z in sorted(벌, key=lambda q: -q["끝"])[:3]:
            print(f"#    {z['라']} {z['끝']:,.0f}원 · 돈÷낙 {z['나']:.2f}",
                  file=sys.stderr)
        if not 벌:
            return ""
        # ⚠️ 그래도 **판은 돈다** — 사용자: 「결과에 따라 테스트가 필요하면
        #    허락받지 말고 그냥 테스트해」. 끝 자산이 제일 큰 것을 기준선으로
        #    삼아 **앞뒤 분할에서도 버티는지** 본다.
        #    ⚠️⚠️ 이건 **후보가 아니라 살펴보기**다. 반영 판단에 쓰지 않는다
        캠 = max(벌, key=lambda z: z["끝"])
        print(f"# ⇒ **살펴보기**로 {캠['라']} 를 기준선 삼아 판을 돈다 "
              f"(낙폭이 나빠진 걸 앞뒤 분할이 걸러내나)", file=sys.stderr)
        return 꼴로(캠["라"])
    이긴 = max(붙, key=lambda z: z["끝"])
    print(f"# ⇒ **{이긴['라']}** {이긴['끝']:,.0f}원 · 낙 {이긴['낙']:.1f}% · "
          f"돈÷낙 {이긴['나']:.2f}", file=sys.stderr)
    return 꼴로(이긴["라"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("쓰는 법: python scripts/pick_sell.py <결과파일>", file=sys.stderr)
        raise SystemExit(2)
    print(고른다(sys.argv[1]))
