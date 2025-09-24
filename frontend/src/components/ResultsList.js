import React from 'react';
import { motion } from 'framer-motion';

const ResultsList = ({ companies, onCompanySelect }) => {
  if (companies.length === 0) {
    return <p className="text-center text-lg text-secondary-text py-16">No companies found. Try a different search.</p>;
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.05 }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  };

  return (
    <div className="bg-white shadow-lg rounded-xl overflow-hidden border border-border-color">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Company</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Sector</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Valuation</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Total Funding</th>
            </tr>
          </thead>
          <motion.tbody 
            className="bg-white divide-y divide-gray-200"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {companies.map((company, index) => (
              <motion.tr 
                key={company.name + index} 
                className="hover:bg-gray-50 cursor-pointer transition-colors duration-200"
                onClick={() => onCompanySelect(company)}
                variants={itemVariants}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-semibold text-primary-text">{company.name}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {company.sector || 'N/A'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.valuation || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.total_funding || 'N/A'}</td>
              </motion.tr>
            ))}
          </motion.tbody>
        </table>
      </div>
    </div>
  );
};

export default ResultsList;
