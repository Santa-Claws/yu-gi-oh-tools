"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { CardTile } from "@/components/cards/CardTile";
import { DeckViewer } from "@/components/decks/DeckViewer";
import { usePopularDecks, usePopularCards } from "@/hooks/useMeta";
import { useSaveMetaDeck } from "@/hooks/useDecks";
import { getToken } from "@/lib/auth";
import type { MetaDeck } from "@/types/meta";

const TIER_STYLES: Record<string, string> = {
  S: "bg-yellow-400 text-yellow-900",
  A: "bg-red-500 text-white",
  B: "bg-blue-500 text-white",
  C: "bg-gray-400 text-white",
};

const FORMATS = ["tcg", "ocg", "master_duel"] as const;
const TIERS = ["S", "A", "B", "C"] as const;

function exportMetaDeckAsText(deck: MetaDeck) {
  const lines = [
    `# ${deck.name}`,
    `# Format: ${deck.format}`,
    ...(deck.tier ? [`# Tier: ${deck.tier}`] : []),
    "",
    "[Main Deck]",
    ...deck.key_cards.map((c) => `1x ${c.name_en}`),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${deck.name}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

function MetaDeckCard({
  deck,
  onView,
}: {
  deck: MetaDeck;
  onView: (deck: MetaDeck) => void;
}) {
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const saveMetaDeck = useSaveMetaDeck();

  async function handleSave() {
    if (!getToken()) { alert("Please log in to save decks."); return; }
    setSaveStatus("saving");
    try {
      const cards = deck.has_full_list
        ? [
            ...deck.main_deck.map((dc, i) => ({ card_id: dc.card_id, zone: "main", quantity: dc.quantity, ordering: i })),
            ...deck.extra_deck.map((dc, i) => ({ card_id: dc.card_id, zone: "extra", quantity: dc.quantity, ordering: deck.main_deck.length + i })),
            ...deck.side_deck.map((dc, i) => ({ card_id: dc.card_id, zone: "side", quantity: dc.quantity, ordering: deck.main_deck.length + deck.extra_deck.length + i })),
          ]
        : deck.key_cards.map((c, i) => ({ card_id: c.id, zone: "main", quantity: 1, ordering: i }));
      await saveMetaDeck.mutateAsync({
        name: deck.name,
        format: deck.format,
        archetype: deck.archetype,
        cards,
      });
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 2000);
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            {deck.tier && (
              <span className={`rounded px-2 py-0.5 text-xs font-bold ${TIER_STYLES[deck.tier] ?? "bg-gray-200 text-gray-700"}`}>
                {deck.tier} Tier
              </span>
            )}
            <h3 className="font-semibold text-gray-900">{deck.name}</h3>
          </div>
          {deck.archetype && (
            <p className="mt-0.5 text-xs text-gray-500">Archetype: {deck.archetype}</p>
          )}
        </div>
        <div className="text-right text-xs text-gray-400 shrink-0">
          {deck.tournament_appearances > 0 && (
            <p>{deck.tournament_appearances} tournament{deck.tournament_appearances !== 1 ? "s" : ""}</p>
          )}
          {deck.win_rate != null && (
            <p>{(deck.win_rate * 100).toFixed(1)}% win rate</p>
          )}
        </div>
      </div>

      {deck.key_cards.length > 0 && (
        <div className="flex gap-1 overflow-x-auto pb-1">
          {deck.key_cards.map((card) => {
            const img = card.prints[0]?.image_url_small ?? card.prints[0]?.image_url;
            return (
              <Link key={card.id} href={`/cards/${card.id}`} title={card.name_en}>
                {img ? (
                  <Image
                    src={img}
                    alt={card.name_en}
                    width={48}
                    height={70}
                    className="rounded object-cover shrink-0"
                  />
                ) : (
                  <div className="w-12 h-[70px] rounded bg-gray-100 shrink-0" />
                )}
              </Link>
            );
          })}
        </div>
      )}

      {deck.source_name && (
        <div className="text-xs text-gray-400 flex items-center gap-2">
          <span>{deck.source_name}</span>
          {deck.source_url && (
            <a href={deck.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
              View source ↗
            </a>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => onView(deck)}
          className="flex-1 rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 transition-colors"
        >
          View cards
        </button>
        <button
          onClick={handleSave}
          disabled={saveStatus === "saving"}
          className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            saveStatus === "saved"
              ? "bg-green-100 text-green-700"
              : saveStatus === "error"
              ? "bg-red-100 text-red-700"
              : "bg-blue-50 text-blue-700 hover:bg-blue-100"
          }`}
        >
          {saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "Saved!" : saveStatus === "error" ? "Failed" : "Save to Decks"}
        </button>
        <button
          onClick={() => exportMetaDeckAsText(deck)}
          className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 transition-colors"
        >
          Export
        </button>
      </div>
    </div>
  );
}

export default function PopularPage() {
  const [format, setFormat] = useState<string>("tcg");
  const [tier, setTier] = useState<string | undefined>(undefined);
  const [viewingDeck, setViewingDeck] = useState<MetaDeck | null>(null);

  const { data: cardsData, isLoading: cardsLoading } = usePopularCards(format);
  const { data: decksData, isLoading: decksLoading } = usePopularDecks(format, tier);

  return (
    <div className="space-y-10">
      <h1 className="text-3xl font-bold">Popular &amp; Meta</h1>

      {/* Format tabs */}
      <div className="flex items-center gap-2">
        {FORMATS.map((f) => (
          <button
            key={f}
            onClick={() => setFormat(f)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              format === f
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f === "master_duel" ? "Master Duel" : f.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Popular Cards */}
      <section>
        <h2 className="text-2xl font-bold mb-1">Popular Cards</h2>
        <p className="text-sm text-gray-500 mb-4">Most-viewed &amp; meta-relevant</p>
        {cardsLoading ? (
          <div className="text-gray-400">Loading...</div>
        ) : !cardsData?.length ? (
          <div className="rounded-xl border-2 border-dashed border-gray-200 py-10 text-center text-gray-400">
            No card data yet. Run the scraper from Admin to populate.
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-2">
            {cardsData.map((card) => (
              <div key={card.id} className="shrink-0 w-28">
                <CardTile card={card} compact />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Meta Decks */}
      <section>
        <h2 className="text-2xl font-bold mb-1">Meta Decks</h2>
        <p className="text-sm text-gray-500 mb-4">Competitive archetypes from tier lists &amp; tournament results</p>

        {/* Tier filter */}
        <div className="flex gap-2 mb-5">
          <button
            onClick={() => setTier(undefined)}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
              tier === undefined ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            All
          </button>
          {TIERS.map((t) => (
            <button
              key={t}
              onClick={() => setTier(tier === t ? undefined : t)}
              className={`rounded-full px-3 py-1 text-xs font-bold transition-colors ${
                tier === t
                  ? (TIER_STYLES[t] ?? "bg-gray-200")
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {t} Tier
            </button>
          ))}
        </div>

        {decksLoading ? (
          <div className="text-gray-400">Loading...</div>
        ) : !decksData?.decks.length ? (
          <div className="rounded-xl border-2 border-dashed border-gray-200 py-16 text-center text-gray-400">
            <p className="text-4xl">📊</p>
            <p className="mt-2">No meta deck data yet.</p>
            <p className="text-sm mt-1">Run &quot;Scrape Meta Decks&quot; from Admin to populate.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {decksData.decks.map((deck) => (
              <MetaDeckCard key={deck.id} deck={deck} onView={setViewingDeck} />
            ))}
          </div>
        )}
      </section>

      {viewingDeck && (
        <DeckViewer
          type="meta"
          deck={viewingDeck}
          onClose={() => setViewingDeck(null)}
        />
      )}
    </div>
  );
}
