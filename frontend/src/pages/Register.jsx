import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  UserRound,
  Mail,
  Phone,
  Building2,
  LockKeyhole,
  Eye,
  EyeOff,
  Sparkles,
} from "lucide-react";

function Register() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  return (
    <div className="auth-page register-page">
      <Link to="/" className="auth-back">
        <ArrowLeft size={16} /> Back to home
      </Link>

      <div className="auth-card register-card">
        <Link to="/" className="auth-brand">
          <span className="auth-brand-icon">
            <Sparkles size={22} />
          </span>
          <span>NexaReach</span>
        </Link>

        <div className="auth-heading">
          <h1>Create your account</h1>
          <p>Get started with smarter public communication.</p>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();

            const data = new FormData(event.currentTarget);
            const password = data.get("password");
            const confirmPassword = data.get("confirmPassword");

            if (password !== confirmPassword) {
              alert("Passwords do not match.");
              return;
            }

            alert("Registration UI is ready. Backend integration is coming next.");
          }}
        >
          <label htmlFor="fullName">Full name</label>
          <div className="auth-input-wrap">
            <UserRound size={18} />
            <input
              id="fullName"
              name="name"
              type="text"
              placeholder="Enter your full name"
              autoComplete="name"
              required
            />
          </div>

          <label htmlFor="registerEmail">Email address</label>
          <div className="auth-input-wrap">
            <Mail size={18} />
            <input
              id="registerEmail"
              name="email"
              type="email"
              placeholder="you@organization.com"
              autoComplete="email"
              required
            />
          </div>

          <label htmlFor="phone">Phone number</label>
          <div className="auth-input-wrap">
            <Phone size={18} />
            <input
              id="phone"
              name="phone"
              type="tel"
              placeholder="Enter your phone number"
              autoComplete="tel"
              required
            />
          </div>

          <label htmlFor="organization">Organization</label>
          <div className="auth-input-wrap">
            <Building2 size={18} />
            <input
              id="organization"
              name="organization"
              type="text"
              placeholder="Organization or institution"
              required
            />
          </div>

          <label htmlFor="role">Your role</label>
          <select id="role" name="role" className="auth-select" required defaultValue="">
            <option value="" disabled>Select your role</option>
            <option value="campaign_manager">Campaign Manager</option>
            <option value="communication_team">Communication Team</option>
          </select>

          <label htmlFor="registerPassword">Password</label>
          <div className="auth-input-wrap">
            <LockKeyhole size={18} />
            <input
              id="registerPassword"
              name="password"
              type={showPassword ? "text" : "password"}
              placeholder="Create a password"
              autoComplete="new-password"
              minLength={8}
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

          <label htmlFor="confirmPassword">Confirm password</label>
          <div className="auth-input-wrap">
            <LockKeyhole size={18} />
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Re-enter your password"
              autoComplete="new-password"
              minLength={8}
              required
            />
            <button
              type="button"
              className="password-toggle"
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            >
              {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <button type="submit" className="auth-submit">
            Create Account
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