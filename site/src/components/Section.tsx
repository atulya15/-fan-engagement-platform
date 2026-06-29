import { ReactNode } from "react";

export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto w-full max-w-[1400px] px-6 py-10 sm:px-10 sm:py-12">
      {children}
    </main>
  );
}

export function PageHeader({
  eyebrow,
  title,
  insight,
}: {
  eyebrow: string;
  title: string;
  insight?: string;
}) {
  return (
    <div className="mb-10">
      <p className="num text-xs font-medium uppercase tracking-[0.2em] text-accent">
        {eyebrow}
      </p>
      <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
        {title}
      </h1>
      {insight && (
        <p className="mt-4 max-w-3xl text-base leading-relaxed text-muted">
          {insight}
        </p>
      )}
    </div>
  );
}

export function Section({
  id,
  eyebrow,
  title,
  insight,
  children,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  insight?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="mb-14">
      <p className="num text-xs font-medium uppercase tracking-[0.15em] text-accent">
        {eyebrow}
      </p>
      <h2 className="mt-2 font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
        {title}
      </h2>
      {insight && (
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">
          {insight}
        </p>
      )}
      <div className="mt-5">{children}</div>
    </section>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-hairline bg-surface p-6 backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}
