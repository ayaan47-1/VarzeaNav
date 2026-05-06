import { Github } from "lucide-react";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

const GITHUB_URL = "https://github.com/";

export function Footer() {
  return (
    <footer className="pt-12 pb-14 border-t border-border">
      <div className="max-w-page mx-auto px-6 md:px-10">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 pb-8">
          <div className="flex items-center gap-2.5">
            <Logo size={28} />
            <span className="font-display font-semibold text-fg tracking-tight">
              Várzea<span className="text-accent">Nav</span>
            </span>
            <span className="text-fg-muted text-sm">© 2026</span>
          </div>

          <p className="text-sm text-fg-muted text-center order-3 md:order-2">
            Built for the CBC AI Builders Hackathon · IIT · May 2026
          </p>

          <div className="flex items-center gap-2 order-2 md:order-3">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="GitHub repository"
              className="h-9 w-9 grid place-items-center rounded-full border border-border bg-surface text-fg-muted hover:text-fg hover:border-accent transition-colors"
            >
              <Github size={16} />
            </a>
            <ThemeToggle />
          </div>
        </div>

        <p className="text-xs text-fg-muted leading-relaxed text-pretty max-w-3xl">
          <em>Várzea</em> — flooded forest, Portuguese (Brazil). Data: JRC
          Global Surface Water v1.4 (Copernicus / European Commission / Google
          Earth Engine). Imagery © Esri, Maxar, Earthstar Geographics.
        </p>
      </div>
    </footer>
  );
}
