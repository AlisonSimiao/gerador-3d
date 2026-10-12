# Execução, cancelamento e progresso de Tentativas

O Marco 2 apresenta `GenerationAttemptExecutor` como a única interface de
alto nível para executar uma Tentativa de Geração completa. Cada execução
termina exatamente uma vez como Resultado publicado, falha documentada ou
cancelamento documentado. Falhas esperadas e cancelamentos produzem um
Relatório de Validação sempre que o destino do relatório puder ser criado.

Cancelamento usa o código versionado `execution.cancelled`, distinto de
timeout, e não constitui uma etapa da pipeline. O relatório conserva a etapa
mais distante alcançada. Um pedido anterior ao processo impede seu início;
durante a execução, encerra e recolhe todo o grupo de processos. Pedidos
repetidos são idempotentes. Se o commit da publicação atômica já ocorreu, o
Resultado de Geração vence a corrida e permanece sucesso; antes do commit,
o cancelamento vence e nenhum Asset ou Preview é publicado.

A ordem canônica observável é `input`, `environment`, `validation`, `build`,
`export`, `reimport`, `render`, `publication`, `published`. Progresso relata
essa ordem com sequência crescente, sem percentuais, e é apenas observacional:
sua ausência ou falha não altera o desfecho.

Retry pertence ao caller. Cada nova execução é uma nova Tentativa, ainda que
pertença ao mesmo Job e possua a mesma Impressão Digital da Geração.

## Consequences

CLI e futuros callers recebem desfechos explícitos sem coordenar etapas. O
worker preserva Blender autoritativo, isolamento, validação, reimportação e
publicação atômica. Timeout, cancelamento e término anormal compartilham o
mesmo cleanup, mas conservam códigos distintos. Job permanece fora do worker.
