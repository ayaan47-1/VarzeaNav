import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";

const DEMO_URL =
  (import.meta.env.VITE_DEMO_URL as string | undefined) ?? "http://localhost:5050";

const isLocal = (() => {
  try {
    return new URL(DEMO_URL).hostname === "localhost";
  } catch {
    return DEMO_URL.includes("localhost");
  }
})();

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

interface PlaceholderProps {
  filename: string;
  alt: string;
}

function Placeholder({ filename, alt }: PlaceholderProps) {
  return (
    <div
      role="img"
      aria-label={alt}
      className="placeholder-image relative aspect-[16/10] w-full rounded-xl border border-dashed border-border bg-surface overflow-hidden grid place-items-center"
    >
      <div className="text-center px-6">
        <p className="font-mono text-xs md:text-sm text-fg-muted">
          {filename}
        </p>
        <p className="mt-2 text-xs text-fg-muted/70 max-w-xs mx-auto">
          Drop a 16:10 PNG export from the live demo at this path.
        </p>
      </div>
    </div>
  );
}

export function Demo() {
  return (
    <section
      id="demo"
      aria-labelledby="demo-title"
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
            Live demo
          </motion.p>
          <motion.h2
            variants={fadeUp}
            id="demo-title"
            className="mt-4 font-display font-semibold tracking-tight text-balance"
            style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)" }}
          >
            Same island. Twelve months. Twelve maps.
          </motion.h2>
          <motion.p
            variants={fadeUp}
            className="mt-6 text-base md:text-lg leading-relaxed text-fg-muted text-pretty"
          >
            An island in the Amazon basin near Manaus, at{" "}
            <span className="font-mono text-fg">-3.339, -60.189</span>. Drag
            the slider; the map redraws and Claude rewrites the advisory.
          </motion.p>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="mt-14 text-center font-mono text-xs md:text-sm text-fg-muted"
        >
          Island (-3.339, -60.189) · near Manaus, Amazonas
        </motion.p>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-80px" }}
          transition={{ staggerChildren: 0.1, delayChildren: 0.05 }}
          className="mt-6 grid lg:grid-cols-2 gap-5 md:gap-6"
        >
          <motion.figure variants={fadeUp} className="space-y-3">
            <Placeholder
              filename="/public/demo-classification.png"
              alt="Classified map of the Manaus island showing permanent water in deep blue, active seasonal channels in cyan, and the two route options (a long year-round route and a shorter seasonal shortcut)."
            />
            <figcaption className="text-sm text-fg-muted leading-relaxed">
              VárzeaNav classification — green route uses a seasonal shortcut
              the red route can't see.
            </figcaption>
          </motion.figure>

          <motion.figure variants={fadeUp} className="space-y-3">
            <Placeholder
              filename="/public/demo-satellite.png"
              alt="Satellite imagery of the same Manaus island region showing surface texture but providing no information about navigability."
            />
            <figcaption className="text-sm text-fg-muted leading-relaxed">
              Satellite imagery — no information about navigability.
            </figcaption>
          </motion.figure>
        </motion.div>

        <motion.blockquote
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mt-14 mx-auto max-w-3xl p-7 md:p-9 rounded-2xl bg-surface-elevated border border-border relative"
        >
          <Sparkles
            size={18}
            className="text-accent absolute top-7 left-7"
            aria-hidden
          />
          <p className="pl-8 font-display text-lg md:text-xl text-fg leading-snug text-pretty">
            “In June, the southern corridor shows a 3× increase in active
            seasonal water versus May. The northern channel remains permanent
            and reliable. Caution: floodwater levels in this region typically
            peak late June; expect rapid current near the corridor's narrow
            entry.”
          </p>
          <footer className="pl-8 mt-5 flex items-center gap-3 text-xs">
            <span className="font-mono italic text-fg-muted">
              claude-sonnet-4-5
            </span>
            <span className="text-fg-muted/60">·</span>
            <span className="text-fg-muted">
              Generated live for each month — this is illustrative.
            </span>
          </footer>
        </motion.blockquote>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="mt-12 flex flex-col items-center gap-3"
        >
          <a
            href={DEMO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-2 px-6 h-12 rounded-full bg-accent text-white text-sm font-medium hover:bg-fg transition-colors duration-150"
          >
            Open the live demo
            <ArrowRight
              size={16}
              className="transition-transform group-hover:translate-x-0.5"
            />
          </a>
          {isLocal && (
            <p className="text-xs text-fg-muted text-center max-w-md">
              Demo runs locally. Run{" "}
              <span className="font-mono text-fg">python backend/app.py</span>{" "}
              from the repo root, then open this link.
            </p>
          )}
        </motion.div>
      </div>
    </section>
  );
}
