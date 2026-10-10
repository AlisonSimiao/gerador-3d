# 19: Árvore (v1)

**What to build:** A Árvore passa ao contrato v1 do ADR 0009: `trunk_height` (1,5–8 m, default 3), `trunk_radius` (0,12–0,60 m, default 0,25), `canopy_form` (clustered|round|conical), `foliage_palette` (green|autumn|dark_green), `lean_degrees` (0–20°, default 5°) aplicado ao tronco e à copa. A forma da copa é independente da paleta da folhagem — `pine` não é uma cor (ADR 0009). Âncora no centro da superfície de apoio. Variação observável por Seed; Matriz de Aceitação e baseline versionados.

**Blocked by:** 17: Suíte de dois níveis e gate de release

**Status:** ready-for-agent

- [ ] Contrato v1 da Árvore com campos, faixas e defaults do ADR 0009; `lean` em graus, não fração
- [ ] `canopy_form` e `foliage_palette` independentes e ambos exercitados nos exemplos
- [ ] Variação observável por Seed; mesma Seed reproduz o resultado
- [ ] Matriz de Aceitação e baseline visual versionados; orçamento de 5000 triângulos respeitado
