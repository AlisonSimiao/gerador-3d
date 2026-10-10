# 07: Casa — variação observável por Seed

**What to build:** A Seed seleciona variação visual secundária, controlada e repetível: assimetrias controladas, pequenas proporções estilísticas e detalhes do Estilo. Ela nunca contraria dimensões, opções, função ou família de cores declaradas pela Spec. Seed aceita mas ignorada viola o contrato (ADR 0004, ADR 0008).

**Blocked by:** 06: Casa — roof_form e wall_finish

**Status:** claimed

- [ ] Duas Seeds distintas produzem Previews observavelmente diferentes, mas reconhecivelmente a mesma Casa (mesmas dimensões/opções/família de cores)
- [ ] Mesma Spec + mesma Seed + mesmo ambiente → geometria e materiais equivalentes por propriedades estáveis (identidade binária não é o contrato)
- [ ] A Seed varia detalhes secundários do Estilo (ex.: proporção de beiral, detalhe de enxaimel, inclinação imperceptível de elementos), nunca a estrutura pedida
