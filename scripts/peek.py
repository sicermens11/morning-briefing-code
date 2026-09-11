#!/usr/bin/env python3
r"""
peek.py — **자료를 쓰기 전에 구조부터 찍어본다** (2026-09-04 신설)

## ⚠️⚠️ 왜 만들었나 — 2026-09-04 하루에 같은 실수를 네 번 했다
```
dart-daily      "공시"/"stock_code"로 짐작   -> 실제는 "챙길공시"/"종목코드"
                -> 97차가 **0개**를 파싱하고도 그냥 진행했다
dart-capital    "bddd"만 봄                -> 유상증자 **5,050건**을 통째로 놓쳤다
                (갈래마다 날짜 필드 이름이 다르다: bddd · aq_dd · ...)
krx-daily       "시가총액"으로 짐작          -> 실제는 **"시총"**
index-daily     시가가 있다고 가정           -> **종가·등락률만** 있다
```
⇒ 원인은 하나다. **자료를 안 열어보고 필드명을 짐작했다.**

## 쓰는 법
```
python scripts\peek.py data\dart-daily          폴더의 최신 파일 구조를 찍는다
python scripts\peek.py data\dart-daily --전부   여러 파일을 훑어 **필드가 다른 것**도 찾는다
python scripts\peek.py data\industry.json       파일 하나
python scripts\peek.py --목록                   data 아래 폴더를 다 훑는다
```
⚠️ **새 자료를 처음 쓸 때는 반드시 이걸 먼저 돌린다.**
"""
import collections
import glob
import io
import json
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def 값꼴(v, 길이=70):
    if isinstance(v, dict):
        k = list(v)[:6]
        return f"dict({len(v)}) 키: {k}"
    if isinstance(v, list):
        if not v:
            return "list(0) 비어 있음"
        첫 = v[0]
        if isinstance(첫, dict):
            return f"list({len(v)}) 첫 항목 키: {sorted(첫)[:12]}"
        return f"list({len(v)}) 첫: {str(첫)[:40]}"
    s = str(v)
    return s[:길이] + ("…" if len(s) > 길이 else "")


def 파일찍기(p, 깊이=2):
    print(f"\n  ── {p} ──")
    try:
        d = json.load(io.open(p, encoding="utf-8-sig"))
    except Exception as e:
        print(f"     ⚠️ 못 읽음: {type(e).__name__} {str(e)[:60]}")
        return None
    if isinstance(d, list):
        print(f"     최상위가 **list({len(d)})**")
        if d and isinstance(d[0], dict):
            print(f"     첫 항목 키: {sorted(d[0])}")
        return d
    if not isinstance(d, dict):
        print(f"     최상위가 {type(d).__name__}")
        return d
    print(f"     최상위 키 ({len(d)}개): {list(d)[:10]}")
    for k in list(d)[:8]:
        v = d[k]
        print(f"       {k}: {값꼴(v)}")
        # 한 단계 더
        if 깊이 > 1 and isinstance(v, dict) and v:
            k2 = list(v)[0]
            v2 = v[k2]
            print(f"         └ {k2}: {값꼴(v2)}")
            if isinstance(v2, dict):
                print(f"           키: {sorted(v2)}")
        elif 깊이 > 1 and isinstance(v, list) and v and isinstance(v[0], dict):
            print(f"         └ 첫 항목 전체 키: {sorted(v[0])}")
            # 날짜스러운 필드를 짚어준다 (여기서 자주 틀렸다)
            날 = {kk: vv for kk, vv in v[0].items()
                  if any(w in kk.lower() for w in
                         ("dd", "date", "dt", "ymd", "day", "일", "날"))}
            if 날:
                print(f"           ⭐ 날짜스러운 필드: {날}")
    return d


def 폴더찍기(폴더, 전부=False):
    g = sorted(glob.glob(os.path.join(폴더, "*.json")))
    print(f"\n{'='*78}")
    print(f"  {폴더}  —  파일 {len(g):,}개")
    if not g:
        print("     ⚠️ 비어 있다")
        return
    print(f"     {os.path.basename(g[0])} ~ {os.path.basename(g[-1])}")
    파일찍기(g[-1])
    if not 전부:
        return
    # ⚠️ 파일마다 구조가 다를 수 있다 (갈래마다 필드가 다른 걸 여기서 잡는다)
    키모음 = collections.Counter()
    안쪽키 = collections.Counter()
    본 = g[::max(1, len(g) // 60)][:60]
    for p in 본:
        try:
            d = json.load(io.open(p, encoding="utf-8-sig"))
        except Exception:
            continue
        if isinstance(d, dict):
            키모음["|".join(sorted(d))] += 1
            for k, v in d.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    for it in v[:3]:
                        안쪽키[f"{k}: " + "|".join(sorted(it))] += 1
    print(f"\n     ── {len(본)}개 파일을 훑어본 결과 ──")
    print(f"     최상위 구조 갈래 {len(키모음)}가지")
    for s, n in 키모음.most_common(4):
        print(f"       ({n:>3}회) {s[:100]}")
    if 안쪽키:
        print(f"     목록 안쪽 구조 갈래 {len(안쪽키)}가지")
        for s, n in 안쪽키.most_common(6):
            print(f"       ({n:>3}회) {s[:110]}")
        if len(안쪽키) > 1:
            print("       ⚠️⚠️ **구조가 여러 가지다.** 한 갈래만 보고 파싱하면 놓친다")


def main():
    전부 = "--전부" in sys.argv
    인자 = [a for a in sys.argv[1:] if not a.startswith("--")]

    if "--목록" in sys.argv or not 인자:
        d = os.path.join(_BASE, "data")
        print(f"{'='*78}")
        print(f"  data 아래 폴더 (파일 많은 순)")
        print(f"{'='*78}")
        줄 = []
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if os.path.isdir(p):
                n = len(glob.glob(os.path.join(p, "*.json")))
                줄.append((n, name))
        for n, name in sorted(줄, reverse=True):
            if n:
                print(f"    {n:>7,}개  data/{name}")
        홑 = [f for f in sorted(os.listdir(d))
              if f.endswith(".json") and os.path.isfile(os.path.join(d, f))]
        if 홑:
            print(f"\n    낱개 파일: {', '.join(홑[:12])}")
        print(f"\n  쓰는 법: python scripts\\peek.py data\\<폴더> [--전부]")
        return 0

    for a in 인자:
        p = a if os.path.isabs(a) else os.path.join(_BASE, a)
        if os.path.isdir(p):
            폴더찍기(p, 전부)
        elif os.path.exists(p):
            파일찍기(p)
        else:
            print(f"  ⚠️ 없다: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
