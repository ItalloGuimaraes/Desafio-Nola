import { useState, useEffect } from 'react'
import axios from 'axios'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush 
} from 'recharts'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { format } from 'date-fns'
import './App.css'
import ClientesEmRisco from './ClientesEmRisco'

const API_URL = 'http://localhost:8000'

const METRIC_LABELS = {
  'faturamento_total': 'Faturamento Total (R$)',
  'total_de_vendas': 'Total de Vendas',
  'ticket_medio': 'Ticket Médio (R$)',
  'tempo_entrega_min': 'Tempo Médio de Entrega (min)'
}

const DIMENSION_LABELS = {
  'loja': 'Por Loja',
  'canal': 'Por Canal',
  'produto': 'Por Produto',
  'dia_da_semana': 'Por Dia da Semana',
  'hora_do_dia': 'Por Hora do Dia'
}

function AnalyticsDashboard() {
  const [dadosDaTabela, setDadosDaTabela] = useState([])
  const [canais, setCanais] = useState([])
  const [lojas, setLojas] = useState([])
  const [diasSemana, setDiasSemana] = useState([])

  const [canalSelecionado, setCanalSelecionado] = useState('')
  const [lojaSelecionada, setLojaSelecionada] = useState('')
  const [diaSelecionado, setDiaSelecionado] = useState('')
  const [metricSelecionada, setMetricSelecionada] = useState('faturamento_total')
  const [dimensionSelecionada, setDimensionSelecionada] = useState('loja')
  const [startDate, setStartDate] = useState(null)
  const [endDate, setEndDate] = useState(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isExporting, setIsExporting] = useState(false)

  const [brushStartIndex, setBrushStartIndex] = useState(0)
  const [brushEndIndex, setBrushEndIndex] = useState(9)
  const [isZoomActive, setIsZoomActive] = useState(true)

  useEffect(() => {
    const buscarFiltros = async () => {
      setLoading(true)
      try {
        const [respostaCanais, respostaLojas, respostaDias] = await Promise.all([
          axios.get(`${API_URL}/api/canais`),
          axios.get(`${API_URL}/api/lojas`),
          axios.get(`${API_URL}/api/dias-semana`)
        ])
        setCanais(respostaCanais.data)
        setLojas(respostaLojas.data)
        setDiasSemana(respostaDias.data)
      } catch (err) {
        setError('Falha ao buscar a lista de filtros.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    buscarFiltros()
  }, [])

  useEffect(() => {
    const filtrosBasicosCarregados = canais.length > 0 && lojas.length > 0 && diasSemana.length > 0
    if (!filtrosBasicosCarregados && loading) return

    const buscarDados = async () => {
      setLoading(true)
      try {
        const params = {
          metric: metricSelecionada,
          dimension: dimensionSelecionada
        }
        if (canalSelecionado) params.channel_id = canalSelecionado
        if (lojaSelecionada) params.store_id = lojaSelecionada
        if (diaSelecionado && dimensionSelecionada !== 'dia_da_semana') params.dia_semana = diaSelecionado
        if (startDate) params.date_from = format(startDate, 'yyyy-MM-dd')
        if (endDate) params.date_to = format(endDate, 'yyyy-MM-dd')

        const resposta = await axios.get(`${API_URL}/api/analytics`, { params })
        const data = resposta.data
        setDadosDaTabela(data)

        setBrushStartIndex(0)
        setBrushEndIndex(Math.min(9, data.length > 0 ? data.length - 1 : 0))
        setError(null)
      } catch (err) {
        setError('Falha ao buscar dados da API. O backend está rodando?')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    buscarDados()
  }, [
    canalSelecionado, lojaSelecionada, diaSelecionado, metricSelecionada,
    dimensionSelecionada, startDate, endDate, canais.length, lojas.length, diasSemana.length
  ])

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const params = {
        metric: metricSelecionada,
        dimension: dimensionSelecionada
      }
      if (canalSelecionado) params.channel_id = canalSelecionado
      if (lojaSelecionada) params.store_id = lojaSelecionada
      if (diaSelecionado && dimensionSelecionada !== 'dia_da_semana') params.dia_semana = diaSelecionado
      if (startDate) params.date_from = format(startDate, 'yyyy-MM-dd')
      if (endDate) params.date_to = format(endDate, 'yyyy-MM-dd')

      const response = await axios.get(`${API_URL}/api/exportar-csv`, {
        params,
        responseType: 'blob'
      })

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `relatorio_nola_${new Date().toISOString().split('T')[0]}.csv`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      setError('Falha ao exportar CSV.')
      console.error(err)
    } finally {
      setIsExporting(false)
    }
  }

  const handleToggleZoom = () => {
    const total = dadosDaTabela.length > 0 ? dadosDaTabela.length - 1 : 0
    setIsZoomActive(prev => {
      if (prev) {
        setBrushStartIndex(0)
        setBrushEndIndex(total)
        return false
      } else {
        setBrushStartIndex(0)
        setBrushEndIndex(Math.min(9, total))
        return true
      }
    })
  }

  const formatarValor = (valor) => {
    const valorNum = parseFloat(valor)
    if (metricSelecionada === 'total_de_vendas') {
      return valorNum.toLocaleString('pt-BR')
    }
    return valorNum.toFixed(2)
  }

  const formatarEntidade = (entidade) => {
    if (dimensionSelecionada === 'hora_do_dia') {
      return `${entidade}:00 - ${entidade}:59`
    }
    return entidade
  }

  const mostrarFiltroDeDia = dimensionSelecionada !== 'dia_da_semana'

  if (error) {
    return <div className="App"><h1 style={{ color: 'red' }}>{error}</h1></div>
  }

  return (
    <div className="analytics-dashboard">

      {/* FILTROS */}
      <div className="filtros">
        <label htmlFor="metric-select">Ver Métrica:</label>
        <select id="metric-select" value={metricSelecionada} onChange={(e) => setMetricSelecionada(e.target.value)}>
          {Object.keys(METRIC_LABELS).map((metricKey) => (
            <option key={metricKey} value={metricKey}>{METRIC_LABELS[metricKey]}</option>
          ))}
        </select>
        <label htmlFor="dimension-select">Agrupar Por:</label>
        <select id="dimension-select" value={dimensionSelecionada} onChange={(e) => setDimensionSelecionada(e.target.value)}>
          {Object.keys(DIMENSION_LABELS).map((dimensionKey) => (
            <option key={dimensionKey} value={dimensionKey}>{DIMENSION_LABELS[dimensionKey]}</option>
          ))}
        </select>
        <label htmlFor="loja-select">Filtrar por Loja:</label>
        <select id="loja-select" value={lojaSelecionada} onChange={(e) => setLojaSelecionada(e.target.value)}>
          <option value="">Todas as Lojas</option>
          {lojas.map((loja) => (<option key={loja.id} value={loja.id}>{loja.name}</option>))}
        </select>
        <label htmlFor="canal-select">Filtrar por Canal:</label>
        <select id="canal-select" value={canalSelecionado} onChange={(e) => setCanalSelecionado(e.target.value)}>
          <option value="">Todos os Canais</option>
          {canais.map((canal) => (<option key={canal.id} value={canal.id}>{canal.name}</option>))}
        </select>
        {mostrarFiltroDeDia && (
          <>
            <label htmlFor="dia-select">Filtrar por Dia:</label>
            <select id="dia-select" value={diaSelecionado} onChange={(e) => setDiaSelecionado(e.target.value)}>
              <option value="">Todos os Dias</option>
              {diasSemana.map((dia) => (<option key={dia.id} value={dia.id}>{dia.name}</option>))}
            </select>
          </>
        )}
      </div>

      <div className="filtros">
        <label>De:</label>
        <DatePicker selected={startDate} onChange={(date) => setStartDate(date)} selectsStart startDate={startDate} endDate={endDate} isClearable placeholderText="Início" />
        <label>Até:</label>
        <DatePicker selected={endDate} onChange={(date) => setEndDate(date)} selectsEnd startDate={startDate} endDate={endDate} minDate={startDate} isClearable placeholderText="Fim" />
        <button onClick={handleExport} disabled={isExporting} className="export-button">
          {isExporting ? 'A exportar...' : 'Exportar CSV'}
        </button>
      </div>

      {loading ? (
        <h2>Carregando dados...</h2>
      ) : (
        <div className="visualizacao-container">
          <button onClick={handleToggleZoom} className="zoom-button" style={{ marginBottom: '10px' }}>
            {isZoomActive ? 'Ver Gráfico Completo' : 'Ligar Zoom (Foco no Top 10)'}
          </button>

          {/* --- GRÁFICO --- */}
          <ResponsiveContainer width="100%" height={500}>
            <BarChart 
              key={`chart-${isZoomActive}-${dadosDaTabela.length}`}
              data={dadosDaTabela}
              margin={{ top: 5, right: 30, left: 20, bottom: 120 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="nome_entidade" angle={-45} textAnchor="end" interval={0} height={140}
                tick={{ fontSize: 14, fill: 'var(--text-color)', fontWeight: '600' }} />
              <YAxis tick={{ fontSize: 14, fill: 'var(--text-color)', fontWeight: '600' }} />
              <Legend verticalAlign="top" align="right" height={36} />
              <Tooltip formatter={(value) => formatarValor(value)} />
              <Bar dataKey="valor_metrica" fill="var(--primary-color)" name={METRIC_LABELS[metricSelecionada]} isAnimationActive={false} />

              {/* --- BRUSH: Só aparece quando o zoom está ativo --- */}
              {isZoomActive && (
                <Brush
                  dataKey="nome_entidade"
                  height={30}
                  stroke="var(--primary-color)"
                  startIndex={brushStartIndex}
                  endIndex={brushEndIndex}
                  onChange={(e) => {
                    if (e) {
                      setBrushStartIndex(e.startIndex)
                      setBrushEndIndex(e.endIndex)
                    }
                  }}
                  y={430} // Desce mais a barra do zoom
                />
              )}
            </BarChart>
          </ResponsiveContainer>

          {/* --- TABELA DE DADOS --- */}
          <h2>Dados Completos</h2>
          <table>
            <thead>
              <tr>
                <th>{DIMENSION_LABELS[dimensionSelecionada]}</th>
                <th>{METRIC_LABELS[metricSelecionada]}</th>
              </tr>
            </thead>
            <tbody>
              {(isZoomActive
                ? dadosDaTabela.slice(brushStartIndex, brushEndIndex + 1)
                : dadosDaTabela
              ).map((linha, index) => (
                <tr key={`${linha.nome_entidade}-${index}`}>
                  <td>{formatarEntidade(linha.nome_entidade)}</td>
                  <td>{formatarValor(linha.valor_metrica)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function App() {
  const [abaAtiva, setAbaAtiva] = useState('dashboard')

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <h1>Dashboard Nola</h1>
          <nav>
            <button onClick={() => setAbaAtiva('dashboard')} className={abaAtiva === 'dashboard' ? 'active' : ''}>
              Dashboard Principal
            </button>
            <button onClick={() => setAbaAtiva('clientes')} className={abaAtiva === 'clientes' ? 'active' : ''}>
              Análise de Clientes
            </button>
          </nav>
        </div>
      </header>

      <main className="content-wrapper">
        {abaAtiva === 'dashboard' && <AnalyticsDashboard />}
        {abaAtiva === 'clientes' && <ClientesEmRisco />}
      </main>
    </div>
  )
}

export default App
