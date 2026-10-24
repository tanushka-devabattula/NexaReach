import os
import sys
import traceback

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import Phase 1 test functions
from tests.test_database_migration import (
    test_database_tables_exist,
    test_alembic_head_version,
    test_milestone_1_records_preserved,
)
from tests.test_services import (
    test_ai_generation_offline_fallback,
    test_all_10_languages_supported,
    test_urdu_rtl_and_bidi_isolation,
    test_batch_translation_all_10_languages,
    test_token_extraction_and_rendering,
    test_segment_variants_generation,
    test_readability_calculation,
    test_tone_and_sentiment_analysis,
    test_compliance_rules,
    test_approval_workflow_lifecycle,
    get_test_db,
)

# Import Phase 2 API Router test functions
from tests.test_api_routers import (
    test_api_ai_generate_offline_fallback,
    test_api_ai_history_retrieval,
    test_api_ai_generate_with_mocked_openai,
    test_api_supported_languages,
    test_api_single_translation_urdu_rtl,
    test_api_batch_translation,
    test_api_personalization_preview,
    test_api_segment_variants,
    test_api_segment_variants_not_found,
    test_api_tone_and_readability_analysis,
    test_api_compliance_check_compliant,
    test_api_compliance_check_prohibited_terms,
    test_api_review_lifecycle_submit_and_decide,
    test_api_integrated_workflow_run,
    test_milestone_1_routes_intact,
    test_api_approval_blocked_on_critical_issues,
    test_api_approval_succeeds_on_valid_content,
    test_api_tone_improvement_offline_fallback_and_sms_limit,
    test_api_tone_improvement_mocked_openai,
    test_api_ai_provider_error_retry_and_graceful_fallback,
)


def run_tests():
    phase1_tests = [
        ("Phase 1 - Database: All 15 application tables exist", test_database_tables_exist, False),
        ("Phase 1 - Database: Alembic head version is 0e500f4ad1da", test_alembic_head_version, False),
        ("Phase 1 - Database: Milestone 1 records preserved", test_milestone_1_records_preserved, False),
        ("Phase 1 - AI Service: Offline fallback & history recording", test_ai_generation_offline_fallback, True),
        ("Phase 1 - Translation: All 10 Indian languages supported", test_all_10_languages_supported, False),
        ("Phase 1 - Translation: Urdu RTL and bidi isolation", test_urdu_rtl_and_bidi_isolation, True),
        ("Phase 1 - Translation: Batch translation across all 10 languages", test_batch_translation_all_10_languages, True),
        ("Phase 1 - Personalization: Token extraction and fallback rendering", test_token_extraction_and_rendering, False),
        ("Phase 1 - Personalization: Segment variant generation", test_segment_variants_generation, True),
        ("Phase 1 - Analysis: Readability calculations (Flesch & FKGL)", test_readability_calculation, False),
        ("Phase 1 - Analysis: Tone and sentiment classification", test_tone_and_sentiment_analysis, False),
        ("Phase 1 - Compliance: Channel limits, sensitive words, and disclaimers", test_compliance_rules, False),
        ("Phase 1 - Compliance: Review and approval lifecycle", test_approval_workflow_lifecycle, True),
    ]

    phase2_tests = [
        ("Phase 2 - Router POST /ai/generate (Offline fallback & DB write)", test_api_ai_generate_offline_fallback, False),
        ("Phase 2 - Router GET /ai/history (DB read verification)", test_api_ai_history_retrieval, False),
        ("Phase 2 - Router POST /ai/generate (Mocked external OpenAI provider)", test_api_ai_generate_with_mocked_openai, False),
        ("Phase 2 - Router GET /translate/languages (10 Indian languages & Urdu RTL)", test_api_supported_languages, False),
        ("Phase 2 - Router POST /translate (Urdu RTL & Unicode bidi isolation)", test_api_single_translation_urdu_rtl, False),
        ("Phase 2 - Router POST /translate/batch (Multilingual batch translation)", test_api_batch_translation, False),
        ("Phase 2 - Router POST /personalize/preview (Live audience member token injection)", test_api_personalization_preview, False),
        ("Phase 2 - Router POST /personalize/variants (Cohort personalization)", test_api_segment_variants, False),
        ("Phase 2 - Router POST /personalize/variants (404 on missing segment)", test_api_segment_variants_not_found, False),
        ("Phase 2 - Router POST /analysis/tone-readability (Clarity and tone scores)", test_api_tone_and_readability_analysis, False),
        ("Phase 2 - Router POST /review/compliance-check (Compliant message pass)", test_api_compliance_check_compliant, False),
        ("Phase 2 - Router POST /review/compliance-check (Prohibited words fail)", test_api_compliance_check_prohibited_terms, False),
        ("Phase 2 - Router /review lifecycle (Submit -> DB Write -> DB Read -> Decision)", test_api_review_lifecycle_submit_and_decide, False),
        ("Phase 2 - Router POST /workflow/run (End-to-End Pipeline execution)", test_api_integrated_workflow_run, False),
        ("Phase 2 - Regression: Milestone 1 API routes intact", test_milestone_1_routes_intact, False),
        ("Priority 1 Fix - Compliance: Approval strictly blocked on critical issues", test_api_approval_blocked_on_critical_issues, False),
        ("Priority 1 Fix - Compliance: Approval succeeds on compliant content", test_api_approval_succeeds_on_valid_content, False),
        ("Priority 1 Fix - Tone: POST /ai/improve-tone offline fallback & SMS cap <= 160", test_api_tone_improvement_offline_fallback_and_sms_limit, False),
        ("Priority 1 Fix - Tone: POST /ai/improve-tone mocked AI rewrite", test_api_tone_improvement_mocked_openai, False),
        ("Priority 1 Fix - Resilience: AI provider timeout/retry & graceful fallback", test_api_ai_provider_error_retry_and_graceful_fallback, False),
    ]

    all_tests = phase1_tests + phase2_tests
    passed = 0
    failed = 0

    print("=" * 75)
    print("RUNNING NEXAREACH TEST SUITE (PHASE 1 CORE + PHASE 2 FASTAPI ROUTERS)")
    print("=" * 75)

    for name, func, needs_db in all_tests:
        try:
            if needs_db:
                session_gen = get_test_db()
                session = next(session_gen)
                try:
                    func(session)
                finally:
                    try:
                        next(session_gen)
                    except StopIteration:
                        pass
            else:
                func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    print("=" * 75)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED out of {len(all_tests)} tests.")
    print("=" * 75)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
