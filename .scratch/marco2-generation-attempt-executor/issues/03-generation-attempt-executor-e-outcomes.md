# 03 — GenerationAttemptExecutor e desfechos tipados

**What to build:** Disponibilizar uma única interface de alto nível que recebe uma Tentativa de Geração e retorna um desfecho terminal tipado, reutilizando integralmente a pipeline Python e mantendo a entrada pública anterior como compatibilidade transitória.

**Blocked by:** 01 — ADR de cancelamento e contratos terminais; 02 — Identidade da Tentativa e Impressão Digital da Geração.

**Status:** resolved

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
