import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, Save, Trash2, Home, Settings, Brain, 
  HelpCircle, Rocket, Zap, Database, Download, 
  RefreshCcw, AlertCircle, PlusCircle, CheckCircle2
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const SettingsView = ({ showAdvanced }) => {
  const [activeSubTab, setActiveSubTab] = useState('started');
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState(null);
  const [systemStatus, setSystemStatus] = useState({
    rules: 24,
    aliases: 156,
    catalogue: 842,
    cache: '1.2 GB'
  });
  const [rules, setRules] = useState([
    { id: 1, text: "If operation contains 'AMAZON' and amount > 50, category is 'Shopping'" },
    { id: 2, text: "Treat 'CONAD' and 'COOP' always as 'Groceries'" }
  ]);
  const [newRuleText, setNewRuleText] = useState('');

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      const res = await axios.get(`${API_BASE}/profiles/`);
      setProfiles(res.data);
      const active = res.data.find(p => p.is_active) || res.data[0];
      if (active) setActiveProfile(active);
    } catch (err) {
      console.error("Error fetching profiles:", err);
    }
  };

  const TabButton = ({ id, icon: Icon, label }) => (
    <button
      onClick={() => setActiveSubTab(id)}
      className={`flex items-center gap-2 px-6 py-3 border-b-2 transition-all ${
        activeSubTab === id 
          ? 'border-[#ff4b4b] text-[#ff4b4b] bg-[#ff4b4b]/5' 
          : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-white/5'
      }`}
    >
      <Icon size={18} />
      <span className="font-bold text-sm uppercase tracking-widest">{label}</span>
    </button>
  );

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="pb-20">
      
      {/* Sidebar-like Profile Switcher */}
      <div className="st-card mb-8 flex justify-between items-center bg-[#1f2937]/50">
        <div className="flex items-center gap-4">
          <div className="bg-[#ff4b4b]/20 p-2 rounded-lg">
            <Database size={20} className="text-[#ff4b4b]" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Active Profile</p>
            <select 
              className="bg-transparent border-none text-white font-bold text-lg p-0 focus:ring-0 cursor-pointer"
              value={activeProfile?.id}
              onChange={(e) => {
                const p = profiles.find(p => p.id === parseInt(e.target.value));
                setActiveProfile(p);
              }}
            >
              {profiles.map(p => <option key={p.id} value={p.id} className="bg-[#1f2937]">{p.name}</option>)}
              <option value="new">+ Create New Profile</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 rounded-lg border border-[#374151] text-xs font-bold hover:bg-white/5 transition-all flex items-center gap-2">
            <Download size={14} /> Export JSON
          </button>
          <button className="px-4 py-2 rounded-lg border border-[#ff4b4b]/30 text-[#ff4b4b] text-xs font-bold hover:bg-[#ff4b4b]/10 transition-all">
            Reset Profile
          </button>
        </div>
      </div>

      <div className="st-card p-0 overflow-hidden">
        {/* Sub-tabs Header */}
        <div className="flex border-b border-[#374151] bg-[#161b22]">
          <TabButton id="started" icon={Home} label="Get Started" />
          <TabButton id="general" icon={Settings} label="General Settings" />
          <TabButton id="ai" icon={Brain} label="AI & Memory" />
        </div>

        <div className="p-8">
          <AnimatePresence mode="wait">
            {activeSubTab === 'started' && (
              <motion.div 
                key="started" 
                initial={{ opacity: 0, x: -10 }} 
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className="space-y-8"
              >
                {/* Smart Discovery */}
                <div className="bg-gradient-to-br from-[#ff4b4b]/10 to-transparent p-8 rounded-2xl border border-[#ff4b4b]/20">
                  <div className="flex items-center gap-4 mb-4">
                    <Rocket className="text-[#ff4b4b]" size={32} />
                    <div>
                      <h3 className="text-xl font-bold text-white mb-0">Smart Auto-Discovery</h3>
                      <p className="text-sm text-slate-400">Let the AI detect your bank statement schema automatically</p>
                    </div>
                  </div>
                  <div className="flex gap-4 items-center">
                    <div className="flex-1 border-2 border-dashed border-[#374151] rounded-xl p-6 text-center hover:border-[#ff4b4b]/50 transition-all cursor-pointer">
                      <p className="text-sm text-slate-500">Drop a bank statement sample here</p>
                    </div>
                    <button className="btn-primary py-4 px-8 h-full flex items-center gap-2">
                      <Zap size={18} /> Run Discovery
                    </button>
                  </div>
                </div>

                {/* System Status */}
                <div className="grid grid-cols-4 gap-6">
                  {[
                    { label: 'Rules Memory', value: systemStatus.rules, icon: Brain },
                    { label: 'Merchant Aliases', value: systemStatus.aliases, icon: PlusCircle },
                    { label: 'Merchant Catalogue', value: systemStatus.catalogue, icon: Database },
                    { label: 'Extraction Cache', value: systemStatus.cache, icon: RefreshCcw },
                  ].map((s, i) => (
                    <div key={i} className="bg-[#0d1117] p-6 rounded-xl border border-[#30363d]">
                      <s.icon className="text-slate-500 mb-4" size={20} />
                      <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-1">{s.label}</p>
                      <p className="text-2xl font-bold text-white">{s.value}</p>
                    </div>
                  ))}
                </div>

                {/* Quick Start Expander (Simulated) */}
                <div className="border border-[#374151] rounded-xl overflow-hidden">
                  <div className="bg-[#161b22] p-4 flex justify-between items-center cursor-pointer">
                    <div className="flex items-center gap-3">
                      <HelpCircle size={18} className="text-[#ff4b4b]" />
                      <span className="font-bold">How to use Personal BI Assistant?</span>
                    </div>
                  </div>
                  <div className="p-6 text-sm text-slate-400 space-y-4">
                    <p>1. <strong>Upload</strong> your bank statement (PDF, CSV, or XLSX) in the Import tab.</p>
                    <p>2. <strong>Process</strong> the data: the AI will automatically classify merchants and categories.</p>
                    <p>3. <strong>Verify</strong> transactions in the Data Explorer if confidence is low.</p>
                  </div>
                </div>

                <div className="flex justify-center pt-8">
                  <button className="flex items-center gap-2 text-[#ff4b4b] font-bold text-sm hover:underline">
                    <AlertCircle size={16} /> Deep Recovery (Retry Errors)
                  </button>
                </div>
              </motion.div>
            )}

            {activeSubTab === 'general' && (
              <motion.div 
                key="general"
                initial={{ opacity: 0, x: -10 }} 
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className="space-y-8"
              >
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-6">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-[#ff4b4b]">Core Schema</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Profile Name</label>
                        <input type="text" className="st-input w-full" defaultValue={activeProfile?.name} />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Skip Rows</label>
                          <input type="number" className="st-input w-full" defaultValue={0} />
                        </div>
                        <div>
                          <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Date Format</label>
                          <input type="text" className="st-input w-full" defaultValue="DD/MM/YYYY" />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-[#ff4b4b]">Column Mapping</h3>
                    <div className="grid grid-cols-2 gap-4">
                      {['Date', 'Operation', 'Amount', 'Details'].map(col => (
                        <div key={col}>
                          <label className="text-xs font-bold text-slate-500 uppercase block mb-2">{col} Column</label>
                          <input type="text" className="st-input w-full" defaultValue={col} />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="pt-8 border-t border-[#374151]">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-[#ff4b4b]">Advanced Settings</h3>
                    {showAdvanced ? (
                      <span className="text-[10px] font-black text-[#ff4b4b] uppercase tracking-widest bg-[#ff4b4b]/10 px-2 py-1 rounded">Enabled</span>
                    ) : (
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Locked</span>
                    )}
                  </div>
                  
                  {showAdvanced && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="space-y-6 overflow-hidden">
                      <div className="grid grid-cols-2 gap-8">
                        <div>
                          <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Income Keywords</label>
                          <textarea className="st-input w-full h-24 font-mono text-xs" defaultValue="STIPENDIO, BONIFICO ENTRATA, REFUND" />
                        </div>
                        <div>
                          <label className="text-xs font-bold text-slate-500 uppercase block mb-2">Cleanup Regex Patterns</label>
                          <textarea className="st-input w-full h-24 font-mono text-xs" defaultValue="CARD \d{4}, \d{2}/\d{2} \d{2}:\d{2}" />
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>

                <div className="flex justify-end pt-4">
                  <button className="btn-primary flex items-center gap-2 px-12 py-3">
                    <Save size={18} /> Save Settings
                  </button>
                </div>
              </motion.div>
            )}

            {activeSubTab === 'ai' && (
              <motion.div 
                key="ai"
                initial={{ opacity: 0, x: -10 }} 
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className="space-y-8"
              >
                <div className="bg-[#0d1117] p-8 rounded-2xl border border-[#30363d]">
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <PlusCircle size={20} className="text-[#ff4b4b]" /> New Business Rule
                  </h3>
                  <p className="text-sm text-slate-500 mb-6 italic">Teach the AI new classification rules using natural language.</p>
                  <div className="flex gap-4">
                    <input 
                      type="text" 
                      className="st-input flex-1 py-4 px-6 text-base"
                      placeholder="e.g. Always classify 'Netflix' as 'Subscription' if amount < 20..."
                      value={newRuleText}
                      onChange={(e) => setNewRuleText(e.target.value)}
                    />
                    <button className="btn-primary px-8 flex items-center gap-2">
                      Compile & Learn
                    </button>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-bold uppercase tracking-widest text-[#ff4b4b] mb-6">Active Rules Memory</h3>
                  <div className="space-y-3">
                    {rules.map(rule => (
                      <div key={rule.id} className="bg-[#161b22] p-4 rounded-xl border border-[#374151] flex justify-between items-center group">
                        <div className="flex items-start gap-3">
                          <CheckCircle2 size={16} className="text-emerald-400 mt-1" />
                          <span className="text-sm text-slate-300">{rule.text}</span>
                        </div>
                        <button className="text-slate-600 hover:text-[#ff4b4b] opacity-0 group-hover:opacity-100 transition-all p-2">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {showAdvanced && (
                  <div className="pt-8 border-t border-[#374151]">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-[#ff4b4b] mb-6">LLM Configuration Override</h3>
                  <div className="grid grid-cols-3 gap-6">
                    <div>
                      <label className="text-xs font-bold text-slate-600 uppercase block mb-2">Classification Model</label>
                      <input type="text" className="st-input w-full text-xs font-mono" defaultValue="qwen3:14b" />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-slate-600 uppercase block mb-2">Extraction Model</label>
                      <input type="text" className="st-input w-full text-xs font-mono" defaultValue="gemma3:12b" />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-slate-600 uppercase block mb-2">Recovery Model</label>
                      <input type="text" className="st-input w-full text-xs font-mono" defaultValue="llama3.1:8b" />
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};

export default SettingsView;
