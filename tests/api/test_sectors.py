import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_get_sectors_returns_exactly_11_sectors():
    response = requests.get(f"{BASE_URL}/sectors")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert "sectors" in data

    sectors = data["sectors"]

    assert isinstance(sectors, list)
    assert len(sectors) == 11


def test_get_it_sector_returns_only_it_companies():
    response = requests.get(f"{BASE_URL}/sectors/Information%20Technology/companies")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert "companies" in data

    companies = data["companies"]

    assert isinstance(companies, list)
    assert len(companies) > 0

    for company in companies:
        assert company["broad_sector"] == "Information Technology"
