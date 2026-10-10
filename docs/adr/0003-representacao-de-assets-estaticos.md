# Representação de Assets estáticos

Assets do Marco 1 são exportados como uma única unidade estática: um nó raiz, uma malha e os grupos de materiais necessários. A malha pode reunir múltiplos volumes fechados, inclusive intersectantes, sem exigir uma união watertight do conjunto; cada componente deve continuar tecnicamente válido, com faces não degeneradas, orientação consistente e materiais atribuídos.

Cada tipo define uma Âncora semanticamente útil. Casas, árvores e baús usam o centro da superfície de apoio; espadas usam o centro da empunhadura.

## Consequences

O formato favorece importação simples em engines e não preserva uma hierarquia para animação ou interação. Esses usos exigirão um contrato posterior.
