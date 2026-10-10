# 01: Registro único de Tipos

**What to build:** Cada Tipo de Asset passa a ter um único descritor contratual que reúne schema da Spec, Gerador, Estilos compatíveis, validadores, Orçamento de Triângulos e a Matriz de Aceitação. Todo o pipeline consulta o descritor; orçamento e política deixam de existir em registros paralelos (ADR 0013).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Os quatro Tipos do Marco 1 registrados num único descritor, consultado por todo o pipeline
- [ ] Orçamento de Triângulos vem do descritor; duplicações de orçamento removidas
- [ ] Estilo incompatível com o Tipo é rejeitado na fronteira do descritor
- [ ] Suíte rápida verde: os quatro Tipos continuam gerando com o comportamento atual
