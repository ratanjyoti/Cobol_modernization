import re


def to_camel_case(legacy_name: str) -> str:
    name = re.sub(r"^(WS-|LS-|T-|TCN-)", "", legacy_name or "", flags=re.IGNORECASE)
    parts = [part for part in re.split(r"[-_.\s]+", name.strip()) if part]
    if not parts:
        return "unnamed"
    camel = parts[0].lower() + "".join(part[:1].upper() + part[1:].lower() for part in parts[1:])
    camel = re.sub(r"[^A-Za-z0-9_]", "", camel) or "unnamed"
    if camel[0].isdigit():
        camel = f"method{camel[:1].upper()}{camel[1:]}"
    reserved = {"class", "int", "long", "short", "void", "static", "public", "private", "package"}
    return f"{camel}_" if camel.lower() in reserved else camel


def infer_target_type(pic_clause: str, target_language: str = "java") -> str:
    pic = (pic_clause or "").upper().replace(" ", "").rstrip(".")
    target = (target_language or "java").lower()

    if any(marker in pic for marker in ("V",)) or re.search(r"[9Z]\.[9Z]", pic):
        return "decimal" if target in {"c#", "csharp", "dotnet"} else "BigDecimal"
    if "X" in pic or "A" in pic:
        return "string" if target in {"c#", "csharp", "dotnet"} else "String"
    if "9" in pic or "S9" in pic:
        digits = _numeric_digits(pic)
        if digits <= 4:
            return "short"
        if digits <= 9:
            return "int"
        if digits <= 18:
            return "long"
        return "decimal" if target in {"c#", "csharp", "dotnet"} else "BigInteger"
    return "string" if target in {"c#", "csharp", "dotnet"} else "String"


def _numeric_digits(pic: str) -> int:
    total = 0
    for _symbol, count in re.findall(r"([9Z])\((\d+)\)", pic):
        total += int(count)
    remainder = re.sub(r"[9Z]\(\d+\)", "", pic)
    total += remainder.count("9") + remainder.count("Z")
    return total or 1
