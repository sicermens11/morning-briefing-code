#!/usr/bin/env python3
r"""
check_gaps.py — **빠진 자료를 찾아 채운다** (2026-09-10 신설)

## 왜 만드나
```
2026-09-09 19:00  저녁 수집이 「환율」에서 통째로 죽음 (코드 3221225786)
2026-09-10 19:04  「증자감자」 뒤 또 죽음 -> **뉴스를 못 받았다**
=> 원인을 **특정 못 했다** (유휴·배터리·시간제한 다 아니다)
=> 원인을 못 잡으면 **빠진 것을 찾아 채우는 쪽**이라도 있어야 한다
```

## 하는 일
```
A 자료 폴더마다 **마지막 날짜**를 보고 며칠 밀렸는지 센다
B 밀린 것이 있으면 **그 수집기를 다시 돌린다** (--채움 일 때)
C 아무것도 안 하면 조용히 끝난다
```

## ⚠️ 안전
```
· 기본은 **보기만** 한다. `--채움` 을 줘야 실제로 받는다
· DART 를 쓰는 것은 **한도**를 생각해 하루 한 번만 채운다
· 이미 도는 수집과 겹치지 않게 **20:30** 에 예약한다 (저녁 수집은 19:00)
```

쓰는 법:
    python scripts\check_gaps.py            # 보기만
    python scripts\check_gaps.py --채움      # 빠진 것을 받는다
"""
import datetime as dt
import glob
import io
import os
import subprocess
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
LOG = os.path.join(_DATA, "_gaps.log")

# (폴더, 이름, 며칠까지 봐줄까, 채우는 스크립트, 인자)
_볼것 = [
    ("krx-daily", "주가(KRX)", 2, "morning_krx.py", []),
    ("index-daily", "지수(KRX)", 2, "morning_krx.py", []),
    # ⚠️⚠️ 허용치 **0** (2026-09-29 밤 고침). 네이버는 그날 수급을 **19시 넘어서** 올린다.
    #    저녁 수집(19:04)은 9/15~9/28 열흘 내내 「0종목」이었고, 여기 허용치가 2 라서
    #    수급이 **이틀씩 늦게** 쌓였다 (9/29 밤 flow-daily 마지막이 0923). 20:30 이면 그날치가 있다
    ("flow-daily", "수급(네이버)", 0, "collect_flow.py", []),
    ("dart-daily", "공시(DART)", 2, "fetch_dart.py", []),
    # ⚠️ kind-time 은 collect_evening 안의 함수가 받는다 —
    #    따로 돌릴 스크립트가 없어 **보기만** 한다
    ("kind-time", "공시시각(KIND)", 2, None, []),
    # ⚠️ 허용치 **1** (2026-09-17 고침). ETF 는 하루 뒤 08:10 에 오는데 이 검사는 20:30 에 돈다 —
    #    20:30 에 있을 수 있는 가장 새 자료가 어제치라 **1이 정확한 값**이다.
    #    2 였을 때는 3일째에야 채워서 사용자 화면에 ⚠️ 가 떴다 (09-17 첨부)
    ("etf-krx", "ETF(KRX)", 1, "morning_extra.py", []),
]

# ⚠️⚠️ **날짜 파일이 아닌 것들** (2026-09-11 신설).
#    `news` 와 `dart-capital` 은 **종목코드**로 저장돼 위 방식(마지막 날짜)으로
#    못 잰다. 그래서 감시 목록에 없었고, 9/10·9/11 이틀 연속 저녁 수집이
#    거기서 죽었는데도 `check_gaps` 는 **「빠진 것이 없다」**고 했다.
#    오늘 아침 규칙 검사에서 겪은 「목록에 없으면 영영 안 걸린다」와 같은 구멍이다.
#    ⇒ **폴더에서 가장 최근에 바뀐 파일의 시각**으로 잰다
_시각볼것 = [
    ("news", "뉴스(네이버)", 3),          # 며칠 넘게 안 바뀌면 수집이 죽은 것
    ("dart-capital", "증자감자(DART)", 3),
]


def 찍기(s):
    줄 = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(줄, flush=True)
    try:
        io.open(LOG, "a", encoding="utf-8").write(줄 + "\n")
    except OSError:
        pass


def 마지막날(폴더):
    r"""그 폴더에서 **가장 최근 날짜 파일**의 날짜 (YYYYMMDD)."""
    벌 = []
    for p in glob.glob(os.path.join(_DATA, 폴더, "*.json")):
        b = os.path.basename(p)[:8]
        if b.isdigit() and len(b) == 8:
            벌.append(b)
    return max(벌) if 벌 else None


def _휴장일():
    r"""**주가 파일 달력**에서 휴장일을 찾는다 (2026-09-29 신설).

    ⚠️ 전에는 주말만 뺐다 — 추석(9/24·25)을 거래일로 세어 ETF 가 「4거래일 밀림」으로
       떴다. 실제로 빠진 건 9/28 하루였다 (사용자: 「왜 밀린게 있어?」).
    krx-daily 첫 파일 ~ 마지막 파일 사이 **평일인데 파일이 없는 날** = 휴장일.
    마지막 파일 뒤는 알 수 없어 평일로 센다 (넉넉히 본다)
    """
    거래 = {os.path.basename(p)[:8] for p in glob.glob(os.path.join(_DATA, "krx-daily", "*.json"))}
    거래 = {z for z in 거래 if z.isdigit() and len(z) == 8}
    if not 거래:
        return set()
    d = dt.datetime.strptime(min(거래), "%Y%m%d")
    끝 = dt.datetime.strptime(max(거래), "%Y%m%d")
    쉼 = set()
    while d < 끝:
        d += dt.timedelta(days=1)
        k = d.strftime("%Y%m%d")
        if d.weekday() < 5 and k not in 거래:
            쉼.add(k)
    return 쉼


def 거래일수(a, b, 쉼=None):
    r"""a 부터 b 까지 **주말과 휴장일을 뺀** 날수."""
    쉼 = _휴장일() if 쉼 is None else 쉼
    d1 = dt.datetime.strptime(a, "%Y%m%d")
    d2 = dt.datetime.strptime(b, "%Y%m%d")
    n = 0
    while d1 < d2:
        d1 += dt.timedelta(days=1)
        if d1.weekday() < 5 and d1.strftime("%Y%m%d") not in 쉼:
            n += 1
    return n


def _저녁끝(이름):
    r"""저녁 수집 기록(`_evening.log`)에서 그 수집이 **마지막으로 끝까지 돈 날** (없으면 None).

    ⭐ 2026-09-29 — 증자감자는 새 공시가 없으면 파일이 **안 바뀐다**(「호출 0회」가 정상).
       파일 시각만 보면 멀쩡한데도 「6일 전」으로 떴다. **수집이 돌았나**를 본다
    """
    try:
        줄들 = io.open(os.path.join(_DATA, "_evening.log"), encoding="utf-8",
                     errors="replace").read().splitlines()
    except OSError:
        return None
    for 줄 in reversed(줄들):
        if 이름 in 줄 and " 끝" in 줄 and "실패 0" in 줄:
            try:
                return dt.datetime.strptime(줄[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
    return None


def main():
    채움 = "--채움" in sys.argv
    오늘 = dt.datetime.now().strftime("%Y%m%d")
    찍기(f"===== 빠진 자료 확인 · {오늘} "
         f"({'채운다' if 채움 else '보기만'}) =====")

    빈것 = []
    for 폴더, 이름, 봐줄날, 스크, 인자 in _볼것:
        끝 = 마지막날(폴더)
        if not 끝:
            찍기(f"  ⚠️ {이름:16s} 파일이 **하나도 없다**")
            continue
        밀 = 거래일수(끝, 오늘)
        표 = "✅" if 밀 <= 봐줄날 else "⚠️"
        찍기(f"  {표} {이름:16s} 마지막 {끝} · **{밀}거래일** 밀림")
        if 밀 > 봐줄날:
            빈것.append((이름, 스크, 인자, 밀))

    # ⭐ 종목코드로 저장되는 것들 — **폴더가 언제 바뀌었나**로 잰다
    for 폴더, 이름, 봐줄날 in _시각볼것:
        _d = os.path.join(_DATA, 폴더)
        _f = glob.glob(os.path.join(_d, "*.json"))
        if not _f:
            찍기(f"  ⚠️ {이름:16s} 폴더가 비었다")
            빈것.append((이름, None, [], 99))
            continue
        _새 = max(os.path.getmtime(x) for x in _f)
        # ⭐ 수집이 끝까지 돈 기록이 파일 시각보다 새로우면 그것으로 잰다 (새 공시 0 = 파일 안 바뀜)
        _돈 = _저녁끝(이름.split("(")[0] + "(")
        if _돈 and _돈.timestamp() > _새:
            _새 = _돈.timestamp()
        _민 = (dt.datetime.now() - dt.datetime.fromtimestamp(_새)).days
        표2 = "✅" if _민 <= 봐줄날 else "⚠️"
        찍기(f"  {표2} {이름:16s} 마지막 갱신 "
             f"{dt.datetime.fromtimestamp(_새):%Y-%m-%d %H:%M} · "
             f"**{_민}일** 전")
        if _민 > 봐줄날:
            빈것.append((이름, None, [], _민))

    if not 빈것:
        찍기("  ⇒ 빠진 것이 없다")
        return 0

    찍기(f"\n  ⇒ ⚠️ **밀린 것 {len(빈것)}개**")
    if not 채움:
        찍기("     `--채움` 을 주면 받는다")
        return 0

    for 이름, 스크, 인자, 밀 in 빈것:
        if not 스크:
            찍기(f"  ⚠️ {이름}: 따로 돌릴 스크립트가 없다 (저녁 수집이 받는다)")
            continue
        p = os.path.join(_BASE, "scripts", 스크)
        if not os.path.exists(p):
            찍기(f"  ⚠️ {이름}: {스크} 가 없다")
            continue
        찍기(f"  ▶ {이름} 채우는 중 ({스크})...")
        e2 = dict(os.environ)
        e2["PYTHONIOENCODING"] = "utf-8"
        플 = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            r = subprocess.run([sys.executable, p] + 인자, capture_output=True,
                               timeout=1800, env=e2, cwd=_BASE, creationflags=플)
            꼬 = r.stdout.decode("utf-8", "replace").strip().splitlines()
            찍기(f"    {꼬[-1].strip()[:110] if 꼬 else f'코드 {r.returncode}'}")
            if r.returncode != 0:
                # ⚠️ stderr 를 **남긴다** — 저녁 수집이 이걸 버려서
                #    두 번이나 원인을 놓쳤다 (2026-09-09·09-10)
                for 줄 in r.stderr.decode("utf-8", "replace").splitlines()[-5:]:
                    if 줄.strip():
                        찍기(f"       {줄.strip()[:150]}")
        except subprocess.TimeoutExpired:
            찍기("    ⚠️ 30분을 넘겨 멈췄다")
        except Exception as e:  # noqa: BLE001
            찍기(f"    ⚠️ {type(e).__name__}: {e}")
    찍기("===== 끝 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
