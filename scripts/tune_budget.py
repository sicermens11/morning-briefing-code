#!/usr/bin/env python3
r"""
tune_budget.py — **카드 글자 예산을 재서 알려준다** (2026-08-31 신설)

⚠️⚠️ **왜 필요한가.**
   사용자 제안: *"가로 요약은 공간이 제한적이니 항목마다 공간을 정해두고 글자를 거기 맞추자."*
   맞는 방향인데 **이미 절반은 그렇게 돼 있다** — `build_cards.CUT`이 항목별 글자 예산이고
   `check_layout`이 여백을 잰다. 문제는 **그 숫자를 사람이 손으로 고친다**는 것이다.
   2026-08-31 하루에만 여섯 번 고쳤다(신호 96→190→160→140→118, 컨센서스 150→110 …).

⚠️ **그래서 이 스크립트가 계산한다.** 카드별 아래 여백을 재서
   **"이 항목을 몇 자 더 담을 수 있나 / 몇 자 줄여야 하나"**를 알려준다.

⚠️⚠️ **자동으로 고치지 않는다.** 여백이 남는다고 아무 항목이나 늘리면 안 된다 —
   어느 항목을 늘릴지는 **무엇이 중요한가**의 문제이지 계산 문제가 아니다.
   (2026-08-31에 액션 카드의 남는 자리를 「언제 사나」로 채웠다가 "숫자를 풀어 쓴 것뿐"이라는
    지적을 받고 「긍정·부정 신호」로 바꿨다. 계산은 자리를 알려줄 뿐 무엇을 넣을지는 못 정한다.)

⚠️ 한 줄이 몇 px인지는 **글자 크기와 줄간격에서 나온다.** 카드 본문은 29~31px에
   `line-height:1.45~1.55`라 **한 줄 약 45px**이고, 한 줄에 **약 34자**가 들어간다
   (1080px 폭 − 좌우 여백 196px = 884px ÷ 26px/자).

쓰는 법:
    python scripts\tune_budget.py                 # 최신 날짜
    python scripts\tune_budget.py --date 2026-08-31
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_layout as cl  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = os.path.join(_BASE, "data", "briefing-cards.html")

# ⚠️ 실측값이다. 카드 본문 29~31px · line-height 1.45~1.55 · 폭 884px 기준.
줄높이 = 45       # px
줄글자 = 34       # 자


def 진단(html_path=CARDS):
    exe = cl._chrome()
    html = io.open(html_path, encoding="utf-8-sig").read()
    probe = cl.CARD_PROBE.replace("__MINFONT__", str(cl.MIN_FONT))
    raw, err = cl._run(exe, html + "<script>" + probe + "</script>", 1500, 1300, "R::")
    if err or not raw:
        return {"ok": False, "이유": err or "측정값을 못 읽었다"}

    out = []
    for row in raw.split("@@"):
        p = row.split("|")
        if len(p) < 5:
            continue
        label, 아래 = p[0], int(p[2])
        # 하한(90)까지 쓸 수 있는 자리 / 상한(260)을 넘게 남은 자리
        여유 = 아래 - cl.MIN_MARGIN
        if 여유 >= 0:
            줄 = 여유 // 줄높이
            판정 = ("자리 남음" if 아래 > cl.MAX_MARGIN else "적당")
            메모 = f"{줄}줄({줄 * 줄글자}자) 더 담을 수 있다" if 줄 else "여유 없음"
        else:
            줄 = (-여유 + 줄높이 - 1) // 줄높이
            판정 = "넘침"
            메모 = f"{줄}줄({줄 * 줄글자}자) 줄여야 한다"
        out.append({"카드": label, "아래여백": 아래, "판정":판정, "조치": 메모})
    return {"ok": True, "하한": cl.MIN_MARGIN, "상한": cl.MAX_MARGIN,
            "한줄": f"{줄높이}px · 약 {줄글자}자", "카드": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="사람이 읽는 표 대신 JSON")
    a = ap.parse_args()
    r = 진단()
    if a.json or not r.get("ok"):
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r.get("ok") else 1
    print(f"한 줄 ≈ {r['한줄']} · 여백 하한 {r['하한']} / 상한 {r['상한']}\n")
    print(f"{'카드':<16}{'아래여백':>8}  {'판정':<10}조치")
    for c in r["카드"]:
        print(f"{c['카드'][:14]:<16}{c['아래여백']:>7}px  {c['판정']:<10}{c['조치']}")
    남 = [c for c in r["카드"] if c["판정"] == "자리 남음"]
    넘 = [c for c in r["카드"] if c["판정"] == "넘침"]
    print()
    if 넘:
        print("⚠️ 넘치는 장:", ", ".join(c["카드"] for c in 넘))
    if 남:
        print("· 자리가 남는 장:", ", ".join(c["카드"] for c in 남))
    if not 넘 and not 남:
        print("· 전부 적당하다. 예산을 손댈 이유가 없다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
