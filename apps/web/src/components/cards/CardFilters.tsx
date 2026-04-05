"use client";

import { useForm } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface FilterValues {
  q: string;
  card_type: string;
  attribute: string;
  race: string;
  archetype: string;
  tcg_ban_status: string;
  atk_min: string;
  atk_max: string;
  level_min: string;
  level_max: string;
  sort: string;
}

interface CardFiltersProps {
  onFilter: (values: FilterValues) => void;
}

export function CardFilters({ onFilter }: CardFiltersProps) {
  const { register, handleSubmit, reset } = useForm<FilterValues>({
    defaultValues: {
      q: "", card_type: "", attribute: "", race: "", archetype: "",
      tcg_ban_status: "", atk_min: "", atk_max: "",
      level_min: "", level_max: "", sort: "relevance",
    },
  });

  return (
    <form onSubmit={handleSubmit(onFilter)} className="space-y-3">
      <Input placeholder="Search cards..." {...register("q")} />

      <select
        {...register("card_type")}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All types</option>
        <option value="monster">Monster</option>
        <option value="spell">Spell</option>
        <option value="trap">Trap</option>
      </select>

      <select
        {...register("attribute")}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All attributes</option>
        {["dark","light","earth","water","fire","wind","divine"].map(a => (
          <option key={a} value={a}>{a.toUpperCase()}</option>
        ))}
      </select>

      <select
        {...register("tcg_ban_status")}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All statuses</option>
        <option value="unlimited">Unlimited</option>
        <option value="semi-limited">Semi-Limited</option>
        <option value="limited">Limited</option>
        <option value="forbidden">Forbidden</option>
      </select>

      <select
        {...register("race")}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All races</option>
        {[
          "Aqua","Beast","Beast-Warrior","Cyberse","Dinosaur","Divine-Beast",
          "Dragon","Fairy","Fiend","Fish","Insect","Machine","Plant","Psychic",
          "Pyro","Reptile","Rock","Sea Serpent","Spellcaster","Thunder",
          "Warrior","Winged Beast","Wyrm","Zombie",
        ].map(r => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>

      <Input placeholder="Archetype (e.g. Blue-Eyes)" {...register("archetype")} />

      <div className="grid grid-cols-2 gap-2">
        <Input placeholder="ATK min" type="number" {...register("atk_min")} />
        <Input placeholder="ATK max" type="number" {...register("atk_max")} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Input placeholder="Level min" type="number" {...register("level_min")} />
        <Input placeholder="Level max" type="number" {...register("level_max")} />
      </div>

      <select
        {...register("sort")}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="relevance">Relevance</option>
        <option value="name">Name</option>
        <option value="atk">ATK</option>
        <option value="def">DEF</option>
        <option value="level">Level</option>
        <option value="popularity">Popularity</option>
      </select>

      <div className="flex gap-2">
        <Button type="submit" className="flex-1">Apply</Button>
        <Button type="button" variant="outline" onClick={() => reset()}>Reset</Button>
      </div>
    </form>
  );
}
