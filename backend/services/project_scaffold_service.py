from pathlib import Path


class ProjectScaffoldService:
    """
    Creates minimal project scaffolds for generated code.

    Java   -> Quarkus Maven project files
    Python -> FastAPI project files
    C#     -> ASP.NET Core project files
    """

    def ensure_scaffold(self, project_dir: Path, target_language: str):
        target = (target_language or "java").lower().strip()
        project_dir.mkdir(parents=True, exist_ok=True)

        if target == "java":
            self._ensure_java_quarkus(project_dir)
            return

        if target == "python":
            self._ensure_python_fastapi(project_dir)
            return

        if target in {"csharp", "c#", "cs"}:
            self._ensure_csharp_aspnet(project_dir)
            return

        raise ValueError(f"Unsupported target language for scaffold: {target_language}")

    def _ensure_java_quarkus(self, project_dir: Path):
        pom_path = project_dir / "pom.xml"

        if not pom_path.exists():
            pom_path.write_text(
                """<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.modernizer</groupId>
  <artifactId>generated-migration</artifactId>
  <version>1.0.0-SNAPSHOT</version>
  <properties>
    <maven.compiler.release>21</maven.compiler.release>
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
      <artifactId>quarkus-rest</artifactId>
    </dependency>
    <dependency>
      <groupId>io.quarkus</groupId>
      <artifactId>quarkus-rest-jackson</artifactId>
    </dependency>
    <dependency>
      <groupId>io.quarkus</groupId>
      <artifactId>quarkus-arc</artifactId>
    </dependency>
    <dependency>
      <groupId>io.quarkus</groupId>
      <artifactId>quarkus-hibernate-validator</artifactId>
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
      <plugin>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.13.0</version>
        <configuration>
          <parameters>true</parameters>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
""",
                encoding="utf-8",
            )

        (project_dir / "src" / "main" / "java").mkdir(parents=True, exist_ok=True)
        (project_dir / "src" / "test" / "java").mkdir(parents=True, exist_ok=True)
        self._write_readme(
            project_dir,
            "Generated Java Quarkus Migration",
            "mvn compile",
        )

    def _ensure_python_fastapi(self, project_dir: Path):
        requirements = project_dir / "requirements.txt"
        if not requirements.exists():
            requirements.write_text("fastapi\nuvicorn\npydantic\npytest\n", encoding="utf-8")

        pyproject = project_dir / "pyproject.toml"
        if not pyproject.exists():
            pyproject.write_text(
                """[project]
name = "generated-migration"
version = "1.0.0"
description = "Generated migration project from legacy COBOL/Telon code"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
                encoding="utf-8",
            )

        app_dir = project_dir / "generated_app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "__init__.py").touch(exist_ok=True)

        main_file = app_dir / "main.py"
        if not main_file.exists():
            main_file.write_text(
                """from fastapi import FastAPI

app = FastAPI(title="Generated Migration API")


@app.get("/health")
def health():
    return {"status": "ok"}
""",
                encoding="utf-8",
            )

        (project_dir / "tests").mkdir(parents=True, exist_ok=True)
        self._write_readme(
            project_dir,
            "Generated Python FastAPI Migration",
            "python -m py_compile $(git ls-files '*.py')",
        )

    def _ensure_csharp_aspnet(self, project_dir: Path):
        csproj = project_dir / "GeneratedMigration.csproj"
        if not csproj.exists():
            csproj.write_text(
                """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
""",
                encoding="utf-8",
            )

        program = project_dir / "Program.cs"
        if not program.exists():
            program.write_text(
                """var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.Run();
""",
                encoding="utf-8",
            )

        (project_dir / "Controllers").mkdir(parents=True, exist_ok=True)
        (project_dir / "Services").mkdir(parents=True, exist_ok=True)
        (project_dir / "Models").mkdir(parents=True, exist_ok=True)
        self._write_readme(
            project_dir,
            "Generated C# ASP.NET Core Migration",
            "dotnet build",
        )

    def _write_readme(self, project_dir: Path, title: str, validate_command: str):
        readme = project_dir / "README.md"
        if readme.exists():
            return

        readme.write_text(
            f"""# {title}

This project was generated by ModernizerAI from legacy COBOL/Telon analysis.

## Validate

```bash
{validate_command}
```
""",
            encoding="utf-8",
        )
