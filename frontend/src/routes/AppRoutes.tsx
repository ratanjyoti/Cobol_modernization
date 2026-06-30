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


// Modernization Pipeline (Separated)
import ModernizationPlan from '../pages/ModernizationPlan'; // Import separately
import CodeGeneration from '../pages/CodeGeneration';       // Import separately
import ModernizerChat from '../pages/ModernizerChat';

// System Operations
import MissionControl from '../pages/MissionControl';
import SystemAdmin from '../pages/SystemAdmin'; // Hub for Prompts & Settings
import PromptStudio from '../pages/PromptStudio'; // <--- ADD THIS IMPORT
import Settings from '../pages/Settings';   
// ... existing imports
// ... imports stay the same

const AppRoutes = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />

          {/* DISCOVERY HUB: Added this missing route! */}
          <Route path="discovery" element={<SystemDiscovery />} /> {/* HUB */}
          <Route path="source-files" element={<SourceFiles />} /> 
          <Route path="reverse-engineering" element={<ReverseEngineering />} />
          <Route path="business-logic" element={<BusinessLogic />} />
          
          {/* Modernization (Split into two separate tabs) */}
          <Route path="modernization-plan" element={<ModernizationPlan />} />
          <Route path="code-generation" element={<CodeGeneration />} />
          
          <Route path="chat" element={<ModernizerChat />} />
          <Route path="mission-control" element={<MissionControl />} />
          
          {/* ADMIN HUB */}
          <Route path="prompt-studio" element={<PromptStudio />} /> 
          <Route path="settings" element={<Settings />} />
          
          <Route path="admin" element={<SystemAdmin />} />
                    
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Route>
      </Routes>
    </Router>
  );
};



export default AppRoutes;
