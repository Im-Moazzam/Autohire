import { useQuery } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";
import type { Status } from "../components/ui/StatusBadge";

export type EmailLog = components["schemas"]["EmailLogOut"];
export type EmailType = components["schemas"]["EmailType"];
export type DeliveryStatus = components["schemas"]["DeliveryStatus"];
type EmailPage = components["schemas"]["Page_EmailLogOut_"];

export const EMAIL_TYPE_LABELS: Record<EmailType, string> = {
  APPLICATION_CONFIRMATION: "Application confirmation",
  INTERVIEW_INVITE: "Interview invite",
  INTERVIEW_RESCHEDULE: "Interview reschedule",
  CANCELLATION: "Cancellation",
  REJECTION: "Rejection",
  CUSTOM: "Custom",
};

export const DELIVERY_STATUS_LABELS: Record<DeliveryStatus, Status> = {
  SENT: "Sent",
  FAILED: "Failed",
  PENDING: "Delivery Pending",
};

export interface EmailListFilters {
  job_id?: string;
  candidate_id?: string;
  email_type?: EmailType;
}

export function useEmails(filters: EmailListFilters) {
  const params = new URLSearchParams({ size: "100" });
  if (filters.job_id) params.set("job_id", filters.job_id);
  if (filters.candidate_id) params.set("candidate_id", filters.candidate_id);
  if (filters.email_type) params.set("email_type", filters.email_type);

  return useQuery<EmailPage>({
    queryKey: ["emails", filters],
    queryFn: () => api.get<EmailPage>(`/emails?${params.toString()}`),
  });
}
