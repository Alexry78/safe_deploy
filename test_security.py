import requests

BASE_URL = "http://127.0.0.1:8000"

def login(username, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/login", data={"username": username, "password": password})
    if r.status_code != 200:
        return None
    return s

def test_idor():
    # Алиса логинится
    alice = login("alice", "alice123")
    assert alice is not None

    # Пытается получить файл Боба (id=2) – должно быть 404
    resp = alice.get(f"{BASE_URL}/files/2")
    assert resp.status_code == 404

    # Алиса получает свой файл (id=1) – 200
    resp = alice.get(f"{BASE_URL}/files/1")
    assert resp.status_code == 200

    # Админ логинится
    admin = login("admin", "admin123")
    assert admin is not None

    # Админ удаляет файл Боба (id=2)
    resp = admin.delete(f"{BASE_URL}/files/2")
    assert resp.status_code == 200

    # Боб логинится и проверяет, что у него нет файлов (файл id=2 удалён)
    bob = login("bob", "bob123")
    assert bob is not None
    resp = bob.get(f"{BASE_URL}/files/my")
    assert resp.status_code == 200
    files = resp.json()
    # Убеждаемся, что ни один файл не имеет id=2
    assert not any(f["id"] == 2 for f in files)

def test_my_files():
    alice = login("alice", "alice123")
    resp = alice.get(f"{BASE_URL}/files/my")
    assert resp.status_code == 200
    files = resp.json()
    # Все файлы должны принадлежать Алисе
    assert all(f["owner"] == "alice" for f in files)

def test_admin_all_files():
    admin = login("admin", "admin123")
    resp = admin.get(f"{BASE_URL}/files/all")
    assert resp.status_code == 200
    files = resp.json()
    # После удаления файла 2, осталось 2 файла (1 и 3)
    assert len(files) == 2
