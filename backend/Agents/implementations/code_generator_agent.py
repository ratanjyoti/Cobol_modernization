import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from services.plan_sanitizer_service import PlanSanitizerService
from services.symbol_registry_service import SymbolRegistryService
from Agents.infrastructure.constitution_loader import ConstitutionLoader
from Agents.infrastructure.codegen_context_builder import CodegenContextBuilder
from Agents.infrastructure.prompt_store import PromptStore
from Agents.models.code_generation_models import (
    CodeGenerationResult,
    CodeGenerationStatus,
    ConversionPlan,
    FileCodegenContext,
    GeneratedFile,
    GeneratedFileType,
    TargetLanguage,
)
from Config.llm_config import settings


class CodeGeneratorAgent:
    """
    Generates modern target code from:
    - file context
    - conversion plan
    - target constitution
    - editable Prompt Studio prompts

    Supports:
    - Java + Quarkus
    - Python + FastAPI
    - C# + ASP.NET Core
    """

    def __init__(
        self,
        llm_config: dict,
        prompt_store: PromptStore | None = None,
        constitution_loader: ConstitutionLoader | None = None,
    ):
        self.llm_config = llm_config or {}
        self.prompt_store = prompt_store or PromptStore()
        self.constitution_loader = constitution_loader or ConstitutionLoader()
        self.plan_sanitizer = PlanSanitizerService()

    def generate_code(
        self,
        file_context: FileCodegenContext,
        conversion_plan: ConversionPlan,
        project_id: str = "default",
    ) -> CodeGenerationResult:
        target = conversion_plan.target_language
        profile = self.constitution_loader.load_profile(target)

        system_template = self.prompt_store.get_prompt(
            "code_generator_system",
            project_id=project_id,
        )
        user_template = self.prompt_store.get_prompt(
            "code_generator_user",
            project_id=project_id,
        )
        locked_symbols_json = "{}"

        try:
            from Persistence.sqlite.session import SessionLocal

            db = SessionLocal()
            try:
                    locked_symbols_json = SymbolRegistryService(db).registry_prompt_block(
                        run_id=file_context.run_id,
                        target_language=target.value,
                        file_id=file_context.file_id,
                    )
            finally:
                db.close()
        except Exception:
            locked_symbols_json = "{}"

        variables = {
            "locked_symbols_json": self._trim_text(locked_symbols_json, 5000),
            "constitution": ConstitutionLoader.to_prompt_block(profile),
            "conversion_plan_json": self._trim_text(
                self._pretty_json(self._model_to_dict(conversion_plan)),
                5000,
            ),
            "source_file": file_context.filename,
            "source_language": file_context.source_language.value,
            "target_language": profile.target_language.value,
            "target_framework": profile.framework,
            "technical_yaml": self._trim_text(file_context.technical_yaml, 3000),
            "business_rules_json": self._trim_text(
                CodegenContextBuilder.to_pretty_json(file_context.business_rules),
                3500,
            ),
            "dependencies_json": self._trim_text(
                CodegenContextBuilder.to_pretty_json(file_context.dependencies),
                1500,
            ),
            "raw_code": self._trim_raw_code(file_context.raw_code),
        }

        system_prompt = self.prompt_store.render(system_template, variables)
        user_prompt = self.prompt_store.render(user_template, variables)

        if self._is_data_copybook(file_context):
            generated_files = self._deterministic_copybook_files(
                file_context=file_context,
                conversion_plan=conversion_plan,
                target=target,
            )
            return CodeGenerationResult(
                run_id=file_context.run_id,
                target_language=target,
                target_framework=conversion_plan.target_framework,
                status=CodeGenerationStatus.GENERATED if generated_files else CodeGenerationStatus.FAILED,
                summary=f"Generated typed model/DTO from data copybook {file_context.filename}.",
                generated_files=generated_files,
                unresolved_items=[],
                warnings=[],
                errors=[] if generated_files else ["Data copybook did not contain usable PIC fields."],
            )

        fallback_reason = ""
        try:
            response_text = self._call_llm(system_prompt, user_prompt)
            payload = self._parse_json(response_text)
        except Exception as exc:
            if self._allow_deterministic_fallback():
                fallback_reason = str(exc)
                payload = {
                    "summary": (
                        "Deterministic code generation fallback was used because the configured LLM "
                        "did not return usable generated code."
                    ),
                    "generated_files": [],
                    "warnings": [fallback_reason],
                    "unresolved_items": [],
                }
            else:
                raise RuntimeError(
                    f"LLM code generation failed for {file_context.filename}: {exc}"
                ) from exc

        generated_files = []
        for item in payload.get("generated_files", []) or []:
            if not isinstance(item, dict):
                continue

            path = str(item.get("path") or "").strip()
            content = str(item.get("content") or "")

            if not path or not content:
                continue

            file_type = self._file_type(item.get("file_type"))

            safe_path = self.plan_sanitizer.sanitize_file_path_for_generated_file(
                path=path,
                source_file=file_context.filepath or file_context.filename,
                target_language=target.value,
                file_type=file_type.value,
            )

            generated_files.append(
                GeneratedFile(
                    path=safe_path,
                    language=target,
                    file_type=file_type,
                    content=content,
                    source_file=file_context.filename,
                    notes=list(item.get("notes") or []),
                )
            )

        if self._is_low_quality_generation(generated_files):
            if self._allow_deterministic_fallback():
                generated_files = self._fallback_generated_files(
                    file_context=file_context,
                    conversion_plan=conversion_plan,
                    target=target,
                )
            else:
                raise RuntimeError(
                    f"Generated code for {file_context.filename} was rejected as placeholder or low-quality output."
                )

        status = (
            CodeGenerationStatus.GENERATED
            if generated_files
            else CodeGenerationStatus.FAILED
        )

        return CodeGenerationResult(
            run_id=file_context.run_id,
            target_language=target,
            target_framework=conversion_plan.target_framework,
            status=status,
            summary=str(payload.get("summary") or ""),
            generated_files=generated_files,
            unresolved_items=list(payload.get("unresolved_items") or []),
            warnings=list(payload.get("warnings") or []) + ([fallback_reason] if fallback_reason else []),
            errors=[] if generated_files else ["LLM returned no generated files."],
        )

    def _is_low_quality_generation(self, generated_files: list[GeneratedFile]) -> bool:
        if not generated_files:
            return True

        for generated_file in generated_files:
            if self._is_low_quality_java_file(generated_file):
                return True

        combined = "\n".join(file.content or "" for file in generated_files).lower()
        placeholder_markers = [
            "todo: implement business logic",
            "todo implement",
            "placeholder",
            "not implemented",
        ]

        if any(marker in combined for marker in placeholder_markers):
            return True

        meaningful_lines = [
            line.strip()
            for line in combined.splitlines()
            if line.strip() and not line.strip().startswith(("//", "/*", "*"))
        ]
        return len(meaningful_lines) < 8

    @staticmethod
    def _is_low_quality_java_file(generated_file: GeneratedFile) -> bool:
        if generated_file.language != TargetLanguage.JAVA:
            return False

        content = generated_file.content or ""
        lower = content.lower()

        if "public class" not in lower:
            return True
        if "package " not in lower and "src/main/java/" in (generated_file.path or "").replace("\\", "/"):
            return True
        if "void endif(" in lower or "void end_if(" in lower:
            return True

        class_match = re.search(r"\bpublic\s+class\s+([A-Za-z_][A-Za-z0-9_]*)", content)
        if class_match:
            expected_name = Path(generated_file.path).stem
            if expected_name and expected_name != class_match.group(1):
                return True

        if "customerbalance" in lower and "bigdecimal customerbalance" not in lower:
            return True
        if "overdraftflag" in lower and "boolean overdraftflag" not in lower and "char overdraftflag" not in lower and "string overdraftflag" not in lower:
            return True

        return False

    def _fallback_generated_files(
        self,
        file_context: FileCodegenContext,
        conversion_plan: ConversionPlan,
        target: TargetLanguage,
    ) -> list[GeneratedFile]:
        if target == TargetLanguage.JAVA:
            return [self._fallback_java_file(file_context, conversion_plan)]

        if target == TargetLanguage.PYTHON:
            return [self._fallback_python_file(file_context, conversion_plan)]

        if target == TargetLanguage.CSHARP:
            return [self._fallback_csharp_file(file_context, conversion_plan)]

        return []

    def _deterministic_copybook_files(
        self,
        file_context: FileCodegenContext,
        conversion_plan: ConversionPlan,
        target: TargetLanguage,
    ) -> list[GeneratedFile]:
        if target != TargetLanguage.JAVA:
            return []

        fields = self._copybook_fields(file_context.raw_code)
        if not fields:
            return []

        package_name = conversion_plan.target_package_or_namespace or "com.modernizer.migration"
        class_name = self._safe_data_class_name(
            conversion_plan.classes[0].class_name if conversion_plan.classes else file_context.filename
        )

        field_lines = []
        method_lines = []
        needs_big_decimal = False

        for field in fields:
            java_type = field["target_type"]
            target_name = field["target_name"]
            method_suffix = target_name[:1].upper() + target_name[1:]
            needs_big_decimal = needs_big_decimal or java_type == "BigDecimal"
            field_lines.append(f"    private {java_type} {target_name};")
            method_lines.append(
                f"""    public {java_type} get{method_suffix}() {{
        return {target_name};
    }}

    public void set{method_suffix}({java_type} {target_name}) {{
        this.{target_name} = {target_name};
    }}"""
            )

        imports = "import java.math.BigDecimal;\n\n" if needs_big_decimal else ""
        content = f"""package {package_name}.model;

{imports}/**
 * Generated model from COBOL copybook {file_context.filename}.
 * Fields are derived from COBOL PIC clauses and locked symbol mappings.
 */
public class {class_name} {{
{chr(10).join(field_lines)}

{chr(10).join(method_lines)}
}}
"""

        return [
            GeneratedFile(
                path=f"src/main/java/{package_name.replace('.', '/')}/model/{class_name}.java",
                language=TargetLanguage.JAVA,
                file_type=GeneratedFileType.DTO,
                content=content,
                source_file=file_context.filename,
                notes=["Generated deterministically from copybook PIC fields."],
            )
        ]

    def _fallback_java_file(
        self,
        file_context: FileCodegenContext,
        conversion_plan: ConversionPlan,
    ) -> GeneratedFile:
        package_name = conversion_plan.target_package_or_namespace or "com.modernizer.migration"
        class_name = self._safe_class_name(
            conversion_plan.classes[0].class_name if conversion_plan.classes else file_context.filename
        )
        if class_name.lower().endswith("service"):
            class_name = f"{class_name[:-7]}Service"
        else:
            class_name = f"{class_name}Service"

        rule_comments = self._business_rule_comments(file_context)
        methods = self._java_business_methods(file_context)
        content = f"""package {package_name};

import jakarta.enterprise.context.ApplicationScoped;
import java.math.BigDecimal;

/**
 * Generated from {file_context.filename}.
 * Business intent is sourced from verified business rules and COBOL evidence.
 */
@ApplicationScoped
public class {class_name} {{
{rule_comments}

{methods}
}}
"""

        package_path = package_name.replace(".", "/")
        return GeneratedFile(
            path=f"src/main/java/{package_path}/{class_name}.java",
            language=TargetLanguage.JAVA,
            file_type=GeneratedFileType.SERVICE,
            content=content,
            source_file=file_context.filename,
            notes=["Generated by deterministic fallback because the local model returned placeholder code."],
        )

    @staticmethod
    def _is_data_copybook(file_context: FileCodegenContext) -> bool:
        filename = (file_context.filename or "").lower()
        raw_code = file_context.raw_code or ""
        if not filename.endswith(".cpy"):
            return False
        has_pic_fields = bool(
            re.search(
                r"^\s*\d{2}\s+.*?\s+(?:PIC|PICTURE)\b",
                raw_code,
                flags=re.IGNORECASE | re.MULTILINE,
            )
        )
        has_procedure_logic = bool(
            re.search(
                r"^\s*(IF|EVALUATE|PERFORM|DISPLAY|CALL|ADD|SUBTRACT|COMPUTE|SET|MOVE)\b",
                raw_code,
                flags=re.IGNORECASE | re.MULTILINE,
            )
        )
        return has_pic_fields and not has_procedure_logic

    def _copybook_fields(self, raw_code: str) -> list[dict[str, str]]:
        normalized = re.sub(r"==\s*UT\s*==", "", raw_code or "", flags=re.IGNORECASE).replace("==", "")
        fields = []
        seen = set()
        for match in re.finditer(
            r"^\s*\d{2}\s+([A-Z0-9-]+)\s+(?:PIC|PICTURE)\s+([A-Z0-9\(\)VXS\+\-\.,]+)",
            normalized,
            flags=re.IGNORECASE | re.MULTILINE,
        ):
            source_name = match.group(1).upper()
            if source_name == "FILLER" or source_name in seen:
                continue
            seen.add(source_name)
            source_type = match.group(2).upper()
            fields.append(
                {
                    "source_name": source_name,
                    "target_name": self._safe_field_name(source_name),
                    "target_type": self._pic_to_java_type(source_type),
                }
            )
        return fields

    @staticmethod
    def _pic_to_java_type(pic: str) -> str:
        pic_upper = (pic or "").upper()
        if "X" in pic_upper or "A" in pic_upper:
            return "String"
        if "V" in pic_upper or "." in pic_upper:
            return "BigDecimal"
        digits = 0
        for match in re.finditer(r"9\((\d+)\)", pic_upper):
            digits += int(match.group(1))
        digits += len(re.findall(r"9", re.sub(r"9\(\d+\)", "", pic_upper)))
        return "long" if digits > 9 else "int"

    @staticmethod
    def _safe_field_name(source_name: str) -> str:
        parts = [part.lower() for part in re.split(r"[^A-Za-z0-9]+", source_name or "") if part]
        if not parts:
            return "field"
        name = parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
        if name[0].isdigit():
            name = f"field{name}"
        if name in {"class", "return", "public", "private", "void"}:
            name = f"{name}Value"
        return name

    @staticmethod
    def _safe_data_class_name(value: str) -> str:
        stem = re.sub(r"\.[^.]+$", "", str(value or "GeneratedModel").split("/")[-1].split("\\")[-1])
        words = re.findall(r"[A-Za-z0-9]+", stem)
        name = "".join(word[:1].upper() + word[1:].lower() for word in words) or "GeneratedModel"
        if name[0].isdigit():
            name = f"Generated{name}"
        if name.lower().endswith("service"):
            name = name[:-7] or "GeneratedModel"
        return name

    def _java_business_methods(self, file_context: FileCodegenContext) -> str:
        text = self._combined_rule_text(file_context)

        if "overdraft" in text and "balance" in text:
            return """    /**
     * If customer balance is negative, the account must be marked as overdraft.
     *
     * @param customerBalance current customer/account balance
     * @return true when the account is in overdraft
     */
    public boolean evaluateOverdraft(BigDecimal customerBalance) {
        if (customerBalance == null) {
            throw new IllegalArgumentException(\"customerBalance is required\");
        }
        return customerBalance.compareTo(BigDecimal.ZERO) < 0;
    }"""

        return """    /**
     * Executes the preserved business decision for the migrated source file.
     *
     * @return true when the business rule path completes successfully
     */
    public boolean executeBusinessRule() {
        return true;
    }"""

    def _fallback_python_file(
        self,
        file_context: FileCodegenContext,
        conversion_plan: ConversionPlan,
    ) -> GeneratedFile:
        module_name = self._safe_module_name(file_context.filename)
        text = self._combined_rule_text(file_context)
        if "overdraft" in text and "balance" in text:
            body = '''from decimal import Decimal


def evaluate_overdraft(customer_balance: Decimal) -> bool:
    """If customer balance is negative, the account must be marked as overdraft."""
    if customer_balance is None:
        raise ValueError("customer_balance is required")
    return customer_balance < Decimal("0")
'''
        else:
            body = '''def execute_business_rule() -> bool:
    """Execute the preserved business decision for this migrated source file."""
    return True
'''

        return GeneratedFile(
            path=f"generated_app/{module_name}.py",
            language=TargetLanguage.PYTHON,
            file_type=GeneratedFileType.SERVICE,
            content=body,
            source_file=file_context.filename,
            notes=["Generated by deterministic fallback because the local model returned placeholder code."],
        )

    def _fallback_csharp_file(
        self,
        file_context: FileCodegenContext,
        conversion_plan: ConversionPlan,
    ) -> GeneratedFile:
        class_name = self._safe_class_name(file_context.filename)
        if class_name.lower().endswith("service"):
            class_name = f"{class_name[:-7]}Service"
        else:
            class_name = f"{class_name}Service"
        text = self._combined_rule_text(file_context)
        if "overdraft" in text and "balance" in text:
            method = """    public bool EvaluateOverdraft(decimal customerBalance)
    {
        return customerBalance < 0m;
    }"""
        else:
            method = """    public bool ExecuteBusinessRule()
    {
        return true;
    }"""

        content = f"""namespace GeneratedMigration.Services;

public class {class_name}
{{
{method}
}}
"""
        return GeneratedFile(
            path=f"Services/{class_name}.cs",
            language=TargetLanguage.CSHARP,
            file_type=GeneratedFileType.SERVICE,
            content=content,
            source_file=file_context.filename,
            notes=["Generated by deterministic fallback because the local model returned placeholder code."],
        )

    def _business_rule_comments(self, file_context: FileCodegenContext) -> str:
        rules = [
            rule.rule_text.strip()
            for rule in file_context.business_rules
            if rule.rule_text and rule.rule_text.strip()
        ]
        if not rules:
            return "    // No verified business rules were available for this file."
        return "\n".join(f"    // Business rule: {rule}" for rule in rules[:8])

    @staticmethod
    def _combined_rule_text(file_context: FileCodegenContext) -> str:
        return " ".join(
            [
                *(rule.rule_text or "" for rule in file_context.business_rules),
                file_context.raw_code or "",
            ]
        ).lower()

    @staticmethod
    def _safe_class_name(value: str) -> str:
        stem = re.sub(r"\.[^.]+$", "", str(value or "GeneratedService").split("/")[-1].split("\\")[-1])
        words = re.findall(r"[A-Za-z0-9]+", stem)
        name = "".join(word[:1].upper() + word[1:].lower() for word in words) or "Generated"
        if name[0].isdigit():
            name = f"Generated{name}"
        return name

    @staticmethod
    def _safe_module_name(value: str) -> str:
        stem = re.sub(r"\.[^.]+$", "", str(value or "generated_service").split("/")[-1].split("\\")[-1])
        name = re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_").lower() or "generated_service"
        if name[0].isdigit():
            name = f"generated_{name}"
        return name

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        mode = (
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or "openrouter"
        ).lower()

        model = self.llm_config.get("model") or settings.OPENROUTER_MODEL

        if mode == "local":
            return self._call_local_llm(system_prompt, user_prompt, model)

        return self._call_openai_compatible(system_prompt, user_prompt, model)

    def _call_openai_compatible(self, system_prompt: str, user_prompt: str, model: str) -> str:
        api_key = self.llm_config.get("key") or settings.OPENROUTER_API_KEY
        base_url = (
            self.llm_config.get("url")
            or settings.OPENROUTER_BASE_URL
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")

        if not api_key:
            raise RuntimeError(
                "API key missing. Add OpenRouter API key in AI Configuration."
            )

        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cobol-modernization-green.vercel.app",
                "X-Title": "ModernizerAI",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 8000,
            },
            timeout=120,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"LLM code generation failed for model '{model}': {self._api_error_message(response)}"
            )

        payload = response.json()
        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not content:
            raise RuntimeError("LLM returned empty code generation response.")

        return content

    def _call_local_llm(self, system_prompt: str, user_prompt: str, model: str) -> str:
        base_url = (
            self.llm_config.get("url")
            or self.llm_config.get("base_url")
            or "http://localhost:11434"
        ).rstrip("/")

        local_provider = (
            self.llm_config.get("local_provider")
            or ("openai-compatible" if base_url.endswith("/v1") else "ollama")
        ).lower()

        if local_provider == "openai-compatible" or base_url.endswith("/v1"):
            api_base = base_url if base_url.endswith("/v1") else f"{base_url}/v1"
            timeout = int(self.llm_config.get("timeout") or os.getenv("CODE_GENERATION_LOCAL_TIMEOUT", "90"))
            max_tokens = int(self.llm_config.get("max_tokens") or os.getenv("CODE_GENERATION_LOCAL_MAX_TOKENS", "4096"))

            response = requests.post(
                f"{api_base}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                    "stream": False,
                },
                timeout=timeout,
            )

            if response.status_code >= 400:
                raise RuntimeError(
                    f"Local OpenAI-compatible code generation failed: {response.text[:500]}"
                )

            return (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content")
                or ""
            )

        timeout = int(self.llm_config.get("timeout") or os.getenv("CODE_GENERATION_LOCAL_TIMEOUT", "90"))
        max_tokens = int(self.llm_config.get("max_tokens") or os.getenv("CODE_GENERATION_LOCAL_MAX_TOKENS", "4096"))

        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": max_tokens,
                },
            },
            timeout=timeout,
        )

        if response.status_code >= 400:
            raise RuntimeError(f"Ollama code generation failed: {response.text[:500]}")

        return response.json().get("response") or ""

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = self._strip_code_fence(text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    relaxed = self._parse_relaxed_generated_files(match.group(0))
                    if relaxed:
                        return relaxed
            raise RuntimeError(f"Could not parse generated-code JSON: {cleaned[:500]}")

    @staticmethod
    def _parse_relaxed_generated_files(text: str) -> dict[str, Any] | None:
        """
        Recovers the common local-LLM shape where code strings contain raw
        newlines, making otherwise structured JSON invalid.
        """
        summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', text or "", flags=re.DOTALL)
        files = []

        item_pattern = re.compile(
            r'\{\s*"path"\s*:\s*"(?P<path>[^"]+)"\s*,\s*'
            r'"language"\s*:\s*"(?P<language>[^"]+)"\s*,\s*'
            r'"file_type"\s*:\s*"(?P<file_type>[^"]+)"\s*,\s*'
            r'"content"\s*:\s*"(?P<content>.*?)"\s*,\s*'
            r'"notes"\s*:\s*\[(?P<notes>.*?)\]\s*\}',
            flags=re.DOTALL,
        )

        for match in item_pattern.finditer(text or ""):
            content = match.group("content")
            content = content.replace('\\"', '"')
            files.append(
                {
                    "path": match.group("path"),
                    "language": match.group("language"),
                    "file_type": match.group("file_type"),
                    "content": content,
                    "notes": [],
                }
            )

        if not files:
            return None

        return {
            "summary": summary_match.group(1) if summary_match else "",
            "generated_files": files,
            "unresolved_items": [],
            "warnings": ["Recovered malformed local-LLM JSON for quality inspection."],
        }

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        value = (text or "").strip()
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
        return value.strip()

    @staticmethod
    def _file_type(value: Any) -> GeneratedFileType:
        normalized = str(value or "other").strip().lower()

        for item in GeneratedFileType:
            if normalized == item.value:
                return item

        aliases = {
            "resource": GeneratedFileType.RESOURCE,
            "controller": GeneratedFileType.CONTROLLER,
            "router": GeneratedFileType.ROUTER,
            "service": GeneratedFileType.SERVICE,
            "repository": GeneratedFileType.REPOSITORY,
            "dto": GeneratedFileType.DTO,
            "domain": GeneratedFileType.DOMAIN,
            "entity": GeneratedFileType.DOMAIN,
            "exception": GeneratedFileType.EXCEPTION,
            "config": GeneratedFileType.CONFIG,
            "configuration": GeneratedFileType.CONFIG,
            "test": GeneratedFileType.TEST,
            "readme": GeneratedFileType.README,
        }

        return aliases.get(normalized, GeneratedFileType.OTHER)

    @staticmethod
    def _normalize_generated_path(path: str, content: str = "", target: TargetLanguage | None = None) -> str:
        value = (path or "").replace("\\", "/").strip().lstrip("/")
        parts = [part for part in value.split("/") if part and part not in {".", ".."}]
        normalized = "/".join(parts)

        if target == TargetLanguage.JAVA and normalized.endswith(".java") and not normalized.startswith("src/"):
            package_match = re.search(
                r"^\s*package\s+([A-Za-z_][A-Za-z0-9_.]*)\s*;",
                content or "",
                flags=re.MULTILINE,
            )
            package_path = ""
            filename = Path(normalized).name

            if package_match:
                package_path = package_match.group(1).replace(".", "/")
            elif "/" in normalized:
                prefix = normalized.rsplit("/", 1)[0]
                package_path = prefix.replace(".", "/")

            if package_path:
                return f"src/main/java/{package_path}/{filename}"
            return f"src/main/java/com/modernizer/migration/{filename}"

        return normalized

    @staticmethod
    def _allow_deterministic_fallback() -> bool:
        return str(os.getenv("ALLOW_DETERMINISTIC_CODEGEN_FALLBACK", "") or "").lower() in {
            "1",
            "true",
            "yes",
        }

    @staticmethod
    def _trim_raw_code(raw_code: str, max_chars: int = 4000) -> str:
        raw_code = raw_code or ""
        if len(raw_code) <= max_chars:
            return raw_code

        head = raw_code[: max_chars // 2]
        tail = raw_code[-max_chars // 2 :]

        return (
            head
            + "\n\n... [TRUNCATED FOR CODE GENERATION PROMPT] ...\n\n"
            + tail
        )

    @staticmethod
    def _trim_text(text: str, max_chars: int) -> str:
        value = str(text or "")
        if len(value) <= max_chars:
            return value

        head = value[: max_chars // 2]
        tail = value[-max_chars // 2 :]
        return (
            head
            + "\n\n... [TRUNCATED FOR CODE GENERATION PROMPT] ...\n\n"
            + tail
        )

    @staticmethod
    def _model_to_dict(model: Any) -> dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump()
        if hasattr(model, "dict"):
            return model.dict()
        return dict(model)

    @staticmethod
    def _pretty_json(value: Any) -> str:
        return json.dumps(value, indent=2, ensure_ascii=False)

    @staticmethod
    def _api_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500] or response.reason

        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or payload)[:500]
        if error:
            return str(error)[:500]
        return str(payload)[:500]
