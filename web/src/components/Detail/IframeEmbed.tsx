import { useState } from 'react'

interface IframeEmbedProps {
  url: string
  title: string
}

export function IframeEmbed({ url, title }: IframeEmbedProps) {
  const [showIframe, setShowIframe] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const handleLoad = () => {
    setIsLoading(false)
  }

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
            onClick={() => {
              setShowIframe(!showIframe)
              setIsLoading(true)
            }}
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
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-800">
            Note: Many university sites block iframe embedding. If the preview is blank, use "Open in New Tab" instead.
          </div>
          <div className="relative">
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
                <div className="text-center">
                  <svg
                    className="animate-spin h-8 w-8 text-blue-600 mx-auto mb-2"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  <p className="text-sm text-gray-500">Loading preview...</p>
                </div>
              </div>
            )}
            <iframe
              src={url}
              title={title}
              className="w-full h-[600px] border-0"
              onLoad={handleLoad}
            />
          </div>
        </div>
      )}
    </div>
  )
}
