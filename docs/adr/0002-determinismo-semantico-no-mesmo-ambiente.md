# Determinismo semântico no mesmo ambiente

A mesma Spec, processada pela mesma versão do worker e do Blender, deve produzir Assets geometricamente e visualmente equivalentes. Não garantimos identidade binária entre plataformas ou versões, pois detalhes de serialização e renderização externos ao domínio podem mudar sem alterar o Asset percebido.

## Consequences

O Relatório de Validação registra as versões relevantes. Os testes comparam propriedades estáveis de geometria, materiais e imagem; comparação byte a byte pode ser usada como verificação adicional onde for confiável, mas não constitui o contrato público.
