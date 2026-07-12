class ReasoningExhaustionError(RuntimeError):
    pass


class JavaConverterAgent:
    async def convert(self, content: str, context: dict):
        prompt = context.get("prompt") if isinstance(context, dict) else ""
        return {
            "ConvertedCode": "// Converter client is not configured.\n" + "// Source chunk preserved for review.\n" + content,
            "ChunkSummary": f"Prepared chunk {context.get('current_chunk_index', 0)} for conversion with structured context.",
            "TokensUsed": max(1, (len(content or "") + len(prompt or "")) // 4),
        }
