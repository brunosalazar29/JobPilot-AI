from sqlalchemy import text

from app.core.database import engine


PROFILE_COLUMNS = {
    "seniority": "NVARCHAR(80) NULL",
    "target_roles": "NVARCHAR(MAX) NULL",
    "field_sources": "NVARCHAR(MAX) NULL",
    "missing_fields": "NVARCHAR(MAX) NULL",
    "recommendations": "NVARCHAR(MAX) NULL",
    "profile_completeness": "INT NOT NULL CONSTRAINT DF_profiles_profile_completeness DEFAULT 0",
}


def ensure_profile_detection_columns() -> None:
    with engine.begin() as connection:
        for column_name, sql_type in PROFILE_COLUMNS.items():
            connection.execute(
                text(
                    f"""
                    IF COL_LENGTH('profiles', '{column_name}') IS NULL
                    BEGIN
                        ALTER TABLE profiles ADD {column_name} {sql_type}
                    END
                    """
                )
            )
