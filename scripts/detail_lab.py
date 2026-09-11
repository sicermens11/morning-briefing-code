#!/usr/bin/env python3
r"""
detail_lab.py — **공시 종류·시간대 · 수급 강도 · 신고가 · 연속신호** (2026-09-01 신설)

⚠️⚠️ **지금까지 뭉뚱그려 보던 것을 쪼갠다.**
```
공시 종류   지금은 「호재/악재」 두 덩어리다 → 계약·실적·특허·임상·자사주로 쪼갠다
시간대     지금은 「15:30 이후」 한 덩어리다 → 15:30~16 / 16~18 / 18시 이후로 쪼갠다
수급 강도   지금은 「순매수 양수인가」만 본다 → **금액 ÷ 시총**으로 세기를 잰다
신고가     52주 고가 대비 위치 — 신고가 돌파가 신호인가
연속 신호   같은 종목에 신호가 반복되면 더 좋은가 나쁜가
```

⚠️⚠️ **매수는 D+1 「종가」로 잰다.** `entry_lab`에서 밝힌 look-ahead 오류를 여기서는 처음부터
   피한다 — 장 마감 후 공시를 그날 종가에 살 수는 없다.
   ⚠️ 시가가 아니라 종가인 이유: 여기서는 `omni_lab`의 5-튜플(시가 없음)을 재사용한다.
      **D+1 종가는 D+1 시가보다 보수적**이다(하루 더 늦게 산다).
      시가·종가 차이는 `entry_lab`이 따로 잰다.

⚠️ **공시 「규모」(계약금액)는 못 잰다** — `dart-daily`에 공시명만 있고 금액이 없다(2026-09-01 확인).

⚠️ 네 겹 규칙: 초과수익(실제 지수) · 국면 분리 · 표본 명시 · 여러 지평.
"""
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 5, 20)
_MIN = 60

_종류 = [
    ("계약·수주",   ("단일판매", "공급계약", "수주")),
    ("실적",       ("영업(잠정)", "매출액", "손익구조", "결산실적")),
    ("자사주",      ("자기주식",)),
    ("증자·CB",    ("유상증자", "전환사채", "신주인수권")),
    ("특허·기술",   ("특허", "기술이전", "국책과제")),
    ("임상·승인",   ("임상", "품목허가", "승인")),
    ("투자·설비",   ("신규시설", "타법인주식", "투자판단")),
]


def _분류(n):
    n = re.sub(r"\[[^\]]*\]", "", n or "")
    for 이름, kws in _종류:
        if any(k in n for k in kws):
            return 이름
    return None


def _공시상세(날들):
    """{날짜: {코드: {종류들, 분}}} — 공시명을 종류로 쪼갠다."""
    시각 = {}
    for f in glob.glob(os.path.join(O._DATA, "kind-time", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        시각[d["기준일"]] = d.get("시각") or {}
    out = {}
    for d8 in 날들:
        p = os.path.join(O._DATA, "dart-daily", f"{d8}.json")
        if not os.path.exists(p):
            continue
        try:
            g = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:
            continue
        t = 시각.get(d8) or {}
        표 = {}
        for x in (g.get("챙길공시") or []):
            c = x.get("종목코드")
            if not c:
                continue
            nm = x.get("공시명") or ""
            hhmm = t.get(x.get("접수번호"))
            분 = (int(hhmm[:2]) * 60 + int(hhmm[3:])) if hhmm else None
            e = 표.setdefault(c, {"종류": set(), "분": [], "성격": set()})
            k = _분류(nm)
            if k:
                e["종류"].add(k)
            e["성격"].add(O._성격(nm))
            if 분 is not None:
                e["분"].append(분)
        out[d8] = {c: {"종류": v["종류"], "성격": v["성격"],
                       "분": (max(v["분"]) if v["분"] else None)} for c, v in 표.items()}
    return out


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    상세 = _공시상세(날)
    print(f"  공시 상세 {len(상세)}일", flush=True)

    # 52주 고가: 종목별로 굴리며 계산
    통 = {}

    def 담(축, 라, 국면, h, v):
        s = 통.setdefault((축, 라, 국면, h), [0.0, 0])
        s[0] += v
        s[1] += 1

    최근신호 = {}          # 코드 → 마지막 신호일 인덱스
    for i, d1 in enumerate(날):
        if i + 1 >= len(날):
            break
        a0 = 지수.get(날[i + 1])
        if not a0:
            continue
        s1, sN = 주가[d1], 주가[날[i + 1]]
        fl = 수급.get(d1) or {}
        ds = 상세.get(d1) or {}
        # 52주(240거래일) 고가
        창 = 날[max(0, i - 240):i + 1]
        for code, r in ds.items():
            if "호재" not in r["성격"]:
                continue
            v1, vN = s1.get(code), sN.get(code)
            if not v1 or not vN:
                continue
            c1, 시총, 대금, 등락, 코스닥 = v1
            if 시총 < O._MIN_MC or 대금 < O._MIN_AMT:
                continue
            bb = 기본.get(code) or {}
            부 = str(bb.get("업종") or "")
            if ("관리종목" in 부) or ("SPAC" in 부) or \
               (str(bb.get("상장일") or "") > "20240101") or \
               (bb.get("증권구분") not in (None, "주권")):
                continue
            # ⚠️ 매수는 **D+1 종가** (look-ahead 회피. 시가 비교는 entry_lab이 한다)
            매수 = 주가[날[i + 1]].get(code)
            if not 매수:
                continue
            매수가 = 매수[0]
            장 = "KOSDAQ" if 코스닥 else "KOSPI"

            # 특징
            f = fl.get(code) or {}
            외, 기 = f.get("외국인") or 0, f.get("기관") or 0
            강도 = ((외 + 기) * c1 / 시총 * 100) if 시총 > 0 else 0     # 순매수금액 / 시총 (%)
            고 = max((주가[d].get(code) or (0,))[0] for d in 창) or c1
            근접 = c1 / 고 if 고 > 0 else 0
            분 = r["분"]
            앞 = 최근신호.get(code)
            연속 = (앞 is not None and i - 앞 <= 20)
            최근신호[code] = i

            라벨들 = []
            for k in r["종류"]:
                라벨들.append(("공시종류", k))
            if 분 is not None:
                구 = ("15:30~16시" if 분 < 960 else
                      ("16~18시" if 분 < 1080 else "18시 이후"))
                라벨들.append(("시간대", 구))
            라벨들.append(("수급강도", "0.5%↑ 강함" if 강도 >= 0.5 else
                           ("0~0.5% 약함" if 강도 > 0 else "순매도")))
            라벨들.append(("신고가", "95%↑ 근접" if 근접 >= 0.95 else
                           ("70~95%" if 근접 >= 0.70 else "70%↓ 바닥권")))
            라벨들.append(("연속신호", "20일내 재발생" if 연속 else "첫 신호"))

            for h in _H:
                j = i + 1 + h
                if j >= len(날) or not 지수.get(날[j]):
                    continue
                vv = 주가[날[j]].get(code)
                if not vv:
                    continue
                b = 지수[날[j]]
                시장 = b[장] / a0[장] - 1
                초과 = ((vv[0] / 매수가 - 1) - 시장) * 100
                국면 = "상승" if 시장 > 0 else "하락"
                for 축, 라 in 라벨들:
                    담(축, 라, "전체", h, 초과)
                    담(축, 라, 국면, h, 초과)
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print("\n  신호: 호재 공시 · 매수 D+1 종가 · 정상종목만\n")
    축순 = ["공시종류", "시간대", "수급강도", "신고가", "연속신호"]
    for 축 in 축순:
        라들 = sorted({b for a, b, _, _ in 통 if a == 축})
        if not 라들:
            continue
        print(f"  ══════ {축} ══════")
        print(f"    {'':<18}{'국면':<5}" + "".join(f"{'D+'+str(h):>17}" for h in _H))
        for 라 in 라들:
            for 국면 in ("전체", "상승", "하락"):
                칸 = []
                for h in _H:
                    s = 통.get((축, 라, 국면, h))
                    칸.append(f"{s[0]/s[1]:+.3f} (n={s[1]:,})" if s and s[1] >= _MIN else "—")
                if all(c == "—" for c in 칸):
                    continue
                print(f"    {라 if 국면=='전체' else '':<18}{국면:<5}"
                      + "".join(f"{c:>17}" for c in 칸))
        print()
    print("  ⚠️ 공시 「규모」(계약금액)는 못 쟀다 — dart-daily에 공시명만 있고 금액이 없다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
