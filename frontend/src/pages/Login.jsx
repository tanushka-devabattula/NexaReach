
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Sparkles,
} from "lucide-react";
import { loginUser } from "../services/api";

function Login() {
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();

    const data = new FormData(event.currentTarget);

    try {
      const result = await loginUser({
        email: data.get("email"),
        password: data.get("password"),
      });

      sessionStorage.setItem("access_token", result.access_token);

      navigate("/dashboard", { replace: true });
    } catch (error) {
      const detail = error.response?.data?.detail;

      alert(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : detail || "Login failed. Check your email and password."
      );
    }
  };

  return (
    <div className="auth-page">
      <Link to="/" className="auth-back">
        <ArrowLeft size={16} /> Back to home
      </Link>

      <div className="auth-card">
        <Link to="/" className="auth-brand">
          <span className="auth-brand-icon">
            <Sparkles size={22} />
          </span>
          <span>NexaReach</span>
        </Link>

        <div className="auth-heading">
          <h1>Welcome back</h1>
          <p>Sign in to manage your communication campaigns.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="login-email">Email address</label>
          <div className="auth-input-wrap">
            <Mail size={18} />
            <input
              id="login-email"
              name="email"
              type="email"
              placeholder="you@organization.com"
              required
            />
          </div>

          <label htmlFor="login-password">Password</label>
          <div className="auth-input-wrap">
            <LockKeyhole size={18} />
            <input
              id="login-password"
              name="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              required
            />

            <button
              type="button"
              className="password-toggle"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <button type="submit" className="auth-submit">
            Sign in
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account? <Link to="/register">Create one</Link>
        </p>

        <p className="auth-note">
          AI-powered multilingual public awareness platform
        </p>
      </div>
    </div>
  );
}

export default Login;
