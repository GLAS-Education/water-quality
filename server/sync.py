import os
import asyncpg
import json
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from typing import Optional, Dict, Any, Union
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router for sync endpoints
router = APIRouter(prefix="/sync", tags=["sync"])

# Database connection pool
_db_pool = None

async def get_db_pool():
    """Get or create database connection pool"""
    global _db_pool
    if _db_pool is None:
        database_uri = os.getenv("DATABASE_URI")
        if not database_uri:
            raise HTTPException(status_code=500, detail="DATABASE_URI not configured")
        
        try:
            _db_pool = await asyncpg.create_pool(database_uri)
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
    
    return _db_pool

def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key from Authorization header"""
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Authorization header required"
        )
    
    api_key = os.getenv("API_KEY")
    if not api_key:
        logger.error("API_KEY environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )
    
    # Extract token from Authorization header
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    elif authorization.startswith("API-Key "):
        token = authorization[8:]
    
    if token != api_key:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return True

def flatten_json(obj: Dict[str, Any], parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary/JSON object using dot notation
    Example: {"test": {"foo": "bar"}} becomes {"test.foo": "bar"}
    """
    flattened = {}
    
    for key, value in obj.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            flattened.update(flatten_json(value, new_key, separator))
        elif isinstance(value, list):
            # Handle arrays - convert to JSON string for storage
            flattened[new_key] = json.dumps(value)
        else:
            flattened[new_key] = value
    
    return flattened

def infer_sql_type(value: Any) -> str:
    """
    Infer PostgreSQL column type from Python value
    All columns are nullable as per requirements
    """
    if value is None:
        return "TEXT"  # Default to TEXT for null values
    elif isinstance(value, bool):
        return "BOOLEAN"
    elif isinstance(value, int):
        # Use BIGINT to handle larger integers
        return "BIGINT"
    elif isinstance(value, float):
        return "DOUBLE PRECISION"
    elif isinstance(value, str):
        # Use TEXT for flexibility
        return "TEXT"
    elif isinstance(value, (datetime,)):
        return "TIMESTAMP"
    else:
        # Default to TEXT for complex types (already JSON serialized)
        return "TEXT"

async def experiment_exists(pool: asyncpg.Pool, experiment_id: str) -> bool:
    """Check if experiment already exists in database"""
    async with pool.acquire() as conn:
        # Check if there's a metadata entry for this experiment
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM experiments 
                WHERE id = $1
            )
        """, experiment_id)
        
        return result

async def device_table_exists(pool: asyncpg.Pool, experiment_id: str, device_id: str) -> bool:
    """Check if device table already exists for this experiment"""
    async with pool.acquire() as conn:
        # Check if there's a table for this specific device in this experiment
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
        """, f"exp_{experiment_id}_{device_id}")
        
        return result

async def create_experiment_tables(pool: asyncpg.Pool, experiment_id: str, device_id: str, flattened_data: Dict[str, Any]):
    """Create both typed and backup tables for a specific device in an experiment"""
    async with pool.acquire() as conn:
        # Create device-specific table names
        typed_table_name = f"exp_{experiment_id}_{device_id}"
        backup_table_name = f"exp_{experiment_id}_{device_id}_backup"
        
        # Build column definitions for typed table
        columns = []
        columns.append("id SERIAL PRIMARY KEY")
        columns.append("device_id TEXT")
        columns.append("timestamp TIMESTAMP DEFAULT NOW()")
        
        # Reserved column names that shouldn't be duplicated
        reserved_columns = {'id', 'device_id', 'timestamp'}
        
        # Add columns based on flattened data structure
        for key, value in flattened_data.items():
            # Sanitize column name (replace dots with underscores for SQL)
            col_name = key.replace('.', '_').replace('-', '_')
            
            # Skip if this would conflict with reserved columns
            if col_name.lower() in reserved_columns:
                logger.warning(f"Skipping column '{col_name}' as it conflicts with reserved column")
                continue
                
            sql_type = infer_sql_type(value)
            columns.append(f'"{col_name}" {sql_type}')
        
        # Create typed table
        create_typed_sql = f"""
            CREATE TABLE "{typed_table_name}" (
                {', '.join(columns)}
            )
        """
        
        await conn.execute(create_typed_sql)
        logger.info(f"Created typed table: {typed_table_name}")
        
        # Create backup table (untyped - stores raw JSON)
        create_backup_sql = f"""
            CREATE TABLE "{backup_table_name}" (
                id SERIAL PRIMARY KEY,
                device_id TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                raw_data JSONB
            )
        """
        
        await conn.execute(create_backup_sql)
        logger.info(f"Created backup table: {backup_table_name}")
        
        # Create experiment metadata entry (private by default) - only if it doesn't exist
        try:
            await conn.execute(
                "INSERT INTO experiments (id, pretty_name, is_public) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING",
                experiment_id, experiment_id, False
            )
            logger.info(f"Ensured experiment metadata exists: {experiment_id} (private by default)")
        except Exception as e:
            logger.warning(f"Failed to create experiment metadata for {experiment_id}: {e}")

async def insert_experiment_data(pool: asyncpg.Pool, experiment_id: str, device_id: str, 
                                flattened_data: Dict[str, Any], raw_data: Dict[str, Any]):
    """Insert data into both device-specific typed and backup tables"""
    async with pool.acquire() as conn:
        typed_table_name = f"exp_{experiment_id}_{device_id}"
        backup_table_name = f"exp_{experiment_id}_{device_id}_backup"
        
        # Reserved column names that shouldn't be included in data insertion
        reserved_columns = {'id', 'device_id', 'timestamp'}
        
        typed_success = False
        
        # Try to insert into typed table
        try:
            if flattened_data:
                # Sanitize column names for SQL and filter out reserved columns
                sanitized_data = {}
                for key, value in flattened_data.items():
                    sanitized_key = key.replace('.', '_').replace('-', '_')
                    # Skip reserved columns
                    if sanitized_key.lower() not in reserved_columns:
                        sanitized_data[sanitized_key] = value
                
                if sanitized_data:  # Only insert if there's data after filtering
                    columns = ['device_id'] + list(sanitized_data.keys())
                    values = [device_id] + list(sanitized_data.values())
                    placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
                    columns_str = ', '.join([f'"{col}"' for col in columns])
                    
                    insert_typed_sql = f"""
                        INSERT INTO "{typed_table_name}" ({columns_str})
                        VALUES ({placeholders})
                    """
                    
                    await conn.execute(insert_typed_sql, *values)
                    logger.info(f"Inserted data into typed table: {typed_table_name}")
                    typed_success = True
                else:
                    logger.info(f"No data to insert into typed table after filtering reserved columns")
                    typed_success = True  # Not an error, just no data
        except Exception as e:
            logger.error(f"Failed to insert into typed table {typed_table_name}: {e}")
            # Continue to backup insertion regardless
        
        # Always insert into backup table
        try:
            insert_backup_sql = f"""
                INSERT INTO "{backup_table_name}" (device_id, raw_data)
                VALUES ($1, $2)
            """
            
            await conn.execute(insert_backup_sql, device_id, json.dumps(raw_data))
            logger.info(f"Inserted data into backup table: {backup_table_name}")
        except Exception as e:
            logger.error(f"Failed to insert into backup table {backup_table_name}: {e}")
            # If backup fails, this is a critical error
            raise
        
        return typed_success

@router.post("/{device}")
async def sync_device_data(
    device: str,
    expid: str = Query(..., description="Experiment ID"),
    data: Dict[str, Any] = ...,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Sync data for a specific device and experiment
    
    - Creates device-specific tables automatically if new
    - Each device can have its own schema/columns
    - Flattens hierarchical JSON data
    - Stores both typed and raw backup data
    """
    try:
        logger.info(f"Received sync request for device: {device}, experiment: {expid}")
        
        # Get database pool
        pool = await get_db_pool()
        
        # Flatten the JSON data
        flattened_data = flatten_json(data)
        logger.info(f"Flattened data: {flattened_data}")
        
        # Check if experiment exists
        experiment_exists_flag = await experiment_exists(pool, expid)
        
        # Check if device table exists
        device_table_exists_flag = await device_table_exists(pool, expid, device)
        
        if not device_table_exists_flag:
            # Create new device tables within experiment
            logger.info(f"Creating new device tables for experiment: {expid}, device: {device}")
            await create_experiment_tables(pool, expid, device, flattened_data)
        
        # Insert data into both tables
        typed_success = await insert_experiment_data(pool, expid, device, flattened_data, data)
        
        return {
            "status": "success",
            "message": "Data synchronized successfully",
            "experiment_id": expid,
            "device_id": device,
            "experiment_existed": experiment_exists_flag,
            "device_table_existed": device_table_exists_flag,
            "typed_table_success": typed_success,
            "backup_table_success": True,  # If we reach here, backup succeeded
            "flattened_keys": list(flattened_data.keys())
        }
        
    except Exception as e:
        logger.error(f"Error syncing data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data: {str(e)}"
        )

@router.get("/")
async def sync_root(authenticated: bool = Depends(verify_api_key)):
    """
    Root sync endpoint
    """
    return {"message": "Sync API is available", "status": "authenticated"}

@router.get("/status")
async def sync_status(authenticated: bool = Depends(verify_api_key)):
    """
    Get sync status
    """
    return {
        "status": "active",
        "message": "Sync service is running",
        "authenticated": True
    }

@router.get("/health")
async def sync_health(authenticated: bool = Depends(verify_api_key)):
    """
    Sync service health check
    """
    return {
        "status": "healthy",
        "service": "sync",
        "authenticated": True
    }
