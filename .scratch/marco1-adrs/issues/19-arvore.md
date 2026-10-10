# 19: Árvore (v1)

**What to build:** A Árvore passa ao contrato v1 do ADR 0009: `trunk_height` (1,5–8 m, default 3), `trunk_radius` (0,12–0,60 m, default 0,25), `canopy_form` (clustered|round|conical), `foliage_palette` (green|autumn|dark_green), `lean_degrees` (0–20°, default 5°) aplicado ao tronco e à copa. A forma da copa é independente da paleta da folhagem — `pine` não é uma cor (ADR 0009). Âncora no centro da superfície de apoio. Variação observável por Seed; Matriz de Aceitação e baseline versionados.

**Blocked by:** 17: Suíte de dois níveis e gate de release

**Status:** resolved

- [x] Contrato v1 da Árvore com campos, faixas e defaults do ADR 0009; `lean` em graus, não fração
- [x] `canopy_form` e `foliage_palette` independentes e ambos exercitados nos exemplos
- [x] Variação observável por Seed; mesma Seed reproduz o resultado
- [x] Matriz de Aceitação e baseline visual versionados; orçamento de 5000 triângulos respeitado

## Answer
Contrato v1 já exato em `schema.py`/`registry.py` (faixas e defaults ADR 0009, `lean` antigo rejeitado por campo desconhecido); removido `leaf_pine` de `style.py` (morto — nenhum gerador o referencia; `pine` segue fora do contrato) e corrigido o rótulo `# sphere` → `# round` em `tree.py`.
`lean_degrees` desloca tronco (proporcional à altura) e copa (segue o topo) na mesma direção; âncora `SUPPORT_SURFACE` na origem — ambos com testes.
Seed observável (clustered varia 4–5 copas/offsets; mesma seed = IR idêntica) com testes de variação e reprodução.
Matriz `acceptance/tree/` com 7 specs (3 formas × 3 paletas, limites mín/máx, seed-variant) + `baseline.json` todo `ready-for-human`, aprovador nulo; previews candidatos em `review/` via Blender Eevee oficial.
Orçamento provado: pior variante 126 tris de 5000; suíte rápida 136 passed, integração da matriz 2 passed, mypy limpo.
