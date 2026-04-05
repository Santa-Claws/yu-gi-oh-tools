"use client";

import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/badge";
import type { Card } from "@/types/card";

const cardTypeColors: Record<string, string> = {
  monster: "border-yellow-400",
  spell: "border-green-500",
  trap: "border-red-500",
};

interface CardTileProps {
  card: Card;
  onAddToDeck?: (card: Card) => void;
  compact?: boolean;
}

export function CardTile({ card, onAddToDeck, compact = false }: CardTileProps) {
  const primaryImage = card.prints[0]?.image_url_small ?? card.prints[0]?.image_url;

  return (
    <div
      className={cn(
        "group relative rounded-xl border-2 bg-white shadow-sm transition-shadow hover:shadow-md",
        cardTypeColors[card.card_type] ?? "border-gray-200",
      )}
    >
      <Link href={`/cards/${card.id}`} className="block">
        {primaryImage ? (
          <Image
            src={primaryImage}
            alt={card.name_en}
            width={compact ? 100 : 180}
            height={compact ? 140 : 260}
            className="w-full rounded-t-xl object-cover"
          />
        ) : (
          <div className={cn(
            "flex items-center justify-center rounded-t-xl bg-gray-100 text-gray-400",
            compact ? "h-[140px]" : "h-[260px]",
          )}>
            No image
          </div>
        )}
        <div className="p-2">
          <p className="truncate text-xs font-semibold text-gray-900">{card.name_en}</p>
          {!compact && (
            <div className="mt-1 flex flex-wrap gap-1">
              <Badge variant={card.card_type as "monster" | "spell" | "trap"}>
                {card.card_type}
              </Badge>
              {card.tcg_ban_status !== "unlimited" && (
                <Badge variant={card.tcg_ban_status as "limited" | "semi-limited" | "forbidden"}>
                  {card.tcg_ban_status}
                </Badge>
              )}
            </div>
          )}
          {!compact && card.atk !== null && (
            <p className="mt-1 text-xs text-gray-500">
              ATK/{card.atk} DEF/{card.def ?? "?"}
            </p>
          )}
        </div>
      </Link>
      {onAddToDeck && (
        <button
          onClick={() => onAddToDeck(card)}
          className="absolute right-1 top-1 hidden rounded-full bg-blue-600 p-1 text-white shadow group-hover:block"
          title="Add to deck"
        >
          <span className="text-xs font-bold">+</span>
        </button>
      )}
    </div>
  );
}
