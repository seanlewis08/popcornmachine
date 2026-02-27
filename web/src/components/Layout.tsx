import { Link, Outlet, useLocation } from "react-router-dom";

export function Layout() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <div className="min-h-screen" style={{ fontFamily: "'Roboto Condensed', Arial, sans-serif" }}>
      {/* Header bar */}
      <header
        style={{
          background: "linear-gradient(180deg, #3D2415 0%, #2C1810 100%)",
          borderBottom: "3px solid #C9A84C",
          padding: "12px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 12 }}>
          {/* Basketball icon */}
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
            <circle cx="18" cy="18" r="16" stroke="#C9A84C" strokeWidth="2" fill="#FF6B35" />
            <path d="M2 18 C2 18, 18 10, 34 18" stroke="#2C1810" strokeWidth="1.5" fill="none" />
            <path d="M2 18 C2 18, 18 26, 34 18" stroke="#2C1810" strokeWidth="1.5" fill="none" />
            <line x1="18" y1="2" x2="18" y2="34" stroke="#2C1810" strokeWidth="1.5" />
          </svg>
          <span
            style={{
              fontFamily: "'Oswald', sans-serif",
              fontSize: 28,
              fontWeight: 700,
              color: "#C9A84C",
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            PopcornMachine
          </span>
        </Link>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {!isHome && (
            <Link
              to="/"
              style={{
                color: "#E8D5B7",
                fontSize: 14,
                textDecoration: "none",
                padding: "6px 16px",
                border: "1px solid #5C3A21",
                borderRadius: 4,
                background: "rgba(92, 58, 33, 0.5)",
              }}
            >
              All Games
            </Link>
          )}
          <a
            href="https://seanlewis08.github.io"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: "#E8D5B7",
              fontSize: 14,
              textDecoration: "none",
              padding: "6px 16px",
              border: "1px solid #5C3A21",
              borderRadius: 4,
              background: "rgba(92, 58, 33, 0.5)",
            }}
          >
            Blog
          </a>
        </div>
      </header>

      {/* Main content */}
      <main>
        <Outlet />
      </main>
    </div>
  );
}
