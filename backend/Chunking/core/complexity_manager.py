from Chunking.core.complexity.cobol_scorer import CobolComplexityScorer
from Chunking.core.complexity.jcl_scorer import JclComplexityScorer
from Chunking.core.complexity.telon_scorer import TelonComplexityScorer

class ComplexityManager:
    def __init__(self):
        self.scorers = {
            "COBOL": CobolComplexityScorer(),
            "JCL": JclComplexityScorer(),
            "TELON": TelonComplexityScorer()
        }

    def score_file(self, content: str, lang: str) -> dict:
        scorer = self.scorers.get(self._language_key(lang))
        if scorer is None:
            tier, mode, multiplier = self.scorers["COBOL"].get_tier_and_mode(0)
            return {
                "score": 0,
                "tier": tier,
                "mode": mode,
                "multiplier": multiplier,
                "calculation": [],
            }

        return scorer.analyze(content)

    def _language_key(self, lang: str) -> str:
        normalized_lang = (lang or "").strip().lower()
        if normalized_lang.startswith("cobol"):
            return "COBOL"
        if normalized_lang == "jcl" or normalized_lang.endswith("-jcl"):
            return "JCL"
        if normalized_lang in {"telon", "tln", "tel"} or normalized_lang.startswith("telon"):
            return "TELON"
        return "UNKNOWN"
