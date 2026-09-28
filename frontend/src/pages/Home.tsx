import type { ReactNode, SVGProps } from "react";
import { Logo } from "../components/app/Logo";
import { buttonClassName } from "../components/ui/Button";
import {
  BarChartIcon,
  CalendarIcon,
  ChipIcon,
  FileTextIcon,
  GridIcon,
  HandshakeIcon,
  ListIcon,
  MailIcon,
} from "../components/ui/icons";
import { googleLoginUrl } from "../lib/auth";

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "How it works", href: "#how-it-works" },
];

const FEATURES: {
  icon: (props: SVGProps<SVGSVGElement>) => ReactNode;
  tone: "primary" | "cyan" | "warning" | "error";
  title: string;
  description: string;
  metric: string;
}[] = [
  {
    icon: FileTextIcon,
    tone: "primary",
    title: "Resume screening",
    description:
      "Instantly parse and evaluate thousands of CVs against your specific job criteria.",
    metric: "85% faster shortlisting",
  },
  {
    icon: BarChartIcon,
    tone: "cyan",
    title: "Candidate ranking",
    description:
      "AI scores applicants on skill match, experience, and semantic fit against the role.",
    metric: "Explainable, evidence-backed scores",
  },
  {
    icon: CalendarIcon,
    tone: "warning",
    title: "Interview scheduling",
    description:
      "Automated calendar syncing and self-scheduling links for candidates.",
    metric: "Zero back-and-forth",
  },
  {
    icon: MailIcon,
    tone: "error",
    title: "Gmail automation",
    description:
      "Draft and send personalized outreach, follow-ups, and rejection emails automatically.",
    metric: "Seamless integration",
  },
];

const STEPS: {
  icon: (props: SVGProps<SVGSVGElement>) => ReactNode;
  title: string;
  description: string;
}[] = [
  {
    icon: GridIcon,
    title: "Connect sources",
    description:
      "Launch a job and generate a Drive folder and apply link in one step.",
  },
  {
    icon: ChipIcon,
    title: "AI processing",
    description:
      "Resumes are parsed, embedded, and standardized automatically.",
  },
  {
    icon: ListIcon,
    title: "Review shortlist",
    description:
      "See a ranked dashboard of the top candidates, ready for human review.",
  },
  {
    icon: HandshakeIcon,
    title: "Engage & hire",
    description:
      "Trigger interview invitations and move straight to conversations.",
  },
];

const toneClasses: Record<string, string> = {
  primary: "bg-primary/10 text-primary",
  cyan: "bg-cyan/10 text-cyan",
  warning: "bg-warning/10 text-warning",
  error: "bg-error/10 text-error",
};

function HeroIllustration() {
  const nodes = [
    { x: 60, y: 40 },
    { x: 220, y: 30 },
    { x: 40, y: 160 },
    { x: 230, y: 170 },
    { x: 140, y: 200 },
  ];
  return (
    <svg
      viewBox="0 0 280 220"
      className="h-full w-full max-w-[420px]"
      aria-hidden="true"
    >
      <g stroke="var(--color-primary)" strokeOpacity="0.35" strokeWidth={1.5}>
        {nodes.map((n) => (
          <line key={`${n.x}-${n.y}`} x1={140} y1={110} x2={n.x} y2={n.y} />
        ))}
      </g>
      <circle
        cx={140}
        cy={110}
        r={26}
        fill="var(--color-primary)"
        fillOpacity="0.15"
        stroke="var(--color-primary)"
        strokeWidth={2}
      />
      <circle cx={140} cy={110} r={9} fill="var(--color-primary)" />
      {nodes.map((n) => (
        <g key={`${n.x}-${n.y}-node`}>
          <circle
            cx={n.x}
            cy={n.y}
            r={14}
            fill="var(--color-surface)"
            stroke="var(--color-cyan)"
            strokeWidth={2}
          />
          <circle cx={n.x} cy={n.y} r={5} fill="var(--color-cyan)" />
        </g>
      ))}
    </svg>
  );
}

function AvatarStack() {
  const initials = ["JM", "AK", "RS"];
  return (
    <div className="flex -space-x-3">
      {initials.map((label) => (
        <span
          key={label}
          className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-surface bg-primary-soft text-[11px] font-semibold text-primary"
        >
          {label}
        </span>
      ))}
    </div>
  );
}

export function Home() {
  return (
    <div className="min-h-screen bg-surface text-ink">
      <header className="sticky top-0 z-10 border-b border-border/60 bg-surface/80 backdrop-blur">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between px-6 py-4 sm:px-10">
          <div className="flex items-center gap-2">
            <Logo className="h-6 w-6 text-primary" />
            <span className="text-card font-extrabold">AutoHire</span>
          </div>
          <nav
            className="hidden items-center gap-8 md:flex"
            aria-label="Primary"
          >
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-body font-medium text-muted transition-colors hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-4">
            <a
              href={googleLoginUrl}
              className="text-body font-medium text-muted transition-colors hover:text-ink"
            >
              Login
            </a>
            <a
              href={googleLoginUrl}
              className={buttonClassName({ className: "px-6 py-2 text-body" })}
            >
              Sign up
            </a>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-[1280px] gap-12 px-6 py-16 sm:px-10 md:grid-cols-2 md:items-center md:py-24">
          <div className="flex flex-col items-start gap-6">
            <span className="inline-flex items-center gap-2 rounded-xl bg-primary-soft px-3 py-1 text-helper font-medium tracking-wide text-ink">
              AI-powered recruitment solutions
            </span>
            <h1 className="text-display font-extrabold leading-tight">
              Intelligent talent
              <br />
              <span className="bg-gradient-to-r from-primary to-cyan bg-clip-text text-transparent">
                acquisition
              </span>
            </h1>
            <p className="max-w-[480px] text-body text-muted">
              Automate resume screening, rank top candidates instantly, and
              schedule interviews seamlessly. Let AI handle the busywork so you
              can focus on building great teams.
            </p>
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <a
                href={googleLoginUrl}
                className={buttonClassName({
                  className: "px-8 py-3 text-body",
                })}
              >
                Get started
              </a>
              <a
                href="#how-it-works"
                className={buttonClassName({
                  variant: "secondary",
                  className: "px-8 py-3 text-body",
                })}
              >
                Watch demo
              </a>
            </div>
            <div className="flex items-center gap-3 pt-4">
              <AvatarStack />
              <span className="text-helper text-muted">
                Trusted by 500+ modern recruiting teams
              </span>
            </div>
          </div>
          <div className="flex items-center justify-center">
            <HeroIllustration />
          </div>
        </section>

        <section
          id="features"
          className="mx-auto max-w-[1280px] px-6 py-16 sm:px-10"
        >
          <div className="mx-auto max-w-[672px] text-center">
            <h2 className="text-section font-semibold">
              Streamline every stage of hiring
            </h2>
            <p className="mt-3 text-body text-muted">
              Our integrated suite of AI tools replaces manual data entry and
              guesswork with precision and speed.
            </p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="flex flex-col justify-between rounded-md border border-border bg-canvas p-5 shadow-card"
                >
                  <div>
                    <span
                      className={[
                        "flex h-10 w-10 items-center justify-center rounded-sm",
                        toneClasses[feature.tone],
                      ].join(" ")}
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                    <h3 className="mt-4 text-card font-medium">
                      {feature.title}
                    </h3>
                    <p className="mt-2 text-table text-muted">
                      {feature.description}
                    </p>
                  </div>
                  <p className="mt-6 border-t border-border/60 pt-4 text-helper font-medium text-muted">
                    {feature.metric}
                  </p>
                </div>
              );
            })}
          </div>
        </section>

        <section id="how-it-works" className="bg-canvas py-16">
          <div className="mx-auto max-w-[1280px] px-6 sm:px-10">
            <div className="mx-auto max-w-[672px] text-center">
              <h2 className="text-section font-semibold">How AutoHire works</h2>
              <p className="mt-3 text-body text-muted">
                A seamless workflow from job posting to offer letter.
              </p>
            </div>
            <div className="relative mt-16 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
              <div
                className="absolute top-12 hidden h-px bg-border lg:block"
                style={{ left: "12%", right: "12%" }}
                aria-hidden="true"
              />
              {STEPS.map((step, index) => {
                const Icon = step.icon;
                return (
                  <div
                    key={step.title}
                    className="relative flex flex-col items-center text-center"
                  >
                    <span className="flex h-24 w-24 items-center justify-center rounded-full border-4 border-canvas bg-surface shadow-card">
                      <Icon className="h-7 w-7 text-primary" />
                    </span>
                    <span className="mt-4 text-helper font-semibold uppercase tracking-wide text-primary">
                      Step {index + 1}
                    </span>
                    <h3 className="mt-1 text-body font-medium">{step.title}</h3>
                    <p className="mt-2 max-w-[220px] text-table text-muted">
                      {step.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-canvas">
        <div className="mx-auto flex max-w-[1280px] flex-col gap-8 px-6 py-12 sm:flex-row sm:items-start sm:justify-between sm:px-10">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Logo className="h-6 w-6 text-primary" />
              <span className="text-card font-extrabold">AutoHire</span>
            </div>
            <p className="max-w-[320px] text-body text-ink/80">
              Making hiring intelligent, efficient, and bias-free.
            </p>
            <p className="text-helper text-muted">
              © 2026 AutoHire. All rights reserved.
            </p>
          </div>
          <nav className="flex gap-6" aria-label="Footer">
            <a
              href="#"
              className="text-body text-muted transition-colors hover:text-ink"
            >
              Resources
            </a>
            <a
              href="#"
              className="text-body text-muted transition-colors hover:text-ink"
            >
              Privacy policy
            </a>
            <a
              href="#"
              className="text-body text-muted transition-colors hover:text-ink"
            >
              Terms of service
            </a>
            <a
              href="#"
              className="text-body text-muted transition-colors hover:text-ink"
            >
              Contact
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
