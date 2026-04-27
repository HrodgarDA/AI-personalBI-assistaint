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
  Info,
  Zap,
  X
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
  Cell,
  BarChart,
  Bar
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
  const [stats, setStats] = useState({ 
    total_amount: 0, 
    transaction_count: 0, 
    monthly_income: 0, 
    monthly_expense: 0, 
    monthly_savings: 0, 
    net_balance: 0,
    income_delta: 0, 
    expense_delta: 0, 
    savings_delta: 0 
  });
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
  const [selectedTipology, setSelectedTipology] = useState('All');
  const [selectedStartDate, setSelectedStartDate] = useState(null);
  const [selectedEndDate, setSelectedEndDate] = useState(null);
  const [timeFreq, setTimeFreq] = useState('Daily');
  const [chartIsCumulative, setChartIsCumulative] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [needsReviewOnly, setNeedsReviewOnly] = useState(false);

  const SAVINGS_CAT = "Savings & Investments";
  const REFUND_CAT = "Refund";

  useEffect(() => {
    // Restore state from URL
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('page');
    if (tab) setActiveTab(tab.toLowerCase());
    
    const tipology = params.get('tipology');
    if (tipology) setSelectedTipology(tipology);

    const cats = params.get('categories');
    if (cats) setSelectedCategories(cats.split(',').map(Number));
  }, []);

  useEffect(() => {
    // Sync URL from state
    const params = new URLSearchParams();
    params.set('page', activeTab);
    params.set('tipology', selectedTipology);
    if (selectedCategories.length > 0) params.set('categories', selectedCategories.join(','));
    
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', newUrl);

    fetchStats();
    fetchTransactions();
    fetchProfiles();
    fetchCategories();
  }, [currentMonth, currentYear, selectedCategories, activeTab, selectedTipology, selectedStartDate, selectedEndDate]);

  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API_BASE}/categories/`);
      setCategories(res.data);
    } catch (err) {
      console.error("Error fetching categories:", err);
    }
  };

  const handleUpdateTransaction = async (txId, fieldOrData, value) => {
    try {
      const data = typeof fieldOrData === 'string' ? { [fieldOrData]: value } : fieldOrData;
      await axios.patch(`${API_BASE}/transactions/${txId}`, data);
      fetchTransactions();
      fetchStats();
    } catch (err) {
      console.error("Update error:", err);
    }
  };

  const handleBulkUpdate = async ({ changes, deleted_ids }) => {
    try {
      // In a real implementation, this would be a single POST /transactions/bulk
      // For now we simulate or use multiple calls if the backend doesn't have it
      await Promise.all([
        ...changes.map(c => axios.patch(`${API_BASE}/transactions/${c.id}`, c)),
        ...deleted_ids.map(id => axios.delete(`${API_BASE}/transactions/${id}`))
      ]);
      fetchTransactions();
      fetchStats();
    } catch (err) {
      console.error("Bulk update error:", err);
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

  const handleCategoryChange = (catId) => {
    setSelectedCategories(prev => {
      if (catId === 'All') return [];
      const current = prev.filter(c => c !== 'All');
      if (current.includes(catId)) {
        return current.filter(c => c !== catId);
      }
      return [...current, catId];
    });
  };

  const fetchTransactions = async () => {
    try {
      const params = {
        month: currentMonth,
        year: currentYear,
        tipology: selectedTipology !== 'All' ? selectedTipology : undefined
      };
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
          <h3 className="text-[10px] uppercase font-black mb-6 tracking-[0.2em] text-slate-500 px-2">Ingestion Engine</h3>
          
          <div className="px-2 space-y-6">
            {/* Sidebar Uploader */}
            <div 
              className="border-2 border-dashed border-[#30363d] rounded-2xl p-6 text-center cursor-pointer hover:border-[#ff4b4b]/50 transition-all group bg-[#0d1117]"
              onClick={() => document.getElementById('sidebar-file-input').click()}
            >
              <Upload size={24} className="mx-auto mb-3 text-slate-600 group-hover:text-[#ff4b4b] transition-colors" />
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Drop Statement</p>
              <input 
                id="sidebar-file-input"
                type="file" 
                className="hidden" 
                onChange={handleFileSelect}
              />
            </div>

            {pendingFile && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[#ff4b4b]/10 border border-[#ff4b4b]/20 rounded-lg p-4 relative"
              >
                <p className="text-[10px] font-black text-[#ff4b4b] truncate mb-3 uppercase tracking-tighter">{pendingFile.name}</p>
                <div className="flex gap-2">
                  <button 
                    onClick={startIngestion}
                    className="btn-primary flex-1 text-[10px] font-black uppercase tracking-widest"
                  >
                    Archive
                  </button>
                  <button 
                    onClick={() => { setPendingFile(null); setAnalysisResult(null); }}
                    className="p-2 text-slate-500 hover:text-white transition-colors"
                  >
                    <X size={14} />
                  </button>
                </div>
              </motion.div>
            )}

            <button className="btn-secondary w-full py-3 flex items-center justify-center gap-3 shadow-xl group uppercase tracking-[0.2em] text-[10px] font-black">
              <Zap size={14} className="text-[#ff4b4b] group-hover:scale-125 transition-transform" /> Process Data
            </button>
          </div>

          <div className="mt-10 px-2 space-y-4">
            <h3 className="text-[10px] uppercase font-black mb-4 tracking-[0.2em] text-slate-500">Global Controls</h3>
            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 group-hover:text-slate-300 transition-colors">Advanced Mode</span>
              <div className="relative">
                <input 
                  type="checkbox" 
                  className="sr-only" 
                  checked={showAdvanced}
                  onChange={(e) => setShowAdvanced(e.target.checked)}
                />
                <div className={`w-8 h-4 rounded-full transition-colors ${showAdvanced ? 'bg-[#ff4b4b]' : 'bg-[#30363d]'}`} />
                <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${showAdvanced ? 'translate-x-4' : ''}`} />
              </div>
            </label>
            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 group-hover:text-slate-300 transition-colors">Needs Review</span>
              <div className="relative">
                <input 
                  type="checkbox" 
                  className="sr-only" 
                  checked={needsReviewOnly}
                  onChange={(e) => setNeedsReviewOnly(e.target.checked)}
                />
                <div className={`w-8 h-4 rounded-full transition-colors ${needsReviewOnly ? 'bg-[#ff4b4b]' : 'bg-[#30363d]'}`} />
                <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${needsReviewOnly ? 'translate-x-4' : ''}`} />
              </div>
            </label>
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
        {activeTab !== 'settings' && (
          <header className="mb-12">
            <h1 className="text-center font-bold text-4xl mb-8">Personal BI Assistant</h1>
            
            {/* Filter Container (Bordered Card) */}
            <div className="st-card grid grid-cols-12 gap-6 items-end">
              {/* Col 1 (Width 3): Category Multiselect */}
              <div className="col-span-3">
                <label className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Categories</label>
                <div className="relative group">
                  <div className="st-input min-h-[40px] h-auto py-2 px-3 flex flex-wrap gap-1 cursor-pointer">
                    {selectedCategories.length === 0 ? (
                      <span className="text-slate-500 text-sm">All Categories</span>
                    ) : (
                      selectedCategories.map(catId => {
                        const cat = categories.find(c => c.id === catId);
                        return (
                          <span key={catId} className="bg-[#ff4b4b]/20 text-[#ff4b4b] text-[10px] font-black uppercase px-2 py-0.5 rounded flex items-center gap-1">
                            {cat?.name || catId}
                            <X size={10} className="cursor-pointer hover:text-white" onClick={(e) => { e.stopPropagation(); handleCategoryChange(catId); }} />
                          </span>
                        );
                      })
                    )}
                  </div>
                  {/* Custom Dropdown on Hover/Click */}
                  <div className="absolute top-full left-0 w-64 mt-2 bg-[#1f2937] border border-[#374151] rounded-xl shadow-2xl z-50 opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-all p-2 max-h-64 overflow-y-auto">
                    <div 
                      className={`px-3 py-2 rounded-lg text-xs cursor-pointer mb-1 ${selectedCategories.length === 0 ? 'bg-[#ff4b4b] text-white' : 'hover:bg-white/5 text-slate-300'}`}
                      onClick={() => handleCategoryChange('All')}
                    >
                      All Categories
                    </div>
                    {categories.map(cat => (
                      <div 
                        key={cat.id}
                        className={`px-3 py-2 rounded-lg text-xs cursor-pointer mb-1 ${selectedCategories.includes(cat.id) ? 'bg-[#ff4b4b]/20 text-[#ff4b4b] font-bold' : 'hover:bg-white/5 text-slate-400'}`}
                        onClick={() => handleCategoryChange(cat.id)}
                      >
                        {cat.name}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Col 2 (Width 3): Tipology */}
              <div className="col-span-3">
                <label className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Tipology</label>
                <select 
                  className="st-select mb-0 h-10"
                  value={selectedTipology}
                  onChange={(e) => setSelectedTipology(e.target.value)}
                >
                  <option value="All">All Transactions</option>
                  <option value="Incoming">Incoming (Credits)</option>
                  <option value="Outgoing">Outgoing (Debits)</option>
                </select>
              </div>

              {/* Col 3 (Width 6): Date Range (Simplified as Month/Year for now) */}
              <div className="col-span-6 grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Year</label>
                  <select 
                    className="st-select mb-0 h-10" 
                    value={currentYear} 
                    onChange={(e) => setCurrentYear(parseInt(e.target.value))}
                  >
                    {[2023, 2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2 block">Month</label>
                  <select 
                    className="st-select mb-0 h-10"
                    value={currentMonth}
                    onChange={(e) => setCurrentMonth(parseInt(e.target.value))}
                  >
                    {["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"].map((m, i) => (
                      <option key={m} value={i + 1}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </header>
        )}

        <AnimatePresence mode="wait">
          {activeTab === 'dashboard' && (
            <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              
              {/* Net Balance Widget Banner */}
              <div className="st-card bg-gradient-to-r from-[#1f2937] to-[#111827] border-[#374151] shadow-2xl relative overflow-hidden group mb-8">
                <div className="absolute top-0 right-0 w-64 h-64 bg-[#ff4b4b]/5 rounded-full -mr-32 -mt-32 blur-3xl group-hover:bg-[#ff4b4b]/10 transition-all duration-700" />
                <div className="relative z-10 flex justify-around py-2 w-full">
                  <div className="text-center">
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-2">Net Balance</p>
                    <p className="text-3xl font-black text-[#00d4ff] tracking-tight">€{(stats.net_balance || 0).toLocaleString('it-IT', { minimumFractionDigits: 2 })}</p>
                  </div>
                  <div className="w-px h-12 bg-[#374151] self-center" />
                  <div className="text-center">
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-2">Monthly Net Savings</p>
                    <p className="text-3xl font-black text-white tracking-tight">€{(stats.monthly_savings || 0).toLocaleString('it-IT', { minimumFractionDigits: 2 })}</p>
                  </div>
                </div>
              </div>

              {/* Review Warning */}
              {transactions.some(t => t.confidence < 0.7) && (
                <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-4 mb-8 flex items-center gap-3 text-yellow-200 text-sm">
                  <Info size={18} className="shrink-0" />
                  <span>Some transactions have low classification confidence (&lt; 70%) and should be reviewed in the Data Explorer.</span>
                </div>
              )}

              {/* Metrics Row */}
              <div className="grid grid-cols-4 gap-6 mb-12">
                <div className="st-metric-card">
                  <span className="st-metric-label">Transactions</span>
                  <span className="st-metric-value">{stats.transaction_count}</span>
                </div>
                <div className="st-metric-card">
                  <span className="st-metric-label">Real Income</span>
                  <span className="st-metric-value">€{(stats.monthly_income || 0).toLocaleString('it-IT', {minimumFractionDigits: 2})}</span>
                  {stats.income_delta !== null && stats.income_delta !== undefined && (
                    <span className={`st-metric-delta ${stats.income_delta >= 0 ? 'up' : 'down'}`}>
                      {stats.income_delta >= 0 ? '↑' : '↓'} {Math.abs(stats.income_delta).toFixed(1)}% vs prev. month
                    </span>
                  )}
                </div>
                <div className="st-metric-card">
                  <span className="st-metric-label">Real Expenses (Net)</span>
                  <span className="st-metric-value text-[#ff4b4b]">€{(stats.monthly_expense || 0).toLocaleString('it-IT', {minimumFractionDigits: 2})}</span>
                  {stats.expense_delta !== null && stats.expense_delta !== undefined && (
                    <span className={`st-metric-delta ${stats.expense_delta <= 0 ? 'up' : 'down'}`}>
                      {stats.expense_delta >= 0 ? '↑' : '↓'} {Math.abs(stats.expense_delta).toFixed(1)}% vs prev. month
                    </span>
                  )}
                </div>
                <div className="st-metric-card">
                  <span className="st-metric-label">Top Category</span>
                  <span className="st-metric-value text-sm truncate">
                    {categoryData[0]?.name || "N/A"}
                  </span>
                </div>
              </div>
              {/* Time Series Chart */}
              <div className="st-card">
                <div className="flex justify-between items-center mb-8">
                  <h2 className="st-heading border-none p-0 text-sm font-black uppercase tracking-[0.2em] text-slate-500 m-0">Amount Over Time</h2>
                  <div className="flex gap-4">
                    <div className="flex bg-[#111827] rounded p-1 border border-[#374151]">
                      {['Daily', 'Weekly', 'Monthly'].map(freq => (
                        <button 
                          key={freq}
                          onClick={() => setTimeFreq(freq)}
                          className={`px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded transition-all ${timeFreq === freq ? 'bg-[#ff4b4b] text-white' : 'text-slate-500 hover:text-slate-300'}`}
                        >
                          {freq}
                        </button>
                      ))}
                    </div>
                    <div className="flex bg-[#111827] rounded p-1 border border-[#374151]">
                      {[
                        { id: true, label: 'Cumulative' },
                        { id: false, label: 'Periodical' }
                      ].map(type => (
                        <button 
                          key={type.label}
                          onClick={() => setChartIsCumulative(type.id)}
                          className={`px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded transition-all ${chartIsCumulative === type.id ? 'bg-[#ff4b4b] text-white' : 'text-slate-500 hover:text-slate-300'}`}
                        >
                          {type.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={dailyData}>
                      <defs>
                        <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ff4b4b" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#ff4b4b" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} />
                      <XAxis 
                        dataKey="name" 
                        stroke="#8b949e" 
                        fontSize={10} 
                        tickFormatter={(val) => val.split('-').slice(1).join('/')}
                      />
                      <YAxis stroke="#8b949e" fontSize={10} />
                      <Tooltip 
                        contentStyle={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', fontSize: '11px' }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="value" 
                        stroke="#ff4b4b" 
                        fillOpacity={1} 
                        fill="url(#colorAmount)" 
                        strokeWidth={3}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Sankey Diagram */}
              <div className="st-card">
                <h2 className="st-heading border-none p-0 text-xl">Cash Flow Analysis</h2>
                <div className="h-[500px] mt-6">
                  <SankeyChart data={flowData} />
                </div>
              </div>

                <div className="grid grid-cols-2 gap-8 mt-8">
                  {/* Category Pie */}
                  <div className="st-card p-8">
                    <h2 className="st-heading border-none p-0 text-sm font-black uppercase tracking-[0.2em] text-slate-500 mb-8 m-0">Category Distribution</h2>
                    <div className="flex gap-8 items-center h-64">
                      <div className="w-48 h-48 shrink-0 relative">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={categoryData}
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={85}
                              paddingAngle={5}
                              dataKey="value"
                              stroke="none"
                            >
                              {(Array.isArray(categoryData) ? categoryData : []).map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip 
                              contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11, borderRadius: '12px', padding: '12px' }}
                              formatter={(v) => [`€${v.toLocaleString('it-IT', {minimumFractionDigits:2})}`, '']}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Total</span>
                          <span className="text-lg font-black text-white">€{((Array.isArray(categoryData) ? categoryData : []).reduce((s, d) => s + (d.value || 0), 0) / 1000).toFixed(1)}k</span>
                        </div>
                      </div>
                      <div className="flex-1 space-y-3 overflow-y-auto max-h-full pr-2">
                        {(Array.isArray(categoryData) ? categoryData : []).slice(0, 6).map((item, index) => (
                          <div key={item.name} className="flex items-center justify-between text-[11px]">
                            <div className="flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full" style={{ background: COLORS[index % COLORS.length] }} />
                              <span className="text-slate-400 font-medium">{item.name}</span>
                            </div>
                            <span className="text-white font-bold">€{(item.value || 0).toLocaleString('it-IT')}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Category Bar Chart */}
                  <div className="st-card p-8">
                    <h2 className="st-heading border-none p-0 text-sm font-black uppercase tracking-[0.2em] text-slate-500 mb-8 m-0">Top Expenses</h2>
                    <div className="h-64 mt-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={(Array.isArray(categoryData) ? categoryData : []).slice(0, 8)} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" horizontal={false} />
                          <XAxis type="number" hide />
                          <YAxis 
                            type="category" 
                            dataKey="name" 
                            stroke="#8b949e" 
                            width={100}
                            tick={{ fontSize: 10, fontWeight: 700 }}
                          />
                          <Tooltip 
                            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                            contentStyle={{ background: '#161b22', border: '1px solid #30363d', fontSize: 11, borderRadius: '12px' }}
                          />
                          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                            {(Array.isArray(categoryData) ? categoryData : []).map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} fillOpacity={0.8} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
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
                onUpdate={handleBulkUpdate} 
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
              <SettingsView showAdvanced={showAdvanced} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default App;
