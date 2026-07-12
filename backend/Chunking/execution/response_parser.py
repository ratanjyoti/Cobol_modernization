import json
import re


class ConversionResponseParser:
    SUMMARY_MARKER = re.compile(r"###\s*SUMMARY\s*###", re.I)
    CODE_MARKER = re.compile(r"###\s*CODE\s*###", re.I)

    @classmethod
    def parse(cls, response) -> dict:
        if isinstance(response, dict):
            return {
                "code": response.get("ConvertedCode") or response.get("converted_code") or response.get("code") or "",
                "summary": response.get("ChunkSummary") or response.get("summary") or "",
                "tokens": response.get("TokensUsed") or response.get("tokens") or 0,
            }

        text = str(response or "").strip()
        json_match = re.search(r"```json\s*(.*?)```", text, re.I | re.S)
        candidate = json_match.group(1).strip() if json_match else text
        try:
            parsed = json.loads(candidate)
            return cls.parse(parsed)
        except (TypeError, json.JSONDecodeError):
            pass

        if cls.SUMMARY_MARKER.search(text):
            parts = cls.SUMMARY_MARKER.split(text, maxsplit=1)
            code_part = cls.CODE_MARKER.sub("", parts[0]).strip()
            summary_part = parts[1].strip()
            return {"code": code_part, "summary": summary_part, "tokens": 0}

        return {"code": text, "summary": "No summary returned by converter.", "tokens": 0}
