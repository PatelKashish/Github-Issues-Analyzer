import os
import re
import json
import requests
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import openai
from datetime import datetime
import logging
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
GITHUB_API_BASE = "https://api.github.com"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # Optional, for higher rate limits

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

class GitHubIssueAnalyzer:
    """Core class for analyzing GitHub issues using AI."""
    
    def __init__(self):
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Issue-Analyzer/1.0'
        }
        if GITHUB_TOKEN:
            self.headers['Authorization'] = f'token {GITHUB_TOKEN}'
    
    def parse_github_url(self, url: str) -> tuple[str, str]:
        """Parse GitHub repository URL to extract owner and repo name."""
        # Remove trailing slash and .git if present
        url = url.rstrip('/').replace('.git', '')
        
        # Handle different GitHub URL formats
        patterns = [
            r'https://github\.com/([^/]+)/([^/]+)',
            r'git@github\.com:([^/]+)/([^/]+)',
            r'github\.com/([^/]+)/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                return match.group(1), match.group(2)
        
        raise ValueError("Invalid GitHub repository URL format")
    
    def fetch_issue_data(self, repo_url: str, issue_number: int) -> Dict[str, Any]:
        """Fetch issue data from GitHub API."""
        try:
            owner, repo = self.parse_github_url(repo_url)
            
            # Fetch issue details
            issue_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}"
            issue_response = requests.get(issue_url, headers=self.headers)
            
            if issue_response.status_code == 404:
                raise ValueError(f"Issue #{issue_number} not found in {owner}/{repo}")
            elif issue_response.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded. Please try again later.")
            elif issue_response.status_code != 200:
                raise ValueError(f"Failed to fetch issue data: {issue_response.status_code}")
            
            issue_data = issue_response.json()
            
            # Fetch comments
            comments_url = issue_data['comments_url']
            comments_response = requests.get(comments_url, headers=self.headers)
            comments_data = comments_response.json() if comments_response.status_code == 200 else []
            
            return {
                'title': issue_data['title'],
                'body': issue_data['body'] or '',
                'state': issue_data['state'],
                'labels': [label['name'] for label in issue_data['labels']],
                'created_at': issue_data['created_at'],
                'updated_at': issue_data['updated_at'],
                'user': issue_data['user']['login'],
                'comments_count': issue_data['comments'],
                'comments': [
                    {
                        'body': comment['body'],
                        'user': comment['user']['login'],
                        'created_at': comment['created_at']
                    }
                    for comment in comments_data[:10]  # Limit to first 10 comments
                ]
            }
            
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch data from GitHub: {str(e)}")
    
    def create_analysis_prompt(self, issue_data: Dict[str, Any]) -> str:
        """Create a well-structured prompt for the LLM."""
        
        # Truncate long content to avoid token limits
        title = issue_data['title'][:200]
        body = issue_data['body'][:2000] if issue_data['body'] else "No description provided"
        
        comments_text = ""
        if issue_data['comments']:
            comments_text = "\n\nComments:\n"
            for i, comment in enumerate(issue_data['comments'][:5]):  # Limit to 5 comments
                comment_body = comment['body'][:500]  # Truncate long comments
                comments_text += f"Comment {i+1} by {comment['user']}: {comment_body}\n"
        
        existing_labels = ", ".join(issue_data['labels']) if issue_data['labels'] else "None"
        
        prompt = f"""Analyze the following GitHub issue and provide a structured summary in JSON format.

Issue Title: {title}

Issue Description:
{body}
{comments_text}

Existing Labels: {existing_labels}
Issue State: {issue_data['state']}
Created by: {issue_data['user']}

Please analyze this issue and respond with ONLY a valid JSON object in the following format:
{{
    "summary": "A concise one-sentence summary of the user's problem or request",
    "type": "One of: bug, feature_request, documentation, question, or other",
    "priority_score": "A number from 1-5 with brief justification (format: '3 - Moderate impact on user experience')",
    "suggested_labels": ["2-3 relevant labels like 'bug', 'UI', 'enhancement', etc."],
    "potential_impact": "Brief description of potential user impact (especially for bugs)"
}}

Guidelines:
- For priority_score: 1=Low/Minor, 2=Low-Medium, 3=Medium, 4=High, 5=Critical
- Focus on the core issue, not just implementation details
- Suggested labels should be concise and commonly used in GitHub projects
- If it's not a bug, still describe potential positive impact for features/improvements

Respond with only the JSON object, no additional text."""

        return prompt
    
    def analyze_with_ai(self, prompt: str) -> Dict[str, Any]:
        """Analyze the issue using OpenAI's GPT model."""
        if not OPENAI_API_KEY:
            # Fallback analysis when no API key is provided
            logger.warning("⚠️ OpenAI API Key not configured. Using fallback analysis.")
            return self.fallback_analysis(prompt)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert software developer analyzing GitHub issues. Respond only with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response to ensure valid JSON
            if result_text.startswith('```json'):
                result_text = result_text[7:-3]
            elif result_text.startswith('```'):
                result_text = result_text[3:-3]
            
            return json.loads(result_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self.fallback_analysis(prompt)
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self.fallback_analysis(prompt)
    
    def fallback_analysis(self, prompt: str) -> Dict[str, Any]:
        """Provide a basic analysis when AI is not available."""
        # Extract basic info from the prompt for fallback
        lines = prompt.split('\n')
        title = ""
        for line in lines:
            if line.startswith("Issue Title:"):
                title = line.replace("Issue Title:", "").strip()
                break
        
        # Basic heuristic analysis
        issue_type = "other"
        priority = "2 - Unable to fully analyze without AI"
        labels = ["needs-triage"]
        
        if any(word in title.lower() for word in ['bug', 'error', 'broken', 'crash', 'fail']):
            issue_type = "bug"
            priority = "3 - Potential bug reported"
            labels = ["bug", "needs-investigation"]
        elif any(word in title.lower() for word in ['feature', 'add', 'enhancement', 'improve']):
            issue_type = "feature_request"
            priority = "2 - Feature request"
            labels = ["enhancement", "feature-request"]
        elif any(word in title.lower() for word in ['doc', 'readme', 'guide', 'help']):
            issue_type = "documentation"
            labels = ["documentation"]
        
        return {
            "summary": f"Issue analysis: {title[:100]}..." if len(title) > 100 else title,
            "type": issue_type,
            "priority_score": priority,
            "suggested_labels": labels,
            "potential_impact": "Unable to determine impact without full AI analysis. Please configure OpenAI API key for detailed analysis."
        }

# Initialize analyzer
analyzer = GitHubIssueAnalyzer()

@app.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

@app.route('/api/analyze', methods=['POST'])
def analyze_issue():
    """API endpoint for analyzing GitHub issues."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        repo_url = data.get('repo_url', '').strip()
        issue_number = data.get('issue_number')
        
        # Validation
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        if not issue_number:
            return jsonify({'error': 'Issue number is required'}), 400
        
        try:
            issue_number = int(issue_number)
        except ValueError:
            return jsonify({'error': 'Issue number must be a valid integer'}), 400
        
        if issue_number <= 0:
            return jsonify({'error': 'Issue number must be positive'}), 400
        
        # Fetch and analyze the issue
        logger.info(f"Analyzing issue #{issue_number} from {repo_url}")
        
        issue_data = analyzer.fetch_issue_data(repo_url, issue_number)
        prompt = analyzer.create_analysis_prompt(issue_data)
        analysis = analyzer.analyze_with_ai(prompt)
        
        # Add metadata
        result = {
            'analysis': analysis,
            'metadata': {
                'repository': repo_url,
                'issue_number': issue_number,
                'issue_title': issue_data['title'],
                'issue_state': issue_data['state'],
                'analyzed_at': datetime.utcnow().isoformat() + 'Z',
                'existing_labels': issue_data['labels']
            }
        }
        
        logger.info(f"Successfully analyzed issue #{issue_number}")
        return jsonify(result)
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'ai_configured': bool(OPENAI_API_KEY),
        'github_token_configured': bool(GITHUB_TOKEN)
    })

if __name__ == '__main__':
    # Create templates and static directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)