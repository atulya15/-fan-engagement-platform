export function BackgroundArt() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      {/* Large soft glow orbs, fixed in viewport space so they read as
          ambient lighting rather than scrolling content. Premium dev-
          tool aesthetic (Linear/Vercel-style) instead of stock imagery,
          which would clash with a technical analytics product. */}
      <div
        className="absolute -top-40 left-1/4 h-[36rem] w-[36rem] rounded-full opacity-[0.18] blur-[120px]"
        style={{
          background:
            "radial-gradient(circle, var(--color-accent), transparent 70%)",
        }}
      />
      <div
        className="absolute top-1/3 -right-40 h-[30rem] w-[30rem] rounded-full opacity-[0.12] blur-[120px]"
        style={{
          background:
            "radial-gradient(circle, #3fb950, transparent 70%)",
        }}
      />
      <div
        className="absolute bottom-0 left-1/3 h-[28rem] w-[28rem] rounded-full opacity-[0.10] blur-[120px]"
        style={{
          background:
            "radial-gradient(circle, #818cf8, transparent 70%)",
        }}
      />

      {/* Faint grid, the "data product" texture cue. */}
      <svg className="absolute inset-0 h-full w-full opacity-[0.03]">
        <defs>
          <pattern
            id="grid"
            width="48"
            height="48"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 48 0 L 0 0 0 48"
              fill="none"
              stroke="white"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
    </div>
  );
}
