import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, 
  History, 
  Upload, 
  Settings, 
  Database,
  ArrowUpRight, 
  ArrowDownRight, 
  CheckCircle2,
  Info
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

import TransactionsTable from './components/TransactionsTable';
import TransactionsView from './components/TransactionsView';
import SettingsView from './components/SettingsView';
import CatalogueView from './components/CatalogueView';
import SankeyChart from './components/SankeyChart';

const API_BASE = 'http://localhost:8000';
const COLORS = ['#ff4b4b', '#00d4ff', '#ffaa00', '#2ecc71', '#a55eea', '#4b7bec'];

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth() + 1);
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState({ total_amount: 0, transaction_count: 0, monthly_income: 0, monthly_expense: 0, monthly_savings: 0, income_delta: 0, expense_delta: 0, savings_delta: 0 });
  const [pendingCount, setPendingCount] = useState(0);
  const [categories, setCategories] = useState([]);
  const [dailyData, setDailyData] = useState([]);
  const [categoryData, setCategoryData] = useState([]);
  const [flowData, setFlowData] = useState({ nodes: [], links: [] });
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState(1);
  const [pendingFile, setPendingFile] = useState(null);

  useEffect(() => {
    fetchStats();
    fetchTransactions();
    fetchProfiles();
    fetchCategories();
  }, [currentMonth, currentYear, selectedCategories]);

  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API_BASE}/categories/`);
      setCategories(res.data);
    } catch (err) {
      console.error("Error fetching categories:", err);
    }
  };

  const handleUpdateTransaction = async (txId, data) => {
    try {
      await axios.patch(`${API_BASE}/transactions/${txId}`, data);
      fetchTransactions();
      fetchStats();
    } catch (err) {
      console.error("Update error:", err);
    }
  };

  const fetchProfiles = async () => {
    try {
      const res = await axios.get(`${API_BASE}/profiles/`);
      setProfiles(res.data);
      const active = res.data.find(p => p.is_active);
      if (active) setSelectedProfileId(active.id);
    } catch (err) {
      console.error("Error fetching profiles:", err);
    }
  };

  const fetchStats = async () => {
    try {
      const params = { month: currentMonth, year: currentYear };
      const [summary, daily, cats_stats, flow] = await Promise.all([
        axios.get(`${API_BASE}/transactions/stats/summary`, { params }),
        axios.get(`${API_BASE}/transactions/stats/daily`, { params }),
        axios.get(`${API_BASE}/transactions/stats/categories`, { params }),
        axios.get(`${API_BASE}/transactions/stats/flow`, { params })
      ]);
      setStats(summary.data);
      setDailyData(daily.data);
      setCategoryData(cats_stats.data);
      setFlowData(flow.data);
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  };

  const fetchTransactions = async () => {
    try {
      const params = {};
      if (selectedCategories.length > 0) params.category_ids = selectedCategories.join(',');
      const res = await axios.get(`${API_BASE}/transactions/`, { params });
      setTransactions(res.data);
      // Count pending
      const pending = res.data.filter(t => t.status === 'pending').length;
      setPendingCount(pending);
    } catch (err) {
      console.error("Error fetching transactions:", err);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPendingFile(file);
    setIsUploading(true);
    setUploadStatus({ status: 'ANALYZING', progress: 0.1, logs: ["🔍 Analisi preliminare del file..."] });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('bank_profile_id', selectedProfileId);

    try {
      const res = await axios.post(`${API_BASE}/upload/analyze`, formData);
      setAnalysisResult(res.data);  // includes _file_path
      setIsUploading(false);
      setUploadStatus(null);
    } catch (err) {
      console.error("Analysis error:", err);
      setIsUploading(false);
    }
  };

  const startIngestion = async () => {
    if (!analysisResult?._file_path) return;
    setIsUploading(true);
    setUploadStatus({ status: 'PROCESSING', progress: 0.1, logs: ["🚀 Avvio processo di ingestione..."] });

    const formData = new FormData();
    formData.append('file_path', analysisResult._file_path);
    formData.append('bank_profile_id', selectedProfileId);

    try {
      const res = await axios.post(`${API_BASE}/upload/confirm`, formData);
      pollStatus(res.data.task_id);
    } catch (err) {
      console.error("Ingestion error:", err);
      setIsUploading(false);
    }
  };

  const pollStatus = (taskId) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/upload/status/${taskId}`);
        setUploadStatus(res.data);
        if (res.data.status === 'SUCCESS' || res.data.status === 'FAILURE') {
          clearInterval(interval);
          if (res.data.status === 'SUCCESS') {
            fetchStats();
            fetchTransactions();
            setTimeout(() => {
              setIsUploading(false);
              setAnalysisResult(null);
              setPendingFile(null);
            }, 2000);
          }
        }
      } catch (err) {
        clearInterval(interval);
        setIsUploading(false);
      }
    }, 1000);
  };

  return (
    <div className="flex">
      {/* Streamlit-like Sidebar */}
      <aside className="st-sidebar">
        <h1 className="text-xl font-bold mb-8 flex items-center gap-2">
          <Database className="text-[#ff4b4b]" size={24} /> AI Personal BI
        </h1>

        <div className="st-button-radio">
          <div 
            className={`st-radio-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard size={18} /> Dashboard
          </div>
          <div 
            className={`st-radio-item ${activeTab === 'transactions' ? 'active' : ''}`}
            onClick={() => setActiveTab('transactions')}
          >
            <History size={18} /> Data Explorer
          </div>
          <div 
            className={`st-radio-item ${activeTab === 'import' ? 'active' : ''}`}
            onClick={() => setActiveTab('import')}
          >
            <Upload size={18} /> Import Data
          </div>
          <div 
            className={`st-radio-item ${activeTab === 'catalogue' ? 'active' : ''}`}
            onClick={() => setActiveTab('catalogue')}
          >
            <Database size={18} /> Merchant Catalogue
          </div>
          <div 
            className={`st-radio-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <Settings size={18} /> Settings
          </div>
        </div>

        <div className="mt-8 border-t border-[#30363d] pt-8">
          <h3 className="text-xs uppercase font-bold mb-4 tracking-wider">Filters</h3>
          <div className="flex flex-col gap-4">
            <div>
              <label className="text-sm block mb-2">Select Year</label>
              <select 
                className="st-select" 
                value={currentYear} 
                onChange={(e) => setCurrentYear(parseInt(e.target.value))}
              >
                {[2023, 2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm block mb-2">Select Month</label>
              <select 
                className="st-select"
                value={currentMonth}
                onChange={(e) => setCurrentMonth(parseInt(e.target.value))}
              >
                {["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"].map((m, i) => (
                  <option key={m} value={i + 1}>{m}</option>
                ))}
              </select>
            </div>

            {/* Category multiselect */}
            {categories.length > 0 && (
              <div>
                <label className="text-sm block mb-2">Filter Categories</label>
                <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
                  {categories.map(cat => (
                    <label key={cat.id} className="flex items-center gap-2 text-sm cursor-pointer hover:text-white text-slate-400 transition-colors">
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(cat.id)}
                        onChange={(e) => {
                          setSelectedCategories(prev =>
                            e.target.checked
                              ? [...prev, cat.id]
                              : prev.filter(id => id !== cat.id)
                          );
                        }}
                        className="accent-[#ff4b4b] w-3.5 h-3.5"
                      />
                      {cat.name}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick metric */}
        <div className="mt-6 pt-6 border-t border-[#30363d]">
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Pending classification</span>
            <span className={`text-sm font-bold ${pendingCount > 0 ? 'text-yellow-400' : 'text-emerald-400'}`}>
              {pendingCount}
            </span>
          </div>
        </div>

        <div className="mt-auto pt-8 text-xs text-slate-500">
          Made with ❤️ for Personal BI
        </div>
      </aside>

      {/* Main Area */}
      <main className="st-main">
        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' && (
            <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h1 className="st-heading">Financial Dashboard</h1>
              
              {/* Metrics Row */}
              <div className="grid grid-cols-4 gap-6 mb-12">
                <div className="st-metric-card">
                  <span className="st-metric-label">Total Balance</span>
                  <span className="st-metric-value">€{stats.total_amount.toLocaleString('it-IT', {minimumFractionDigits: 2})}</span>
                </div>
                <div className="st-metric-card">
                  <span className="st-metric-label">Monthly Income</span>
                  <span className="st-metric-value">€{stats.monthly_income.toLocaleString('it-IT', {minimumFractionDigits: 2})}</span>
                  {stats.income_delta !== undefined && (
                    <span className={`st-metric-delta ${stats.income_delta >= 0 ? 'up' : 'down'}`}>
                      {stats.income_delta >= 0 ? '↑' : '↓'} {Math.abs(stats.income_delta).toFixed(1)}% vs prev. month
                    </span>
                  )}
                </div>
                <div className="st-metric-card">
                  <span className="st-metric-label">Monthly Spending</span>
                  <span className="st-metric-value text-[#ff4b4b]">€{stats.monthly_expense.toLocaleString('it-IT', {minimumFractionDigits: 2})}</span>
                  {stats.expense_delta !== undefined && (
                    <span className={`st-metric-delta ${stats.expense_delta <= 0 ? 'up' : 'down'}`}>
                      {stats.expense_delta >= 0 ? '↑' : '↓'} {Math.abs(stats.expense_delta).toFixed(1)}% vs prev. month
                    </span>
                  )}
                </div>
                <div className="st-metric-card">
                  <span className="st-metric-label">Monthly Savings</span>
                  <span className="st-metric-value text-[#2ecc71]">€{stats.monthly_savings.toLocaleString('it-IT', {minimumFractionDigits: 2})}</span>
                  {stats.savings_delta !== undefined && (
                    <span className={`st-metric-delta ${stats.savings_delta >= 0 ? 'up' : 'down'}`}>
                      {stats.savings_delta >= 0 ? '↑' : '↓'} {Math.abs(stats.savings_delta).toFixed(1)}% vs prev. month
                    </span>
                  )}
                </div>
              </div>

              {/* Sankey Diagram */}
              <div className="st-card">
                <h2 className="st-heading border-none p-0 text-xl">Cash Flow Analysis</h2>
                <div className="h-[500px] mt-6">
                  <SankeyChart data={flowData} />
                </div>
              </div>

              {/* Two Column Charts */}
              <div className="grid grid-cols-2 gap-8 mt-8">
                <div className="st-card">
                  <h2 className="st-heading border-none p-0 text-lg">Spending Trend</h2>
                  <div className="h-80 mt-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={dailyData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} />
                        <XAxis 
                          dataKey="name" 
                          stroke="#8b949e"
                          tickFormatter={(val) => {
                            try {
                              const d = new Date(val);
                              return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
                            } catch { return val; }
                          }}
                          tick={{ fontSize: 11 }}
                        />
                        <YAxis stroke="#8b949e" tick={{ fontSize: 11 }} tickFormatter={(v) => `€${v}`} />
                        <Tooltip 
                          contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 12 }} 
                          formatter={(v) => [`€${Math.abs(v).toLocaleString('it-IT', {minimumFractionDigits: 2})}`, 'Amount']}
                        />
                        <Area type="monotone" dataKey="value" stroke="#ff4b4b" fill="#ff4b4b" fillOpacity={0.1} strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="st-card">
                  <h2 className="st-heading border-none p-0 text-lg">Category Breakdown</h2>
                  <div className="flex gap-4 mt-4">
                    {/* Pie */}
                    <div className="w-48 h-48 shrink-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={categoryData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={70}
                            paddingAngle={3}
                            dataKey="value"
                          >
                            {categoryData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(v) => [`€${v.toLocaleString('it-IT', {minimumFractionDigits:2})}`, '']} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    {/* Legend */}
                    <div className="flex flex-col gap-2 overflow-y-auto flex-1 justify-center">
                      {(() => {
                        const total = categoryData.reduce((s, d) => s + d.value, 0);
                        return categoryData.map((item, index) => (
                          <div key={item.name} className="flex items-center justify-between text-xs gap-2">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: COLORS[index % COLORS.length] }} />
                              <span className="text-slate-300 truncate">{item.name}</span>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <span className="text-slate-500">{total ? Math.round((item.value / total) * 100) : 0}%</span>
                              <span className="font-semibold text-slate-200">€{item.value.toLocaleString('it-IT', {minimumFractionDigits: 2})}</span>
                            </div>
                          </div>
                        ));
                      })()}
                    </div>
                  </div>
                </div>
              </div>

              {/* Recent Transactions Section */}
              <h2 className="st-heading mt-12">Recent Transactions</h2>
              <TransactionsTable transactions={transactions.slice(0, 5)} categories={categories} onUpdate={handleUpdateTransaction} />
            </motion.div>
          )}

          {activeTab === 'transactions' && (
            <motion.div key="explorer" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h1 className="st-heading">Data Explorer</h1>
              <TransactionsView 
                transactions={transactions} 
                categories={categories} 
                onUpdate={handleUpdateTransaction} 
              />
            </motion.div>
          )}

          {activeTab === 'import' && (
            <motion.div key="import" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h1 className="st-heading">Import Data</h1>
              
              <div className="st-card">
                <h3 className="mb-4">Select Bank Profile</h3>
                <select 
                  className="st-select max-w-sm"
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                >
                  {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                
                <div className="mt-8 border-2 border-dashed border-[#30363d] rounded-lg p-12 text-center">
                  {!isUploading && !analysisResult ? (
                    <div className="flex flex-col items-center gap-4">
                      <Upload className="text-[#ff4b4b]" size={48} />
                      <p>Drag and drop or click to upload PDF/CSV/XLSX</p>
                      <label className="btn-primary cursor-pointer">
                        Browse Files
                        <input type="file" className="hidden" onChange={handleFileSelect} />
                      </label>
                    </div>
                  ) : null}

                  {isUploading && (
                    <div className="flex flex-col gap-6 items-center w-full max-w-md mx-auto">
                      <div className="w-full">
                        <div className="flex justify-between text-sm mb-2">
                          <span>Processing...</span>
                          <span>{Math.round((uploadStatus?.progress || 0) * 100)}%</span>
                        </div>
                        <div className="w-full bg-[#30363d] h-2 rounded-full overflow-hidden">
                          <div className="h-full bg-[#ff4b4b]" style={{ width: `${(uploadStatus?.progress || 0) * 100}%` }} />
                        </div>
                      </div>
                      <div className="w-full bg-black rounded-lg p-4 font-mono text-[10px] text-left h-48 overflow-y-auto">
                        {(uploadStatus?.logs || []).map((l, i) => <div key={i} className="mb-1">{l}</div>)}
                      </div>
                    </div>
                  )}

                  {analysisResult && !isUploading && (
                    <div className="flex flex-col gap-6 w-full text-left py-4">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="st-metric-card">
                          <span className="st-metric-label">Total Rows</span>
                          <span className="st-metric-value">{analysisResult.total_rows}</span>
                        </div>
                        <div className="st-metric-card">
                          <span className="st-metric-label">New Rows</span>
                          <span className="st-metric-value text-emerald-400">{analysisResult.new_rows}</span>
                        </div>
                        <div className="st-metric-card">
                          <span className="st-metric-label">Duplicates</span>
                          <span className="st-metric-value text-slate-500">{analysisResult.duplicate_rows ?? (analysisResult.total_rows - analysisResult.new_rows)}</span>
                        </div>
                      </div>
                      {analysisResult.estimated_seconds > 0 && (
                        <p className="text-sm text-slate-400">
                          ⏱ Estimated: <strong className="text-white">~{Math.round(analysisResult.estimated_seconds)}s</strong>
                          {analysisResult.avg_speed ? ` (${analysisResult.new_rows} rows × ${analysisResult.avg_speed.toFixed(1)}s avg)` : ""}
                        </p>
                      )}
                      {analysisResult.preview_rows?.length > 0 && (
                        <div>
                          <p className="text-xs text-slate-500 mb-2 uppercase font-bold tracking-wider">Data Preview (first {analysisResult.preview_rows.length} rows)</p>
                          <div className="overflow-x-auto rounded border border-[#30363d]">
                            <table className="w-full text-xs text-left">
                              <thead>
                                <tr className="bg-[#161b22] border-b border-[#30363d]">
                                  {Object.keys(analysisResult.preview_rows[0]).map(col => (
                                    <th key={col} className="px-3 py-2 text-slate-500 font-semibold uppercase whitespace-nowrap">{col}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {analysisResult.preview_rows.map((row, i) => (
                                  <tr key={i} className="border-b border-[#21262d] hover:bg-white/[0.02]">
                                    {Object.values(row).map((val, j) => (
                                      <td key={j} className="px-3 py-2 text-slate-300 max-w-[180px] truncate">{String(val ?? "")}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                      <div className="text-center pt-2">
                        <button onClick={startIngestion} className="btn-primary px-12 py-3">
                          Confirm & Process {analysisResult.new_rows} rows
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'catalogue' && (
            <motion.div key="catalogue" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h1 className="st-heading">Merchant Catalogue</h1>
              <CatalogueView categories={categories} />
            </motion.div>
          )}

          {activeTab === 'settings' && (
            <motion.div key="settings" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h1 className="st-heading">Settings</h1>
              <SettingsView />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default App;
