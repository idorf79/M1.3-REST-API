# app.py - Main REST API Server Application
import json
import random
import time
from flask import Flask, request, jsonify, abort, make_response
from flask_cors import CORS
import os
from functools import wraps
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
CORS(app)

# Configuration for different themes
THEMES = {
    "space_exploration": {
        "name": "Space Exploration API",
        "description": "API for managing space missions and astronaut data",
        "entities": ["missions", "astronauts", "spacecraft"],
    },
    "fantasy_rpg": {
        "name": "Fantasy RPG API",
        "description": "API for managing characters, quests and items in a fantasy world",
        "entities": ["characters", "quests", "items"],
    },
    "smart_city": {
        "name": "Smart City API",
        "description": "API for managing smart city infrastructure and services",
        "entities": ["traffic_sensors", "public_transport", "energy_consumption"],
    }
}

# Data storage (in-memory for simplicity)
data_store = {}
for theme, info in THEMES.items():
    data_store[theme] = {}
    for entity in info["entities"]:
        data_store[theme][entity] = []

# Error simulation configuration 
ERROR_TYPES = {
    "timeout": {"chance": 0.1, "description": "Server timeout simulation"},
    "rate_limit": {"chance": 0.15, "description": "Rate limiting simulation"},
    "server_error": {"chance": 0.1, "description": "Internal server error simulation"},
    "validation_error": {"chance": 0.2, "description": "Data validation error simulation"}
}

# Configuration from environment variables
def get_config():
    return {
        "error_rate": float(os.environ.get("ERROR_RATE", "0.2")),  # 20% error rate by default
        "timeout_seconds": float(os.environ.get("TIMEOUT_SECONDS", "2.0")),  # Max timeout in seconds
    }

# Token validation middleware
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-API-Token')
        if not token:
            abort(401, description="API token is missing")
        if token != "student_test_token":  # Simple fixed token for testing
            abort(403, description="Invalid API token")
        return f(*args, **kwargs)
    return decorated

# Error simulation middleware
def simulate_errors(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        config = get_config()
        
        # Random chance to simulate errors based on configured error rate
        if random.random() < config["error_rate"]:
            error_type = random.choices(
                list(ERROR_TYPES.keys()), 
                weights=[ERROR_TYPES[t]["chance"] for t in ERROR_TYPES.keys()],
                k=1
            )[0]
            
            if error_type == "timeout":
                # Simulate a slow response
                time.sleep(random.uniform(1.0, config["timeout_seconds"]))
                
            elif error_type == "rate_limit":
                abort(429, description="Rate limit exceeded. Try again later.")
                
            elif error_type == "server_error":
                abort(500, description="Internal server error occurred")
                
            elif error_type == "validation_error":
                abort(422, description="Invalid data format or content")
        
        return f(*args, **kwargs)
    return decorated

# Custom error handler
@app.errorhandler(HTTPException)
def handle_exception(e):
    response = e.get_response()
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response

# Root endpoint - API information
@app.route('/', methods=['GET'])
def get_api_info():
    return jsonify({
        "name": "Integration Testing Learning API",
        "version": "1.0.0",
        "description": "API for learning integration testing with different themes",
        "themes": {theme: info["name"] for theme, info in THEMES.items()},
        "documentation": "/docs",
    })

# Documentation endpoint
@app.route('/docs', methods=['GET'])
def get_docs():
    return jsonify({
        "documentation": "API Documentation",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Get API information"},
            {"path": "/docs", "method": "GET", "description": "Get API documentation"},
            {"path": "/themes", "method": "GET", "description": "List available themes"},
            {"path": "/themes/<theme_id>", "method": "GET", "description": "Get theme details"},
            {"path": "/themes/<theme_id>/<entity_type>", "method": "GET", "description": "List entities of a type"},
            {"path": "/themes/<theme_id>/<entity_type>", "method": "POST", "description": "Create a new entity"},
            {"path": "/themes/<theme_id>/<entity_type>/<entity_id>", "method": "GET", "description": "Get entity details"},
            {"path": "/themes/<theme_id>/<entity_type>/<entity_id>", "method": "PUT", "description": "Update an entity"},
            {"path": "/themes/<theme_id>/<entity_type>/<entity_id>", "method": "DELETE", "description": "Delete an entity"},
            {"path": "/error-test", "method": "GET", "description": "Test different error responses"}
        ],
        "authentication": "Use X-API-Token header with value 'student_test_token'",
        "error_simulation": "The API randomly simulates errors for testing purposes",
    })

# List themes
@app.route('/themes', methods=['GET'])
def get_themes():
    return jsonify({
        "themes": [
            {"id": theme_id, "name": info["name"], "description": info["description"]}
            for theme_id, info in THEMES.items()
        ]
    })

# Get theme details
@app.route('/themes/<theme_id>', methods=['GET'])
def get_theme(theme_id):
    if theme_id not in THEMES:
        abort(404, description=f"Theme '{theme_id}' not found")
    
    return jsonify({
        "id": theme_id,
        **THEMES[theme_id],
        "entities": [
            {"type": entity, "count": len(data_store[theme_id][entity])}
            for entity in THEMES[theme_id]["entities"]
        ]
    })

# List entities
@app.route('/themes/<theme_id>/<entity_type>', methods=['GET'])
@token_required
@simulate_errors
def list_entities(theme_id, entity_type):
    if theme_id not in THEMES:
        abort(404, description=f"Theme '{theme_id}' not found")
    if entity_type not in THEMES[theme_id]["entities"]:
        abort(404, description=f"Entity type '{entity_type}' not found in theme '{theme_id}'")
    
    return jsonify({
        "theme": theme_id,
        "entity_type": entity_type,
        "items": data_store[theme_id][entity_type]
    })

# Create entity
@app.route('/themes/<theme_id>/<entity_type>', methods=['POST'])
@token_required
@simulate_errors
def create_entity(theme_id, entity_type):
    if theme_id not in THEMES:
        abort(404, description=f"Theme '{theme_id}' not found")
    if entity_type not in THEMES[theme_id]["entities"]:
        abort(404, description=f"Entity type '{entity_type}' not found in theme '{theme_id}'")
    
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="Invalid JSON data")
    
    # Ensure required fields based on entity type
    required_fields = {"name", "description"}
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        abort(400, description=f"Missing required fields: {', '.join(missing)}")
    
    # Create new entity with ID
    new_entity = {
        "id": str(len(data_store[theme_id][entity_type]) + 1),
        **data,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    data_store[theme_id][entity_type].append(new_entity)
    
    return jsonify(new_entity), 201

# Get entity details
@app.route('/themes/<theme_id>/<entity_type>/<entity_id>', methods=['GET'])
@token_required
@simulate_errors
def get_entity(theme_id, entity_type, entity_id):
    if theme_id not in THEMES:
        abort(404, description=f"Theme '{theme_id}' not found")
    if entity_type not in THEMES[theme_id]["entities"]:
        abort(404, description=f"Entity type '{entity_type}' not found in theme '{theme_id}'")
    
    for entity in data_store[theme_id][entity_type]:
        if entity["id"] == entity_id:
            return jsonify(entity)
    
    abort(404, description=f"Entity with ID '{entity_id}' not found")

# Update entity
@app.route('/themes/<theme_id>/<entity_type>/<entity_id>', methods=['PUT'])
@token_required
@simulate_errors
def update_entity(theme_id, entity_type, entity_id):
    if theme_id not in THEMES:
        abort(404, description=f"Theme '{theme_id}' not found")
    if entity_type not in THEMES[theme_id]["entities"]:
        abort(404, description=f"Entity type '{entity_type}' not found in theme '{theme_id}'")
    
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="Invalid JSON data")
    
    for i, entity in enumerate(data_store[theme_id][entity_type]):
        if entity["id"] == entity_id:
            # Update entity but preserve ID and creation timestamp
            updated_entity = {
                **entity,
                **data,
                "id": entity_id,  # Ensure ID remains unchanged
                "created_at": entity["created_at"],  # Preserve original creation time
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            data_store[theme_id][entity_type][i] = updated_entity
            return jsonify(updated_entity)
    
    abort(404, description=f"Entity with ID '{entity_id}' not found")

# Delete entity
@app.route('/themes/<theme_id>/<entity_type>/<entity_id>', methods=['DELETE'])
@token_required
@simulate_errors
def delete_entity(theme_id, entity_type, entity_id):
    if theme_id not in THEMES:
        abort(404, description=f"Theme '{theme_id}' not found")
    if entity_type not in THEMES[theme_id]["entities"]:
        abort(404, description=f"Entity type '{entity_type}' not found in theme '{theme_id}'")
    
    for i, entity in enumerate(data_store[theme_id][entity_type]):
        if entity["id"] == entity_id:
            deleted = data_store[theme_id][entity_type].pop(i)
            return jsonify({
                "message": f"Entity '{entity_id}' deleted successfully",
                "deleted": deleted
            })
    
    abort(404, description=f"Entity with ID '{entity_id}' not found")

# Error testing endpoint
@app.route('/error-test', methods=['GET'])
def test_errors():
    error_type = request.args.get('type')
    
    if not error_type or error_type not in ERROR_TYPES:
        return jsonify({
            "available_errors": {
                error_type: ERROR_TYPES[error_type]["description"]
                for error_type in ERROR_TYPES
            }
        })
    
    if error_type == "timeout":
        time.sleep(3)  # Fixed long delay
        return jsonify({"message": "Response after timeout"})
    
    elif error_type == "rate_limit":
        abort(429, description="Rate limit exceeded. Try again later.")
    
    elif error_type == "server_error":
        abort(500, description="Internal server error occurred")
    
    elif error_type == "validation_error":
        abort(422, description="Invalid data format or content")

# Initialize sample data
def init_sample_data():
    # Space Exploration theme
    data_store["space_exploration"]["missions"] = [
        {
            "id": "1", 
            "name": "Mars Rover Mission", 
            "description": "Explore the surface of Mars",
            "status": "in-progress",
            "created_at": "2023-01-15 10:30:00"
        },
        {
            "id": "2", 
            "name": "Jupiter Orbital", 
            "description": "Study Jupiter's atmosphere",
            "status": "planned",
            "created_at": "2023-02-20 14:45:00"
        }
    ]
    
    data_store["space_exploration"]["astronauts"] = [
        {
            "id": "1", 
            "name": "Dr. Sarah Chen", 
            "description": "Astrophysicist and mission specialist",
            "specialty": "Planetary geology",
            "created_at": "2023-01-10 09:20:00"
        }
    ]
    
    # Fantasy RPG theme
    data_store["fantasy_rpg"]["characters"] = [
        {
            "id": "1", 
            "name": "Elindra", 
            "description": "Elven ranger from the western forests",
            "class": "Ranger",
            "level": 5,
            "created_at": "2023-03-05 11:15:00"
        }
    ]
    
    data_store["fantasy_rpg"]["quests"] = [
        {
            "id": "1", 
            "name": "The Lost Artifact", 
            "description": "Recover an ancient artifact from the ruins",
            "difficulty": "Medium",
            "reward": "500 gold",
            "created_at": "2023-03-10 16:20:00"
        }
    ]
    
    # Smart City theme
    data_store["smart_city"]["traffic_sensors"] = [
        {
            "id": "1", 
            "name": "Downtown Junction A", 
            "description": "Main intersection traffic monitor",
            "status": "active",
            "created_at": "2023-04-12 08:30:00"
        }
    ]
    
    data_store["smart_city"]["public_transport"] = [
        {
            "id": "1", 
            "name": "Metro Line 1", 
            "description": "North-South metro connection",
            "status": "operational",
            "capacity": 1200,
            "created_at": "2023-04-15 13:45:00"
        }
    ]

if __name__ == "__main__":
    init_sample_data()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
