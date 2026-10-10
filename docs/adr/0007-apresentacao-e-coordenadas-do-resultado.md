# Apresentação e coordenadas do Resultado de Geração

O Asset entregue usa metros, sistema destro, eixo `+Y` para cima e `+Z` como frente, com sua Âncora na origem. O Preview é um único PNG quadrado de 1024 px organizado como prancha, com uma vista principal em perspectiva e vistas menores frontal, lateral e traseira.

O Relatório de Validação possui schema versionado e campos estáveis para status, etapa alcançada, backend realmente utilizado, versões do ambiente, Spec Resolvida, verificações executadas, artefatos publicados e erro estruturado.

## Consequences

O exportador converte explicitamente as coordenadas internas do Blender para o contrato glTF. O Preview deixa de ser uma fotografia estética arbitrária e passa a servir como instrumento consistente de inspeção, enquanto o relatório pode ser consumido pelo futuro backend SaaS sem interpretar mensagens livres.
