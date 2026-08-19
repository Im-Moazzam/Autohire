import { useNavigate } from "react-router-dom";
import { useCurrentRecruiter, useLogout } from "../../lib/auth";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}

export function Header() {
  const { data: recruiter } = useCurrentRecruiter();
  const logout = useLogout();
  const navigate = useNavigate();

  function handleLogout() {
    logout.mutate(undefined, { onSuccess: () => navigate("/") });
  }

  return (
    <header className="flex h-[72px] shrink-0 items-center justify-end gap-4 border-b border-border bg-surface px-6">
      {recruiter && (
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-soft text-helper font-semibold text-primary">
            {initials(recruiter.name)}
          </span>
          <div className="flex flex-col">
            <span className="text-body font-medium leading-tight">{recruiter.name}</span>
            <span className="text-helper text-muted leading-tight">{recruiter.email}</span>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={logout.isPending}
            className="ml-2 text-body text-muted hover:text-ink disabled:opacity-50"
          >
            {logout.isPending ? "Signing out…" : "Sign out"}
          </button>
        </div>
      )}
    </header>
  );
}
