# Expermed — Prospecção Trabalhista (contexto do projeto)

Este documento existe pra qualquer sessão nova do Claude Code entender o
projeto de uma vez, sem precisar reconstruir o histórico de decisões do
zero. Leia isso inteiro antes de começar a mexer em qualquer coisa.

## O que é esse projeto

A Expermed presta perícias médicas/técnicas/contábeis em processos
trabalhistas (assistência técnica, laudos, manifestações). O time comercial
(liderado pela Mariana Mello) faz prospecção outbound de empresas que
podem precisar desses serviços.

**O problema real que este projeto resolve:** não é falta de empresas pra
prospectar — é o **trabalho manual repetitivo** entre "empresa já
qualificada" e "e-mail enviado": cadastrar no Pipedrive, catar contato,
achar o script certo, escrever e mandar. Isso trava o volume de envio e
por consequência o número de reuniões agendadas (meta: ~3/semana). **O
foco do projeto é aumentar esse volume, automatizando o meio do processo**
— não a descoberta/qualificação de empresas, que segue manual.

## Decisões já tomadas (não rediscutir sem motivo novo)

1. **Fonte de empresas-alvo:** pesquisa manual do time comercial. Chegam
   prontas no Pipedrive (funil **"Outbound Trabalhista"**, pipeline_id=1).
   Não há automação de descoberta por assunto/tribunal (foi avaliado e
   descartado — ver seção "Caminhos avaliados e descartados" abaixo).

2. **Pipedrive é a fonte única da verdade.** O painel/dashboard deste
   projeto é só uma *visualização* melhor organizada do que já está lá —
   nunca um banco de dados paralelo. Toda escrita (etapa, contato,
   histórico) deve ir pro Pipedrive, não ficar presa num banco local.

3. **Consulta de processos por CNPJ (Data Lawyer):** a Expermed já paga
   Data Lawyer e ele já entrega isso. A ideia é só automatizar a chamada
   via API deles — **ainda sem credencial de API** (o acesso atual da
   Expermed é de usuário de painel, não de desenvolvedor). Ver
   `app/pipeline/datalawyer.py` — interface pronta, falta a chave.
   Precisa: falar com comercial da Data Lawyer sobre acesso via API.

4. **Busca de contato: Apollo.** Já implementado e validado
   (`app/pipeline/apollo.py`):
   - Resolve o domínio da empresa pelo **nome** (não pelo campo "site" do
     Pipedrive, que está vazio em quase todos os registros)
   - Prioriza cargos jurídico/advogado trabalhista antes de RH/SST
   - Revela no máximo **5 contatos por empresa**, só os que têm e-mail ou
     telefone
   - **REGRA CRÍTICA DE CUSTO:** cada "revelar contato" consome crédito
     real da conta Apollo. **NUNCA rodar isso em lote ou automaticamente
     sem confirmação humana explícita antes, a cada vez.** Já aconteceu de
     rodar sem perguntar e o usuário reclamou com razão — não repetir esse
     erro. Isso vale pra qualquer API paga (Apollo, e futuramente Data
     Lawyer/Judit/Escavador se algum entrar).
   - Chave de credencial da conta: `comercial@expermed.com.br` (conta
     Apollo). Saldo no momento da última checagem: ~2.500 créditos
     restantes — dá pra checar de novo em
     `GET /api/v1/users/api_profile?include_credit_usage=true` (esse
     endpoint específico é **0 créditos**, documentado pela própria
     Apollo, seguro de chamar quantas vezes quiser).

5. **Geração de mensagem:** usa os scripts reais da Mariana (recebidos em
   PDF: Jurídico Empresas, RH Trabalhista, Escritórios Trabalhistas — esse
   último é pra outro tipo de lead, parceria com escritório, não usado no
   fluxo atual). O cargo do contato (que a Apollo já prioriza) decide qual
   família de script usar: jurídico/advogado → script Jurídico; RH/pessoal
   → script RH. Ver `docs/scripts-email-mariana/` pros textos completos
   de cada e-mail da cadência (1 a 5 + "outros setores").

6. **Data/horário da reunião:** os scripts têm datas fixas no texto
   original ("09/09 às 10h") — isso precisa virar **dinâmico** no gerador
   (sugerir próximo horário disponível, não uma data que já passou). No
   mockup do painel já existe um seletor manual de dia/horário que
   preenche o texto ao vivo — ver seção "Mockup do painel" abaixo. Falta
   ligar isso à geração de mensagem de verdade.

7. **Envio do e-mail — fase 1 (atual): rascunho + aprovação humana antes
   de enviar.** Fase 2 (futura, só depois de validar qualidade/confiança):
   envio automático sem revisão. O escopo do Google que estamos pedindo
   pra Mariana (`gmail.compose`) **já cobre as duas fases** — ele permite
   criar rascunho E enviar, não é preciso pedir escopo novo depois. Ver
   manual em `docs/manual-google-gmail.pdf` (passo a passo simples, sem
   jargão, pra qualquer pessoa não-técnica seguir).

8. **Cadência de follow-up:** 5 e-mails (1 inicial + 4 follow-ups), textos
   prontos por persona. **PENDENTE: intervalo real entre um e-mail e
   outro** — o documento original tinha uma regra provisória ("7 dias, 2
   tentativas") que não bate com os 5 e-mails reais dos scripts. Precisa
   confirmar com a Mariana/comercial qual o intervalo certo antes de
   automatizar isso.

9. **Rastreio de progresso da cadência (revisão / follow-up N / retorno):**
   decisão de arquitetura: usar o recurso nativo de **Atividades/Tarefas
   do Pipedrive** vinculadas ao negócio (uma atividade por etapa da
   cadência: "E-mail 1", "Follow-up 1"... "Follow-up 4"), em vez de criar
   um campo/tabela paralela. O dashboard lê essas atividades pra mostrar
   em que ponto cada empresa está. **Ainda não implementado.**

10. **Retorno → Google Calendar:** quando o contato responde e a reunião é
    marcada, a ideia é criar o evento automaticamente na agenda Google.
    Precisa da **Google Calendar API** (escopo adicional, mesmo projeto do
    Google Cloud que a Mariana já está configurando pro Gmail — não
    precisa recomeçar do zero, só adicionar o escopo quando chegar a
    hora).

## Caminhos avaliados e descartados (não perder tempo revalidando)

- **DataJud (API pública do CNJ):** testado e confirmado — nunca expõe
  dado de parte (CNPJ/nome), em nenhuma direção de busca, por política
  oficial do CNJ. Não serve pra achar empresa nem pra buscar processo por
  CNPJ.
- **Consulta pública do PJe/TRT direto (scraping):** tecnicamente existe
  (achamos a API real por trás da tela de consulta), mas é protegida por
  captcha de propósito, pra impedir automação em massa. **Não construir
  automação de captcha pra isso** — é contornar um controle de segurança,
  independente da intenção ser legítima.
- **Escavador (API):** não tem busca "de descoberta" (por assunto, sem
  CNPJ prévio) — só serve pra confirmar CNPJ já conhecido. Não resolve o
  problema de descoberta, mas nem precisa mais já que a descoberta é
  manual.
- **Judit.io:** tecnicamente resolveria tanto descoberta quanto CNPJ→
  processos (endpoint `/lawsuits` com `subject_codes` OU
  `party_documents`), mas não é self-service (precisa contato comercial
  pra ter chave). Ficou de lado porque a decisão foi manter Data Lawyer.

## Estado atual do código

- **Stack:** Python + FastAPI + SQLite + Jinja2 (escolha própria, não
  vem do documento original — decisão de manter simples pro tamanho do
  time e do problema)
- `app/schema.sql` — schema do banco local (funciona como cache/auditoria,
  não como fonte de verdade — ver decisão #2)
- `app/pipeline/apollo.py` — funcional e validado com dados reais
- `app/pipeline/pipedrive.py` — só leitura por enquanto (lista negócios do
  funil Outbound Trabalhista). Escrita (mover etapa, criar
  atividade/histórico) ainda não implementada
- `app/pipeline/datalawyer.py` — stub, aguardando credencial
- Painel FastAPI (`app/routers/`, `app/templates/`) — esqueleto simples,
  **desatualizado** em relação a tudo isso; não reflete os dados reais
  ainda. O layout de referência de verdade é o mockup (ver abaixo).

## Mockup do painel (referência de design/fluxo)

Existe uma versão navegável (HTML, um arquivo só, sem backend) publicada
como Claude Artifact, usada pra validar layout e fluxo com a equipe antes
de conectar ao backend real. Pedir pro usuário original da conversa
(Malu/comercial) o link se precisar consultar, ou reconstruir o layout
a partir da descrição: 4 telas (Visão Geral, Fila da Mariana, Revisão de
mensagens, Histórico), paleta verde-azulada (teal), tipografia Newsreader
(serifada, títulos) + IBM Plex Sans (corpo) + IBM Plex Mono (números).

## Regras de negócio importantes

- Tom de e-mail: consultivo, profissional, nunca menciona preço na
  abordagem inicial, nunca cita nomes de clientes/volume de processos
  específico da empresa-alvo (só menção genérica de segmento)
- Sempre pedir confirmação de recebimento no fim do e-mail (padrão dos
  scripts da Mariana)
- **Nunca rodar ação com custo real (crédito de API paga) sem perguntar
  antes, especificamente, a cada vez.** Essa é a regra mais importante
  deste documento inteiro.

## Pendências abertas (perguntar antes de assumir)

- [ ] Credencial de API do Data Lawyer (aguardando comercial deles)
- [ ] Acesso Google Cloud/Gmail da Mariana (manual já enviado a ela)
- [ ] Intervalo real entre e-mails da cadência de follow-up
- [ ] Se/quando pedir escopo do Google Calendar
- [ ] Desenho final do "gatilho humano" antes de qualquer chamada paga
      (proposta: botão manual por empresa + aviso de custo + teto
      configurável de consultas — ainda não implementado)

## Sobre as credenciais

O arquivo `.env` **não está incluído neste pacote** por segurança (não
deve circular em zip por e-mail/WhatsApp). Copie `.env.example` para
`.env` e peça as chaves reais separadamente para quem está te repassando
este projeto:
- `PIPEDRIVE_API_TOKEN`
- `APOLLO_API_KEY`
- Data Lawyer e Gmail: ainda pendentes de configurar (ver seção de
  pendências acima)
