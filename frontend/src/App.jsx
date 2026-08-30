import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { fetchCsrf, fetchMe } from "./api.js";
import Shell from "./components/Shell.jsx";
import Beats from "./pages/Beats.jsx";
import BeatTypes from "./pages/BeatTypes.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import Operators from "./pages/Operators.jsx";
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
      <div className="wrap">
        <p className="muted">Cargando…</p>
      </div>
    );
  }

  if (!session) {
    return (
      <Routes>
        <Route path="*" element={<Login onLogin={setSession} />} />
      </Routes>
    );
  }

  return (
    <Shell session={session} onSession={setSession}>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="operators" element={<Operators />} />
        <Route path="systems" element={<Systems />} />
        <Route path="tipos" element={<BeatTypes />} />
        <Route path="beats" element={<Beats />} />
        <Route path="login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Dashboard />} />
      </Routes>
    </Shell>
  );
}
