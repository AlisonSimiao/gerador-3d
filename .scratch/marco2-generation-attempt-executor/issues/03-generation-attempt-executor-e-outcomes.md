# 03 — GenerationAttemptExecutor e desfechos tipados

**What to build:** Disponibilizar uma única interface de alto nível que recebe uma Tentativa de Geração e retorna um desfecho terminal tipado, reutilizando integralmente a pipeline Python e mantendo a entrada pública anterior como compatibilidade transitória.

**Blocked by:** 01 — ADR de cancelamento e contratos terminais; 02 — Identidade da Tentativa e Impressão Digital da Geração.

**Status:** ready-for-agent

- [x] `GenerationAttempt` reúne identidade da Tentativa, Spec não confiável, destino confiável, política de destino ocupado e timeout opcional válido.
- [x] A interface rejeita opções de execução inválidas antes de iniciar o processo Blender.
- [x] `GenerationAttemptExecutor` apresenta uma única operação pública para a Tentativa completa e não expõe operações por etapa.
- [x] Sucesso retorna `PublishedResult` somente depois de o Resultado de Geração completo ter sido publicado atomicamente.
- [x] Falhas esperadas retornam `FailedAttempt` com Relatório de Validação estruturado, sem exigir que o caller combine exceção e leitura posterior do destino.
- [x] Exceções ficam restritas a uso inválido da interface ou defeito interno para o qual não seja possível construir um desfecho confiável.
- [x] Destino ocupado é rejeitado por padrão e preservado sem alterações; substituição continua sendo uma decisão explícita.
- [x] A execução retorna somente depois que o processo filho terminou ou foi encerrado e recolhido e o cleanup observável terminou.
- [x] O executor delega à pipeline existente; não duplica validação, geração, exportação, reimportação, renderização, relatório ou publicação.
- [x] A entrada Python anterior permanece disponível como wrapper transitório sem lógica própria e mantém seu comportamento documentado.
- [x] Testes no seam do executor cobrem ao menos sucesso oficial, entrada inválida, ambiente indisponível e destino ocupado.

## Answer

`GenerationAttemptExecutor.execute` é o seam único e retorna os três desfechos tipados. A entrada anterior delega por wrapper e a pipeline oficial permanece a única implementação.

Lacunas reais fechadas nesta passagem (commit `8d34f5c`):

- `generate_from_spec_file` tratava `CancelledAttempt` como sucesso e devolvia
  o relatório de cancelamento como se fosse resultado. Agora traduz falha e
  cancelamento para `GenerateError` com o código estruturado, mantendo
  `PublishedResult` como único caminho de retorno.
- Um `GERADOR_3D_TIMEOUT_SECONDS` operacional inválido escapava como
  `could not convert string to float`. `_timeout_seconds` agora valida o
  default também e levanta `ValueError("timeout_seconds deve ser finito e
  positivo")` antes de qualquer processo filho, como as opções explícitas.

Critérios já satisfeitos, agora com evidência no seam do executor
(`tests/test_attempt_executor.py`):

- Campo de `GenerationAttempt` e defaults (`REJECT`, sem timeout, sem
  cancellation) fixados por teste; nenhum comando de etapa no input.
- `GenerationAttemptExecutor` expõe publicamente apenas `execute`.
- Destino ocupado rejeitado por padrão preservando cada byte
  (`publication.failed`); `ExistingResultPolicy.REPLACE` substitui o conjunto
  inteiro atomicamente sem resíduo de staging.
- Wrapper anterior delega sem lógica própria e traduz o código da falha.

Sucesso oficial permanece coberto apenas pelo nível `integration`
(`test_distinct_attempts_share_the_fingerprint_of_the_same_generation`),
conforme o ADR de release gate; verificado verde com Blender 5.2.2 LTS.
