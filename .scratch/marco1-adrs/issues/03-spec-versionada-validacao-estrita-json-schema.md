# 03: Spec versionada, validação estrita e JSON Schema

**What to build:** O contrato de Spec ganha versão explícita (`spec_version`). A validação é estrita e sem coerção: rejeita tipos JSON incorretos, números não finitos, campos desconhecidos e faixas violadas. Toda Spec aceita vira Spec Resolvida com todos os valores efetivos explícitos. Cada versão publica um JSON Schema distribuído com o worker, derivado da mesma fonte de verdade do modelo Python (ADR 0005).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `spec_version` aceita e registrada; versões ausentes ou não suportadas rejeitadas
- [x] Rejeição sem coerção: tipo JSON errado, NaN/Infinity, campos desconhecidos, faixas violadas
- [x] JSON Schema gerado da fonte única de verdade, com teste que acusa divergência entre modelo e schema
- [x] Relatório da Tentativa registra a Spec Resolvida (defaults tornados explícitos)

## Answer

O contrato completo de entrada `v1` agora é gerado a partir das dataclasses e dos
descritores usados pelo runtime e distribuído em `blender_worker/schemas/spec-v1.schema.json`.
A suíte compara o artefato público integralmente com o contrato runtime, cobrindo tipos,
constantes, enums, defaults, obrigatoriedade e limites. A validação estrita cobre também
números não finitos, e uma Tentativa com entrada mínima comprova no seam público que o
Relatório registra a Spec Resolvida completa.

## Comments

- Context pointer: implementação em `c4447de` (`Implement strict versioned spec schema (#03)`).
- Verificação: `25 passed`; mypy sem erros; wheel contém `spec-v1.schema.json`.
