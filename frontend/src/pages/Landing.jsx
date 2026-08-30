import { Link } from "react-router-dom";
import GlossaryTerm from "../components/GlossaryTerm.jsx";

export default function Landing() {
  return (
    <main className="landing">
      <p className="eyebrow">Plataforma</p>
      <h1>
        BeatLab <GlossaryTerm termId="hub">Hub</GlossaryTerm>
      </h1>
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
  );
}
