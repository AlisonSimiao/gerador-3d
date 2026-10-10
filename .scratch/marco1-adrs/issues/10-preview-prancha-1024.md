# 10: Preview oficial — prancha 1024 px e perfil de render versionado

**What to build:** O Preview oficial é um PNG quadrado de 1024 px organizado como prancha: vista principal em perspectiva e vistas menores frontal, lateral e traseira. Câmera, iluminação, fundo e gerenciamento de cor vêm de um perfil de render fixo e versionado para o Estilo, com enquadramento automático pelo bounding box da Âncora (ADR 0007, ADR 0008, ADR 0012). O rasterizador auxiliar puro-Python deixa de produzir artefato oficial.

**Blocked by:** 08: Processo Blender limpo por Tentativa de Geração

**Status:** claimed

- [ ] `preview.png` oficial: 1024×1024, quatro vistas (principal em perspectiva + frontal, lateral, traseira), fundo neutro
- [ ] Perfil de render do Estilo versionado no repositório e aplicado na geração (câmera, luz, fundo, color management)
- [ ] Enquadramento automático pelo bounding box; mesmo Estilo → mesma iluminação e fundo
- [ ] Fallback não publica `preview.png`
