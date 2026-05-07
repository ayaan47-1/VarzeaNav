import { useEffect, useState } from "react";
import { Github, Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "../lib/cn";

const ANCHORS = [
  { href: "#problem", label: "Problem" },
  { href: "#how", label: "How it works" },
  { href: "#ai", label: "AI" },
  { href: "#roadmap", label: "Roadmap" },
] as const;

const GITHUB_URL = "https://github.com/";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-200 ease-out-soft",
        scrolled
          ? "bg-bg/80 backdrop-blur-md border-b border-border"
          : "bg-transparent border-b border-transparent",
      )}
    >
      <div className="max-w-page mx-auto px-6 md:px-10 h-16 flex items-center justify-between gap-6">
        <a href="#top" className="flex items-center gap-2.5 group">
          <Logo size={32} animated />
          <span className="font-display font-semibold text-fg tracking-tight">
            Várzea<span className="text-accent">Nav</span>
          </span>
        </a>

        <nav className="hidden md:flex items-center gap-7" aria-label="Primary">
          {ANCHORS.map((a) => (
            <a
              key={a.href}
              href={a.href}
              className="text-sm text-fg-muted hover:text-fg transition-colors"
            >
              {a.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub repository"
            className="hidden md:grid h-9 w-9 place-items-center rounded-full border border-border bg-surface text-fg-muted hover:text-fg hover:border-accent transition-colors"
          >
            <Github size={16} />
          </a>
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="md:hidden h-9 w-9 grid place-items-center rounded-full border border-border bg-surface text-fg-muted"
          >
            {open ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden fixed inset-0 top-16 bg-bg/98 backdrop-blur-md z-40">
          <div className="max-w-page mx-auto px-6 py-10 flex flex-col gap-2">
            {ANCHORS.map((a) => (
              <a
                key={a.href}
                href={a.href}
                onClick={() => setOpen(false)}
                className="font-display text-3xl font-semibold tracking-tight text-fg py-3 border-b border-border"
              >
                {a.label}
              </a>
            ))}
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setOpen(false)}
              className="mt-4 inline-flex items-center gap-2 text-sm text-fg-muted"
            >
              <Github size={14} /> GitHub
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
