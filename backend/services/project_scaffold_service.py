from pathlib import Path
from typing import Any


class ProjectScaffoldService:
    """
    Creates target-language project scaffolds.

    Java: Quarkus/Maven project
    Python: FastAPI project
    C#: ASP.NET Core project
    """

    def ensure_scaffold(
        self,
        project_dir: str | Path,
        target_language: str,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        root = Path(project_dir)
        root.mkdir(parents=True, exist_ok=True)

        if target == "java":
            return self._ensure_java_scaffold(root)

        if target == "python":
            return self._ensure_python_scaffold(root)

        if target == "csharp":
            return self._ensure_csharp_scaffold(root)

        raise ValueError(f"Unsupported target language: {target_language}")

    def _ensure_java_scaffold(self, root: Path) -> dict[str, Any]:
        created: list[str] = []

        dirs = [
            "src/main/java/com/modernizer/migration/programs",
            "src/main/java/com/modernizer/migration/services",
            "src/main/java/com/modernizer/migration/resources",
            "src/main/java/com/modernizer/migration/repositories",
            "src/main/java/com/modernizer/migration/models",
            "src/main/java/com/modernizer/migration/copybooks",
            "src/main/java/com/modernizer/migration/dto",
            "src/main/java/com/modernizer/migration/adapters",
            "src/main/java/com/modernizer/migration/batch",
            "src/main/java/com/modernizer/migration/exceptions",
            "src/test/java/com/modernizer/migration",
        ]

        for item in dirs:
            path = root / item
            path.mkdir(parents=True, exist_ok=True)
            created.append(path.as_posix())

        pom = root / "pom.xml"
        if not pom.exists():
            pom.write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.modernizer</groupId>
    <artifactId>generated-migration</artifactId>
    <version>1.0.0-SNAPSHOT</version>

    <properties>
        <maven.compiler.release>17</maven.compiler.release>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <quarkus.platform.group-id>io.quarkus.platform</quarkus.platform.group-id>
        <quarkus.platform.artifact-id>quarkus-bom</quarkus.platform.artifact-id>
        <quarkus.platform.version>3.15.1</quarkus.platform.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>${quarkus.platform.group-id}</groupId>
                <artifactId>${quarkus.platform.artifact-id}</artifactId>
                <version>${quarkus.platform.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <dependencies>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-arc</artifactId>
        </dependency>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-rest</artifactId>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>${quarkus.platform.group-id}</groupId>
                <artifactId>quarkus-maven-plugin</artifactId>
                <version>${quarkus.platform.version}</version>
                <extensions>true</extensions>
            </plugin>
        </plugins>
    </build>
</project>
""",
                encoding="utf-8",
            )
            created.append(pom.as_posix())

        readme = root / "README.md"
        if not readme.exists():
            readme.write_text(
                """# Generated Java Migration

This project contains Java/Quarkus code generated from COBOL/Telon source.

## Build

```bash
mvn compile
```

## Structure

```txt
src/main/java/com/modernizer/migration/
  programs/
  services/
  resources/
  repositories/
  models/
  copybooks/
  dto/
  adapters/
  batch/
  exceptions/
```
""",
                encoding="utf-8",
            )
            created.append(readme.as_posix())

        return {
            "target_language": "java",
            "framework": "Quarkus",
            "project_dir": str(root),
            "created": created,
        }

    def _ensure_python_scaffold(self, root: Path) -> dict[str, Any]:
        created: list[str] = []

        dirs = [
            "generated_app",
            "generated_app/programs",
            "generated_app/services",
            "generated_app/routers",
            "generated_app/repositories",
            "generated_app/models",
            "generated_app/copybooks",
            "generated_app/schemas",
            "generated_app/adapters",
            "generated_app/batch",
            "generated_app/exceptions",
            "tests",
        ]

        for item in dirs:
            path = root / item
            path.mkdir(parents=True, exist_ok=True)
            created.append(path.as_posix())

            init_file = path / "__init__.py"
            if item.startswith("generated_app") and not init_file.exists():
                init_file.write_text("", encoding="utf-8")
                created.append(init_file.as_posix())

        main_py = root / "generated_app" / "main.py"
        if not main_py.exists():
            main_py.write_text(
                """from fastapi import FastAPI

app = FastAPI(
    title="Generated Migration API",
    version="1.0.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
""",
                encoding="utf-8",
            )
            created.append(main_py.as_posix())

        requirements = root / "requirements.txt"
        if not requirements.exists():
            requirements.write_text(
                """fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
python-dotenv>=1.0.0
""",
                encoding="utf-8",
            )
            created.append(requirements.as_posix())

        pyproject = root / "pyproject.toml"
        if not pyproject.exists():
            pyproject.write_text(
                """[project]
name = "generated-migration"
version = "1.0.0"
description = "Generated Python/FastAPI migration from COBOL/Telon"
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
""",
                encoding="utf-8",
            )
            created.append(pyproject.as_posix())

        readme = root / "README.md"
        if not readme.exists():
            readme.write_text(
                """# Generated Python Migration

This project contains Python/FastAPI code generated from COBOL/Telon source.

## Validate

```bash
python -m compileall generated_app tests
```

## Run API

```bash
uvicorn generated_app.main:app --reload
```

## Structure

```txt
generated_app/
  programs/
  services/
  routers/
  repositories/
  models/
  copybooks/
  schemas/
  adapters/
  batch/
  exceptions/
```
""",
                encoding="utf-8",
            )
            created.append(readme.as_posix())

        return {
            "target_language": "python",
            "framework": "FastAPI",
            "project_dir": str(root),
            "created": created,
        }

    def _ensure_csharp_scaffold(self, root: Path) -> dict[str, Any]:
        created: list[str] = []

        dirs = [
            "Controllers",
            "Services",
            "Repositories",
            "Models",
            "DTOs",
            "Adapters",
            "Batch",
            "Exceptions",
            "Tests",
        ]

        for item in dirs:
            path = root / item
            path.mkdir(parents=True, exist_ok=True)
            created.append(path.as_posix())

        csproj = root / "GeneratedMigration.csproj"
        if not csproj.exists():
            csproj.write_text(
                """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>GeneratedMigration</RootNamespace>
  </PropertyGroup>
</Project>
""",
                encoding="utf-8",
            )
            created.append(csproj.as_posix())

        program_cs = root / "Program.cs"
        if not program_cs.exists():
            program_cs.write_text(
                """var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapControllers();

app.Run();
""",
                encoding="utf-8",
            )
            created.append(program_cs.as_posix())

        readme = root / "README.md"
        if not readme.exists():
            readme.write_text(
                """# Generated C# Migration

This project contains C# ASP.NET Core code generated from COBOL/Telon source.

## Build

```bash
dotnet build
```

## Run

```bash
dotnet run
```

## Structure

```txt
Controllers/
Services/
Repositories/
Models/
DTOs/
Adapters/
Batch/
Exceptions/
Tests/
```
""",
                encoding="utf-8",
            )
            created.append(readme.as_posix())

        return {
            "target_language": "csharp",
            "framework": "ASP.NET Core",
            "project_dir": str(root),
            "created": created,
        }

    @staticmethod
    def _normalize_target(target_language: str) -> str:
        value = str(target_language or "").lower().strip()

        if value in {"python", "py", "fastapi"}:
            return "python"

        if value in {"csharp", "c#", "cs", "dotnet"}:
            return "csharp"

        return "java"
