# SaaS de Assets 3D Low-Poly — Plano do MVP

> Geração procedural de assets 3D low-poly organizada por categorias.
> IA interpreta prompts → converte em parâmetros JSON → **Blender** constrói os modelos.
> A IA **não** executa Python arbitrário: apenas preenche specs validadas.

Este plano é um índice: as decisões vivem em `docs/adr/*.md`, o contrato
de entrada em `blender_worker/schemas/spec-v1.schema.json` e o uso em
`README.md`. Em caso de divergência, valem o schema e os ADRs.

## 1. Decisões registradas

| Tema | Onde |
|---|---|
| Backend autoritativo, determinismo, IR, isolamento | ADR 0001, 0002, 0010, 0013 |
| Tipos do Marco 1 e vocabulário do domínio | ADR 0009, `GLOSSARY.md` |
| Specs versionadas e validação estrita | ADR 0005 |
| Validação Blender, publicação atômica, relatório | ADR 0006, 0007 |
| Coordenadas, preview, baselines, conformidade | ADR 0007, 0010, 0012, 0015 |
| Migração e conclusão do Marco 1 | ADR 0017 |

## 2. Categorias (Marco 1: 1 gerador por categoria)

| Categoria | Gerador | Orçamento |
|---|---|---|
| Construções | `house` (casa, exterior fechado) | ≤ 8000 tris |
| Armas e equipamentos | `sword` (espada de uma mão) | ≤ 2000 tris |
| Natureza | `tree` (árvore individual) | ≤ 5000 tris |
| Objetos e móveis | `chest` (baú fechado) | ≤ 2000 tris |

Detalhes de escopo no ADR 0009. Sem IA e sem infraestrutura SaaS no Marco 1.

## 3. Contrato de spec (v1)

Autoridade: `blender_worker/schemas/spec-v1.schema.json`. Exemplos
completos em `specs/*_default.json`. Resumo dos campos por tipo:

```jsonc
// house — corpo externo, porta sempre presente
{ "spec_version": 1, "type": "house", "seed": 42,
  "width": 6.0, "depth": 5.0, "floors": 1,
  "roof_form": "gable", "wall_finish": "plaster",
  "window_count": 4, "has_chimney": true,
  "style": "medieval_lowpoly" }

// sword — lâmina e empunhadura; secundários vêm do estilo
{ "spec_version": 1, "type": "sword", "seed": 7,
  "blade_length": 0.9, "blade_width": 0.07,
  "guard_form": "straight", "grip_length": 0.14,
  "pommel_form": "round", "style": "medieval_lowpoly" }

// tree — inclinação em graus aplicada a tronco e copa
{ "spec_version": 1, "type": "tree", "seed": 13,
  "trunk_height": 3.0, "trunk_radius": 0.25,
  "canopy_form": "clustered", "foliage_palette": "green",
  "lean_degrees": 5.0, "style": "medieval_lowpoly" }

// chest — envelope externo completo, sem interior
{ "spec_version": 1, "type": "chest", "seed": 3,
  "width": 1.0, "height": 0.6, "depth": 0.6,
  "lid_form": "arched", "band_count": 2, "has_lock": true,
  "style": "medieval_lowpoly" }
```

Regras (ADR 0005): campos desconhecidos são rejeitados; aleatoriedade
somente via `seed` determinística (reprodutibilidade).

## 4. Arquitetura do worker

Ver `README.md` (uso, ambiente, testes) e o código em `blender_worker/`:
`main.py` (CLI) → `process_runner.py` (processo isolado por tentativa) →
`export.py` (GLB + preview + relatório) sobre `generators/`, `geometry/`,
`materials/`, `validators/` e `style.py` (tema `medieval_lowpoly`).

## 5. Camada de estilo

Geradores **nunca** fixam cores/proporções no código: pedem tudo ao
`style.py`. Novo estilo no futuro = novo dicionário de paleta/parâmetros,
sem tocar nos geradores (ADR 0008).

## 6. Critérios de qualidade (validadores)

Falha bloqueia a geração (exit ≠ 0 + motivo no `report.json`). O gate de
release exige ainda a suíte de integração verde, os GLBs aprovados pelo
Blender **e** pelo Khronos glTF Validator, e os baselines com aprovação
humana (ADR 0015, ADR 0017, `acceptance/README.md`):

1. Malha válida: sem faces degeneradas nem geometria não-manifold.
2. Triângulos dentro do orçamento da categoria (§2).
3. Toda a malha com material atribuído.
4. Âncora na origem, escala em metros, rotação zerada (ADR 0007).
5. GLB válido: reimportação no Blender + Khronos glTF Validator.
6. Preview em prancha 4-vistas de 1024 px (perfil `medieval_lowpoly-v1`)
   para avaliação visual (ADR 0010).

Validação técnica não substitui avaliação visual: `acceptance/` guarda as
matrizes e os baselines por tipo.

## 7. CLI e artefatos

Ver `README.md` §Uso. Saída atômica em `--out`: `model.glb`,
`preview.png` (prancha 1024 px) e `report.json` (ADR 0007).

## 8. Ambiente

Ver `README.md` §Ambiente oficial: `uv` → venv Python 3.13 →
`bpy==5.2.2`, Linux `x86_64` (ADR 0010).

## 9. Ordem de execução

Concluída no Marco 1 (ADR 0017): pipeline base, fatia vertical da casa,
migração de árvore/espada/baú, matrizes de aceitação e gates.

## 10. Riscos

Ver ADRs (ex.: diferenças da API do Blender 5.2 no passo de setup,
calibração dos orçamentos de triângulos no Marco 1).

## 11. Fora de escopo do Marco 1

- IA (tradução texto → spec).
- Backend SaaS, autenticação, fila de jobs, billing.
- UI de geração.
