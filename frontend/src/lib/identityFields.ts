/** Mirrors backend/app/services/identity_fields.py's resolve_identity_fields —
 * same normalize (lowercase, strip non-alphanumeric), same "email" exclusion
 * for the name match, same first-field-wins ordering. Kept in sync via the
 * shared golden file (docs/identity-fields-cases.json, issue #23). */
function normalize(label: string): string {
  return label.toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function resolveIdentityFields(labels: string[]): {
  emailIndex: number | null;
  nameIndex: number | null;
} {
  let emailIndex: number | null = null;
  let nameIndex: number | null = null;
  labels.forEach((label, index) => {
    const norm = normalize(label);
    if (emailIndex === null && norm.includes("email")) emailIndex = index;
    if (nameIndex === null && !norm.includes("email") && norm.includes("name"))
      nameIndex = index;
  });
  return { emailIndex, nameIndex };
}

export function hasIdentityFields(labels: string[]): {
  email: boolean;
  name: boolean;
} {
  const { emailIndex, nameIndex } = resolveIdentityFields(labels);
  return { email: emailIndex !== null, name: nameIndex !== null };
}
