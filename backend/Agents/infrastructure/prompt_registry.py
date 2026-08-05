# Agents/infrastructure/prompt_registry.py
PROMPT_KEYS = {
    "business_logic": {
        "system": "business_logic_{lang}_system", # e.g. business_logic_cobol_system
        "user": "business_logic_user_template"
    },
    "code_generation": {
        "system": "code_gen_{lang}_system",
        "user": "code_gen_user_template"
    },
    "compile_fix": {
        "system": "compile_fix_system",
        "user": "compile_fix_user_template"
    },
    "planner": {
        "system": "planner_system",
        "user": "planner_user_template"
    },
    "tech_analyzer": {
        "system": "tech_analyzer_system",
        "user": "tech_analyzer_user_template"
    },
    "ddd": {
        "system": "ddd_discovery_system",
        "user": "ddd_discovery_user_template"
    }
}
