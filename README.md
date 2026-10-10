# SaaS de Assets 3D Low-Poly — Worker (Marco 1)

Geração procedural de assets 3D low-poly organizada por categorias.
IA interpreta prompts → converte em parâmetros JSON → worker constrói os modelos.
A IA **não** executa Python arbitrário: apenas preenche specs validadas.

## Tipos de Asset

| Categoria | Gerador | Orçamento |
|---|---|---|
| Construções | `house` | ≤ 8000 tris |
| Armas | `sword` | ≤ 2000 tris |
| Natureza | `tree` | ≤ 5000 tris |
| Objetos/móveis | `chest` | ≤ 2000 tris |

## Ambiente oficial

- `uv` (binário único, sem sudo) → venv Python **3.13** → `bpy==5.2.2`.
- O wheel `bpy` exige CPython 3.13 (o Python 3.14 do sistema não é suportado).
- Linux `x86_64` é a única plataforma oficial do Marco 1.
- Sem `bpy`, somente a inspeção rápida da IR está disponível; ela nunca
  publica `model.glb` ou `preview.png` e não constitui Resultado de Geração.

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

Saída atômica em `--out`: `model.glb`, prancha `preview.png` (1024 px) e
`report.json`. Um destino ocupado falha sem alterações; use `--force` para
substituí-lo atomicamente. Falhas produzem exit diferente de zero e, quando o
destino puder ser criado, apenas um relatório com código estruturado.

## Testes e typecheck

```bash
uv run pytest -m "not integration" # suíte rápida: contrato, IR e validadores
uv run pytest -m integration       # obrigatório para release; requer bpy 5.2.2
uv run mypy blender_worker
```

## Layout

Ver `PLANO_MVP.md` §4. Geradores nunca fixam cores: pedem tudo ao
`blender_worker/style.py` (tema `medieval_lowpoly` no MVP).
