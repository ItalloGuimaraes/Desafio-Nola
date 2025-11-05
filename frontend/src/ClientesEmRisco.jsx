import { useState, useEffect } from 'react'
import axios from 'axios'

// Define a URL dA API
const API_URL = 'http://localhost:8000'

function ClientesEmRisco() {
  const [clientes, setClientes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const buscarClientes = async () => {
      try {
        setLoading(true)
        const resposta = await axios.get(`${API_URL}/api/clientes-em-risco`)
        setClientes(resposta.data)
        setError(null)
      } catch (err) {
        setError('Falha ao buscar clientes em risco.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    buscarClientes()
  }, []) 

  if (loading) {
    return <h2>Carregando clientes em risco...</h2>
  }

  if (error) {
    return <h2 style={{ color: 'red' }}>{error}</h2>
  }

  return (
    <div className="clientes-container">
      <h2>Clientes em Risco (3+ compras, sem voltar há 30+ dias)</h2>
      <p>Esta é a lista de clientes que a Maria precisa contactar para reengajamento.</p>
      <table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>Email</th>
            <th>Telefone</th>
            <th>Total de Compras</th>
            <th>Última Compra (dias)</th>
            <th>Valor Total Gasto (R$)</th>
          </tr>
        </thead>
        <tbody>
          {clientes.map((cliente) => (
            <tr key={cliente.email}>
              <td>{cliente.customer_name}</td>
              <td>{cliente.email}</td>
              <td>{cliente.phone_number}</td>
              <td>{cliente.total_compras}</td>
              <td>{cliente.dias_desde_ultima_compra}</td>
              <td>{parseFloat(cliente.ltv_total).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ClientesEmRisco