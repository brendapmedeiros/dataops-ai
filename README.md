# DataOps AI

DataOps AI é uma plataforma local e em nuvem para monitoramento de pipelines de dados com agentes de IA. O projeto executa uma pipeline de séries temporais usando a API SGS do Banco Central, valida a qualidade dos dados com contratos declarativos, investiga incidentes autonomamente e gera planos de resolução com histórico e trilha de auditoria imutável (SHA-256) por execução.

## Arquitetura

```text
BCB API
  -> Extraction
  -> Transform
  -> Data Quality & Contracts (YAML)
      -> Se Aprovado  -> Carga no Banco (Silver/Gold)
      -> Se Reprovado -> Circuit Breaker: Quarentena (DLQ)
  -> Agent Orchestrator
      -> DataQualityAgent (Drift estatístico Z-Score, Anomalias, PII/LGPD)
      -> InvestigationAgent (Logs, Banco, Quarentena)
      -> ResolutionAgent (Correções, Prevenção, Impacto)
  -> Trilha de Auditoria (SHA-256 imutável)
  -> Relatórios & Histórico
  -> Mission Pulse Dashboard (Streamlit + Bento Grid Design System)
```

## Funcionalidades

- **Extração & Transformação:** Integração com a API SGS do Banco Central e padronização de séries temporais.
- **Contratos de Dados Declarativos (YAML):** Regras de schema, nulabilidade, limites e tipos expressas em `config/contracts/`.
- **Padrão Circuit Breaker / Dead Letter Queue (DLQ):** Se um lote violar contratos de qualidade, a carga na tabela oficial é bloqueada imediatamente e os registros são isolados em `data/dlq/` para proteger o banco analítico.
- **Validações Avançadas de Qualidade:**
  - Valores nulos e registros duplicados
  - Mudança de estrutura (schema drift) e tipos inválidos
  - Detecção estatística de anomalias por Z-Score (drift acentuado)
  - Auditoria de privacidade e proteção contra vazamento de dados sensíveis (PII/LGPD)
- **Segurança & Trilha de Auditoria Criptográfica:** Cada execução gera uma assinatura SHA-256 inviolável que sela os dados processados e o diagnóstico dos agentes.
- **Dashboard Mission Pulse (Bento Grid):** Interface moderna em Streamlit com Design System OLED Dark, telemetria em tempo real e console interativo de simulação de incidentes.
- **Diagnóstico com Gemini & Fallback Autônomo:** Diagnóstico via Gemini Interactions API com saída estruturada em Pydantic e fallback local baseado em regras determinísticas.
- **Persistência Híbrida:** Suporte a SQLite local ou PostgreSQL via `DATABASE_URL`.
- **API REST FastAPI:** Microsserviço pronto para integração e execuções remotas.

## Stack

- **Linguagem & Core:** Python 3.11+ / 3.12
- **Processamento:** Pandas, NumPy
- **Validação & Contratos:** Pydantic v2, PyYAML
- **Banco de Dados:** SQLAlchemy v2, SQLite, PostgreSQL (psycopg2)
- **IA & LLM:** Google Gemini API (Interactions API / `google-genai`)
- **Backend:** FastAPI, Uvicorn, HTTPX
- **Frontend & Visualização:** Streamlit, Altair, Vanilla CSS Design Tokens
- **Testes & DevOps:** `unittest`, Docker, Docker Compose, Google Cloud Run

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

dashboard/
  app.py                     # Orquestrador do frontend
  styles/
    theme.css                # Design System (Tokens OLED, cores semânticas, tipografia)
  components/
    hero.py                  # Hero Card com status e esfera bioluminescente
    metrics.py               # Mini Cards 2x2 de métricas e KPIs
    telemetry.py             # Pulso telemétrico com gráfico Altair neon
    console.py               # Console de operações e diagnóstico SHA-256
    audit.py                 # Drawer de auditoria com histórico detalhado

config/
  contracts/                 # Contratos de dados declarativos (YAML)

data/
  raw/                       # Dados brutos extraídos
  processed/                 # Dados transformados
  curated/                   # Relatórios e históricos consolidados
  dlq/                       # Quarentena de lotes reprovados (Circuit Breaker)

logs/                        # Logs estruturados em JSONL
tests/                       # Suíte de testes unitários automatizados
main.py                      # CLI do DataOps AI
```

## Setup Local

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para validar a instalação e rodar os 31 testes unitários:

```bash
python -m unittest discover -s tests
```

## Configuração

Crie um arquivo `.env` a partir de `.env.example`:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_STORE_INTERACTIONS=true

DATABASE_URL=sqlite:///dataops_ai.db

BCB_SERIES_CODE=11
BCB_START_DATE=01/01/2024
BCB_END_DATE=31/01/2024
```

* Sem `GEMINI_API_KEY`, o diagnóstico opera com regras locais determinísticas de alta precisão.
* `GEMINI_STORE_INTERACTIONS=true` permite registrar a interaction do Gemini para rastreabilidade temporária.

## Banco de Dados

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

## Dashboard Mission Pulse (Streamlit)

O dashboard oferece uma interface moderna no padrão **Bento Grid OLED Dark**, desacoplada em componentes modulares:

1. **Hero Card:** Status consolidado de governança em tempo real (*100% Saudável*, *Proteção Ativa* ou *Sistema Pronto*) com indicadores de conexão da API BCB e do Banco de Dados.
2. **KPIs Bento (2x2):**
   - **Pipeline Health (%):** Taxa de aprovação das cargas sem anomalias.
   - **Quarentena / DLQ:** Contador de lotes isolados pelo circuit breaker.
   - **Volume Monitorado:** Total de execuções auditadas na série SGS.
   - **Ações dos Agentes:** Contagem de investigações e revisões executadas pela IA.
3. **Pulso Telemétrico (ECG):** Gráfico de onda contínua com curvas neon via Altair comparando falhas detectadas com o limiar de contrato (tolerância zero).
4. **Console de Operações:** Disparo de execuções e injeção de falhas com exibição imediata do diagnóstico dos agentes e do **Hash SHA-256 criptográfico**.
5. **Trilha de Auditoria (Drawer):** Histórico forense detalhado e pesquisável.

### Executar o Dashboard:

Localmente via Python:
```bash
streamlit run dashboard/app.py
```

Ou via Docker Compose:
```bash
docker compose up --build dashboard
```
Acesse em: `http://localhost:8501`

## Como Executar via CLI

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

## API FastAPI

Subir a API localmente:

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

A documentação interativa Swagger fica disponível em: `http://127.0.0.1:8000/docs`

## Cenários de Teste

| Cenário | Descrição |
|---|---|
| `sem_incidente` | Executa a pipeline padrão sem forçar erros. |
| `valores_nulos` | Insere valores nulos em colunas obrigatórias para testar regras de nulabilidade. |
| `mudanca_estrutura` | Simula quebra de contrato e schema drift removendo colunas obrigatórias. |
| `registros_duplicados` | Duplica registros para testar a idempotência e unicidade. |
| `tipo_invalido` | Insere strings em colunas numéricas de taxas/valores. |
| `timeout_api` | Simula falha de conexão na API BCB e disparo de fallback local. |

## Deploy em Nuvem (Google Cloud Platform - GCP)

A aplicação está pronta para deploy no **Google Cloud Run (Serverless)**:

1. **Artifact Registry:** Repositório Docker gerenciado.
2. **Cloud Run (API):** Microsserviço FastAPI com escalabilidade automática e HTTPS gerenciado.
3. **Cloud Run (Dashboard):** Frontend Streamlit conectado à URL da API.
4. **Secret Manager:** Armazenamento seguro de chaves (`GEMINI_API_KEY`) e credenciais de banco.

Exemplo de deploy rápido com a CLI `gcloud`:

```bash
# Deploy da API
gcloud run deploy dataops-api \
    --source . \
    --region southamerica-east1 \
    --allow-unauthenticated \
    --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest" \
    --port 8000 \
    --command "uvicorn,dataops_ai.api:app,--host,0.0.0.0,--port,8000"

# Deploy do Dashboard
gcloud run deploy dataops-dashboard \
    --source . \
    --region southamerica-east1 \
    --allow-unauthenticated \
    --set-env-vars="DATAOPS_API_URL=https://dataops-api-xyz.a.run.app" \
    --port 8501 \
    --command "streamlit,run,dashboard/app.py,--server.port,8501,--server.address,0.0.0.0,--server.enableCORS,false,--server.enableXsrfProtection,false"
```

## Agentes Autônomos

* **`AgentOrchestrator`:** Coordena a execução completa: pipeline, validações, diagnóstico, investigação, resolução e persistência dos relatórios.
* **`DataQualityAgent`:** Analisa o relatório de qualidade, verifica drift estatístico (Z-Score) e vazamento de PII. Usa Gemini quando configurado e fallback local determinístico.
* **`InvestigationAgent`:** Consulta logs, banco e a quarentena (DLQ) para levantar evidências forenses do incidente.
* **`ResolutionAgent`:** Gera planos de resolução com correções sugeridas, ações preventivas, impacto e indicação de necessidade de revisão manual.
