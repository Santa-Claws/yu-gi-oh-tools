"use client";

import { useEffect, useState } from "react";
import { CardTile } from "@/components/cards/CardTile";
import { useDeck, useSaveMetaDeck } from "@/hooks/useDecks";
import { getToken } from "@/lib/auth";
import type { Card } from "@/types/card";
import type { MetaDeck } from "@/types/meta";

const TIER_STYLES: Record<string, string> = {
  S: "bg-yellow-400 text-yellow-900",
  A: "bg-red-500 text-white",
  B: "bg-blue-500 text-white",
  C: "bg-gray-400 text-white",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DeckViewerProps =
  | { type: "user"; deckId: string; deckName: string; onClose: () => void }
  | { type: "meta"; deck: MetaDeck; onClose: () => void };

function CardZoneSection({ label, cards }: { label: string; cards: Card[] }) {
  if (!cards.length) return null;
  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        {label} <span className="text-gray-400 font-normal">({cards.length})</span>
      </h3>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
        {cards.map((card, i) => (
          <CardTile key={`${card.id}-${i}`} card={card} compact />
        ))}
      </div>
    </section>
  );
}

async function downloadUserDeck(deckId: string, deckName: string) {
  const token = getToken();
  const res = await fetch(`${API_URL}/decks/${deckId}/export?format=text`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const text = await res.text();
  triggerDownload(text, `${deckName}.txt`);
}

function exportMetaDeckAsText(deck: MetaDeck) {
  const lines = [
    `# ${deck.name}`,
    `# Format: ${deck.format}`,
    ...(deck.tier ? [`# Tier: ${deck.tier}`] : []),
    ...(deck.source_name ? [`# Source: ${deck.source_name}`] : []),
    "",
    "[Main Deck]",
    ...deck.key_cards.map((c) => `1x ${c.name_en}`),
  ];
  triggerDownload(lines.join("\n"), `${deck.name}.txt`);
}

function triggerDownload(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function UserDeckBody({ deckId }: { deckId: string }) {
  const { data: deck, isLoading } = useDeck(deckId);

  if (isLoading) {
    return <div className="flex items-center justify-center py-16 text-gray-400">Loading cards...</div>;
  }
  if (!deck) {
    return <div className="flex items-center justify-center py-16 text-gray-400">Could not load deck.</div>;
  }

  const mainCards = deck.cards
    .filter((dc) => dc.zone === "main" && dc.card)
    .flatMap((dc) => Array(dc.quantity).fill(dc.card) as Card[]);
  const extraCards = deck.cards
    .filter((dc) => dc.zone === "extra" && dc.card)
    .flatMap((dc) => Array(dc.quantity).fill(dc.card) as Card[]);
  const sideCards = deck.cards
    .filter((dc) => dc.zone === "side" && dc.card)
    .flatMap((dc) => Array(dc.quantity).fill(dc.card) as Card[]);

  if (!mainCards.length && !extraCards.length && !sideCards.length) {
    return <div className="flex items-center justify-center py-16 text-gray-400">This deck has no cards yet.</div>;
  }

  return (
    <div className="space-y-6">
      <CardZoneSection label="Main Deck" cards={mainCards} />
      <CardZoneSection label="Extra Deck" cards={extraCards} />
      <CardZoneSection label="Side Deck" cards={sideCards} />
    </div>
  );
}

export function DeckViewer(props: DeckViewerProps) {
  const { onClose } = props;
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const saveMetaDeck = useSaveMetaDeck();

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const isUser = props.type === "user";
  const name = isUser ? props.deckName : props.deck.name;
  const format = isUser ? null : props.deck.format;
  const tier = isUser ? null : props.deck.tier;

  async function handleSave() {
    if (props.type !== "meta") return;
    if (!getToken()) { alert("Please log in to save decks."); return; }
    setSaveStatus("saving");
    try {
      await saveMetaDeck.mutateAsync({
        name: props.deck.name,
        format: props.deck.format,
        archetype: props.deck.archetype,
        cardIds: props.deck.key_cards.map((c) => c.id),
      });
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 2000);
    }
  }

  async function handleExport() {
    if (props.type === "meta") {
      exportMetaDeckAsText(props.deck);
    } else {
      await downloadUserDeck(props.deckId, props.deckName);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="max-w-4xl w-full max-h-[90vh] flex flex-col bg-white rounded-2xl overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-6 py-4 border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {tier && (
              <span className={`rounded px-2 py-0.5 text-xs font-bold shrink-0 ${TIER_STYLES[tier] ?? "bg-gray-200 text-gray-700"}`}>
                {tier} Tier
              </span>
            )}
            {format && (
              <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 shrink-0">
                {format === "master_duel" ? "Master Duel" : format.toUpperCase()}
              </span>
            )}
            <h2 className="text-lg font-semibold text-gray-900 truncate">{name}</h2>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {props.type === "meta" && (
              <button
                onClick={handleSave}
                disabled={saveStatus === "saving"}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  saveStatus === "saved"
                    ? "bg-green-100 text-green-700"
                    : saveStatus === "error"
                    ? "bg-red-100 text-red-700"
                    : "bg-blue-50 text-blue-700 hover:bg-blue-100"
                }`}
              >
                {saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "Saved!" : saveStatus === "error" ? "Failed" : "Save to My Decks"}
              </button>
            )}
            <button
              onClick={handleExport}
              className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 transition-colors"
            >
              Export
            </button>
            <button
              onClick={onClose}
              className="rounded-full p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 transition-colors"
              aria-label="Close"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-6">
          {props.type === "user" ? (
            <UserDeckBody deckId={props.deckId} />
          ) : (
            props.deck.key_cards.length > 0 ? (
              <CardZoneSection label="Key Cards" cards={props.deck.key_cards} />
            ) : (
              <div className="flex items-center justify-center py-16 text-gray-400">
                No card data available for this deck.
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
