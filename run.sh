#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  🏛️ Structura.AI — HackTown 2026 Edition"
echo "  Ponte Físico-Arquitetônica com Google Gemini & FastAPI"
echo "============================================================"

# Check if docker is requested
if [ "$1" == "--docker" ]; then
    echo "🐳 Iniciando com Docker Compose (PostgreSQL 16 + FastAPI)..."
    docker compose up --build
    exit 0
fi

# Local execution
echo "🚀 Iniciando ambiente local Python..."

if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual .venv..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

export PYTHONPATH=.

echo "⚡ Servidor FastAPI Monolítico rodando em http://localhost:8000"
echo "👉 Acesse o Studio Interativo em http://localhost:8000/analyzer"
echo "👉 Para rodar com Docker + PostgreSQL: ./run.sh --docker"
echo "============================================================"

exec uvicorn structura_ai.main:app --host 0.0.0.0 --port 8000 --reload
