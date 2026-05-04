import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

/* ─────────────────────────────────────────────
   HELPER UTILITIES
───────────────────────────────────────────── */
function formatTime(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  } catch {
    return String(ts);
  }
}

function getMostFrequentAttack(logs) {
  if (!logs || !logs.length) return "—";
  const freq = {};
  logs.forEach((l) => {
    // Exclude basic normal traffic if needed, but here we count valid attack variations
    if (l.attack_type !== undefined && l.attack_type !== null && l.attack_type !== "Unknown" && l.attack_type !== -1) {
      freq[l.attack_type] = (freq[l.attack_type] || 0) + 1;
    }
  });
  const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]);
  return sorted.length > 0 ? sorted[0][0] : "—";
}

/* ─────────────────────────────────────────────
   SUB-COMPONENTS
───────────────────────────────────────────── */
function MetricCard({ icon, label, value, accent }) {
  const borderColor =
    accent === "red"
      ? "#ef4444"
      : accent === "amber"
        ? "#f59e0b"
        : accent === "cyan"
          ? "#06b6d4"
          : "#6366f1";

  return (
    <div className="metric-card" style={{ borderTopColor: borderColor, flex: 1, minWidth: "200px", padding: "16px", borderRadius: "8px", background: "rgba(255,255,255,0.02)", display: "flex", flexDirection: "column", gap: "8px", borderTopWidth: "3px", borderTopStyle: "solid" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span className="metric-icon" style={{ fontSize: "1.5rem" }}>{icon}</span>
        <div className="metric-label" style={{ color: "#94a3b8", fontSize: "0.9rem", textTransform: "uppercase", fontWeight: "600", letterSpacing: "0.5px" }}>{label}</div>
      </div>
      <div className="metric-value" style={{ color: borderColor, fontSize: "2rem", fontWeight: "bold" }}>
        {value}
      </div>
    </div>
  );
}

const SEVERITY_STYLES = {
  CRITICAL: { bg: "rgba(220,38,38,0.25)",   color: "#fca5a5", border: "#dc2626" },
  HIGH:     { bg: "rgba(239,68,68,0.2)",    color: "#fca5a5", border: "#ef4444" },
  MEDIUM:   { bg: "rgba(245,158,11,0.2)",   color: "#fcd34d", border: "#f59e0b" },
  LOW:      { bg: "rgba(34,197,94,0.15)",   color: "#86efac", border: "#22c55e" },
};

function AlertBadge({ severity }) {
  const s = SEVERITY_STYLES[severity] || SEVERITY_STYLES.LOW;
  return (
    <span
      className="alert-badge"
      style={{
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        padding: "4px 10px",
        borderRadius: "4px",
        fontSize: "0.78rem",
        fontWeight: "bold",
        textTransform: "uppercase",
        letterSpacing: "0.5px",
        whiteSpace: "nowrap",
      }}
    >
      {severity === "CRITICAL" ? "🚨 " : severity === "HIGH" ? "🔴 " : severity === "MEDIUM" ? "⚠️ " : "✅ "}
      {severity}
    </span>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const val = payload[0].value;
    if (payload[0].dataKey === "anomaly") {
      const timeLabel = payload[0].payload.timeLabel || label;
      return (
        <div className="chart-tooltip" style={{ background: "#1e293b", padding: "12px", border: "1px solid #334155", borderRadius: "8px", color: "#f8fafc", boxShadow: "0 4px 6px rgba(0,0,0,0.3)" }}>
          <p className="tooltip-label" style={{ margin: "0 0 6px 0", fontSize: "12px", color: "#94a3b8" }}>Time: {timeLabel}</p>
          <p style={{ color: val === 1 ? "#ef4444" : "#22c55e", margin: 0, fontWeight: "bold", display: "flex", alignItems: "center", gap: "6px" }}>
            {val === 1 ? "🔴 Anomaly Detected" : "🟢 Normal Traffic"}
          </p>
        </div>
      );
    } else {
      return (
        <div className="chart-tooltip" style={{ background: "#1e293b", padding: "12px", border: "1px solid #334155", borderRadius: "8px", color: "#f8fafc", boxShadow: "0 4px 6px rgba(0,0,0,0.3)" }}>
          <p className="tooltip-label" style={{ margin: "0 0 6px 0", fontSize: "12px", color: "#94a3b8" }}>Attack Type: {label}</p>
          <p style={{ color: "#38bdf8", margin: 0, fontWeight: "bold" }}>
            Count: {val}
          </p>
        </div>
      );
    }
  }
  return null;
}

/* ─────────────────────────────────────────────
   MAIN DASHBOARD
───────────────────────────────────────────── */
function Dashboard() {
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(null);

  // Real-time & Error State Handling
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchData = async () => {
    setIsUpdating(true);
    try {
      const [logsRes, alertsRes] = await Promise.all([
        fetch("http://127.0.0.1:5000/logs"),
        fetch("http://127.0.0.1:5000/alerts"),
      ]);

      if (!logsRes.ok || !alertsRes.ok) throw new Error("API completely unresponsive.");

      const logsData = await logsRes.json();
      const alertsData = await alertsRes.json();

      setLogs(logsData);
      setAlerts(alertsData);
      setLastRefresh(new Date());
      setErrorMsg(null);
    } catch (err) {
      console.error("Fetch error:", err);
      setErrorMsg("Failed to connect to the backend server. Re-trying...");
    } finally {
      setIsUpdating(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  /* ── Derived Metrics & Data Validation ── */
  const displayLogs = logs.slice(-100).reverse(); // Latest 100 max, newest first
  const totalLogs = logs.length;
  // Anomaly Rate: Count logs where anomaly is 1 / Total Logs
  // anomaly is now a bool (true = anomaly) after Phase 3 fix
  const anomalyCount = logs.filter((l) => l.anomaly === true || l.anomaly === -1).length;
  const anomalyRate = totalLogs > 0 ? ((anomalyCount / totalLogs) * 100).toFixed(1) : "0.0";
  const highAlerts = alerts.filter((a) => a.severity === "HIGH" || a.severity === "CRITICAL").length;
  const topAttack = getMostFrequentAttack(logs);

  /* ── System Status Logic ── */
  let systemStatus = "NORMAL";
  let statusColor = "#22c55e";
  let statusBg = "rgba(34,197,94,0.1)";

  const criticalAlerts = alerts.filter((a) => a.severity === "CRITICAL").length;
  if (criticalAlerts >= 1 || highAlerts >= 3) {
    systemStatus = "CRITICAL";
    statusColor = "#ef4444";
    statusBg = "rgba(239,68,68,0.15)";
  } else if (parseFloat(anomalyRate) > 20 || highAlerts >= 1) {
    systemStatus = "WARNING";
    statusColor = "#f59e0b";
    statusBg = "rgba(245,158,11,0.15)";
  }

  /* ── Chart Data (Anomaly Trend: Oldest to Newest, max 50 for readability) ── */
  const chartData = logs.slice(-50).map((l, i) => ({
    index: i + 1,
    // support both bool (new) and -1/1 (legacy)
    anomaly: (l.anomaly === true || l.anomaly === -1) ? 1 : 0,
    timeLabel: new Date(l.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })
  }));

  /* ── Attack Distribution Chart Data ── */
  const attackFreq = {};
  logs.forEach(l => {
    const at = l.attack_type;
    if (at && at !== "Unknown" && at !== -1 && at !== "Normal") {
      attackFreq[at] = (attackFreq[at] || 0) + 1;
    }
  });
  // attack_type is now a decoded string — use it directly
  const attackChartData = Object.entries(attackFreq)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  /* ── Latest Alerts ── */
  const recentAlerts = alerts.slice(0, 5);

  return (
    <div className="dashboard" style={{ display: "flex", flexDirection: "column", gap: "24px", paddingBottom: "40px", maxWidth: "1400px", margin: "0 auto", padding: "20px", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      {/* GLOBAL ANIMATIONS */}
      <style>
        {`
          @keyframes highlightNew {
            0% { background-color: rgba(99, 102, 241, 0.4); }
            100% { background-color: transparent; }
          }
          @keyframes pulseSync {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.9); }
            100% { opacity: 1; transform: scale(1); }
          }
          .log-row-anim {
            animation: highlightNew 2s ease-out forwards;
          }
          .sync-icon {
            display: inline-block;
          }
          .syncing .sync-icon {
            animation: pulseSync 1s infinite ease-in-out;
            color: #38bdf8 !important;
          }
        `}
      </style>

      {/* ── ERROR & LOADING STATE ── */}
      {errorMsg && (
        <div style={{ padding: "16px", background: "rgba(239,68,68,0.15)", border: "1px solid #ef4444", borderRadius: "8px", color: "#fca5a5", textAlign: "center", fontWeight: "bold" }}>
          ⚠️ {errorMsg}
        </div>
      )}

      {/* ── STATUS BANNER ── */}
      <div style={{
        padding: "16px",
        borderRadius: "8px",
        border: `1px solid ${statusColor}`,
        backgroundColor: statusBg,
        textAlign: "center",
        fontWeight: "bold",
        fontSize: "1.2rem",
        color: statusColor,
        letterSpacing: "1px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "12px",
        textTransform: "uppercase",
        boxShadow: `0 0 16px ${statusBg}`
      }}>
        {systemStatus === "CRITICAL" ? "🚨 " : systemStatus === "WARNING" ? "⚠️ " : "✅ "}
        SYSTEM STATUS: {systemStatus}
      </div>

      {/* ── HEADER ── */}
      <header className="dash-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "10px", borderBottom: "1px solid #1e293b" }}>
        <div className="header-left" style={{ display: "flex", gap: "16px", alignItems: "center" }}>
          <span className="header-shield" style={{ fontSize: "2.5rem", WebkitDropShadow: "0 2px 4px rgba(0,0,0,0.5)" }}>🛡️</span>
          <div>
            <h1 className="header-title" style={{ margin: "0", fontSize: "1.8rem", color: "#f8fafc", fontWeight: "800" }}>AI SIEM Dashboard</h1>
            <p className="header-sub" style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: "0.95rem" }}>Security Information & Event Management</p>
          </div>
        </div>
        <div className="header-right" style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span className="live-dot" style={{ width: "10px", height: "10px", background: "#ef4444", borderRadius: "50%", display: "inline-block", boxShadow: "0 0 8px #ef4444" }} />
            <span className="live-label" style={{ color: "#ef4444", fontWeight: "bold", letterSpacing: "1px" }}>LIVE</span>
          </div>
          <span className={`refresh-time ${isUpdating ? 'syncing' : ''}`} style={{ color: "#94a3b8", fontSize: "0.95rem", background: "#1e293b", padding: "8px 14px", borderRadius: "8px", border: "1px solid #334155", display: "flex", alignItems: "center", gap: "8px", width: "220px", justifyContent: "center" }}>
            <span className="sync-icon">⚡</span>
            {loading ? "Connecting..." : lastRefresh ? (
              <span>Last updated: <span style={{ color: "#f8fafc", fontWeight: "600" }}>{lastRefresh.toLocaleTimeString("en-IN", { hour12: false })}</span></span>
            ) : "Waiting for data..."}
          </span>
        </div>
      </header>

      {/* ── SECTION 1: SUMMARY METRICS ── */}
      <section className="section" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", padding: "24px" }}>
        <h2 className="section-title" style={{ marginTop: "0", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px", fontSize: "1.3rem" }}>📈 Overview</h2>
        <div className="metrics-grid" style={{ display: "flex", flexWrap: "wrap", gap: "16px" }}>
          <MetricCard icon="📄" label="Total Logs" value={totalLogs} accent="indigo" />
          <MetricCard icon="⚠️" label="Anomaly Rate" value={`${anomalyRate}%`} accent="amber" />
          <MetricCard icon="🔴" label="High Alerts" value={highAlerts} accent="red" />
          <MetricCard icon="🎯" label="Top Attack" value={topAttack} accent="cyan" />
        </div>
      </section>

      {/* ── MAIN LAYOUT GRID ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>

        {/* ── ALERTS COLUMN ── */}
        <section className="section" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", padding: "24px", display: "flex", flexDirection: "column" }}>
          <div className="section-header-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <h2 className="section-title" style={{ margin: 0, color: "#f8fafc", fontSize: "1.3rem" }}>🚨 Recent Alerts</h2>
            {recentAlerts.length > 0 && <span className="badge-count" style={{ background: "#1e293b", padding: "6px 12px", borderRadius: "6px", fontSize: "0.85rem", color: "#94a3b8", fontWeight: "600" }}>{recentAlerts.length} shown</span>}
          </div>

          {recentAlerts.length === 0 ? (
            <div className="empty-state" style={{ color: "#22c55e", textAlign: "center", padding: "40px 0", flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px" }}>
              <span style={{ fontSize: "3rem", filter: "drop-shadow(0 0 10px rgba(34,197,94,0.4))" }}>✅</span>
              <span style={{ fontWeight: "bold", fontSize: "1.2rem", color: "#86efac" }}>System operating normally</span>
              <span style={{ color: "#94a3b8", fontSize: "0.95rem" }}>No anomalies detected</span>
            </div>
          ) : (
            <div className="alerts-list" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {recentAlerts.map((a, idx) => {
                const sStyle = SEVERITY_STYLES[a.severity] || SEVERITY_STYLES.LOW;
                // Use reason (Phase 4) if available, else fall back to legacy message
                const message = a.reason
                  || a.message
                  || (a.attack_type
                      ? `${a.attack_type} detected (confidence: ${Number(a.confidence).toFixed(2)})`
                      : "Anomaly detected");

                return (
                  <div
                    key={a._id || `alert-${idx}`}
                    className="alert-row log-row-anim"
                    style={{
                      padding: "14px 16px",
                      borderRadius: "8px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: "12px",
                      background: `${sStyle.bg}`,
                      borderLeft: `5px solid ${sStyle.border}`,
                      boxShadow: "0 2px 4px rgba(0,0,0,0.2)"
                    }}
                  >
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                        <AlertBadge severity={a.severity} />
                        {a.attack_type && (
                          <span style={{ color: "#cbd5e1", fontSize: "0.85rem", fontWeight: "600" }}>
                            {a.attack_type}
                          </span>
                        )}
                        {a.confidence != null && (
                          <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
                            conf: <span style={{ color: sStyle.color, fontWeight: "bold" }}>{Number(a.confidence).toFixed(2)}</span>
                          </span>
                        )}
                      </div>
                      <span className="alert-message" style={{ color: "#cbd5e1", fontSize: "0.88rem", lineHeight: "1.4" }}>
                        {message}
                      </span>
                    </div>
                    <span className="alert-time" style={{ color: "#64748b", fontSize: "0.82rem", whiteSpace: "nowrap", paddingTop: "2px" }}>
                      {formatTime(a.timestamp)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── ATTACK DISTRIBUTION ── */}
        <section className="section" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", padding: "24px", display: "flex", flexDirection: "column" }}>
          <h2 className="section-title" style={{ margin: "0 0 20px 0", color: "#f8fafc", fontSize: "1.3rem" }}>🎯 Attack Distribution</h2>
          {attackChartData.length === 0 ? (
            <div className="empty-state" style={{ color: "#22c55e", textAlign: "center", padding: "40px 0", flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px" }}>
              <span style={{ fontSize: "3rem", filter: "drop-shadow(0 0 10px rgba(34,197,94,0.4))" }}>🛡️</span>
              <span style={{ fontWeight: "bold", fontSize: "1.2rem", color: "#86efac" }}>Traffic is clean</span>
              <span style={{ color: "#94a3b8", fontSize: "0.95rem" }}>Not enough attack data</span>
            </div>
          ) : (
            <div className="chart-container" style={{ width: "100%", height: "260px", flex: 1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={attackChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="type" tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 500 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.05)" }} />
                  <Bar dataKey="count" fill="#38bdf8" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      </div>

      {/* ── SECTION 3: TREND CHART ── */}
      <section className="section" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", padding: "24px" }}>
        <h2 className="section-title" style={{ margin: "0 0 6px 0", color: "#f8fafc", fontSize: "1.3rem" }}>📊 Anomaly Trend</h2>
        <p className="section-desc" style={{ color: "#64748b", fontSize: "0.9rem", margin: "0 0 20px 0" }}>
          Timeline of detected anomalies (Latest 50 entries) - Smoothed Graph
        </p>
        <div className="chart-container" style={{ width: "100%", height: "260px" }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="timeLabel" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} minTickGap={40} />
              <YAxis ticks={[0, 1]} tickFormatter={(v) => (v === 1 ? "Anomaly" : "Normal")} tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 500 }} width={80} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={1} stroke="#ef4444" strokeDasharray="4 2" strokeOpacity={0.2} />
              <Line type="monotone" dataKey="anomaly" stroke="#6366f1" strokeWidth={3}
                dot={(props) => {
                  const { cx, cy, payload } = props;
                  return (
                    <circle key={`dot-${payload.index || payload.timeLabel}`} cx={cx} cy={cy} r={3.5} fill={payload.anomaly === 1 ? "#ef4444" : "#22c55e"} stroke="none" />
                  );
                }}
                activeDot={{ r: 6, stroke: "#fff", strokeWidth: 2 }} isAnimationActive={true} animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* ── SECTION 4: LOGS TABLE ── */}
      <section className="section" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "12px", padding: "24px", overflow: "hidden" }}>
        <div className="section-header-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h2 className="section-title" style={{ margin: 0, color: "#f8fafc", fontSize: "1.3rem" }}>🗒️ Log Entries</h2>
          {displayLogs.length > 0 && <span className="badge-count" style={{ background: "#1e293b", padding: "6px 14px", borderRadius: "6px", fontSize: "0.9rem", color: "#94a3b8", fontWeight: "600" }}>Showing latest {displayLogs.length} records</span>}
        </div>

        {displayLogs.length === 0 ? (
          <div className="empty-state" style={{ color: "#22c55e", textAlign: "center", padding: "60px 0", flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "12px" }}>
            <span style={{ fontSize: "3rem", filter: "drop-shadow(0 0 10px rgba(34,197,94,0.4))" }}>📝</span>
            <span style={{ fontWeight: "bold", fontSize: "1.2rem", color: "#86efac" }}>No logs available yet</span>
            <span style={{ color: "#94a3b8", fontSize: "0.95rem" }}>System is waiting for traffic data.</span>
          </div>
        ) : (
          <div className="table-wrapper" style={{ overflowX: "auto" }}>
            <table className="logs-table" style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.95rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #334155", color: "#94a3b8" }}>
                  <th style={{ padding: "14px 16px", fontWeight: "600" }}>Log ID</th>
                  <th style={{ padding: "14px 16px", fontWeight: "600" }}>Status</th>
                  <th style={{ padding: "14px 16px", fontWeight: "600" }}>Attack Type</th>
                  <th style={{ padding: "14px 16px", fontWeight: "600" }}>Severity</th>
                  <th style={{ padding: "14px 16px", fontWeight: "600" }}>Confidence</th>
                  <th style={{ padding: "14px 16px", fontWeight: "600" }}>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {displayLogs.map((log, idx) => {
                  const isAnomaly = log.anomaly === true || log.anomaly === -1;
                  const displayIndex = totalLogs - idx;
                  const sev = log.severity || (isAnomaly ? "HIGH" : "LOW");
                  return (
                    <tr
                      key={log._id || `log-${displayIndex}`}
                      className="log-row-anim"
                      style={{
                        backgroundColor: idx % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent",
                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                        transition: "background 0.2s"
                      }}
                      onMouseOver={e => e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.06)"}
                      onMouseOut={e => e.currentTarget.style.backgroundColor = idx % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent"}
                    >
                      <td style={{ padding: "14px 16px", color: "#64748b", fontWeight: "500" }}>#{displayIndex}</td>
                      <td style={{ padding: "14px 16px" }}>
                        <span className="status-pill" style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          padding: "4px 12px",
                          borderRadius: "12px",
                          fontSize: "0.85rem",
                          fontWeight: "bold",
                          textTransform: "uppercase",
                          background: isAnomaly ? "rgba(239,68,68,0.15)" : "rgba(34,197,94,0.15)",
                          color: isAnomaly ? "#ef4444" : "#22c55e",
                          border: `1px solid ${isAnomaly ? "rgba(239,68,68,0.3)" : "rgba(34,197,94,0.3)"}`
                        }}>
                          {isAnomaly ? "⚠️ Anomaly" : "✔ Normal"}
                        </span>
                      </td>
                      <td style={{ padding: "14px 16px", color: "#e2e8f0", fontWeight: "500" }}>
                        {log.attack_type || "—"}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <AlertBadge severity={sev} />
                      </td>
                      <td style={{ padding: "14px 16px", color: "#e2e8f0" }}>
                        {log.confidence != null ? (
                          <span style={{ color: log.confidence > 0.9 ? "#ef4444" : log.confidence > 0.6 ? "#f59e0b" : "#22c55e" }}>
                            {Number(log.confidence).toFixed(2)}
                          </span>
                        ) : "—"}
                      </td>
                      <td style={{ padding: "14px 16px", color: "#94a3b8" }}>{formatTime(log.timestamp)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <footer className="dash-footer" style={{ textAlign: "center", color: "#64748b", padding: "24px 0 10px 0", fontSize: "0.95rem", borderTop: "1px solid #1e293b", marginTop: "20px" }}>
        AI SIEM Dashboard &nbsp;·&nbsp; Enterprise Monitoring System
      </footer>
    </div>
  );
}

export default Dashboard;