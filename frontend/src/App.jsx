import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AIStudio from "./pages/AIStudio";
import LandingPage from "./pages/LandingPage";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Audience from "./pages/Audience";
import Campaigns from "./pages/Campaigns";
import Templates from "./pages/Templates";
import Segments from "./pages/Segments";
import UserManagement from "./pages/UserManagement";
import ProtectedRoute from "./components/ProtectedRoute";
import Announcements from "./pages/Announcements";
import "./App.css";
import Review from "./pages/Review";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/announcements" element={<Announcements />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/audience"
          element={
            <ProtectedRoute>
              <Audience />
            </ProtectedRoute>
          }
        />
        <Route
          path="/campaigns"
          element={
            <ProtectedRoute>
              <Campaigns />
            </ProtectedRoute>
          }
        />
        <Route
          path="/templates"
          element={
            <ProtectedRoute>
              <Templates />
            </ProtectedRoute>
          }
        />
        <Route
          path="/segments"
          element={
            <ProtectedRoute>
              <Segments />
            </ProtectedRoute>
          }
        />
        <Route
          path="/ai-studio"
          element={
            <ProtectedRoute>
              <AIStudio />
            </ProtectedRoute>
          }
        />
        <Route
          path="/review"
          element={
            <ProtectedRoute roles={["admin", "reviewer", "communication_team"]}>
              <Review />
            </ProtectedRoute>
          }
        />
        <Route
          path="/users"
          element={
            <ProtectedRoute roles={["admin"]}>
              <UserManagement />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
