# 13: Relatório de Validação versionado

**What to build:** O Relatório de Validação ganha schema versionado e campos estáveis: status, etapa alcançada, backend realmente utilizado, versões do ambiente, Spec Resolvida, verificações executadas, artefatos publicados e erro estruturado. O futuro backend SaaS consome o relatório sem interpretar mensagens livres (ADR 0007, GLOSSARY).

**Blocked by:** 08: Processo Blender limpo por Tentativa de Geração

**Status:** ready-for-agent

- [ ] `schema_version` presente; campos estáveis documentados e cobertos por teste de contrato
- [ ] Relatório registra: status, etapa, backend real, versões (worker, Blender, Python, perfil de render), Spec Resolvida, verificações, artefatos, erro estruturado
- [ ] Toda Tentativa de Geração produz Relatório quando o destino puder ser criado — inclusive em falha
- [ ] Duração por etapa e pico aproximado de memória presentes como campos (baseline; ainda sem gate)
