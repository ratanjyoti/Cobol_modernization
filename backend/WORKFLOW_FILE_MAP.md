# Workflow File Map

This map keeps workflow ownership compact. Prefer editing the owner files listed here before adding new files or moving logic. Preserve current routes, DB models, frontend calls, and API response shapes unless a workflow change truly requires it.

## 1. Initial Setup

Purpose:
Capture project settings such as source language, target language, LLM provider, model, and service configuration.

Files:
- `frontend/src/pages/InitialSetup.tsx` - UI for selecting project/language/model settings.
- `frontend/src/services/api.ts` - `ProjectAPI` calls for creating projects and reading/updating project config.
- `backend/source/routes/project.py` - routes for project creation, config updates, dashboard status, and service health.
- `backend/Persistence/sqlite/models.py` - `Project` model fields saved by setup.
- `backend/Config/llm_config.py` - default provider/model configuration.

Change here when:
- adding a setup field
- changing source or target language choices
- changing LLM provider settings

Do not change:
- business logic extractor files unless setup introduces extractor configuration

## 2. File Upload and Language Detection

Purpose:
Ingest uploaded files, ZIPs, folders, local repos, or GitHub sources; detect or correct source language; store source files and chunks.

Files:
- `frontend/src/pages/SourceFiles.tsx` - upload UI, language correction UI, and launch actions.
- `frontend/src/services/api.ts` - upload, list files, confirm language, launch, and relation calls.
- `backend/source/routes/discovery.py` - upload endpoints, language inference helpers, and discovery launch endpoints.
- `backend/Processes/discovery_process.py` - file scanning, chunk creation, complexity, and relation discovery orchestration.
- `backend/Chunking/core/language_detector.py` - compact source-language detection rules.
- `backend/Chunking/chunking_orchestrator.py` - chunking workflow owner.
- `backend/Chunking/dependency_scanner/dependency_manager.py` - scanner selection and `FileRelation` creation.
- `backend/Persistence/sqlite/models.py` - `ProjectFile`, `FileChunk`, `FileComplexity`, and `FileRelation` storage.

Change here when:
- adding a new upload source
- changing language detection or manual correction
- changing chunking or dependency scanning

Do not change:
- technical analyzer prompts unless YAML structure changes
- business logic prompts unless extraction behavior changes

## 3. Technical YAML Analysis

Purpose:
Generate structured technical YAML per chunk/file before business logic extraction and code generation.

Files:
- `backend/Processes/analysis_process.py` - chunk-level YAML and deep technical analysis orchestration.
- `backend/Agents/implementations/cobol_analyzer_agent.py` - technical YAML generation agent.
- `backend/Agents/implementations/technical_analyzer.py` - full-file technical analysis agent.
- `backend/Agents/prompts/analysis_prompts.py` - technical analysis prompt text.
- `backend/Agents/models/analysis_models.py` - analysis report models.
- `backend/source/routes/analysis.py` - API route for analysis/business-rule review compatibility.
- `backend/Persistence/sqlite/models.py` - `ChunkAnalysis`, `TechnicalAnalysis`, and `FileAnalysis` persistence.
- `frontend/src/pages/ReverseEngineering.tsx` - frontend view using technical/discovery output.
- `frontend/src/services/analysisPrefetch.ts` - frontend prefetch helper for discovery/analysis data.

Change here when:
- changing technical YAML structure
- improving analyzer prompts
- adding fields to technical reports

Do not change:
- business logic extraction files unless extraction must consume new YAML fields
- code generation prompts unless generator inputs change

## 4. Agentic Business Logic Extraction

Purpose:
Extract normalized business purpose, functional logic, rules, validations, calculations, data rules, transitions, dependencies, and unresolved items from technical YAML plus source code.

Files:
- `backend/Processes/logic_extraction_process.py` - process orchestration, DB loading, dependency context, and `BusinessRule` persistence.
- `backend/Agents/implementations/agentic_business_logic_extractor.py` - language-aware routing, LLM calls, JSON parsing, fallback, and normalization.
- `backend/Agents/prompts/business_logic_agentic_prompts.py` - COBOL, Telon, JCL, Copybook, SQL, Generic prompts, and common JSON schema.
- `backend/source/routes/business_rule_routes.py` - extract/list/update business rules API.
- `frontend/src/pages/BusinessLogic.tsx` - business rule review UI.
- `frontend/src/services/api.ts` - business rule API calls.
- `backend/Persistence/sqlite/models.py` - `BusinessRule` table.

Change here when:
- adding a source language to extraction
- changing business rule JSON schema
- improving prompt behavior
- changing fallback or persistence behavior

Do not change:
- technical analyzer files unless YAML evidence structure changes
- code generation files unless generated code consumes new business-rule fields
- separate per-language extractor files; keep language routing compact in `agentic_business_logic_extractor.py`

## 5. Dependency Graph

Purpose:
Store and display source-file relationships discovered during discovery, with optional Neo4j projection.

Files:
- `backend/Processes/graphing_process.py` - graph build orchestration.
- `backend/Persistence/neo4j/graph_service.py` - Neo4j persistence and query integration.
- `backend/Chunking/dependency_scanner/dependency_manager.py` - scanner orchestration and relation storage.
- `backend/Chunking/dependency_scanner/cobol_scanner.py` - compatibility export for the COBOL scanner.
- `backend/Chunking/dependency_scanner/interfaces/cobol_scanner.py` - actual COBOL dependency scanner rules.
- `backend/Persistence/sqlite/models.py` - `FileRelation` storage.
- `backend/source/routes/discovery.py` and `backend/source/routes/project.py` - graph, relation, and discovery-data API routes.
- `frontend/src/pages/DependencyGraph.tsx` - dependency graph UI.
- `frontend/src/pages/SystemDiscovery.tsx` and `frontend/src/pages/ReverseEngineering.tsx` - related discovery/analysis views.
- `frontend/src/services/api.ts` - relation and discovery-data calls.

Change here when:
- adding a relation type
- changing graph display fields
- changing Neo4j projection/query behavior
- improving dependency scanning

Do not change:
- business logic prompts unless relation context changes extraction behavior
- code generation prompts unless graph data becomes a generator input

## Program Flow / Procedural Logic Flow

Purpose:
Shows how a legacy program executes step by step.

Core files:
- `backend/Processes/procedural_flow_process.py`
  Owns DB loading, technical YAML/source loading, extraction loop, and JSON file persistence.

- `backend/Agents/implementations/procedural_flow_extractor.py`
  Owns procedural-flow prompt, LLM call, deterministic fallback, JSON parsing, and normalization.

Related files:
- `backend/source/routes/business_rule_routes.py`
  Exposes procedural flow API routes.

- `frontend/src/pages/BusinessLogic.tsx`
  Displays the Program Flow tab below Business Logic.

Change here when:
- adding a new procedural flow section
- changing entry point detection
- changing execution flow JSON shape
- changing how loops/branches/calls are displayed

Do not change:
- agentic business logic prompts unless business-rule extraction changes
- code generation files

## 6. Code Generation

Purpose:
Plan and generate target-language code for Java, Python, and C# using technical YAML, business rules, registry data, and target-language constitutions.

Files:
- `backend/source/routes/code_generation_routes.py` - code generation API endpoints.
- `backend/Processes/conversion_planning_process.py` - plan orchestration.
- `backend/Processes/code_generation_process.py` - generation, file listing, download, validation, and repair orchestration.
- `backend/Processes/full_code_generation_pipeline.py` - full multi-stage generation pipeline and status updates.
- `backend/Agents/implementations/conversion_planner_agent.py` - target-language conversion plan agent.
- `backend/Agents/implementations/code_generator_agent.py` - target-language code generation agent.
- `backend/Agents/implementations/compile_fix_agent.py` - compile/error fix agent.
- `backend/Agents/prompts/code_generation/*.md` - planning, generation, and compile-fix prompts.
- `backend/Agents/infrastructure/codegen_context_builder.py` - combines YAML, rules, relations, symbols, and registry context.
- `backend/Agents/infrastructure/constitution_loader.py` and `backend/data/constitution/*.yml` - target architecture rules.
- `backend/services/symbol_registry_service.py` - symbol registry construction.
- `backend/services/project_scaffold_service.py` - generated project scaffolding.
- `backend/services/migration_report_service.py` - migration report output.
- `frontend/src/pages/CodeGeneration.tsx` - generation UI.
- `frontend/src/services/codeGenerationApi.ts` - generation API client.

Change here when:
- adding a target language
- changing generated architecture or file layout
- changing conversion plan schema
- changing generation status/progress

Do not change:
- agentic business logic prompts unless business-rule inputs need different content
- upload/discovery routes unless generation requires new source metadata

## Agentic Code Conversion

Purpose:
Converts legacy files into the selected target language using target-language-specific conversion behavior.

Core files:
- `backend/Processes/code_generation_process.py`
  Owns generation orchestration, context loading, generated file writing, validation handoff, and ZIP creation.

- `backend/Agents/implementations/agentic_code_conversion_orchestrator.py`
  Owns target-language routing, Java/Python/C# conversion behavior, LLM calls, fallback, JSON parsing, and normalization.

- `backend/Agents/prompts/code_conversion_agentic_prompts.py`
  Owns Java/Python/C#/Generic conversion prompts and output JSON schema.

Related files:
- `backend/Processes/conversion_planning_process.py`
  Creates conversion plans before code conversion.

- `backend/Agents/implementations/conversion_planner_agent.py`
  LLM agent for creating conversion plans.

- `backend/services/plan_sanitizer_service.py`
  Cleans generated paths for Java/Python/C#.

- `backend/services/project_scaffold_service.py`
  Creates Java/Python/C# project scaffold.

- `backend/Processes/full_code_generation_pipeline.py`
  Runs full one-click code generation.

- `frontend/src/pages/CodeGeneration.tsx`
  Displays target-language code generation UI.

Change here when:
- adding a new target language
- changing Java/Python/C# output style
- changing generated file JSON schema
- changing fallback conversion behavior

Do not change:
- business logic extraction files unless business-rule schema changes
- procedural flow files unless program-flow schema changes

## 7. Validation / Quality Gate

Purpose:
Validate generated code, detect quality issues, repair generated methods, and support full-pipeline quality gates.

Files:
- `backend/services/code_validation_service.py` - generated project validation.
- `backend/services/generation_quality_service.py` - quality gate checks.
- `backend/services/method_quality_service.py` - generated method quality checks.
- `backend/services/plan_sanitizer_service.py` - backend plan/path sanitization.
- `backend/Processes/code_fix_process.py` - compile fix workflow.
- `backend/Processes/method_body_repair_process.py` - method repair process.
- `backend/Agents/implementations/compile_fix_agent.py` - compile fix agent.
- `backend/Agents/implementations/method_body_repair_agent.py` - method repair agent.
- `backend/Processes/full_code_generation_pipeline.py` - final quality-gate orchestration.
- `backend/source/routes/code_generation_routes.py` - validate, fix, full-run, and repair endpoints.
- `frontend/src/pages/CodeGeneration.tsx` - validation and repair controls/results.
- `frontend/src/services/codeGenerationApi.ts` - validation, fix, and repair calls.

Change here when:
- changing compile or quality criteria
- adding a target-language validator
- changing repair behavior
- changing quality-gate response details

Do not change:
- source-language analysis prompts unless validation needs new metadata
- business-rule persistence unless generated-code quality depends on new rule fields

## 8. Frontend Pages and API Service Files

Purpose:
Keep page-level UI in pages and HTTP calls in service files. Avoid hiding workflow behavior in shared components unless it is genuinely reused.

Files:
- `frontend/src/routes/AppRoutes.tsx` - page routing.
- `frontend/src/constants/navigation.ts` - navigation labels and route metadata.
- `frontend/src/services/api.ts` - project, discovery, upload, business rule, and LLM health APIs.
- `frontend/src/services/codeGenerationApi.ts` - code generation APIs.
- `frontend/src/services/analysisPrefetch.ts` - discovery/analysis cache warmup.
- `frontend/src/pages/InitialSetup.tsx` - setup UI.
- `frontend/src/pages/SourceFiles.tsx` - upload and language detection UI.
- `frontend/src/pages/BusinessLogic.tsx` - business rule review UI.
- `frontend/src/pages/SystemDiscovery.tsx`, `DependencyGraph.tsx`, `ReverseEngineering.tsx`, `DDDDiscovery.tsx` - discovery and analysis UIs.
- `frontend/src/pages/CodeGeneration.tsx` - code generation and quality UI.
- `frontend/src/pages/PromptStudio.tsx` - prompt editing UI.

Change here when:
- changing a page layout
- adding frontend calls for existing backend routes
- changing navigation
- changing user-facing workflow order

Do not change:
- backend process files for UI-only copy/layout changes
- backend DB models unless the API contract needs new persisted fields

## Shared Infrastructure and Persistence

Files:
- `backend/Persistence/sqlite/models.py` - SQLAlchemy DB models.
- `backend/Persistence/sqlite/session.py` - SQLite engine, schema migration helpers, indexes.
- `backend/Agents/infrastructure/chat_client_factory.py` - LLM client selection.
- `backend/Agents/infrastructure/llm_api_client.py` - local/OpenRouter client implementations.
- `backend/Agents/infrastructure/prompt_store.py` - prompt persistence for Prompt Studio.
- `backend/source/routes/llm_health.py` - LLM health checks.
- `backend/source/routes/prompt_routes.py` - prompt editing/reset APIs.

Change here when:
- adding DB columns
- changing LLM client/provider behavior
- changing Prompt Studio storage
- changing health-check behavior

Do not change unless necessary:
- DB response shapes used by existing frontend pages
- route paths consumed by `frontend/src/services/api.ts` or `frontend/src/services/codeGenerationApi.ts`
- generated output folders under `backend/output/`

## Compactness Rules

- Prefer 2-3 owner files per workflow area.
- Add comments/docstrings pointing to owner files before moving logic.
- Keep business logic extraction in exactly these core files:
  - `backend/Processes/logic_extraction_process.py`
  - `backend/Agents/implementations/agentic_business_logic_extractor.py`
  - `backend/Agents/prompts/business_logic_agentic_prompts.py`
- Keep prompt changes centralized under `backend/Agents/prompts/`.
- Keep process orchestration centralized under `backend/Processes/`.
- Keep API route shapes stable under `backend/source/routes/`.
- Keep DB persistence changes in `backend/Persistence/sqlite/models.py` and `backend/Persistence/sqlite/session.py`.
- Do not add per-language business logic extractor files unless the compact router file becomes genuinely unmaintainable.
