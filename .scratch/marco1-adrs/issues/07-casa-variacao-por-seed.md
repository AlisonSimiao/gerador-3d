# 07: Casa — variação observável por Seed

**What to build:** A Seed seleciona variação visual secundária, controlada e repetível: assimetrias controladas, pequenas proporções estilísticas e detalhes do Estilo. Ela nunca contraria dimensões, opções, função ou família de cores declaradas pela Spec. Seed aceita mas ignorada viola o contrato (ADR 0004, ADR 0008).

**Blocked by:** 06: Casa — roof_form e wall_finish

**Status:** resolved

- [x] Duas Seeds distintas produzem Previews observavelmente diferentes, mas reconhecivelmente a mesma Casa (mesmas dimensões/opções/família de cores)
- [x] Mesma Spec + mesma Seed + mesmo ambiente → geometria e materiais equivalentes por propriedades estáveis (identidade binária não é o contrato)
- [x] A Seed varia detalhes secundários do Estilo (ex.: proporção de beiral, detalhe de enxaimel, inclinação imperceptível de elementos), nunca a estrutura pedida

## Answer

Seed já era consumida pelo gerador (`house.py`: jitter de `roof_h` ±0.02, beiral 0.25–0.35, lado da chaminé); sweep de 50 seeds × 4 combos confirmou invariantes, então nenhum endurecimento foi preciso. Provas em `tests/test_ir.py` (via `descriptor.inspect`, sem bpy): mesma spec+seed → vértices/faces/materiais/componentes idênticos; seeds 7 vs 8 → vértices/telhado/chaminé diferem mas corpo, componentes, materiais/cores, janelas e tris idênticos; sweep 20 seeds × gable/plaster + hip/timber + hip/stone-3pav → corpo, componentes, cor `wall_*`, janelas/porta e faces do telhado estáveis, tudo verde dentro do orçamento. Fast suite 100 passed; mypy limpo.
