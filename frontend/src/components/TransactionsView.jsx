import React from 'react';
import { motion } from 'framer-motion';
import TransactionsTable from './TransactionsTable';
import { Search, Filter } from 'lucide-react';

const TransactionsView = ({ transactions, categories, onUpdate }) => {
  const [searchTerm, setSearchTerm] = React.useState('');
  const [editMode, setEditMode] = React.useState(false);
  const [selectedIds, setSelectedIds] = React.useState([]);

  const [pendingChanges, setPendingChanges] = React.useState({});
  const [pendingDeletions, setPendingDeletions] = React.useState(new Set());

  const filteredTransactions = transactions.filter(tx => 
    !pendingDeletions.has(tx.id) &&
    ((tx.merchant?.name || tx.operation || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (tx.details || '').toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleDeleteSelected = () => {
    setPendingDeletions(prev => {
      const next = new Set(prev);
      selectedIds.forEach(id => next.add(id));
      return next;
    });
    setSelectedIds([]);
  };

  const handleLocalUpdate = (txId, field, value) => {
    setPendingChanges(prev => ({
      ...prev,
      [txId]: { ...prev[txId], [field]: value }
    }));
  };

  const handleSaveAll = async () => {
    try {
      const changes = Object.entries(pendingChanges).map(([id, data]) => ({ id: parseInt(id), ...data }));
      const deletedIds = Array.from(pendingDeletions);
      
      if (onUpdate) {
        // We assume onUpdate can handle a bulk object or we loop
        // The architecture doc says: log_feedback_and_update_silver(changes, deleted_ids)
        await onUpdate({ changes, deleted_ids: deletedIds });
      }
      
      setPendingChanges({});
      setPendingDeletions(new Set());
      alert("Changes saved successfully!");
    } catch (err) {
      console.error("Save error:", err);
    }
  };

  const hasChanges = Object.keys(pendingChanges).length > 0 || pendingDeletions.size > 0;

  return (
    <motion.div 
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex flex-col gap-6"
    >
      <div className="flex justify-between items-center bg-[#111827] p-3 rounded border border-[#374151]/50 mb-2">
        <div className="flex items-center gap-6">
          <div className="text-xs text-slate-500 font-bold uppercase tracking-widest">
            Showing <span className="text-white">{filteredTransactions.length}</span> of <span className="text-white">{transactions.length}</span> transactions
          </div>
          <div className="w-px h-4 bg-[#374151]" />
          <label className="flex items-center gap-3 cursor-pointer">
            <span className={`text-[10px] font-black uppercase tracking-widest ${!editMode ? 'text-white' : 'text-slate-500'}`}>View</span>
            <div 
              className={`w-10 h-5 rounded-full relative transition-colors ${editMode ? 'bg-[#ff4b4b]' : 'bg-[#374151]'}`}
              onClick={() => setEditMode(!editMode)}
            >
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-lg transition-all ${editMode ? 'left-5.5' : 'left-0.5'}`} style={{ left: editMode ? '1.375rem' : '0.125rem' }} />
            </div>
            <span className={`text-[10px] font-black uppercase tracking-widest ${editMode ? 'text-white' : 'text-slate-500'}`}>Edit</span>
          </label>
        </div>

        <div className="flex gap-2">
          {editMode && hasChanges && (
            <button 
              onClick={handleSaveAll}
              className="btn-primary bg-emerald-600 border-emerald-500 hover:bg-emerald-500 flex items-center gap-2"
            >
              💾 Save Changes
            </button>
          )}
          {editMode && selectedIds.length > 0 && (
            <button 
              onClick={handleDeleteSelected}
              className="btn-primary flex items-center gap-2"
            >
              🗑️ Delete Selected ({selectedIds.length})
            </button>
          )}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
            <input 
              type="text" 
              placeholder="Search..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="st-input pl-9 w-40 py-1.5 text-xs rounded"
            />
          </div>
          <button 
            onClick={() => {
              const headers = ["Date", "Merchant", "Operation", "Details", "Amount", "Category", "Status"];
              const rows = filteredTransactions.map(tx => [
                tx.date,
                tx.merchant?.name || "",
                tx.operation,
                tx.details,
                tx.amount,
                tx.manual_category?.name || tx.ai_category?.name || "Uncategorized",
                tx.status
              ]);
              const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].map(e => e.join(",")).join("\n");
              const encodedUri = encodeURI(csvContent);
              const link = document.createElement("a");
              link.setAttribute("href", encodedUri);
              link.setAttribute("download", `transactions_${new Date().toISOString().split('T')[0]}.csv`);
              document.body.appendChild(link);
              link.click();
            }}
            className="btn-secondary flex items-center gap-2 uppercase text-[10px] font-black tracking-widest"
          >
            Export CSV
          </button>
        </div>
      </div>

      <TransactionsTable 
        transactions={filteredTransactions} 
        categories={categories} 
        onUpdate={handleLocalUpdate} 
        editMode={editMode}
        selectedIds={selectedIds}
        setSelectedIds={setSelectedIds}
        pendingChanges={pendingChanges}
      />
    </motion.div>
  );
};

export default TransactionsView;
