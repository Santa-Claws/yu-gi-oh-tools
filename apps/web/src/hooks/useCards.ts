"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch, apiUpload } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Card, CardSearchResult, CardIdentifyResponse } from "@/types/card";

export function useCard(id: string) {
  return useQuery<Card>({
    queryKey: ["card", id],
    queryFn: () => apiFetch(`/cards/${id}`),
    enabled: !!id,
  });
}

export function useCards(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") search.set(k, String(v));
  }
  return useQuery<CardSearchResult>({
    queryKey: ["cards", params],
    queryFn: () => apiFetch(`/cards?${search}`),
  });
}

export function useIdentifyImage() {
  return useMutation<CardIdentifyResponse, Error, File>({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiUpload("/cards/identify/image", fd, getToken() ?? undefined);
    },
  });
}

export function useIdentifyText() {
  return useMutation<CardIdentifyResponse, Error, { text: string; language?: string }>({
    mutationFn: (body) =>
      apiFetch("/cards/identify/text", {
        method: "POST",
        body,
        token: getToken() ?? undefined,
      }),
  });
}
