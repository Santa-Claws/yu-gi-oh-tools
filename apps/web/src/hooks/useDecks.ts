"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Deck, DeckDetail, DeckVersion } from "@/types/deck";

function authFetch<T>(path: string, opts: Parameters<typeof apiFetch>[1] = {}) {
  return apiFetch<T>(path, { ...opts, token: getToken() ?? undefined });
}

export function useDecks() {
  return useQuery<Deck[]>({
    queryKey: ["decks"],
    queryFn: () => authFetch("/decks"),
  });
}

export function useDeck(id: string) {
  return useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => authFetch(`/decks/${id}`),
    enabled: !!id,
  });
}

export function useCreateDeck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      authFetch<DeckDetail>("/decks", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["decks"] }),
  });
}

export function useUpdateDeck(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      authFetch<DeckDetail>(`/decks/${id}`, { method: "PUT", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["decks"] });
      qc.invalidateQueries({ queryKey: ["deck", id] });
    },
  });
}

export function useDeleteDeck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => authFetch(`/decks/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["decks"] }),
  });
}

export function useAddCardsToDeck(deckId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cards: unknown[]) =>
      authFetch<DeckDetail>(`/decks/${deckId}/cards`, { method: "POST", body: cards }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deck", deckId] }),
  });
}

export function useDeckVersions(deckId: string) {
  return useQuery<DeckVersion[]>({
    queryKey: ["deck-versions", deckId],
    queryFn: () => authFetch(`/decks/${deckId}/versions`),
    enabled: !!deckId,
  });
}

export function useSaveMetaDeck() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      name: string;
      format: string;
      archetype?: string | null;
      cardIds: string[];
    }) => {
      const newDeck = await authFetch<DeckDetail>("/decks", {
        method: "POST",
        body: { name: params.name, format: params.format, archetype: params.archetype },
      });
      if (params.cardIds.length > 0) {
        await authFetch<DeckDetail>(`/decks/${newDeck.id}/cards`, {
          method: "POST",
          body: params.cardIds.map((card_id, i) => ({
            card_id,
            zone: "main",
            quantity: 1,
            ordering: i,
          })),
        });
      }
      return newDeck;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["decks"] }),
  });
}

export function useSaveDeckVersion(deckId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (note?: string) =>
      authFetch<DeckVersion>(`/decks/${deckId}/versions?${note ? `note=${encodeURIComponent(note)}` : ""}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deck-versions", deckId] }),
  });
}
