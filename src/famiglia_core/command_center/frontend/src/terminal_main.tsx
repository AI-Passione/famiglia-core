import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { TerminalApp } from './TerminalApp.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TerminalApp />
  </StrictMode>,
)
