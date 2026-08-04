from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class RuleQualityDecision:
    accepted: bool
    rule: dict[str, Any] | None = None
    reason: str = ""


class BusinessRuleQualityService:
    REJECT_PATTERNS = [
        re.compile(r"is equal to\s+is equal to", re.IGNORECASE),
        re.compile(r"\bif\s+true\b", re.IGNORECASE),
        re.compile(r"matching business outcome", re.IGNORECASE),
        re.compile(r"specified business amount", re.IGNORECASE),
        re.compile(r"required business message", re.IGNORECASE),
        re.compile(r"==[A-Z0-9-]+==", re.IGNORECASE),
        re.compile(r"\.\.", re.IGNORECASE),
    ]

    REQUIRED_RULE_TYPES = {
        "validation",
        "calculation",
        "decision",
        "data_rule",
        "transaction",
        "workflow",
        "state_transition",
        "external_dependency",
        "other",
    }

    def evaluate(self, rule: dict[str, Any]) -> RuleQualityDecision:
        text = self._rule_text(rule)
        if not text:
            return RuleQualityDecision(False, reason="missing_rule_text")

        for pattern in self.REJECT_PATTERNS:
            if pattern.search(text):
                return RuleQualityDecision(False, reason=f"rejected_pattern:{pattern.pattern}")

        normalized = dict(rule)
        normalized["rule_text"] = self._clean_text(text)
        normalized["rule_type"] = self._normalize_rule_type(normalized.get("rule_type"))
        normalized["confidence"] = self._normalize_confidence(normalized.get("confidence"))
        normalized["derivation"] = normalized.get("derivation") or "llm"
        normalized["evidence_status"] = normalized.get("evidence_status") or (
            "verified" if self._has_source_evidence(normalized) else "unresolved"
        )

        if normalized["evidence_status"] != "verified":
            normalized["confidence"] = min(float(normalized["confidence"]), 0.55)
        if normalized["rule_type"] == "other":
            normalized["confidence"] = min(float(normalized["confidence"]), 0.6)

        return RuleQualityDecision(True, normalized)

    def filter_rules(self, rules: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, str]] = []

        for item in rules or []:
            if not isinstance(item, dict):
                rejected.append({"reason": "not_a_rule_object", "rule_text": str(item or "")})
                continue
            decision = self.evaluate(item)
            if decision.accepted and decision.rule:
                accepted.append(decision.rule)
            else:
                rejected.append({"reason": decision.reason, "rule_text": self._rule_text(item)})

        return accepted, rejected

    def filter_rules_for_primary_range(
        self,
        rules: list[Any],
        primary_start_line: int,
        primary_end_line: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        accepted, rejected = self.filter_rules(rules)
        range_accepted: list[dict[str, Any]] = []

        for rule in accepted:
            if not self.validate_rule_source_range(rule, primary_start_line, primary_end_line):
                rejected.append(
                    {
                        "reason": "source_range_outside_primary",
                        "rule_text": self._rule_text(rule),
                    }
                )
                continue
            if not self._has_business_outcome(rule):
                rejected.append(
                    {
                        "reason": "missing_business_outcome",
                        "rule_text": self._rule_text(rule),
                    }
                )
                continue
            range_accepted.append(rule)

        return range_accepted, rejected

    @staticmethod
    def validate_rule_source_range(
        rule: dict[str, Any],
        primary_start_line: int,
        primary_end_line: int,
    ) -> bool:
        start = rule.get("source_start_line")
        end = rule.get("source_end_line", start)

        if isinstance(start, str) and start.isdigit():
            start = int(start)
            rule["source_start_line"] = start
        if isinstance(end, str) and end.isdigit():
            end = int(end)
            rule["source_end_line"] = end

        if not isinstance(start, int) or not isinstance(end, int):
            return False

        return (
            primary_start_line <= start <= primary_end_line
            and primary_start_line <= end <= primary_end_line
            and start <= end
        )

    def _rule_text(self, rule: dict[str, Any]) -> str:
        return str(
            rule.get("rule_text")
            or rule.get("description")
            or rule.get("business_meaning")
            or rule.get("calculation_text")
            or ""
        ).strip()

    def _has_business_outcome(self, rule: dict[str, Any]) -> bool:
        text = self._rule_text(rule)
        explicit_outcome = str(
            rule.get("business_outcome")
            or rule.get("outcome")
            or rule.get("rule_text")
            or ""
        ).strip()
        if not explicit_outcome:
            return False
        if re.search(r"\b(apply the branch outcome|apply the verified outcome)\b", text, re.IGNORECASE):
            return False
        return True

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"==\s*([A-Z0-9-]+)\s*==(?=[A-Z0-9-])", r"\1-", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+\.", ".", text)
        return text.strip()

    def _normalize_rule_type(self, value: Any) -> str:
        normalized = str(value or "other").lower().strip()
        mapping = {
            "business_decision": "decision",
            "data_access": "data_rule",
            "external_service": "external_dependency",
        }
        normalized = mapping.get(normalized, normalized)
        return normalized if normalized in self.REQUIRED_RULE_TYPES else "other"

    @staticmethod
    def _normalize_confidence(value: Any) -> float:
        if isinstance(value, (int, float)):
            return max(0.0, min(1.0, float(value)))
        mapping = {"high": 0.9, "medium": 0.7, "low": 0.45}
        return mapping.get(str(value or "").lower().strip(), 0.7)

    @staticmethod
    def _has_source_evidence(rule: dict[str, Any]) -> bool:
        return bool(
            rule.get("source_excerpt")
            or rule.get("technical_reference")
            or rule.get("technical_ref")
            or rule.get("paragraph")
        )
