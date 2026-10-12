# Proveniência e identidade de gerações

Seeds controlam variação, mas não garantem resultados únicos: valores diferentes podem selecionar a mesma variante. O Relatório de Validação inclui uma Impressão Digital da Geração derivada da Spec Resolvida, versão do worker, Blender e perfil de Estilo.

Quando uma entrada não puder ser resolvida, o relatório registra erros estruturados e uma hash da entrada, sem copiar automaticamente o conteúdo inválido.

No schema versionado do relatório versionado pela ADR 0007, a Impressão Digital da Geração é o campo `generation_fingerprint` e aparece apenas em relatórios de sucesso. A hash segura da entrada é o campo `input_hash` e substitui qualquer cópia da entrada rejeitada: relatórios de entrada inválida registram apenas `attempt_id` e `input_hash`, com `resolved_spec` nulo.

## Consequences

Cache e investigação usam a impressão digital, não a Seed. Relatórios correlacionam entradas inválidas sem armazenar dados arbitrários que possam ter sido enviados por engano.
