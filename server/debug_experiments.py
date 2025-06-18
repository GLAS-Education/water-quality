import os
import asyncio
import asyncpg

async def check_experiments():
    database_uri = os.getenv('DATABASE_URI')
    if not database_uri:
        print('DATABASE_URI not set')
        return
    
    pool = await asyncpg.create_pool(database_uri)
    async with pool.acquire() as conn:
        # Get all experiments from metadata table
        print('=== All experiments in metadata table ===')
        experiments = await conn.fetch('SELECT id, pretty_name, is_public FROM experiments ORDER BY created_at DESC')
        for exp in experiments:
            print(f"ID: {exp['id']}, Name: {exp['pretty_name']}, Public: {exp['is_public']}")
        
        print(f'\nTotal experiments in metadata: {len(experiments)}')
        
        # Check which have data tables
        print('\n=== Checking for corresponding data tables ===')
        for exp in experiments:
            table_name = f'exp_{exp["id"]}'
            exists = await conn.fetchval('SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)', table_name)
            if exists:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
                print(f'✓ {table_name}: {count} records')
            else:
                print(f'✗ {table_name}: table missing')
    
    await pool.close()

if __name__ == '__main__':
    asyncio.run(check_experiments()) 