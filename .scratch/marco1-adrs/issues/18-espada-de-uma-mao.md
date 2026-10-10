# 18: Espada de Uma Mão (v1)

**What to build:** A Espada passa ao contrato v1 do ADR 0009: `blade_length` (0,6–1,1 m, default 0,9), `blade_width` (0,04–0,10 m, default 0,07), `guard_form` (straight|curved|none), `grip_length` (0,10–0,18 m, default 0,14), `pommel_form` (round|faceted|none). A Spec controla lâmina e empunhadura; espessuras e proporções secundárias vêm do Estilo. Âncora no centro da empunhadura (ADR 0003). Variação observável por Seed; Matriz de Aceitação e baseline no padrão da Casa.

**Blocked by:** 17: Suíte de dois níveis e gate de release

**Status:** claimed

- [ ] Contrato v1 da Espada com campos, faixas e defaults do ADR 0009; campos antigos rejeitados
- [ ] Âncora no centro da empunhadura, na origem; validação ancorada confere
- [ ] Variação observável por Seed dentro das intenções da Spec; mesma Seed reproduz o resultado
- [ ] Matriz de Aceitação e baseline visual versionados; orçamento de 2000 triângulos respeitado
