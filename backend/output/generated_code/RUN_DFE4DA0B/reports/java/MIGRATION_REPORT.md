# Migration Report

**Run ID:** `RUN_DFE4DA0B`
**Project:** Run_1
**Target:** java / Quarkus

## Summary

- Source files: **83**
- Business rules: **98**
- Dependencies: **74**
- Conversion plans: **77**
- Generated files: **99**
- Validation: **Failed**
- Validation command: `generation quality gate`
- Generation quality gate: **Failed**
  - Only 38 source file(s) were generated, but 77 conversion plan(s) exist.
  - Generated project is missing planned class files: mixed004-padded.cbl, src/main/java/com/modernizer/migration/AlphaException.java, src/main/java/com/modernizer/migration/BController.java, src/main/java/com/modernizer/migration/BDTO.java, src/main/java/com/modernizer/migration/BadCopyGroupItem.java, src/main/java/com/modernizer/migration/BetaService.java, src/main/java/com/modernizer/migration/Bipm012IModuleData.java, src/main/java/com/modernizer/migration/Bipm012Service.java, src/main/java/com/modernizer/migration/CModel.java, src/main/java/com/modernizer/migration/COPY003Item1.java, src/main/java/com/modernizer/migration/COPY003Item2.java, src/main/java/com/modernizer/migration/COPY004Item1.java, src/main/java/com/modernizer/migration/COPY004Item2.java, src/main/java/com/modernizer/migration/COPY006Item1.java, src/main/java/com/modernizer/migration/COPY006Item2.java, src/main/java/com/modernizer/migration/COPYR001-paddedController.java, src/main/java/com/modernizer/migration/COPYR001-paddedDomainB.java, src/main/java/com/modernizer/migration/COPYR001-paddedDomainC.java, src/main/java/com/modernizer/migration/COPYR001-paddedDtoB.java, src/main/java/com/modernizer/migration/COPYR001-paddedDtoC.java
  - Placeholder/stub generated code was rejected: src/main/java/com/modernizer/migration/AdapterStub.java, src/main/java/com/modernizer/migration/dto/Mixed005GroupItemDto.java
  - Generated methods contain comments but no executable implementation: src/main/java/com/modernizer/migration/AdapterStub.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaController.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaControllerTest.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaDomainModelTest.java (2 method(s)), src/main/java/com/modernizer/migration/AlphaDTOTest.java (2 method(s)), src/main/java/com/modernizer/migration/AlphaRepository.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaRepositoryTest.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaService.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaServiceTest.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaTable1Test.java (2 method(s)), src/main/java/com/modernizer/migration/AlphaTable2Test.java (2 method(s)), src/main/java/com/modernizer/migration/BadcopyGroupItemService.java (1 method(s)), src/main/java/com/modernizer/migration/CallMockAfterService.java (8 method(s)), src/main/java/com/modernizer/migration/ConvertTestAfterService.java (2 method(s)), src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareFiles.java (1 method(s)), src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareRecords.java (1 method(s)), src/main/java/com/modernizer/migration/Db2progRepository.java (5 method(s)), src/main/java/com/modernizer/migration/Db2progService.java (5 method(s)), src/main/java/com/modernizer/migration/DpicnumbersService/DpicnumbersService.java (1 method(s)), src/main/java/com/modernizer/migration/FileMockAfterController.java (5 method(s))
  - Locked method coverage is too low: 20/67 (30%).
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

- `generation_manifest.json` (22650 bytes)
- `pom.xml` (2200 bytes)
- `README.md` (160 bytes)
- `src/main/java/com/modernizer/migration/AdapterStub.java` (228 bytes)
- `src/main/java/com/modernizer/migration/AlphaController.java` (472 bytes)
- `src/main/java/com/modernizer/migration/AlphaControllerTest.java` (368 bytes)
- `src/main/java/com/modernizer/migration/AlphaDomainModel.java` (521 bytes)
- `src/main/java/com/modernizer/migration/AlphaDomainModelTest.java` (426 bytes)
- `src/main/java/com/modernizer/migration/AlphaDTO.java` (853 bytes)
- `src/main/java/com/modernizer/migration/AlphaDTOTest.java` (386 bytes)
- `src/main/java/com/modernizer/migration/AlphaRepository.java` (268 bytes)
- `src/main/java/com/modernizer/migration/AlphaRepositoryTest.java` (368 bytes)
- `src/main/java/com/modernizer/migration/AlphaService.java` (265 bytes)
- `src/main/java/com/modernizer/migration/AlphaServiceTest.java` (359 bytes)
- `src/main/java/com/modernizer/migration/AlphaTable1.java` (619 bytes)
- `src/main/java/com/modernizer/migration/AlphaTable1Test.java` (389 bytes)
- `src/main/java/com/modernizer/migration/AlphaTable2.java` (619 bytes)
- `src/main/java/com/modernizer/migration/AlphaTable2Test.java` (389 bytes)
- `src/main/java/com/modernizer/migration/BadcopyGroupItemService.java` (629 bytes)
- `src/main/java/com/modernizer/migration/CallMockAfterService.java` (947 bytes)
- `src/main/java/com/modernizer/migration/ConvertTestAfterService.java` (616 bytes)
- `src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareFiles.java` (400 bytes)
- `src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareRecords.java` (406 bytes)
- `src/main/java/com/modernizer/migration/ConvertTestAfterServiceInitialize.java` (382 bytes)
- `src/main/java/com/modernizer/migration/Copy003Item1.java` (484 bytes)
- `src/main/java/com/modernizer/migration/Copy003Item2.java` (484 bytes)
- `src/main/java/com/modernizer/migration/Copy004Item1.java` (484 bytes)
- `src/main/java/com/modernizer/migration/Copy004Item2.java` (484 bytes)
- `src/main/java/com/modernizer/migration/Copy006Item1.java` (485 bytes)
- `src/main/java/com/modernizer/migration/Copy006Item2.java` (485 bytes)
- `src/main/java/com/modernizer/migration/Db2progDomain.java` (653 bytes)
- `src/main/java/com/modernizer/migration/Db2progDTO.java` (650 bytes)
- `src/main/java/com/modernizer/migration/Db2progException.java` (170 bytes)
- `src/main/java/com/modernizer/migration/Db2progRepository.java` (887 bytes)
- `src/main/java/com/modernizer/migration/Db2progService.java` (881 bytes)
- `src/main/java/com/modernizer/migration/domain/CopyDomainModel.java` (298 bytes)
- `src/main/java/com/modernizer/migration/domain/service/ReturncodeService.java` (650 bytes)
- `src/main/java/com/modernizer/migration/DpicnumbersService/DpicnumbersService.java` (507 bytes)
- `src/main/java/com/modernizer/migration/dto/CopyDTO.java` (279 bytes)
- `src/main/java/com/modernizer/migration/dto/Mixed005GroupItemDto.java` (285 bytes)
- `src/main/java/com/modernizer/migration/exception/CopyException.java` (321 bytes)
- `src/main/java/com/modernizer/migration/FileMockAfterController.java` (784 bytes)
- `src/main/java/com/modernizer/migration/FileMockAfterDomain.java` (444 bytes)
- `src/main/java/com/modernizer/migration/FileMockAfterDTO.java` (441 bytes)
- `src/main/java/com/modernizer/migration/FileMockAfterException.java` (427 bytes)
- `src/main/java/com/modernizer/migration/FileMockAfterRepository.java` (632 bytes)
- `src/main/java/com/modernizer/migration/FileMockAfterService.java` (629 bytes)
- `src/main/java/com/modernizer/migration/greeting/GreetingController.java` (468 bytes)
- `src/main/java/com/modernizer/migration/greeting/GreetingDomain.java` (1406 bytes)
- `src/main/java/com/modernizer/migration/greeting/GreetingDTO.java` (1400 bytes)
- `src/main/java/com/modernizer/migration/greeting/GreetingException.java` (190 bytes)
- `src/main/java/com/modernizer/migration/greeting/GreetingRepository.java` (468 bytes)
- `src/main/java/com/modernizer/migration/greeting/GreetingService.java` (946 bytes)
- `src/main/java/com/modernizer/migration/Group1Item1.java` (419 bytes)
- `src/main/java/com/modernizer/migration/Group1Item1Item11.java` (460 bytes)
- `src/main/java/com/modernizer/migration/Group1Item1Item12.java` (460 bytes)
- `src/main/java/com/modernizer/migration/Group1Item2.java` (411 bytes)
- `src/main/java/com/modernizer/migration/Group1Item2Item21.java` (460 bytes)
- `src/main/java/com/modernizer/migration/Group1Item2Item22.java` (460 bytes)
- `src/main/java/com/modernizer/migration/MinimalAfterService.java` (806 bytes)
- `src/main/java/com/modernizer/migration/MinimalAfterServiceEnd.java` (356 bytes)
- `src/main/java/com/modernizer/migration/MinimalAfterServiceUtAfter.java` (364 bytes)
- `src/main/java/com/modernizer/migration/MinimalAfterServiceUtBefore.java` (367 bytes)
- `src/main/java/com/modernizer/migration/MinimalAfterServiceUtInitialize.java` (379 bytes)
- `src/main/java/com/modernizer/migration/MinimalBeforeService.java` (536 bytes)
- `src/main/java/com/modernizer/migration/Mixed003Item1.java` (385 bytes)
- `src/main/java/com/modernizer/migration/Mixed003Item2.java` (385 bytes)
- `src/main/java/com/modernizer/migration/Mixed004Item1.java` (495 bytes)
- `src/main/java/com/modernizer/migration/Mixed004Item2.java` (495 bytes)
- `src/main/java/com/modernizer/migration/Mixed006Item1.java` (553 bytes)
- `src/main/java/com/modernizer/migration/Mixed006Item2.java` (553 bytes)
- `src/main/java/com/modernizer/migration/model/Ccheckws.java` (9967 bytes)
- `src/main/java/com/modernizer/migration/model/Dfheiblk.java` (4413 bytes)
- `src/main/java/com/modernizer/migration/model/Sqlca.java` (3751 bytes)
- `src/main/java/com/modernizer/migration/model/Texe2.java` (995 bytes)
- `src/main/java/com/modernizer/migration/model/Texem.java` (775 bytes)
- `src/main/java/com/modernizer/migration/NewTextGroup1.java` (316 bytes)
- `src/main/java/com/modernizer/migration/NewTextItem11.java` (316 bytes)
- `src/main/java/com/modernizer/migration/NewTextItem12.java` (316 bytes)
- `src/main/java/com/modernizer/migration/NewTextItem21.java` (316 bytes)
- `src/main/java/com/modernizer/migration/NewTextItem22.java` (316 bytes)
- `src/main/java/com/modernizer/migration/OutField2Service.java` (479 bytes)
- `src/main/java/com/modernizer/migration/OutField3Service.java` (479 bytes)
- `src/main/java/com/modernizer/migration/OutrecDomainModel.java` (334 bytes)
- `src/main/java/com/modernizer/migration/OutrecDTO.java` (318 bytes)
- `src/main/java/com/modernizer/migration/OutrecRepository.java` (524 bytes)
- `src/main/java/com/modernizer/migration/OutrecService.java` (565 bytes)
- `src/main/java/com/modernizer/migration/Replace2Service.java` (489 bytes)
- `src/main/java/com/modernizer/migration/Replace3Service.java` (993 bytes)
- `src/main/java/com/modernizer/migration/repository/CopyRepository.java` (838 bytes)
- `src/main/java/com/modernizer/migration/service/CopyService.java` (986 bytes)
- `src/main/java/com/modernizer/migration/service/Mixed005GroupItemService.java` (414 bytes)
- `src/main/java/com/modernizer/migration/TestnestedService.java` (503 bytes)
- `src/main/java/com/modernizer/migration/TestSomeOtherStuff.java` (539 bytes)
- `src/main/java/com/modernizer/migration/UtGamma.java` (241 bytes)
- `src/main/java/com/modernizer/migration/UtMockAfterService.java` (606 bytes)
- `src/main/java/com/modernizer/migration/UtMockClassicCallService.java` (529 bytes)
- `src/main/java/com/modernizer/migration/UtMockDynamicCallService.java` (439 bytes)
- `src/main/java/com/modernizer/migration/UtOmega.java` (241 bytes)

## Conversion Plans

### CCHECKPD.CPY

Conversion Plan for CCHECKPD.CPY to Java Quarkus

**Target classes:**
- `CcheckpdService` → `CcheckpdService.java` (resource)
- `MockRecord` → `MockRecord.java` (resource)
- `MockFile` → `MockFile.java` (resource)
- `CcheckpdRepository` → `CcheckpdRepository.java` (repository)
- `CcheckpdDTO` → `CcheckpdDTO.java` (dto)
- `CcheckpdDomainModel` → `CcheckpdDomainModel.java` (domain)
- `CcheckpdException` → `CcheckpdException.java` (exception)

**Unresolved items:**
- External call to an adapter stub

### BADCOPY.CBL

Conversion Plan for BADCOPY.CBL to Java Quarkus

**Target classes:**
- `BadcopyGroupItemService` → `BadcopyGroupItemService.java` (service)

**Unresolved items:**
- Group item data structure
- Result of group item processing

### BIPM012I.CBL

Conversion Plan for BIPM012I.CBL to Java Quarkus

**Target classes:**
- `Bipm012IModuleData` → `Bipm012IModuleData.java` (resource)

**Unresolved items:**
- Input/output table for BIPM012I module data
- Input data for BIPM012I module
- Output data for BIPM012I module

### COPY001-padded.CBL

Conversion Plan for Java Quarkus Backend Service Generation

**Target classes:**
- `TestDataElement001A1Service` → `com/modernizer/migration/testDataElement001A1Service.java` (resource)
- `TestDataElement001A2Service` → `com/modernizer/migration/testDataElement001A2Service.java` (resource)
- `TestDataElement001B1Service` → `com/modernizer/migration/testDataElement001B1Service.java` (resource)
- `TestDataElement001B2Service` → `com/modernizer/migration/testDataElement001B2Service.java` (resource)

**Unresolved items:**
- Stub adapter for unresolved dependencies

### COPY001.CBL

Conversion Plan for Java Quarkus Backend Service

**Target classes:**
- `TestDataElement001A1Service` → `com/modernizer/migration/dataelement001a1service/TestDataElement001A1Service.java` (resource)
- `TestDataElement001B1Repository` → `com/modernizer/migration/dataelement001b1repository/TestDataElement001B1Repository.java` (repository)
- `TestDataElement001A2Service` → `com/modernizer/migration/dataelement001a2service/TestDataElement001A2Service.java` (service)
- `TestDataElement001B2Repository` → `com/modernizer/migration/dataelement001b2repository/TestDataElement001B2Repository.java` (repository)

### COPY002-padded.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `CopyService` → `src/main/java/com/modernizer/migration/service/CopyService.java` (service)
- `CopyRepository` → `src/main/java/com/modernizer/migration/repository/CopyRepository.java` (repository)
- `CopyDTO` → `src/main/java/com/modernizer/migration/dto/CopyDTO.java` (dto)
- `CopyDomainModel` → `src/main/java/com/modernizer/migration/domain/CopyDomainModel.java` (domain)
- `CopyException` → `src/main/java/com/modernizer/migration/exception/CopyException.java` (exception)

**Unresolved items:**
- adapter-stub

### COPY002.CBL

Conversion Plan for COPY002.CBL to Java Quarkus

**Target classes:**
- `Copy002Resource` → `src/main/java/com/modernizer/migration/resource/copy/Copy002Resource.java` (resource)

**Unresolved items:**
- COPY003.CBL
- COPY004.CBL

### COPY003.CBL

Conversion Plan for COPY003.CBL to Java Quarkus

**Target classes:**
- `Copy003Item1Service` → `com/modernizer/migration/Copy003Item1Service.java` (resource)
- `Copy003Item2Service` → `com/modernizer/migration/Copy003Item2Service.java` (resource)

### COPY004.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `Copy004Service` → `com/modernizer/migration/Copy004Service.java` (service)

**Unresolved items:**
- adapter-stub

### COPY005-padded.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `CopyService` → `src/main/java/com/modernizer/migration/service/CopyService.java` (service)

**Unresolved items:**
- {"item_type": "adapter-stub", "source_file": "src/main/cobol/adapter/COPY005-padded.CBL"}

### COPY005.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `CopyItemService` → `src/main/java/com/modernizer/migration/service/CopyItemService.java` (service)

**Unresolved items:**
- COPY006.CBL
- adapter-stub

### CCHECKWS.CPY

CCHECKWS.CPY is a data copybook and will be migrated as a shared model/DTO class.

**Target classes:**
- `Ccheckws` → `src/main/java/com/modernizer/migration/model/Ccheckws.java` (model)

### COPY006.CBL

Conversion Plan for COPY006.CBL to Java Quarkus

**Target classes:**
- `Copy006Item1` → `src/main/java/com/modernizer/migration/copy/Copy006Item1.java` (resource)
- `Copy006Item2` → `src/main/java/com/modernizer/migration/copy/Copy006Item2.java` (resource)

**Unresolved items:**
- COPY003
- COPY004

### COPYP001-padded.CBL

Conversion Plan for COPYP001-padded.CBL to Java Quarkus

**Target classes:**
- `CopyProcessor` → `com/modernizer/migration/CopyProcessor.java` (resource)

**Unresolved items:**
- Unresolved reference to item 1, line 1
- Unresolved reference to item 2, line 1

### COPYP001.CBL

Conversion Plan for COPYP001.CBL to Java Quarkus

**Target classes:**
- `CopyGroup1` → `com/modernizer/migration/CopyGroup1.java` (resource)
- `CopyItem1` → `com/modernizer/migration/CopyItem1.java` (service)

**Unresolved items:**
- ==XXX==-ITEM-1-1-1
- ==XXX==-ITEM-1-2-1

### COPYP002-padded.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `Group1Item1` → `com/modernizer/migration/Group1Item1.java` (resource)
- `Group1Item2` → `com/modernizer/migration/Group1Item2.java` (resource)

**Unresolved items:**
- adapter-stub

### COPYP002.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `Group1Item1` → `com/modernizer/migration/Group1Item1.java` (resource)
- `Group1Item1Item11` → `com/modernizer/migration/Group1Item1Item11.java` (resource)
- `Group1Item1Item12` → `com/modernizer/migration/Group1Item1Item12.java` (resource)
- `Group1Item2` → `com/modernizer/migration/Group1Item2.java` (resource)
- `Group1Item2Item21` → `com/modernizer/migration/Group1Item2Item21.java` (resource)
- `Group1Item2Item22` → `com/modernizer/migration/Group1Item2Item22.java` (resource)

**Unresolved items:**
- Stub adapter dependency

### COPYR001-padded.CBL

Conversion Plan for COPYR001-padded.CBL to Java Quarkus

**Target classes:**
- `BController` → `COPYR001-paddedController.java` (resource)
- `CService` → `COPYR001-paddedService.java` (service)
- `DRepository` → `COPYR001-paddedRepository.java` (repository)
- `DtoB` → `COPYR001-paddedDtoB.java` (dto)
- `DtoC` → `COPYR001-paddedDtoC.java` (dto)
- `DtoD` → `COPYR001-paddedDtoD.java` (dto)
- `DomainB` → `COPYR001-paddedDomainB.java` (domain)
- `DomainC` → `COPYR001-paddedDomainC.java` (domain)
- `ExceptionA` → `COPYR001-paddedExceptionA.java` (exception)
- `ExceptionC` → `COPYR001-paddedExceptionC.java` (exception)
- `ExceptionD` → `COPYR001-paddedExceptionD.java` (exception)

**Unresolved items:**
- Input from A. External call.
- Output from C. External call.
- Data access for D. External call.

### COPYR001.CBL

Conversion plan for COBOL to Java Quarkus backend service

**Target classes:**
- `BController` → `com/modernizer/migration/BController.java` (resource)
- `CService` → `com/modernizer/migration/CService.java` (service)
- `DRepository` → `com/modernizer/migration/DRepository.java` (repository)
- `BDTO` → `com/modernizer/migration/BDTO.java` (dto)
- `CModel` → `com/modernizer/migration/CModel.java` (domain)
- `DException` → `com/modernizer/migration/DException.java` (exception)

**Unresolved items:**
- Stub adapter for COBOL program D

### EX002-padded.CBL

Conversion plan for EX002-padded.CBL to Java Quarkus backend service

**Target classes:**
- `Copy003Item1` → `Copy003Item1.java` (resource)
- `Copy003Item2` → `Copy003Item2.java` (resource)
- `Copy004Item1` → `Copy004Item1.java` (resource)
- `Copy004Item2` → `Copy004Item2.java` (resource)
- `TestSomeOtherStuff` → `TestSomeOtherStuff.java` (resource)

**Unresolved items:**
- Unresolved dependency

### EX002.CBL

Conversion Plan for EX002.CBL to Java Quarkus

**Target classes:**
- `Copy003Item1` → `Copy003Item1.java` (resource)
- `Copy003Item2` → `Copy003Item2.java` (resource)
- `Copy004Item1` → `Copy004Item1.java` (resource)
- `Copy004Item2` → `Copy004Item2.java` (resource)
- `TestSomeOtherStuff` → `TestSomeOtherStuff.java` (resource)

**Unresolved items:**
- adapter-stub

### EX005-padded.CBL

Conversion Plan for EX005-padded.CBL to Java Quarkus

**Target classes:**
- `Copy003Item1` → `Copy003Item1.java` (resource)
- `Copy003Item2` → `Copy003Item2.java` (resource)
- `Copy004Item1` → `Copy004Item1.java` (resource)
- `Copy004Item2` → `Copy004Item2.java` (resource)
- `Copy006Item1` → `Copy006Item1.java` (resource)
- `Copy006Item2` → `Copy006Item2.java` (resource)

**Unresolved items:**
- adapter-stub

### DFHEIBLK.CPY

DFHEIBLK.CPY is a data copybook and will be migrated as a shared model/DTO class.

**Target classes:**
- `Dfheiblk` → `src/main/java/com/modernizer/migration/model/Dfheiblk.java` (model)

### EX005.CBL

Conversion Plan for EX005.CBL to Java Quarkus

**Target classes:**
- `Copy003Item1` → `COPY003Item1.java` (resource)
- `Copy003Item2` → `COPY003Item2.java` (resource)
- `Copy004Item1` → `COPY004Item1.java` (resource)
- `Copy004Item2` → `COPY004Item2.java` (resource)
- `Copy006Item1` → `COPY006Item1.java` (resource)
- `Copy006Item2` → `COPY006Item2.java` (resource)

**Unresolved items:**
- adapter-stub

### EXP01-padded.CBL

Conversion Plan for EXP01-padded.CBL to Java Quarkus

**Target classes:**
- `Exp01Service` → `com/modernizer/migration/Exp01Service.java` (resource|service)

**Unresolved items:**
- Adapter stub for external call

### EXP01.CBL

Conversion Plan for EXP01.CBL to Java Quarkus

**Target classes:**
- `NewTextGroup1` → `com/modernizer/migration/NewTextGroup1.java` (resource)
- `NewTextItem11` → `com/modernizer/migration/NewTextItem11.java` (resource)
- `NewTextItem12` → `com/modernizer/migration/NewTextItem12.java` (resource)
- `NewTextItem21` → `com/modernizer/migration/NewTextItem21.java` (resource)
- `NewTextItem22` → `com/modernizer/migration/NewTextItem22.java` (resource)

**Unresolved items:**
- adapter-stub

### EXR001-padded.CBL

Conversion Plan for EXR001-padded.CBL to Java Quarkus

**Target classes:**
- `AlphaService` → `AlphaService.java` (resource)
- `BetaService` → `BetaService.java` (service)
- `DeltaRepository` → `DeltaRepository.java` (repository)

**Unresolved items:**
- Stub adapter for external calls

### EXR001.CBL

Conversion Plan for EXR001.CBL to Java Quarkus

**Target classes:**
- `AlphaService` → `AlphaService.java` (resource)
- `BetaService` → `BetaService.java` (service)
- `DeltaRepository` → `DeltaRepository.java` (repository)

**Unresolved items:**
- Missing adapter implementation for DeltaRepository

### mixed003-padded.CBL

Conversion Plan for mixed003-padded.CBL to Java Quarkus

**Target classes:**
- `Mixed003Item1` → `mixed003-padded.java` (resource)
- `Mixed003Item2` → `mixed003-padded.java` (resource)

### mixed003.CBL

Conversion Plan for mixed003.CBL to Java Quarkus

**Target classes:**
- `Mixed003Item1` → `mixed003Item1.java` (resource)
- `Mixed003Item2` → `mixed003Item2.java` (resource)

**Unresolved items:**
- adapter-stub

### mixed004-padded.CBL

Conversion Plan for mixed004-padded.CBL to Java Quarkus

**Target classes:**
- `Mixed004Item1` → `mixed004-padded.cbl` (resource)
- `Mixed004Item2` → `mixed004-padded.cbl` (resource)

**Unresolved items:**
- adapter-stub

### mixed004.CBL

Conversion plan for mixed004.CBL to Java Quarkus backend service

**Target classes:**
- `Mixed004Item1` → `mixed004Item1.java` (resource)
- `Mixed004Item2` → `mixed004Item2.java` (resource)

**Unresolved items:**
- adapter-stub

### mixed005-padded.CBL

Conversion Plan for mixed005-padded.CBL to Java Quarkus

**Target classes:**
- `Mixed005GroupItemService` → `src/main/java/com/modernizer/migration/service/Mixed005GroupItemService.java` (service)

**Unresolved items:**
- mixed006.CBL

### mixed005.CBL

Conversion Plan for mixed005.CBL to Java Quarkus

**Target classes:**
- `Mixed005GroupItemService` → `src/main/java/com/modernizer/migration/mixed005/Mixed005GroupItemService.java` (service)

**Unresolved items:**
- mixed005GroupItemRepository
- mixed005GroupItemEntity

### mixed006-padded.CBL

Conversion Plan for mixed006-padded.CBL to Java Quarkus

**Target classes:**
- `Mixed006Item1` → `src/main/java/com/modernizer/migration/Mixed006Item1.java` (resource)
- `Mixed006Item2` → `src/main/java/com/modernizer/migration/Mixed006Item2.java` (resource)

**Unresolved items:**
- adapter-stub

### mixed006.CBL

Conversion Plan for mixed006.CBL to Java Quarkus

**Target classes:**
- `Mixed006Item1` → `src/main/java/com/modernizer/migration/mixed006/Mixed006Item1.java` (resource)
- `Mixed006Item2` → `src/main/java/com/modernizer/migration/mixed006/Mixed006Item2.java` (resource)

**Unresolved items:**
- MIXED006-Group-1
- MIXED006-Group-2

### mixedex005-padded.CBL

Conversion Plan for mixedex005-padded.CBL to Java Quarkus

**Target classes:**
- `Mixed003Item1` → `mixed003Item1.java` (resource)
- `Mixed003Item2` → `mixed003Item2.java` (resource)
- `Mixed004Item1` → `mixed004Item1.java` (resource)
- `Mixed004Item2` → `mixed004Item2.java` (resource)
- `Mixed006Item1` → `mixed006Item1.java` (resource)
- `Mixed006Item2` → `mixed006Item2.java` (resource)

**Unresolved items:**
- mixed005-Copy
- mixed006-Copy

### mixedex005.CBL

Conversion Plan for mixedex005.CBL to Java Quarkus

**Target classes:**
- `Mixed003Item1` → `mixed003Item1.java` (resource)
- `Mixed003Item2` → `mixed003Item2.java` (resource)
- `Mixed004Item1` → `mixed004Item1.java` (resource)
- `Mixed004Item2` → `mixed004Item2.java` (resource)
- `Mixed006Item1` → `mixed006Item1.java` (resource)
- `Mixed006Item2` → `mixed006Item2.java` (resource)

**Unresolved items:**
- mixed005GroupItem
- mixed006Group1
- mixed006Group2

### OUTREC.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `OutrecService` → `src/main/java/com/modernizer/migration/OutrecService.java` (resource)
- `OutrecRepository` → `src/main/java/com/modernizer/migration/OutrecRepository.java` (repository)
- `OutrecDTO` → `src/main/java/com/modernizer/migration/OutrecDTO.java` (dto)
- `OutrecDomainModel` → `src/main/java/com/modernizer/migration/OutrecDomainModel.java` (domain)

### OUTREC2.CBL

Convert COBOL to Java Quarkus backend service

**Target classes:**
- `OutField2Service` → `OutField2Service.java` (resource)
- `OutField3Service` → `OutField3Service.java` (resource)

**Unresolved items:**
- OutField2Repository
- OutField3Repository

### SQLCA.cpy

SQLCA.cpy is a data copybook and will be migrated as a shared model/DTO class.

**Target classes:**
- `Sqlca` → `src/main/java/com/modernizer/migration/model/Sqlca.java` (model)

### TEXE2.cpy

TEXE2.cpy is a data copybook and will be migrated as a shared model/DTO class.

**Target classes:**
- `Texe2` → `src/main/java/com/modernizer/migration/model/Texe2.java` (model)

### TEXEM.cpy

TEXEM.cpy is a data copybook and will be migrated as a shared model/DTO class.

**Target classes:**
- `Texem` → `src/main/java/com/modernizer/migration/model/Texem.java` (model)

### DB2PROG.cbl

Conversion plan for DB2PROG COBOL program to Java Quarkus backend service

**Target classes:**
- `Db2progService` → `src/main/java/com/modernizer/migration/Db2progService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `Db2progRepository` → `src/main/java/com/modernizer/migration/Db2progRepository.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `Db2progDTO` → `src/main/java/com/modernizer/migration/Db2progDTO.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `Db2progDomain` → `src/main/java/com/modernizer/migration/Db2progDomain.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `Db2progException` → `src/main/java/com/modernizer/migration/Db2progException.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- Cursor for DB2 instructions
- SQL call area for DB2 instructions

### DPICNUMBERS.CBL

Conversion plan for DPICNUMBERS.CBL to Java Quarkus backend service

**Target classes:**
- `DpicnumbersService` → `DpicnumbersService.java` (resource)

### FileCopy.cbl

Conversion plan for COBOL to Java Quarkus

**Target classes:**
- `FileCopyService` → `src/main/java/com/modernizer/migration/filecopy/FileCopyService.java` (resource)
- `FileCopyController` → `src/main/java/com/modernizer/migration/filecopy/FileCopyController.java` (controller)
- `FileCopyRepository` → `src/main/java/com/modernizer/migration/filecopy/FileCopyRepository.java` (repository)
- `FileCopyDTO` → `src/main/java/com/modernizer/migration/filecopy/FileCopyDTO.java` (dto)
- `FileCopyDomain` → `src/main/java/com/modernizer/migration/filecopy/FileCopyDomain.java` (domain)
- `FileCopyException` → `src/main/java/com/modernizer/migration/filecopy/FileCopyException.java` (exception)

**Unresolved items:**
- The status of the input file after it is opened.
- The status of the output file after it is written.

### GREETING.CBL

Conversion plan for GREETING.CBL to Java Quarkus backend service

**Target classes:**
- `GreetingService` → `GreetingService.java` (resource)
- `GreetingRepository` → `GreetingRepository.java` (repository)
- `GreetingDTO` → `GreetingDTO.java` (dto)
- `GreetingDomain` → `GreetingDomain.java` (domain)

### LONGLINESANDNUMBERS.CBL

COBOL to Java Quarkus conversion plan

**Target classes:**
- `GreetingService` → `GreetingService.java` (resource)
- `GreetingController` → `GreetingController.java` (controller)
- `GreetingRepository` → `GreetingRepository.java` (repository)
- `GreetingDTO` → `GreetingDTO.java` (dto)
- `GreetingDomain` → `GreetingDomain.java` (domain)
- `GreetingException` → `GreetingException.java` (exception)

**Unresolved items:**
- WS-COUNT
- WS-FRIEND
- WS-GREETING
- WS-USER-NAME
- WS-FAREWELL
- WS-FAREWELL-LONG

### MOCK.CBL

Conversion Plan for MOCK.CBL to Java Quarkus

**Target classes:**
- `MockService` → `src/main/java/com/modernizer/migration/MockService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- PROG3
- BOOK-PARAM
- ACTION-PARAM
- OUTPUT-VALUE

### MOCKPARA.CBL

Conversion Plan for MOCKPARA.CBL

**Target classes:**
- `MockparaService` → `MockparaService.java` (resource)

**Unresolved items:**
- NUMERIC-1
- NUMERIC-2
- NUMERIC-3
- TEXT-1
- TEXT-2
- TEXT-3

### MOCKTEST.CBL

COBOL to Java Quarkus conversion plan

**Target classes:**
- `MocktestService` → `src/main/java/com/modernizer/migration/MocktestService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `MocktestController` → `src/main/java/com/modernizer/migration/MocktestController.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `MocktestRepository` → `src/main/java/com/modernizer/migration/MocktestRepository.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `MocktestDTO` → `src/main/java/com/modernizer/migration/MocktestDTO.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `MocktestDomain` → `src/main/java/com/modernizer/migration/MocktestDomain.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `MocktestException` → `src/main/java/com/modernizer/migration/MocktestException.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- Unresolved external dependency

### NUMBERS.CBL

Conversion Plan for NUMBERS.CBL to Java Quarkus

**Target classes:**
- `NumbersService` → `NumbersService.java` (service)
- `NumbersRepository` → `NumbersRepository.java` (repository)
- `NumbersDTO` → `NumbersDTO.java` (dto)
- `NumberServiceTest` → `NumberServiceTest.java` (test)

**Unresolved items:**
- adapter-stub

### REPLAC.CBL

COBOL to Java Quarkus conversion plan

**Target classes:**
- `ReplacService` → `ReplacService.java` (resource)

**Unresolved items:**
- WS-COUNT
- WS-FRIEND
- WS-GREETING
- WS-FAREWELL

### RETURNCODE.CBL

Conversion plan for RETURNCODE.CBL to Java Quarkus backend service

**Target classes:**
- `ReturncodeService` → `src/main/java/com/modernizer/migration/domain/service/ReturncodeService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- EXTERNAL_SERVICE

### TESTNESTED.CBL

Conversion plan for TESTNESTED.CBL to Java Quarkus backend service

**Target classes:**
- `TestnestedService` → `TestnestedService.java` (resource)

### WS88LEVEL.CBL

COBOL to Java Quarkus conversion plan

**Target classes:**
- `UtSLinefile` → `UtSLinefile.java` (resource)
- `UtSLinefileStatus` → `UtSLinefileStatus.java` (resource)
- `Lv88Levels` → `Lv88Levels.java` (resource)
- `Lv88LevelsNumeric` → `Lv88LevelsNumeric.java` (resource)
- `UtSProgName` → `UtSProgName.java` (resource)
- `UtSSubprogramName` → `UtSSubprogramName.java` (resource)
- `Lv88LevelsController` → `Lv88LevelsController.java` (controller)

### CCHECKPARAGRAPHSPD.CPY

Conversion Plan for CCHECKPARAGRAPHSPD.CPY

**Target classes:**
- `CcheckParagraphspdService` → `src/main/java/com/modernizer/migration/CcheckparagraphspdService.java` (resource)

**Unresolved items:**
- Format string for ==UT==ACTUAL-ACCESSES
- Format string for ==UT==EXPECTED-ACCESSES

### CCHECKRESULTPD.CPY

Conversion Plan for CCHECKRESULTPD.CPY to Java Quarkus

**Target classes:**
- `TestResultProcessor` → `src/main/java/com/modernizer/migration/processor/TestResultProcessor.java` (resource)

**Unresolved items:**
- ==UT==TEST-CASE-NUMBER
- ==UT==NUMBER-PASSED
- ==UT==NUMBER-FAILED
- ==UT==NUMBER-UNMOCK-CALL
- ==UT==RETCODE

### CCHECKWS.CPY

CCHECKWS.CPY is a data copybook and will be migrated as a shared model/DTO class.

**Target classes:**
- `Ccheckws` → `src/main/java/com/modernizer/migration/model/Ccheckws.java` (model)

### DFHEIBLK.CPY

DFHEIBLK.CPY is a data copybook and will be migrated as a shared model/DTO class.

**Target classes:**
- `Dfheiblk` → `src/main/java/com/modernizer/migration/model/Dfheiblk.java` (model)

### CALL-MOCK-AFTER.CBL

Conversion plan for CALL-MOCK-AFTER.CBL to Java Quarkus

**Target classes:**
- `CallMockAfterService` → `src/main/java/com/modernizer/migration/CallMockAfterService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockAfterService` → `src/main/java/com/modernizer/migration/UtMockAfterService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockClassicCallService` → `src/main/java/com/modernizer/migration/UtMockClassicCallService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockDynamicCallService` → `src/main/java/com/modernizer/migration/UtMockDynamicCallService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- NOTREALNAME

### CICDEMO-AFTER.CBL

Conversion Plan for CICSDEMO-AFTER.CBL to Java Quarkus

**Target classes:**
- `CicdemoAfterService` → `src/main/java/com/modernizer/migration/CicdemoAfterService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockAfterService` → `src/main/java/com/modernizer/migration/UtMockAfterService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockInitializeService` → `src/main/java/com/modernizer/migration/UtMockInitializeService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockFindService` → `src/main/java/com/modernizer/migration/UtMockFindService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockAccessService` → `src/main/java/com/modernizer/migration/UtMockAccessService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockWriteService` → `src/main/java/com/modernizer/migration/UtMockWriteService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockReadService` → `src/main/java/com/modernizer/migration/UtMockReadService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `UtMockEndService` → `src/main/java/com/modernizer/migration/UtMockEndService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- adapter-stub

### ALPHA.CBL

COBOL to Java Quarkus conversion plan

**Target classes:**
- `AlphaController` → `AlphaController.java` (controller)
- `AlphaService` → `AlphaService.java` (service)
- `AlphaRepository` → `AlphaRepository.java` (repository)
- `AlphaDTO` → `AlphaDTO.java` (dto)
- `AlphaDomainModel` → `AlphaDomainModel.java` (domain)
- `AlphaException` → `AlphaException.java` (exception)

**Unresolved items:**
- {"item_id": "RUN_DFE4DA0B", "file_id": 7, "filename": "ALPHA.CBL", "source_name": "WS-THING-1", "target_name": "wsThing1", "type_mapping": ["X(5).", "String"], "confidence": 0.85, "evidence": "WS-THING-1 PIC X(5)."}
- {"item_id": "RUN_DFE4DA0B", "file_id": 7, "filename": "ALPHA.CBL", "source_name": "WS-THING-2", "target_name": "wsThing2", "type_mapping": ["X(5).", "String"], "confidence": 0.85, "evidence": "WS-THING-2 PIC X(5)."}
- {"item_id": "RUN_DFE4DA0B", "file_id": 7, "filename": "ALPHA.CBL", "source_name": "WS-THING-3", "target_name": "wsThing3", "type_mapping": ["X(5).", "String"], "confidence": 0.85, "evidence": "WS-THING-3 PIC X(5)."}
- {"item_id": "RUN_DFE4DA0B", "file_id": 7, "filename": "ALPHA.CBL", "source_name": "WS-THING-4", "target_name": "wsThing4", "type_mapping": ["X(5).", "String"], "confidence": 0.85, "evidence": "WS-THING-4 PIC X(5)."}
- {"item_id": "RUN_DFE4DA0B", "file_id": 7, "filename": "ALPHA.CBL", "source_name": "WS-DISPLAY-NUMERIC", "target_name": "wsDisplayNumeric", "type_mapping": ["999.", "BigDecimal"], "confidence": 0.85, "evidence": "WS-DISPLAY-NUMERIC PIC 999."}

### CONVERT-TEST-AFTER.CBL

Conversion plan for CONVERT-TEST-AFTER.CBL to Java Quarkus backend service

**Target classes:**
- `ConvertTestAfterService` → `src/main/java/com/modernizer/migration/ConvertTestAfterService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `ConvertTestAfterServiceInitialize` → `src/main/java/com/modernizer/migration/ConvertTestAfterServiceInitialize.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `ConvertTestAfterServiceCompareFiles` → `src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareFiles.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `ConvertTestAfterServiceCompareRecords` → `src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareRecords.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- command-line-arguments

### FILE-MOCK-AFTER.CBL

Conversion Plan for FILE-MOCK-AFTER.CBL to Java Quarkus

**Target classes:**
- `FileMockAfterService` → `src/main/java/com/modernizer/migration/FileMockAfterService.java` (resource)
- `FileMockAfterController` → `src/main/java/com/modernizer/migration/FileMockAfterController.java` (controller)
- `FileMockAfterRepository` → `src/main/java/com/modernizer/migration/FileMockAfterRepository.java` (repository)
- `FileMockAfterDTO` → `src/main/java/com/modernizer/migration/FileMockAfterDTO.java` (dto)
- `FileMockAfterDomain` → `src/main/java/com/modernizer/migration/FileMockAfterDomain.java` (domain)
- `FileMockAfterException` → `src/main/java/com/modernizer/migration/FileMockAfterException.java` (exception)

**Unresolved items:**
- {"symbol_name": "INPUT-RECORD", "type_mapping": "String"}
- {"symbol_name": "OUTPUT-RECORD", "type_mapping": "String"}
- {"symbol_name": "WS-FILE-STATUS", "type_mapping": "String"}

### INVDATE-AFTER.CBL

Conversion plan for INVDATE-AFTER.CBL to Java Quarkus

**Target classes:**
- `InvdateAfterService` → `InvdateAfterService.java` (service)
- `UtTest` → `UtTest.java` (test)

**Unresolved items:**
- Flag to indicate whether current date should be set
- Flag to indicate whether comparison is normal
- Flag to indicate whether comparison is default

### MINIMAL-AFTER.CBL

Conversion plan for COBOL to Java Quarkus backend service

**Target classes:**
- `MinimalAfterService` → `src/main/java/com/modernizer/migration/MinimalAfterService.java` (resource)
- `MinimalAfterServiceUtBefore` → `src/main/java/com/modernizer/migration/MinimalAfterServiceUtBefore.java` (resource)
- `MinimalAfterServiceUtAfter` → `src/main/java/com/modernizer/migration/MinimalAfterServiceUtAfter.java` (resource)
- `MinimalAfterServiceUtInitialize` → `src/main/java/com/modernizer/migration/MinimalAfterServiceUtInitialize.java` (resource)
- `MinimalAfterServiceEnd` → `src/main/java/com/modernizer/migration/MinimalAfterServiceEnd.java` (resource)

**Unresolved items:**
- WS-MESSAGE-TYPE
- WS-MESSAGE
- UT-TEST-CASE-NAME
- UT-ACTUAL
- UT-EXPECTED
- UT-NORMAL-COMPARE
- UT-COMPARE-DEFAULT

### MINIMAL-BEFORE.CBL

Conversion Plan for MINIMAL-BEFORE.CBL to Java Quarkus

**Target classes:**
- `MinimalBeforeService` → `src/main/java/com/modernizer/migration/MinimalBeforeService.java` (resource)

**Unresolved items:**
- WS-MESSAGE-TYPE
- WS-MESSAGE

### PARA-MOCK-AFTER.CBL

Conversion plan for COBOL to Java Quarkus backend service

**Target classes:**
- `ParaMockAfterService` → `src/main/java/com/modernizer/migration/ParaMockAfterService.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `ParaMockAfterController` → `src/main/java/com/modernizer/migration/ParaMockAfterController.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)
- `MockDemoConfig` → `src/main/java/com/modernizer/migration/MockDemoConfig.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- ZUTZCWS
- ZUTZCPD

### REPLACE.CBL

Conversion plan for REPLACE.CBL to Java Quarkus backend service

**Target classes:**
- `ReplaceService` → `ReplaceService.java` (resource)

**Unresolved items:**
- WS-ALPHA

### REPLACE2.CBL

COBOL to Java Quarkus conversion plan

**Target classes:**
- `Replace2Service` → `src/main/java/com/modernizer/migration/Replace2Service.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- WS-SUBPROGRAM-NAME

### REPLACE3.CBL

Convert COBOL program to Java Quarkus backend service

**Target classes:**
- `Replace3Service` → `src/main/java/com/modernizer/migration/Replace3Service.java` (resource|controller|router|service|repository|dto|domain|exception|config|test|other)

**Unresolved items:**
- External service or program called by WS-SUBPROGRAM-NAME
- Stub implementation for external service or program ADAPTER-STUB

### SUBPROG-AFTER.CBL

Conversion Plan for SUBPROG-AFTER.CBL to Java Quarkus

**Target classes:**
- `SubprogAfterService` → `SubprogAfterService.java` (resource)
- `UtBeforeHandler` → `UtBeforeHandler.java` (service)
- `UtAfterHandler` → `UtAfterHandler.java` (service)
- `UtInitializeHandler` → `UtInitializeHandler.java` (service)
- `UtEndHandler` → `UtEndHandler.java` (service)

**Unresolved items:**
- LS-ARG-1
- LS-ARG-2

### BIPM012.CBL

Conversion of COBOL to Java Quarkus

**Target classes:**
- `Bipm012Service` → `Bipm012Service.java` (resource|service)

**Unresolved items:**
- BDSIXXX
- PARM

### ALPHA.CBL

Conversion Plan for ALPHA.CBL to Java Quarkus

**Target classes:**
- `AlphaController` → `AlphaController.java` (controller)
- `AlphaService` → `AlphaService.java` (service)
- `AlphaRepository` → `AlphaRepository.java` (repository)
- `AlphaDTO` → `AlphaDTO.java` (dto)
- `AlphaDomainModel` → `AlphaDomainModel.java` (domain)

### NUMBERS.CBL

Conversion Plan for NUMBERS.CBL to Java Quarkus

**Target classes:**
- `NumbersService` → `NumbersService.java` (service)
- `NumbersRepository` → `NumbersRepository.java` (repository)
- `NumbersDTO` → `NumbersDTO.java` (dto)
- `NumbersDomainModel` → `NumbersDomainModel.java` (domain)

### BADCOPY-padded.CBL

Conversion Plan for COBOL to Java Quarkus

**Target classes:**
- `BadCopyGroupItem` → `com/modernizer/migration/BadCopyGroupItem.java` (resource)

**Unresolved items:**
- adapter-stub

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
- Generated project validation failed. Review compiler/syntax errors before production use.

## Validation Output

```txt
Only 38 source file(s) were generated, but 77 conversion plan(s) exist.
Generated project is missing planned class files: mixed004-padded.cbl, src/main/java/com/modernizer/migration/AlphaException.java, src/main/java/com/modernizer/migration/BController.java, src/main/java/com/modernizer/migration/BDTO.java, src/main/java/com/modernizer/migration/BadCopyGroupItem.java, src/main/java/com/modernizer/migration/BetaService.java, src/main/java/com/modernizer/migration/Bipm012IModuleData.java, src/main/java/com/modernizer/migration/Bipm012Service.java, src/main/java/com/modernizer/migration/CModel.java, src/main/java/com/modernizer/migration/COPY003Item1.java, src/main/java/com/modernizer/migration/COPY003Item2.java, src/main/java/com/modernizer/migration/COPY004Item1.java, src/main/java/com/modernizer/migration/COPY004Item2.java, src/main/java/com/modernizer/migration/COPY006Item1.java, src/main/java/com/modernizer/migration/COPY006Item2.java, src/main/java/com/modernizer/migration/COPYR001-paddedController.java, src/main/java/com/modernizer/migration/COPYR001-paddedDomainB.java, src/main/java/com/modernizer/migration/COPYR001-paddedDomainC.java, src/main/java/com/modernizer/migration/COPYR001-paddedDtoB.java, src/main/java/com/modernizer/migration/COPYR001-paddedDtoC.java
Placeholder/stub generated code was rejected: src/main/java/com/modernizer/migration/AdapterStub.java, src/main/java/com/modernizer/migration/dto/Mixed005GroupItemDto.java
Generated methods contain comments but no executable implementation: src/main/java/com/modernizer/migration/AdapterStub.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaController.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaControllerTest.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaDomainModelTest.java (2 method(s)), src/main/java/com/modernizer/migration/AlphaDTOTest.java (2 method(s)), src/main/java/com/modernizer/migration/AlphaRepository.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaRepositoryTest.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaService.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaServiceTest.java (1 method(s)), src/main/java/com/modernizer/migration/AlphaTable1Test.java (2 method(s)), src/main/java/com/modernizer/migration/AlphaTable2Test.java (2 method(s)), src/main/java/com/modernizer/migration/BadcopyGroupItemService.java (1 method(s)), src/main/java/com/modernizer/migration/CallMockAfterService.java (8 method(s)), src/main/java/com/modernizer/migration/ConvertTestAfterService.java (2 method(s)), src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareFiles.java (1 method(s)), src/main/java/com/modernizer/migration/ConvertTestAfterServiceCompareRecords.java (1 method(s)), src/main/java/com/modernizer/migration/Db2progRepository.java (5 method(s)), src/main/java/com/modernizer/migration/Db2progService.java (5 method(s)), src/main/java/com/modernizer/migration/DpicnumbersService/DpicnumbersService.java (1 method(s)), src/main/java/com/modernizer/migration/FileMockAfterController.java (5 method(s))
Locked method coverage is too low: 20/67 (30%).
```

---
Generated by ModernizerAI.