from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import json
from flask import send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from openai import OpenAI
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

# Setup OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Setup rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

def get_date_range():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    return start_str, end_str

def get_severity(reason=''):
    if not reason:
        return 'low'
    reason = reason.lower()
    if 'class i' in reason or 'serious' in reason:
        return 'high'
    elif 'class ii' in reason or 'temporary' in reason:
        return 'medium'
    return 'low'

@app.route('/api/search', methods=['GET'])
def search_drugs():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    try:
        start_str, end_str = get_date_range()
       
        # Search FDA API
        api_url = f"https://api.fda.gov/drug/enforcement.json?search=report_date:[{start_str}+TO+{end_str}]"
        if query:
            api_url += f"+AND+(product_description:{query}+OR+reason_for_recall:{query})"
        api_url += "&limit=100"

        response = requests.get(api_url)
       
        if response.status_code != 200:
            return jsonify({'error': f'FDA API error: {response.status_code}'}), response.status_code

        data = response.json()
       
        # Print first result for debugging
        if data.get('results'):
            print("First FDA API Result:")
            print(json.dumps(data['results'][0], indent=2))

        results = []
        for recall in data.get('results', []):
            # We'll temporarily set source_url to a generic FDA page
            # until we figure out the correct URL structure
            alert = {
                'title': recall.get('product_description', '').split('.')[0],
                'description': recall.get('reason_for_recall', ''),
                'date': recall.get('recall_initiation_date', ''),
                'source': 'FDA',
                'severity': get_severity(recall.get('classification', '')),
                'category': recall.get('product_type', 'Drug'),
                'components': recall.get('openfda', {}).get('substance_name', []),
                'status': recall.get('status', ''),
                'classification': recall.get('classification', ''),
                'source_url': 'https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts'  # Temporary
            }
            results.append(alert)
           
            # Print debugging info for this recall
            print("\nRecall Information:")
            print(f"Title: {alert['title']}")
            print(f"Raw recall data: {json.dumps(recall, indent=2)}")

        return jsonify({
            'results': results,
            'total': len(results)
        })

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
def generate_summary(query, alerts):
    prompt = f"""Analyze the following drug safety alerts for {query} and provide a concise executive summary highlighting key patterns, severity trends, and important observations:

Alerts:
{[f"- {alert['date']}: {alert['severity'].upper()} - {alert['description']}" for alert in alerts]}

Please provide a professional summary in 2-3 paragraphs."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a pharmaceutical safety expert creating executive summaries for compliance reports."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        return "Error generating summary. Please review the detailed alerts below."

@app.route('/api/generate-report', methods=['POST'])
@limiter.limit("10 per minute")
def generate_report():
    try:
        data = request.json
        query = data.get('query', '')
        alerts = data.get('alerts', [])

        # Generate summary using OpenAI
        summary = generate_summary(query, alerts)
       
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
       
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        story.append(Paragraph(f"Drug Safety Report: {query}", title_style))
        story.append(Spacer(1, 12))
       
        # Date
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
        story.append(Spacer(1, 12))
       
        # Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        story.append(Paragraph(summary, styles['Normal']))
        story.append(Spacer(1, 12))
       
        # Alerts Table
        story.append(Paragraph("Detailed Alerts", styles['Heading2']))
        table_data = [['Date', 'Severity', 'Description']]
        for alert in alerts:
            table_data.append([
                alert.get('date', ''),
                alert.get('severity', '').upper(),
                alert.get('description', '')
            ])
       
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
       
        table = Table(table_data)
        table.setStyle(table_style)
        story.append(table)
       
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return send_file(
            buffer,
            download_name=f'{query.lower().replace(" ", "-")}-report.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return jsonify({'error': 'Failed to generate report'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)