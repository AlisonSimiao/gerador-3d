# 16: Matriz de Aceitação e baseline visual da Casa

**What to build:** A Casa versiona no repositório as Specs de sua Matriz de Aceitação (caso canônico, opções, limites, Seeds e combinações de maior risco) e os respectivos Previews aprovados; GLBs de referência não são versionados. Cada baseline registra aprovador, data e versões da Spec, worker, Blender e perfil de renderização. Testes automatizados verificam propriedades objetivas, mas não substituem a decisão humana sobre qualidade estética (ADR 0012, GLOSSARY).

**Blocked by:** 07: Casa — variação observável por Seed, 12: Publicação atômica do Resultado de Geração, 13: Relatório de Validação versionado

**Status:** claimed

- [ ] Matriz de Specs da Casa versionada, cobrindo canônico, opções, limites, Seeds e combinações de risco
- [ ] Previews aprovados versionados com metadados de baseline (aprovador, data, versões de Spec/worker/Blender/perfil)
- [ ] Teste automatizado regenera a matriz e compara propriedades objetivas (determinismo, orçamento, validadores)
- [ ] Aprovação visual humana registrada explicitamente — marcada `ready-for-human`, não automatizável
