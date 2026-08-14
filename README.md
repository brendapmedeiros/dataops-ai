# DataOps AI - V1

Mini plataforma de DataOps com agentes de IA para monitorar pipelines, detectar problemas de qualidade e gerar diagnosticos.

## Objetivo da V1

Construir o core, sem interface:

```text
BCB API -> Extraction -> Transform -> Banco -> Data Quality -> Quality Agent -> Diagnostico
```

## Stack da V1

- Python
- Pandas
- Pydantic
- SQLite local por padrao
- PostgreSQL-ready via DATABASE_URL
- Gemini opcional

## Por que SQLite agora?

Para manter custo zero e facilitar estudo durante a primeira versao. A camada de banco foi isolada para permitir trocar para PostgreSQL depois sem reescrever o pipeline.

## Como rodar

```bash
cd "C:\Users\brend\Desktop\DataOps AI"
python main.py run
```

Se `python` nao estiver no PATH, use o Python do seu ambiente ou crie uma venv.

## Simular incidentes

```bash
python main.py scenarios
python main.py run --scenario scenario_01_null_values
python main.py run --scenario scenario_02_schema_drift
python main.py run --scenario scenario_04_duplicate_records
python main.py run --scenario scenario_05_invalid_type
```

## Gemini

Crie `.env` a partir de `.env.example` e preencha `GEMINI_API_KEY`. Sem chave, o agente usa diagnostico local por regras.

## O que explicar em entrevista

- Pipeline separado em extract, transform e load.
- Tools retornam fatos objetivos sobre qualidade.
- Agent interpreta os fatos e recomenda acoes.
- LLM fica desacoplado: Gemini pode ser trocado depois.
- SQLite e usado localmente, mas a arquitetura mira PostgreSQL.
