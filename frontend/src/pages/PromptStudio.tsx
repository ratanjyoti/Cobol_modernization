import { useState } from 'react';
import { Save, Play, FileText, AlertTriangle } from 'lucide-react';

const PromptStudio = () => {
  const [prompts, setPrompts] = useState({
    conversion: "Convert the following COBOL code to Java 21. Use Spring Boot 3 annotations. Ensure BigDecimals are used for financial calculations. Follow DDD principles.",
    refinement: "Analyze the generated Java code for performance bottlenecks. Suggest optimizations for loop structures and database queries.",
    extraction: "Extract business rules from the COBOL Procedure Division. Format as: Rule ID | Rule Name | Functional Requirement."
  });

  const handleSave = () => {
    alert("Constitution.yaml updated successfully!");
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Prompt Studio</h1>
          <p className="text-slate-400">Fine-tune the AI's behavior by editing the system constitutions.</p>
        </div>
        <button 
          onClick={handleSave}
          className="bg-accent text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 hover:bg-blue-600 transition-all"
        >
          <Save size={18} /> Save to Constitution
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {Object.entries(prompts).map(([key, value]) => (
          <div key={key} className="bg-panel border border-slate-700 rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-accent/20 rounded-lg">
                  <FileText size={18} className="text-accent" />
                </div>
                <h3 className="text-white font-bold capitalize">{key.replace('_', ' ')} Prompt</h3>
              </div>
              <button className="text-xs text-slate-400 hover:text-white flex items-center gap-1">
                <Play size={12} /> Test Prompt
              </button>
            </div>
            
            <textarea 
              value={value}
              onChange={(e) => setPrompts({...prompts, [key]: e.target.value})}
              className="w-full h-32 bg-darkbg border border-slate-600 rounded-lg p-4 text-sm text-slate-300 font-mono focus:outline-none focus:border-accent transition-all"
            />
            
            <div className="flex items-center gap-2 text-amber-400 text-[10px] uppercase font-bold">
              <AlertTriangle size={12} />
              <span>Changing this will affect all current and future chunks in the pipeline.</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PromptStudio;
