# 10: Preview oficial — prancha 1024 px e perfil de render versionado

**What to build:** O Preview oficial é um PNG quadrado de 1024 px organizado como prancha: vista principal em perspectiva e vistas menores frontal, lateral e traseira. Câmera, iluminação, fundo e gerenciamento de cor vêm de um perfil de render fixo e versionado para o Estilo, com enquadramento automático pelo bounding box da Âncora (ADR 0007, ADR 0008, ADR 0012). O rasterizador auxiliar puro-Python deixa de produzir artefato oficial.

**Blocked by:** 08: Processo Blender limpo por Tentativa de Geração

**Status:** resolved

- [x] `preview.png` oficial: 1024×1024, quatro vistas (principal em perspectiva + frontal, lateral, traseira), fundo neutro
- [x] Perfil de render do Estilo versionado no repositório e aplicado na geração (câmera, luz, fundo, color management)
- [x] Enquadramento automático pelo bounding box; mesmo Estilo → mesma iluminação e fundo
- [x] Fallback não publica `preview.png`

## Answer
O `preview.png` oficial é uma prancha 1024×1024 (4 tiles de 512) renderizada pelo backend Blender via Eevee (`blender_worker/preview.py`), com vistas perspective/front/side/rear do perfil versionado `medieval_lowpoly-v1` (`blender_worker/render_profile.json`: câmera, 2 luzes, fundo [38,40,46], color management Standard) e enquadramento automático pelo bounding box da cena.
O rasterizador puro-Python foi removido de `export.py`; `generate()` exige bpy e a queda de ambiente falha antes de qualquer publicação.
Evidência: fast 82 passed (`tests/test_preview.py` novo: perfil versionado + fallback sem `preview.png`), integração 9 passed (incl. `test_official_preview_uses_versioned_eevee_four_view_profile`), `mypy blender_worker` limpo.
