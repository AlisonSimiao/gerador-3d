# Contrato operacional da CLI

O comando oficial falha quando o destino já contém um Resultado de Geração. Substituição exige `--force` explícito e continua usando publicação atômica. CLI e Relatório de Validação compartilham uma taxonomia versionada de falhas para entrada, ambiente, construção, validação, renderização, exportação, reimportação e publicação.

Linux `x86_64` é a única plataforma oficial do Marco 1. Duração por etapa e pico aproximado de memória são registrados desde o início, mas só se tornam gates depois que uma linha de base for medida no ambiente oficial.

## Consequences

Resultados existentes não são destruídos silenciosamente, consumidores podem classificar falhas sem interpretar texto livre e alegações de suporte ficam limitadas a plataformas efetivamente testadas.
