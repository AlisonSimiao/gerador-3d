# Escopo dos Tipos do Marco 1

O contrato inicial contém quatro Tipos estreitos: Casa com exterior fechado, Espada de Uma Mão, Árvore individual e Baú Fechado. Elementos como portas, janelas, chaminés, tampas e fechos são representações visuais, não peças funcionais.

## Consequences

Interiores navegáveis, edifícios modulares, outras famílias de lâminas, conjuntos de vegetação e objetos animáveis exigem Tipos ou contratos futuros. A forma da copa de uma Árvore é independente da paleta de sua folhagem; `pine` não é uma cor.

As dimensões da Casa medem o corpo externo das paredes, sem beirais; sua contagem de janelas é total e distribuída deterministicamente entre fachadas. Na Espada, a Spec controla lâmina e empunhadura, enquanto espessuras e proporções secundárias vêm do Estilo. A inclinação da Árvore é um ângulo em graus aplicado ao tronco e à copa. As dimensões do Baú medem seu envelope externo completo, incluindo tampa e cintas.

Os campos específicos candidatos a `v1` são:

- **Casa:** `width`, `depth`, `floors`, `roof_form` (`gable | hip`), `window_count`, `wall_finish` (`plaster | timber | stone`) e `has_chimney`; uma porta está sempre presente.
- **Espada de Uma Mão:** `blade_length`, `blade_width`, `guard_form` (`straight | curved | none`), `grip_length` e `pommel_form` (`round | faceted | none`).
- **Árvore:** `trunk_height`, `trunk_radius`, `canopy_form` (`clustered | round | conical`), `foliage_palette` (`green | autumn | dark_green`) e `lean_degrees`.
- **Baú Fechado:** `width`, `height`, `depth`, `lid_form` (`arched | flat`), `band_count` e `has_lock`.

Ornamentações adicionais pertencem à variação por Seed e ao Estilo, não a novos campos do contrato inicial.

As faixas iniciais de calibração são:

- **Comum:** `seed` entre `0` e `4.294.967.295`; `style` usa `medieval_lowpoly` por default.
- **Casa:** `width` 3–12 m (default 6), `depth` 3–10 m (default 5), `floors` 1–3 (default 1), `window_count` 0–16 (default 4).
- **Espada:** `blade_length` 0,6–1,1 m (default 0,9), `blade_width` 0,04–0,10 m (default 0,07), `grip_length` 0,10–0,18 m (default 0,14).
- **Árvore:** `trunk_height` 1,5–8 m (default 3), `trunk_radius` 0,12–0,60 m (default 0,25), `lean_degrees` 0–20° (default 5°).
- **Baú:** `width` 0,6–1,8 m (default 1), `height` 0,4–1,1 m (default 0,6), `depth` 0,4–1,0 m (default 0,6), `band_count` 0–4 (default 2).

Essas faixas podem ser reduzidas antes do congelamento de `spec_version: 1`, conforme os resultados da Matriz de Aceitação.
