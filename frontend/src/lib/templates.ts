import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./http";
import type { components } from "./api";

export type Template = components["schemas"]["TemplateOut"];
export type TemplateField = components["schemas"]["TemplateFieldOut"];
export type TemplateFieldInput = components["schemas"]["TemplateFieldIn"];
export type FieldType = components["schemas"]["FieldType"];
type TemplatePage = components["schemas"]["Page_TemplateOut_"];

export const FIELD_TYPE_LABELS: Record<FieldType, string> = {
  SHORT_TEXT: "Short text",
  PARAGRAPH: "Paragraph",
  MULTIPLE_CHOICE: "Multiple choice",
  DROPDOWN: "Dropdown",
  FILE_UPLOAD: "File upload",
  DATE: "Date",
  NUMBER: "Number",
};

export const FIELD_TYPES_WITH_OPTIONS: FieldType[] = ["MULTIPLE_CHOICE", "DROPDOWN"];

export function useTemplates() {
  return useQuery<TemplatePage>({
    queryKey: ["templates"],
    queryFn: () => api.get<TemplatePage>("/templates?size=100"),
  });
}

export function useTemplate(templateId: string | undefined) {
  return useQuery<Template>({
    queryKey: ["templates", templateId],
    queryFn: () => api.get<Template>(`/templates/${templateId}`),
    enabled: !!templateId,
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { template_name: string; fields: TemplateFieldInput[] }) =>
      api.post<Template>("/templates", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["templates"] }),
  });
}

export function useReplaceTemplate(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { template_name: string; fields: TemplateFieldInput[] }) =>
      api.put<Template>(`/templates/${templateId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      queryClient.invalidateQueries({ queryKey: ["templates", templateId] });
    },
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) => api.delete<void>(`/templates/${templateId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["templates"] }),
  });
}
