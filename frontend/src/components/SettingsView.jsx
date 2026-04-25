import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Plus, Edit2, Save, X, Trash2, CheckCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const AI_MODELS = [
  'qwen3:8b',
  'qwen3:14b',
  'gemma3:4b',
  'gemma3:12b',
  'llama3.1:8b',
  'mistral:7b',
  'phi4:14b',
];

const SettingsView = () => {
  const [profiles, setProfiles] = useState([]);
  const [editingProfile, setEditingProfile] = useState(null);
  const [isNew, setIsNew] = useState(false);
  const [categories, setCategories] = useState([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryType, setNewCategoryType] = useState('expense');

  useEffect(() => {
    fetchProfiles();
    fetchCategories();
  }, []);

  const fetchProfiles = async () => {
    try {
      const res = await axios.get(`${API_BASE}/profiles/`);
      setProfiles(res.data);
    } catch (err) {
      console.error("Error fetching profiles:", err);
    }
  };

  const fetchCategories = async () => {
    try {
      const res = await axios.get(`${API_BASE}/categories/`);
      setCategories(res.data);
    } catch (err) {
      console.error("Error fetching categories:", err);
    }
  };

  const handleEdit = (profile) => {
    setEditingProfile({
      ...profile,
      config: typeof profile.config === 'string' ? JSON.parse(profile.config) : profile.config
    });
    setIsNew(false);
  };

  const handleNew = () => {
    setEditingProfile({
      name: '',
      description: '',
      config: {
        column_mapping: { date: 'Data', operation: 'Operazione', details: 'Dettagli', amount: 'Importo', category_hint: 'Categoria' },
        invert_signs: false,
        classification_model: 'qwen3:8b',
        system_prompt: ''
      }
    });
    setIsNew(true);
  };

  const handleSave = async () => {
    try {
      if (isNew) {
        await axios.post(`${API_BASE}/profiles/`, editingProfile);
      } else {
        await axios.patch(`${API_BASE}/profiles/${editingProfile.id}`, editingProfile);
      }
      setEditingProfile(null);
      fetchProfiles();
    } catch (err) {
      console.error("Error saving profile:", err);
    }
  };

  const toggleActive = async (profile) => {
    try {
      await axios.patch(`${API_BASE}/profiles/${profile.id}`, { is_active: true });
      fetchProfiles();
    } catch (err) {
      console.error("Error activating profile:", err);
    }
  };

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) return;
    try {
      await axios.post(`${API_BASE}/categories/`, { name: newCategoryName.trim(), type: newCategoryType });
      setNewCategoryName('');
      fetchCategories();
    } catch (err) {
      console.error("Error adding category:", err);
    }
  };

  const handleDeleteCategory = async (id) => {
    if (!window.confirm("Are you sure? This will affect transaction classification.")) return;
    try {
      await axios.delete(`${API_BASE}/categories/${id}`);
      fetchCategories();
    } catch (err) {
      console.error("Error deleting category:", err);
    }
  };

  const incomeCategories = categories.filter(c => c.type === 'income' || c.is_income);
  const expenseCategories = categories.filter(c => c.type !== 'income' && !c.is_income);

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-12 pb-20">

      {/* Bank Profiles Section */}
      <section className="flex flex-col gap-6">
        <div className="flex justify-between items-center">
          <h2>Bank Profiles</h2>
          <button onClick={handleNew} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New Profile
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles.map(profile => (
            <div key={profile.id} className="st-card flex flex-col gap-3 relative group">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold flex items-center gap-2 text-base">
                    {profile.name}
                    {profile.is_active && <CheckCircle size={14} className="text-emerald-400" />}
                  </h3>
                  <p className="text-sm text-slate-500">{profile.description || 'No description'}</p>
                </div>
                {!profile.is_active && (
                  <button onClick={() => toggleActive(profile)} className="text-xs px-2 py-1 border border-[#30363d] rounded hover:bg-[#30363d] transition-colors">
                    Set Active
                  </button>
                )}
              </div>
              <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => handleEdit(profile)} className="text-xs px-3 py-1 border border-[#30363d] rounded hover:bg-[#30363d] transition-colors flex items-center gap-1">
                  <Edit2 size={12} /> Edit
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Taxonomy Section */}
      <section className="flex flex-col gap-6">
        <h2>Taxonomy Management</h2>
        <div className="st-card">
          <div className="flex gap-2 mb-6">
            <input
              type="text"
              placeholder="New category name..."
              value={newCategoryName}
              onChange={e => setNewCategoryName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleAddCategory()}
              className="st-select flex-1 mb-0"
            />
            <select value={newCategoryType} onChange={e => setNewCategoryType(e.target.value)} className="st-select mb-0 w-36">
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </select>
            <button onClick={handleAddCategory} className="btn-primary px-4">Add</button>
          </div>

          <div className="grid grid-cols-2 gap-8">
            {/* Expense categories */}
            <div>
              <h3 className="text-sm font-bold mb-3 text-[#ff4b4b] uppercase tracking-wider">Expense Categories</h3>
              <div className="flex flex-col gap-1.5 max-h-64 overflow-y-auto">
                {expenseCategories.map(cat => (
                  <div key={cat.id} className="flex items-center justify-between px-3 py-2 bg-[#161b22] rounded border border-[#30363d] group">
                    <span className="text-sm">{cat.name}</span>
                    <button onClick={() => handleDeleteCategory(cat.id)} className="text-slate-600 hover:text-[#ff4b4b] opacity-0 group-hover:opacity-100 transition-all">
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
                {expenseCategories.length === 0 && <p className="text-slate-600 text-sm">No expense categories</p>}
              </div>
            </div>

            {/* Income categories */}
            <div>
              <h3 className="text-sm font-bold mb-3 text-emerald-400 uppercase tracking-wider">Income Categories</h3>
              <div className="flex flex-col gap-1.5 max-h-64 overflow-y-auto">
                {incomeCategories.map(cat => (
                  <div key={cat.id} className="flex items-center justify-between px-3 py-2 bg-[#161b22] rounded border border-[#30363d] group">
                    <span className="text-sm">{cat.name}</span>
                    <button onClick={() => handleDeleteCategory(cat.id)} className="text-slate-600 hover:text-[#ff4b4b] opacity-0 group-hover:opacity-100 transition-all">
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
                {incomeCategories.length === 0 && <p className="text-slate-600 text-sm">No income categories</p>}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Edit Profile Modal */}
      {editingProfile && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="st-card max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold">{isNew ? 'Create Profile' : 'Edit Profile'}</h3>
              <button onClick={() => setEditingProfile(null)} className="text-slate-400 hover:text-white">
                <X size={24} />
              </button>
            </div>

            <div className="flex flex-col gap-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-sm text-slate-400">Profile Name</label>
                  <input
                    type="text"
                    value={editingProfile.name}
                    onChange={e => setEditingProfile({ ...editingProfile, name: e.target.value })}
                    className="st-select mb-0"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-sm text-slate-400">AI Classification Model</label>
                  <select
                    value={editingProfile.config?.classification_model || 'qwen3:8b'}
                    onChange={e => setEditingProfile({
                      ...editingProfile,
                      config: { ...editingProfile.config, classification_model: e.target.value }
                    })}
                    className="st-select mb-0"
                  >
                    {AI_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm text-slate-400">Description</label>
                <textarea
                  value={editingProfile.description || ''}
                  onChange={e => setEditingProfile({ ...editingProfile, description: e.target.value })}
                  className="st-select mb-0 h-16 resize-none"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm text-slate-400">Custom System Prompt (leave empty for default)</label>
                <textarea
                  value={editingProfile.config?.system_prompt || ''}
                  onChange={e => setEditingProfile({
                    ...editingProfile,
                    config: { ...editingProfile.config, system_prompt: e.target.value }
                  })}
                  className="st-select mb-0 h-32 resize-none font-mono text-xs"
                  placeholder="You are a financial assistant. Classify the following transaction..."
                />
              </div>

              <div className="border-t border-[#30363d] pt-4">
                <h4 className="font-semibold mb-4 text-sm">Column Mapping</h4>
                <div className="grid grid-cols-2 gap-3">
                  {Object.keys(editingProfile.config?.column_mapping || {}).map(key => (
                    <div key={key} className="flex flex-col gap-1">
                      <label className="text-xs text-slate-500 uppercase">{key}</label>
                      <input
                        type="text"
                        value={editingProfile.config.column_mapping[key]}
                        onChange={e => {
                          const newMapping = { ...editingProfile.config.column_mapping, [key]: e.target.value };
                          setEditingProfile({ ...editingProfile, config: { ...editingProfile.config, column_mapping: newMapping } });
                        }}
                        className="st-select mb-0 text-sm"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={editingProfile.config?.invert_signs || false}
                  onChange={e => setEditingProfile({
                    ...editingProfile,
                    config: { ...editingProfile.config, invert_signs: e.target.checked }
                  })}
                  className="w-4 h-4 accent-[#ff4b4b]"
                />
                <label className="text-sm">Invert Amount Signs</label>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setEditingProfile(null)} className="px-5 py-2 text-slate-400 hover:text-white transition-colors">Cancel</button>
                <button onClick={handleSave} className="btn-primary flex items-center gap-2 px-6">
                  <Save size={16} /> Save Profile
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  );
};

export default SettingsView;
