import React from 'react';
import { motion } from 'framer-motion';

// Helper to create colored tags for "Sinarmas Interest"
const InterestTag = ({ interest }) => {
    if (!interest || interest === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerInterest = interest.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerInterest === 'high') colorClasses = 'bg-red-100 text-red-800';
    else if (lowerInterest === 'medium') colorClasses = 'bg-yellow-100 text-yellow-800';
    else if (lowerInterest === 'low') colorClasses = 'bg-green-100 text-green-800';
    
    return <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${colorClasses}`}>{interest}</span>;
}

// Helper to create tags for "Share Transfer Allowed?"
const ShareTag = ({ allowed }) => {
    if (!allowed || allowed === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerAllowed = allowed.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerAllowed === 'yes') colorClasses = 'bg-green-100 text-green-800';
    else if (lowerAllowed === 'no') colorClasses = 'bg-red-100 text-red-800';

    return <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${colorClasses}`}>{allowed}</span>;
}

// Helper for "Nearing Liquidity Event?"
const LiquidityEventTag = ({ eventStatus }) => {
    // Default to 'No' if the prop is falsy (null, undefined, '')
    const displayStatus = eventStatus || 'No';
    const lowerStatus = displayStatus.toLowerCase();

    let colorClasses = 'bg-gray-100 text-gray-800'; // Default for 'No'
    if (lowerStatus === 'yes') colorClasses = 'bg-green-100 text-green-800';
    
    return <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${colorClasses}`}>{displayStatus}</span>;
}


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
      {/* This div enables horizontal scrolling on smaller screens */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {/* Added all the new column headers */}
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider sticky left-0 bg-gray-50 z-10">Company</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Sector</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Overview</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Valuation</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Implied Valuation</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Latest Funding</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Latest Funding Date</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Total Funding</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Investors</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Sinarmas Interest</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Share Transfer</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Nearing Liquidity Event?</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Website</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Liquidity EZ</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Liquidity Forge</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Liquidity Nasdaq</th>
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
                {/* Company Name (sticky to the left for better scrolling) */}
                <td className="px-6 py-4 whitespace-nowrap sticky left-0 bg-white hover:bg-gray-50 z-10">
                  <div className="text-sm font-semibold text-primary-text">{company.name}</div>
                </td>
                
                {/* Sector */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {company.sector || 'N/A'}
                  </span>
                </td>

                {/* Overview (truncated) */}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 max-w-xs truncate">
                  {company.overview || 'N/A'}
                </td>

                {/* Valuation data */}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.valuation || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.implied_valuation || 'N/A'}</td>

                {/* Funding data */}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.latest_funding || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.latest_funding_date || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.total_funding || 'N/A'}</td>

                {/* Investors (truncated) */}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 max-w-xs truncate">
                  {company.investors || 'N/A'}
                </td>
                
                {/* Internal data */}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                  <InterestTag interest={company.sinarmas_interest} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                  <ShareTag allowed={company.share_transfer_allowed} />
                </td>

                <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                  <LiquidityEventTag eventStatus={company.nearing_liquidity_event} />
                </td>
                
                {/* Website */}
                 <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 hover:underline">
                  <a 
                    href={company.website ? `//${company.website.replace(/^https?:\/\//, '')}` : '#'} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()} // Prevents modal from opening when link is clicked
                  >
                    {company.website || 'N/A'}
                  </a>
                </td>

                {/* Liquidity data */}
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.liquidity_ez || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.liquidity_forge || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{company.liquidity_nasdaq || 'N/A'}</td>

              </motion.tr>
            ))}
          </motion.tbody>
        </table>
      </div>
    </div>
  );
};

export default ResultsList;
