# 04 — Migrar a CLI para GenerationAttemptExecutor

**What to build:** Fazer a CLI oficial consumir o novo executor sem alterar a experiência existente, tornando-a um caller fino que traduz argumentos em uma Tentativa e o desfecho terminal em saída de processo.

**Blocked by:** 03 — GenerationAttemptExecutor e desfechos tipados.

**Status:** resolved

- [x] O comando oficial cria uma Tentativa e chama exclusivamente o executor de alto nível.
- [x] A forma do comando e os argumentos existentes continuam aceitos, incluindo destino, `--force` e timeout configurável.
- [x] Uma execução bem-sucedida conserva código de saída zero, mensagem útil e o trio indivisível de Asset, Preview e Relatório de Validação.
- [x] Falhas esperadas conservam código de saída diferente de zero e expõem o mesmo código estruturado em stderr sem exigir interpretação de texto livre.
- [x] Um destino ocupado sem `--force` permanece intacto e falha segundo o contrato existente.
- [x] `--force` continua substituindo apenas por publicação atômica, sem misturar artefatos de Resultados diferentes.
- [x] O timeout explícito e o default operacional conservam o comportamento do Marco 1.
- [x] A CLI não conhece nem coordena etapas internas e não recria tratamento de falhas ou construção de relatórios.
- [x] Testes de compatibilidade demonstram que scripts que dependem de argumentos, códigos de saída, stderr e artefatos continuam funcionando.

## Answer

A CLI tornou-se caller do executor e preservou argumentos, códigos de saída, stderr estruturado, `--force`, timeout e publicação atômica.

Verificação no worktree `ticket/m2-04` sobre `integration/marco2-generation-attempt-executor` (0920f3c): sete dos oito critérios já estavam satisfeitos pelo código anterior e foram confirmados por teste — `main()` monta uma `GenerationAttempt` e chama apenas `GenerationAttemptExecutor.execute` (`blender_worker/main.py:39`); a forma do comando, `--force` e `--timeout-seconds` continuam aceitos e traduzidos para `ExistingResultPolicy` e `timeout_seconds`; sucesso sai com 0 e imprime `ok: N tris -> out`; falha esperada sai com 1 e escreve `<code>: <mensagem>` em stderr a partir do `error.code` do relatório; destino ocupado sem `--force` preserva cada byte do Resultado de Geração anterior; `--force` publica o trio sem artefatos remanescentes; e o default operacional de timeout continua vindo de `GERADOR_3D_TIMEOUT_SECONDS`/`DEFAULT_TIMEOUT_SECONDS`.

Lacuna fechada: o cancelamento era tratado como falha comum, compartilhando o código de saída 1, o que impede um script de shell de distinguir uma interrupção intencional de um Gerador ou ambiente quebrado. `CancelledAttempt` agora recebe o código de saída 130 (convenção 128+SIGINT), mantendo `execution.cancelled` em stderr e o exit 1 das demais falhas; os códigos do contrato do Marco 1 também passaram a constantes nomeadas (`EXIT_SUCCESS`, `EXIT_UNSUCCESSFUL`, `EXIT_MISUSE`, `EXIT_CANCELLED`) em `blender_worker/main.py`.

`tests/test_cli_compatibility.py` cobre a superfície da CLI sem afirmar prosa: forma do comando e erro de uso, construção de uma única `Tentativa` a partir de `argv`, trio indivisível com exit 0 e stderr vazio, destino ocupado sem `--force`, `--force` substituindo sem misturar artefatos, timeout explícito, default operacional, código estruturado de falha e código de saída do cancelamento. Suíte não-integração 241 passando, integração oficial 29 passando e 1 pulada, `mypy blender_worker` sem issues.
