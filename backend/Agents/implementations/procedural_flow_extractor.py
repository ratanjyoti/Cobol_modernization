from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests


PROCEDURAL_FLOW_SCHEMA = """
Return ONLY valid JSON.

Use this exact JSON structure:

{
  "entry_point": {
    "name": "",
    "description": "",
    "technical_reference": ""
  },
  "execution_flow": [
    {
      "step_no": 1,
      "name": "",
      "type": "paragraph|section|job_step|screen_event|function|unknown",
      "description": "",
      "technical_reference": "",
      "calls": []
    }
  ],
  "decision_branches": [
    {
      "condition": "",
      "technical_reference": "",
      "true_path": [],
      "false_path": [],
      "description": ""
    }
  ],
  "loops": [
    {
      "loop_type": "",
      "condition": "",
      "technical_reference": "",
      "repeated_steps": [],
      "exit_condition": ""
    }
  ],
  "data_movement": [
    {
      "variable": "",
      "flow": [],
      "technical_reference": ""
    }
  ],
  "external_operations": [
    {
      "sequence": 1,
      "operation_type": "file_read|file_write|database_select|database_update|database_insert|database_delete|screen_io|other",
      "name": "",
      "description": "",
      "technical_reference": ""
    }
  ],
  "external_calls": [
    {
      "program": "",
      "status": "resolved|unresolved|unknown",
      "description": "",
      "technical_reference": ""
    }
  ],
  "exit_paths": [
    {
      "type": "normal|error|early_return|unknown",
      "steps": [],
      "technical_reference": ""
    }
  ],
  "unresolved_items": [
    {
      "item": "",
      "reason": "",
      "technical_reference": ""
    }
  ]
}
"""


SYSTEM_PROMPT = f"""
You are a legacy program procedural-flow extraction agent.

Your task:
Extract how the program executes step by step.

Focus on:
- program entry point
- paragraph / section / step execution order
- PERFORM / CALL / GO TO flow
- IF / EVALUATE decision paths
- loops and repeated record processing
- data movement through variables
- file/database/screen operation sequence
- external program calls
- normal and error exit paths

Important:
- This is NOT business logic extraction.
- Do not produce user stories.
- Do not explain syntax.
- Use technical YAML as the main evidence.
- Use raw source code only to verify missing details.
- If flow is uncertain, add unresolved_items.
- Return JSON only.

{PROCEDURAL_FLOW_SCHEMA}
"""


USER_PROMPT_TEMPLATE = """
Extract procedural logic flow for this file.

File metadata:
- File ID: {file_id}
- File name: {file_name}
- Detected language: {detected_language}

Technical YAML:
{technical_yaml}

Raw source code:
```text
{source_code}
```

Return only valid JSON using the required schema.
"""


class ProceduralFlowExtractor:
    """
    Compact procedural-flow extractor.

    Owns prompt construction, LLM calls, JSON parsing, deterministic fallback,
    and normalized output for the program-flow process.
    """

    def __init__(self, llm_config: dict[str, Any]):
        self.llm_config = llm_config or {}
        self.timeout = int(self.llm_config.get("timeout") or 180)

    def extract(
        self,
        file_id: int | str,
        file_name: str,
        detected_language: str,
        technical_yaml: str,
        source_code: str,
    ) -> dict[str, Any]:
        try:
            result = self._extract_with_llm(
                file_id=file_id,
                file_name=file_name,
                detected_language=detected_language,
                technical_yaml=technical_yaml,
                source_code=source_code,
            )
            result = self._augment_with_source_signals(
                payload=result,
                file_name=file_name,
                detected_language=detected_language,
                source_code=source_code,
            )
            result["fallback_used"] = False
        except Exception as exc:
            result = self._deterministic_fallback(
                file_id=file_id,
                file_name=file_name,
                detected_language=detected_language,
                technical_yaml=technical_yaml,
                source_code=source_code,
                reason=str(exc),
            )
            result["fallback_used"] = True
            result["fallback_reason"] = str(exc)

        result["file_id"] = file_id
        result["file_name"] = file_name
        result["detected_language"] = detected_language
        return self._normalize(result)

    def _extract_with_llm(
        self,
        file_id: int | str,
        file_name: str,
        detected_language: str,
        technical_yaml: str,
        source_code: str,
    ) -> dict[str, Any]:
        budgets = self._prompt_budgets()
        user_prompt = USER_PROMPT_TEMPLATE.format(
            file_id=file_id,
            file_name=file_name,
            detected_language=detected_language or "unknown",
            technical_yaml=self._trim(technical_yaml, budgets["technical_yaml"]),
            source_code=self._trim(source_code, budgets["source_code"]),
        )

        response = self._call_llm(SYSTEM_PROMPT, user_prompt)
        return self._parse_json(response)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        mode = (
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or self.llm_config.get("llm_provider")
            or "local"
        ).lower()

        base_url = (
            self.llm_config.get("url")
            or self.llm_config.get("base_url")
            or self.llm_config.get("custom_api_base_url")
            or "http://127.0.0.1:11434"
        )

        model = (
            self.llm_config.get("model")
            or self.llm_config.get("llm_model")
            or "llama3"
        )

        api_key = (
            self.llm_config.get("key")
            or self.llm_config.get("api_key")
            or self.llm_config.get("openrouter_api_key")
        )

        if mode in {"openrouter", "api", "cloud", "custom"} or "/v1" in base_url:
            return self._call_openai_compatible(
                base_url=base_url,
                model=model,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        response = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    def _call_openai_compatible(
        self,
        base_url: str,
        model: str,
        api_key: str | None,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
            "response_format": self._json_response_format("procedural_flow_result"),
        }

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code == 400 and str(base_url).rstrip("/").endswith("/v1"):
            payload.pop("response_format", None)
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _prompt_budgets(self) -> dict[str, int]:
        base_url = str(
            self.llm_config.get("url")
            or self.llm_config.get("base_url")
            or self.llm_config.get("custom_api_base_url")
            or ""
        ).lower()
        mode = str(
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or self.llm_config.get("llm_provider")
            or "local"
        ).lower()
        if mode == "local" or "127.0.0.1" in base_url or "localhost" in base_url:
            return {"technical_yaml": 5000, "source_code": 9000}
        return {"technical_yaml": 16000, "source_code": 16000}

    @staticmethod
    def _json_response_format(name: str) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": False,
                "schema": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        }

    def _parse_json(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))

        raise ValueError(f"Invalid procedural flow JSON: {raw[:500]}")

    def _deterministic_fallback(
        self,
        file_id: int | str,
        file_name: str,
        detected_language: str,
        technical_yaml: str,
        source_code: str,
        reason: str,
    ) -> dict[str, Any]:
        paragraphs = self._extract_cobol_paragraphs(source_code)
        performs = self._extract_performs(source_code)
        decisions = self._extract_decisions(source_code)
        loops = self._extract_loops(source_code)
        externals = self._extract_external_operations(source_code)
        calls = self._extract_calls(source_code)
        exits = self._extract_exit_paths(source_code)

        entry_name = paragraphs[0] if paragraphs else self._infer_entry_point(file_name, detected_language)
        execution_flow = [
            {
                "step_no": index,
                "name": paragraph,
                "type": "paragraph",
                "description": f"Executes paragraph {paragraph}.",
                "technical_reference": paragraph,
                "calls": performs.get(paragraph, []),
            }
            for index, paragraph in enumerate(paragraphs[:80], start=1)
        ]

        if not execution_flow:
            execution_flow.append(
                {
                    "step_no": 1,
                    "name": entry_name,
                    "type": "unknown",
                    "description": "Entry flow inferred from file because detailed paragraph flow was unavailable.",
                    "technical_reference": file_name,
                    "calls": [],
                }
            )

        return {
            "file_id": file_id,
            "file_name": file_name,
            "detected_language": detected_language,
            "entry_point": {
                "name": entry_name,
                "description": "Inferred program entry point.",
                "technical_reference": entry_name,
            },
            "execution_flow": execution_flow,
            "decision_branches": decisions,
            "loops": loops,
            "data_movement": self._extract_data_movement(source_code),
            "external_operations": externals,
            "external_calls": calls,
            "exit_paths": exits,
            "unresolved_items": [
                {
                    "item": "LLM procedural flow extraction",
                    "reason": reason,
                    "technical_reference": file_name,
                }
            ],
        }

    def _extract_cobol_paragraphs(self, source_code: str) -> list[str]:
        paragraphs = []
        excluded = {
            "IDENTIFICATION",
            "ENVIRONMENT",
            "DATA",
            "PROCEDURE",
            "DIVISION",
            "SECTION",
            "FILE-CONTROL",
            "INPUT-OUTPUT",
            "WORKING-STORAGE",
            "LOCAL-STORAGE",
            "LINKAGE",
            "END-IF",
            "END-EVALUATE",
            "END-PERFORM",
            "END-CALL",
            "EXIT",
            "CONTINUE",
            "PROGRAM-ID",
        }

        in_procedure = False
        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue

            if re.search(r"\bPROCEDURE\s+DIVISION\b", stripped, re.IGNORECASE):
                in_procedure = True
                continue

            if not in_procedure:
                continue

            match = re.match(
                r"^([A-Z0-9][A-Z0-9-]{1,60})(?:\s+SECTION)?\.?\s*$",
                stripped,
                re.IGNORECASE,
            )
            if match:
                name = match.group(1).upper()
                if name.startswith("END-"):
                    continue
                if self._looks_like_continuation_data_name(name):
                    continue
                if name not in excluded and name not in paragraphs:
                    paragraphs.append(name)

        return paragraphs

    @staticmethod
    def _looks_like_continuation_data_name(name: str) -> bool:
        upper = (name or "").upper()
        return bool(
            re.match(r"^(VALUE|TEMP|OUTPUT|ACTION|BOOK)(?:-\d+|-VALUE)?$", upper)
        )

    def _extract_performs(self, source_code: str) -> dict[str, list[str]]:
        current = ""
        mapping: dict[str, list[str]] = {}

        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            para = re.match(r"^([A-Z0-9][A-Z0-9-]{1,60})\.\s*$", stripped, re.IGNORECASE)
            if para:
                current = para.group(1).upper()
                mapping.setdefault(current, [])
                continue

            for match in re.finditer(r"\bPERFORM\s+([A-Z0-9][A-Z0-9-]+)", stripped, re.IGNORECASE):
                if current:
                    mapping.setdefault(current, []).append(match.group(1).upper())

        return mapping

    def _extract_decisions(self, source_code: str) -> list[dict[str, Any]]:
        decisions = []
        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            if re.match(r"^IF\b", stripped, re.IGNORECASE):
                decisions.append(
                    {
                        "condition": re.sub(r"^\s*IF\s+", "", stripped, flags=re.IGNORECASE),
                        "technical_reference": stripped,
                        "true_path": ["Continue through IF branch"],
                        "false_path": ["ELSE branch or next statement if present"],
                        "description": "Conditional branch detected.",
                    }
                )
            elif re.search(r"\bEVALUATE\b", stripped, re.IGNORECASE):
                decisions.append(
                    {
                        "condition": stripped,
                        "technical_reference": stripped,
                        "true_path": ["Matching WHEN branch"],
                        "false_path": ["Other WHEN branch or WHEN OTHER"],
                        "description": "Multi-branch decision detected.",
                    }
                )
        return decisions[:80]

    def _extract_loops(self, source_code: str) -> list[dict[str, Any]]:
        loops = []
        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            if re.search(r"\bPERFORM\b.*\bUNTIL\b", stripped, re.IGNORECASE):
                loops.append(
                    {
                        "loop_type": "PERFORM UNTIL",
                        "condition": stripped,
                        "technical_reference": stripped,
                        "repeated_steps": ["Repeated paragraph or statement block"],
                        "exit_condition": "UNTIL condition becomes true",
                    }
                )
            elif re.search(r"\bPERFORM\b.*\bVARYING\b", stripped, re.IGNORECASE):
                loops.append(
                    {
                        "loop_type": "PERFORM VARYING",
                        "condition": stripped,
                        "technical_reference": stripped,
                        "repeated_steps": ["Repeated varying loop block"],
                        "exit_condition": "VARYING termination condition",
                    }
                )
        return loops[:50]

    def _extract_data_movement(self, source_code: str) -> list[dict[str, Any]]:
        movements = []
        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            move = re.search(r"\bMOVE\s+(.+?)\s+TO\s+(.+)", stripped, re.IGNORECASE)
            if move:
                movements.append(
                    {
                        "variable": move.group(2).rstrip("."),
                        "flow": [f"Receives value from {move.group(1)}"],
                        "technical_reference": stripped,
                    }
                )

            compute = re.search(r"\bCOMPUTE\s+([A-Z0-9-]+)\s*=", stripped, re.IGNORECASE)
            if compute:
                movements.append(
                    {
                        "variable": compute.group(1).upper(),
                        "flow": ["Computed from expression"],
                        "technical_reference": stripped,
                    }
                )
        return movements[:80]

    def _extract_external_operations(self, source_code: str) -> list[dict[str, Any]]:
        operations = []
        sequence = 1
        patterns = [
            ("file_read", r"\bREAD\s+([A-Z0-9-]+)"),
            ("file_write", r"\bWRITE\s+([A-Z0-9-]+)"),
            ("file_write", r"\bREWRITE\s+([A-Z0-9-]+)"),
            ("file_read", r"\bOPEN\s+(?:INPUT|I-O|EXTEND|OUTPUT)?\s*([A-Z0-9-]+)"),
            ("database_select", r"\bSELECT\b"),
            ("database_update", r"\bUPDATE\b"),
            ("database_insert", r"\bINSERT\b"),
            ("database_delete", r"\bDELETE\b"),
            ("screen_io", r"\b(?:ACCEPT|DISPLAY)\b"),
        ]

        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            upper = stripped.upper()

            for op_type, pattern in patterns:
                name_match = re.search(pattern, upper)
                if name_match:
                    name = name_match.group(1) if name_match.groups() else op_type
                    operations.append(
                        {
                            "sequence": sequence,
                            "operation_type": op_type,
                            "name": name,
                            "description": f"{op_type.replace('_', ' ').title()} operation detected.",
                            "technical_reference": stripped,
                        }
                    )
                    sequence += 1
                    break

        return operations[:100]

    def _extract_calls(self, source_code: str) -> list[dict[str, Any]]:
        calls = []
        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            for match in re.finditer(r"\bCALL\s+['\"]?([A-Z0-9-]+)['\"]?", stripped, re.IGNORECASE):
                calls.append(
                    {
                        "program": match.group(1).upper(),
                        "status": "unknown",
                        "description": "External program call detected.",
                        "technical_reference": stripped,
                    }
                )
        return calls[:50]

    def _extract_exit_paths(self, source_code: str) -> list[dict[str, Any]]:
        exits = []
        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            if re.search(r"\bSTOP\s+RUN\b", stripped, re.IGNORECASE):
                exits.append(
                    {
                        "type": "normal",
                        "steps": ["STOP RUN"],
                        "technical_reference": stripped,
                    }
                )
            elif re.search(r"\bGOBACK\b", stripped, re.IGNORECASE):
                exits.append(
                    {
                        "type": "normal",
                        "steps": ["GOBACK"],
                        "technical_reference": stripped,
                    }
                )

        return exits or [
            {
                "type": "unknown",
                "steps": ["Exit path not clearly identified"],
                "technical_reference": "",
            }
        ]

    def _augment_with_source_signals(
        self,
        payload: dict[str, Any],
        file_name: str,
        detected_language: str,
        source_code: str,
    ) -> dict[str, Any]:
        result = dict(payload or {})
        paragraphs = self._extract_cobol_paragraphs(source_code)
        entry = result.get("entry_point") if isinstance(result.get("entry_point"), dict) else {}
        entry_name = str(entry.get("name") or "").strip()
        if paragraphs and (not entry_name or entry_name.upper().startswith("PROGRAM-ID")):
            result["entry_point"] = {
                "name": paragraphs[0],
                "description": "Program entry inferred from PROCEDURE DIVISION paragraph order.",
                "technical_reference": paragraphs[0],
            }
        elif entry_name.upper().startswith("PROGRAM-ID"):
            result["entry_point"] = {
                "name": "PROCEDURE DIVISION",
                "description": "Program execution begins at the first executable statement in PROCEDURE DIVISION.",
                "technical_reference": "PROCEDURE DIVISION",
            }
        elif not entry_name:
            result["entry_point"] = {
                "name": self._infer_entry_point(file_name, detected_language),
                "description": "Entry point inferred from file metadata.",
                "technical_reference": file_name,
            }

        result["external_operations"] = self._remove_call_misclassified_as_operation(
            result.get("external_operations")
        )

        if not result.get("execution_flow") and paragraphs:
            performs = self._extract_performs(source_code)
            result["execution_flow"] = [
                {
                    "step_no": index,
                    "name": paragraph,
                    "type": "paragraph",
                    "description": f"Executes paragraph {paragraph}.",
                    "technical_reference": paragraph,
                    "calls": performs.get(paragraph, []),
                }
                for index, paragraph in enumerate(paragraphs[:80], start=1)
            ]

        self._merge_missing_items(result, "decision_branches", self._extract_decisions(source_code))
        self._merge_missing_items(result, "loops", self._extract_loops(source_code))
        self._merge_missing_items(result, "data_movement", self._extract_data_movement(source_code))
        self._merge_missing_items(result, "external_operations", self._extract_external_operations(source_code))
        self._merge_missing_items(result, "external_calls", self._extract_calls(source_code))

        exits = result.get("exit_paths")
        if not isinstance(exits, list) or not exits:
            result["exit_paths"] = self._extract_exit_paths(source_code)

        return result

    def _merge_missing_items(
        self,
        payload: dict[str, Any],
        key: str,
        deterministic_items: list[dict[str, Any]],
    ) -> None:
        existing = payload.get(key)
        if not isinstance(existing, list):
            existing = []

        if key == "external_operations":
            for item in existing:
                if isinstance(item, dict):
                    item["operation_type"] = self._canonical_operation_type(item)

        seen = {self._merge_marker(key, item) for item in existing if isinstance(item, dict)}
        existing_operation_types = {
            str(item.get("operation_type") or "").lower()
            for item in existing
            if isinstance(item, dict)
        }

        for item in deterministic_items:
            if key == "external_operations":
                item["operation_type"] = self._canonical_operation_type(item)
                op_type = str(item.get("operation_type") or "").lower()
                if op_type.startswith("database_") and op_type in existing_operation_types:
                    continue

            marker = self._merge_marker(key, item)
            if marker and marker not in seen:
                existing.append(item)
                seen.add(marker)
                if key == "external_operations":
                    existing_operation_types.add(str(item.get("operation_type") or "").lower())

        payload[key] = existing

    def _merge_marker(self, key: str, item: dict[str, Any]) -> str:
        if key == "external_calls":
            return str(item.get("program") or item).strip().upper()
        if key == "external_operations":
            op_type = self._canonical_operation_type(item)
            if op_type.startswith("database_"):
                return op_type
        return str(
            item.get("technical_reference")
            or item.get("condition")
            or item.get("name")
            or item.get("variable")
            or item.get("loop_type")
            or item
        ).strip().lower()

    def _remove_call_misclassified_as_operation(self, value: Any) -> list[dict[str, Any]]:
        cleaned = []
        for item in self._as_list(value):
            if not isinstance(item, dict):
                continue
            op_type = self._canonical_operation_type(item)
            text = " ".join(
                str(item.get(field) or "")
                for field in ("name", "description", "technical_reference")
            ).lower()
            if "external call" in text or re.search(r"\bcall\b", text):
                continue
            item["operation_type"] = op_type
            cleaned.append(item)
        return cleaned

    def _canonical_operation_type(self, item: dict[str, Any]) -> str:
        op_type = str(item.get("operation_type") or "other").lower()
        text = " ".join(
            str(item.get(field) or "")
            for field in ("name", "description", "technical_reference")
        ).lower()

        if "select" in op_type or "query" in op_type or "select" in text or "query" in text:
            return "database_select"
        if "update" in op_type or "update" in text:
            return "database_update"
        if "insert" in op_type or "insert" in text:
            return "database_insert"
        if "delete" in op_type or "delete" in text:
            return "database_delete"

        return op_type

    def _infer_entry_point(self, file_name: str, detected_language: str) -> str:
        lang = str(detected_language or "").lower()
        if lang == "jcl":
            return "JOB"
        if lang == "telon":
            return "SCREEN_OR_EVENT_ENTRY"
        return Path(file_name or "program").stem.upper()

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "file_id": payload.get("file_id"),
            "file_name": payload.get("file_name", ""),
            "detected_language": payload.get("detected_language", ""),
            "entry_point": self._entry_point(payload.get("entry_point")),
            "execution_flow": self._steps(payload.get("execution_flow")),
            "decision_branches": self._dedupe_dicts(self._nonempty_dicts(payload.get("decision_branches")), "condition"),
            "loops": self._nonempty_dicts(payload.get("loops")),
            "data_movement": self._dedupe_dicts(self._nonempty_dicts(payload.get("data_movement")), "technical_reference"),
            "external_operations": self._operations(payload.get("external_operations")),
            "external_calls": self._dedupe_dicts(self._nonempty_dicts(payload.get("external_calls")), "program"),
            "exit_paths": self._nonempty_dicts(payload.get("exit_paths")),
            "unresolved_items": self._nonempty_dicts(payload.get("unresolved_items")),
            "fallback_used": bool(payload.get("fallback_used", False)),
            "fallback_reason": payload.get("fallback_reason", ""),
        }

    def _entry_point(self, value: Any) -> dict[str, Any]:
        entry = value if isinstance(value, dict) else {}
        return {
            "name": str(entry.get("name") or ""),
            "description": str(entry.get("description") or ""),
            "technical_reference": str(entry.get("technical_reference") or ""),
        }

    def _steps(self, value: Any) -> list[dict[str, Any]]:
        steps = []
        for index, item in enumerate(self._as_list(value), start=1):
            if not isinstance(item, dict):
                continue
            steps.append(
                {
                    "step_no": int(item.get("step_no") or index),
                    "name": str(item.get("name") or f"Step {index}"),
                    "type": self._normalize_step_type(item.get("type")),
                    "description": str(item.get("description") or ""),
                    "technical_reference": str(item.get("technical_reference") or ""),
                    "calls": self._as_list(item.get("calls")),
                }
            )
        return steps

    def _normalize_step_type(self, value: Any) -> str:
        raw = str(value or "unknown").strip().lower().replace(" ", "_")
        allowed = {"paragraph", "section", "job_step", "screen_event", "function", "unknown"}
        if raw in allowed:
            return raw
        if "screen" in raw:
            return "screen_event"
        if "job" in raw or "sql" in raw or "database" in raw or "file" in raw:
            return "job_step"
        if "paragraph" in raw or "conditional" in raw or "comput" in raw or "function" in raw or "sequence" in raw:
            return "function"
        if "section" in raw:
            return "section"
        return "unknown"

    def _operations(self, value: Any) -> list[dict[str, Any]]:
        operations = []
        allowed = {
            "file_read",
            "file_write",
            "database_select",
            "database_update",
            "database_insert",
            "database_delete",
            "screen_io",
            "other",
        }
        for index, item in enumerate(self._as_list(value), start=1):
            if not isinstance(item, dict):
                continue
            op_type = self._canonical_operation_type(item)
            if op_type not in allowed:
                op_type = "other"
            operations.append(
                {
                    "sequence": int(item.get("sequence") or index),
                    "operation_type": op_type,
                    "name": str(item.get("name") or ""),
                    "description": str(item.get("description") or ""),
                    "technical_reference": str(item.get("technical_reference") or ""),
                }
            )
        return operations

    def _nonempty_dicts(self, value: Any) -> list[dict[str, Any]]:
        items = []
        for item in self._as_list(value):
            if not isinstance(item, dict):
                continue
            if any(str(value or "").strip() for value in item.values()):
                items.append(item)
        return items

    def _dedupe_dicts(self, items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        result = []
        seen = set()
        for item in items:
            marker = str(item.get(key) or item.get("technical_reference") or item).strip().lower()
            if marker in seen:
                continue
            seen.add(marker)
            result.append(item)
        return result

    def _as_list(self, value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if value in (None, ""):
            return []
        return [value]

    def _trim(self, value: str, limit: int) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        return text[:limit] + "\n...[trimmed]..."
