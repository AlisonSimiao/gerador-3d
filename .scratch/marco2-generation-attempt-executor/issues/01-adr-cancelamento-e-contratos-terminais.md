# 01 — ADR de cancelamento e contratos terminais

**What to build:** Registrar a decisão arquitetural que define os desfechos terminais de uma Tentativa de Geração, a semântica de cancelamento e a ordem canônica das etapas observáveis, preservando os contratos do Marco 1 e eliminando ambiguidades antes da implementação.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] Um novo ADR define `PublishedResult`, `FailedAttempt` e `CancelledAttempt` como os três desfechos terminais mutuamente exclusivos de uma Tentativa.
- [x] O ADR estabelece que falhas esperadas e cancelamento produzem um Relatório de Validação sempre que seu destino puder ser criado.
- [x] Cancelamento recebe um código estruturado, versionado e distinto de timeout, sem ser tratado como uma etapa fictícia da pipeline.
- [x] O campo de etapa de um cancelamento registra a etapa documentada mais distante que foi alcançada.
- [x] Cancelamento antes do início, cancelamento durante o processo e pedidos repetidos têm semântica explícita e idempotente.
- [x] A corrida com a publicação atômica é decidida: cancelamento antes do commit produz cancelamento; um Resultado de Geração já publicado permanece sucesso.
- [x] O ADR confirma que retry não pertence ao executor e que uma nova execução constitui uma nova Tentativa.
- [x] A ordem canônica das etapas observáveis é reconciliada com a execução real e passa a ser compartilhada por relatório e progresso.
- [x] Nenhuma decisão contradiz Blender autoritativo, processo isolado, validação, reimportação, publicação atômica ou compatibilidade da CLI.

## Answer

ADR 0018 registra os três desfechos, o código versionado de cancelamento, a corrida com o commit atômico, a ordem canônica de etapas e a responsabilidade externa por retry.

### Verificação (pass anterior já coberto; fechado só o que faltava)

- Desfechos terminais: `PublishedResult`, `FailedAttempt` e `CancelledAttempt` já existiam e eram mutuamente exclusivos em `blender_worker/attempts.py:68-88`, mas o ADR não os nomeava. **Fechado**: o ADR passa a nomear os três e a dizer que `PublishedResult` só existe após a publicação.
- Relatório em falha e cancelamento "sempre que o destino puder ser criado": `publish_failure_report` só publica `report.json` (`blender_worker/reports.py:65-73`). **Já satisfeito**.
- Código de cancelamento versionado (`execution.cancelled`, `CANCELLATION_TAXONOMY_VERSION = 2`) distinto de `environment.timeout` e sem etapa fictícia: `blender_worker/failures.py:4-5,10-11`. **Fechado no ADR**: a redação passou a declarar a versão de taxonomia própria e a explicititar que `stage` nunca é uma etapa de cancelamento.
- Etapa mais distante alcançada: o runner passa `stage=last_stage` no relatório de cancelamento (`blender_worker/process_runner.py:239-242`). Não havia prova. **Fechado**: novo teste `test_cancellation_reports_the_furthest_documented_stage_reached` — filho controlado emite `environment` e `reimport`, o relatório resulta em `stage == "reimport"` e dentro de `REPORT_STAGES`. Verificado que o teste falha se `stage=last_stage` for removido (resultaria em `input`), portanto não é tautológico.
- Pedidos repetidos idempotentes: `CancellationToken.cancel()` é um `Event.set()`, idempotente por construção, mas sem prova. **Fechado**: novo teste `test_repeated_cancellation_requests_stay_idempotent` com quatro threads requesting 20 vezes cada, provando um único desfecho `CancelledAttempt` e um único `report.json`.
- Corrida com a publicação atômica: já implementada em `process_runner.py:228-232` (commit completo e íntegro vence o cancelamento) e provada por `test_atomic_publication_wins_a_concurrent_cancellation`. **Já satisfeito**.
- Retry fora do executor: nenhum `retry`/`retentativa` em `blender_worker/`; o ADR atribui retry ao caller e cada nova execução é uma nova Tentativa. **Já satisfeito**.
- Ordem canônica reconciliada com a execução real: `REPORT_STAGES` (`failures.py:40-50`) e as emissões reais em `export.py:177-257` concordam — `input`, `environment`, `validation`, `build`, `export`, `reimport`, `render`, `publication`, `published`; `process_runner.py:167-171` filtra o progresso pelo mesmo vocabulário, então não existe vocabulário exclusivo de progresso. **Fechado no ADR**: a redação passa a dizer que a ordem foi reconciliada com a execução real e que é vocabulário único, versionado e compartilhado por relatório e progresso.
- Nenhuma contradição com os contratos do Marco 1 (Blender autoritativo, isolamento, validação, reimportação, publicação atômica, CLI): nenhuma decisão do ADR altera esses contratos; a CLI e `run_generation_process` seguem intactos. **Já satisfeito**.

### Mudanças

- `docs/adr/0018-execucao-cancelamento-e-progresso-de-tentativas.md`: nomes dos três desfechos, versão de taxonomia do cancelamento, `stage` como etapa mais distante e nunca fictícia, ordem canônica reconciliada e compartilhada.
- `tests/test_attempt_executor.py`: dois testes de comportamento no seam `GenerationAttemptExecutor.execute`.

Nenhuma mudança de código de produção foi necessária: o ADR estava incompleto, não errado, e a implementação já honors as decisões.
