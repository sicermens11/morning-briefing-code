#!/usr/bin/env python3
r"""
make_spec.py — 무리 판 결과(⑨ 결론)에서 **통과 규칙**을 뽑아 multi_lab 재료(스펙)를 만든다 (2026-10-02)

· 어제(10/1)는 scratchpad 의 parse_rules.py 로 손으로 만들었다 → 정식 스크립트로 옮김
· 쓰는 법:  SPEC_GLOB="2026-10-0*_B*_무리전용_*_자름20_낙폭체없음.txt" python scripts/make_spec.py
  → data/_labs/multi_rules_spec.json (전 것은 multi_rules_spec_<시각>.json 으로 남김)
  → data/_labs/multi_groups.txt (own_lab OWN_GROUPS 한 줄 — 규칙이 있는 무리만 · 결과 파일 이름 앞머리는 SPEC_OUTPRE)
· ⑨ 결론 줄 모양: `  [조건] · 앞 2011~ 8.0년짜리( ⚠️) · 사는 문턱 X · 하루 N종목 · 순서 Y · 파는 규칙 Z`
                 다음 줄 `     뒤 2019~: 끝원 (현금만 …) · 연 a% · 낙폭 b% · 1년 c번`
"""
import datetime
import glob
import io
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
_L = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "_labs")


def 무리칸(무리):
    """「규모 10,000억~(상한 없음)」 → 규모||10000|| · 「업종 = 건설」 → 업종|건설|| (종류|값|LO|HI)"""
    m = re.match(r"규모 ([\d,]+)억~(?:\(상한 없음\)|([\d,]+)억)$", 무리)
    if m:
        return f"규모||{m.group(1).replace(',', '')}|{(m.group(2) or '').replace(',', '')}"
    m = re.match(r"(섹터|업종|종목) = (.+)$", 무리)
    if m:
        return f"{m.group(1)}|{m.group(2)}||"
    raise SystemExit(f"🛑 무리 글을 못 읽는다: {무리!r}")


def main():
    pat = os.environ.get("SPEC_GLOB")
    if not pat:
        raise SystemExit("🛑 SPEC_GLOB 을 준다 (예: 2026-10-0*_B*_무리전용_*_자름20_낙폭체없음.txt)")
    파일들 = sorted(p for p in glob.glob(os.path.join(_L, pat)) if ".시간." not in p)
    if not 파일들:
        raise SystemExit(f"🛑 파일이 없다: {pat}")
    규칙들, 빈, 터짐 = [], [], []
    for p in 파일들:
        s = io.open(p, encoding="utf-8", errors="replace").read()
        if "[대조] 무리" not in s:
            터짐.append(os.path.basename(p))
            continue
        m = re.search(r"── 무리 전용 규칙 ── ([^\n]+)", s)
        무리 = m.group(1).strip()
        a, b = s.find("⑨ **결론"), s.find("[대조] 무리")
        구 = s[a:b] if a >= 0 else ""
        줄들 = 구.splitlines()
        n0 = len(규칙들)
        for k, 줄 in enumerate(줄들):
            z = re.match(r"\s+\[(.+?)\] · 앞 (\d{4})~ ([\d.]+)년짜리( ⚠️)? · 사는 문턱 (.+?) · 하루 (\d+)종목 · 순서 (\S+) · 파는 규칙 (.+)$", 줄)
            if not z:
                if re.match(r"\s{5}\[", 줄) and " · 앞 " in 줄:
                    print(f"  ⚠️ 결론 줄인데 못 읽음: {os.path.basename(p)} {줄.strip()[:120]}")
                continue
            라, 년, 해, 경, 문, 자, 순, 팔 = z.groups()
            # ⚠️ 10/2 독립 검사: OR 묶음 줄은 조건 하나가 아니다 — 다시 만들 수 없어 뺀다
            if 라.startswith("OR "):
                print(f"  🛑 뺌(OR 묶음): {os.path.basename(p)} [{라}]")
                continue
            # ⚠️ 10/2 독립 검사: 10/2 전 own_lab 은 ⑨ 조건을 [:40] 로 잘랐다 — 「돈으로 넘길 조건」 목록([:60])에서 전체를 되찾는다
            if len(라) >= 40:
                되 = sorted({m2.group(1).rstrip() for m2 in re.finditer(r"^  (\S[^\n]{39,59}?)\s+[\d,]+\s+[\d.]+%", s, re.M)
                            if m2.group(1).rstrip().startswith(라)})
                if len(되) == 1 and len(되[0]) < 60:
                    print(f"  ⓘ 잘린 조건을 되찾음: [{라}] → [{되[0]}]")
                    라 = 되[0]
                else:
                    print(f"  🛑 뺌(조건 글이 잘려 되찾지 못함 · 후보 {len(되)}개): {os.path.basename(p)} [{라}]")
                    continue
            r = {"파일": os.path.basename(p), "무리": 무리, "조건": 라, "앞시작": 년, "앞해": float(해), "짧음": bool(경),
                 "문턱": (99.0 if 문.strip() == "안 봄" else float(문.replace("%p", ""))), "자리": int(자), "순서": 순, "팔기": 팔.strip()}
            다음 = 줄들[k + 1] if k + 1 < len(줄들) else ""
            mm = re.match(r"\s+뒤 \d{4}~: ([\d,]+)원 \(현금만 [\d,]+\) · 연 ([\-\d.]+)% · 낙폭 ([\-\d.]+)% · 1년 (\d+)번", 다음)
            if mm:
                r.update({"뒤끝": int(mm.group(1).replace(",", "")), "뒤연": float(mm.group(2)),
                          "뒤낙폭": float(mm.group(3)), "뒤1년": int(mm.group(4))})
            else:
                print(f"  ⚠️ 뒤 기간 줄을 못 읽음: {os.path.basename(p)} [{라}]")
            규칙들.append(r)
        if len(규칙들) == n0:
            빈.append(무리)
    for k, r in enumerate(규칙들, 1):
        r["id"] = f"O{k:02d}"
    print(f"파일 {len(파일들)}개 · 통과 규칙 {len(규칙들)}개 · 통과 0 무리 {len(빈)}개 · 끝까지 안 간 파일 {len(터짐)}개 {터짐 or ''}")
    for r in 규칙들:
        print(f"  {r['id']} {r['무리']:<26} [{r['조건']}] 앞 {r['앞시작']}~{' ⚠️' if r['짧음'] else ''} · 문턱 {r['문턱']:g} · 자리 {r['자리']}"
              f" · {r['순서']} · {r['팔기']} · 뒤 연 {r.get('뒤연')}% · 낙폭 {r.get('뒤낙폭')}%")
    밖 = os.path.join(_L, "multi_rules_spec.json")
    if os.path.exists(밖):
        shutil.copy(밖, os.path.join(_L, f"multi_rules_spec_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"))
    io.open(밖, "w", encoding="utf-8").write(json.dumps(
        {"만든날": f"{datetime.datetime.now():%Y-%m-%d %H:%M}", "출처": pat, "규칙": 규칙들}, ensure_ascii=False, indent=1))
    앞머리 = os.environ.get("SPEC_OUTPRE") or f"{datetime.date.today():%Y-%m-%d}_내보내기_"
    무리들 = []
    for r in 규칙들:
        if r["무리"] not in 무리들:
            무리들.append(r["무리"])
    칸들 = []
    for k, 무리 in enumerate(무리들, 1):
        칸들.append(f"{무리칸(무리)}|{앞머리}{k:02d}.txt")
    io.open(os.path.join(_L, "multi_groups.txt"), "w", encoding="utf-8").write(";".join(칸들))
    print(f"썼다 {밖} · multi_groups.txt 무리 {len(칸들)}개")
    if 터짐:
        print("  🛑 끝까지 안 간 결과 파일이 있다 — 그 무리 규칙은 빠졌다")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
