# DataOps AI · Frontend

Cockpit React/TypeScript para observabilidade diária, qualidade de dados e governança de pipelines.

## Executar localmente

```bash
npm install
npm run dev
```

Por padrão, o Vite encaminha `/api` para `http://127.0.0.1:8000`. Para usar outra API, defina `VITE_API_URL`.

## Princípios de produto

- Uma fonte indisponível nunca é exibida como saudável; a interface mantém o último dado disponível e sinaliza a degradação.
- O cockpit prioriza incidente ativo, freshness e qualidade recente antes de gráficos exploratórios.
- O simulador fica isolado em **Laboratório** e deve ser protegido por RBAC e trilha de auditoria no backend antes de uso produtivo.
- As ações de reprocessamento, aprovação de DLQ e acknowledgment devem ser expostas pelo backend com identidade, autorização e motivo auditável.

## Contrato de API usado

- `GET /status`
- `GET /cenarios`
- `GET /historico?limit=100`
- `GET /dados/gold?limit=250`
- `GET /dados/quarentena`
- `POST /execucoes`

## Verificação

```bash
npx tsc -p tsconfig.app.json --noEmit --incremental false
npx tsc -p tsconfig.node.json --noEmit --incremental false
```
