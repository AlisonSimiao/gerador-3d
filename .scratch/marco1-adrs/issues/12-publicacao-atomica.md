# 12: Publicação atômica do Resultado de Geração

**What to build:** Asset e Preview são publicados juntos no destino final somente após todas as validações. Em caso de falha, o destino contém apenas o Relatório de Validação; artefatos intermediários permanecem numa área temporária descartável. Existência de arquivo deixa de significar sucesso parcial (ADR 0006).

**Blocked by:** 10: Preview oficial — prancha 1024 px e perfil de render versionado, 11: Gate de reimportação do Asset

**Status:** claimed

- [ ] Sucesso: destino contém `model.glb`, `preview.png` e `report.json` mutuamente consistentes (mesma Spec Resolvida)
- [ ] Falha em qualquer etapa: destino contém somente `report.json`; nenhum Asset/Preview parcial
- [ ] Área temporária descartada ao fim da Tentativa, em sucesso e em falha
- [ ] Teste de falha forçada (ex.: gate de reimportação) confirma publicação apenas do Relatório
