#!/usr/bin/env python3
r"""
kis_api.py — **한국투자증권 Open API 조회 전용** (2026-10-22 신설 · 사용자 「넣었어」)

⚠️⚠️⚠️ **주문 함수가 없다. 일부러 없다.** 이 파일엔 조회(GET)만 둔다.
   주문(매수·매도·정정·취소)은 사용자가 명시해서 정한 뒤 **다른 파일**에 만든다. 여기에 더하지 않는다.
⚠️ 열쇠는 config.get 으로만 읽는다(secrets.json · 채팅 금지). 로그·예외에 열쇠·토큰을 찍지 않는다.
⚠️ 접근토큰은 **발급할 때마다 알림톡이 간다**(공식 kis_auth.py 주석) → data/_kis_token_<모의|실전>.json 에 24시간 묵혀 쓴다.

주소·TR 이름은 공식 저장소(koreainvestment/open-trading-api examples_llm)에서 그대로 옮겼다(10/22):
  모의 https://openapivts.koreainvestment.com:29443 · 실전 https://openapi.koreainvestment.com:9443
  토큰   POST /oauth2/tokenP {grant_type: client_credentials, appkey, appsecret}
  잔고   GET  /uapi/domestic-stock/v1/trading/inquire-balance        TTTC8434R / 모의 VTTC8434R
  체결   GET  /uapi/domestic-stock/v1/trading/inquire-daily-ccld     TTTC0081R / 모의 VTTC0081R (3개월 안)
  현재가 GET  /uapi/domestic-stock/v1/quotations/inquire-price       FHKST01010100
  예상체결 GET /uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn  FHKST01010200 (output2 = 예상체결)
헤더: appkey · appsecret · authorization: Bearer · tr_id · custtype P
계좌: CANO = 8자리 · ACNT_PRDT_CD = "01"(위탁종합 — 10/22 사용자 계좌)

쓰는 법:
    python scripts\kis_api.py --잔고                 모의 계좌 잔고(현금·보유)
    python scripts\kis_api.py --현재가 005930 000660  현재가·예상체결
    python scripts\kis_api.py --체결 20261022         그날 주문·체결 내역
    (실전은 --실전 을 붙인다 · 열쇠가 없으면 안 돈다)
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_BASE, "data")
_URL = {"모의": "https://openapivts.koreainvestment.com:29443", "실전": "https://openapi.koreainvestment.com:9443"}
_KEYS = {"모의": ("KIS_MOCK_APP_KEY", "KIS_MOCK_APP_SECRET", "KIS_MOCK_ACCOUNT"),
         "실전": ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT")}
_TR = {"잔고": {"모의": "VTTC8434R", "실전": "TTTC8434R"},
       "체결": {"모의": "VTTC0081R", "실전": "TTTC0081R"},
       "현재가": {"모의": "FHKST01010100", "실전": "FHKST01010100"},
       "예상체결": {"모의": "FHKST01010200", "실전": "FHKST01010200"}}
상품코드 = "01"


class KIS:
    def __init__(self, 환경="모의"):
        if 환경 not in _URL:
            raise ValueError("환경은 모의 또는 실전")
        self.환경 = 환경
        k1, k2, k3 = _KEYS[환경]
        self.appkey, self.secret, self.계좌 = config.get(k1), config.get(k2), config.get(k3)
        if not (self.appkey and self.secret and self.계좌):
            raise RuntimeError(f"{환경} 열쇠가 없다 — secrets.json 의 {k1}·{k2}·{k3} (값은 채팅에 올리지 않는다)")
        self.base = _URL[환경]
        self._토큰파일 = os.path.join(_DATA, f"_kis_token_{환경}.json")
        self.토큰 = self._토큰()

    # ── 토큰 (24시간 묵혀 쓴다 · 발급마다 알림톡이 가므로 함부로 다시 받지 않는다) ──
    def _토큰(self):
        try:
            j = json.load(io.open(self._토큰파일, encoding="utf-8"))
            if time.time() - float(j.get("받은때", 0)) < 23 * 3600 and j.get("token"):
                return j["token"]
        except (OSError, ValueError):
            pass
        body = json.dumps({"grant_type": "client_credentials", "appkey": self.appkey, "appsecret": self.secret}).encode()
        req = urllib.request.Request(self.base + "/oauth2/tokenP", data=body, headers={"content-type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8"))
        tok = j.get("access_token")
        if not tok:
            raise RuntimeError("토큰 발급 응답에 access_token 이 없다")
        try:
            os.makedirs(_DATA, exist_ok=True)
            with io.open(self._토큰파일, "w", encoding="utf-8") as f:
                json.dump({"token": tok, "받은때": time.time(), "만료": j.get("access_token_token_expired")}, f)
        except OSError:
            pass
        return tok

    _마지막 = 0.0

    def _get(self, path, tr, params):
        url = self.base + path + "?" + urllib.parse.urlencode(params)
        h = {"content-type": "application/json; charset=utf-8", "authorization": f"Bearer {self.토큰}",
             "appkey": self.appkey, "appsecret": self.secret, "tr_id": tr, "custtype": "P"}
        # 10/22 실측: 모의투자는 초당 호출 제한이 낮다(EGW00201 「초당 거래건수 초과」) → 요청 사이 0.6초 · 걸리면 1.5초 쉬고 두 번 더
        #    실전은 문서상 초당 20번이지만 실측(10/22) 여섯 프로세스 12번/초에서 바로 EGW00201 → 0.25초 · 걸리면 2·4·6·8초 쉬고 다시(여섯 번)
        for 시도 in range(6):
            쉼 = (0.25 if self.환경 == "실전" else 0.6) - (time.time() - KIS._마지막)
            if 쉼 > 0:
                time.sleep(쉼)
            KIS._마지막 = time.time()
            req = urllib.request.Request(url, headers=h)
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    j = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                txt = e.read().decode("utf-8", errors="replace")[:300]
                if "EGW00201" in txt and 시도 < 5:
                    time.sleep(2 * (시도 + 1))
                    continue
                raise RuntimeError(f"{tr} HTTP {e.code}: {txt}") from None
        if str(j.get("rt_cd")) != "0":
            raise RuntimeError(f"{tr} 실패 rt_cd={j.get('rt_cd')} msg_cd={j.get('msg_cd')} {j.get('msg1')}")
        return j

    def 토큰폐기(self):
        """접근토큰을 서버에서 죽인다(/oauth2/revokeP) · 토큰 파일 삭제 — 실전 열쇠를 지우기 전에 부른다(10/22 사용자 「실전 열쇠로 받고 키를 지우면 어때?」)"""
        body = json.dumps({"appkey": self.appkey, "appsecret": self.secret, "token": self.토큰}).encode()
        req = urllib.request.Request(self.base + "/oauth2/revokeP", data=body, headers={"content-type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.loads(r.read().decode("utf-8"))
            결과 = f"폐기 응답 {j.get('code')} {j.get('message')}"
        except urllib.error.HTTPError as e:
            결과 = f"폐기 HTTP {e.code}"
        try:
            os.remove(self._토큰파일)
            결과 += " · 토큰 파일 삭제"
        except OSError:
            pass
        self.토큰 = None
        return 결과

    # ── 조회들 ──
    def 공매도일별(self, 코드, 시작8, 끝8):
        j = self._get("/uapi/domestic-stock/v1/quotations/daily-short-sale", "FHPST04830000",
                      {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": 코드, "FID_INPUT_DATE_1": 시작8, "FID_INPUT_DATE_2": 끝8})
        return j.get("output2") or j.get("output") or []

    def 신용잔고일별(self, 코드, 기준8):
        """기준일부터 거슬러 30건(결제일 기준) — 더 받으려면 가장 옛 deal_date 전날을 다시 넣는다"""
        j = self._get("/uapi/domestic-stock/v1/quotations/daily-credit-balance", "FHPST04760000",
                      {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "20476", "FID_INPUT_ISCD": 코드, "FID_INPUT_DATE_1": 기준8})
        return j.get("output") or []

    def 대차일별(self, 코드, 시작8, 끝8):
        """종목별 대차 잔고 — 시장코드 **3 = 종목**(1·2 는 코스피·코스닥 전체 합계였다 · 10/23 실측) · 한 번 최대 100건 · 최근 것부터 · 2014~"""
        j = self._get("/uapi/domestic-stock/v1/quotations/daily-loan-trans", "HHPST074500C0",
                      {"MRKT_DIV_CLS_CODE": "3", "MKSC_SHRN_ISCD": 코드, "START_DATE": 시작8, "END_DATE": 끝8, "CTS": ""})
        return j.get("output1") or []

    def 투자의견(self, 코드, 시작8, 끝8):
        """증권사 투자의견·목표가 — 한 번 최대 100건 · 최근 것부터 · 2010~(대형주만 촘촘)"""
        j = self._get("/uapi/domestic-stock/v1/quotations/invest-opinion", "FHKST663300C0",
                      {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "16633", "FID_INPUT_ISCD": 코드,
                       "FID_INPUT_DATE_1": 시작8, "FID_INPUT_DATE_2": 끝8})
        return j.get("output") or []

    def 잔고(self):
        j = self._get("/uapi/domestic-stock/v1/trading/inquire-balance", _TR["잔고"][self.환경], {
            "CANO": self.계좌, "ACNT_PRDT_CD": 상품코드, "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00", "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""})
        return {"보유": j.get("output1") or [], "요약": (j.get("output2") or [{}])[0]}

    def 현재가(self, 코드):
        j = self._get("/uapi/domestic-stock/v1/quotations/inquire-price", _TR["현재가"][self.환경],
                      {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": 코드})
        return j.get("output") or {}

    def 예상체결(self, 코드):
        j = self._get("/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn", _TR["예상체결"][self.환경],
                      {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": 코드})
        return {"호가": j.get("output1") or {}, "예상": j.get("output2") or {}}

    def 체결(self, 시작8, 끝8=None):
        j = self._get("/uapi/domestic-stock/v1/trading/inquire-daily-ccld", _TR["체결"][self.환경], {
            "CANO": self.계좌, "ACNT_PRDT_CD": 상품코드, "INQR_STRT_DT": 시작8, "INQR_END_DT": 끝8 or 시작8,
            "SLL_BUY_DVSN_CD": "00", "PDNO": "", "CCLD_DVSN": "00", "INQR_DVSN": "00", "INQR_DVSN_3": "00",
            "ORD_GNO_BRNO": "", "ODNO": "", "INQR_DVSN_1": "", "CTX_AREA_FK100": "", "CTX_AREA_NK100": "", "EXCG_ID_DVSN_CD": "KRX"})
        return j.get("output1") or []


def _원(v):
    try:
        return f"{int(float(v)):,}"
    except (TypeError, ValueError):
        return str(v)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    환경 = "실전" if "--실전" in sys.argv else "모의"
    k = KIS(환경)
    print(f"[{환경}] 계좌 끝 {k.계좌[-4:]} · {dt.datetime.now():%m-%d %H:%M}")
    if "--잔고" in sys.argv:
        b = k.잔고()
        s = b["요약"]
        print(f"  예수금 {_원(s.get('dnca_tot_amt'))} · 총평가 {_원(s.get('tot_evlu_amt'))} · 주문가능현금 {_원(s.get('prvs_rcdl_excc_amt') or s.get('nxdy_excc_amt'))}")
        for x in b["보유"]:
            if float(x.get("hldg_qty") or 0) > 0:
                print(f"  보유 {x.get('prdt_name')} {x.get('pdno')} {_원(x.get('hldg_qty'))}주 · 평균 {_원(x.get('pchs_avg_pric'))} · 현재 {_원(x.get('prpr'))} · 평가손익 {_원(x.get('evlu_pfls_amt'))}")
        if not any(float(x.get("hldg_qty") or 0) > 0 for x in b["보유"]):
            print("  보유 없음")
    if "--현재가" in sys.argv:
        i = sys.argv.index("--현재가")
        코드들 = []
        for z in sys.argv[i + 1:]:
            if z.startswith("--"):
                break
            코드들.append(z)
        for c in 코드들:
            p = k.현재가(c)
            e = k.예상체결(c)["예상"]
            print(f"  {c} 현재가 {_원(p.get('stck_prpr'))} · 전일 {_원(p.get('stck_sdpr'))} · 등락 {p.get('prdy_ctrt')}% · "
                  f"예상체결가 {_원(e.get('antc_cnpr'))} · 예상량 {_원(e.get('antc_cnqn'))} · 예상등락 {e.get('antc_cntg_prdy_ctrt')}%")
    if "--체결" in sys.argv:
        i = sys.argv.index("--체결")
        d = sys.argv[i + 1] if i + 1 < len(sys.argv) else dt.date.today().strftime("%Y%m%d")
        rows = k.체결(d)
        print(f"  {d} 주문·체결 {len(rows)}건")
        for x in rows:
            print(f"   {x.get('ord_tmd')} {x.get('prdt_name')} {x.get('pdno')} {x.get('sll_buy_dvsn_cd_name')} 주문 {_원(x.get('ord_qty'))}@{_원(x.get('ord_unpr'))} "
                  f"체결 {_원(x.get('tot_ccld_qty'))}@{_원(x.get('avg_prvs'))} · {x.get('ord_dvsn_name')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
