#!/usr/bin/env python3
"""
check_jargon.py - morning-sector-briefing 용어/출처링크/내부코드명 검산 스크립트
(2026-08-12 신설 DECISIONS.md 121차, 2026-08-13 내부코드명 검사·text모드·GLOSSARY확장 DECISIONS.md 123차,
 2026-08-18 판정로직 강화 DECISIONS.md 125차)

목적: STEP5(Gmail HTML)·STEP7(카카오 텍스트)에서 완성한 본문을 LLM이 다시 통째로 훑는 대신,
스크립트가 기계적으로 (1) 화이트리스트에 없는 전문용어가 괄호설명 없이 등장했는지,
(2) 출처링크 필수 카테고리(HTML 전용)에 링크/[출처 미확인]이 빠졌는지,
(3) 내부 코드명(F1/F2/D1·강화-*·MCP-*·조건부-*·검색* 등)이 본문에 그대로 노출됐는지를
찾아 좌표(문맥)만 반환한다. 실제 문구 수정은 LLM이 한다.

설계 원칙:
- 화이트리스트(WHITELIST): 설명 없이 써도 되는 기초 용어. 여기 없으면 기본값은 "설명 필요".
- 용어집(GLOSSARY): 이미 확인된 어려운 용어 -> 쉬운 설명. 새 용어가 나올 때마다 이 dict에
  추가하면 됨(반기 정비 또는 발견 즉시). 화이트리스트 방식이 아니라 "여기 없어도 대문자
  약어처럼 보이면 일단 걸어서 보여주는" 정규식 후보 방식과 병행 - 신규 용어도 잡히게 함.
- 정규식 후보: 화이트리스트/용어집 어디에도 없는 신규 영문약어·티커 패턴을 기계적으로 잡아냄
  (한글 전문용어는 정규식으로 못 잡으므로 용어집 등재가 유일한 방법 - 한계로 문서화).
- 내부코드명(INTERNAL_CODE_PATTERNS): "설명이 있냐 없냐"와 무관하게 절대 노출되면 안 되는
  내부 도구 코드명 - 발견 즉시 무조건 플래그(2026-08-13 F2/VAL/RISK 등이 카카오 본문에
  그대로 노출된 실제 사고 계기로 신설).
- 입력 채널 2종: html(STEP5 Gmail, 태그 제거+링크검사 포함) / text(STEP7 카카오, 이미 순수
  텍스트라 링크검사 생략) - 둘 다 용어검사·내부코드명검사는 동일하게 적용.
- 의존성: 표준 라이브러리만 사용(compute_ta.py와 동일 원칙, 별도 패키지 설치 불필요).

2026-08-18(125차) 변경 사항 — 08-12 실측 감사(08-12 발송 메일에서 VIX·VKOSPI·PER 미설명
사례 실측 확인)로 드러난 판정 로직 구멍 3건 수정:
  1. **단어경계 미적용**: "PER" 같은 짧은 영문 용어가 다른 단어(예: SUPER, PERIOD) 안에서도
     매칭돼, 그 안에서 우연히 "설명됨"으로 처리되면 뒤에 나오는 진짜 위반이 중복제거(seen)에
     막혀 리포트에서 누락될 수 있었음 -> ASCII 용어는 \\b 단어경계를 적용.
  2. **용어집 등재 용어의 중복제거로 반복 위반 은폐**: 기존엔 같은 용어의 "첫 번째 미설명
     등장"만 리포트하고 이후 등장은 전부 건너뜀 -> 이미 한 번 설명됐어도 그 뒤에 다시
     설명없이 나오면(예: PBR 0.94는 설명, PBR 7.05는 무설명) 후자가 놓쳤음. 용어집 등재
     용어는 중복제거 없이 위반 전부 리포트하도록 변경(신규 미등재 용어 후보는 노이즈 방지
     목적으로 기존처럼 첫 등장만 리포트 유지).
  3. **"설명됨" 판정이 내용을 안 봄**: 용어 뒤 괄호 안에 한글이 하나라도 있으면 무조건
     "설명 완료"로 처리해서, "VIX (-1.16%, 안도 구간)"처럼 정의와 무관한 괄호도 통과됐음.
     용어집 등재 용어는 그 용어의 정의 문자열에서 뽑은 키워드가 괄호 안에 실제로 있는지까지
     확인하도록 강화(예: VIX 정의 "시장 공포지수" -> "시장" 또는 "공포지수"가 괄호에 있어야
     통과). 신규 미등재 용어는 정의를 모르므로 기존처럼 "한글 있으면 통과" 유지(한계로 문서화).

입력(stdin, JSON): {"html": "[완성 HTML]"} 또는 {"text": "[완성 순수텍스트]"} 둘 중 하나.

출력(stdout, JSON): {
  "missing_terms": [{"term": str, "context": str}, ...],     # 괄호설명 없이 등장한 용어
  "missing_links": [{"marker_context": str}, ...],            # html 모드 전용, LINK_REQUIRED인데 링크/출처미확인 없음
  "internal_leaks": [{"code": str, "context": str}, ...],     # 내부 코드명이 본문에 그대로 노출
  "error": str|null
}
"""
import sys
import json
import re

# 설명 없이 써도 되는 기초 용어 - 여기 없으면 기본값은 "설명 필요"
WHITELIST = {
    "주가", "매출", "영업이익", "순이익", "배당", "상장", "코스피", "코스닥",
    "시가총액", "거래량", "종가", "시가", "고가", "저가", "등락률", "상한가",
    "하한가", "액면가", "매수", "매도", "증권사", "투자", "기업", "종목",
}

# 이미 확인된 어려운 용어 -> 쉬운 설명(새 용어 발견 시 여기 추가)
# 값은 "정식 정의 + 실전에서 자주 쓰이는 해석어(숫자→의미연결 문장에 등장하는 표현 포함)"를
# 공백으로 나열 - has_glossary_explanation()이 이 중 하나라도 괄호 안에 있으면 통과시킨다
# (2026-08-18, 125차: 정의 문자열 그대로만 요구하면 SKILL.md 86행 예시 "PBR 0.8배(장부가치보다
# 20% 싸게 거래 중 — 저평가 신호)"조차 "주가순자산비율"이라는 리터럴이 없어 오탐 처리되는
# 문제를 실측으로 확인, 주요 용어에 해석어를 보강).
GLOSSARY = {
    "VIX": "시장 공포지수 변동성 안정 불안 공포",
    "SPY": "미국 S&P500 지수 추종 ETF",
    "QQQ": "나스닥100 지수 추종 ETF",
    "^NDX": "나스닥100 지수",
    "NDX": "나스닥100 지수",
    "WTI": "국제 유가 기준이 되는 미국산 원유",
    "Nikkei": "일본 대표 주가지수",
    "니케이": "일본 대표 주가지수",
    "VKOSPI": "코스피 변동성지수 공포지수 변동성 안정 불안",
    "EWY": "한국 증시를 추종하는 미국 상장 ETF",
    "CAGR": "연평균 성장률",
    "이자보상배율": "영업이익으로 이자를 몇 배 감당 가능한지 나타내는 지표 이자 감당",
    "PER": "주가수익비율 이익 대비 수익 대비 배수 고평가 저평가",
    "PBR": "주가순자산비율 장부가치 장부가 순자산 저평가 고평가",
    "PEG": "주가수익성장비율 이익성장 대비 성장 대비 저평가 고평가",
    "ROE": "자기자본이익률 자기자본 대비 수익성 효율",
    "RSI": "상대강도지수 과매수 과매도 판단 지표",
    "MACD": "이동평균수렴확산지수 추세 전환 지표",
    "ISM": "공급관리협회 지수",
    "NFP": "비농업고용지수",
    "PMI": "구매관리자지수",
    "CPI": "소비자물가지수",
    "PCE": "개인소비지출물가지수",
    "FOMC": "미국 연방공개시장위원회",
    "골든크로스": "단기 이동평균선이 장기 이동평균선을 상향 돌파 상승전환 신호",
    "데드크로스": "단기 이동평균선이 장기 이동평균선을 하향 돌파 하락전환 신호",
    "자본잠식": "누적손실로 자본금이 잠식된 상태",
    "볼린저밴드": "20일 평균 기준 상하 변동폭 지표",
    "컨센서스": "시장 전문가 평균 예상치",
    "목표주가": "애널리스트가 제시하는 적정 주가",
    # 2026-08-13 추가 (실측 누락 사례 기반)
    "CapEx": "설비투자",
    "OpEx": "운영비용",
    "FCF": "잉여현금흐름",
    "MSCI": "세계 주요 주가지수 산출기관(지수 편입 여부가 외국인 자금 유출입에 영향)",
    "제로트러스트": "모든 접근을 기본적으로 신뢰하지 않고 매번 검증하는 보안 체계",
    "NAC": "네트워크 접근제어(비인가 기기 차단 보안기술)",
    "CMP": "반도체 표면을 화학·물리적으로 평탄화하는 연마 공정·장비",
    # 2026-08-21 추가 (강화-TA 확장: 거래량·지지저항·ATR·캔들패턴, DECISIONS.md 137차)
    "ATR": "평균진폭 최근 일정기간 하루 평균 가격변동폭 변동성 지표",
    "지지선": "주가가 잘 안 뚫고 내려가는 가격대",
    "저항선": "주가가 잘 못 뚫고 올라가는 가격대",
    "장악형": "오늘 캔들 몸통이 어제 캔들 몸통을 반대방향으로 완전히 감싸는 추세전환 캔들패턴",
    "마루보즈": "꼬리가 거의 없이 시가부터 종가까지 한 방향으로 쭉 밀린 캔들패턴 강한 확신",
    "도지": "시가와 종가가 거의 같아 매수·매도가 팽팽히 맞선 캔들패턴",
}

# 정규식으로 잡는 후보 패턴(영문약어·티커류) - 화이트리스트/용어집에 이미 있으면 제외
TICKER_LIKE = re.compile(r"\b[A-Z]{2,6}\b|\b\d{4,6}\.[A-Z]{2}\b|\^[A-Z]{2,5}\b")

# 화이트리스트로 취급할 일반적인 영문 대문자 토큰(오탐 방지 - 브랜드명/고유명사 등)
COMMON_SAFE_CAPS = {"IT", "AI", "GDP", "CEO", "CFO", "ETF", "IPO", "M", "B", "T", "USD", "KRW"}

# 내부 도구 코드명 패턴 - 설명 유무와 무관하게 본문에 절대 노출되면 안 됨(2026-08-13 신설)
# 계기: 카카오 본문에 "F2:", "RISK무결", "VAL낙관(...)", "galp 4/4" 등이 그대로 노출된 실측 사고.
INTERNAL_CODE_PATTERNS = [
    re.compile(r"강화-[A-Z0-9]+"),
    re.compile(r"조건부-[A-Z0-9]+"),
    re.compile(r"\bMCP-(?:GLOBAL|SEASON|DAYCHECK|\d{1,2})\b"),
    re.compile(r"검색\d[a-zA-Z]?(?:-[A-Z])?"),
    re.compile(r"\b정책\d\b"),
    re.compile(r"\bgalp\b", re.IGNORECASE),
    re.compile(r"\b[FD]\d\b"),  # F1/F2/D1/D2 등 내부 스텝 코드(강화- 접두어 없이도 단독 노출됨)
    re.compile(r"\b(?:CAP|VAL|RISK|TA|QUANT|BUYBACK|PREF|OWNERSHIP|MACRO|ANCHOR)\b"),
    # ⚠️ Cowork 병행 실행 시절의 구분 마커. 2026-08-25 폐지됐는데 모델이 08-25·08-26
    #    이틀 연속 카카오 첫 줄과 Gmail 제목에 도로 붙였다. 여기 없어서 검산을 통과했다.
    re.compile(r"\[코드\]"),
]


def strip_html(html: str) -> str:
    text = re.sub(r"<!--LINK_REQUIRED-->", "\x00LINKMARK\x00", html)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def _definition_keywords(definition: str):
    """정의 문자열에서 2글자 이상 토큰만 키워드 후보로 추출 (2026-08-18 신설)."""
    tokens = re.split(r"[^\w가-힣]+", definition)
    return [t for t in tokens if len(t) >= 2]


def check_terms(text: str):
    """text는 이미 태그가 제거된(또는 애초에 태그가 없는) 평문이어야 함."""
    missing = []
    seen_candidates = set()  # 정규식 후보(신규 미등재 용어)에만 적용하는 중복제거

    TAIL_WINDOW = 40
    KOREAN_RE = re.compile(r"[가-힣]")
    PAREN_RE = re.compile(r"\(([^()]*)\)")
    SENTENCE_END_RE = re.compile(r"[.!?\n](?!\d)")

    def scope_of(window: str) -> str:
        boundary = SENTENCE_END_RE.search(window)
        return window[:boundary.start()] if boundary else window

    def has_loose_explanation(window: str) -> bool:
        """신규 미등재 용어용: 괄호 안에 한글이 있으면 통과(정의를 모르므로 이게 한계)."""
        for pm in PAREN_RE.finditer(scope_of(window)):
            if KOREAN_RE.search(pm.group(1)):
                return True
        return False

    def has_glossary_explanation(window: str, definition: str) -> bool:
        """용어집 등재 용어용: 괄호 안에 그 용어 정의의 키워드가 실제로 있어야 통과
        (2026-08-18 강화 — 이전엔 아무 한글이나 있으면 통과라 "VIX (안도 구간)" 같은
        무관한 괄호도 설명으로 잘못 인정했음)."""
        keywords = _definition_keywords(definition)
        for pm in PAREN_RE.finditer(scope_of(window)):
            content = pm.group(1)
            if not KOREAN_RE.search(content):
                continue
            if any(kw in content for kw in keywords):
                return True
        return False

    # 1) 용어집(GLOSSARY) 등재 용어 - 중복제거 없이 위반 전부 리포트(2026-08-18 변경)
    for term, definition in GLOSSARY.items():
        pattern = re.compile(r"\b" + re.escape(term) + r"\b") if term.isascii() else re.compile(re.escape(term))
        for m in pattern.finditer(text):
            start, end = m.span()
            window = text[end:end + TAIL_WINDOW]
            if has_glossary_explanation(window, definition):
                continue
            context = text[max(0, start - 20):end + 20].strip()
            missing.append({"term": term, "context": context})

    # 2) 정규식 후보(화이트리스트/용어집에 없는 신규 영문약어·티커) - 첫 등장만 리포트(노이즈 방지 유지)
    for m in TICKER_LIKE.finditer(text):
        token = m.group()
        if token in COMMON_SAFE_CAPS or token in WHITELIST or token in GLOSSARY:
            continue
        start, end = m.span()
        window = text[end:end + TAIL_WINDOW]
        if has_loose_explanation(window):
            continue
        key = token
        if key in seen_candidates:
            continue
        seen_candidates.add(key)
        context = text[max(0, start - 20):end + 20].strip()
        missing.append({"term": token, "context": context, "source": "regex_candidate"})

    return missing


def check_internal_leak(text: str):
    leaks = []
    seen = set()
    for pattern in INTERNAL_CODE_PATTERNS:
        for m in pattern.finditer(text):
            token = m.group()
            if token in seen:
                continue
            seen.add(token)
            start, end = m.span()
            context = text[max(0, start - 20):end + 20].strip()
            leaks.append({"code": token, "context": context})
    return leaks


def check_links(html: str):
    missing = []
    parts = html.split("<!--LINK_REQUIRED-->")
    for segment in parts[1:]:
        window = segment[:400]
        has_link = "<a href" in window
        has_unconfirmed = "[출처 미확인]" in window
        if not has_link and not has_unconfirmed:
            plain = re.sub(r"<[^>]+>", " ", window[:120]).strip()
            missing.append({"marker_context": plain})
    return missing


def _load_payload():
    """입력 소스 결정. 반환값 (payload, error_message).

    2026-08-21 추가 — Windows(PowerShell) 환경 이식용. 세 가지 호출 방식을 지원한다:
      1. `--html-file <경로>` : 파일 내용을 **그대로** html로 취급(JSON 이스케이프 불필요)
      2. `--text-file <경로>` : 파일 내용을 그대로 text로 취급(카카오 본문용)
      3. 인자 없음            : 기존 stdin JSON({"html":...} 또는 {"text":...})
    1·2번이 Windows용으로 신설된 경로다. PowerShell엔 bash heredoc이 없어서 완성 HTML을
    JSON 문자열로 감싸 stdin에 밀어넣으려면 따옴표·역슬래시·개행을 전부 이스케이프해야
    하는데, 이게 실무에서 가장 잘 깨지는 지점이다. 원문을 파일에 그대로 쓰고 경로만
    넘기면 이스케이프 자체가 사라진다. 기존 stdin 방식은 유지되므로 Cowork 호출은 무영향.
    """
    argv = sys.argv[1:]
    for flag, field in (("--html-file", "html"), ("--text-file", "text")):
        if flag in argv:
            path = argv[argv.index(flag) + 1]
            try:
                # utf-8-sig: PowerShell이 붙이는 UTF-8 BOM을 제거한다. 그냥 utf-8로 읽으면
                # BOM이 본문 첫 글자로 남아 문서 맨 앞 용어의 단어경계 판정을 흔든다.
                with open(path, "r", encoding="utf-8-sig") as fp:
                    return {field: fp.read()}, None
            except Exception as e:
                return None, f"입력 파일 읽기 실패({path}): {e}"
    try:
        return json.loads(sys.stdin.read()), None
    except Exception as e:
        return None, f"입력 JSON 파싱 실패: {e}"


def main():
    payload, load_error = _load_payload()
    if load_error:
        print(json.dumps({"missing_terms": [], "missing_links": [], "internal_leaks": [],
                           "error": load_error}, ensure_ascii=False))
        return

    is_html = bool(payload.get("html"))
    raw_content = payload.get("html") or payload.get("text") or ""
    if not raw_content:
        print(json.dumps({"missing_terms": [], "missing_links": [], "internal_leaks": [],
                           "error": "html 또는 text 필드가 비어있음"}, ensure_ascii=False))
        return

    try:
        plain_text = strip_html(raw_content)  # text 모드여도 무해(태그 없으면 그대로 통과)
        missing_terms = check_terms(plain_text)
        internal_leaks = check_internal_leak(plain_text)
        missing_links = check_links(raw_content) if is_html else []
        print(json.dumps({
            "missing_terms": missing_terms,
            "missing_links": missing_links,
            "internal_leaks": internal_leaks,
            "error": None,
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"missing_terms": [], "missing_links": [], "internal_leaks": [],
                           "error": f"계산오류: {type(e).__name__}: {e}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
