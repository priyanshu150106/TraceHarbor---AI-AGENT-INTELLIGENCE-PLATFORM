"""
TraceHarbor API — Dataset Management & Ingestion Tests
"""

import json

import pytest
from httpx import AsyncClient

from app.tests.conftest import TEST_API_KEY


@pytest.mark.asyncio
async def test_create_and_get_dataset(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Create dataset with initial cases
    create_payload = {
        "name": "Customer Support FAQ",
        "description": "Standard golden test dataset for returns and warranties",
        "cases": [
            {
                "input": "What is the return policy?",
                "expected_output": "Returns are accepted within 30 days.",
                "criteria": {"required_keywords": ["30 days"]},
                "metadata": {"category": "policy"},
                "tags": ["returns", "faq"],
            },
            {
                "input": "How long does shipping take?",
                "expected_output": "Standard shipping takes 3-5 days.",
                "criteria": {"required_keywords": ["3-5 days"]},
            },
        ],
    }

    create_res = await client.post("/v1/datasets", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["name"] == "Customer Support FAQ"
    assert data["test_cases_count"] == 2
    dataset_id = data["id"]

    # 2. Get dataset detail with paginated cases
    get_res = await client.get(f"/v1/datasets/{dataset_id}", headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["name"] == "Customer Support FAQ"
    assert detail["test_cases_count"] == 2
    assert len(detail["test_cases"]) == 2
    assert detail["test_cases"][0]["input"] == "What is the return policy?"
    assert detail["test_cases"][0]["criteria"] == {"required_keywords": ["30 days"]}

    # 3. List datasets
    list_res = await client.get("/v1/datasets", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    found = any(d["id"] == dataset_id for d in list_data["items"])
    assert found is True


@pytest.mark.asyncio
async def test_add_test_cases_batch(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    # Create empty dataset
    create_res = await client.post(
        "/v1/datasets",
        json={"name": "Warranty Test Suite", "description": "Warranty edge cases"},
        headers=headers,
    )
    assert create_res.status_code == 201
    dataset_id = create_res.json()["id"]

    # Add batch of 2 cases
    cases_payload = [
        {"input": "Do you offer international warranty?", "expected_output": "Yes, on select models."},
        {"input": "What does warranty exclude?", "expected_output": "Accidental damage."},
    ]
    add_res = await client.post(f"/v1/datasets/{dataset_id}/cases", json=cases_payload, headers=headers)
    assert add_res.status_code == 201
    added = add_res.json()
    assert len(added) == 2

    # Verify count in detail
    get_res = await client.get(f"/v1/datasets/{dataset_id}", headers=headers)
    assert get_res.json()["test_cases_count"] == 2


@pytest.mark.asyncio
async def test_upload_json_dataset(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    sample_json = [
        {
            "input": "How do I exchange an item?",
            "expected_output": "Exchanges are allowed within 30 days.",
            "criteria": {"required_keywords": ["30 days", "Exchange"]},
            "tags": ["exchange"],
        },
        {
            "input": "Where is my package?",
            "expected_output": "Track your package using the tracking link.",
        },
    ]

    files = {"file": ("uploaded_faq.json", json.dumps(sample_json).encode("utf-8"), "application/json")}
    data = {"name": "Uploaded JSON Dataset", "description": "Imported via multipart"}

    res = await client.post("/v1/datasets/upload", data=data, files=files, headers=headers)
    assert res.status_code == 201
    upload_data = res.json()
    assert upload_data["cases_imported"] == 2
    dataset_id = upload_data["id"]

    # Verify imported cases
    detail_res = await client.get(f"/v1/datasets/{dataset_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["test_cases_count"] == 2


@pytest.mark.asyncio
async def test_upload_csv_dataset(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    csv_content = (
        'input,expected_output,criteria,metadata,tags\n'
        '"What is return policy?","30 days return window.","{""required_keywords"": [""30 days""]}","{""diff"": ""easy""}","returns"\n'
        '"Do you ship to Canada?","Yes, express shipping available.","","","shipping"\n'
    )

    files = {"file": ("dataset.csv", csv_content.encode("utf-8"), "text/csv")}
    data = {"name": "Uploaded CSV Dataset"}

    res = await client.post("/v1/datasets/upload", data=data, files=files, headers=headers)
    assert res.status_code == 201
    upload_data = res.json()
    assert upload_data["cases_imported"] == 2


@pytest.mark.asyncio
async def test_dataset_upload_validation_errors(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    # 1. Empty file
    files = {"file": ("empty.json", b"", "application/json")}
    res = await client.post("/v1/datasets/upload", data={"name": "Empty"}, files=files, headers=headers)
    assert res.status_code == 422
    assert "empty" in res.json()["detail"].lower()

    # 2. Malformed JSON
    files = {"file": ("malformed.json", b"[{\"input\": \"question\",", "application/json")}
    res = await client.post("/v1/datasets/upload", data={"name": "Malformed"}, files=files, headers=headers)
    assert res.status_code == 422
    assert "malformed json" in res.json()["detail"].lower()

    # 3. Missing required input field
    files = {"file": ("no_input.json", b"[{\"expected_output\": \"answer\"}]", "application/json")}
    res = await client.post("/v1/datasets/upload", data={"name": "NoInput"}, files=files, headers=headers)
    assert res.status_code == 422
    assert "missing required" in res.json()["detail"].lower()

    # 4. CSV missing input header
    files = {"file": ("bad.csv", b"question,answer\n\"What is it?\",\"Answer\"\n", "text/csv")}
    res = await client.post("/v1/datasets/upload", data={"name": "BadCSV"}, files=files, headers=headers)
    assert res.status_code == 422
    assert "missing required csv header 'input'" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_dataset_deletion(client: AsyncClient):
    headers = {"X-API-Key": TEST_API_KEY}

    create_res = await client.post(
        "/v1/datasets",
        json={"name": "To be deleted", "cases": [{"input": "Temporary test"}]},
        headers=headers,
    )
    dataset_id = create_res.json()["id"]

    # Delete
    del_res = await client.delete(f"/v1/datasets/{dataset_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify 404
    get_res = await client.get(f"/v1/datasets/{dataset_id}", headers=headers)
    assert get_res.status_code == 404
