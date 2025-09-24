import React, { useState } from 'react';
import { FaSearch } from 'react-icons/fa';

const SearchBar = ({ onSearch }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center w-full bg-card-white rounded-full shadow-lg p-2 focus-within:ring-2 focus-within:ring-primary-red transition-shadow duration-300">
      <FaSearch className="text-secondary-text text-lg mx-4" />
      <input
        type="text"
        className="flex-grow bg-transparent text-lg text-primary-text placeholder-gray-400 focus:outline-none"
        placeholder="Search for 'innovative tech in renewable energy'..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button type="submit" className="px-8 py-3 bg-primary-red text-white font-semibold rounded-full hover:bg-secondary-red transition-colors duration-200">
        Search
      </button>
    </form>
  );
};

export default SearchBar;
