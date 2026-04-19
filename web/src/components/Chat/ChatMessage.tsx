import { Link } from 'react-router-dom'
import type { ChatMessage as ChatMessageType } from '../../api/types'

interface ChatMessageProps {
  message: ChatMessageType
}

function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Links: [text](/path) - convert to <a> tags
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline">$1</a>')
    // Numbered lists
    .replace(/^(\d+)\.\s+(.+)$/gm, '<li class="ml-4 list-decimal">$2</li>')
    // Bullet lists
    .replace(/^[-*]\s+(.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    // Paragraphs (double newlines)
    .replace(/\n\n/g, '</p><p class="mt-2">')
    // Single newlines within text
    .replace(/\n/g, '<br/>')
  return `<p>${html}</p>`
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <>
            <div
              className="prose prose-sm max-w-none [&_a]:text-blue-600 [&_a]:hover:underline"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
              onClick={(e) => {
                // Handle internal links via React Router
                const target = e.target as HTMLElement
                if (target.tagName === 'A') {
                  const href = target.getAttribute('href')
                  if (href?.startsWith('/technology/')) {
                    e.preventDefault()
                    window.location.href = href
                  }
                }
              }}
            />
            {message.technologies && message.technologies.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {message.technologies.map((tech) => (
                  <Link
                    key={tech.uuid}
                    to={`/technology/${tech.uuid}`}
                    className="block p-2 rounded bg-white border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all"
                  >
                    <div className="flex justify-between items-start gap-2">
                      <span className="font-medium text-xs text-gray-900 leading-tight">
                        {tech.title}
                      </span>
                      {tech.similarity > 0 && (
                        <span className="text-xs text-gray-400 shrink-0">
                          {Math.round(tech.similarity * 100)}%
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {tech.university}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
