export const SESSION_COOKIE = "dw_session";

// Fails closed: if the server has no password configured, nobody gets in.
// Constant-time comparison so response timing doesn't leak the password.
export function passwordMatches(candidate: string | undefined, expected: string | undefined): boolean {
  if (!candidate || !expected) return false;
  if (candidate.length !== expected.length) return false;
  let mismatch = 0;
  for (let i = 0; i < candidate.length; i++) {
    mismatch |= candidate.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  return mismatch === 0;
}
