"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { useMe, useLogout } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

const navLinks = [
  { href: "/cards", label: "Cards" },
  { href: "/identify", label: "Identify" },
  { href: "/decks", label: "Decks" },
  { href: "/recommend", label: "Recommend" },
  { href: "/popular", label: "Popular" },
  { href: "/meta", label: "Meta" },
];

export function Navbar() {
  const pathname = usePathname();
  const { data: user } = useMe();
  const logout = useLogout();

  return (
    <nav className="sticky top-0 z-40 border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-xl font-bold text-blue-600">
          YGO Tools
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {navLinks.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                pathname.startsWith(href)
                  ? "bg-blue-50 text-blue-600"
                  : "text-gray-600 hover:bg-gray-50",
              )}
            >
              {label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <span className="hidden text-sm text-gray-600 sm:block">
                {user.display_name ?? user.email}
              </span>
              {user.role === "admin" && (
                <Link href="/admin">
                  <Button size="sm" variant="outline">Admin</Button>
                </Link>
              )}
              <Button size="sm" variant="outline" onClick={logout}>Logout</Button>
            </>
          ) : (
            <Link href="/login">
              <Button size="sm">Login</Button>
            </Link>
          )}
        </div>
      </div>

      {/* Mobile nav */}
      <div className="flex overflow-x-auto border-t border-gray-100 px-4 py-2 md:hidden">
        {navLinks.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "mr-3 whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium",
              pathname.startsWith(href) ? "bg-blue-100 text-blue-700" : "text-gray-600",
            )}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
