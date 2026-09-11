#!/usr/bin/env python3
r"""
config.py — API 키 로더 (2026-08-25 신설)

키를 코드나 SKILL.md에 박지 않는다. 이유:
  - SKILL.md는 매 실행마다 모델 컨텍스트로 통째로 들어간다. 거기 키를 두면 매일 노출된다.
  - 스크립트에 박으면 파일을 공유하거나 백업할 때 같이 새어나간다.

읽는 순서(먼저 찾은 것을 쓴다):
  1. 환경변수  (예: DART_API_KEY)
  2. `data\secrets.json`  — 이 PC에만 두는 로컬 파일

`data\secrets.json` 형식:
    {
      "DART_API_KEY": "발급받은 40자리 키"
    }

⚠️ 이 파일은 백업·공유 대상에서 빼는 것이 안전하다.
"""
import json
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SECRETS = os.path.join(_BASE, "data", "secrets.json")

_cache = None


def _load_file() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if os.path.exists(_SECRETS):
        try:
            with open(_SECRETS, "r", encoding="utf-8-sig") as fp:
                _cache = json.load(fp)
        except Exception:
            # 파일이 깨져 있어도 죽지 않는다 — 환경변수 경로가 남아 있다.
            _cache = {}
    else:
        _cache = {}
    return _cache


def get(name: str, default=None):
    """환경변수 우선, 없으면 secrets.json에서 찾는다."""
    v = os.environ.get(name)
    if v:
        return v.strip()
    v = _load_file().get(name)
    return v.strip() if isinstance(v, str) and v.strip() else default


def require(name: str) -> str:
    """없으면 사람이 읽을 수 있는 안내와 함께 예외를 던진다."""
    v = get(name)
    if not v:
        raise RuntimeError(
            f"{name}가 설정되지 않았습니다. "
            f"환경변수로 넣거나 {_SECRETS} 에 "
            f'{{"{name}": "..."}} 형태로 저장하세요.'
        )
    return v


if __name__ == "__main__":
    # 진단용: 어떤 키가 잡히는지 확인한다. 값은 절대 출력하지 않고 존재 여부와 길이만 보여준다.
    names = ["DART_API_KEY"]
    out = {}
    for n in names:
        v = get(n)
        out[n] = {"설정됨": bool(v), "길이": len(v) if v else 0,
                  "출처": "환경변수" if os.environ.get(n) else ("secrets.json" if v else "없음")}
    print(json.dumps({"secrets_path": _SECRETS, "keys": out}, ensure_ascii=False, indent=2))
