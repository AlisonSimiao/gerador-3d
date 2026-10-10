# 14: Taxonomia versionada de falhas

**What to build:** CLI e Relatório de Validação compartilham uma taxonomia versionada de falhas cobrindo entrada, ambiente, construção, validação, renderização, exportação, reimportação e publicação. Consumidores classificam falhas sem depender de texto livre; a mensagem humana é derivada do código (ADR 0011).

**Blocked by:** 13: Relatório de Validação versionado

**Status:** claimed

- [ ] Taxonomia versionada no repositório, com um código estável por classe de falha da pipeline
- [ ] Toda falha da Tentativa mapeia para exatamente um código; CLI e Relatório reportam o mesmo código
- [ ] Mensagens humanas derivadas do código, nunca a fonte da verdade
- [ ] Teste cobre ao menos um caminho de falha por classe da taxonomia
