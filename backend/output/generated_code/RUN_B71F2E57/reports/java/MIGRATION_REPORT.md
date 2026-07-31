# Migration Report

**Run ID:** `RUN_B71F2E57`
**Project:** Run_4
**Target:** java / Quarkus

## Summary

- Source files: **83**
- Business rules: **98**
- Dependencies: **74**
- Conversion plans: **78**
- Generated files: **4**
- Validation: **Passed**
- Validation command: `static Java source validation (mvn not found)`
- Auto-fix: **Not run**

## Source Files

- `copybooks\CCHECKPD.CPY` (cobol, PENDING_CONFIRMATION)
- `copybooks\CCHECKWS.CPY` (cobol, PENDING_CONFIRMATION)
- `copybooks\DFHEIBLK.CPY` (cobol, PENDING_CONFIRMATION)
- `expected-output.txt` (pli, PENDING_CONFIRMATION)
- `Generator-java-save.txt` (cobol, PENDING_CONFIRMATION)
- `notice.txt` (text, PENDING_CONFIRMATION)
- `src\main\cobol\ALPHA.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\BIPM012.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\BADCOPY-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\BADCOPY.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\BIPM012I.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY001-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY001.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY002-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY002.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY003.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY004.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY005-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY005.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPY006.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPYP001-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPYP001.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPYP002-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPYP002.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPYR001-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\COPYR001.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EX002-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EX002.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EX005-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EX005.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EXP01-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EXP01.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EXR001-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\EXR001.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed003-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed003.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed004-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed004.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed005-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed005.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed006-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixed006.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixedex005-padded.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\mixedex005.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\Outrec\OUTREC.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\Outrec\OUTREC2.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\SQLCA.cpy` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\copy\TEXE2.cpy` (cobol-sql, PENDING_CONFIRMATION)
- `src\main\cobol\copy\TEXEM.cpy` (cobol-sql, PENDING_CONFIRMATION)
- `src\main\cobol\DB2PROG.cbl` (cobol-sql, PENDING_CONFIRMATION)
- `src\main\cobol\DPICNUMBERS.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\FileCopy.cbl` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\GREETING.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\LONGLINESANDNUMBERS.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\MOCK.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\MOCKPARA.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\MOCKTEST.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\NUMBERS.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\REPLAC.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\RETURNCODE.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\TESTNESTED.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\cobol\WS88LEVEL.CBL` (cobol, PENDING_CONFIRMATION)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKPARAGRAPHSPD.CPY` (cobol, PENDING_CONFIRMATION)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKRESULTPD.CPY` (cobol, PENDING_CONFIRMATION)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKWS.CPY` (cobol, PENDING_CONFIRMATION)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\DFHEIBLK.CPY` (cobol, PENDING_CONFIRMATION)
- `src\test\approvalTest\expected-output.txt` (pli, PENDING_CONFIRMATION)
- `testfiles\CALL-MOCK-AFTER.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\CICDEMO-AFTER.CBL` (cobol-cics, PENDING_CONFIRMATION)
- `testfiles\CONVERT-TEST-AFTER.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\FILE-MOCK-AFTER.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\INVDATE-AFTER.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\MINIMAL-AFTER.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\MINIMAL-BEFORE.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\PARA-MOCK-AFTER.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\REPLACE.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\REPLACE2.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\REPLACE3.CBL` (cobol, PENDING_CONFIRMATION)
- `testfiles\SUBPROG-AFTER.CBL` (cobol, PENDING_CONFIRMATION)
- `TESTPRG.CBL` (cobol, PENDING_CONFIRMATION)
- `vs-code-extension\Cobol-check\ParserErrorLog.txt` (text, PENDING_CONFIRMATION)
- `vs-code-extension\Cobol-check\src\main\cobol\ALPHA.CBL` (cobol, PENDING_CONFIRMATION)
- `vs-code-extension\Cobol-check\src\main\cobol\NUMBERS.CBL` (cobol, PENDING_CONFIRMATION)

## Generated Files

- `generation_manifest.json` (343 bytes)
- `pom.xml` (2200 bytes)
- `README.md` (160 bytes)
- `src/main/java/com/modernizer/migration/CcheckpdService.java` (1124 bytes)

## Conversion Plans

### mixed006-padded.CBL

Deterministic conversion plan for mixed006-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed006PaddedService` → `src/main/java/com/modernizer/migration/Mixed006PaddedService.java` (service)

### mixed006.CBL

Deterministic conversion plan for mixed006.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed006Service` → `src/main/java/com/modernizer/migration/Mixed006Service.java` (service)

### mixedex005-padded.CBL

Deterministic conversion plan for mixedex005-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixedex005PaddedService` → `src/main/java/com/modernizer/migration/Mixedex005PaddedService.java` (service)

### mixedex005.CBL

Deterministic conversion plan for mixedex005.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixedex005Service` → `src/main/java/com/modernizer/migration/Mixedex005Service.java` (service)

### OUTREC.CBL

Deterministic conversion plan for OUTREC.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `OutrecService` → `src/main/java/com/modernizer/migration/OutrecService.java` (service)

### OUTREC2.CBL

Deterministic conversion plan for OUTREC2.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Outrec2Service` → `src/main/java/com/modernizer/migration/Outrec2Service.java` (service)

### SQLCA.cpy

Deterministic conversion plan for SQLCA.cpy. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `SqlcaService` → `src/main/java/com/modernizer/migration/SqlcaService.java` (service)

### TEXE2.cpy

Deterministic conversion plan for TEXE2.cpy. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Texe2Service` → `src/main/java/com/modernizer/migration/Texe2Service.java` (service)

### TEXEM.cpy

Deterministic conversion plan for TEXEM.cpy. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `TexemService` → `src/main/java/com/modernizer/migration/TexemService.java` (service)

### DB2PROG.cbl

Deterministic conversion plan for DB2PROG.cbl. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Db2progService` → `src/main/java/com/modernizer/migration/Db2progService.java` (service)

### DPICNUMBERS.CBL

Deterministic conversion plan for DPICNUMBERS.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `DpicnumbersService` → `src/main/java/com/modernizer/migration/DpicnumbersService.java` (service)

### FileCopy.cbl

Deterministic conversion plan for FileCopy.cbl. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `FilecopyService` → `src/main/java/com/modernizer/migration/FilecopyService.java` (service)

### GREETING.CBL

Deterministic conversion plan for GREETING.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `GreetingService` → `src/main/java/com/modernizer/migration/GreetingService.java` (service)

### LONGLINESANDNUMBERS.CBL

Deterministic conversion plan for LONGLINESANDNUMBERS.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `LonglinesandnumbersService` → `src/main/java/com/modernizer/migration/LonglinesandnumbersService.java` (service)

### MOCK.CBL

Deterministic conversion plan for MOCK.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `MockService` → `src/main/java/com/modernizer/migration/MockService.java` (service)

### MOCKPARA.CBL

Deterministic conversion plan for MOCKPARA.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `MockparaService` → `src/main/java/com/modernizer/migration/MockparaService.java` (service)

### MOCKTEST.CBL

Deterministic conversion plan for MOCKTEST.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `MocktestService` → `src/main/java/com/modernizer/migration/MocktestService.java` (service)

### NUMBERS.CBL

Deterministic conversion plan for NUMBERS.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `NumbersService` → `src/main/java/com/modernizer/migration/NumbersService.java` (service)

### REPLAC.CBL

Deterministic conversion plan for REPLAC.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `ReplacService` → `src/main/java/com/modernizer/migration/ReplacService.java` (service)

### RETURNCODE.CBL

Deterministic conversion plan for RETURNCODE.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `ReturncodeService` → `src/main/java/com/modernizer/migration/ReturncodeService.java` (service)

### TESTNESTED.CBL

Deterministic conversion plan for TESTNESTED.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `TestnestedService` → `src/main/java/com/modernizer/migration/TestnestedService.java` (service)

### WS88LEVEL.CBL

Deterministic conversion plan for WS88LEVEL.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Ws88levelService` → `src/main/java/com/modernizer/migration/Ws88levelService.java` (service)

### CCHECKPARAGRAPHSPD.CPY

Deterministic conversion plan for CCHECKPARAGRAPHSPD.CPY. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `CcheckparagraphspdService` → `src/main/java/com/modernizer/migration/CcheckparagraphspdService.java` (service)

### CCHECKRESULTPD.CPY

Deterministic conversion plan for CCHECKRESULTPD.CPY. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `CcheckresultpdService` → `src/main/java/com/modernizer/migration/CcheckresultpdService.java` (service)

### CCHECKWS.CPY

Deterministic conversion plan for CCHECKWS.CPY. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `CcheckwsService` → `src/main/java/com/modernizer/migration/CcheckwsService.java` (service)

### DFHEIBLK.CPY

Deterministic conversion plan for DFHEIBLK.CPY. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `DfheiblkService` → `src/main/java/com/modernizer/migration/DfheiblkService.java` (service)

### CALL-MOCK-AFTER.CBL

Deterministic conversion plan for CALL-MOCK-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `CallMockAfterService` → `src/main/java/com/modernizer/migration/CallMockAfterService.java` (service)

### CICDEMO-AFTER.CBL

Deterministic conversion plan for CICDEMO-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `CicdemoAfterService` → `src/main/java/com/modernizer/migration/CicdemoAfterService.java` (service)

### CONVERT-TEST-AFTER.CBL

Deterministic conversion plan for CONVERT-TEST-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `ConvertTestAfterService` → `src/main/java/com/modernizer/migration/ConvertTestAfterService.java` (service)

### FILE-MOCK-AFTER.CBL

Deterministic conversion plan for FILE-MOCK-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `FileMockAfterService` → `src/main/java/com/modernizer/migration/FileMockAfterService.java` (service)

### INVDATE-AFTER.CBL

Deterministic conversion plan for INVDATE-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `InvdateAfterService` → `src/main/java/com/modernizer/migration/InvdateAfterService.java` (service)

### MINIMAL-AFTER.CBL

Deterministic conversion plan for MINIMAL-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `MinimalAfterService` → `src/main/java/com/modernizer/migration/MinimalAfterService.java` (service)

### MINIMAL-BEFORE.CBL

Deterministic conversion plan for MINIMAL-BEFORE.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `MinimalBeforeService` → `src/main/java/com/modernizer/migration/MinimalBeforeService.java` (service)

### PARA-MOCK-AFTER.CBL

Deterministic conversion plan for PARA-MOCK-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `ParaMockAfterService` → `src/main/java/com/modernizer/migration/ParaMockAfterService.java` (service)

### REPLACE.CBL

Deterministic conversion plan for REPLACE.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `ReplaceService` → `src/main/java/com/modernizer/migration/ReplaceService.java` (service)

### REPLACE2.CBL

Deterministic conversion plan for REPLACE2.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Replace2Service` → `src/main/java/com/modernizer/migration/Replace2Service.java` (service)

### REPLACE3.CBL

Deterministic conversion plan for REPLACE3.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Replace3Service` → `src/main/java/com/modernizer/migration/Replace3Service.java` (service)

### SUBPROG-AFTER.CBL

Deterministic conversion plan for SUBPROG-AFTER.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `SubprogAfterService` → `src/main/java/com/modernizer/migration/SubprogAfterService.java` (service)

### TESTPRG.CBL

Deterministic conversion plan for TESTPRG.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `TestprgService` → `src/main/java/com/modernizer/migration/TestprgService.java` (service)

### ALPHA.CBL

Deterministic conversion plan for ALPHA.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `AlphaService` → `src/main/java/com/modernizer/migration/AlphaService.java` (service)

### NUMBERS.CBL

Deterministic conversion plan for NUMBERS.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `NumbersService` → `src/main/java/com/modernizer/migration/NumbersService.java` (service)

### CCHECKPD.CPY

Deterministic conversion plan for CCHECKPD.CPY. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `CcheckpdService` → `src/main/java/com/modernizer/migration/CcheckpdService.java` (service)

### CCHECKWS.CPY

Deterministic conversion plan for CCHECKWS.CPY. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `CcheckwsService` → `src/main/java/com/modernizer/migration/CcheckwsService.java` (service)

### DFHEIBLK.CPY

Deterministic conversion plan for DFHEIBLK.CPY. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `DfheiblkService` → `src/main/java/com/modernizer/migration/DfheiblkService.java` (service)

### ALPHA.CBL

Deterministic conversion plan for ALPHA.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `AlphaService` → `src/main/java/com/modernizer/migration/AlphaService.java` (service)

### BIPM012.CBL

Deterministic conversion plan for BIPM012.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Bipm012Service` → `src/main/java/com/modernizer/migration/Bipm012Service.java` (service)

### BADCOPY-padded.CBL

Deterministic conversion plan for BADCOPY-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `BadcopyPaddedService` → `src/main/java/com/modernizer/migration/BadcopyPaddedService.java` (service)

### BADCOPY.CBL

Deterministic conversion plan for BADCOPY.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `BadcopyService` → `src/main/java/com/modernizer/migration/BadcopyService.java` (service)

### BIPM012I.CBL

Deterministic conversion plan for BIPM012I.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Bipm012iService` → `src/main/java/com/modernizer/migration/Bipm012iService.java` (service)

### COPY001-padded.CBL

Deterministic conversion plan for COPY001-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy001PaddedService` → `src/main/java/com/modernizer/migration/Copy001PaddedService.java` (service)

### COPY001.CBL

Deterministic conversion plan for COPY001.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy001Service` → `src/main/java/com/modernizer/migration/Copy001Service.java` (service)

### COPY002-padded.CBL

Deterministic conversion plan for COPY002-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy002PaddedService` → `src/main/java/com/modernizer/migration/Copy002PaddedService.java` (service)

### COPY002.CBL

Deterministic conversion plan for COPY002.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy002Service` → `src/main/java/com/modernizer/migration/Copy002Service.java` (service)

### COPY003.CBL

Deterministic conversion plan for COPY003.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy003Service` → `src/main/java/com/modernizer/migration/Copy003Service.java` (service)

### COPY004.CBL

Deterministic conversion plan for COPY004.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy004Service` → `src/main/java/com/modernizer/migration/Copy004Service.java` (service)

### COPY005-padded.CBL

Deterministic conversion plan for COPY005-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy005PaddedService` → `src/main/java/com/modernizer/migration/Copy005PaddedService.java` (service)

### COPY005.CBL

Deterministic conversion plan for COPY005.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy005Service` → `src/main/java/com/modernizer/migration/Copy005Service.java` (service)

### COPY006.CBL

Deterministic conversion plan for COPY006.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copy006Service` → `src/main/java/com/modernizer/migration/Copy006Service.java` (service)

### COPYP001-padded.CBL

Deterministic conversion plan for COPYP001-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copyp001PaddedService` → `src/main/java/com/modernizer/migration/Copyp001PaddedService.java` (service)

### COPYP001.CBL

Deterministic conversion plan for COPYP001.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copyp001Service` → `src/main/java/com/modernizer/migration/Copyp001Service.java` (service)

### COPYP002-padded.CBL

Deterministic conversion plan for COPYP002-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copyp002PaddedService` → `src/main/java/com/modernizer/migration/Copyp002PaddedService.java` (service)

### COPYP002.CBL

Deterministic conversion plan for COPYP002.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copyp002Service` → `src/main/java/com/modernizer/migration/Copyp002Service.java` (service)

### COPYR001-padded.CBL

Deterministic conversion plan for COPYR001-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copyr001PaddedService` → `src/main/java/com/modernizer/migration/Copyr001PaddedService.java` (service)

### COPYR001.CBL

Deterministic conversion plan for COPYR001.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Copyr001Service` → `src/main/java/com/modernizer/migration/Copyr001Service.java` (service)

### EX002-padded.CBL

Deterministic conversion plan for EX002-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Ex002PaddedService` → `src/main/java/com/modernizer/migration/Ex002PaddedService.java` (service)

### EX002.CBL

Deterministic conversion plan for EX002.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Ex002Service` → `src/main/java/com/modernizer/migration/Ex002Service.java` (service)

### EX005-padded.CBL

Deterministic conversion plan for EX005-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Ex005PaddedService` → `src/main/java/com/modernizer/migration/Ex005PaddedService.java` (service)

### EX005.CBL

Deterministic conversion plan for EX005.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Ex005Service` → `src/main/java/com/modernizer/migration/Ex005Service.java` (service)

### EXP01-padded.CBL

Deterministic conversion plan for EXP01-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Exp01PaddedService` → `src/main/java/com/modernizer/migration/Exp01PaddedService.java` (service)

### EXP01.CBL

Deterministic conversion plan for EXP01.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Exp01Service` → `src/main/java/com/modernizer/migration/Exp01Service.java` (service)

### EXR001-padded.CBL

Deterministic conversion plan for EXR001-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Exr001PaddedService` → `src/main/java/com/modernizer/migration/Exr001PaddedService.java` (service)

### EXR001.CBL

Deterministic conversion plan for EXR001.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Exr001Service` → `src/main/java/com/modernizer/migration/Exr001Service.java` (service)

### mixed003-padded.CBL

Deterministic conversion plan for mixed003-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed003PaddedService` → `src/main/java/com/modernizer/migration/Mixed003PaddedService.java` (service)

### mixed003.CBL

Deterministic conversion plan for mixed003.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed003Service` → `src/main/java/com/modernizer/migration/Mixed003Service.java` (service)

### mixed004-padded.CBL

Deterministic conversion plan for mixed004-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed004PaddedService` → `src/main/java/com/modernizer/migration/Mixed004PaddedService.java` (service)

### mixed004.CBL

Deterministic conversion plan for mixed004.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed004Service` → `src/main/java/com/modernizer/migration/Mixed004Service.java` (service)

### mixed005-padded.CBL

Deterministic conversion plan for mixed005-padded.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed005PaddedService` → `src/main/java/com/modernizer/migration/Mixed005PaddedService.java` (service)

### mixed005.CBL

Deterministic conversion plan for mixed005.CBL. The source will be migrated as a service/data-definition component using extracted business rules and source evidence.

**Target classes:**
- `Mixed005Service` → `src/main/java/com/modernizer/migration/Mixed005Service.java` (service)

## Business Rules

- **BR-001** [PENDING]: If numeric comparison is active, the expected numeric result message must be shown to the business user or output channel.
- **BR-002** [PENDING]: If verification passed condition is active, the verification passed message must be shown to the business user or output channel.
- **BR-003** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-004** [PENDING]: The system must subtract the specified business amount from the target value to keep the resulting balance accurate.
- **BR-005** [PENDING]: The system must retrieve the required business record record before continuing the business process.
- **BR-006** [PENDING]: The system must access database information required to complete the business transaction.
- **BR-007** [PENDING]: The system must access database information required to complete the business transaction.
- **BR-008** [PENDING]: The system must access database information required to complete the business transaction.
- **BR-009** [PENDING]: If not output ok, the 9999 abort business step must be performed.
- **BR-010** [PENDING]: The system must retrieve the required business record record before continuing the business process.
- **BR-011** [PENDING]: The system must perform 5400 write output record as part of the business workflow.
- **BR-012** [PENDING]: The system must create or output the required business record record as part of the business process.
- **BR-013** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-014** [PENDING]: If message is greeting is active, the ws user name must be set to world.
- **BR-015** [PENDING]: If ws friend is equal to spaces, the ws user name must be set to world.
- **BR-016** [PENDING]: If message is farewell is active, the ws user name must be set to alligator !.
- **BR-017** [PENDING]: If ws friend is equal to spaces, the ws user name must be set to alligator !.
- **BR-018** [PENDING]: The system must capture the required business record input before processing can continue.
- **BR-019** [PENDING]: If message is greeting is active, the ws user name must be set to world.
- **BR-020** [PENDING]: If ws friend is equal to spaces, the ws user name must be set to world.
- **BR-021** [PENDING]: If message is farewell is active, the ws user name must be set to alligator !.
- **BR-022** [PENDING]: If ws friend is equal to spaces, the ws user name must be set to alligator !.
- **BR-023** [PENDING]: If message is farewell long is active, the ws user name long must be set to : text :.
- **BR-024** [PENDING]: If ws friend is equal to spaces, the ws user name long must be set to : text :.
- **BR-025** [PENDING]: The system must capture the required business record input before processing can continue.
- **BR-026** [PENDING]: The system must invoke prog1 to complete the required supporting business operation.
- **BR-027** [PENDING]: The system must invoke mycobol' using action param , to complete the required supporting business operation.
- **BR-028** [PENDING]: The system must invoke value 2 using value 1 to complete the required supporting business operation.
- **BR-029** [PENDING]: The system must invoke value 2 to complete the required supporting business operation.
- **BR-030** [PENDING]: The system must invoke prog3' using to complete the required supporting business operation.
- **BR-031** [PENDING]: The system must invoke prog3' using value 1 to complete the required supporting business operation.
- **BR-032** [PENDING]: The system must calculate numeric 3 using the defined legacy formula before the result is used downstream.
- **BR-033** [PENDING]: The system must invoke prog1 to complete the required supporting business operation.
- **BR-034** [PENDING]: The system must invoke mycobol' using action value , to complete the required supporting business operation.
- **BR-035** [PENDING]: The system must invoke value 2 using value 1 to complete the required supporting business operation.
- **BR-036** [PENDING]: The system must invoke value 2 to complete the required supporting business operation.
- **BR-037** [PENDING]: The system must invoke prog3' using to complete the required supporting business operation.
- **BR-038** [PENDING]: The system must invoke prog3' using value 1 to complete the required supporting business operation.
- **BR-039** [PENDING]: The system must invoke program' using value 1 to complete the required supporting business operation.
- **BR-040** [PENDING]: The system must invoke program2' using value 1 to complete the required supporting business operation.
- **BR-041** [PENDING]: If message is greeting is active, the ws user name must be set to world.
- **BR-042** [PENDING]: If ws friend is equal to spaces, the ws user name must be set to world.
- **BR-043** [PENDING]: If message is farewell is active, the ws user name must be set to alligator !.
- **BR-044** [PENDING]: If ws friend is equal to spaces, the ws user name must be set to alligator !.
- **BR-045** [PENDING]: The system must capture the required business record input before processing can continue.
- **BR-046** [PENDING]: The system must invoke prog1 to complete the required supporting business operation.
- **BR-047** [PENDING]: If numeric comparison is active, the expected numeric result message must be shown to the business user or output channel.
- **BR-048** [PENDING]: If numeric comparison is active, the was actual numeric message must be shown to the business user or output channel.
- **BR-049** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-050** [PENDING]: The system must subtract the specified business amount from the target value to keep the resulting balance accurate.
- **BR-051** [PENDING]: The system must invoke statement mocks to complete the required supporting business operation.
- **BR-052** [PENDING]: The system must invoke statement to complete the required supporting business operation.
- **BR-053** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-054** [PENDING]: The system must invoke to dynamic subprogram to complete the required supporting business operation.
- **BR-055** [PENDING]: If ut mock found is active, the ut assert accesses business step must be performed.
- **BR-056** [PENDING]: The system must retrieve the required business record record before continuing the business process.
- **BR-057** [PENDING]: The system must perform 0100 read dataset as part of the business workflow.
- **BR-058** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-059** [PENDING]: The system must create or output the required business record record as part of the business process.
- **BR-060** [PENDING]: The system must perform 0200 write dataset as part of the business workflow.
- **BR-061** [PENDING]: If expected result filename is equal to spaces, the expected usage : convert result filename result message must be shown to the business user or output channel.
- **BR-062** [PENDING]: If test fail is active, the test status message must be shown to the business user or output channel.
- **BR-063** [PENDING]: The system must capture the required business record input before processing can continue.
- **BR-064** [PENDING]: The system must retrieve the required business record record before continuing the business process.
- **BR-065** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-066** [PENDING]: If ut mock found is active, the ut lookup file business step must be performed.
- **BR-067** [PENDING]: If ut mock found is active, the ut mock find filename must be marked as input file.
- **BR-068** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-069** [PENDING]: The system must perform 0200 read input file as part of the business workflow.
- **BR-070** [PENDING]: If ws remainder is zero, the ws current day must be set to 29.
- **BR-071** [PENDING]: The system must perform 2000 next invoice date as part of the business workflow.
- **BR-072** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-073** [PENDING]: The system must perform 1000 process invoices as part of the business workflow.
- **BR-074** [PENDING]: The system must divide the specified business values according to the legacy calculation rule while preserving decimal precision.
- **BR-075** [PENDING]: If ws message type is is equal to to 'greeting, the ws message must be set to hello , world !.
- **BR-076** [PENDING]: If ws message type is is equal to to 'farewell, the ws message must be set to see you later , alligator !.
- **BR-077** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-078** [PENDING]: If ws message type is is equal to to 'greeting, the ws message must be set to hello , world !.
- **BR-079** [PENDING]: If ws message type is is equal to to 'farewell, the ws message must be set to see you later , alligator !.
- **BR-080** [PENDING]: If ut mock found is active, the ut assert accesses business step must be performed.
- **BR-081** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-082** [PENDING]: The system must retrieve the required business record record before continuing the business process.
- **BR-083** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-084** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-085** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-086** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-087** [PENDING]: If ut comparison passed is active, the ut display passed business step must be performed.
- **BR-088** [PENDING]: If ut comparison numeric is active, the expected ut numeric result message must be shown to the business user or output channel.
- **BR-089** [PENDING]: If ut expected accesses is is equal to to 1, the ut label expected access pl must be set to spaces.
- **BR-090** [PENDING]: If ut verify passed is active, the ut verification passed message must be shown to the business user or output channel.
- **BR-091** [PENDING]: If message is greeting is active, the ws user name must be set to world.
- **BR-092** [PENDING]: If ws friend equals spaces is active, the ws user name must be set to world.
- **BR-093** [PENDING]: If message is farewell is active, the ws user name must be set to alligator !.
- **BR-094** [PENDING]: If ws friend equals spaces is active, the ws user name must be set to alligator !.
- **BR-095** [PENDING]: The system must add the specified business amount into the target total to keep accumulated values accurate.
- **BR-096** [PENDING]: The system must perform ut display passed as part of the business workflow.
- **BR-097** [PENDING]: The system must perform ut display failed as part of the business workflow.
- **BR-098** [PENDING]: The system must capture the required business record input before processing can continue.

## Dependencies

- `copybooks\CCHECKPD.CPY` --READS--> `LENGTH` (resolved)
- `copybooks\CCHECKPD.CPY` --READS--> `1` (resolved)
- `copybooks\CCHECKWS.CPY` --CALLS--> `VALUE` (resolved)
- `Generator-java-save.txt` --INCLUDES--> `statements` (resolved)
- `Generator-java-save.txt` --INCLUDES--> `statement` (resolved)
- `Generator-java-save.txt` --READS--> `original` (resolved)
- `Generator-java-save.txt` --READS--> `COPY` (resolved)
- `Generator-java-save.txt` --READS--> `copybooks` (resolved)
- `Generator-java-save.txt` --READS--> `config.properties` (resolved)
- `Generator-java-save.txt` --READS--> `cobol-check` (resolved)
- `Generator-java-save.txt` --READS--> `the` (resolved)
- `src\main\cobol\copy\COPY002-padded.CBL` --CALLS--> `src\main\cobol\copy\COPY003.CBL` (resolved)
- `src\main\cobol\copy\COPY002-padded.CBL` --CALLS--> `src\main\cobol\copy\COPY004.CBL` (resolved)
- `src\main\cobol\copy\COPY002.CBL` --CALLS--> `src\main\cobol\copy\COPY003.CBL` (resolved)
- `src\main\cobol\copy\COPY002.CBL` --CALLS--> `src\main\cobol\copy\COPY004.CBL` (resolved)
- `src\main\cobol\copy\COPY005-padded.CBL` --CALLS--> `src\main\cobol\copy\COPY006.CBL` (resolved)
- `src\main\cobol\copy\COPY005.CBL` --CALLS--> `src\main\cobol\copy\COPY006.CBL` (resolved)
- `src\main\cobol\copy\COPY006.CBL` --CALLS--> `src\main\cobol\copy\COPY003.CBL` (resolved)
- `src\main\cobol\copy\COPY006.CBL` --CALLS--> `src\main\cobol\copy\COPY004.CBL` (resolved)
- `src\main\cobol\copy\mixed005-padded.CBL` --CALLS--> `src\main\cobol\copy\mixed006.CBL` (resolved)
- `src\main\cobol\copy\mixed005.CBL` --CALLS--> `src\main\cobol\copy\mixed006.CBL` (resolved)
- `src\main\cobol\copy\mixed006-padded.CBL` --CALLS--> `src\main\cobol\copy\mixed003.CBL` (resolved)
- `src\main\cobol\copy\mixed006-padded.CBL` --CALLS--> `src\main\cobol\copy\mixed004.CBL` (resolved)
- `src\main\cobol\copy\mixed006.CBL` --CALLS--> `src\main\cobol\copy\mixed003.CBL` (resolved)
- `src\main\cobol\copy\mixed006.CBL` --CALLS--> `src\main\cobol\copy\mixed004.CBL` (resolved)
- `src\main\cobol\copy\Outrec\OUTREC.CBL` --CALLS--> `src\main\cobol\copy\Outrec\OUTREC2.CBL` (resolved)
- `src\main\cobol\DB2PROG.cbl` --INCLUDES--> `src\main\cobol\copy\TEXEM.cpy` (resolved)
- `src\main\cobol\FileCopy.cbl` --CALLS--> `src\main\cobol\copy\Outrec\OUTREC.CBL` (resolved)
- `src\main\cobol\MOCK.CBL` --CALLS--> `PROG1` (resolved)
- `src\main\cobol\MOCK.CBL` --CALLS--> `MYCOBOL` (resolved)
- `src\main\cobol\MOCK.CBL` --CALLS--> `MOVE` (resolved)
- `src\main\cobol\MOCK.CBL` --CALLS--> `VALUE-2` (resolved)
- `src\main\cobol\MOCK.CBL` --CALLS--> `PROG3` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `PROG1` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `MYCOBOL` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `MOVE` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `VALUE-2` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `PROG3` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `PROGRAM` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `PROGRAM2` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `END-CALL` (resolved)
- `src\main\cobol\MOCKTEST.CBL` --CALLS--> `CALL` (resolved)
- `src\main\cobol\RETURNCODE.CBL` --CALLS--> `PROG1` (resolved)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKPARAGRAPHSPD.CPY` --READS--> `LENGTH` (resolved)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKPARAGRAPHSPD.CPY` --READS--> `1` (resolved)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKRESULTPD.CPY` --CALLS--> `TO` (resolved)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKWS.CPY` --CALLS--> `PIC` (resolved)
- `src\main\resources\org\openmainframeproject\cobolcheck\copybooks\CCHECKWS.CPY` --CALLS--> `VALUE` (resolved)
- `testfiles\CALL-MOCK-AFTER.CBL` --CALLS--> `STATEMENT` (resolved)
- `testfiles\CALL-MOCK-AFTER.CBL` --CALLS--> `ADD` (resolved)
- `testfiles\CALL-MOCK-AFTER.CBL` --CALLS--> `to` (resolved)
- `testfiles\CALL-MOCK-AFTER.CBL` --INCLUDES--> `ZUTZCWS` (resolved)
- `testfiles\CALL-MOCK-AFTER.CBL` --INCLUDES--> `ZUTZCPD` (resolved)
- `testfiles\CICDEMO-AFTER.CBL` --INCLUDES--> `ZUTZCWS` (resolved)
- `testfiles\CICDEMO-AFTER.CBL` --INCLUDES--> `copybooks\DFHEIBLK.CPY` (resolved)
- `testfiles\CICDEMO-AFTER.CBL` --INCLUDES--> `ZUTZCPD` (resolved)
- `testfiles\CONVERT-TEST-AFTER.CBL` --INCLUDES--> `OUTPUT` (resolved)
- `testfiles\CONVERT-TEST-AFTER.CBL` --READS--> `COMMAND-LINE` (resolved)
- `testfiles\FILE-MOCK-AFTER.CBL` --INCLUDES--> `ZUTZCWS` (resolved)
- `testfiles\FILE-MOCK-AFTER.CBL` --INCLUDES--> `ZUTZCPD` (resolved)
- `testfiles\INVDATE-AFTER.CBL` --INCLUDES--> `ZUTZCWS` (resolved)
- `testfiles\INVDATE-AFTER.CBL` --INCLUDES--> `DATETIME` (resolved)
- `testfiles\INVDATE-AFTER.CBL` --INCLUDES--> `ZUTZCPD` (resolved)
- `testfiles\MINIMAL-AFTER.CBL` --INCLUDES--> `ZUTZCWS` (resolved)
- `testfiles\MINIMAL-AFTER.CBL` --INCLUDES--> `ZUTZCPD` (resolved)
- `testfiles\PARA-MOCK-AFTER.CBL` --INCLUDES--> `ZUTZCWS` (resolved)
- `testfiles\PARA-MOCK-AFTER.CBL` --INCLUDES--> `ZUTZCPD` (resolved)
- `testfiles\REPLACE.CBL` --CALLS--> `MOVE` (resolved)
- `testfiles\REPLACE2.CBL` --CALLS--> `MOVE` (resolved)
- `testfiles\REPLACE3.CBL` --CALLS--> `MOVE` (resolved)
- `testfiles\SUBPROG-AFTER.CBL` --INCLUDES--> `ZUTZCWS` (resolved)
- `testfiles\SUBPROG-AFTER.CBL` --INCLUDES--> `ZUTZCPD` (resolved)
- `TESTPRG.CBL` --CALLS--> `VALUE` (resolved)
- `TESTPRG.CBL` --READS--> `1` (resolved)

## Risk Notes

- No unresolved dependency references were found in the generated report.

## Validation Output

```txt
Maven was not found on this machine, so the validator checked generated Java source structure, class names, packages, braces, and placeholder markers.
```

---
Generated by ModernizerAI.