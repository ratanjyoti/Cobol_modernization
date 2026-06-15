import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header';
import ConfigModal from '../components/ConfigModal';
import HITLModal from '../components/HITLModal';

const MainLayout = () => {
  const [showConfig, setShowConfig] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  const [hitlOpen, setHitlOpen] = useState(false);
  const [hitlData, setHitlData] = useState({ tabName: '', message: '', reason: '' });

  // This effect handles the actual theme switching on the HTML element
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  useEffect(() => {
    const config = localStorage.getItem('ai_config');
    if (!config) {
      setShowConfig(true);
    }
  }, []);

  useEffect(() => {
    (window as any).openAIConfig = () => setShowConfig(true);
    (window as any).triggerHITL = (name: string, msg: string, reason: string) => {
      setHitlData({ tabName: name, message: msg, reason: reason });
      setHitlOpen(true);
    };
  }, []);

  return (
    <div className="min-h-screen transition-colors duration-300">
      {/* Pass theme and toggle function to Header */}
      <Header theme={theme} toggleTheme={toggleTheme} />
      <main className="p-8 max-w-7xl mx-auto">
        <Outlet />
      </main>
      
      <ConfigModal 
        isOpen={showConfig} 
        onClose={() => setShowConfig(false)} 
      />

      <HITLModal 
        isOpen={hitlOpen} 
        onDeny={() => setHitlOpen(false)}
        onApprove={() => setHitlOpen(false)}
        config={hitlData}
      />
    </div>
  );
};

export default MainLayout;


