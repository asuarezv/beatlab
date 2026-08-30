import { useRef } from "react";

const LENGTH = 6;

function onlyDigits(value) {
  return String(value ?? "").replace(/\D/g, "");
}

export default function OtpInput({
  value,
  onChange,
  onComplete,
  disabled = false,
  invalid = false,
  id = "otp",
}) {
  const inputsRef = useRef([]);
  const digits = Array.from({ length: LENGTH }, (_, index) => value[index] ?? "");

  function focusAt(index) {
    const next = Math.max(0, Math.min(LENGTH - 1, index));
    const el = inputsRef.current[next];
    if (el) {
      el.focus();
      el.select();
    }
  }

  function applyDigits(nextDigits) {
    const next = onlyDigits(nextDigits.join("")).slice(0, LENGTH);
    onChange(next);
    if (next.length === LENGTH && next !== value) {
      onComplete?.(next);
    }
    return next;
  }

  function handleChange(index, event) {
    const raw = onlyDigits(event.target.value);
    if (!raw) {
      const next = [...digits];
      next[index] = "";
      applyDigits(next);
      return;
    }
    if (raw.length > 1) {
      const next = [...digits];
      raw.split("").forEach((digit, offset) => {
        if (index + offset < LENGTH) {
          next[index + offset] = digit;
        }
      });
      const filled = applyDigits(next);
      focusAt(Math.min(filled.length, LENGTH) - 1);
      return;
    }
    const next = [...digits];
    next[index] = raw;
    applyDigits(next);
    if (index < LENGTH - 1) {
      focusAt(index + 1);
    }
  }

  function handleKeyDown(index, event) {
    if (event.key === "Backspace") {
      event.preventDefault();
      if (digits[index]) {
        const next = [...digits];
        next[index] = "";
        applyDigits(next);
        return;
      }
      if (index > 0) {
        const next = [...digits];
        next[index - 1] = "";
        applyDigits(next);
        focusAt(index - 1);
      }
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      focusAt(index - 1);
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      focusAt(index + 1);
    }
  }

  function handlePaste(index, event) {
    const pasted = onlyDigits(event.clipboardData?.getData("text"));
    if (!pasted) {
      return;
    }
    event.preventDefault();
    const next = [...digits];
    pasted.split("").forEach((digit, offset) => {
      if (index + offset < LENGTH) {
        next[index + offset] = digit;
      }
    });
    const filled = applyDigits(next);
    focusAt(Math.min(filled.length, LENGTH) - 1);
  }

  return (
    <div
      className="otp-field"
      role="group"
      aria-label="Código de verificación de 6 dígitos"
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          id={index === 0 ? id : `${id}-${index}`}
          ref={(el) => {
            inputsRef.current[index] = el;
          }}
          className={invalid ? "otp-input invalid" : "otp-input"}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          autoFocus={index === 0}
          pattern="[0-9]*"
          maxLength={index === 0 ? LENGTH : 1}
          value={digit}
          disabled={disabled}
          aria-label={`Dígito ${index + 1} de ${LENGTH}`}
          onChange={(event) => handleChange(index, event)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          onPaste={(event) => handlePaste(index, event)}
          onFocus={(event) => event.target.select()}
        />
      ))}
    </div>
  );
}
