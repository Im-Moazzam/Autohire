import { useQuery } from "@tanstack/react-query";
import type { components } from "./api";
import { api } from "./http";

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

export const DELIVERY_STATUS_LABELS: Record<DeliveryStatus, string> = {
  SENT: "Sent",
  FAILED: "Failed",
  PENDING: "Delivery Pending",
};

export const DELIVERY_STATUS_COLORS: Record<DeliveryStatus, string> = {
  SENT: "success",
  FAILED: "error",
  PENDING: "warning",
};

export function useEmails() {
  return useQuery<EmailPage>({
    queryKey: ["emails"],
    queryFn: () => api.get<EmailPage>("/emails?size=100"),
  });
}
