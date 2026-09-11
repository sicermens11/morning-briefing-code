#!/usr/bin/env python3
r"""
build_archive.py — 브리핑 아카이브 HTML 조립 (2026-08-27 신설)

왜 만드나:
  브리핑 HTML(34,695자)이 **두 번 출력**되고 있다 —
    ① `Write`로 briefing.html 에 쓸 때 (검산 스크립트가 읽어야 하므로 필요)
    ② `update_draft(htmlBody="...")` 로 Gmail에 넘길 때 (MCP가 문자열만 받으므로)
  2026-08-27 실측: 전체 출력 100,370토큰 중 약 35,000토큰(35%)이 이 중복이고,
  초당 약 74토큰이므로 **약 8분**이다.

  이 스크립트가 그 중복을 없앤다. 모델은 **오늘 브리핑을 한 번만** 쓰고,
  나머지(껍데기·날짜 목록·과거분 유지)는 스크립트가 파일에서 파일로 옮긴다.
  ⚠️ **모델이 옮겨 적으면 그게 곧 실행 시간이다.**

무엇을 하나:
  `data\briefings\YYYY-MM-DD.html` 들을 모아 **고정 링크 한 개짜리 아카이브**를 만든다.
  열면 최신 날짜가 바로 보이고, 상단 날짜 칩으로 과거를 오간다.

사용:
    run-py.ps1 -Script build_archive.py -Args @('--add','2026-08-27','--html','<경로>')
    run-py.ps1 -Script build_archive.py -Args @('--build')     # 아카이브만 다시 조립

⚠️ 브리핑 본문은 **인라인 스타일 전용**이다(Gmail 제약). 색이 밝은 쪽에 고정돼 있어
   아카이브 껍데기가 다크 모드여도 본문 카드는 흰 바탕을 유지한다 — 의도된 것이다.
"""
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DAYS_DIR = os.path.join(_DATA, "briefings")
OUT = os.path.join(_DATA, "briefing-archive.html")
URL_FILE = os.path.join(_DATA, "archive-url.txt")

WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]

SHELL_HEAD = """<title>모닝 섹터 브리핑</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root{
  --chrome:#101519; --chrome-2:#182026; --chrome-line:#26313A;
  --on-chrome:#E8EEF2; --on-chrome-dim:#94A5B0;
  --accent:#63B3D8; --paper:#FFFFFF; --page:#F2F5F7;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){ --page:#0A0E11; }
}
:root[data-theme="dark"]{ --page:#0A0E11; }

*{box-sizing:border-box}
body{
  margin:0;background:var(--page);color:var(--on-chrome);
  font-family:"Gothic A1","Malgun Gothic",sans-serif;-webkit-font-smoothing:antialiased;
}

/* ── 상단 고정 크롬 ── */
.top{
  position:sticky;top:0;z-index:20;background:var(--chrome);
  border-bottom:1px solid var(--chrome-line)
}
.bar{
  max-width:960px;margin:0 auto;padding:14px 20px 0;
  display:flex;align-items:baseline;gap:12px;flex-wrap:wrap
}
.bar h1{
  font-size:17px;font-weight:800;margin:0;letter-spacing:-.02em;color:var(--on-chrome)
}
.bar .sub{
  font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.08em;
  color:var(--on-chrome-dim);text-transform:uppercase
}
.days{
  max-width:960px;margin:0 auto;padding:12px 20px;display:flex;gap:7px;
  overflow-x:auto;scrollbar-width:thin
}
.day{
  flex:none;border:1px solid var(--chrome-line);background:var(--chrome-2);
  color:var(--on-chrome-dim);border-radius:3px;padding:7px 13px;cursor:pointer;
  font-family:"JetBrains Mono",monospace;font-size:12px;line-height:1.3;
  white-space:nowrap;transition:border-color .12s,color .12s
}
.day b{display:block;font-size:13px;font-weight:600;color:var(--on-chrome)}
.day span{font-size:10.5px;letter-spacing:.04em}
.day:hover{border-color:var(--accent)}
.day[aria-selected="true"]{border-color:var(--accent);color:var(--accent);background:#12222B}
.day[aria-selected="true"] b{color:var(--accent)}
.day:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* ── 본문 ── */
main{max-width:960px;margin:0 auto;padding:26px 20px 80px}
.sheet{display:none}
.sheet[data-active="true"]{display:block}
.stamp{
  font-family:"JetBrains Mono",monospace;font-size:11.5px;letter-spacing:.1em;
  color:var(--on-chrome-dim);text-transform:uppercase;margin:0 0 12px
}
/* ── 가로 카드뉴스 ─────────────────────────────────────────────
   좌우로 넘긴다. 폰에서는 손가락으로 밀고, PC에서는 ←/→ 키나 아래 화살표 버튼.
   ⚠️ 카드가 화면보다 길 수 있으므로 **카드 안쪽은 세로 스크롤**을 따로 준다.
      가로 스냅과 세로 스크롤이 서로 안 싸우게 축을 분리한 것이다. */
.cards{
  display:flex;overflow-x:auto;overflow-y:hidden;
  scroll-snap-type:x mandatory;scroll-behavior:smooth;
  gap:16px;padding-bottom:8px;
  scrollbar-width:none;-ms-overflow-style:none
}
.cards::-webkit-scrollbar{display:none}
.card{
  flex:0 0 100%;scroll-snap-align:center;scroll-snap-stop:always;
  display:flex;flex-direction:column;min-width:0;
  height:calc(100dvh - 190px);min-height:340px
}
.card-h{
  display:flex;align-items:baseline;gap:10px;margin:0 0 9px;flex:none;
  font-family:"JetBrains Mono",monospace
}
.card-h .n{
  font-size:11px;font-weight:600;color:var(--accent);letter-spacing:.1em;
  font-variant-numeric:tabular-nums
}
.card-h .t{
  font-family:"Gothic A1",sans-serif;font-size:15px;font-weight:600;
  color:var(--on-chrome);letter-spacing:-.01em
}
/* ── 넘기기 조작 ── */
.nav{
  position:sticky;bottom:0;z-index:12;background:var(--chrome);
  border-top:1px solid var(--chrome-line);
  display:flex;align-items:center;justify-content:center;gap:14px;padding:11px 20px
}
.nav button{
  background:var(--chrome-2);border:1px solid var(--chrome-line);color:var(--on-chrome);
  border-radius:3px;padding:7px 15px;cursor:pointer;font-size:15px;line-height:1;
  font-family:"JetBrains Mono",monospace
}
.nav button:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
.nav button:disabled{opacity:.32;cursor:default}
.nav button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.dots{display:flex;gap:6px;align-items:center}
.dots i{
  width:6px;height:6px;border-radius:50%;background:var(--chrome-line);
  transition:background .15s,transform .15s;display:block
}
.dots i.on{background:var(--accent);transform:scale(1.45)}
.pos{
  font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--on-chrome-dim);
  font-variant-numeric:tabular-nums;min-width:52px;text-align:center
}

/* 브리핑 본문은 인라인 스타일(밝은색 고정)이라 항상 흰 종이 위에 올린다 */
.paper{
  flex:1 1 auto;overflow-y:auto;overscroll-behavior:contain;
  background:var(--paper);color:#1a252f;border-radius:4px;padding:22px;
  line-height:1.65;
  font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-size:14px;
  box-shadow:0 1px 3px rgba(0,0,0,.18)
}
/* ── 모바일 교정 ────────────────────────────────────────────────
   브리핑 본문은 **Gmail용 테이블 레이아웃 + 인라인 스타일**이다. 폭이 px로 박혀 있어
   좁은 화면에서 글자가 한두 자씩 끊겨 내려간다(2026-08-27 사용자 확인).
   원본을 고치면 Gmail이 깨지므로 **여기서만 덮어쓴다.** `!important`가 필요한 이유는
   원본이 전부 인라인 style 속성(248개)이기 때문이다 — 선택자 우선순위로는 못 이긴다. */
.paper table{max-width:100%!important;width:100%!important;table-layout:auto!important}
.paper td,.paper th{
  word-break:keep-all;overflow-wrap:anywhere;
  min-width:0!important;white-space:normal!important
}
.paper img{max-width:100%;height:auto}
.paper div,.paper p,.paper span{max-width:100%!important}
@media(max-width:640px){
  .paper{padding:14px;font-size:15px}
  /* 2열 이상 표는 세로로 편다 — 폰에서 가로 스크롤보다 읽기 쉽다 */
  .paper table,.paper tbody,.paper tr,.paper td,.paper th{
    display:block!important;width:auto!important
  }
  .paper tr{border-bottom:1px solid #e5e9ec;padding:6px 0}
  .paper tr:last-child{border-bottom:none}
  .paper td,.paper th{padding:3px 0!important;text-align:left!important}
}
.note{
  background:var(--chrome-2);border-left:2px solid var(--accent);
  padding:14px 18px;border-radius:3px;color:var(--on-chrome-dim);font-size:13.5px
}
.note b{color:var(--on-chrome)}
footer{
  max-width:960px;margin:0 auto;padding:0 20px 60px;
  font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--on-chrome-dim);line-height:1.9
}
</style>
"""

SHELL_SCRIPT = """<script>
(function(){
  var chips = Array.prototype.slice.call(document.querySelectorAll('.day'));
  var sheets = Array.prototype.slice.call(document.querySelectorAll('.sheet'));
  function show(d){
    chips.forEach(function(c){ c.setAttribute('aria-selected', String(c.dataset.d === d)); });
    sheets.forEach(function(s){ s.setAttribute('data-active', String(s.dataset.d === d)); });
    try { localStorage.setItem('briefing-day', d); } catch(e) {}
    window.scrollTo({top:0, behavior:'instant'});
  }
  chips.forEach(function(c){
    c.addEventListener('click', function(){ show(c.dataset.d); });
    c.addEventListener('keydown', function(e){
      if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); show(c.dataset.d); }
    });
  });
  // 마지막으로 보던 날짜를 기억하되, 없거나 사라졌으면 최신으로.
  var want = null;
  try { want = localStorage.getItem('briefing-day'); } catch(e) {}
  var ok = chips.some(function(c){ return c.dataset.d === want; });
  show(ok ? want : (chips[0] && chips[0].dataset.d));

  // ── 가로 넘기기 ────────────────────────────────────────────────
  var dots = document.querySelector('.dots');
  var pos  = document.querySelector('.pos');
  var prev = document.querySelector('.nav .prev');
  var next = document.querySelector('.nav .next');

  function rail(){ return document.querySelector('.sheet[data-active="true"]'); }
  function cardsOf(r){ return r ? Array.prototype.slice.call(r.querySelectorAll('.card')) : []; }

  function index(){
    var r = rail(); if(!r) return 0;
    // 가장 왼쪽에 가까운 카드가 지금 카드다. 스냅이 center라 반 칸 보정한다.
    return Math.round(r.scrollLeft / (r.clientWidth + 16));
  }
  function go(i){
    var r = rail(); if(!r) return;
    var n = cardsOf(r).length;
    i = Math.max(0, Math.min(n - 1, i));
    r.scrollTo({left: i * (r.clientWidth + 16), behavior:'smooth'});
  }
  function paint(){
    var r = rail(); if(!r) return;
    var n = cardsOf(r).length, i = Math.max(0, Math.min(n - 1, index()));
    if(dots && dots.childElementCount !== n){
      dots.innerHTML = Array(n).join(',').split(',').map(function(){ return '<i></i>'; }).join('');
    }
    if(dots) Array.prototype.forEach.call(dots.children, function(el, k){
      el.className = (k === i) ? 'on' : '';
    });
    if(pos) pos.textContent = (i + 1) + ' / ' + n;
    if(prev) prev.disabled = (i <= 0);
    if(next) next.disabled = (i >= n - 1);
  }

  if(prev) prev.addEventListener('click', function(){ go(index() - 1); });
  if(next) next.addEventListener('click', function(){ go(index() + 1); });
  document.addEventListener('keydown', function(e){
    if(e.key === 'ArrowRight'){ go(index() + 1); }
    else if(e.key === 'ArrowLeft'){ go(index() - 1); }
  });
  // 스크롤 중 갱신 — rAF로 묶어 과하게 안 돌게 한다.
  var tick = false;
  function onScroll(){
    if(tick) return;
    tick = true;
    requestAnimationFrame(function(){ paint(); tick = false; });
  }
  sheets.forEach(function(s){ s.addEventListener('scroll', onScroll, {passive:true}); });
  window.addEventListener('resize', paint);
  chips.forEach(function(c){ c.addEventListener('click', function(){ setTimeout(paint, 60); }); });
  paint();
})();
</script>
"""


def _days():
    """저장된 날짜별 브리핑을 최신순으로."""
    if not os.path.isdir(DAYS_DIR):
        return []
    out = []
    for f in sorted(os.listdir(DAYS_DIR), reverse=True):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\.html$", f)
        if m:
            out.append((m.group(1), os.path.join(DAYS_DIR, f)))
    return out


# ⚠️ **카드 순서는 브리핑 원본 순서를 그대로 따른다** (2026-08-27 사용자 결정).
#    한때 액션플랜을 맨 앞으로 끌어올렸다가 되돌렸다 — 원본은 근거를 쌓고 결론을 내는
#    순서로 쓰여 있고, 결론만 먼저 보면 왜 그 등급인지가 사라진다.
#    "오늘 뭘 살까"만 급할 때는 **카카오톡 요약**이 그 역할을 한다.
EXCLUDE = ["실행 로그"]   # Artifact·인스타에는 안 싣는다. 사람이 읽을 내용이 아니다.
# 구획 주석 이름 → 카드 제목. 없으면 주석 이름을 그대로 쓴다.
TITLE = {
    "⑥ 액션플랜": "액션플랜", "① 시장 한눈에": "시장 한눈에", "② 근거 데이터": "근거 데이터",
    "③ 국장 수급": "국장 수급", "⑤ 기관 의견 & 애널리스트": "기관 의견",
}


def _cards(body: str):
    r"""브리핑 HTML을 구획 주석으로 잘라 카드 목록으로 만든다. (2026-08-27 신설)

    브리핑은 `<!-- ===== ① 시장 한눈에 ===== -->` 꼴 주석으로 구획이 나뉘어 있다.
    그 위치에서 자르면 원본을 한 글자도 다시 쓰지 않고 카드가 된다.

    ⚠️ **원본 순서를 지킨다**(①시장→②근거→③수급→⑤의견→⑥액션플랜→후보들).
       브리핑은 근거를 쌓고 결론을 내는 순서로 쓰여 있다. 결론만 앞으로 빼면
       왜 그 등급인지가 사라진다. 급할 때는 카카오톡 요약이 그 역할을 한다.
    ⚠️ `EXCLUDE`에 든 구획(실행 로그)은 뺀다. 도구 호출수·실패 기록은 사람이 읽을 것이 아니다.
    ⚠️ 주석이 없거나 못 자르면 **통째로 한 장**으로 둔다. 억지로 쪼개서 내용을 잃지 않는다.
    """
    marks = [(m.start(), m.group(1).strip())
             for m in re.finditer(r"<!--\s*=*\s*([^=\-][^-]*?)\s*=*\s*-->", body)
             if m.group(1).strip()]
    if len(marks) < 2:
        return [("브리핑", body)]
    out = []
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        chunk = body[pos:end].strip()
        if len(re.sub(r"<[^>]+>", "", chunk).strip()) < 30:
            continue                      # 알맹이 없는 구획은 버린다
        # ⚠️ **앞부분 일치**로 본다. 정확히 같은지 보면 안 된다 —
        #    구획 이름이 `⑤ 기관 의견 & 애널리스트`처럼 꼬리가 붙는 경우가 있다.
        if any(name.startswith(x) for x in EXCLUDE):
            continue
        title = next((v for k, v in TITLE.items() if name.startswith(k)), name)
        out.append((title, chunk))
    return out


def _headline(html: str) -> str:
    r"""날짜 칩에 붙일 한 줄 — 채택 후보의 등급 배지와 종목명.

    ⚠️ **종목코드를 먼저 찾고 거꾸로 배지를 본다.** 배지에서 앞으로 훑는 방식은 실패한다 —
       실제 본문이 `🟡 점검 (국내 연관) 디아이 (003160)` 꼴이라 배지와 종목명 사이에
       `(국내 연관)` 같은 꼬리표가 끼기 때문이다. 2026-08-27 실측에서 후보 4개가 전부
       안 잡히고 "관망"으로 나왔다.
    """
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    seen, out = set(), []
    for m in re.finditer(r"([가-힣A-Za-z0-9]{2,16})\s*\((\d{6})\)", text):
        name = m.group(1)
        if name in seen:
            continue
        # 이름 앞 60자 안에서 **가장 가까운** 배지를 찾는다.
        before = text[max(0, m.start() - 60):m.start()]
        badges = re.findall(r"[🔴🟢🟡]", before)
        if not badges:
            continue
        seen.add(name)
        if len(out) < 2:
            out.append(badges[-1] + name)
    if not out:
        return "관망"
    return " · ".join(out) + (f" 외 {len(seen) - len(out)}" if len(seen) > len(out) else "")


def build() -> dict:
    days = _days()
    if not days:
        return {"error": f"저장된 브리핑이 없다: {DAYS_DIR}"}

    chips, sheets = [], []
    for i, (d, path) in enumerate(days):
        body = io.open(path, encoding="utf-8-sig").read()
        dt = datetime.strptime(d, "%Y-%m-%d")
        label = f"{dt.month:02d}/{dt.day:02d}"
        wd = WEEKDAY[dt.weekday()]
        head = _headline(body)
        sel = "true" if i == 0 else "false"
        chips.append(
            f'<button class="day" data-d="{d}" role="tab" aria-selected="{sel}" '
            f'tabindex="0"><b>{label}({wd})</b><span>{head}</span></button>')
        cards = _cards(body)
        blocks = "".join(
            f'<article class="card" data-i="{k}">'
            f'<div class="card-h"><span class="n">{k + 1:02d}/{len(cards):02d}</span>'
            f'<span class="t">{title}</span></div>'
            f'<div class="paper">{chunk}</div></article>'
            for k, (title, chunk) in enumerate(cards))
        sheets.append(
            f'<section class="sheet cards" data-d="{d}" data-active="{sel}" '
            f'data-n="{len(cards)}">'
            f'<p class="stamp">{d}({wd}) 개장 전 브리핑 · {len(cards)}장</p>'
            f'{blocks}</section>')

    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    html = (SHELL_HEAD
            + '<div class="top">'
            + '<div class="bar"><h1>모닝 섹터 브리핑</h1>'
            + f'<span class="sub">{len(days)}일치 · 갱신 {now} KST</span></div>'
            + '<div class="days" role="tablist">' + "".join(chips) + '</div></div>'
            + '<main>' + "".join(sheets) + '</main>'
            + '<div class="nav">'
            + '<button class="prev" aria-label="이전 카드">&#8592;</button>'
            + '<div class="dots" aria-hidden="true"></div>'
            + '<span class="pos"></span>'
            + '<button class="next" aria-label="다음 카드">&#8594;</button></div>'
            + '<footer>평일 08:00 자동 생성 · 투자 참고용이며 매수 권유가 아닙니다.<br>'
            + '상세는 Gmail 초안, 요약은 카카오톡으로 함께 발송됩니다.</footer>'
            + SHELL_SCRIPT)

    io.open(OUT, "w", encoding="utf-8").write(html)
    return {"ok": True, "파일": OUT, "날짜수": len(days),
            "크기자": len(html),
            "최신": days[0][0],
            "url": (io.open(URL_FILE, encoding="utf-8-sig").read().strip()
                    if os.path.exists(URL_FILE) else None),
            "_다음": ("Artifact 도구로 위 `파일`을 발행한다. `url`이 null이 아니면 그 값을 "
                       "url 파라미터로 넘겨 **같은 링크를 유지**한다. 처음 발행했으면 받은 URL을 "
                       f"{URL_FILE} 에 한 줄로 저장한다.")}


def add(date: str, src: str) -> dict:
    """오늘 브리핑 HTML을 날짜별 보관함에 복사한다. 모델이 내용을 옮겨 적지 않는다."""
    if not os.path.exists(src):
        return {"error": f"원본 없음: {src}"}
    os.makedirs(DAYS_DIR, exist_ok=True)
    body = io.open(src, encoding="utf-8-sig").read()
    dst = os.path.join(DAYS_DIR, f"{date}.html")
    io.open(dst, "w", encoding="utf-8").write(body)
    return {"저장": dst, "크기자": len(body)}


def main():
    argv = sys.argv[1:]
    known = {"--add", "--html", "--build"}
    unknown = [a for a in argv if a.startswith("--") and a not in known]
    if unknown:
        print(json.dumps({"error": f"모르는 인자: {unknown} (허용: {sorted(known)})"},
                         ensure_ascii=False))
        return
    res = {}
    if "--add" in argv:
        if "--html" not in argv:
            print(json.dumps({"error": "--add 에는 --html <경로> 가 필요하다"},
                             ensure_ascii=False))
            return
        res["add"] = add(argv[argv.index("--add") + 1], argv[argv.index("--html") + 1])
    if "--build" in argv or "--add" in argv:
        res["build"] = build()
    if not res:
        print(json.dumps({"error": "--add <날짜> --html <경로> 또는 --build"},
                         ensure_ascii=False))
        return
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()

