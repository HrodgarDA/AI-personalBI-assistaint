import React, { useState } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown, Brain } from 'lucide-react';

const STATUS_BADGE = {
  pending:    { label: 'Pending',    cls: 'bg-slate-700 text-slate-300' },
  classified: { label: 'Classified', cls: 'bg-blue-900/60 text-blue-300' },
  verified:   { label: 'Verified',   cls: 'bg-emerald-900/60 text-emerald-300' },
};

const SortIcon = ({ col, sortConfig }) => {
  if (sortConfig.key !== col) return <ChevronsUpDown size={13} className="text-slate-600" />;
  return sortConfig.direction === 'asc'
    ? <ChevronUp size={13} className="text-[#ff4b4b]" />
    : <ChevronDown size={13} className="text-[#ff4b4b]" />;
};

const TransactionsTable = ({ transactions, categories = [], onUpdate, editMode = false, selectedIds = [], setSelectedIds, pendingChanges = {} }) => {
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });
  const [expandedId, setExpandedId] = useState(null);

  const handleSort = (key) => {
    setSortConfig(prev =>
      prev.key === key
        ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { key, direction: 'asc' }
    );
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(sorted.map(t => t.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectRow = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const sorted = [...transactions].sort((a, b) => {
    let aVal, bVal;
    switch (sortConfig.key) {
      case 'date':    aVal = a.date; bVal = b.date; break;
      case 'amount':  aVal = a.amount; bVal = b.amount; break;
      case 'merchant': aVal = (a.merchant?.name || a.operation || '').toLowerCase(); bVal = (b.merchant?.name || b.operation || '').toLowerCase(); break;
      case 'category': aVal = (a.manual_category?.name || a.ai_category?.name || '').toLowerCase(); bVal = (b.manual_category?.name || b.ai_category?.name || '').toLowerCase(); break;
      case 'status':  aVal = a.status; bVal = b.status; break;
      default: return 0;
    }
    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const thClass = "px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest text-left cursor-pointer select-none hover:text-slate-300 transition-colors";

  return (
    <div className="st-card p-0 overflow-hidden border-[#30363d] bg-[#161b22]/50">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-[#30363d] bg-[#161b22]">
              {editMode && (
                <th className="px-4 py-3 w-10">
                  <input 
                    type="checkbox" 
                    className="w-4 h-4 accent-[#ff4b4b] cursor-pointer" 
                    onChange={handleSelectAll}
                    checked={selectedIds.length === sorted.length && sorted.length > 0}
                  />
                </th>
              )}
              <th className={thClass} onClick={() => handleSort('date')}>
                <span className="flex items-center gap-1">Date <SortIcon col="date" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass} onClick={() => handleSort('merchant')}>
                <span className="flex items-center gap-1">Merchant / Operation <SortIcon col="merchant" sortConfig={sortConfig} /></span>
              </th>
              {!editMode && <th className={thClass}>Details</th>}
              <th className={thClass} onClick={() => handleSort('category')}>
                <span className="flex items-center gap-1">Category <SortIcon col="category" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass} onClick={() => handleSort('amount')}>
                <span className="flex items-center gap-1">Amount <SortIcon col="amount" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass} onClick={() => handleSort('status')}>
                <span className="flex items-center gap-1">Status <SortIcon col="status" sortConfig={sortConfig} /></span>
              </th>
              {editMode && (
                <>
                  <th className={thClass + " text-center"}>Verify</th>
                  <th className={thClass + " text-center"}>AI Reasoning</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {sorted.map((tx) => {
              const pending = pendingChanges[tx.id] || {};
              const currentStatus = pending.status || tx.status;
              const badge = STATUS_BADGE[currentStatus] || STATUS_BADGE.pending;
              const currentCategoryId = pending.manual_category_id || tx.manual_category?.id || tx.ai_category?.id || '';
              const isExpanded = expandedId === tx.id;
              const details = tx.details || '';
              const truncDetails = details.length > 35 ? details.slice(0, 35) + '…' : details;
              const isSelected = selectedIds.includes(tx.id);

              return (
                <React.Fragment key={tx.id}>
                  <tr className={`border-b border-[#21262d] transition-colors ${isSelected ? 'bg-[#ff4b4b]/5' : 'hover:bg-white/[0.02]'}`}>
                    {/* Checkbox */}
                    {editMode && (
                      <td className="px-4 py-3">
                        <input 
                          type="checkbox" 
                          checked={isSelected}
                          onChange={() => handleSelectRow(tx.id)}
                          className="w-4 h-4 accent-[#ff4b4b] cursor-pointer" 
                        />
                      </td>
                    )}

                    {/* Date */}
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap font-mono text-xs">{tx.date}</td>

                    {/* Merchant */}
                    <td className="px-4 py-3 font-medium text-slate-200">
                      {tx.merchant?.name || tx.operation}
                      {tx.confidence < 0.7 && !editMode && <span className="ml-2 text-yellow-500" title="Low confidence">⚠️</span>}
                    </td>

                    {/* Details (only in view mode) */}
                    {!editMode && (
                      <td className="px-4 py-3 text-slate-500 max-w-[180px]">
                        <span title={details} className="cursor-help">{truncDetails || '—'}</span>
                      </td>
                    )}

                    {/* Category inline dropdown */}
                    <td className="px-4 py-3">
                      <select
                        value={currentCategoryId}
                        onChange={(e) => onUpdate && onUpdate(tx.id, 'manual_category_id', parseInt(e.target.value))}
                        className="bg-[#161b22] border border-[#30363d] rounded-md px-2 py-1 text-xs text-slate-300 focus:ring-1 focus:ring-[#ff4b4b] outline-none w-full max-w-[140px]"
                      >
                        <option value="">Uncategorized</option>
                        {categories.map(cat => (
                          <option key={cat.id} value={cat.id}>{cat.name}</option>
                        ))}
                      </select>
                    </td>

                    {/* Amount */}
                    <td className="px-4 py-3 font-bold whitespace-nowrap text-right">
                      <span className={tx.amount >= 0 ? 'text-[#00d4ff]' : 'text-[#ff4b4b]'}>
                        {tx.amount >= 0 ? '+' : '-'}€{Math.abs(tx.amount).toLocaleString('it-IT', { minimumFractionDigits: 2 })}
                      </span>
                    </td>

                    {/* Status badge */}
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-tighter ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>

                    {/* Extra cols for Edit Mode */}
                    {editMode && (
                      <>
                        <td className="px-4 py-3 text-center">
                          <input
                            type="checkbox"
                            checked={currentStatus === 'verified'}
                            onChange={() => onUpdate && onUpdate(tx.id, 'status', currentStatus === 'verified' ? 'classified' : 'verified')}
                            className="w-4 h-4 rounded accent-[#ff4b4b] cursor-pointer"
                          />
                        </td>
                        <td className="px-4 py-3 text-center">
                          {tx.ai_reasoning ? (
                            <button
                              onClick={() => setExpandedId(isExpanded ? null : tx.id)}
                              className={`p-1.5 rounded-lg transition-colors ${isExpanded ? 'bg-[#ff4b4b]/20 text-[#ff4b4b]' : 'text-slate-600 hover:text-slate-300'}`}
                              title="Show AI Reasoning"
                            >
                              <Brain size={14} />
                            </button>
                          ) : (
                            <span className="text-slate-700">—</span>
                          )}
                        </td>
                      </>
                    )}
                  </tr>

                  {/* Inline AI Reasoning expander */}
                  {isExpanded && tx.ai_reasoning && (
                    <tr className="border-b border-[#21262d] bg-black/20">
                      <td colSpan={editMode ? 9 : 6} className="px-8 py-4">
                        <div className="flex items-start gap-4 max-w-3xl">
                          <Brain size={18} className="text-[#ff4b4b] mt-0.5 shrink-0" />
                          <div>
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">AI Categorization Reasoning</p>
                            <p className="text-sm text-slate-300 italic leading-relaxed bg-[#161b22] p-4 rounded-xl border border-[#30363d] shadow-2xl">{tx.ai_reasoning}</p>
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
      </div>

      {/* Row counter */}
      <div className="px-6 py-4 border-t border-[#30363d] text-xs text-slate-500 flex justify-between items-center bg-[#161b22]">
        <span>Showing <strong>{sorted.length}</strong> of <strong>{transactions.length}</strong> transactions</span>
        {editMode && selectedIds.length > 0 && <span className="text-[#ff4b4b] font-bold">{selectedIds.length} items selected for action</span>}
      </div>
    </div>
  );
};

export default TransactionsTable;
