import { useState } from 'react'

interface IframeEmbedProps {
  url: string
  title: string
}

export function IframeEmbed({ url, title }: IframeEmbedProps) {
  const [showIframe, setShowIframe] = useState(false)
  const [iframeError, setIframeError] = useState(false)

  return (
    <div className="border-t border-gray-200">
      <div className="p-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-900">Original Source</h3>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline"
          >
            {url.length > 60 ? url.slice(0, 60) + '...' : url}
          </a>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowIframe(!showIframe)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              showIframe
                ? 'bg-gray-200 text-gray-700'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {showIframe ? 'Hide Preview' : 'Show Preview'}
          </button>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
          >
            Open in New Tab
          </a>
        </div>
      </div>

      {showIframe && (
        <div className="border-t border-gray-200">
          {iframeError ? (
            <div className="p-8 text-center bg-gray-50">
              <p className="text-gray-600 mb-2">
                Unable to embed this page. Some sites block iframe embedding.
              </p>
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                Open in new tab instead
              </a>
            </div>
          ) : (
            <iframe
              src={url}
              title={title}
              className="w-full h-[600px] border-0"
              onError={() => setIframeError(true)}
              sandbox="allow-scripts allow-same-origin allow-popups"
            />
          )}
        </div>
      )}
    </div>
  )
}
