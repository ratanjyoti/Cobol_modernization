from sqlalchemy.orm import Session
from Persistence.sqlite.models import FileChunk, ChunkAnalysis
from Agents.implementations.cobol_analyzer_agent import CobolAnalyzerAgent
from Chunking.context.chunk_context_manager import ChunkContextManager
from Agents.infrastructure.chat_client_factory import ChatClientFactory

class AnalysisProcess:
    def __init__(self, db_session: Session, llm_provider: str):
        self.db = db_session
        self.context_mgr = ChunkContextManager(db_session)
        # Get the correct LLM client (Azure or Ollama)
        self.llm_client = ChatClientFactory.get_client(llm_provider)
        self.agent = CobolAnalyzerAgent(self.llm_client)

    async def analyze_project(self, run_id: str):
        # 1. Get all chunks for the project
        chunks = self.db.query(FileChunk).filter_by(run_id=run_id).order_by(FileChunk.chunk_index).all()

        for chunk in chunks:
            # 2. Build the "Context Packet" (The Memory)
            # This pulls the Global Locks and the Sliding Window of previous chunks
            context = self.context_mgr.build_context_for_chunk(
                run_id, chunk.file_id, chunk.chunk_index
            )

            # 3. Execute the Analysis
            try:
                technical_yaml = self.agent.generate_technical_yaml(
                    chunk_content=chunk.content,
                    global_types=context["global_types"],
                    signatures=context["global_signatures"],
                    context_summary=context["summary_history"]
                )

                # 4. Store the result in SQLite
                analysis = ChunkAnalysis(
                    chunk_id=chunk.id,
                    run_id=run_id,
                    technical_yaml=technical_yaml,
                    analysis_status="COMPLETED"
                )
                self.db.add(analysis)
                self.db.commit()
                
            except Exception as e:
                print(f"Error analyzing chunk {chunk.chunk_index}: {e}")
                self.db.add(ChunkAnalysis(
                    chunk_id=chunk.id, run_id=run_id, 
                    technical_yaml="", analysis_status="FAILED"
                ))
                self.db.commit()

        return True
