import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import MetricsPage from "./pages/MetricsPage";
import DagPage from "./pages/DagPage";

// Add a page: create it in src/pages and add one entry here.
const PAGES = [
  { path: "/metrics", label: "Metrics", element: <MetricsPage /> },
  { path: "/dag", label: "DAG", element: <DagPage /> },
];

export default function App() {
  return (
    <div className="shell">
      <nav className="sidebar">
        <div className="brand">MA-Gym</div>
        {PAGES.map((p) => (
          <NavLink key={p.path} to={p.path} className={({ isActive }) => (isActive ? "active" : "")}>
            {p.label}
          </NavLink>
        ))}
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/metrics" replace />} />
          {PAGES.map((p) => (
            <Route key={p.path} path={p.path} element={p.element} />
          ))}
        </Routes>
      </main>
    </div>
  );
}
