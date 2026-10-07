class RouterError(Exception):
    pass


class ConfigError(RouterError):
    pass


class MissingPriceError(RouterError):
    """A price needed to compute cost has not been filled in config/prices.yaml. We never guess one."""


class ProviderError(RouterError):
    """A provider call failed (network, auth, rate limit, bad model id...)."""
