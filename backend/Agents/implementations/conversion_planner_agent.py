import json
import os
import re
from typing import Any

import requests
from services.plan_sanitizer_service import PlanSanitizerService
from Agents.infrastructure.constitution_loader import ConstitutionLoader
from Agents.infrastructure.codegen_context_builder import CodegenContextBuilder
from Agents.infrastructure.prompt_store import PromptStore
from Agents.models.code_generation_models import (
    ConversionPlan,
    FileCodegenContext,
    PlannedClass,
    PlannedMethod,
    TargetLanguage,
)
from Config.llm_config import settings
from services.symbol_registry_service import SymbolRegistryService

class ConversionPlannerAgent:
    """
    Creates a file-level conversion plan.

    It does not generate code.
    It only decides target classes, methods, mappings, unresolved dependencies,
    package/namespace, and assumptions.
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

    def create_plan(
        self,
        file_context: FileCodegenContext,
        target_language: str,
        project_id: str = "default",
    ) -> ConversionPlan:
        target = self.constitution_loader._normalize_target_language(target_language)
        profile = self.constitution_loader.load_profile(target)

        system_template = self.prompt_store.get_prompt(
            "conversion_planner_system",
            project_id=project_id,
        )
        user_template = self.prompt_store.get_prompt(
            "conversion_planner_user",
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
            "constitution": self._trim_text(
                ConstitutionLoader.to_prompt_block(profile),
                3500,
            ),
            "source_file": file_context.filename,
            "locked_symbols_json": self._trim_text(locked_symbols_json, 3000),
            "source_language": file_context.source_language.value,
            "target_language": profile.target_language.value,
            "target_framework": profile.framework,
            "technical_yaml": self._trim_text(file_context.technical_yaml, 5000),
            "business_rules_json": self._trim_text(
                CodegenContextBuilder.to_pretty_json(file_context.business_rules),
                3500,
            ),
            "dependencies_json": self._trim_text(
                CodegenContextBuilder.to_pretty_json(file_context.dependencies),
                2500,
            ),
            "raw_code": self._trim_raw_code(file_context.raw_code, max_chars=5000),
        }

        system_prompt = self.prompt_store.render(system_template, variables)
        user_prompt = self.prompt_store.render(user_template, variables)

        if self._is_data_copybook(file_context):
            raw_plan = self._copybook_model_plan_payload(file_context, target)
        else:
            try:
                response_text = self._call_llm(system_prompt, user_prompt)
                raw_plan = self._parse_json(response_text)

                raw_plan = self.plan_sanitizer.sanitize_plan(
                    raw_plan=raw_plan,
                    source_file=file_context.filepath or file_context.filename,
                    target_language=target.value,
                )
            except Exception as exc:
                if self._allow_deterministic_fallback() or self._is_local_mode():
                    raw_plan = self._fallback_plan_payload(
                        file_context=file_context,
                        target_language=target,
                        target_framework=profile.framework,
                        reason=str(exc),
                    )
                    raw_plan = self.plan_sanitizer.sanitize_plan(
                        raw_plan=raw_plan,
                        source_file=file_context.filepath or file_context.filename,
                        target_language=target.value,
                    )
                else:
                    raise RuntimeError(
                        f"LLM conversion planning failed for {file_context.filename}: {exc}"
                    ) from exc

                return self._to_conversion_plan(
                    raw_plan=raw_plan,
                    file_context=file_context,
                    target_language=target,
                    target_framework=profile.framework,
                )

        return self._to_conversion_plan(
            raw_plan=raw_plan,
            file_context=file_context,
            target_language=target,
            target_framework=profile.framework,
        )

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
                "max_tokens": 4000,
            },
            timeout=90,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"LLM planning request failed for model '{model}': {self._api_error_message(response)}"
            )

        payload = response.json()
        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not content:
            raise RuntimeError("LLM returned empty conversion plan response.")

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
            timeout = int(self.llm_config.get("timeout") or os.getenv("CONVERSION_PLANNER_LOCAL_TIMEOUT", "45"))
            max_tokens = int(self.llm_config.get("max_tokens") or os.getenv("CONVERSION_PLANNER_LOCAL_MAX_TOKENS", "2200"))

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
                    f"Local OpenAI-compatible planning failed: {response.text[:500]}"
                )

            return (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content")
                or ""
            )

        timeout = int(self.llm_config.get("timeout") or os.getenv("CONVERSION_PLANNER_LOCAL_TIMEOUT", "45"))
        max_tokens = int(self.llm_config.get("max_tokens") or os.getenv("CONVERSION_PLANNER_LOCAL_MAX_TOKENS", "2200"))

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
            raise RuntimeError(f"Ollama planning failed: {response.text[:500]}")

        return response.json().get("response") or ""

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = self._strip_code_fence(text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise RuntimeError(f"Could not parse conversion plan JSON: {cleaned[:500]}")

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        value = (text or "").strip()
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
        return value.strip()

    def _to_conversion_plan(
        self,
        raw_plan: dict[str, Any],
        file_context: FileCodegenContext,
        target_language: TargetLanguage,
        target_framework: str,
    ) -> ConversionPlan:
        classes = []
        for item in raw_plan.get("classes", []) or []:
            if not isinstance(item, dict):
                continue
            classes.append(
                PlannedClass(
                    class_name=str(item.get("class_name") or item.get("name") or ""),
                    file_path=str(item.get("file_path") or item.get("path") or ""),
                    layer=str(item.get("layer") or "other"),
                    responsibility=str(item.get("responsibility") or ""),
                    source_mapping=list(item.get("source_mapping") or []),
                )
            )

        methods = []
        for item in raw_plan.get("methods", []) or []:
            if not isinstance(item, dict):
                continue
            methods.append(
                PlannedMethod(
                    method_name=str(item.get("method_name") or item.get("name") or ""),
                    owning_class=str(item.get("owning_class") or item.get("class") or ""),
                    responsibility=str(item.get("responsibility") or ""),
                    source_mapping=list(item.get("source_mapping") or []),
                    inputs=list(item.get("inputs") or []),
                    outputs=list(item.get("outputs") or []),
                )
            )

        return ConversionPlan(
            run_id=file_context.run_id,
            file_id=file_context.file_id,
            source_file=file_context.filename,
            source_language=file_context.source_language,
            target_language=target_language,
            target_framework=target_framework,
            target_package_or_namespace=str(
                raw_plan.get("target_package_or_namespace")
                or raw_plan.get("target_package")
                or raw_plan.get("target_namespace")
                or ""
            ),
            summary=str(raw_plan.get("summary") or ""),
            classes=classes,
            methods=methods,
            data_models=self._list_of_dicts(raw_plan.get("data_models")),
            external_dependencies=self._list_of_strings(raw_plan.get("external_dependencies")),
            unresolved_items=self._list_of_strings(raw_plan.get("unresolved_items")),
            assumptions=self._list_of_strings(raw_plan.get("assumptions")),
            raw_plan=raw_plan,
        )

    def _fallback_plan_payload(
        self,
        file_context: FileCodegenContext,
        target_language: TargetLanguage,
        target_framework: str,
        reason: str,
    ) -> dict[str, Any]:
        class_name = self._safe_class_name(file_context.filename)
        package_or_namespace = self._default_package_or_namespace(target_language)
        file_path = self._default_file_path(
            class_name=class_name,
            target_language=target_language,
            package_or_namespace=package_or_namespace,
        )

        return {
            "target_package_or_namespace": package_or_namespace,
            "summary": (
                f"Deterministic conversion plan for {file_context.filename}. "
                "The source will be migrated as a service/data-definition component using extracted business rules and source evidence."
            ),
            "classes": [
                {
                    "class_name": class_name,
                    "file_path": file_path,
                    "layer": "service",
                    "responsibility": (
                        "Preserve the business behavior, validations, calculations, messages, and shared data semantics "
                        f"identified in {file_context.filename}."
                    ),
                    "source_mapping": [file_context.filename],
                }
            ],
            "methods": [
                {
                    "method_name": "execute",
                    "owning_class": class_name,
                    "responsibility": "Execute the preserved business rule path for this legacy source file.",
                    "source_mapping": [file_context.filename],
                    "inputs": [],
                    "outputs": [],
                }
            ],
            "data_models": [],
            "external_dependencies": [
                item.target_item
                for item in file_context.dependencies
                if item.target_item
            ],
            "unresolved_items": [],
            "assumptions": [
                "Fallback plan created because the configured LLM did not return a usable conversion plan.",
                reason[:300],
            ],
        }

    def _copybook_model_plan_payload(
        self,
        file_context: FileCodegenContext,
        target_language: TargetLanguage,
    ) -> dict[str, Any]:
        class_name = self._safe_data_class_name(file_context.filename)
        package_or_namespace = self._default_package_or_namespace(target_language)
        file_path = self._default_model_file_path(
            class_name=class_name,
            target_language=target_language,
            package_or_namespace=package_or_namespace,
        )

        return {
            "target_package_or_namespace": package_or_namespace,
            "summary": (
                f"{file_context.filename} is a data copybook and will be migrated as a shared model/DTO class."
            ),
            "classes": [
                {
                    "class_name": class_name,
                    "file_path": file_path,
                    "layer": "model",
                    "responsibility": "Represent the shared COBOL copybook fields as typed target-language fields.",
                    "source_mapping": [file_context.filename],
                }
            ],
            "methods": [],
            "data_models": [
                {
                    "class_name": class_name,
                    "source_file": file_context.filename,
                    "field_count": len(self._copybook_fields(file_context.raw_code)),
                }
            ],
            "external_dependencies": [],
            "unresolved_items": [],
            "assumptions": [
                "Data copybook model plan created deterministically from COBOL PIC fields."
            ],
        }

    @staticmethod
    def _safe_class_name(value: str) -> str:
        stem = re.sub(r"\.[^.]+$", "", str(value or "GeneratedService").split("/")[-1].split("\\")[-1])
        words = re.findall(r"[A-Za-z0-9]+", stem)
        name = "".join(word[:1].upper() + word[1:].lower() for word in words) or "Generated"
        if name[0].isdigit():
            name = f"Generated{name}"
        if not name.lower().endswith("service"):
            name = f"{name}Service"
        return name

    @staticmethod
    def _safe_data_class_name(value: str) -> str:
        stem = re.sub(r"\.[^.]+$", "", str(value or "GeneratedModel").split("/")[-1].split("\\")[-1])
        words = re.findall(r"[A-Za-z0-9]+", stem)
        name = "".join(word[:1].upper() + word[1:].lower() for word in words) or "GeneratedModel"
        if name[0].isdigit():
            name = f"Generated{name}"
        return name

    @staticmethod
    def _default_package_or_namespace(target_language: TargetLanguage) -> str:
        if target_language == TargetLanguage.JAVA:
            return "com.modernizer.migration"
        if target_language == TargetLanguage.CSHARP:
            return "GeneratedMigration.Services"
        return "generated_app"

    @staticmethod
    def _default_file_path(
        class_name: str,
        target_language: TargetLanguage,
        package_or_namespace: str,
    ) -> str:
        if target_language == TargetLanguage.JAVA:
            return f"src/main/java/{package_or_namespace.replace('.', '/')}/{class_name}.java"
        if target_language == TargetLanguage.CSHARP:
            return f"Services/{class_name}.cs"
        module_name = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
        return f"generated_app/{module_name}.py"

    @staticmethod
    def _default_model_file_path(
        class_name: str,
        target_language: TargetLanguage,
        package_or_namespace: str,
    ) -> str:
        if target_language == TargetLanguage.JAVA:
            return f"src/main/java/{package_or_namespace.replace('.', '/')}/model/{class_name}.java"
        if target_language == TargetLanguage.CSHARP:
            return f"Models/{class_name}.cs"
        module_name = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
        return f"generated_app/models/{module_name}.py"

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

    @staticmethod
    def _copybook_fields(raw_code: str) -> list[str]:
        fields = []
        normalized = re.sub(r"==\s*UT\s*==", "", raw_code or "", flags=re.IGNORECASE).replace("==", "")
        for match in re.finditer(
            r"^\s*\d{2}\s+([A-Z0-9-]+)\s+(?:PIC|PICTURE)\b",
            normalized,
            flags=re.IGNORECASE | re.MULTILINE,
        ):
            name = match.group(1).upper()
            if name != "FILLER":
                fields.append(name)
        return fields

    @staticmethod
    def _allow_deterministic_fallback() -> bool:
        return str(os.getenv("ALLOW_DETERMINISTIC_CODEGEN_FALLBACK", "") or "").lower() in {
            "1",
            "true",
            "yes",
        }

    def _is_local_mode(self) -> bool:
        mode = (
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or ""
        ).lower()
        return mode == "local" or str(self.llm_config.get("url") or "").rstrip("/").endswith("/v1")

    @staticmethod
    def _list_of_strings(value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]

        items: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                text = (
                    item.get("description")
                    or item.get("item_name")
                    or item.get("name")
                    or item.get("value")
                    or json.dumps(item, ensure_ascii=False)
                )
                text = str(text).strip()
            else:
                text = str(item).strip()
            if text:
                items.append(text)
        return items

    @staticmethod
    def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _trim_raw_code(raw_code: str, max_chars: int = 8000) -> str:
        raw_code = raw_code or ""
        if len(raw_code) <= max_chars:
            return raw_code

        head = raw_code[: max_chars // 2]
        tail = raw_code[-max_chars // 2 :]

        return (
            head
            + "\n\n... [TRUNCATED FOR PLANNING PROMPT] ...\n\n"
            + tail
        )

    @staticmethod
    def _trim_text(value: str, max_chars: int) -> str:
        text = str(value or "")
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n... [TRUNCATED FOR LOCAL MODEL CONTEXT] ..."

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
