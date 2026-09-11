#!/usr/bin/env python3
r"""gap1_lab.py — **갭①(장 마감 후 공시)을 처음으로 제대로 잰다** (2026-09-01 신설)

⚠️⚠️ **그동안 못 쟀다.** DART API에는 시각이 없어(`rcept_dt`는 날짜뿐) **접수번호 순번**을
   대리지표로 썼는데, 그건 실제 시각이 아니라 그날 접수 **순서**였고 계열이 섞여 부정확했다.
   그 부정확한 지표로 「호재+늦게+무반응」이 −0.581(D+5)로 나왔고, 나는 그걸 근거로
   **갭①을 의심했다.** 이제 **거래소(KIND)의 실제 시각**으로 다시 잰다.

**붙이는 방법**
```
data/kind-time/{날짜}.json   {접수번호: "HH:MM"}      ← 거래소에서 받음
data/dart-daily/{날짜}.json  접수번호 → 종목코드·공시명  ← 이미 있음
```

⚠️ **장 마감은 15:30이다.** 그 뒤 접수가 갭①의 「장 마감 후」다.
⚠️ 다만 **시간외 거래(15:40~18:00)**가 있어 "다음날 시가에 반영"이라는 전제가 그대로는
   아니다. **18:00 이후**도 따로 잰다 — 시간외조차 끝난 뒤라 갭①에 가장 가깝다.

⚠️ 네 겹 규칙(초과수익률 · 상승/하락 · 표본 · 여러 지평)은 그대로다.
⚠️⚠️ **갭③(수급)은 아직 못 넣었다.** 조합 결과는 갭③이 들어오면 **달라질 수 있다.**
   갭① **단독** 결과만 갭③과 무관하다.

쓰는 법: python scripts\gap1_lab.py
"""
import datetime as dt
import glob
import io
import json
import os
import re
import statistics as st
import sys

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_MIN_MC, _MIN_AMT = 5e10, 1e8
_H = (1, 5, 20)
_호재 = ("단일판매", "공급계약", "수주", "자기주식취득", "자기주식소각", "무상증자",
         "현금ㆍ현물배당", "영업양수", "타법인주식및출자증권취득")
_악재 = ("유상증자", "전환사채", "신주인수권부사채", "교환사채", "거래정지", "상장폐지",
         "소송등의제기", "감자", "자기주식처분", "관리종목", "횡령", "배임")


def _지수():
    """{YYYYMMDD: {"KOSPI": 종가, "KOSDAQ": 종가}} — 실제 지수."""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "index-daily", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        z = d.get("지수") or {}
        k1 = (z.get("코스피") or {}).get("종가")
        k2 = (z.get("코스닥") or {}).get("종가")
        if k1 and k2:
            표[d["기준일"]] = {"KOSPI": k1, "KOSDAQ": k2}
    return 표


_IDX = None
_FLOW = None
_BASE_ = None


def _수급():
    """{날짜: {코드: {외국인, 기관}}} — 2026-09-01에 받은 flow-daily 648일."""
    표 = {}
    for f in glob.glob(os.path.join(_DATA, "flow-daily", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        표[d["기준일"]] = d.get("종목") or {}
    return 표


def _기본():
    """⚠️ 관리종목·SPAC·신규상장·리츠를 걸러내기 위한 종목 기본정보."""
    try:
        return json.load(io.open(os.path.join(_DATA, "stock-base.json"),
                                 encoding="utf-8-sig"))["종목"]
    except Exception:
        return {}


def _성격(n):
    n = re.sub(r"\[[^\]]*\]", "", n or "")
    if any(k in n for k in _악재):
        return "악재"
    return "호재" if any(k in n for k in _호재) else "중립"


def _날(s):
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def main():
    global _IDX, _FLOW, _BASE_
    _IDX = _지수()
    _FLOW = _수급()
    _BASE_ = _기본()
    print(f"  실제 지수 {len(_IDX)}일 · 수급 {len(_FLOW)}일 · 종목기본 {len(_BASE_)}개",
          flush=True)
    fs = sorted(glob.glob(os.path.join(_DATA, "krx-daily", "*.json")))
    일 = []
    for f in fs:
        d8 = os.path.basename(f)[:8]
        dd = os.path.join(_DATA, "dart-daily", f"{d8}.json")
        kt = os.path.join(_DATA, "kind-time", f"{d8}.json")
        if not (os.path.exists(dd) and os.path.exists(kt)):
            continue
        with io.open(f, encoding="utf-8-sig") as fp:
            시세 = json.load(fp).get("종목") or {}
        with io.open(dd, encoding="utf-8-sig") as fp:
            공 = json.load(fp).get("챙길공시") or []
        with io.open(kt, encoding="utf-8-sig") as fp:
            시각 = json.load(fp).get("시각") or {}
        정보 = {}
        for x in 공:
            code, 번 = x.get("종목코드"), x.get("접수번호")
            if not code or not 번:
                continue
            hm = 시각.get(번)
            r = 정보.setdefault(code, {"성격": set(), "분": []})
            r["성격"].add(_성격(x.get("공시명")))
            if hm:
                try:
                    r["분"].append(int(hm[:2]) * 60 + int(hm[3:5]))
                except (ValueError, IndexError):
                    pass
        일.append((d8, 시세, 정보))
    if len(일) < 20:
        print(json.dumps({"ok": False, "이유": f"세 자료가 다 있는 날이 {len(일)}일뿐"},
                         ensure_ascii=False))
        return 1
    행 = []
    for i, (d1, s1, 정보) in enumerate(일):
        시장h = {}
        for h in _H:
            j = i + h
            if j >= len(일) or (_날(일[j][0]) - _날(d1)).days > h * 2 + 4:
                continue
            s2 = 일[j][1]
            # ⚠️⚠️ **실제 지수를 쓴다** (2026-09-01). 전에는 「전 종목 단순평균」이었다.
            #    코스피는 시총가중이라 단순평균과 크게 다르다 — 대형주가 오르고
            #    소형주가 내리면 지수는 오르는데 단순평균은 내린다.
            a, b = _IDX.get(일[i][0]), _IDX.get(일[j][0])
            if a and b:
                시장h[h] = (s2, {"KOSPI": b["KOSPI"] / a["KOSPI"] - 1,
                                 "KOSDAQ": b["KOSDAQ"] / a["KOSDAQ"] - 1})
        for code, v1 in s1.items():
            try:
                c1 = float(v1["종가"]); 시총 = float(v1["시총"]); 대금 = float(v1["거래대금"])
                등락 = float(v1["등락률"])
            except (TypeError, ValueError, KeyError):
                continue
            if c1 <= 0 or 시총 < _MIN_MC or 대금 < _MIN_AMT:
                continue
            r = 정보.get(code) or {}
            분 = max(r["분"]) if r.get("분") else None
            # ⚠️ 갭③ 수급 — **외국인·기관 둘 다 순매수**여야 한다(스킬 정의 그대로)
            fl = (_FLOW.get(일[i][0]) or {}).get(code) or {}
            외, 기 = fl.get("외국인"), fl.get("기관")
            갭3 = (외 is not None and 기 is not None and 외 > 0 and 기 > 0)
            # ⚠️ 오염 제거 — 관리종목·SPAC·2024년 이후 신규상장·리츠는 뺀다
            bb = _BASE_.get(code) or {}
            부 = str(bb.get("업종") or "")
            더럽 = (("관리종목" in 부) or ("SPAC" in 부)
                    or (str(bb.get("상장일") or "") > "20240101")
                    or (bb.get("증권구분") not in (None, "주권")))
            f = {"공시": bool(r), "성격": r.get("성격", set()), "분": 분,
                 "무반응": abs(등락) < 1, "시총": 시총, "갭3": 갭3, "더럽": 더럽}
            장 = v1.get("시장") or "KOSPI"
            장 = "KOSDAQ" if "KOSDAQ" in str(장).upper() else "KOSPI"
            for h, (s2, 시장맵) in 시장h.items():
                시장평 = 시장맵[장]
                v2 = s2.get(code)
                if not v2:
                    continue
                try:
                    c2 = float(v2["종가"])
                except (TypeError, ValueError, KeyError):
                    continue
                g = dict(f)
                g["h"] = h
                g["초과"] = ((c2 / c1 - 1) - 시장평) * 100
                g["시장"] = 시장평
                행.append(g)
    조건 = [
        ("공시 있음(전체)", lambda x: x["공시"]),
        ("장중 공시(~15:30)", lambda x: x["분"] is not None and x["분"] < 930),
        ("장 마감 후(15:30~)", lambda x: x["분"] is not None and x["분"] >= 930),
        ("18시 이후(시간외도 끝)", lambda x: x["분"] is not None and x["분"] >= 1080),
        ("호재 + 장중", lambda x: "호재" in x["성격"] and x["분"] is not None and x["분"] < 930),
        ("호재 + 장 마감 후", lambda x: "호재" in x["성격"] and x["분"] is not None and x["분"] >= 930),
        ("호재 + 18시 이후", lambda x: "호재" in x["성격"] and x["분"] is not None and x["분"] >= 1080),
        ("[갭①④] 호재+장후+무반응", lambda x: "호재" in x["성격"] and x["분"] is not None
         and x["분"] >= 930 and x["무반응"]),
        ("[+소형주제외] 위 + 3천억↑", lambda x: "호재" in x["성격"] and x["분"] is not None
         and x["분"] >= 930 and x["무반응"] and x["시총"] >= 3e11),
        ("── 갭③ 수급 ──", None),
        ("호재 + 갭③(외인·기관 동반)", lambda x: "호재" in x["성격"] and x["갭3"]),
        ("호재 + 갭③ 없음", lambda x: "호재" in x["성격"] and not x["갭3"]),
        ("[갭①③] 호재+장후+수급", lambda x: "호재" in x["성격"] and x["분"] is not None
         and x["분"] >= 930 and x["갭3"]),
        ("[갭①③④] 장후+무반응+수급", lambda x: "호재" in x["성격"] and x["분"] is not None
         and x["분"] >= 930 and x["무반응"] and x["갭3"]),
        ("── 오염 제거 ──", None),
        ("[갭①④] 정상종목만", lambda x: "호재" in x["성격"] and x["분"] is not None
         and x["분"] >= 930 and x["무반응"] and not x["더럽"]),
        ("[갭①③④] 정상종목만", lambda x: "호재" in x["성격"] and x["분"] is not None
         and x["분"] >= 930 and x["무반응"] and x["갭3"] and not x["더럽"]),
    ]
    print(f"  세 자료가 다 있는 날 {len(일)}일 · 관측 {len(행):,}건")
    for 라벨, 필터 in [("전체", lambda x: True),
                       ("시장 상승", lambda x: x["시장"] > 0),
                       ("시장 하락", lambda x: x["시장"] <= 0)]:
        print(f"\n  [{라벨}]")
        print(f"    {'조건':26s}" + "".join(f"{'D+'+str(h):>17s}" for h in _H))
        for 이름, c in 조건:
            줄 = f"    {이름:26s}"
            for h in _H:
                부분 = [x for x in 행 if x["h"] == h and 필터(x)]
                a = [x["초과"] for x in 부분 if c(x)]
                b = [x["초과"] for x in 부분 if not c(x)]
                if len(a) < 100 or len(b) < 100:
                    줄 += f"{'—':>17s}"
                else:
                    줄 += f"{f'{st.mean(a)-st.mean(b):+.3f} (n={len(a)})':>17s}"
            print(줄)
    return 0


if __name__ == "__main__":
    sys.exit(main())
