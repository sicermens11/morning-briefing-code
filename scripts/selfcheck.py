#!/usr/bin/env python3
r"""
selfcheck.py — **반복되는 실수를 기계가 잡는다** (2026-09-04 신설)

⚠️⚠️ **사용자 지시.**
   *"버그는 계속 잡고 반복적으로 일어나는 건 프로그램을 따로 만들어서
     감시하든 점검하든 체크를 해야할 것 같은데!"*

## 2026-09-04 하루에 난 것들 — 같은 게 계속 났다
```
① 자료 필드명을 **짐작**       dart-daily · dart-capital · krx-daily · index-daily
② 갈래 하나를 **빠뜨림**       자사주처분 3,682건 (결론이 뒤집혔다)
③ 파싱 **0건인데 그냥 진행**   4,104일 읽고 0개 -> 틀린 결론 낼 뻔
④ heredoc **백슬래시**        네 번
⑤ **낙폭은 음수**인데 부등호를 그대로  (⭐가 나쁜 것에 붙었다)
⑥ 예약에 **전체 경로** 안 씀   새벽 테스트가 통째로 안 돌았다
⑦ 실전에서만 드러나는 것       Yahoo 마지막 일봉이 비어 있음
⑧ 앞 절 결과를 **뒷 절에 반영 안 함**  100차 보유일 10일/20일
```

## 무엇을 점검하나
```
A 자료 신선도     폴더별 최신 날짜가 며칠 밀렸나
B ⭐ 자료 구조    필드명을 스냅샷과 비교 (바뀌면 알린다)  -> data/_shape.json
C 예약 작업      마지막 실행 결과 코드 (0이 아니면 알린다)
D 스크립트 문법   전체 .py를 **SyntaxWarning 포함**해 검사
E ⭐ 알려진 함정  코드에서 위험한 꼴을 찾는다
F 시험 결과      _labs 최근 파일에 Traceback·「0개」·「표본 부족」이 있나
```

쓰는 법:
    python scripts\selfcheck.py           전부 점검
    python scripts\selfcheck.py --기준잡기 지금 구조를 정답으로 저장 (처음 한 번)
    python scripts\selfcheck.py --조용     문제가 있을 때만 찍는다 (예약용)
"""
import ast
import datetime as dt
import glob
import io
import json
import os
import re
import subprocess
import sys
import warnings

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_SHAPE = os.path.join(_DATA, "_shape.json")

# (폴더, 며칠까지 밀려도 되나) — 거래일 기준이 아니라 달력일
신선 = (("krx-daily", 4), ("dart-daily", 4), ("index-daily", 4),
        ("flow-daily", 4), ("etf-krx", 4), ("kind-time", 5),
        ("yahoo", 3), ("naver-quarter", 120), ("dart-capital", 400),
        ("dart-major", 400), ("dart-exec", 400))

# ⚠️⚠️ **미국 휴일을 안 봐서 거짓 경보가 났다** (2026-09-08).
#    「yahoo 4일 밀림」 — 실은 09-07(월)이 노동절이라 09-04가 마지막 거래일이었다
#    날짜를 박아두는 대신 **규칙으로** 낸다 (해마다 안 고쳐도 되게)
_미국고정 = ((1, 1), (6, 19), (7, 4), (12, 25))   # 신정·준틴스·독립기념일·성탄


def _n번째요일(해, 달, 요일, n):
    d = dt.date(해, 달, 1)
    d += dt.timedelta(days=(요일 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _마지막요일(해, 달, 요일):
    d = (dt.date(해, 달 + 1, 1) if 달 < 12 else dt.date(해 + 1, 1, 1)) \
        - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - 요일) % 7)


def _미국휴일(해):
    """뉴욕증권거래소가 쉬는 날 (토·일 옮김 포함)"""
    h = set()
    for m, dd in _미국고정:
        d = dt.date(해, m, dd)
        if d.weekday() == 5:
            d -= dt.timedelta(days=1)      # 토 -> 금
        elif d.weekday() == 6:
            d += dt.timedelta(days=1)      # 일 -> 월
        h.add(d)
    h.add(_n번째요일(해, 1, 0, 3))          # 마틴 루서 킹 데이 (1월 셋째 월)
    h.add(_n번째요일(해, 2, 0, 3))          # 대통령의 날 (2월 셋째 월)
    h.add(_마지막요일(해, 5, 0))            # 메모리얼 데이 (5월 마지막 월)
    h.add(_n번째요일(해, 9, 0, 1))          # 노동절 (9월 첫 월)
    h.add(_n번째요일(해, 11, 3, 4))         # 추수감사절 (11월 넷째 목)
    # 성금요일 (부활절 앞 금요일) — 계산이 길어 뺀다. 3~4월에 하루 오차 가능
    return h


def _미국마지막장(오늘):
    """오늘 기준 **미국 장이 마지막으로 섰던 날**"""
    d = 오늘
    휴 = _미국휴일(d.year) | _미국휴일(d.year - 1)
    for _ in range(12):
        d -= dt.timedelta(days=1)
        if d.weekday() < 5 and d not in 휴:
            return d
    return 오늘


문제 = []
경고 = []


def 알림(심각, s):
    (문제 if 심각 else 경고).append(s)
    print(f"    {'❌' if 심각 else '⚠️'} {s}")


def 구조뽑기(폴더):
    """폴더 최신 파일에서 (최상위 키, 목록 안쪽 키)를 뽑는다"""
    g = sorted(glob.glob(os.path.join(_DATA, 폴더, "*.json")))
    if not g:
        return None
    out = {"파일수": len(g), "최신": os.path.basename(g[-1])}
    # ⚠️ 갈래마다 구조가 다를 수 있다 -> 여러 파일을 훑는다
    최상위, 안쪽 = set(), {}
    for p in g[::max(1, len(g) // 25)][:25] + [g[-1]]:
        try:
            d = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        최상위 |= set(d)
        for k, v in d.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                안쪽.setdefault(k, set()).update(v[0].keys())
            elif isinstance(v, dict) and v:
                k2 = list(v)[0]
                if isinstance(v[k2], dict):
                    안쪽.setdefault(k, set()).update(v[k2].keys())
    out["최상위"] = sorted(최상위)
    out["안쪽"] = {k: sorted(v) for k, v in 안쪽.items()}
    return out


def main():
    조용 = "--조용" in sys.argv
    기준잡기 = "--기준잡기" in sys.argv
    오늘 = dt.date.today()
    if not 조용:
        print("=" * 78)
        print(f"  자체 점검  {dt.datetime.now():%Y-%m-%d %H:%M}")
        print("=" * 78)

    # ══ A 자료 신선도 ══
    if not 조용:
        print("\n  ══ A 자료 신선도 ══")
    for 폴더, 허용 in 신선:
        g = sorted(glob.glob(os.path.join(_DATA, 폴더, "*.json")))
        if not g:
            알림(False, f"{폴더}: 비어 있다")
            continue
        이름 = os.path.basename(g[-1])[:8]
        if 이름.isdigit() and len(이름) == 8:
            try:
                d = dt.date(int(이름[:4]), int(이름[4:6]), int(이름[6:]))
            except ValueError:
                continue
            밀림 = (오늘 - d).days
            if 밀림 > 허용:
                알림(밀림 > 허용 * 2,
                     f"{폴더}: 최신 {이름} — **{밀림}일 밀림** (허용 {허용}일)")
            elif not 조용:
                print(f"    ✅ {폴더:<16}{이름}  {밀림}일 전  "
                      f"({len(g):,}개)")
        else:
            # yahoo처럼 파일명이 심볼인 곳은 안쪽 날짜를 본다
            try:
                dd = json.load(io.open(g[-1], encoding="utf-8-sig"))
                k = sorted(dd.get("종가") or {})
                if k:
                    d = dt.date(int(k[-1][:4]), int(k[-1][4:6]),
                                int(k[-1][6:]))
                    # ⭐ **미국 자료는 미국 장 기준으로 센다** (2026-09-08)
                    #    주말·미국 공휴일을 빼야 거짓 경보가 안 난다
                    기준 = (_미국마지막장(오늘)
                            if 폴더 in ("yahoo", "us-daily", "us-symbols")
                            else 오늘)
                    밀림 = (기준 - d).days
                    if 밀림 > 허용:
                        알림(밀림 > 허용 * 2,
                             f"{폴더}: 최신 {k[-1]} — **{밀림}일 밀림** "
                             f"(미국 마지막 장 {기준:%Y-%m-%d} 기준)")
                    elif not 조용:
                        print(f"    ✅ {폴더:<16}{k[-1]}  {밀림}일 전  "
                              f"({len(g):,}개)")
            except Exception:
                pass

    # ══ A-2 **안이 빈 파일이 있나** ══ (2026-09-09 신설)
    #  ⚠️⚠️ 사용자: 「버그 정기적으로 보는데 **하나도 못 잡은 거네?**」
    #     맞다. 여기는 「파일이 **있나**」만 봤고 「**안이 비었나**」는 안 봤다.
    #     컨센서스 38개 파일이 **건수 0** 인 채로 몇 주를 지나갔다 —
    #     수집기가 오류 나도 0건으로 저장했고, 다음엔 「이미 받음」으로 건너뛰었다
    if not 조용:
        print("\n  ══ A-2 안이 빈 자료 파일 ══")
    # ⚠️⚠️ **「건수: 0」은 고장이 아니다** (2026-09-11 고침).
    #    `dart-exec`(임원 매매)·`dart-major`(5% 대량보유)는 **그 종목에 공시가
    #    없으면 정상적으로 0** 이다. 수집기가 돌아서 「없음」을 적어 둔 것이다.
    #    그런데 이걸 실패로 올려 **676건**이 경보에 섞였고, 그 바람에
    #    진짜 문제(저녁 수집 실패·시험 결과 이상)가 목록 아래로 밀렸다.
    #    ⇒ **`건수` 칸이 있으면 0이어도 정상**으로 본다. 칸 자체가 없으면 고장이다
    _센것있으면정상 = {"dart-exec", "dart-major"}
    빈볼곳 = (("consensus", "리포트"), ("contract", None),
              ("dart-exec", "이력"), ("dart-major", "이력"),
              ("news", "뉴스"), ("krx-daily", "종목"),
              ("index-daily", "지수"), ("flow-daily", "종목"),
              ("dart-daily", None))
    for 폴더, 키 in 빈볼곳:
        d = os.path.join(_DATA, 폴더)
        if not os.path.isdir(d):
            continue
        파일 = sorted(glob.glob(os.path.join(d, "*.json")))
        if not 파일:
            continue
        빈파일 = []
        for f in 파일:
            try:
                # ⚠️ 「건수 0」 파일은 **45바이트쯤**이라 이 지름길에 먼저 걸렸다.
                #    그래서 위의 `_센것있으면정상` 이 무용지물이었다 (2026-09-11)
                if 폴더 not in _센것있으면정상 and os.path.getsize(f) < 60:
                    빈파일.append(os.path.basename(f))
                    continue
                j = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                빈파일.append(os.path.basename(f))
                continue
            if 폴더 in _센것있으면정상:
                # 수집기가 돌았으면 `건수` 를 적는다. 0 이어도 정상이다
                if "건수" not in j:
                    빈파일.append(os.path.basename(f))
            elif 키:
                v = j.get(키)
                if not v:
                    빈파일.append(os.path.basename(f))
            elif isinstance(j, dict) and len(j) <= 2:
                빈파일.append(os.path.basename(f))
        몫 = len(빈파일) / len(파일) * 100
        if 빈파일:
            알림(몫 >= 5,
                 f"{폴더}: **{len(빈파일):,}개 파일이 비었다** "
                 f"({몫:.0f}%) — 예: {', '.join(x[:8] for x in 빈파일[:5])}")
        elif not 조용:
            print(f"    ✅ {폴더:<16}{len(파일):,}개 · 빈 것 없음")

    # ══ B 자료 구조 ══
    if not 조용:
        print("\n  ══ B 자료 구조 (필드명이 바뀌었나) ══")
    옛구조 = {}
    if os.path.exists(_SHAPE):
        try:
            옛구조 = json.load(io.open(_SHAPE, encoding="utf-8-sig"))
        except Exception:
            옛구조 = {}
    새구조 = {}
    볼폴더 = [f for f, _ in 신선] + ["dart-fin", "consensus", "etf-daily"]
    for 폴더 in 볼폴더:
        s = 구조뽑기(폴더)
        if s:
            새구조[폴더] = s
    if 기준잡기 or not 옛구조:
        io.open(_SHAPE, "w", encoding="utf-8").write(
            json.dumps(새구조, ensure_ascii=False, indent=1))
        if not 조용:
            print(f"    ⭐ 지금 구조를 정답으로 저장했다 → {_SHAPE}")
            print(f"       ({len(새구조)}개 폴더)")
    else:
        같음 = 0
        for 폴더, s in 새구조.items():
            옛 = 옛구조.get(폴더)
            if not 옛:
                알림(False, f"{폴더}: 기준에 없는 새 폴더다")
                continue
            빠짐 = set(옛.get("최상위") or []) - set(s.get("최상위") or [])
            더함 = set(s.get("최상위") or []) - set(옛.get("최상위") or [])
            if 빠짐:
                알림(True, f"{폴더}: 최상위 키가 **사라졌다** {sorted(빠짐)}")
            if 더함:
                알림(False, f"{폴더}: 최상위 키가 늘었다 {sorted(더함)}")
            for k, v in (옛.get("안쪽") or {}).items():
                새v = set((s.get("안쪽") or {}).get(k) or [])
                빠짐2 = set(v) - 새v
                if 빠짐2:
                    알림(True, f"{폴더}[{k}]: 필드가 **사라졌다** "
                               f"{sorted(빠짐2)[:6]}")
            if not 빠짐 and not 더함:
                같음 += 1
        if not 조용:
            print(f"    ✅ {같음}/{len(새구조)}개 폴더가 기준과 같다")

    # ══ C 예약 작업 ══
    if not 조용:
        print("\n  ══ C 예약 작업 ══")
    이름들 = ("MorningSectorBriefing", "EveningDataCollect", "ForwardRecord",
              "NightLabs0904", "DartOldBackfill", "IndustryCollect",
              "CapitalCollect")
    ps = ("$n=@(" + ",".join(f"'{x}'" for x in 이름들) + "); "
          "foreach($x in $n){ $t=Get-ScheduledTask -TaskName $x "
          "-EA SilentlyContinue; if($t){ $i=$t|Get-ScheduledTaskInfo; "
          "'{0}|{1}|{2}|{3}' -f $x,$t.State,$i.LastTaskResult,"
          "$i.NextRunTime } else { '{0}|없음||' -f $x } }")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, timeout=60)
        엮 = r.stdout.decode("utf-8", errors="replace")
        for line in 엮.splitlines():
            부 = line.strip().split("|")
            if len(부) < 3 or not 부[0]:
                continue
            이, 상, 결 = 부[0], 부[1], 부[2]
            if 상 == "없음":
                알림(False, f"예약 {이}: 등록 안 됨")
                continue
            try:
                코 = int(결)
            except ValueError:
                코 = 0
            # ⚠️ **SelfCheck 자신은 뺀다** (2026-09-07). 이 점검기는 문제를 찾으면
            #    일부러 코드 1로 끝난다. 그걸 다음 점검이 「예약 실패」로 다시 잡아
            #    **자기가 낸 경보를 자기가 또 잡는 고리**가 됐다 (오늘 3건이 그거였다)
            if 이.startswith("SelfCheck"):
                if not 조용:
                    print(f"    ✅ {이:<24}{상:<9}(코드 {결} — 이 점검기는 "
                          f"문제를 찾으면 1로 끝난다)")
                continue
            if 코 not in (0, 267011):        # 267011 = 아직 안 돌았음
                뜻 = ("**파일을 못 찾음 — 전체 경로를 썼나**"
                      if 코 == 2147942402 else f"코드 {코}")
                알림(True, f"예약 {이}: 마지막 실행 실패 — {뜻}")
            elif not 조용:
                print(f"    ✅ {이:<24}{상:<9}{부[3][:16] if len(부)>3 else ''}")
    except Exception as e:
        알림(False, f"예약 작업을 못 읽었다: {type(e).__name__}")

    # ══ D 스크립트 문법 ══
    if not 조용:
        print("\n  ══ D 스크립트 문법 (SyntaxWarning 포함) ══")
    나쁨 = 0
    for p in sorted(glob.glob(os.path.join(_BASE, "scripts", "*.py"))):
        try:
            # ⚠️ **utf-8-sig**로 읽는다. BOM이 붙은 파일이 5개 있는데
            #    utf-8로 읽으면 ast.parse가 「SyntaxError 줄 1」을 낸다.
            #    파이썬 실행은 BOM을 알아서 처리하므로 **진짜 오류가 아니다**
            src = io.open(p, encoding="utf-8-sig").read()
        except Exception:
            continue
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                ast.parse(src)
            except SyntaxError as e:
                알림(True, f"{os.path.basename(p)}: SyntaxError 줄 {e.lineno}")
                나쁨 += 1
                continue
            for x in w:
                if issubclass(x.category, SyntaxWarning):
                    알림(False, f"{os.path.basename(p)}: {x.message}")
                    나쁨 += 1
    if not 조용 and 나쁨 == 0:
        n = len(glob.glob(os.path.join(_BASE, "scripts", "*.py")))
        print(f"    ✅ {n}개 파일 모두 깨끗하다")

    # ══ D-2 규칙이 여기저기 어긋났나 ══ (2026-09-08 신설)
    # ⚠️⚠️ **왜 만들었나**: 124차(나눠팔기)를 09-07에 채택했는데
    #    rule-capital.json 은 채택 **전** 값으로, build_rule_cases 는
    #    **앞 몫만** 계산한 채로 남아 있었다. 하나만 고치고 나머지를 잊었다.
    #    사용자가 「테스트 결과 반영됐냐」고 물어서야 찾았다
    #    ⇒ 규칙을 적어놓은 자리들이 **서로 맞는지** 기계가 본다
    if not 조용:
        print("\n  ══ D-2 규칙이 여기저기 어긋났나 ══")
    try:
        import re as _re2

        def _몫읽기(파일):
            """_몫들 = ((0.5, 15.0, 40), (0.5, 40.0, 90)) 에서 목표들을 뽑는다"""
            p = os.path.join(_BASE, "scripts", 파일)
            if not os.path.exists(p):
                return None
            s = io.open(p, encoding="utf-8").read()
            m = _re2.search(r"_몫들\s*=\s*\(\((.+?)\)\)", s, _re2.S)
            if not m:
                return None
            return tuple(float(x) for x in
                         _re2.findall(r"[\d.]+", m.group(1)))

        몫들 = {f: _몫읽기(f) for f in ("record_pick.py", "bought.py")}
        본것 = [v for v in 몫들.values() if v]
        if len(본것) >= 2 and len(set(본것)) > 1:
            알림(True, f"**규칙이 파일마다 다르다** — {몫들}")
        elif 본것:
            if not 조용:
                print(f"    ✅ record_pick 과 bought 의 매도 규칙이 같다 {본것[0]}")

        # rule-cases.json 이 코드보다 오래됐나
        _rc = os.path.join(_DATA, "rule-cases.json")
        _rp = os.path.join(_BASE, "scripts", "record_pick.py")
        if os.path.exists(_rc) and os.path.exists(_rp):
            if os.path.getmtime(_rc) < os.path.getmtime(_rp) - 3600:
                알림(True, "rule-cases.json 이 record_pick.py 보다 **오래됐다** "
                          "— 규칙을 고치고 사례를 안 다시 만들었다 "
                          "(docs/규칙바뀌면.md 참고)")
            elif not 조용:
                print("    ✅ rule-cases.json 이 규칙 코드보다 최신이다")

        # ⭐⭐⭐ **값 대조** (2026-09-11 신설 · 전수조사 ⑤).
        #    위는 **파일 시각**만 본다. 그래서 2026-09-11 에 어긋남을 **9개**
        #    찾을 때까지 아무도 못 잡았다 — 그중 둘은 돈이 걸린 것이었다
        #      · 시험 시총 하한이 500억 (실전 300억) — 158차에 바꿨는데 그대로
        #      · 화면이 「D+40 에 **전량** 정리」 (실제는 반만 · D+90 은 안 알림)
        try:
            import rule_align as _RA
            _곳, _줄, _어 = _RA.보기()
            if _어:
                for _z in _어:
                    알림(True, f"규칙이 곳마다 다르다 — {_z}")
            elif not 조용:
                print("    ✅ 규칙 값이 다섯 곳에서 모두 같다 (rule_align)")
        except Exception as _e:  # noqa: BLE001
            알림(False, f"rule_align 을 못 돌렸다: {_e}")

        # rule-capital.json 이 나눠팔기를 반영했나
        _cap = os.path.join(_DATA, "rule-capital.json")
        if os.path.exists(_cap):
            _cj = json.load(io.open(_cap, encoding="utf-8-sig"))
            if "나눔" not in str(_cj.get("출처", "")) and \
                    "나눠팔기" not in str(_cj.get("출처", "")):
                알림(False, "rule-capital.json 출처에 매도 방식이 안 적혀 있다 "
                           "— 어느 규칙으로 잰 값인지 확인하라")
            elif not 조용:
                print("    ✅ rule-capital.json 에 매도 방식이 적혀 있다")
    except Exception as e:  # noqa: BLE001
        알림(False, f"규칙 대조 실패: {type(e).__name__} {str(e)[:60]}")

    # ══ E 알려진 함정 ══
    if not 조용:
        print("\n  ══ E 알려진 함정 ══")
    # ⚠️⚠️ **줄 단위로 본다.** 처음엔 통짜 정규식(lookahead)으로 짰다가
    #    「주수·금액 혼동」이 **19개 전부 오탐**이었다 (다 원시를 쓰고 있었다).
    #    **틀린 경보를 내는 점검기는 없느니만 못하다.**
    #    ⇒ 조건을 「이 꼴이면 나쁘다」가 아니라
    #      **「이 꼴인데 안전장치가 그 줄에 없으면 나쁘다」**로 바꿨다
    def 함정검사(줄글, 이름):
        out = []
        for n, L in enumerate(줄글, 1):
            s2 = L.split("#")[0]        # 주석은 뺀다
            if not s2.strip():
                continue
            # ① 낙폭은 음수 — 「더 나쁜 것」을 통과시키는 비교
            if re.search(r"낙\w*\s*<=\s*기낙", s2):
                out.append((n, "낙폭 부호",
                            "낙폭은 **음수**다. `낙2 <= 기낙2*1.15`는 "
                            "「더 나쁜 것」을 통과시킨다"))
            # ② 주수를 **수정주가**로 나누면 안 된다 (53차).
            #    ⚠️⚠️ **2026-09-07 다시 좁혔다.** 「그 줄에 원시가 있나」만 보다가
            #       또 **5개 전부 오탐**을 냈다 —
            #         gate2_lab `주수 = int(총주수 * 비율)`  (총주수는 위에서 원시로 냈다)
            #         bought.py `주수 = int(주.replace(",", ""))`  (사람이 친 값이다)
            #       ⇒ 나눗셈이 **그 줄에 실제로 있을 때만** 본다.
            #         그리고 원시를 **앞뒤 3줄**까지 찾는다 (변수로 빼 쓰는 게 흔하다)
            if (re.search(r"주수\s*=\s*int\(", s2) and "/" in s2
                    and not re.search(r"원시|매수원|원가",
                                      "".join(줄글[max(0, n - 4):n + 3]))):
                out.append((n, "주수·금액 혼동",
                            "주수는 **원본 시가(원시)**로 나눠야 한다 (53차 버그)"))
            # ③ 백슬래시 검사는 **뺐다** (2026-09-04)
            #    `\n` 같은 **정상 이스케이프**까지 잡아 **724개 오탐**을 냈고,
            #    D절이 ast.parse로 **진짜 SyntaxWarning**을 이미 잡으므로 중복이다.
            #    ⚠️ 점검기는 오탐이 하나라도 있으면 아무도 안 본다.
            #       「이 검사가 지금 코드에서 오탐 0인가」를 넣기 전에 확인한다
            # ④ DART 날짜를 bddd로만 — 갈래마다 이름이 다르다
            if 'get("bddd")' in s2 and "rcept_no" not in "".join(줄글):
                out.append((n, "bddd만 봄",
                            "갈래마다 날짜 필드가 다르다. "
                            "**rcept_no 앞 8자리**를 쓴다"))
        return out

    걸림 = 0
    for p in sorted(glob.glob(os.path.join(_BASE, "scripts", "*.py"))):
        if os.path.basename(p) == "selfcheck.py":
            continue        # ⚠️ 자기 자신은 뺀다 (함정 설명글이 걸린다)
        try:
            줄글 = io.open(p, encoding="utf-8-sig").read().splitlines()
        except Exception:
            continue
        for n, 이름, 설 in 함정검사(줄글, os.path.basename(p)):
            알림(False, f"{os.path.basename(p)}:{n} [{이름}] {설}")
            걸림 += 1
    if not 조용 and 걸림 == 0:
        print("    ✅ 알려진 함정에 걸린 곳 없음")
    # ⚠️ **J절(이름 덮어쓰기 검사)은 뺐다** (2026-09-07).
    #     같은 **정상 코드를 잡았다** —
    #    날이 반복 대상이지 반복 변수가 아닌데 정규식이 구분을 못 했다.
    #    **울부짖는 경보는 없는 것만 못하다.**
    #    대신 각 시험 스크립트에 **실행 시 확인**을 넣는다:
    #       assert isinstance(날, list) and len(날) > 1000
    #    그게 훨씬 확실하다 (signal_map2.py 참고)

    # ══ I 훑기 결과가 전부 같지 않나 ══
    #    ⚠️ 2026-09-07 에 이걸로 당했다. 문턱을 9가지로 바꿔 훑었는데
    #       **전부 6,586,181원 · 52건**이 나왔다. 수집 단계에서 그 값을
    #       이미 걸어버려서 시뮬이 아무것도 못 바꾼 것이다.
    #       프로그램은 정상 종료하고 표도 그럴듯해서 **눈으로만 잡힌다**
    if not 조용:
        print("\n  ══ I 훑기 결과가 전부 같은 표가 있나 ══")
    import collections as _c
    for p in sorted(glob.glob(os.path.join(_DATA, "_labs", "2026-*.txt")))[-12:]:
        try:
            t = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:  # noqa: BLE001
            continue
        b = os.path.basename(p)
        나쁨 = []
        덩 = t.split("──")
        for 조각 in 덩:
            돈 = re.findall(r"([0-9]{1,3}(?:,[0-9]{3})+)원", 조각)
            if len(돈) < 4:
                continue
            c = _c.Counter(돈)
            많, 몇 = c.most_common(1)[0]
            if 몇 >= 4 and 몇 >= len(돈) * 0.8:
                머 = 조각.strip().split("\n")[0][:40]
                나쁨.append(머 + " -> " + str(몇) + "줄이 전부 " + 많 + "원")
        if 나쁨:
            알림(True, b + ": **훑기 결과가 전부 같다** — 문턱을 바꿔도 안 변한다는 뜻이다. " + 나쁨[0])
        elif not 조용:
            print("    ✅ " + b)


    # ══ E-2 하기로 해놓고 안 한 것 ══ (2026-09-08 신설)
    #    ⚠️⚠️ **「새로운 조합」이 가번호 150으로 계획에 있다가 사라졌다.**
    #       150번이 걷기검증에 붙으면서 목록에서 빠졌고, 사용자가 물어서 알았다
    #       ⇒ 계획을 **글이 아니라 표**(docs/할일.md)에 적고 기계가 맞춰본다
    if not 조용:
        print("\n  ══ E-2 하기로 해놓고 안 한 것 ══")
    try:
        import subprocess as _sp
        _r = _sp.run([sys.executable,
                      os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "plan_check.py"), "--조용"],
                     capture_output=True, text=True, encoding="utf-8",
                     errors="replace", timeout=120)
        _말 = (_r.stdout or "") + (_r.stderr or "")
        _어긋 = [x.strip() for x in _말.splitlines() if x.strip().startswith("·")]
        if _r.returncode != 0 and _어긋:
            for _x in _어긋:
                알림(True, f"할일.md 와 어긋남: {_x.lstrip('· ')}")
        elif not 조용:
            for _l in _말.splitlines():
                if "적힌 줄" in _l:
                    print("   " + _l.strip())
            print("    ✅ 할일.md 와 어긋난 것 없다")
    except Exception as _e:  # noqa: BLE001
        알림(False, f"할일 점검을 못 돌렸다: {type(_e).__name__}")

    # ══ F 시험 결과 ══
    if not 조용:
        print("\n  ══ F 최근 시험 결과 ══")
    최근 = sorted(glob.glob(os.path.join(_DATA, "_labs", "2026-*.txt")))[-8:]
    for p in 최근:
        try:
            t = io.open(p, encoding="utf-8").read()
        except Exception:
            continue
        b = os.path.basename(p)
        if "Traceback" in t:
            알림(True, f"{b}: **Traceback**이 들어 있다")
        elif re.search(r"있는 종목 0개|0건 확보|파싱 결과가 0", t):
            알림(True, f"{b}: **파싱 0건**이 들어 있다")
        elif not 조용:
            print(f"    ✅ {b}")

    # ══ G PC가 비정상으로 꺼진 적 있나 ══
    #    ⚠️ **2026-09-04 신설.** 2026-09-01 18:09에 Kernel-Power 41이 찍혔다
    #       (정상 종료 절차 없이 꺼짐). 밤새 도는 예약이 통째로 날아간다
    #       — 그런데 **아무도 몰랐다.** 예약은 「돌았다」로 표시된다
    if not 조용:
        print("\n  ══ G PC 비정상 종료 (최근 7일) ══")
    try:
        _ps = (
            "Get-WinEvent -FilterHashtable @{LogName='System';Id=41,6008;"
            "StartTime=(Get-Date).AddDays(-7)} -EA SilentlyContinue | "
            "ForEach-Object { $_.TimeCreated.ToString('yyyy-MM-dd HH:mm') }"
        )
        _r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _ps],
            capture_output=True, timeout=60)
        _때 = sorted({x.strip() for x in
                      _r.stdout.decode("utf-8", errors="replace").splitlines()
                      if x.strip()})
        if _때:
            알림(False, f"PC가 비정상 종료됨 **{len(_때)}회** — "
                        f"{', '.join(_때[-3:])} · 그때 돌던 예약은 날아갔다")
        elif not 조용:
            print("    ✅ 최근 7일 비정상 종료 없음")
    except Exception as e:
        if not 조용:
            print(f"    (못 봤다: {type(e).__name__})")

    # ══ H 예약이 실패로 끝난 게 있나 ══
    if not 조용:
        print("\n  ══ H 예약 마지막 실행 결과 ══")
    try:
        _ps2 = (
            "Get-ScheduledTask | Where-Object { $_.TaskName -match "
            "'AutoSearch|Capital|Weekend|Forward|SelfCheck|Morning|Evening'"
            " } | ForEach-Object { $i=$_ | Get-ScheduledTaskInfo; "
            "\"$($_.TaskName)`t$($i.LastTaskResult)`t$($i.LastRunTime)\" }"
        )
        _r2 = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _ps2],
            capture_output=True, timeout=60)
        for _x in _r2.stdout.decode("utf-8", errors="replace").splitlines():
            _p = _x.strip().split("\t")
            if len(_p) < 3:
                continue
            # 0=정상 · 267011(0x41303)=아직 안 돔 · 267014=사용자가 끝냄
            # ⚠️ SelfCheck 은 문제를 찾으면 일부러 1로 끝난다 — 위와 같은 이유로 뺀다
            if _p[0].startswith("SelfCheck") or _p[1] in ("0", "267011", "267014"):
                if not 조용:
                    print(f"    ✅ {_p[0]:<24}{_p[2][:16]}")
            else:
                알림(True, f"예약 **{_p[0]}**이 코드 {_p[1]}로 끝났다 "
                           f"({_p[2][:16]})")
    except Exception as e:
        if not 조용:
            print(f"    (못 봤다: {type(e).__name__})")

    # ══ 마무리 ══
    print()
    if 문제:
        print(f"  ❌ **고쳐야 할 것 {len(문제)}개**")
        for s in 문제:
            print(f"     · {s}")
    if 경고:
        print(f"  ⚠️ 살펴볼 것 {len(경고)}개")
        for s in 경고[:12]:
            print(f"     · {s}")
        if len(경고) > 12:
            print(f"     … 외 {len(경고)-12}개")
    if not 문제 and not 경고:
        print("  ⭐ **모두 정상**")
    return 1 if 문제 else 0


if __name__ == "__main__":
    sys.exit(main())
