#!/usr/bin/env python3
r"""
collect_news_hist.py — **규칙 후보마다 신호 직전 7일 기사 제목을 받는다 (구글 뉴스 RSS · 날짜 범위)** (2026-10-21 신설)

왜: 사용자 10/21 「다른 경제쪽 받을 수 있는 곳 없어?」 → 「진행해보자.」
    네이버 금융 종목뉴스는 정확히 1년치뿐 · 네이버 검색 API 는 신규 신청이 막혔다 ([[news-sources-blocked]]).
    구글 뉴스 RSS 는 검색어에 `after:YYYY-MM-DD before:YYYY-MM-DD` 를 붙이면 옛 기사를 준다(10/21 실측 · 키 불필요).

입력: data/_labs/news_events.jsonl  (gate7 ONLY=NEWSCUT NEWSDUMP=1 이 만든다 · {code, 이름, 날})
출력: data/_labs/news_hist.jsonl    ({code, 이름, 날, 제목:[[제목, 언론], ...], 원건수}) — 10/21 첫 178줄은 제목만(옛 꼴) — 이어 받기(이미 받은 줄은 건너뜀)

규칙
- 기간 = 신호 날 7일 전 ~ 신호 날(그날 저녁 기사까지 · 다음 날 08:55 판단 전에 볼 수 있는 것). pubDate 로 한 번 더 자른다
- 제목에 회사 이름이 있어야 한다 · 이름 바로 뒤가 한글이면 조사(은는이가…)일 때만 (quant_n34._소식 과 같은 거르기)
- ⚠️ 이름은 지금 이름이다 — 옛날에 이름이 달랐던 종목은 덜 받힌다
- 요청 간격 4초 · 구글이 막으면(503) 2분부터 두 배씩 쉬고 이어 받는다 · 본문은 안 받는다(제목만)

쓰는 법:
    python scripts\collect_news_hist.py            # 전부(이어 받기)
    python scripts\collect_news_hist.py --최대 30   # 시험으로 30건만
"""
import argparse
import datetime as dt
import email.utils
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
_D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_입력 = os.path.join(_D, "_labs", "news_events.jsonl")
_출력 = os.path.join(_D, "_labs", "news_hist.jsonl")
_H = {"User-Agent": "Mozilla/5.0"}
_조사 = set("은는이가을를의에와과도로만")


def 이름맞나(이름, 제):
    for m in re.finditer(re.escape(이름), 제):
        뒤 = 제[m.end():m.end() + 1]
        if not 뒤 or not ("가" <= 뒤 <= "힣") or 뒤 in _조사:
            return True
    return False


def 받기(이름, 날8):
    끝 = dt.date(int(날8[:4]), int(날8[4:6]), int(날8[6:8]))
    시작 = 끝 - dt.timedelta(days=7)
    q = f'"{이름}" after:{시작.isoformat()} before:{(끝 + dt.timedelta(days=1)).isoformat()}'
    u = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
    with urllib.request.urlopen(urllib.request.Request(u, headers=_H), timeout=25) as r:
        t = r.read().decode("utf-8", errors="replace")
    items = re.findall(r"<item>(.*?)</item>", t, re.S)
    out = []
    for it in items:
        m = re.search(r"<title>(.*?)</title>", it, re.S)
        p = re.search(r"<pubDate>(.*?)</pubDate>", it)
        if not m:
            continue
        제 = m.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
        제 = re.sub(r"\s+-\s+[^-]+$", "", 제).strip()      # 끝의 「 - 언론사」 떼기
        if p:
            try:
                d = email.utils.parsedate_to_datetime(p.group(1)).astimezone(dt.timezone(dt.timedelta(hours=9))).date()
                if not (시작 <= d <= 끝):
                    continue
            except (TypeError, ValueError):
                pass
        # 10/21 언론 이름도 남긴다 — 「모든 언론」 과 「경제·증권 언론만」 을 다시 안 받고 견주려고
        #    (사용자 「기사를 경제·증권 언론으로 좁히는게 나아? … 아니면 구글로 괜찮아?」 → 넓게 받고 언론을 적어 둔다)
        s = re.search(r"<source[^>]*>(.*?)</source>", it, re.S)
        언 = (s.group(1).strip() if s else "")
        if 이름맞나(이름, 제) and 제 not in [z[0] for z in out]:
            out.append([제, 언])
    return out, len(items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--최대", type=int, default=0)
    a = ap.parse_args()
    ev = [json.loads(z) for z in io.open(_입력, encoding="utf-8") if z.strip()]
    한 = set()
    if os.path.exists(_출력):
        for z in io.open(_출력, encoding="utf-8"):
            try:
                j = json.loads(z)
                한.add((j["code"], j["날"]))
            except (ValueError, KeyError):
                pass
    남 = [e for e in ev if (e["code"], e["날"]) not in 한 and e.get("이름")]
    if a.최대:
        남 = 남[:a.최대]
    print(f"{dt.datetime.now():%m-%d %H:%M} 후보 {len(ev):,} · 이미 {len(한):,} · 받을 것 {len(남):,} · 이름 없음 {sum(1 for e in ev if not e.get('이름')):,}", flush=True)
    실패 = 0
    # ⚠️ 10/21 첫 판: 1초 간격으로 178건째에 구글이 503(잠시 그만)을 줬고 30번 실패로 멈췄다
    #    ⇒ 간격 4초 · 503/429 면 2분부터 두 배씩(최대 30분) 쉬고 같은 건을 다시 · 쉰 시간이 합쳐 4시간을 넘으면 멈춘다
    쉼합 = 0
    with io.open(_출력, "a", encoding="utf-8") as fo:
        for k, e in enumerate(남, 1):
            r = None
            쉼 = 120
            while r is None:
                try:
                    r = 받기(e["이름"], e["날"])
                except Exception as ex:  # noqa: BLE001
                    막힘 = ("503" in str(ex)) or ("429" in str(ex))
                    if not 막힘:
                        print(f"   실패 {e['code']} {e['날']}: {ex}", flush=True)
                        break
                    if 쉼합 >= 4 * 3600:
                        print(f"🛑 구글이 4시간 넘게 막았다 — 멈춘다 · 받은 것 {k - 1:,}/{len(남):,}", flush=True)
                        print(f"{dt.datetime.now():%m-%d %H:%M} ===== 기사 받기 끝 · 실패 {실패} =====", flush=True)
                        return
                    print(f"{dt.datetime.now():%m-%d %H:%M}   막힘({ex}) — {쉼 // 60}분 쉬고 다시 · 지금까지 {k - 1:,}/{len(남):,}", flush=True)
                    time.sleep(쉼)
                    쉼합 += 쉼
                    쉼 = min(쉼 * 2, 1800)
            if r is None:
                실패 += 1
                if 실패 >= 30:
                    print("🛑 막힘이 아닌 실패 30건 — 멈춘다", flush=True)
                    break
                continue
            fo.write(json.dumps({"code": e["code"], "이름": e["이름"], "날": e["날"], "제목": r[0], "원건수": r[1]}, ensure_ascii=False) + "\n")
            fo.flush()
            if k % 100 == 0:
                print(f"{dt.datetime.now():%m-%d %H:%M}   {k:,}/{len(남):,} · 실패 {실패}", flush=True)
            time.sleep(4.0)
    print(f"{dt.datetime.now():%m-%d %H:%M} ===== 기사 받기 끝 · 실패 {실패} =====", flush=True)


if __name__ == "__main__":
    main()
