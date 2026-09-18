"""Map instagrapi login exceptions without importing the library at module load."""

from src.modules.instagram_clients.exceptions import (
    InstagramChallengeRequired,
    InstagramTwoFactorRequired,
)


def raise_login_exception(exc: BaseException) -> None:
    name = type(exc).__name__
    if name == "TwoFactorRequired":
        raise InstagramTwoFactorRequired from exc
    if name == "ChallengeRequired":
        raise InstagramChallengeRequired from exc
    raise exc
