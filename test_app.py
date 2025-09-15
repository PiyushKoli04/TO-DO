import pytest
import json
import os
import tempfile
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client"""
    # Create a temporary database
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
    
    os.close(db_fd)
    os.unlink(app.config.get('DATABASE', 'todos.db'))

def test_index_page(client):
    """Test the main page loads"""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Flask Todo App' in rv.data

def test_add_todo(client):
    """Test adding a todo"""
    rv = client.post('/add', data={'title': 'Test Todo', 'description': 'Test Description'})
    assert rv.status_code == 302  # Redirect after add
    
    # Check if todo appears on page
    rv = client.get('/')
    assert b'Test Todo' in rv.data
    assert b'Test Description' in rv.data

def test_add_empty_todo(client):
    """Test adding empty todo fails gracefully"""
    rv = client.post('/add', data={'title': '', 'description': ''})
    assert rv.status_code == 302  # Still redirects but doesn't add

def test_api_health_check(client):
    """Test health check endpoint"""
    rv = client.get('/api/health')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data

def test_api_get_todos(client):
    """Test API todos endpoint"""
    # Add a todo first
    client.post('/add', data={'title': 'API Test Todo'})
    
    rv = client.get('/api/todos')
    assert rv.status_code == 200
    todos = json.loads(rv.data)
    assert isinstance(todos, list)
    assert len(todos) >= 1
    assert todos[0]['title'] == 'API Test Todo'

def test_api_add_todo(client):
    """Test adding todo via API"""
    todo_data = {
        'title': 'API Added Todo',
        'description': 'Added via API'
    }
    rv = client.post('/api/todos', 
                    data=json.dumps(todo_data),
                    content_type='application/json')
    
    assert rv.status_code == 201
    data = json.loads(rv.data)
    assert data['title'] == 'API Added Todo'
    assert data['description'] == 'Added via API'
    assert data['completed'] == False

def test_api_add_todo_no_title(client):
    """Test API validation"""
    todo_data = {'description': 'No title'}
    rv = client.post('/api/todos',
                    data=json.dumps(todo_data),
                    content_type='application/json')
    
    assert rv.status_code == 400
    data = json.loads(rv.data)
    assert 'error' in data

def test_toggle_todo(client):
    """Test toggling todo completion"""
    # Add a todo first
    client.post('/add', data={'title': 'Toggle Test'})
    
    # Get todos to find the ID
    rv = client.get('/api/todos')
    todos = json.loads(rv.data)
    todo_id = todos[0]['id']
    
    # Toggle completion
    rv = client.get(f'/toggle/{todo_id}')
    assert rv.status_code == 302
    
    # Check if it's completed
    rv = client.get('/api/todos')
    todos = json.loads(rv.data)
    assert todos[0]['completed'] == 1

def test_delete_todo(client):
    """Test deleting a todo"""
    # Add a todo first
    client.post('/add', data={'title': 'Delete Test'})
    
    # Get todos to find the ID
    rv = client.get('/api/todos')
    todos = json.loads(rv.data)
    todo_id = todos[0]['id']
    initial_count = len(todos)
    
    # Delete the todo
    rv = client.get(f'/delete/{todo_id}')
    assert rv.status_code == 302
    
    # Check if it's deleted
    rv = client.get('/api/todos')
    todos = json.loads(rv.data)
    assert len(todos) == initial_count - 1

def test_filters(client):
    """Test todo filters"""
    # Add completed and active todos
    client.post('/add', data={'title': 'Active Todo'})
    client.post('/add', data={'title': 'Completed Todo'})
    
    # Get todos and complete one
    rv = client.get('/api/todos')
    todos = json.loads(rv.data)
    client.get(f'/toggle/{todos[0]["id"]}')
    
    # Test filters
    rv = client.get('/?filter=active')
    assert rv.status_code == 200
    assert b'Active Todo' in rv.data or b'Completed Todo' in rv.data
    
    rv = client.get('/?filter=completed')
    assert rv.status_code == 200
    
    rv = client.get('/?filter=all')
    assert rv.status_code == 200

def test_clear_completed(client):
    """Test clearing completed todos"""
    # Add and complete some todos
    client.post('/add', data={'title': 'Todo 1'})
    client.post('/add', data={'title': 'Todo 2'})
    
    rv = client.get('/api/todos')
    todos = json.loads(rv.data)
    
    # Complete first todo
    client.get(f'/toggle/{todos[0]["id"]}')
    
    # Clear completed
    rv = client.get('/clear-completed')
    assert rv.status_code == 302
    
    # Check remaining todos
    rv = client.get('/api/todos')
    remaining_todos = json.loads(rv.data)
    assert len(remaining_todos) == 1
    assert all(todo['completed'] == 0 for todo in remaining_todos)
