import { useState } from "react";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://127.0.0.1:5000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Login failed");
      localStorage.setItem("siem_token", data.token);
      localStorage.setItem("siem_role", data.role);
      onLogin(data.role);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "#020817", fontFamily: "system-ui, -apple-system, sans-serif"
    }}>
      <div style={{
        background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px",
        padding: "40px", width: "100%", maxWidth: "380px", display: "flex",
        flexDirection: "column", gap: "24px"
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "2.5rem" }}>🛡️</div>
          <h1 style={{ margin: "8px 0 4px", color: "#f8fafc", fontSize: "1.5rem", fontWeight: "800" }}>
            AI SIEM
          </h1>
          <p style={{ margin: 0, color: "#64748b", fontSize: "0.9rem" }}>Admin Login</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            style={inputStyle}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={inputStyle}
          />
          {error && (
            <div style={{ color: "#fca5a5", background: "rgba(239,68,68,0.1)", border: "1px solid #ef4444", borderRadius: "6px", padding: "10px", fontSize: "0.88rem", textAlign: "center" }}>
              {error}
            </div>
          )}
          <button type="submit" disabled={loading} style={{
            padding: "12px", borderRadius: "8px", border: "none", cursor: loading ? "not-allowed" : "pointer",
            background: loading ? "#334155" : "#6366f1", color: "#fff", fontWeight: "700",
            fontSize: "1rem", letterSpacing: "0.5px", transition: "background 0.2s"
          }}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}

const inputStyle = {
  padding: "12px 14px", borderRadius: "8px", border: "1px solid #334155",
  background: "#1e293b", color: "#f8fafc", fontSize: "0.95rem", outline: "none",
  width: "100%", boxSizing: "border-box"
};
