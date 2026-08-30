import { Link } from "react-router-dom";
import GlossaryTerm from "../components/GlossaryTerm.jsx";

function HeartbeatIcon() {
  return (
    <svg
      className="heartbeat"
      viewBox="0 0 24 24"
      width="28"
      height="28"
      aria-hidden="true"
    >
      <path
        fill="currentColor"
        d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
      />
    </svg>
  );
}

export default function Landing() {
  return (
    <div className="wrap center">
      <main className="landing">
        <div className="landing-brand">
          <img
            src="/brand/wordmark-on-dark.svg"
            alt="NynuSoft"
            width="180"
            height="34"
          />
          <HeartbeatIcon />
        </div>
        <p className="eyebrow">SaaS</p>
        <h1>BeatLab Hub</h1>
        <p className="muted landing-lead">
          Controla la salud de tus{" "}
          <GlossaryTerm termId="system">systems</GlossaryTerm>. Demo de 15 días
          con 10.000 Beats.
        </p>
        <div className="landing-actions">
          <Link className="landing-cta" to="/registro">
            Crear mi Hub
          </Link>
          <Link className="landing-ghost" to="/entrar">
            Entrar
          </Link>
        </div>
      </main>
    </div>
  );
}
