# 03: Spec versionada, validação estrita e JSON Schema

**What to build:** O contrato de Spec ganha versão explícita (`spec_version`). A validação é estrita e sem coerção: rejeita tipos JSON incorretos, números não finitos, campos desconhecidos e faixas violadas. Toda Spec aceita vira Spec Resolvida com todos os valores efetivos explícitos. Cada versão publica um JSON Schema distribuído com o worker, derivado da mesma fonte de verdade do modelo Python (ADR 0005).

**Blocked by:** None (can start immediately)

**Status:** claimed

- [ ] `spec_version` aceita e registrada; versões ausentes ou não suportadas rejeitadas
- [ ] Rejeição sem coerção: tipo JSON errado, NaN/Infinity, campos desconhecidos, faixas violadas
- [ ] JSON Schema gerado da fonte única de verdade, com teste que acusa divergência entre modelo e schema
- [ ] Relatório da Tentativa registra a Spec Resolvida (defaults tornados explícitos)
