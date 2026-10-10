# Geração Procedural de Assets 3D

Vocabulário canônico do worker que transforma especificações declarativas em assets 3D low-poly.

## Language

**Marco 1**:
Marco técnico interno destinado a provar, de ponta a ponta, que o pipeline de geração é confiável. Não constitui um produto SaaS utilizável ou comercializável.
_Avoid_: MVP comercial, produto inicial

**Spec**:
Descrição declarativa do Asset solicitado. Pode omitir parâmetros que possuam defaults documentados, mas sempre informa o Tipo de Asset e a Seed.
_Avoid_: Prompt, configuração livre

**Spec Resolvida**:
Forma validada e versionada de uma Spec, contendo explicitamente todos os valores efetivos usados pela geração.
_Avoid_: Entrada original, Spec parcial

**Tipo de Asset**:
Arquétipo contratual de Asset, com sua própria Spec, Gerador e critérios de aceitação.
_Avoid_: Categoria, Gerador

**Categoria**:
Agrupamento editorial de Tipos de Asset usado para organizar o catálogo, sem alterar o processo de geração.
_Avoid_: Tipo de Asset

**Gerador**:
Componente que interpreta a Spec de um Tipo de Asset e constrói sua representação geométrica segundo um Estilo.
_Avoid_: Tipo de Asset, Categoria

**Estilo**:
Linguagem visual compartilhada que define silhueta, densidade de faces, paleta, propriedades de superfície e proporções estilísticas, sem substituir as dimensões e opções próprias da Spec.
_Avoid_: Tema, paleta

**Asset**:
Modelo 3D low-poly estático, em formato GLB, produzido a partir de uma Spec e tratado como uma única unidade posicionável. No Marco 1 não inclui rig, animação, colisores ou peças interativas.
_Avoid_: Pacote de artefatos, malha intermediária

**Âncora**:
Ponto de referência que posiciona um Asset no mundo. Coincide com o centro da superfície de apoio para objetos apoiados e com o centro da empunhadura para objetos seguráveis.
_Avoid_: Base-centro, origem geométrica

**Seed**:
Valor da Spec que seleciona variações visuais secundárias, controladas e repetíveis, dentro da intenção explícita da Spec. Seeds diferentes podem selecionar a mesma variação e não identificam unicamente um Asset.
_Avoid_: Identificador do Asset, fonte irrestrita de aleatoriedade

**Impressão Digital da Geração**:
Identificador derivado da Spec Resolvida e das versões do worker, Blender e perfil de Estilo que caracterizam o ambiente lógico de uma geração.
_Avoid_: Seed, identificador aleatório

**Resultado de Geração**:
Conjunto indivisível que comprova uma geração bem-sucedida, formado pelo Asset, pelo Preview e pelo Relatório de Validação correspondentes à mesma Spec.
_Avoid_: Asset, diretório de saída

**Tentativa de Geração**:
Execução iniciada para transformar uma entrada em um Asset, independentemente de terminar com sucesso ou falha. Sempre produz um Relatório de Validação quando o destino desse relatório puder ser criado.
_Avoid_: Resultado de Geração, job

**Preview**:
Prancha visual padronizada do Asset, produzida pelo backend oficial, com uma vista principal e vistas frontal, lateral e traseira para permitir sua avaliação sem abrir o modelo 3D.
_Avoid_: Thumbnail genérica, rasterização auxiliar

**Relatório de Validação**:
Evidência estruturada e legível por máquina de como uma Tentativa de Geração terminou, até qual etapa avançou e quais critérios técnicos foram avaliados.
_Avoid_: Log

**Matriz de Aceitação**:
Conjunto representativo de Specs usado para aprovar visual e tecnicamente um Tipo de Asset antes de congelar seu contrato. Abrange o caso canônico, opções, limites, Seeds e combinações de maior risco sem exigir todas as combinações possíveis.
_Avoid_: Spec default, suíte exaustiva

**Orçamento de Triângulos**:
Limite máximo de complexidade geométrica definido por Tipo de Asset e calibrado contra sua Matriz de Aceitação. É um teto de segurança, não uma meta de detalhamento.
_Avoid_: Meta de triângulos, orçamento da Categoria

## Tipos de Asset do Marco 1

**Casa**:
Casa medieval com exterior fechado e sem interior navegável. Porta, janelas e chaminé são elementos visuais, não aberturas ou peças funcionais.
_Avoid_: Construção genérica, edifício modular

**Espada de Uma Mão**:
Arma medieval estática composta por lâmina, guarda, empunhadura e pomo, dimensionada para uso com uma mão.
_Avoid_: Espada, arma genérica

**Árvore**:
Árvore estilizada individual cuja forma da copa e paleta da folhagem são características independentes.
_Avoid_: Vegetação, floresta

**Baú Fechado**:
Baú medieval estático sem interior ou mecanismo de abertura; tampa, cintas e fecho são elementos visuais.
_Avoid_: Baú interativo, contêiner
