#!/usr/bin/env python3
r"""
alert_check.py — 조용히 안 돈 것을 카톡으로 알린다 (2026-10-19 · 사용자 「알림은 카톡으로 하자.」)

왜: 계정 잠김·Claude 인증 만료로 09:05 확인 같은 예약이 2주에 5일 안 돌았는데 아무도 몰랐다.
예약 「AlertCheck」(로그인 상태 실행 — 계정이 잠겨도 돈다)가 08:15 · 09:15 · 19:30 에 부른다.

보는 것 (장 서는 날만):
  ① 꼭 돌아야 하는 예약이 오늘 돌았나 · 결과가 0 인가   (08:15 브리핑 · 09:15 동시호가·장 시작 확인 · 19:30 저녁 수집)
  ② 예약이 「계정 잠김·로그온 실패」 로 시작도 못 했나  (작업 스케줄러 기록 101·104)
  ③ 오늘 브리핑 로그에 Claude 인증 실패가 있나         (「authenticate」·「OAuth」)
  ④ 오늘 게시가 됐나                                  (「올림 완료」)
같은 알림은 하루 한 번만 보낸다(data/_alert_sent.json). 문제가 없으면 아무것도 안 보낸다.

    python scripts\alert_check.py            지금 시각에 맞는 점검
    python scripts\alert_check.py --보기     보내지 않고 무엇을 보낼지만 찍는다
⚠️ 조회·알림만. 주문은 없다.
"""
import datetime as dt
import glob
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENT = os.path.join(_BASE, "data", "_alert_sent.json")
LOGS = os.path.join(_BASE, "run-logs")

# 시각(이 시각 이후 점검에서 봄) → 오늘 돌았어야 할 예약
_꼭 = [("08:12", "MorningSectorBriefing", "08:02 아침 브리핑"),
       ("09:12", "FetchAntc0850", "08:55 동시호가(지정가 판정)"),
       ("09:12", "EntryCheck0905", "09:05 장 시작 확인"),
       ("19:25", "EveningDataCollect", "19:00 저녁 수집")]


def _ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=90)
    return r.stdout.decode("utf-8", "replace")


def _예약상태():
    names = ",".join(f"'{n}'" for _, n, _ in _꼭)
    out = _ps("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
              f"Get-ScheduledTask -TaskName {names} -ErrorAction SilentlyContinue | ForEach-Object {{ "
              "$i = $_ | Get-ScheduledTaskInfo; "
              "\"$($_.TaskName)`t$($i.LastTaskResult)`t$(if ($i.LastRunTime) { $i.LastRunTime.ToString('yyyy-MM-dd HH:mm') } else { '' })\" }")
    표 = {}
    for z in out.splitlines():
        p = z.strip().split("\t")
        if len(p) == 3:
            표[p[0]] = (p[1], p[2])
    return 표


def _시작실패(오늘):
    r"""오늘 작업 스케줄러 101·104(시작·로그온 실패) 중 이 저장소 예약 — {이름: 코드}"""
    out = _ps("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
              "Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational'; Id=101,104; "
              "StartTime=(Get-Date).Date} -ErrorAction SilentlyContinue | ForEach-Object { "
              "$n = if ($_.Message -match '\"\\\\([^\"]+)\"') { $matches[1] } else { '?' }; "
              "$c = if ($_.Message -match 'Error Value: (\\d+)') { $matches[1] } else { '' }; "
              "\"$($_.TimeCreated.ToString('HH:mm'))`t$n`t$c\" }")
    ours = {n for _, n, _ in _꼭} | {"SelfCheck", "SelfCheck-1200", "SelfCheck-2000", "ForwardRecord",
                                    "ForwardRecordDaily", "KrxFetchBeforeBriefing", "DataGapFill", "OvernightDataCollect"}
    실패 = {}
    for z in out.splitlines():
        p = z.strip().split("\t")
        if len(p) == 3 and p[1] in ours:
            실패.setdefault(p[1], (p[0], p[2]))
    return 실패


def _코드말(c):
    return {"2147944309": "계정 잠김", "1909": "계정 잠김", "267011": "아직 안 돎", "2147942402": "파일 못 찾음"}.get(str(c), f"코드 {c}")


def 점검(지금=None):
    지금 = 지금 or dt.datetime.now()
    hm = 지금.strftime("%H:%M")
    오늘 = 지금.strftime("%Y-%m-%d")
    말들 = []
    상태 = _예약상태()
    for 때, 이름, 뜻 in _꼭:
        if hm < 때:
            continue
        결과, 마지막 = 상태.get(이름, ("?", ""))
        if not 마지막.startswith(오늘):
            말들.append((f"안돎:{이름}", f"⚠️ {뜻} 이 오늘 안 돌았습니다 (마지막 {마지막 or '없음'})"))
        elif 결과 not in ("0", "267009"):
            말들.append((f"실패:{이름}", f"⚠️ {뜻} 이 실패로 끝났습니다 ({_코드말(결과)})"))
    for 이름, (시각, 코드) in _시작실패(오늘).items():
        말들.append((f"시작실패:{이름}", f"⚠️ 예약 {이름} 이 {시각}에 시작을 못 했습니다 ({_코드말(코드)})"))
    if hm >= "08:12":
        fs = sorted(glob.glob(os.path.join(LOGS, f"briefing_{오늘}_*.log")))
        if not fs:
            말들.append(("브리핑로그없음", "⚠️ 오늘 아침 브리핑 기록이 없습니다"))
        else:
            글 = "".join(io.open(f, encoding="utf-8", errors="replace").read() for f in fs)
            if "authenticate" in 글 or "OAuth" in 글:
                말들.append(("인증", "🔴 Claude 인증이 만료돼 브리핑이 실패했습니다 — 터미널에서 다시 로그인 필요"))
            if hm >= "08:40" and "올림 완료" not in 글:
                말들.append(("게시", "⚠️ 오늘 브리핑이 아직 사이트에 안 올라갔습니다"))
    return 말들


def main():
    보기 = "--보기" in sys.argv
    try:
        from krx_calendar import 장서는날
        if not 장서는날() and "--강제" not in sys.argv:
            print("장 안 서는 날 — 점검 안 함")
            return 0
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ 휴장일 판정 실패({type(e).__name__}) — 그대로 점검")
    오늘 = dt.date.today().isoformat()
    try:
        보냄 = json.load(io.open(SENT, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        보냄 = {}
    보냄 = {k: v for k, v in 보냄.items() if v == 오늘}     # 오늘 것만 남긴다
    새 = [(k, m) for k, m in 점검() if k not in 보냄]
    if not 새:
        print("알릴 것 없음")
        return 0
    글 = f"[브리핑 알림 {dt.datetime.now():%m/%d %H:%M}]\n" + "\n".join(m for _, m in 새)
    print(글)
    if 보기:
        return 0
    from kakao_notify import 보내기
    if 보내기(글):
        for k, _ in 새:
            보냄[k] = 오늘
        io.open(SENT, "w", encoding="utf-8").write(json.dumps(보냄, ensure_ascii=False))
        print("카톡 보냄")
        return 0
    print("카톡 실패 — data/_kakao.log")
    return 1


if __name__ == "__main__":
    sys.exit(main())
