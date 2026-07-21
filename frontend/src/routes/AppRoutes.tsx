import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import MainLayout from '../layouts/MainLayout';

// Core Pages
import Dashboard          from '../pages/Dashboard';
import Projects           from '../pages/Projects';

import InitialSetup from '../pages/InitialSetup';

// Reverse Engineering
import SourceFiles        from '../pages/SourceFiles';
import SystemDiscovery    from '../pages/SystemDiscovery';
import ReverseEngineering from '../pages/ReverseEngineering';
import BusinessLogic      from '../pages/BusinessLogic';

// Modernization
import ModernizationPlan  from '../pages/ModernizationPlan';
import CodeGeneration     from '../pages/CodeGeneration';
import ModernizerChat     from '../pages/ModernizerChat';

// System
import MissionControl     from '../pages/MissionControl';
import SystemAdmin        from '../pages/SystemAdmin';
import PromptStudio       from '../pages/PromptStudio';
import Settings           from '../pages/Settings';

// Page wrapper — smooth fade+slide on every route change
const PageWrapper = ({ children }: { children: React.ReactNode }) => (
  <motion.div
    initial={{ opacity: 0, y: 14 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -8 }}
    transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
  >
    {children}
  </motion.div>
);

const AnimatedRoutes = () => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location}>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />

          <Route path="dashboard"            element={<PageWrapper><Dashboard /></PageWrapper>} />
          <Route path="/initial-setup" element={<InitialSetup />} />

          <Route path="projects"             element={<PageWrapper><Projects /></PageWrapper>} />
          <Route path="discovery"            element={<PageWrapper><SystemDiscovery /></PageWrapper>} />
          <Route path="source-files"         element={<PageWrapper><SourceFiles /></PageWrapper>} />
          <Route path="reverse-engineering"  element={<PageWrapper><ReverseEngineering /></PageWrapper>} />
          <Route path="business-logic"       element={<PageWrapper><BusinessLogic /></PageWrapper>} />
          <Route path="modernization-plan"   element={<PageWrapper><ModernizationPlan /></PageWrapper>} />
          <Route path="code-generation"      element={<PageWrapper><CodeGeneration /></PageWrapper>} />
          <Route path="chat"                 element={<PageWrapper><ModernizerChat /></PageWrapper>} />
          <Route path="mission-control"      element={<PageWrapper><MissionControl /></PageWrapper>} />
          <Route path="prompt-studio"        element={<PageWrapper><PromptStudio /></PageWrapper>} />
          <Route path="settings"             element={<PageWrapper><Settings /></PageWrapper>} />
          <Route path="admin"                element={<PageWrapper><SystemAdmin /></PageWrapper>} />

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </AnimatePresence>
  );
};

const AppRoutes = () => (
  <Router>
    <AnimatedRoutes />
  </Router>
);

export default AppRoutes;

