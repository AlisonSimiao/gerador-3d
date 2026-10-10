# 02: IR com componentes e Âncora

**What to build:** Os Geradores produzem uma representação intermediária independente do Blender contendo geometria, componentes nomeados (volumes fechados, podendo intersectar), materiais e a Âncora do Tipo (ADR 0003, ADR 0013). Validação e inspeção operam na IR sem `bpy`. A Âncora fica na origem: centro da superfície de apoio para objetos apoiados, centro da empunhadura para seguráveis.

**Blocked by:** 01: Registro único de Tipos

**Status:** resolved

- [x] IR expõe componentes nomeados, materiais e Âncora; geradores emitem IR
- [x] Validações de malha, orçamento, materiais e posicionamento operam na IR e são ancoradas na Âncora, não numa "base-centro" genérica
- [x] Sem `bpy`, a Tentativa de Geração inspeciona e valida a IR sem publicar Asset nem Preview
- [x] Suíte rápida verde sobre a nova IR

## Answer

A IR pública agora identifica a semântica da Âncora (`support_surface_center` ou
`grip_center`), mantém componentes nomeados sem intervalos vazios e atribui material a cada face.
O validador confirma cobertura exclusiva das faces, volumes fechados e orientados, materiais e
posicionamento a partir da própria Âncora. Telhados de duas águas e tampas arqueadas foram
fechados. `descriptor.inspect()` continua totalmente independente de `bpy` e não publica arquivos.

## Comments

- Contexto local: [IR pública](../../../blender_worker/geometry/mesh.py),
  [validadores](../../../blender_worker/validators/__init__.py) e
  [testes rápidos](../../../tests/test_ir.py). Verificação: `mypy blender_worker tests` e
  `pytest -q tests/test_ir.py tests/test_schema.py`.
