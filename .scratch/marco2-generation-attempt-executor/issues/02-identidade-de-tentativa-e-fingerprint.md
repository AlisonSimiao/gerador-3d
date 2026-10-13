# 02 — Identidade da Tentativa e Impressão Digital da Geração

**What to build:** Tornar a identidade de cada Tentativa e a Impressão Digital da Geração observáveis no Relatório de Validação, distinguindo-as de Job e Seed e cumprindo os requisitos de proveniência e proteção de entradas inválidas.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [x] Cada Tentativa recebe uma identidade opaca, não vazia e independente de Job, Seed e Impressão Digital da Geração.
- [x] Duas Tentativas da mesma Spec mantêm identidades distintas mesmo quando produzem a mesma Impressão Digital.
- [x] A Impressão Digital é derivada da Spec Resolvida e das versões relevantes do worker, Blender e perfil de Estilo.
- [x] Representações equivalentes da entrada que resolvem para a mesma Spec no mesmo ambiente produzem a mesma Impressão Digital.
- [x] A Impressão Digital não depende da identidade de Job ou Tentativa e não usa a Seed isoladamente como identidade.
- [x] Relatórios de sucesso registram a identidade da Tentativa e a Impressão Digital da Geração.
- [x] Relatórios de entrada inválida registram a identidade da Tentativa e uma hash segura da entrada sem copiar conteúdo arbitrário rejeitado.
- [x] Os novos campos possuem contrato documentado e testes de estabilidade compatíveis com o schema versionado do relatório.
- [x] A alteração não muda a geometria, o Preview, a publicação atômica nem o significado dos campos existentes.

## Answer

Relatórios agora correlacionam a Tentativa; sucessos incluem fingerprint canônico e entradas inválidas incluem somente hash segura. A integração provou identidades distintas com fingerprint idêntico para a mesma geração lógica.

Verificação contra o código existente (`blender_worker/attempts.py`, `blender_worker/reports.py`), sem alterar a implementação: `AttemptId` recusa valores vazios/brancos e `new_attempt_id()` deriva `uuid4`; `generation_fingerprint` hasheia `resolved_spec` + `WORKER_VERSION` + versão do Blender + `RENDER_PROFILE` com chaves ordenadas; `success_report` grava `attempt_id` e `generation_fingerprint`; `failure_report` grava `attempt_id` e `input_hash` (`resolved_spec` nulo) sem copiar a entrada.

Lacuna real fechada: os critérios de derivação e independência da Impressão Digital só eram provados por um teste marcado `integration` (que exige Blender). Adicionados testes rápidos no seam de contrato do relatório: literal conhecido-bom do digest para um ambiente fixado (detecta mudança acidental nos insumos da derivação), sensibilidade a cada versão relevante, equivalência entre representações da entrada que resolvem para a mesma Spec Resolvida (incluindo ordem de chaves), independência de `attempt_id`, e Seed como insumo e não como identidade. Adicionados ainda: `attempt_id` opaco/não vazio, unicidade das identidades geradas, e o contrato `attempt_id` + `input_hash` do relatório de entrada inválida sem `generation_fingerprint` e sem a entrada rejeitada. ADR 0014 passou a nomear `generation_fingerprint` e `input_hash` para ancorar o contrato documentado.

Nenhuma mudança em geometria, Preview, publicação atômica ou significado de campos existentes.
