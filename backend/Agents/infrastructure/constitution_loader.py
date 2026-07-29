import json
from pathlib import Path
from typing import Any, Dict

import yaml

from Agents.models.code_generation_models import TargetLanguage, TargetProfile


class ConstitutionLoader:
    """
    Loads target-language generation rules.

    This is intentionally small and stable.
    Future changes for Java/Python/C# standards should mostly happen in:
      backend/data/constitution/*.yml
    """

    PROFILE_FILES = {
        TargetLanguage.JAVA: "java-quarkus.yml",
        TargetLanguage.PYTHON: "python-fastapi.yml",
        TargetLanguage.CSHARP: "csharp-aspnet.yml",
    }

    def __init__(self, constitution_dir: str | Path | None = None):
        if constitution_dir is None:
            self.constitution_dir = self._default_constitution_dir()
        else:
            self.constitution_dir = Path(constitution_dir)

    @staticmethod
    def _default_constitution_dir() -> Path:
        """
        Expected location:
          legacy-modernizer/backend/data/constitution
        """
        current = Path(__file__).resolve()
        backend_root = current.parents[2]
        return backend_root / "data" / "constitution"

    def load_profile(self, target_language: str | TargetLanguage) -> TargetProfile:
        target = self._normalize_target_language(target_language)
        profile_file = self.PROFILE_FILES[target]
        profile_path = self.constitution_dir / profile_file

        if not profile_path.exists():
            raise FileNotFoundError(
                f"Constitution profile not found for {target.value}: {profile_path}"
            )

        raw_text = profile_path.read_text(encoding="utf-8", errors="ignore")
        raw_profile = self._parse_yaml(raw_text)

        profile_block = raw_profile.get("profile", {}) if isinstance(raw_profile, dict) else {}

        return TargetProfile(
            id=str(profile_block.get("id") or profile_path.stem),
            target_language=target,
            framework=str(profile_block.get("framework") or self._default_framework(target)),
            constitution_text=raw_text,
            raw_profile=raw_profile,
        )

    def load_constitution_text(self, target_language: str | TargetLanguage) -> str:
        return self.load_profile(target_language).constitution_text

    def list_profiles(self) -> list[dict[str, Any]]:
        profiles = []

        for target_language in TargetLanguage:
            try:
                profile = self.load_profile(target_language)
                profiles.append({
                    "id": profile.id,
                    "target_language": profile.target_language.value,
                    "framework": profile.framework,
                })
            except FileNotFoundError:
                continue

        return profiles

    @staticmethod
    def _normalize_target_language(value: str | TargetLanguage) -> TargetLanguage:
        if isinstance(value, TargetLanguage):
            return value

        normalized = str(value or "").strip().lower()

        aliases = {
            "java": TargetLanguage.JAVA,
            "quarkus": TargetLanguage.JAVA,
            "python": TargetLanguage.PYTHON,
            "py": TargetLanguage.PYTHON,
            "fastapi": TargetLanguage.PYTHON,
            "c#": TargetLanguage.CSHARP,
            "csharp": TargetLanguage.CSHARP,
            "cs": TargetLanguage.CSHARP,
            ".net": TargetLanguage.CSHARP,
            "dotnet": TargetLanguage.CSHARP,
            "aspnet": TargetLanguage.CSHARP,
        }

        if normalized not in aliases:
            raise ValueError(
                f"Unsupported target language '{value}'. "
                "Supported values: java, python, csharp."
            )

        return aliases[normalized]

    @staticmethod
    def _default_framework(target: TargetLanguage) -> str:
        if target == TargetLanguage.JAVA:
            return "Quarkus"
        if target == TargetLanguage.PYTHON:
            return "FastAPI"
        if target == TargetLanguage.CSHARP:
            return "ASP.NET Core"
        return "Unknown"

    @staticmethod
    def _parse_yaml(raw_text: str) -> Dict[str, Any]:
        try:
            parsed = yaml.safe_load(raw_text) or {}
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        return {
            "raw": raw_text,
        }

    @staticmethod
    def to_prompt_block(profile: TargetProfile) -> str:
        return "\n".join([
            "## Target Generation Constitution",
            f"Profile ID: {profile.id}",
            f"Target Language: {profile.target_language.value}",
            f"Framework: {profile.framework}",
            "",
            profile.constitution_text,
        ])

    @staticmethod
    def to_json(profile: TargetProfile) -> str:
        if hasattr(profile, "model_dump"):
            return json.dumps(profile.model_dump(), indent=2)
        return json.dumps(profile.dict(), indent=2)