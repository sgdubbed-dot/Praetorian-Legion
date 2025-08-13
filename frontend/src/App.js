import React from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import MissionControl from "./pages/MissionControl";
import Missions from "./pages/Missions";
import MissionDetail from "./pages/MissionDetail";
import Forums from "./pages/Forums";
import Rolodex from "./pages/Rolodex";
import ProspectDetail from "./pages/ProspectDetail";
import HotLeads from "./pages/HotLeads";
import HotLeadDetail from "./pages/HotLeadDetail";
import Agents from "./pages/Agents";
import Guardrails from "./pages/Guardrails";
import GuardrailDetail from "./pages/GuardrailDetail";
import Exports from "./pages/Exports";
import Findings from "./pages/Findings";
import FindingDetail from "./pages/FindingDetail";
import ErrorBoundary from "./components/ErrorBoundary";

function NavLink({ to, children }) {
  const location = useLocation();
  const active = location.pathname.startsWith(to);
  return (
    <Link to={to} className={`px-3 py-2 rounded ${active ? "bg-blue-600 text-white" : "hover:bg-neutral-200"}`}>{children}</Link>
  );
}

function AppShell() {
  return (
    <div className="p-4 space-y-4">
      <BrowserRouter>
        {/* Brand Header */}
        <div className="bg-white rounded shadow p-4 text-center">
          <h1 className="text-2xl font-bold text-neutral-800">Augustus</h1>
          <p className="text-sm italic text-neutral-600 mt-1">Praetoria Legio - Machina Prudentia Negotiorum Magister</p>
        </div>
        
        {/* Navigation */}
        <div className="flex items-center gap-2 bg-white rounded shadow p-2">
          <NavLink to="/">Campaign Control</NavLink>
          <NavLink to="/campaigns">Campaigns</NavLink>
          <NavLink to="/forums">Forums</NavLink>
          <NavLink to="/rolodex">Rolodex</NavLink>
          <NavLink to="/hotleads">Hot Leads</NavLink>
          <NavLink to="/agents">Agents</NavLink>
          <NavLink to="/guardrails">Guardrails</NavLink>
          <NavLink to="/exports">Exports</NavLink>
          <NavLink to="/findings">Findings</NavLink>
        </div>
        <div>
          <Routes>
            <Route path="/" element={<MissionControl />} />
            <Route path="/campaigns" element={<ErrorBoundary page="Campaigns"><Missions /></ErrorBoundary>} />
            <Route path="/campaigns/:id" element={<ErrorBoundary page="CampaignDetail"><MissionDetail /></ErrorBoundary>} />
            <Route path="/forums" element={<Forums />} />
            <Route path="/rolodex" element={<Rolodex />} />
            <Route path="/prospects/:id" element={<ProspectDetail />} />
            <Route path="/hotleads" element={<HotLeads />} />
            <Route path="/hotleads/:id" element={<HotLeadDetail />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/guardrails" element={<Guardrails />} />
            <Route path="/guardrails/:id" element={<GuardrailDetail />} />
            <Route path="/exports" element={<Exports />} />
            <Route path="/findings" element={<ErrorBoundary page="Findings"><Findings /></ErrorBoundary>} />
            <Route path="/findings/:id" element={<ErrorBoundary page="FindingDetail"><FindingDetail /></ErrorBoundary>} />
          </Routes>
        </div>
      </BrowserRouter>
    </div>
  );
}

export default function App() {
  return <AppShell />;
}