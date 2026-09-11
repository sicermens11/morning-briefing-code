# 펀더멘털 캐시 (F2·VAL·RISK 전용, 2026-07-31 신설)

morning-sector-briefing STEP3.5의 강화-F2·강화-VAL·강화-RISK 결과를 종목코드(stock_code) 기준으로 캐싱하는 파일입니다. 이 3개는 분기·연간 공시 기반이라 며칠 사이 거의 변하지 않으므로, 같은 종목이 최근 10거래일 내 재등장하면 이 캐시를 재사용하고 3개 호출을 생략합니다.

⚠️ D1·E·P·TA·PREF·CAP·BUYBACK·OWNERSHIP은 이 캐시 대상이 아닙니다 — 신규 공시·이벤트 감지가 목적인 항목이라 항상 매번 새로 조회합니다.

형식(종목코드당 1개 항목, 재등장 시 upsert — 있으면 갱신, 없으면 추가):

```
## [종목코드] [종목명]
갱신일자: [YYYY-MM-DD]
F2: 부채비율 [X]% | 순이익률 [X]% | 성장률(CAGR) [X]% | 자본잠식 [여부]
VAL: PER [X] | PBR [X] | 시나리오밸류(비관/중립/낙관) [값1]/[값2]/[값3]
RISK: negative_cfo_streak=[true/false] | revenue_decline_streak=[true/false] | earnings_cash_divergence=[true/false]
```

---

## 058470 리노공업
갱신일자: 2026-08-07
F2: 부채비율 8.3% | 순이익률 40.8% | 성장률(CAGR) 20.7%(매출, 2년) | 자본잠식 없음
VAL: PER 33.55 | PBR 6.97 | 시나리오밸류(비관/중립/낙관) 15,951/23,082/31,847
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false

## 237690 에스티팜
갱신일자: 2026-08-07
F2: 부채비율 32.0% | 순이익률 16.5% | 성장률(CAGR) 76.5%(순이익, 2년) | 자본잠식 없음
VAL: PER 38.76 | PBR 3.57 | 시나리오밸류(비관/중립/낙관) 20,908/34,786/54,194
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false

---

## 189330 씨이랩
갱신일자: 2026-08-05
F2: 부채비율 17.2% | 순이익률 -30.4% | 성장률(CAGR) +15.5% | 자본잠식 없음
VAL: PER 적자(N/A) | PBR 4.11 | 시나리오밸류(비관/중립/낙관) N/A/N/A/N/A
RISK: negative_cfo_streak=true | revenue_decline_streak=false | earnings_cash_divergence=N/A

## 012450 한화에어로스페이스
갱신일자: 2026-08-11
F2: 부채비율 221.38% | 순이익률 8.25% | 성장률(CAGR) 64.36%(순이익, 4년) | 자본잠식 없음
VAL: PER 25.43 | PBR 3.34 | 시나리오밸류(비관/중립/낙관) 341,635/568,395/885,518
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false | high_debt_ratio=true

## 034020 두산에너빌리티
갱신일자: 2026-08-11
F2: 부채비율 129.1% | 순이익률 1.2% | 성장률(CAGR) -24.92%(순이익, 4년) | 자본잠식 없음
VAL: PER 242.6 | PBR 4.14 | 시나리오밸류(비관/중립/낙관) 1,084/2,149/3,843 (기계적 산출, 수주잔고 미반영)
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false | low_interest_coverage=true

## 023160 태광
갱신일자: 2026-08-12
F2: 부채비율 10.63% | 순이익률 22.06% | 성장률(CAGR) +37.09%(순이익, 4년) | 자본잠식 없음
VAL: PER 9.63 | PBR 0.94 | 시나리오밸류(비관/중립/낙관) 20,262/33,710/52,518
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false

## 420770 기가비스
갱신일자: 2026-08-12
F2: 부채비율 13.4% | 순이익률 29.47% | 성장률(CAGR) -31.22%(순이익, 2년) | 자본잠식 없음
VAL: PER 96.31 | PBR 7.05 | 시나리오밸류(비관/중립/낙관) 3,173/7,326/14,628 (기계적 산출, 수주모멘텀 미반영)
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false

## 041830 인바디
갱신일자: 2026-08-12
F2: 부채비율 12.91% | 순이익률 12.82% | 성장률(CAGR) -3.08%(순이익, 4년) | 자본잠식 없음
VAL: PER 31.42 | PBR 2.95 | 시나리오밸류(비관/중립/낙관) 16,201/21,233/26,693 (기계적 산출)
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false

## 010120 엘에스일렉트릭
갱신일자: 2026-09-01
F2: 부채비율 131.48% | 순이익률 5.72% | 성장률(CAGR) 16.99%(순이익, 2년) | 자본잠식 없음 | ROE 13.27% | 당좌비율 105.92% | FCF +991억
VAL: PER 109.50 | PBR 14.54 | 시나리오밸류(비관/중립/낙관) 15,160/25,223/39,296 (기계적 산출, 현재가 207,500원 대비 대폭 고평가)
RISK: 적신호 0건 — negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false | low_interest_coverage=false(이자보상배율 7.09) | capital_impairment=false
분기추세(2026.06): 부채비율 172.12%(3분기 연속 상승 — 연간 131.48%와 괴리 주의) | 영업이익률 11.32% | ROE 19.30%

## 010140 삼성중공업
갱신일자: 2026-09-01
F2: 부채비율 265.05% | 순이익률 5.03% | 성장률(CAGR) 15.31%(매출, 2년) | 자본잠식 없음 | ROE 13.08%(3년 -4.22→1.77→13.73 개선) | 당좌비율 49.69% | CFO +1.56조 / FCF +1.35조
VAL: PER 34.33 | PBR 4.49 | 시나리오밸류(비관/중립/낙관) 4,870/6,088/7,306 (성장이력 없음 0% 가정 — 흑자전환 초기라 과도하게 보수적)
RISK: high_debt_ratio=true(265%) ⚠️ 조선 부채비율 구조적 예외 적용해 재무취약 미판정 | negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false | low_interest_coverage=조회불가(이자비용 null)
분기추세(2026.06): 부채비율 281.27% | 영업이익률 10.06% | ROE 13.42%

## 071970 HD현대마린엔진
갱신일자: 2026-08-20
F2: 부채비율 66.63% | 순이익률 41.03% | 성장률(CAGR) 25.18%(매출, 4년) | 자본잠식 없음
VAL: PER 11.12 | PBR 3.75 | 시나리오밸류(비관/중립/낙관) 38,937/48,672/58,406
RISK: negative_cfo_streak=false | revenue_decline_streak=false | earnings_cash_divergence=false

## 025560 미래산업
갱신일자: 2026-09-01
F2: 부채비율 24.26% | 순이익률 19.91% | 성장률(CAGR) 52.83%(매출, 2년, 순이익 CAGR은 적자전환으로 산출불가) | 자본잠식 없음 | ROE 8.25% | 당좌비율 126.74% | CFO 2025년 -52억(음수)
VAL: PER 18.08 | PBR 1.49 | 시나리오밸류(비관/중립/낙관) 2,912/4,083/5,471 (현재가 6,580원 대비 중립 기준 61% 고평가)
RISK: earnings_cash_divergence=true ⚠️ 재무취약(-2) 근거 — cfo_to_net_income 2024년 0.05 / 2025년 -0.51 | high_debt_ratio=false | low_interest_coverage=false(이자보상배율 3) | negative_cfo_streak=false | revenue_decline_streak=false | capital_impairment=false
분기추세(2026.06): 부채비율 36.26% | 영업이익률 33.64% | ROE 19.41% (분기 실적은 빠르게 개선 중)
CAP: 2026-07-09 유상증자결정 정정 · 2026-07-27 유상증자 발행결과 → 3개월내 유상증자 -2점

## 207940 삼성바이오로직스
갱신일자: 2026-09-01
F2: 부채비율 48.44% | 순이익률 39.16% | 성장률(CAGR) 44.24%(순이익, 2년) | 자본잠식 없음 | ROE 23.95% | 당좌비율 85.93% | CFO +2.25조 / FCF +8,561억 | 이자보상배율 14.64
VAL: PER 39.38 | PBR 9.43 | 시나리오밸류(비관/중립/낙관) 308,372/513,053/799,299 | PEG 0.89(성장 대비 저평가 참고) | 과거 PER 밴드 92.82→91.76→63.79로 하향 중
RISK: 적신호 0건 — high_debt_ratio=false | low_interest_coverage=false | negative_cfo_streak=false | revenue_decline_streak=false | capital_impairment=false | earnings_cash_divergence=false
분기추세(2026.06): 부채비율 51.31% | 영업이익률 44.40% | ROE 19.88%
CAP: 2026-08-28 유상증자 결정(3조원, 펩타이드 사업 인수 자금) → 3개월내 유상증자 -2점

## 042660 한화오션
갱신일자: 2026-09-03
F2: 부채비율 226.17% | 순이익률 9.75% | 성장률(CAGR) 179.01%(순이익, 2년) | 자본잠식 없음 | ROE 20.18% | 당좌비율 30.88%(3년 연속 악화 50.56→32.77→30.88) | CFO +1.31조 / FCF +6,051억 | 이자보상배율 1.52
VAL: PER 20.17 | PBR 4.07 | 시나리오밸류(비관/중립/낙관) 32,529/40,661/48,794 (성장 이력 미인식 0% 가정 기계적 산출, 현재가 82,000원은 중립가의 2.02배) | 과거 PER 밴드 33.15→21.67→27.94
RISK: high_debt_ratio=true(226.2%) ⚠️ 조선 부채비율 구조적 예외 적용해 재무취약 미판정 | low_interest_coverage=false(1.52) | negative_cfo_streak=false | revenue_decline_streak=false | capital_impairment=false | earnings_cash_divergence=false
분기추세(2026.06): 부채비율 167.61%(3분기 연속 개선 226.17→204.67→167.61, 연간 226.17%와 괴리) | 영업이익률 13.52% | ROE 32.55%
CAP/BUYBACK: 3개월내 유상증자 없음 · 2025 사업보고서 자기주식 소각 없음(기타취득 16,207주)

## 267260 HD현대일렉트릭
갱신일자: 2026-09-03
F2: 부채비율 134.63% | 순이익률 17.94% | 성장률(CAGR) 67.95%(순이익, 2년) | 자본잠식 없음 | ROE 36.0% | 당좌비율 72.30%(100 미만) | CFO +9,596억 / FCF +7,261억 | 이자보상배율 6.39
VAL: PER 35.02 | PBR 12.61 | 시나리오밸류(비관/중립/낙관) 162,413/203,016/243,620 ⚠️ 도구가 성장 이력을 인식 못 해 0% 가정 — 실제 순이익 CAGR 67.95%라 실제보다 크게 낮음, 방향만 채택 | 과거 PER 밴드 11.43→27.45→38.08 상향 지속
RISK: 적신호 0건 — high_debt_ratio=false | low_interest_coverage=false(6.39) | negative_cfo_streak=false | revenue_decline_streak=false | capital_impairment=false | earnings_cash_divergence=false
분기추세(2026.06): 부채비율 143.18% | 영업이익률 25.14% | ROE 43.70%
CAP/BUYBACK: 3개월내 유상증자 없음 · 2025 사업보고서 자기주식 소각 없음(보통주 기타취득 54,431주)

## 036930 주성엔지니어링
갱신일자: 2026-09-03
F2: 부채비율 50.37% | 순이익률 11.49% | 성장률(CAGR) 2.46%(순이익, 2년) | 자본잠식 없음 | ROE 6.05%(10% 미만) | 당좌비율 261.82% | CFO 2025년 -307억(음수 1년, 2년 연속 아님) | 이자보상배율 8.04
VAL: PER 226.20 | PBR 13.67 | 시나리오밸류(비관/중립/낙관) 2,142/4,748/9,215 (과거 4년 순이익 CAGR -29.62% 반영으로 회복국면 미반영, 현재가 173,700원은 중립가의 36.6배) | 과거 PER 밴드 48.53→13.18→36.68
RISK: 적신호 0건 — high_debt_ratio=false(50.4%) | low_interest_coverage=false(8.04) | negative_cfo_streak=false | revenue_decline_streak=false | capital_impairment=false | earnings_cash_divergence=false
분기추세(2026.06): 부채비율 46.37% | 영업이익률 2.38% | 2025.12 -24.07%·2026.03 -12.81% 영업적자 후 2026.06 흑자전환, 2026.09 잠정 21.85%
공매도: 최근5일 11.07%(직전 7.35%, 급증) — 외국인 순매수와 방향 갈림

## 082740 한화엔진
갱신일자: 2026-09-03
F2: 부채비율 204.92% | 순이익률 12.67% | 성장률(CAGR) 매출 26.68%(순이익은 적자전환으로 산출불가) | 자본잠식 없음 | ROE 31.24% | 당좌비율 110.55% | CFO +3,303억 / FCF +2,970억
VAL: PER 21.44 | PBR 6.70 | 시나리오밸류(비관/중립/낙관) 16,658/20,822/24,986
RISK: high_debt_ratio=true(204.9%, 조선 구조적 예외로 단독 미판정) + **low_interest_coverage=true(이자보상배율 0.75)** ⚠️ 이 항목으로 재무취약 -2점 확정 — 조선 예외는 부채비율 단독 조건만 제외한다 | negative_cfo_streak=false | revenue_decline_streak=false | capital_impairment=false | earnings_cash_divergence=false
분기추세(2026.06): 부채비율 234.09%(연간 204.92%보다 악화) | 영업이익률 10.47%
CAP/BUYBACK: 2026-07-14 자기주식취득결정 · 2026-08-03 취득결과보고서 — **취득이지 소각이 아니므로 +1점 미부여**. 유상증자 없음
비고: 2026-09-03 브리핑에서 검증했으나 갭 4가지 전부 미충족으로 후보 제외
