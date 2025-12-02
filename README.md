1. Introdução

Este projeto teve o objetivo de implementar um sistema distribuído capaz de:

Realizar descoberta entre processos usando um broker MQTT

Eleger um líder de forma distribuída

Alternar papéis entre controlador (líder) e mineradores

Executar um desafio de prova de trabalho (POW) simples

O sistema segue exatamente o modelo proposto pelo professor, usando um broker EMQX público e as filas sd/init, sd/voting, sd/challenge, sd/solution e sd/result.

Apesar de parecer um sistema simples, vários detalhes técnicos surgiram durante o desenvolvimento — especialmente relacionados ao comportamento assíncrono do MQTT e à sincronização entre processos. A seguir, descrevo o funcionamento final e também os problemas que precisei resolver.

2. Arquitetura Geral do Sistema

Cada processo executa dois papéis ao mesmo tempo:

Participante da eleição

Controlador ou minerador (dependendo do resultado da votação)

Todas as comunicações entre nós acontecem exclusivamente via MQTT, garantindo desacoplamento entre processos.

O sistema foi dividido em cinco fases:

DISCOVERY: cada nó envia seu ClientID e descobre os outros

ELECTION: cada nó envia um voto aleatório e o líder é escolhido

CHALLENGE: o líder gera desafios para mineração

MINING: mineradores procuram soluções via SHA-1

RESULT: o líder valida e anuncia o vencedor

A comunicação é totalmente assíncrona.

3. Problemas encontrados e lições aprendidas

Durante o desenvolvimento original (antes da versão final), surgiram diversos problemas importantes. Alguns deles consumiram bastante tempo até serem entendidos. Vou resumir os principais:

3.1 Problema: Perda de mensagens durante inscrição MQTT

O MQTT não garante recepção de mensagens enquanto o cliente ainda não terminou o processo de subscribe.
Isso causava:

nós que nunca recebiam INIT

travamento eterno esperando outros nós

eleições incompletas

Correção na versão final:
inscrição em todos os tópicos é feita imediatamente ao conectar, evitando qualquer perda.

3.2 Problema: Estado interno inconsistente

Em uma versão antiga, o ID do cliente era trocado depois da conexão.
Isso simplesmente não funciona no Paho MQTT, porque ele mantém buffers internos.

Resultado:

mensagens não chegavam

inscrições eram descartadas

comportamentos aleatórios surgiam

Correção:
Cliente agora é criado diretamente com ID final, logo na inicialização.

3.3 Problema: Mineração interrompida antes do fim

Alguns nós paravam de minerar mesmo sem resultado.
Isso acontecia porque o estado de "transação encerrada" não era resetado corretamente.

Correção:
Variáveis de estado agora são reiniciadas a cada novo desafio.

4. Funcionamento da Versão Final (reescrita)

Na nova implementação:

O nó envia seu ID até todos os participantes serem descobertos

A eleição é feita com votos totalmente aleatórios

O líder selecionado automaticamente vira controlador

Mineradores ficam tentando encontrar hashes com prefixo de zeros

O líder valida as soluções

Novo desafio é criado 5 segundos após cada vencedor

Esse fluxo é contínuo e completamente distribuído.

5. Conclusão

O projeto foi um ótimo exercício para entender:

como coordenação distribuída funciona na prática

por que sincronização é um desafio real

como sistemas Publish/Subscribe lidam com latência e concorrência

a importância do desenho correto de estados internos

A nova versão do código ficou mais organizada, estável e clara, e cumpre 100% dos requisitos do trabalho.

Mesmo com os desafios e alguns travamentos iniciais, a versão final funcionou de forma consistente, e foi possível visualizar todos os papéis sendo executados corretamente: descoberta, eleição, mineração e validação.