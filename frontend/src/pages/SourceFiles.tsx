import { useState, type ChangeEvent } from 'react';
import { Upload, FileText, CheckCircle2, Clock, AlertCircle, Layers } from 'lucide-react';

interface CobolFile {
  id: string;
  name: string;
  size: number; // in lines
  status: 'Pending' | 'Chunking' | 'Analyzed' | 'Error';
  chunks: number;
}

const SourceFiles = () => {
  const [files, setFiles] = useState<CobolFile[]>([
    { id: '1', name: 'ACCOUNT-PROC.cbl', size: 1200, status: 'Analyzed', chunks: 1 },
    { id: '2', name: 'MAIN-SVR.cbl', size: 4500, status: 'Chunking', chunks: 15 },
    { id: '3', name: 'REPORT-GEN.cbl', size: 800, status: 'Pending', chunks: 1 },
  ]);

  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = e.target.files;
    if (!uploadedFiles) return;

    // Mocking the "File Size Check" logic from Layer 2
    const newFiles: CobolFile[] = Array.from(uploadedFiles).map((file) => {
      const mockSize = Math.floor(Math.random() * 5000); // Mocking line count
      return {
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: mockSize,
        status: mockSize > 3000 ? 'Chunking' : 'Pending',
        chunks: mockSize > 3000 ? Math.ceil(mockSize / 300) : 1,
      };
    });

    setFiles([...files, ...newFiles]);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Analyzed': return <CheckCircle2 size={16} className="text-green-400" />;
      case 'Chunking': return <Layers size={16} className="text-blue-400 animate-spin" />;
      case 'Pending': return <Clock size={16} className="text-slate-400" />;
      default: return <AlertCircle size={16} className="text-red-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Source Files</h1>
          <p className="text-slate-400">Upload and analyze your COBOL source code.</p>
        </div>
        
        <label className="cursor-pointer bg-accent hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-bold transition-all flex items-center gap-2">
          <Upload size={18} />
          Upload COBOL Files
          <input type="file" multiple className="hidden" onChange={handleFileUpload} accept=".cbl,.cob" />
        </label>
      </div>

      {/* File Analysis Table */}
      <div className="bg-panel border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-800/50 text-slate-300 text-xs uppercase tracking-wider">
              <th className="p-4 font-semibold">File Name</th>
              <th className="p-4 font-semibold">Size (Lines)</th>
              <th className="p-4 font-semibold">Analysis Status</th>
              <th className="p-4 font-semibold">Chunks</th>
              <th className="p-4 font-semibold">Action</th>
            </tr>
          </thead>
          <tbody className="text-slate-300">
            {files.map((file) => (
              <tr key={file.id} className="border-t border-slate-700 hover:bg-slate-800/30 transition-colors">
                <td className="p-4 flex items-center gap-3">
                  <FileText size={16} className="text-slate-500" />
                  <span className="font-medium">{file.name}</span>
                </td>
                <td className="p-4 text-sm">{file.size} LLOC</td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(file.status)}
                    <span className="text-sm">{file.status}</span>
                  </div>
                </td>
                <td className="p-4 text-sm">
                  {file.chunks > 1 ? (
                    <span className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-xs border border-blue-500/30">
                      {file.chunks} Chunks
                    </span>
                  ) : (
                    <span className="text-slate-500 text-xs">Single File</span>
                  )}
                </td>
                <td className="p-4">
                  <button 
                    disabled={file.status !== 'Analyzed'}
                    className={`text-xs px-3 py-1 rounded transition-all ${
                      file.status === 'Analyzed' 
                      ? 'bg-slate-700 hover:bg-slate-600 text-white' 
                      : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    }`}
                  >
                    View Analysis
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Layer 2 Explanation Card */}
      <div className="bg-blue-500/5 border border-blue-500/20 p-4 rounded-xl">
        <div className="flex items-center gap-2 text-blue-400 mb-2 font-bold text-sm">
          <Layers size={16} />
          <span>Layer 2: Chunking Orchestrator Logic</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          Files <span className="text-white font-semibold">{"< 3000 lines"}</span> are processed directly. 
          Files <span className="text-white font-semibold">{"> 3000 lines"}</span> are automatically split 
          into chunks of 300 lines with a 300-line overlap to preserve context across AI prompts.
        </p>
      </div>
    </div>
  );
};

export default SourceFiles;
