import {
  ArrowRight,
Sparkles,
Globe2,
BrainCircuit,
Send,
BarChart3,
Users,
WandSparkles,
Languages,
ChartNoAxesCombined,
} from "lucide-react";
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useEffect } from "react";
import { checkBackendHealth } from "../services/api";
import Footer from "../components/Footer";

function LandingPage() {
  useEffect(() => {
  checkBackendHealth()
    .then((data) => {
      console.log("Backend health:", data);
    })
    .catch((error) => {
      console.error("Backend connection failed:", error.message);
    });
}, []);
  return (
    <div className="landing-page">
      <Navbar />

      <main>
        <section className="hero">
          <div className="hero-content">
            <div className="hero-badge">
              <Sparkles size={16} />
              AI-Powered Mass Communication
            </div>

            <h1>
              Build. Communicate.
              <span> Create Impact.</span>
            </h1>

            <p className="hero-description">
              A smarter way to create, translate, personalize, and deliver
              public awareness campaigns across languages and communication
              channels.
            </p>

            <div className="hero-actions">
              <Link to="/register" className="primary-btn">
                Get Started
                <ArrowRight size={18} />
              </Link>

              <a href="#features" className="secondary-btn">
                Explore Platform
              </a>
            </div>

            <div className="hero-highlights">
              <div className="highlight-item">
                <Globe2 size={20} />
                <div>
                  <strong>Multilingual</strong>
                  <span>Reach diverse audiences</span>
                </div>
              </div>

              <div className="highlight-item">
                <BrainCircuit size={20} />
                <div>
                  <strong>AI-Powered</strong>
                  <span>Create smarter content</span>
                </div>
              </div>
            </div>
          </div>

          <div className="hero-visual">
            <div className="visual-glow"></div>

            <div className="dashboard-preview">
              <div className="preview-header">
                <div>
                  <span className="preview-label">Campaign Overview</span>
                  <h3>Public Awareness Campaign</h3>
                </div>

                <span className="status-badge">Live</span>
              </div>

              <div className="preview-stats">
                <div className="stat-card">
                  <span>Reach</span>
                  <strong>24.8K</strong>
                  <small>+18.4%</small>
                </div>

                <div className="stat-card">
                  <span>Engagement</span>
                  <strong>76.2%</strong>
                  <small>+12.7%</small>
                </div>
              </div>

              <div className="language-preview">
                <div className="language-title">
                  <span>Language Distribution</span>
                  <span>View all</span>
                </div>

                <div className="language-bars">
                  <div className="language-row">
                    <span>English</span>
                    <div className="bar">
                      <div className="bar-fill english"></div>
                    </div>
                    <strong>42%</strong>
                  </div>

                  <div className="language-row">
                    <span>Telugu</span>
                    <div className="bar">
                      <div className="bar-fill telugu"></div>
                    </div>
                    <strong>31%</strong>
                  </div>

                  <div className="language-row">
                    <span>Hindi</span>
                    <div className="bar">
                      <div className="bar-fill hindi"></div>
                    </div>
                    <strong>27%</strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="floating-card floating-card-one">
              <Globe2 size={18} />
              <div>
                <strong>10+ Languages</strong>
                <span>Multilingual reach</span>
              </div>
            </div>

            <div className="floating-card floating-card-two">
              <Sparkles size={18} />
              <div>
                <strong>AI Content</strong>
                <span>Generated instantly</span>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="features-section">
          <div className="section-heading">
            <span className="section-label">POWERFUL CAPABILITIES</span>

            <h2>
              Everything you need to
              <span className="gradient-text"> communicate at scale.</span>
            </h2>

            <p>
              From creating multilingual content to understanding audience
              engagement, the platform brings the complete communication
              workflow together.
            </p>
          </div>

          <div className="features-grid">
            <div className="feature-card featured-card">
              <div className="feature-icon">
                <Globe2 size={24} />
              </div>

              <span className="feature-number">01</span>

              <h3>Multilingual Reach</h3>

              <p>
                Create and deliver public awareness messages across multiple
                Indian languages, helping organizations communicate with diverse
                communities.
              </p>

              <div className="feature-tag">
                Hindi · Telugu · Tamil · Kannada +
              </div>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <BrainCircuit size={24} />
              </div>

              <span className="feature-number">02</span>

              <h3>AI Content Creation</h3>

              <p>
                Generate campaign content with AI based on the campaign type,
                audience, tone, channel, and key communication points.
              </p>

              <div className="feature-tag">Generate · Personalize · Review</div>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <Send size={24} />
              </div>

              <span className="feature-number">03</span>

              <h3>Multi-Channel Communication</h3>

              <p>
                Reach audiences through email, SMS, WhatsApp, push
                notifications, and web broadcasts from one unified campaign
                workflow.
              </p>

              <div className="feature-tag">Email · SMS · WhatsApp · Push</div>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <BarChart3 size={24} />
              </div>

              <span className="feature-number">04</span>

              <h3>Engagement Analytics</h3>

              <p>
                Understand campaign performance with audience engagement,
                channel performance, language insights, and campaign analytics.
              </p>

              <div className="feature-tag">Track · Analyze · Improve</div>
            </div>
          </div>
        </section>
        <section id="how-it-works" className="how-section">
  <div className="section-heading">
    <span className="section-label">HOW IT WORKS</span>

    <h2>
      From idea to
      <span className="gradient-text"> impact.</span>
    </h2>

    <p>
      A simple workflow that takes your campaign from planning to
      measurable audience engagement.
    </p>
  </div>

  <div className="workflow">

    <div className="workflow-line"></div>

    <div className="workflow-step">
      <div className="step-icon">
        <Sparkles size={22} />
        <span>01</span>
      </div>

      <div className="step-content">
        <h3>Create Campaign</h3>
        <p>
          Define your campaign objective, type, priority, dates,
          and communication goals.
        </p>
      </div>
    </div>


    <div className="workflow-step">
      <div className="step-icon">
        <Users size={22} />
        <span>02</span>
      </div>

      <div className="step-content">
        <h3>Select Your Audience</h3>
        <p>
          Choose audience members or create targeted segments
          using demographic and engagement-based criteria.
        </p>
      </div>
    </div>


    <div className="workflow-step">
      <div className="step-icon">
        <WandSparkles size={22} />
        <span>03</span>
      </div>

      <div className="step-content">
        <h3>Generate with AI</h3>
        <p>
          Create campaign content with AI and personalize the
          message according to audience, tone, and channel.
        </p>
      </div>
    </div>


    <div className="workflow-step">
      <div className="step-icon">
        <Languages size={22} />
        <span>04</span>
      </div>

      <div className="step-content">
        <h3>Translate & Personalize</h3>
        <p>
          Adapt your communication into multiple languages while
          keeping the message relevant to each audience.
        </p>
      </div>
    </div>


    <div className="workflow-step">
      <div className="step-icon">
        <ChartNoAxesCombined size={22} />
        <span>05</span>
      </div>

      <div className="step-content">
        <h3>Distribute & Measure</h3>
        <p>
          Deliver across communication channels and track
          engagement, performance, and audience feedback.
        </p>
      </div>
    </div>

  </div>
</section>
        <section id="about" className="about-section">
           <div className="about-content">
    <div className="about-icon">
      <Sparkles size={22} />
    </div>

    <span className="section-label">BUILT FOR IMPACT</span>

    <h2>
      Communication that
      <span className="gradient-text"> reaches everyone.</span>
    </h2>

    <p>
      Create meaningful public awareness campaigns, reach diverse
      audiences in their preferred languages, and understand the
      impact of every communication.
    </p>

    <Link to="/register" className="primary-btn about-btn">
      Start Building Campaigns
      <ArrowRight size={18} />
    </Link>
  </div>
        </section>
           </main>

      <Footer />
    </div>
  );
}

export default LandingPage;
