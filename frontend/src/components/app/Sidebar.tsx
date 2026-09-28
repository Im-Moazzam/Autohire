import type { ReactNode, SVGProps } from "react";
import { NavLink } from "react-router-dom";
import { Logo } from "./Logo";
import {
  BriefcaseIcon,
  CalendarIcon,
  FileTextIcon,
  GearIcon,
  GridIcon,
  MailIcon,
} from "../ui/icons";

interface NavItem {
  label: string;
  to?: string;
  icon: (props: SVGProps<SVGSVGElement>) => ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", to: "/dashboard", icon: GridIcon },
  { label: "Templates", to: "/templates", icon: FileTextIcon },
  { label: "Jobs", to: "/jobs", icon: BriefcaseIcon },
  { label: "Scheduling", to: "/scheduling", icon: CalendarIcon },
  { label: "Emails", to: "/emails", icon: MailIcon },
  { label: "Settings", to: "/settings", icon: GearIcon },
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-[260px] shrink-0 flex-col border-r border-border bg-surface p-4">
      <div className="flex items-center gap-2 px-2 pb-4">
        <Logo className="h-6 w-6 text-primary" />
        <span className="text-card font-extrabold">AutoHire</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          if (!item.to) {
            return (
              <span
                key={item.label}
                title="Coming soon"
                className="flex items-center gap-3 rounded-md px-3 py-2 text-body text-muted/50 cursor-not-allowed"
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </span>
            );
          }
          return (
            <NavLink
              key={item.label}
              to={item.to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-md px-3 py-2 text-body font-medium transition-colors",
                  isActive
                    ? "bg-primary text-white"
                    : "text-ink hover:bg-primary-soft",
                ].join(" ")
              }
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
