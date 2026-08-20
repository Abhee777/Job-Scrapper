from flask import Flask, render_template, request, jsonify
from duckduckgo_search import DDGS
import logging
import re
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def extract_eligibility_from_url(url, fallback_snippet):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Extract text from p, li, div
            text_blocks = [t.get_text(separator=' ', strip=True) for t in soup.find_all(['p', 'li', 'div', 'span'])]
            full_text = " ".join(text_blocks)

            keywords = ["eligibility", "qualification", "requirement", "degree", "diploma", "pass", "b.tech", "graduate", "age", "criteria", "experience"]
            sentences = full_text.split('.')
            eligibility_info = []

            for s in sentences:
                if any(k in s.lower() for k in keywords):
                    # Filter out very long generic sentences to keep it concise
                    if len(s.split()) < 50:
                        eligibility_info.append(s.strip())

            # Return first few matches or fallback
            if eligibility_info:
                # Deduplicate and return first 2
                unique_info = list(dict.fromkeys(eligibility_info))[:3]
                return " ".join(unique_info) + "."
    except Exception as e:
        logging.warning(f"Failed to fetch {url}: {e}")

    # Fallback to snippet if fetching fails or finds nothing
    keywords = ["eligibility", "qualification", "requirement", "degree", "diploma", "pass", "b.tech", "graduate", "age", "criteria", "experience"]
    sentences = fallback_snippet.split('.')
    eligibility_info = []
    for s in sentences:
        if any(k in s.lower() for k in keywords):
            eligibility_info.append(s.strip())

    if eligibility_info:
        return " ".join(eligibility_info) + "."

    return "See official link for detailed eligibility and requirements."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query is required", "results": []})

    # Restrict to government sites and target job related keywords
    search_query = f"{query} site:gov.in (job OR recruitment)"

    results_list = []
    try:
        with DDGS() as ddgs:
            # Get up to 15 results
            results = ddgs.text(search_query, max_results=15)
            for r in results:
                title = r.get('title', '')
                href = r.get('href', '')
                body = r.get('body', '')

                # Try to extract eligibility from actual URL or fallback to snippet
                eligibility = extract_eligibility_from_url(href, body)

                results_list.append({
                    "title": title,
                    "link": href,
                    "snippet": body,
                    "eligibility": eligibility
                })
    except Exception as e:
        logging.error(f"Search error: {e}")
        return jsonify({"error": str(e), "results": []}), 500

    return jsonify({"results": results_list})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
