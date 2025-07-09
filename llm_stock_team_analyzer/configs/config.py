"""
Configuration management for the agent, using Pydantic models and YAML loading.
"""

import os
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import BaseModel, SecretStr, StrictFloat, StrictInt, StrictStr
from pydantic_settings import BaseSettings


class LLMConfig(BaseModel):
    temperature: StrictFloat
    max_tokens: StrictInt
    retry: StrictInt
    max_debate_rounds: Optional[StrictInt] = 1
    request_timeout: Optional[StrictInt] = 60
    retry_delay: Optional[StrictInt] = 60
    max_retries: Optional[StrictInt] = 3


class RateLimitingConfig(BaseModel):
    enabled: Optional[bool] = True
    requests_per_minute: Optional[StrictInt] = 10
    tokens_per_minute: Optional[StrictInt] = 40000
    delay_between_requests: Optional[StrictInt] = 6


class AzureOpenAIConfig(BaseModel):
    endpoint: StrictStr
    api_version: StrictStr
    deployment: StrictStr
    subscription_key: SecretStr


class Config(BaseSettings):
    llm: LLMConfig
    azure_openai: AzureOpenAIConfig
    rate_limiting: Optional[RateLimitingConfig] = None


def get_config() -> dict:
    """Get unified configuration from YAML config"""
    config = {}

    try:
        config_path = os.getenv(
            "CONFIG_PATH", os.path.join(os.path.dirname(__file__), "config.yaml")
        )

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                yaml_config = yaml.safe_load(f)

            if yaml_config:
                # Flatten nested structure for compatibility
                if "llm" in yaml_config:
                    llm_config = yaml_config["llm"]
                    config.update(
                        {
                            "temperature": llm_config.get("temperature", 0.5),
                            "max_tokens": llm_config.get("max_tokens", 4096),
                            "retry": llm_config.get("retry", 3),
                            "max_debate_rounds": llm_config.get("max_debate_rounds", 1),
                            "request_timeout": llm_config.get("request_timeout", 60),
                            "retry_delay": llm_config.get("retry_delay", 60),
                            "max_retries": llm_config.get("max_retries", 3),
                        }
                    )

                if "rate_limiting" in yaml_config:
                    rate_config = yaml_config["rate_limiting"]
                    config.update(
                        {
                            "rate_limiting_enabled": rate_config.get("enabled", True),
                            "requests_per_minute": rate_config.get(
                                "requests_per_minute", 10
                            ),
                            "tokens_per_minute": rate_config.get(
                                "tokens_per_minute", 40000
                            ),
                            "delay_between_requests": rate_config.get(
                                "delay_between_requests", 6
                            ),
                        }
                    )

                if "azure_openai" in yaml_config:
                    azure_config = yaml_config["azure_openai"]
                    config.update(
                        {
                            "endpoint": azure_config.get("endpoint"),
                            "api_version": azure_config.get("api_version"),
                            "deployment": azure_config.get("deployment"),
                            "subscription_key": azure_config.get("subscription_key"),
                            # Also add with azure_ prefix for compatibility
                            "azure_endpoint": azure_config.get("endpoint"),
                            "azure_api_version": azure_config.get("api_version"),
                            "azure_deployment": azure_config.get("deployment"),
                            "azure_subscription_key": azure_config.get(
                                "subscription_key"
                            ),
                        }
                    )
        else:
            # Default values if config file doesn't exist
            config = {
                "temperature": 0.5,
                "max_tokens": 4096,
                "retry": 3,
                "max_debate_rounds": 1,
                "request_timeout": 60,
                "retry_delay": 60,
                "max_retries": 3,
                "rate_limiting_enabled": True,
                "requests_per_minute": 10,
                "tokens_per_minute": 40000,
                "delay_between_requests": 6,
            }

    except Exception as e:
        print(f"Warning: Could not load YAML config: {e}")
        # Fallback default values
        config = {
            "temperature": 0.5,
            "max_tokens": 4096,
            "retry": 3,
            "max_debate_rounds": 1,
            "request_timeout": 60,
            "retry_delay": 60,
            "max_retries": 3,
            "rate_limiting_enabled": True,
            "requests_per_minute": 10,
            "tokens_per_minute": 40000,
            "delay_between_requests": 6,
        }

    return config


@lru_cache()
def get_pydantic_config() -> Config:
    """Get Pydantic configuration object (for type safety)"""
    config_path = os.getenv(
        "CONFIG_PATH", os.path.join(os.path.dirname(__file__), "config.yaml")
    )

    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    return Config(**raw_config)
