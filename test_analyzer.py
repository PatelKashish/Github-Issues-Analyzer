import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_github_api():
    """Test GitHub API connectivity."""
    print("🔍 Testing GitHub API connectivity...")
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'GitHub-Issue-Analyzer-Test/1.0'
    }
    
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token:
        headers['Authorization'] = f'token {github_token}'
        print("   ✓ Using GitHub token for higher rate limits")
    else:
        print("   ⚠ No GitHub token found - using anonymous requests (lower rate limits)")
    
    # Test with a known public issue
    test_url = "https://api.github.com/repos/octocat/Hello-World/issues/1"
    
    try:
        response = requests.get(test_url, headers=headers)
        if response.status_code == 200:
            print("   ✓ GitHub API connection successful")
            rate_limit = response.headers.get('X-RateLimit-Remaining', 'Unknown')
            print(f"   ✓ Rate limit remaining: {rate_limit}")
            return True
        else:
            print(f"   ❌ GitHub API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ GitHub API connection failed: {e}")
        return False

def test_openai_api():
    """Test OpenAI API connectivity."""
    print("\n🤖 Testing OpenAI API connectivity...")
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("   ⚠ No OpenAI API key found - will use fallback analysis")
        return False
    
    try:
        import openai
        openai.api_key = openai_key
        
        # Test with a simple completion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API test successful'"}],
            max_tokens=10
        )
        
        if response.choices[0].message.content:
            print("   ✓ OpenAI API connection successful")
            return True
        else:
            print("   ❌ OpenAI API returned empty response")
            return False
            
    except ImportError:
        print("   ❌ OpenAI library not installed")
        return False
    except Exception as e:
        print(f"   ❌ OpenAI API connection failed: {e}")
        return False

def test_local_server():
    """Test if the Flask server can start."""
    print("\n🌐 Testing Flask application...")
    
    try:
        # Import the app to check for import errors
        from app import app, analyzer
        print("   ✓ Flask app imports successfully")
        
        # Test the analyzer class
        test_repo = "https://github.com/octocat/Hello-World"
        test_issue = 1
        
        try:
            issue_data = analyzer.fetch_issue_data(test_repo, test_issue)
            print("   ✓ Issue fetching works correctly")
            
            prompt = analyzer.create_analysis_prompt(issue_data)
            if len(prompt) > 100:  # Basic check that prompt is generated
                print("   ✓ Prompt generation works correctly")
            else:
                print("   ⚠ Prompt seems too short")
                
            return True
            
        except Exception as e:
            print(f"   ❌ Analyzer test failed: {e}")
            return False
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("   💡 Make sure you've run: pip install -r requirements.txt")
        return False

def test_full_analysis():
    """Test a complete analysis workflow."""
    print("\n🔬 Testing complete analysis workflow...")
    
    try:
        from app import analyzer
        
        # Use a well-known test issue
        test_repo = "https://github.com/octocat/Hello-World"
        test_issue = 1
        
        print(f"   📊 Analyzing issue #{test_issue} from {test_repo}")
        
        # Fetch issue data
        issue_data = analyzer.fetch_issue_data(test_repo, test_issue)
        print(f"   ✓ Fetched issue: '{issue_data['title'][:50]}...'")
        
        # Create prompt
        prompt = analyzer.create_analysis_prompt(issue_data)
        print("   ✓ Generated analysis prompt")
        
        # Run AI analysis
        analysis = analyzer.analyze_with_ai(prompt)
        print("   ✓ Completed AI analysis")
        
        # Validate output format
        required_fields = ['summary', 'type', 'priority_score', 'suggested_labels', 'potential_impact']
        missing_fields = [field for field in required_fields if field not in analysis]
        
        if not missing_fields:
            print("   ✓ Analysis output has all required fields")
            print(f"   📋 Type: {analysis['type']}")
            print(f"   ⚡ Priority: {analysis['priority_score']}")
            print(f"   🏷️ Labels: {', '.join(analysis['suggested_labels'])}")
            return True
        else:
            print(f"   ❌ Missing fields in analysis: {missing_fields}")
            return False
            
    except Exception as e:
        print(f"   ❌ Full analysis test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 GitHub Issue Analyzer - Setup Test")
    print("=" * 50)
    
    tests = [
        ("GitHub API", test_github_api),
        ("OpenAI API", test_openai_api),
        ("Flask App", test_local_server),
        ("Full Analysis", test_full_analysis)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("-" * 25)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:15} {status}")
        if not passed:
            all_passed = False
    
    print("-" * 25)
    
    if all_passed:
        print("🎉 All tests passed! Your setup is ready.")
        print("\n💡 To start the application, run: python app.py")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        print("\n💡 Common solutions:")
        print("   - Install dependencies: pip install -r requirements.txt")
        print("   - Set up API keys in .env file")
        print("   - Check your internet connection")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())