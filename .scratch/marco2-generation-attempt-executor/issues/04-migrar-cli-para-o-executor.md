# 04 — Migrar a CLI para GenerationAttemptExecutor

**What to build:** Fazer a CLI oficial consumir o novo executor sem alterar a experiência existente, tornando-a um caller fino que traduz argumentos em uma Tentativa e o desfecho terminal em saída de processo.

**Blocked by:** 03 — GenerationAttemptExecutor e desfechos tipados.

**Status:** resolved

- [x] O comando oficial cria uma Tentativa e chama exclusivamente o executor de alto nível.
- [x] A forma do comando e os argumentos existentes continuam aceitos, incluindo destino, `--force` e timeout configurável.
- [x] Uma execução bem-sucedida conserva código de saída zero, mensagem útil e o trio indivisível de Asset, Preview e Relatório de Validação.
- [x] Falhas esperadas conservam código de saída diferente de zero e expõem o mesmo código estruturado em stderr sem exigir interpretação de texto livre.
- [x] Um destino ocupado sem `--force` permanece intacto e falha segundo o contrato existente.
- [x] `--force` continua substituindo apenas por publicação atômica, sem misturar artefatos de Resultados diferentes.
- [x] O timeout explícito e o default operacional conservam o comportamento do Marco 1.
- [x] A CLI não conhece nem coordena etapas internas e não recria tratamento de falhas ou construção de relatórios.
- [x] Testes de compatibilidade demonstram que scripts que dependem de argumentos, códigos de saída, stderr e artefatos continuam funcionando.

## Answer

A CLI tornou-se caller do executor e preservou argumentos, códigos de saída, stderr estruturado, `--force`, timeout e publicação atômica.
