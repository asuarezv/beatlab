import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { fetchCsrf, fetchMe } from "./api.js";
import PublicShell from "./components/PublicShell.jsx";
import Shell from "./components/Shell.jsx";
import Beats from "./pages/Beats.jsx";
import BeatTypes from "./pages/BeatTypes.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Consumo from "./pages/Consumo.jsx";
import Glossary from "./pages/Glossary.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Operators from "./pages/Operators.jsx";
import Register from "./pages/Register.jsx";
import Systems from "./pages/Systems.jsx";

export default function App() {
  const [session, setSession] = useState(undefined);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await fetchCsrf();
        const data = await fetchMe();
        if (!cancelled) setSession(data.user ? data : null);
      } catch {
        if (!cancelled) setSession(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (session === undefined) {
    return (
      <Routes>
        <Route element={<PublicShell />}>
          <Route index element={<Landing />} />
          <Route path="*" element={<p className="muted">Cargando…</p>} />
        </Route>
      </Routes>
    );
  }

  if (!session) {
    return (
      <Routes>
        <Route element={<PublicShell />}>
          <Route index element={<Landing />} />
          <Route path="registro" element={<Register onLogin={setSession} />} />
          <Route path="entrar" element={<Login onLogin={setSession} />} />
          <Route path="login" element={<Navigate to="/entrar" replace />} />
          <Route path="glosario" element={<Navigate to="/entrar" replace />} />
          <Route path="*" element={<Login onLogin={setSession} />} />
        </Route>
      </Routes>
    );
  }

  return (
    <Shell session={session} onSession={setSession}>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="consumo" element={<Consumo />} />
        <Route path="operators" element={<Operators />} />
        <Route path="systems" element={<Systems />} />
        <Route path="tipos" element={<BeatTypes />} />
        <Route path="beats" element={<Beats />} />
        <Route path="glosario" element={<Glossary />} />
        <Route path="login" element={<Navigate to="/" replace />} />
        <Route path="entrar" element={<Navigate to="/" replace />} />
        <Route path="registro" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Dashboard />} />
      </Routes>
    </Shell>
  );
}
