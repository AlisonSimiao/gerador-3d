# Migração e conclusão do Marco 1

As Specs JSON atuais são exemplos pré-`v1` e serão migradas explicitamente, sem compatibilidade automática. A implementação avança primeiro numa fatia vertical completa da Casa — Spec versionada, Blender, validação, GLB, Preview, relatório e publicação atômica — e só depois migra Árvore, Espada de Uma Mão e Baú Fechado.

ADRs registram os motivos das decisões, o JSON Schema é a autoridade do contrato de entrada, um documento próprio define os gates do Marco 1 e o README cobre instalação e uso. O `PLANO_MVP.md` será reescrito para apontar essa estrutura, não permanecer como fonte concorrente.

O Marco 1 só termina quando os quatro Tipos passam suas Matrizes de Aceitação, os GLBs passam Blender e Khronos glTF Validator, os baselines visuais possuem aprovação humana, fallback e backend oficial estão inequivocamente separados, a CI oficial está verde e contratos e documentação descrevem o comportamento real.
