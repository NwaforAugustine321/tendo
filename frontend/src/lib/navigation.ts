export type PrimarySection = "insights" | "recent" | "analytics";

export function primaryFromPathname(pathname: string): PrimarySection {
  if (pathname.startsWith("/me/insights")) return "insights";
  if (pathname.startsWith("/me/recent")) return "recent";
  if (pathname.startsWith("/me/analytics")) return "analytics";
  return "insights";
}

export function panelTitle(primary: PrimarySection): string {
  switch (primary) {
    case "insights":
      return "Insights";
    case "recent":
      return "Recent";
    case "analytics":
      return "Analytics";
  }
}
