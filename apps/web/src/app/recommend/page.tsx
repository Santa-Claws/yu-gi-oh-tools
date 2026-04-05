"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { useDecks } from "@/hooks/useDecks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface Recommendation {
  card: { id: string; name_en: string; card_type: string; effect_text: string | null; prints: { image_url_small: string | null }[] };
  score: number;
  synergy_reason: string;
  role: string | null;
  meta_relevance: string | null;
  full_explanation: string | null;
}

interface RecommendResponse {
  recommendations: Recommendation[];
  meta_context: string | null;
  deck_analysis: string | null;
}

export default function RecommendPage() {
  const { data: decks } = useDecks();
  const [deckId, setDeckId] = useState("");
  const [archetype, setArchetype] = useState("");
  const [format, setFormat] = useState("tcg");
  const [explain, setExplain] = useState(false);

  const recommend = useMutation<RecommendResponse>({
    mutationFn: () =>
      apiFetch("/recommendations/cards", {
        method: "POST",
        body: { deck_id: deckId || null, archetype: archetype || null, format, explain },
        token: getToken() ?? undefined,
      }),
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-3xl font-bold">Card Recommendations</h1>

      <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium">Deck</label>
            <select
              value={deckId}
              onChange={(e) => setDeckId(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">No deck selected</option>
              {decks?.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Archetype</label>
            <Input
              placeholder="e.g. Blue-Eyes, Tearlaments"
              value={archetype}
              onChange={(e) => setArchetype(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Format</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="tcg">TCG</option>
              <option value="ocg">OCG</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={explain}
              onChange={(e) => setExplain(e.target.checked)}
              className="rounded"
            />
            Include meta context
          </label>
        </div>

        <Button
          loading={recommend.isPending}
          disabled={!deckId && !archetype}
          onClick={() => recommend.mutate()}
        >
          Get Recommendations
        </Button>
      </div>

      {recommend.data && (
        <div className="space-y-4">
          {recommend.data.deck_analysis && (
            <div className="rounded-xl bg-blue-50 p-4 text-sm text-blue-800">
              {recommend.data.deck_analysis}
            </div>
          )}

          {recommend.data.meta_context && (
            <div className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
              <strong>Meta Context:</strong> {recommend.data.meta_context}
            </div>
          )}

          {recommend.data.recommendations.map((r, i) => (
            <Link
              key={r.card.id}
              href={`/cards/${r.card.id}`}
              className="flex gap-4 rounded-xl border border-gray-200 bg-white p-4 hover:shadow-md transition-shadow"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
                {i + 1}
              </span>
              {r.card.prints[0]?.image_url_small && (
                <Image
                  src={r.card.prints[0].image_url_small}
                  alt={r.card.name_en}
                  width={50}
                  height={70}
                  className="rounded"
                />
              )}
              <div className="flex-1 space-y-1">
                <p className="font-semibold">{r.card.name_en}</p>
                <p className="text-sm text-gray-500">{r.synergy_reason}</p>
                {r.role && <Badge>{r.role}</Badge>}
              </div>
              <div className="text-right text-sm font-semibold text-green-600">
                {Math.round(r.score * 100)}%
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
