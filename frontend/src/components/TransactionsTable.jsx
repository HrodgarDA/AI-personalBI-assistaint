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

const TransactionsTable = ({ transactions, categories = [], onUpdate }) => {
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });
  const [expandedId, setExpandedId] = useState(null);

  const handleSort = (key) => {
    setSortConfig(prev =>
      prev.key === key
        ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
        : { key, direction: 'asc' }
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

  const thClass = "px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-left cursor-pointer select-none hover:text-slate-300 transition-colors";

  return (
    <div className="st-card p-0 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-[#30363d] bg-[#161b22]">
              <th className={thClass} onClick={() => handleSort('date')}>
                <span className="flex items-center gap-1">Date <SortIcon col="date" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass} onClick={() => handleSort('merchant')}>
                <span className="flex items-center gap-1">Merchant / Operation <SortIcon col="merchant" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass}>Details</th>
              <th className={thClass} onClick={() => handleSort('category')}>
                <span className="flex items-center gap-1">Category <SortIcon col="category" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass} onClick={() => handleSort('amount')}>
                <span className="flex items-center gap-1">Amount <SortIcon col="amount" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass} onClick={() => handleSort('status')}>
                <span className="flex items-center gap-1">Status <SortIcon col="status" sortConfig={sortConfig} /></span>
              </th>
              <th className={thClass + " text-center"}>Verified</th>
              <th className={thClass + " text-center"}>AI</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((tx) => {
              const badge = STATUS_BADGE[tx.status] || STATUS_BADGE.pending;
              const isExpanded = expandedId === tx.id;
              const details = tx.details || '';
              const truncDetails = details.length > 45 ? details.slice(0, 45) + '…' : details;

              return (
                <React.Fragment key={tx.id}>
                  <tr className="border-b border-[#21262d] hover:bg-white/[0.02] transition-colors">
                    {/* Date */}
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{tx.date}</td>

                    {/* Merchant */}
                    <td className="px-4 py-3 font-medium text-slate-200">
                      {tx.merchant?.name || tx.operation}
                    </td>

                    {/* Details */}
                    <td className="px-4 py-3 text-slate-500 max-w-[200px]">
                      <span title={details} className="cursor-help">{truncDetails || '—'}</span>
                    </td>

                    {/* Category inline dropdown */}
                    <td className="px-4 py-3">
                      <select
                        value={tx.manual_category?.id || tx.ai_category?.id || ''}
                        onChange={(e) => onUpdate && onUpdate(tx.id, { manual_category_id: parseInt(e.target.value) })}
                        className="bg-[#161b22] border border-[#30363d] rounded px-2 py-1 text-xs text-slate-300 focus:ring-1 focus:ring-[#ff4b4b] outline-none max-w-[160px]"
                      >
                        <option value="">Uncategorized</option>
                        {categories.map(cat => (
                          <option key={cat.id} value={cat.id}>{cat.name}</option>
                        ))}
                      </select>
                    </td>

                    {/* Amount */}
                    <td className="px-4 py-3 font-semibold whitespace-nowrap">
                      <span className={tx.amount >= 0 ? 'text-emerald-400' : 'text-[#ff4b4b]'}>
                        {tx.amount >= 0 ? '+' : ''}€{Math.abs(tx.amount).toLocaleString('it-IT', { minimumFractionDigits: 2 })}
                      </span>
                    </td>

                    {/* Status badge */}
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>

                    {/* Verified checkbox */}
                    <td className="px-4 py-3 text-center">
                      <input
                        type="checkbox"
                        checked={tx.status === 'verified'}
                        onChange={() => onUpdate && onUpdate(tx.id, {
                          status: tx.status === 'verified' ? 'classified' : 'verified'
                        })}
                        className="w-4 h-4 rounded accent-[#ff4b4b] cursor-pointer"
                      />
                    </td>

                    {/* AI Reasoning toggle */}
                    <td className="px-4 py-3 text-center">
                      {tx.ai_reasoning ? (
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : tx.id)}
                          className={`p-1.5 rounded transition-colors ${isExpanded ? 'bg-[#ff4b4b]/20 text-[#ff4b4b]' : 'text-slate-600 hover:text-slate-300'}`}
                          title="Show AI Reasoning"
                        >
                          <Brain size={14} />
                        </button>
                      ) : (
                        <span className="text-slate-700">—</span>
                      )}
                    </td>
                  </tr>

                  {/* Inline AI Reasoning expander */}
                  {isExpanded && tx.ai_reasoning && (
                    <tr className="border-b border-[#21262d] bg-[#0d1117]">
                      <td colSpan={8} className="px-6 py-4">
                        <div className="flex items-start gap-3">
                          <Brain size={16} className="text-[#ff4b4b] mt-0.5 shrink-0" />
                          <div>
                            <p className="text-xs font-semibold text-slate-400 mb-1">AI Reasoning</p>
                            <p className="text-sm text-slate-300 italic leading-relaxed">{tx.ai_reasoning}</p>
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
      <div className="px-4 py-3 border-t border-[#30363d] text-xs text-slate-500">
        Showing {sorted.length} of {transactions.length} transactions
      </div>
    </div>
  );
};

export default TransactionsTable;
