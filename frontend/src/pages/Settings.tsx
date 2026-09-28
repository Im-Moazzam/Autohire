import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, Input } from "../components/ui";
import { CalendarIcon, LinkIcon, LockIcon } from "../components/ui/icons";
import { useToast } from "../components/ui/Toast";
import {
  googleReconnectUrl,
  useCurrentRecruiter,
  useLogout,
  useUpdateRecruiter,
} from "../lib/auth";
import { apiErrorMessage } from "../lib/http";

export function Settings() {
  const { data: recruiter, isLoading } = useCurrentRecruiter();
  const updateRecruiter = useUpdateRecruiter();
  const logout = useLogout();
  const { showToast } = useToast();

  const [fullName, setFullName] = useState("");
  const [nameError, setNameError] = useState<string>();

  useEffect(() => {
    if (recruiter) setFullName(recruiter.name);
  }, [recruiter]);

  function handleSave() {
    setNameError(undefined);
    if (!fullName.trim()) {
      setNameError("Name is required.");
      return;
    }
    updateRecruiter.mutate(fullName.trim(), {
      onSuccess: () => showToast("Settings saved.", "success"),
      onError: (err) => setNameError(apiErrorMessage(err, "Couldn't save.")),
    });
  }

  if (isLoading || !recruiter) {
    return <Card isLoading />;
  }

  const nameChanged = fullName.trim() !== recruiter.name;

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="text-page font-semibold">Settings</h1>
        <p className="text-body text-muted">
          Manage your account and integrations.
        </p>
      </div>

      <Card title="Account">
        <div className="flex flex-col gap-4">
          <Input
            label="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            errorText={nameError}
          />
          <div>
            <span className="text-body font-medium text-ink">Email</span>
            <p className="mt-1 text-body text-muted">{recruiter.email}</p>
          </div>
          <div className="flex items-center justify-between">
            <Button
              onClick={handleSave}
              isLoading={updateRecruiter.isPending}
              disabled={!nameChanged}
            >
              Save changes
            </Button>
            <Button
              variant="secondary"
              onClick={() => logout.mutate()}
              isLoading={logout.isPending}
            >
              Sign out
            </Button>
          </div>
        </div>
      </Card>

      <Card title="Google connection">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                recruiter.account_state === "REAUTH_REQUIRED"
                  ? "bg-warning/10 text-warning"
                  : "bg-success/10 text-success"
              }`}
              aria-hidden="true"
            >
              <LinkIcon className="h-5 w-5" />
            </span>
            <div>
              <div className="text-body font-medium text-ink">
                {recruiter.account_state === "REAUTH_REQUIRED"
                  ? "Reconnection needed"
                  : "Connected"}
              </div>
              <p className="mt-1 text-body text-muted">
                {recruiter.account_state === "REAUTH_REQUIRED"
                  ? "Google access has expired — reconnect to keep scheduling and email sending working."
                  : "Calendar, Gmail, and Drive access is active."}
              </p>
            </div>
          </div>
          {recruiter.account_state === "REAUTH_REQUIRED" && (
            <a href={googleReconnectUrl} className="shrink-0">
              <Button variant="secondary">Reconnect Google</Button>
            </a>
          )}
        </div>
      </Card>

      <Card title="Interview availability">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-soft text-primary"
              aria-hidden="true"
            >
              <CalendarIcon className="h-5 w-5" />
            </span>
            <p className="text-body text-muted">
              Set the days and hours you're available for interviews.
            </p>
          </div>
          <Link to="/scheduling" className="shrink-0">
            <Button variant="secondary">Go to Scheduling</Button>
          </Link>
        </div>
      </Card>

      <div className="flex items-center gap-2 text-helper text-muted">
        <LockIcon className="h-3.5 w-3.5" />
        Signed in with Google — AutoHire has no separate password.
      </div>
    </div>
  );
}
