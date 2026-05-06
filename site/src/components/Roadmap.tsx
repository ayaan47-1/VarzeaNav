import { motion } from "framer-motion";
import { ArrowRight, CircleDot } from "lucide-react";

const today = [
  "Historical 2021 monthly data from JRC Global Surface Water v1.4 — not real-time.",
  "Surface water presence only — no depth or bathymetry.",
  "Climatological average; drought years are masked.",
  "Sufficient for small craft and launches; deeper vessels would need bathymetric integration.",
  "Static advisory panel for route output.",
] as const;

const future = [
  "Live ANA (Agência Nacional de Águas) hydrology feed in place of historical tiles.",
  "Bathymetric layer for deeper-draft vessels.",
  "Per-vessel draft input, so the route adapts to the boat.",
  "Full Google Maps–style UX: dynamic scrolling, tap-to-route, turn-by-turn.",
  "Offline tiles for low-connectivity stretches.",
] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export function Roadmap() {
  return (
    <section
      id="roadmap"
      aria-labelledby="roadmap-title"
      className="py-24 md:py-32 border-t border-border/60"
    >
      <div className="max-w-page mx-auto px-6 md:px-10">
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ staggerChildren: 0.08 }}
          className="max-w-3xl"
        >
          <motion.p
            variants={fadeUp}
            className="text-xs uppercase tracking-[0.2em] font-medium text-accent"
          >
            Limitations & next steps
          </motion.p>
          <motion.h2
            variants={fadeUp}
            id="roadmap-title"
            className="mt-4 font-display font-semibold tracking-tight text-balance"
            style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)" }}
          >
            What this is, and what it isn't.
          </motion.h2>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ staggerChildren: 0.1, delayChildren: 0.05 }}
          className="mt-14 grid md:grid-cols-2 gap-6 md:gap-8"
        >
          <motion.div
            variants={fadeUp}
            className="p-7 md:p-8 rounded-2xl border border-border bg-surface"
          >
            <p className="text-xs uppercase tracking-[0.2em] font-medium text-fg-muted">
              Today (hackathon prototype)
            </p>
            <ul className="mt-6 space-y-4">
              {today.map((t) => (
                <li key={t} className="flex items-start gap-3 text-sm md:text-base text-fg-muted leading-relaxed">
                  <CircleDot size={16} className="mt-1 text-fg-muted shrink-0" aria-hidden />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            variants={fadeUp}
            className="p-7 md:p-8 rounded-2xl border border-accent/40 bg-surface-elevated"
          >
            <p className="text-xs uppercase tracking-[0.2em] font-medium text-accent">
              Production
            </p>
            <ul className="mt-6 space-y-4">
              {future.map((t) => (
                <li key={t} className="flex items-start gap-3 text-sm md:text-base text-fg leading-relaxed">
                  <ArrowRight size={16} className="mt-1 text-accent shrink-0" aria-hidden />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
