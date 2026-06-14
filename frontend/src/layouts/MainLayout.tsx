import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header';
import ConfigModal from '../components/ConfigModal';

const MainLayout = () => {
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    // Check if AI configuration exists in localStorage
    const config = localStorage.getItem('ai_config');
    if (!config) {
      setShowConfig(true);
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <main className="p-8 max-w-7xl mx-auto">
        <Outlet />
      </main>
      
      {/* The Configuration Modal */}
      <ConfigModal 
        isOpen={showConfig} 
        onClose={() => setShowConfig(false)} 
      />
    </div>
  );
};

export default MainLayout;
