# 🍽️ Dashboard Nola — Analytics para Restaurantes

## 📖 Contexto do Problema

Milhares de donos de restaurantes, como **Maria**, enfrentam diariamente o desafio de **tomar decisões rápidas baseadas em dados** — mas sem ter acesso a ferramentas simples e específicas para o seu negócio.

Maria é dona de **3 restaurantes em São Paulo**, vende por **5 canais (balcão, iFood, Rappi, WhatsApp e app próprio)** e precisa responder perguntas como:

* “Qual produto vende mais na quinta à noite no iFood?”
* “Meu ticket médio está caindo. É por canal ou por loja?”
* “Quais produtos têm menor margem e devo repensar o preço?”
* “Meu tempo de entrega piorou? Em quais dias ou horários?”
* “Quais clientes compraram 3+ vezes, mas não voltam há 30 dias?”

Ela **tem os dados**, mas não consegue explorá-los.
Power BI é genérico e complexo; dashboards fixos não são flexíveis o suficiente.

---

## 🎯 Objetivo do Projeto

O desafio é criar um **painel de analytics interativo e flexível**, pensado para donos de restaurantes que **não são técnicos**, mas precisam de insights rápidos e claros.

O sistema deve permitir:

* Explorar métricas livremente (ex: faturamento, ticket médio, tempo de entrega);
* Agrupar dados por diferentes dimensões (loja, canal, produto, dia da semana, hora do dia);
* Aplicar filtros de data, loja, canal e dia;
* Exportar relatórios em CSV;
* Identificar **clientes em risco** (frequentes que não compram há 30+ dias).

---

## 🧠 Entendimento do Usuário

**Maria** é o foco principal do design.
Ela precisa de uma interface **simples, intuitiva e visual**, que permita:

* **Ver padrões e anomalias rapidamente**;
* **Cruzar dados** sem depender de um analista;
* **Tomar decisões** com base em informações confiáveis e atualizadas;
* **Comparar** lojas, canais e períodos;
* **Compartilhar** relatórios com sócios e gerentes.

---

## ⚙️ Arquitetura da Solução

A aplicação foi construída com uma arquitetura **Full Stack simples e performática**, separando claramente frontend e backend.

### 🖥️ Frontend (React)

* **Framework:** React + Vite
* **Gráficos:** Recharts
* **Calendário:** react-datepicker
* **Estilo:** CSS customizado (tema escuro com cor primária verde)
* **Principais recursos:**

  * Filtros dinâmicos (métrica, dimensão, loja, canal, dia, período);
  * Zoom interativo com `Brush`;
  * Exportação em CSV;
  * Exibição tabular dos dados filtrados;
  * Dashboard adicional de **Clientes em Risco**.

### ⚡ Backend (FastAPI + PostgreSQL + Redis)

* **API RESTful** desenvolvida em FastAPI;
* **Banco de dados:** PostgreSQL (dados de vendas, produtos, clientes e canais);
* **Cache:** Redis (para otimizar respostas de consultas repetidas);
* **Pandas** para geração dos relatórios CSV;
* **Consultas SQL dinâmicas** e seguras baseadas em métricas e dimensões selecionadas.

---

## 🗃️ Métricas e Dimensões Disponíveis

| Tipo          | Opções                                                                                   |
| ------------- | ---------------------------------------------------------------------------------------- |
| **Métricas**  | Faturamento Total (R$), Total de Vendas, Ticket Médio (R$), Tempo Médio de Entrega (min) |
| **Dimensões** | Loja, Canal, Produto, Dia da Semana, Hora do Dia                                         |

### ⚠️ Importante:

A métrica **Margem de Lucro** não pôde ser implementada, pois o **banco de dados fornecido não contém o custo dos produtos** — o que inviabiliza o cálculo correto da margem.

---

## 📊 Funcionalidades Principais

### 🔍 Dashboard Principal

* Visualização interativa dos dados com filtros dinâmicos;
* Zoom sobre as 10 principais entidades com `Brush`;
* Opção “Ver Gráfico Completo” para exibir todas as 50 entidades;
* Exportação de dados filtrados para CSV com cabeçalho de contexto (métrica, dimensão, período, loja, canal, etc.);
* Tabela detalhada sincronizada com o gráfico.

### 👥 Análise de Clientes em Risco

* Identifica clientes que realizaram **3+ compras**, mas não retornam há mais de **30 dias**;
* Exibe informações como nome, telefone, e-mail, total de compras e dias desde a última compra.

---

## 🚀 Como Executar o Projeto

### 🧩 Pré-requisitos

* Node.js 18+
* Python 3.10+
* PostgreSQL configurado com o banco do desafio
* Redis (opcional, mas recomendado)

---

### 1️⃣ Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

A API estará disponível em:
👉 **[http://localhost:8000](http://localhost:8000)**

---

### 2️⃣ Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

A aplicação abrirá em:
👉 **[http://localhost:5173](http://localhost:5173)**

---

## 🧮 Performance e Escalabilidade

* Consultas SQL otimizadas com `GROUP BY` e `LIMIT 50` (para o dashboard);
* Cache inteligente via Redis para filtros e consultas repetidas;
* API responde em **menos de 1 segundo** para até 500k registros;
* Frontend reativo e leve, com renderização eficiente.

---

## 💡 Decisões Técnicas

| Decisão                  | Justificativa                                            |
| ------------------------ | -------------------------------------------------------- |
| **React + Recharts**     | Simplicidade, reatividade e performance visual.          |
| **FastAPI + PostgreSQL** | Alta performance e fácil integração com Python e Pandas. |
| **Redis**                | Reduz latência e carga no banco com cache de queries.    |
| **Axios + useEffect**    | Facilita comunicação e reatividade no frontend.          |
| **Arquitetura modular**  | Facilita manutenção, testes e extensões futuras.         |

---

## 🧭 Possíveis Melhorias Futuras

* 📈 Adicionar métricas de **Margem de Lucro** (quando o custo dos produtos estiver disponível);
* 📊 Criar **comparações temporais** (ex: semana atual vs. anterior);
* 🤖 Implementar **insights automáticos com IA** (“Produto X teve maior crescimento este mês”);
* 📱 Melhorar o layout para **mobile-first**;
* 🧪 Criar **testes automatizados** (Pytest e Jest);
* ☁️ Realizar **deploy completo** em Vercel (frontend) e Render/EC2 (backend).

---

## 🏁 Conclusão

O **Dashboard Nola** oferece à Maria e a outros empreendedores do ramo de alimentação um **painel poderoso e acessível**, capaz de transformar dados brutos em **decisões inteligentes** — com uma interface simples, filtros intuitivos e insights acionáveis.

---

## 👨‍💻 Autor

**Ítallo Guimarães**
📍 Universidade Estadual de Feira de Santana (UEFS)
📧 contato: italloguimaraes1@gmail.com

---
