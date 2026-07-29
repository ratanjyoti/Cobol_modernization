from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from Processes.code_generation_process import CodeGenerationProcess
from Persistence.sqlite.session import get_db
from Processes.conversion_planning_process import ConversionPlanningProcess
from Processes.code_fix_process import CodeFixProcess
from services.migration_report_service import MigrationReportService
from services.symbol_registry_service import SymbolRegistryService

router = APIRouter(prefix="/code-generation", tags=["Code Generation"])

@router.post("/{run_id}/registry/finalize")
async def finalize_symbol_registry(
    run_id: str,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    try:
        service = SymbolRegistryService(db)
        return service.finalize_registry(
            run_id=run_id,
            target_language=target_language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{run_id}/registry")
async def get_symbol_registry(
    run_id: str,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    try:
        service = SymbolRegistryService(db)
        return service.get_registry(
            run_id=run_id,
            target_language=target_language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/{run_id}/plan")
async def create_conversion_plan(
    run_id: str,
    target_language: str = Query(default="java"),
    file_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        process = ConversionPlanningProcess(db)
        return process.create_plans(
            run_id=run_id,
            target_language=target_language,
            file_id=file_id,
            project_id=run_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{run_id}/plans")
async def list_conversion_plans(
    run_id: str,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    process = ConversionPlanningProcess(db)
    return process.list_plans(
        run_id=run_id,
        target_language=target_language,
    )

@router.post("/{run_id}/generate")
async def generate_code(
    run_id: str,
    target_language: str = Query(default="java"),
    file_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        process = CodeGenerationProcess(db)
        return process.generate(
            run_id=run_id,
            target_language=target_language,
            file_id=file_id,
            project_id=run_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{run_id}/files")
async def list_generated_files(
    run_id: str,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    process = CodeGenerationProcess(db)
    return process.list_generated_files(
        run_id=run_id,
        target_language=target_language,
    )


@router.get("/{run_id}/file")
async def read_generated_file(
    run_id: str,
    target_language: str = Query(default="java"),
    path: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        process = CodeGenerationProcess(db)
        return process.read_generated_file(
            run_id=run_id,
            target_language=target_language,
            path=path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{run_id}/download")
async def download_generated_project(
    run_id: str,
    target_language: str = Query(default="java"),
    require_valid: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    try:
        process = CodeGenerationProcess(db)
        zip_path = process.create_zip(
            run_id=run_id,
            target_language=target_language,
            require_valid=require_valid,
        )

        return FileResponse(
            path=str(zip_path),
            filename=zip_path.name,
            media_type="application/zip",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

@router.get("/{run_id}/plans/{file_id}")
async def get_conversion_plan(
    run_id: str,
    file_id: int,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    try:
        process = ConversionPlanningProcess(db)
        return process.get_plan(
            run_id=run_id,
            file_id=file_id,
            target_language=target_language,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.post("/{run_id}/validate")
async def validate_generated_project(
    run_id: str,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    try:
        process = CodeGenerationProcess(db)
        return process.validate_generated_project(
            run_id=run_id,
            target_language=target_language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/{run_id}/fix")
async def fix_generated_code(
    run_id: str,
    target_language: str = Query(default="java"),
    max_files: int = Query(default=3),
    db: Session = Depends(get_db),
):
    try:
        process = CodeFixProcess(db)
        return process.fix_latest_validation_errors(
            run_id=run_id,
            target_language=target_language,
            max_files=max_files,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/{run_id}/report")
async def generate_migration_report(
    run_id: str,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    try:
        service = MigrationReportService(db)
        return service.generate_report(
            run_id=run_id,
            target_language=target_language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{run_id}/report")
async def get_migration_report(
    run_id: str,
    target_language: str = Query(default="java"),
    db: Session = Depends(get_db),
):
    try:
        service = MigrationReportService(db)
        return service.read_markdown_report(
            run_id=run_id,
            target_language=target_language,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
