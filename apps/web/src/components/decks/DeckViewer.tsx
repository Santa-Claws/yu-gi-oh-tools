"use client";

import { useEffect } from "react";
import { CardTile } from "@/components/cards/CardTile";
import { useDeck } from "@/hooks/useDecks";
import type { Card } from "@/types/card";
import type { MetaDeck } from "@/types/meta";

const TIER_STYLES: Record<string, string> = {
  S: "bg-yellow-400 text-yellow-900",
  A: "bg-red-500 text-white",
  B: "bg-blue-500 text-white",
  C: "bg-gray-400 text-white",
};

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
        {cards.map((card) => (
          <CardTile key={card.id} card={card} compact />
        ))}
      </div>
    </section>
  );
}

function UserDeckBody({ deckId }: { deckId: string }) {
  const { data: deck, isLoading } = useDeck(deckId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        Loading cards...
      </div>
    );
  }

  if (!deck) {
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        Could not load deck.
      </div>
    );
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
    return (
      <div className="flex items-center justify-center py-16 text-gray-400">
        This deck has no cards yet.
      </div>
    );
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
          <button
            onClick={onClose}
            className="shrink-0 rounded-full p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            aria-label="Close"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
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
