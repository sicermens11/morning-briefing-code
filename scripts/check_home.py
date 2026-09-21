#!/usr/bin/env python3
r"""
check_home.py — **홈 화면 7절 검사 다섯** (2026-09-21 신설)

정본: `design-share/reference/home-source.dc.html`
명세: `design-share/reference/HOME-FINAL.md` · 값이 어긋나면 **정본이 이긴다**

```
① 폭 393px 에서 세로 스크롤 0
② 글자 잘림·넘침 0 (지수 이름·값·등락 전부)
③ 메뉴 네 칸의 높이가 서로 같다
④ 주의 문구가 두 줄이고 가운데 정렬이다
⑤ 본문 최소 글자 10.5px 이상
```

## 왜 따로 만드나
`check_layout.py` 는 **카드**(1080×1600)를 잰다. 홈은 **폰 한 화면**(393×717)이고
「스크롤 0」 같은 조건이 카드에는 아예 없다. 같은 검사기에 우겨넣으면 둘 다 흐려진다.

## 어떻게 재나
`check_layout` 과 같은 길 — **크롬 헤드리스 + `--dump-dom`**.
재 본 값을 `document.title` 에 적어 두고 덤프에서 긁어온다.
⚠️ puppeteer 같은 건 안 쓴다. 이 PC 에 없고, 있어도 한 가지를 더 챙겨야 한다.

쓰는 법:
    python scripts\check_home.py
    python scripts\check_home.py --site data\briefing-site.html
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.request import pathname2url

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")

CHROME = (
    os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                 r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                 r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 r"Google\Chrome\Application\chrome.exe"),
)

# 폰 기준 — 명세 머리말 「기기 폭 393px 기준으로 짰고, 폰에서 스크롤 없이 한 화면」
W, H = 393, 717

# ⚠️ 화면에서 재는 부분. `document.title` 에 JSON 을 적어 덤프에서 긁는다.
#    `__RESULT__` 표시를 앞에 붙여 다른 title 과 안 섞이게 한다
JS = r"""
<script>
(function(){
  function 재기(){
    var out={실패:[],값:{}};
    var home=document.querySelector('#home');
    if(!home){out.실패.push('#home 을 못 찾았다');끝(out);return;}

    // ① 세로 스크롤 0
    var de=document.documentElement;
    var 넘=Math.max(0,de.scrollHeight-de.clientHeight);
    out.값['①세로넘침']=넘;
    if(넘>1) out.실패.push('① 세로로 '+넘+'px 넘친다 — 스크롤 0 이어야 한다');
    var 가로=Math.max(0,de.scrollWidth-de.clientWidth);
    out.값['가로넘침']=가로;
    if(가로>1) out.실패.push('가로로 '+가로+'px 넘친다');

    // ② 잘림·넘침 (지수 이름·값·등락 + 메뉴 글자)
    var 잘=[];
    home.querySelectorAll('.idxw .k,.idxw .v,.idxw .d,.big .t1,.big .sub,.big .up,.big .n')
      .forEach(function(el){
        if(el.scrollWidth>el.clientWidth+1) 잘.push(el.className+':"'+el.textContent.trim()+'"');
      });
    out.값['②잘린것']=잘;
    if(잘.length) out.실패.push('② 잘리거나 넘친 글자 '+잘.length+'개: '+잘.join(' · '));

    // ③ 메뉴 네 칸 높이가 같다
    var 칸=[].slice.call(home.querySelectorAll('.btns .big'));
    var 높=칸.map(function(e){return Math.round(e.getBoundingClientRect().height);});
    out.값['③칸수']=칸.length; out.값['③높이']=높;
    if(칸.length!==4) out.실패.push('③ 메뉴 칸이 '+칸.length+'개다 — 넷이어야 한다');
    if(높.length && (Math.max.apply(null,높)-Math.min.apply(null,높)>1))
      out.실패.push('③ 칸 높이가 다르다: '+높.join(' / '));

    // ④ 주의 문구 두 줄 · 가운데
    var 주=[].slice.call(home.querySelectorAll('.note span')).filter(function(e){
      return getComputedStyle(e).display!=='none';});
    out.값['④주의']=주.map(function(e){return e.textContent.trim();});
    if(주.length!==2) out.실패.push('④ 주의 문구가 '+주.length+'줄이다 — 두 줄이어야 한다');
    주.forEach(function(e){
      if(getComputedStyle(e).textAlign!=='center')
        out.실패.push('④ 가운데 정렬이 아니다: "'+e.textContent.trim()+'"');
    });

    // ⑤ 본문 최소 10.5px
    var 작=null;
    home.querySelectorAll('*').forEach(function(el){
      var cs=getComputedStyle(el);
      if(cs.display==='none'||cs.visibility==='hidden') return;
      var 글=false;
      for(var i=0;i<el.childNodes.length;i++){
        var n=el.childNodes[i];
        if(n.nodeType===3 && n.nodeValue.trim()){글=true;break;}
      }
      if(!글) return;
      var fs=parseFloat(cs.fontSize);
      if(!작||fs<작.px) 작={px:fs,t:el.textContent.trim().slice(0,20)};
    });
    out.값['⑤최소글자']=작;
    if(작 && 작.px<10.5)
      out.실패.push('⑤ '+작.px+'px 글자가 있다 ("'+작.t+'") — 10.5px 이상이어야 한다');

    // 참고로 남기는 값
    function h(s){var e=home.querySelector(s);return e?Math.round(e.getBoundingClientRect().height):null;}
    out.값['블록높이']={머리:h('.hd'),지수:h('.idxw'),메뉴:h('.btns'),주의:h('.note')};
    var bn=home.querySelector('.hd .bn');
    out.값['제목']=bn?(getComputedStyle(bn).fontSize+' '+getComputedStyle(bn).fontFamily.split(',')[0]):null;
    out.값['지수줄']=[].slice.call(home.querySelectorAll('.idxw .r')).map(function(e){
      return [].slice.call(e.querySelectorAll('.k,.v,.d')).map(function(x){
        return x.textContent.trim();}).join(' | ');});
    out.값['칸색']=칸.map(function(e){return getComputedStyle(e).backgroundColor;});
    끝(out);
  }
  function 끝(o){document.title='__RESULT__'+JSON.stringify(o);}
  if(document.fonts && document.fonts.ready){
    document.fonts.ready.then(function(){setTimeout(재기,300);});
  } else { setTimeout(재기,800); }
})();
</script>
"""


def _chrome():
    for p in CHROME:
        if p and os.path.exists(p):
            return p
    return None


def 재다(site):
    exe = _chrome()
    if not exe:
        return {"ok": None, "이유": "크롬을 못 찾았다 — 검사를 건너뛴다"}
    with open(site, encoding="utf-8-sig") as f:
        html = f.read()
    # ⚠️ 사이트는 화면 셋(home·cal·day)이 한 페이지에 있고 home 말고는 hidden 이다.
    #    그대로 열면 home 이 보이므로 손댈 것이 없다
    html = html.replace("</body>", JS + "</body>") if "</body>" in html else html + JS
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, "p.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(html)
        url = "file:///" + pathname2url(page).lstrip("/")
        try:
            r = subprocess.run(
                [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--allow-file-access-from-files",
                 f"--window-size={W},{H}",
                 "--virtual-time-budget=15000", "--dump-dom", url],
                capture_output=True, timeout=120)
        except Exception as e:  # noqa: BLE001
            return {"ok": None, "이유": f"크롬 실행 실패: {e}"}
    m = re.search(r"__RESULT__(\{.*?\})</title>", r.stdout.decode("utf-8", "replace"), re.S)
    if not m:
        return {"ok": None, "이유": "화면에서 잰 값을 못 읽었다 (title 표시 없음)"}
    try:
        return json.loads(m.group(1))
    except ValueError as e:
        return {"ok": None, "이유": f"잰 값이 JSON 이 아니다: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=os.path.join(_DATA, "briefing-site.html"))
    a = ap.parse_args()
    if not os.path.exists(a.site):
        print(json.dumps({"ok": False, "이유": f"{a.site} 없다"}, ensure_ascii=False))
        return 1
    r = 재다(a.site)
    if r.get("ok") is None and "이유" in r:
        print(json.dumps(r, ensure_ascii=False))
        return 0            # 못 재는 것은 실패가 아니다 (크롬이 없을 수 있다)
    실패 = r.get("실패") or []
    print(json.dumps({"ok": not 실패, "실패": 실패, "잰값": r.get("값")},
                     ensure_ascii=False, indent=1))
    return 1 if 실패 else 0


if __name__ == "__main__":
    sys.exit(main())
