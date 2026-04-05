"use client";

import { useState, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { getToken, setToken, clearToken } from "@/lib/auth";

interface UserOut {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  preferences: Record<string, unknown>;
}

export function useMe() {
  return useQuery<UserOut>({
    queryKey: ["me"],
    queryFn: () => apiFetch("/auth/me", { token: getToken() ?? undefined }),
    enabled: !!getToken(),
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { email: string; password: string }) => {
      const data = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body,
      });
      setToken(data.access_token);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { email: string; password: string; display_name?: string }) => {
      const data = await apiFetch<{ access_token: string }>("/auth/register", {
        method: "POST",
        body,
      });
      setToken(data.access_token);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useCallback(() => {
    clearToken();
    qc.clear();
  }, [qc]);
}
