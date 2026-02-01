import React, { useState, useEffect, useRef } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Play, Terminal, Activity, CheckCircle, Circle, AlertCircle, Cpu } from 'lucide-react';
import './App.css'; // Import the new CSS file

const WS_URL = 'ws://localhost:8000/ws/test-status';
const API_URL = 'http://localhost:8000';

// --- CONFIGURATION: App Variants & Modules ---
const APP_VARIANTS = {
  FARMER: {
    id: "regular_farmer",
    label: "Krishivaas Farmer (Regular)",
    modules: [
      { name: 'Login', path: 'tests/test_cases/regular_farmer_test_cases/test_login_pytest.py' },
      { name: 'Dashboard', path: 'tests/farmer/test_dashboard.py' },
      { name: 'Add Updates', path: 'tests/farmer/test_updates.py' },
    ]
  },
  CLIENT: {
    id: "regular_client",
    label: "Krishivaas Client (Regular)",
    modules: [
      { name: 'Login', path: 'tests/test_cases/regular_client_test_cases/test_login_pytest.py' },
      { name: 'Marketplace', path: 'tests/client/test_marketplace.py' },
      { name: 'Cart', path: 'tests/client/test_cart.py' },
    ]
  },
  STATE_FARMER: {
    id: "state_farmer",
    label: "State Farmer App",
    modules: [
      { name: 'Login', path: 'tests/state_farmer/test_login.py' },
      { name: 'Schemes', path: 'tests/state_farmer/test_schemes.py' },
    ]
  },
  STATE_CLIENT: {
    id: "state_client",
    label: "State Client App",
    modules: [
      { name: 'Login', path: 'tests/state_client_test_cases/test_login.py' },
      { name: 'Tenders', path: 'tests/state_client/test_tenders.py' },
    ]
  }
};

// --- COMPONENT: Module Flow Status ---
const ModuleFlow = ({ modules, isRunning, onToggleModule }) => {
  return (
    <div className="dashboard-card module-card">
      <h3 className="card-title">
        <Activity size={20} className="icon-blue" /> Module Flow Status
      </h3>
      <div className="module-list">
        {modules.map((mod, idx) => {
          let statusClass = "status-pending";
          let icon = <Circle size={16} />;

          if (mod.status === 'completed') {
            statusClass = "status-success";
            icon = <CheckCircle size={16} />;
          } else if (mod.status === 'running') {
            statusClass = "status-running";
            icon = <Activity size={16} className="icon-pulse" />;
          } else if (mod.status === 'failed') {
            statusClass = "status-failed";
            icon = <AlertCircle size={16} />;
          }

          return (
            <div key={idx} className={`module-item ${statusClass}`}>
              {/* Show checkbox only if NOT running */}
              {!isRunning ? (
                <input
                  type="checkbox"
                  checked={!!mod.isSelected}
                  onChange={() => onToggleModule(idx)}
                  className="mr-2 cursor-pointer"
                  style={{ marginRight: '8px' }}
                />
              ) : (
                // Show status icon if running or if selected
                mod.isSelected ? icon : <Circle size={16} className="text-gray-500" />
              )}

              <span className={`module-name ${!mod.isSelected && !isRunning ? 'opacity-50' : ''}`}>
                {mod.name}
              </span>
              {mod.status === 'running' && <span className="status-label">Testing...</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// --- COMPONENT: Live Metrics Chart ---
const MetricsChart = ({ data }) => {
  return (
    <div className="dashboard-card chart-card">
      <h3 className="card-title">
        <Cpu size={20} className="icon-purple" /> Live Profiler Metrics
      </h3>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" hide />
            <YAxis yAxisId="left" stroke="#94a3b8" label={{ value: 'CPU %', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
            <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" label={{ value: 'MB', angle: 90, position: 'insideRight' }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#e2e8f0' }}
              itemStyle={{ color: '#e2e8f0' }}
            />
            <Line yAxisId="left" type="monotone" dataKey="cpu" stroke="#38bdf8" strokeWidth={2} dot={false} animationDuration={300} />
            <Line yAxisId="right" type="monotone" dataKey="memory" stroke="#c084fc" strokeWidth={2} dot={false} animationDuration={300} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// --- COMPONENT: Log Console ---
const LogConsole = ({ logs }) => {
  const endRef = useRef(null);
  const [searchTerm, setSearchTerm] = useState('');
  const filteredLogs = logs.filter((log) => {
    if (!searchTerm) return true;
    const q = searchTerm.toLowerCase();
    return (
      log.message.toLowerCase().includes(q) ||
      log.type.toLowerCase().includes(q) ||
      String(log.time).toLowerCase().includes(q)
    );
  });

  const normalizedSearch = searchTerm.toLowerCase().trim();

  const matchesSearch = (log) => {
    if (!normalizedSearch) return false;
    return (
      log.message.toLowerCase().includes(normalizedSearch) ||
      log.type.toLowerCase().includes(normalizedSearch) ||
      String(log.time).toLowerCase().includes(normalizedSearch)
    );
  };

  return (
    <div className="log-console">
      <div className="console-header-row">
        <h3 className="console-header">
          <Terminal size={14} /> LIVE LOGS CONSOLE
        </h3>
        {/* Search bar */}
        <div className="log-search">
          <input
            type="text"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="text-input"
          />
        </div>
      </div>
      <div className="console-body">
        {logs.map((log, i) => {
          const isMatch = matchesSearch(log);
          return (
            <div
              key={i}
              className={`log-line ${log.type.toLowerCase()} ${isMatch ? 'log-line-highlight' : ''
                }`}
            >
              <span className="timestamp">[{log.time}]</span>
              <span className="message">{log.message}</span>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
};

// --- MAIN APP COMPONENT ---
function App() {
  const [apkUrl, setApkUrl] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [appIcon, setAppIcon] = useState(null);
  const [appTitle, setAppTitle] = useState('');
  const [isDeviceConnected, setIsDeviceConnected] = useState(false);
  const [selectedAppKey, setSelectedAppKey] = useState('FARMER');
  // Initialize modules based on default selection
  const [modules, setModules] = useState(() => {
    return APP_VARIANTS['FARMER'].modules.map(m => ({
      ...m,
      status: 'pending',
      isSelected: true
    }));
  });

  const [existingApks, setExistingApks] = useState([]);
  const [selectedApk, setSelectedApk] = useState('');
  const reportWindowRef = useRef(null);
  const [hasOpenedReport, setHasOpenedReport] = useState(false);

  // --- Update modules when App Type changes ---
  useEffect(() => {
    if (!isRunning) {
      setModules(APP_VARIANTS[selectedAppKey].modules.map(m => ({
        ...m,
        status: 'pending',
        isSelected: true
      })));
    }
  }, [selectedAppKey, isRunning]);

  const toggleModuleSelection = (index) => {
    if (isRunning) return;
    setModules(prev => prev.map((m, i) => i === index ? { ...m, isSelected: !m.isSelected } : m));
  };

  const updateModuleStatus = (moduleName, newStatus) => {
    setModules(prev =>
      prev.map(m =>
        m.name.toLowerCase() === moduleName.toLowerCase()
          ? { ...m, status: newStatus }
          : m
      )
    );
  };

  const { lastJsonMessage, sendMessage, readyState } = useWebSocket(WS_URL, {
    shouldReconnect: () => true,
    onMessage: (event) => {
      const data = JSON.parse(event.data);
      handleIncomingData(data);
    }
  });

  const openOrNavigateReport = (url) => {
    if (!url || hasOpenedReport) return;
    window.open(url, '_blank', 'noopener,noreferrer');
    setHasOpenedReport(true);
  };

  const handleIncomingData = (data) => {
    if (data.type === 'LOG') {
      const { message, status } = data.payload || {};
      setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), message, type: status || 'INFO' }]);

    } else if (data.type === 'MODULE') {
      const { module, status, message } = data.payload || {};
      if (module && status) {
        setModules(prev => {
          const updated = prev.map(m =>
            m.name.toLowerCase() === module.toLowerCase() ? { ...m, status } : m
          );
          if (!updated.some(m => m.status === 'running')) setIsRunning(false);
          return updated;
        });

        if (message) {
          setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), message: `[${module}] ${message}`, type: status.toUpperCase() }]);
        }
      }
    } else if (data.type === 'RUN_COMPLETE') {
      if (!hasOpenedReport && data.payload?.report_url) {
        window.open(data.payload.report_url, '_blank', 'noopener,noreferrer');
        setHasOpenedReport(true);
      }
    }
  };

const handleRunTest = async () => {
    if (!apkUrl && !selectedApk) {
      alert("Please enter a Google Drive URL or select an existing APK!");
      return;
    }

    const testsToRun = modules
      .filter(m => m.isSelected)
      .map(m => ({ name: m.name, path: m.path }));

    if (testsToRun.length === 0) {
      alert("Please select at least one module to run.");
      return;
    }

    setHasOpenedReport(false);
    setModules(prev => prev.map(m => ({ ...m, status: 'pending' })));
    setIsRunning(true);
    setIsDownloading(!!apkUrl);
    setLogs([]); 

    // --- NEW: Add initial log ---
    const appLabel = APP_VARIANTS[selectedAppKey].label;
    handleIncomingData({
      type: 'LOG',
      payload: { 
        message: `Initializing ${appLabel} test with ${testsToRun.length} modules...`, 
        status: 'INFO' 
      }
    });

    try {
      // --- NEW: Send app_type in payload ---
      const payload = {
        tests_to_run: testsToRun,
        app_type: APP_VARIANTS[selectedAppKey].id 
      };

      let endpoint = selectedApk ? '/start-test-existing' : '/start-test';
      let body = selectedApk 
        ? { ...payload, apk_name: selectedApk } 
        : { ...payload, url: apkUrl };

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (data.app_icon) setAppIcon(data.app_icon);
      if (data.app_name) setAppTitle(data.app_name);

      if (!response.ok) throw new Error(data.detail || 'Failed to start test');

      handleIncomingData({
        type: 'LOG',
        payload: { message: `Backend accepted job. APK Path: ${data.apk_path}`, status: 'SUCCESS' }
      });

    } catch (error) {
      console.error("Error starting test:", error);
      handleIncomingData({
        type: 'LOG',
        payload: { message: `Error: ${error.message}`, status: 'FAILED' }
      });
      setIsRunning(false);
    } finally {
      setIsDownloading(false);
    }
  };

const handleStopTest = async () => {
    try {
      await fetch(`${API_URL}/stop-test`, { method: 'POST' });
    } catch (e) { console.error(e); }
    setIsRunning(false);
    setIsDownloading(false);
    handleIncomingData({ type: 'LOG', payload: { message: 'Test stopped by user.', status: 'FAILED' } });
  };

// Poll device & Load APKs
  useEffect(() => {
    const checkDevice = async () => {
      try {
        const res = await fetch(`${API_URL}/device-status`);
        const data = await res.json();
        setIsDeviceConnected(!!data.connected);
      } catch (e) { setIsDeviceConnected(false); }
    };
    
    const loadApks = async () => {
      try {
        const res = await fetch(`${API_URL}/api/apk-list`);
        const data = await res.json();
        setExistingApks(data.apks || []);
      } catch (e) {}
    };

    loadApks();
    checkDevice();
    const id = setInterval(checkDevice, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        {appIcon ? (
          <div className="app-header-left">
            <img
              src={appIcon}
              alt="App Logo"
              className="app-logo"
            />
            <h1>{appTitle || 'Android App'}</h1>
          </div>
        ) : (
          // Fallback placeholder if no icon yet
          <div className="w-16 h-16 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-500">
            {/* <span className="text-xs">No Icon</span> */}
          </div>
        )}
        <div>
          <h1 className="brand-title">TAP / Android</h1>
          <p className="brand-subtitle">Test Automation Platform • Live Profiler</p>
        </div>
        <div>
          <div className="system-status">
            <div className={`status-dot ${isDeviceConnected ? 'online' : 'offline'}`}></div>
            <span>{isDeviceConnected ? 'Device Connected' : 'No Device'}</span>
          </div>
          <div className="system-status">
            <div className={`status-dot ${readyState === ReadyState.OPEN ? 'online' : 'offline'}`}></div>
            <span>{readyState === ReadyState.OPEN ? 'Server Connected' : 'Offline'}</span>
          </div>
        </div>
      </header>

      <div className="dashboard-grid">
        {/* Panel 1: Controls */}
        <div className="dashboard-card control-panel">
          <h2 className="card-title">Test Execution</h2>
          {/* App Selector */}
          <div className="input-group mb-4">
            <label className="input-label">Select Application Scope</label>
            <div className="select-wrapper">
              <select
                className="text-input"
                value={selectedAppKey}
                onChange={(e) => setSelectedAppKey(e.target.value)}
                disabled={isRunning}
              >
                {Object.entries(APP_VARIANTS).map(([key, config]) => (
                  <option key={key} value={key}>{config.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="input-group">
            <label className="input-label">APK Source (Drive URL)</label>
            <input
              type="text"
              placeholder="https://drive.google.com/..."
              value={apkUrl}
              onChange={(e) => { setApkUrl(e.target.value); if (e.target.value) setSelectedApk(''); }}
              className="text-input"
              disabled={isRunning || !!selectedApk}
            />
          </div>

          <div className="input-group mt-2">
             <label className="input-label">OR Select Existing APK</label>
             <select
              className="text-input"
              value={selectedApk}
              onChange={(e) => { setSelectedApk(e.target.value); if (e.target.value) setApkUrl(''); }}
              disabled={isRunning || !!apkUrl}
            >
              <option value="">-- Select from Server --</option>
              {existingApks.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>

          <div className="action-row mt-4">
            <button
              onClick={handleRunTest}
              disabled={isRunning}
              className={`run-button ${isRunning ? 'disabled' : ''}`}
            >
              <Play size={18} fill="currentColor" />
              {isDownloading ? 'Downloading...' : (isRunning ? 'Running Tests...' : 'Start Automation')}
            </button>
            
            {isRunning && (
              <button onClick={handleStopTest} className="run-button stop-button ml-2">
                Stop
              </button>
            )}
          </div>
        </div>

        {/* Panel 2: Module Flow */}
        <div className="grid-item-flow">
          <ModuleFlow
            modules={modules}
            isRunning={isRunning}
            onToggleModule={toggleModuleSelection}
          />
        </div>

        {/* Panel 3: Logs */}
        <div className="grid-item-logs">
          <LogConsole logs={logs} />
        </div>
      </div>
    </div>
  );
}

export default App;