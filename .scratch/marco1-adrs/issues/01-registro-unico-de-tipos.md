# 01: Registro único de Tipos

**What to build:** Cada Tipo de Asset passa a ter um único descritor contratual que reúne schema da Spec, Gerador, Estilos compatíveis, validadores, Orçamento de Triângulos e a Matriz de Aceitação. Todo o pipeline consulta o descritor; orçamento e política deixam de existir em registros paralelos (ADR 0013).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] Os quatro Tipos do Marco 1 registrados num único descritor, consultado por todo o pipeline
- [x] Orçamento de Triângulos vem do descritor; duplicações de orçamento removidas
- [x] Estilo incompatível com o Tipo é rejeitado na fronteira do descritor
- [x] Suíte rápida verde: os quatro Tipos continuam gerando com o comportamento atual

## Answer

O registro imutável e process-wide agora concentra schema, Gerador, Estilos, validadores
executáveis, Orçamento de Triângulos e diretório da Matriz de Aceitação. A fronteira pública do
descritor constrói e valida a IR; carregamento de Spec e pipeline delegam estilo, geração,
validadores e orçamento a ela. Os quatro Tipos foram cobertos pela suíte rápida.

## Comments

- Contexto local: [registro contratual](../../../blender_worker/registry.py) e
  [testes do seam público](../../../tests/test_ir.py). Verificação: `mypy blender_worker tests` e
  `pytest -q tests/test_ir.py tests/test_schema.py`.
