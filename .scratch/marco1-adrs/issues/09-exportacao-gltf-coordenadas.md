# 09: Exportação oficial glTF com conversão de coordenadas

**What to build:** O backend Blender oficial é o único que transforma a IR em Asset: exporta o GLB com conversão explícita das coordenadas internas do Blender para o contrato glTF — metros, sistema destro, `+Y` para cima, `+Z` como frente, com a Âncora na origem (ADR 0003, ADR 0007). O escritor puro-Python deixa de ser o exportador do produto.

**Blocked by:** 08: Processo Blender limpo por Tentativa de Geração

**Status:** claimed

- [ ] `model.glb` do Resultado oficial produzido pelo exportador Blender, não pelo antigo escritor puro-Python
- [ ] Após reimportação manual: `+Y` para cima, `+Z` frente, escala em metros, Âncora na origem
- [ ] Materiais e grupos de materiais do Estilo preservados no export (uma malha, um nó raiz)
