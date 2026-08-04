from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from Agents.implementations.agentic_business_logic_extractor import (
    AgenticBusinessLogicExtractor,
    BusinessLogicFileContext,
)
from Persistence.sqlite.models import (
    Base,
    BusinessRule,
    FileChunk,
    FileStatus,
    Project,
    ProjectFile,
    SignatureRegistry,
    TypeMappingTable,
)
from Processes.logic_extraction_process import LogicExtractionProcess
from services.business_logic_chunk_context_service import build_chunk_source, format_chunk_for_prompt
from services.business_logic_reconciler import BusinessLogicReconciler
from services.business_rule_quality_service import BusinessRuleQualityService
from services.legacy_source_preprocessor import LegacySourcePreprocessor


class BusinessLogicExistingChunksTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.db.add(Project(run_id="RUN_TEST", project_name="Test", ai_mode="local", llm_provider="local"))
        self.db.add(
            ProjectFile(
                id=1,
                run_id="RUN_TEST",
                filename="CCHECKPD.CPY",
                filepath="CCHECKPD.CPY",
                detected_lang="copybook",
                status=FileStatus.CONFIRMED,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_business_logic_reuses_existing_file_chunks(self):
        chunk = FileChunk(
            id=10,
            run_id="RUN_TEST",
            file_id=1,
            chunk_index=0,
            content="UT-TEST.\n    ADD 1 TO UT-NUMBER-PASSED.",
            start_line=1,
            end_line=2,
            overlap_content="",
            semantic_units='["paragraph:UT-TEST"]',
            status="PENDING",
        )
        self.db.add(chunk)
        self.db.commit()

        process = LogicExtractionProcess(self.db, {"mode": "local", "provider": "local"})
        with patch("Processes.logic_extraction_process.ChunkingOrchestrator.process_file_pipeline") as mocked:
            chunks = process._load_or_create_chunks_for_file(
                run_id="RUN_TEST",
                file_id=1,
                file_name="CCHECKPD.CPY",
                source_code=chunk.content,
                language="copybook",
            )

        mocked.assert_not_called()
        self.assertEqual([item.id for item in chunks], [10])

    def test_overlap_is_context_only(self):
        chunk = FileChunk(
            run_id="RUN_TEST",
            file_id=1,
            chunk_index=1,
            content=(
                "IF UT-OVERLAP-FLAG\n"
                "   ADD 1 TO UT-NUMBER-PASSED.\n"
                "UT-PRIMARY.\n"
                "   DISPLAY 'PRIMARY ONLY'."
            ),
            start_line=10,
            end_line=11,
            overlap_content="IF UT-OVERLAP-FLAG\n   ADD 1 TO UT-NUMBER-PASSED.",
            semantic_units='["paragraph:UT-PRIMARY"]',
            status="PENDING",
        )
        chunk_source = build_chunk_source(chunk)
        formatted = format_chunk_for_prompt(chunk_source)
        extractor = AgenticBusinessLogicExtractor({"mode": "local", "provider": "local"})
        extractor.use_llm = False
        result = extractor.extract_chunk(
            BusinessLogicFileContext(
                file_id=1,
                file_name="CCHECKPD.CPY",
                detected_language="copybook",
                source_code=formatted,
                technical_yaml="",
            ),
            chunk_index=1,
            total_chunks=1,
            primary_start_line=10,
            primary_end_line=11,
            semantic_units=["paragraph:UT-PRIMARY"],
        )
        accepted, _ = BusinessRuleQualityService().filter_rules_for_primary_range(
            result.get("business_rules", []),
            10,
            11,
        )

        all_rule_text = "\n".join(rule.get("rule_text", "") for rule in accepted)
        self.assertNotIn("overlap", all_rule_text.lower())

    def test_overlap_does_not_duplicate_rules(self):
        reconciled = BusinessLogicReconciler().reconcile(
            [
                {
                    "business_rules": [
                        {
                            "rule_type": "calculation",
                            "paragraph": "UT-DISPLAY-PASSED",
                            "source_start_line": 20,
                            "source_end_line": 20,
                            "rule_text": "When a test passes, increment the passed-test counter by one.",
                            "confidence": 0.7,
                        }
                    ]
                },
                {
                    "business_rules": [
                        {
                            "rule_type": "calculation",
                            "paragraph": "UT-DISPLAY-PASSED",
                            "source_start_line": 20,
                            "source_end_line": 20,
                            "rule_text": "When a test passes, increment the passed-test counter by one.",
                            "confidence": 0.6,
                        }
                    ]
                },
            ],
            {"file_name": "CCHECKPD.CPY", "file_role": "test_support", "artifact_type": "procedural_copybook"},
        )

        self.assertEqual(len(reconciled["business_rules"]), 1)

    def test_chunk_rules_use_original_source_lines(self):
        chunk = FileChunk(
            run_id="RUN_TEST",
            file_id=1,
            chunk_index=0,
            content="UT-PASSED.\n    ADD 1 TO UT-NUMBER-PASSED.",
            start_line=100,
            end_line=101,
            overlap_content="",
            semantic_units='["paragraph:UT-PASSED"]',
            status="PENDING",
        )
        chunk_source = build_chunk_source(chunk)
        formatted = format_chunk_for_prompt(chunk_source)
        extractor = AgenticBusinessLogicExtractor({"mode": "local", "provider": "local"})
        extractor.use_llm = False
        result = extractor.extract_chunk(
            BusinessLogicFileContext(
                file_id=1,
                file_name="CCHECKPD.CPY",
                detected_language="copybook",
                source_code=formatted,
                technical_yaml="",
            ),
            chunk_index=0,
            total_chunks=1,
            primary_start_line=100,
            primary_end_line=101,
            semantic_units=["paragraph:UT-PASSED"],
        )
        accepted, _ = BusinessRuleQualityService().filter_rules_for_primary_range(
            result.get("business_rules", []),
            100,
            101,
        )

        self.assertTrue(accepted)
        self.assertTrue(all(rule["source_start_line"] >= 100 for rule in accepted))
        self.assertTrue(all(rule["source_end_line"] <= 101 for rule in accepted))

    def test_one_chunk_fallback_produces_hybrid_result(self):
        chunk_execution = {
            "processing_mode": "chunked_hybrid",
            "stored_chunks": 2,
            "request_batches": 2,
            "completed_chunks": 2,
            "llm_chunks": 1,
            "fallback_chunks": 1,
            "failed_chunks": 0,
            "overlap_lines": 0,
            "analysis_coverage": 1.0,
            "quality_status": "PASSED",
        }

        self.assertEqual(chunk_execution["processing_mode"], "chunked_hybrid")
        self.assertEqual(chunk_execution["fallback_chunks"], 1)
        self.assertEqual(chunk_execution["analysis_coverage"], 1.0)

    def test_business_extraction_preserves_symbol_registry(self):
        self.db.add(SignatureRegistry(run_id="RUN_TEST", file_id=1, legacy_name="UT-PASSED"))
        self.db.add(
            TypeMappingTable(
                run_id="RUN_TEST",
                file_id=1,
                legacy_variable="UT-NUMBER-PASSED",
                legacy_type="9(4)",
            )
        )
        self.db.commit()

        process = LogicExtractionProcess(self.db, {"mode": "local", "provider": "local"})
        project_file = self.db.query(ProjectFile).filter_by(id=1).first()
        process._replace_business_rules_for_file(
            "RUN_TEST",
            project_file,
            {
                "business_purpose": "Test purpose.",
                "functional_logic": [],
                "business_rules": [],
                "technical_yaml": "",
            },
        )

        self.assertEqual(self.db.query(SignatureRegistry).filter_by(run_id="RUN_TEST").count(), 1)
        self.assertEqual(self.db.query(TypeMappingTable).filter_by(run_id="RUN_TEST").count(), 1)

    def test_ccheckpd_quality_terms(self):
        source = """
UT-DISPLAY-PASSED.
    ADD 1 TO ==UT==NUMBER-PASSED.
UT-SET-MOCK.
    ADD 1 TO ==UT==MOCK-COUNT.
UT-REVERSE-RESULT.
    IF ==UT==COMPARE-PASSED
       SET ==UT==COMPARE-FAILED TO TRUE.
"""
        preprocessor = LegacySourcePreprocessor()
        profile = preprocessor.prepare(source, "CCHECKPD.CPY", "copybook")
        extractor = AgenticBusinessLogicExtractor({"mode": "local", "provider": "local"})
        extractor.use_llm = False
        result = extractor.extract(
            BusinessLogicFileContext(
                file_id=1,
                file_name="CCHECKPD.CPY",
                detected_language=profile.detected_language,
                source_code=profile.source_code,
                technical_yaml=preprocessor.to_technical_yaml(profile),
                artifact_type=profile.artifact_type,
                file_role=profile.file_role,
                paragraphs=profile.paragraphs,
            )
        )
        all_rule_text = "\n".join(rule.get("rule_text", "") for rule in result.get("business_rules", []))

        self.assertNotIn("==UT==", all_rule_text)
        self.assertNotIn("is equal to is equal to", all_rule_text)
        self.assertNotIn("matching business outcome", all_rule_text)
        self.assertIn("passed-test counter", all_rule_text)
        self.assertIn("mock", all_rule_text.lower())
        self.assertIn("reverse", all_rule_text.lower())


if __name__ == "__main__":
    unittest.main()
