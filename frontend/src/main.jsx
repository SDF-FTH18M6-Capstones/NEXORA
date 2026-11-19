import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/nexora.css'
import './styles/nexora-2.css'
import './styles/tailwind.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
