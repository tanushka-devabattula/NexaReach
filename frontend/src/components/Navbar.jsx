import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

function Navbar() {
  return (
    <header className="navbar">
      <div className="nav-container">
        <Link to="/" className="brand">
          <div className="brand-icon">
            <Sparkles size={20} />
          </div>

          <div className="brand-text">
            <span className="brand-name">NexaReach</span>
            <span className="brand-subtitle">AI Communication Platform</span>
          </div>
        </Link>

        <nav className="nav-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">How It Works</a>
          <a href="#about">About</a>
        </nav>

        <div className="nav-actions">
          <Link to="/login" className="login-btn">
            Login
          </Link>

          <Link to="/register" className="register-btn">
            Get Started
          </Link>
        </div>
      </div>
    </header>
  );
}

export default Navbar;