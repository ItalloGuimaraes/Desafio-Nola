import os
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional
from datetime import date
import redis
import json
import pandas as pd
from io import StringIO
from starlette.responses import StreamingResponse

# Configura o logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Configuração de CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuração do Cache (Redis) ---
try:
    cache = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    cache.ping()
    logger.info("Conexão com o Redis bem-sucedida!")
except redis.exceptions.ConnectionError as e:
    logger.error(f"Não foi possível conectar ao Redis: {e}. A aplicação continuará sem cache.")
    cache = None

# --- Conexão com o Banco de Dados ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5433"),
            database=os.getenv("DB_NAME", "challenge_db"),
            user=os.getenv("DB_USER", "challenge"),
            password=os.getenv("DB_PASSWORD", "challenge_2024")
        )
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# --- Definições Seguras de Métricas e Dimensões ---
METRICS_MAP = {
    "faturamento_total": "SUM(v.total_amount)",
    "total_de_vendas": "COUNT(v.id)",
    "ticket_medio": "AVG(v.total_amount)",
    "tempo_entrega_min": "AVG(v.delivery_seconds) / 60.0"
}
# Adicionamos os nomes 'amigáveis' para o relatório
METRIC_LABELS_FOR_REPORT = {
    "faturamento_total": "Faturamento Total (R$)",
    "total_de_vendas": "Total de Vendas",
    "ticket_medio": "Ticket Médio (R$)",
    "tempo_entrega_min": "Tempo Médio de Entrega (min)"
}

DIMENSIONS_MAP = {
    "loja": {"field": "s.name", "join": "JOIN stores s ON v.store_id = s.id", "label": "nome_entidade", "label_report": "Loja"},
    "canal": {"field": "c.name", "join": "JOIN channels c ON v.channel_id = c.id", "label": "nome_entidade", "label_report": "Canal"},
    "produto": {"field": "p.name", "join": "JOIN product_sales ps ON ps.sale_id = v.id JOIN products p ON ps.product_id = p.id", "label": "nome_entidade", "label_report": "Produto"},
    "dia_da_semana": {"field": "CASE EXTRACT(DOW FROM v.created_at) WHEN 0 THEN 'Domingo' WHEN 1 THEN 'Segunda-feira' WHEN 2 THEN 'Terça-feira' WHEN 3 THEN 'Quarta-feira' WHEN 4 THEN 'Quinta-feira' WHEN 5 THEN 'Sexta-feira' WHEN 6 THEN 'Sábado' END", "join": "", "label": "nome_entidade", "label_report": "Dia da Semana"},
    "hora_do_dia": {"field": "EXTRACT(HOUR FROM v.created_at)::INTEGER", "join": "", "label": "nome_entidade", "label_report": "Hora do Dia"}
}

# --- Funções de Cache ---
def get_from_cache(key: str):
    if cache is None: return None
    try:
        cached_data = cache.get(key)
        if cached_data:
            logger.info(f"Cache HIT para a chave: {key}")
            return json.loads(cached_data)
        logger.info(f"Cache MISS para a chave: {key}")
        return None
    except redis.exceptions.RedisError as e:
        logger.error(f"Erro ao ler do Redis: {e}")
        return None

def set_to_cache(key: str, data: any, ttl_seconds: int = 600):
    if cache is None: return
    try:
        cache.setex(key, ttl_seconds, json.dumps(data, default=str))
        logger.info(f"Cache SET para a chave: {key}")
    except redis.exceptions.RedisError as e:
        logger.error(f"Erro ao escrever no Redis: {e}")

# --- LÓGICA DE QUERY REUTILIZÁVEL ---
def build_analytics_query(
    metric: str, dimension: str, channel_id: Optional[int],
    store_id: Optional[int], dia_semana: Optional[int],
    date_from: Optional[date], date_to: Optional[date]
):
    if metric not in METRICS_MAP:
        raise HTTPException(status_code=400, detail="Métrica inválida")
    if dimension not in DIMENSIONS_MAP:
        raise HTTPException(status_code=400, detail="Dimensão inválida")

    metric_sql = METRICS_MAP[metric]
    dimension_info = DIMENSIONS_MAP[dimension]
    dimension_field = dimension_info["field"]
    dimension_join = dimension_info["join"]
    dimension_label = dimension_info["label"]

    where_clauses = ["v.sale_status_desc = 'COMPLETED'"]
    params = []

    if channel_id is not None:
        where_clauses.append("v.channel_id = %s")
        params.append(channel_id)
    if store_id is not None:
        where_clauses.append("v.store_id = %s")
        params.append(store_id)
    if dia_semana is not None:
        where_clauses.append("EXTRACT(DOW FROM v.created_at) = %s")
        params.append(dia_semana)
    if date_from is not None:
        where_clauses.append("CAST(v.created_at AS DATE) >= %s")
        params.append(date_from)
    if date_to is not None:
        where_clauses.append("CAST(v.created_at AS DATE) <= %s")
        params.append(date_to)
    if metric == "tempo_entrega_min":
        where_clauses.append("v.delivery_seconds IS NOT NULL")

    where_sql = " AND ".join(where_clauses)
    
    sql = f"""
        SELECT 
            {dimension_field} AS {dimension_label},
            {metric_sql} AS valor_metrica 
        FROM sales v
        {dimension_join}
        WHERE {where_sql}
        GROUP BY {dimension_field}
        ORDER BY valor_metrica DESC
    """
    return sql, params

# --- Endpoints de Filtros (com cache) ---
@app.get("/")
def read_root():
    return {"message": "API de Analytics da Nola está no ar!"}
@app.get("/api/canais")
def get_canais():
    cache_key = "filtros:canais"
    cached_data = get_from_cache(cache_key)
    if cached_data: return cached_data
    conn = get_db_connection()
    if conn is None: raise HTTPException(status_code=500, detail="Não foi possível conectar ao banco de dados")
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id, name FROM channels ORDER BY name;")
        canais = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        set_to_cache(cache_key, canais)
        return canais
    except Exception as e:
        logger.error(f"Erro na query de canais: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/lojas")
def get_lojas():
    cache_key = "filtros:lojas"
    cached_data = get_from_cache(cache_key)
    if cached_data: return cached_data
    conn = get_db_connection()
    if conn is None: raise HTTPException(status_code=500, detail="Não foi possível conectar ao banco de dados")
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id, name FROM stores WHERE is_active = true ORDER BY name;")
        lojas = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        set_to_cache(cache_key, lojas)
        return lojas
    except Exception as e:
        logger.error(f"Erro na query de lojas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/dias-semana")
def get_dias_semana():
    cache_key = "filtros:dias_semana"
    cached_data = get_from_cache(cache_key)
    if cached_data: return cached_data
    dias = [{"id": 0, "name": "Domingo"}, {"id": 1, "name": "Segunda-feira"}, {"id": 2, "name": "Terça-feira"}, {"id": 3, "name": "Quarta-feira"}, {"id": 4, "name": "Quinta-feira"}, {"id": 5, "name": "Sexta-feira"}, {"id": 6, "name": "Sábado"}]
    set_to_cache(cache_key, dias, ttl_seconds=3600)
    return dias

# --- Endpoint de Agregação (Usa o cache) ---
@app.get("/api/analytics")
def get_analytics(
    metric: str = Query("faturamento_total"),
    dimension: str = Query("loja"),
    channel_id: Optional[int] = Query(None),
    store_id: Optional[int] = Query(None),
    dia_semana: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None)
):
    cache_key = f"analytics:{metric}:{dimension}:{channel_id}:{store_id}:{dia_semana}:{date_from}:{date_to}"
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data
        
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Não foi possível conectar ao banco de dados")
    
    try:
        sql, params = build_analytics_query(metric, dimension, channel_id, store_id, dia_semana, date_from, date_to)
        sql += " LIMIT 50" # Adiciona o LIMITE apenas para o dashboard
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(sql, tuple(params))
        rows = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        set_to_cache(cache_key, rows)
        return rows
        
    except Exception as e:
        logger.error(f"Erro na query de analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT DE EXPORTAÇÃO (MODIFICADO) ---
@app.get("/api/exportar-csv")
def exportar_csv(
    metric: str = Query("faturamento_total"),
    dimension: str = Query("loja"),
    channel_id: Optional[int] = Query(None),
    store_id: Optional[int] = Query(None),
    dia_semana: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None)
):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Não foi possível conectar ao banco de dados")

    try:
        # 1. Constrói a query (SEM LIMITE)
        sql, params = build_analytics_query(metric, dimension, channel_id, store_id, dia_semana, date_from, date_to)
        
        # 2. Executa a query
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(sql, tuple(params))
        rows = [dict(row) for row in cursor.fetchall()]
        
        if not rows:
            raise HTTPException(status_code=404, detail="Nenhum dado encontrado para exportar com estes filtros.")

        
        # 3. Busca os nomes dos filtros
        store_name = "Todas as Lojas"
        channel_name = "Todos os Canais"
        dia_name = "Todos os Dias"

        if store_id:
            cursor.execute("SELECT name FROM stores WHERE id = %s", (store_id,))
            store_name = cursor.fetchone()['name']
        if channel_id:
            cursor.execute("SELECT name FROM channels WHERE id = %s", (channel_id,))
            channel_name = cursor.fetchone()['name']
        if dia_semana is not None:
            # Reutiliza o endpoint estático
            dias = {d['id']: d['name'] for d in get_dias_semana()}
            dia_name = dias.get(dia_semana, str(dia_semana))

        cursor.close()
        conn.close()

        # 4. Converte os dados para DataFrame
        df = pd.DataFrame(rows)
        # Renomeia as colunas para ficarem amigáveis
        df = df.rename(columns={
            "nome_entidade": DIMENSIONS_MAP[dimension]['label_report'], # ex: 'Loja'
            "valor_metrica": METRIC_LABELS_FOR_REPORT[metric] # ex: 'Faturamento Total (R$)'
        })

        # 5. Cria o cabeçalho de metadados
        header = f"Relatorio Nola Gerado em: {date.today().isoformat()}\n\n"
        header += "Filtros Aplicados:\n"
        header += f"Metrica: {METRIC_LABELS_FOR_REPORT[metric]}\n"
        header += f"Agrupado Por: {DIMENSIONS_MAP[dimension]['label_report']}\n"
        header += f"Loja: {store_name}\n"
        header += f"Canal: {channel_name}\n"
        header += f"Dia da Semana: {dia_name}\n"
        header += f"De: {date_from if date_from else 'Inicio'}\n"
        header += f"Ate: {date_to if date_to else 'Fim'}\n\n"

        output = StringIO() # Cria um "ficheiro" em memória
        output.write(header) # Escreve o cabeçalho
        df.to_csv(output, index=False, sep=';', decimal=',') # Escreve os dados
        output.seek(0)

        # 6. Devolve o CSV como um download
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=relatorio_nola_{date.today()}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar CSV: {e}")
        # Fecha a conexão em caso de erro
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn: conn.close()
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint de Clientes (com cache)
@app.get("/api/clientes-em-risco")
def get_clientes_em_risco():
    cache_key = "segmentos:clientes_em_risco"
    cached_data = get_from_cache(cache_key) 
    if cached_data: return cached_data
    conn = get_db_connection()
    if conn is None: raise HTTPException(status_code=500, detail="Não foi possível conectar ao banco de dados")
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        sql = """
            WITH KpisClientes AS (
                SELECT customer_id, COUNT(id) AS total_compras, MAX(created_at) AS ultima_compra, SUM(total_amount) AS ltv_total
                FROM sales
                WHERE customer_id IS NOT NULL AND sale_status_desc = 'COMPLETED'
                GROUP BY customer_id
            )
            SELECT
                c.customer_name, c.phone_number, c.email,
                k.total_compras, k.ultima_compra, k.ltv_total,
                (CURRENT_DATE - k.ultima_compra::date) AS dias_desde_ultima_compra
            FROM KpisClientes k
            JOIN customers c ON k.customer_id = c.id
            WHERE k.total_compras >= 3 AND (CURRENT_DATE - k.ultima_compra::date) > 30
            ORDER BY dias_desde_ultima_compra DESC, k.total_compras DESC;
        """
        
        cursor.execute(sql)
        clientes = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        set_to_cache(cache_key, clientes, ttl_seconds=3600)
        return clientes
    except Exception as e:
        logger.error(f"Erro na query de clientes em risco: {e}")
        raise HTTPException(status_code=500, detail=str(e))