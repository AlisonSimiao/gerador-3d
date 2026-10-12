# 20: Baú Fechado (v1)

**What to build:** O Baú passa ao contrato v1 do ADR 0009: `width` (0,6–1,8 m, default 1), `height` (0,4–1,1 m, default 0,6), `depth` (0,4–1,0 m, default 0,6), `lid_form` (arched|flat), `band_count` (0–4, default 2), `has_lock`. As dimensões medem o envelope externo completo, incluindo tampa e cintas; sem interior ou mecanismo de abertura — tampa, cintas e fecho são elementos visuais (ADR 0003, ADR 0009). Âncora no centro da superfície de apoio. Variação observável por Seed; Matriz de Aceitação e baseline versionados.

**Blocked by:** 17: Suíte de dois níveis e gate de release

**Status:** resolved

- [x] Contrato v1 do Baú com campos, faixas e defaults do ADR 0009; campos antigos rejeitados
- [x] Envelope externo confere com as dimensões declaradas (tampa e cintas incluídas)
- [x] Variação observável por Seed; mesma Seed reproduz o resultado
- [x] Matriz de Aceitação e baseline visual versionados; orçamento de 2000 triângulos respeitado

## Answer
Contrato chest v1 verificado sem mudanças no gerador: envelope externo
(±w/2, ±d/2, 0..h) confere para tampa arched|flat e cintas/fecho contidos,
âncora no centro do apoio. Seed varia a largura das cintas de forma
observável e reproduzível sem contrariar dimensões/opções/materiais.
Matriz com 6 specs (canonical, 2 opções, 2 limites, 1 seed-variant) e
baseline.json ready-for-human; previews candidatos via Blender Eevee em
acceptance/chest/review/ aguardam aprovação humana. Fast 161 verdes,
integração da matriz verde, mypy limpo.

## Comments

Em 2026-10-12, o revisor humano (`user`) aprovou os 6 previews da matriz de
Baú regenerados com o perfil `medieval_lowpoly-v2`; o baseline registra a
aprovação por Spec.
