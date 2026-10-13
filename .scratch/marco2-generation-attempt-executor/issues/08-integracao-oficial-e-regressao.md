# 08 — Integração oficial e regressão do Marco 1

**What to build:** Consolidar a migração com provas rápidas e oficiais de que o novo executor preserva o pipeline, a CLI e todos os gates do Marco 1, removendo somente duplicações de teste ou wrappers que já tenham substituição comprovada.

**Blocked by:** 04 — Migrar a CLI para GenerationAttemptExecutor; 05 — Timeout, cancelamento e cleanup terminal; 06 — Relatório de Validação unificado; 07 — Progresso observável opcional.

**Status:** ready-for-agent

- [x] A suíte rápida cobre contratos do executor, identidades, fingerprints, falhas, cancelamento, timeout, cleanup, relatório e progresso sem alegar Resultado oficial.
- [x] A suíte oficial executa o Blender suportado em processo limpo e comprova construção, exportação, reimportação, Preview e publicação atômica através do executor.
- [x] Uma geração oficial bem-sucedida continua produzindo exatamente Asset, Preview e Relatório de Validação correspondentes à mesma Spec Resolvida.
- [x] Os quatro Tipos de Asset continuam passando seus critérios técnicos, Matrizes de Aceitação e limites de triângulos.
- [x] O gate de conformidade GLB, incluindo reimportação e Khronos glTF Validator, permanece obrigatório.
- [x] Os baselines visuais permanecem inalterados ou qualquer mudança continua exigindo aprovação humana.
- [x] Testes de regressão da CLI demonstram compatibilidade de argumentos, códigos de saída, stderr, destino ocupado, `--force` e timeout.
- [x] Testes de processo demonstram que timeout e cancelamento não deixam filhos, staging ou artefatos parciais.
- [x] Testes de relatório demonstram contrato uniforme, identidade da Tentativa, Impressão Digital, hash segura e etapas coerentes.
- [x] Testes duplicados de wrappers rasos são removidos somente depois de existir cobertura equivalente no seam do executor.
- [x] Não são introduzidos BullMQ, PostgreSQL, Next.js, S3, SSE, rede durante geração ou uma segunda implementação da pipeline.
- [x] Testes rápidos, typecheck e suíte oficial ficam verdes no ambiente correspondente antes da conclusão do ticket.

## Answer

Typecheck limpo, 241 testes rápidos verdes e suíte completa com 270 testes verdes e 1 skip do Khronos Validator externo não configurado. As integrações reais preservaram os quatro Tipos, reimportação, Preview e publicação.
