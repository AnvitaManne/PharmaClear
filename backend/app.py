from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS  # We need this for frontend-backend communication

app = Flask(__name__)
CORS(app)  # Enable CORS

class FDAScraper:
    def __init__(self):
        self.base_url = "https://www.fda.gov/drugs/drug-safety-and-availability"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_safety_alerts(self):
        try:
            response = requests.get(f"{self.base_url}", headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            alerts = []
            # Find the safety announcement container
            announcements = soup.find_all('div', class_='content-box')
            
            for announcement in announcements:
                try:
                    title = announcement.find('h3').text.strip()
                    date_str = announcement.find('p', class_='date').text.strip()
                    description = announcement.find('p', class_='description').text.strip()
                    link = announcement.find('a')['href']
                    
                    alert = {
                        'title': title,
                        'date': date_str,
                        'description': description,
                        'source_url': f"https://www.fda.gov{link}",
                        'agency': 'FDA',
                        'severity': self._determine_severity(title, description)
                    }
                    alerts.append(alert)
                except Exception as e:
                    print(f"Error parsing announcement: {e}")
                    continue
                    
            return alerts
        except Exception as e:
            print(f"Error fetching FDA alerts: {e}")
            return []

    def _determine_severity(self, title, description):
        urgent_keywords = ['urgent', 'recall', 'serious', 'death', 'fatal', 'emergency']
        warning_keywords = ['warning', 'caution', 'alert', 'risk']
        
        title_desc = (title + ' ' + description).lower()
        
        if any(keyword in title_desc for keyword in urgent_keywords):
            return 'High'
        elif any(keyword in title_desc for keyword in warning_keywords):
            return 'Medium'
        return 'Low'

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    scraper = FDAScraper()
    alerts = scraper.fetch_safety_alerts()
    return jsonify(alerts)

if __name__ == '__main__':
    app.run(debug=True, port=5000)