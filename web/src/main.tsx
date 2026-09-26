import '@fontsource/geist/latin-400.css'
import '@fontsource/geist/latin-500.css'
import '@fontsource/geist/latin-600.css'
import '@fontsource/geist-mono/latin-400.css'
import '@fontsource/geist-mono/latin-500.css'
import '@fontsource/geist-mono/latin-600.css'
import './styles/tokens.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HttpError } from './lib/api'
import { createAppRouter } from './router'

// one retry for a blip; never for a 404 (an unknown strategy won't appear on a second try)
const retry = (failures: number, error: Error) => !(error instanceof HttpError && error.status === 404) && failures < 1
const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry } } })
const router = createAppRouter()

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
