# Conformidade GLB e gate de release

Uma geração oficial precisa passar pela reimportação no Blender e pelo Khronos glTF Validator sem erros de conformidade. O GLB contém somente geometria, materiais e metadados necessários, com transforms aplicados e normais exportadas, sem câmera, luz, animação ou dependências externas.

Toda release executa automaticamente os testes rápidos e a suíte Blender completa em Linux `x86_64`, reprovando quando qualquer Matriz de Aceitação falha tecnicamente. Mudanças nos baselines visuais continuam exigindo aprovação humana.

O Marco 1 entrega lockfile e automação reproduzível de setup e CI, mas não exige imagem de container; empacotamento para infraestrutura fica para o marco SaaS.
