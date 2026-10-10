# 06: Casa — roof_form e wall_finish

**What to build:** `roof_form` gable e hip produzem silhuetas estruturalmente distintas e corretas. `wall_finish` plaster, timber e stone alteram a aparência da fachada segundo a paleta do Estilo `medieval_lowpoly` (timber = enxaimel; pedra = blocos; reboco = plano). Nenhuma opção `flat` no contrato. Geradores continuam sem fixar cores: tudo vem do Estilo (ADR 0004, ADR 0008, ADR 0009).

**Blocked by:** 05: Casa — corpo, porta e janelas

**Status:** ready-for-agent

- [ ] gable e hip distinguíveis na silhueta, ambos dentro do Orçamento de Triângulos
- [ ] plaster/timber/stone visualmente distintos, com cores e proporções do Estilo — sem cores fixadas no Gerador
- [ ] Especificações de exemplo cobrem as combinações estruturais de maior risco (roof_form × wall_finish)
- [ ] Geração verde para cada combinação da matriz de cobertura
