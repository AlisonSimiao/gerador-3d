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
