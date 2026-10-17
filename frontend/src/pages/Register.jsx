
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  UserRound,
  Phone,
  Building2,
  Sparkles,
} from "lucide-react";
import { registerUser } from "../services/api";
import "../App.css";

function Register() {
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage("");

    const data = new FormData(event.currentTarget);
    const password = data.get("password");
    const confirmPassword = data.get("confirmPassword");

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setErrorMessage("Password must contain at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      const result = await registerUser({
        full_name: data.get("name").trim(),
        email: data.get("email").trim(),
        phone: data.get("phone") || null,
        organization: data.get("organization") || null,
        password,
        role: "user",
      });

      alert(`Account created successfully! Welcome, ${result.full_name}.`);
      navigate("/login");
    } catch (error) {
      console.error("Registration error:", error.response?.data || error);

      const detail = error.response?.data?.detail;
      setErrorMessage(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : detail || error.message || "Registration failed."
      );
    } finally {
      setLoading(false);
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
          <h1>Create your account</h1>
          <p>Join us to organize public awareness campaigns.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="register-name">Full name</label>
          <div className="auth-input-wrap">
            <UserRound size={18} />
            <input
              id="register-name"
              name="name"
              type="text"
              placeholder="Enter your full name"
              minLength={2}
              required
            />
          </div>

          <label htmlFor="register-email">Email address</label>
          <div className="auth-input-wrap">
            <Mail size={18} />
            <input
              id="register-email"
              name="email"
              type="email"
              placeholder="you@organization.com"
              required
            />
          </div>

          <label htmlFor="register-phone">Phone (optional)</label>
          <div className="auth-input-wrap">
            <Phone size={18} />
            <input
              id="register-phone"
              name="phone"
              type="tel"
              placeholder="Enter phone number"
            />
          </div>

          <label htmlFor="register-organization">Organization (optional)</label>
          <div className="auth-input-wrap">
            <Building2 size={18} />
            <input
              id="register-organization"
              name="organization"
              type="text"
              placeholder="Enter organization"
            />
          </div>

          <label htmlFor="register-password">Password</label>
          <div className="auth-input-wrap">
            <LockKeyhole size={18} />
            <input
              id="register-password"
              name="password"
              type={showPassword ? "text" : "password"}
              placeholder="At least 8 characters"
              minLength={8}
              maxLength={128}
              required
            />
            <button
              type="button"
              className="password-toggle"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword((value) => !value)}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <label htmlFor="register-confirm-password">Confirm password</label>
          <div className="auth-input-wrap">
            <LockKeyhole size={18} />
            <input
              id="register-confirm-password"
              name="confirmPassword"
              type={showPassword ? "text" : "password"}
              placeholder="Re-enter password"
              required
            />
          </div>

          {errorMessage && (
            <p className="error-message" role="alert">
              {errorMessage}
            </p>
          )}

          <button
            type="submit"
            className="auth-submit"
            disabled={loading}
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>

        <p className="auth-note">
          AI-powered multilingual public awareness platform
        </p>
      </div>
    </div>
  );
}

export default Register;
