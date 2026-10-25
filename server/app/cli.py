import sys
import asyncio
import argparse
from server.app.database import AsyncSessionLocal, engine, Base
from server.app.models import Tenant, APIKey
from server.app.auth import generate_api_key


async def create_tenant_cmd(tenant_name: str, key_name: str = "default"):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create Tenant
        tenant = Tenant(name=tenant_name, status="active")
        session.add(tenant)
        await session.flush()

        # Generate API Key
        raw_key, key_hash = generate_api_key(prefix="ww_")
        api_key = APIKey(
            tenant_id=tenant.id,
            key_hash=key_hash,
            name=key_name,
            is_active=True,
        )
        session.add(api_key)
        await session.commit()

        print("=" * 60)
        print(" Weirwise Tenant & API Key Created Successfully")
        print("=" * 60)
        print(f" Tenant ID : {tenant.id}")
        print(f" Tenant Name: {tenant.name}")
        print(f" API Key    : {raw_key}")
        print("=" * 60)
        print(" SAVE THIS KEY NOW! It will never be displayed again.")
        print("=" * 60)


def cli():
    parser = argparse.ArgumentParser(description="Weirwise Admin CLI")
    subparsers = parser.add_subparsers(dest="command")

    admin_parser = subparsers.add_parser("admin")
    admin_sub = admin_parser.add_subparsers(dest="subcommand")

    create_tenant_p = admin_sub.add_parser("create-tenant")
    create_tenant_p.add_argument("--name", required=True, help="Tenant workspace name")
    create_tenant_p.add_argument(
        "--key-name", default="default", help="Descriptive name for the API key"
    )

    args = parser.parse_args()

    if args.command == "admin" and args.subcommand == "create-tenant":
        asyncio.run(create_tenant_cmd(args.name, args.key_name))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
