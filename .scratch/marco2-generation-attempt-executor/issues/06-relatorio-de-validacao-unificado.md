# 06 — Relatório de Validação unificado

**What to build:** Fazer todos os caminhos terminais usarem uma única construção de Relatório de Validação, eliminando divergências entre sucesso, falhas internas, falhas do executor, timeout e cancelamento sem mudar os contratos estáveis do Marco 1.

**Blocked by:** 02 — Identidade da Tentativa e Impressão Digital da Geração; 03 — GenerationAttemptExecutor e desfechos tipados; 05 — Timeout, cancelamento e cleanup terminal.

**Status:** ready-for-agent

- [x] Um único módulo de construção concentra schema, status, etapa, backend, ambiente, identidade, proveniência, checks, artefatos, erro e métricas.
- [x] Sucesso, entrada inválida, ambiente indisponível, timeout, cancelamento e falhas de cada etapa atravessam essa construção comum.
- [x] Todo relatório terminal carrega identidade da Tentativa e duração total não negativa.
- [x] Relatórios de sucesso carregam Spec Resolvida, Impressão Digital e exatamente os artefatos do Resultado de Geração.
- [x] Relatórios de insucesso carregam erro estruturado e nunca alegam Asset ou Preview publicado.
- [x] Entrada inválida preserva somente a hash segura exigida, sem vazar conteúdo arbitrário.
- [x] A taxonomia e os campos estáveis existentes permanecem compatíveis; a extensão de cancelamento segue o ADR aprovado.
- [x] Relatórios obsoletos em destinos ocupados nunca são confundidos com o relatório da Tentativa corrente.
- [x] Construtores anteriores tornam-se delegações finas ou são removidos depois que todos os caminhos migram.
- [x] Testes de contrato exercitam todas as famílias de desfecho pelo seam mais alto possível e não dependem de detalhes internos do construtor.

## Answer

O módulo de relatórios centraliza ambiente, identidade, proveniência, métricas, artefatos e erros para o pipeline e o runner, mantendo wrappers apenas por compatibilidade.
