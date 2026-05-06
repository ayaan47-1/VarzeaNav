import { cn } from "../lib/cn";

interface LogoProps {
  size?: number;
  animated?: boolean;
  className?: string;
}

export function Logo({ size = 40, animated = false, className }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label="VárzeaNav logo — circular green disk with two river swooshes and a centered map pin"
      className={cn("shrink-0", className)}
    >
      <defs>
        <radialGradient id="vn-disk" cx="50%" cy="45%" r="60%">
          <stop offset="0%" stopColor="#CDE5C5" />
          <stop offset="70%" stopColor="#A8CFA0" />
          <stop offset="100%" stopColor="#7DB58A" />
        </radialGradient>
        <linearGradient id="vn-river-a" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1F5F3F" />
          <stop offset="100%" stopColor="#0d47a1" />
        </linearGradient>
        <linearGradient id="vn-river-b" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#0F2A1D" />
          <stop offset="100%" stopColor="#1F5F3F" />
        </linearGradient>
      </defs>

      <circle cx="50" cy="50" r="48" fill="url(#vn-disk)" />
      <circle
        cx="50"
        cy="50"
        r="48"
        fill="none"
        stroke="#1F5F3F"
        strokeOpacity="0.18"
        strokeWidth="1"
      />

      <g
        className={cn("river-swoosh", animated && "river-swoosh--anim")}
        style={{ transformOrigin: "50px 50px" }}
      >
        <path
          d="M 8 38 C 28 22, 52 60, 92 30"
          stroke="url(#vn-river-a)"
          strokeWidth="6"
          strokeLinecap="round"
          fill="none"
          opacity="0.85"
        />
        <path
          d="M 10 70 C 32 92, 60 50, 90 72"
          stroke="url(#vn-river-b)"
          strokeWidth="5"
          strokeLinecap="round"
          fill="none"
          opacity="0.7"
        />
      </g>

      <g>
        <path
          d="M 50 36 C 43 36, 38 41, 38 48 C 38 56, 50 68, 50 68 C 50 68, 62 56, 62 48 C 62 41, 57 36, 50 36 Z"
          fill="#0F2A1D"
        />
        <circle cx="50" cy="48" r="4.5" fill="#FAFBF8" />
      </g>
    </svg>
  );
}
