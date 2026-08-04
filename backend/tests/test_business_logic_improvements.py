from __future__ import annotations

import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.business_rule_quality_service import BusinessRuleQualityService
from services.legacy_source_preprocessor import LegacySourcePreprocessor


class LegacySourcePreprocessorTests(unittest.TestCase):
    def test_normalizes_copy_replacing_pseudo_text_without_destroying_equals(self):
        source = "IF ==UT==COMPARE-88-LEVEL = 'Y'"

        profile = LegacySourcePreprocessor().prepare(
            source,
            file_name="CCHECKPD.CPY",
            detected_language="copybook",
        )

        self.assertIn("UT-COMPARE-88-LEVEL = 'Y'", profile.source_code)
        self.assertNotIn("==UT==", profile.source_code)
        self.assertEqual(profile.line_map[0].original_text, source)
        self.assertEqual(profile.artifact_type, "procedural_copybook")
        self.assertEqual(profile.file_role, "test_support")

    def test_assembles_multiline_cobol_statement(self):
        source = """
UT-ASSERT-ACCESSES.
    IF ==UT==ACTUAL-ACCESSES IS GREATER THAN OR EQUAL TO
       ==UT==EXPECTED-ACCESSES
       ADD 1 TO ==UT==NUMBER-PASSED.
"""

        profile = LegacySourcePreprocessor().prepare(
            source,
            file_name="CCHECKPD.CPY",
            detected_language="copybook",
        )
        all_statements = [statement.text for paragraph in profile.paragraphs for statement in paragraph.statements]

        self.assertTrue(
            any(
                "UT-ACTUAL-ACCESSES IS GREATER THAN OR EQUAL TO UT-EXPECTED-ACCESSES" in statement
                for statement in all_statements
            )
        )


class BusinessRuleQualityServiceTests(unittest.TestCase):
    def test_rejects_low_quality_templates(self):
        service = BusinessRuleQualityService()
        accepted, rejected = service.filter_rules(
            [
                {"rule_text": "If true, the matching business outcome must be applied.", "rule_type": "decision"},
                {
                    "rule_text": "When a test passes, increment the passed-test counter by one.",
                    "rule_type": "calculation",
                    "technical_reference": "UT-DISPLAY-PASSED lines 10-12",
                },
            ]
        )

        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(rejected), 1)
        self.assertIn("passed-test counter", accepted[0]["rule_text"])


if __name__ == "__main__":
    unittest.main()
