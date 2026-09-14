from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import configuracoes, empresas, execucoes, home, revisao

app = FastAPI(title="Expermed - Prospecção Trabalhista")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(home.router)
app.include_router(empresas.router)
app.include_router(revisao.router)
app.include_router(execucoes.router)
app.include_router(configuracoes.router)


@app.on_event("startup")
def on_startup():
    init_db()
