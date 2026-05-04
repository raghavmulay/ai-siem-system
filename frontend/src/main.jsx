import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import Dashboard from './App.jsx';
import Login from './Login.jsx';
import './index.css';

function Root() {
  const [role, setRole] = useState(localStorage.getItem("siem_role"));

  const handleLogin = (userRole) => setRole(userRole);

  const handleLogout = () => {
    localStorage.removeItem("siem_token");
    localStorage.removeItem("siem_role");
    setRole(null);
  };

  if (!role) return <Login onLogin={handleLogin} />;
  return <Dashboard role={role} onLogout={handleLogout} />;
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
