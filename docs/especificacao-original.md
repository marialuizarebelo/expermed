# Especificação Técnica — Sistema de Prospecção Expermed (Trabalhista)

Documento de trabalho para construção via Claude Code. v4 — parâmetros de qualificação confirmados, suporte multiusuário, decisão de hospedagem em aberto.

---

## 1. Objetivo

Sistema local (banco de dados + painel + pipeline orquestrado) para descoberta, qualificação e abordagem inicial de leads da linha trabalhista da Expermed — da identificação de empresas com processos relevantes até o agendamento de reunião. A partir da reunião marcada, o processo volta a ser 100% humano.

Substitui o Data Lawyer (pago) pela API Pública do DataJud (CNJ, gratuita) como fonte de dados processuais.

---

## 2. Fluxo macro

```
[DataJud — busca processos por assunto de interesse, por tribunal]
        ↓
[Agregação por empresa — CNPJ/nome extraído dos resultados, contagem de processos]
        ↓
[Filtro — volume mínimo + fora da lista de bloqueio + não é cliente/negócio já aberto]
        ↓
[Apollo — busca responsáveis da empresa (jurídico/trabalhista/RH)]
        ↓
[Pipedrive — cria/atualiza negócio e contato]
        ↓
[Geração de mensagem personalizada (e-mail)]
        ↓
[Revisão humana no painel]
        ↓
[Rascunho no Gmail — envio manual nesta fase]
        ↓
[Cadência até resposta → condução até agendamento — fase posterior ao MVP]
```

---

## 3. Parâmetros de qualificação (confirmados pela Expermed)

- **Assuntos de interesse:** insalubridade, periculosidade, acidente de trabalho, ergonomia, doença ocupacional (todos trabalhistas)
- **Volume mínimo:** empresa precisa ter **pelo menos 200 processos ativos** no total, sendo **pelo menos metade (100+) nos assuntos selecionados acima**
- **Critério de "ritmo"** (processos recentes, não só antigos): confirmado como critério válido — **falta definir o período exato** (ex.: distribuídos nos últimos 12 meses). Pendência a fechar antes de codificar o filtro.
- **Escopo geográfico:** Brasil inteiro — todos os TRTs relevantes (implica cobrir os ~24 endpoints do DataJud, não um subconjunto)

**Nota de complexidade técnica:** com volume mínimo de 200 processos ativos por empresa e escopo nacional, o volume de dados a agregar é grande — empresas desse porte podem ter milhares de processos espalhados por vários TRTs. A agregação (juntar processos da mesma empresa vindos de tribunais diferentes) precisa lidar com paginação (a API permite até 10.000 registros por página) e possíveis variações de grafia/CNPJ entre tribunais. Isso é engenharia real, não só "chamar a API" — vale reservar tempo pra isso na primeira semana.

---

## 4. Viabilidade técnica — API Pública do DataJud (CNJ)

- **Confirmado:** acesso a metadados processuais (classe, assuntos codificados pela Tabela Processual Unificada do CNJ, movimentações, data de distribuição) via API Elasticsearch, autenticação por chave pública.
- **Confirmado:** cada tribunal tem endpoint próprio (`api_publica_trt1` ... `trt24`) — cobertura nacional exige consultar os 24 endpoints e agregar por conta própria.
- **Confirmado:** não há campo pronto de "processo ativo/inativo" — precisa inferir a partir da última movimentação.
- **A validar:** buscar por assunto codificado + tribunal, e extrair CNPJ/nome do polo passivo (reclamada) dos resultados. Como processo trabalhista costuma ser público (não sigiloso), é provável que funcione — mas precisa ser testado num endpoint real antes de assumir.

Chave pública de teste fornecida pela Mari (pública por definição, não é credencial sensível):
`Authorization: APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==`

**Primeiro teste técnico a rodar (via Claude Code, já que o domínio do DataJud não está liberado no ambiente de chat):** busca por assunto num endpoint de TRT (ex. TRT4) e conferir se o CNPJ/nome da empresa reclamada vem nos resultados.

---

## 5. Modelo de dados (SQLite)

```
empresas
  id, cnpj, razao_social, uf, segmento,
  total_processos_relevantes, status  -- novo | qualificada | descartada | bloqueada | ja_cliente
  motivo_descarte, responsavel  -- pessoa do time responsável por esse lead
  criado_em, atualizado_em

processos
  id, empresa_id (FK), numero_processo, tribunal, assunto_codigo, assunto_descricao,
  data_distribuicao, status_inferido,  -- ativo | arquivado | indefinido
  ultima_movimentacao, criado_em

contatos
  id, empresa_id (FK), nome, cargo, departamento, email, telefone,
  origem,  -- apollo
  criado_em

mensagens
  id, contato_id (FK), empresa_id (FK), canal,  -- email
  template_usado, conteudo_gerado,
  status,  -- rascunho_gerado | aprovada | editada | rejeitada | enviada | respondida
  gmail_draft_id, criado_em, revisado_em, enviado_em

negocios_pipedrive
  id, empresa_id (FK), pipedrive_deal_id, etapa_atual, criado_em, atualizado_em

execucoes
  id, tipo,  -- busca_datajud | busca_apollo | geracao_mensagem | sync_pipedrive
  status,  -- rodando | concluida | erro | pausada
  iniciado_em, finalizado_em, resumo

eventos_log
  id, execucao_id (FK), empresa_id (FK, opcional), nivel,  -- info | warning | error
  mensagem, criado_em

lista_bloqueio
  id, cnpj_ou_razao_social, motivo, adicionado_em
```

---

## 6. Pipeline — contrato de cada etapa

**6.1 Busca DataJud**
- Input: lista de códigos de assunto (Tabela Processual Unificada do CNJ) + lista de tribunais a consultar
- Ação: POST no endpoint de cada tribunal, paginar resultados, extrair `numeroProcesso`, `assuntos`, `dataAjuizamento`, `movimentos`, e dados do polo passivo (reclamada)
- Output: grava em `processos`; cria/atualiza `empresas` se CNPJ novo
- Log: quantos processos encontrados, por tribunal, falhas de request

**6.2 Agregação e filtro**
- Ação: conta processos relevantes por empresa; aplica volume mínimo (200 total / 100 nos assuntos-alvo) + critério de ritmo; verifica `lista_bloqueio`; verifica se já existe negócio aberto/cliente no Pipedrive
- Output: atualiza `status` em `empresas` (`qualificada` ou `descartada` com `motivo_descarte`)

**6.3 Busca Apollo**
- Input: empresas com status `qualificada`
- Ação: busca por empresa + departamento (jurídico/trabalhista/RH), conforme personas do briefing original
- Output: grava em `contatos`
- Log: empresas sem contato encontrado

**6.4 Registro Pipedrive**
- Ação: cria negócio no funil configurado, etapa inicial, vinculado a organização/pessoa; usa API direta (não navegação)
- Output: grava `pipedrive_deal_id` em `negocios_pipedrive`

**6.5 Geração de mensagem**
- Input: dados da empresa + contato + segmento
- Ação: chamada pontual ao Claude (sem estado acumulado) gerando texto seguindo tom/regras da seção 9 — **usando como base os scripts que a Mariana já tem prontos por tipo de destinatário** (resgatar esses templates antes de gerar do zero)
- Output: grava em `mensagens` com status `rascunho_gerado`

**6.6 Revisão humana**
- Ação: humano aprova/edita/rejeita no painel
- Output: se aprovada, cria rascunho no Gmail (`gmail_draft_id`); status vira `aprovada`

---

## 7. Integrações — o que precisa ser levantado/solicitado

| Integração | Uso no fluxo | Status |
|---|---|---|
| **API Pública DataJud (CNJ)** | Descoberta de empresas com processos trabalhistas relevantes por assunto | Chave pública em mãos. Falta validar tecnicamente (seção 4) |
| **Apollo** | Buscar responsáveis (jurídico/trabalhista/RH) direto por empresa | Acesso **confirmado**. Cobertura de dados (busca por empresa+departamento) **ainda sendo verificada** pela Expermed |
| **Pipedrive** | Criar/mover negócio, registrar histórico, consultar duplicidade e lista de bloqueio | CRM comercial já é o Pipedrive (confirmado). Token de API, ID do funil, nomes das etapas **pendentes** |
| **Gmail** | Criar rascunhos de e-mail para revisão/envio | Conta a ser usada e escopo de acesso (draft vs envio direto) **pendente** |
| **Projeto Claude da Expermed** | Contexto, documentos de apoio, planilha de e-mails já levantada | Acesso a confirmar |

**Fora do escopo de integração ativa:** LinkedIn (não é mais necessário no fluxo), Data Lawyer (sendo substituído pelo DataJud).

---

## 8. Painel — telas e ações

**8.1 Visão geral (home)**
- Cards de métrica: empresas processadas (hoje/semana), qualificadas, mensagens geradas, negócios por etapa no Pipedrive
- Gráfico simples de volume por dia

**8.2 Empresas**
- Tabela filtrável por status (novo/qualificada/descartada/bloqueada/cliente) e por responsável
- Detalhe da empresa: processos encontrados, contato(s), mensagem gerada, negócio no Pipedrive

**8.3 Fila de revisão**
- Lista de mensagens com status `rascunho_gerado`, filtrada por responsável
- Ações: aprovar, editar, rejeitar

**8.4 Execuções**
- Histórico de rodadas do pipeline com status e log detalhado
- Ações: **rodar agora**, **pausar execução em andamento**, reprocessar empresa específica

**8.5 Configurações**
- Lista de bloqueio (adicionar/remover)
- Parâmetros: assuntos de interesse, volume mínimo, tribunais ativos

---

## 9. Regras de negócio a codificar

- Tom de voz: profissional, consultivo, objetivo, sem agressividade; não expor volume/detalhe de processos ao prospect; não citar nomes de clientes, só menção genérica de segmento
- Sem menção de preço na abordagem inicial — remeter pra reunião
- Personalização obrigatória: nome correto, cargo, empresa, segmento
- Follow-up: até 2 tentativas, 7 dias de intervalo, depois "sem retorno" (validar número com a Expermed)

> Regras vindas do briefing da outra equipe — confirmar com a Expermed o que vale pra esse projeto.

---

## 10. O que checar assim que o acesso ao Claude delas chegar

- [ ] Que tipo de projeto é (Claude.ai Project simples, ou já usa API/Claude Code do lado delas?)
- [ ] Quais documentos/arquivos já estão anexados
- [ ] Scripts de mensagem da Mariana por tipo de destinatário
- [ ] Estrutura da planilha de e-mails já levantada (colunas, origem, quantidade de linhas)
- [ ] Se há histórico de tentativas anteriores (o que já rodou, o que funcionou/não)

---

## 11. Escopo recomendado para a primeira versão (MVP)

1. Busca no DataJud por assunto de interesse, cobrindo os TRTs relevantes
2. Agregação por empresa (CNPJ, nome, contagem de processos) + filtro (200 total / 100 nos assuntos-alvo / ritmo)
3. Verificação contra lista de bloqueio e negócios já existentes no Pipedrive
4. Busca de contato no Apollo (responsáveis jurídico/trabalhista/RH)
5. Registro no Pipedrive (negócio + contato)
6. Geração de mensagem personalizada (e-mail), usando os templates da Mariana como base
7. Revisão humana no painel → rascunho no Gmail — **envio ainda manual nesta fase**
8. Cada etapa grava no banco de dados local (base do painel e da auditoria)

Deixar de fora do MVP: WhatsApp, envio autônomo sem revisão, condução automática da conversa até agendamento.

---

## 12. Hospedagem — adiada por decisão própria

**Decisão (data desta versão):** rodar tudo localmente, nesta máquina, por enquanto. Compartilhamento com o time fica pra depois, resolvido em separado — não é prioridade agora e não deve travar a construção.

Isso não muda nada da arquitetura (seções 5 a 8): o backend, banco de dados e painel são os mesmos rodando localmente ou compartilhados depois — a diferença é só em qual endereço/máquina ele fica acessível. Quando for a hora de decidir, as opções ficam registradas pra referência futura: máquina compartilhada na rede da Expermed, VPN leve (ex. Tailscale), ou servidor pequeno na nuvem.

---

## 13. Stack sugerida

- **Backend:** Python + FastAPI (endpoints para cada ação do painel: rodar, pausar, aprovar mensagem, etc.)
- **Banco:** SQLite (arquivo local, suficiente pra time pequeno; migra pra Postgres depois se precisar de acesso remoto real)
- **Frontend:** HTML servido pelo próprio backend (Jinja2) + JS simples para as ações — controlável e sem dependência de framework pesado
- **Construção:** Claude Code, do zero até o painel funcionando
- **Multiusuário:** campo `responsavel` já vai no schema desde o início (não custa nada deixar pronto), mas login/seleção de usuário no painel fica pra quando o compartilhamento for resolvido — v1 roda com um usuário só, localmente

---

## 14. Perguntas em aberto (o que ainda falta pra fechar)

**Parâmetros de negócio**
- [ ] Período exato do critério de "ritmo" (processos recentes) — ex.: últimos 12 meses? outro período?

**Acessos**
- [ ] Confirmação da cobertura de dados do Apollo (busca por empresa+departamento retorna o necessário?)
- [ ] Token de API do Pipedrive, ID do funil, nomes das etapas
- [ ] Conta Gmail a ser usada e escopo de acesso (draft vs envio)
- [ ] Resgatar os scripts de mensagem que a Mariana já tem prontos por tipo de destinatário

**Operação**
- [x] Hospedagem — decidido rodar local por enquanto (seção 12); compartilhamento fica pra depois
- [ ] Intervalo de execução do pipeline (ex.: a cada X horas — "sempre atualizado" na prática vira "roda com frequência", não tempo real, já que o DataJud não tem webhook)

**Resolvido nesta rodada:** assuntos de interesse, volume mínimo, escopo geográfico (nacional), confirmação de acesso ao Apollo, confirmação de que Pipedrive é o CRM oficial, confirmação de que a revisão humana acontece dentro do painel, necessidade de suporte multiusuário.
