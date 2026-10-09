# SaaS de Assets 3D Low-Poly — Plano do MVP

> Geração procedural de assets 3D low-poly organizada por categorias.
> IA interpreta prompts → converte em parâmetros JSON → **Blender** constrói os modelos.
> A IA **não** executa Python arbitrário: apenas preenche specs validadas.

## 1. Decisões registradas

| Tema | Decisão |
|---|---|
| Identidade visual | **Estilo único** no MVP, com **camada de abstração de estilo** para permitir múltiplos estilos no futuro sem refatorar geradores |
| Runtime Blender | **Módulo `bpy` via pip** (venv Python 3.13 gerenciado com `uv`; wheel `bpy 5.2.2` exige CPython 3.13 — o Python 3.14 do sistema não é suportado) |
| Escopo do Marco 1 | **1 gerador por categoria** (`house`, `sword`, `tree`, `chest`) + pipeline completo, sem IA e sem infraestrutura SaaS |

## 2. Categorias

| Categoria | Marco 1 | Versões posteriores |
|---|---|---|
| Construções | `house` (casa) | taverna, torre, cabana, loja |
| Armas e equipamentos | `sword` (espada) | machado, escudo, ferramentas |
| Natureza | `tree` (árvore) | rocha, arbusto, cogumelo |
| Objetos e móveis | `chest` (baú) | mesa, cadeira, barril, estante |

Personagens, criaturas e veículos ficam para versões posteriores (exigem geradores geométricos mais sofisticados).

## 3. Contrato de spec (JSON por tipo)

Cada gerador recebe um JSON validado com parâmetros próprios. Exemplos:

```jsonc
// house
{ "type": "house", "seed": 42,
  "width": 6.0, "depth": 5.0, "floors": 1,
  "roof_type": "gable", "chimney": true,
  "windows": 4, "wall_material": "plaster", "style": "medieval_lowpoly" }

// sword
{ "type": "sword", "seed": 7,
  "blade_length": 0.9, "blade_width": 0.08,
  "guard_type": "straight", "grip_length": 0.15,
  "pommel": "round", "style": "medieval_lowpoly" }

// tree
{ "type": "tree", "seed": 13,
  "trunk_height": 2.5, "trunk_radius": 0.25,
  "canopy_type": "cluster", "leaf_color": "green",
  "lean": 0.05, "style": "medieval_lowpoly" }

// chest
{ "type": "chest", "seed": 3,
  "width": 1.0, "height": 0.6, "depth": 0.6,
  "lid_type": "arched", "bands": 2, "lock": true,
  "style": "medieval_lowpoly" }
```

Regras: campos desconhecidos são rejeitados; aleatoriedade somente via `seed` determinística (reprodutibilidade).

## 4. Arquitetura do worker

```
gerador-3d/
├── pyproject.toml              # uv, python 3.13, bpy 5.2.2
├── blender_worker/
│   ├── main.py                 # CLI: generate --spec X --out Y
│   ├── schema.py               # dataclasses de spec + validação de campos
│   ├── style.py                # camada de estilo (1 tema no MVP)
│   ├── geometry/               # helpers: prism, taper, extrude, merge, bevel leve
│   ├── materials/              # criação de materiais a partir da paleta do estilo
│   ├── generators/
│   │   ├── base.py             # registro + contrato (spec -> objetos bpy)
│   │   ├── buildings/house.py
│   │   ├── weapons/sword.py
│   │   ├── nature/tree.py
│   │   └── props/chest.py
│   ├── validators/             # malha, tris, materiais, origem/escala, GLB
│   └── export.py               # GLB + preview.png + report.json
├── specs/                      # specs JSON de exemplo (1+ por gerador)
├── tests/                      # roda os 4 geradores, asserts nos validadores
├── output/                     # artefatos gerados (gitignore)
└── README.md
```

## 5. Camada de estilo

Geradores **nunca** fixam cores/proporções no código: pedem tudo ao `style.py`
(ex.: `style.wall_color("plaster")`, `style.metal("steel")`).

- MVP entrega um único tema: `medieval_lowpoly`.
- Novo estilo no futuro = novo dicionário de paleta/parâmetros, sem tocar nos geradores.

## 6. Critérios de qualidade (validadores)

Rodam **antes** do export; falha bloqueia a geração (exit code ≠ 0 + motivo no `report.json`):

1. Malha válida: sem faces degeneradas nem geometria não-manifold (checagem via `bmesh`).
2. Contagem de triângulos dentro do orçamento por categoria (ex.: props ≤ 2k, construções ≤ 8k — valores a calibrar no Marco 1).
3. Toda a malha com material atribuído.
4. Origem na base-centro do objeto, escala em metros, rotação zerada.
5. GLB válido: re-importação como smoke test.
6. Preview renderizado (512px, câmera auto-enquadrada pelo bounding box, fundo neutro) para avaliação visual.

Validação técnica não substitui avaliação visual: manter uma pequena biblioteca de assets de referência + testes visuais por gerador.

## 7. CLI e artefatos

```bash
uv run python -m blender_worker generate \
  --spec specs/house_default.json \
  --out output/house_001
```

Saída em `--out`:

```
house_001/
├── model.glb      # asset exportado
├── preview.png    # render para avaliação
└── report.json    # spec usada, nº de tris, resultado de cada validador
```

## 8. Ambiente

- `uv` (binário único, sem sudo) → venv Python 3.13 → `pip install bpy==5.2.2`.
- Nada é instalado no Python do sistema.
- Download do wheel `bpy`: ~300MB.

## 9. Ordem de execução

1. **Setup**: instalar `uv` → venv Python 3.13 → instalar `bpy` → smoke test (renderizar um cubo).
2. **Pipeline base**: scaffold do pacote + `schema.py` + `style.py` + helpers de geometria + validadores + export.
3. **Gerador `house`** ponta a ponta (prova o pipeline inteiro).
4. **Geradores `tree`, `sword`, `chest`**.
5. **Fechamento**: specs de exemplo, testes automatizados (os 4 geradores passam nos validadores), README.

## 10. Riscos

- API do Blender 5.2 tem diferenças da 4.x (ex.: sockets do Principled BSDF) — mitigado pelo smoke test no passo 1.
- Orçamentos de triângulos ainda precisam de calibração visual no Marco 1.

## 11. Fora de escopo do Marco 1

- IA (tradução texto → spec).
- Backend SaaS, autenticação, fila de jobs, billing.
- UI de geração (o protótipo atual organiza parâmetros; a conexão com o backend vem depois).
