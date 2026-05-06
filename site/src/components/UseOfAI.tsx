import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export function UseOfAI() {
  return (
    <section
      id="ai"
      aria-labelledby="ai-title"
      className="py-24 md:py-32 bg-surface-elevated/40"
    >
      <div className="max-w-2xl mx-auto px-6 md:px-10">
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ staggerChildren: 0.08 }}
        >
          <motion.p
            variants={fadeUp}
            className="text-xs uppercase tracking-[0.2em] font-medium text-accent"
          >
            Use of AI
          </motion.p>
          <motion.h2
            variants={fadeUp}
            id="ai-title"
            className="mt-4 font-display font-semibold tracking-tight text-balance"
            style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)" }}
          >
            Claude is the translator, not the decoration.
          </motion.h2>
          <motion.p
            variants={fadeUp}
            className="mt-7 text-base md:text-lg leading-relaxed text-fg-muted text-pretty"
          >
            Pixel counts are scientific data. They're correct, and they're
            useless to a boat captain. VárzeaNav sends Claude (Sonnet 4.5)
            the corridor statistics for the selected month and the previous
            month, and asks for two-to-three sentences on which corridor is
            more navigable, what changed, and any caution flags. The model is
            doing the one thing models are good at — turning numbers into
            language a person can act on. Without an API key, the app falls
            back to a deterministic stub so the demo still works offline.
          </motion.p>

          <motion.div
            variants={fadeUp}
            className="mt-9 p-6 md:p-7 rounded-xl bg-surface-elevated border border-border"
          >
            <p className="font-mono text-xs uppercase tracking-widest text-accent mb-3">
              System prompt · backend/advisory.py
            </p>
            <p className="font-mono text-sm md:text-[0.95rem] text-fg leading-relaxed">
              "You are an Amazon river navigation advisor for municipal
              logistics. Write 2-3 sentences. No bullet points, no headings,
              no AI disclaimers."
            </p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
