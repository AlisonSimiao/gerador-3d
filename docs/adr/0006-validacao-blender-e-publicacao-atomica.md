# Validação Blender e publicação atômica

Uma geração oficial só termina com sucesso depois que o Blender valida a cena e reimporta o GLB exportado, comprovando topologia por componente, materiais, Âncora, transformações, unidades e integridade do Asset entregue. Verificações puro-Python são auxiliares e não substituem esse gate.

Asset e Preview são publicados juntos no destino final somente após todas as validações. Em caso de falha, o destino contém apenas o Relatório de Validação; artefatos intermediários permanecem numa área temporária descartável.

## Consequences

Existência de arquivo deixa de significar sucesso parcial. A suíte precisa testar o caminho Blender real, e cada Tipo só congela seu contrato após aprovação técnica e humana de sua Matriz de Aceitação e calibração do Orçamento de Triângulos.
