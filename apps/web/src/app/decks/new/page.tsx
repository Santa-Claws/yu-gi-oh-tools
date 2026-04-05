"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateDeck } from "@/hooks/useDecks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const schema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().optional(),
  format: z.enum(["tcg", "ocg", "goat", "speed"]),
  archetype: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function NewDeckPage() {
  const router = useRouter();
  const createDeck = useCreateDeck();
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { format: "tcg" },
  });

  const onSubmit = (data: FormValues) => {
    createDeck.mutate(data as Record<string, unknown>, {
      onSuccess: (deck) => router.push(`/decks/${deck.id}`),
    });
  };

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-6 text-3xl font-bold">New Deck</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Deck Name *</label>
          <Input placeholder="My Deck" {...register("name")} />
          {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Description</label>
          <Input placeholder="Optional description" {...register("description")} />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Format</label>
          <select
            {...register("format")}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="tcg">TCG</option>
            <option value="ocg">OCG</option>
            <option value="goat">GOAT</option>
            <option value="speed">Speed Duel</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Archetype</label>
          <Input placeholder="e.g. Blue-Eyes, Tearlaments" {...register("archetype")} />
        </div>

        <Button type="submit" loading={createDeck.isPending} className="w-full">
          Create Deck
        </Button>
      </form>
    </div>
  );
}
