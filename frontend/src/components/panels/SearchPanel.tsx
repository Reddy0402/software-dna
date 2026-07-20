/**
 * Search Panel — search entities and highlight results on the graph.
 */
import { useState, useCallback } from 'react';
import { useGraphStore } from '../../store/graphStore';
import { useSearch } from '../../hooks/useGraphHooks';
import { getEntityColor } from '../../utils/colors';
import type { SearchResultItem } from '../../types/graph';
import { useReactFlow } from '@xyflow/react';

export default function SearchPanel() {
  const {
    searchQuery,
    setSearchQuery,
    setSelectedNodeId,
    setDetailPanelOpen,
  } = useGraphStore();
  const { search } = useSearch();
  const { setCenter } = useReactFlow();

  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = useCallback(
    async (value: string) => {
      setSearchQuery(value);
      if (!value.trim()) {
        setResults([]);
        return;
      }
      setIsSearching(true);
      const searchResults = await search(value);
      setResults(searchResults);
      setIsSearching(false);
    },
    [search, setSearchQuery],
  );

  const handleResultClick = useCallback(
    (item: SearchResultItem) => {
      setSelectedNodeId(item.entity.id);
      setDetailPanelOpen(true);
      setIsOpen(false);
      // Try to center the view on the selected node
      // This will be handled by the graph canvas when it detects the selectedNodeId change
    },
    [setSelectedNodeId, setDetailPanelOpen],
  );

  return (
    <div className="search-panel">
      <div className="search-panel__input-wrap">
        <span className="search-panel__icon">🔍</span>
        <input
          type="text"
          className="search-panel__input"
          placeholder="Search entities, classes, methods…"
          value={searchQuery}
          onChange={(e) => {
            handleSearch(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
        />
        {searchQuery && (
          <button
            className="search-panel__clear"
            onClick={() => {
              setSearchQuery('');
              setResults([]);
              setIsOpen(false);
            }}
          >
            ✕
          </button>
        )}
      </div>

      {isOpen && searchQuery && (
        <div className="search-panel__results glass-panel">
          {isSearching && (
            <div className="search-panel__searching">Searching…</div>
          )}
          {!isSearching && results.length === 0 && (
            <div className="search-panel__empty">No results found</div>
          )}
          {results.map((item) => {
            const colors = getEntityColor(item.entity.entity_type);
            return (
              <button
                key={item.entity.id}
                className="search-panel__result"
                onClick={() => handleResultClick(item)}
              >
                <span
                  className="search-panel__result-icon"
                  style={{ background: colors.gradient }}
                >
                  {colors.icon}
                </span>
                <div className="search-panel__result-info">
                  <div className="search-panel__result-name">
                    {item.entity.name}
                  </div>
                  <div className="search-panel__result-meta">
                    <span style={{ color: colors.primary }}>
                      {item.entity.entity_type}
                    </span>
                    {item.entity.file_path && (
                      <span className="search-panel__result-path">
                        {item.entity.file_path}
                      </span>
                    )}
                  </div>
                </div>
                <span className="search-panel__match-badge">
                  {item.match_field.replace('_', ' ')}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
