"use client";

import { useState, useRef } from "react";
import { useCards, useSemanticSearch } from "@/hooks/useCards";
import { CardGrid } from "@/components/cards/CardGrid";
import { CardFilters } from "@/components/cards/CardFilters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SemanticSearchResult } from "@/types/card";

type Mode = "filter" | "ai";

export default function CardsPage() {
  const [mode, setMode] = useState<Mode>("filter");

  // Filter mode state
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({});
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useCards({ ...filters, page });

  // AI search state
  const [aiQuery, setAiQuery] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const aiSearch = useSemanticSearch();
  const inputRef = useRef<HTMLInputElement>(null);

  function handleAiSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!aiQuery.trim()) return;
    setSubmitted(true);
    aiSearch.mutate({ query: aiQuery.trim(), limit: 30 });
  }

  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setMode("filter")}
          className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
            mode === "filter"
              ? "bg-gray-900 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Filters
        </button>
        <button
          onClick={() => { setMode("ai"); setTimeout(() => inputRef.current?.focus(), 50); }}
          className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
            mode === "ai"
              ? "bg-indigo-600 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          ✦ AI Search
        </button>
      </div>

      {mode === "filter" && (
        <div className="flex gap-6">
          <aside className="hidden w-56 shrink-0 lg:block">
            <div className="sticky top-20 rounded-xl border border-gray-200 bg-white p-4">
              <h2 className="mb-3 font-semibold">Filters</h2>
              <CardFilters
                onFilter={(vals) => {
                  setFilters(vals as unknown as Record<string, string | number | undefined>);
                  setPage(1);
                }}
              />
            </div>
          </aside>

          <div className="flex-1 space-y-4">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">Cards</h1>
              {data && (
                <span className="text-sm text-gray-500">{data.total.toLocaleString()} results</span>
              )}
            </div>

            {isLoading && (
              <div className="flex h-48 items-center justify-center text-gray-400">Loading...</div>
            )}
            {isError && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
                Failed to load cards.
              </div>
            )}
            {data && <CardGrid cards={data.cards} />}

            {data && data.pages > 1 && (
              <div className="flex items-center justify-center gap-3 pt-4">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                  Previous
                </Button>
                <span className="text-sm text-gray-600">Page {page} of {data.pages}</span>
                <Button variant="outline" size="sm" disabled={page >= data.pages} onClick={() => setPage(p => p + 1)}>
                  Next
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {mode === "ai" && (
        <div className="space-y-6">
          <form onSubmit={handleAiSubmit} className="flex gap-2">
            <Input
              ref={inputRef}
              value={aiQuery}
              onChange={e => setAiQuery(e.target.value)}
              placeholder='Try "zombie field spell", "cards that negate effects", "dragon fusion monsters"…'
              className="flex-1"
            />
            <Button type="submit" disabled={aiSearch.isPending || !aiQuery.trim()}>
              {aiSearch.isPending ? "Searching…" : "Search"}
            </Button>
          </form>

          {aiSearch.isPending && (
            <div className="flex h-48 items-center justify-center text-gray-400">
              Thinking…
            </div>
          )}

          {aiSearch.isError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
              Search failed. Make sure embeddings have been generated (run index/embed from admin panel).
            </div>
          )}

          {submitted && aiSearch.data && aiSearch.data.length === 0 && (
            <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 text-yellow-800">
              No results found. Embeddings may still be generating — check the admin panel.
            </div>
          )}

          {aiSearch.data && aiSearch.data.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">
                {aiSearch.data.length} results for &ldquo;{aiQuery}&rdquo;
              </p>
              <AiResultGrid results={aiSearch.data} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AiResultGrid({ results }: { results: SemanticSearchResult[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {results.map(({ card, similarity }) => {
        const img = card.prints[0]?.image_url_small ?? card.prints[0]?.image_url;
        const pct = Math.round(similarity * 100);
        return (
          <a key={card.id} href={`/cards/${card.id}`} className="group relative block overflow-hidden rounded-lg border border-gray-200 bg-white transition hover:shadow-md">
            {img ? (
              <img src={img} alt={card.name_en} className="aspect-[421/614] w-full object-cover" />
            ) : (
              <div className="flex aspect-[421/614] items-center justify-center bg-gray-100 text-xs text-gray-400 p-2 text-center">
                {card.name_en}
              </div>
            )}
            <div className="p-2">
              <p className="truncate text-xs font-medium">{card.name_en}</p>
              <p className="text-xs text-gray-400">{pct}% match</p>
            </div>
          </a>
        );
      })}
    </div>
  );
}
