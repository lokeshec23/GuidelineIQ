# backend/utils/report_generator.py

"""
PDF report generator for token usage monitoring.
Creates professional reports showing LLM consumption and costs.
"""

import os
from datetime import datetime
from typing import Dict
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class TokenUsageReportGenerator:
    """
    Generates professional PDF reports for token usage monitoring.
    """
    
    def __init__(self, output_path: str):
        """
        Initialize the report generator.
        
        Args:
            output_path: Full path where the PDF will be saved
        """
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        self.styles = getSampleStyleSheet()
        self.story = []
        
        # Custom styles
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for the report."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Info style
        self.styles.add(ParagraphStyle(
            name='InfoText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=6
        ))
        
        # Highlight style
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#27ae60'),
            fontName='Helvetica-Bold',
            spaceAfter=10
        ))
    
    def generate_report(self, summary: Dict):
        """
        Generate the complete PDF report.
        
        Args:
            summary: Token usage summary from TokenTracker.get_summary()
        """
        # Add header
        self._add_header(summary)
        
        # Add metadata section
        self._add_metadata_section(summary)
        
        # Add summary statistics
        self._add_summary_section(summary)
        
        # Add per-chunk breakdown
        self._add_chunk_breakdown(summary)
        
        # Add footer
        self._add_footer()
        
        # Build the PDF
        self.doc.build(self.story)
        print(f"✅ Token usage report generated: {self.output_path}")
    
    def _add_header(self, summary: Dict):
        """Add report header with title."""
        title = Paragraph("LLM Token Usage Report", self.styles['CustomTitle'])
        self.story.append(title)
        
        subtitle = Paragraph(
            f"GuidelineIQ Ingestion Process - {summary['investor']} v{summary['version']}",
            self.styles['InfoText']
        )
        self.story.append(subtitle)
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_metadata_section(self, summary: Dict):
        """Add metadata section with file and model information."""
        section_title = Paragraph("Process Information", self.styles['CustomSubtitle'])
        self.story.append(section_title)
        
        # Create metadata table
        metadata = [
            ["PDF File:", summary['pdf_name']],
            ["Investor:", summary['investor']],
            ["Version:", summary['version']],
            ["LLM Provider:", summary['provider'].upper()],
            ["Model:", f"{summary['model']} ({summary['model_description']})"],
            ["Start Time:", self._format_datetime(summary['start_time'])],
            ["End Time:", self._format_datetime(summary['end_time']) if summary['end_time'] else "In Progress"],
            ["Duration:", f"{summary['duration_seconds']:.2f} seconds" if summary['duration_seconds'] else "N/A"],
        ]
        
        table = Table(metadata, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_summary_section(self, summary: Dict):
        """Add summary statistics section with USD and INR."""
        section_title = Paragraph("Token Usage Summary", self.styles['CustomSubtitle'])
        self.story.append(section_title)
        
        # Summary statistics table
        summary_data = [
            ["Metric", "Value", "Cost (USD)", "Cost (INR)"],
            ["Total Chunks Processed", str(summary['total_chunks']), "-", "-"],
            ["Total Prompt Tokens", f"{summary['total_prompt_tokens']:,}", 
             f"${summary['total_prompt_tokens'] / 1_000_000 * summary['input_price_per_1m']:.6f}",
             f"₹{summary['total_prompt_tokens'] / 1_000_000 * summary['input_price_per_1m'] * summary['usd_to_inr_rate']:.4f}"],
            ["Total Completion Tokens", f"{summary['total_completion_tokens']:,}", 
             f"${summary['total_completion_tokens'] / 1_000_000 * summary['output_price_per_1m']:.6f}",
             f"₹{summary['total_completion_tokens'] / 1_000_000 * summary['output_price_per_1m'] * summary['usd_to_inr_rate']:.4f}"],
            ["Total Tokens", f"{summary['total_tokens']:,}", "-", "-"],
            ["Total Cost", "-", f"${summary['total_cost']:.6f}", f"₹{summary['total_cost_inr']:.4f}"],
        ]
        
        table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2c3e50')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 0.2*inch))
        
        # Pricing information
        pricing_info = Paragraph(
            f"<b>Pricing:</b> ${summary['input_price_per_1m']:.2f} per 1M input tokens, "
            f"${summary['output_price_per_1m']:.2f} per 1M output tokens | "
            f"<b>Exchange Rate:</b> 1 USD = ₹{summary['usd_to_inr_rate']:.2f}",
            self.styles['InfoText']
        )
        self.story.append(pricing_info)
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_chunk_breakdown(self, summary: Dict):
        """Add per-chunk breakdown table with USD and INR."""
        section_title = Paragraph("Per-Chunk Breakdown", self.styles['CustomSubtitle'])
        self.story.append(section_title)
        
        # Chunk breakdown table header
        chunk_data = [
            ["Chunk", "Pages", "Prompt", "Completion", "Total", "USD", "INR"]
        ]
        
        # Add each chunk's data
        for chunk in summary['chunk_details']:
            chunk_data.append([
                str(chunk['chunk_num']),
                chunk['page_numbers'] or "N/A",
                f"{chunk['prompt_tokens']:,}",
                f"{chunk['completion_tokens']:,}",
                f"{chunk['total_tokens']:,}",
                f"${chunk['total_cost']:.6f}",
                f"₹{chunk['total_cost_inr']:.4f}"
            ])
        
        # Calculate column widths
        col_widths = [0.6*inch, 0.7*inch, 1*inch, 1*inch, 1*inch, 1.1*inch, 1.1*inch]
        
        table = Table(chunk_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#95a5a6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_footer(self):
        """Add report footer."""
        footer_text = Paragraph(
            f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by GuidelineIQ Token Monitoring System</i>",
            self.styles['InfoText']
        )
        self.story.append(Spacer(1, 0.3*inch))
        self.story.append(footer_text)
    
    def _format_datetime(self, iso_string: str) -> str:
        """Format ISO datetime string to readable format."""
        try:
            dt = datetime.fromisoformat(iso_string)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return iso_string


def generate_token_report(summary: Dict, output_dir: str, investor: str, version: str) -> str:
    """
    Convenience function to generate a token usage report.
    
    Args:
        summary: Token usage summary from TokenTracker.get_summary()
        output_dir: Directory where the report will be saved
        investor: Investor name for filename
        version: Version string for filename
    
    Returns:
        Path to the generated PDF report
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"token_report_{investor}_{version}_{timestamp}.pdf"
    output_path = os.path.join(output_dir, filename)
    
    # Generate the report
    generator = TokenUsageReportGenerator(output_path)
    generator.generate_report(summary)
    
    return output_path
