export const NAV_METADATA = {
  '/projects': {
    title: 'Projects',
    description: 'The Project Hub. This is where you create new migration projects or resume old ones. Think of it as your folder system for different legacy applications.'
  },
  '/source-files': {
    title: 'Source Files',
    description: 'The Ingestion Gate. Upload your legacy code via ZIP or GitHub. The system automatically scans the files to identify if they are COBOL, JCL, or Telon.'
  },
  '/discovery': {
    title: 'Discovery',
    description: 'The Architectural Map. We scan your code for connections (CALLs and COPY-books) to build a visual graph, showing exactly how your programs talk to each other.'
  },
  '/business-logic': {
    title: 'Business Logic',
    description: 'The Translation Phase. We turn complex technical COBOL code into plain English "Business Rules" so you can verify the logic without needing to read the legacy code.'
  },
  '/dashboard': {
    title: 'Migration Plan',
    description: 'The Blueprint. We map out how the legacy COBOL paragraphs will be reorganized into modern Java or C# classes and methods before any code is generated.'
  },
  '/code-generation': {
    title: 'Code Generation',
    description: 'The AI Factory. This is where the magic happens—the system converts the verified business rules into high-quality, modern, and maintainable source code.'
  },
  '/mission-control': {
    title: 'Mission Control',
    description: 'The Quality Gate. We run the code through a "Compile-Test-Fix" loop, automatically fixing bugs until the code is 100% syntactically healthy.'
  },
};
