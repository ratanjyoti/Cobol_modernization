import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';

// Core Pages
import Dashboard from '../pages/Dashboard';
import Projects from '../pages/Projects';

// Reverse Engineering Pipeline (The "Discovery" Flow)
import SourceFiles from '../pages/SourceFiles';
import SystemDiscovery from '../pages/SystemDiscovery'; // Hub for Graph & DDD
import ReverseEngineering from '../pages/ReverseEngineering';
import BusinessLogic from '../pages/BusinessLogic';

// Modernization Pipeline
import ModernizationHub from '../pages/ModernizationHub'; // Hub for Plan & CodeGen
import ModernizerChat from '../pages/ModernizerChat';

// System Operations
import MissionControl from '../pages/MissionControl';
import SystemAdmin from '../pages/SystemAdmin'; // Hub for Prompts & Settings

// ... existing imports
const AppRoutes = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          
          {/* Discovery is now merged into SourceFiles */}
          <Route path="source-files" element={<SourceFiles />} /> 
          <Route path="reverse-engineering" element={<ReverseEngineering />} />
          <Route path="business-logic" element={<BusinessLogic />} />
          
          <Route path="modernization" element={<ModernizationHub />} />
          <Route path="chat" element={<ModernizerChat />} />
          <Route path="mission-control" element={<MissionControl />} />
          <Route path="admin" element={<SystemAdmin />} />
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Route>
      </Routes>
    </Router>
  );
};


export default AppRoutes;
