# 02 — Identidade da Tentativa e Impressão Digital da Geração

**What to build:** Tornar a identidade de cada Tentativa e a Impressão Digital da Geração observáveis no Relatório de Validação, distinguindo-as de Job e Seed e cumprindo os requisitos de proveniência e proteção de entradas inválidas.

**Blocked by:** None — can start immediately.

**Status:** resolved

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
