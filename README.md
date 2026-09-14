# Expermed — Prospecção Trabalhista

Projeto em construção com Claude Code. **Leia `CLAUDE.md` primeiro** — tem
todo o contexto, decisões já tomadas e pendências. Este README é só o
passo a passo rápido pra rodar localmente.

## Rodando local

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Preencha o `.env` com as chaves reais (peça separadamente, não vêm neste
pacote por segurança — ver `CLAUDE.md`, seção "Sobre as credenciais").

```bash
uvicorn app.main:app --reload
```

Abra `http://localhost:8000` no navegador.

## Continuando com o Claude Code

Abra o Claude Code CLI ou Desktop app dentro desta pasta. Ele lê o
`CLAUDE.md` automaticamente e já entende o histórico do projeto — não
precisa reexplicar nada, só continuar de onde parou.

## Referências úteis

- `docs/scripts-email-mariana/` — os scripts de e-mail reais, por persona
- `docs/manual-google-gmail.pdf` — passo a passo pra liberar o Gmail
- `docs/especificacao-original.md` — o documento de especificação inicial
  do projeto (histórico, mantido pra referência)
