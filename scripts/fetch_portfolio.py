#!/usr/bin/env python3
r"""
fetch_portfolio.py — NH PLUG로 보유 종목을 받아 `data\portfolio.json`을 갱신한다

⚠️⚠️ **금액은 화면에 안 나간다** (2026-08-28 사용자 선택 A). 이 사이트는 주소를 아는
   사람이면 누구나 본다. 종목 추천은 남이 봐도 되지만 **내 평가금액은 다른 문제다.**
   여기서 받은 금액은 `portfolio.json`에 들어가 **섹터 비율 계산에만** 쓰이고,
   `build_site.portfolio_view()`가 화면에는 퍼센트만 그린다.
   ⚠️ 금액을 화면에 내보내고 싶어지면 **사이트를 비공개로 옮기는 것이 먼저다** —
      GitHub Pages 무료 요금제는 비공개가 안 된다.

⚠️ **조회만 한다. 주문 API는 부르지 않는다.** 이 시스템은 사는 걸 돕지 대신 사지 않는다.

⚠️ **계좌번호를 사람이 적지 않는다.** `/n2/acctinfo`가 앱키에 딸린 계좌를 다 준다.
   손으로 적으면 오타가 나고, 계좌가 늘거나 줄 때 반드시 한쪽이 낡는다.
   ⚠️ 모의투자 계좌(`acct_type` 03)가 섞여 온다. **운영 도메인에서 모의계좌를 부르면
      실패한다** — SDK의 `usable` 판정으로 환경에 맞는 것만 쓴다.

⚠️ 자격증명은 `data\secrets.json`에 둔다(`NHPLUG_APP_KEY`·`NHPLUG_APP_SECRET`).
   SDK 기본은 `~/.nhplug/.env`지만 **키를 두 곳에 흩으면 하나는 반드시 잊힌다.**
   여기서 환경변수로 넘겨주면 SDK가 그걸 먼저 읽는다(실제 환경변수가 최우선).

쓰는 법:
    python scripts\fetch_portfolio.py --accounts   # 계좌 목록만 (번호는 가림)
    python scripts\fetch_portfolio.py              # 잔고 받아 portfolio.json 갱신
    python scripts\fetch_portfolio.py --exclude 12345678   # 특정 계좌 빼고
"""
import argparse
import io
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "portfolio.json")
MAP = os.path.join(_BASE, "data", "value-chain-map.md")
MAP_해외 = os.path.join(_BASE, "data", "overseas-sector.json")


def _env():
    """secrets.json → 환경변수. SDK를 부르기 **전에** 해야 한다."""
    for k in ("NHPLUG_APP_KEY", "NHPLUG_APP_SECRET"):
        v = config.get(k)
        if not v:
            raise RuntimeError(f"{k}가 없다. data\\secrets.json에 넣는다.")
        os.environ[k] = v
    os.environ.setdefault("NHPLUG_BASE_URL", "https://api.nhplug.com:8443")
    os.environ.setdefault("NHPLUG_AUTH_URL", "https://api.nhplug.com:8443")


# ⚠️⚠️ **NH PLUG 앱키에도 사용기간이 있다(1년).** KRX·GitHub 토큰에는 만료 경고가
#    있는데 여기만 없었다(2026-08-31 발견). 만료되면 어느 날 조용히 인증이 실패하고
#    **포트폴리오 화면이 빈다** — 그런데 화면은 "종목 없음"으로 멀쩡해 보인다.
#    ⚠️ API가 만료일을 안 알려주므로 **사람이 적어야 한다.** 갱신하면 이 날짜를 고친다.
KEY_ISSUED = "2026-08-28"      # nhplug.com에서 앱키·시크릿을 받은 날
KEY_DAYS = 365


def _만료경고():
    try:
        남음 = KEY_DAYS - (datetime.now() - datetime.strptime(KEY_ISSUED, "%Y-%m-%d")).days
    except Exception:  # noqa: BLE001
        return None
    if 남음 <= 60:
        return (f"⚠️ NH PLUG 앱키가 {남음}일 뒤 만료된다(발급 {KEY_ISSUED}). "
                f"nhplug.com에서 갱신하고 fetch_portfolio.py의 KEY_ISSUED를 고친다.")
    return None


def _mask(no):
    """계좌번호는 **뒤 네 자리만** 남긴다. 로그·화면 어디에도 전체가 안 남게."""
    s = str(no or "")
    return ("*" * max(0, len(s) - 4)) + s[-4:] if s else "-"


def accounts():
    _env()
    from nhplug import call
    d = call("/n2/acctinfo", {})
    out = []
    for a in (d.get("Output_0") or []):
        t = (a.get("acct_type") or "").strip()
        out.append({"no": a.get("acct_no"), "type": t,
                    "env": {"01": "운영", "02": "운영(주문대리인)",
                            "03": "모의투자"}.get(t, f"미정의({t})"),
                    "usable": t in ("01", "02")})
    return out


def balance(act_no):
    from nhplug import call
    return call("/krstock/inquiry/v1/balance", {
        "act_no": act_no, "bnc_bse_cd": "5", "ltg_aot_dit_cd": "9",
        "aet_bse": "2", "qut_dit_cd": "UNT"})


# ⚠️ 나라마다 따로 불러야 한다. 지금은 미국만 본다 — 2026-08-28 확인 시점에 보유가
#    미국뿐이었다. 늘어나면 여기에 코드를 더한다(070.일본 120.홍콩 160.상해 170.심천).
#    ⚠️ 나라를 늘리면 **호출이 계좌×나라로 곱해진다.** 호출 상한이 있으니 함부로 늘리지 않는다.
해외국가 = (("200", "미국"),)


def balance_해외(act_no):
    r"""**해외주식 잔고.** 국내와 API가 완전히 다르다.

    ⚠️⚠️ 2026-08-28까지 이걸 안 불러서 **미국 종목 10개가 통째로 빠져 있었다.**
       화면에는 안랩 100%로 나왔고, 그건 틀린 그림이 아니라 **틀린 줄 모르는 그림**이었다.
       국내 잔고 API(`/krstock/...`)는 해외 보유를 한 줄도 주지 않는다.

    ⚠️ `cur_cd`는 **`KRW`가 "전체 통화"**라는 뜻이다(원화 보유가 아니다). 명세 그대로다.
    ⚠️ 금액은 **`krw_eal_amt`(원화 환산)**를 쓴다. 달러로 받으면 국내와 못 더한다 —
       비율을 내려면 같은 자로 재야 한다.
    """
    from nhplug import call
    out = []
    for 코드, 이름 in 해외국가:
        try:
            d = call("/gbstock/inquiry/v1/balance", {
                "act_no": act_no, "qut_iqr_dit_cd": "9",
                "fc_sec_trd_nat_cd": 코드, "cur_cd": "KRW", "xns_dit_cd": "0"})
        except Exception as e:  # noqa: BLE001
            out.append(("실패", 이름, type(e).__name__))
            continue
        for r in (d.get("Output_1") or []):
            out.append(("행", 이름, r))
    return out


def _sector_index():
    r"""가치사슬맵에서 **종목명 → 섹터**. 코드가 아니라 이름으로 맞춘다.

    ⚠️ 맵은 `### 섹터명` 다음 줄에 종목명을 OR로 늘어놓은 형식이다. 코드가 없다.
       그래서 이름으로 맞추고, 못 찾으면 `미분류`로 둔다 — **억지로 넣지 않는다.**
    """
    idx, sec = {}, None
    if not os.path.exists(MAP):
        return idx
    for line in io.open(MAP, encoding="utf-8-sig"):
        line = line.strip()
        if line.startswith("### "):
            sec = line[4:].strip()
        elif sec and line.startswith("`") and " OR " in line:
            body = line.strip("`").split("[")[0]
            for nm in body.split(" OR "):
                nm = nm.strip().strip('"').strip()
                if nm:
                    idx.setdefault(nm, sec)
    return idx


def _sector_해외():
    r"""티커 → 섹터. 가치사슬맵에 **미국 종목이 하나도 없어서** 따로 둔다.

    ⚠️ 스크립트에 박지 않고 파일로 뺐다. 보유가 바뀔 때마다 코드를 고치게 하면
       결국 아무도 안 고치고 전부 `미분류`로 쌓인다.
    """
    try:
        with io.open(MAP_해외, encoding="utf-8-sig") as fp:
            return json.load(fp).get("섹터") or {}
    except Exception:  # noqa: BLE001
        return {}


def _수동():
    r"""**API로 못 가져오는 계좌**를 손으로 적어 두는 자리.

    ⚠️⚠️ **NH PLUG는 위탁계좌만 다룬다.** 명세 정본(llms-full.txt) 어디에도 "ISA"·"연금"이
       없다(2026-08-28 확인, 0건). 등록계좌가 CMA 하나뿐인 것은 설정 실수가 아니라
       **API의 범위가 거기까지**여서다. 포털에서 추가할 방법이 없다.
       그렇다고 그 종목들을 화면에서 빼면 **쏠림이 거짓으로 보인다** — 반도체에
       몰려 있는데 "괜찮다"고 보이는 것이 이 화면이 낼 수 있는 가장 나쁜 오답이다.

    ⚠️ **매일 갱신이 이걸 지우지 않는다.** `portfolio.json`의 `수동` 항목은
       API 결과와 합쳐지고 그대로 남는다. 손으로 적은 것을 기계가 덮으면
       다음 날 조용히 사라지고, 사라진 줄도 모른다.

    ⚠️ **금액은 안 적어도 된다.** `수량`만 있으면 KRX 종가로 곱한다(`_krx_시세`).
       사람이 평가금액을 손으로 적으면 주가가 움직인 날 비율이 통째로 틀린다 —
       그리고 틀린 줄 모른다. **수량은 사람만 알고, 가격은 기계가 안다.**
    """
    if not os.path.exists(OUT):
        return []
    try:
        with io.open(OUT, encoding="utf-8-sig") as fp:
            return [h for h in (json.load(fp).get("수동") or []) if h.get("code")]
    except Exception:  # noqa: BLE001
        return []


def _krx_시세():
    r"""가장 최근 KRX 일별 캐시에서 **코드 → (이름, 종가)**.

    ⚠️ 수동 입력이 수량만 있을 때 쓴다. 캐시가 없으면 빈 dict — 그러면 수량만 있는
       항목은 **버려지지 않고 평가금액 0으로 남아** 비율 계산에서 빠진다.
       (`main`이 이걸 `수동_시세없음`으로 알린다. 조용히 사라지는 게 최악이다.)
    """
    import glob
    fs = sorted(glob.glob(os.path.join(_BASE, "data", "krx-daily", "*.json")))
    if not fs:
        return {}
    try:
        with io.open(fs[-1], encoding="utf-8") as fp:
            종목 = (json.load(fp).get("종목") or {})
    except Exception:  # noqa: BLE001
        return {}
    return {c: (v.get("이름"), v.get("종가")) for c, v in 종목.items()}


def collect(exclude=()):
    _env()
    acs = [a for a in accounts() if a["usable"] and a["no"] not in exclude]
    sec_idx = _sector_index()
    sec_ovs = _sector_해외()
    hold, 실패, 불일치 = {}, [], []
    for a in acs:
        try:
            d = balance(a["no"])
        except Exception as e:  # noqa: BLE001
            실패.append({"계좌": _mask(a["no"]), "오류": type(e).__name__})
            continue
        for r in (d.get("Output_1") or []):
            code = (r.get("iem_cd") or "").strip().lstrip("A")
            name = (r.get("iem_nm") or "").strip()
            # ⚠️⚠️ **실제 보유 = `rsdl_qty`(잔량수량)이다.** 정본 필드 설명으로 확인했다
            #    (openapi.json: itg_bnc_qty=통합잔고수량 · ny_stl_qty=미결제수량 ·
            #     rsdl_qty=잔량수량).
            #
            #    ⚠️ 여기서 두 번 틀렸다. 처음엔 `itg_bnc_qty`만 봐서 **오늘 산 것이 안 보였고**,
            #       고친다고 `itg + ny_stl`로 바꿨더니 이번엔 **오늘 사서 판 것이 남았다.**
            #       2026-08-28 안랩이 그랬다 — 사고 판 종목이 화면에 2주 보유로 떴다.
            #       원인: 매도 다리가 **종목코드 없는 별도 행**(`ny_stl_qty` −2)으로 와서,
            #       코드 없는 행을 버리는 규칙에 걸려 매수 +2만 남았다.
            #       **없는 보유가 있는 것처럼 보이는 것**이 이 화면 최악의 오답이다 —
            #       "이미 들고 있으니 더 담지 말라"는 경고가 거짓이 되기 때문이다.
            #
            #    ⚠️ 잔량이 통합잔고+미결제와 다르면 남긴다. 같은 종류의 실수를 또 하지 않으려면
            #       **어긋나는 날을 봐야 한다** — 특히 사서 그대로 들고 있는 날.
            잔량 = _num(r.get("rsdl_qty"))
            합산 = (_num(r.get("itg_bnc_qty")) or 0) + (_num(r.get("ny_stl_qty")) or 0)
            if 잔량 is None:
                잔량 = 합산
            elif code and 잔량 != 합산:
                불일치.append({"종목": name or code, "잔량": 잔량, "통합＋미결제": 합산})
            qty = 잔량
            price = _num(r.get("now_pr")) or 0
            # ⚠️ `eal_amt`(평가금액)는 미결제 건에서 0으로 온다. 직접 곱한다.
            amt = qty * price
            # 코드가 없는 행(결제 상계용)과 보유 0인 종목은 버린다.
            if not code or qty <= 0 or amt <= 0:
                continue
            # ⭐⭐ **매입가**(`phs_pr`) 를 같이 담는다 (2026-09-15 · 분할 매수).
            #    분할 매수를 화면에 담으려면 「**매입가보다 몇 % 빠졌나**」를 알아야 하는데,
            #    여태 `now_pr`(현재가)만 뽑고 있어서 **매입가를 몰랐다.**
            #    잔고 API 가 17개 필드를 주는데 그중 `phs_pr`·`pft_rt` 가 있었다.
            #    ⚠️ 금액은 **화면에 안 나간다** — 「-5% 빠졌다」는 **비율**만 낸다
            #    ⚠️ 여러 계좌에 나뉘어 있으면 **수량 가중 평균**이어야 맞다
            매입 = _num(r.get("phs_pr")) or 0
            h = hold.setdefault(code, {"code": code, "name": name,
                                       "섹터": sec_idx.get(name, "미분류"),
                                       "평가금액": 0.0, "수량": 0.0, "계좌수": 0,
                                       "_매입합": 0.0})
            h["평가금액"] += amt
            h["수량"] += qty
            h["계좌수"] += 1
            if 매입 > 0:
                h["_매입합"] += 매입 * qty
        # ⚠️ 같은 계좌의 **해외 보유**를 이어서 담는다. 국내와 한 그릇에 넣어야
        #    "내 돈이 어디에 몰려 있나"가 나온다 — 국장·미장을 갈라 놓으면 쏠림이 안 보인다.
        for 종류, 나라, r in balance_해외(a["no"]):
            if 종류 == "실패":
                실패.append({"계좌": _mask(a["no"]), "구분": f"해외·{나라}", "오류": r})
                continue
            code = (r.get("iem_cd") or "").strip()          # 티커 (AAPL 등)
            name = (r.get("iem_nm") or r.get("oss_iem_eng_nm") or "").strip()
            qty = _num(r.get("cns_bse_bnc_qty")) or 0
            amt = _num(r.get("krw_eal_amt")) or 0
            if not code or qty <= 0 or amt <= 0:
                continue
            h = hold.setdefault(code, {
                "code": code, "name": name or code,
                "섹터": (sec_ovs.get(code) or sec_idx.get(name) or "미분류"),
                "평가금액": 0.0, "수량": 0.0, "계좌수": 0, "시장": 나라})
            h["평가금액"] += amt
            h["수량"] += qty
            h["계좌수"] += 1

    # 손으로 적은 계좌를 합친다. 같은 종목이면 금액을 더한다.
    시세 = _krx_시세()
    # ⚠️ **종목명으로도 적을 수 있게 한다.** 사람은 코드를 안 외운다. 코드를 강요하면
    #    "005930"을 "05930"으로 적는 실수가 나고, 그건 조용히 시세없음으로 빠진다.
    이름코드 = {nm: c for c, (nm, _) in 시세.items() if nm}
    시세없음, 이름모름 = [], []
    for m in _수동():
        code = str(m.get("code") or "").strip()
        if not code and m.get("name"):
            code = 이름코드.get(str(m["name"]).strip(), "")
            if not code:
                이름모름.append(m.get("name"))
        code = code.zfill(6) if code else ""
        if not code:
            continue
        qty = _num(m.get("수량")) or 0
        krx이름, krx종가 = 시세.get(code, (None, None))
        # 금액을 적었으면 그걸 쓰고, 아니면 **수량 × KRX 종가**로 계산한다.
        amt = _num(m.get("평가금액"))
        if amt is None:
            amt = qty * krx종가 if (qty and krx종가) else 0
            if qty and not krx종가:
                시세없음.append(code)
        name = m.get("name") or krx이름 or code
        h = hold.setdefault(code, {"code": code, "name": name,
                                   "섹터": m.get("섹터")
                                   or sec_idx.get(name, "미분류"),
                                   "평가금액": 0.0, "수량": 0.0, "계좌수": 0})
        h["평가금액"] += amt
        h["수량"] += qty
        h["출처"] = "수동"
    # ⭐ 매입가를 **수량 가중 평균**으로 굳히고, 지금 몇 % 위/아래인지 함께 낸다.
    #    ⚠️ `매입가대비` 만 화면에 쓸 수 있다 — 매입가 자체는 **금액**이라 안 나간다
    for _h in hold.values():
        _합 = _h.pop("_매입합", 0.0)
        _수 = _h.get("수량") or 0
        if _합 > 0 and _수 > 0:
            _평단 = _합 / _수
            _h["매입가"] = _평단
            _이제 = (_h.get("평가금액") or 0) / _수
            if _평단 > 0:
                _h["매입가대비"] = round((_이제 / _평단 - 1) * 100, 2)
    return (acs, sorted(hold.values(), key=lambda x: -x["평가금액"]),
            실패, 시세없음, 이름모름, 불일치)


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", action="store_true", help="계좌 목록만 본다")
    ap.add_argument("--exclude", nargs="*", default=[], help="뺄 계좌번호")
    a = ap.parse_args()
    try:
        if a.accounts:
            rows = accounts()
            print(json.dumps({"ok": True, "계좌": [
                {"계좌": _mask(x["no"]), "구분": x["env"], "사용가능": x["usable"]}
                for x in rows]}, ensure_ascii=False))
            return 0

        acs, hold, 실패, 시세없음, 이름모름, 불일치 = collect(set(a.exclude))
        미분류 = [h["name"] for h in hold if h["섹터"] == "미분류"]
        d = {
            "_설명": "⚠️ 금액은 **화면에 나가지 않는다.** 섹터 비율 계산에만 쓴다.",
            "_주의": "계좌번호·주문내역은 넣지 않는다. 이 파일은 공개 사이트의 재료다.",
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "계좌수": len(acs),
            # ⚠️ `수량`도 화면에 안 나간다. 나중에 대조할 일이 있어 파일에만 남긴다.
            "holdings": [{k: v for k, v in h.items() if k != "계좌수"} for h in hold],
            # ⚠️ 손으로 적은 것은 **그대로 되돌려 쓴다.** 안 그러면 매일 갱신이 지운다.
            "수동": _수동(),
            "_수동설명": "NH PLUG가 못 보는 계좌(ISA·연금)를 여기에 적는다. "
                      "**코드와 수량만** 적으면 된다 — 금액은 KRX 종가로 계산한다. "
                      "형식: {\"name\":\"삼성전자\",\"수량\":10} 또는 "
                      "{\"code\":\"005930\",\"수량\":10}. "
                      "매일 갱신해도 이 항목은 지워지지 않는다.",
        }
        with io.open(OUT, "w", encoding="utf-8") as fp:
            json.dump(d, fp, ensure_ascii=False, indent=2)
        res = {"ok": True, "계좌": len(acs), "종목": len(hold)}
        경고 = _만료경고()
        if 경고:
            res["경고"] = 경고
        if 미분류:
            res["섹터_미분류"] = 미분류
        if 불일치:
            # ⚠️ 막지는 않는다. 다만 **반드시 눈에 띄게** 남긴다.
            res["잔량_불일치"] = 불일치
        if 이름모름:
            # ⚠️ 이름을 못 찾으면 그 종목은 통째로 빠진다. 반드시 말한다.
            res["수동_이름못찾음"] = 이름모름
        if 시세없음:
            # ⚠️ 조용히 0원으로 두지 않는다. 비율에서 빠진 종목은 반드시 말한다.
            res["수동_시세없음"] = 시세없음
        if 실패:
            res["실패"] = 실패
        print(json.dumps(res, ensure_ascii=False))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "오류": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
