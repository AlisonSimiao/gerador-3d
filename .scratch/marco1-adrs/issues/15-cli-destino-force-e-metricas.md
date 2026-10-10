# 15: CLI — destino ocupado, --force e métricas por etapa

**What to build:** O comando oficial falha quando o destino já contém um Resultado de Geração; substituição exige `--force` explícito e continua usando publicação atômica. Duração por etapa e pico aproximado de memória são registrados desde o início (baseline, sem gate ainda). Linux `x86_64` é a única plataforma oficial do Marco 1 (ADR 0011).

**Blocked by:** 14: Taxonomia versionada de falhas

**Status:** claimed

- [ ] Destino já com Resultado de Geração → falha com código de publicação; sem destruição do resultado existente
- [ ] `--force` substitui com segurança, ainda com publicação atômica
- [ ] Relatório registra duração por etapa e pico aproximado de memória da Tentativa
- [ ] Plataforma oficial documentada; plataforma não suportada falha cedo com código de ambiente
