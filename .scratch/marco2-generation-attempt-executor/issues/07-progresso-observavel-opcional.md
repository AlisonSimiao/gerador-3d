# 07 — Progresso observável opcional

**What to build:** Permitir a observação local e opcional do avanço de uma Tentativa por eventos ordenados, sem transformar etapas em comandos públicos nem permitir que telemetria altere o desfecho da geração.

**Blocked by:** 01 — ADR de cancelamento e contratos terminais; 03 — GenerationAttemptExecutor e desfechos tipados; 06 — Relatório de Validação unificado.

**Status:** resolved

- [x] O executor funciona normalmente sem observer configurado.
- [x] Cada evento contém a identidade da Tentativa, sequência estritamente crescente e uma etapa do vocabulário versionado compartilhado com o relatório.
- [x] Eventos seguem a ordem canônica e uma etapa observada nunca regride.
- [x] Progresso comunica etapas alcançadas ou concluídas e não inventa percentuais de conclusão.
- [x] Exatamente um `AttemptOutcome` terminal é produzido, independentemente da quantidade de eventos observados.
- [x] Exceção, indisponibilidade ou lentidão do observer não muda sucesso, falha ou cancelamento e não bloqueia Blender indefinidamente.
- [x] Existem ao menos dois adapters justificados para tornar o seam real: um adapter local estruturado e um adapter no-op ou em memória para testes.
- [x] Nenhum adapter remoto, fila, banco, SSE ou conceito de infraestrutura SaaS é introduzido.
- [x] Testes provam opcionalidade, monotonicidade, isolamento de falhas do observer e consistência entre a última etapa observada e o Relatório de Validação.

## Answer

Observers em memória e JSONL local recebem etapas monotônicas por dispatcher desacoplado. Observer ausente, lento ou quebrado não altera o desfecho nem bloqueia indefinidamente a Tentativa.
