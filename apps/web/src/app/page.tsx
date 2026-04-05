import Link from "next/link";

const features = [
  { href: "/cards", icon: "🃏", title: "Browse Cards", desc: "Search and filter the full card database" },
  { href: "/identify", icon: "🔍", title: "Identify Card", desc: "Upload an image or enter card text" },
  { href: "/decks", icon: "📦", title: "Build Deck", desc: "Create, edit, and export your decks" },
  { href: "/recommend", icon: "✨", title: "Get Recommendations", desc: "AI-powered card suggestions for your deck" },
  { href: "/popular", icon: "📈", title: "Popular Decks", desc: "Browse top decklists and archetypes" },
  { href: "/meta", icon: "⚔️", title: "Meta Overview", desc: "Current meta trends and top archetypes" },
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">Yu-Gi-Oh Tools</h1>
        <p className="mt-3 text-lg text-gray-500">
          Identify cards, build decks, and stay ahead of the meta — all in one place.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            href="/identify"
            className="rounded-xl bg-blue-600 px-6 py-3 text-white font-medium hover:bg-blue-700 transition-colors"
          >
            Identify a Card
          </Link>
          <Link
            href="/cards"
            className="rounded-xl border border-gray-300 px-6 py-3 font-medium hover:bg-gray-50 transition-colors"
          >
            Browse Cards
          </Link>
        </div>
      </section>

      <section>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ href, icon, title, desc }) => (
            <Link
              key={href}
              href={href}
              className="group rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="text-3xl">{icon}</div>
              <h2 className="mt-3 text-lg font-semibold group-hover:text-blue-600">{title}</h2>
              <p className="mt-1 text-sm text-gray-500">{desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
