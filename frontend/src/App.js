import React, { useState } from 'react';
import axios from 'axios';
import Header from './components/Header';
import SearchBar from './components/SearchBar';
import AdvancedSearch from './components/AdvancedSearch';
import ResultsList from './components/ResultsList';
import Loader from './components/Loader';
import CompanyModal from './components/CompanyModal'; // New component
import { AnimatePresence } from 'framer-motion';

const API_URL = 'http://localhost:8000';

function App() {
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedCompany, setSelectedCompany] = useState(null); // State for the modal

  const handleSearch = async (url, params) => {
    setIsLoading(true);
    setError('');
    setResults(null);
    setSelectedCompany(null);
    try {
      const response = await axios.get(url, { params });
      setResults(response.data);
    } catch (err) {
      setError('Failed to fetch results. Please check if the backend is running.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSemanticSearch = (query) => {
    if (!query) return;
    handleSearch(`${API_URL}/search`, { q: query, limit: 50 });
  };

  const handleAdvancedSearch = (filters) => {
    const validFilters = Object.entries(filters).reduce((acc, [key, value]) => {
      if (value) acc[key] = value;
      return acc;
    }, {});
    if (Object.keys(validFilters).length === 0) return;
    handleSearch(`${API_URL}/advanced-search`, validFilters);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-primary-text mb-2">Company Search</h1>
          <p className="text-lg text-secondary-text max-w-2xl mx-auto">
            Use AI-powered semantic search or apply advanced filters to find companies.
          </p>
        </div>
        
        <div className="max-w-4xl mx-auto mb-8">
          <SearchBar onSearch={handleSemanticSearch} />
          <AdvancedSearch onSearch={handleAdvancedSearch} />
        </div>
        
        <div className="relative min-h-[200px]">
            {isLoading && <Loader />}
            {error && <p className="text-center text-primary-red text-xl p-8">{error}</p>}
            {results && (
              <ResultsList 
                companies={results} 
                onCompanySelect={(company) => setSelectedCompany(company)}
              />
            )}
        </div>
      </main>

      <AnimatePresence>
        {selectedCompany && (
          <CompanyModal 
            company={selectedCompany} 
            onClose={() => setSelectedCompany(null)} 
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
