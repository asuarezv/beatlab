import { useEffect, useId, useRef, useState } from "react";
import { getGlossaryEntry } from "../data/glossary.js";
import GlossaryDialog from "./GlossaryDialog.jsx";

function TermsGlossaryLink({ termId, children, openId, onOpen }) {
  const entry = getGlossaryEntry(termId);
  const label = entry?.term ?? "término";
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

export default function TermsDialog({ open, onClose }) {
  const titleId = useId();
  const descId = useId();
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  const lastFocusRef = useRef(null);
  const onCloseRef = useRef(onClose);
  const glossaryOpenRef = useRef(false);
  const [glossaryId, setGlossaryId] = useState(null);
  const glossaryEntry = getGlossaryEntry(glossaryId);
  onCloseRef.current = onClose;
  glossaryOpenRef.current = Boolean(glossaryId);

  function term(termId, text) {
    return (
      <TermsGlossaryLink
        termId={termId}
        openId={glossaryId}
        onOpen={setGlossaryId}
      >
        {text}
      </TermsGlossaryLink>
    );
  }

  useEffect(() => {
    if (!open) setGlossaryId(null);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;

    lastFocusRef.current = document.activeElement;
    closeRef.current?.focus();

    function onKey(event) {
      if (glossaryOpenRef.current) return;

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

  if (!open) return null;

  return (
    <>
      <div
        className="glossary-backdrop"
        onMouseDown={(event) => {
          if (glossaryId) return;
          if (event.target === event.currentTarget) onClose();
        }}
      >
        <div
          ref={panelRef}
          className="glossary-dialog terms-dialog"
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
          <p className="eyebrow">BeatLab</p>
          <h2 id={titleId}>Términos y condiciones</h2>
          <div id={descId} className="terms-body">
            <p>
              BeatLab es un software como servicio (SaaS). Al crear tu Hub
              obtienes un espacio aislado para tu empresa: desde ahí controlas
              la salud de tus {term("system", "Systems")}, das de alta{" "}
              {term("operator", "Operators")} y tipos de {term("beat", "Beat")},
              y recibes las señales que esos {term("system", "Systems")} envían.
            </p>
            <p>
              La alta incluye una demo de 15 días con un cupo de 10.000{" "}
              {term("beat", "Beats")}. Durante ese periodo usas un Hub
              particular, con un límite de tiempo y de mensajes. Al terminar la
              demo, el acceso y el cupo dependen de un plan comercial.
            </p>
            <p>
              El Hub está pensado para uso legítimo de tu organización:
              administrar credenciales, clasificar mensajes y observar la salud
              de tus propias aplicaciones. No es un buzón genérico ni un canal
              para datos ajenos o ilícitos.
            </p>
            <p>
              Todos los {term("beat", "Beats")} que se envían están cifrados. Un{" "}
              {term("beat", "Beat")} es la señal autenticada que emite un{" "}
              {term("system", "System")}; el cifrado protege ese envío hacia el
              Hub.
            </p>
            <p>
              Eres responsable de las cuentas de tu Hub, de las credenciales JWT
              de tus {term("system", "Systems")} y de lo que esos{" "}
              {term("system", "Systems")} publiquen. BeatLab no sustituye tus
              propios procesos de operación, seguridad o cumplimiento.
            </p>
            <p>
              Estos términos describen el servicio de forma breve. No son
              asesoría legal ni un contrato exhaustivo. Si no estás de acuerdo,
              no crees el Hub.
            </p>
          </div>
        </div>
      </div>
      <GlossaryDialog
        entry={glossaryEntry}
        open={Boolean(glossaryId)}
        onClose={() => setGlossaryId(null)}
      />
    </>
  );
}
