"""Tests for NYT Cooking integration with mocked HTTP."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.grocery_wizard.integrations.nyt_cooking import (
    NytAuthError,
    NytCollection,
    NYTCookingClient,
    NytCredentials,
    NytSyncCancelledError,
    _ingredients_from_parts,
    _parse_recipe_payload,
    credentials_status,
    flag_metadata_issues,
    format_metadata_review,
    load_credentials,
    parse_regi_id,
    prompt_collection_choice,
    sync_saved_recipes_to_notion,
)
from src.grocery_wizard.recipes.add_recipe import PrefetchedCreateResult


@pytest.fixture
def credentials() -> NytCredentials:
    return NytCredentials(nyt_s_cookie="test-cookie", regi_id="12345678")


@pytest.fixture
def env_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NYT_S_COOKIE", "test-cookie")
    monkeypatch.setenv("NYT_REGI_ID", "12345678")


def test_parse_regi_id_from_cookie() -> None:
    assert parse_regi_id("regi_id=87654321; other=value") == "87654321"
    assert parse_regi_id("87654321") == "87654321"


def test_load_credentials_from_env(env_credentials: None) -> None:
    loaded = load_credentials()
    assert loaded == NytCredentials(nyt_s_cookie="test-cookie", regi_id="12345678")


def test_load_credentials_accepts_nyt_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NYT_S_COOKIE", "test-cookie")
    monkeypatch.setenv("NYT_USER_ID", "87654321")
    monkeypatch.delenv("NYT_REGI_ID", raising=False)

    loaded = load_credentials()
    assert loaded == NytCredentials(nyt_s_cookie="test-cookie", regi_id="87654321")


def test_load_credentials_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NYT_S_COOKIE", raising=False)
    monkeypatch.delenv("NYT_REGI_ID", raising=False)
    monkeypatch.delenv("NYT_USER_ID", raising=False)

    assert load_credentials() is None


def test_credentials_status_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NYT_S_COOKIE", raising=False)
    monkeypatch.delenv("NYT_REGI_ID", raising=False)
    monkeypatch.delenv("NYT_USER_ID", raising=False)

    status = credentials_status()
    assert status["configured"] is False


def test_credentials_status_configured(env_credentials: None) -> None:
    status = credentials_status()
    assert status["configured"] is True
    assert status["regi_id"] == "12345678"


def test_ingredients_from_parts() -> None:
    parts = [
        {
            "ingredients": [
                {"display_quantity": "1 cup", "display_text": "flour"},
                {"display_quantity": "", "display_text": "salt"},
            ]
        }
    ]
    assert _ingredients_from_parts(parts) == ["1 cup flour", "salt"]


def test_parse_recipe_payload() -> None:
    recipe = _parse_recipe_payload(
        {
            "id": 1019049,
            "name": "Simple Pasta",
            "url": "/recipes/1019049-simple-pasta",
            "byline": "sam sifton",
            "parts": [{"ingredients": [{"display_quantity": "8 oz", "display_text": "spaghetti"}]}],
        }
    )
    assert recipe.id == "1019049"
    assert recipe.name == "Simple Pasta"
    assert recipe.url == "https://cooking.nytimes.com/recipes/1019049-simple-pasta"
    assert recipe.author == "Sam Sifton"
    assert recipe.ingredients == ["8 oz spaghetti"]


def _mock_response(
    *,
    status_code: int = 200,
    payload: dict | None = None,
    text: str = "",
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.text = text
    if payload is not None:
        response.json.return_value = payload
    return response


def test_list_saved_recipes_pagination(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)

    session.get.side_effect = [
        _mock_response(
            payload={
                "collectables": [
                    {"id": "1", "name": "Recipe A", "url": "/recipes/1-a", "byline": "Author"},
                ],
                "collectables_count": 2,
            }
        ),
        _mock_response(
            payload={
                "collectables": [
                    {"id": "2", "name": "Recipe B", "url": "/recipes/2-b", "byline": None},
                ],
                "collectables_count": 2,
            }
        ),
    ]

    recipes = list(client.iter_all_saved_recipes(per_page=1))
    assert len(recipes) == 2
    assert recipes[0].name == "Recipe A"
    assert recipes[1].url == "https://cooking.nytimes.com/recipes/2-b"


def test_list_collections(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)
    session.get.return_value = _mock_response(
        payload={
            "collections": [
                {"id": 10, "name": "Weeknight", "collectables_count": 3},
                {"id": 11, "name": "Desserts", "collectables_count": 1},
            ]
        }
    )

    collections = client.list_collections()
    assert len(collections) == 2
    assert collections[0].name == "Weeknight"


def test_find_collection_by_name_case_insensitive(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)
    session.get.return_value = _mock_response(
        payload={"collections": [{"id": 10, "name": "Weeknight", "collectables_count": 3}]}
    )

    found = client.find_collection_by_name("weeknight")
    assert found is not None
    assert found.id == "10"


def test_get_recipe(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)
    session.get.return_value = _mock_response(
        payload={
            "id": 99,
            "name": "Soup",
            "url": "/recipes/99-soup",
            "parts": [{"ingredients": [{"display_quantity": "2 cups", "display_text": "broth"}]}],
            "cooking_time": {"display": "45 minutes", "minutes": 45},
            "prep_time": {"display": "15 minutes", "minutes": 15},
            "cook_time": {"display": "30 minutes", "minutes": 30},
        }
    )

    recipe = client.get_recipe("99")
    assert recipe.ingredients == ["2 cups broth"]
    assert recipe.total_time_minutes == 45.0
    assert recipe.prep_time_minutes == 15.0
    assert recipe.cook_time_minutes == 30.0


def test_verify_auth_rejects_401(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)
    session.get.return_value = _mock_response(status_code=401)

    with pytest.raises(NytAuthError):
        client.verify_auth()


def test_missing_credentials_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NYT_S_COOKIE", raising=False)
    monkeypatch.delenv("NYT_REGI_ID", raising=False)
    monkeypatch.delenv("NYT_USER_ID", raising=False)
    client = NYTCookingClient(None)
    with pytest.raises(NytAuthError):
        client.list_saved_recipes()


def test_sync_dry_run_skips_notion_writes(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)
    session.get.return_value = _mock_response(
        payload={
            "collectables": [
                {
                    "id": "1",
                    "name": "New Recipe",
                    "url": "https://cooking.nytimes.com/recipes/1-new",
                }
            ],
            "collectables_count": 1,
        }
    )

    db = MagicMock()
    db.find_by_link.return_value = None

    with (
        patch("src.grocery_wizard.recipes.add_recipe.add_prefetched_recipes") as add_mock,
        patch(
            "src.grocery_wizard.integrations.nyt_cooking._fetch_nyt_recipe_for_sync",
            return_value=(30.0, ["1 cup flour", "salt"]),
        ),
    ):
        summary = sync_saved_recipes_to_notion(db, client, dry_run=True)

    assert summary.total == 1
    assert summary.dry_run == 1
    assert summary.created == 0
    assert summary.created_recipes[0].ingredient_count == 2
    add_mock.assert_not_called()


def test_sync_skips_existing_links(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)
    session.get.return_value = _mock_response(
        payload={
            "collectables": [
                {
                    "id": "1",
                    "name": "Existing",
                    "url": "https://cooking.nytimes.com/recipes/1-existing",
                }
            ],
            "collectables_count": 1,
        }
    )

    db = MagicMock()
    db.find_by_link.return_value = MagicMock(name="Already There")

    with patch("src.grocery_wizard.recipes.add_recipe.add_prefetched_recipes") as add_mock:
        summary = sync_saved_recipes_to_notion(db, client)

    assert summary.skipped_existing == 1
    add_mock.assert_not_called()


def test_sync_creates_missing_recipes(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)

    session.get.return_value = _mock_response(
        payload={
            "collectables": [
                {
                    "id": "42",
                    "name": "Fresh Recipe",
                    "url": "https://cooking.nytimes.com/recipes/42-fresh",
                }
            ],
            "collectables_count": 1,
        }
    )

    db = MagicMock()
    db.find_by_link.return_value = None
    ingredients = ["2 cups broth", "1 onion"]

    with (
        patch(
            "src.grocery_wizard.recipes.add_recipe.add_prefetched_recipes",
            return_value=[
                PrefetchedCreateResult(
                    page_id="page-1",
                    name="Fresh Recipe",
                    url="https://cooking.nytimes.com/recipes/42-fresh",
                    field_values={
                        "Name": "Fresh Recipe",
                        "Link": "https://cooking.nytimes.com/recipes/42-fresh",
                        "Ingredients": "2 cups broth\n1 onion",
                    },
                )
            ],
        ) as add_mock,
        patch(
            "src.grocery_wizard.integrations.nyt_cooking._fetch_nyt_recipe_for_sync",
            return_value=(45.0, ingredients),
        ),
    ):
        summary = sync_saved_recipes_to_notion(db, client)

    assert summary.created == 1
    assert summary.created_recipes[0].ingredient_count == 2
    add_mock.assert_called_once()
    args, kwargs = add_mock.call_args
    assert args[1][0] == (
        "Fresh Recipe",
        "https://cooking.nytimes.com/recipes/42-fresh",
        ingredients,
        45.0,
    )
    assert kwargs["include_ingredients"] is True
    assert kwargs["mark_nyt_synced"] is True


def test_fetch_nyt_recipe_for_sync_uses_scrape_fallback(credentials: NytCredentials) -> None:
    from src.grocery_wizard.integrations.nyt_cooking import _fetch_nyt_recipe_for_sync
    from src.grocery_wizard.recipes.scraper import ScrapedRecipe

    client = NYTCookingClient(credentials, session=MagicMock())
    url = "https://cooking.nytimes.com/recipes/42-fresh"

    with (
        patch.object(client, "get_recipe", side_effect=NytAuthError("bad")),
        patch(
            "src.grocery_wizard.recipes.scraper.scrape_recipe",
            return_value=ScrapedRecipe(
                title="Fresh Recipe",
                url=url,
                ingredients=["1 lemon"],
                total_time_minutes=20.0,
            ),
        ),
    ):
        total_minutes, ingredients = _fetch_nyt_recipe_for_sync(client, "42", url)

    assert ingredients == ["1 lemon"]
    assert total_minutes == 20.0


def test_prompt_collection_choice_picks_folder(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)

    def fake_get(url: str, **kwargs: object) -> MagicMock:
        if "collections" in url:
            return _mock_response(
                payload={
                    "collections": [
                        {"id": 10, "name": "Weeknight", "collectables_count": 3},
                        {"id": 11, "name": "Desserts", "collectables_count": 1},
                    ]
                }
            )
        if "recipe_box_search" in url:
            return _mock_response(payload={"collectables": [], "collectables_count": 12})
        raise AssertionError(f"Unexpected URL: {url}")

    session.get.side_effect = fake_get
    prompts = iter(["2"])
    collection_id, label = prompt_collection_choice(
        client,
        prompt_fn=lambda _msg: next(prompts),
    )

    assert collection_id == "11"
    assert label == "Desserts"


def test_prompt_collection_choice_picks_first_folder(credentials: NytCredentials) -> None:
    session = MagicMock()
    client = NYTCookingClient(credentials, session=session)

    def fake_get(url: str, **kwargs: object) -> MagicMock:
        if "collections" in url:
            return _mock_response(
                payload={
                    "collections": [
                        {"id": 10, "name": "Weeknight", "collectables_count": 3},
                    ]
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")

    session.get.side_effect = fake_get
    prompts = iter(["1"])
    collection_id, label = prompt_collection_choice(
        client,
        prompt_fn=lambda _msg: next(prompts),
    )

    assert collection_id == "10"
    assert label == "Weeknight"


def test_prompt_collection_choice_fallback_when_collections_unavailable(
    credentials: NytCredentials,
) -> None:
    from src.grocery_wizard.integrations.nyt_cooking import NytNetworkError

    client = NYTCookingClient(credentials, session=MagicMock())
    with (
        patch.object(
            client,
            "list_collections",
            side_effect=NytNetworkError("collections unavailable"),
        ),
        pytest.raises(NytSyncCancelledError),
    ):
        prompt_collection_choice(
            client,
            prompt_fn=lambda _msg: "",
            on_info=lambda _msg: None,
        )


def test_prompt_collection_choice_cancelled(credentials: NytCredentials) -> None:
    client = NYTCookingClient(credentials, session=MagicMock())
    with (
        patch.object(
            client,
            "list_collections",
            return_value=[NytCollection(id="1", name="Weeknight", recipe_count=2)],
        ),
        patch.object(
            client,
            "list_saved_recipes",
            return_value={"collectables": [], "collectables_count": 2},
        ),
        pytest.raises(NytSyncCancelledError),
    ):
        prompt_collection_choice(client, prompt_fn=lambda _msg: "")


def test_run_recipe_box_sync_passes_folder_and_saves_report() -> None:
    from src.grocery_wizard.integrations.nyt_cooking import (
        NytCreatedRecipe,
        NytSyncSummary,
        run_recipe_box_sync,
    )

    summary = NytSyncSummary(
        total=2,
        created=1,
        collection_label="Weeknight",
        created_recipes=[
            NytCreatedRecipe(
                page_id="p1",
                name="Pasta",
                url="https://cooking.nytimes.com/recipes/1",
                metadata={"Meal": "Dinner"},
                flags=[],
            )
        ],
    )
    db = MagicMock()
    client = MagicMock()

    with (
        patch(
            "src.grocery_wizard.integrations.nyt_cooking.sync_saved_recipes_to_notion",
            return_value=summary,
        ) as sync_mock,
        patch("src.grocery_wizard.integrations.nyt_cooking.save_sync_report") as save_mock,
    ):
        result = run_recipe_box_sync(
            db,
            client,
            collection_id="10",
            collection_label="Weeknight",
            dry_run=False,
        )

    sync_mock.assert_called_once()
    kwargs = sync_mock.call_args.kwargs
    assert kwargs["collection_id"] == "10"
    assert kwargs["collection_label"] == "Weeknight"
    save_mock.assert_called_once_with(summary)
    assert result.review_report is not None
    assert result.review_report["created"][0]["name"] == "Pasta"


def test_list_recipe_box_folders_orders_preferred_labels_first() -> None:
    from src.grocery_wizard.integrations.nyt_cooking import (
        NytCollection,
        list_recipe_box_folders,
    )

    client = MagicMock()
    client.list_collections.return_value = [
        NytCollection(id="c1", name="Weeknight", recipe_count=5),
        NytCollection(id="c2", name="Favorites", recipe_count=2),
        NytCollection(id="c3", name="To make", recipe_count=7),
    ]
    folders = list_recipe_box_folders(client)

    assert [folder.label for folder in folders] == ["To make", "Favorites", "Weeknight"]
    assert all(folder.collection_id is not None for folder in folders)


def test_flag_metadata_issues_detects_dessert_mismatch() -> None:
    flags = flag_metadata_issues(
        "World's Best Chocolate Cake",
        {"Meal": "Dinner", "Protein": "Dairy"},
    )
    assert flags
    assert "Dessert" in flags[0]


def test_format_metadata_review_lists_recipes() -> None:
    report = {
        "collection": "Weeknight",
        "synced_at": "2026-01-01T00:00:00Z",
        "created": [
            {
                "name": "Pasta",
                "metadata": {"Meal": "Dinner"},
                "flags": [],
            }
        ],
    }
    text = format_metadata_review(report)
    assert "Pasta" in text
    assert "Meal: Dinner" in text


def test_verify_nyt_credentials_raises_when_not_configured() -> None:
    from src.grocery_wizard.integrations.nyt_cooking import NytAuthError, verify_nyt_credentials

    with (
        patch("src.grocery_wizard.integrations.nyt_cooking.load_credentials", return_value=None),
        pytest.raises(NytAuthError, match="not configured"),
    ):
        verify_nyt_credentials()


def test_reclassify_updates_meal_and_weeknight() -> None:
    from dataclasses import dataclass

    from src.grocery_wizard.integrations.notion import ColumnInfo, DatabaseSchema
    from src.grocery_wizard.integrations.nyt_cooking import (
        NytRecipe,
        reclassify_nyt_synced_recipes,
    )

    @dataclass
    class StubRecipe:
        page_id: str
        name: str
        link: str
        ingredients: str | None
        properties: dict

    db = MagicMock()
    db.nyt_synced_column_name.return_value = "Synced from NYT recipe box"
    db.schema = DatabaseSchema(
        name_column="Name",
        link_column="Link",
        ingredients_column="Ingredients",
        filter_columns=[
            ColumnInfo(
                name="Meal",
                type="select",
                options=["Dinner", "Lunch", "Snack/Side", "Dessert"],
            ),
        ],
        checkbox_columns=[
            ColumnInfo(name="Dinner: Weeknight Friendly", type="checkbox"),
        ],
        all_columns={
            "Meal": ColumnInfo(name="Meal", type="select", options=["Dinner", "Lunch"]),
            "Dinner: Weeknight Friendly": ColumnInfo(
                name="Dinner: Weeknight Friendly",
                type="checkbox",
            ),
            "Synced from NYT recipe box": ColumnInfo(
                name="Synced from NYT recipe box",
                type="checkbox",
            ),
        },
    )
    db.query_recipes.return_value = [
        StubRecipe(
            page_id="page-1",
            name="Corn Salad With Mango",
            link="https://cooking.nytimes.com/recipes/101-corn-salad",
            ingredients=None,
            properties={
                "Synced from NYT recipe box": True,
                "Meal": "Dinner",
                "Dinner: Weeknight Friendly": False,
            },
        ),
        StubRecipe(
            page_id="page-2",
            name="Chickpea Salad Sandwich",
            link="https://cooking.nytimes.com/recipes/102-sandwich",
            ingredients=None,
            properties={
                "Synced from NYT recipe box": True,
                "Meal": "Dinner",
                "Dinner: Weeknight Friendly": False,
            },
        ),
    ]

    client = MagicMock()
    client.get_recipe.side_effect = [
        NytRecipe(
            id="101",
            name="Corn Salad With Mango",
            url="https://cooking.nytimes.com/recipes/101-corn-salad",
            ingredients=[],
            total_time_minutes=20,
        ),
        NytRecipe(
            id="102",
            name="Chickpea Salad Sandwich",
            url="https://cooking.nytimes.com/recipes/102-sandwich",
            ingredients=[],
            total_time_minutes=25,
        ),
    ]

    summary = reclassify_nyt_synced_recipes(db, client, dry_run=False)

    assert summary.total == 2
    assert summary.meal_changes == 2
    assert summary.weeknight_set == 0
    assert db.update_recipe.call_count == 2
    db.update_recipe.assert_any_call("page-1", {"Meal": "Snack/Side"})
    db.update_recipe.assert_any_call("page-2", {"Meal": "Lunch"})


def test_format_sync_summary_includes_counts() -> None:
    from src.grocery_wizard.integrations.nyt_cooking import NytSyncSummary, format_sync_summary

    text = format_sync_summary(
        NytSyncSummary(total=10, skipped_existing=3, created=2, dry_run=0, failed=1)
    )
    assert "10 in NYT" in text
    assert "3 already in Notion" in text
    assert "2 created" in text
