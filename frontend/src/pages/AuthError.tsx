import { Link } from "react-router-dom";
import { buttonClassName } from "../components/ui/Button";

export function AuthError() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-page font-semibold">Sign-in didn't complete</h1>
      <p className="max-w-[440px] text-body text-muted">
        Google sign-in was cancelled or ran into an error before AutoHire could
        confirm your account. No changes were made — try again when you're ready.
      </p>
      <Link to="/" className={buttonClassName({ className: "mt-2" })}>
        Back to home
      </Link>
    </div>
  );
}
