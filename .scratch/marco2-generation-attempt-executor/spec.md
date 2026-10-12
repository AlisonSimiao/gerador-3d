# Marco 2: GenerationAttemptExecutor

Status: ready-for-agent

## Problem Statement

O worker do Marco 1 já transforma uma Spec em um Resultado de Geração oficial de ponta a ponta: valida e resolve a entrada, executa o Blender em processo isolado, constrói e valida a geometria, exporta e reimporta o GLB, produz o Preview, registra o Relatório de Validação e publica o conjunto atomicamente. Entretanto, callers ainda precisam conhecer detalhes operacionais dispersos entre a CLI, o executor de processo e a pipeline, incluindo caminhos de arquivos, exceções, leitura posterior do relatório e política de substituição do destino.

Essa interface é insuficiente para o Marco 2. Ela permite que novos callers recriem decisões sobre falhas, timeout, cleanup, correlação e interpretação do desfecho. Também não formaliza as diferenças entre a identidade futura de um Job, a identidade de cada Tentativa de Geração e a Impressão Digital da Geração. Reconstruir a pipeline em outra camada ou linguagem duplicaria responsabilidades já comprovadas e arriscaria divergir dos ADRs existentes.

O worker precisa apresentar um único módulo profundo que execute uma Tentativa de Geração completa. Esse módulo deve preservar o comportamento oficial do Marco 1, tornar sucesso, falha e cancelamento resultados explícitos, continuar atendendo à CLI e oferecer uma forma opcional de observar progresso sem expor as etapas como comandos públicos.

## Solution

Introduzir o módulo `GenerationAttemptExecutor` como a única interface de alto nível para executar uma Tentativa de Geração. Seu ponto de entrada recebe um `GenerationAttempt` e devolve um `AttemptOutcome` terminal. A implementação reutiliza e aprofunda a pipeline Python existente; não cria uma segunda pipeline nem transfere sua coordenação para outro runtime.

`GenerationAttempt` contém apenas os dados necessários para uma execução: identidade opaca e única da Tentativa, Spec não confiável, destino derivado por um caller autorizado, política explícita para destino ocupado, timeout opcional e controle opcional de cancelamento. Validação estrita, defaults, Spec Resolvida, seleção do Tipo de Asset, construção, isolamento, gates, métricas, staging, Relatório de Validação e publicação permanecem escondidos na implementação.

`AttemptOutcome` distingue sucesso, falha e cancelamento. Sucesso referencia um Resultado de Geração oficial já publicado; falha e cancelamento carregam o Relatório de Validação correspondente sempre que ele puder ser produzido. Falhas esperadas da geração deixam de exigir que o caller combine uma exceção com a inspeção posterior do destino. Exceções ficam reservadas a violação da interface ou defeito interno que impeça a produção de um desfecho confiável.

O seam principal de uso e teste será a execução completa de `GenerationAttemptExecutor`. Callers e testes observarão somente o `AttemptOutcome`, o conteúdo final do destino e, quando habilitadas, notificações de progresso. Os seams atuais de processo isolado, Blender real, reimportação e publicação atômica continuam internos e são usados apenas para testes especializados e para a suíte oficial de integração.

## User Stories

1. As a caller do worker, I want to execute one complete Tentativa de Geração through one operation, so that I do not coordinate individual pipeline stages.
2. As a caller do worker, I want to provide an untrusted Spec, so that strict validation and default resolution remain authoritative inside the worker.
3. As a caller do worker, I want a typed terminal outcome, so that I do not infer success from files or exception text.
4. As a caller do worker, I want success to mean that the complete Resultado de Geração was atomically published, so that I never consume partial artifacts.
5. As a caller do worker, I want expected generation failures returned with a Relatório de Validação, so that I can classify them without parsing free-form messages.
6. As a caller do worker, I want cancellation represented separately from technical failure, so that an intentional interruption is not mistaken for a broken Gerador or environment.
7. As a caller do worker, I want a unique Tentativa identity, so that concurrent and repeated executions can be correlated independently.
8. As a future job orchestrator, I want one Job to be able to originate multiple Tentativas, so that retry history remains truthful.
9. As a cache consumer, I want equivalence to use the Impressão Digital da Geração, so that Job identifiers, Tentativa identifiers and Seeds are not misused as content identity.
10. As an operator, I want the Relatório de Validação to record the Tentativa identity, so that a terminal outcome can be correlated with its execution.
11. As an operator, I want a successful report to contain the Impressão Digital da Geração, so that provenance and cache investigation follow ADR 0014.
12. As an operator, I want an invalid-input report to contain only a safe input hash, so that arbitrary rejected input is not copied into operational records.
13. As an operator, I want every official Tentativa to run in a fresh Blender process, so that global Blender state cannot leak between Assets.
14. As an operator, I want a finite timeout for every official Tentativa, so that a stuck Blender process cannot occupy a worker indefinitely.
15. As an operator, I want timeout to terminate and reap the complete process group, so that descendants cannot survive the Tentativa.
16. As an operator, I want cancellation to terminate and reap the complete process group, so that intentional interruption has the same cleanup guarantees as timeout.
17. As an operator, I want staging artifacts removed after success, failure, timeout or cancellation, so that abandoned work does not accumulate.
18. As an operator, I want an existing Resultado de Geração preserved by default, so that retries cannot destroy a valid result.
19. As a CLI user, I want `--force` to remain an explicit replacement request, so that existing command behavior remains compatible.
20. As a CLI user, I want exit status and stderr behavior to remain useful for shell automation, so that the new module does not break current workflows.
21. As a CLI user, I want the same artifacts and reports as before, so that adopting the new module is behaviorally compatible.
22. As a developer, I want Blender to remain the authoritative backend, so that a fast pure-Python path cannot claim an official Resultado de Geração.
23. As a developer, I want validation and GLB reimportation to remain mandatory for official success, so that the new interface cannot bypass existing quality gates.
24. As a developer, I want the current Geradores, representation, validators and publication implementation reused, so that the Marco 2 does not create a competing pipeline.
25. As a developer, I want progress to be optional observation, so that execution remains correct when no observer exists.
26. As a developer, I want progress-observer failure to leave the generation outcome unchanged, so that telemetry cannot corrupt domain behavior.
27. As a progress consumer, I want ordered and monotonic notifications, so that a stage never appears to move backwards.
28. As a progress consumer, I want only documented stage identifiers rather than arbitrary percentages, so that the interface does not promise inaccurate completion estimates.
29. As a maintainer, I want the actual pipeline order and the documented stage order reconciled, so that reports and progress describe the same execution.
30. As a maintainer, I want timeout, cancellation and ordinary failure to use one cleanup implementation, so that lifecycle fixes remain local.
31. As a maintainer, I want one report builder for every terminal path, so that success and failure reports cannot drift in schema or provenance.
32. As a maintainer, I want expected failure codes to remain versioned, so that existing consumers are not silently broken.
33. As a maintainer, I want cancellation to have a documented structured code, so that it is distinguishable without adding an ambiguous pipeline stage.
34. As a maintainer, I want replacement policy to be explicit in the attempt input, so that callers cannot overwrite results accidentally.
35. As a maintainer, I want the destination derived by trusted application code, so that an untrusted Spec cannot select arbitrary filesystem locations.
36. As a test author, I want to test the module through the same execution seam used by the CLI, so that tests prove caller-visible behavior.
37. As a test author, I want fast controlled process adapters for timeout, cancellation and crash scenarios, so that lifecycle behavior is deterministic without pretending to prove an official generation.
38. As a release owner, I want official integration tests to keep using the real supported Blender environment, so that mocks cannot satisfy the release gate.
39. As a release owner, I want existing acceptance matrices and visual approvals to remain valid, so that an interface refactor does not weaken Tipo de Asset quality.
40. As a future infrastructure author, I want queue, persistence and remote storage concerns kept outside this module, so that they can be introduced without changing generation semantics.

## Implementation Decisions

- `GenerationAttemptExecutor` is a deep Python module with one public execution operation. It coordinates the existing implementation but does not reproduce the implementation of its stages.
- The external seam is one complete Tentativa de Geração. Validation, build, export, reimportation, rendering and publication are not public operations and cannot be invoked or reordered by callers.
- The execution operation is terminal: it returns only after the child process has exited or been terminated and reaped, staging cleanup has completed, and the final destination has reached its observable terminal state.
- `GenerationAttempt` contains an opaque `attempt_id`, an untrusted Spec value, a trusted logical destination, an occupied-destination policy, an optional positive timeout and an optional cancellation control. It does not contain pipeline-stage commands, queue metadata or infrastructure-specific handles.
- The default occupied-destination policy is rejection. Explicit replacement preserves the existing CLI `--force` behavior and must still use atomic publication. Routine retry must not imply replacement.
- The default timeout continues to come from the worker's configured operational default. An explicit timeout must be finite and positive. Invalid execution options are interface misuse and fail before a child process starts.
- `AttemptOutcome` is a discriminated terminal result with three cases: `PublishedResult`, `FailedAttempt` and `CancelledAttempt`.
- `PublishedResult` contains the Tentativa identity, the destination, the Impressão Digital da Geração and the successful Relatório de Validação. It is returned only after the indivisible Resultado de Geração is committed.
- `FailedAttempt` contains the Tentativa identity and the failure Relatório de Validação. Expected input, environment, build, validation, render, export, reimportation and publication errors use the existing versioned taxonomy.
- `CancelledAttempt` contains the Tentativa identity and a Relatório de Validação describing the intentional interruption. Cancellation is not reported as successful and never publishes an Asset or Preview.
- For backward compatibility, a cancelled Relatório de Validação remains a non-success report and gains a versioned structured cancellation code. Cancellation does not become a fictitious pipeline stage: `stage` records the furthest documented stage reached.
- The cancellation code is distinct from timeout. Timeout means the configured execution limit elapsed; cancellation means a caller explicitly requested interruption. Neither condition is retried by `GenerationAttemptExecutor`; retry policy belongs to a future caller.
- Cancellation is best-effort until the atomic publication commit point. If cancellation wins before commit, the result is `CancelledAttempt`, the process group is terminated and only the report may be published. If the Resultado de Geração has already committed, success wins and the valid result is never replaced by a cancellation report.
- A cancellation request before process launch produces a cancelled outcome without starting Blender. A request during execution terminates and reaps the child process group. Repeated cancellation requests are idempotent.
- Cancellation, timeout, abnormal child termination and ordinary pipeline failure share one cleanup path for process-group termination, staging removal and report construction.
- Exceptions are not the normal representation of generation failure. An exception may escape only for invalid use of the interface or an internal/protocol failure for which no trustworthy `AttemptOutcome` can be constructed. The CLI translates outcomes back to its existing exit-code and stderr contract.
- A Job is the stable identity of a caller-level generation request. A Job may own zero or more Tentativas. Job identity and job lifecycle remain outside the worker and are not required by `GenerationAttempt`.
- A Tentativa identity identifies one actual execution. Every retry receives a new Tentativa identity, even when it belongs to the same Job and uses the same Spec.
- The Impressão Digital da Geração identifies the logical generation environment and content according to ADR 0014. It derives from the Spec Resolvida and the relevant worker, Blender and Estilo versions. It is neither supplied by callers nor replaced by Job identity, Tentativa identity or Seed.
- Seed controls repeatable visual variation and is never used as an identity for Job, Tentativa, Asset uniqueness or cache lookup.
- Successful reports record both the Tentativa identity and the computed Impressão Digital da Geração. Invalid-input reports record the Tentativa identity and the safe hash required by ADR 0014, without copying arbitrary rejected input.
- The module preserves Blender as the sole authoritative backend for an official Resultado de Geração. Pure-Python inspection remains a non-official development and test facility.
- The module preserves the supported official environment, fresh-process isolation, no-network rule, Spec semantics, Tipo registry, Geradores, Estilo behavior, coordinate contract, Preview contract, validation gates, reimportation gate, Khronos conformance requirement, metrics and atomic publication required by existing ADRs.
- The module does not introduce a second export, report, publication or failure-taxonomy implementation. Existing implementations are consolidated behind the new interface where necessary.
- One internal report builder produces every success, failure, timeout and cancellation report. It preserves the stable report fields and centralizes stage, environment, provenance, metrics, artifacts and structured-error construction.
- The stable ordering of observable stages must be reconciled with the actual implementation before progress is exposed. The ordering is versioned and shared by reports and optional progress; there is no separate progress-only stage vocabulary.
- Optional progress is delivered through an observer owned by the executor's composition, not through public methods for individual stages. The observer receives the Tentativa identity, a monotonically increasing sequence and a documented stage transition.
- Progress reports completed or reached stages, not percentage estimates. Exactly one terminal `AttemptOutcome` exists regardless of how many progress notifications were observed.
- Progress is observational and best-effort. Absence, slowness or failure of an observer cannot change, cancel or invalidate a Tentativa. The implementation must prevent observer backpressure from blocking the Blender process indefinitely.
- The observer seam is introduced only with two justified adapters, such as a no-op/in-memory adapter for tests and a local structured-output adapter for process integration. No remote transport is part of this specification.
- Filesystem staging, clocks, process launching and process signaling remain internal seams. They may have controlled adapters for tests but are not added to the public `GenerationAttempt` interface.
- The CLI becomes a caller of `GenerationAttemptExecutor` while retaining its current command shape, default behavior, `--force`, configurable timeout, exit-code semantics, standard error classification and output artifacts.
- Existing callers of the current Python entry point remain compatible through a transitional wrapper if direct removal would be breaking. The wrapper delegates to `GenerationAttemptExecutor`; it contains no generation logic.
- The module owns no queue, Job persistence, retry schedule, quota, tenant, HTTP, object-storage or UI concepts.

## Testing Decisions

- The highest and preferred test seam is `GenerationAttemptExecutor.execute`. Behavior tests provide a `GenerationAttempt` and assert only the returned `AttemptOutcome`, the final destination and optional observable progress.
- A good behavior test does not call private stages, inspect staging implementation details while execution is in progress, patch individual pipeline functions merely to verify ordering, or assert free-form error prose. It verifies stable outcomes, structured codes, artifacts, reports and cleanup.
- Success tests prove that the returned outcome and on-disk report refer to the same Tentativa, Spec Resolvida and Impressão Digital da Geração, and that the destination contains exactly the Asset, Preview and Relatório de Validação.
- Failure tests prove that expected failures return `FailedAttempt`, preserve the structured taxonomy and leave only the Relatório de Validação when its destination can be created.
- Invalid-input tests prove strict validation, safe input hashing, absence of Blender launch, absence of arbitrary input copying and absence of Asset/Preview.
- Occupied-destination tests prove rejection preserves every byte of an existing Resultado de Geração. Explicit replacement tests prove CLI-compatible atomic replacement without mixed or leftover artifacts.
- Timeout tests use a controlled child process to prove that the whole process group is terminated and reaped, staging is removed, the timeout code is returned and no partial Asset or Preview is published.
- Cancellation-before-start tests prove Blender is never launched and a cancelled outcome/report is produced.
- Cancellation-during-execution tests use a controlled child process to prove idempotent signaling, process-group termination, reaping, cleanup and a cancellation code distinct from timeout.
- Cancellation-versus-publication race tests prove a single terminal rule: cancellation before commit yields cancellation; completed atomic commit yields success and remains untouched.
- Crash and malformed-child-output tests prove the parent either constructs a trustworthy structured failure outcome or raises the narrowly documented internal/protocol exception; it never trusts a stale report.
- Progress tests prove monotonic sequence, non-regressing documented stages, optional observation and exactly one terminal outcome. Observer exceptions and slow observers must not alter the generation result.
- Identity tests prove that separate Tentativas may share one Spec and one Impressão Digital while retaining distinct Tentativa identities. They also prove that different Job identities, when modeled by a caller test, do not affect fingerprint calculation.
- Fingerprint tests prove that it derives from the Spec Resolvida and required environment versions, not the raw input representation, Tentativa identity, Job identity or Seed alone.
- CLI compatibility tests retain prior coverage for command arguments, occupied destinations, `--force`, timeout, exit codes, stderr codes and the successful artifact triple, now observed through delegation to the executor.
- Fast tests may use the real temporary filesystem and controlled local process adapters. These tests prove executor orchestration and lifecycle but do not claim an official Resultado de Geração.
- Official integration tests continue to use the real supported Blender environment and exercise construction, export, reimportation, rendering and publication. Only this level may prove a successful official Resultado de Geração.
- Existing acceptance-matrix and visual-baseline tests remain release requirements and are not replaced by executor tests.
- Existing process-runner, report-contract, pipeline, timeout and atomic-publication tests are prior art. They should be migrated upward or retained as focused internal tests according to the behavior they uniquely prove. Redundant tests of shallow wrappers should be deleted after equivalent executor coverage exists.
- The release gate remains subject to all existing ADR requirements, including Blender and Khronos validation, supported platform, full integration suite and human approval of changed visual baselines.

## Out of Scope

- BullMQ, Redis or any other queue implementation.
- PostgreSQL or any other Job/Tentativa persistence implementation.
- Next.js, HTTP endpoints or application-facing API contracts.
- S3 or any remote artifact-storage adapter.
- Server-Sent Events, WebSockets or any remote progress transport.
- Authentication, authorization, tenants, quotas, billing, scheduling or concurrency policy across workers.
- Automatic retry, retry backoff, leases, dead-letter handling or Job state machines.
- Cache storage or deduplication policy, beyond defining the identity semantics of the Impressão Digital da Geração.
- Container images, deployment topology or infrastructure provisioning.
- New Tipos de Asset, changes to existing Specs, visual redesign of Assets or changes to acceptance matrices.
- Splitting the pipeline into independently queued stages.
- Reimplementing the pipeline in Node.js or moving generation semantics out of Python.
- Network access during a Tentativa de Geração.

## Further Notes

- This specification deepens an existing module cluster; it is not a rewrite. Deleting `GenerationAttemptExecutor` after implementation would force every caller to relearn process isolation, timeout, cancellation, taxonomy, validation gates, cleanup and atomic publication, which is the intended evidence that the module earns its depth.
- The current implementation and documented stage vocabulary must be audited together because their apparent order differs. That reconciliation is part of implementing this specification, but exposing individual stages as public commands is not.
- ADR 0014 already requires an Impressão Digital da Geração and safe hashing for unresolved input. If the current report omits either field, implementation should close that compliance gap rather than create a competing identity scheme.
- Cancellation and the three-way `AttemptOutcome` add semantics not fully covered by the Marco 1 ADRs. Implementation must update or add an ADR before treating those semantics as stable, while preserving rather than silently rewriting the earlier decisions.
- The terms Job and `GenerationAttempt` are intentionally separated from the canonical Tentativa de Geração. Job belongs to a future caller; the worker's domain remains the transformation of a Spec into either a Resultado de Geração or a documented unsuccessful Tentativa.
