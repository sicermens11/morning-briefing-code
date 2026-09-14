#!/usr/bin/env python3
r"""
bought.py — **실제로 산 것을 기록한다** (2026-09-07 신설)

## ⚠️ 왜 필요한가
```
사용자 지적: 「매수 후 언제 매도해야 하는지 관리해주지 않는다」
확인해보니 맞다:
  지정가 매도    사면서 걸어두면 증권사가 처리한다        ✅ 잊어도 된다
  기한 정리     **아무도 안 알려준다**                  ❌ 사람이 날짜를 센다
더 근본적으로 forward-log 의 「산것」은 **늘 빈 배열**이었다.
「09:00에 실제로 산 것을 나중에 채운다」고 주석만 있고 채우는 경로가 없었다
⇒ 기록이 없으니 D+40 을 셀 수도 없다
```
⚠️ **주문은 하지 않는다.** 사람이 산 것을 적기만 한다.

## 쓰는 법
```
산 뒤에 (또는 아무 때나)
    python scripts\bought.py 052460=4550
    python scripts\bought.py 052460=4550,092070=11700
    python scripts\bought.py --주수 052460=4550x220        주수까지 적을 때
    python scripts\bought.py --보기                        지금 들고 있는 것
    python scripts\bought.py --팔았다 052460               판 것을 지운다
```
저장: `data/forward-log.jsonl` 의 그날 줄 안 `산것`
"""
import datetime as dt
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⭐⭐⭐ **규칙은 `rule_def.py` 한 곳에만** (2026-09-11). 숫자를 다시 적지 않는다
import rule_def as R  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "forward-log.jsonl")
KRX = os.path.join(_BASE, "data", "krx-daily")
# ⚠️ 2026-09-07 나눠팔기로 바뀜 — 한 종목을 사면 주수를 반으로 나눈다
_몫들 = R.몫들                        # (비율, 목표%, 최대보유일)


def _몫말(비율):
    """「반은」 / 「40%는」 — 비율에서 (2026-09-14 · 퍼센트 뒤 조사는 「는」)"""
    return "반은" if abs(비율 - .5) < 1e-9 else f"{비율 * 100:g}%는"

_최대보유 = R.최대보유   # 뒤 몫까지 들고 있으므로 긴 쪽으로 센다
_목표 = R.앞몫목표     # 앞 몫


def 거래일들():
    return sorted(os.path.basename(p)[:8]
                  for p in glob.glob(os.path.join(KRX, "*.json")))


def 읽기():
    줄 = []
    if os.path.exists(LOG):
        for x in io.open(LOG, encoding="utf-8"):
            x = x.strip()
            if x:
                try:
                    줄.append(json.loads(x))
                except ValueError:
                    pass
    return 줄


def 쓰기(줄):
    with io.open(LOG, "w", encoding="utf-8") as f:
        for r in 줄:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def 보유목록(줄):
    """[(신호기준일, 산것)] — 아직 안 판 것만"""
    out = []
    for r in 줄:
        for x in (r.get("산것") or []):
            if not x.get("판날"):
                out.append((r.get("신호기준일"), x))
    return out


def 남은날(산날, 오늘=None):
    """산 날부터 몇 거래일 지났나 · 뒤 몫(D+90)까지 며칠 남았나

    ⚠️ 앞 몫은 D+40, 뒤 몫은 D+90 이다. 여기서는 **긴 쪽**을 센다 —
       앞 몫이 D+40에 정리돼도 뒤 몫이 남아 있기 때문이다
    """
    날 = 거래일들()
    오늘 = 오늘 or (날[-1] if 날 else None)
    try:
        i = 날.index(산날)
    except ValueError:
        return None, None
    j = len(날) - 1 if 오늘 not in 날 else 날.index(오늘)
    지 = j - i
    return 지, _최대보유 - 지


def main():
    줄 = 읽기()
    if not 줄:
        print("⚠️ forward-log.jsonl 이 비어 있다. 먼저 record_pick 을 돌려라")
        return 1

    # ── 보기 ──
    if "--보기" in sys.argv or len(sys.argv) == 1:
        보유 = 보유목록(줄)
        print("=" * 72)
        print("  지금 들고 있는 것")
        print("=" * 72)
        if not 보유:
            print("\n  ⬛ **없다.** 산 것을 적으려면:")
            print("     python scripts\\bought.py 052460=4550")
            print("=" * 72)
            return 0
        print(f"\n  {'종목':<14}{'산 날':<11}{'산 값':>10}"
              f"{'지난 날':>8}{'남은 날':>8}   할 일")
        for 기, x in 보유:
            지, 남 = 남은날(x.get("산날") or 기)
            할 = ""
            if 남 is None:
                할 = "⚠️ 날짜를 모르겠다"
            elif 남 <= 0:
                할 = "🔴 **오늘 정리** (D+90 지남)"
            elif 남 <= 3:
                할 = f"🟡 {남}거래일 뒤 정리"
            else:
                할 = "보유 · +15%/+40% 지정가 둘 다 걸어둘 것"
            print(f"  {(x.get('이름') or x.get('종목코드','')):<14}"
                  f"{(x.get('산날') or 기 or ''):<11}"
                  f"{x.get('산값', 0):>10,}"
                  f"{(지 if 지 is not None else 0):>8}"
                  f"{(남 if 남 is not None else 0):>8}   {할}")
        print("\n  ⚠️ +20% 지정가는 **사면서 걸어두면** 증권사가 처리한다.")
        print("     사람이 기억할 것은 **D+40 정리**뿐이다")
        print("=" * 72)
        return 0

    # ── 팔았다 ──
    if "--팔았다" in sys.argv:
        코드 = sys.argv[sys.argv.index("--팔았다") + 1].strip().zfill(6)
        찾 = 0
        for r in 줄:
            for x in (r.get("산것") or []):
                if x.get("종목코드") == 코드 and not x.get("판날"):
                    x["판날"] = dt.date.today().strftime("%Y-%m-%d")
                    찾 += 1
        쓰기(줄)
        print(f"  {코드} — {찾}건을 판 것으로 표시했다")
        return 0

    # ── 적기 ──
    값 = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not 값:
        print("⚠️ 꼴: python scripts\\bought.py 052460=4550")
        return 1
    끝 = 줄[-1]
    이름표 = {x["종목코드"]: x for x in (끝.get("후보") or [])}
    산것 = 끝.setdefault("산것", [])
    오늘 = dt.date.today().strftime("%Y-%m-%d")
    날 = 거래일들()
    산날 = 날[-1] if 날 else 오늘
    센 = 0
    for 조각 in ",".join(값).split(","):
        조각 = 조각.strip()
        if not 조각 or "=" not in 조각:
            continue
        c, v = 조각.split("=", 1)
        c = c.strip().zfill(6)
        주수 = None
        if "x" in v.lower():
            v, 주 = v.lower().split("x", 1)
            try:
                주수 = int(주.replace(",", ""))
            except ValueError:
                주수 = None
        try:
            산값 = float(v.replace(",", ""))
        except ValueError:
            print(f"  ⚠️ {조각} — 숫자가 아니다. 건너뛴다")
            continue
        후 = 이름표.get(c)
        if 후 is None:
            print(f"  ⚠️ **{c} 는 오늘 후보에 없다.** 종목코드를 확인하라 "
                  f"(그래도 적는다)")
        if any(x.get("종목코드") == c and not x.get("판날") for x in 산것):
            print(f"  · {c} 는 이미 들고 있다 — 건너뛴다")
            continue
        산것.append({"종목코드": c, "이름": (후 or {}).get("이름", ""),
                     "산값": round(산값), "주수": 주수,
                     "산날": 산날, "적은날": 오늘, "판날": None,
                     # ⭐ 목표는 rule_def 에서 (2026-09-14) — 1.15/1.40 이 박혀 있었다
                     "목표가앞": round(산값 * (1 + R.앞몫목표 / 100)),
                     "목표가뒤": round(산값 * (1 + R.뒷몫목표 / 100))})
        센 += 1
        print(f"  ✅ {(후 or {}).get('이름', c)} ({c}) {산값:,.0f}원 적음 "
              f"· {_몫말(R.몫들[0][0])} {산값 * (1 + R.앞몫목표 / 100):,.0f}원(+{R.앞몫목표:g}%) "
              f"· {_몫말(R.몫들[1][0])} {산값 * (1 + R.뒷몫목표 / 100):,.0f}원(+{R.뒷몫목표:g}%)")
    if 센:
        쓰기(줄)
        print(f"\n  {센}건 기록 → {LOG}")
        print(f"  ⚠️ 사면서 **매도 주문을 둘로 나눠** 걸어라 — "
              f"{_몫말(R.몫들[0][0])} +{R.앞몫목표:g}%, {_몫말(R.몫들[1][0])} +{R.뒷몫목표:g}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
