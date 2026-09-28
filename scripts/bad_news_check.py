r"""**악재 공시 알림** — 보유 종목과 최근 후보에 나쁜 공시가 떴나 (2026-09-28 신설)

왜 있나 (연휴 판 EXIT ② · BAD)
    보유 중에 악재 공시가 뜬 종목을 **다음 날 시가에** 팔면
      끝 자산 341,022,569 → 360,648,766원 (106%) · 낙폭 **−10.8% → −6.7%** · 위험 대비 171%
    증분 걷기도 앞 +3.3% 뒤 +7.9% 로 넘었다 (해마다는 4승 5패 — 고르게 좋은 게 아니라
    가끔 오는 큰 사고를 피해서 버는 방식이다).

사용자 (2026-09-28): 「악재 매도 장치는 있으면 좋을 것 같아. **실제로 매수를 했든 안 했든 참고가 되니까**」
    ⇒ 보유 종목만 보지 않는다. **최근 후보로 올랐던 종목**도 같이 본다.

무엇을 하나
    ① 보유 종목 — data/portfolio.json 의 holdings
    ② 최근 후보 — data/forward-log.jsonl 의 최근 N일(기본 90일) 후보
    ③ 그 종목들에 **최근 며칠(기본 3거래일)** 안에 악재 공시가 떴나 (data/dart-daily)
    ④ 떴으면 종목·공시명·날짜를 찍는다. 보유 중이면 **「다음 날 시가 매도 대상」**이라고 붙인다

⚠️ 이 장치는 **알리기만 한다.** 자동으로 팔지 않는다 — 주문 API 는 부르지 않는다.
⚠️ 악재말은 newmat._악재말 하나에서 온다 (판과 실전이 같은 목록을 쓴다).

쓰기: python scripts/bad_news_check.py [--날수 3] [--후보일 90] [--조용]
나가는 값: 보유 종목에 악재가 있으면 1 (없으면 0)
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
뿌리 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(뿌리, "scripts"))
import krx_calendar as K  # noqa: E402
import newmat as _NM  # noqa: E402


def 인자(이름, 기본):
    if 이름 in sys.argv:
        i = sys.argv.index(이름)
        if i + 1 < len(sys.argv) and sys.argv[i + 1].lstrip("-").isdigit():
            return int(sys.argv[i + 1])
    return 기본


날수 = 인자("--날수", 3)
후보일 = 인자("--후보일", 90)
조용 = "--조용" in sys.argv

# ── ① 볼 종목 모으기 ──
볼것 = {}          # code -> {"이름":…, "왜": set()}


def 더하기(code, 이름, 왜):
    code = str(code or "").strip()
    if not code:
        return
    볼것.setdefault(code, {"이름": 이름 or "", "왜": set()})
    if 이름 and not 볼것[code]["이름"]:
        볼것[code]["이름"] = 이름
    볼것[code]["왜"].add(왜)


try:
    _p = json.load(io.open(os.path.join(뿌리, "data", "portfolio.json"), encoding="utf-8-sig"))
    for h in (_p.get("holdings") or []):
        더하기(h.get("code"), h.get("name"), "보유")
    for h in (_p.get("수동") or []):
        더하기(h.get("code"), h.get("name"), "보유")
except (OSError, ValueError) as e:
    print(f"⚠️ 보유 기록을 못 읽었다: {type(e).__name__}")

import datetime as dt  # noqa: E402

_오늘 = dt.date.today()
_후보경계 = (_오늘 - dt.timedelta(days=후보일)).strftime("%Y%m%d")
try:
    for z in io.open(os.path.join(뿌리, "data", "forward-log.jsonl"), encoding="utf-8-sig"):
        z = z.strip()
        if not z:
            continue
        try:
            d = json.loads(z)
        except ValueError:
            continue
        if str(d.get("신호기준일") or "") < _후보경계:
            continue
        for c in (d.get("후보") or []):
            더하기(c.get("종목코드"), c.get("이름"), "후보")
except OSError:
    pass

# ── ② 최근 며칠의 공시 ──
_볼날 = []
_d = _오늘
while len(_볼날) < 날수 and len(_볼날) < 30:
    if K.장서는날(_d)[0]:
        _볼날.append(_d.strftime("%Y%m%d"))
    _d -= dt.timedelta(days=1)

걸린 = []
본공시 = 0
for _d8 in _볼날:
    _길 = os.path.join(뿌리, "data", "dart-daily", f"{_d8}.json")
    try:
        _j = json.load(io.open(_길, encoding="utf-8-sig"))
    except (OSError, ValueError):
        continue
    for _칸 in ("챙길공시", "그밖의공시"):
        for _x in (_j.get(_칸) or []):
            본공시 += 1
            _c = str(_x.get("종목코드") or "").strip()
            if _c not in 볼것:
                continue
            _제 = str(_x.get("공시명") or "")
            _맞 = [w for w in _NM._악재말 if w in _제]
            if _맞:
                # ⚠️ **반대말**이 섞인다 — 「거래정지**해제**」는 좋은 소식인데 「거래정지」가 걸린다.
                #    판과 같은 목록을 써야 성적이 옵기므로 **목록은 그대로 두고 표시만** 한다 (2026-09-28)
                _반대 = [w for w in ("해제", "취소", "철회", "종결", "기각") if w in _제]
                걸린.append({"날": _d8, "code": _c, "이름": 볼것[_c]["이름"] or _x.get("종목명") or "",
                            "공시명": _제, "말": _맞, "왜": 볼것[_c]["왜"], "반대": _반대})

# ── ③ 찍기 ──
_보유걸림 = [z for z in 걸린 if "보유" in z["왜"]]
if not 조용 or 걸린:
    print(f"악재 공시 확인 — 본 종목 {len(볼것)}개 (보유 {sum(1 for v in 볼것.values() if '보유' in v['왜'])}"
          f" · 최근 {후보일}일 후보 {sum(1 for v in 볼것.values() if '후보' in v['왜'])})"
          f" · 공시 {본공시:,}건 ({' · '.join(_볼날)})")
if 걸린:
    print(f"\n⚠️ 악재 공시 {len(걸린)}건")
    for z in sorted(걸린, key=lambda y: (-("보유" in y["왜"]), y["날"])):
        _표 = "🔴 보유 — **다음 날 시가 매도 대상**" if "보유" in z["왜"] else "· 후보였던 종목 (참고)"
        print(f"   {z['날']}  {z['이름']}({z['code']})  {_표}")
        print(f"      {z['공시명'][:70]}   ← 걸린 말: {', '.join(z['말'])}"
              + (f"   ⚠️ 「{'·'.join(z['반대'])}」가 들어 있다 — 반대말일 수 있다" if z.get("반대") else ""))
    if _보유걸림:
        print(f"\n🔴 보유 종목 {len(_보유걸림)}건이 규칙상 **다음 날 시가 매도** 대상이다")
        print("   ⚠️ 이 장치는 알리기만 한다 — 주문은 사람이 낸다")
elif not 조용:
    print("✅ 보유·후보 종목에 악재 공시 없다")
raise SystemExit(1 if _보유걸림 else 0)
