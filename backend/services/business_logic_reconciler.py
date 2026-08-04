from __future__ import annotations

import re
from typing import Any


class BusinessLogicReconciler:
    def reconcile(
        self,
        chunk_results: list[dict[str, Any]],
        file_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        rules: list[dict[str, Any]] = []
        for result in chunk_results:
            for rule in result.get("business_rules", []) or []:
                if isinstance(rule, dict):
                    rules.append(dict(rule))

        rules = self._deduplicate(rules)
        rules.sort(
            key=lambda rule: (
                self._line_or_max(rule.get("source_start_line")),
                self._line_or_max(rule.get("source_end_line")),
                str(rule.get("rule_text") or ""),
            )
        )

        chunk_summaries = [
            str(result.get("chunk_summary") or result.get("business_purpose") or "").strip()
            for result in chunk_results
            if str(result.get("chunk_summary") or result.get("business_purpose") or "").strip()
        ]

        return {
            "business_purpose": self._merge_purpose(chunk_summaries, file_metadata, rules),
            "functional_logic": self._merge_functional_logic(chunk_results, file_metadata),
            "business_rules": rules,
            "chunk_count": len(chunk_results),
        }

    def _deduplicate(self, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
        by_source: dict[tuple[Any, ...], dict[str, Any]] = {}

        for rule in rules:
            key = (
                str(rule.get("rule_type") or "other").lower(),
                str(rule.get("paragraph") or rule.get("semantic_unit") or "").upper(),
                rule.get("source_start_line"),
                rule.get("source_end_line"),
                self._normalize_rule_text(str(rule.get("rule_text") or "")),
            )
            source_key = (
                str(rule.get("paragraph") or rule.get("semantic_unit") or "").upper(),
                rule.get("source_start_line"),
                rule.get("source_end_line"),
            )

            if key in by_key:
                by_key[key] = self._merge_rule(by_key[key], rule)
                continue
            if source_key in by_source:
                merged = self._merge_rule(by_source[source_key], rule)
                by_source[source_key] = merged
                old_key = next((item_key for item_key, item in by_key.items() if item is by_source[source_key]), None)
                if old_key:
                    by_key[old_key] = merged
                else:
                    by_key[key] = merged
                continue

            by_key[key] = rule
            by_source[source_key] = rule

        return list(by_key.values())

    @staticmethod
    def _merge_rule(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = dict(existing)
        existing_confidence = float(existing.get("confidence") or 0)
        incoming_confidence = float(incoming.get("confidence") or 0)
        if incoming_confidence > existing_confidence:
            merged["rule_text"] = incoming.get("rule_text") or existing.get("rule_text")
            merged["confidence"] = incoming_confidence

        refs = [
            str(existing.get("technical_reference") or existing.get("technical_ref") or "").strip(),
            str(incoming.get("technical_reference") or incoming.get("technical_ref") or "").strip(),
        ]
        refs = [ref for ref in refs if ref]
        if refs:
            merged["technical_reference"] = "; ".join(dict.fromkeys(refs))
        return merged

    @staticmethod
    def _merge_purpose(
        chunk_summaries: list[str],
        file_metadata: dict[str, Any],
        rules: list[dict[str, Any]],
    ) -> str:
        file_name = file_metadata.get("file_name") or "this source file"
        role = str(file_metadata.get("file_role") or "legacy component").replace("_", " ")
        artifact = str(file_metadata.get("artifact_type") or "legacy artifact").replace("_", " ")
        paragraphs = file_metadata.get("major_paragraphs") or []
        paragraph_text = ", ".join(paragraphs[:8]) if paragraphs else "the analyzed primary source"

        if rules:
            return (
                f"{file_name} is a {role} {artifact} whose extracted rules are grounded in "
                f"{paragraph_text}. It preserves the observable legacy behavior represented by "
                f"{len(rules)} accepted business-rule candidates."
            )

        if chunk_summaries:
            return f"{file_name} is a {role} {artifact}. {' '.join(chunk_summaries[:3])}"

        return f"{file_name} is a {role} {artifact}. No verified business rules were found in the primary chunk ranges."

    @staticmethod
    def _merge_functional_logic(
        chunk_results: list[dict[str, Any]],
        file_metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        descriptions: list[str] = []
        for result in chunk_results:
            for item in result.get("functional_logic", []) or []:
                if isinstance(item, dict):
                    text = str(item.get("description") or "").strip()
                else:
                    text = str(item or "").strip()
                if text:
                    descriptions.append(text)

        if not descriptions:
            descriptions.append(
                "Business logic was reconciled from stored FileChunk primary source ranges with overlap used only as context."
            )

        return [
            {
                "title": "Reconciled chunk flow",
                "description": " ".join(dict.fromkeys(descriptions[:8])),
                "technical_reference": file_metadata.get("file_name") or "",
                "confidence": 0.7,
            }
        ]

    @staticmethod
    def _normalize_rule_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    @staticmethod
    def _line_or_max(value: Any) -> int:
        return value if isinstance(value, int) else 10**9
