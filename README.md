# SaaS de Assets 3D Low-Poly — Worker (Marco 1)

Geração procedural de assets 3D low-poly organizada por categorias.
IA interpreta prompts → converte em parâmetros JSON → worker constrói os modelos.
A IA **não** executa Python arbitrário: apenas preenche specs validadas.

## Geradores (1 por categoria)

| Categoria | Gerador | Orçamento |
|---|---|---|
| Construções | `house` | ≤ 8000 tris |
| Armas | `sword` | ≤ 2000 tris |
| Natureza | `tree` | ≤ 5000 tris |
| Objetos/móveis | `chest` | ≤ 2000 tris |

## Ambiente

- `uv` (binário único, sem sudo) → venv Python **3.13** → `bpy==5.2.2`.
- O wheel `bpy` exige CPython 3.13 (o Python 3.14 do sistema não é suportado).
- Sem `bpy` (ex.: CI sem Blender), o worker usa o pipeline `fallback`
  puro-Python com o mesmo contrato de artefatos; `report.json` registra
  `"renderer": "fallback"` vs `"bpy"`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13
uv venv --python 3.13
uv pip install -e '.[dev]'   # instala bpy==5.2.2 no Python 3.13
```

## Uso

```bash
uv run python -m blender_worker generate \
  --spec specs/house_default.json \
  --out output/house_001
```

Saída em `--out`: `model.glb`, `preview.png` (512px), `report.json`.
Falha de validação → exit ≠ 0 + motivo no `report.json`.

## Testes e typecheck

```bash
uv run pytest
uv run mypy blender_worker
```

## Layout

Ver `PLANO_MVP.md` §4. Geradores nunca fixam cores: pedem tudo ao
`blender_worker/style.py` (tema `medieval_lowpoly` no MVP).
