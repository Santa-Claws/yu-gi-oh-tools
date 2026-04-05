import { cn } from "@/lib/cn";

const variants = {
  default: "bg-gray-100 text-gray-800",
  monster: "bg-yellow-100 text-yellow-800",
  spell: "bg-green-100 text-green-800",
  trap: "bg-red-100 text-red-800",
  forbidden: "bg-red-600 text-white",
  limited: "bg-orange-500 text-white",
  "semi-limited": "bg-yellow-500 text-white",
  unlimited: "bg-gray-200 text-gray-700",
};

type BadgeVariant = keyof typeof variants;

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
