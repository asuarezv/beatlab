import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import GlossaryTerm from "../components/GlossaryTerm.jsx";

function GlossaryTermGlue({ termId, children, punct }) {
  return (
    <span className="glossary-term-glue">
      <GlossaryTerm termId={termId}>{children}</GlossaryTerm>{punct}
    </span>
  );
}

const CHANNELS = ["Web", "App móvil", "API", "Job"];

const STEPS = [
  {
    title: "Tus systems envían",
    body: (
      <>
        Cada aplicación o proceso manda un{" "}
        <GlossaryTermGlue termId="beat" punct=":">
          Beat
        </GlossaryTermGlue>{" "}
        la señal de que está vivo y cómo está.
      </>
    ),
  },
  {
    title: "El mensaje viaja cifrado",
    body: (
      <>
        Todos los <GlossaryTerm termId="beat">Beats</GlossaryTerm> van cifrados
        hacia el{" "}
        <GlossaryTermGlue termId="hub" punct=".">
          Hub
        </GlossaryTermGlue>{" "}
        El envío queda protegido hasta la central.
      </>
    ),
  },
  {
    title: "El Hub recibe y valida",
    body: (
      <>
        La central reconoce cada{" "}
        <GlossaryTermGlue termId="beat" punct=",">
          Beat
        </GlossaryTermGlue>{" "}
        lo clasifica y lo deja listo para tu equipo.
      </>
    ),
  },
  {
    title: "Aviso al celular",
    body: (
      <>
        El <GlossaryTerm termId="operator">Operator</GlossaryTerm> lo recibe en{" "}
        <GlossaryTermGlue termId="monitor" punct=",">
          Monitor
        </GlossaryTermGlue>{" "}
        en su teléfono.
      </>
    ),
  },
];

export default function Landing() {
  const { hash } = useLocation();

  useEffect(() => {
    if (hash !== "#como-funciona") return;
    const section = document.getElementById("como-funciona");
    if (!section) return;
    section.focus({ preventScroll: true });
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    section.scrollIntoView({
      behavior: reduce ? "auto" : "smooth",
      block: "start",
    });
  }, [hash]);

  return (
    <main className="landing">
      <section className="landing-hero">
        <p className="eyebrow">Plataforma</p>
        <h1>
          BeatLab <GlossaryTerm termId="hub">Hub</GlossaryTerm>
        </h1>
        <p className="muted landing-lead">
          Controla la salud de tus{" "}
          <GlossaryTermGlue termId="system" punct=".">
            systems
          </GlossaryTermGlue>{" "}
          Demo de 15 días con 10.000 Beats.
        </p>
        <div className="landing-actions">
          <Link className="landing-cta" to="/registro">
            Crear mi Hub
          </Link>
          <Link className="landing-ghost" to="/entrar">
            Entrar
          </Link>
        </div>
      </section>

      <section
        id="como-funciona"
        className="landing-how"
        tabIndex={-1}
        aria-labelledby="como-funciona-title"
      >
        <p className="eyebrow">La ruta</p>
        <h2 id="como-funciona-title">¿Cómo funciona?</h2>
        <p className="muted landing-how-lead">
          Tu <GlossaryTerm termId="hub">Hub</GlossaryTerm> es la central. Recibe{" "}
          <GlossaryTerm termId="beat">Beats</GlossaryTerm> de tus{" "}
          <GlossaryTerm termId="system">systems</GlossaryTerm> —
          web, app móvil, API o un job — y los hace llegar al celular.
        </p>
        <div className="how-channels">
          {CHANNELS.map((label) => (
            <p key={label} className="how-channel">
              {label}
            </p>
          ))}
        </div>
        <ol className="how-steps">
          {STEPS.map((step, index) => (
            <li key={step.title} className="how-step">
              <span className="how-step-num" aria-hidden="true">
                {index + 1}
              </span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
