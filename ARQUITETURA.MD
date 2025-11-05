# 📖 Documentação de Decisões Arquiteturais

Este documento detalha as decisões técnicas, trade-offs e a arquitetura geral da solução para o Nola God Level Coder Challenge, focada em resolver as dores da utilizadora "Maria".

## 1. Arquitetura da Solução

A aplicação foi construída com uma arquitetura Full Stack modular, separando o frontend (apresentação) do backend (lógica de negócio e dados), comunicando via uma API RESTful.

### 🖥️ Frontend (React)

* **Framework:** React + Vite
* **Justificativa:** O Vite foi escolhido pela sua performance de desenvolvimento (HMR rápido). O React permite uma arquitetura baseada em componentes, ideal para criar uma UI complexa, mas reutilizável (ex: os componentes `AnalyticsDashboard` e `ClientesEmRisco`).
* **Bibliotecas-chave:**
    * `Recharts`: Para visualização de dados (gráficos).
    * `react-datepicker`: Para os filtros de período de data.
    * `axios`: Para a comunicação com o backend.

### ⚡ Backend (FastAPI + PostgreSQL + Redis)

* **Framework:** FastAPI (Python)
* **Justificativa:** O FastAPI foi escolhido pela sua altíssima performance assíncrona (ideal para operações de I/O de banco de dados e cache) e pela sua integração nativa com Pydantic, que valida automaticamente os filtros da API.
* **Banco de Dados:** PostgreSQL (Fornecido pelo desafio).
* **Cache:** Redis.
* **Exportação:** Pandas (para geração de CSV).

## 2. Decisões Técnicas Chave (Justificativas)

A avaliação foca em "como você pensa". Esta tabela resume os trade-offs:

| Decisão | Justificativa |
| :--- | :--- |
| **React + Recharts** | Simplicidade, reatividade e boa documentação. Permite criar gráficos interativos (como o `Brush` para zoom) de forma rápida. |
| **FastAPI + PostgreSQL** | Alta performance. O Python tem uma integração nativa e robusta com o ecossistema de dados (Pandas), o que facilitou a funcionalidade de "Exportar CSV". |
| **Implementação de Cache (Redis)** | **Requisito Crítico.** O desafio exigia "queries rápidas". O Redis armazena os resultados das consultas da API, reduzindo a latência de >1s para <50ms em pedidos repetidos (Cache HITs). |
| **SQL Dinâmico via Mapeamento** | Para evitar Injeção de SQL, o backend não aceita SQL puro. Ele usa dicionários (METRICS_MAP, DIMENSIONS_MAP) para mapear parâmetros seguros (ex: "ticket_medio") para trechos de SQL válidos ("AVG(v.total_amount)"). |
| **Arquitetura Modular (Abas)** | O frontend foi dividido em duas abas ("Dashboard" e "Clientes") para separar as preocupações. O Dashboard foca em *agregação*, e a Análise de Clientes foca em *segmentação*, melhorando a UX. |

## 3. Performance e Escalabilidade

* **Cache (Redis):** Todas as consultas principais da API (`/api/analytics`, `/api/clientes-em-risco`, `/api/lojas`, etc.) são cacheadas com um TTL (Time-to-Live) de 10 minutos. Isto garante que cliques repetidos nos filtros sejam instantâneos.
* **Queries Otimizadas:** As consultas ao PostgreSQL usam `GROUP BY` e `JOINs` eficientes.
* **Limite de Dados:** O endpoint `/api/analytics` (usado pelo gráfico) limita os resultados em 50 (`LIMIT 50`) para manter o frontend responsivo. O endpoint de exportação (`/api/exportar-csv`) remove este limite para fornecer o relatório completo.

## 4. Lacuna Identificada (Margem de Lucro)

A "dor" do utilizador sobre **"Quais produtos têm menor margem...?"** não foi implementada.

* **Justificativa:** A análise do schema de dados fornecido (`database-schema.sql`) revelou que, embora tenhamos o preço de venda (`base_price`), o **preço de custo** do produto não está disponível.
* **Conclusão:** Sem o custo, é impossível calcular a margem (`Venda - Custo`). A aplicação está pronta para receber esta métrica assim que os dados de custo forem disponibilizados no banco.