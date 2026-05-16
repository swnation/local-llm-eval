# R4 Review Packet — v0.2 quick rerun 결과 해석

**Round**: R4 (v0.2 final → quick rerun 결과 sign-off)
**작성**: 2026-05-16, Claude Code (autonomous run 종료 후)
**선행 round**: R1 GO (v0.2 prompt set) / R2 GO (Step 1 산출물) / R3 GO (compute_score 분기 순서)
**성격**: 결과 해석 sign-off — must-fix only loop 아님

---

## §1. Scope

본 review의 범위:

✅ **포함**:
- quick rerun 결과 해석의 타당성 검토
- provisional production 후보 판단의 합리성 검토
- 64GB part 2 진입 전 추가 최소 검증 의견

❌ **제외** (별도 round에서 다룸):
- v0.2 prompt set 본문 재검토 (R1 GO 완료)
- `score_runner.py` 전체 코드리뷰 (D smoke fixture로 검증 통과)
- `SCORING_CONTRACT.md` rubric 재설계 (R2/R3 GO 완료)
- production 최종 채택 확정 (32GB only 평가, 64GB part 2 후 결정)

---

## §2. Attached files (reviewer가 봐야 할 범위)

**필수**:
- `reviews/quick-rerun-2026-05-16-report.md` ← **본 review 대상 본문**
  - §0 TL;DR + §2 종합 ranking + §5 보조 실험 + §7 production 권고 우선

**보조 (필요 시 참조)**:
- `score_runner.py` (SCORING_CONTRACT.md 구현체)
- `SCORING_CONTRACT.md` (rubric spec)
- `results/_scored_quick_rerun_20260516.json` (Step 4 채점 raw)
- `results/_scored_hari8b_chatml_20260516.json` (§5.1)
- `results/_scored_hari14b_chatml_20260516.json` (§5.5)
- `results/_scored_gpt_oss_medium_20260516.json` (§5.2)
- `results/clinical_hari_a02_retry_20260516_*.json` (§5.6)
- `results/ministral_d02_retry_20260516_*.json` (§5.3)

---

## §3. Review questions

### Q1. provisional production 후보 판단 (시나리오 C)

본 리포트 §7은 **`gpt-oss-20b 단독 + dynamic reasoning_effort` (D=low, A/B/C=medium)** 를 시나리오 C로 추천하며, 그 근거로:

- hard_fail 0건 (단일 모델 운영의 핵심 안정성)
- D avg 4.67 (clinical-hari-q5와 동률)
- C medium 적용 시 2.00 → 3.33 (§5.2 실증)
- 모델 로드/스왑 비용 없음

**Q1**: 이 판단이 타당한가? medium의 A/B/D 미검증을 알면서 provisional production 후보로 두는 게 합리적 보수성 수준인가?

### Q2. clinical-hari-q5 1위 보류 해석

`clinical-hari-q5-current` 가 종합 avg 3.15 (retry 적용 시 ~3.4 추정)로 가장 높은 점수지만, 본 리포트는 production 1순위로 두지 않음. 이유:

- A_02 단발 빈응답 (§5.6 retry 3/3 정상 — 단발 ollama quirk)
- A 카테고리 응답이 일관되게 JSON 형식 (text format 강제 system prompt overlay 필요)
- 두 가지 모두 운영 패치로 회피 가능하지만 시나리오 C(gpt-oss)는 그런 패치 없이 hard_fail 0건

**Q2**: 점수 1위를 후보 보류로 두는 해석이 합리적인가? 또는 retry 패치 + system overlay를 명시 운영 조건으로 묶어 1순위로 올리는 게 더 정직한가?

### Q3. hari-14b-chatml formatter-only 후보 분리

`hari-14b-i1-chatml` 은 §5.5에서 A 카테고리 3.00 (전체 1위)을 받았지만 B/C는 평범하고 D는 모두 hard_fail. 본 리포트는 이 모델을 **차팅 정리 전용 (Formatter)** 후보로 분리 기록.

**Q3**: 단일 모델 운영 대신 역할 분리 시 hari-14b-chatml을 Formatter로 따로 운영하는 시나리오를 별도 항목으로 유지하는 게 합리적인가? 또는 시나리오 C 단독 운영을 채택했다면 14b-chatml 별도 운영은 over-engineering으로 보는 게 맞는가?

### Q4. 64GB part 2 전 최소 추가 검증

본 평가는 32GB 환경 한정. 다음 단계는 64GB 업그레이드 후 Qwen3.6-35B / Gemma 4 26B/31B / magistral / exaone4 GPU+CPU split. 그 전에 32GB 환경에서 반드시 더 돌려야 할 검증이 있는가?

특히 후보:

- **gpt-oss medium 으로 A/B/D 카테고리도 평가** (현재 medium은 C만 검증) — 시나리오 C 정합성 확인용
- ministral Mistral V7 명시 template Modelfile 재시도 — D_02 1 token EOT 이슈 진단
- clinical-hari-q5 retry x N으로 A_02 quirk 발생률 측정 (단발 vs 일관 패턴)
- gpt-oss `reasoning_effort='high'` 1~2 prompt 실험 — medium보다 더 좋아지는지 vs 속도 trade-off

**Q4**: 위 중 어떤 것이 64GB 진입 전 **반드시** 필요한지, 그리고 64GB로 미루어도 되는지 의견 요청.

---

## §4. Non-goals

다음은 본 R4 round에서 **요청 X**:

- v0.2 prompt 본문 수정 (R1 GO 완료 — 단 결과 해석을 뒤집을 must-fix가 있다면 예외)
- scoring rubric 재설계 (R2/R3 GO 완료 — 단 채점 결과 자체에 bug가 있다면 예외)
- production 최종 채택 확정 (64GB part 2 후 별도 round)

→ Q1~Q4 외 must-fix 발견 시에는 알려주되, 그 외 prompt/rubric/scorer 영역 의견은 backlog로 기록만.

---

## §5. 판정 형식 권장

```
판정: GO | CONDITIONAL GO | NOT GO

Q1 (production 후보 판단): {정성 의견}
Q2 (clinical-hari 보류 해석): {정성 의견}
Q3 (hari-14b-chatml 분리): {정성 의견}
Q4 (64GB 전 최소 검증): {필수 항목 list}

Must-fix (있을 시): {결과 해석을 뒤집는 사항만}
Should-fix: {운영 권고 보강}
Minor: {backlog}
```

---

**문서 끝**

본 packet은 R2/R3과 같은 must-fix only loop가 아닌 **결과 해석 sign-off** 성격. 응답이 GO이면 64GB part 2 진입 준비 단계로, CONDITIONAL GO이면 Q4의 추가 검증부터 수행 후 R4.1.
