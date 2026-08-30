import { useState } from "react";
import { getGlossaryEntry } from "../data/glossary.js";
import GlossaryDialog from "./GlossaryDialog.jsx";

export default function GlossaryTerm({ termId, children }) {
  const [open, setOpen] = useState(false);
  const entry = getGlossaryEntry(termId);
  const label = entry?.term ?? "término";

  return (
    <>
      <button
        type="button"
        className="glossary-term"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`Definición de ${label}`}
      >
        {children}
      </button>{open ? (
        <GlossaryDialog
          entry={entry}
          open={open}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}
