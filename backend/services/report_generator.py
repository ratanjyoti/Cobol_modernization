from datetime import datetime
import json

class ReportGenerator:
    def generate_reverse_engineering_md(self, run_id: str, db_session):
        from Persistence.sqlite.models import TechnicalAnalysis
        results = db.query(TechnicalAnalysis).filter_by(run_id=run_id).all()
        
        md = f"# Reverse Engineering Details\n\n**Generated**: {datetime.now()}\n"
        md += f"**Total Files Analyzed**: {len(results)}\n\n---\n\n"
        
        for res in results:
            data = json.loads(res.report_json)
            
            md += f"## {res.filename}\n\n"
            md += f"### Business Purpose\n{data['business_purpose']}\n\n---\n\n"
            
            md += "### Technical Analysis\n\n"
            md += f"**Program Purpose**: {data['business_purpose']}\n\n"
            
            md += "**Data Structures and Record Layouts**\n"
            for ds in data['data_structures']:
                md += f"#### {ds['structure_name']}\n"
                for field in ds['fields']:
                    md += f"- `{field['field_name']}`: {field['data_type']} - {field['description']}\n"
            
            md += "\n**Processing Logic Flow**\n"
            for step in data['logic_flow']:
                md += f"{step['step_number']}. {step['description']} (Trigger: {step['technical_trigger']})\n"
            
            md += f"\n**External Dependencies**\n- {', '.join(data['dependencies'])}\n\n"
            
            md += "**Modernization Recommendations**\n"
            for rec in data['recommendations']:
                md += f"- {rec}\n"
            
            md += "\n---\n\n"
            
        return md
