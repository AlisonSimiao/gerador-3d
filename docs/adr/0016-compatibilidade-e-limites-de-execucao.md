# Compatibilidade e limites de execução

Depois de congelada, a Spec `v1` preserva sua semântica em todas as releases compatíveis; mudanças incompatíveis exigem nova versão de Spec. O worker usa versionamento semântico e registra no relatório a versão publicada e o commit exato da build quando disponível.

Gerações não acessam a rede nem baixam recursos depois que o ambiente está instalado. Cada processo Blender possui timeout configurável; quando excedido, o processo é encerrado, artefatos temporários são descartados e um relatório de falha específico é publicado. O timeout default será definido após a medição da linha de base.
