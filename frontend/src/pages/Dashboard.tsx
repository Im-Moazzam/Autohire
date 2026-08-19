import { useCurrentRecruiter } from "../lib/auth";

export function Dashboard() {
  // AppShell already gates this route on a real session — recruiter is
  // guaranteed non-null here, this just reads the cached query result.
  const { data: recruiter } = useCurrentRecruiter();

  return (
    <div>
      <h1 className="text-page font-semibold">Dashboard overview</h1>
      <p className="text-body text-muted">
        Welcome back, {recruiter?.name}. Signed in as {recruiter?.email}.
      </p>
    </div>
  );
}
