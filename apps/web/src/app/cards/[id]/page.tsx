"use client";

import { use } from "react";
import Image from "next/image";
import { useCard } from "@/hooks/useCards";
import { Badge } from "@/components/ui/badge";

export default function CardDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: card, isLoading, isError } = useCard(id);

  if (isLoading) return <div className="py-20 text-center text-gray-400">Loading...</div>;
  if (isError || !card) return <div className="py-20 text-center text-red-500">Card not found.</div>;

  const primaryPrint = card.prints[0];

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex flex-col gap-8 md:flex-row">
        {/* Card image */}
        <div className="shrink-0">
          {primaryPrint?.image_url ? (
            <Image
              src={primaryPrint.image_url}
              alt={card.name_en}
              width={280}
              height={400}
              className="rounded-xl shadow-lg"
            />
          ) : (
            <div className="flex h-[400px] w-[280px] items-center justify-center rounded-xl bg-gray-100 text-gray-400">
              No image
            </div>
          )}
        </div>

        {/* Card details */}
        <div className="flex-1 space-y-4">
          <div>
            <h1 className="text-3xl font-bold">{card.name_en}</h1>
            {card.name_ja && (
              <p className="mt-1 text-lg text-gray-500">{card.name_ja}</p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant={card.card_type as "monster" | "spell" | "trap"}>
              {card.card_type}
            </Badge>
            {card.monster_type && <Badge>{card.monster_type}</Badge>}
            {card.attribute && <Badge>{card.attribute.toUpperCase()}</Badge>}
            {card.race && <Badge>{card.race}</Badge>}
            {card.archetype && <Badge>{card.archetype}</Badge>}
          </div>

          {(card.level !== null || card.rank !== null || card.link_rating !== null) && (
            <div className="flex gap-4 text-sm">
              {card.level !== null && <span>Level {card.level}</span>}
              {card.rank !== null && <span>Rank {card.rank}</span>}
              {card.link_rating !== null && <span>Link {card.link_rating}</span>}
              {card.atk !== null && <span>ATK {card.atk}</span>}
              {card.def !== null && <span>DEF {card.def}</span>}
            </div>
          )}

          {(card.effect_text || card.flavor_text) && (
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-sm leading-relaxed text-gray-700">
                {card.effect_text ?? card.flavor_text}
              </p>
            </div>
          )}

          {card.pendulum_text && (
            <div className="rounded-xl border border-purple-200 bg-purple-50 p-4">
              <p className="text-xs font-medium uppercase text-purple-600">Pendulum Effect</p>
              <p className="mt-1 text-sm text-gray-700">{card.pendulum_text}</p>
            </div>
          )}

          {/* Banlist */}
          <div className="rounded-xl border border-gray-200 p-4">
            <h3 className="mb-2 text-sm font-semibold">Format Legality</h3>
            <div className="flex gap-4">
              <div>
                <span className="text-xs text-gray-500">TCG</span>
                <div className="mt-1">
                  <Badge variant={card.tcg_ban_status as "unlimited" | "limited" | "semi-limited" | "forbidden"}>
                    {card.tcg_ban_status}
                  </Badge>
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-500">OCG</span>
                <div className="mt-1">
                  <Badge variant={card.ocg_ban_status as "unlimited" | "limited" | "semi-limited" | "forbidden"}>
                    {card.ocg_ban_status}
                  </Badge>
                </div>
              </div>
            </div>
          </div>

          {/* Prints */}
          {card.prints.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">Sets</h3>
              <div className="flex flex-wrap gap-2">
                {card.prints.map((p) => (
                  <span key={p.id} className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">
                    {p.set_code ?? p.set_name ?? "Unknown set"}
                    {p.rarity ? ` · ${p.rarity}` : ""}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
