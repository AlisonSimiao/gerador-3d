# 14: Taxonomia versionada de falhas

**What to build:** CLI e Relatório de Validação compartilham uma taxonomia versionada de falhas cobrindo entrada, ambiente, construção, validação, renderização, exportação, reimportação e publicação. Consumidores classificam falhas sem depender de texto livre; a mensagem humana é derivada do código (ADR 0011).

**Blocked by:** 13: Relatório de Validação versionado

**Status:** resolved

- [x] Taxonomia versionada no repositório, com um código estável por classe de falha da pipeline
- [x] Toda falha da Tentativa mapeia para exatamente um código; CLI e Relatório reportam o mesmo código
- [x] Mensagens humanas derivadas do código, nunca a fonte da verdade
- [x] Teste cobre ao menos um caminho de falha por classe da taxonomia

## Answer

`generate()` agora envolve cada etapa com seu código (`export.py`): construção→`build.failed`, validação→`validation.failed` explícito, exportação glTF→`export.failed`, reimportação→`reimport.failed` (inclusive exceção), `render_official_preview`→`render.failed`, `os.replace`→`publication.failed`; o `except` genérico segue como `build.failed`. A CLI (`main.py`) imprime `MESSAGES[código]` em vez de texto livre, e o runner deriva `stage` via `stage_for_code`. `tests/test_failure_taxonomy.py` cobre um caminho por classe (9 códigos + paridade CLI/relatório), reaproveitando `assert_report_contract` do ticket 13. Fast: 105 passed; integração: 10 passed; mypy limpo.
