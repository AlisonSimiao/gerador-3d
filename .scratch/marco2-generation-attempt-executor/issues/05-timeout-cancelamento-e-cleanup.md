# 05 — Timeout, cancelamento e cleanup terminal

**What to build:** Permitir que uma Tentativa seja cancelada antes ou durante a execução e garantir que cancelamento, timeout e término anormal compartilhem as mesmas garantias de encerramento, coleta do processo e limpeza de intermediários.

**Blocked by:** 01 — ADR de cancelamento e contratos terminais; 03 — GenerationAttemptExecutor e desfechos tipados.

**Status:** resolved

- [x] Um pedido de cancelamento anterior ao lançamento retorna `CancelledAttempt` sem iniciar Blender.
- [x] Um pedido durante a execução encerra e recolhe todo o grupo do processo isolado e retorna `CancelledAttempt`.
- [x] Pedidos repetidos de cancelamento são seguros e não criam mais de um desfecho terminal.
- [x] Timeout continua retornando `FailedAttempt` com seu código estruturado atual, distinto de cancelamento.
- [x] Cancelamento e timeout descartam staging e nunca publicam Asset ou Preview parciais.
- [x] O Relatório de Validação de cancelamento conserva a última etapa documentada alcançada e contém apenas os artefatos permitidos para insucesso.
- [x] Se o commit atômico vencer a corrida, o executor retorna sucesso e não substitui o Resultado de Geração por relatório de cancelamento.
- [x] Se o cancelamento vencer antes do commit, nenhum Resultado de Geração se torna observável.
- [x] Processo inexistente, término simultâneo e falha ao sinalizar são tratados de forma idempotente sem deixar descendentes ou staging.
- [x] Testes com processo controlado provam término do grupo, coleta, códigos estruturados, corrida terminal e ausência de artefatos intermediários.

## Answer

Cancelamento antes/durante a execução e timeout compartilham encerramento do grupo, coleta e cleanup. Testes controlados provam também que um commit atômico já visível vence a corrida.
