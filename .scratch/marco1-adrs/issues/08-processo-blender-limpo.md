# 08: Processo Blender limpo por Tentativa de Geração

**What to build:** Uma geração oficial só existe com o Blender: cada Tentativa de Geração roda em um processo Blender limpo, encerrado ao fim da execução, sem vazamento de estado global entre Assets. Blender indisponível ou com integração falha → falha explícita, nunca sucesso. O fallback puro-Python apenas inspeciona e testa a IR e não publica `model.glb` nem `preview.png`; artefatos do fallback não são um Resultado de Geração oficial (ADR 0001, ADR 0010, ADR 0013).

**Blocked by:** 02: IR com componentes e Âncora

**Status:** resolved

- [x] Sem `bpy`: falha de ambiente explícita (exit ≠ 0, código estruturado), sem Asset/Preview publicados
- [x] Com `bpy`: cada Tentativa usa processo Blender limpo encerrado ao fim; duas Tentativas seguidas não se contaminam
- [x] Relatório registra o backend realmente utilizado e as versões do ambiente
- [x] Suíte rápida (sem `bpy`) cobre o caminho de inspeção da IR; caminho oficial coberto na suíte de integração

## Answer

A geração oficial agora é orquestrada por um runner que cria um novo processo Python com `bpy`
para cada Tentativa, espera e recolhe esse processo. O limite é configurável por CLI ou ambiente;
no timeout, todo o grupo de processo é encerrado, o staging da Tentativa é descartado e uma falha
`environment.timeout` é registrada. Ausência de `bpy` produz `environment.unavailable`, backend
nulo e somente `report.json`. Relatórios de sucesso registram backend, versões e PID do processo
isolado; `inspect()` permanece o único caminho puro-Python e não publica artefatos.

## Comments

- Contexto local: [runner oficial](../../../blender_worker/process_runner.py),
  [entrada do processo filho](../../../blender_worker/generation_process.py) e
  [testes do processo](../../../tests/test_process_runner.py). Verificação rápida: 46 testes;
  integração oficial: geração de casa e duas gerações determinísticas em processos distintos;
  `mypy blender_worker tests` verde.
