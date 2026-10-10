# Ambiente oficial e isolamento

O Marco 1 suporta oficialmente Python `>=3.13,<3.14` com `bpy==5.2.2`. Cada Tentativa de Geração oficial ocorre em um processo Blender limpo, encerrado ao fim da execução, evitando vazamento de estado global entre Assets.

A suíte possui dois níveis: testes rápidos de contrato e geometria podem usar o pipeline puro-Python; testes de integração obrigatórios para release executam no ambiente oficial e cobrem construção, renderização, exportação e reimportação no Blender.

## Consequences

As versões do ambiente são fixadas e registradas no Relatório de Validação. Compatibilidade ampla com Pythons sem `bpy` não é parte do produto, e uma release não pode ser aprovada apenas pelos testes fallback.
