import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";

export default function ConfirmDialog({
  open,
  eyebrow,
  title,
  description,
  acceptLabel = "Aceptar",
  cancelLabel = "Cancelar",
  pending = false,
  onAccept,
  onCancel,
}) {
  const titleId = useId();
  const descId = useId();
  const panelRef = useRef(null);
  const cancelRef = useRef(null);
  const lastFocusRef = useRef(null);
  const onCancelRef = useRef(onCancel);
  onCancelRef.current = onCancel;

  useEffect(() => {
    if (!open) return undefined;

    lastFocusRef.current = document.activeElement;
    cancelRef.current?.focus();

    function onKey(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (!pending) onCancelRef.current?.();
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
  }, [open, pending]);

  if (!open) return null;

  return createPortal(
    <div
      className="glossary-backdrop"
      onMouseDown={(event) => {
        if (pending) return;
        if (event.target === event.currentTarget) onCancel?.();
      }}
    >
      <div
        ref={panelRef}
        className="glossary-dialog confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
      >
        <div className="glossary-dialog-bar" aria-hidden="true" />
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2 id={titleId}>{title}</h2>
        {description ? <p id={descId}>{description}</p> : null}
        <div className="confirm-actions">
          <button type="button" onClick={onAccept} disabled={pending}>
            {acceptLabel}
          </button>
          <button
            ref={cancelRef}
            type="button"
            className="secondary"
            onClick={onCancel}
            disabled={pending}
          >
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
