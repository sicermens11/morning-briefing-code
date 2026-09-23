r"""A2 — **수집기 전수: 자료가 거래일만큼 최신인가** (2026-09-23 · 연휴 계획 A2)

왜 있나: 수집기가 조용히 실패해도 브리핑은 **옛 자료로 그냥 돈다.**
9/11·9/12·9/15·9/16 에 「어느 시장도 못 받았다」가 있었는데 아무도 몰랐다.
빈 날이 연휴·휴장이면 정상이라, **거래일 달력과 대조**해야 진짜 구멍이 보인다.

무엇을 하나
  ① data/ 의 json·jsonl 에서 가장 최신 날짜를 뽑는다 (YYYY-MM-DD 또는 YYYYMMDD)
  ② krx_calendar 의 직전 거래일과 견준다 — 며칠(거래일) 뒤처졌나
  ③ data/_*.log 의 마지막 줄에서 ok:false 를 찾는다
  ④ 뒤처진 거래일이 문턱(기본 3)을 넘으면 ❌

쓰기: python scripts/check_collectors.py [뒤처짐문턱]
나가는 값: 문턱 넘는 자료가 있으면 1
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "scripts"))
import krx_calendar as K  # noqa: E402

문턱 = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3
자료방 = os.path.join(뿌리, "data")

# 날마다 새로 받는 게 아닌 것들 — 뒤처져도 정상
# ⭐ 2026-09-23 A2 첫 돌림에서 나온 넷 — 이유를 적어 둔다 (소음이 실패를 숨기지 않게)
#   industry.json   — KRX 업종 분류. 기준일이 08-03 이고 분기마다 바뀜다 (받은 날은 09-18)
#   stock-base.json — 판(lab) 전용. 실전 브리핑 경로가 안 읽는다 (2026-09-23 확인)
#   us-index.json   — 버린 자료. 미국은 이제 yahoo(_yahoo.log · SPY 09-22)가 받는다
#   etf-daily.json  — 버린 자료. ETF 는 collect_krx_etf(_etfkrx.log · 09-21)로 옮겨갔다
느린것 = {"dart-corpcode.json", "krx-holidays", "secrets.json", "portfolio.json",
          "industry.json", "stock-base.json", "us-index.json", "etf-daily.json",
          "vanish-kind.json", "sell-options.json", "percode-rules.json",
          "event-calendar.json", "earnings-dates.json", "rule-capital.json",
          "consensus-history.jsonl", "backtest-returns.jsonl", "rule-cases.json",
          "rule-frequency.json", "_shape.json", "_무리_60.json", "unmapped-log.jsonl"}

날짜꼴 = re.compile(r"(20\d{2})-(\d{2})-(\d{2})|(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")


def 최신날짜(길, 최대바이트=4_000_000):
    """파일 안에서 가장 큰(최신) 날짜 문자열을 찾는다. 큰 파일은 뒤쪽만 본다"""
    try:
        크기 = os.path.getsize(길)
        with io.open(길, encoding="utf-8", errors="replace") as f:
            if 크기 > 최대바이트:
                f.seek(크기 - 최대바이트)
            글 = f.read()
    except OSError:
        return None
    제일 = None
    for m in 날짜꼴.finditer(글):
        y, mo, d = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(4), m.group(5), m.group(6))
        날 = f"{y}-{mo}-{d}"
        if not ("2010" <= y <= "2030") or not ("01" <= mo <= "12") or not ("01" <= d <= "31"):
            continue
        if 제일 is None or 날 > 제일:
            제일 = 날
    return 제일


거래일 = sorted(K.장서는날들() if hasattr(K, "장서는날들") else [])
직전 = K.직전거래일()
직전 = 직전.isoformat() if hasattr(직전, "isoformat") else str(직전)


def 뒤처짐(날):
    """그 날짜가 직전 거래일보다 몇 거래일 뒤처졌나"""
    import datetime as dt
    try:
        a = dt.date.fromisoformat(날)
    except ValueError:
        return None
    b = dt.date.fromisoformat(직전) if isinstance(직전, str) else 직전
    수 = 0
    보 = b
    while 보 > a and 수 < 400:
        보 -= dt.timedelta(days=1)
        if K.장서는날(보):
            수 += 1
    return 수


줄들, 걸림 = [], []
for 이름 in sorted(os.listdir(자료방)):
    if not 이름.endswith((".json", ".jsonl")) or 이름 in 느린것 or 이름.startswith("krx-holidays"):
        continue
    길 = os.path.join(자료방, 이름)
    날 = 최신날짜(길)
    if not 날:
        continue
    뒤 = 뒤처짐(날)
    줄들.append((뒤 if 뒤 is not None else 999, 이름, 날))
    if 뒤 is not None and 뒤 > 문턱:
        걸림.append((이름, 날, 뒤))

# ── 자료 폴더 — 날마다 파일이 쌓이는 곳 (수집기의 진짜 자취) ──
#    파일 이름에 든 날짜(20260922 또는 2026-09-22)에서 가장 최신을 본다
안볼폴더 = {"_labs", "_test", "_bak", "_cache", "_search", "_backup_consensus",
            "_bak_20260911_design", "SKILL-backups", "briefings", "card-copy",
            "fred", "ecos", "us-daily", "etf-daily", "minute", "naver-quarter",
            "us-symbols",   # 미국 종목 목록(2025-01-02 고정) — 날마다 받는 게 아니다
            # ⭐ 아래 넷은 **쌓아 두는 곳**이다 — 수집기는 날마다 돌지만 「이미 받음 · 받을 것 0」이라 파일이 안 바뀐다
            #    (2026-09-23 확인: _consensus/_quarter/_capital/_dartsnap 전부 실패 0). 대신 **로그 돈 때**로 본다
            "dart-fin", "quarter-fin", "consensus", "dart-capital"}
폴더걸림, 폴더본수 = [], 0
for 이름 in sorted(os.listdir(자료방)):
    방 = os.path.join(자료방, 이름)
    if not os.path.isdir(방) or 이름 in 안볼폴더:
        continue
    최신 = None
    try:
        것들 = os.listdir(방)
    except OSError:
        continue
    for 파 in 것들:
        m = 날짜꼴.search(파)
        if not m:
            continue
        y, mo, d = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(4), m.group(5), m.group(6))
        날 = f"{y}-{mo}-{d}"
        if 최신 is None or 날 > 최신:
            최신 = 날
    # ⚠️ 이름에 날짜가 없는 폴더(코드별 파일 등)는 **건너뛰면 사각지대**가 된다 —
    #    가장 새 파일의 시각으로 대신 본다 (「검사기의 사각지대」 2026-09-23)
    꼴 = "이름"
    if 최신 is None:
        늦 = None
        for 파 in 것들:
            try:
                t = os.path.getmtime(os.path.join(방, 파))
            except OSError:
                continue
            if 늦 is None or t > 늦:
                늦 = t
        if 늦 is None:
            continue
        import time as _t
        최신, 꼴 = _t.strftime("%Y-%m-%d", _t.localtime(늦)), "시각"
    폴더본수 += 1
    뒤 = 뒤처짐(최신)
    if 뒤 is not None and 뒤 > 문턱:
        폴더걸림.append((f"{이름} ({꼴})", 최신, 뒤, len(것들)))

# ── 수집기 로그의 마지막 결과 ──
나쁜로그 = []
for 이름 in sorted(os.listdir(자료방)):
    if not (이름.startswith("_") and 이름.endswith(".log")):
        continue
    길 = os.path.join(자료방, 이름)
    try:
        꼬리 = io.open(길, encoding="utf-8", errors="replace").read().splitlines()[-6:]
    except OSError:
        continue
    for z in 꼬리:
        if '"ok": false' in z or '"ok":false' in z:
            나쁜로그.append((이름, z.strip()[:150]))
            break

# ── 수집기 로그가 **제 주기**를 지키나 (2026-09-23) ──
#    ⚠️ 「며칠 안 돌았다」로만 보면 한 번짜리 메꿈 로그(_krx-fill·_queue12…) 35개가 쏟아진다 —
#       소음이 실패를 숨긴다. 그래서 로그마다 **평소 간격**을 스스로 재고,
#       평소의 3배 넘게 쉬고 있을 때만 잡는다. 한 번짜리(날짜 3개 미만)는 애초에 안 본다
import datetime as _dt
import time as _tt

안돈것, 주기본수 = [], 0
for 이름 in sorted(os.listdir(자료방)):
    if not (이름.startswith("_") and 이름.endswith(".log")):
        continue
    길 = os.path.join(자료방, 이름)
    try:
        글 = io.open(길, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    날들 = sorted({f"{m.group(1) or m.group(4)}-{m.group(2) or m.group(5)}-{m.group(3) or m.group(6)}"
                   for m in 날짜꼴.finditer(글)})
    날들 = [z for z in 날들 if "2025-01-01" < z <= 직전]
    if len(날들) < 4:          # 한 번짜리·메꿈 로그는 주기가 없다
        continue
    주기본수 += 1
    사이 = sorted((_dt.date.fromisoformat(날들[i + 1]) - _dt.date.fromisoformat(날들[i])).days
                  for i in range(len(날들) - 1))
    평소 = 사이[len(사이) // 2] or 1
    마지막 = 날들[-1]
    쉰날 = (_dt.date.fromisoformat(직전) - _dt.date.fromisoformat(마지막)).days
    if 쉰날 > max(평소 * 3, 평소 + 2):
        안돈것.append((이름, 마지막, 쉰날, 평소))

print(f"A2 — 직전 거래일 {직전} 기준 · 뒤처짐 문턱 {문턱}거래일")
if 걸림:
    print(f"❌ 뒤처진 자료 {len(걸림)}개")
    for 이름, 날, 뒤 in sorted(걸림, key=lambda z: -z[2]):
        print(f"   {이름:<34} 최신 {날}  ({뒤}거래일 뒤처짐)")
else:
    print(f"✅ 본 자료 {len(줄들)}개 전부 {문턱}거래일 안")
if 폴더걸림:
    print(f"❌ 뒤처진 자료 폴더 {len(폴더걸림)}개")
    for 이름, 날, 뒤, 수 in sorted(폴더걸림, key=lambda z: -z[2]):
        print(f"   data/{이름:<28} 최신 {날}  ({뒤}거래일 뒤처짐 · 파일 {수:,}개)")
else:
    print(f"✅ 자료 폴더 {폴더본수}개 전부 {문턱}거래일 안")
if 안돈것:
    print(f"❌ 제 주기를 크게 넘긴 수집기 {len(안돈것)}개")
    for 이름, 때, 쉰, 평소 in sorted(안돈것, key=lambda z: -z[2]):
        print(f"   data/{이름:<28} 마지막 {때}  ({쉰}일 쉬는 중 · 평소 {평소}일마다)")
else:
    print(f"✅ 되풀이 수집기 {주기본수}개 전부 제 주기 안")
if 나쁜로그:
    print(f"\n⚠️ 마지막 줄이 ok:false 인 수집기 로그 {len(나쁜로그)}개")
    for 이름, z in 나쁜로그:
        print(f"   {이름}  {z}")
raise SystemExit(1 if (걸림 or 폴더걸림 or 안돈것) else 0)
