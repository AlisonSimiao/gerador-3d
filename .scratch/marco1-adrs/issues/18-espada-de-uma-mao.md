# 18: Espada de Uma Mão (v1)

**What to build:** A Espada passa ao contrato v1 do ADR 0009: `blade_length` (0,6–1,1 m, default 0,9), `blade_width` (0,04–0,10 m, default 0,07), `guard_form` (straight|curved|none), `grip_length` (0,10–0,18 m, default 0,14), `pommel_form` (round|faceted|none). A Spec controla lâmina e empunhadura; espessuras e proporções secundárias vêm do Estilo. Âncora no centro da empunhadura (ADR 0003). Variação observável por Seed; Matriz de Aceitação e baseline no padrão da Casa.

**Blocked by:** 17: Suíte de dois níveis e gate de release

**Status:** resolved

- [x] Contrato v1 da Espada com campos, faixas e defaults do ADR 0009; campos antigos rejeitados
- [x] Âncora no centro da empunhadura, na origem; validação ancorada confere
- [x] Variação observável por Seed dentro das intenções da Spec; mesma Seed reproduz o resultado
- [x] Matriz de Aceitação e baseline visual versionados; orçamento de 2000 triângulos respeitado

## Answer
Espada v1 fechada no padrão da Casa: contrato ADR 0009 travado por testes
(`tests/test_sword.py`, 21 testes — faixas/defaults exatos, campos antigos
rejeitados), âncora `grip_center` na origem verificada para todas as opções
de guarda/pomo (docstring corrigida), Seed com variação observável e
reprodução idêntica. Matriz `acceptance/sword/` com 8 specs (canonical,
3 opções, risco none×none, limites min/max, seed-variant), `baseline.json`
todo `ready-for-human` com aprovador nulo, e `review/` com 8 `preview.png`
1024px gerados pela via oficial Blender. Orçamento folgado: pico de 164 tris
contra 2000. Fast 151 green, integração da matriz green (~7 min), mypy limpo.

## Comments

Em 2026-10-12, o revisor humano (`user`) aprovou os 8 previews da matriz de
Espada regenerados com o perfil `medieval_lowpoly-v2`; o baseline registra a
aprovação por Spec.
