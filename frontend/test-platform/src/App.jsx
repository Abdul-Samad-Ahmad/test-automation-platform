// import { useState } from 'react'
// import reactLogo from './assets/react.svg'
// import viteLogo from '/vite.svg'
// import './App.css'

// function App() {
//   const [count, setCount] = useState(0)

//   return (
//     <>
//       <div>
//         <a href="https://vite.dev" target="_blank">
//           <img src={viteLogo} className="logo" alt="Vite logo" />
//         </a>
//         <a href="https://react.dev" target="_blank">
//           <img src={reactLogo} className="logo react" alt="React logo" />
//         </a>
//       </div>
//       <h1>Vite + React</h1>
//       <div className="card">
//         <button onClick={() => setCount((count) => count + 1)}>
//           count is {count}
//         </button>
//         <p>
//           Edit <code>src/App.jsx</code> and save to test HMR
//         </p>
//       </div>
//       <p className="read-the-docs">
//         Click on the Vite and React logos to learn more
//       </p>
//     </>
//   )
// }

// export default App

import React, { useState, useEffect, useRef } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Play, Terminal, Activity, CheckCircle, Circle, AlertCircle, Cpu } from 'lucide-react';
import './App.css'; // Import the new CSS file

const WS_URL = 'ws://localhost:8000/ws/test-status';

// --- COMPONENT: Module Flow Status ---
const ModuleFlow = ({ modules }) => {
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
              {icon}
              <span className="module-name">{mod.name}</span>
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

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="log-console">
      <h3 className="console-header">
        <Terminal size={14} /> LIVE LOGS CONSOLE
      </h3>
      <div className="console-body">
        {logs.map((log, i) => (
          <div key={i} className={`log-line ${log.type.toLowerCase()}`}>
            <span className="timestamp">[{log.time}]</span>
            <span className="message">{log.message}</span>
          </div>
        ))}
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
  const [modules, setModules] = useState([
    { name: 'Login', status: 'pending' },
    { name: 'Dashboard', status: 'pending' },
    { name: 'Onboarding', status: 'pending' },
    { name: 'Add farmer updates', status: 'pending' },
  ]);

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

  const handleIncomingData = (data) => {
    if (data.type === 'LOG') {
      const message = data.payload?.message || '';
      const status = data.payload?.status || 'INFO';

      setLogs(prev => [
        ...prev,
        {
          time: new Date().toLocaleTimeString(),
          message,
          type: status,
        },
      ]);

      // (optional) keep your existing LOG-based heuristics if you like
      const lowerMsg = message.toLowerCase();
      if (
        lowerMsg.includes("login") &&
        (lowerMsg.includes("starting") || lowerMsg.includes("start"))
      ) {
        updateModuleStatus("Login", "running");
      }
      if (
        lowerMsg.includes("login") &&
        (lowerMsg.includes("passed") || lowerMsg.includes("success"))
      ) {
        updateModuleStatus("Login", "completed");
      }
      if (lowerMsg.includes("login") && lowerMsg.includes("failed")) {
        updateModuleStatus("Login", "failed");
      }

    } else if (data.type === 'METRIC') {
      setMetrics(prev => {
        const newMetrics = [...prev, data.payload];
        return newMetrics.slice(-20);
      });

    } else if (data.type === 'MODULE') {
      const moduleName = data.payload?.module;
      const status = data.payload?.status;
      const message = data.payload?.message || '';

      if (moduleName && status) {
        // 1) Update module status and also decide if anything is still running
        setModules(prev => {
          const updated = prev.map(m =>
            m.name.toLowerCase() === moduleName.toLowerCase()
              ? { ...m, status }
              : m
          );

          const anyRunning = updated.some(m => m.status === 'running');
          if (!anyRunning) {
            // No modules are running anymore -> show "Run Test" again
            setIsRunning(false);
          }

          return updated;
        });

        // 2) Log the module status change
        if (message) {
          setLogs(prev => [
            ...prev,
            {
              time: new Date().toLocaleTimeString(),
              message: `[${moduleName}] ${message}`,
              type: status.toUpperCase(),
            },
          ]);
        }
      }
    }
  };


  const handleRunTest = async () => {
    if (!apkUrl) {
      alert("Please enter a Google Drive URL first!");
      return;
    }
    setModules(prev => prev.map(m => ({ ...m, status: 'pending' }))); // reset

    setIsRunning(true);
    setIsDownloading(true);
    setLogs([]); // Clear old logs
    setMetrics([]); // Clear old metrics

    // 1. Show immediate feedback in UI logs
    handleIncomingData({
      type: 'LOG',
      payload: { message: "Initializing test request...", status: 'INFO' }
    });

    try {
      // 2. Send the URL to the Python Backend
      const response = await fetch('http://localhost:8000/start-test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: apkUrl }),
      });

      const data = await response.json();

      if (data.app_icon) {
        setAppIcon(data.app_icon);
      }

      if (data.app_name) {
        setAppTitle(data.app_name);
      }

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start test');
      }

      // 3. Backend accepted it
      handleIncomingData({
        type: 'LOG',
        payload: { message: `APK Downloaded at: ${data.apk_path}`, status: 'SUCCESS' }
      });

      // Note: The WebSocket will handle the rest of the updates (Installing, Testing, etc.)

    } catch (error) {
      console.error("Error starting test:", error);
      handleIncomingData({
        type: 'LOG',
        payload: { message: `Error: ${error.message}`, status: 'FAILED' }
      });
      setIsRunning(false); // Reset button state on error
    } finally {
      setIsDownloading(false);
    }
  };

  // Poll device status every 5s
  useEffect(() => {
    const checkDevice = async () => {
      try {
        const res = await fetch('http://localhost:8000/device-status');
        const data = await res.json();
        setIsDeviceConnected(!!data.connected);
      } catch (e) {
        setIsDeviceConnected(false);
      }
    };
    checkDevice();
    const id = setInterval(checkDevice, 5000);
    return () => clearInterval(id);
  }, []);
  // const simulateTest = () => {
  //   let tick = 0;
  //   const interval = setInterval(() => {
  //     tick++;
  //     const simMetric = {
  //       time: tick,
  //       cpu: 20 + Math.random() * 30 + (tick % 10) * 2,
  //       memory: 150 + Math.random() * 20 + tick
  //     };
  //     handleIncomingData({ type: 'METRIC', payload: simMetric });

  //     if (tick === 1) handleIncomingData({ type: 'LOG', payload: { message: "Downloading APK...", status: 'INFO' } });
  //     if (tick === 10) handleIncomingData({ type: 'LOG', payload: { message: "Starting Module: Authentication", status: 'INFO' } });
  //     if (tick === 25) handleIncomingData({ type: 'LOG', payload: { message: "Login Button Clicked", status: 'SUCCESS' } });
  //     if (tick === 40) handleIncomingData({ type: 'LOG', payload: { message: "Module Passed", status: 'SUCCESS' } });
  //     if (tick === 45) handleIncomingData({ type: 'LOG', payload: { message: "Starting Module: Dashboard", status: 'INFO' } });

  //     if (tick > 100) clearInterval(interval);
  //   }, 200);
  // };

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
            <span>{readyState === ReadyState.OPEN ? 'System Online' : 'Offline'}</span>
          </div>
        </div>
      </header>

      <div className="dashboard-grid">
        {/* Panel 1: Controls */}
        <div className="dashboard-card control-panel">
          <h2 className="card-title">Test Execution</h2>
          <div className="input-group">
            <input
              type="text"
              placeholder="Paste Google Drive Link (APK Source)"
              value={apkUrl}
              onChange={(e) => setApkUrl(e.target.value)}
              className="text-input"
            />
            <button
              onClick={handleRunTest}
              disabled={isRunning}
              className={`run-button ${isRunning ? 'disabled' : ''}`}
            >
              <Play size={18} fill="currentColor" />
              {isDownloading
                ? 'Downloading APK...'
                : (isRunning ? 'Testing...' : 'Run Test')}
              {isDownloading && <span className="loader" />}
            </button>
          </div>
        </div>

        {/* Panel 2: Module Flow */}
        <div className="grid-item-flow">
          <ModuleFlow modules={modules} />
        </div>

        {/* Panel 3: Live Metrics */}
        <div className="grid-item-chart">
          <MetricsChart data={metrics} />
        </div>

        {/* Panel 4: Logs */}
        <div className="grid-item-logs">
          <LogConsole logs={logs} />
        </div>
      </div>
    </div>
  );
}

export default App;