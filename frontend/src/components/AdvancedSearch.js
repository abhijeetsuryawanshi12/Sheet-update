import React, { useState } from 'react';
import './AdvancedSearch.css';
import { FaFilter, FaChevronDown } from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';

const AdvancedSearch = ({ onSearch }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState({
    name: '',
    sector: '',
    valuation: '',
    website: '',
    investors: ''
  });

  const handleChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(filters);
  };

  return (
    <div className="advanced-search-container">
      <button className="toggle-button" onClick={() => setIsOpen(!isOpen)}>
        <FaFilter />
        <span>Advanced Search</span>
        <FaChevronDown className={`chevron-icon ${isOpen ? 'open' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.form
            className="advanced-form"
            onSubmit={handleSubmit}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            <div className="form-grid">
              <input type="text" name="name" placeholder="Company Name" value={filters.name} onChange={handleChange} />
              <input type="text" name="sector" placeholder="Sector (e.g., Fintech)" value={filters.sector} onChange={handleChange} />
              <input type="text" name="valuation" placeholder="Valuation (e.g., $1.2B)" value={filters.valuation} onChange={handleChange} />
              <input type="text" name="website" placeholder="Website URL" value={filters.website} onChange={handleChange} />
              <input type="text" name="investors" placeholder="Investors" value={filters.investors} onChange={handleChange} />
            </div>
            <button type="submit" className="apply-filters-button">Apply Filters</button>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AdvancedSearch;
