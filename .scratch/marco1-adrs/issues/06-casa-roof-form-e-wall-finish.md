# 06: Casa — roof_form e wall_finish

**What to build:** `roof_form` gable e hip produzem silhuetas estruturalmente distintas e corretas. `wall_finish` plaster, timber e stone alteram a aparência da fachada segundo a paleta do Estilo `medieval_lowpoly` (timber = enxaimel; pedra = blocos; reboco = plano). Nenhuma opção `flat` no contrato. Geradores continuam sem fixar cores: tudo vem do Estilo (ADR 0004, ADR 0008, ADR 0009).

**Blocked by:** 05: Casa — corpo, porta e janelas

**Status:** resolved

- [x] gable e hip distinguíveis na silhueta, ambos dentro do Orçamento de Triângulos
- [x] plaster/timber/stone visualmente distintos, com cores e proporções do Estilo — sem cores fixadas no Gerador
- [x] Especificações de exemplo cobrem as combinações estruturais de maior risco (roof_form × wall_finish)
- [x] Geração verde para cada combinação da matriz de cobertura

## Answer

Matriz 2×3 roof_form × wall_finish verde no seam `descriptor.inspect`: gable=5 faces vs hip=12, todas dentro do teto 8000 tris (`test_house_roof_form_by_wall_finish_matrix_is_green_within_budget`, 6 casos). Fachadas timber/stone leem proporções e cores do Estilo (`timber_facade`/`stone_facade` em `style.py`); teste de override de paleta prova que o Gerador não fixa cores (`test_house_facade_details_follow_the_style_not_the_generator`). Mutantes (largura de viga, cor chapada) quebram os testes. Matriz versionada/baselines seguem com o ticket 16 — nada em `acceptance/` foi tocado.
Evidência: fast 88 passed; integration house 2 passed; mypy limpo (26 arquivos).
