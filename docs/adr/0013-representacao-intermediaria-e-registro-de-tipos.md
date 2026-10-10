# Representação intermediária e registro de Tipos

Geradores produzem uma única representação intermediária independente do Blender, contendo geometria, componentes, materiais e Âncora. O backend Blender oficial é o único responsável por transformar essa representação em cena, Asset e Preview. O fallback puro-Python apenas inspeciona e testa a representação e não publica `model.glb` ou `preview.png`.

Cada Tipo de Asset possui um único descritor que reúne schema, Gerador, Estilos compatíveis, validadores, Orçamento de Triângulos e Matriz de Aceitação.

## Consequences

Testes rápidos continuam desacoplados de `bpy`, mas não existe um segundo exportador capaz de divergir silenciosamente do produto. Orçamentos e políticas deixam de ser duplicados em registros separados.
