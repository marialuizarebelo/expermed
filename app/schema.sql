-- Schema do sistema de prospecção Expermed (trabalhista)
-- Ver especificação, seção 5.

CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj TEXT UNIQUE,
    razao_social TEXT NOT NULL,
    uf TEXT,
    segmento TEXT,
    site TEXT,
    pipedrive_org_id TEXT,
    total_processos_relevantes INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'novo' CHECK (status IN ('novo', 'qualificada', 'descartada', 'bloqueada', 'ja_cliente')),
    motivo_descarte TEXT,
    responsavel TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS processos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    numero_processo TEXT NOT NULL,
    tribunal TEXT NOT NULL,
    assunto_codigo TEXT,
    assunto_descricao TEXT,
    data_distribuicao TEXT,
    status_inferido TEXT DEFAULT 'indefinido' CHECK (status_inferido IN ('ativo', 'arquivado', 'indefinido')),
    ultima_movimentacao TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (numero_processo, tribunal)
);

CREATE TABLE IF NOT EXISTS contatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    nome TEXT NOT NULL,
    cargo TEXT,
    departamento TEXT,
    email TEXT,
    telefone TEXT,
    origem TEXT DEFAULT 'apollo',
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contato_id INTEGER NOT NULL REFERENCES contatos(id),
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    canal TEXT NOT NULL DEFAULT 'email',
    template_usado TEXT,
    conteudo_gerado TEXT,
    status TEXT NOT NULL DEFAULT 'rascunho_gerado' CHECK (status IN ('rascunho_gerado', 'aprovada', 'editada', 'rejeitada', 'enviada', 'respondida')),
    gmail_draft_id TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    revisado_em TEXT,
    enviado_em TEXT
);

CREATE TABLE IF NOT EXISTS negocios_pipedrive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    pipedrive_deal_id TEXT,
    etapa_atual TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS execucoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('busca_datajud', 'busca_apollo', 'geracao_mensagem', 'sync_pipedrive')),
    status TEXT NOT NULL DEFAULT 'rodando' CHECK (status IN ('rodando', 'concluida', 'erro', 'pausada')),
    iniciado_em TEXT NOT NULL DEFAULT (datetime('now')),
    finalizado_em TEXT,
    resumo TEXT
);

CREATE TABLE IF NOT EXISTS eventos_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execucao_id INTEGER NOT NULL REFERENCES execucoes(id),
    empresa_id INTEGER REFERENCES empresas(id),
    nivel TEXT NOT NULL DEFAULT 'info' CHECK (nivel IN ('info', 'warning', 'error')),
    mensagem TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lista_bloqueio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj_ou_razao_social TEXT NOT NULL,
    motivo TEXT,
    adicionado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_processos_empresa ON processos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_contatos_empresa ON contatos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_mensagens_status ON mensagens(status);
CREATE INDEX IF NOT EXISTS idx_empresas_status ON empresas(status);
