import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import ConfigModal from '../components/ConfigModal';
import HITLModal from '../components/HITLModal';

const MainLayout = () => {
  const [showConfig, setShowConfig] = useState(
    () => !localStorage.getItem('ai_config')
  );
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState(
    localStorage.getItem('theme') || 'light'
  );

  const [hitlOpen, setHitlOpen] = useState(false);
  const [hitlData, setHitlData] = useState({
    step: '',     // Changed from tabName to step for clarity
    message: '',
    reason: '',
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    // Global function to trigger the HITL pop-up from ANY component
    (window as any).triggerHITL = (
      step: string,
      message: string,
      reason: string
    ) => {
      setHitlData({
        step,
        message,
        reason,
      });
      setHitlOpen(true);
    };

    // Fixed: window.openAIConfig for the settings button in sidebar
    (window as any).openAIConfig = () => setShowConfig(true);

    return () => {
      window.openAIConfig = undefined;
      window.triggerHITL = undefined;
    };
  }, []);

  return (
    <div className="h-screen flex overflow-hidden bg-app">
      <Sidebar
        isOpen={sidebarOpen}
        toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        theme={theme}
        toggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        openConfig={() => setShowConfig(true)}
      />

      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="w-full min-w-0 p-4 lg:p-6 xl:p-8">
          <Outlet />
        </div>
      </main>

      {showConfig && (
        <ConfigModal
          isOpen={showConfig}
          onClose={() => setShowConfig(false)}
        />
      )}

      {/* HITL Notification Pop-up */}
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
