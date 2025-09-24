import React, { useState } from 'react';
import { FaFilter, FaChevronDown } from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';

const AdvancedSearch = ({ onSearch }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState({
    name: '', sector: '', valuation: '', website: '', investors: ''
  });

  const handleChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(filters);
  };

  return (
    <div className="mt-6 text-center">
      <button onClick={() => setIsOpen(!isOpen)} className="inline-flex items-center gap-2 px-4 py-2 text-secondary-text hover:text-primary-text transition-colors">
        <FaFilter />
        <span>Advanced Search</span>
        <FaChevronDown className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.form
            onSubmit={handleSubmit}
            initial={{ opacity: 0, height: 0, marginTop: 0 }}
            animate={{ opacity: 1, height: 'auto', marginTop: '1rem' }}
            exit={{ opacity: 0, height: 0, marginTop: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="bg-card-white p-6 rounded-xl shadow-md border border-border-color overflow-hidden"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
              <input type="text" name="name" placeholder="Company Name" value={filters.name} onChange={handleChange} className="w-full px-4 py-2 border border-border-color rounded-lg focus:ring-2 focus:ring-primary-red focus:outline-none transition" />
              <input type="text" name="sector" placeholder="Sector (e.g., Fintech)" value={filters.sector} onChange={handleChange} className="w-full px-4 py-2 border border-border-color rounded-lg focus:ring-2 focus:ring-primary-red focus:outline-none transition" />
              <input type="text" name="valuation" placeholder="Min Valuation (e.g., $1.2B)" value={filters.valuation} onChange={handleChange} className="w-full px-4 py-2 border border-border-color rounded-lg focus:ring-2 focus:ring-primary-red focus:outline-none transition" />
              <input type="text" name="website" placeholder="Website URL" value={filters.website} onChange={handleChange} className="w-full px-4 py-2 border border-border-color rounded-lg focus:ring-2 focus:ring-primary-red focus:outline-none transition" />
              <input type="text" name="investors" placeholder="Investors" value={filters.investors} onChange={handleChange} className="w-full px-4 py-2 border border-border-color rounded-lg focus:ring-2 focus:ring-primary-red focus:outline-none transition" />
            </div>
            <button type="submit" className="px-8 py-2 bg-primary-text text-white font-semibold rounded-full hover:bg-black transform hover:-translate-y-0.5 transition-all duration-200">
              Apply Filters
            </button>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AdvancedSearch;
