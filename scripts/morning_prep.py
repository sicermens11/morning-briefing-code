#!/usr/bin/env python3
r"""
morning_prep.py — **매일 07:50에 브리핑 준비를 한 번에** (2026-09-04 신설)

## 하는 일 (차례대로)
```
1. 미국 시세 갱신          어젯밤 미국 종가가 있어야 국면을 잰다
                          ⚠️ Yahoo가 마지막 일봉을 늦게 채운다 -> meta로 보정 (2026-09-04 고침)
2. 예측 기록 + 채점        record_pick.py
                          오늘 후보를 남기고, 40일 지난 옛 후보를 채점한다
3. 브리핑 조각 만들기       build_rule_html.py -> data/today-rule.html
                          08:00 브리핑이 이 파일을 읽어 그대로 붙인다
```
⚠️ 하나가 실패해도 다음을 돈다. 실패는 로그에 그대로 남긴다.
⚠️ **브리핑(08:00)보다 먼저** 끝나야 한다. 그래서 07:50이다.

쓰는 법:
    python scripts\morning_prep.py
로그: `data/_morning_prep.log`
"""
import datetime as dt
import io
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "_morning_prep.log")

차례 = (
    # ⚠️⚠️ **이게 맨 앞에 있어야 한다** (2026-09-04 신설).
    #    record_pick 은 `기준일 = 가장 최근 krx-daily`로 신호를 만든다.
    #    그런데 전 거래일 종가 파일은 **08:20쯤 브리핑이 받아 왔다** (실측: 09-04 08:22).
    #    morning_prep 은 07:50이라 **그때는 아직 없다.**
    #    ⇒ 그대로 두면 record_pick 이 **하루 묵은 종가**로 후보를 뽑는다.
    #      월요일 07:50이면 금요일이 아니라 목요일 종가를 쓴다 — 조용히 하루가 밀린다
    #    ⚠️ `--check` 는 안 붙인다. 그건 브리핑 로그의 picks 와 대조하는 것인데
    #       07:50에는 오늘 브리핑이 아직 안 돌아서 대조할 게 없다
    # ⚠️⚠️ **2026-09-07 실측: 07:50에는 아직 안 준다.**
    #    09-03 자료 -> 09-04 08:22:59 도착 / 09-04 자료 -> 09-07 08:24:18 도착
    #    그래서 그날 07:50 실행이 **하루 묵은 종가로 후보를 뽑았고**,
    #    신호기준일이 같아 중복방지가 걸려 **기록이 아예 안 남았다**
    #    ⇒ 여기서 **기다렸다 받는다** (2분 간격, 최대 25분 = 08:15까지)
    # 2026-09-07 저녁: **후보 뽑기를 여기서 뺐다.**
    #    07:50  record_pick 이 「가장 최근 krx-daily」로 후보를 뽑는다
    #    08:19~08:24  브리핑이 fetch_krx 로 전 거래일 종가를 받는다 (나흘 실측)
    #    -> 07:50 후보는 늘 **하루 묵은 종가**로 뽑힌 것이었다
    #    fetch_krx_wait(2분 간격 25분 = 08:15까지)로 메우려 했지만 그래도 늦다.
    #    => record_pick / build_rule_html 을 run-briefing.ps1 의 KRX 절 뒤로 옮겼다.
    #       거기서는 종가가 확실히 있고, 웹 게시(publish_pages)보다도 앞이다
    # ⚠⚠ **여기가 맞다 — 저녁으로 옮겼다가 되돌렸다** (2026-09-09).
    #    사용자 지적: 「미국 시세는 우리 새벽에 끝나서 그 시세와 뉴스가
    #      그날 우리 국장에 반영되니까, 저녁이 아니라 **새벽 미장 끝나고
    #      국장 시작 전**에 받는 게 맞는 거 아니야?」
    #    맞다. 미국 장은 한국 시간 **새벽 5~6시**에 끝난다:
    #      저녁 19:00 에 받으면 -> **그날 새벽 종가**까지만 들어 있고
    #      아침 07:50 에 받으면 -> **방금 끝난 미장**이 들어 있다 ← 이게 맞다
    #    오늘 아침 브리핑은 **오늘 새벽 미장**을 보고 써야 한다
    ("미국 시세 갱신", ["collect_yahoo.py", "--심볼",
                        "NVDA,AMAT,LRCX,SOXX,KLAC,WDC,MU,ASML,QQQ,XLK,SPY"],
     600),

)


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as fp:
            fp.write(line + "\n")
    except Exception:
        pass


def 장서는날():
    r"""오늘 한국 장이 서나. 서면 (True, 사유), 아니면 (False, 사유)

    ⚠️ **2026-09-04 신설.** 예약이 토·일에도 07:50에 돌고 있었다.
       그러면 **금요일 종가로 「오늘 볼 종목」을 만들어** today-rule.html에
       박아놓는다. 월요일 07:50에 다시 만들기는 하지만,
       그 사이 브리핑을 열면 **이틀 묵은 후보를 오늘 것처럼 본다**
    ⚠️ 공휴일은 여기서 안 본다. **krx-daily의 마지막 날짜**로 판단한다 —
       달력을 따로 두면 그게 또 틀린다 (설·추석은 해마다 움직인다)
    """
    오 = dt.date.today()
    if 오.weekday() >= 5:
        return False, f"{'토일'[오.weekday()-5]}요일 — 장이 안 선다"
    return True, ""


def main():
    선다, 왜 = 장서는날()
    if not 선다:
        찍기(f"===== 아침 준비 **건너뜀** — {왜} =====")
        찍기("     (today-rule.html을 낡은 자료로 덮어쓰지 않는다)")
        return 0
    찍기("===== 아침 준비 시작 =====")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    실패 = 0
    for 이름, 인자, 제한 in 차례:
        p = os.path.join(_BASE, "scripts", 인자[0])
        if not os.path.exists(p):
            찍기(f"  ⚠️ {이름}: {인자[0]} 없음 — 건너뜀")
            실패 += 1
            continue
        시 = dt.datetime.now()
        try:
            r = subprocess.run([sys.executable, p] + 인자[1:],
                               capture_output=True, timeout=제한,
                               env=env, cwd=_BASE)
            초 = (dt.datetime.now() - 시).total_seconds()
            if r.returncode == 0:
                찍기(f"  ✅ {이름} ({초:.0f}초)")
            else:
                실패 += 1
                꼬 = r.stdout.decode("utf-8", errors="replace")[-300:]
                찍기(f"  ⚠️ {이름}: 코드 {r.returncode} — {꼬.strip()[:200]}")
        except subprocess.TimeoutExpired:
            실패 += 1
            찍기(f"  ⚠️ {이름}: 시간 초과 ({제한}초)")
        except Exception as e:
            실패 += 1
            찍기(f"  ⚠️ {이름}: {type(e).__name__} {str(e)[:100]}")
    # ── ⚠️ **신호기준일이 전 거래일이 맞나** (2026-09-04 신설) ──
    #    KRX가 07:50에 전 거래일 종가를 이미 줬는지는 **해봐야 안다.**
    #    안 줬으면 record_pick 이 하루 묵은 종가로 후보를 뽑는데,
    #    로그만 보면 「✅ 성공」이라 **조용히 틀린다.** 그래서 여기서 대조한다
    try:
        import glob as _g
        _f = sorted(_g.glob(os.path.join(_BASE, "data", "krx-daily", "*.json")))
        _최신 = os.path.basename(_f[-1])[:8] if _f else "(없음)"
        _d = dt.date.today() - dt.timedelta(days=1)
        while _d.weekday() >= 5:
            _d -= dt.timedelta(days=1)
        _전 = _d.strftime("%Y%m%d")
        if _최신 == _전:
            찍기(f"  ✅ 종가 자료 최신 {_최신} = 전 거래일")
        else:
            # 2026-09-07: 이제 07:50에 밀려 있는 게 **정상**이다.
            #    후보는 브리핑(08:20쯤)이 종가를 받은 뒤에 뽑으므로 실패로 안 센다
            찍기(f"  · 07:50 현재 종가는 아직 전 거래일이 아니다 — 최신 {_최신}, "
                 f"달력상 전 거래일은 {_전}")
            찍기(f"     달력상 전 거래일은 {_전} — 브리핑이 08:20쯤 받아서 "
                 f"그때 후보를 뽑는다. 여기서는 문제가 아니다")
    except Exception as e:
        찍기(f"  ⚠️ 종가 날짜 대조 실패: {type(e).__name__} {str(e)[:60]}")

    # 결과 확인
    h = os.path.join(_BASE, "data", "today-rule.html")
    if os.path.exists(h):
        크 = os.path.getsize(h)
        찍기(f"  today-rule.html {크:,}바이트")
    else:
        찍기("  ⚠️⚠️ today-rule.html이 없다 — 브리핑에서 그 절이 빠진다")
    찍기(f"===== 끝 · 실패 {실패}건 =====")
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
