import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import Dashboard from '../pages/Dashboard';
import Projects from '../pages/Projects';
import SourceFiles from '../pages/SourceFiles';
import ReverseEngineering from '../pages/ReverseEngineering';
import DependencyGraph from '../pages/DependencyGraph';
import BusinessLogic from '../pages/BusinessLogic';
import DDDDiscovery from '../pages/DDDDiscovery';
import ModernizerChat from '../pages/ModernizerChat'; // Ensure this import exists
import ModernizationPlan from '../pages/ModernizationPlan';
import CodeGeneration from '../pages/CodeGeneration';
import MissionControl from '../pages/MissionControl';
import PromptStudio from '../pages/PromptStudio';
import Settings from '../pages/Settings';

const AppRoutes = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="source-files" element={<SourceFiles />} />
          <Route path="reverse-engineering" element={<ReverseEngineering />} />
          <Route path="dependency-graph" element={<DependencyGraph />} />
          <Route path="business-logic" element={<BusinessLogic />} />
          <Route path="ddd-discovery" element={<DDDDiscovery />} />
          <Route path="chat" element={<ModernizerChat />} /> {/* THIS LINE IS CRITICAL */}
          <Route path="modernization-plan" element={<ModernizationPlan />} />
          <Route path="code-generation" element={<CodeGeneration />} />
          <Route path="mission-control" element={<MissionControl />} />
          <Route path="prompt-studio" element={<PromptStudio />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
};

export default AppRoutes;
