"use client";

import { use, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useDeck, useAddCardsToDeck, useSaveDeckVersion } from "@/hooks/useDecks";
import { useCards } from "@/hooks/useCards";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Card } from "@/types/card";

export default function DeckDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: deck, isLoading } = useDeck(id);
  const addCards = useAddCardsToDeck(id);
  const saveVersion = useSaveDeckVersion(id);
  const [search, setSearch] = useState("");
  const [zone, setZone] = useState<"main" | "extra" | "side">("main");
  const [exportFmt, setExportFmt] = useState("json");

  const { data: searchResults } = useCards({ q: search, page_size: 12 });

  if (isLoading) return <div className="py-20 text-center text-gray-400">Loading...</div>;
  if (!deck) return <div className="py-20 text-center text-red-500">Deck not found.</div>;

  const byZone = (z: string) => deck.cards.filter((c) => c.zone === z);

  const handleAddCard = (card: Card) => {
    addCards.mutate([{ card_id: card.id, zone, quantity: 1 }]);
  };

  const handleExport = async () => {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/decks/${id}/export?format=${exportFmt}`,
      { headers: { Authorization: `Bearer ${getToken() ?? ""}` } },
    );
    const text = await res.text();
    const blob = new Blob([text], { type: exportFmt === "json" ? "application/json" : "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${deck.name}.${exportFmt === "json" ? "json" : "txt"}`;
    a.click();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">{deck.name}</h1>
          <div className="mt-1 flex gap-2">
            <Badge>{deck.format.toUpperCase()}</Badge>
            {deck.archetype && <Badge>{deck.archetype}</Badge>}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            loading={saveVersion.isPending}
            onClick={() => saveVersion.mutate(undefined)}
          >
            Save Version
          </Button>
          <select
            value={exportFmt}
            onChange={(e) => setExportFmt(e.target.value)}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
          >
            <option value="json">JSON</option>
            <option value="text">Text</option>
          </select>
          <Button size="sm" onClick={handleExport}>Export</Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Deck contents */}
        <div className="space-y-4">
          {[
            { label: `Main Deck (${deck.main_count})`, zone: "main" },
            { label: `Extra Deck (${deck.extra_count})`, zone: "extra" },
            { label: `Side Deck (${deck.side_count})`, zone: "side" },
          ].map(({ label, zone: z }) => (
            <div key={z}>
              <h3 className="mb-2 font-semibold text-sm text-gray-500 uppercase tracking-wider">{label}</h3>
              {byZone(z).length === 0 ? (
                <p className="text-sm text-gray-400">Empty</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {byZone(z).map((dc) => (
                    <span key={dc.id} className="rounded-full bg-gray-100 px-2 py-1 text-xs">
                      {dc.quantity}x {dc.card_id.slice(0, 8)}…
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Card search to add */}
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <h3 className="mb-3 font-semibold">Add Cards</h3>
          <div className="flex gap-2 mb-3">
            <Input
              placeholder="Search cards..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              value={zone}
              onChange={(e) => setZone(e.target.value as "main" | "extra" | "side")}
              className="rounded-lg border border-gray-300 px-2 py-2 text-sm"
            >
              <option value="main">Main</option>
              <option value="extra">Extra</option>
              <option value="side">Side</option>
            </select>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {searchResults?.cards.slice(0, 9).map((card) => (
              <button
                key={card.id}
                onClick={() => handleAddCard(card)}
                className="group rounded-lg border border-gray-200 p-1 text-left transition-colors hover:border-blue-400"
              >
                {card.prints[0]?.image_url_small ? (
                  <Image
                    src={card.prints[0].image_url_small}
                    alt={card.name_en}
                    width={80}
                    height={112}
                    className="w-full rounded"
                  />
                ) : (
                  <div className="flex h-[80px] items-center justify-center bg-gray-100 rounded text-xs text-gray-400">
                    No img
                  </div>
                )}
                <p className="mt-1 truncate text-xs">{card.name_en}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
