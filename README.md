# DataOps AI

DataOps AI e uma plataforma local para monitoramento de pipelines de dados com agentes de IA. O projeto executa uma pipeline de series temporais usando a API SGS do Banco Central, valida a qualidade dos dados, investiga incidentes e gera um plano de resolucao com historico rastreavel por execucao.

## Arquitetura

```text
BCB API
  -> Extraction
  -> Transform
  -> Banco
  -> Data Quality
  -> Agent Orchestrator
      -> DataQualityAgent
      -> InvestigationAgent
      -> ResolutionAgent
  -> Relatorios
  -> Historico
```

## Funcionalidades

- Extracao de dados da API SGS do Banco Central.
- Transformacao e padronizacao de series temporais.
- Carga local em SQLite ou PostgreSQL via `DATABASE_URL`.
- Validacoes de qualidade:
  - valores nulos
  - registros duplicados
  - mudanca de estrutura
  - tipos invalidos
  - anomalias simples
- Diagnostico com Gemini, com fallback local por regras.
- Investigacao baseada em banco e logs da pipeline.
- Plano de resolucao com correcoes e prevencao.
- Relatorio de incidente em Markdown.
- Historico de execucoes em JSONL e na tabela `incident_history`.
- `run_id` para rastrear logs, diagnostico, investigacao, resolucao e historico da mesma execucao.

## Stack

- Python
- Pandas
- Pydantic
- SQLite
- SQLAlchemy
- Gemini API
- unittest
- Git/GitHub

## Estrutura

```text
src/dataops_ai/
  agents/
    orchestrator.py
    quality_agent.py
    investigation_agent.py
    resolution_agent.py

  pipelines/
    extract.py
    transform.py
    load.py

  tools/
    api_tools.py
    database_tools.py
    incident_tools.py
    log_tools.py
    quality_tools.py

  config.py
  models.py
  scenarios.py

data/
  raw/
  processed/
  curated/

logs/
tests/
main.py
```

## Setup local

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para validar a instalacao:

```bash
python -m unittest discover -s tests
```

## Configuracao

Crie um arquivo `.env` a partir de `.env.example`.

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-latest

DATABASE_URL=sqlite:///dataops_ai.db

BCB_SERIES_CODE=11
BCB_START_DATE=01/01/2024
BCB_END_DATE=31/01/2024
```

Sem `GEMINI_API_KEY`, o diagnostico roda com regras locais.

## Banco de dados

Por padrao, o projeto usa SQLite local:

```env
DATABASE_URL=sqlite:///dataops_ai.db
```

Para rodar com PostgreSQL local via Docker:

```bash
docker compose up -d postgres
```

Depois, atualize o `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataops_ai
```

Validar a conexao configurada:

```bash
python main.py banco
```

Validar banco e API antes de executar a pipeline:

```bash
python main.py status
```

Rodar uma validacao rapida do core:

```bash
python main.py validar
```

## Como executar

Rodar a pipeline sem forcar incidente:

```bash
python main.py rodar
```

Listar cenarios disponiveis:

```bash
python main.py cenarios
```

Executar um cenario especifico:

```bash
python main.py rodar --scenario valores_nulos
python main.py rodar --scenario mudanca_estrutura
python main.py rodar --scenario registros_duplicados
python main.py rodar --scenario tipo_invalido
python main.py rodar --scenario timeout_api
```

## Cenarios simulados

| Cenario | Descricao |
|---|---|
| `sem_incidente` | Executa a pipeline sem forcar erro. |
| `valores_nulos` | Insere valor nulo em uma coluna obrigatoria. |
| `mudanca_estrutura` | Simula mudanca de estrutura no dataset. |
| `registros_duplicados` | Duplica registros para testar idempotencia. |
| `tipo_invalido` | Insere texto em campo numerico. |
| `timeout_api` | Simula falha na API e uso de fallback local. |

## Saidas geradas

A cada execucao, o projeto gera artefatos em `data/curated/`:

```text
quality_diagnosis.json
incident_report.md
incident_history.jsonl
```

Tambem sao gravados logs em:

```text
logs/pipeline_runs.jsonl
```

Quando o banco esta configurado, o resumo da execucao tambem e gravado na tabela:

```text
incident_history
```

## Historico

Listar execucoes recentes:

```bash
python main.py historico
```

Com PostgreSQL configurado, o comando consulta a tabela `incident_history`. Se a tabela ainda nao existir, usa o arquivo `data/curated/incident_history.jsonl`.

Exemplo de saida:

```text
Historico recente de incidentes:
- 20260817005902253788 | timeout na API | gravidade: baixa | falhas: 0 | revisao manual: sim
```

## Agentes

### AgentOrchestrator

Coordena a execucao completa: pipeline, validacoes, diagnostico, investigacao, resolucao e persistencia dos relatorios.

### DataQualityAgent

Analisa o relatorio de qualidade e gera o diagnostico inicial. Usa Gemini quando configurado e fallback local quando nao ha chave ou quando a API falha.

### InvestigationAgent

Consulta logs e banco para levantar evidencias do incidente. Tambem identifica falhas operacionais, como uso de fallback apos timeout da API.

### ResolutionAgent

Gera plano de resolucao com impacto, correcoes sugeridas, acoes preventivas e indicacao de revisao manual.

## Roadmap

- API com FastAPI para disparar execucoes e consultar historico.
- Docker Compose com aplicacao e banco.
- Dashboard para visualizacao de execucoes e incidentes.
- Expansao das regras de qualidade e contratos de schema.
