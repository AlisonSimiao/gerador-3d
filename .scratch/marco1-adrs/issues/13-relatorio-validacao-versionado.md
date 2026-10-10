# 13: Relatório de Validação versionado

**What to build:** O Relatório de Validação ganha schema versionado e campos estáveis: status, etapa alcançada, backend realmente utilizado, versões do ambiente, Spec Resolvida, verificações executadas, artefatos publicados e erro estruturado. O futuro backend SaaS consome o relatório sem interpretar mensagens livres (ADR 0007, GLOSSARY).

**Blocked by:** 08: Processo Blender limpo por Tentativa de Geração

**Status:** resolved

- [x] `schema_version` presente; campos estáveis documentados e cobertos por teste de contrato
- [x] Relatório registra: status, etapa, backend real, versões (worker, Blender, Python, perfil de render), Spec Resolvida, verificações, artefatos, erro estruturado
- [x] Toda Tentativa de Geração produz Relatório quando o destino puder ser criado — inclusive em falha
- [x] Duração por etapa e pico aproximado de memória presentes como campos (baseline; ainda sem gate)

## Answer

`REPORT_STAGES` + `stage_for_code()` em `failures.py` documentam a etapa como vocabulário estável (input/environment/build/validation/render/export/reimport/publication/published); `_StageClock` em `export.py` mede laps por etapa e pico tracemalloc, e os três construtores de relatório (sucesso, `generate_in_process_*`, runner) agora registram duração total + pico sempre, com laps parciais preservados em falha. `tests/test_report_contract.py` fixa o contrato. Evidência: 85 fast verdes, 8/8 integração verdes, mypy limpo.
