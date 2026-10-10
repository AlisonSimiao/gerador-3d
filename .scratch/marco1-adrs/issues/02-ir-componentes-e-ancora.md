# 02: IR com componentes e Âncora

**What to build:** Os Geradores produzem uma representação intermediária independente do Blender contendo geometria, componentes nomeados (volumes fechados, podendo intersectar), materiais e a Âncora do Tipo (ADR 0003, ADR 0013). Validação e inspeção operam na IR sem `bpy`. A Âncora fica na origem: centro da superfície de apoio para objetos apoiados, centro da empunhadura para seguráveis.

**Blocked by:** 01: Registro único de Tipos

**Status:** ready-for-agent

- [ ] IR expõe componentes nomeados, materiais e Âncora; geradores emitem IR
- [ ] Validações de malha, orçamento, materiais e posicionamento operam na IR e são ancoradas na Âncora, não numa "base-centro" genérica
- [ ] Sem `bpy`, a Tentativa de Geração inspeciona e valida a IR sem publicar Asset nem Preview
- [ ] Suíte rápida verde sobre a nova IR
