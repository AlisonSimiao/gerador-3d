# 08: Processo Blender limpo por Tentativa de Geração

**What to build:** Uma geração oficial só existe com o Blender: cada Tentativa de Geração roda em um processo Blender limpo, encerrado ao fim da execução, sem vazamento de estado global entre Assets. Blender indisponível ou com integração falha → falha explícita, nunca sucesso. O fallback puro-Python apenas inspeciona e testa a IR e não publica `model.glb` nem `preview.png`; artefatos do fallback não são um Resultado de Geração oficial (ADR 0001, ADR 0010, ADR 0013).

**Blocked by:** 02: IR com componentes e Âncora

**Status:** ready-for-agent

- [ ] Sem `bpy`: falha de ambiente explícita (exit ≠ 0, código estruturado), sem Asset/Preview publicados
- [ ] Com `bpy`: cada Tentativa usa processo Blender limpo encerrado ao fim; duas Tentativas seguidas não se contaminam
- [ ] Relatório registra o backend realmente utilizado e as versões do ambiente
- [ ] Suíte rápida (sem `bpy`) cobre o caminho de inspeção da IR; caminho oficial coberto na suíte de integração
