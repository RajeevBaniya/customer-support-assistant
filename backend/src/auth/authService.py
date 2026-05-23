from sqlalchemy.ext.asyncio import AsyncSession

from core.appEnvironment import AppEnvironment
from models.organizationModel import Organization
from models.userModel import User
from repositories.organizationRepository import OrganizationRepository
from repositories.userRepository import UserRepository
from schemas.authSchemas import ClerkTokenPayload
from shared.customExceptions import AuthException, BaseApplicationException


def _workspace_title(given_name: str | None) -> str:
    name = (given_name or "").strip() or "User"
    return f"{name}'s Workspace"


def _slug_base(token: ClerkTokenPayload) -> str:
    if token.email and "@" in token.email:
        return token.email.split("@", 1)[0]
    return token.sub.replace("user_", "").replace("|", "-")


async def load_or_create_user(
    session: AsyncSession,
    settings: AppEnvironment,
    token: ClerkTokenPayload,
) -> User:
    users = UserRepository(session)
    orgs = OrganizationRepository(session)
    existing = await users.get_by_clerk_id_with_org(token.sub)
    if existing is not None:
        return existing

    member = await users.get_role_by_name("member")
    if member is None:
        raise BaseApplicationException(
            "Default member role is missing; run migrations.",
            error_code="server_misconfiguration",
            status_code=500,
            details={"role_name": "member"},
        )

    slug = await orgs.reserve_unique_slug(_slug_base(token))
    org = Organization(organization_name=_workspace_title(token.given_name), slug=slug)
    await orgs.add(org)

    email = (token.email or "").strip() or f"{token.sub}@users.clerk.local"
    user = User(
        clerk_user_id=token.sub,
        email_address=email[:320],
        first_name=token.given_name,
        last_name=token.family_name,
        organization_id=org.id,
    )
    await users.add(user)
    await users.attach_role(user.id, member.id)

    loaded = await users.get_by_clerk_id_with_org(token.sub)
    if loaded is None:
        raise AuthException("User bootstrap failed")
    return loaded


def auth_me_view(token: ClerkTokenPayload) -> dict[str, object]:
    return {
        "clerk_user_id": token.sub,
        "email": token.email,
        "email_verified": token.email_verified,
        "given_name": token.given_name,
        "family_name": token.family_name,
        "issuer": token.issuer,
        "expires_at": token.expires_at,
    }
