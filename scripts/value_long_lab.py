#!/usr/bin/env python3
r"""
value_long_lab.py — **B248 장기 가치투자 (숫자로 되는 부분)** — 해마다 한 번 사서 1년 들고 바꾼다 (2026-10-12)

사용자 10/8: 「장기 가치투자는 할 수 있는데 지금이랑 방식이 달라서 안하는거야? 아니면 못 하는거야?」 →
          「장기투자법에 유의미한 결과가 나온다면, 퀀트 후보랑은 다른 별도 카테고리가 될거야」
⚠️ 연휴(10/9~11)에 돌렸어야 했는데 안 돌렸다 — 10/12 다시

방식
· 바꾸는 날: 해마다 4월 첫 거래일(전년 사업보고서가 나온 뒤 · day_lab.연간재무 와 같은 「Y년치는 Y+1년 4/1 부터」)
· 대상: 그날 시총 300억↑ · 그 해 재무가 있는 종목 (관리종목 여부는 옛날 것을 모른다 — 빼지 못함 ⚠️)
· 묶음마다 상위 20종목 같은 돈으로 · 1년 뒤 다음 바꾸는 날 종가에 판다 · 비용 0.26%(사고팔기 한 번)
· 사라진 종목(상장폐지 등)은 마지막 값의 절반으로 센다(own_lab 과 같은 보수적 가정)
· 수정 주가(omni_lab.수정주가 · 권리락 반영)
묶음
  ① 저PBR+품질 — ROE>0 · 부채비율<100% 중 PBR 낮은 순위 + ROE 높은 순위 합
  ② 마법공식 — 이익수익률(영업이익 ÷ (시총+부채)) 순위 + ROIC근사(영업이익 ÷ (자본+비유동부채)) 순위 합 (영업이익>0)
  ③ F점수 높고 싼 것 — F점수7 ≥ 5 중 PBR 낮은 순
  ④ 넷넷 — (유동자산 − 부채총계) > 0 인 것 중 시총 대비 큰 순
  견줌: 대상 전체 같은 돈 · 코스피 지수
쓰는 법: python scripts\value_lab.py   → data/_labs/<날>_B248_장기가치.txt
"""
import datetime as dt
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omni_lab as O  # noqa: E402
import newmat  # noqa: E402

_L = os.path.join(O._DATA, "_labs")
_밖 = io.open(os.path.join(_L, os.environ.get("LAB_OUT") or f"{dt.date.today():%Y-%m-%d}_B248_장기가치.txt"), "w", encoding="utf-8")
_N = int(os.environ.get("VALUE_N") or 20)
_비용 = 0.26


def 찍기(s=""):
    print(s, flush=True)
    _밖.write(s + "\n")
    _밖.flush()


def 코스피표():
    out = {}
    for f in sorted(glob.glob(os.path.join(O._DATA, "index-daily", "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8-sig"))
        except ValueError:
            continue
        v = ((d.get("지수") or {}).get("코스피") or {}).get("종가")
        if isinstance(v, (int, float)):
            out[os.path.basename(f)[:8]] = float(v)
    return out


def main():
    주가 = O.수정주가(("시총",))
    날 = sorted(주가)
    재 = newmat._연간원본()
    코 = 코스피표()
    바꿈날 = []
    for y in range(2016, int(날[-1][:4]) + 1):
        d = next((z for z in 날 if z >= f"{y}0401"), None)
        if d:
            바꿈날.append(d)
    if 날[-1] not in 바꿈날:
        바꿈날.append(날[-1])        # 마지막 해는 오늘까지(1년 안 됨)
    찍기("=" * 110)
    찍기(f"  B248 장기 가치투자 — 해마다 4월 첫 거래일에 상위 {_N}종목 · 1년 들고 바꿈 · 비용 {_비용}% · 사라지면 마지막 값의 절반")
    찍기(f"  바꾸는 날: {' · '.join(바꿈날)}")
    찍기("  ⚠️ 관리종목·거래정지 여부는 옛 날 것을 모른다 · 재무는 별도(dart-fin) · 시총 300억↑")
    찍기("=" * 110)
    묶음이름 = ("① 저PBR+품질", "② 마법공식", "③ F점수↑·저PBR", "④ 넷넷", "대상 전체", "코스피")
    해수익 = {k: [] for k in 묶음이름}
    고른수 = {k: [] for k in 묶음이름}
    for a, b in zip(바꿈날[:-1], 바꿈날[1:]):
        표 = []
        for code, v in 주가[a].items():
            시총 = v[1] if len(v) > 1 else None
            if not 시총 or 시총 < 300e8 or not v[0]:
                continue
            f = newmat.재무새값(재, code, a, 시총)
            t = 재.get(code)
            if not f or not t:
                continue
            import bisect
            p = bisect.bisect_right(t[0], a) - 1
            원 = t[1][p]
            자본 = 원["자본"]
            pbr = (시총 / 자본) if (자본 and 자본 > 0) else None
            roe = (원["순익"] / 자본 * 100) if (자본 and 자본 > 0 and 원["순익"] is not None) else None
            부채비 = (원["부채"] / 자본 * 100) if (자본 and 자본 > 0 and 원["부채"] is not None) else None
            표.append({"code": code, "시총": 시총, "pbr": pbr, "roe": roe, "부채비": 부채비, **f, "산": v[0]})

        def 순위(rows, 키, 큰게좋다):
            s = sorted(rows, key=lambda r: r[키], reverse=큰게좋다)
            return {r["code"]: k for k, r in enumerate(s)}
        고 = {}
        g1 = [r for r in 표 if r["pbr"] and r["roe"] is not None and r["roe"] > 0 and r["부채비"] is not None and r["부채비"] < 100]
        if g1:
            r1, r2 = 순위(g1, "pbr", False), 순위(g1, "roe", True)
            고["① 저PBR+품질"] = sorted(g1, key=lambda r: r1[r["code"]] + r2[r["code"]])[:_N]
        g2 = [r for r in 표 if r.get("이익수익률EV") is not None and r.get("ROIC근사") is not None and r["이익수익률EV"] > 0]
        if g2:
            r1, r2 = 순위(g2, "이익수익률EV", True), 순위(g2, "ROIC근사", True)
            고["② 마법공식"] = sorted(g2, key=lambda r: r1[r["code"]] + r2[r["code"]])[:_N]
        g3 = [r for r in 표 if r.get("F점수7") is not None and r["F점수7"] >= 5 and r["pbr"]]
        고["③ F점수↑·저PBR"] = sorted(g3, key=lambda r: r["pbr"])[:_N]
        g4 = [r for r in 표 if r.get("넷넷") is not None and r["넷넷"] > 0]
        고["④ 넷넷"] = sorted(g4, key=lambda r: -r["넷넷"])[:_N]
        고["대상 전체"] = 표

        def 수익(rows):
            if not rows:
                return None
            rs = []
            for r in rows:
                v2 = 주가[b].get(r["code"])
                if v2 and v2[0]:
                    rs.append(v2[0] / r["산"] - 1)
                else:
                    # 사라짐 — b 전 마지막 값의 절반
                    마 = None
                    for d in reversed([z for z in 날 if a < z < b]):
                        v3 = 주가[d].get(r["code"])
                        if v3 and v3[0]:
                            마 = v3[0]
                            break
                    rs.append(((마 or r["산"]) * 0.5) / r["산"] - 1)
            return sum(rs) / len(rs) * 100 - _비용
        for k in 묶음이름[:-1]:
            v = 수익(고.get(k) or [])
            해수익[k].append(v)
            고른수[k].append(len(고.get(k) or []))
        ka, kb = 코.get(a), 코.get(b)
        해수익["코스피"].append(((kb / ka - 1) * 100) if (ka and kb) else None)
        고른수["코스피"].append(0)
    찍기(f"\n  {'묶음':<18}" + "".join(f"{d[:4]}~{e[2:4]}/{e[4:6]:>3}" for d, e in zip(바꿈날[:-1], 바꿈날[1:])) + "     연평균   500만→     최악해")
    for k in 묶음이름:
        rs = 해수익[k]
        돈 = 500.0
        for r in rs:
            if r is not None:
                돈 *= (1 + r / 100)
        해수 = (dt.date(int(바꿈날[-1][:4]), int(바꿈날[-1][4:6]), int(바꿈날[-1][6:])) - dt.date(int(바꿈날[0][:4]), int(바꿈날[0][4:6]), int(바꿈날[0][6:]))).days / 365.25
        연 = ((돈 / 500.0) ** (1 / 해수) - 1) * 100 if 해수 > 0 else 0
        최악 = min((r for r in rs if r is not None), default=None)
        찍기(f"  {k:<18}" + "".join(f"{(f'{r:+.1f}%' if r is not None else '—'):>10}" for r in rs)
             + f"  {연:+7.1f}%  {돈:>7,.0f}만  {(f'{최악:+.1f}%' if 최악 is not None else '—'):>8}")
    찍기("\n  고른 종목 수(해마다): " + " · ".join(f"{k} {고른수[k]}" for k in 묶음이름[:4]))
    찍기("  ⚠️ 마지막 칸은 1년이 안 된 올해(4월~지금) · 해 단위라 해 안의 낙폭은 안 보인다")
    찍기("  [대조] B248 끝")


if __name__ == "__main__":
    main()
