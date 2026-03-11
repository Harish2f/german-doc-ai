from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Central configuration for GermanDocAI loaded from environment variables in .env file.

    All secrets (API keys, passwords) default to empty string locally and are
    populated from Azure application settings in production.
    """
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive = False
    )
    # App
    app_name : str = "GermanDocAI"
    app_version: str = "0.1.0"
    environment: str = "Development"
    debug: bool = False

    # Azure OpenAI
    azure_openai_api_key: str = Field(default="", description="Azure OpenAI API key")
    azure_openai_endpoint: str = Field(default="", description = "Azure OpenAI endpoint URL")
    azure_openai_deployment: str = Field(default="gpt-4o", description = "Azure OpenAI deployment name")

    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port:int = 9200
    opensearch_index: str = "german-docs"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "germandocai"
    postgres_username: str = "admin"
    postgres_password: str = Field(default = "", description= "PostgreSQL password")

    # Langfuse
    langfuse_public_key: str = Field(default= "", description= "Langfuse Public Key")
    langfuse_secret_key: str = Field(default="", description= "Langfuse Secret Key")

    # API key
    api_key: str = Field(default="dev-secret-key", description="API key for endpoint authentication")

def get_settings() -> Settings:
    """ Factory function(creates an Object and returns it) to isolate settings for different environments """
    return Settings()
