#!/usr/bin/env python3
r"""
check_layout.py — 만들어진 페이지가 **실제로 안 깨졌는지** 브라우저로 재본다

⚠️⚠️ **이게 없으면 템플릿화가 의미가 없다.** 레이아웃은 코드에 고정이고 매일 바뀌는 건
   `card-copy`의 글뿐인데, **그 글 길이가 레이아웃을 깬다.** 2026-08-27 하루에만
   카드가 넘친 걸 열 번 넘게 잡았고 전부 "글이 길어져서"였다. 사람이 매번 눈으로
   확인할 수 없으니 기계가 본다.

⚠️ 이 검사는 **게시 전에** 돈다. 실패하면 `run-briefing.ps1`이 게시를 건너뛰고
   **어제 페이지를 그대로 둔다** — 깨진 페이지를 올리는 것보다 하루 묵은 게 낫다.

재는 것:
  1. 카드 여백    본문 글자가 카드 가장자리에서 90px 이상 떨어져 있나 (넘침 = 음수)
  2. 최소 글자    22px 미만이 없나 (`card_theme` 규칙)
  3. 한글 글꼴    한글에 고정폭 글꼴이나 넓은 자간이 걸리지 않았나
  4. 가로 넘침    320·390px에서 페이지가 옆으로 삐져나오지 않나

⚠️ 크롬이 없으면 **검사를 건너뛰고 통과로 본다**(`ok: true`, `skipped: true`).
   검사기가 없다고 브리핑 발행을 막지는 않는다 — 그건 본말전도다.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import pathname2url

# ⚠️⚠️ **`card_theme.BREATH_BOTTOM`과 짝이다** — 그 값을 바꾸면 여기도 본다.
#    2026-08-31에 아래 여백을 위와 같게 맞추면서(176px → 92px) 하한도 내렸다.
#    예전 90은 아래 여백이 176px이던 시절 값이라, 그대로 두면 **정상 카드가
#    92px에 서서 2px 차이로 아슬아슬**해진다.
#    ⚠️ 50인 이유: 설계 목표가 92px이므로, 50 아래로 내려왔다는 건 글이
#       **비워 둔 자리를 42px이나 파고들어 가장자리에 붙었다**는 뜻이다.
MIN_MARGIN = 50     # 카드 안쪽 여백 하한(px)
# ⚠️⚠️ **위쪽 한계도 본다** (2026-08-31 신설). 지금까지는 "넘쳤나"만 봤다. 그런데
#    사용자가 걸고넘어진 건 반대쪽이었다 — **"페이지마다 끝나는 자리가 다르다"**.
#    한 장은 꽉 차고 다음 장은 텅 비면 넘기면서 눈에 거슬린다. 실측으로 08-27
#    기관 의견 카드가 290px 남고 같은 날 액션플랜은 86px였다.
#    ⚠️ 막지 않는다(경고). 그날 글이 짧은 건 레이아웃이 고칠 수 있는 일이 아니다 —
#       **글을 더 쓰라는 신호**로 쓴다.
MAX_MARGIN = 260    # 이보다 많이 남으면 "글을 더 담을 자리가 있다"는 뜻
# ⚠️ 2026-08-28에 22 → 26으로 올렸다. 사용자가 "아무리 작아도 본문 크기 정도"를 요청했고,
#    실측으로 26까지는 액션플랜 카드가 견디는 것을 확인했다(글 예산을 같이 줄여서).
#    ⚠️ 더 올리려면 `build_cards.CUT`을 또 줄여야 한다 — 글자와 글은 같은 자리를 다툰다.
# ⚠️ **본문은 29px, 라벨·페이지번호는 26px이다.** 하한은 낮은 쪽에 맞춘다.
#    2026-08-28에 29로 올렸다가 라벨("03 / 08", "장 시작 후 확인")이 전부 걸려
#    **게시가 조용히 막혔다** — 로컬은 새 화면인데 라이브는 옛 화면이 그대로였다.
#    라벨까지 29로 올리려면 카드 자리를 더 내줘야 한다. 지금은 26이 실질 하한이다.
MIN_FONT = 26       # 최소 글자 크기(px)
NARROW = (320, 390)  # 재볼 화면 폭 — 320은 아이폰 SE, 390은 최근 아이폰

CHROME = [
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                 r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 r"Google\Chrome\Application\chrome.exe"),
]

# ── 카드: 여백·글꼴 ─────────────────────────────────────────────
CARD_PROBE = r"""
setTimeout(function(){
 /* ⚠️ 퀀트 화면은 `hidden` 이라 그냥 두면 크기가 0 이다 — 펼쳐서 잰다 */
 ["qt","pf"].forEach(function(id){
   var v=document.getElementById(id);
   if(v){v.hidden=false; v.style.display="block";}});
 document.querySelectorAll(".rail").forEach(function(r){
   r.setAttribute("data-active","true"); r.style.display="block";});
 document.querySelectorAll(".rail section").forEach(function(s){
   s.style.transform="none"; s.style.margin="0 0 20px 0";});
 setTimeout(function(){
  var out=[];
  document.querySelectorAll("section[data-label]").forEach(function(s){
   var sr=s.getBoundingClientRect(),W=sr.width,H=sr.height;
   var t=1e9,b=-1e9,l=1e9,r=-1e9,bad=[],cut=0,cutTxt="";
   /* ⚠️⚠️ **글자 마디(text node)를 직접 잰다** (2026-09-11).
      전에는 `k.children.length` 로 잎을 골랐는데 그러면
          <div><b>머리</b><br>본문</div>
      의 **「본문」을 통째로 못 본다**. 3장이 그래서 「넘침 0」으로
      나왔는데 실제로는 잘려 있었다 */
   var w=document.createTreeWalker(s, NodeFilter.SHOW_TEXT, null), n;
   while((n=w.nextNode())){
     var raw=(n.nodeValue||"").trim();
     if(!raw) continue;
     var rg=document.createRange(); rg.selectNodeContents(n);
     var rects=rg.getClientRects();
     for(var i=0;i<rects.length;i++){
       var q=rects[i];
       if(q.height<3||q.width<3) continue;
       t=Math.min(t,q.top-sr.top); b=Math.max(b,q.bottom-sr.top);
       l=Math.min(l,q.left-sr.left); r=Math.max(r,q.right-sr.left);
       /* ⚠️⚠️ **카드 밖만 보면 안 된다** (2026-09-11).
          카드는 위/가운데(overflow:hidden)/아래 인데 `아래` 가 바닥에
          붙어 **가운데가 잘라먹어도 카드는 꽉 차 보인다.**
          그래서 잘리는 칸을 거슬러 올라가 직접 확인한다 */
       var an=n.parentElement;
       while(an&&an!==s){
         var acs=getComputedStyle(an);
         if(acs.overflow==="hidden"||acs.overflowY==="hidden"){
           var ar=an.getBoundingClientRect();
           if(q.bottom>ar.bottom+1||q.top<ar.top-1){
             if(!cut) cutTxt=raw.slice(0,16);
             cut++;
           }
         }
         an=an.parentElement;
       }
       var cs=getComputedStyle(n.parentElement), fs=parseFloat(cs.fontSize);
       var ko=/[가-힣]/.test(raw), txt=raw.slice(0,12);
       if(fs<__MINFONT__) bad.push("작음"+Math.round(fs)+":"+txt);
       if(ko&&/JetBrains|SFMono|Consolas|monospace/.test(cs.fontFamily))
         bad.push("한글고정폭:"+txt);
       if(ko&&cs.letterSpacing!=="normal"&&parseFloat(cs.letterSpacing)>0.5)
         bad.push("한글자간:"+txt);
     }
   }
   out.push([s.dataset.label, Math.round(t), Math.round(H-b),
             Math.round(l), Math.round(W-r), bad.join(";"),
             cut, cutTxt].join("|"));
  });
  document.title="R::"+out.join("@@");
 },600);
},1400);
"""

# ── 사이트: 좁은 화면 가로 넘침 ────────────────────────────────
NARROW_HOST = r"""
<style>html,body{margin:0}iframe{border:0;display:block}</style>
<iframe id="f" src="__SRC__" width="__W__" height="820"></iframe>
<script>
document.getElementById("f").onload=function(){
 var d=this.contentDocument, w=__W__;
 setTimeout(function(){
  var btn=d.getElementById("btn-today"); if(btn) btn.click();
  setTimeout(function(){
   var de=d.documentElement, over=[];
   d.querySelectorAll("body *").forEach(function(el){
     if(el.closest(".rail")) return;            // 레일은 가로로 넘기는 게 목적이다
     var r=el.getBoundingClientRect();
     if(r.width>0&&r.right>w+0.5)
       over.push(el.tagName+"«"+(el.textContent||"").trim().slice(0,14)+"»");
   });
   document.title="N::"+de.scrollWidth+"|"+over.length+"|"+over.slice(0,3).join(",");
  },900);
 },1700);
};
</script>
"""


def _chrome():
    for p in CHROME:
        if os.path.exists(p):
            return p
    return None


# ── 세로 상세: 모양이 가로와 갈렸나 (정적 대조) ─────────────────
# ⚠️⚠️ **2026-09-01 신설 — 그동안 검사기는 카드만 봤다.**
#    `section[data-label]`(카드)만 훑어서 **세로 상세는 검사 대상이 아니었다.**
#    2026-08-31에 상자 모서리를 가로만 둥글게 하고 세로를 빼먹었는데 검사기는
#    **"통과"라고 보고했다.** 사용자가 눈으로 보고 물어봐서야 알았다.
#
# ⚠️ **브라우저로 재지 않는다.** 세로는 기본이 `display:none`이고 조상(`.view`)까지
#    숨겨져 있어, 헤드리스에서 강제로 켜도 **폭이 0으로 잡혀 상자를 하나도 못 찾았다**
#    (2026-09-01 실측: `0|0|0`으로 조용히 통과). 억지로 켜는 코드는 화면 구조가 바뀔
#    때마다 또 깨진다. **글자로 세는 쪽이 확실하다.**
#
# ⚠️ 세로에는 "넘쳤다"는 개념이 없다(길이가 정해져 있지 않다). 그래서 여백은 안 잰다.
#    **가로와 갈라졌는지만** 본다.

def check_scroll_shape(site_path):
    r"""**가로·세로가 모양 값을 손으로 따로 박아두지 않았나** (2026-09-01).

    ⚠️ 처음에는 "세로에 각진 상자가 몇 개인가"를 셌는데 **오탐 51개**가 났다 —
       줄무늬 표 행처럼 **원래 각져야 하는 것**까지 잡혔다. 화면을 세는 방식으로는
       "각져야 할 것"과 "둥글어야 할 것"을 못 가른다.

    ⇒ **화면이 아니라 코드를 본다.** 진짜 위험은 "각졌다"가 아니라
       **"같은 값을 두 파일에 손으로 박아둔 것"**이다. 2026-08-31에 `14px`을
       가로 9곳·세로 4곳에 따로 박았고, 그때 세로를 빼먹어 갈라졌다.
       값이 `card_theme.RADIUS` 한 곳에서만 나오면 그 사고가 구조적으로 불가능해진다.

    ⚠️ 세로에는 "넘쳤다"는 개념이 없어(길이가 정해져 있지 않다) 여백은 안 잰다.
    """
    out = []
    base = os.path.dirname(os.path.abspath(__file__))
    for name in ("build_cards.py", "build_scroll.py"):
        f = os.path.join(base, name)
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8-sig") as fp:
            src = fp.read()
        박힌 = []
        for ln in src.split(chr(10)):
            m = re.search(r"border-radius:\s*(\d+)px", ln)
            if not m:
                continue
            v = m.group(1)
            # 999px(알약 모양)은 상수로 뺄 값이 아니다 — 뜻이 "완전히 둥글게"다.
            if v == "999":
                continue
            # ⚠️ **페이지 UI는 뺀다.** `.day{...}` 같은 CSS 규칙은 카드가 아니라
            #    날짜 버튼·네비게이션이다. 카드 상자를 바꿀 때 버튼까지 따라
            #    바뀌면 안 되므로 **일부러 따로 둔 값**이다(2026-09-01).
            if re.match(r"\s*[.#][\w-]+[\s,{]", ln):
                continue
            박힌.append(v)
        if 박힌:
            out.append(f"{name}: 모서리 값이 손으로 박혀 있다 {sorted(set(박힌))} "
                       f"({len(박힌)}곳) — `card_theme.RADIUS`로 빼라. "
                       f"두 파일에 따로 박으면 한쪽만 고치고 갈라진다")
    # 세로가 아예 둥근 상자를 안 쓰면 그것도 신호다(전부 빠뜨린 경우)
    if site_path and os.path.exists(site_path):
        with open(site_path, encoding="utf-8-sig") as fp:
            h = fp.read()
        구역 = "".join(re.findall(r'<div class="scrollwrap".*?(?=<div class="scrollwrap"|</body|$)',
                                  h, re.S))
        if 구역 and "border-radius" not in 구역:
            out.append("세로 상세에 둥근 상자가 하나도 없다 — 가로만 고치고 빠뜨렸는지 본다")
    return out


def _run(exe, html, width, height, marker):
    """헤드리스로 열고 `document.title`에 남긴 결과를 긁어 온다."""
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, "p.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(html)
        url = "file:///" + pathname2url(page).lstrip("/")
        try:
            r = subprocess.run(
                [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--allow-file-access-from-files",
                 f"--window-size={width},{height}",
                 "--virtual-time-budget=12000", "--dump-dom", url],
                capture_output=True, timeout=90)
        except Exception as e:  # noqa: BLE001
            return None, f"크롬 실행 실패: {e}"
        m = re.search(marker + r"([^<]*)", r.stdout.decode("utf-8", "replace"))
        return (m.group(1) if m else None), None


# ── 정적 확인: 좌우 잠금이 CSS에 실제로 박혀 있나 ───────────────
# ⚠️⚠️ **이건 크롬으로는 못 잡는다.** 2026-08-27, 데스크톱 크롬 393px에서 넘침이 0으로
#    나왔는데 아이폰에서는 페이지가 좌우로 밀렸다. 원인은 뿌리 잠금이 `overflow-x:clip`
#    **하나뿐**이었던 것 — `clip`은 비교적 새 값이라 모르는 엔진은 선언을 통째로 버린다.
#    측정으로 못 잡는 종류라 **글자로 확인한다.** 사용자가 세 번 지적한 항목이다.
LOCKS = [
    (r"html\s*,\s*body\s*{[^}]*overflow-x\s*:\s*hidden",
     "뿌리(html,body) 좌우 잠금이 없다 — `clip`만으로는 모르는 엔진에서 통째로 무시된다"),
    (r"\.top\s+\.in\s*{[^}]*flex-wrap\s*:\s*wrap",
     "상단 막대에 flex-wrap이 없다 — 좁은 화면에서 한 줄에 우겨넣다 페이지가 밀린다"),
    (r"\.scrollwrap\s*{[^}]*width\s*:\s*100%",
     "`.scrollwrap`에 width:100%가 없다 — flex 자식 + margin:auto 조합이라 "
     "내용 최소 폭으로 벌어져 아이폰에서 글이 잘린다(2026-08-28 실측)"),
    (r"word-wrap\s*:\s*break-word",
     "`word-wrap:break-word`가 없다 — `overflow-wrap`만 쓰면 구형 엔진이 못 알아본다"),
]


def check_js(path):
    """페이지 안 <script>가 **문법적으로 성립하는지** 본다.

    ⚠️⚠️ 2026-08-27, 진단 코드를 넣다가 JS 문자열 안에 진짜 줄바꿈이 들어가 스크립트가
       통째로 죽었고, **첫 화면 단추가 전부 안 눌리는 상태로 게시됐다.** 화면은 멀쩡해
       보였고 레이아웃 검사도 통과했다 — 그림은 그려지는데 손잡이만 없었던 것이다.
       그래서 '보이는가'와 별개로 '움직이는가'를 따로 본다. node가 없으면 건너뛴다.
    """
    if not (path and os.path.exists(path)):
        return []
    node = shutil.which("node")
    if not node:
        return []
    with open(path, encoding="utf-8") as f:
        blocks = re.findall(r"<script>(.*?)</script>", f.read(), re.S)
    bad = []
    for i, b in enumerate(blocks):
        with tempfile.TemporaryDirectory() as d:
            js = os.path.join(d, "b.js")
            with open(js, "w", encoding="utf-8") as fp:
                fp.write(b)
            r = subprocess.run([node, "--check", js], capture_output=True, timeout=30)
            if r.returncode:
                msg = r.stderr.decode("utf-8", "replace").strip().splitlines()
                head = next((x for x in msg if "Error" in x or "^" not in x), "")[:120]
                bad.append(f"script #{i} 문법 오류 — 페이지 동작이 통째로 죽는다: {head}")
    return bad


def check_locks(site_path):
    if not (site_path and os.path.exists(site_path)):
        return []
    with open(site_path, encoding="utf-8") as f:
        css = f.read()
    return [msg for pat, msg in LOCKS if not re.search(pat, css, re.S)]


def check(cards_path, site_path=None):
    exe = _chrome()
    if not exe:
        # ⚠️ 크롬이 없어도 **정적 확인은 돈다.** 좌우 잠금은 측정이 아니라 글자로 보는 것이라
        #    크롬 유무와 무관하다. 브라우저가 필요한 항목만 건너뛴다.
        lock_fails = check_locks(site_path) + check_js(site_path) + check_js(cards_path)
        return {"ok": not lock_fails, "실패": lock_fails, "경고": [], "skipped": True,
                "_안내": "크롬이 없어 화면 측정은 건너뛴다(좌우 잠금 확인은 했다)"}

    fails, notes = [], []
    # ⚠️ 세로 상세는 **경고로만** 낸다. 세로가 어긋났다고 게시를 막으면 가로까지 못
    #    올라간다 — 지메일 백업이 없는 쪽이 더 손해다.
    notes.extend(check_scroll_shape(site_path))

    # 1~3. 카드 여백·글꼴
    if cards_path and os.path.exists(cards_path):
        with open(cards_path, encoding="utf-8") as f:
            html = f.read()
        probe = CARD_PROBE.replace("__MINFONT__", str(MIN_FONT))
        raw, err = _run(exe, html + "<script>" + probe + "</script>", 1500, 1300, "R::")
        if err:
            notes.append(err)
        elif not raw:
            notes.append("카드 측정값을 못 읽었다 — 검사 자체가 실패했다")
        else:
            for row in raw.split("@@"):
                p = row.split("|")
                if len(p) < 5:
                    continue
                label, margins, bad = p[0], [int(x) for x in p[1:5]], (p[5] if len(p) > 5 else "")
                # ⚠️⚠️ **잘린 글은 여백보다 심각하다** — 여백은 보기 나쁜 것이고
                #    잘린 글은 **아예 안 보이는 것**이다 (2026-09-11)
                _cut = int(p[6]) if len(p) > 6 and p[6].isdigit() else 0
                if _cut:
                    fails.append(f"{label}: **글 {_cut}마디가 칸 안에서 잘렸다** "
                                 f"— 화면에 안 나온다 (첫 조각: "
                                 f"{p[7] if len(p) > 7 else '?'})")
                if min(margins) < MIN_MARGIN:
                    fails.append(f"{label}: 여백 {min(margins)}px (하한 {MIN_MARGIN}) — 내용이 넘쳤다")
                elif margins[1] > MAX_MARGIN:
                    fails.append(f"{label}: 아래가 {margins[1]}px 남았다 (여유 {MAX_MARGIN} 초과) "
                                 f"— 글을 더 담을 자리가 있다")
                if bad:
                    fails.append(f"{label}: {bad}")

    # ⚠️⚠️ **퀀트 카드도 잰다** (2026-09-11 신설).
    #    지금까지 이 검사는 `--cards`(브리핑 카드)만 봤다. 퀀트 카드 3장은
    #    **사이트 쪽에 있어서 한 번도 안 재봤고**, 그 사이 1장 242px,
    #    2장 161px 이 잘려 나갔다. 사용자가 화면을 보고 직접 찾아냈다
    if site_path and os.path.exists(site_path):
        with open(site_path, encoding="utf-8") as f:
            shtml = f.read()
        sprobe = CARD_PROBE.replace("__MINFONT__", str(MIN_FONT))
        sraw, serr = _run(exe, shtml + "<script>" + sprobe + "</script>",
                          1500, 1300, "R::")
        if serr:
            notes.append(f"퀀트 카드 측정 실패: {serr}")
        elif not sraw:
            notes.append("퀀트 카드 측정값을 못 읽었다")
        else:
            for row in sraw.split("@@"):
                p = row.split("|")
                if len(p) < 7 or not p[0].startswith("퀀트"):
                    continue
                label = p[0]
                _cut = int(p[6]) if p[6].isdigit() else 0
                if _cut:
                    fails.append(f"{label}: **글 {_cut}마디가 칸 안에서 잘렸다** "
                                 f"— 화면에 안 나온다 (첫 조각: "
                                 f"{p[7] if len(p) > 7 else '?'})")
                _m = min(int(x) for x in p[1:5])
                if _m < MIN_MARGIN:
                    fails.append(f"{label}: 여백 {_m}px (하한 {MIN_MARGIN}) "
                                 f"— 내용이 넘쳤다")

    # 0. 좌우 잠금 + 스크립트 문법 (크롬 측정으로는 못 잡는 것들)
    fails.extend(check_locks(site_path))
    fails.extend(check_js(site_path))
    fails.extend(check_js(cards_path))

    # 4. 좁은 화면 가로 넘침
    if site_path and os.path.exists(site_path):
        src = "file:///" + pathname2url(os.path.abspath(site_path)).lstrip("/")
        for w in NARROW:
            host = NARROW_HOST.replace("__SRC__", src).replace("__W__", str(w))
            raw, err = _run(exe, host, 900, 900, "N::")
            if err:
                notes.append(err)
                break
            if not raw:
                notes.append(f"{w}px 측정값을 못 읽었다")
                continue
            doc_w, n_over, who = (raw.split("|") + ["", "", ""])[:3]
            if int(doc_w or 0) > w:
                fails.append(f"{w}px: 페이지가 {doc_w}px로 넘친다 — 좌우로 밀린다 ({who})")
            elif int(n_over or 0):
                fails.append(f"{w}px: 화면 밖으로 나간 요소 {n_over}개 ({who})")

    # ⚠️⚠️ **모든 실패가 같은 무게는 아니다** (2026-08-28 분리).
    #    좌우가 안 잠기거나 스크립트가 죽으면 **페이지를 못 쓴다** — 올리면 안 된다.
    #    반면 카드 한 장이 20px 넘친 것은 **보기 나쁠 뿐** 읽을 수는 있다.
    #    그걸로 그날 웹 전체를 막으면, 지메일은 나갔는데 웹만 어제 것으로 남는다.
    #    실제로 2026-08-28에 그 일이 벌어져 한 시간 넘게 옛 화면이 서 있었다.
    치명키 = ("좌우 잠금", "flex-wrap", "word-wrap", "문법 오류", "px:", "한글고정폭", "한글자간")
    치명 = [x for x in fails if any(k in x for k in 치명키)]
    # ⚠️ **잘린 글을 맨 앞에 놓는다** (2026-09-11). 여백이 몇 px 모자란 것과
    #    **글이 아예 안 보이는 것**은 무게가 다르다. 막지는 않는다 —
    #    2026-08-28 결정(카드 한 장 때문에 사이트를 어제 것으로 두지 않는다)은
    #    그대로다 — 대신 줄줄이 늘어선 경고에 **묻히지 않게** 앞으로 올린다
    경고 = [x for x in fails if x not in 치명]
    경고.sort(key=lambda x: (0 if "잘렸다" in x else 1))
    res = {"ok": not 치명, "실패": 치명, "경고": 경고}
    if notes:
        res["_안내"] = notes
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=None,
                    help="여백 하한을 임시로 바꿔 본다(글자 예산을 잴 때 쓴다)")
    ap.add_argument("--cards", help="카드뉴스 HTML")
    ap.add_argument("--site", help="사이트 HTML")
    a = ap.parse_args()
    if a.min is not None:
        MIN_MARGIN = a.min          # noqa: F841 — 아래 globals()로 반영한다
        globals()["MIN_MARGIN"] = a.min
    out = check(a.cards, a.site)
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out.get("ok") else 1)
