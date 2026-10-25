from fastapi import Security, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from server.app.database import get_db
from server.app.models import APIKey, Tenant
from server.app.auth import hash_api_key

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_tenant(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(api_key)

    query = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.is_active,
    )
    result = await db.execute(query)
    api_key_obj = result.scalars().first()

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    # Get Tenant
    tenant_query = select(Tenant).where(
        Tenant.id == api_key_obj.tenant_id,
        Tenant.status == "active",
    )
    tenant_res = await db.execute(tenant_query)
    tenant = tenant_res.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive or disabled",
        )

    return tenant
