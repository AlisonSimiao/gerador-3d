# Blender como backend autoritativo

O Marco 1 deve provar o pipeline baseado em Blender descrito pelo produto. Por isso, uma geração oficial exige que o Blender exporte o Asset e renderize o Preview; o pipeline puro-Python permanece disponível apenas como fallback explicitamente solicitado para desenvolvimento e testes rápidos, sem comprovar a conclusão do marco nem alegar equivalência com uma renderização Blender.

## Consequences

O comando normal de geração falha de forma explícita quando o Blender está indisponível ou quando sua integração falha. Relatórios distinguem o backend realmente utilizado, e artefatos produzidos pelo fallback não constituem um Resultado de Geração oficial.
