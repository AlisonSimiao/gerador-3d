# Specs normalizadas e versionadas

A entrada aceita a omissão de parâmetros com defaults documentados, mas cada Tentativa de Geração produz primeiro uma Spec Resolvida, validada e com todos os valores efetivos explícitos. O Relatório de Validação registra essa forma resolvida.

O contrato da Spec possui versão explícita. A versão `v1` só será congelada depois que nomes, tipos, semânticas, faixas e defaults forem exercitados e aprovados numa matriz visual representativa; até lá, o contrato é provisório.

## Consequences

Mudanças futuras de contrato são rejeitadas ou migradas conscientemente, nunca reinterpretadas em silêncio. Validação deve ser estrita em runtime, e defaults fazem parte da versão da Spec.

Todo parâmetro de `v1` precisa causar uma diferença visual reconhecível e coerente com seu nome: opções estruturais alteram geometria, opções de paleta alteram aparência e booleanos controlam a presença do elemento nomeado. Campos redundantes, enganosos ou visualmente indistinguíveis são removidos antes do congelamento.

A validação é estrita e não faz coerções: rejeita tipos JSON incorretos, números não finitos, campos desconhecidos e versões ou Estilos não suportados. Além das faixas individuais, valida relações entre campos para preservar o arquétipo; os limites dessas relações são calibrados visualmente.

Cada versão publica um JSON Schema distribuído com o worker. O modelo Python e o schema público derivam de uma única fonte de verdade para impedir divergência entre a fronteira consumida pela IA, pelo backend e pelo worker.
