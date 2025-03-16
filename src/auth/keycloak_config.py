from fastapi.security import OAuth2AuthorizationCodeBearer
from keycloak import KeycloakOpenID
from settings import Settings

settings = Settings()

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"http://{settings.KC_HOSTNAME}:{settings.KC_PORT}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth",
    tokenUrl=f"http://{settings.KC_HOSTNAME}:{settings.KC_PORT}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
)

keycloak_openid = KeycloakOpenID(
    server_url=f"http://{settings.KC_HOSTNAME}:{settings.KC_PORT}/",
    client_id=settings.KEYCLOAK_CLIENT_ID,
    realm_name=settings.KEYCLOAK_REALM,
    client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
    verify=True,
)
