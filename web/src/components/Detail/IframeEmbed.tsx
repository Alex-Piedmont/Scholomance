interface SourceLinkProps {
  url: string
}

export function SourceLink({ url }: SourceLinkProps) {
  return (
    <div className="border-t border-gray-200 p-4">
      <h3 className="text-sm font-medium text-gray-900 mb-2">Original Source</h3>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
      >
        View on University Website
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </a>
      <p className="mt-2 text-xs text-gray-500">{url}</p>
    </div>
  )
}
