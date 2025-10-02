import React from 'react';
import { motion } from 'framer-motion';
import { 
  FaTimes, FaBuilding, FaGlobe, FaFileInvoiceDollar, FaChartBar, FaChartLine, FaInfoCircle,
  FaTags, FaHandHoldingUsd, FaArrowUp, FaArrowDown, FaUsers, FaTable, FaBalanceScale,
  FaHandshake, FaFileSignature, FaWater
} from 'react-icons/fa';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

// NOTE: You need to install recharts for the charts to work:
// npm install recharts

// --- MOCK DATA for demonstration (Price History Only) ---
const mockPriceHistory = [
  { name: 'Q1 \'23', price: 110 }, { name: 'Q2 \'23', price: 125 },
  { name: 'Q3 \'23', price: 120 }, { name: 'Q4 \'23', price: 140 },
  { name: 'Q1 \'24', price: 155 }, { name: 'Q2 \'24', price: 150 },
];

// --- Helper Components ---
const Section = ({ title, icon, children }) => (
  <section className="mt-8">
    <div className="flex items-center gap-3 mb-4">
      <div className="text-primary-red text-xl">{icon}</div>
      <h3 className="text-xl font-bold text-primary-text">{title}</h3>
    </div>
    <div className="bg-gray-50 p-6 rounded-lg border border-border-color">
      {children}
    </div>
  </section>
);

const StatCard = ({ title, value, icon }) => (
  <div className="p-4 bg-white rounded-lg shadow-sm border border-border-color">
    <div className="flex items-start gap-3">
      <div className="text-gray-400 text-lg mt-1">{icon}</div>
      <div>
        <p className="text-sm text-secondary-text">{title}</p>
        <p className="text-lg font-bold text-primary-text">{value || 'N/A'}</p>
      </div>
    </div>
  </div>
);

const InterestTag = ({ interest }) => {
    if (!interest || interest === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerInterest = interest.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerInterest === 'high') colorClasses = 'bg-red-100 text-red-800';
    else if (lowerInterest === 'medium') colorClasses = 'bg-yellow-100 text-yellow-800';
    else if (lowerInterest === 'low') colorClasses = 'bg-green-100 text-green-800';
    return <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${colorClasses}`}>{interest}</span>;
};

const ShareTag = ({ allowed }) => {
    if (!allowed || allowed === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerAllowed = allowed.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerAllowed === 'yes') colorClasses = 'bg-green-100 text-green-800';
    else if (lowerAllowed === 'no') colorClasses = 'bg-red-100 text-red-800';
    return <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${colorClasses}`}>{allowed}</span>;
};

const parseJSON = (jsonString, fallback) => {
    if (!jsonString) return fallback;
    try {
        const data = JSON.parse(jsonString);
        return Array.isArray(data) ? data : fallback;
    } catch (e) {
        console.error("Failed to parse JSON string:", jsonString, e);
        return fallback;
    }
};

const CompanyModal = ({ company, onClose }) => {
  const priceHistory = parseJSON(company.price_history, mockPriceHistory);
  
  // --- REAL DATA PARSING ---
  // Parse the funding_history JSON string from the company data, fallback to an empty array
  const fundingHistoryTable = parseJSON(company.funding_history, []);

  // Separate the main data from the "Totals" row for special rendering
  const totalsRow = Array.isArray(fundingHistoryTable) ? fundingHistoryTable.find(row => row['Share Class'] === 'Totals') : null;
  const regularRows = Array.isArray(fundingHistoryTable) ? fundingHistoryTable.filter(row => row['Share Class'] !== 'Totals') : [];

  // Generate chart data from the parsed funding history
  const fundingHistoryChart = (() => {
    const data = regularRows || [];
    const byYear = data
      .filter(round => round['Date of Financing']) // Ensure there's a date to process
      .reduce((acc, round) => {
        const dateStr = round['Date of Financing']; // e.g., "7/22/2021"
        const year = new Date(dateStr).getFullYear().toString();
        
        // Parse amount string like "$205,900,014.30"
        const amount = parseFloat(String(round['Total Financing Size']).replace(/[^0-9.]/g, ''));
        
        if (year && !isNaN(amount)) {
          // Aggregate amounts per year, converting to millions for the chart
          acc[year] = (acc[year] || 0) + (amount / 1000000); 
        }
        return acc;
      }, {});

    // Sort data by year for the chart
    const chartData = Object.entries(byYear).map(([year, amount]) => ({ year, amount: parseFloat(amount.toFixed(2)) })).sort((a,b) => a.year.localeCompare(b.year));
    return chartData.length > 0 ? chartData : [];
  })();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 50, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-card-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-y-auto relative scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-primary-red transition-colors z-10">
          <FaTimes size={24} />
        </button>

        <div className="p-8">
          {/* Header */}
          <div className="flex items-center gap-4 mb-6 pb-6 border-b border-border-color">
            <div className="bg-red-50 p-3 rounded-xl">
              <FaBuilding className="text-primary-red text-3xl" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-primary-text">{company.name || 'N/A'}</h2>
              {company.website && (
                <a
                  href={`//${company.website.replace(/^https?:\/\//, '')}`}
                  target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-primary-red hover:underline"
                >
                  <FaGlobe /> {company.website}
                </a>
              )}
            </div>
          </div>
          
          <Section title="Company Details" icon={<FaInfoCircle />}>
            <p className="text-secondary-text mb-6 whitespace-pre-wrap">{company.summary || company.overview || 'No summary available.'}</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard title="Sector" value={company.sector} icon={<FaTags />} />
                <StatCard title="Valuation" value={company.valuation} icon={<FaFileInvoiceDollar />} />
                <StatCard title="Implied Valuation" value={company.implied_valuation} icon={<FaBalanceScale />} />
                <StatCard title="Sinarmas Interest" value={<InterestTag interest={company.sinarmas_interest} />} icon={<FaHandshake />} />
                <StatCard title="Share Transfer" value={<ShareTag allowed={company.share_transfer_allowed} />} icon={<FaFileSignature />} />
            </div>
            <h4 className="font-semibold text-primary-text mt-6 mb-2">Liquidity</h4>
             <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard title="EZ" value={company.liquidity_ez} icon={<FaWater />} />
                <StatCard title="Forge" value={company.liquidity_forge} icon={<FaWater />} />
                <StatCard title="Nasdaq" value={company.liquidity_nasdaq} icon={<FaWater />} />
            </div>
          </Section>

          <Section title="Active Market & Trade Metrics" icon={<FaChartBar />}>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
              <StatCard title="Sellers Ask" value={company.sellers_ask} icon={<FaArrowUp className="text-red-500" />} />
              <StatCard title="Buyers Bid" value={company.buyers_bid} icon={<FaArrowDown className="text-green-500" />} />
              <StatCard title="EZ Total Bid Volume" value={company.ez_total_bid_volume} icon={<FaArrowDown />} />
              <StatCard title="EZ Total Ask Volume" value={company.ez_total_ask_volume} icon={<FaArrowUp />} />
              <StatCard title="Highest Bid" value={company.highest_bid_price} icon={<FaArrowUp className="text-green-500"/>} />
              <StatCard title="Lowest Ask" value={company.lowest_ask_price} icon={<FaArrowDown className="text-red-500"/>} />
            </div>
             <h4 className="font-semibold text-primary-text mb-2">Price History</h4>
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={priceHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={['dataMin - 10', 'dataMax + 10']} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="price" stroke="#E63946" strokeWidth={2} activeDot={{ r: 8 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Section>

          <Section title="Funding Details" icon={<FaHandHoldingUsd />}>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <StatCard title="Total Funding" value={company.total_funding} icon={<FaHandHoldingUsd />} />
                <StatCard title="Latest Funding" value={company.latest_funding} icon={<FaFileInvoiceDollar />} />
                <StatCard title="Latest Funding Date" value={company.latest_funding_date} icon={<FaFileInvoiceDollar />} />
            </div>
            <div className="mb-6">
                <h4 className="font-semibold text-primary-text mb-1 flex items-center gap-2"><FaUsers /> Key Investors</h4>
                <p className="text-secondary-text">{company.investors || 'N/A'}</p>
            </div>
            <h4 className="font-semibold text-primary-text mb-2">Funding History (by Year)</h4>
             <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                    <BarChart data={fundingHistoryChart}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="year" />
                        <YAxis label={{ value: 'Amount (in millions)', angle: -90, position: 'insideLeft' }}/>
                        <Tooltip formatter={(value) => `$${value}M`} />
                        <Legend />
                        <Bar dataKey="amount" fill="#E63946" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
            <h4 className="font-semibold text-primary-text mt-6 mb-2 flex items-center gap-2"><FaTable /> Funding Rounds</h4>
             <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Date</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Share Class</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Liq. Rank</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Amount Raised</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Price/Share</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Shares Out.</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Liq. Preference</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {regularRows.length > 0 ? regularRows.map((round, index) => (
                            <tr key={index}>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round['Date of Financing'] || 'N/A'}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round['Share Class'] || 'N/A'}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round['Liquidity Rank'] || 'N/A'}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round['Total Financing Size'] || 'N/A'}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round['Issue Price'] || 'N/A'}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round['Shares Outstanding'] || 'N/A'}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round['Liquidation Preference'] || 'N/A'}</td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="7" className="text-center py-4 text-gray-500">No funding round data available.</td>
                            </tr>
                        )}
                    </tbody>
                    {totalsRow && (
                        <tfoot className="bg-gray-100 font-bold border-t-2 border-gray-300">
                            <tr>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{totalsRow['Date of Financing'] || ''}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{totalsRow['Share Class']}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{totalsRow['Liquidity Rank'] || ''}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{totalsRow['Total Financing Size']}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{totalsRow['Issue Price'] || ''}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{totalsRow['Shares Outstanding']}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{totalsRow['Liquidation Preference']}</td>
                            </tr>
                        </tfoot>
                    )}
                </table>
             </div>
          </Section>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CompanyModal;