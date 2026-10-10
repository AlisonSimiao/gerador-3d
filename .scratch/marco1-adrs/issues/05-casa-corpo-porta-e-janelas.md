# 05: Casa — corpo, porta e janelas

**What to build:** O Gerador da Casa mede `width`/`depth` como o corpo externo das paredes, sem beirais (beira do telhado é componente separado e não infla as dimensões declaradas). Uma porta está sempre presente. `window_count` é o total, distribuído deterministicamente entre as quatro fachadas. Silhueta legível e dentro do Orçamento de Triângulos (ADR 0008, ADR 0009).

**Blocked by:** 02: IR com componentes e Âncora, 04: Contrato v1 da Casa

**Status:** resolved

- [x] Extensão do corpo da malha confere com as dimensões declaradas da Spec Resolvida (tolerância de exportação)
- [x] Porta sempre presente como componente visual; `window_count` distribuído deterministicamente — mesma Seed, mesma distribuição
- [x] Componentes nomeados na IR: corpo, telhado, porta, janelas
- [x] Geração da Casa canônica verde no pipeline completo, dentro do orçamento

## Answer

A IR agora expõe limites de componentes e dos volumes fechados desconectados que os
compõem. Isso permite verificar diretamente que o corpo canônico mede exatamente 6 × 5 m,
enquanto o beiral pertence apenas ao telhado e ultrapassa essas medidas. A porta permanece
um volume visual nomeado em todas as variantes exercitadas. Dez janelas resultam em dez
volumes distribuídos deterministicamente 3/3/2/2 entre as quatro fachadas para a mesma
Spec. A Casa canônica também passou pelo pipeline Blender oficial dentro do orçamento.

## Comments

- Context pointer: implementação em `05ac97d` (`Verify house body doors and windows (#05)`).
- Tip da integração `6806890` incorporado antes da conclusão.
- Verificação pós-merge: 30 testes focados passaram; mypy sem erros.
