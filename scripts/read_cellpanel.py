r"""칸 판(Q-29) 결과에서 **혼자 선 칸**만 뽑아 한 장으로 (2026-09-24)

칸 판 하나가 400KB 다. 눈으로 읽으면 놓친다.
「걷기: ✅ … (혼자 서는 규칙 · 절대 기준)」이 붙은 칸만 모아 돈 순으로 세운다.

쓰기: python scripts/read_cellpanel.py data/_labs/2026-09-25_B73_칸판_대형.txt [...]
     python scripts/read_cellpanel.py --전부        (data/_labs 의 칸판_* 전부)
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

인자 = sys.argv[1:]
if not 인자 or 인자[0] == "--전부":
    파일들 = sorted(glob.glob(os.path.join(뿌리, "data", "_labs", "*칸판_*.txt")))
else:
    파일들 = [z if os.path.isabs(z) else os.path.join(뿌리, z) for z in 인자]
if not 파일들:
    print("칸 판 파일이 없다")
    raise SystemExit(2)

머리 = re.compile(r"──\s*\[(.+?)\]\s*해마다 \+ 걷기\s*──")
해마다 = re.compile(r"해마다 — 평균 ([+-][\d.]+)% · 진 해 (\d+)/(\d+)")
앞 = re.compile(r"앞 [\d~]+: [\d,]+원 → ([\d,]+)원\s+([+-][\d.]+)%\s+\(낙폭 ([+-][\d.]+)% · 산 것 (\d+)\)\s+(✅|❌)")
뒤 = re.compile(r"뒤 [\d~]+: [\d,]+원 → ([\d,]+)원\s+([+-][\d.]+)%\s+\(낙폭 ([+-][\d.]+)% · 산 것 (\d+)\)\s+(✅|❌)")
섰다 = "혼자 서는 규칙"
문틀 = re.compile(r"재무 — 잉여금 ≥ ([\d.]+)%.*?부채 ≤ ([\d.]+)%")
대금틀 = re.compile(r"대금 — ≥ ([\d.]+)억")
갭틀 = re.compile(r"상대갭 — ([+-][\d.]+)%")
칸머리 = re.compile(r"══ \[(.+?)\] ([\d,]+)건 — 이 칸 자료로만 ══")

전체 = []
for 길 in 파일들:
    이름 = os.path.basename(길)
    줄들 = io.open(길, encoding="utf-8", errors="replace").read().splitlines()
    지금칸, 지금문 = None, {}
    for i, z in enumerate(줄들):
        m0 = 칸머리.search(z)
        if m0:
            지금칸 = m0.group(1)
            지금문 = {"사건": m0.group(2)}
            continue
        m1 = 문틀.search(z)
        if m1:
            지금문["잉여금"], 지금문["부채"] = m1.group(1), m1.group(2)
        m2 = 대금틀.search(z)
        if m2:
            지금문["대금"] = m2.group(1)
        m3 = 갭틀.search(z)
        if m3:
            지금문["갭"] = m3.group(1)
        m = 머리.search(z)
        if not m:
            continue
        칸 = m.group(1)
        꼬리 = "\n".join(줄들[i:i + 8])
        if 섰다 not in 꼬리:
            continue
        ma, mb, mh = 앞.search(꼬리), 뒤.search(꼬리), 해마다.search(꼬리)
        if not (ma and mb):
            continue
        if ma.group(5) != "✅" or mb.group(5) != "✅":
            continue
        전체.append({
            "파일": 이름, "칸": 칸, "칸머리": 지금칸 or "?",
            "끝": int(mb.group(1).replace(",", "")),
            "앞%": float(ma.group(2)), "뒤%": float(mb.group(2)),
            "앞낙": float(ma.group(3)), "뒤낙": float(mb.group(3)),
            "앞산": int(ma.group(4)), "뒤산": int(mb.group(4)),
            "해평균": float(mh.group(1)) if mh else None,
            "진해": f"{mh.group(2)}/{mh.group(3)}" if mh else "?",
            "문": dict(지금문),
        })

print(f"칸 판 {len(파일들)}개에서 **혼자 선 칸 {len(전체)}개**")
for 길 in 파일들:
    이름 = os.path.basename(길)
    몇 = [z for z in 전체 if z["파일"] == 이름]
    print(f"   {이름:<44} {len(몇):>4}개")
print()
print(f"{'끝 자산':>14}{'앞':>8}{'뒤':>8}{'뒤낙폭':>8}{'산것':>6}{'진해':>7}  칸 (띠 파일)")
for z in sorted(전체, key=lambda z: -z["끝"])[:40]:
    띠 = z["파일"].split("칸판_")[-1].replace(".txt", "")
    print(f"{z['끝']:>14,}{z['앞%']:>7.0f}%{z['뒤%']:>7.0f}%{z['뒤낙']:>7.1f}%{z['뒤산']:>6}{z['진해']:>7}  {z['칸'][:58]} ({띠})")

if 전체:
    print("\n── 위 다섯 칸의 문 ──")
    for z in sorted(전체, key=lambda z: -z["끝"])[:5]:
        문 = z["문"]
        print(f"   {z['칸'][:56]}")
        print(f"      칸 = {z['칸머리']} · 사건 {문.get('사건', '?')}건 · 잉여금 ≥ {문.get('잉여금', '?')}% ·"
              f" 부채 ≤ {문.get('부채', '?')}% · 대금 ≥ {문.get('대금', '?')}억 · 칸 상대갭 {문.get('갭', '?')}%")
