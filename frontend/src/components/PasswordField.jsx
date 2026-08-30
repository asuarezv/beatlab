export default function PasswordField({
  label,
  name,
  value,
  onChange,
  autoComplete,
  visible,
  onToggle,
  className,
  invalid,
}) {
  const inputClass = [className, invalid ? "invalid" : null]
    .filter(Boolean)
    .join(" ") || undefined;

  return (
    <label>
      {label} <span className="req">*</span>
      <span className="password-field">
        <input
          name={name}
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          value={value}
          onChange={onChange}
          className={inputClass}
          minLength={8}
          required
        />
        <button
          type="button"
          className="password-toggle"
          onClick={onToggle}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
        >
          {visible ? (
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path
                fill="currentColor"
                d="M12 5c-7 0-10 7-10 7s3 7 10 7 10-7 10-7-3-7-10-7zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-2.5A2.5 2.5 0 1 0 12 9a2.5 2.5 0 0 0 0 5z"
              />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path
                fill="currentColor"
                d="M3.3 2.3 2 3.6l3.1 3.1C3.1 8.3 1.7 10.2 1.2 11c.4.7 3.4 7 10.8 7 2 0 3.7-.4 5.1-1.1l3.3 3.3 1.3-1.3L3.3 2.3zM12 16c-5.2 0-7.8-4.3-8.6-5.7.6-1 2-2.8 4.2-4l2.2 2.2A4 4 0 0 0 12 16zm7.4-1.6-1.5-1.5c.4-.6.7-1.2.9-1.7C17.8 9.3 15.2 5 12 5c-.6 0-1.1.1-1.6.2L8.8 3.6C9.8 3.2 10.9 3 12 3c7.4 0 10.4 6.3 10.8 7-.3.6-1.4 2.6-3.4 4.4z"
              />
            </svg>
          )}
        </button>
      </span>
    </label>
  );
}
