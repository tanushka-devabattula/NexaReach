
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import LandingPage from "./pages/LandingPage";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Audience from "./pages/Audience";
import Campaigns from "./pages/Campaigns";
import Templates from "./pages/Templates";
import Segments from "./pages/Segments";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/audience" element={<Audience />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/segments" element={<Segments />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
