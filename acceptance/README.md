# Matrizes de Aceitação

Cada diretório contém Specs v1 representativas e `baseline.json`. Previews só
se tornam baseline depois da revisão visual humana; GLBs nunca são versionados.
O gate de release exige a suíte de integração e todos os baselines com
`status: approved`.

## Gate de release

Uma release só é aprovada com o nível de integração verde no ambiente
oficial (Python 3.13 + `bpy` 5.2.2):

```bash
uv run pytest -m integration
```

O nível rápido (`pytest -m "not integration"`, sem `bpy`) é feedback de
desenvolvimento e nunca aprova release sozinho: a inspeção pura-Python nunca
publica `model.glb`/`preview.png` e não constitui Resultado de Geração.

## Validador Khronos glTF (gate de release, ADR 0015)

Além do Blender, os GLBs precisam passar pelo Khronos glTF Validator sem
erros de conformidade. O binário é infraestrutura opcional, nunca
versionado neste repo. Instalação (Linux x86_64):

```bash
versao=2.0.0-dev.3.10
base="https://github.com/KhronosGroup/glTF-Validator/releases"
asset="gltf_validator-${versao}-linux64.tar.xz"
curl -sL -o /tmp/gltf_validator.tar.xz "${base}/download/${versao}/${asset}"
tar -xJf /tmp/gltf_validator.tar.xz -C /tmp
/tmp/gltf_validator --help
```

Validação manual de um GLB gerado pelo caminho oficial (relatório JSON
no stdout, exit ≠ 0 se houver ao menos um erro):

```bash
uv run --python 3.13 python -m blender_worker generate \
  --spec acceptance/chest/canonical.json --out /tmp/chest_check
/tmp/gltf_validator -o /tmp/chest_check/model.glb
```

ou, sobre um diretório, um relatório por Asset (`*.glb` recursivo):

```bash
/tmp/gltf_validator /caminho/para/resultados/
```

O teste `tests/test_gltf_validator_integration.py` localiza o binário via
`GLTF_VALIDATOR` (caminho explícito) ou `gltf_validator` no `PATH`:

```bash
GLTF_VALIDATOR=/tmp/gltf_validator uv run pytest -m integration
```

Sem o binário, o teste pula com o motivo explícito — e a release segue
bloqueada, pois o gate exige zero erros do validador.
