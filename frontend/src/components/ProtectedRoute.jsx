import { Navigate } from "react-router-dom";
import { getSession } from "../services/api";

// Wrap a page with <ProtectedRoute> to require login.
// Add roles={["admin"]} to also require one of those roles.
export default function ProtectedRoute({ children, roles }) {
  const { token, user } = getSession();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (roles && user?.role && !roles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
