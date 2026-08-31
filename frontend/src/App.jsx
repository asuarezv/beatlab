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
import ActivateOperator, { RecoverOperator } from "./pages/ActivateOperator.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Monitoreo from "./pages/Monitoreo.jsx";
import Operators from "./pages/Operators.jsx";
import Profile from "./pages/Profile.jsx";
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

  useEffect(() => {
    if (!session) return undefined;
    const id = setInterval(() => {
      fetchMe()
        .then((data) => {
          if (data.user) setSession(data);
        })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(id);
  }, [Boolean(session)]);

  if (session === undefined) {
    return (
      <Routes>
        <Route element={<PublicShell />}>
          <Route index element={<Landing />} />
          <Route path="invitar" element={<ActivateOperator />} />
          <Route path="recuperar" element={<RecoverOperator />} />
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
          <Route path="invitar" element={<ActivateOperator />} />
          <Route path="recuperar" element={<RecoverOperator />} />
          <Route path="login" element={<Navigate to="/entrar" replace />} />
          <Route path="perfil" element={<Navigate to="/entrar" replace />} />
          <Route path="glosario" element={<Navigate to="/entrar" replace />} />
          <Route path="*" element={<Login onLogin={setSession} />} />
        </Route>
      </Routes>
    );
  }

  const isOperator = session.role === "operator";

  return (
    <Routes>
      <Route element={<PublicShell />}>
        <Route path="invitar" element={<ActivateOperator />} />
        <Route path="recuperar" element={<RecoverOperator />} />
      </Route>
      <Route
        path="*"
        element={
          <Shell session={session} onSession={setSession}>
            <Routes>
              {isOperator ? (
                <>
                  <Route index element={<Monitoreo />} />
                  <Route path="monitoreo" element={<Monitoreo />} />
                  <Route path="glosario" element={<Glossary />} />
                  <Route
                    path="perfil"
                    element={
                      <Profile session={session} onSession={setSession} />
                    }
                  />
                  <Route path="login" element={<Navigate to="/" replace />} />
                  <Route path="entrar" element={<Navigate to="/" replace />} />
                  <Route path="registro" element={<Navigate to="/" replace />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </>
              ) : (
                <>
                  <Route index element={<Dashboard />} />
                  <Route path="consumo" element={<Consumo />} />
                  <Route path="operators" element={<Operators />} />
                  <Route path="systems" element={<Systems />} />
                  <Route path="tipos" element={<BeatTypes />} />
                  <Route path="beats" element={<Beats />} />
                  <Route path="glosario" element={<Glossary />} />
                  <Route
                    path="perfil"
                    element={
                      <Profile session={session} onSession={setSession} />
                    }
                  />
                  <Route path="login" element={<Navigate to="/" replace />} />
                  <Route path="entrar" element={<Navigate to="/" replace />} />
                  <Route path="registro" element={<Navigate to="/" replace />} />
                  <Route path="*" element={<Dashboard />} />
                </>
              )}
            </Routes>
          </Shell>
        }
      />
    </Routes>
  );
}
