import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import HITLModal from '../components/HITLModal';
import Sidebar from '../components/Sidebar';

const MainLayout = () => {
  const [theme, setTheme] = useState(
    localStorage.getItem('theme') || 'light'
  );
  const [sidebarOpen, setSidebarOpen] = useState(() => localStorage.getItem('sidebarOpen') !== 'false');

  const toggleSidebar = () => {
    setSidebarOpen((open) => {
      const nextOpen = !open;
      localStorage.setItem('sidebarOpen', String(nextOpen));
      return nextOpen;
    });
  };

  const [hitlOpen, setHitlOpen] = useState(false);
  const [hitlData, setHitlData] = useState({
    step: '',
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
    (window as any).triggerHITL = (
      step: string,
      message: string,
      reason: string
    ) => {
      setHitlData({ step, message, reason });
      setHitlOpen(true);
    };

    return () => {
      window.triggerHITL = undefined;
    };
  }, []);

  return (
    <div className="app-shell h-screen w-full flex overflow-hidden" style={{ background: 'var(--corporate-bg)' }}>
      <Sidebar
        isOpen={sidebarOpen}
        toggleSidebar={toggleSidebar}
        theme={theme}
        toggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      />

      <main className="app-main min-w-0 flex-1 overflow-y-auto" style={{ background: 'var(--corporate-bg)' }}>
        <div className="app-content-shell w-full min-w-0">
          <Outlet />
        </div>
      </main>

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










