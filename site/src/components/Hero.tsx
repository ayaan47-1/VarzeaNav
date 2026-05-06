import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Logo } from "./Logo";

const DEMO_URL =
  (import.meta.env.VITE_DEMO_URL as string | undefined) ?? "http://localhost:5050";

const fade = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

const stagger = {
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

export function Hero() {
  return (
    <section
      id="top"
      aria-labelledby="hero-title"
      className="relative pt-36 md:pt-44 pb-24 md:pb-32 overflow-hidden"
    >
      <div className="absolute inset-0 -z-10 pointer-events-none">
        <div
          className="absolute -top-32 -left-40 w-[40rem] h-[40rem] rounded-full opacity-40 blur-3xl"
          style={{
            background:
              "radial-gradient(closest-side, var(--accent-soft), transparent 70%)",
          }}
        />
        <div
          className="absolute top-20 right-[-10rem] w-[36rem] h-[36rem] rounded-full opacity-25 blur-3xl"
          style={{
            background:
              "radial-gradient(closest-side, var(--water-permanent), transparent 70%)",
          }}
        />
      </div>

      <div className="max-w-page mx-auto px-6 md:px-10">
        <motion.div
          initial="hidden"
          animate="show"
          variants={stagger}
          className="grid md:grid-cols-[1fr_auto] gap-10 md:gap-16 items-center"
        >
          <div className="order-2 md:order-1">
            <motion.p
              variants={fade}
              className="text-xs uppercase tracking-[0.2em] font-medium text-accent mb-6"
            >
              CBC AI Builders Hackathon · IIT · May 2026
            </motion.p>

            <motion.h1
              id="hero-title"
              variants={fade}
              className="font-display font-bold tracking-tight leading-[0.95] text-balance"
              style={{ fontSize: "clamp(3.5rem, 9vw, 7rem)" }}
            >
              <span className="text-fg">Várzea</span>
              <span className="text-accent">Nav</span>
            </motion.h1>

            <motion.p
              variants={fade}
              className="mt-5 text-xs uppercase tracking-[0.28em] font-medium text-accent-soft"
            >
              Amazon seasonal navigation
            </motion.p>

            <motion.p
              variants={fade}
              className="mt-8 max-w-xl text-base md:text-lg leading-relaxed text-fg-muted text-pretty"
            >
              Routes that change with the river. Built for the eight million
              people who depend on it.
            </motion.p>

            <motion.div
              variants={fade}
              className="mt-10 flex flex-wrap items-center gap-3"
            >
              <a
                href={DEMO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="group inline-flex items-center gap-2 px-5 h-11 rounded-full bg-accent text-white text-sm font-medium hover:bg-fg transition-colors duration-150"
              >
                See the live demo
                <ArrowRight
                  size={16}
                  className="transition-transform group-hover:translate-x-0.5"
                />
              </a>
              <a
                href="#how"
                className="inline-flex items-center gap-2 px-5 h-11 rounded-full border border-border bg-surface text-fg text-sm font-medium hover:border-accent transition-colors duration-150"
              >
                How it works
              </a>
            </motion.div>

            <motion.p
              variants={fade}
              className="mt-12 font-mono text-xs md:text-sm text-fg-muted"
            >
              <span className="text-fg">8M</span> people <span className="opacity-50">·</span>{" "}
              <span className="text-fg">6,400 km</span> of river{" "}
              <span className="opacity-50">·</span>{" "}
              <span className="text-fg">0</span> commercial maps for seasonal
              water
            </motion.p>
          </div>

          <motion.div
            variants={fade}
            className="order-1 md:order-2 flex justify-center md:justify-end"
          >
            <div className="relative">
              <div
                aria-hidden
                className="absolute inset-0 rounded-full blur-2xl opacity-50"
                style={{
                  background:
                    "radial-gradient(closest-side, var(--accent-soft), transparent 70%)",
                }}
              />
              <Logo
                size={260}
                animated
                className="relative drop-shadow-[0_24px_48px_rgba(15,42,29,0.18)]"
              />
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
