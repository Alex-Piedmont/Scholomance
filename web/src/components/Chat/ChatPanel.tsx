import { useRef, useEffect } from 'react'
import { useChat } from '../../hooks/useChat'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import type { TechnologyFilters } from '../../api/types'

const EXAMPLE_QUERIES = [
  'What technologies address drug delivery challenges?',
  'Show me AI and machine learning innovations',
  'Find renewable energy solutions',
]

interface ChatPanelProps {
  filters: TechnologyFilters
  isOpen: boolean
  onToggle: () => void
}

export function ChatPanel({ filters, isOpen, onToggle }: ChatPanelProps) {
  const { messages, loading, error, fallback, llmAvailable, sendMessage, clearMessages } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = (query: string) => {
    sendMessage(query, filters)
  }

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-6 right-6 z-50 bg-blue-600 text-white rounded-full p-4 shadow-lg hover:bg-blue-700 transition-colors"
        title="Open chat"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      </button>
    )
  }

  return (
    <div className="w-[400px] shrink-0 border-l border-gray-200 flex flex-col bg-white h-[calc(100vh-64px)] sticky top-16">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h3 className="font-semibold text-sm text-gray-800">Chat Search</h3>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-xs text-gray-400 hover:text-gray-600"
              title="Clear conversation"
            >
              Clear
            </button>
          )}
          <button
            onClick={onToggle}
            className="text-gray-400 hover:text-gray-600 p-1"
            title="Close chat"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Notices */}
      {fallback && (
        <div className="px-3 py-1.5 bg-yellow-50 text-yellow-700 text-xs border-b border-yellow-200">
          Using text search (semantic search unavailable)
        </div>
      )}
      {!llmAvailable && (
        <div className="px-3 py-1.5 bg-yellow-50 text-yellow-700 text-xs border-b border-yellow-200">
          AI summary unavailable -- showing raw search results
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="text-gray-400 mb-4">
              <svg className="w-10 h-10 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Ask about university technologies using natural language
            </p>
            <div className="space-y-2 w-full">
              {EXAMPLE_QUERIES.map((query) => (
                <button
                  key={query}
                  onClick={() => handleSend(query)}
                  className="block w-full text-left text-xs px-3 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition-colors"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} />
            ))}
            {loading && (
              <div className="flex justify-start mb-3">
                <div className="bg-gray-100 rounded-lg px-3 py-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            {error && (
              <div className="mb-3 px-3 py-2 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
                {error}
                <button
                  onClick={() => {
                    const lastUserMsg = [...messages].reverse().find(m => m.role === 'user')
                    if (lastUserMsg) handleSend(lastUserMsg.content)
                  }}
                  className="block mt-1 text-red-600 hover:text-red-800 underline"
                >
                  Retry
                </button>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  )
}
