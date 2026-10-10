# 11: Gate de reimportação do Asset

**What to build:** Uma geração oficial só termina com sucesso depois que o Blender reimporta o GLB exportado e comprova topologia por componente, materiais, Âncora, transformações, unidades e integridade do Asset entregue. Verificações puro-Python são auxiliares e não substituem esse gate (ADR 0006).

**Blocked by:** 09: Exportação oficial glTF com conversão de coordenadas

**Status:** ready-for-agent

- [ ] Reimportação do GLB roda dentro da Tentativa, antes de qualquer publicação
- [ ] Gate comprova: topologia por componente, materiais atribuídos, Âncora na origem, transformações, unidades, integridade do Asset
- [ ] GLB corrompido ou incompleto (teste de falha) → gate rejeita, exit ≠ 0, motivo estruturado no Relatório
- [ ] Verificações puro-Python continuam presentes como auxiliares, sem substituir o gate
