# 15: CLI — destino ocupado, --force e métricas por etapa

**What to build:** O comando oficial falha quando o destino já contém um Resultado de Geração; substituição exige `--force` explícito e continua usando publicação atômica. Duração por etapa e pico aproximado de memória são registrados desde o início (baseline, sem gate ainda). Linux `x86_64` é a única plataforma oficial do Marco 1 (ADR 0011).

**Blocked by:** 14: Taxonomia versionada de falhas

**Status:** resolved

- [x] Destino já com Resultado de Geração → falha com código de publicação; sem destruição do resultado existente
- [x] `--force` substitui com segurança, ainda com publicação atômica
- [x] Relatório registra duração por etapa e pico aproximado de memória da Tentativa
- [x] Plataforma oficial documentada; plataforma não suportada falha cedo com código de ambiente

## Answer
Destino ocupado sem `--force` falha com `publication.failed` e preserva o Resultado existente (provado no caminho real com Blender: hash do `model.glb` idêntico). `--force` republica atomicamente sem deixar `.previous` ou staging. O runner ignorava relatórios obsoletos de resultados existentes (`KeyError: 'error`); agora só confia em relatório novo e recupera o código estruturado que o filho imprime no stderr. Relatórios levam durações por etapa (`inspect/build/export/reimport/render/total_seconds`) + pico via tracemalloc, e plataforma ≠ Linux `x86_64` falha cedo com `environment.unavailable`. Fast: 119 green; integração pontual (3 testes, incl. geração ponta a ponta) green; mypy limpo.
