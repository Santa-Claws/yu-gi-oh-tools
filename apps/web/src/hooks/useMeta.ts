"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Card } from "@/types/card";
import type { MetaDecksResult } from "@/types/meta";

export function usePopularDecks(format: string, tier?: string, page = 1) {
  const params = new URLSearchParams({ format, page: String(page) });
  if (tier) params.set("tier", tier);
  return useQuery<MetaDecksResult>({
    queryKey: ["meta-decks", format, tier, page],
    queryFn: () => apiFetch(`/meta/popular-decks?${params}`),
  });
}

export function usePopularCards(format = "tcg", limit = 20) {
  return useQuery<Card[]>({
    queryKey: ["popular-cards", format, limit],
    queryFn: () => apiFetch(`/meta/popular-cards?format=${format}&limit=${limit}`),
  });
}
