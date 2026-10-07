#!/usr/bin/env python3
r"""
preflight_check.py — **판을 걸기 전 점검** (2026-10-07)

사용자 10/7 「지금 테스트가 효율적인가?」 → 이번 주 다시 돌리기 6번 중 셋은 걸기 전에 알 수 있었다:
  · B225 시장 전체 판 — 시작 때 여유 27.7GB 로 24.5GB 판을 걸어 메모리로 꺼짐
  · B230 한 계좌 합치기 — 실전 후보(10/1 까지)와 무리 후보(10/2 까지) 끝 날이 달라 멈춤
  · B234 — 후보는 나눔 2023 으로 냈는데 합치기는 2019 로 돌아 대조 틀림
쓰는 법 (대기열 스크립트에서 판 바로 앞에):
    python scripts\preflight_check.py --종류 multi      (MULTI_SPEC · MULTI_CAND · MULTI_SPLIT 환경변수를 그대로 본다)
    python scripts\preflight_check.py --종류 own_all    (시장 전체 · 여유 32GB↑)
    python scripts\preflight_check.py --종류 own        (무리 판 · 여유 15GB↑)
    python scripts\preflight_check.py --종류 gate7      (여유 12GB↑)
끝 코드 0 = 걸어도 된다 · 1 = 걸지 마라(이유를 찍는다)
"""
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
_B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_L = os.path.join(_B, "data", "_labs")
_필요GB = {"own_all": 32.0, "own": 15.0, "gate7": 12.0, "multi": 12.0}


def 여유GB():
    try:
        o = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "[math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory/1MB,1)"],
                           capture_output=True, text=True, timeout=60).stdout.strip()
        return float(o)
    except Exception:  # noqa: BLE001
        return None


def 머리끝날(p):
    끝 = set()
    for 줄 in io.open(p, encoding="utf-8"):
        if '"_머리"' in 줄:
            끝.add(json.loads(줄)["끝날"])
    return 끝


def 대조나눔(p):
    나 = set()
    for 줄 in io.open(p, encoding="utf-8"):
        if '"대조끝"' in 줄:
            z = json.loads(줄)
            if z.get("나눔"):
                나.add(str(z["나눔"])[:4])
    return 나


def main():
    종류 = sys.argv[sys.argv.index("--종류") + 1] if "--종류" in sys.argv else "own"
    문제 = []
    m = 여유GB()
    필요 = _필요GB.get(종류, 15.0)
    if m is not None and m < 필요:
        문제.append(f"메모리 여유 {m}GB < 이 판에 필요한 {필요}GB")
    if 종류 == "multi":
        스펙 = os.environ.get("MULTI_SPEC") or "multi_rules_spec.json"
        후보 = os.environ.get("MULTI_CAND") or "multi_cand_own.jsonl"
        나눔 = os.environ.get("MULTI_SPLIT") or "2019"
        경로 = {"스펙": os.path.join(_L, 스펙), "무리 후보": os.path.join(_L, 후보),
                "실전 후보": os.path.join(_L, "multi_cand_live.jsonl")}
        for 이름, p in 경로.items():
            if not os.path.exists(p):
                문제.append(f"{이름} 파일이 없다: {p}")
        if not 문제 or all("없다" not in x for x in 문제):
            끝들 = 머리끝날(경로["무리 후보"]) | 머리끝날(경로["실전 후보"])
            if len(끝들) != 1:
                문제.append(f"후보 파일들의 끝 날이 다르다 {sorted(끝들)} — 실전 후보(MULTIDUMP)나 무리 후보를 다시 내라")
            나들 = 대조나눔(경로["무리 후보"])
            if 나들 and 나들 != {나눔}:
                문제.append(f"무리 후보의 나누는 해 {sorted(나들)} ≠ 합치기 MULTI_SPLIT {나눔}")
    if 문제:
        print("🛑 걸지 마라 — " + " · ".join(문제))
        return 1
    print(f"✅ 점검 통과 ({종류} · 여유 {m}GB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
