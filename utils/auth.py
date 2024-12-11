import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWT
from jwt.exceptions import InvalidTokenError

from config import settings


class UnauthenticatedException(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication")


# 👇 new code
class VerifyToken:
    """Does all the token verification using PyJWT"""

    def __init__(self):
        self.cognito_issuer = (
            f"https://cognito-idp.{settings.COGNITO_USER_POOL_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}"
        )
        self.jwks_url = f"{self.cognito_issuer}/.well-known/jwks.json"
        self.cognito_audience = settings.COGNITO_WEB_CLIENT_ID
        self.jwt = PyJWT()

    def get_jwks(self):
        response = requests.get(self.jwks_url)
        return response.json()["keys"]

    def decode_token(self, token: str):
        try:
            token = token.replace("Bearer ", "").replace("bearer ", "")
            if token == settings.API_KEY:
                return {"sub": "system"}

            jwk_client = PyJWKClient(self.jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)

            claims = self.jwt.decode(
                token,
                key=signing_key.key,
                algorithms=["RS256"],
                issuer=self.cognito_issuer,
                options={"verify_aud": False},
            )
            return claims
        except InvalidTokenError as e:
            print(e)
            raise UnauthenticatedException()

    def get_current_user(self, token: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        return self.decode_token(token.credentials)
