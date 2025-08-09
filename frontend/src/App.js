import React from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import "./App.css";
import MissionControl from "./pages/MissionControl";
import Missions from "./pages/Missions";
import Agents from "./pages/Agents";
import Forums from "./pages/Forums";
import Rolodex from "./pages/Rolodex";
import HotLeads from "./pages/HotLeads";
import Guardrails from "./pages/Guardrails";
import Exports from "./pages/Exports";

const NavBar = () => (
  <div className="w-full bg-neutral-900 text-white">
    <div className="max-w-6xl mx-auto flex flex-wrap gap-3 p-3 text-sm">
      {[
        ["Mission Control", "/"],
        ["Missions", "/missions"],
        ["Forums", "/forums"],
        ["Rolodex", "/rolodex"],
        ["Hot Leads", "/hotleads"],
        ["Agents", "/agents"],
        ["Guardrails", "/guardrails"],
        ["Exports", "/exports"],
      ].map(([label, path]) => (
        <NavLink
          key={path}
          to={path}
          end
          className={({ isActive }) =>
            `px-3 py-1 rounded ${isActive ? "bg-blue-600" : "hover:bg-neutral-800"}`
          }
        >
          {label}
        </NavLink>
      ))}
    </div>
  </div>
);

function App() {
  return (
    <div className="min-h-screen bg-neutral-100">
      <BrowserRouter>
        <NavBar />
        <div className="max-w-6xl mx-auto p-4">
          <Routes>
            <Route path="/" element={<MissionControl />} />
            <Route path="/missions" element={<Missions />} />
            <Route path="/forums" element={<Forums />} />
            <Route path="/rolodex" element={<Rolodex />} />
            <Route path="/hotleads" element={<HotLeads />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/guardrails" element={<Guardrails />} />
            <Route path="/exports" element={<Exports />} />
          </Routes>
        </div>
      </BrowserRouter>
    </div>
  );
}

export default App;