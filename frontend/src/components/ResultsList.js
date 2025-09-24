import React from 'react';
import CompanyCard from './CompanyCard';
import './ResultsList.css';
import { motion } from 'framer-motion';

const ResultsList = ({ companies }) => {
  if (companies.length === 0) {
    return <p className="no-results">No companies found. Try a different search.</p>;
  }
  
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  };

  return (
    <motion.div 
      className="results-grid"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {companies.map((company, index) => (
        <motion.div key={company.name + index} variants={itemVariants}>
          <CompanyCard company={company} />
        </motion.div>
      ))}
    </motion.div>
  );
};

export default ResultsList;