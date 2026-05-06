import { motion } from "framer-motion";

const stats = [
  {
    n: "8M",
    label: "Amazonians outside cities. The river is their only road.",
  },
  {
    n: "~6 mo",
    label: "of every year that shortcuts are open and unmapped.",
  },
  {
    n: "0",
    label: "commercial mapping services that account for seasonal flooding.",
  },
] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export function Problem() {
  return (
    <section
      id="problem"
      aria-labelledby="problem-title"
      className="py-24 md:py-32 border-t border-border/60"
    >
      <div className="max-w-page mx-auto px-6 md:px-10">
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ staggerChildren: 0.08 }}
          className="grid md:grid-cols-2 gap-x-16 gap-y-8 md:items-end"
        >
          <motion.p
            variants={fadeUp}
            className="text-xs uppercase tracking-[0.2em] font-medium text-accent"
          >
            The problem
          </motion.p>
          <motion.div variants={fadeUp} aria-hidden className="hidden md:block" />

          <motion.h2
            variants={fadeUp}
            id="problem-title"
            className="font-display font-semibold tracking-tight text-balance"
            style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)" }}
          >
            Every minute counts.
          </motion.h2>

          <motion.p
            variants={fadeUp}
            className="text-base md:text-lg leading-relaxed text-fg-muted text-pretty"
          >
            The river is the road. School boats, ambulances, and supply runs
            all plan around the long, year-round route. Seasonal shortcuts
            open for half the year — and disappear from no commercial map.
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ staggerChildren: 0.1, delayChildren: 0.1 }}
          className="mt-16 grid md:grid-cols-3 gap-4 md:gap-5"
        >
          {stats.map((s) => (
            <motion.div
              key={s.n}
              variants={fadeUp}
              className="group p-7 md:p-8 rounded-2xl border border-border bg-surface transition-all duration-200 ease-out-soft hover:-translate-y-0.5 hover:border-accent"
            >
              <div
                className="font-display font-bold tracking-tight text-accent leading-none"
                style={{ fontSize: "clamp(2.75rem, 5vw, 4rem)" }}
              >
                {s.n}
              </div>
              <p className="mt-5 text-sm md:text-base text-fg-muted leading-relaxed">
                {s.label}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
