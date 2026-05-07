import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { Problem } from "./components/Problem";
import { HowItWorks } from "./components/HowItWorks";
import { UseOfAI } from "./components/UseOfAI";
import { Roadmap } from "./components/Roadmap";
import { Footer } from "./components/Footer";

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-fg font-sans">
      <Nav />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <UseOfAI />
        <Roadmap />
      </main>
      <Footer />
    </div>
  );
}
