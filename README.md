# DataOps AI

DataOps AI é uma plataforma local e em nuvem para monitoramento de pipelines de dados com agentes de IA. O projeto executa uma pipeline de séries temporais usando a API SGS do Banco Central, valida a qualidade dos dados com contratos, investiga incidentes autonomamente e gera planos de resolução com histórico e trilha de auditoria imutável (SHA-256) por execução.

## Arquitetura

```mermaid
flowchart TD
    subgraph Ingestao["Ingestao e Coleta"]
        BCB["API SGS Banco Central"] --> Extract["Pipeline de Extracao"]
    end

    subgraph Validacao["Contratos e Qualidade"]
        Extract --> Contracts["Data Contracts (YAML)"]
        Contracts --> Checks{"Validacao de Qualidade"}
    end

    subgraph Armazenamento["Protecao e Armazenamento"]
        Checks -- "Aprovado" --> DB[("PostgreSQL / Cloud SQL")]
        Checks -- "Reprovado" --> DLQ["Quarentena (DLQ Local / GCS)"]
    end

    subgraph Agentes["Triagem Multiagente"]
        Checks --> QA["DataQualityAgent (Diagnostico)"]
        QA --> IA["InvestigationAgent (Evidencias)"]
        IA --> Supervisor{"Avaliacao do Supervisor"}
        Supervisor -- "Calibracao Necessaria" --> QA
        Supervisor -- "Consenso Homologado" --> RA["ResolutionAgent (Plano de Acao)"]
    end

    subgraph Auditoria["Governanca e Entrega"]
        RA --> Hash["Hash Criptografico SHA-256"]
        Hash --> Reports["Relatorios de Auditoria"]
        Reports --> Dashboard["Dashboard Mission Pulse"]
    end
```


## Funcionalidades

- **Extração & Transformação:** Integração com a API SGS do Banco Central e padronização de séries temporais.
- **Contratos de Dados Declarativos (YAML):** Regras de schema, nulos, limites e tipos expressas em `config/contracts/`.
- **Padrão Circuit Breaker / Dead Letter Queue (DLQ):** Se um lote violar contratos de qualidade, a carga na tabela oficial é bloqueada e os registros são isolados em `data/dlq/` para proteger o banco analítico.
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
    theme.css                # Design System 
  components/
    hero.py                  # Hero Card com status
    metrics.py               # Mini Cards de métricas e KPIs
    telemetry.py             # Pulso com gráfico de acompanhamento
    console.py               # Console de operações e diagnóstico SHA-256
    audit.py                 # Auditoria com histórico detalhado

config/
  contracts/                 # Contratos de dados

data/
  raw/                       # Dados brutos
  processed/                 # Dados transformados
  curated/                   # Relatórios e históricos consolidados
  dlq/                       # Quarentena de lotes reprovados (Circuit Breaker)

logs/                        # Logs em JSONL
tests/                       # Testes automatizados
main.py                      # CLI do DataOps AI
```

## Setup Local

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Para validar a instalação e rodar os testes:

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

* Sem `GEMINI_API_KEY`, o diagnóstico opera com regras locais.
* `GEMINI_STORE_INTERACTIONS=true` permite registrar a interação do Gemini para rastreabilidade.

## Banco de Dados

Por padrão o projeto usa SQLite local:

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

## Dashboard // Live Observability Cockpit

O dashboard foi reformulado para ser uma ferramenta operacional indispensável de observabilidade de dados (Data Observability & Incident Response), estruturado em abas especializadas:

1. **Barra Operacional do Topo (Header):** Status em tempo real do pipeline (`100% Saudável` ou `Circuit Breaker`), indicador de **Freshness/SLA** do último lote, conectividade da API SGS 11, status do banco de dados e motor de IA ativo.
2. **Aba 1: 📊 Visão Geral & SLAs:**
   - **4 KPIs Operacionais:** *Pipeline Health Rate (%)*, *Circuit Breaker / DLQ (lotes retidos)*, *Volume na Base Homologada (linhas)* e *Taxa de Autonomia dos Agentes*.
   - **Linha do Tempo das Execuções:** Gráfico interativo com status de aprovação vs retenção e volume por execução.
   - **Pareto de Violações:** Gráfico de barras identificando as regras de contrato que mais falham historicamente (*Nulos*, *Schema Drift*, *Tipo Inválido*, *Duplicatas*, etc.).
3. **Aba 2: 🚨 Central de Incidentes & RCA:**
   - **Seletor de Execução:** Raio-X individual de qualquer run com carimbo criptográfico SHA-256.
   - **Tabela de Contratos de Dados:** Status detalhado (`PASS`/`FAIL`), coluna e quantidade de linhas afetadas por cada regra do contrato YAML.
   - **Painel de Investigação Multiagente (RCA):** Diagnóstico e causas prováveis (`DataQualityAgent`), evidências técnicas e hipótese (`InvestigationAgent`), e plano de correção com análise de impacto (`ResolutionAgent`).
4. **Aba 3: 📦 Quarentena & Dead Letter Queue (DLQ):**
   - Gestão ativa dos lotes bloqueados pelo Circuit Breaker em `data/dlq/`.
   - Visualização dos metadados e preview tabular completo dos registros defeituosos retidos.
5. **Aba 4: 🗄️ Dados Homologados (Camada Gold):**
   - Curva temporal da Taxa Selic diária (SGS 11) diretamente do banco analítico (`sqlite`/`postgres`).
   - Estatísticas descritivas (média, mínimo, máximo, intervalo de datas) e tabela analítica para conferência de negócio.
6. **Aba 5: ⚡ Simulador de Falhas & Injeção de Anomalias:**
   - Disparo controlado de cenários com matriz de risco e feedback imediato dos agentes.
7. **Trilha de Auditoria Criptográfica (Drawer):** Histórico detalhado e inviolável de execuções.

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

## Infraestrutura Cloud-Native e Deploy (GCP)

A infraestrutura foi desenhada como código (IaC) com Terraform no diretório `infra/`, seguindo preceitos serverless e boas práticas de FinOps para garantir custo zero absoluto quando ociosa:

1. **Google Cloud Run (Serverless):** Microsserviços da API e do Dashboard configurados com `min_instance_count = 0` para desligar totalmente os contêineres quando não houver tráfego.
2. **Google Cloud Storage (Data Lake):** Buckets separados para camadas `raw`, `curated` e `quarantine` (DLQ), com políticas de ciclo de vida configuradas para mover arquivos isolados para arquivamento frio (Nearline) após 30 dias.
3. **Secret Manager:** Armazenamento centralizado e seguro de chaves de API e credenciais de banco.
4. **IAM Least Privilege:** Service Account dedicada (`dataops-ai-runner`) com acesso restrito apenas aos buckets e segredos do projeto.
5. **CI/CD Automatizado:** Pipeline no GitHub Actions (`.github/workflows/ci_cd.yml`) com execução de testes, validação estática de Terraform e autenticação via Workload Identity Federation (sem chaves JSON estáticas).

### Como inicializar a infraestrutura com Terraform

```bash
cd infra
terraform init
terraform plan
```

Caso deseje provisionar no seu projeto GCP:

```bash
terraform apply -var="project_id=SEU_PROJECT_ID"
```

### Práticas de FinOps e Custo Zero

- **Free Tier permanente:** Cloud Run oferece 2 milhões de requisições gratuitas por mês, o GCS oferece 5 GB e o Secret Manager oferece 6 segredos ativos gratuitos.
- **Instância Cloud SQL desativada por padrão:** A variável `enable_cloud_sql` vem definida como `false` para evitar custos fixos de instâncias gerenciadas, permitindo o uso de PostgreSQL serverless gratuito (ex: Neon/Supabase) ou execução local.
- **Destruição rápida:** Para encerrar todos os recursos após testes, basta executar:

```bash
cd infra
terraform destroy -var="project_id=SEU_PROJECT_ID"
```


## Agentes Autônomos

* **`AgentOrchestrator`:** Coordena a execução completa: pipeline, validações, diagnóstico, investigação, resolução e persistência dos relatórios.
* **`DataQualityAgent`:** Analisa o relatório de qualidade, verifica drift estatístico (Z-Score) e vazamento de PII. Usa Gemini quando configurado e fallback local determinístico.
* **`InvestigationAgent`:** Consulta logs, banco e a quarentena (DLQ) para levantar evidências do incidente.
* **`ResolutionAgent`:** Gera planos de resolução com correções sugeridas, ações preventivas, impacto e indicação de necessidade de revisão manual.
