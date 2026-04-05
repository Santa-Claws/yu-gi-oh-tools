"use client";

import { CardTile } from "./CardTile";
import type { Card } from "@/types/card";

interface CardGridProps {
  cards: Card[];
  onAddToDeck?: (card: Card) => void;
}

export function CardGrid({ cards, onAddToDeck }: CardGridProps) {
  if (cards.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-gray-400">
        No cards found.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {cards.map((card) => (
        <CardTile key={card.id} card={card} onAddToDeck={onAddToDeck} />
      ))}
    </div>
  );
}
