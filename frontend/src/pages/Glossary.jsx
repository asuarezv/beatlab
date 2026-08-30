import { useState } from "react";
import GlossaryDialog from "../components/GlossaryDialog.jsx";
import { GLOSSARY_ENTRIES, getGlossaryEntry } from "../data/glossary.js";

export default function Glossary() {
  const [openId, setOpenId] = useState(null);
  const entry = getGlossaryEntry(openId);

  return (
    <section>
      <h2>Glosario</h2>
      <p className="muted">
        Términos del dominio BeatLab. Pulsa una ficha para ver la definición.
      </p>
      <ul className="glossary-index">
        {GLOSSARY_ENTRIES.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className="glossary-entry"
              onClick={() => setOpenId(item.id)}
              aria-haspopup="dialog"
              aria-expanded={openId === item.id}
            >
              <span className="eyebrow">{item.fullName}</span>
              <strong>{item.term}</strong>
            </button>
          </li>
        ))}
      </ul>
      <GlossaryDialog
        entry={entry}
        open={Boolean(entry)}
        onClose={() => setOpenId(null)}
      />
    </section>
  );
}
