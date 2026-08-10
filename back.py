import os
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

@app.route('/')
def home():
    """Serves page.html directly to browser without authentication"""
    return send_file('page.html')

@app.route('/api/compare', methods=['GET'])
def compare_prices():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "Missing query argument"}), 400

    print(f"\n--- Live Web Search Grounding for Hardware: {query} ---")

    prompt = f"""
    Search active e-commerce platforms in India (e.g. Robu.in, ElectronicsComp, MakerBazar, Amazon India) for current pricing and details of the hardware component: "{query}".

    Produce a structured JSON matching this exact schema:
    1. 'items': An array of up to 5 real vendor listings sorted by price:
       - 'name': Clean, standardized product title (e.g., "NEMA 17 Stepper Motor 1.2A 42Ncm").
       - 'mpn': Exact Manufacturer Part Number or SKU (e.g., 'RP2040', '17HS19-2004S', 'AMS1117-3.3').
       - 'mfr': Component manufacturer (e.g., 'STMicroelectronics', 'Raspberry Pi', 'Generic').
       - 'form_factor': Package/Module type (e.g., 'Breakout Module', 'DIP-8', 'SMD IC', 'NEMA Frame').
       - 'vendor': Vendor or site name (e.g., 'Robu.in', 'ElectronicsComp', 'MakerBazar', 'Amazon IN').
       - 'price': Unit price in INR as a floating point number.
       - 'shipping': Estimated shipping in INR as a float (default 50.0 if not listed).
       - 'link': Direct URL or search link to product on vendor site.
    2. 'compatibility_notes': An array of 2 crucial technical engineering notes for an embedded developer working with "{query}" (e.g., operating voltage tolerances, logic level shifter requirements, heat dissipation, driver IC specs).
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "items": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "name": {"type": "STRING"},
                                    "mpn": {"type": "STRING"},
                                    "mfr": {"type": "STRING"},
                                    "form_factor": {"type": "STRING"},
                                    "vendor": {"type": "STRING"},
                                    "price": {"type": "NUMBER"},
                                    "shipping": {"type": "NUMBER"},
                                    "link": {"type": "STRING"}
                                },
                                "required": ["name", "mpn", "mfr", "form_factor", "vendor", "price", "shipping", "link"]
                            }
                        },
                        "compatibility_notes": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        }
                    },
                    "required": ["items", "compatibility_notes"]
                }
            )
        )

        ai_payload = json.loads(response.text)
        
        if "items" in ai_payload and isinstance(ai_payload["items"], list):
            ai_payload["items"].sort(key=lambda x: x.get('price', 0))

        return jsonify(ai_payload)

    except Exception as e:
        print(f"GenAI Search Error: {e}")
        return jsonify({
            "items": [],
            "compatibility_notes": [f"Search Error: Unable to fetch live search telemetry for '{query}'."]
        }), 500

if __name__ == '__main__':
    print("Starting Pure-GenAI Hardware Telemetry Engine...")
    app.run(host='0.0.0.0', port=5000, debug=True)
