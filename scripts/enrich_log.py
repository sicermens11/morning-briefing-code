#!/usr/bin/env python3
r"""
enrich_log.py — 픽마다 **서술 전용 11개 값**을 일일 로그에 붙인다

⚠️⚠️ **왜 필요한가** (2026-08-28 신설).
   서술 전용 11개(공매도·외국인지분율추이·분기6개·당좌비율·상대강도·어닝서프라이즈·
   의견추이·등급변경·후보간중복·신고가돌파·선물원자재)는 **점수에 반영되지 않는다.**
   그건 옳다 — "이게 좋으면 오른다"가 확인된 적이 없다.
   그런데 **값이 어디에도 안 쌓이고 있었다.** 그날 글로 나갔다가 증발했다.
   그러면 넉 달이 지나도 "당좌비율이 높은 픽이 실제로 더 올랐나"를 계산할 수 없다.
   **점수화 이전에 기록이 먼저다.** 이 스크립트가 그 기록을 만든다.

⚠️ **모델을 거치지 않는다.** 값은 이미 `data\snapshots\<날짜>\`에 있다. 모델에게
   옮겨 적게 하면 토큰이 들고 옮기다 틀린다. 스크립트가 직접 읽어 붙인다.

⚠️ **점수·등급을 바꾸지 않는다.** `features`라는 새 칸에만 쓴다. 기존 필드는 손대지 않는다.
   배점은 표본이 쌓이고 상관이 확인된 뒤의 일이다(AGENDA A-핵심).

쓰는 법:
    python scripts\enrich_log.py                 # 가장 최근 날짜
    python scripts\enrich_log.py --date 2026-08-28
    python scripts\enrich_log.py --all           # 스냅샷이 있는 날 전부 (소급)
"""
import argparse
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
SNAP = os.path.join(_BASE, "data", "snapshots")


try:
    from fetch_consensus import change_for as _consensus_change, load_history as _chist
except Exception:  # noqa: BLE001
    _consensus_change = _chist = None


def _load(pat, date):
    """그날 스냅샷 중 이름에 `pat`이 든 첫 파일."""
    for f in sorted(glob.glob(os.path.join(SNAP, date, f"*{pat}*"))):
        try:
            with io.open(f, encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:  # noqa: BLE001
            pass
    return {}


def _num(x):
    """`"1,234"` · `"-0.5%"` 같은 문자열도 숫자로. 못 바꾸면 None."""
    if isinstance(x, (int, float)):
        return x
    s = str(x or "").replace(",", "").replace("%", "").replace("+", "").strip()
    if s in ("", "-", "N/A", "없음"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _last(seq):
    """뒤에서부터 처음 나오는 숫자. 분기 표의 마지막 칸은 `-`인 경우가 많다."""
    for x in reversed(list(seq or [])):
        v = _num(x)
        if v is not None:
            return v
    return None


def _krx(date):
    r"""**발굴일 기준 KRX 전종목 시세.** 추가 호출 0회 — `fetch_krx.py`가 이미 받아 뒀다.

    ⚠️⚠️ **그날 파일이 아니라 「직전 거래일」 파일을 본다.** 브리핑은 08:00 개장 전에
       돌고, 발굴가는 **직전 거래일 종가**다. 그날 파일을 찾으면 아직 없거나(개장 전)
       엉뚱한 날 값이 붙는다 — 실제로 08-31 픽에 시총이 하나도 안 붙었다.
    ⚠️ 캐시에 있는 날짜 중 **그 날짜보다 앞선 가장 가까운 날**을 쓴다. 휴장·수집 실패로
       하루씩 비는 경우가 있어 "하루 전"으로 고정하면 놓친다.
    """
    d = date.replace("-", "")
    보관 = sorted(os.path.basename(x)[:-5]
                for x in glob.glob(os.path.join(_BASE, "data", "krx-daily", "*.json")))
    앞선 = [x for x in 보관 if x < d]
    if not 앞선:
        return {}
    f = os.path.join(_BASE, "data", "krx-daily", f"{앞선[-1]}.json")
    if not os.path.exists(f):
        return {}
    try:
        with io.open(f, encoding="utf-8") as fp:
            return json.load(fp).get("종목") or {}
    except Exception:  # noqa: BLE001
        return {}


def _섹터색인():
    r"""가치사슬맵에서 **종목명 → 섹터**. 픽에 섹터를 붙여 **섹터별 성과**를 볼 수 있게."""
    idx, sec = {}, None
    f = os.path.join(_BASE, "data", "value-chain-map.md")
    if not os.path.exists(f):
        return idx
    for line in io.open(f, encoding="utf-8-sig"):
        line = line.strip()
        if line.startswith("### "):
            sec = line[4:].strip()
        elif sec and line.startswith("`") and " OR " in line:
            for nm in line.strip("`").split("[")[0].split(" OR "):
                nm = nm.strip().strip('"').strip()
                if nm:
                    idx.setdefault(nm, sec)
    return idx


def _뉴스빈도(name, date):
    r"""그날 받은 섹터 뉴스에서 **그 종목 이름이 제목에 몇 번 나오나.**

    ⚠️⚠️ 갭②(정보갭)는 "언론이 이 재료와 종목을 아직 연결 안 지었나"인데, 지금은
       **모델이 눈으로 보고 판정**한다. 이 값은 그걸 **숫자로 재는 대리지표**다 —
       0건이면 진짜 안 퍼진 것이고, 여러 건이면 이미 퍼진 것이다.
    ⚠️ 완전하지 않다. **우리가 받은 섹터 뉴스 안에서만** 센다. 전체 언론이 아니다.
       그래서 점수로 쓰지 않고 기록만 한다 — 나중에 갭② 판정과 대조할 재료다.
    """
    tot = 0
    for f in glob.glob(os.path.join(SNAP, date, "*sector_news*")):
        try:
            with io.open(f, encoding="utf-8") as fp:
                d = json.load(fp)
        except Exception:  # noqa: BLE001
            continue
        for arts in (d.get("섹터별뉴스") or {}).values():
            tot += sum(1 for a in (arts or []) if name and name in str(a.get("제목", "")))
    return tot


def features_for(code, stock, ta, date, chist=None):
    """픽 하나의 `features`. **없으면 그 키를 넣지 않는다** — 0으로 채우지 않는다.

    ⚠️ 빈 값을 0으로 채우면 나중에 상관을 잴 때 "값이 0인 픽"과 "못 잰 픽"이
       섞인다. 그러면 계산이 통째로 거짓말이 된다.
    """
    f = {}
    v = stock.get("공매도") or {}
    if v.get("최근5일평균pct") is not None:
        f["공매도_5일평균pct"] = _num(v.get("최근5일평균pct"))
        f["공매도_직전평균pct"] = _num(v.get("직전평균pct"))
        f["공매도_추세"] = v.get("추세")

    v = stock.get("외국인지분율추이") or {}
    if v.get("변화pct_p") is not None:
        f["외국인지분율_변화pct_p"] = _num(v.get("변화pct_p"))
        f["외국인지분율_증가일비율"] = v.get("증가일비율")

    v = stock.get("재무3개년") or {}
    for src, dst in (("당좌비율", "당좌비율"), ("부채비율", "부채비율_연간"),
                     ("영업이익률", "영업이익률_연간"), ("순이익률", "순이익률_연간"),
                     ("ROE", "ROE_연간"), ("PER", "PER"), ("PBR", "PBR")):
        n = _last(v.get(src))
        if n is not None:
            f[dst] = n

    v = stock.get("분기6개") or {}
    for src, dst in (("영업이익률", "영업이익률_최근분기"),
                     ("순이익률", "순이익률_최근분기"),
                     ("부채비율", "부채비율_최근분기")):
        n = _last(v.get(src))
        if n is not None:
            f[dst] = n
    # ⚠️ **분기 편차**가 요점이다. 연간만 보면 매끄러워 보이는 회사가
    #    분기로는 들쭉날쭉한 경우가 있다(2026-08-28 안랩: 24.98 → 3.26 → 7.55).
    ops = [x for x in (_num(y) for y in (v.get("영업이익률") or [])) if x is not None]
    if len(ops) >= 3:
        f["영업이익률_분기편차"] = round(max(ops) - min(ops), 2)

    v = stock.get("수급10일") or []
    if v:
        fo = sum(x for x in (_num(r.get("외국인순매수수량")) for r in v) if x is not None)
        it = sum(x for x in (_num(r.get("기관순매수수량")) for r in v) if x is not None)
        f["외국인_10일합"] = int(fo)
        f["기관_10일합"] = int(it)

    if (stock.get("컨센서스") or {}).get("error"):
        f["컨센서스"] = "커버리지없음"
    elif stock.get("컨센서스"):
        f["컨센서스"] = "있음"

    # ⚠️ **컨센서스 변화** — 네이버는 현재값만 주므로 `fetch_consensus.py`가 매일 쌓은
    #    이력에서 직전 관측과 비교해 만든다. 이게 "투자의견 강등 −1"의 판정 근거다.
    #    간격일도 같이 남긴다 — "하루 만에 0.2 내렸다"와 "열흘 만에"는 무게가 다르다.
    if chist is not None:
        ch = _consensus_change(code, date, chist)
        if ch:
            f.update({("컨센_" + k): v for k, v in ch.items()})

    rs = ((ta.get("_상대강도") or {}).get("종목별") or {}).get(code) or {}
    for k in ("20일", "60일", "120일"):
        d = rs.get(k) or {}
        if isinstance(d, dict) and d.get("상대강도") is not None:
            f[f"상대강도_{k}"] = _num(d.get("상대강도"))

    t = ta.get(code) or {}
    for src, dst in (("rsi14", "RSI14"), ("atr14_pct", "ATR14pct"),
                     ("above_sma20", "20일선위"), ("dead_cross_macd", "MACD데드크로스")):
        if t.get(src) is not None:
            f[dst] = t.get(src)

    # 후보간중복 — 그 종목이 낀 쌍 중 **가장 높은 상관**. 조합의 속성이라 점수는 못 되지만
    # "둘 다 담으면 분산이 죽는다"를 나중에 검정할 재료는 된다.
    # ⚠️⚠️ **KRX 캐시에서 바로 붙인다** (2026-08-31 신설, 추가 호출 0회).
    #    전종목 2,767개를 매일 받아 두고도 픽에는 안 붙이고 있었다.
    #    · 시총 — **"작은 회사라 잘 오른 것"과 "신호가 좋아서 오른 것"을 구분**하려면 있어야 한다.
    #    · 거래대금 — 체결 가능성. 348억과 30억은 같은 신호라도 다른 이야기다.
    #    · 고가·저가 — 그날 장중에 어디까지 갔나(수익률은 종가만 본다).
    k = (_krx(date) or {}).get(code) or {}
    for src, dst in (("시총", "시가총액"), ("거래대금", "거래대금"),
                     ("고가", "발굴일고가"), ("저가", "발굴일저가"), ("종가", "발굴일종가")):
        if k.get(src) is not None:
            f[dst] = k[src]

    쌍 = ((ta.get("_후보간중복") or {}).get("쌍") or [])
    mine = [p.get("상관") for p in 쌍 if code in (p.get("쌍") or [])]
    if mine:
        f["후보간최대상관"] = max(x for x in mine if x is not None)
    return f


def enrich(date):
    if not os.path.isdir(os.path.join(SNAP, date)):
        return {"date": date, "ok": False, "이유": "스냅샷 폴더가 없다"}
    if not os.path.exists(LOG):
        return {"date": date, "ok": False, "이유": "일일 로그가 없다"}

    ta = _load("compute_ta", date)
    섹터색인 = _섹터색인()
    chist = _chist() if _chist else None
    stocks = {}
    for f in sorted(glob.glob(os.path.join(SNAP, date, "*fetch_stock*"))):
        try:
            with io.open(f, encoding="utf-8") as fp:
                stocks.update((json.load(fp).get("stocks") or {}))
        except Exception:  # noqa: BLE001
            pass

    lines, hit = [], 0
    with io.open(LOG, encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("date") == date:
                for p in (o.get("picks") or []):
                    ft = features_for(p["code"], stocks.get(p["code"]) or {}, ta, date, chist)
                    # ⚠️ 섹터·뉴스빈도는 **종목명**이 있어야 구한다. `features_for`는
                    #    코드만 받으므로 여기서 붙인다.
                    nm = p.get("name") or ""
                    if nm:
                        sec = 섹터색인.get(nm)
                        if sec:
                            ft["섹터"] = sec
                        ft["뉴스빈도_3일"] = _뉴스빈도(nm, date)
                    if ft:
                        p["features"] = ft
                        hit += 1
                # 그날 전체에 걸리는 것 — 종목별로 다르지 않아 픽이 아니라 날짜에 붙인다.
                if ta.get("_시장국면"):
                    o["시장국면_원본"] = ta["_시장국면"]
            lines.append(json.dumps(o, ensure_ascii=False))

    with io.open(LOG, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")
    return {"date": date, "ok": True, "붙인_픽": hit}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--all", action="store_true", help="스냅샷이 있는 날 전부 소급")
    a = ap.parse_args()
    days = ([os.path.basename(d.rstrip("\\/")) for d in sorted(glob.glob(os.path.join(SNAP, "*/")))]
            if a.all else [a.date or
                           os.path.basename(sorted(glob.glob(os.path.join(SNAP, "*/")))[-1]
                                            .rstrip("\\/"))])
    out = [enrich(d) for d in days]
    print(json.dumps(out if len(out) > 1 else out[0], ensure_ascii=False))
    sys.exit(0)
