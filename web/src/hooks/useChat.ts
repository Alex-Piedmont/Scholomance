import { useState, useCallback } from 'react'
import { chatApi } from '../api/client'
import type { ChatMessage, TechnologyFilters } from '../api/types'

interface UseChatResult {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
  fallback: boolean
  llmAvailable: boolean
  sendMessage: (query: string, filters: TechnologyFilters) => Promise<void>
  clearMessages: () => void
}

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fallback, setFallback] = useState(false)
  const [llmAvailable, setLlmAvailable] = useState(true)

  const sendMessage = useCallback(async (query: string, filters: TechnologyFilters) => {
    if (!query.trim()) return

    // Append user message
    const userMessage: ChatMessage = { role: 'user', content: query }
    setMessages(prev => [...prev, userMessage])
    setLoading(true)
    setError(null)

    // Build history from existing messages (exclude the one we just added)
    const history = messages.map(m => ({ role: m.role, content: m.content }))

    // Build filter payload
    const chatFilters = {
      university: filters.university,
      top_field: filters.top_field,
      subfield: filters.subfield,
      patent_status: filters.patent_status,
      from_date: filters.from_date,
      to_date: filters.to_date,
    }

    try {
      const response = await chatApi.send({
        query,
        filters: chatFilters,
        history,
      })

      setFallback(response.fallback)
      setLlmAvailable(response.llm_available)

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        technologies: response.technologies,
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'Failed to get response'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [messages])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
    setFallback(false)
    setLlmAvailable(true)
  }, [])

  return {
    messages,
    loading,
    error,
    fallback,
    llmAvailable,
    sendMessage,
    clearMessages,
  }
}
