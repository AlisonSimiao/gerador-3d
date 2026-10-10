# 12: Publicação atômica do Resultado de Geração

**What to build:** Asset e Preview são publicados juntos no destino final somente após todas as validações. Em caso de falha, o destino contém apenas o Relatório de Validação; artefatos intermediários permanecem numa área temporária descartável. Existência de arquivo deixa de significar sucesso parcial (ADR 0006).

**Blocked by:** 10: Preview oficial — prancha 1024 px e perfil de render versionado, 11: Gate de reimportação do Asset

**Status:** resolved

- [x] Sucesso: destino contém `model.glb`, `preview.png` e `report.json` mutuamente consistentes (mesma Spec Resolvida)
- [x] Falha em qualquer etapa: destino contém somente `report.json`; nenhum Asset/Preview parcial
- [x] Área temporária descartada ao fim da Tentativa, em sucesso e em falha
- [x] Teste de falha forçada (ex.: gate de reimportação) confirma publicação apenas do Relatório

## Answer
Publicação atômica provada no seam do diretório-destino
(`tests/test_atomic_publication.py`, via TDD): o teste de sucesso gera a
house oficial e confere o triplete exato `model.glb`/`preview.png`/
`report.json` com a mesma Spec Resolvida no relatório em disco, materiais do
relatório == IR e materiais do gate == materiais atribuídos da IR, sem restos
`.generation-*`. O teste de falha força o gate a rejeitar (`ok=False`) e
confere destino com só `report.json` (`PUBLICATION`/`REIMPORT_FAILED`,
`artifacts == ["report.json"]`) e staging descartado. Nenhum código de
produção precisou mudar (staging + `os.replace` + report-only já existiam);
o ciclo red ensinou só a distinção materiais-definidos vs atribuídos.
Fast: 113 passed. Integração (pipeline/reimport/publication): 15 passed.
Mypy limpo.
