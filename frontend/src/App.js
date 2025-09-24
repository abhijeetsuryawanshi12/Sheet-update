import React, { useState } from 'react';
import axios from 'axios';
import './App.css';
import Header from './components/Header';
import SearchBar from './components/SearchBar';
import AdvancedSearch from './components/AdvancedSearch';
import ResultsList from './components/ResultsList';
import Loader from './components/Loader';
import { AnimatePresence } from 'framer-motion';

// The base URL for your FastAPI backend
const API_URL = 'http://localhost:8000';

function App() {
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSemanticSearch = async (query) => {
    if (!query) return;
    setIsLoading(true);
    setError('');
    setResults(null);
    try {
      const response = await axios.get(`${API_URL}/search`, {
        params: { q: query, limit: 20 },
      });
      setResults(response.data);
    } catch (err) {
      setError('Failed to fetch results. Please check if the backend is running.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdvancedSearch = async (filters) => {
    setIsLoading(true);
    setError('');
    setResults(null);
    
    // Remove empty filters
    const validFilters = Object.entries(filters).reduce((acc, [key, value]) => {
      if (value) {
        acc[key] = value;
      }
      return acc;
    }, {});

    try {
      const response = await axios.get(`${API_URL}/advanced-search`, {
        params: validFilters,
      });
      setResults(response.data);
    } catch (err) {
      setError('Failed to fetch results. Please check if the backend is running.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <Header />
      <main className="content-container">
        <div className="search-section">
          <h1>Company Search</h1>
          <p className="subtitle">
            Use AI-powered semantic search or apply advanced filters to find companies.
          </p>
          <SearchBar onSearch={handleSemanticSearch} />
          <AdvancedSearch onSearch={handleAdvancedSearch} />
        </div>
        
        <div className="results-section">
          <AnimatePresence>
            {isLoading && <Loader />}
            {error && <p className="error-message">{error}</p>}
            {results && <ResultsList companies={results} />}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default App;