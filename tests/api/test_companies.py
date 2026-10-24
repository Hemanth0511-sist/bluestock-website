import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_get_companies_returns_92_records():
    response = requests.get(f"{BASE_URL}/companies")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 92
    assert len(data["companies"]) == 92


def test_get_tcs_returns_correct_data():
    response = requests.get(f"{BASE_URL}/companies/TCS")

    assert response.status_code == 200

    data = response.json()

    assert data["company"]["id"] == "TCS"
    assert data["company"]["company_name"] == "Tata Consultancy Services Ltd"


def test_get_invalid_company_returns_404():
    response = requests.get(f"{BASE_URL}/companies/INVALID")

    assert response.status_code == 404
