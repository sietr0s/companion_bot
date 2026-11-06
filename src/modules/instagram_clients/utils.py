"""Map instagrapi login exceptions without importing the library at module load."""

from src.modules.instagram_clients.exceptions import (
    InstagramChallengeRequiredError,
    InstagramTwoFactorRequiredError,
)


def raise_login_exception(exc: BaseException) -> None:
    name = type(exc).__name__
    if name == "TwoFactorRequired":
        raise InstagramTwoFactorRequiredError from exc
    if name == "ChallengeRequired":
        raise InstagramChallengeRequiredError from exc
    raise exc
