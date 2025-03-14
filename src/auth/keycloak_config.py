from keycloak import KeycloakOpenID

from settings import Settings

settings = Settings()


keycloak_openid = KeycloakOpenID(
    server_url=f"http://{settings.KC_HOSTNAME}:{settings.KC_PORT}/auth/",
    client_id="zip-service-client",
    realm_name="zip-service-realm",
    client_secret_key=settings.KEYCLOAK_CLIENT_SECRET
)