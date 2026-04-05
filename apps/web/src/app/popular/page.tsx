"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface PopularDeck {
  id: string;
  title: string | null;
  url: string | null;
  scraped_at: string | null;
}

export default function PopularPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["popular-decks"],
    queryFn: () => apiFetch<{ decks: PopularDeck[]; page: number; page_size: number }>("/meta/popular-decks"),
  });

  if (isLoading) return <div className="py-20 text-center text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Popular Decks</h1>
      {!data?.decks.length ? (
        <div className="rounded-2xl border-2 border-dashed border-gray-200 py-16 text-center text-gray-400">
          <p className="text-4xl">📊</p>
          <p className="mt-2">No popular deck data yet. Run the scraper from Admin to populate.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.decks.map((deck) => (
            <a
              key={deck.id}
              href={deck.url ?? "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              <h2 className="font-semibold">{deck.title ?? "Untitled deck"}</h2>
              {deck.scraped_at && (
                <p className="mt-1 text-xs text-gray-400">
                  Scraped {new Date(deck.scraped_at).toLocaleDateString()}
                </p>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
