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
