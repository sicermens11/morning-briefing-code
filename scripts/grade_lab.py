#!/usr/bin/env python3
r"""
grade_lab.py — **우리 등급이 실제로 작동하나** (2026-09-01 신설)

⚠️⚠️⚠️ **이 프로젝트의 핵심 질문이다.** AGENDA에 *"2026-09-15에 답한다"*로 박아뒀는데
   픽이 하루 3~4건씩만 쌓여서였다. **이제 648일 전 종목으로 오늘 답할 수 있다.**

**무엇을 하나**: 점수표를 **소급 계산 가능한 항목만으로** 재현해 점수를 매기고,
점수 구간별 성적을 본다. 점수가 높을수록 성적이 좋아야 등급이 「작동한다」고 말할 수 있다.

**소급 계산되는 점수 항목 7개** (전체 11개 중)
```
갭① 시간갭   장 마감 후(15:30~) 공시            +1   kind-time
갭③ 수급갭   외국인·기관 **둘 다** 순매수         +1   flow-daily
갭④ 가격갭   등락률 절댓값 1% 미만(무반응)         +1   krx-daily
조건부-C     목표주가 상향 +1 / 하향 −2 / 의견강등 −1   consensus
강화-D1      임원 자사주 신고 30일내              +2   dart-exec
강화-CAP     유상증자·CB 공시                   −2   dart-daily
재무취약     최신 **분기** 부채비율200%+ 또는 순이익률 음수  −2   naver-quarter
```
❌ 못 넣는 것: 갭②(뉴스) · 강화-G/B🇺🇸 · 미장급등 — 과거 자료가 없다.

⚠️⚠️ **그래서 이건 「반쪽 등급」이다.** 결론이 한쪽으로만 강하다:
```
반쪽으로도 작동한다   → 나머지 4개가 도움 되는지는 **여전히 모른다** (약한 결론)
반쪽으로도 작동 안 함 → ⚠️ **점수표를 손봐야 한다** (강한 결론)
```

⚠️ **매수는 D+1 종가**로 잰다 — 장 마감 후 공시를 그날 종가에 살 수 없다(look-ahead 회피).
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
_증자 = ("유상증자", "전환사채", "신주인수권")


def _증자공시(날들):
    """{날짜: {코드}} — 그날 유상증자·CB 공시가 난 종목."""
    out = {}
    for d8 in 날들:
        p = os.path.join(O._DATA, "dart-daily", f"{d8}.json")
        if not os.path.exists(p):
            continue
        try:
            g = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:
            continue
        s = set()
        for x in (g.get("챙길공시") or []):
            nm = re.sub(r"\[[^\]]*\]", "", x.get("공시명") or "")
            if any(k in nm for k in _증자) and x.get("종목코드"):
                s.add(x["종목코드"])
        out[d8] = s
    return out


def main():
    print("  자료 읽는 중…", flush=True)
    주가 = O._주가()
    날 = sorted(주가)
    지수, 수급, 기본 = O._지수(), O._수급(), O._기본()
    공시 = O._공시(날)
    재무 = O._분기재무()
    임원 = O._이벤트("dart-exec")
    컨센 = O._컨센()
    증자 = _증자공시(날)
    print(f"  적재 완료 · 증자공시 {sum(len(v) for v in 증자.values()):,}건", flush=True)

    통 = {}
    항목통 = {}

    def 담(표, k, v):
        s = 표.setdefault(k, [0.0, 0])
        s[0] += v
        s[1] += 1

    for i, d1 in enumerate(날):
        if i + 1 >= len(날):
            break
        a0 = 지수.get(날[i + 1])
        if not a0:
            continue
        s1 = 주가[d1]
        fl = 수급.get(d1) or {}
        ds = 공시.get(d1) or {}
        cb = 증자.get(d1) or set()
        구 = set(날[max(0, i - 20):i + 1])
        for code, r in ds.items():
            # ⚠️ **공시가 있는 종목만** 본다 — 브리핑도 공시에서 후보를 찾는다
            if "호재" not in r.get("성격", set()):
                continue
            v1 = s1.get(code)
            매수v = 주가[날[i + 1]].get(code)
            if not v1 or not 매수v:
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

            f = fl.get(code) or {}
            fin = {}
            for 적용, 값 in (재무.get(code) or []):
                if 적용 <= d1:
                    fin = 값
                else:
                    break
            항목 = {}
            항목["갭①"] = 1 if (r.get("분") is not None and r["분"] >= 930) else 0
            항목["갭③"] = 1 if ((f.get("외국인") or 0) > 0 and (f.get("기관") or 0) > 0) else 0
            항목["갭④"] = 1 if abs(등락) < 1 else 0
            방 = (컨센.get(code) or {}).get(d1)
            항목["조건부C"] = 1 if 방 == "상향" else (-2 if 방 == "하향" else 0)
            항목["강화D1"] = 2 if ((임원.get(code) or set()) & 구) else 0
            항목["강화CAP"] = -2 if code in cb else 0
            부채, 순익 = fin.get("부채비율"), fin.get("순이익률")
            항목["재무취약"] = -2 if ((부채 is not None and 부채 >= 200)
                                     or (순익 is not None and 순익 < 0)) else 0
            점수 = sum(항목.values())

            장 = "KOSDAQ" if 코스닥 else "KOSPI"
            매수가 = 매수v[0]
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
                # 점수 구간
                구간 = ("3점↑" if 점수 >= 3 else "2점" if 점수 == 2 else
                        "1점" if 점수 == 1 else "0점" if 점수 == 0 else "음수")
                for 국 in ("전체", 국면):
                    담(통, (구간, 국, h), 초과)
                    담(통, ("── 전체 평균", 국, h), 초과)
                # 항목별 기여도: 그 항목이 켜진 것 vs 꺼진 것
                for k, v in 항목.items():
                    담(항목통, (k, "켜짐" if v != 0 else "꺼짐", 국면 if 국면 else "전체", h), 초과)
                    담(항목통, (k, "켜짐" if v != 0 else "꺼짐", "전체", h), 초과)
        if i % 150 == 0:
            print(f"    {i}/{len(날)}일", flush=True)

    print("\n  ══════ 점수 구간별 (반쪽 등급 — 7개 항목만) ══════")
    print(f"    {'점수':<14}{'국면':<5}" + "".join(f"{'D+'+str(h):>17}" for h in _H))
    for 구간 in ("3점↑", "2점", "1점", "0점", "음수", "── 전체 평균"):
        for 국면 in ("전체", "상승", "하락"):
            칸 = []
            for h in _H:
                s = 통.get((구간, 국면, h))
                칸.append(f"{s[0]/s[1]:+.3f} (n={s[1]:,})" if s and s[1] >= _MIN else "—")
            if all(c == "—" for c in 칸):
                continue
            print(f"    {구간 if 국면=='전체' else '':<14}{국면:<5}"
                  + "".join(f"{c:>17}" for c in 칸))
    print("\n  ⚠️ **점수가 높을수록 성적이 좋아야** 등급이 「작동한다」고 말할 수 있다.")
    print("     단조롭게 올라가지 않으면 점수표가 잘못됐다는 뜻이다.")

    print("\n  ══════ 항목별 기여도 (켜짐 vs 꺼짐, 전체) ══════")
    print(f"    {'항목':<12}{'상태':<6}" + "".join(f"{'D+'+str(h):>17}" for h in _H))
    for k in ("갭①", "갭③", "갭④", "조건부C", "강화D1", "강화CAP", "재무취약"):
        for st in ("켜짐", "꺼짐"):
            칸 = []
            for h in _H:
                s = 항목통.get((k, st, "전체", h))
                칸.append(f"{s[0]/s[1]:+.3f} (n={s[1]:,})" if s and s[1] >= _MIN else "—")
            if all(c == "—" for c in 칸):
                continue
            print(f"    {k if st=='켜짐' else '':<12}{st:<6}"
                  + "".join(f"{c:>17}" for c in 칸))
    print("\n  ⚠️ 「켜짐」이 「꺼짐」보다 나빠야 하는 항목(강화CAP·재무취약)은 **음수 감점**이다.")
    print("     방향이 반대면 그 감점은 근거가 없다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
