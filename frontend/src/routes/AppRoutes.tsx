import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';

// Existing Pages
import Dashboard from '../pages/Dashboard';
import Projects from '../pages/Projects';
import SourceFiles from '../pages/SourceFiles';
import ReverseEngineering from '../pages/ReverseEngineering';
import BusinessLogic from '../pages/BusinessLogic';
import ModernizerChat from '../pages/ModernizerChat';
import MissionControl from '../pages/MissionControl';

// NEW HUB Pages (Ensure these files are created in your /pages folder)
import SystemDiscovery from '../pages/SystemDiscovery'; // Replaces DependencyGraph & DDDDiscovery
import ModernizationHub from '../pages/ModernizationHub'; // Replaces ModernizationPlan & CodeGeneration
import SystemAdmin from '../pages/SystemAdmin';           // Replaces PromptStudio & Settings

const AppRoutes = () => {
  return (
    <Router>
      <Routes>
        {/* MainLayout acts as the wrapper for the Sidebar and Header */}
        <Route path="/" element={<MainLayout />}>
          
          {/* Redirect root to dashboard */}
          <Route index element={<Navigate to="/dashboard" />} />
          
          {/* Core Group */}
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          
          {/* Reverse Engineering Group */}
          <Route path="source-files" element={<SourceFiles />} />
          <Route path="reverse-engineering" element={<ReverseEngineering />} />
          <Route path="discovery" element={<SystemDiscovery />} /> {/* HUB */}
          <Route path="business-logic" element={<BusinessLogic />} />
          
          {/* Modernization Group */}
          <Route path="modernization" element={<ModernizationHub />} /> {/* HUB */}
          <Route path="chat" element={<ModernizerChat />} />
          
          {/* System Group */}
          <Route path="mission-control" element={<MissionControl />} />
          <Route path="admin" element={<SystemAdmin />} /> {/* HUB */}
          
        </Route>
      </Routes>
    </Router>
  );
};

export default AppRoutes;
