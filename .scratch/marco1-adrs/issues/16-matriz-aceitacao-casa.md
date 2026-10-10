# 16: Matriz de Aceitação e baseline visual da Casa

**What to build:** A Casa versiona no repositório as Specs de sua Matriz de Aceitação (caso canônico, opções, limites, Seeds e combinações de maior risco) e os respectivos Previews aprovados; GLBs de referência não são versionados. Cada baseline registra aprovador, data e versões da Spec, worker, Blender e perfil de renderização. Testes automatizados verificam propriedades objetivas, mas não substituem a decisão humana sobre qualidade estética (ADR 0012, GLOSSARY).

**Blocked by:** 07: Casa — variação observável por Seed, 12: Publicação atômica do Resultado de Geração, 13: Relatório de Validação versionado

**Status:** ready-for-human

- [x] Matriz de Specs da Casa versionada, cobrindo canônico, opções, limites, Seeds e combinações de risco
- [x] Previews aprovados versionados com metadados de baseline (aprovador, data, versões de Spec/worker/Blender/perfil)
- [x] Teste automatizado regenera a matriz e compara propriedades objetivas (determinismo, orçamento, validadores)
- [ ] Aprovação visual humana registrada explicitamente — marcada `ready-for-human`, não automatizável

## Comments

Aprovação visual pendente de humano: `acceptance/house/review/<spec>/preview.png`
(9 candidatos gerados pelo caminho oficial Blender Eevee) aguardam revisão;
`baseline.json` segue `ready-for-human` com aprovador nulo. Nada foi
auto-aprovado. GLBs nunca versionados.

## Answer

Matriz com 9 specs (`canonical`, `risk-hip-timber` reaproveitados + 7 novos:
`opt-gable-stone`, `opt-hip-plaster`, `risk-hip-stone`, `risk-gable-timber`,
`limit-min`, `limit-max`, `seed-variant`) cobrindo os 6 combos
roof_form × wall_finish, extremos de pavimentos/limites e variação de seed.
`baseline.json` com metadados por spec, todos `ready-for-human`. Testes:
`tests/test_house_acceptance_matrix.py` (rápido) e
`tests/test_house_acceptance_matrix_integration.py` (regeneração oficial).
Humano precisa: abrir os 9 previews em `review/`, aprovar/rejeitar e registrar
aprovador/data em `baseline.json`.
