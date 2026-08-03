from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from Agents.prompts.code_conversion_agentic_prompts import (
    SYSTEM_PROMPTS,
    USER_PROMPT_TEMPLATE,
)


class AgenticCodeConversionOrchestrator:
    """
    Owns target-language code conversion routing.

    Chooses Java/Python/C#/Generic conversion behavior from the requested
    target language, calls the configured LLM, parses generated-file JSON,
    normalizes files, and falls back deterministically when needed.
    """

    def __init__(self, llm_config: dict[str, Any]):
        self.llm_config = llm_config or {}

    def convert(self, context: dict[str, Any]) -> dict[str, Any]:
        target_language = self._normalize_target_language(context.get("target_language"))
        agent_key = self._select_agent(target_language)

        try:
            result = self._convert_with_agent(context=context, agent_key=agent_key)
            result["agent_key"] = agent_key
            result["agent_name"] = self._agent_name(agent_key)
            result["fallback_used"] = False
            normalized = self._normalize_result(result, context, agent_key)
            self._assert_semantic_completeness(normalized, context)
            return normalized
        except Exception as exc:
            fallback = self._deterministic_fallback(
                context=context,
                agent_key=agent_key,
                reason=str(exc),
            )
            fallback["agent_key"] = "generic"
            fallback["agent_name"] = self._agent_name("generic")
            fallback["fallback_used"] = True
            fallback["fallback_reason"] = str(exc)
            return self._normalize_result(fallback, context, "generic")

    def _convert_with_agent(self, context: dict[str, Any], agent_key: str) -> dict[str, Any]:
        system_prompt = SYSTEM_PROMPTS.get(agent_key) or SYSTEM_PROMPTS["generic"]
        budgets = self._prompt_budgets()
        user_prompt = USER_PROMPT_TEMPLATE.format(
            target_language=context.get("target_language", ""),
            target_framework=context.get("target_framework", ""),
            agent_key=agent_key,
            file_id=context.get("file_id", ""),
            file_name=context.get("file_name", ""),
            source_language=context.get("source_language", ""),
            conversion_plan=self._trim_json(context.get("conversion_plan"), budgets["conversion_plan"]),
            technical_yaml=self._trim(context.get("technical_yaml"), budgets["technical_yaml"]),
            business_rules_json=self._trim_json(context.get("business_rules"), budgets["business_rules"]),
            procedural_flow_json=self._trim_json(context.get("procedural_flow"), budgets["procedural_flow"]),
            dependencies_json=self._trim_json(context.get("dependencies"), budgets["dependencies"]),
            locked_symbols_json=self._trim_json(context.get("locked_symbols"), budgets["locked_symbols"]),
            source_code=self._trim(context.get("source_code"), budgets["source_code"]),
        )

        response = self._call_llm(system_prompt, user_prompt)
        return self._parse_json(response)

    def _select_agent(self, target_language: str) -> str:
        target = self._normalize_target_language(target_language)
        if target in {"java", "python", "csharp"}:
            return target
        return "generic"

    def _agent_name(self, agent_key: str) -> str:
        names = {
            "java": "JavaConversionAgent",
            "python": "PythonConversionAgent",
            "csharp": "CSharpConversionAgent",
            "generic": "GenericConversionAgent",
        }
        return names.get(agent_key, "GenericConversionAgent")

    def _normalize_target_language(self, value: Any) -> str:
        text = str(value or "").lower().strip()
        if text in {"python", "py", "fastapi"}:
            return "python"
        if text in {"csharp", "c#", "cs", "dotnet", "aspnet", "asp.net", ".net"}:
            return "csharp"
        if text in {"java", "quarkus"}:
            return "java"
        return text or "java"

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
        local_like = mode == "local" or any(host in str(base_url).lower() for host in ("127.0.0.1", "localhost", ":1234", ":11434"))
        timeout = int(
            self.llm_config.get("timeout")
            or (90 if local_like else 180)
        )

        if mode in {"openrouter", "api", "cloud", "custom", "local"} and "/v1" in base_url:
            return self._call_openai_compatible(
                base_url=base_url,
                model=model,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout=timeout,
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
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    def _call_openai_compatible(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        system_prompt: str,
        user_prompt: str,
        timeout: int,
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
            "response_format": self._json_response_format("code_conversion_result"),
        }

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code == 400:
            payload.pop("response_format", None)
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
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
            return {
                "conversion_plan": 2400,
                "technical_yaml": 3200,
                "business_rules": 2200,
                "procedural_flow": 2600,
                "dependencies": 1200,
                "locked_symbols": 1400,
                "source_code": 7000,
            }

        return {
            "conversion_plan": 9000,
            "technical_yaml": 12000,
            "business_rules": 8000,
            "procedural_flow": 7000,
            "dependencies": 5000,
            "locked_symbols": 6000,
            "source_code": 16000,
        }

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

        raise ValueError(f"Invalid code conversion JSON: {raw[:500]}")

    def _normalize_result(
        self,
        payload: dict[str, Any],
        context: dict[str, Any],
        agent_key: str,
    ) -> dict[str, Any]:
        files = payload.get("files") if isinstance(payload, dict) else []
        if not isinstance(files, list):
            files = []

        normalized_files = []
        for item in files:
            if not isinstance(item, dict):
                continue

            file_path = str(item.get("file_path") or item.get("path") or "").strip()
            content = self._normalize_generated_content(
                str(item.get("content") or "").strip(),
                self._normalize_target_language(item.get("language") or context.get("target_language")),
            )
            if not file_path or not content:
                continue

            normalized_files.append(
                {
                    "file_path": file_path.replace("\\", "/"),
                    "file_type": self._normalize_file_type(item.get("file_type")),
                    "language": self._normalize_target_language(
                        item.get("language") or context.get("target_language")
                    ),
                    "content": self._strip_code_fences(content),
                    "description": str(item.get("description") or ""),
                    "source_references": self._as_list(item.get("source_references")),
                }
            )

        return {
            "target_language": self._normalize_target_language(context.get("target_language")),
            "target_framework": context.get("target_framework", ""),
            "agent_key": payload.get("agent_key", agent_key),
            "agent_name": payload.get("agent_name", self._agent_name(agent_key)),
            "fallback_used": bool(payload.get("fallback_used", False)),
            "fallback_reason": payload.get("fallback_reason", ""),
            "files": normalized_files,
            "summary": str(payload.get("summary") or ""),
            "warnings": self._as_list(payload.get("warnings")),
            "unresolved_items": self._as_list(payload.get("unresolved_items")),
        }

    def _normalize_file_type(self, value: Any) -> str:
        text = str(value or "other").lower().strip()
        aliases = {
            "resource": "controller",
            "router": "controller",
            "domain": "model",
            "entity": "model",
            "schema": "dto",
            "adapter": "other",
        }
        text = aliases.get(text, text)
        allowed = {"model", "service", "controller", "repository", "dto", "config", "test", "other"}
        return text if text in allowed else "other"

    @staticmethod
    def _normalize_generated_content(content: str, target_language: str) -> str:
        if not content:
            return ""

        target = (target_language or "").lower().strip()
        if target == "java":
            content = re.sub(r"\bexecuteBusinessRule\s*\(", "execute(", content)
        elif target == "csharp":
            content = re.sub(r"\bExecuteBusinessRule\s*\(", "Execute(", content)
        elif target == "python":
            content = re.sub(r"\bexecute_business_rule\s*\(", "execute(", content)
        return content

    def _assert_semantic_completeness(self, result: dict[str, Any], context: dict[str, Any]) -> None:
        content = "\n".join(
            str(item.get("content") or "")
            for item in result.get("files") or []
            if isinstance(item, dict)
        )
        source = str(context.get("source_code") or "")
        source_upper = source.upper()
        content_upper = content.upper()
        missing: list[str] = []

        for literal in self._quoted_literals(source):
            if literal.upper() not in content_upper:
                missing.append(f"literal:{literal}")

        for program in self._called_programs(source):
            if program.upper() not in content_upper:
                missing.append(f"call:{program}")

        if "MOVE TEMP TO" in source_upper and "TEMP" not in content_upper:
            missing.append("temp-swap")

        if "EVALUATE " in source_upper and "SWITCH" not in content_upper and "IF " not in content_upper:
            missing.append("decision-logic")

        if missing:
            sample = ", ".join(missing[:8])
            raise ValueError(f"LLM conversion missed source behavior: {sample}")

    @staticmethod
    def _quoted_literals(source: str) -> list[str]:
        ignored = {"initial"}
        literals = re.findall(r"['\"]([^'\"]{1,80})['\"]", source or "")
        return [
            literal.strip()
            for literal in literals
            if literal.strip() and literal.strip().lower() not in ignored
        ]

    @staticmethod
    def _called_programs(source: str) -> list[str]:
        programs = re.findall(r"\bCALL\s+['\"]([^'\"]+)['\"]", source or "", flags=re.IGNORECASE)
        return [program.strip() for program in programs if program.strip()]

    def _deterministic_fallback(
        self,
        context: dict[str, Any],
        agent_key: str,
        reason: str,
    ) -> dict[str, Any]:
        target = self._normalize_target_language(context.get("target_language"))
        file_name = str(context.get("file_name") or "LegacyProgram")
        class_name = self._class_name_from_file(file_name)
        module_name = self._snake_name(Path(file_name).stem)

        if target == "python":
            return {
                "files": [
                    {
                        "file_path": f"generated_app/services/{module_name}_service.py",
                        "file_type": "service",
                        "language": "python",
                        "content": self._fallback_python(module_name),
                        "description": "Deterministic fallback Python service.",
                        "source_references": [file_name],
                    }
                ],
                "summary": "Generated deterministic fallback Python service.",
                "warnings": [reason],
                "unresolved_items": [],
            }

        if target == "csharp":
            return {
                "files": [
                    {
                        "file_path": f"Services/{class_name}Service.cs",
                        "file_type": "service",
                        "language": "csharp",
                        "content": self._fallback_csharp(class_name),
                        "description": "Deterministic fallback C# service.",
                        "source_references": [file_name],
                    }
                ],
                "summary": "Generated deterministic fallback C# service.",
                "warnings": [reason],
                "unresolved_items": [],
            }

        return {
            "files": [
                    {
                        "file_path": f"src/main/java/com/modernizer/migration/services/{class_name}Service.java",
                        "file_type": "service",
                        "language": "java",
                        "content": self._fallback_java(class_name, context),
                        "description": "Deterministic fallback Java service.",
                        "source_references": [file_name],
                    }
            ],
            "summary": "Generated deterministic fallback Java service.",
            "warnings": [reason],
            "unresolved_items": [],
        }

    def _fallback_java(self, class_name: str, context: dict[str, Any]) -> str:
        source_code = str(context.get("source_code") or "")
        fields = self._extract_cobol_fields(source_code)
        paragraphs = self._extract_cobol_paragraph_blocks(source_code)
        start_body = paragraphs.get("000-START") or next(iter(paragraphs.values()), [])

        field_lines = []
        for source_name, target_name, initial_value in fields:
            field_lines.append(f'    private String {target_name} = "{self._java_escape(initial_value)}";')

        if not field_lines:
            field_lines.append("    private String lastValue = \"\";")

        methods = []
        method_index = {name: self._java_method_name(name) for name in paragraphs}

        execute_calls = []
        if "000-START" in paragraphs:
            execute_calls.append(f"        {method_index['000-START']}();")
        else:
            for line in start_body:
                perform = re.search(r"\bPERFORM\s+([A-Z0-9][A-Z0-9-]+)", line, re.IGNORECASE)
                if perform:
                    paragraph = perform.group(1).upper()
                    execute_calls.append(f"        {method_index.get(paragraph, self._java_method_name(paragraph))}();")

        if not execute_calls:
            flow = context.get("procedural_flow") or {}
            for step in flow.get("execution_flow") or []:
                paragraph = str(step.get("name") or "").upper()
                if paragraph == "000-START":
                    continue
                if paragraph in method_index:
                    execute_calls.append(f"        {method_index[paragraph]}();")

        if not execute_calls:
            execute_calls.extend(self._java_lines_from_cobol(start_body, method_index))

        if not execute_calls:
            execute_calls.append('        this.lastOperation = "Executed legacy program.";')

        for paragraph, body_lines in paragraphs.items():
            method_name = method_index[paragraph]
            converted = self._java_lines_from_cobol(body_lines, method_index)
            if not converted:
                converted = ['        this.lastOperation = "No operation";']
            methods.append(
                "\n".join([
                    f"    private void {method_name}() {{",
                    *converted,
                    "    }",
                ])
            )

        if "000-START" in paragraphs:
            methods.insert(
                0,
                "\n".join([
                    "    private void start() {",
                    *execute_calls,
                    "    }",
                ]),
            )
            execute_body = ["        start();"]
        else:
            execute_body = execute_calls

        if fields:
            snapshot_args = ", ".join(f"this.{target_name}" for _, target_name, _ in fields)
            snapshot_fields = ", ".join(f"String {target_name}" for _, target_name, _ in fields)
        else:
            snapshot_args = "this.lastValue"
            snapshot_fields = "String lastValue"

        return f"""package com.modernizer.migration.services;

import jakarta.enterprise.context.ApplicationScoped;
import java.util.ArrayList;
import java.util.List;

@ApplicationScoped
public class {class_name}Service {{

{chr(10).join(field_lines)}
    private String lastOperation = "";
    private final List<String> messages = new ArrayList<>();

    public Snapshot execute() {{
{chr(10).join(execute_body)}
        return snapshot();
    }}

{chr(10).join(methods)}

    private void invokeProgram(String programName) {{
        this.lastOperation = "CALL " + programName;
    }}

    private void recordMessage(String message) {{
        this.messages.add(message);
        this.lastOperation = message;
    }}

    private Snapshot snapshot() {{
        return new Snapshot({snapshot_args}, this.lastOperation, List.copyOf(this.messages));
    }}

    public record Snapshot({snapshot_fields}, String lastOperation, List<String> messages) {{}}
}}
"""

    def _extract_cobol_fields(self, source_code: str) -> list[tuple[str, str, str]]:
        fields = []
        seen = set()
        normalized = re.sub(r"==\s*UT\s*==", "", source_code or "", flags=re.IGNORECASE).replace("==", "")
        pattern = re.compile(r"^\s*\d{2}\s+([A-Z0-9-]+)\s+(?:PIC|PICTURE)\b(?P<body>[^.\n]*)", re.IGNORECASE | re.MULTILINE)
        value_pattern = re.compile(r"\bVALUE\s+['\"]?([^'\".\s]+)", re.IGNORECASE)
        for match in pattern.finditer(normalized):
            source_name = match.group(1).upper()
            if source_name == "FILLER" or source_name in seen:
                continue
            seen.add(source_name)
            value_match = value_pattern.search(match.group("body") or "")
            fields.append((source_name, self._java_field_name(source_name), value_match.group(1) if value_match else ""))
        return fields[:40]

    def _extract_cobol_paragraph_blocks(self, source_code: str) -> dict[str, list[str]]:
        blocks: dict[str, list[str]] = {}
        current = ""
        in_procedure = False
        excluded = {
            "END-IF",
            "END-EVALUATE",
            "END-PERFORM",
            "END-CALL",
            "ELSE",
            "IF",
            "THEN",
            "WHEN",
            "OTHER",
            "EXIT",
            "CONTINUE",
            "GOBACK",
        }

        for line in str(source_code or "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            if re.search(r"\bPROCEDURE\s+DIVISION\b", stripped, re.IGNORECASE):
                in_procedure = True
                continue
            if not in_procedure:
                continue

            label = re.match(
                r"^([A-Z0-9][A-Z0-9-]{1,60})(?:\s+SECTION)?\.?\s*$",
                stripped,
                re.IGNORECASE,
            )
            if label:
                name = label.group(1).upper()
                if name not in excluded and not re.match(r"^(VALUE|TEMP|OUTPUT|ACTION|BOOK)(?:-\d+|-VALUE)?$", name):
                    current = name
                    blocks.setdefault(current, [])
                    continue

            if current:
                blocks[current].append(stripped)

        return blocks

    def _java_lines_from_cobol(
        self,
        body_lines: list[str],
        method_index: dict[str, str],
    ) -> list[str]:
        java_lines: list[str] = []
        index = 0
        while index < len(body_lines):
            line = body_lines[index].rstrip(".")
            upper = line.upper()

            if upper.startswith("IF "):
                if_lines, consumed = self._java_if_from_cobol(body_lines[index:], method_index)
                java_lines.extend(if_lines)
                index += consumed
                continue

            if upper.startswith("EVALUATE "):
                variable = self._java_expr(line.split(None, 1)[1])
                switch_lines, consumed = self._java_switch_from_evaluate(
                    body_lines[index:],
                    variable,
                    method_index,
                )
                java_lines.extend(switch_lines)
                index += consumed
                continue

            converted = self._java_statement_from_cobol(line, method_index)
            if converted:
                java_lines.extend(converted)
            index += 1
        return java_lines

    def _java_if_from_cobol(
        self,
        lines: list[str],
        method_index: dict[str, str],
    ) -> tuple[list[str], int]:
        first = lines[0].strip().rstrip(".")
        condition = re.sub(r"^\s*IF\s+", "", first, flags=re.IGNORECASE)
        result = [f"        if ({self._java_condition(condition)}) {{"]
        consumed = 1
        in_else = False

        for raw in lines[1:]:
            consumed += 1
            line = raw.strip().rstrip(".")
            upper = line.upper()
            if upper.startswith("END-IF") or upper.startswith("END IF"):
                break
            if upper == "ELSE":
                result.append("        } else {")
                in_else = True
                continue
            converted = self._java_statement_from_cobol(line, method_index, indent="            ")
            result.extend(converted)

        result.append("        }")
        return result, consumed

    def _java_switch_from_evaluate(
        self,
        lines: list[str],
        variable: str,
        method_index: dict[str, str],
    ) -> tuple[list[str], int]:
        result = [f"        switch ({variable}) {{"]
        current_case = ""
        consumed = 1
        for raw in lines[1:]:
            consumed += 1
            line = raw.strip().rstrip(".")
            upper = line.upper()
            if upper.startswith("END-EVALUATE"):
                break
            if upper.startswith("WHEN "):
                if current_case:
                    result.append("            }")
                condition = line[5:].strip()
                current_case = "default" if condition.upper() == "OTHER" else f"case {self._java_expr(condition)}"
                result.append(f"            {current_case} -> {{")
                continue
            converted = self._java_statement_from_cobol(line, method_index, indent="                ")
            result.extend(converted)
        if current_case:
            result.append("            }")
        result.append("        }")
        return result, consumed

    def _java_statement_from_cobol(
        self,
        line: str,
        method_index: dict[str, str],
        indent: str = "        ",
    ) -> list[str]:
        stripped = line.strip().rstrip(".")
        if not stripped:
            return []

        move = re.search(r"\bMOVE\s+(.+?)\s+TO\s+([A-Z0-9-]+)", stripped, re.IGNORECASE)
        if move:
            return [f"{indent}{self._java_field_name(move.group(2))} = {self._java_expr(move.group(1))};"]

        subtract = re.search(r"\bSUBTRACT\s+(.+?)\s+FROM\s+([A-Z0-9-]+)", stripped, re.IGNORECASE)
        if subtract:
            target = self._java_field_name(subtract.group(2))
            return [f"{indent}{target} = String.valueOf(Integer.parseInt({target}) - Integer.parseInt({self._java_expr(subtract.group(1))}));"]

        add = re.search(r"\bADD\s+(.+?)\s+TO\s+([A-Z0-9-]+)", stripped, re.IGNORECASE)
        if add:
            target = self._java_field_name(add.group(2))
            return [f"{indent}{target} = String.valueOf(Integer.parseInt({target}) + Integer.parseInt({self._java_expr(add.group(1))}));"]

        perform = re.search(r"\bPERFORM\s+([A-Z0-9][A-Z0-9-]+)", stripped, re.IGNORECASE)
        if perform:
            target = perform.group(1).upper()
            return [f"{indent}{method_index.get(target, self._java_method_name(target))}();"]

        call = re.search(r"\bCALL\s+['\"]?([A-Z0-9-]+)['\"]?", stripped, re.IGNORECASE)
        if call:
            program = call.group(1)
            if program.upper() == program and "-" not in program:
                expr = f'"{self._java_escape(program)}"'
            else:
                expr = self._java_expr(program)
            return [f"{indent}invokeProgram({expr});"]

        display = re.search(r"\bDISPLAY\s+(.+)", stripped, re.IGNORECASE)
        if display:
            return [f"{indent}recordMessage({self._java_expr(display.group(1))});"]

        if re.search(r"\b(?:CONTINUE|EXIT\s+(?:SECTION|PARAGRAPH))\b", stripped, re.IGNORECASE):
            return [f'{indent}this.lastOperation = "CONTINUE";']

        if re.search(r"\bGOBACK\b", stripped, re.IGNORECASE):
            return [f'{indent}this.lastOperation = "GOBACK";']

        return []

    def _java_condition(self, condition: str) -> str:
        text = str(condition or "").strip().rstrip(".")
        match = re.match(
            r"([A-Z0-9-]+)\s+(LESS\s+THAN|GREATER\s+THAN|=|EQUAL\s+TO|NOT\s+=)\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return "true"

        left = self._java_expr(match.group(1))
        op_text = match.group(2).upper()
        right = self._java_expr(match.group(3))
        op = {
            "LESS THAN": "<",
            "GREATER THAN": ">",
            "=": "==",
            "EQUAL TO": "==",
            "NOT =": "!=",
        }.get(op_text, "==")
        return f"Integer.parseInt({left}) {op} Integer.parseInt({right})"

    def _java_expr(self, value: str) -> str:
        text = str(value or "").strip().rstrip(",.")
        quoted = re.match(r"""^['"](.+)['"]$""", text)
        if quoted:
            return f'"{self._java_escape(quoted.group(1))}"'
        if re.match(r"^-?\d+(?:\.\d+)?$", text):
            return text
        return f"this.{self._java_field_name(text)}"

    def _java_field_name(self, value: str) -> str:
        camel = self._camel_name(value)
        if camel in {"class", "return", "switch", "default", "public", "private", "void"}:
            camel += "Value"
        return camel or "value"

    def _java_method_name(self, value: str) -> str:
        raw = str(value or "execute")
        number = re.match(r"^(\d+)[-_]*(.*)$", raw)
        if number:
            suffix = self._camel_name(number.group(2))
            camel = f"p{number.group(1)}{suffix[:1].upper() + suffix[1:] if suffix else ''}"
        else:
            camel = self._camel_name(raw)
        if camel in {"class", "return", "switch", "default", "public", "private", "void", "if", "else", "case", "for", "while", "do", "try", "catch", "finally"}:
            camel += "Paragraph"
        return camel or "executeParagraph"

    def _camel_name(self, value: str) -> str:
        parts = re.split(r"[^A-Za-z0-9]+", str(value or ""))
        parts = [part.lower() for part in parts if part]
        if not parts:
            return ""
        return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])

    def _java_escape(self, value: str) -> str:
        return str(value or "").replace("\\", "\\\\").replace('"', '\\"')

    def _fallback_python(self, module_name: str) -> str:
        return f"""from decimal import Decimal


class {self._class_name(module_name)}Service:
    def execute_business_rule(self, balance: Decimal | None) -> bool:
        if balance is None:
            return False
        return balance >= Decimal("0")
"""

    def _fallback_csharp(self, class_name: str) -> str:
        return f"""namespace GeneratedMigration.Services;

public class {class_name}Service
{{
    public bool ExecuteBusinessRule(decimal? balance)
    {{
        if (balance is null)
        {{
            return false;
        }}

        return balance.Value >= 0m;
    }}
}}
"""

    def _class_name_from_file(self, file_name: str) -> str:
        return self._class_name(Path(file_name or "LegacyProgram").stem)

    def _class_name(self, text: str) -> str:
        parts = re.split(r"[^A-Za-z0-9]+", str(text or "LegacyProgram"))
        value = "".join(part[:1].upper() + part[1:].lower() for part in parts if part)
        return value or "LegacyProgram"

    def _snake_name(self, text: str) -> str:
        value = re.sub(r"[^A-Za-z0-9]+", "_", str(text or "legacy_program"))
        value = re.sub(r"_{2,}", "_", value).strip("_").lower()
        return value or "legacy_program"

    def _strip_code_fences(self, content: str) -> str:
        text = str(content or "").strip()
        text = re.sub(r"^```[a-zA-Z0-9_+-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip() + "\n"

    def _as_list(self, value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if value in (None, ""):
            return []
        return [value]

    def _trim(self, text: Any, max_chars: int) -> str:
        value = str(text or "")
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + "\n\n...[TRUNCATED]..."

    def _trim_json(self, value: Any, max_chars: int) -> str:
        try:
            text = json.dumps(value or {}, indent=2, ensure_ascii=False)
        except Exception:
            text = str(value or "")
        return self._trim(text, max_chars)
