# DataOps AI

Plataforma de operações com agentes de IA para monitorar pipelines, detectar problemas de qualidade e gerar diagnósticos.

## Objetivo atual

Construir o core, sem interface:

```text
BCB API -> Extraction -> Transform -> Banco -> Data Quality -> Agent Orchestrator -> Quality Agent -> Investigation Agent -> Resolution Agent
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

## Simular incidentes

```bash
python main.py cenarios
python main.py rodar --scenario valores_nulos
python main.py rodar --scenario mudanca_estrutura
python main.py rodar --scenario registros_duplicados
python main.py rodar --scenario tipo_invalido
python main.py rodar --scenario timeout_api
```

O cenario `timeout_api` simula uma falha na coleta, usa fallback local e registra isso nos logs para o agente de investigacao analisar.

## Gemini

Crie `.env` a partir de `.env.example` e preencha `GEMINI_API_KEY`. Sem chave, o agente usa diagnostico local por regras.

## Agentes

- `AgentOrchestrator`: coordena pipeline, validacoes e agentes.
- `DataQualityAgent`: interpreta as falhas de qualidade e gera o diagnostico.
- `InvestigationAgent`: consulta banco e logs para levantar evidencias do incidente.
- `ResolutionAgent`: sugere plano de correcao e gera relatorio de incidente.
