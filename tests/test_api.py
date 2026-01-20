"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        if name in activities:
            activities[name]["participants"] = details["participants"].copy()


def test_root_redirects_to_static(client):
    """Test that root path redirects to static/index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client):
    """Test getting all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, dict)
    assert "Soccer Team" in data
    assert "Swimming Club" in data
    
    # Verify activity structure
    soccer = data["Soccer Team"]
    assert "description" in soccer
    assert "schedule" in soccer
    assert "max_participants" in soccer
    assert "participants" in soccer
    assert isinstance(soccer["participants"], list)


def test_signup_for_activity_success(client):
    """Test successful signup for an activity"""
    email = "newstudent@mergington.edu"
    activity_name = "Chess Club"
    
    response = client.post(
        f"/activities/{activity_name}/signup?email={email}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert email in data["message"]
    assert activity_name in data["message"]
    
    # Verify student was added
    assert email in activities[activity_name]["participants"]


def test_signup_for_nonexistent_activity(client):
    """Test signup for an activity that doesn't exist"""
    email = "student@mergington.edu"
    
    response = client.post(
        "/activities/Nonexistent Activity/signup?email=" + email
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_signup_when_already_registered(client):
    """Test signup when student is already registered"""
    email = "alex@mergington.edu"  # Already registered for Soccer Team
    activity_name = "Soccer Team"
    
    response = client.post(
        f"/activities/{activity_name}/signup?email={email}"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already signed up" in data["detail"]


def test_signup_when_activity_full(client):
    """Test signup when activity is full"""
    activity_name = "Chess Club"
    max_participants = activities[activity_name]["max_participants"]
    
    # Fill up the activity
    activities[activity_name]["participants"] = [
        f"student{i}@mergington.edu" for i in range(max_participants)
    ]
    
    # Try to add one more
    response = client.post(
        f"/activities/{activity_name}/signup?email=overflow@mergington.edu"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "full" in data["detail"]


def test_unregister_from_activity_success(client):
    """Test successful unregistration from an activity"""
    email = "alex@mergington.edu"
    activity_name = "Soccer Team"
    
    # Verify student is registered
    assert email in activities[activity_name]["participants"]
    
    response = client.delete(
        f"/activities/{activity_name}/unregister?email={email}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert email in data["message"]
    assert activity_name in data["message"]
    
    # Verify student was removed
    assert email not in activities[activity_name]["participants"]


def test_unregister_from_nonexistent_activity(client):
    """Test unregister from an activity that doesn't exist"""
    email = "student@mergington.edu"
    
    response = client.delete(
        "/activities/Nonexistent Activity/unregister?email=" + email
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_unregister_when_not_registered(client):
    """Test unregister when student is not registered"""
    email = "notregistered@mergington.edu"
    activity_name = "Soccer Team"
    
    response = client.delete(
        f"/activities/{activity_name}/unregister?email={email}"
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "not registered" in data["detail"]


def test_signup_and_unregister_workflow(client):
    """Test complete workflow of signup and unregister"""
    email = "workflow@mergington.edu"
    activity_name = "Drama Club"
    
    # Get initial participant count
    initial_count = len(activities[activity_name]["participants"])
    
    # Sign up
    signup_response = client.post(
        f"/activities/{activity_name}/signup?email={email}"
    )
    assert signup_response.status_code == 200
    assert len(activities[activity_name]["participants"]) == initial_count + 1
    
    # Unregister
    unregister_response = client.delete(
        f"/activities/{activity_name}/unregister?email={email}"
    )
    assert unregister_response.status_code == 200
    assert len(activities[activity_name]["participants"]) == initial_count


def test_multiple_signups_different_activities(client):
    """Test that a student can sign up for multiple activities"""
    email = "multitasker@mergington.edu"
    
    # Sign up for multiple activities
    activities_to_join = ["Chess Club", "Drama Club", "Art Studio"]
    
    for activity_name in activities_to_join:
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert response.status_code == 200
        assert email in activities[activity_name]["participants"]


def test_activities_have_correct_structure(client):
    """Test that all activities have the required structure"""
    response = client.get("/activities")
    data = response.json()
    
    required_fields = ["description", "schedule", "max_participants", "participants"]
    
    for activity_name, activity_details in data.items():
        for field in required_fields:
            assert field in activity_details, f"{activity_name} missing {field}"
        
        assert isinstance(activity_details["max_participants"], int)
        assert activity_details["max_participants"] > 0
        assert isinstance(activity_details["participants"], list)
        assert len(activity_details["participants"]) <= activity_details["max_participants"]
