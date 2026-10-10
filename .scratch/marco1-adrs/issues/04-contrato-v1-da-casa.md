# 04: Contrato v1 da Casa

**What to build:** A Casa passa a falar o contrato candidato a `v1` do ADR 0009: `roof_form` (gable|hip), `wall_finish` (plaster|timber|stone), `window_count`, `has_chimney`, porta sempre presente; `width`/`depth` medem o corpo externo das paredes sem beirais. Faixas: width 3–12 m (default 6), depth 3–10 m (default 5), floors 1–3 (default 1), window_count 0–16 (default 4); seed 0–4.294.967.295; relações entre campos preservam o arquétipo. O Gerador é adaptado mecanicamente para os novos nomes, mantendo a suíte verde.

**Blocked by:** 03: Spec versionada, validação estrita e JSON Schema

**Status:** ready-for-agent

- [ ] Campos e valores antigos da Casa rejeitados; novos aceitos com defaults documentados
- [ ] Faixas do ADR 0009 e relações entre campos validadas (janelas cabem nas fachadas; profundidade coerente com a altura por pavimento)
- [ ] Especificação de exemplo da Casa atualizada; geração da Casa verde com o Gerador adaptado
- [ ] Todo parâmetro candidato a v1 altera geometria ou aparência de forma reconhecível — sem campos redundantes ou visualmente indistinguíveis
