# DataOps AI

DataOps AI é uma plataforma local para monitoramento de pipelines de dados com agentes de IA. O projeto executa uma pipeline de séries temporais usando a API SGS do Banco Central, valida a qualidade dos dados, investiga incidentes e gera um plano de resolução com histórico rastreável por execução.

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
  -> Relatórios
  -> Histórico
```

## Funcionalidades

- Extração de dados da API SGS do Banco Central.
- Transformação e padronização de séries temporais.
- Carga local em SQLite ou PostgreSQL via `DATABASE_URL`.
- Validações de qualidade:
  - valores nulos
  - registros duplicados
  - mudança de estrutura
  - tipos inválidos
  - anomalias simples
- Diagnóstico com Gemini via Interactions API, com saída estruturada e fallback local por regras.
- Investigação baseada em banco e logs da pipeline.
- Plano de resolução com correções e prevenção.
- Relatório de incidente em Markdown.
- Histórico de execuções em JSONL e na tabela `incident_history`.
- `run_id` para rastrear logs, diagnóstico, investigação, resolução e histórico da mesma execução.

## Stack

- Python
- Pandas
- Pydantic
- SQLite
- SQLAlchemy
- Gemini API
- FastAPI
- Streamlit
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

  llm/
    provider.py

  config.py
  api.py
  models.py
  scenarios.py

data/
  raw/
  processed/
  curated/

dashboard/
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

Para validar a instalação:

```bash
python -m unittest discover -s tests
```

## Configuração

Crie um arquivo `.env` a partir de `.env.example`.

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_STORE_INTERACTIONS=true

DATABASE_URL=sqlite:///dataops_ai.db

BCB_SERIES_CODE=11
BCB_START_DATE=01/01/2024
BCB_END_DATE=31/01/2024
```

Sem `GEMINI_API_KEY`, o diagnóstico roda com regras locais.

`GEMINI_STORE_INTERACTIONS=true` permite registrar a interaction do Gemini para rastreabilidade temporária na API do Google. O projeto também salva localmente os metadados principais da chamada.

## Banco de dados

Por padrão, o projeto usa SQLite local:

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

Validar a conexão configurada:

```bash
python main.py banco
```

Validar banco e API antes de executar a pipeline:

```bash
python main.py status
```

Rodar uma validação rápida do core:

```bash
python main.py validar
```

Subir PostgreSQL e API juntos pelo Docker:

```bash
docker compose up --build api
```

A API fica disponível em:

```text
http://127.0.0.1:8000
```

Subir PostgreSQL, API e dashboard:

```bash
docker compose up --build dashboard
```

O dashboard fica disponível em:

```text
http://127.0.0.1:8501
```

## Como executar

Rodar a pipeline sem forçar incidente:

```bash
python main.py rodar
```

Listar cenários disponíveis:

```bash
python main.py cenarios
```

Executar um cenário específico:

```bash
python main.py rodar --scenario valores_nulos
python main.py rodar --scenario mudanca_estrutura
python main.py rodar --scenario registros_duplicados
python main.py rodar --scenario tipo_invalido
python main.py rodar --scenario timeout_api
```

## API local

Subir a API:

```bash
uvicorn dataops_ai.api:app --reload
```

Ou pelo Docker Compose:

```bash
docker compose up --build api
```

Endpoints principais:

```text
GET  /saude
GET  /status
GET  /cenarios
GET  /historico
POST /execucoes
```

Exemplo de execução pela API:

```bash
curl -X POST http://127.0.0.1:8000/execucoes -H "Content-Type: application/json" -d "{\"scenario\":\"tipo_invalido\"}"
```

## Cenários simulados

| Cenário | Descrição |
|---|---|
| `sem_incidente` | Executa a pipeline sem forçar erro. |
| `valores_nulos` | Insere valor nulo em uma coluna obrigatória. |
| `mudanca_estrutura` | Simula mudança de estrutura no dataset. |
| `registros_duplicados` | Duplica registros para testar idempotência. |
| `tipo_invalido` | Insere texto em campo numérico. |
| `timeout_api` | Simula falha na API e uso de fallback local. |

## Saídas geradas

A cada execução, o projeto gera artefatos em `data/curated/`:

```text
quality_diagnosis.json
incident_report.md
incident_history.jsonl
```

Também são gravados logs em:

```text
logs/pipeline_runs.jsonl
```

Quando o banco está configurado, o resumo da execução também é gravado na tabela:

```text
incident_history
```

## Gemini

O `DataQualityAgent` usa Gemini como motor de diagnóstico quando `GEMINI_API_KEY` está configurada. A chamada principal usa a Interactions API com contrato de resposta baseado no modelo Pydantic `AgentDiagnosis`.

Metadados salvos a cada execução:

- provedor usado
- modelo
- API chamada
- `interaction_id`, quando retornado
- `previous_interaction_id`, quando houver ciclo com tool
- formato da resposta
- versão do prompt
- latência
- tools disponíveis para o agente
- tools chamadas pelo Gemini
- motivo de fallback, quando houver

O provider também suporta function calling em um ciclo controlado: o Gemini pode pedir uma tool, a aplicação executa a função local e envia o resultado de volta usando `previous_interaction_id`. Nesta versão, o `DataQualityAgent` disponibiliza tools para consultar o relatório de qualidade e o contexto da execução.

Se a chamada principal com Interactions falhar, o provider tenta `generateContent` como compatibilidade. Se o Gemini continuar indisponível, o projeto usa regras locais e registra o motivo no relatório.

## Histórico

Listar execuções recentes:

```bash
python main.py historico
```

Com PostgreSQL configurado, o comando consulta a tabela `incident_history`. Se a tabela ainda não existir, usa o arquivo `data/curated/incident_history.jsonl`.

Exemplo de saída:

```text
Histórico recente de incidentes:
- 20260817005902253788 | timeout na API | gravidade: baixa | falhas: 0 | revisão manual: sim
```

## Agentes

### AgentOrchestrator

Coordena a execução completa: pipeline, validações, diagnóstico, investigação, resolução e persistência dos relatórios.

### DataQualityAgent

Analisa o relatório de qualidade e gera o diagnóstico inicial. Usa Gemini quando configurado e fallback local quando não há chave ou quando a API falha.

### InvestigationAgent

Consulta logs e banco para levantar evidências do incidente. Também identifica falhas operacionais, como uso de fallback após timeout da API.

### ResolutionAgent

Gera plano de resolução com impacto, correções sugeridas, ações preventivas e indicação de revisão manual.

## Roadmap

- Expansão das regras de qualidade e contratos de schema.
