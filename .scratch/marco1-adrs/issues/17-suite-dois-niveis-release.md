# 17: Suíte de dois níveis e gate de release

**What to build:** A suíte possui dois níveis: testes rápidos de contrato e geometria rodam com o pipeline puro-Python (inspeção da IR, sem `bpy`); testes de integração obrigatórios para release rodam no ambiente oficial e cobrem construção, renderização, exportação e reimportação no Blender. Uma release não pode ser aprovada apenas pelos testes fallback (ADR 0010).

**Blocked by:** 12: Publicação atômica do Resultado de Geração, 13: Relatório de Validação versionado

**Status:** resolved

## Answer

- Nível rápido provado sem `bpy`: `tests/test_suite_levels.py` roda a suíte
  rápida com import de `bpy`/`mathutils` bloqueado mais AST-scan anti-regressão.
- Integração por estágio: `tests/test_pipeline_stages.py` (construção via
  `mesh_to_bpy`, render via `render_official_preview`, export via `_export_glb`,
  reimport via `_reimport_gate`) — 4 testes, sem duplicar o gate do ticket 11.
- Gate de release em README.md + acceptance/README.md e job `integration` em
  `.github/workflows/ci.yml` (fast em Python 3.12 sem `bpy`, release só com
  integration verde + baselines `approved`).
- Sem-`bpy` amplo fora de escopo: nota no README; `requires-python` inalterado.

- [x] Nível rápido sem `bpy` distinto e executável em CI sem Blender; cobre contrato de Spec, IR e validadores
- [x] Nível de integração no ambiente oficial (Python 3.13 + `bpy` 5.2.2) cobre construção, renderização, exportação e reimportação
- [x] Documentado e verificado que release exige o nível de integração verde
- [x] Compatibilidade ampla com Pythons sem `bpy` não é parte do produto
