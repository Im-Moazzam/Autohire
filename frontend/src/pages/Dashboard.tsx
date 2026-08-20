import { Navigate } from "react-router-dom";
import { useCurrentRecruiter } from "../lib/auth";
import { Card } from "../components/ui";

export function Dashboard() {
  const { data: recruiter, isLoading, isError } = useCurrentRecruiter();

  if (isLoading) {
    return (
      <div className="p-8">
        <Card isLoading />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8">
        <Card errorText="Couldn't reach the API. Confirm the backend is running and try again." />
      </div>
    );
  }

  // useCurrentRecruiter resolves a 401 to `null` rather than throwing, since
  // "not logged in" is an expected outcome here, not a fetch failure.
  if (!recruiter) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="p-8">
      <h1 className="text-page font-semibold">Dashboard overview</h1>
      <p className="text-body text-muted">
        Welcome back, {recruiter.name}. Signed in as {recruiter.email}.
      </p>
    </div>
  );
}
