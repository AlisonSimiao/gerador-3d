# 09: Exportação oficial glTF com conversão de coordenadas

**What to build:** O backend Blender oficial é o único que transforma a IR em Asset: exporta o GLB com conversão explícita das coordenadas internas do Blender para o contrato glTF — metros, sistema destro, `+Y` para cima, `+Z` como frente, com a Âncora na origem (ADR 0003, ADR 0007). O escritor puro-Python deixa de ser o exportador do produto.

**Blocked by:** 08: Processo Blender limpo por Tentativa de Geração

**Status:** resolved

- [x] `model.glb` do Resultado oficial produzido pelo exportador Blender, não pelo antigo escritor puro-Python
- [x] Após reimportação manual: `+Y` para cima, `+Z` frente, escala em metros, Âncora na origem
- [x] Materiais e grupos de materiais do Estilo preservados no export (uma malha, um nó raiz)

## Answer

O exportador oficial (`bpy.ops.export_scene.gltf`, `export_yup=True`, unidades métricas) é o único caminho que produz `model.glb`; o escritor puro-Python `_write_glb` foi removido. `mesh_to_bpy` aplica a rotação explícita da IR para o espaço Blender, e o gate de reimportação agora registra `coordinate_system`, `mesh_count`, `root_nodes` e `root_transform_identity`. Teste novo `test_official_glb_has_blender_provenance_and_the_coordinate_contract` prova proveniência Blender, 1 malha/1 nó raiz sem TRS, materiais do estilo e porta em `+Z` com base em `Y≈0`. Evidência: rápida 80 passed, integração 9 passed, `mypy blender_worker` limpo.
