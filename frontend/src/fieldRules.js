export const COMPANY_NAME_ERROR =
  "El nombre de la empresa solo puede incluir letras, números, espacios y los símbolos & y -.";

export const USERNAME_ERROR =
  "El usuario solo puede incluir letras y números, sin espacios ni símbolos.";

export const EMAIL_ERROR = "El correo no es válido.";

export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_MISMATCH_ERROR = "Las contraseñas no coinciden.";

export const PASSWORD_CHANGE_REQUIRED =
  "La contraseña actual y la nueva son obligatorias.";

const COMPANY_NAME_RE = /^[\p{L}\p{N} &-]+$/u;
const USERNAME_RE = /^[A-Za-z0-9]+$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidCompanyName(name) {
  return COMPANY_NAME_RE.test(name);
}

export function sanitizeUsername(value) {
  return String(value ?? "").replace(/[^A-Za-z0-9]/g, "");
}

export function isValidUsername(username) {
  return USERNAME_RE.test(username);
}

export function isValidEmail(email) {
  return EMAIL_RE.test(email);
}

export function isValidPassword(password) {
  return String(password ?? "").trim().length >= PASSWORD_MIN_LENGTH;
}
