#!/usr/bin/env python3
r"""
collect_overnight.py — **밤새 남은 것을 순서대로 이어받는다** (2026-09-01 신설)

⚠️⚠️ **왜 필요한가.** 2026-09-01에 받을 것이 한꺼번에 여럿 생겼는데
   **DART 하루 한도가 20,000회**라 자정 전에 다 못 받는다.
   자정이 지나면 한도가 리셋되므로, **00:10에 한 번 돌면 나머지가 끝난다.**

⚠️ **전부 이어받기다.** 이미 받은 것은 건너뛴다 → 몇 번 돌려도 안전하고,
   앞선 수집이 잘 끝났으면 **"받을 것이 없다"만 찍고 끝난다.**

⚠️⚠️ **두 번 예약돼 있다: 00:10 과 06:30.** 사용자가 퇴근 후 집에서 KRX 서비스를
   신청하는데 **승인 시각을 모르기 때문**이다. 00:10에 아직 승인 전이면 못 받고,
   06:30에 다시 돌면서 받는다. 시험도 그때 다시 돌아 새 자료가 반영된다.

⚠️ 순서는 **값어치 순**이다. 도중에 죽어도 중요한 것이 먼저 남는다.

쓰는 법:
    python scripts\collect_overnight.py
"""
import datetime as dt
import glob
import io
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_S = os.path.join(_BASE, "scripts")
LOG = os.path.join(_BASE, "data", "_overnight.log")

# (설명, 스크립트, 인자)
할일 = [
    # ⚠️ **가장 먼저** 어제 주가를 시도한다. KRX는 당일 일봉을 저녁에 안 주지만
    #    (2026-09-01 20:28 실측) 새벽엔 올라와 있을 수 있다. 있으면 D+5 측정이 하루 앞당겨진다.
    ("어제 주가",     "fetch_krx.py",         []),
    # ⚠️⚠️ **--갱신일 6 이 없으면 한 건도 안 받는다** (2026-09-09 확인).
    #    두 스크립트는 **종목 단위로** 「이미 받았으면 건너뛴다」다 —
    #    2,650종목이 다 받아진 2026-09-01 뒤로 **8일간 갱신이 멈춰 있었다.**
    #    (dart-exec 마지막 수정 09-01 20:03 · 189차 로그도 20260901 까지)
    ("임원 자사주",   "collect_exec.py",      ["--갱신일", "6"]),
    ("대량보유(5%)",  "collect_major.py",     ["--갱신일", "6"]),
    # ⚠️ **--갱신일 6** — 종목 단위로 건너뛰므로 없으면 한 건도 안 받는다
    ("분기재무",      "collect_quarterly.py", ["--갱신일", "6"]),
    # ⚠️⚠️⚠️ **DART 하루 한도 20,000회.** 오늘 밤 예산을 이렇게 나눴다(2026-09-01):
    #    ⭐ 계약금액 13,400회 — **가장 값어치 높다.** 「15억 계약」과 「1조 계약」은 완전히
    #       다른데 지금은 「호재 공시」 한 덩어리로 본다. `계약금액 ÷ 시총`이 진짜 신호 강도다.
    #    나머지(자기주식·소액주주·배당)는 **연 스냅샷이라 시점이 흐릿해** 09-03으로 미룬다.
    #    ⚠️ 「증자감자」는 **뺐다 — 중복이다.** `grade_lab`이 이미 dart-daily 공시명으로
    #       유상증자·CB를 잡는다. 연 스냅샷보다 그쪽이 시점이 정확하다.
    #    13,400 + 브리핑 몫 4,100 = 17,500 / 20,000  ✅
    # ⚠️ F-Score는 「전년 대비」가 절반이라 **2023년치가 있어야** 2025-04부터 쓸 수 있다.
    #    없으면 2026-04부터 100일뿐이다. 505회로 싸다.
    ("2023 연간재무",  "collect_fin.py",       ["--해", "2023"]),
    # ⚠️⚠️ **2026-09-10 고침** — 13,500 -> **5,000**.
    #    13,500 은 DART 하루 한도(20,000)의 **2/3** 이라
    #    임원·대량보유·분기재무가 굶었다. 실제로 2026-09-10 저녁 수집의
    #    「공시(DART)」가 **020 한도 초과**로 실패했다.
    #    ⚠️ 게다가 트리거가 3개여서 **40,500회**를 요구하고 있었다
    #       (트리거는 00:10 하나로 줄였다)
    ("계약금액 ⭐",    "collect_contract.py",  ["--상한", "15000"]),
    # ⚠️ 승인 안 됐으면 **조용히 넘어간다.** 사용자가 집에서 신청하면 그 다음 실행에 받는다.
    ("KRX 추가(선물·상품·채권)", "collect_krx_extra.py", []),
]

# ⚠️⚠️ **수집이 전부 끝난 뒤에만 돈다.** 2026-09-01 사용자 지적:
#    *"데이터 수집이 끝나면 테스트하라고, 이미 다 받은 재료로 테스트를 최대한 돌리지 말고!"*
#    부분 데이터로 미리 돌리면 **결론을 또 물러야 한다** — 그날 하루에만 여섯 번 물렀다.
시험 = [
    # ⚠️⚠️ **entry_lab 을 맨 앞에 둔다.** 기존 분석의 look-ahead 오류(장 마감 후 공시를
    #    그날 종가에 샀다고 가정)를 숫자로 재는 시험이라, 이 결과가 나머지 해석을 바꾼다.
    ("매수시점·손절·보유", "entry_lab.py",     []),
    # ⚠️⚠️ **전제를 의심하는 시험을 맨 앞에 둔다.** 「공시가 최선의 출발점인가」에
    #    답이 나와야 나머지 결과를 어떻게 읽을지 정해진다.
    ("출발점 비교 ⭐⭐⭐", "origin_lab.py",    []),
    ("등급이 작동하나 ⭐", "grade_lab.py",     []),
    ("역추적: 오른 종목의 공통점 ⭐", "reverse_lab.py", []),
    ("위험(최악·낙폭·분산)", "risk_lab.py",     []),
    ("시간 안정성·기술지표 ⭐", "stability_lab.py", []),
    ("매도 규칙·최대상승",   "exit_lab.py",      []),
    ("전방위(축 57개)",  "omni_lab.py",      []),
    ("공시상세·신호강도",  "detail_lab.py",    []),
    ("갭 넷 통합",       "gap_all.py",       []),
    ("섹터 14개",       "sector_lab.py",    []),
    ("비용 후 실수익",    "cost_lab.py",      []),
    ("컨센서스",         "consensus_lab.py", []),
    ("조합 탐색(학습/검증)", "combo_lab.py",   []),
    ("가상매매 D+1",     "paper_trade.py",   ["--등급", "전부", "--보유", "1", "--손절없이"]),
    ("가상매매 D+3",     "paper_trade.py",   ["--등급", "전부", "--보유", "3", "--손절없이"]),
    ("가상매매 D+5",     "paper_trade.py",   ["--등급", "전부", "--보유", "5", "--손절없이"]),
    ("가상매매 D+5 손절", "paper_trade.py",   ["--등급", "전부", "--보유", "5"]),
]


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def main():
    찍기(f"===== 밤샘 수집 시작 · 할 일 {len(할일)}개 =====")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    # ⚠️ 06:30 재실행이 헛돌지 않게 — **새로 받은 게 있을 때만** 시험을 다시 돌린다.
    def 재료수():
        n = 0
        for g in ("dart-exec/*.json", "dart-major/*.json", "naver-quarter/*.json",
                  "dart-snap/*/*.json", "krx-extra/*/*.json"):
            n += len(glob.glob(os.path.join(_BASE, "data", g)))
        return n
    전 = 재료수()
    for i, (이름, 스, 인자) in enumerate(할일, 1):
        찍기(f"[{i}/{len(할일)}] {이름} 시작")
        try:
            # ⚠️ 하위 프로세스 출력은 파일로 흘린다 — 콘솔 인코딩(cp949)에 안 걸리게.
            r = subprocess.run([sys.executable, os.path.join(_S, 스)] + 인자,
                               cwd=_BASE, env=env, # ⚠️ 시험 하나가 1시간을 넘기면 끊는다 — 08:00 브리핑을 침범하면 안 된다.
                               capture_output=True, timeout=3600)
            꼬리 = (r.stdout or b"").decode("utf-8", "replace").strip().split("\n")[-1]
            if 이름 == "어제 주가" and r.returncode != 0:
                # ⚠️ 새벽엔 KRX 일봉이 거의 늘 없다 — 설계된 시도다. RuntimeError 로 찍으면 전수점검이 매일 잡는다
                찍기(f"[{i}/{len(할일)}] {이름} — 아직 안 올라옴 (예상대로 · 08:00 KrxFetchBeforeBriefing 이 받는다)")
            else:
                찍기(f"[{i}/{len(할일)}] {이름} 끝 (exit={r.returncode}) {꼬리[:110]}")
        except Exception as e:
            찍기(f"[{i}/{len(할일)}] ⚠️ {이름} 실패: {type(e).__name__} {e}")
    후 = 재료수()
    찍기(f"===== 밤샘 수집 끝 · 재료 {전:,} → {후:,} (+{후-전:,}) =====")

    # ⚠️ 수집이 다 끝났으니 이제 시험을 돌린다. 결과는 파일로 남긴다.
    출 = os.path.join(_BASE, "data", "_test")
    os.makedirs(출, exist_ok=True)
    이미 = len(glob.glob(os.path.join(출, "*.txt")))
    if 후 == 전 and 이미 >= len(시험):
        찍기(f"  새로 받은 것이 없고 시험 결과 {이미}개가 이미 있다 — 시험을 건너뛴다.")
        return 0
    # ⚠️⚠️ **다른 큰 시험이 돌면 기다린다** (2026-09-09 밤 신설).
    #    이 예약은 수집 뒤에 시험 20개를 이어서 돌린다. 그런데 밤에는
    #    우리 줄(run_queue…)도 돌고 있다 — **group_lab 은 혼자 16.3GB**를 쓴다.
    #    전체 램 31.9GB 에서 둘이 겹치면 **97%** 가 된다 (2026-09-09 실측,
    #    시험 하나를 죽여야 했다).
    #    ⚠️ 다만 **08:00 브리핑을 침범하면 안 된다** — 07:00 이 넘으면
    #       기다리기를 그만두고 시험을 통째로 건너뛴다. 수집은 이미 끝났다
    def 다른시험():
        """지금 도는 **큰 시험** 이름들"""
        큰것 = ("group_lab", "info_lab2", "gate5_lab", "gate6_lab", "gate7_lab",
                "corr_lab", "herd_lab", "sector_own_lab", "chain_lab",
                "world_lab", "vola_lab")
        try:
            o = subprocess.run(["wmic", "process", "where", "name='python.exe'",
                                "get", "CommandLine"],
                               capture_output=True, text=True, timeout=30).stdout
        except Exception:  # noqa: BLE001
            return []
        return sorted({n for n in 큰것 if f"{n}.py" in o})

    import time as _t
    while True:
        도 = 다른시험()
        if not 도:
            break
        if dt.datetime.now().hour >= 7:
            찍기(f"  ⛔ 07:00 이 넘었다 — 시험을 건너뛴다 (도는 중: {도}). "
                 f"08:00 브리핑이 먼저다")
            return 0
        찍기(f"  ⏳ 다른 시험이 돌고 있다 {도} — 5분 뒤 다시 본다")
        _t.sleep(300)

    찍기(f"===== 시험 시작 · {len(시험)}개 =====")
    for i, (이름, 스, 인자) in enumerate(시험, 1):
        찍기(f"[{i}/{len(시험)}] {이름} 시작")
        try:
            r = subprocess.run([sys.executable, os.path.join(_S, 스)] + 인자,
                               cwd=_BASE, env=env, # ⚠️ 시험 하나가 1시간을 넘기면 끊는다 — 08:00 브리핑을 침범하면 안 된다.
                               capture_output=True, timeout=3600)
            꼬리 = ("_" + "_".join(x.lstrip("-") for x in 인자)) if 인자 else ""
            io.open(os.path.join(출, 스[:-3] + 꼬리 + ".txt"), "w", encoding="utf-8").write(
                (r.stdout or b"").decode("utf-8", "replace") + chr(10)
                + "--- stderr ---" + chr(10)
                + (r.stderr or b"").decode("utf-8", "replace"))
            찍기(f"[{i}/{len(시험)}] {이름} 끝 (exit={r.returncode}) → data/_test/{스[:-3]}.txt")
        except Exception as e:
            찍기(f"[{i}/{len(시험)}] ⚠️ {이름} 실패: {type(e).__name__} {e}")
    찍기("===== 시험 끝 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
