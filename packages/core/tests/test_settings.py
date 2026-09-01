from justnews_core.settings import Settings


class TestDatabaseUrl:
    def test_bare_postgresql_scheme_gets_the_asyncpg_driver(self) -> None:
        # Supabase's dashboard hands out exactly this shape - no driver, since
        # it has no idea which one the app needs.
        settings = Settings(
            database_url="postgresql://user:pw@db.example.supabase.co:5432/postgres"
        )
        assert str(settings.database_url).startswith("postgresql+asyncpg://")

    def test_explicit_driver_is_left_alone(self) -> None:
        settings = Settings(database_url="postgresql+asyncpg://user:pw@localhost:5432/justnews")
        assert str(settings.database_url).startswith("postgresql+asyncpg://")

    def test_sync_database_url_swaps_in_psycopg(self) -> None:
        settings = Settings(
            database_url="postgresql://user:pw@db.example.supabase.co:5432/postgres"
        )
        assert settings.sync_database_url.startswith("postgresql+psycopg://")
