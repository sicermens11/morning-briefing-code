#!/usr/bin/env python3
r"""
macro_sector_lab.py — **거시 지표가 특정 섹터를 움직이나** (2026-09-02 · 2차)

⚠️⚠️ **1차에서 KRX 3종(선물·유가·금·국고채)이 「국면 필터」로는 전부 실패했다.**
   `market_lab` 결과: 베이시스 −0.181 · 금리 −0.335 · 스프레드 −0.417 · 유가 −0.243 (D+5)
   → **시장 전체에는 안 통한다.**

⚠️ **하지만 「섹터별로는?」은 안 물어봤다.**
```
유가 오르면   정유·화학이 오르나?  조선·해운은?
금리 오르면   금융은 오르나?  건설·성장주는 내리나?
금 오르면     금 관련주는?
환율 오르면   수출주(반도체·자동차)는 오르나?
```
**이건 상식적으로 연결이 있어야 하는 관계다. 없으면 우리 섹터 분류가 틀린 것이다.**

**어떻게 재나**: 업종지수 71개를 거시 지표 방향별로 갈라 다음날 성적을 본다.
⚠️ **종목이 아니라 업종지수를 쓴다** — 개별 종목 잡음을 없애고 섹터 반응만 본다.
⚠️ 거시 지표는 **당일 종가 기준**, 성적은 **다음날부터** 잰다(look-ahead 회피).
"""
import glob
import io
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402

_H = (1, 5, 20)
_MIN = 60


def _n(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _거시():
    """{날짜: {지표: 값}}"""
    표 = {}
    for f in glob.glob(os.path.join(O._DATA, "krx-extra", "일반상품", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        하루 = 표.setdefault(d["기준일"], {})
        for r in (d.get("자료", {}).get("oil_bydd_trd") or []):
            if str(r.get("OIL_NM")) == "휘발유":
                v = _n(r.get("WT_DIS_AVG_PRC"))
                if v:
                    하루["유가"] = v
        for r in (d.get("자료", {}).get("gold_bydd_trd") or []):
            if "99.99_1kg" in str(r.get("ISU_NM") or ""):
                v = _n(r.get("TDD_CLSPRC"))
                if v:
                    하루["금"] = v
    for f in glob.glob(os.path.join(O._DATA, "krx-extra", "국고채", "*.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except Exception:
            continue
        하루 = 표.setdefault(d["기준일"], {})
        for r in (d.get("자료", {}).get("kts_bydd_trd") or []):
            if str(r.get("GOVBND_ISU_TP_NM")) != "지표":
                continue
            만 = str(r.get("BND_EXP_TP_NM") or "")
            y = _n(r.get("CLSPRC_YD"))
            if 만 in ("3", "10") and y:
                하루[f"금리{만}"] = y
    환 = O._환율()
    for d, v in 환.items():
        표.setdefault(d, {})["환율"] = v
    return 표


def main():
    print("  자료 읽는 중...", flush=True)
    지수 = O._지수()
    날 = sorted(지수)
    거시 = _거시()
    쓸수 = [d for d in 날 if 거시.get(d)]
    print(f"  지수 {len(날)}일 · 거시 {len(쓸수)}일", flush=True)

    # 업종지수 목록 (모든 날에 있는 것만)
    업종 = None
    for d in 날:
        s = set(지수[d].get("업종") or {})
        업종 = s if 업종 is None else (업종 & s)
    업종 = sorted(업종 or [])
    print(f"  업종지수 {len(업종)}개", flush=True)

    지표들 = ["유가", "금", "금리3", "금리10", "환율"]
    통 = {}

    def 담(k, v):
        s = 통.setdefault(k, [0.0, 0])
        s[0] += v
        s[1] += 1

    for i in range(1, len(날) - max(_H)):
        d1, 전 = 날[i], 날[i - 1]
        g1, g0 = 거시.get(d1), 거시.get(전)
        if not g1 or not g0:
            continue
        방향 = {}
        for k in 지표들:
            if g1.get(k) and g0.get(k):
                방향[k] = "상승" if g1[k] > g0[k] else "하락"
        if not 방향:
            continue
        u1 = 지수[d1].get("업종") or {}
        for h in _H:
            j = i + h
            u2 = 지수[날[j]].get("업종") or {}
            # 시장 전체(코스피) 대비 초과
            시장 = 지수[날[j]]["KOSPI"] / 지수[d1]["KOSPI"] - 1
            for u in 업종:
                a, b = u1.get(u), u2.get(u)
                if not a or not b:
                    continue
                초 = ((b / a - 1) - 시장) * 100
                for k, v in 방향.items():
                    담((u, k, v, h), 초)

    # 지표별로 「상승일 - 하락일」 차이가 큰 업종 상위/하위
    print("\n  업종지수 초과수익(코스피 대비) · 거시 지표 방향별 · D+5 기준\n")
    for k in 지표들:
        줄 = []
        for u in 업종:
            up = 통.get((u, k, "상승", 5))
            dn = 통.get((u, k, "하락", 5))
            if not up or not dn or up[1] < _MIN or dn[1] < _MIN:
                continue
            a, b = up[0] / up[1], dn[0] / dn[1]
            줄.append((a - b, u, a, b, up[1], dn[1]))
        if not 줄:
            continue
        줄.sort(reverse=True)
        print(f"  ══════ {k} ══════")
        print(f"    {'업종':<26}{'상승일':>10}{'하락일':>10}{'차이':>10}{'n':>8}")
        for 차, u, a, b, n1, n2 in 줄[:5]:
            print(f"    {u[:24]:<26}{a:>+9.3f}{b:>+9.3f}{차:>+10.3f}{n1:>8,}")
        print(f"    {'…':<26}")
        for 차, u, a, b, n1, n2 in 줄[-3:]:
            print(f"    {u[:24]:<26}{a:>+9.3f}{b:>+9.3f}{차:>+10.3f}{n1:>8,}")
        print()
    print("  읽는 법")
    print("    - '차이'가 크면 그 거시 지표가 그 업종을 실제로 움직인다는 뜻")
    print("    - 상식과 맞아야 한다 (유가↑ → 정유/화학, 금리↑ → 금융)")
    print("    - 상식과 안 맞으면 우연이거나 우리 해석이 틀린 것이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
