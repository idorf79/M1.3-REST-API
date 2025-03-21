# test_api.py - Student integration testing framework
import pytest
import requests
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:5000"  # Update this if your API is hosted elsewhere
API_TOKEN = "student_test_token"
HEADERS = {"X-API-Token": API_TOKEN, "Content-Type": "application/json"}

# --- Helper functions ---

def log_request(method, url, headers=None, data=None):
    """Log details of a request"""
    logger.info(f"Request: {method} {url}")
    if headers:
        logger.debug(f"Headers: {json.dumps(headers)}")
    if data:
        logger.debug(f"Data: {json.dumps(data)}")

def log_response(response):
    """Log details of a response"""
    logger.info(f"Response: {response.status_code} {response.reason}")
    try:
        content = response.json()
        logger.debug(f"Content: {json.dumps(content)}")
        return content
    except json.JSONDecodeError:
        logger.warning("Response is not valid JSON")
        logger.debug(f"Content: {response.text}")
        return None

def make_request(method, endpoint, expected_status=None, headers=None, json_data=None, retry=2, retry_delay=1):
    """Make HTTP request with logging and optional retry"""
    url = f"{BASE_URL}{endpoint}"
    request_headers = headers or HEADERS
    
    log_request(method, url, request_headers, json_data)
    
    start_time = time.time()
    response = None
    
    for attempt in range(retry + 1):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json_data,
                timeout=10
            )
            break
        except requests.exceptions.RequestException as e:
            if attempt < retry:
                logger.warning(f"Request failed. Retrying in {retry_delay}s... ({attempt+1}/{retry})")
                time.sleep(retry_delay)
            else:
                logger.error(f"Request failed after {retry} retries: {str(e)}")
                raise
    
    elapsed_time = time.time() - start_time
    logger.info(f"Request completed in {elapsed_time:.2f}s")
    
    content = log_response(response)
    
    if expected_status and response.status_code != expected_status:
        logger.error(f"Expected status {expected_status}, got {response.status_code}")
        
    return response, content

# --- Test fixtures ---

@pytest.fixture
def theme():
    """Choose your theme by uncommenting one of the options"""
    # return "space_exploration"
    # return "fantasy_rpg"
    return "smart_city"  # Default theme

@pytest.fixture
def entity_type(theme):
    """Return the first entity type for the chosen theme"""
    response, content = make_request("GET", f"/themes/{theme}")
    return content["entities"][0]["type"]

@pytest.fixture
def create_test_entity(theme, entity_type):
    """Create a test entity and return its data"""
    test_entity = {
        "name": f"Test {entity_type.title()} {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": f"Created during automated testing at {datetime.now().isoformat()}"
    }
    
    response, content = make_request(
        "POST", 
        f"/themes/{theme}/{entity_type}", 
        expected_status=201,
        json_data=test_entity
    )
    
    # Return the created entity for use in tests
    return content

# --- Basic API connectivity tests ---

def test_api_info():
    """Test that the API is reachable and returns basic info"""
    response, content = make_request("GET", "/")
    
    assert response.status_code == 200
    assert "name" in content
    assert "themes" in content
    assert "version" in content

def test_api_documentation():
    """Test that the API documentation is available"""
    response, content = make_request("GET", "/docs")
    
    assert response.status_code == 200
    assert "documentation" in content
    assert "endpoints" in content

def test_list_themes():
    """Test that we can retrieve the list of themes"""
    response, content = make_request("GET", "/themes")
    
    assert response.status_code == 200
    assert "themes" in content
    assert len(content["themes"]) > 0

# --- Theme-specific tests ---

def test_theme_details(theme):
    """Test that we can get detailed information about the selected theme"""
    response, content = make_request("GET", f"/themes/{theme}")
    
    assert response.status_code == 200
    assert "id" in content
    assert content["id"] == theme
    assert "entities" in content
    assert len(content["entities"]) > 0

def test_entity_listing_requires_auth(theme, entity_type):
    """Test that entity listing requires authentication"""
    url = f"{BASE_URL}/themes/{theme}/{entity_type}"
    response = requests.get(url)  # No auth token
    
    assert response.status_code == 401

def test_list_entities(theme, entity_type):
    """Test that we can list entities with proper authentication"""
    response, content = make_request("GET", f"/themes/{theme}/{entity_type}")
    
    assert response.status_code == 200
    assert "items" in content
    assert isinstance(content["items"], list)

# --- CRUD Operation Tests ---

def test_create_entity(theme, entity_type):
    """Test creating a new entity"""
    new_entity = {
        "name": f"New {entity_type.title()} {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": f"Created during create test at {datetime.now().isoformat()}"
    }
    
    response, content = make_request(
        "POST", 
        f"/themes/{theme}/{entity_type}", 
        expected_status=201,
        json_data=new_entity
    )
    
    assert response.status_code == 201
    assert "id" in content
    assert content["name"] == new_entity["name"]
    assert content["description"] == new_entity["description"]
    assert "created_at" in content

def test_create_entity_validation(theme, entity_type):
    """Test validation when creating an entity with missing required fields"""
    incomplete_entity = {
        "name": f"Incomplete {entity_type.title()}"
        # Missing description field
    }
    
    response, content = make_request(
        "POST", 
        f"/themes/{theme}/{entity_type}",
        json_data=incomplete_entity
    )
    
    assert response.status_code == 400
    assert "description" in content.get("description", "").lower()

def test_get_entity(theme, entity_type, create_test_entity):
    """Test retrieving a specific entity by ID"""
    entity_id = create_test_entity["id"]
    
    response, content = make_request(
        "GET", 
        f"/themes/{theme}/{entity_type}/{entity_id}"
    )
    
    assert response.status_code == 200
    assert content["id"] == entity_id
    assert content["name"] == create_test_entity["name"]

def test_update_entity(theme, entity_type, create_test_entity):
    """Test updating an existing entity"""
    entity_id = create_test_entity["id"]
    updated_data = {
        "name": f"Updated {create_test_entity['name']}",
        "description": f"Updated at {datetime.now().isoformat()}"
    }
    
    response, content = make_request(
        "PUT", 
        f"/themes/{theme}/{entity_type}/{entity_id}",
        json_data=updated_data
    )
    
    assert response.status_code == 200
    assert content["id"] == entity_id
    assert content["name"] == updated_data["name"]
    assert content["description"] == updated_data["description"]
    assert "updated_at" in content

def test_delete_entity(theme, entity_type, create_test_entity):
    """Test deleting an entity"""
    entity_id = create_test_entity["id"]
    
    response, content = make_request(
        "DELETE", 
        f"/themes/{theme}/{entity_type}/{entity_id}"
    )
    
    assert response.status_code == 200
    assert "deleted" in content
    assert content["deleted"]["id"] == entity_id
    
    # Verify it's really gone
    response, _ = make_request(
        "GET", 
        f"/themes/{theme}/{entity_type}/{entity_id}"
    )
    assert response.status_code == 404

# --- Error handling tests ---

def test_nonexistent_theme():
    """Test requesting a theme that doesn't exist"""
    response, _ = make_request("GET", "/themes/nonexistent_theme")
    assert response.status_code == 404

def test_nonexistent_entity_type(theme):
    """Test requesting an entity type that doesn't exist"""
    response, _ = make_request("GET", f"/themes/{theme}/nonexistent_entity_type")
    assert response.status_code == 404

def test_nonexistent_entity(theme, entity_type):
    """Test requesting an entity that doesn't exist"""
    response, _ = make_request("GET", f"/themes/{theme}/{entity_type}/9999")
    assert response.status_code == 404

# --- Error simulation tests ---

def test_explicit_timeout_error():
    """Test the explicit timeout error endpoint"""
    response, _ = make_request("GET", "/error-test?type=timeout", retry=0)
    assert response.elapsed.total_seconds() > 2.0

def test_explicit_rate_limit_error():
    """Test the explicit rate limit error endpoint"""
    response, content = make_request("GET", "/error-test?type=rate_limit")
    assert response.status_code == 429

def test_explicit_server_error():
    """Test the explicit server error endpoint"""
    response, content = make_request("GET", "/error-test?type=server_error")
    assert response.status_code == 500

def test_explicit_validation_error():
    """Test the explicit validation error endpoint"""
    response, content = make_request("GET", "/error-test?type=validation_error")
    assert response.status_code == 422

# --- Additional test ideas (students can implement these) ---

# TODO: Test handling of concurrent requests
# TODO: Test performance under load
# TODO: Test with invalid JSON data
# TODO: Test with very large payloads
# TODO: Test recovery after errors

# --- Custom test template ---

def test_student_custom():
    """
    This is a template for students to write their own tests.
    Replace this with your own test logic.
    """
    # Your test code here
    pass

if __name__ == "__main__":
    # This allows running individual tests for debugging
    test_api_info()
    logger.info("API info test completed successfully!")
