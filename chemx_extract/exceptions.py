"""Project-specific exceptions."""


class NoLLMProviderError(RuntimeError):
    """Raised when neither Anthropic nor OpenAI API keys are configured."""
