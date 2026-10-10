# 05: Casa — corpo, porta e janelas

**What to build:** O Gerador da Casa mede `width`/`depth` como o corpo externo das paredes, sem beirais (beira do telhado é componente separado e não infla as dimensões declaradas). Uma porta está sempre presente. `window_count` é o total, distribuído deterministicamente entre as quatro fachadas. Silhueta legível e dentro do Orçamento de Triângulos (ADR 0008, ADR 0009).

**Blocked by:** 02: IR com componentes e Âncora, 04: Contrato v1 da Casa

**Status:** claimed

- [ ] Extensão do corpo da malha confere com as dimensões declaradas da Spec Resolvida (tolerância de exportação)
- [ ] Porta sempre presente como componente visual; `window_count` distribuído deterministicamente — mesma Seed, mesma distribuição
- [ ] Componentes nomeados na IR: corpo, telhado, porta, janelas
- [ ] Geração da Casa canônica verde no pipeline completo, dentro do orçamento
