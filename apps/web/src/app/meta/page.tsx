"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface Archetype {
  name: string;
  card_count: number;
}

export default function MetaPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["archetypes"],
    queryFn: () => apiFetch<{ archetypes: Archetype[] }>("/meta/archetypes"),
  });

  if (isLoading) return <div className="py-20 text-center text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Meta Overview</h1>
      <p className="text-gray-500">Archetypes ranked by number of cards in the database.</p>

      {!data?.archetypes.length ? (
        <div className="text-gray-400">No archetype data. Import cards first.</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.archetypes.map((a) => (
            <div
              key={a.name}
              className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm"
            >
              <span className="font-medium">{a.name}</span>
              <span className="text-sm text-gray-500">{a.card_count} cards</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
