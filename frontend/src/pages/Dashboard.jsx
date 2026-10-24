
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  LogOut,
  Users,
  Megaphone,
  FileText,
  LayoutDashboard,
  Layers,
  ArrowUpRight,
  Sparkles,
  Globe,
  BrainCircuit,
} from "lucide-react";
import "./Dashboard.css";

export default function Dashboard() {
  const navigate = useNavigate();

  useEffect(() => {
    if (!sessionStorage.getItem("access_token")) {
      navigate("/login", { replace: true });
    }
  }, [navigate]);

  const logout = () => {
    sessionStorage.removeItem("access_token");
    navigate("/login", { replace: true });
  };

  const items = [
    {
      title: "Audience",
      description: "Organize your audience and manage member details.",
      icon: Users,
      path: "/audience",
      number: "01",
      color: "purple",
    },
    {
      title: "Campaigns",
      description: "Create and manage public awareness campaigns.",
      icon: Megaphone,
      path: "/campaigns",
      number: "02",
      color: "blue",
    },
    {
      title: "Templates",
      description: "Create reusable messages in multiple languages.",
      icon: FileText,
      path: "/templates",
      number: "03",
      color: "orange",
    },
    {
      title: "Segments",
      description: "Group audiences using reusable targeting criteria.",
      icon: Layers,
      path: "/segments",
      number: "04",
      color: "green",
    },
    {
      title: "AI Studio",
      description:
        "Generate, translate, personalize, analyze, and review messages.",
      icon: BrainCircuit,
      path: "/ai-studio",
      number: "05",
      color: "purple",
    },
  ];

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div className="dashboard-brand">
          <span className="dashboard-brand-icon">
            <Sparkles size={22} />
          </span>
          <div>
            <strong>NexaReach</strong>
            <small>COMMUNICATION PLATFORM</small>
          </div>
        </div>

        <p className="dashboard-sidebar-label">WORKSPACE</p>

        <nav className="dashboard-nav">
          <button
            className="dashboard-nav-item active"
            onClick={() => navigate("/dashboard")}
          >
            <LayoutDashboard size={16} /> Dashboard
          </button>

          {items.map(({ title, icon: Icon, path }) => (
            <button
              className="dashboard-nav-item"
              key={title}
              onClick={() => navigate(path)}
            >
              <Icon size={16} /> {title}
            </button>
          ))}
        </nav>

        <div className="dashboard-sidebar-bottom">
          <div className="dashboard-sidebar-note">
            <Globe size={18} />
            <strong>Communication without barriers.</strong>
            <p>Reach communities in their preferred language.</p>
          </div>

          <button className="dashboard-signout" onClick={logout}>
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="dashboard-topbar">
          <div>
            <span className="dashboard-breadcrumb">
              Workspace / Dashboard
            </span>
            <h1>Dashboard</h1>
          </div>

          <button
            className="dashboard-website-btn"
            onClick={() => navigate("/")}
          >
            View website <ArrowUpRight size={15} />
          </button>
        </header>

        <section className="dashboard-hero">
          <div>
            <span className="dashboard-eyebrow">
              <Sparkles size={13} /> YOUR WORKSPACE
            </span>

            <h2>
              Make every message
              <br />
              create an <span>impact.</span>
            </h2>

            <p>
              Manage your audience, build campaigns, and create multilingual
              messages — all in one place.
            </p>

            <button
              className="dashboard-get-started"
              onClick={() => navigate("/ai-studio")}
            >
              Open AI Studio <ArrowUpRight size={15} />
            </button>
          </div>

          <div className="dashboard-hero-art">
            <div className="dashboard-orbit">
              <Globe size={57} strokeWidth={1.5} />
            </div>
            <span className="dashboard-float-tag tag-one">
              ✦ Multilingual
            </span>
            <span className="dashboard-float-tag tag-two">
              ↗ Public impact
            </span>
            <span className="dashboard-float-tag tag-three">
              ✧ AI-powered
            </span>
          </div>
        </section>

        <section className="dashboard-workspace">
          <div className="dashboard-section-heading">
            <div>
              <h2>Your workspace</h2>
              <p>Choose a module to continue working.</p>
            </div>
            <span className="dashboard-module-count">
              {String(items.length).padStart(2, "0")} MODULES
            </span>
          </div>

          <div className="dashboard-cards">
            {items.map(
              ({ title, description, icon: Icon, path, number, color }) => (
                <button
                  className="dashboard-card"
                  key={title}
                  onClick={() => navigate(path)}
                >
                  <div className={`dashboard-card-icon ${color}`}>
                    <Icon size={21} />
                  </div>

                  <span className="dashboard-card-number">{number}</span>
                  <h3>{title}</h3>
                  <p>{description}</p>

                  <span className="dashboard-card-link">
                    Open module <ArrowUpRight size={14} />
                  </span>
                </button>
              )
            )}
          </div>
        </section>

        <footer className="dashboard-footer">
          <span>© 2026 NexaReach</span>
          <span>Empowering communication for everyone.</span>
        </footer>
      </main>
    </div>
  );
}
