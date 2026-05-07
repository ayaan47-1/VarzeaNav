import { motion } from "framer-motion";

interface ChipDef {
  label: string;
  desc: string;
  swatch: string | null;
  faded?: boolean;
}

const chips: readonly ChipDef[] = [
  {
    label: "Permanent water",
    desc: "Year-round navigable channel. Renders.",
    swatch: "var(--water-permanent)",
  },
  {
    label: "Seasonal — active",
    desc: "Open this month. The shortcut. Renders.",
    swatch: "var(--water-active)",
  },
  {
    label: "Seasonal — inactive",
    desc: "Seasonal pixel, no water observed this month. Doesn't render — context only.",
    swatch: null,
    faded: true,
  },
  {
    label: "Rarely inundated",
    desc: "Floods only in extreme years. Renders faintly.",
    swatch: "var(--water-rare)",
  },
  {
    label: "Land",
    desc: "Never navigable. Doesn't render.",
    swatch: null,
    faded: true,
  },
] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export function HowItWorks() {
  return (
    <section
      id="how"
      aria-labelledby="how-title"
      className="py-24 md:py-32 bg-surface-elevated/40"
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
            How it works
          </motion.p>
          <motion.h2
            variants={fadeUp}
            id="how-title"
            className="mt-4 font-display font-semibold tracking-tight text-balance"
            style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)" }}
          >
            Five classes of pixel.{" "}
            <span className="text-accent">One adaptive route.</span>
          </motion.h2>
          <motion.p
            variants={fadeUp}
            className="mt-6 text-base md:text-lg leading-relaxed text-fg-muted text-pretty"
          >
            We classify every 30m pixel from the JRC Global Surface Water
            dataset (Copernicus / European Commission), then pair it with the
            monthly water history for the selected month. Three of the five
            classes render on the map — they're the ones that matter for
            routing.
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ staggerChildren: 0.06, delayChildren: 0.1 }}
          className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3 md:gap-4"
        >
          {chips.map((c) => (
            <motion.div
              key={c.label}
              variants={fadeUp}
              className={`p-5 rounded-xl border bg-surface transition-colors ${
                c.faded
                  ? "opacity-60 border-dashed border-border"
                  : "border-border hover:border-accent"
              }`}
            >
              <div className="flex items-center gap-2.5">
                {c.swatch ? (
                  <span
                    aria-hidden
                    className="inline-block h-3 w-3 rounded-full ring-1 ring-black/5"
                    style={{ backgroundColor: c.swatch }}
                  />
                ) : (
                  <span
                    aria-hidden
                    className="inline-block h-3 w-3 rounded-full border border-dashed border-fg-muted/60"
                  />
                )}
                <span className="font-display font-semibold text-fg text-sm">
                  {c.label}
                </span>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-fg-muted">
                {c.desc}
              </p>
            </motion.div>
          ))}
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="mt-12 max-w-3xl text-base md:text-lg leading-relaxed text-fg-muted text-pretty"
        >
          When the slider moves, the backend reclassifies the pixels for that
          month, recomputes corridor stats north and south of the island
          midpoint, and asks Claude for a one-sentence advisory.
        </motion.p>
      </div>
    </section>
  );
}
