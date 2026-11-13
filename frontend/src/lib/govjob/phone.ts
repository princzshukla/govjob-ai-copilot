/** Indian mobile numbers are collected as a bare national number; the
 * country code is a fixed UI adornment, never trusted from the client. */
export const COUNTRY_CODE = "91";
export const NATIONAL_LENGTH = 10;

const S10 = /^\d{10}$/;

/** Returns the canonical stored value, `+91…`, or null when invalid/empty. */
export function toIndianMobile(value: string): string | null {
  if (!value) return null;
  const digits = value.replace(/\D/g, "");
  if (!S10.test(digits)) return null;
  return `+91${digits}`;
}

/** Splits a stored E.164 like "+919876543210" into { cc, national }. */
export function splitPhone(value: string | null | undefined): {
  countryCode: string;
  national: string;
} | null {
  if (!value) return null;
  const digits = value.replace(/\D/g, "");
  if (value.startsWith("+") && digits.length === 12 && digits.startsWith(COUNTRY_CODE)) {
    return { countryCode: COUNTRY_CODE, national: digits.slice(2) };
  }
  // Fallback: treat as raw national-length oddity, show it as-is.
  if (digits.length === NATIONAL_LENGTH && S10.test(digits)) {
    return { countryCode: COUNTRY_CODE, national: digits };
  }
  return { countryCode: COUNTRY_CODE, national: digits };
}
