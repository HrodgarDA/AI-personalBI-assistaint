import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Search, ShieldCheck, Plus, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const CatalogueView = ({ categories }) => {
  const [merchants, setMerchants] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [aliasInput, setAliasInput] = useState('');

  useEffect(() => {
    fetchMerchants();
  }, []);

  const fetchMerchants = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/merchants/`);
      setMerchants(res.data);
    } catch (err) {
      console.error("Error fetching merchants:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (merchantId, data) => {
    try {
      await axios.patch(`${API_BASE}/merchants/${merchantId}`, data);
      fetchMerchants();
    } catch (err) {
      console.error("Error updating merchant:", err);
    }
  };

  const handleAddAlias = async (merchantId) => {
    if (!aliasInput.trim()) return;
    await handleUpdate(merchantId, { add_alias: aliasInput.trim() });
    setAliasInput('');
  };

  const handleRemoveAlias = async (merchantId, alias) => {
    await handleUpdate(merchantId, { remove_alias: alias });
  };

  const filtered = merchants.filter(m =>
    m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (m.raw_names || []).some(r => r.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-6">

      {/* Search bar */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
        <input
          type="text"
          placeholder="Search by name or alias..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="st-select pl-9 mb-0"
        />
      </div>

      {/* Table */}
      <div className="st-card p-0 overflow-hidden">
        {loading ? (
          <div className="py-20 text-center text-slate-500">Loading...</div>
        ) : (
          <>
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="border-b border-[#30363d] bg-[#161b22]">
                  <th className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Merchant</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Raw Names / Aliases</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-center"># Tx</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Outgoing Category</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Incoming Category</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-center">Override</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((merchant) => {
                  const isExpanded = expandedId === merchant.id;
                  const hasOverride = merchant.default_outgoing_category_id || merchant.default_incoming_category_id;
                  return (
                    <React.Fragment key={merchant.id}>
                      <tr
                        className="border-b border-[#21262d] hover:bg-white/[0.02] transition-colors cursor-pointer"
                        onClick={() => setExpandedId(isExpanded ? null : merchant.id)}
                      >
                        {/* Merchant name */}
                        <td className="px-5 py-3 font-semibold text-slate-200">
                          {merchant.name}
                        </td>

                        {/* Raw names badges */}
                        <td className="px-5 py-3">
                          <div className="flex flex-wrap gap-1">
                            {(merchant.raw_names || []).slice(0, 3).map((raw, i) => (
                              <span key={i} className="text-[10px] px-2 py-0.5 bg-[#30363d] text-slate-400 rounded-full">{raw}</span>
                            ))}
                            {(merchant.raw_names || []).length > 3 && (
                              <span className="text-[10px] px-2 py-0.5 bg-[#30363d] text-slate-500 rounded-full">+{(merchant.raw_names || []).length - 3} more</span>
                            )}
                            {(merchant.raw_names || []).length === 0 && (
                              <span className="text-[10px] text-slate-600">—</span>
                            )}
                          </div>
                        </td>

                        {/* Transaction count */}
                        <td className="px-5 py-3 text-center">
                          <span className="text-sm font-semibold text-slate-300">{merchant.transaction_count ?? 0}</span>
                        </td>

                        {/* Outgoing category */}
                        <td className="px-5 py-3" onClick={e => e.stopPropagation()}>
                          <select
                            value={merchant.default_outgoing_category_id || ''}
                            onChange={(e) => handleUpdate(merchant.id, { default_outgoing_category_id: e.target.value ? parseInt(e.target.value) : null })}
                            className="bg-[#161b22] border border-[#30363d] rounded px-2 py-1 text-xs text-slate-300 focus:ring-1 focus:ring-[#ff4b4b] outline-none w-full"
                          >
                            <option value="">(AI Decide)</option>
                            {categories.map(cat => <option key={cat.id} value={cat.id}>{cat.name}</option>)}
                          </select>
                        </td>

                        {/* Incoming category */}
                        <td className="px-5 py-3" onClick={e => e.stopPropagation()}>
                          <select
                            value={merchant.default_incoming_category_id || ''}
                            onChange={(e) => handleUpdate(merchant.id, { default_incoming_category_id: e.target.value ? parseInt(e.target.value) : null })}
                            className="bg-[#161b22] border border-[#30363d] rounded px-2 py-1 text-xs text-slate-300 focus:ring-1 focus:ring-[#ff4b4b] outline-none w-full"
                          >
                            <option value="">(AI Decide)</option>
                            {categories.map(cat => <option key={cat.id} value={cat.id}>{cat.name}</option>)}
                          </select>
                        </td>

                        {/* Override status */}
                        <td className="px-5 py-3 text-center">
                          {hasOverride ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded">
                              <ShieldCheck size={10} /> ON
                            </span>
                          ) : (
                            <span className="text-xs text-slate-600">Auto</span>
                          )}
                        </td>
                      </tr>

                      {/* Expanded alias management row */}
                      {isExpanded && (
                        <tr className="border-b border-[#30363d] bg-[#0d1117]">
                          <td colSpan={6} className="px-6 py-4">
                            <div className="flex flex-col gap-3">
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Alias Management</p>
                              <div className="flex flex-wrap gap-2 min-h-[28px]">
                                {(merchant.raw_names || []).map((alias, i) => (
                                  <span key={i} className="flex items-center gap-1 text-xs px-2 py-1 bg-[#21262d] border border-[#30363d] rounded-full text-slate-300">
                                    {alias}
                                    <button
                                      onClick={() => handleRemoveAlias(merchant.id, alias)}
                                      className="text-slate-600 hover:text-[#ff4b4b] transition-colors"
                                    >
                                      <X size={11} />
                                    </button>
                                  </span>
                                ))}
                                {(merchant.raw_names || []).length === 0 && (
                                  <span className="text-xs text-slate-600 italic">No aliases registered</span>
                                )}
                              </div>
                              <div className="flex gap-2 max-w-sm">
                                <input
                                  type="text"
                                  placeholder="Add raw alias name..."
                                  value={aliasInput}
                                  onChange={e => setAliasInput(e.target.value)}
                                  onKeyDown={e => e.key === 'Enter' && handleAddAlias(merchant.id)}
                                  className="st-select mb-0 text-xs flex-1"
                                />
                                <button
                                  onClick={() => handleAddAlias(merchant.id)}
                                  className="btn-primary flex items-center gap-1 px-3 py-1 text-xs"
                                >
                                  <Plus size={12} /> Add
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>

            {filtered.length === 0 && !loading && (
              <div className="py-20 text-center text-slate-500">No merchants match your search.</div>
            )}

            <div className="px-5 py-3 border-t border-[#30363d] text-xs text-slate-600">
              {filtered.length} of {merchants.length} merchants
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
};

export default CatalogueView;
