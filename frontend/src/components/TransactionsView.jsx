import React from 'react';
import { motion } from 'framer-motion';
import TransactionsTable from './TransactionsTable';
import { Search, Filter } from 'lucide-react';

const TransactionsView = ({ transactions, categories, onUpdate }) => {
  const [searchTerm, setSearchTerm] = React.useState('');

  const filteredTransactions = transactions.filter(tx => 
    (tx.merchant?.name || tx.operation || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (tx.details || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <motion.div 
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex flex-col gap-6"
    >
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Transaction History</h2>
        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input 
              type="text" 
              placeholder="Filter by merchant..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="st-input pl-9 w-48 py-2 text-sm"
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
            className="btn-primary px-4 py-2 text-sm flex items-center gap-2"
          >
            Export CSV
          </button>
          <button className="btn-primary px-4 py-2 text-sm flex items-center gap-2">
            <Filter size={16} /> Filters
          </button>
        </div>
      </div>

      <TransactionsTable 
        transactions={filteredTransactions} 
        categories={categories} 
        onUpdate={onUpdate} 
      />
    </motion.div>
  );
};

export default TransactionsView;
