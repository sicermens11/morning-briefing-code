#!/usr/bin/env python3
"""
compute_ta.py - morning-sector-briefing 강화-TA 기술지표 계산 스크립트 (2026-08-11 신설, DECISIONS.md 120차)
2026-08-21 확장(DECISIONS.md 137차): 거래량비율·지지저항·ATR14·캔들패턴3종 추가 — 전부 이미 받아오던
OHLCV(open/high/low/volume, 기존엔 close만 사용)에서 추가 호출 없이 계산. 서술전용, 점수·등급 미반영.

목적: SMA/RSI/볼린저밴드/MACD 등을 LLM이 수기로 계산하던 것을 대체 — 계산오류 제거.
의존성: Python 표준 라이브러리만 사용(pandas/numpy 등 외부 패키지 설치 불필요, 자동실행 sandbox에서
바로 동작 보장 목적).

2026-08-26 개편:
  ① `--codes 298040,079550` 모드 신설 — 스크립트가 가격이력을 **직접** 받는다.
     이전에는 모델이 OHLCV 배열을 손으로 파일에 옮겨 적었다(실측 12.9KB/회).
  ② 가격이력 100 → 약 250거래일 → **SMA120·SMA200** 계산 가능, 52주고점도 직접 계산.
  ③ **지지·저항 재설계** — 20일 최저/최고가는 지지선이 아니었다(실측 -33%짜리 값이 나옴).
     스윙 저점·고점을 묶어 현재가에서 **가장 가까운** 자리를 찾는 방식으로 바꿨다.

사용:
    run-py.ps1 -Script compute_ta.py -Args @('--codes','298040,079550')   ← 권장
    run-py.ps1 -Script compute_ta.py -Args @('--file','...json')          ← 폴백(직접조회 불가시)

입력(stdin 또는 --file, JSON): {
  "candidates": {
    "[종목코드]": {
      "rows": [{"date":"YYYYMMDD","open":.,"high":.,"low":.,"close":.,"volume":.}, ...],  // 순서 무관, 최소 40행 권장
      "current_price": 12345,      // 강화-P 응답의 price 필드 재사용(신규 호출 없음)
      "week52_high": 67890         // 강화-P 응답의 week52_high 필드 재사용(OHLCV로 계산 안 함 — 60~100일 데이터로는
                                    // 52주치를 계산할 수 없어 애초에 잘못된 설계였음, 2026-08-11에 이 방식으로 수정)
    }, ...
  }
}

출력(stdout, JSON): {
  "[종목코드]": {
    "insufficient_data": bool,       // true면 아래 필드는 전부 null (30거래일 미만)
    "sma20": float|null, "sma60": float|null,
    "golden_cross_sma": bool|null,   // 최근 5거래일 내 SMA20이 SMA60을 상향 돌파했는지(SMA60 계산 불가하면 null)
    "dead_cross_sma": bool|null,
    "rsi14": float|null,
    "bollinger": {"upper":float,"mid":float,"lower":float}|null,
    "macd": {"macd":float,"signal":float,"histogram":float}|null,
    "golden_cross_macd": bool|null,  // 최근 5거래일 내 MACD가 시그널선을 상향 돌파했는지
    "dead_cross_macd": bool|null,
    "week52_high_drawdown_pct": float|null,   // (current_price - week52_high) / week52_high * 100, 항상 <=0
    "above_sma20": bool|null,
    "volume_ratio": float|null,        // 오늘 거래량 / 최근20일 평균거래량(오늘 제외). 배수(1.0=평소와 동일)
    "resistance_20d": float|null,      // 최근 20거래일 최고가(오늘 포함)
    "support_20d": float|null,         // 최근 20거래일 최저가(오늘 포함)
    "atr14": float|null,               // 14일 평균진폭(Wilder), 원 단위
    "atr14_pct": float|null,           // atr14 / 최근종가 * 100
    "today_move_vs_atr": float|null,   // 오늘 |종가-전일종가| / atr14. 1.0=평소와 같은 폭, 클수록 평소보다 큰 움직임
    "candle": {
      "engulfing": "bullish"|"bearish"|null,   // 상승/하락 장악형(오늘 몸통이 어제 몸통을 반대방향으로 완전히 감쌈), 아니면 null
      "marubozu": "bullish"|"bearish"|null,    // 몸통이 당일 변동폭의 90%+ (꼬리 거의 없음), 아니면 null
      "doji": bool|null                          // 몸통이 당일 변동폭의 10% 이하
    }|null,
    "error": str|null
  }, ...
}
"""
import sys
import itertools
import json
import statistics as st
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://m.stock.naver.com/",
}

# 52주고점을 직접 계산하려면 250거래일이 필요하고, 휴장일을 감안해 달력 400일을 요청한다.
FETCH_CALENDAR_DAYS = 400
WEEK52_ROWS = 250


def fetch_rows(code: str):
    """네이버 일별시세에서 OHLCV를 직접 받는다. (2026-08-26 신설)

    ⚠️ 왜 만들었나 — 이전에는 이 데이터가 **API → 모델 컨텍스트 → 모델이 손으로 다시 출력 →
    파일 → 이 스크립트** 경로로 흘렀다. 2026-08-26 실행에서 모델이 써낸 `ta_in_0826.json`이
    12.9KB였다. 모델이 숫자 배열의 **복사 파이프** 노릇을 하고 있었던 것이고,
    브리핑 실행 시간은 출력 토큰에 정비례하므로(실측 약 70토큰/초) 그만큼 그대로 시간이다.
    여기서 직접 받으면 그 왕복이 통째로 사라지고 MCP 호출도 2회 줄어든다.

    부수 효과 — **52주고점이 정확해진다.** 시세 API의 `week52_high` 필드는 무상증자·액면분할을
    반영하지 않아, 2026-08-25 엘에스일렉트릭에서 907,000원(비조정)과 313,000원(조정)이 갈렸다.
    그날은 모델이 이상함을 알아채고 손으로 바로잡았지만, 못 알아채면 등급조정④가 잘못 걸린다.
    이 시계열은 조정가 기준이라 같은 기준으로 계산된다.
    """
    end = datetime.now(KST)
    start = end - timedelta(days=FETCH_CALENDAR_DAYS)
    url = ("https://api.finance.naver.com/siseJson.naver"
           f"?symbol={code}&requestType=1&startTime={start:%Y%m%d}"
           f"&endTime={end:%Y%m%d}&timeframe=day")
    raw = urllib.request.urlopen(
        urllib.request.Request(url, headers=_HEADERS), timeout=25
    ).read().decode("utf-8", errors="replace")
    # 응답이 파이썬 리스트 리터럴 꼴(작은따옴표)이라 JSON으로 바꿔 읽는다. 첫 행은 헤더.
    parsed = [r for r in json.loads(raw.replace("'", '"'))[1:] if isinstance(r, list)]
    return [{"date": str(r[0]), "open": r[1], "high": r[2],
             "low": r[3], "close": r[4], "volume": r[5]} for r in parsed]


def build_payload_from_codes(codes):
    """`--codes`용 payload 조립. 종목별로 독립 실패한다(한 종목이 죽어도 나머지는 계산)."""
    cands = {}
    for code in codes:
        try:
            rows = fetch_rows(code)
            if not rows:
                cands[code] = {"rows": [], "_fetch_error": "가격이력 0행"}
                continue
            cands[code] = {
                "rows": rows,
                "current_price": rows[-1]["close"],
                "week52_high": max(r["high"] for r in rows[-WEEK52_ROWS:]),
                "_week52_source": f"조정 시계열 {min(len(rows), WEEK52_ROWS)}행 최고가",
            }
        except Exception as e:
            cands[code] = {"rows": [], "_fetch_error": f"{type(e).__name__}: {e}"}
    return {"candidates": cands}


def sort_rows_ascending(rows):
    return sorted(rows, key=lambda r: r["date"])


def sma_series(closes, period):
    """각 인덱스 i에 대해 closes[i-period+1..i]의 평균. 앞쪽 period-1개는 None."""
    out = [None] * len(closes)
    if len(closes) < period:
        return out
    running_sum = sum(closes[:period])
    out[period - 1] = running_sum / period
    for i in range(period, len(closes)):
        running_sum += closes[i] - closes[i - period]
        out[i] = running_sum / period
    return out


def ema_series(values, period):
    """values(None 없는 리스트)로 EMA 시리즈 계산, 첫 period개 평균으로 시드. 앞쪽 period-1개는 None."""
    out = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def recent_cross(fast_series, slow_series, lookback=5):
    """최근 lookback거래일 안에서 fast가 slow를 상향/하향 돌파했는지 확인.
    반환: (golden, dead) 각각 bool|None. 계산불가하면 (None, None)."""
    n = len(fast_series)
    valid_idxs = [i for i in range(n) if fast_series[i] is not None and slow_series[i] is not None]
    if len(valid_idxs) < 2:
        return None, None
    golden = False
    dead = False
    window_start = max(0, len(valid_idxs) - lookback - 1)
    window = valid_idxs[window_start:]
    for j in range(1, len(window)):
        prev_i, cur_i = window[j - 1], window[j]
        prev_diff = fast_series[prev_i] - slow_series[prev_i]
        cur_diff = fast_series[cur_i] - slow_series[cur_i]
        if prev_diff <= 0 and cur_diff > 0:
            golden = True
        if prev_diff >= 0 and cur_diff < 0:
            dead = True
    return golden, dead


def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = [0.0] * len(closes)
    losses = [0.0] * len(closes)
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains[i] = max(diff, 0.0)
        losses[i] = max(-diff, 0.0)
    avg_gain = sum(gains[1:period + 1]) / period
    avg_loss = sum(losses[1:period + 1]) / period
    for i in range(period + 1, len(closes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_bollinger(closes, period=20, num_std=2):
    if len(closes) < period:
        return None
    window = closes[-period:]
    mid = sum(window) / period
    variance = sum((x - mid) ** 2 for x in window) / period
    std = variance ** 0.5
    return {
        "mid": round(mid, 2),
        "upper": round(mid + num_std * std, 2),
        "lower": round(mid - num_std * std, 2),
    }


def compute_macd(closes, fast=12, slow=26, signal=9, lookback=5):
    """MACD line = EMA(fast) - EMA(slow) (인덱스 정렬됨, 둘 다 None인 구간은 None).
    signal line = EMA(signal) of MACD line(비-None 구간만)."""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    macd_line_full = [None] * len(closes)
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line_full[i] = ema_fast[i] - ema_slow[i]
    first_valid = next((i for i, v in enumerate(macd_line_full) if v is not None), None)
    if first_valid is None:
        return None, None, None
    macd_values_only = macd_line_full[first_valid:]
    signal_partial = ema_series(macd_values_only, signal)
    signal_line_full = [None] * len(closes)
    for offset, v in enumerate(signal_partial):
        signal_line_full[first_valid + offset] = v
    latest_macd = macd_line_full[-1]
    latest_signal = signal_line_full[-1]
    if latest_macd is None or latest_signal is None:
        return None, None, None
    result = {
        "macd": round(latest_macd, 2),
        "signal": round(latest_signal, 2),
        "histogram": round(latest_macd - latest_signal, 2),
    }
    golden, dead = recent_cross(macd_line_full, signal_line_full, lookback)
    return result, golden, dead


def compute_atr14(highs, lows, closes, period=14):
    """Wilder 평활화 방식 ATR. True Range = max(고-저, |고-전일종가|, |저-전일종가|)."""
    n = len(closes)
    if n < period + 1:
        return None
    tr = [None] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    avg = sum(tr[1:period + 1]) / period
    for i in range(period + 1, n):
        avg = (avg * (period - 1) + tr[i]) / period
    return round(avg, 2)


def compute_volume_ratio(volumes, window=20):
    """오늘 거래량 / 최근window일 평균거래량(오늘 제외)."""
    n = len(volumes)
    if n < window + 1:
        return None
    today = volumes[-1]
    baseline = volumes[-(window + 1):-1]
    avg = sum(baseline) / window
    if avg == 0:
        return None
    return round(today / avg, 2)


def compute_support_resistance(highs, lows, window=20):
    """최근 N거래일의 최고/최저. ⚠️ 이건 **레인지**지 지지·저항선이 아니다.

    2026-08-26까지 이 값을 브리핑에 "지지선/저항선"으로 내보내고 있었는데, 실측에서
    효성중공업 지지선이 1,834,000원(현재가 대비 **-33%**)으로 나왔다. 계산은 맞았다 —
    07-30 패닉 저점이 20거래일 안에 들어 있었을 뿐이다. 4주 전 최저가는 사실이지만
    **오늘 진입 판단에는 못 쓴다.** 진짜 지지선은 아래 `swing_levels`가 계산한다.
    이 필드는 "최근 변동 범위"로만 쓴다.
    """
    if len(highs) < window:
        return None, None
    return round(max(highs[-window:]), 2), round(min(lows[-window:]), 2)


def _swing_pivots(highs, lows, k=2):
    """좌우 k봉보다 낮으면(높으면) 스윙 저점(고점). 되돌림이 실제로 일어난 자리다."""
    lo, hi = [], []
    for i in range(k, len(lows) - k):
        if lows[i] == min(lows[i - k:i + k + 1]):
            lo.append((i, lows[i]))
        if highs[i] == max(highs[i - k:i + k + 1]):
            hi.append((i, highs[i]))
    return lo, hi


def _cluster(pivots, tol_pct):
    """가까운 스윙끼리 묶는다. 같은 자리를 여러 번 눌렀으면 그만큼 단단한 선이다."""
    out = []
    for idx, price in sorted(pivots, key=lambda x: x[1]):
        if out and (price - out[-1]["_base"]) / out[-1]["_base"] * 100 <= tol_pct:
            c = out[-1]
            c["_ps"].append(price)
            c["_idx"].append(idx)
        else:
            out.append({"_base": price, "_ps": [price], "_idx": [idx]})
    for c in out:
        c["level"] = round(sum(c["_ps"]) / len(c["_ps"]), 2)
        c["touches"] = len(c["_ps"])
        c["_last"] = max(c["_idx"])
    return out


def swing_levels(dates, highs, lows, current_price, atr14_pct, window=120):
    """현재가에서 **가장 가까운** 지지·저항을 찾는다.

    왜 최저/최고가가 아니라 이 방식인가: 진입 판단에 필요한 건 "언젠가 찍은 바닥"이 아니라
    **"지금 여기서 아래로 밀리면 어디서 받쳐지나"**다. 최저가 방식은 급락이 한 번만 있어도
    수십 % 아래를 가리켜 손절선으로도 목표가로도 못 쓴다(2026-08-26 실측 -33%).

    - 스윙 저점·고점을 뽑아 서로 가까운 것끼리 묶고, 현재가 기준 바로 아래/위 묶음을 고른다.
    - 묶는 폭은 종목 변동성에 비례시킨다(ATR 기준). 하루에 9% 움직이는 종목과 3% 움직이는
      종목에 같은 폭을 쓰면 한쪽은 전부 따로 놀고 한쪽은 전부 뭉친다.
    - 되돌림 계산에는 **최근 120거래일만** 쓴다. 가격이력을 200일로 늘려도(SMA120/200 계산용)
      1년 전 자리가 오늘 지지선으로 올라오지 않게 하려는 것이다.
    """
    if current_price is None or len(lows) < 30:
        return None
    h, l, d = highs[-window:], lows[-window:], dates[-window:]
    tol = 2.0 if not atr14_pct else max(1.0, min(3.0, atr14_pct * 0.35))
    lo_pv, hi_pv = _swing_pivots(h, l, k=2)

    def pick(clusters, below, min_touches=1):
        # 현재가에 붙어 있는 묶음(±0.2%)은 제외한다 — "지지선이 현재가"는 정보가 아니다.
        if below:
            cand = [c for c in clusters
                    if c["level"] < current_price * 0.998 and c["touches"] >= min_touches]
        else:
            cand = [c for c in clusters
                    if c["level"] > current_price * 1.002 and c["touches"] >= min_touches]
        if not cand:
            return None
        c = max(cand, key=lambda x: x["level"]) if below else min(cand, key=lambda x: x["level"])
        return {
            "level": c["level"],
            "touches": c["touches"],
            "last_touch": d[c["_last"]],
            "dist_pct": round((c["level"] - current_price) / current_price * 100, 2),
        }

    lo_cl, hi_cl = _cluster(lo_pv, tol), _cluster(hi_pv, tol)
    sup, res = pick(lo_cl, True), pick(hi_cl, False)
    # ⚠️ "가장 가까운 자리"와 "단단한 자리"는 다르다. 2026-08-26 효성중공업에서 최근접 저항이
    #    **5개월 전에 한 번 스친 자리**(+0.8%, 터치 1회)로 나왔다 — 사실이지만 그걸 저항으로
    #    믿고 목표가를 잡을 근거는 약하다. 두 번 이상 눌린 자리를 따로 내보내 모델이 고르게 한다.
    sup2, res2 = pick(lo_cl, True, 2), pick(hi_cl, False, 2)
    return {
        "tolerance_pct": round(tol, 2),
        "lookback_days": len(h),
        "support": sup,                 # 현재가 바로 아래(터치 1회여도 포함)
        "resistance": res,              # 현재가 바로 위
        "support_strong": sup2,         # 2회 이상 눌린 자리 중 가장 가까운 것(없으면 null)
        "resistance_strong": res2,
        # 가까운 자리가 없으면 그 사실 자체가 판단 재료다 — 손절 기준을 잡을 데가 없다는 뜻.
        "support_far": bool(sup and abs(sup["dist_pct"]) > 10),
        "resistance_far": bool(res and abs(res["dist_pct"]) > 10),
    }


def compute_candle(rows_sorted):
    """rows_sorted: 오름차순 정렬된 원본 rows(오늘이 마지막). open/high/low/close 사용."""
    if len(rows_sorted) < 2:
        return None
    today, yday = rows_sorted[-1], rows_sorted[-2]
    o, c, h, l = float(today["open"]), float(today["close"]), float(today["high"]), float(today["low"])
    day_range = h - l
    body = abs(c - o)

    engulfing = None
    yo, yc = float(yday["open"]), float(yday["close"])
    y_bullish = yc > yo
    t_bullish = c > o
    if t_bullish != y_bullish and t_bullish is not None:
        # 오늘 몸통이 어제 몸통을 완전히 감싸는지
        today_hi, today_lo = max(o, c), min(o, c)
        yday_hi, yday_lo = max(yo, yc), min(yo, yc)
        if today_hi >= yday_hi and today_lo <= yday_lo and body > 0:
            engulfing = "bullish" if t_bullish else "bearish"

    marubozu = None
    doji = None
    if day_range > 0:
        ratio = body / day_range
        if ratio >= 0.9:
            marubozu = "bullish" if c >= o else "bearish"
        elif ratio <= 0.1:
            doji = True
    if doji is None and day_range > 0:
        doji = False

    return {"engulfing": engulfing, "marubozu": marubozu, "doji": doji}


def compute_one(payload):
    try:
        rows = payload.get("rows", [])
        current_price = payload.get("current_price")
        week52_high = payload.get("week52_high")

        if len(rows) < 30:
            # 가져오다 실패한 것과 데이터가 원래 적은 것을 구분해서 알린다 — 대응이 다르다.
            why = payload.get("_fetch_error") or f"데이터 {len(rows)}행, 30거래일 미만"
            return {"insufficient_data": True, "error": why}

        sorted_rows = sort_rows_ascending(rows)
        closes = [float(r["close"]) for r in sorted_rows]
        highs = [float(r["high"]) for r in sorted_rows]
        lows = [float(r["low"]) for r in sorted_rows]
        volumes = [float(r.get("volume", 0)) for r in sorted_rows]
        dates = [str(r["date"]) for r in sorted_rows]

        atr14 = compute_atr14(highs, lows, closes, 14)
        atr14_pct = round(atr14 / closes[-1] * 100, 2) if atr14 and closes[-1] else None
        today_move_vs_atr = None
        if atr14 and len(closes) >= 2 and atr14 > 0:
            today_move_vs_atr = round(abs(closes[-1] - closes[-2]) / atr14, 2)
        volume_ratio = compute_volume_ratio(volumes, 20)
        resistance_20d, support_20d = compute_support_resistance(highs, lows, 20)
        candle = compute_candle(sorted_rows)

        levels = swing_levels(dates, highs, lows, current_price, atr14_pct)

        # 신고가 돌파 여부. (2026-08-26 신설)
        # ⚠️ 지금까지 52주고점 **대비 하락률**만 봤다 — "얼마나 빠졌나"는 알아도
        #    **"고점을 뚫었나"는 몰랐다.** 둘은 정반대 국면인데 같은 숫자로만 봤던 것이다.
        newhigh = None
        if current_price is not None and len(highs) >= 60:
            for win, label in ((250, "52주"), (120, "6개월"), (60, "3개월")):
                if len(highs) >= win:
                    prior = max(highs[-win:-1]) if len(highs) > win else max(highs[:-1])
                    if prior and current_price >= prior:
                        newhigh = {"구간": label, "직전최고": round(prior, 2),
                                   "현재가": current_price}
                        break

        sma20_series = sma_series(closes, 20)
        sma60_series = sma_series(closes, 60)
        sma20_latest = sma20_series[-1]
        sma60_latest = sma60_series[-1]
        golden_cross_sma, dead_cross_sma = recent_cross(sma20_series, sma60_series, lookback=5)
        # SMA120·200은 데이터가 충분할 때만 나온다(각 120·200거래일 필요).
        # 이전에는 가격이력이 100일 상한이라 아예 계산할 수 없었다 — MCP 도구의 1회 요청
        # 최대치가 100이었기 때문이고, 직접 호출로 바꾸면서 그 제약이 사라졌다.
        sma120_latest = sma_series(closes, 120)[-1]
        sma200_latest = sma_series(closes, 200)[-1]

        rsi14 = compute_rsi(closes, 14)
        bollinger = compute_bollinger(closes, 20, 2)
        macd_result, golden_cross_macd, dead_cross_macd = compute_macd(closes, 12, 26, 9, lookback=5)

        week52_drawdown = None
        if current_price is not None and week52_high:
            week52_drawdown = round((current_price - week52_high) / week52_high * 100, 2)

        above_sma20 = None
        if current_price is not None and sma20_latest is not None:
            above_sma20 = current_price >= sma20_latest

        return {
            "insufficient_data": False,
            "rows_used": len(sorted_rows),
            "sma20": round(sma20_latest, 2) if sma20_latest is not None else None,
            "sma60": round(sma60_latest, 2) if sma60_latest is not None else None,
            "sma120": round(sma120_latest, 2) if sma120_latest is not None else None,
            "sma200": round(sma200_latest, 2) if sma200_latest is not None else None,
            "golden_cross_sma": golden_cross_sma,
            "dead_cross_sma": dead_cross_sma,
            "rsi14": rsi14,
            "bollinger": bollinger,
            "macd": macd_result,
            "golden_cross_macd": golden_cross_macd,
            "dead_cross_macd": dead_cross_macd,
            "week52_high_drawdown_pct": week52_drawdown,
            "above_sma20": above_sma20,
            "volume_ratio": volume_ratio,
            # ⚠️ 아래 두 개는 "최근 20일 레인지"다. **지지선·저항선으로 쓰지 않는다.**
            #    진입 판단용 선은 `levels`를 쓴다(2026-08-26 재설계).
            "range_20d_high": resistance_20d,
            "range_20d_low": support_20d,
            "resistance_20d": resistance_20d,   # 하위호환(구 필드명). 신규 서술엔 쓰지 말 것.
            "support_20d": support_20d,         # 하위호환(구 필드명). 신규 서술엔 쓰지 말 것.
            "levels": levels,
            "atr14": atr14,
            "atr14_pct": atr14_pct,
            "today_move_vs_atr": today_move_vs_atr,
            "candle": candle,
            "신고가돌파": newhigh,
            "error": None,
        }
    except Exception as e:
        return {"insufficient_data": True, "error": f"계산오류: {type(e).__name__}: {e}"}


def _read_input() -> str:
    """입력 소스 결정: `--file <경로>`가 있으면 그 파일(UTF-8), 없으면 stdin.

    2026-08-21 추가 — Windows(PowerShell) 환경 이식용. PowerShell에는 bash heredoc이 없어
    긴 JSON을 stdin으로 밀어넣을 때 인용부호·인코딩이 깨지는 사고가 잦다. 파일 경유로
    받으면 그 문제가 원천 차단된다. 기존 stdin 방식은 그대로 유지되므로 Cowork(리눅스
    샌드박스) 쪽 호출은 아무 영향 없음.
    """
    argv = sys.argv[1:]
    if "--file" in argv:
        path = argv[argv.index("--file") + 1]
        # utf-8-sig: PowerShell의 Set-Content/Out-File은 UTF-8 BOM을 붙이는 경우가 많다.
        # 그냥 utf-8로 읽으면 BOM이 본문 첫 글자로 남아 json.loads가 곧바로 실패한다.
        with open(path, "r", encoding="utf-8-sig") as fp:
            return fp.read()
    return sys.stdin.read()


def market_regime() -> dict:
    """코스피가 20일선 대비 어디에 있나. (2026-08-26 신설, 추가 조회 1회 약 0.2초)

    ⚠️ **점수·등급에 반영하지 않는다. 지금은 기록과 서술 전용이다.**

    왜 재나 — 2026-08-26 백테스트에서 **유일하게 유의에 가까운 축**이 이것이었다:
      코스피가 20일선 **아래**일 때 발굴한 픽: 19건 중 14건 플러스, 평균 **+8.8%p**
      코스피가 20일선 **위**일 때 발굴한 픽: **3건 전부 마이너스**, 평균 **-7.5%p** (p=0.064)

    논리도 맞는다 — 시장이 눌려 있을 때 "재료 있는데 안 움직인 종목"은 진짜 미반영이고,
    시장이 과열인데 안 움직였다면 **안 움직일 이유가 있는 것**일 수 있다.

    ⚠️ **그런데 20일선 위 표본이 3건뿐이다.** 이걸로 등급조정 규칙을 만들면 3건에 시스템을
       맞추는 것이다. 그래서 지금은 **매일 값을 남겨 표본을 쌓는 단계**다.
       몇 주 뒤 `backtest_returns.py`로 검정해 점수 반영 여부를 정한다.
    """
    try:
        rows = fetch_rows("KOSPI")
        if len(rows) < 21:
            return {"error": "코스피 시계열 부족"}
        cl = [float(r["close"]) for r in rows]
        prev, sma20 = cl[-1], st.mean(cl[-20:])
        dev = round((prev / sma20 - 1) * 100, 2)
        band = ("과열(+3%↑)" if dev >= 3 else "위" if dev >= 0
                else "아래" if dev > -5 else "깊은 눌림(-5%↓)")
        return {
            "코스피": prev, "SMA20": round(sma20, 2), "기준일": rows[-1]["date"],
            "20일선대비pct": dev, "국면": band,
            "_서술지침": (
                "①시장 한눈에에 **한 줄 적는다**. 갭 판정이나 등급은 바꾸지 않는다.\n"
                "· 20일선 아래 → \"시장이 눌려 있어 '재료 있는데 안 움직임'이 미반영일 가능성이 높은 구간\"\n"
                "· 20일선 위(특히 +3%↑) → \"시장이 과열 구간이라, 재료가 있는데도 안 움직였다면 "
                "**안 움직일 이유가 있을 가능성**을 함께 본다 — 오늘 갭④ 해석의 신뢰도는 평소보다 낮다\"\n"
                "⚠️ 이 값으로 후보를 빼거나 등급을 낮추지 않는다. 표본이 22건뿐이라 아직 검정되지 않았다."),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def relative_strength(candidates: dict) -> dict:
    """지수 대비 상대강도. (2026-08-26 신설)

    ⚠️ 지금까지 **당일 동종업계 등락률**만 봤다. "최근 한 달간 지수보다 강했나"를 못 봤다.
       갭 전략이 고르는 종목은 **발굴 전 60일 수익률 중앙값이 -32.7%**(2026-08-26 실측)라
       구조적으로 역추세다. 그게 의도된 것인지 아닌지를 보려면 이 숫자가 필요하다.

    ⚠️ **점수·등급에 반영하지 않는다.** 2026-08-26 백테스트에서 모멘텀은 성과 차이를
       만들지 못했다(발굴 전 하락 중 +6.79%p vs 상승 중 +6.15%p). 서술·기록 전용이다.
    """
    try:
        k = fetch_rows("KOSPI")
        kc = [float(r["close"]) for r in k]
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    out = {}
    for code, data in candidates.items():
        rows = sort_rows_ascending(data.get("rows") or [])
        cl = [float(r["close"]) for r in rows]
        if len(cl) < 21 or len(kc) < 21:
            continue
        rec = {}
        for w in (20, 60, 120):
            if len(cl) > w and len(kc) > w:
                s = (cl[-1] / cl[-1 - w] - 1) * 100
                m = (kc[-1] / kc[-1 - w] - 1) * 100
                rec[f"{w}일"] = {"종목": round(s, 2), "코스피": round(m, 2),
                                 "상대강도": round(s - m, 2)}
        if rec:
            out[code] = rec
    return {"기준": "코스피 대비 초과수익률(%p)", "종목별": out,
            "_주의": "점수·등급 미반영. 서술·기록 전용이다."}


OVERLAP_WINDOW = 60
OVERLAP_HIGH = 0.70
OVERLAP_MID = 0.55


def candidate_overlap(candidates: dict) -> dict:
    """오늘 후보들끼리 얼마나 같이 움직이는지. (2026-08-26 신설)

    ⚠️ 왜 필요한가 — 후보를 여러 개 내면서 **서로 얼마나 겹치는지는 한 번도 안 봤다.**
       후보 둘이 다 전력인프라면 등급이 각각 🟢·🟡라도 **사실상 한 종목에 두 번 베팅**하는 것이다.
       분산이 됐다고 착각하기 쉬운데, 같이 오르고 같이 빠진다.

    ⚠️ **점수·등급에 반영하지 않는다.** 서술 전용이다 —
       "이 둘은 사실상 같은 베팅"이라고 알려주기만 하고, 무엇을 뺄지는 사람이 정한다.

    추가 조회 0회: `--codes` 모드가 이미 후보 전원의 250거래일 시계열을 받아왔다.
    """
    ser = {}
    for code, data in candidates.items():
        rows = sort_rows_ascending(data.get("rows") or [])
        cl = [float(r["close"]) for r in rows][-(OVERLAP_WINDOW + 1):]
        if len(cl) >= 30:
            ser[code] = [(cl[i] - cl[i - 1]) / cl[i - 1] for i in range(1, len(cl)) if cl[i - 1]]
    if len(ser) < 2:
        return {"판정": "표본부족", "_안내": "후보 2개 이상 + 각 30거래일 이상 필요"}

    n = min(len(v) for v in ser.values())
    ser = {k: v[-n:] for k, v in ser.items()}
    codes = sorted(ser)
    pairs = []
    for a, b in itertools.combinations(codes, 2):
        x, y = ser[a], ser[b]
        mx, my = st.mean(x), st.mean(y)
        num = sum((p - mx) * (q - my) for p, q in zip(x, y))
        dx = sum((p - mx) ** 2 for p in x) ** 0.5
        dy = sum((q - my) ** 2 for q in y) ** 0.5
        c = round(num / (dx * dy), 3) if dx and dy else 0.0
        level = ("높음" if c >= OVERLAP_HIGH else "보통" if c >= OVERLAP_MID else "낮음")
        pairs.append({"쌍": [a, b], "상관": c, "겹침": level})
    pairs.sort(key=lambda p: -p["상관"])
    worst = pairs[0]
    return {
        "표본거래일": n, "쌍": pairs,
        "최고상관": worst["상관"], "판정": worst["겹침"],
        "_해석": (f"상관 {OVERLAP_HIGH} 이상이면 **사실상 같은 베팅**이라 분산 효과가 거의 없다. "
                   f"{OVERLAP_MID}~{OVERLAP_HIGH}면 부분 중복. 그 미만이면 독립적이다. "
                   "⚠️ 점수·등급에는 반영하지 않는다 — 액션플랜에 한 줄 알리고 판단은 사람이 한다."),
    }


def main():
    argv = sys.argv[1:]
    if "--codes" in argv:
        # 권장 경로: 스크립트가 가격이력을 직접 받는다(모델이 배열을 옮겨 적지 않는다).
        codes = [c.strip() for c in argv[argv.index("--codes") + 1].split(",") if c.strip()]
        payload = build_payload_from_codes(codes)
    else:
        # 폴백 경로: 호출자가 rows를 통째로 넘긴다. 네이버가 막히거나 비상장·해외 종목처럼
        # 직접 조회가 안 되는 경우를 위해 남겨둔다.
        try:
            raw = _read_input()
        except Exception as e:
            print(json.dumps({"_fatal_error": f"입력 파일 읽기 실패: {e}"}, ensure_ascii=False))
            return
        try:
            payload = json.loads(raw)
        except Exception as e:
            print(json.dumps({"_fatal_error": f"입력 JSON 파싱 실패: {e}"}))
            return
    candidates = payload.get("candidates", {})
    result = {code: compute_one(data) for code, data in candidates.items()}
    if len(candidates) >= 2:
        result["_후보간중복"] = candidate_overlap(candidates)
    if "--codes" in argv:            # 직접조회 모드일 때만(폴백 경로는 네트워크가 없을 수 있다)
        result["_시장국면"] = market_regime()
        result["_상대강도"] = relative_strength(candidates)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()


