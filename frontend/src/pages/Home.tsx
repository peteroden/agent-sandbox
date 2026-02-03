import { useEffect } from 'preact/hooks'
import { logger } from '../services/telemetry'

export function Home() {
  useEffect(() => {
    logger.info('Home page loaded')
  }, [])

  return (
    <div class="container mx-auto p-4">
      <h1 class="text-3xl font-bold mb-4">Home</h1>
      <p class="text-gray-600">Welcome to the frontend skeleton</p>
    </div>
  )
}
