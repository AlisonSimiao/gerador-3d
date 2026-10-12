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
  --out output/house_001 \
  --timeout-seconds 300
```

Saída atômica em `--out`: `model.glb`, prancha `preview.png` (1024 px) e
`report.json`. Um destino ocupado falha sem alterações; use `--force` para
substituí-lo atomicamente. Falhas produzem exit diferente de zero e, quando o
destino puder ser criado, apenas um relatório com código estruturado.

Cada Tentativa oficial roda em um processo Python com `bpy` novo, encerrado e
recolhido ao terminar. O timeout também pode ser definido por
`GERADOR_3D_TIMEOUT_SECONDS`; `GERADOR_3D_PYTHON` seleciona o Python 3.13 do
ambiente Blender quando ele não for o executável que iniciou a CLI.

## Executor de Tentativas

`GenerationAttemptExecutor` é a interface Python de alto nível para uma
Tentativa de Geração completa. Ele recebe uma `GenerationAttempt` e retorna
um `PublishedResult`, `FailedAttempt` ou `CancelledAttempt`; callers não
coordenam validação, Blender, exportação, reimportação ou publicação.

Cada Tentativa possui identidade própria. Retry cria outra Tentativa; a
Impressão Digital da Geração identifica a Spec Resolvida no mesmo ambiente e
não é substituída por Job, Tentativa ou Seed. O Relatório de Validação registra
essas identidades.

Cancelamento é cooperativo no caller e forçado no processo isolado: antes do
commit atômico encerra o grupo de processos, descarta staging e publica apenas
o relatório quando possível. Depois do commit, o Resultado de Geração vence a
corrida. Progresso pode ser observado localmente em etapas monotônicas; é
opcional e nunca altera o desfecho.

## Testes e typecheck

A suíte tem dois níveis:

- **Rápido** (`-m "not integration"`): contrato de Spec, IR e validadores.
  Roda em qualquer Python ≥ 3.11 sem `bpy` (prova mecânica em
  `tests/test_suite_levels.py`); é o feedback de desenvolvimento.
- **Integração** (`-m integration`): construção, renderização, exportação e
  reimportação no ambiente oficial (Python 3.13 + `bpy` 5.2.2), com um teste
  por estágio em `tests/test_pipeline_stages.py`.

```bash
uv run pytest -m "not integration" # suíte rápida: contrato, IR e validadores
uv run pytest -m integration       # obrigatório para release; requer bpy 5.2.2
uv run mypy blender_worker
```

**Gate de release:** nenhuma release é aprovada só com o nível rápido ou com
artefatos fallback — exige o nível de integração verde no ambiente oficial
(job `integration` em `.github/workflows/ci.yml`) e todos os baselines de
`acceptance/` com `status: approved`.

**Fora de escopo:** compatibilidade ampla com Pythons sem `bpy` não é parte
do produto. O `requires-python = ">=3.11"` existe só para o nível rápido; o
ambiente oficial é Python 3.13 + `bpy` 5.2.2 em Linux x86_64.

## Layout

Ver `PLANO_MVP.md` §4. Geradores nunca fixam cores: pedem tudo ao
`blender_worker/style.py` (tema `medieval_lowpoly` no MVP).
