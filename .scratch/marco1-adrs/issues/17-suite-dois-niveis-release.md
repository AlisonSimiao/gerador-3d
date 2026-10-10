# 17: Suíte de dois níveis e gate de release

**What to build:** A suíte possui dois níveis: testes rápidos de contrato e geometria rodam com o pipeline puro-Python (inspeção da IR, sem `bpy`); testes de integração obrigatórios para release rodam no ambiente oficial e cobrem construção, renderização, exportação e reimportação no Blender. Uma release não pode ser aprovada apenas pelos testes fallback (ADR 0010).

**Blocked by:** 12: Publicação atômica do Resultado de Geração, 13: Relatório de Validação versionado

**Status:** claimed

- [ ] Nível rápido sem `bpy` distinto e executável em CI sem Blender; cobre contrato de Spec, IR e validadores
- [ ] Nível de integração no ambiente oficial (Python 3.13 + `bpy` 5.2.2) cobre construção, renderização, exportação e reimportação
- [ ] Documentado e verificado que release exige o nível de integração verde
- [ ] Compatibilidade ampla com Pythons sem `bpy` não é parte do produto
