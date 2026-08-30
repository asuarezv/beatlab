import { useEffect, useId, useRef } from "react";

export default function GlossaryDialog({ entry, open, onClose }) {
  const titleId = useId();
  const descId = useId();
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  const lastFocusRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;

    lastFocusRef.current = document.activeElement;
    closeRef.current?.focus();

    function onKey(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const root = panelRef.current;
      if (!root) return;
      const nodes = [
        ...root.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ].filter((el) => !el.hasAttribute("disabled"));
      if (!nodes.length) return;

      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      lastFocusRef.current?.focus?.();
    };
  }, [open]);

  if (!open || !entry) return null;

  return (
    <div
      className="glossary-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className="glossary-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
      >
        <div className="glossary-dialog-bar" aria-hidden="true" />
        <button
          ref={closeRef}
          type="button"
          className="glossary-close"
          onClick={onClose}
          aria-label="Cerrar"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              fill="currentColor"
              d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
            />
          </svg>
        </button>
        <p className="eyebrow">Glosario</p>
        <h2 id={titleId}>{entry.term}</h2>
        {entry.fullName ? (
          <p className="muted glossary-fullname">{entry.fullName}</p>
        ) : null}
        <p id={descId} className="glossary-definition">
          {entry.definition}
        </p>
      </div>
    </div>
  );
}
