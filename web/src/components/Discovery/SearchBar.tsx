import { forwardRef } from 'react'
import { Icon } from '../Layout/Icon'

export type SearchMode = 'semantic' | 'keyword'

interface SearchBarProps {
  query: string
  setQuery: (q: string) => void
  mode: SearchMode
  setMode: (m: SearchMode) => void
  onSubmit?: () => void
}

export const SearchBar = forwardRef<HTMLInputElement, SearchBarProps>(function SearchBar(
  { query, setQuery, mode, setMode, onSubmit },
  ref,
) {
  return (
    <div>
      <div className="search">
        <div className="search__icon">
          <Icon name="search" size={18} />
        </div>
        <div className="search__modes">
          <button
            type="button"
            className={`search__mode-btn ${mode === 'semantic' ? 'is-active' : ''}`}
            onClick={() => setMode('semantic')}
          >
            Semantic
          </button>
          <button
            type="button"
            className={`search__mode-btn ${mode === 'keyword' ? 'is-active' : ''}`}
            onClick={() => setMode('keyword')}
          >
            Keyword
          </button>
        </div>
        <input
          ref={ref}
          className="search__input"
          placeholder={
            mode === 'semantic'
              ? 'Describe a commercial problem or an adjacent market — e.g. “low-cost wastewater destruction of forever chemicals”'
              : 'Title, description, keyword…'
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && onSubmit) onSubmit()
          }}
        />
        {query && (
          <button type="button" className="search__clear" onClick={() => setQuery('')}>
            Clear
          </button>
        )}
      </div>
      <div className="search-hint">
        {mode === 'semantic' ? (
          <>
            pgvector cosine similarity over title + description embeddings •{' '}
            <kbd>Enter</kbd> to re-rank
          </>
        ) : (
          <>
            Full-text search across title, description, keywords • <kbd>⌘K</kbd> to
            focus
          </>
        )}
      </div>
    </div>
  )
})
