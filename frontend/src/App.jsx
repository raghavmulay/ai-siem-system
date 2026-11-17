import { useEffect, useState } from "react";
import {
  LineChart, Line, BarChart, Bar, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";

/* ═══════════════════════════════
   HELPERS
═══════════════════════════════ */
function fmt(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("en-IN", {
      day: "2-digit", month: "short",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false,
    });
  } catch { return String(ts); }
}

function topAttack(logs) {
  const freq = {};
  logs.forEach(l => {
    const t = l.attack_type;
    if (t && t !== "Normal" && t !== "Unknown" && t !== -1)
      freq[t] = (freq[t] || 0) + 1;
  });
  const e = Object.entries(freq).sort((a, b) => b[1] - a[1]);
  return e[0]?.[0] ?? "—";
}

const isAnomaly = l => l.anomaly === true || l.anomaly === -1;

/* ═══════════════════════════════
   SEVERITY CONFIG
═══════════════════════════════ */
const SEV = {
  CRITICAL: { color: "var(--color-critical)", bg: "rgba(255,56,56,0.08)"  },
  HIGH:     { color: "var(--color-high)",     bg: "rgba(255,107,53,0.08)" },
  MEDIUM:   { color: "var(--color-medium)",   bg: "rgba(255,170,0,0.08)"  },
  LOW:      { color: "var(--color-low)",      bg: "rgba(0,255,136,0.07)"  },
};
const sev = k => SEV[k] || SEV.LOW;

function Badge({ severity }) {
  const s = sev(severity);
  return (
    <span style={{
      display: "inline-block", padding: "2px 7px", borderRadius: "3px",
      fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.8px",
      textTransform: "uppercase",
      color: s.color, background: s.bg,
      border: `1px solid ${s.color}`,
      opacity: 0.9,
    }}>
      {severity}
    </span>
  );
}

/* ═══════════════════════════════
   CUSTOM CHART TOOLTIP
═══════════════════════════════ */
function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const isAnomKey = payload[0].dataKey === "anomaly";
  const val = payload[0].value;
  return (
    <div style={{
      background: "var(--bg-elevated)", border: "1px solid var(--border)",
      borderRadius: "4px", padding: "9px 13px",
      fontSize: "0.75rem", color: "var(--text-secondary)",
      boxShadow: "var(--shadow-lg)",
    }}>
      {isAnomKey ? (
        <>
          <div style={{ color: "var(--text-muted)", marginBottom: 3 }}>
            {payload[0].payload.timeLabel || label}
          </div>
          <div style={{ color: val === 1 ? "var(--color-critical)" : "var(--color-low)", fontWeight: 700 }}>
            {val === 1 ? "Anomaly" : "Normal"}
          </div>
        </>
      ) : (
        <>
          <div style={{ color: "var(--text-muted)", marginBottom: 3 }}>{label}</div>
          <div style={{ color: "var(--accent)", fontWeight: 700 }}>Count: {val}</div>
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════
   METRIC CARD
═══════════════════════════════ */
function MetricCard({ label, value, color }) {
  return (
    <div className="metric-card" style={{ borderLeftColor: color }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color }}>{value}</div>
    </div>
  );
}

/* ═══════════════════════════════
   THEME TOGGLE
═══════════════════════════════ */
function ThemeToggle({ dark, onToggle }) {
  return (
    <div className="theme-toggle" onClick={onToggle} title="Toggle theme">
      <span className="toggle-icon">{dark ? "🌙" : "☀️"}</span>
      <div className={`toggle-track ${dark ? "on" : ""}`}>
        <div className="toggle-thumb" />
      </div>
    </div>
  );
}

/* ═══════════════════════════════
   DISTRIBUTION CHART
   height grows with bar count so
   there is no dead space below
═══════════════════════════════ */
const BAR_H   = 32;   // px per bar
const CHART_MIN = 160; // minimum height px

function DistributionChart({ data }) {
  if (!data.length) return (
    <div className="empty-state">
      <span className="empty-icon">📊</span>
      <span className="empty-text">No attack data yet</span>
    </div>
  );

  // Sort ascending so largest bar is at top (horizontal layout reads top→bottom)
  const sorted = [...data].sort((a, b) => a.count - b.count);
  const chartH = Math.max(CHART_MIN, sorted.length * BAR_H + 40);

  // Pick bar colour by rank (top 3 = red gradient, rest = cyan)
  const maxCount = Math.max(...sorted.map(d => d.count));

  return (
    <div style={{ width: "100%", height: chartH }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 4, right: 48, bottom: 4, left: 90 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            axisLine={false} tickLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="type"
            width={86}
            tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
            axisLine={false} tickLine={false}
          />
          <Tooltip content={<ChartTip />} cursor={{ fill: "var(--bg-hover)" }} />
          <Bar dataKey="count" radius={[0, 3, 3, 0]} maxBarSize={22}>
            {sorted.map((entry, i) => {
              const ratio = entry.count / maxCount;
              const fill = ratio > 0.75
                ? "var(--color-critical)"
                : ratio > 0.4
                  ? "var(--color-medium)"
                  : "var(--accent)";
              return <Cell key={entry.type} fill={fill} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ═══════════════════════════════
   MAIN DASHBOARD
═══════════════════════════════ */
export default function Dashboard() {
  const [logs,         setLogs]         = useState([]);
  const [alerts,       setAlerts]       = useState([]);
  const [chains,       setChains]       = useState([]);
  const [lastRefresh,  setLastRefresh]  = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [errorMsg,     setErrorMsg]     = useState(null);
  const [clearing,     setClearing]     = useState(false);
  const [darkMode,     setDarkMode]     = useState(true);

  /* apply theme to <html> */
  useEffect(() => {
    document.documentElement.setAttribute(
      "data-theme", darkMode ? "dark" : "light"
    );
  }, [darkMode]);

  const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

  const fetchData = async () => {
    try {
      const [lr, ar, cr] = await Promise.all([
        fetch(`${API}/logs`),
        fetch(`${API}/alerts`),
        fetch(`${API}/attack-chains`),
      ]);
      if (!lr.ok || !ar.ok) throw new Error();
      const [ld, ad, cd] = await Promise.all([
        lr.json(), ar.json(), cr.ok ? cr.json() : { chains: [] },
      ]);
      setLogs(ld);
      setAlerts(ad);
      setChains(cd.chains || []);
      setLastRefresh(new Date());
      setErrorMsg(null);
    } catch {
      setErrorMsg("Cannot reach backend — retrying…");
    } finally {
      setLoading(false);
    }
  };

  const clearAll = async () => {
    if (!window.confirm("Clear all logs and alerts?")) return;
    setClearing(true);
    try {
      await fetch(`${API}/clear`, { method: "DELETE" });
      setLogs([]); setAlerts([]); setChains([]);
    } finally { setClearing(false); }
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 3000);
    return () => clearInterval(id);
  }, []);

  /* ── Derived values ── */
  const displayLogs  = logs.slice(0, 100);
  const total        = logs.length;
  const anomCount    = logs.filter(isAnomaly).length;
  const anomRate     = total > 0 ? ((anomCount / total) * 100).toFixed(1) : "0.0";
  const highCount    = alerts.filter(a => a.severity === "HIGH" || a.severity === "CRITICAL").length;
  const critCount    = alerts.filter(a => a.severity === "CRITICAL").length;
  const top          = topAttack(logs);

  let sysStatus = "normal";
  if (critCount >= 1 || highCount >= 3)                   sysStatus = "critical";
  else if (parseFloat(anomRate) > 20 || highCount >= 1)   sysStatus = "warning";

  /* ── Trend chart data (last 50) ── */
  const trendData = logs.slice(-50).map((l, i) => ({
    index: i + 1,
    anomaly: isAnomaly(l) ? 1 : 0,
    timeLabel: new Date(l.timestamp).toLocaleTimeString("en-IN", {
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    }),
  }));

  /* ── Attack distribution (top 12) ── */
  const freq = {};
  logs.forEach(l => {
    const t = l.attack_type;
    if (t && t !== "Normal" && t !== "Unknown" && t !== -1)
      freq[t] = (freq[t] || 0) + 1;
  });
  const distData = Object.entries(freq)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 12);

  const recentAlerts = alerts.slice(0, 6);

  /* ════════════════════════════════
     RENDER
  ════════════════════════════════ */
  return (
    <div className="dashboard">

      {/* ── HEADER ── */}
      <header className="dash-header">
        <div className="header-left">
          <span className="logo-icon">⬡</span>
          <div>
            <div className="logo-text">AI SIEM</div>
            <div className="header-sub">Security Information &amp; Event Management</div>
          </div>
        </div>

        <div className="header-right">
          {/* Theme toggle */}
          <ThemeToggle dark={darkMode} onToggle={() => setDarkMode(d => !d)} />

          <button
            onClick={clearAll}
            disabled={clearing}
            style={{ color: "var(--color-critical)", borderColor: "var(--color-critical)" }}
          >
            {clearing ? "Clearing…" : "✕ Clear"}
          </button>

          <div className="status-indicator">
            <span className="live-dot" />
            <span className="live-label">Live</span>
          </div>

          <span className="time-stamp">
            {loading ? "Connecting…"
              : lastRefresh
                ? `${lastRefresh.toLocaleTimeString("en-IN", { hour12: false })}`
                : "Waiting…"}
          </span>
        </div>
      </header>

      {/* ── STATUS BANNER ── */}
      <div className={`status-banner ${sysStatus}`}>
        {sysStatus === "critical"
          ? "● CRITICAL — Active threat detected"
          : sysStatus === "warning"
            ? "● WARNING — Elevated anomaly rate"
            : "● All systems nominal"}
      </div>

      {/* ── ERROR ── */}
      {errorMsg && (
        <div style={{
          margin: "14px 40px 0",
          padding: "10px 14px",
          background: "color-mix(in srgb, var(--color-critical) 8%, transparent)",
          border: "1px solid var(--color-critical)",
          borderRadius: "4px",
          color: "var(--color-critical)",
          fontSize: "0.75rem",
        }}>
          ⚠ {errorMsg}
        </div>
      )}

      {/* ── CONTENT ── */}
      <div className="dashboard-content">

        {/* 1 ── OVERVIEW ── */}
        <div className="section">
          <div className="section-title">Overview</div>
          <div className="metrics-grid">
            <MetricCard label="Total Logs"   value={total}            color="var(--accent)"          />
            <MetricCard label="Anomaly Rate" value={`${anomRate}%`}   color="var(--color-medium)"    />
            <MetricCard label="High Alerts"  value={highCount}        color="var(--color-critical)"  />
            <MetricCard label="Top Attack"   value={top}              color="var(--color-low)"       />
          </div>
        </div>

        {/* 2 ── ALERTS + DISTRIBUTION (side by side, each auto-height) ── */}
        <div className="two-col">

          {/* Alerts */}
          <div className="section" style={{ margin: 0 }}>
            <div className="section-header-row">
              <div className="section-title">Recent Alerts</div>
              <span className="badge-count">{recentAlerts.length} shown</span>
            </div>

            {recentAlerts.length === 0 ? (
              <div className="empty-state">
                <span className="empty-icon">✓</span>
                <span className="empty-text">No anomalies detected</span>
              </div>
            ) : (
              <div className="alerts-list">
                {recentAlerts.map((a, i) => {
                  const s = sev(a.severity);
                  const msg = a.reason || a.message
                    || (a.attack_type
                      ? `${a.attack_type} — conf ${Number(a.confidence).toFixed(2)}`
                      : "Anomaly detected");
                  return (
                    <div
                      key={a._id || i}
                      className="alert-row fade-in"
                      style={{ borderLeftColor: s.color, background: s.bg }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: 5, flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap" }}>
                          <Badge severity={a.severity} />
                          {a.attack_type && (
                            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                              {a.attack_type}
                            </span>
                          )}
                        </div>
                        <span className="alert-message">{msg}</span>
                      </div>
                      <span className="alert-time">{fmt(a.timestamp)}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Attack Distribution */}
          <div className="section" style={{ margin: 0 }}>
            <div className="section-title">Attack Distribution</div>
            <DistributionChart data={distData} />
          </div>

        </div>{/* /two-col */}

        {/* 3 ── ANOMALY TREND ── */}
        <div className="section">
          <div className="section-header-row">
            <div className="section-title">Anomaly Trend</div>
            <span className="badge-count">Last 50 events</span>
          </div>
          <div className="section-desc">Red dot = anomaly · Green dot = normal</div>

          {trendData.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">📈</span>
              <span className="empty-text">Waiting for data…</span>
            </div>
          ) : (
            <div style={{ width: "100%", height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 6, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis
                    dataKey="timeLabel"
                    tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                    axisLine={false} tickLine={false}
                    minTickGap={40}
                  />
                  <YAxis
                    ticks={[0, 1]}
                    tickFormatter={v => v === 1 ? "Anomaly" : "Normal"}
                    tick={{ fill: "var(--text-muted)", fontSize: 10 }}
                    width={62}
                    axisLine={false} tickLine={false}
                    domain={[-0.1, 1.1]}
                  />
                  <Tooltip content={<ChartTip />} />
                  <ReferenceLine y={1} stroke="var(--color-critical)" strokeDasharray="4 2" strokeOpacity={0.2} />
                  <Line
                    type="monotone" dataKey="anomaly"
                    stroke="var(--border-light)" strokeWidth={1}
                    dot={({ cx, cy, payload }) => (
                      <circle
                        key={`d-${payload.index}`}
                        cx={cx} cy={cy} r={3.5}
                        fill={payload.anomaly === 1 ? "var(--color-critical)" : "var(--color-low)"}
                        stroke="none"
                      />
                    )}
                    activeDot={{ r: 5, stroke: "var(--text-primary)", strokeWidth: 1.5 }}
                    isAnimationActive animationDuration={600}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* 4 ── ATTACK CHAINS ── */}
        <div className="section">
          <div className="section-header-row">
            <div className="section-title">Attack Chains</div>
            <span className="badge-count">
              {chains.length} pattern{chains.length !== 1 ? "s" : ""} · last 10 min
            </span>
          </div>

          {chains.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">🔗</span>
              <span className="empty-text">No coordinated patterns detected</span>
            </div>
          ) : (
            <div className="alerts-list">
              {chains.map((c, i) => {
                const s = sev(c.severity);
                return (
                  <div key={i} className="alert-row" style={{ borderLeftColor: s.color, background: s.bg }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7, flexWrap: "wrap" }}>
                        <Badge severity={c.severity} />
                        <span style={{ color: "var(--text-primary)", fontWeight: 700, fontSize: "0.82rem" }}>
                          {c.pattern}
                        </span>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.68rem" }}>
                          {c.log_count} events
                        </span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 5, flexWrap: "wrap" }}>
                        {c.steps.map((step, si) => (
                          <span key={si} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                            <span style={{
                              padding: "2px 7px", borderRadius: "3px",
                              fontSize: "0.62rem", fontWeight: 700,
                              textTransform: "uppercase", letterSpacing: "0.5px",
                              color: "var(--accent)",
                              background: "color-mix(in srgb, var(--accent) 10%, transparent)",
                              border: "1px solid color-mix(in srgb, var(--accent) 30%, transparent)",
                            }}>{step}</span>
                            {si < c.steps.length - 1 && (
                              <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>→</span>
                            )}
                          </span>
                        ))}
                      </div>
                      {c.first_seen && (
                        <div style={{ marginTop: 5, color: "var(--text-muted)", fontSize: "0.65rem" }}>
                          {fmt(c.first_seen)} → {fmt(c.last_seen)}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 5 ── LOG TABLE ── */}
        <div className="section">
          <div className="section-header-row">
            <div className="section-title">Log Entries</div>
            {displayLogs.length > 0 && (
              <span className="badge-count">Latest {displayLogs.length}</span>
            )}
          </div>

          {displayLogs.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">▤</span>
              <span className="empty-text">No log entries yet</span>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="logs-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Status</th>
                    <th>Attack Type</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {displayLogs.map((log, idx) => {
                    const anom = isAnomaly(log);
                    const sv   = log.severity || (anom ? "HIGH" : "LOW");
                    const conf = log.confidence != null ? Number(log.confidence) : null;
                    const confColor = conf == null ? "var(--text-muted)"
                      : conf > 0.9 ? "var(--color-critical)"
                      : conf > 0.6 ? "var(--color-medium)"
                      : "var(--color-low)";
                    return (
                      <tr key={log._id || idx} className={idx === 0 ? "log-row-anim" : ""}>
                        <td style={{ color: "var(--text-muted)" }}>#{idx + 1}</td>
                        <td>
                          <span style={{
                            display: "inline-block", padding: "2px 7px", borderRadius: "3px",
                            fontSize: "0.6rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px",
                            color:      anom ? "var(--color-critical)" : "var(--color-low)",
                            background: anom ? "color-mix(in srgb, var(--color-critical) 10%, transparent)"
                                             : "color-mix(in srgb, var(--color-low) 8%, transparent)",
                            border: `1px solid ${anom ? "var(--color-critical)" : "var(--color-low)"}`,
                            opacity: 0.9,
                          }}>
                            {anom ? "Anomaly" : "Normal"}
                          </span>
                        </td>
                        <td style={{ color: "var(--text-secondary)" }}>{log.attack_type || "—"}</td>
                        <td><Badge severity={sv} /></td>
                        <td style={{ color: confColor, fontVariantNumeric: "tabular-nums" }}>
                          {conf != null ? conf.toFixed(2) : "—"}
                        </td>
                        <td style={{ color: "var(--text-muted)" }}>{fmt(log.timestamp)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>{/* /dashboard-content */}

      <footer style={{
        textAlign: "center",
        padding: "18px 40px",
        borderTop: "1px solid var(--border)",
        color: "var(--text-muted)",
        fontSize: "0.65rem",
        letterSpacing: "1px",
        textTransform: "uppercase",
      }}>
        AI SIEM &nbsp;·&nbsp; Enterprise Security Monitoring
      </footer>

    </div>
  );
}
