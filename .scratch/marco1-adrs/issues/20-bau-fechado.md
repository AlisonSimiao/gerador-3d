# 20: Baú Fechado (v1)

**What to build:** O Baú passa ao contrato v1 do ADR 0009: `width` (0,6–1,8 m, default 1), `height` (0,4–1,1 m, default 0,6), `depth` (0,4–1,0 m, default 0,6), `lid_form` (arched|flat), `band_count` (0–4, default 2), `has_lock`. As dimensões medem o envelope externo completo, incluindo tampa e cintas; sem interior ou mecanismo de abertura — tampa, cintas e fecho são elementos visuais (ADR 0003, ADR 0009). Âncora no centro da superfície de apoio. Variação observável por Seed; Matriz de Aceitação e baseline versionados.

**Blocked by:** 17: Suíte de dois níveis e gate de release

**Status:** claimed

- [ ] Contrato v1 do Baú com campos, faixas e defaults do ADR 0009; campos antigos rejeitados
- [ ] Envelope externo confere com as dimensões declaradas (tampa e cintas incluídas)
- [ ] Variação observável por Seed; mesma Seed reproduz o resultado
- [ ] Matriz de Aceitação e baseline visual versionados; orçamento de 2000 triângulos respeitado
