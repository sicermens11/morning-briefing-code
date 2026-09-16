#!/usr/bin/env python3
r"""
audit_all.py — **전수 점검** (2026-09-09 밤 신설)

## 사용자 말 (그대로)
```
「스크립트 중에 **제대로 작동 안하는게 계속 나오는 것 같은데** 그것도 한번 전체적으로 점검하고!
  그리고 아까 **재료가 0개인데 문제가 0개로 인식**해서 제대로 수집 안되는 것도 있었던거 같은데
  **그런 류의 문제가 또 없나** 확인하고!」
```

## 오늘 하루에 나온 「조용한 실패」들 — 이 도구가 찾아야 할 것
```
① 컨센서스 빈 파일 38개   오류로 0건 받았는데 **저장해버려서**, 다음엔 「이미 받음」으로 건너뜀
② 임원·5%보유 8일 멈춤    **종목 단위** 「이미 받았으면 건너뛴다」 — 새 매매를 영영 안 받음
③ 예약 넷 일회성 트리거    9/2~9/4 이후 안 돌았는데 목록엔 「준비」로 보임
④ 저녁 수집 통째로 죽음    하위의 Ctrl+C 가 부모까지 죽임 (except Exception 이 못 잡음)
⑤ 금리(FRED) 접속 실패    9/3부터 TimeoutError — 매일 10분 버림
⑥ 190차 4관문 「전부 통과」  **기회가 6~37% 로 줄었는데** 이김만 보고 통과로 셈
```

## 재는 것
```
A  **자료가 며칠 밀렸나** — 폴더마다 최신 날짜
B  ⭐ **빈 파일·거의 빈 파일** (조용한 실패의 흔적)
C  ⭐ **0건이어도 저장하는 수집기** (코드에서 찾는다)
D  ⭐ **「이미 받았으면 건너뛴다」만 있고 갱신 수단이 없는 수집기**
E  스크립트 문법 검사 (import 까지)
F  최근 로그의 오류·타임아웃
G  ⭐ **판정에 기회 수를 안 보는 시험** (185·190차에서 들통난 그것)
```

쓰는 법:
    python scripts\audit_all.py
"""
import ast
import datetime as dt
import glob
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_D = os.path.join(_BASE, "data")
_S = os.path.join(_BASE, "scripts")

# (폴더, 이름, 며칠 밀리면 문제인가)
_폴더 = (("krx-daily", "주가", 2), ("index-daily", "지수", 2),
         ("dart-daily", "공시", 1), ("flow-daily", "수급", 2),
         ("kind-time", "공시시각", 1), ("etf-krx", "ETF", 3),
         ("krx-extra", "KRX추가", 3), ("consensus", "컨센서스", 8),
         ("news", "뉴스", 2), ("dart-exec", "임원매매", 8),
         ("dart-major", "5%보유", 8), ("dart-fin", "연간재무", 40),
         ("quarter-fin", "분기재무", 40), ("naver-quarter", "네이버분기", 40),
         ("dart-capital", "증자감자", 40), ("dart-snap", "사업보고서", 40),
         ("yahoo", "해외", 3), ("fred", "금리", 8))


def _최신(폴더):
    """(최신 날짜문자열 또는 None, 파일 수)"""
    바 = os.path.join(_D, 폴더)
    if not os.path.isdir(바):
        return None, 0
    fs = glob.glob(os.path.join(바, "*.json")) + \
        glob.glob(os.path.join(바, "*", "*.json"))
    if not fs:
        return None, 0
    # 이름이 날짜면 그걸 쓰고, 아니면 수정시각을 쓴다
    날 = []
    for f in fs:
        m = re.search(r"(20\d{6})", os.path.basename(f))
        if m:
            날.append(m.group(1))
    if 날:
        return max(날), len(fs)
    가장 = max(os.path.getmtime(f) for f in fs)
    return dt.datetime.fromtimestamp(가장).strftime("%Y%m%d"), len(fs)


def A절():
    print("\n" + "=" * 96)
    print("  A **자료가 며칠 밀렸나**")
    print("=" * 96)
    오늘 = dt.date.today()
    나쁨 = []
    print(f"  {'자료':<12}{'최신':>10}{'밀림':>7}{'파일수':>9}   판정")
    for 폴, 라, 한 in _폴더:
        최, n = _최신(폴)
        if 최 is None:
            print(f"  {라:<12}{'없음':>10}{'':>7}{n:>9}   ⚠️ 폴더가 비었다")
            나쁨.append(f"{라}: 자료 없음")
            continue
        try:
            d = dt.datetime.strptime(최, "%Y%m%d").date()
            밀 = (오늘 - d).days
        except ValueError:
            밀 = -1
        표 = "✅" if 밀 <= 한 else f"⚠️ **{밀}일 밀렸다**"
        if 밀 > 한:
            나쁨.append(f"{라}: {밀}일 밀림 (최신 {최})")
        print(f"  {라:<12}{최:>10}{밀:>6}일{n:>9,}   {표}")
    return 나쁨


def B절():
    print("\n" + "=" * 96)
    print("  B ⭐ **진짜 깨진 파일** — 조용한 실패의 흔적")
    print("     ⚠️ 크기로 재면 안 된다. {\"건수\": 0, \"이력\": []} 는 **정상**이다")
    print("        (그 종목에 그 일이 없었다는 뜻이다)")
    print("     여기서는 **0바이트이거나 JSON 이 깨진 것**만 센다")
    print("=" * 96)
    나쁨 = []
    for 폴, 라, _ in _폴더:
        바 = os.path.join(_D, 폴)
        if not os.path.isdir(바):
            continue
        fs = glob.glob(os.path.join(바, "*.json")) + \
            glob.glob(os.path.join(바, "*", "*.json"))
        깨짐, 빈모양 = [], 0
        for f in fs:
            n = os.path.getsize(f)
            if n == 0:
                깨짐.append(f)
                continue
            if n >= 400:
                continue
            # 작은 것만 열어본다 (큰 것은 정상으로 본다)
            try:
                d = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                깨짐.append(f)
                continue
            if isinstance(d, dict) and d:
                빈모양 += 1          # 모양이 갖춰진 빈 값 — 정상
            else:
                깨짐.append(f)
        if 깨짐:
            예 = ", ".join(os.path.basename(x) for x in 깨짐[:3])
            print(f"  ⚠️ {라:<12}**깨진 파일 {len(깨짐):,}개**  예) {예}")
            나쁨.append(f"{라}: 깨진 파일 {len(깨짐)}개")
        elif 빈모양:
            print(f"  {라:<12}빈 값 {빈모양:,}개 (모양은 갖춰졌다 — 정상)")
    if not 나쁨:
        print("  ✅ 깨진 파일 없음")
    return 나쁨


def C절():
    print("\n" + "=" * 96)
    print("  C (없앴다) — 「0건이어도 저장하나」는 코드 문자열로 못 가린다")
    print("     수집기 거의 전부에 거짓 경보를 냈다. **B절이 결과로 잡는다**")
    print("=" * 96)
    return []


def D절():
    print("\n" + "=" * 96)
    print("  D ⭐ **「이미 받았으면 건너뛴다」만 있고 갱신 수단이 없는 수집기**")
    print("     ⚠️ 임원매매·5%보유가 이 병으로 **9/1 이후 8일간 멈춰 있었다**")
    print("=" * 96)
    나쁨 = []
    for f in sorted(glob.glob(os.path.join(_S, "collect_*.py"))):
        나 = os.path.basename(f)
        try:
            t = io.open(f, encoding="utf-8-sig").read()
        except Exception:  # noqa: BLE001
            continue
        # ⚠️ **종목 단위로 건너뛰는 것만** 찍는다 (2026-09-09 고침).
        #    날짜·달·접수번호 단위는 「지난 것은 안 변하니 건너뛴다」가 **맞다**:
        #      collect_index·disclosure_time  날짜 단위 ✅
        #      collect_consensus(_slow)       달 단위 ✅
        #      collect_contract               접수번호 단위 ✅
        #    처음엔 이것들까지 찍어서 **진짜(dart_snap)를 묻어버렸다**
        건너 = ("c not in 받" in t or "if c in corp and c not in 받" in t
                or "종목 if c not in 받" in t)
        갱신 = ("--갱신일" in t or "_갱신일" in t or "--갱신" in t
                or "--다시" in t or "--강제" in t)
        if 건너 and not 갱신:
            print(f"  ⚠️ {나:<28} 건너뛰기만 있고 **갱신 수단이 없다**")
            나쁨.append(f"{나}: 갱신 수단 없음")
    if not 나쁨:
        print("  ✅ 다 갱신 수단이 있다")
    return 나쁨


def E절():
    print("\n" + "=" * 96)
    print("  E 스크립트 문법 검사")
    print("=" * 96)
    나쁨 = []
    fs = sorted(glob.glob(os.path.join(_S, "*.py")))
    for f in fs:
        나 = os.path.basename(f)
        try:
            ast.parse(io.open(f, encoding="utf-8-sig").read())
        except SyntaxError as e:
            print(f"  ❌ {나:<30} 줄 {e.lineno}: {e.msg}")
            나쁨.append(f"{나}: 문법 오류 줄 {e.lineno}")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {나:<30} {type(e).__name__}")
            나쁨.append(f"{나}: {type(e).__name__}")
    print(f"  스크립트 {len(fs)}개 중 문제 **{len(나쁨)}개**")
    return 나쁨


def F절():
    print("\n" + "=" * 96)
    print("  F 최근 로그의 오류·타임아웃 (마지막 200줄씩)")
    print("=" * 96)
    나쁨 = []
    for f in sorted(glob.glob(os.path.join(_D, "_*.log"))):
        나 = os.path.basename(f)
        try:
            줄들 = io.open(f, encoding="utf-8", errors="replace").read().splitlines()[-200:]
        except Exception:  # noqa: BLE001
            continue
        # ⚠️ 2026-09-16 — 「실패 0」「Error 0」까지 세어 40개 로그가 다 빨개졌다. 아무도 안 읽었다.
        #    최근 3일 줄만, 진짜 나쁜 것만 센다
        import re as _re
        _오늘 = dt.date.today()
        _날들 = {(_오늘 - dt.timedelta(days=k)).strftime(f) for k in range(3) for f in ("%Y-%m-%d", "%m-%d")}
        _최근 = [z for z in 줄들 if any(d in z for d in _날들)]
        if not _최근:
            continue          # 3일 안에 안 바뀐 로그 — 옛 일이다
        _나쁨패턴 = _re.compile(r"Traceback|MemoryError|\w+Error:|❌|Timeout|실패 [1-9]\d*|코드 [1-9]\d*|터졌다|죽었다|못 받았다")
        # ⚠️ 는 안내에도 쓴다(「09:01에 미체결 주문을 취소한다」) — 실패 낱말이 같이 있을 때만 센다
        _경고실패 = _re.compile(r"⚠️.*(실패|못 |없다|밀림|끊|죽|오류|Error|코드 [1-9])")
        _가짜 = _re.compile(r"실패 0\b|Error 0\b|오류 0\b|경고 0\b|예상대로|이어받는다")
        나쁜줄 = [z for z in _최근
                  if (_나쁨패턴.search(z) or _경고실패.search(z)) and not _가짜.search(z)]
        if 나쁜줄:
            print(f"\n  [{나}]  나쁜 줄 {len(나쁜줄)}개 · 마지막 둘:")
            for z in 나쁜줄[-2:]:
                print(f"    {z.strip()[:110]}")
            나쁨.append(f"{나}: 오류 {len(나쁜줄)}줄")
    if not 나쁨:
        print("  ✅ 최근 로그에 오류 없음")
    return 나쁨


def H절():
    """예약 작업 — 결과 코드 ≠ 0 · 매일 도는 것이 오래 안 돎"""
    import subprocess
    print("\n" + "=" * 96)
    print("  H 예약 작업 — LastTaskResult ≠ 0 · 3일 넘게 안 돈 매일 작업")
    print("=" * 96)
    나쁨 = []
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\\' -and $_.State -ne 'Disabled' } | Get-ScheduledTaskInfo | "
                              "Select-Object TaskName, LastTaskResult, "
                              "@{n='Last';e={$_.LastRunTime.ToString('yyyy-MM-dd HH:mm')}} | ConvertTo-Json"],
                             capture_output=True, timeout=60)
        rows = json.loads(out.stdout.decode("utf-8", errors="replace") or "[]")
        if isinstance(rows, dict):
            rows = [rows]
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ 예약 작업을 못 읽었다: {type(e).__name__}")
        return ["H: 예약 작업 못 읽음"]
    _우리 = ("Collect", "Briefing", "Antc", "Entry", "Krx", "Dart", "Forward", "Consensus", "Gap", "Capital", "Industry", "Dividend")
    _주간 = ("AutoSearch", "Weekly", "Verify", "Backfill", "Resume", "1220", "DividendCollect", "IndustryCollect", "CapitalCollect")
    _오늘 = dt.date.today()
    for r in rows:
        n, rc, last = str(r.get("TaskName")), r.get("LastTaskResult"), str(r.get("Last") or "")
        if not any(k in n for k in _우리):
            continue
        if rc not in (0, 267009, 267011, None):          # 267009=지금 도는 중 · 267011=아직 안 돎
            뜻 = {267014: "사용자/재부팅이 끊음", 1: "스크립트 실패(1)", 2: "스크립트 실패(2)"}.get(rc, f"코드 {rc}")
            print(f"  ❌ {n:<26} {last}  결과 {rc} — {뜻}")
            나쁨.append(f"H 예약 {n}: 결과 {rc}")
        try:
            며칠 = (_오늘 - dt.datetime.strptime(last[:10], "%Y-%m-%d").date()).days
        except ValueError:
            며칠 = None
        if 며칠 is not None and 며칠 > 3 and not any(k in n for k in _주간):
            print(f"  ❌ {n:<26} 마지막 {last} — {며칠}일 전")
            나쁨.append(f"H 예약 {n}: {며칠}일 안 돎")
    if not 나쁨:
        print("  ✅ 예약 작업 이상 없음")
    return 나쁨


def I절():
    """밤 판(run-logs/queue_*.log) — 「끝」 없이 끝났거나 Traceback/MemoryError"""
    print("\n" + "=" * 96)
    print("  I 밤 판 — 끝 표시 없이 끝났거나 Traceback (최근 2일)")
    print("=" * 96)
    나쁨 = []
    _컷 = (dt.datetime.now() - dt.timedelta(days=2)).timestamp()
    _파일들 = sorted(glob.glob(os.path.join(_BASE, "run-logs", "queue_*.log")), key=os.path.getmtime)
    _끝난판 = {}       # 판 이름 → 「끝」으로 끝난 가장 새 로그의 mtime
    def _판이름(f):      # queue_news_2026… · nightly_news_2026… → "news"
        _t = os.path.basename(f).split("_")
        return _t[1] if len(_t) > 2 else _t[0]
    for f in _파일들:
        _판 = _판이름(f)
        if "끝 =====" in io.open(f, encoding="utf-8", errors="replace").read():
            _끝난판[_판] = max(_끝난판.get(_판, 0), os.path.getmtime(f))
    for f in _파일들:
        if os.path.getmtime(f) < _컷:
            continue
        t = io.open(f, encoding="utf-8", errors="replace").read()
        나 = os.path.basename(f)
        _판 = _판이름(f)
        if "Traceback" in t or "MemoryError" in t or "Error:" in t:
            마지막 = [z for z in t.splitlines() if "Error" in z][-1:]
            if _끝난판.get(_판, 0) > os.path.getmtime(f):
                print(f"  ✅ {나}: 죽었지만 **다시 돌려 끝났다** ({마지막[0].strip()[-50:] if 마지막 else ''})")
                continue
            print(f"  ❌ {나}: {마지막[0].strip()[:100] if 마지막 else '오류'}")
            나쁨.append(f"I 밤 판 {나}: 죽음")
        elif "끝 =====" not in t and (dt.datetime.now().timestamp() - os.path.getmtime(f)) > 3 * 3600:
            print(f"  ❌ {나}: 3시간 넘게 「끝」 표시가 없다 (죽었거나 멈춤)")
            나쁨.append(f"I 밤 판 {나}: 끝 없음")
        else:
            # ⚠️ 2026-09-16 pairs4: 복사한 줄 스크립트가 옛 「앞줄 끝」 문구를 들고 있어 70분을 헛기다렸다
            import re as _reI
            _마지막 = (t.strip().splitlines() or [""])[-1]
            _m = _reI.search(r"앞줄\((queue_\w+?)\)이 끝나길 기다린다", _마지막)
            _기다림분 = (dt.datetime.now().timestamp() - os.path.getmtime(f)) / 60
            if _m and _기다림분 > 15:
                _앞 = _m.group(1)
                _앞로그 = sorted(glob.glob(os.path.join(_BASE, "run-logs", f"{_앞}_*.log")), key=os.path.getmtime)
                if _앞로그 and f"{_앞} 끝" in io.open(_앞로그[-1], encoding="utf-8", errors="replace").read():
                    print(f"  ❌ {나}: 앞줄 {_앞} 은 이미 끝났는데 {_기다림분:.0f}분째 기다린다 — 「앞줄 끝」 문구가 틀렸을 것")
                    나쁨.append(f"I 줄 {나}: 앞줄 끝났는데 기다림")
    if not 나쁨:
        print("  ✅ 밤 판 이상 없음")
    return 나쁨


def J절():
    """판정→게시 — _antc.log 재게시 실패 · 사이트 파일이 오늘 안 만들어짐"""
    print("\n" + "=" * 96)
    print("  J 판정 → 웹 게시 (오늘)")
    print("=" * 96)
    나쁨 = []
    오늘 = dt.date.today().strftime("%Y-%m-%d")
    try:
        줄 = [z for z in io.open(os.path.join(_D, "_antc.log"), encoding="utf-8", errors="replace") if z.startswith(오늘)]
    except OSError:
        줄 = []
    p = os.path.join(_D, "briefing-site.html")
    _실패 = [z for z in 줄 if "재게시 실패" in z]
    if _실패:
        _실패시각 = _실패[-1][:19]
        _사이트시각 = dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S") if os.path.exists(p) else ""
        if _사이트시각 > _실패시각:
            print(f"  ✅ {_실패시각[11:16]} 재게시 실패 → {_사이트시각[11:16]} 다시 올라갔다 (복구됨)")
        else:
            print(f"  ❌ {_실패시각[11:16]} 판정 재게시 실패 — 판정은 됐는데 화면엔 **아직** 안 올라갔다")
            나쁨.append("J 재게시 실패")
    if os.path.exists(p) and dt.date.fromtimestamp(os.path.getmtime(p)) != dt.date.today() and dt.datetime.now().hour >= 9:
        print("  ❌ briefing-site.html 이 오늘 안 만들어졌다 (게시가 막혔거나 안 돎)")
        나쁨.append("J 사이트 오늘 안 만듦")
    if not 나쁨:
        print("  ✅ 판정·게시 이상 없음")
    return 나쁨


def K절():
    """퀀트 판정 N개인데 09:05 진입확인 결과가 비었다"""
    print("\n" + "=" * 96)
    print("  K 퀀트 판정 vs 09:05 진입확인")
    print("=" * 96)
    나쁨 = []
    오늘 = dt.date.today().strftime("%Y-%m-%d")
    try:
        줄 = [z for z in io.open(os.path.join(_D, "_antc.log"), encoding="utf-8", errors="replace") if z.startswith(오늘)]
    except OSError:
        줄 = []
    import re as _re
    n = 0
    for z in 줄:
        m = _re.search(r"오늘 살 것: (\d+)개", z)
        if m:
            n = int(m.group(1))
    # 「살 것」은 forward-log 오늘 줄의 후보 중 규칙매수=True 로 남는다 (quant_cards 가 그걸 그린다)
    기록 = None
    try:
        for ln in io.open(os.path.join(_D, "forward-log.jsonl"), encoding="utf-8"):
            try:
                o = json.loads(ln)
            except ValueError:
                continue
            if str(o.get("기록시각", ""))[:10] == 오늘:
                기록 = o
    except OSError:
        pass
    if 기록 is None:
        if dt.datetime.now().hour >= 9:
            print("  ❌ forward-log 에 오늘 줄이 없다 — 08:00 기록(ForwardRecord)이 안 돌았다")
            나쁨.append("K forward-log 오늘 줄 없음")
        return 나쁨
    _잰 = str((기록.get("동시호가") or {}).get("잰시각") or "")
    m = sum(1 for x in (기록.get("후보") or []) if x.get("규칙매수"))
    if dt.datetime.now().hour >= 9 and not _잰:
        print("  ❌ 08:55 동시호가 판정이 forward-log 에 안 붙었다 (FetchAntc0850 이 record_pick 을 못 불렀다)")
        나쁨.append("K 동시호가 판정 없음")
    elif n != m:
        print(f"  ❌ 로그는 「살 것 {n}개」인데 forward-log 규칙매수는 {m}개 — 기록과 화면이 다르다")
        나쁨.append(f"K 살 것 {n}≠{m}")
    else:
        print(f"  ✅ 살 것 {n}개 = forward-log 규칙매수 {m}개 (잰 시각 {_잰[11:16]})")
    print("     ※ 09:05 진입확인(check_entry)은 섹터 브리핑 픽만 본다 — 퀀트는 08:55 판정이 곧 진입 판정 (참고)")
    return 나쁨


def L절():
    """수집기 열 밀림 — 값이 뜻과 안 맞는 필드"""
    print("\n" + "=" * 96)
    print("  L 수집기 열 밀림 (표본 200종목)")
    print("=" * 96)
    나쁨 = []
    import re as _re
    # 2026-09-16 12:00 수집기 둘을 고쳤다 (보유목적 ← report_resn · 사유 → 지분율/증감비율).
    # 옛 파일은 매일 밤 --갱신일 6 으로 일주일 안에 다 바뀐다 → 고친 뒤 받은 파일만 검사한다
    _고친때 = dt.datetime(2026, 9, 16, 12, 0).timestamp()
    def _표본(폴더, 키, 새것만=True):
        벌, 옛 = [], 0
        for f in sorted(glob.glob(os.path.join(_D, 폴더, "*.json")), key=os.path.getmtime, reverse=True):
            if os.path.getmtime(f) < _고친때:
                옛 += 1
                continue
            if len(벌) >= 3000:
                continue
            try:
                j = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                continue
            for x in (j.get("이력") or []):
                벌.append(x.get(키))
        return 벌, 옛
    v, 옛 = _표본("dart-major", "보유목적")
    if not v:
        print(f"  ⏳ dart-major — 고친 뒤 받은 파일이 아직 없다 (옛 파일 {옛:,} · 밤 수집이 바꾼다)")
    else:
        숫 = sum(1 for z in v if _re.fullmatch(r"[\d,]+", str(z or "")))
        if 숫 / len(v) > 0.3:
            print(f"  ❌ dart-major 「보유목적」 {숫}/{len(v)} 가 숫자 — 고친 뒤에도 열이 밀렸다")
            나쁨.append("L dart-major 보유목적 열 밀림")
        else:
            print(f"  ✅ dart-major 보유목적 글자 ({len(v):,}건) · 옛 파일 {옛:,} 남음")
    v, 옛 = _표본("dart-exec", "지분율")
    if not v:
        print(f"  ⏳ dart-exec — 고친 뒤 받은 파일이 아직 없다 (옛 파일 {옛:,} · 밤 수집이 바꾼다)")
    elif sum(1 for z in v if z in (None, "", "None")) / len(v) > 0.9:
        print(f"  ❌ dart-exec 「지분율」 {len(v)}건 중 90% 넘게 비어 있다 — 수집기가 안 받는다")
        나쁨.append("L dart-exec 지분율 비어 있음")
    else:
        print(f"  ✅ dart-exec 지분율 참 ({len(v):,}건) · 옛 파일 {옛:,} 남음")
    return 나쁨


def M절():
    """rule_align ❌"""
    import subprocess
    print("\n" + "=" * 96)
    print("  M 규칙 정합 (rule_align)")
    print("=" * 96)
    try:
        out = subprocess.run([sys.executable, "-X", "utf8", os.path.join(_BASE, "scripts", "rule_align.py")],
                             capture_output=True, timeout=120, cwd=_BASE)
        t = out.stdout.decode("utf-8", errors="replace")
        나쁜 = [z.strip() for z in t.splitlines() if "❌" in z]
        for z in 나쁜[:6]:
            print(f"  {z[:110]}")
        if 나쁜:
            return [f"M rule_align 어긋남 {len(나쁜)}"]
        print("  ✅ 규칙이 한 곳에서만 나온다")
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ rule_align 못 돌림: {type(e).__name__}")
        return ["M rule_align 못 돌림"]
    return []


def N절():
    """금지 호스트(data.krx.co.kr · short.krx.co.kr)를 **주석이 아닌 코드**에서 부르는 곳"""
    print("\n" + "=" * 96)
    print("  N 금지 호스트 — KRX 웹 포털을 부르는 살아 있는 코드 (규칙 2026-08-28)")
    print("=" * 96)
    나쁨 = []
    import re as _re
    _금지 = _re.compile(r"https?://(data|short)\.krx\.co\.kr")
    for f in sorted(glob.glob(os.path.join(_S, "*.py"))):
        if os.path.basename(f) in ("audit_all.py", "api_probe.py"):
            continue
        try:
            src = io.open(f, encoding="utf-8-sig").read()
            tree = ast.parse(src)
        except Exception:  # noqa: BLE001
            continue
        # 문자열 상수 안에 든 금지 URL 중, 독스트링이 아닌 것
        독스트링 = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                    독스트링.add(id(node.body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and _금지.search(node.value) and id(node) not in 독스트링:
                print(f"  ❌ {os.path.basename(f)}:{node.lineno}  {node.value[:70]}")
                나쁨.append(f"N 금지 호스트 {os.path.basename(f)}:{node.lineno}")
    if not 나쁨:
        print("  ✅ 코드에 KRX 웹 포털 URL 없음")
    else:
        print("     ※ 문자열이 남아 있어도 안 부르면 되지만, 부르는지 아닌지는 사람이 봐야 한다")
    return 나쁨


def G절():
    print("\n" + "=" * 96)
    print("  G ⭐⭐ **판정에 「기회 수」를 안 보는 시험**")
    print("     사용자: 「매도 타이밍과 자산 보유 현황도 중요하지만")
    print("             **그것도 때문에 상승 기회를 놓쳐서는 안돼**」")
    print("     ⚠️ 185차는 기회가 **1/50**, 190차는 **6~37%** 로 줄었는데 「통과」로 찍혔다")
    print("=" * 96)
    나쁨 = []
    for f in sorted(glob.glob(os.path.join(_S, "*_lab.py")) +
                    glob.glob(os.path.join(_S, "gate*.py"))):
        나 = os.path.basename(f)
        try:
            t = io.open(f, encoding="utf-8-sig").read()
        except Exception:  # noqa: BLE001
            continue
        # 「낫다/통과」 판정이 있는데 기회 비율을 안 쓰는 것
        판정 = ("낫다" in t or "전부 낫다" in t or "⇒ **통과**" in t
                or "통과표" in t)
        기회 = ("기회비" in t or "기회 " in t and "%" in t)
        if 판정 and not 기회:
            print(f"  ⚠️ {나:<28} 판정은 하는데 **기회 수를 안 본다**")
            나쁨.append(f"{나}: 기회 수 미반영")
    if not 나쁨:
        print("  ✅ 다 기회 수를 본다")
    return 나쁨


def main():
    print("=" * 96)
    print("  audit_all — **전수 점검** (2026-09-09 밤)")
    print(f"  {dt.datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 96)
    모 = []
    for 절 in (A절, B절, C절, D절, E절, F절, G절, H절, I절, J절, K절, L절, M절, N절):
        try:
            모 += 절() or []
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {절.__name__} 자체가 터졌다: {type(e).__name__} {e}")
            모.append(f"{절.__name__}: 점검 실패")
    print("\n" + "=" * 96)
    print(f"  ⇒ 찾은 문제 **{len(모)}개**")
    print("=" * 96)
    for z in 모:
        print(f"    · {z}")
    return 0


if __name__ == "__main__":
    _p = os.path.join(_D, "_labs",
                      os.environ.get("LAB_OUT")
                      or f"{dt.date.today():%Y-%m-%d}_전수점검.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
