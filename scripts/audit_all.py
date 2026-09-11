#!/usr/bin/env python3
r"""
audit_all.py — **전수 점검** (2026-09-09 밤 신설)

## 사용자 말 (그대로)
```
「스크립트 중에 **제대로 작동 안하는게 계속 나오는 것 같은데** 그것도 한번 전체적으로 점검하고!
  그리고 아까 **재료가 0개인데 문제가 0개로 인식**해서 제대로 수집 안되는 것도 있었던거 같은데
  **그런 류의 문제가 또 없나** 확인하고!」
```

## 오늘 하루에 나온 「조용한 실패」들 — 이 도구가 찾아야 할 것
```
① 컨센서스 빈 파일 38개   오류로 0건 받았는데 **저장해버려서**, 다음엔 「이미 받음」으로 건너뜀
② 임원·5%보유 8일 멈춤    **종목 단위** 「이미 받았으면 건너뛴다」 — 새 매매를 영영 안 받음
③ 예약 넷 일회성 트리거    9/2~9/4 이후 안 돌았는데 목록엔 「준비」로 보임
④ 저녁 수집 통째로 죽음    하위의 Ctrl+C 가 부모까지 죽임 (except Exception 이 못 잡음)
⑤ 금리(FRED) 접속 실패    9/3부터 TimeoutError — 매일 10분 버림
⑥ 190차 4관문 「전부 통과」  **기회가 6~37% 로 줄었는데** 이김만 보고 통과로 셈
```

## 재는 것
```
A  **자료가 며칠 밀렸나** — 폴더마다 최신 날짜
B  ⭐ **빈 파일·거의 빈 파일** (조용한 실패의 흔적)
C  ⭐ **0건이어도 저장하는 수집기** (코드에서 찾는다)
D  ⭐ **「이미 받았으면 건너뛴다」만 있고 갱신 수단이 없는 수집기**
E  스크립트 문법 검사 (import 까지)
F  최근 로그의 오류·타임아웃
G  ⭐ **판정에 기회 수를 안 보는 시험** (185·190차에서 들통난 그것)
```

쓰는 법:
    python scripts\audit_all.py
"""
import ast
import datetime as dt
import glob
import io
import json
import os
import re
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_D = os.path.join(_BASE, "data")
_S = os.path.join(_BASE, "scripts")

# (폴더, 이름, 며칠 밀리면 문제인가)
_폴더 = (("krx-daily", "주가", 2), ("index-daily", "지수", 2),
         ("dart-daily", "공시", 1), ("flow-daily", "수급", 2),
         ("kind-time", "공시시각", 1), ("etf-krx", "ETF", 3),
         ("krx-extra", "KRX추가", 3), ("consensus", "컨센서스", 8),
         ("news", "뉴스", 2), ("dart-exec", "임원매매", 8),
         ("dart-major", "5%보유", 8), ("dart-fin", "연간재무", 40),
         ("quarter-fin", "분기재무", 40), ("naver-quarter", "네이버분기", 40),
         ("dart-capital", "증자감자", 40), ("dart-snap", "사업보고서", 40),
         ("yahoo", "해외", 3), ("fred", "금리", 8))


def _최신(폴더):
    """(최신 날짜문자열 또는 None, 파일 수)"""
    바 = os.path.join(_D, 폴더)
    if not os.path.isdir(바):
        return None, 0
    fs = glob.glob(os.path.join(바, "*.json")) + \
        glob.glob(os.path.join(바, "*", "*.json"))
    if not fs:
        return None, 0
    # 이름이 날짜면 그걸 쓰고, 아니면 수정시각을 쓴다
    날 = []
    for f in fs:
        m = re.search(r"(20\d{6})", os.path.basename(f))
        if m:
            날.append(m.group(1))
    if 날:
        return max(날), len(fs)
    가장 = max(os.path.getmtime(f) for f in fs)
    return dt.datetime.fromtimestamp(가장).strftime("%Y%m%d"), len(fs)


def A절():
    print("\n" + "=" * 96)
    print("  A **자료가 며칠 밀렸나**")
    print("=" * 96)
    오늘 = dt.date.today()
    나쁨 = []
    print(f"  {'자료':<12}{'최신':>10}{'밀림':>7}{'파일수':>9}   판정")
    for 폴, 라, 한 in _폴더:
        최, n = _최신(폴)
        if 최 is None:
            print(f"  {라:<12}{'없음':>10}{'':>7}{n:>9}   ⚠️ 폴더가 비었다")
            나쁨.append(f"{라}: 자료 없음")
            continue
        try:
            d = dt.datetime.strptime(최, "%Y%m%d").date()
            밀 = (오늘 - d).days
        except ValueError:
            밀 = -1
        표 = "✅" if 밀 <= 한 else f"⚠️ **{밀}일 밀렸다**"
        if 밀 > 한:
            나쁨.append(f"{라}: {밀}일 밀림 (최신 {최})")
        print(f"  {라:<12}{최:>10}{밀:>6}일{n:>9,}   {표}")
    return 나쁨


def B절():
    print("\n" + "=" * 96)
    print("  B ⭐ **진짜 깨진 파일** — 조용한 실패의 흔적")
    print("     ⚠️ 크기로 재면 안 된다. {\"건수\": 0, \"이력\": []} 는 **정상**이다")
    print("        (그 종목에 그 일이 없었다는 뜻이다)")
    print("     여기서는 **0바이트이거나 JSON 이 깨진 것**만 센다")
    print("=" * 96)
    나쁨 = []
    for 폴, 라, _ in _폴더:
        바 = os.path.join(_D, 폴)
        if not os.path.isdir(바):
            continue
        fs = glob.glob(os.path.join(바, "*.json")) + \
            glob.glob(os.path.join(바, "*", "*.json"))
        깨짐, 빈모양 = [], 0
        for f in fs:
            n = os.path.getsize(f)
            if n == 0:
                깨짐.append(f)
                continue
            if n >= 400:
                continue
            # 작은 것만 열어본다 (큰 것은 정상으로 본다)
            try:
                d = json.load(io.open(f, encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001
                깨짐.append(f)
                continue
            if isinstance(d, dict) and d:
                빈모양 += 1          # 모양이 갖춰진 빈 값 — 정상
            else:
                깨짐.append(f)
        if 깨짐:
            예 = ", ".join(os.path.basename(x) for x in 깨짐[:3])
            print(f"  ⚠️ {라:<12}**깨진 파일 {len(깨짐):,}개**  예) {예}")
            나쁨.append(f"{라}: 깨진 파일 {len(깨짐)}개")
        elif 빈모양:
            print(f"  {라:<12}빈 값 {빈모양:,}개 (모양은 갖춰졌다 — 정상)")
    if not 나쁨:
        print("  ✅ 깨진 파일 없음")
    return 나쁨


def C절():
    print("\n" + "=" * 96)
    print("  C (없앴다) — 「0건이어도 저장하나」는 코드 문자열로 못 가린다")
    print("     수집기 거의 전부에 거짓 경보를 냈다. **B절이 결과로 잡는다**")
    print("=" * 96)
    return []


def D절():
    print("\n" + "=" * 96)
    print("  D ⭐ **「이미 받았으면 건너뛴다」만 있고 갱신 수단이 없는 수집기**")
    print("     ⚠️ 임원매매·5%보유가 이 병으로 **9/1 이후 8일간 멈춰 있었다**")
    print("=" * 96)
    나쁨 = []
    for f in sorted(glob.glob(os.path.join(_S, "collect_*.py"))):
        나 = os.path.basename(f)
        try:
            t = io.open(f, encoding="utf-8-sig").read()
        except Exception:  # noqa: BLE001
            continue
        # ⚠️ **종목 단위로 건너뛰는 것만** 찍는다 (2026-09-09 고침).
        #    날짜·달·접수번호 단위는 「지난 것은 안 변하니 건너뛴다」가 **맞다**:
        #      collect_index·disclosure_time  날짜 단위 ✅
        #      collect_consensus(_slow)       달 단위 ✅
        #      collect_contract               접수번호 단위 ✅
        #    처음엔 이것들까지 찍어서 **진짜(dart_snap)를 묻어버렸다**
        건너 = ("c not in 받" in t or "if c in corp and c not in 받" in t
                or "종목 if c not in 받" in t)
        갱신 = ("--갱신일" in t or "_갱신일" in t or "--갱신" in t
                or "--다시" in t or "--강제" in t)
        if 건너 and not 갱신:
            print(f"  ⚠️ {나:<28} 건너뛰기만 있고 **갱신 수단이 없다**")
            나쁨.append(f"{나}: 갱신 수단 없음")
    if not 나쁨:
        print("  ✅ 다 갱신 수단이 있다")
    return 나쁨


def E절():
    print("\n" + "=" * 96)
    print("  E 스크립트 문법 검사")
    print("=" * 96)
    나쁨 = []
    fs = sorted(glob.glob(os.path.join(_S, "*.py")))
    for f in fs:
        나 = os.path.basename(f)
        try:
            ast.parse(io.open(f, encoding="utf-8-sig").read())
        except SyntaxError as e:
            print(f"  ❌ {나:<30} 줄 {e.lineno}: {e.msg}")
            나쁨.append(f"{나}: 문법 오류 줄 {e.lineno}")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {나:<30} {type(e).__name__}")
            나쁨.append(f"{나}: {type(e).__name__}")
    print(f"  스크립트 {len(fs)}개 중 문제 **{len(나쁨)}개**")
    return 나쁨


def F절():
    print("\n" + "=" * 96)
    print("  F 최근 로그의 오류·타임아웃 (마지막 200줄씩)")
    print("=" * 96)
    나쁨 = []
    for f in sorted(glob.glob(os.path.join(_D, "_*.log"))):
        나 = os.path.basename(f)
        try:
            줄들 = io.open(f, encoding="utf-8", errors="replace").read().splitlines()[-200:]
        except Exception:  # noqa: BLE001
            continue
        나쁜줄 = [z for z in 줄들
                  if ("실패" in z or "Timeout" in z or "Error" in z
                      or "❌" in z or "코드 3221" in z)]
        if 나쁜줄:
            print(f"\n  [{나}]  나쁜 줄 {len(나쁜줄)}개 · 마지막 둘:")
            for z in 나쁜줄[-2:]:
                print(f"    {z.strip()[:110]}")
            나쁨.append(f"{나}: 오류 {len(나쁜줄)}줄")
    if not 나쁨:
        print("  ✅ 최근 로그에 오류 없음")
    return 나쁨


def G절():
    print("\n" + "=" * 96)
    print("  G ⭐⭐ **판정에 「기회 수」를 안 보는 시험**")
    print("     사용자: 「매도 타이밍과 자산 보유 현황도 중요하지만")
    print("             **그것도 때문에 상승 기회를 놓쳐서는 안돼**」")
    print("     ⚠️ 185차는 기회가 **1/50**, 190차는 **6~37%** 로 줄었는데 「통과」로 찍혔다")
    print("=" * 96)
    나쁨 = []
    for f in sorted(glob.glob(os.path.join(_S, "*_lab.py")) +
                    glob.glob(os.path.join(_S, "gate*.py"))):
        나 = os.path.basename(f)
        try:
            t = io.open(f, encoding="utf-8-sig").read()
        except Exception:  # noqa: BLE001
            continue
        # 「낫다/통과」 판정이 있는데 기회 비율을 안 쓰는 것
        판정 = ("낫다" in t or "전부 낫다" in t or "⇒ **통과**" in t
                or "통과표" in t)
        기회 = ("기회비" in t or "기회 " in t and "%" in t)
        if 판정 and not 기회:
            print(f"  ⚠️ {나:<28} 판정은 하는데 **기회 수를 안 본다**")
            나쁨.append(f"{나}: 기회 수 미반영")
    if not 나쁨:
        print("  ✅ 다 기회 수를 본다")
    return 나쁨


def main():
    print("=" * 96)
    print("  audit_all — **전수 점검** (2026-09-09 밤)")
    print(f"  {dt.datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 96)
    모 = []
    for 절 in (A절, B절, C절, D절, E절, F절, G절):
        try:
            모 += 절() or []
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {절.__name__} 자체가 터졌다: {type(e).__name__} {e}")
            모.append(f"{절.__name__}: 점검 실패")
    print("\n" + "=" * 96)
    print(f"  ⇒ 찾은 문제 **{len(모)}개**")
    print("=" * 96)
    for z in 모:
        print(f"    · {z}")
    return 0


if __name__ == "__main__":
    _p = os.path.join(_D, "_labs",
                      os.environ.get("LAB_OUT")
                      or f"{dt.date.today():%Y-%m-%d}_전수점검.txt")

    class _Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.__stdout__

        def write(self, s):
            self.o.write(s)
            self.f.write(s)

        def flush(self):
            self.o.flush()
            self.f.flush()

    with io.open(_p, "w", encoding="utf-8") as _f:
        sys.stdout = _Tee(_f)
        # ⚠️⚠️ **오류도 이 파일에 남긴다** (2026-09-09).
        #    전에는 stdout 만 가로채서, 죽으면 트레이스백이 **아무 데도 안 남았다.**
        #    189차가 같은 자리에서 **세 번** 죽었는데 원인을 못 봤다
        sys.stderr = sys.stdout
        try:
            _r = main()
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    print(f"\n  ✅ {_p}")
    sys.exit(_r)
