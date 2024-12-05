from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWT
from jwt.exceptions import InvalidTokenError
import requests

from config import settings


class UnauthenticatedException(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication123")


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
            
            header = self.jwt.get_unverified_header(token)
            kid = header["kid"]
            jwks = self.get_jwks()
            key = [k for k in jwks if k["kid"] == kid][0]
            
            public_key = self.jwt.algorithms.RSAAlgorithm.from_jwk(key)
            
            claims = self.jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256"],
                audience=self.cognito_audience,
                issuer=self.cognito_issuer
            )
            return claims
        except InvalidTokenError as e:
            print(e)
            raise UnauthenticatedException()

    def get_current_user(self, token: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        return self.decode_token(token.credentials)
