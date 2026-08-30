import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getGlossaryEntry } from "../data/glossary.js";

function GlossaryLink({ termId, children, openId, onOpen }) {
  const linked = getGlossaryEntry(termId);
  const label = linked?.term ?? "término";
  return (
    <button
      type="button"
      className="glossary-term"
      onClick={() => onOpen(termId)}
      aria-haspopup="dialog"
      aria-expanded={openId === termId}
      aria-label={`Definición de ${label}`}
    >
      {children}
    </button>
  );
}

export default function GlossaryDialog({ entry, open, onClose }) {
  const titleId = useId();
  const descId = useId();
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  const lastFocusRef = useRef(null);
  const onCloseRef = useRef(onClose);
  const nestedOpenRef = useRef(false);
  const [nestedId, setNestedId] = useState(null);
  const nestedEntry = getGlossaryEntry(nestedId);
  onCloseRef.current = onClose;
  nestedOpenRef.current = Boolean(nestedId);

  let linkIndex = 0;
  function term(termId, text) {
    return (
      <GlossaryLink
        key={`${termId}-${linkIndex++}`}
        termId={termId}
        openId={nestedId}
        onOpen={setNestedId}
      >
        {text}
      </GlossaryLink>
    );
  }

  const definition =
    typeof entry?.definition === "function"
      ? entry.definition(term)
      : entry?.definition;

  useEffect(() => {
    if (!open) setNestedId(null);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;

    lastFocusRef.current = document.activeElement;
    closeRef.current?.focus();

    function onKey(event) {
      if (nestedOpenRef.current) return;

      if (event.key === "Escape") {
        event.preventDefault();
        event.stopImmediatePropagation();
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

  return createPortal(
    <>
    <div
      className="glossary-backdrop"
      onMouseDown={(event) => {
        if (nestedId) return;
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
        <div id={descId} className="glossary-body">
          <p className="glossary-definition">{definition}</p>
          {entry.examples?.length ? (
            <>
              {entry.examplesLabel ? (
                <p className="glossary-examples-label">{entry.examplesLabel}</p>
              ) : null}
              <div className="glossary-examples">
                {entry.examples.map((item) => (
                  <p key={item}>
                    <em>{item}</em>
                  </p>
                ))}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
    <GlossaryDialog
      entry={nestedEntry}
      open={Boolean(nestedId)}
      onClose={() => setNestedId(null)}
    />
    </>,
    document.body,
  );
}
