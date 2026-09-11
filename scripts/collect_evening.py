#!/usr/bin/env python3
r"""
collect_evening.py — **장 마감 뒤 그날 것을 받아 쌓는다** (2026-09-01 신설)

⚠️⚠️ **왜 저녁인가.** 아침 08:00 브리핑에 붙이면 안 된다:
   - **수급**(외국인·기관)은 **확정치가 18시 이후**에 나온다. 장중 값은 잠정치다.
   - **공시**는 장 마감 뒤에도 계속 올라온다. 아침에 받으면 전날 것이 미완성이다.
   - 아침에 받으면 **하루 늦은 것**을 쓰게 되어 갭①(장 마감 후 공시)을
     **그날 판단에 못 쓴다.** 저녁에 받아두면 다음날 아침이 바로 쓴다.

⚠️ **주가(KRX)는 이미 아침 브리핑이 받고 있다**(전 거래일 종가를 캐시한다).
   그래도 여기서 한 번 더 부른다 — 이미 있으면 `fetch_krx`가 캐시를 그대로 쓴다.

⚠️ **네 가지를 서로 독립으로 돌린다.** 하나가 실패해도 나머지는 받는다.
   (2026-08-26 교훈: 한 곳만 막고 "전부 막았다"고 착각한 적이 있다)

⚠️ **휴장일이면 아무것도 안 한다.** KRX가 빈 값을 주면 거기서 멈춘다.

쓰는 법:
    python scripts\collect_evening.py            # 오늘 것
    python scripts\collect_evening.py --date 20260831
"""
import datetime as dt
import io
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
LOG = os.path.join(_DATA, "_evening.log")


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 주가(날):
    # ⚠️ `fetch`는 **튜플 (자료, 캐시였나)**를 돌려준다. 딕셔너리가 아니다.
    import fetch_krx
    자료, 캐시 = fetch_krx.fetch(날)
    n = len((자료 or {}).get("종목") or {})
    return n, f"{n:,}종목" + (" (이미 있던 것)" if 캐시 else " ← 새로 받음")


def 공시(날):
    import fetch_dart as D
    p = os.path.join(_DATA, "dart-daily", f"{날}.json")
    g = D.disclosures(날)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(json.dumps(
        {"기준일": 날, "전체건수": g.get("전체건수"),
         "챙길공시": g.get("챙길공시") or [],
         "정보성건수": g.get("정보성건수"),
         # >>> 2026-09-03 추가. 전에는 이걸 버려서 나중에 쓰려면 다시 받는 수밖에 없었다
         "그밖의공시": g.get("그밖의공시") or []}, ensure_ascii=False))
    return g.get("전체건수") or 0, f"전체 {g.get('전체건수')}건 · 챙길 {len(g.get('챙길공시') or [])}건"


def 공시시각(날):
    # ⚠️ `하루()`는 돌려주기만 하고 저장은 안 한다 — 저장은 여기서 한다.
    import collect_disclosure_time as C
    표 = C.하루(날)
    if 표:
        p = os.path.join(_DATA, "kind-time", f"{날}.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"기준일": 날, "건수": len(표), "시각": 표}, ensure_ascii=False))
    return len(표), f"{len(표)}건의 시각"


def 수급(날):
    # ⚠️⚠️ 백필이 도는 중이면 건너뛴다. 네이버를 동시에 두 배로 때리면 PC가 얼 수 있다
    #    (2026-09-01 실제로 얼었다). 어차피 백필이 그날 것까지 채운다.
    잠 = os.path.join(_DATA, "_flowfill.lock")
    if os.path.exists(잠):
        연 = dt.datetime.fromtimestamp(os.path.getmtime(잠))
        if (dt.datetime.now() - 연).total_seconds() < 6 * 3600:      # 6시간 넘으면 죽은 잠금
            raise RuntimeError(f"백필이 도는 중이라 건너뛴다 (잠금 {연:%H:%M})")
        os.remove(잠)
    import collect_flow
    # ⚠️⚠️ **2026-09-03 수정.** 전에는 `sys.argv = ["x"]`로 인자를 비웠다.
    #   그러면 `collect_flow`가 **`fetch_one` 경로**를 타는데, 그건 종목당
    #   거래상태·재무3개년·분기6개·**공매도**·리서치까지 **5개 API**를 부른다.
    #   2,766종목이면 **1만 4천 회**다. 게다가 공매도는 KRX 세션이 필요해 자주 실패하고
    #   재시도로 시간을 끈다 — 09-02 저녁 수집이 이 단계에서 오래 끌다 끊겼다.
    #   ⇒ `--bizdate`를 주면 **`trend` API 하나만** 부른다(종목당 1회). 수급만 필요하니 그걸로 충분하다.
    # ⚠️ **`bizdate`는 「그 날짜 **이전** 10영업일」을 준다** (2026-09-03 실측).
    #   `--bizdate 20260901`을 주면 08-31까지만 오고 09-01은 안 온다.
    #   ⇒ 그날 것을 받으려면 **이틀 뒤**를 줘야 한다. 넉넉히 잡아도 손해가 없다
    #     (어차피 10일치를 받아 이미 있는 날은 덮어쓴다).
    뒷날 = (dt.datetime.strptime(날, "%Y%m%d") + dt.timedelta(days=2)).strftime("%Y%m%d")
    sys.argv = ["x", "--bizdate", 뒷날]
    collect_flow.main()
    p = os.path.join(_DATA, "flow-daily", f"{날}.json")
    n = json.load(io.open(p, encoding="utf-8-sig")).get("종목수", 0) if os.path.exists(p) else 0
    return n, f"{n:,}종목"


def main():
    날 = (sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv
          else dt.date.today().strftime("%Y%m%d"))
    찍기(f"===== 저녁 수집 시작 · {날} =====")

    # ⚠️⚠️ **당일 주가는 저녁에 못 받는다** (2026-09-01 20:28 실측: 아직 안 준다).
    #    KRX OpenAPI는 일봉을 늦게 올린다 — 아침 브리핑이 08:27에 **전 거래일** 것을 받는다.
    #    그래서 여기서는 **전 거래일이 캐시에 있는지 확인만** 하고, 당일은 시도만 한다.
    # ⚠️ 예전에는 "주가 0종목 → 휴장일 → 나머지 건너뛴다"였는데, 당일 주가가 원래 안 오므로
    #    **평일에도 전부 건너뛸 수 있는 위험한 판정**이었다. 없앴다.
    # ⚠️⚠️ **저녁에 KRX 주가를 시도하지 않는다** (2026-09-09 고침).
    #    when_krx.py 로 20분 간격 관측한 결과 **답이 나왔다**:
    #      09-08 19:02 ~ 09-09 07:43  계속 없음
    #      09-09 **08:03**  유가증권·코스닥·지수가 **2초 안에 같이** 도착
    #    -> 밤새 절대 안 나온다. 시도할 이유가 없다
    #    -> 아침 **07:52 예약 `KrxFetchBeforeBriefing`** 이 받는다
    #    사용자: 「이거 왜 또 뜨는 거야? 수집 시간 수정한 거 아니야?」
    찍기("  주가(KRX)     — 저녁엔 안 받는다 (실측 **08:03 도착**). "
         "아침 07:52 예약이 받는다")

    # ⚠️⚠️ **2026-09-03 추가: 지수(KRX).** 전에는 이 목록에 **지수가 아예 없었다.**
    #   그래서 `index-daily`가 09-02에 비었고, 지금까지 사람이 `collect_index.py`를
    #   수동으로 돌려 채워왔다. 국면 판정(코스피 200일 수익률)이 지수를 쓰므로 빠지면 안 된다.
    def 지수(날):
        import collect_index
        앞 = sys.argv[:]
        sys.argv = ["x"]
        try:
            collect_index.main()
        finally:
            sys.argv = 앞
        p = os.path.join(_DATA, "index-daily", f"{날}.json")
        n = len(json.load(io.open(p, encoding="utf-8-sig")).get("지수") or {}) \
            if os.path.exists(p) else 0
        return n, (f"{n}개 지수" if n else "아직 안 올라왔다")

    def etf(날):
        r"""국내 ETF 전종목 종가.

        ⚠️ **2026-09-07 여기에 넣었다.** collect_krx_etf.py 는 09-03에
           「16.7년치 한 번 받는 것」으로 만들었는데 **매일 도는 자리가 없어서**
           닷새 밀렸다 (최신 20260901). selfcheck 가 잡아줘서 알았다.
           ⇒ 저녁 수집에 붙인다. 이미 받은 날은 건너뛰므로 보통 몇 초다
        """
        import subprocess
        p = os.path.join(_BASE, "scripts", "collect_krx_etf.py")
        e2 = dict(os.environ)
        e2["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, p, "--최근", "10"],
                           capture_output=True, timeout=900, env=e2, cwd=_BASE)
        꼬 = r.stdout.decode("utf-8", errors="replace").strip()\
                     .splitlines()
        return 0, (꼬[-1].strip() if 꼬 and 꼬[-1].strip()
                   else f"코드 {r.returncode}")

    def _돌리기(파일, 인자, 제한=1800):
        """스크립트 하나를 돌리고 마지막 줄을 돌려준다"""
        import subprocess
        p = os.path.join(_BASE, "scripts", 파일)
        if not os.path.exists(p):
            return 0, f"{파일} 없음"
        e2 = dict(os.environ)
        e2["PYTHONIOENCODING"] = "utf-8"
        # ⚠️⚠️ **하위를 별도 프로세스 그룹에 넣는다** (2026-09-09).
        #    2026-09-09 19:00:11 에 저녁 수집이 「환율」에서 통째로 죽었다 —
        #      환율   코드 **3221225786** (0xC000013A = STATUS_CONTROL_C_EXIT)
        #    그 뒤 금리·수급·ETF·뉴스가 **하나도 안 받아졌다.**
        #    아래 for 문에 `except Exception` 이 있었는데도 소용없었다:
        #    **KeyboardInterrupt 는 Exception 이 아니라 BaseException** 이고,
        #    Ctrl+C 는 **콘솔 그룹 전체**에 가므로 부모까지 같이 죽는다.
        #    CREATE_NEW_PROCESS_GROUP 이면 하위가 죽어도 부모는 산다
        플 = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        _t0 = time.time()
        r = subprocess.run([sys.executable, p] + 인자, capture_output=True,
                           timeout=제한, env=e2, cwd=_BASE,
                           creationflags=플)
        _걸림 = time.time() - _t0
        꼬 = r.stdout.decode("utf-8", errors="replace").strip().splitlines()
        # ⚠️⚠️ **2026-09-10 넣음** — 전에는 `r.stderr` 를 잡아놓고 **버렸다**.
        #    2026-09-09·09-10 두 번이나 저녁 수집이 통째로 죽었는데
        #    (코드 3221225786) **무슨 일이 있었는지 알 길이 없었다**
        if r.returncode != 0:
            _e = r.stderr.decode("utf-8", errors="replace").strip()
            찍기(f"    ⚠️ {파일} 코드 {r.returncode} ({_걸림:.0f}초)")
            for _줄 in _e.splitlines()[-6:]:
                if _줄.strip():
                    찍기(f"       {_줄.strip()[:150]}")
        말 = (꼬[-1].strip()[:110] if 꼬 and 꼬[-1].strip()
              else f"코드 {r.returncode}")
        return 0, f"{말}  [{_걸림:.0f}초]"

    # ══════════════════════════════════════════════════════════════
    #  ⭐⭐ **2026-09-09 합침** — 흩어져 있던 수집기를 여기로 모은다
    #     사용자: 「어차피 수집하는 거면 한번에 수집하는 게 좋을 것 같아서!
    #             매일 수집해야 하는 정보는 한 가지 스크립트로 시간 맞춰서 한번에」
    #     전에는 26개 수집기 중 **8개만** 여기서 돌았고 나머지는
    #     주말 예약이거나 **아무도 안 불렀다** (컨센서스 6일·임원지분 7일 밀림)
    #
    #  ⭐⭐ **2026-09-09 밤 · 셋 더 합침** — 예약이 **일회성 트리거**여서
    #     며칠째 안 돌고 있던 것들이다 (OvernightDataCollect 는 9/2 이후 안 돎):
    #       CapitalCollect  -> 매일 「증자감자(DART)」
    #       IndustryCollect -> 토요일 「업종분류(DART)」
    #       DividendCollect -> 일요일 「사업보고서(DART)」
    #     ⚠️ **OvernightDataCollect 는 합치지 않는다.** 그 존재 이유가
    #        「DART 하루 한도 20,000회 때문에 **저녁에 못 받은 걸 자정 후에** 받기」다.
    #        합치면 한도에 걸려 둘 다 못 받는다
    # ══════════════════════════════════════════════════════════════

    def 환율(날):
        """원/달러·엔/원 (2026-09-09 합침 — 전에는 아무도 안 불렀다)"""
        return _돌리기("collect_fx.py", [], 600)

    def 금리(날):
        """미국 금리 (**Alpha Vantage** · 2026-09-09 갈아탐)

        ⚠️⚠️ **FRED 는 2026-09-03부터 접속 자체가 안 된다** —
           TimeoutError · ConnectionResetError 가 이어졌고, 저녁 수집에서
           **매일 600초(10분)를 버렸다.**
           그런데 시험들(brief_lab·cut_lab·group_lab·prob2_lab)이 읽는 것은
           원래부터 **AV_(Alpha Vantage) 파일**이었다. 그걸 갱신하는 쪽이 맞다.
           ✅ 실측: 기준금리 26,367개 · 2년물 12,563개 · **10년물 16,155개(새로)**
        """
        return _돌리기("collect_rates_av.py", [], 300)

    def 미국시세(날):
        # ⚠⚠ **쓰지 않는다** (2026-09-09 되돌림).
        #    미국 장은 한국 시간 새벽 5~6시에 끝난다.
        #    저녁 19:00 에 받으면 **그날 새벽 것까지**만 들어 있어
        #    내일 아침 브리핑이 쓰기에는 **하루 묵은 것**이 된다.
        #    -> `morning_prep.py` 가 07:50 에 받는 게 맞다 (사용자 지적)
        #    함수는 남겨둔다 — 아침이 실패했을 때 손으로 부를 수 있게
        r"""미국 지수·ETF (Yahoo).

        ⚠️ 아침 07:50(morning_prep)에서 **저녁으로 옮겼다** (2026-09-09).
           미국 장은 우리 새벽에 끝나므로 저녁에 받아도 늦지 않고,
           아침 브리핑이 만들어질 때 **이미 있는 상태**가 된다
        """
        return _돌리기("collect_yahoo.py",
                       ["--심볼",
                        "NVDA,AMAT,LRCX,SOXX,KLAC,WDC,MU,ASML,QQQ,XLK,SPY"],
                       900)

    def 컨센서스(날):
        """증권사 목표주가 (한경 · **주 1회**)"""
        return _돌리기("collect_consensus.py", [], 1800)

    def 계약수주(날):
        """계약·수주 공시의 금액 (**주 1회**)"""
        return _돌리기("collect_contract.py", [], 1800)

    def 임원지분(날):
        """임원·주요주주 매매 (**주 1회**)"""
        # ⚠️ **--갱신일 6** 이 없으면 한 건도 안 받는다 (2026-09-09 확인).
        #    종목 단위로 「이미 받았으면 건너뛴다」라서 2026-09-01 이후
        #    8일간 갱신이 멈춰 있었다
        return _돌리기("collect_exec.py",
                       ["--상한", "3000", "--갱신일", "6"], 3000)

    def 대량보유(날):
        """5% 대량보유 신고 (**주 1회**)"""
        # ⚠️ 임원지분과 같은 병 — **--갱신일 6** 을 준다
        return _돌리기("collect_major.py",
                       ["--상한", "3000", "--갱신일", "6"], 3000)

    def 연간재무(날):
        """연간 재무제표 (**주 1회**)"""
        return _돌리기("collect_fin.py", [], 2400)

    def 주식선물(날):
        r"""선물·주식선물·국고채·금·유가 (KRX).

        경고: 2026-09-07 여기 넣었다. 사용자가 「주식선물(유가)」를 신청해
        승인받았는데, 매일 도는 자리가 없으면 오늘치로 멈춘다 —
        etf-krx 가 닷새 밀렸던 것과 같은 함정이다
        """
        return _돌리기("collect_krx_extra.py", ["--최근", "10"])

    def 분기재무(날):
        r"""DART 분기 재무.

        경고: DART 하루 한도 20,000회를 공시 수집과 나눠 쓴다.
        그래서 저녁에는 3,000회만 쓴다. 백필은 며칠에 걸쳐 끝난다
        """
        return _돌리기("collect_quarter.py", ["--상한", "3000"], 2400)

    def 뉴스(날):
        r"""종목뉴스 (네이버).

        경고: 비공식 API라 천천히 돈다. --갱신 이라 새 기사만 덧붙인다
        """
        # ⭐⭐ **2026-09-10 사용자 결정 ㉡** — 밴드(2,410종목) -> **후보만**
        #    ```
        #    전   --밴드   2,410종목 x 3쪽 x 0.5초  =  **4시간**
        #    후   --후보   forward-log 종목 40개 안팎  =  **몇 분**
        #    ```
        #    왜: record_pick 에 뉴스가 0줄이라 **퀀트 후보에 안 쓰인다**.
        #        읽는 곳은 전부 시험 파일인데 189차 G절이 「자료가 1.5년뿐 —
        #        **참고만** 한다」고 적어놨다. 네이버 종목뉴스는 **과거를
        #        소급해 못 받아** 16.7년 검증이 영영 불가능하다.
        #        그런데 저녁 수집 **맨 뒤**라 죽으면 통째로 날아간다
        #        (2026-09-10 19:04 실제로 죽어 뉴스를 못 받았다)
        #    => **앞으로 쌓는 쪽**으로 바꾼다. 예측 기록과 짝이 맞는다
        return _돌리기("collect_news.py",
                       ["--후보", "--갱신", "--쪽", "3", "--쉼", "0.5"], 1800)

    def 증자감자(날):
        """증자·감자·자사주 **결정** 공시 (2026-09-09 합침 · 옛 CapitalCollect)

        ⚠️ dart-daily 의 **공시 제목**만으로는 규모를 모른다 —
           「유상증자 1%」와 「유상증자 50%」가 같이 세어졌다.
           이 API 는 **주식수·금액·비율**을 준다
        """
        # ⚠️ **--갱신일 6** 이 없으면 한 건도 안 받는다 — 종목 단위로 건너뛰기 때문
        # ⚠️⚠️ **6 -> 30** (2026-09-11). `--갱신일 6` 은 6일 지난 종목을 전부
        #    다시 받는다 -> 3,989종목 · **호출 23,934회(상한 19,000) · 72분**.
        #    제한이 40분이라 **끝날 수 없는 구조**였고, 9/10·9/11 이틀 연속
        #    여기서 죽어 뒤에 있던 **뉴스가 통째로 날아갔다.**
        #    증자·감자 공시는 한 번 나면 안 바뀌고, 새 공시는 `dart-daily` 가
        #    매일 따로 받는다 -> 같은 종목을 6일마다 다시 받을 이유가 없다
        return _돌리기("collect_capital.py", ["--갱신일", "30"], 2400)

    def 업종분류(날):
        """업종 분류 (2026-09-09 합침 · 옛 IndustryCollect)

        ⚠️ 신규상장 때만 바뀐다 -> **주 1회(토)** 면 충분하다
        """
        return _돌리기("collect_industry.py", [], 1800)

    def 사업보고서(날):
        """자기주식·소액주주·증자감자·배당 (2026-09-09 합침 · 옛 DividendCollect)

        ⚠️ **사업보고서 = 연 1회 스냅샷**이다. 2024 사업보고서는 2025년 3~4월에 나온다.
           매일 돌 까닭이 없다 -> **주 1회(일)**. 이미 받은 것은 건너뛴다
        """
        return _돌리기("collect_dart_snap.py",
                       ["--항목", "자기주식", "--상한", "5400"], 5400)

    # ⚠️⚠️ **순서가 중요하다.** 뉴스가 최대 90분 걸린다 —
    #    앞에 두면 뒤엣것이 다 밀린다. **가벼운 것부터, 뉴스는 맨 뒤로**
    매일할것 = (("공시(DART)", 공시), ("공시시각(KIND)", 공시시각),
                ("환율", 환율), ("금리(FRED)", 금리),
                ("수급(네이버)", 수급),
                # ⚠️⚠️ **ETF·주식선물은 아침 08:11 로 옮겼다** (2026-09-10).
                #    실측: 이것들은 **08:10 에 온다** — 저녁 19:00 엔 그날 자료가 없어
                #    **하루 늦은 것**을 받고 있었다 (krx-extra 최신이 이틀 전이었다).
                #    ⚠️ record_pick 이 etf-krx 를 읽는다 — 낡으면 후보가 틀어진다
                # ⚠️ **분기재무는 밤샘으로 넘김** (2026-09-09) —
                #    collect_overnight 이 매일 같은 것을 받는다(중복).
                #    DART 하루 한도 20,000회가 **자정에 리셋**되므로 밤샘이 유리하다
                # ⭐ 2026-09-09 합침 — 옛 CapitalCollect 예약.
                #    증자·감자는 **날짜 이벤트**라 매일 받아야 한다
                # ⚠️⚠️ **뉴스가 증자감자보다 앞이다** (2026-09-11).
                #    뉴스는 후보 40종목만 받아 **2분**이면 끝나는데,
                #    72분짜리 증자감자 뒤에 서 있어 **이틀 연속 날아갔다.**
                #    가벼운 것을 먼저 끝내면 뒤엣것이 죽어도 뉴스는 남는다
                ("뉴스(네이버)", 뉴스),
                ("증자감자(DART)", 증자감자))
    # ⭐ **요일을 보고** 부르는 것들 (0=월 … 6=일).
    #    매일 부르면 서버에 미안하고 시간도 오래 걸린다.
    #    하루에 하나씩 나눠 **주 1회**씩 돈다
    # ⚠️⚠️ **화·수·목을 밤샘으로 넘겼다** (2026-09-09) —
    #    계약·수주 / 임원지분 / 5%대량보유 셋 다 collect_overnight 이 **매일** 받는다.
    #    주 1회였던 것이 오히려 **더 자주** 갱신된다.
    #    DART 하루 한도(20,000회)가 자정에 리셋되므로 밤샘 쪽이 예산에 맞다
    주간할것 = {0: ("컨센서스(한경)", 컨센서스),
                4: ("연간재무(DART)", 연간재무),
                # ⭐ 2026-09-09 합침 — 월~금이 이미 차서 토·일에 넣는다
                5: ("업종분류(DART)", 업종분류),
                6: ("사업보고서(DART)", 사업보고서)}
    요 = dt.datetime.strptime(날, "%Y%m%d").weekday()
    오늘것 = list(매일할것)
    if 요 in 주간할것:
        오늘것.append(주간할것[요])
        찍기(f"  (오늘은 {'월화수목금토일'[요]}요일 — "
             f"**{주간할것[요][0]}**도 받는다)")
    # ⚠️ 뉴스는 **매일할것 안**으로 옮겼다 (2026-09-11) — 아래 줄은 없앴다.
    #    「가장 오래 걸린다」는 옛말이다: 2,410종목 -> 후보 40종목으로 바뀌어
    #    **2분**이면 끝난다 (2026-09-10 사용자 결정 ㉡)
    # ⚠️ **시작도 찍는다** (2026-09-10) — 전에는 **끝날 때만** 찍어서
    #    통째로 죽으면 「어디까지 갔는지」를 마지막 성공으로만 짐작해야 했다
    for _n, (이름, 함수) in enumerate(오늘것, 1):
        try:
            찍기(f"  [{_n}/{len(오늘것)}] {이름} 시작")
            _, 말 = 함수(날)
            찍기(f"  {이름:14s}{말}")
        except Exception as e:
            찍기(f"  ⚠️ {이름} 실패: {type(e).__name__} {e}")
            찍기("     " + traceback.format_exc().strip().split("\n")[-1])
        except KeyboardInterrupt:
            # ⚠️ 사람이 진짜 Ctrl+C 를 눌렀으면 **멈추는 게 맞다.**
            #    다만 **어디서 멈췄는지 남긴다** — 2026-09-09 에는 이 줄이 없어서
            #    「환율에서 죽었다」를 로그를 뒤져 알아내야 했다
            찍기(f"  ⛔ {이름} 에서 멈춤 (Ctrl+C) — 남은 것은 안 받는다")
            raise
    찍기("===== 끝 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
