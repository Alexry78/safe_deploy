import requests

BASE_URL = "http://127.0.0.1:8000"

def login(username, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/login", data={"username": username, "password": password})
    if r.status_code != 200:
        return None
    return s

def test_idor():
    alice = login("alice", "alice123")
    assert alice is not None
    resp = alice.get(f"{BASE_URL}/files/2")
    assert resp.status_code == 404
    resp = alice.get(f"{BASE_URL}/files/1")
    assert resp.status_code == 200
    admin = login("admin", "admin123")
    assert admin is not None
    resp = admin.delete(f"{BASE_URL}/files/2")
    assert resp.status_code == 200
    bob = login("bob", "bob123")
    assert bob is not None
    resp = bob.get(f"{BASE_URL}/files/my")
    assert resp.status_code == 200
    files = resp.json()
    assert not any(f["id"] == 2 for f in files)

def test_my_files():
    alice = login("alice", "alice123")
    resp = alice.get(f"{BASE_URL}/files/my")
    assert resp.status_code == 200
    files = resp.json()
    assert all(f["owner"] == "alice" for f in files)

def test_admin_all_files():
    admin = login("admin", "admin123")
    resp = admin.get(f"{BASE_URL}/files/all")
    assert resp.status_code == 200
    files = resp.json()
    assert len(files) == 2   
