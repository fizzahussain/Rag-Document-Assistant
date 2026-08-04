import argparse
import uuid

from backend.app.config import settings
from backend.app.core.security import create_access_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local development access token")
    parser.add_argument("--user-id", default=settings.DEV_USER_ID)
    parser.add_argument("--expires-in", type=int, default=settings.ACCESS_TOKEN_TTL_SECONDS)
    args = parser.parse_args()
    user_id = uuid.UUID(args.user_id)
    print(create_access_token(str(user_id), expires_in=args.expires_in))


if __name__ == "__main__":
    main()
