export interface CardPrint {
  id: string;
  set_code: string | null;
  set_name: string | null;
  card_number: string | null;
  rarity: string | null;
  region: string | null;
  language: string;
  release_date: string | null;
  image_url: string | null;
  image_url_small: string | null;
  image_url_cropped: string | null;
}

export interface Card {
  id: string;
  ygoprodeck_id: number | null;
  name_en: string;
  name_ja: string | null;
  card_type: "monster" | "spell" | "trap";
  monster_type: string | null;
  race: string | null;
  attribute: string | null;
  level: number | null;
  rank: number | null;
  link_rating: number | null;
  link_markers: string[] | null;
  pendulum_scale: number | null;
  atk: number | null;
  def: number | null;
  effect_text: string | null;
  pendulum_text: string | null;
  flavor_text: string | null;
  archetype: string | null;
  tcg_ban_status: string;
  ocg_ban_status: string;
  is_extra_deck: boolean;
  prints: CardPrint[];
  created_at: string;
  updated_at: string;
}

export interface CardSearchResult {
  cards: Card[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface CardIdentifyResult {
  card: Card;
  confidence: number;
  match_type: string;
  match_reason: string;
}

export interface CardIdentifyResponse {
  candidates: CardIdentifyResult[];
  ocr_text: string | null;
  ocr_confidence: number | null;
  used_vision_fallback: boolean;
}
