# DataOps AI

Mini plataforma de DataOps com agentes de IA para monitorar pipelines, detectar problemas de qualidade e gerar diagnosticos.

## Objetivo atual

Construir o core, sem interface:

```text
BCB API -> Extraction -> Transform -> Banco -> Data Quality -> Quality Agent -> Investigation Agent
```

## Stack da V1

- Python
- Pandas
- Pydantic
- SQLite local por padrao
- PostgreSQL-ready via DATABASE_URL
- Gemini opcional (`gemini-flash-latest`)

## Por que SQLite agora?

Para manter custo zero e facilitar estudo durante a primeira versao. A camada de banco foi isolada para permitir trocar para PostgreSQL depois sem reescrever o pipeline.

## Como rodar

```bash
cd "C:\Users\brend\Desktop\DataOps AI"
python main.py rodar
```

Se `python` nao estiver no PATH, use o Python do seu ambiente ou crie uma venv.

## Simular incidentes

```bash
python main.py cenarios
python main.py rodar --scenario valores_nulos
python main.py rodar --scenario mudanca_estrutura
python main.py rodar --scenario registros_duplicados
python main.py rodar --scenario tipo_invalido
```

## Gemini

Crie `.env` a partir de `.env.example` e preencha `GEMINI_API_KEY`. Sem chave, o agente usa diagnostico local por regras.

## Agentes

- `DataQualityAgent`: interpreta as falhas de qualidade e gera o diagnostico.
- `InvestigationAgent`: consulta banco e logs para levantar evidencias do incidente.

## O que explicar em entrevista

- Pipeline separado em extract, transform e load.
- Tools retornam fatos objetivos sobre qualidade.
- O agente de qualidade interpreta os fatos e recomenda acoes.
- O agente de investigacao busca evidencias no banco e nos logs.
- LLM fica desacoplado: Gemini pode ser trocado depois.
- SQLite e usado localmente, mas a arquitetura mira PostgreSQL.
