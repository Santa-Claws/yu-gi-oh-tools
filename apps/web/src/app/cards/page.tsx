"use client";

import { useState } from "react";
import { useCards } from "@/hooks/useCards";
import { CardGrid } from "@/components/cards/CardGrid";
import { CardFilters } from "@/components/cards/CardFilters";
import { Button } from "@/components/ui/button";

export default function CardsPage() {
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({});
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useCards({ ...filters, page });

  return (
    <div className="flex gap-6">
      {/* Sidebar filters — sticky on desktop */}
      <aside className="hidden w-56 shrink-0 lg:block">
        <div className="sticky top-20 rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="mb-3 font-semibold">Filters</h2>
          <CardFilters
            onFilter={(vals) => {
              setFilters(vals as Record<string, string>);
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
  );
}
