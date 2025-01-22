from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)