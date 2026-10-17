
function Footer() {
  return (
    <footer
      style={{
        padding: "24px 20px",
        textAlign: "center",
        background: "#f8fafc",
        borderTop: "1px solid #e2e8f0",
        color: "#64748b",
        fontSize: "13px",
      }}
    >
      © {new Date().getFullYear()} NexaReach. AI-powered multilingual
      public awareness platform.
    </footer>
  );
}

export default Footer;
