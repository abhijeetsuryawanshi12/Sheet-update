import React from 'react';
import { motion } from 'framer-motion';

const Loader = () => {
  return (
    <motion.div 
      className="flex justify-center items-center py-16"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="w-12 h-12 border-4 border-border-color border-t-primary-red rounded-full animate-spin"></div>
    </motion.div>
  );
};

export default Loader;
