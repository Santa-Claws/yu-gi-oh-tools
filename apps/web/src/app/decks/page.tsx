"use client";

import { useState } from "react";
import Link from "next/link";
import { useDecks, useDeleteDeck } from "@/hooks/useDecks";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DeckViewer } from "@/components/decks/DeckViewer";

export default function DecksPage() {
  const { data: decks, isLoading } = useDecks();
  const deleteDeck = useDeleteDeck();
  const [viewingDeck, setViewingDeck] = useState<{ id: string; name: string } | null>(null);

  if (isLoading) return <div className="py-20 text-center text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">My Decks</h1>
        <Link href="/decks/new">
          <Button>New Deck</Button>
        </Link>
      </div>

      {!decks?.length && (
        <div className="rounded-2xl border-2 border-dashed border-gray-200 py-16 text-center text-gray-400">
          <p className="text-4xl">📦</p>
          <p className="mt-2">No decks yet. Create your first deck!</p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {decks?.map((deck) => (
          <div
            key={deck.id}
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div>
                <h2 className="font-semibold">{deck.name}</h2>
                {deck.description && (
                  <p className="mt-1 text-sm text-gray-500 line-clamp-2">{deck.description}</p>
                )}
              </div>
              <Badge>{deck.format.toUpperCase()}</Badge>
            </div>

            <div className="mt-3 flex gap-3 text-xs text-gray-500">
              <span>Main: {deck.main_count}</span>
              <span>Extra: {deck.extra_count}</span>
              <span>Side: {deck.side_count}</span>
            </div>

            {deck.archetype && (
              <p className="mt-2 text-xs text-gray-400">Archetype: {deck.archetype}</p>
            )}

            <div className="mt-4 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setViewingDeck({ id: deck.id, name: deck.name })}
              >
                View
              </Button>
              <Link href={`/decks/${deck.id}`} className="flex-1">
                <Button variant="outline" size="sm" className="w-full">Edit</Button>
              </Link>
              <Button
                variant="danger"
                size="sm"
                loading={deleteDeck.isPending}
                onClick={() => {
                  if (confirm("Delete this deck?")) deleteDeck.mutate(deck.id);
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        ))}
      </div>

      {viewingDeck && (
        <DeckViewer
          type="user"
          deckId={viewingDeck.id}
          deckName={viewingDeck.name}
          onClose={() => setViewingDeck(null)}
        />
      )}
    </div>
  );
}
