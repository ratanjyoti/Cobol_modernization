import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { Toaster } from 'react-hot-toast';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Toaster
      position="top-right"
      toastOptions={{
        style: {
          background: '#0f172a',
          color: '#f8fafc',
          border: '1px solid rgba(51, 65, 85, 0.82)',
        },
      }}
    />
    <App />
  </React.StrictMode>,
)
