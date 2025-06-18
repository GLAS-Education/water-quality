import os
import asyncpg
import json
import time
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from typing import Optional, Dict, Any, List
import logging
from functools import lru_cache
from datetime import datetime
from auth import get_current_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router for query endpoints
router = APIRouter(prefix="/query", tags=["query"])

# Cache configuration
CACHE_TTL_SECONDS = 300  # 5 minutes
_query_cache = {}
_cache_timestamps = {}

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

async def get_db_pool():
    """Get database connection pool (reuse from sync.py logic)"""
    database_uri = os.getenv("DATABASE_URI")
    if not database_uri:
        raise HTTPException(status_code=500, detail="DATABASE_URI not configured")
    
    try:
        pool = await asyncpg.create_pool(database_uri)
        return pool
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def is_cache_valid(cache_key: str) -> bool:
    """Check if cache entry is still valid based on TTL"""
    if cache_key not in _cache_timestamps:
        return False
    
    cache_time = _cache_timestamps[cache_key]
    current_time = time.time()
    
    return (current_time - cache_time) < CACHE_TTL_SECONDS

def get_cache_key(experiment_id: str, device_id: str) -> str:
    """Generate cache key for experiment/device combination"""
    return f"{experiment_id}:{device_id}"

def cache_result(cache_key: str, result: Any):
    """Store result in cache with timestamp"""
    _query_cache[cache_key] = result
    _cache_timestamps[cache_key] = time.time()
    logger.info(f"Cached result for key: {cache_key}")

def get_cached_result(cache_key: str) -> Optional[Any]:
    """Get result from cache if valid"""
    if is_cache_valid(cache_key):
        logger.info(f"Cache hit for key: {cache_key}")
        return _query_cache[cache_key]
    else:
        # Clean up expired cache entries
        if cache_key in _query_cache:
            del _query_cache[cache_key]
        if cache_key in _cache_timestamps:
            del _cache_timestamps[cache_key]
        logger.info(f"Cache miss for key: {cache_key}")
        return None

async def experiment_exists(pool: asyncpg.Pool, experiment_id: str) -> bool:
    """Check if experiment exists in database"""
    async with pool.acquire() as conn:
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM experiments 
                WHERE id = $1
            )
        """, experiment_id)
        return result

async def get_experiment_device_ids(pool: asyncpg.Pool, experiment_id: str) -> List[str]:
    """Get all device IDs for an experiment by looking at table names"""
    async with pool.acquire() as conn:
        # Find all tables that match the pattern exp_{experiment_id}_{device_id}
        # We exclude backup tables (which end with _backup)
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name LIKE $1 
            AND table_schema = 'public'
            ORDER BY table_name
        """, f"exp_{experiment_id}_%")
        
        device_ids = []
        prefix = f"exp_{experiment_id}_"
        backup_suffix = "_backup"
        
        for table in tables:
            table_name = table["table_name"]
            if table_name.startswith(prefix) and not table_name.endswith(backup_suffix):
                # Extract device_id from table name
                device_id = table_name[len(prefix):]
                device_ids.append(device_id)
        
        return device_ids

async def device_table_exists(pool: asyncpg.Pool, experiment_id: str, device_id: str) -> bool:
    """Check if device table exists for this experiment"""
    async with pool.acquire() as conn:
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
        """, f"exp_{experiment_id}_{device_id}")
        return result

async def ensure_experiment_metadata(pool: asyncpg.Pool, experiment_id: str):
    """Ensure experiment exists in experiments table"""
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM experiments WHERE id = $1",
            experiment_id
        )
        
        if not existing:
            # Create experiment with default values
            pretty_name = experiment_id
            await conn.execute(
                "INSERT INTO experiments (id, pretty_name, is_public) VALUES ($1, $2, $3)",
                experiment_id, pretty_name, False
            )
            logger.info(f"Created new experiment metadata entry: {experiment_id}")

async def check_experiment_access(pool: asyncpg.Pool, experiment_id: str, current_user: Optional[Dict[str, Any]]) -> bool:
    """Check if user can access experiment (public OR authenticated)"""
    async with pool.acquire() as conn:
        # Ensure experiment metadata exists
        await ensure_experiment_metadata(pool, experiment_id)
        
        # Get experiment public status
        is_public = await conn.fetchval(
            "SELECT is_public FROM experiments WHERE id = $1",
            experiment_id
        )
        
        # Allow access if experiment is public OR user is authenticated
        return is_public or (current_user is not None)

async def query_experiment_data(pool: asyncpg.Pool, experiment_id: str, device_id: str, include_backup: bool = False) -> Dict[str, Any]:
    """Query data for a specific experiment and device"""
    async with pool.acquire() as conn:
        typed_table_name = f"exp_{experiment_id}_{device_id}"
        backup_table_name = f"exp_{experiment_id}_{device_id}_backup"
        
        # Check if device table exists
        table_exists = await device_table_exists(pool, experiment_id, device_id)
        if not table_exists:
            return {
                "data": [],
                "record_count": 0
            }
        
        # Query typed data
        typed_data = []
        try:
            typed_rows = await conn.fetch(f"""
                SELECT * FROM "{typed_table_name}" 
                WHERE device_id = $1 
                ORDER BY id ASC
            """, device_id)
            
            # Convert rows to dictionaries
            for row in typed_rows:
                row_dict = dict(row)
                # Convert datetime objects to ISO strings for JSON serialization
                for key, value in row_dict.items():
                    if isinstance(value, datetime):
                        row_dict[key] = value.isoformat()
                typed_data.append(row_dict)
                
        except Exception as e:
            logger.warning(f"Failed to query typed table {typed_table_name}: {e}")
        
        result = {
            "data": typed_data,
            "record_count": len(typed_data)
        }
        
        # Only query backup data if requested
        if include_backup:
            backup_data = []
            try:
                backup_rows = await conn.fetch(f"""
                    SELECT id, device_id, timestamp, raw_data FROM "{backup_table_name}" 
                    WHERE device_id = $1 
                    ORDER BY id ASC
                """, device_id)
                
                for row in backup_rows:
                    row_dict = {
                        "id": row["id"],
                        "device_id": row["device_id"],
                        "timestamp": row["timestamp"].isoformat(),
                        "raw_data": row["raw_data"]  # This is already JSON
                    }
                    backup_data.append(row_dict)
                    
            except Exception as e:
                logger.warning(f"Failed to query backup table {backup_table_name}: {e}")
            
            result["backup_data"] = backup_data
            result["backup_record_count"] = len(backup_data)
        
        return result

@router.get("/{device}")
async def query_device_data(
    device: str,
    expid: str = Query(..., description="Experiment ID"),
    backup: bool = Query(False, description="Include backup data"),
    authenticated: bool = Depends(verify_api_key),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Query all data for a specific device and experiment
    
    - Returns typed data by default
    - Include backup data with ?backup=true parameter
    - Implements server-side caching (5 minute TTL)
    - Results ordered by id (oldest first)
    - Each device has its own table with device-specific schema
    """
    try:
        logger.info(f"Received query request for device: {device}, experiment: {expid}")
        
        # Check cache first (include backup flag in cache key for different cache entries)
        cache_key = f"{get_cache_key(expid, device)}:backup={backup}"
        cached_result = get_cached_result(cache_key)
        
        if cached_result:
            return {
                "status": "success",
                "experiment_id": expid,
                "device_id": device,
                "cached": True,
                "cache_ttl_seconds": CACHE_TTL_SECONDS,
                "include_backup": backup,
                **cached_result
            }
        
        # Get database pool
        pool = await get_db_pool()
        
        # Check if experiment exists
        exists = await experiment_exists(pool, expid)
        
        if not exists:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment '{expid}' not found"
            )
        
        # Check access permissions (public experiment OR authenticated user)
        has_access = await check_experiment_access(pool, expid, current_user)
        
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Experiment is private. Authentication required."
            )
        
        # Check if device table exists
        device_exists = await device_table_exists(pool, expid, device)
        
        if not device_exists:
            raise HTTPException(
                status_code=404,
                detail=f"Device '{device}' not found in experiment '{expid}'"
            )
        
        # Query the data
        query_result = await query_experiment_data(pool, expid, device, include_backup=backup)
        
        # Cache the result
        cache_result(cache_key, query_result)
        
        # Close the pool
        await pool.close()
        
        return {
            "status": "success",
            "experiment_id": expid,
            "device_id": device,
            "cached": False,
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "include_backup": backup,
            **query_result
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error querying data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query data: {str(e)}"
        )


@router.get("/cache/stats")
async def cache_statistics(authenticated: bool = Depends(verify_api_key)):
    """Get cache statistics for monitoring"""
    current_time = time.time()
    valid_entries = 0
    
    for cache_key in _cache_timestamps:
        if (current_time - _cache_timestamps[cache_key]) < CACHE_TTL_SECONDS:
            valid_entries += 1
    
    return {
        "cache_stats": {
            "total_entries": len(_query_cache),
            "valid_entries": valid_entries,
            "expired_entries": len(_query_cache) - valid_entries,
            "ttl_seconds": CACHE_TTL_SECONDS
        }
    }

@router.delete("/cache/clear")
async def clear_cache(authenticated: bool = Depends(verify_api_key)):
    """Clear all cache entries"""
    global _query_cache, _cache_timestamps
    
    old_count = len(_query_cache)
    _query_cache.clear()
    _cache_timestamps.clear()
    
    logger.info(f"Cache cleared: {old_count} entries removed")
    
    return {
        "status": "success",
        "message": f"Cache cleared: {old_count} entries removed"
    }

@router.get("/experiment/{experiment_id}/all")
async def query_all_experiment_data(
    experiment_id: str,
    backup: bool = Query(False, description="Include backup data"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Query all data for all devices in an experiment
    
    - Returns typed data from all devices by default
    - Include backup data with ?backup=true parameter
    - Results ordered by id (oldest first)
    - Public experiments accessible without authentication
    - Private experiments require authentication
    - Each device has its own table with device-specific schema
    - Combines data from all device tables in the experiment
    """
    try:
        logger.info(f"Received query request for all devices in experiment: {experiment_id}")
        
        # Get database pool
        pool = await get_db_pool()
        
        # Check if experiment exists
        exists = await experiment_exists(pool, experiment_id)
        
        if not exists:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment '{experiment_id}' not found"
            )
        
        # Check access permissions (public experiment OR authenticated user)
        has_access = await check_experiment_access(pool, experiment_id, current_user)
        
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Experiment is private. Authentication required."
            )
        
        # Get all device IDs for this experiment
        device_ids = await get_experiment_device_ids(pool, experiment_id)
        
        if not device_ids:
            return {
                "status": "success",
                "experiment_id": experiment_id,
                "include_backup": backup,
                "data": [],
                "record_count": 0,
                "device_ids": [],
                "device_count": 0
            }
        
        async with pool.acquire() as conn:
            all_typed_data = []
            all_backup_data = []
            
            # Query each device table
            for device_id in device_ids:
                typed_table_name = f"exp_{experiment_id}_{device_id}"
                backup_table_name = f"exp_{experiment_id}_{device_id}_backup"
                
                # Query typed data for this device
                try:
                    typed_rows = await conn.fetch(f"""
                        SELECT * FROM "{typed_table_name}" 
                        ORDER BY id ASC
                    """)
                    
                    # Convert rows to dictionaries
                    for row in typed_rows:
                        row_dict = dict(row)
                        # Convert datetime objects to ISO strings for JSON serialization
                        for key, value in row_dict.items():
                            if isinstance(value, datetime):
                                row_dict[key] = value.isoformat()
                        all_typed_data.append(row_dict)
                        
                except Exception as e:
                    logger.warning(f"Failed to query typed table {typed_table_name}: {e}")
                
                # Query backup data if requested
                if backup:
                    try:
                        backup_rows = await conn.fetch(f"""
                            SELECT id, device_id, timestamp, raw_data FROM "{backup_table_name}" 
                            ORDER BY id ASC
                        """)
                        
                        for row in backup_rows:
                            row_dict = {
                                "id": row["id"],
                                "device_id": row["device_id"],
                                "timestamp": row["timestamp"].isoformat(),
                                "raw_data": row["raw_data"]  # This is already JSON
                            }
                            all_backup_data.append(row_dict)
                            
                    except Exception as e:
                        logger.warning(f"Failed to query backup table {backup_table_name}: {e}")
            
            # Sort all data by timestamp for consistent ordering across devices
            all_typed_data.sort(key=lambda x: x.get('timestamp', ''))
            if backup:
                all_backup_data.sort(key=lambda x: x.get('timestamp', ''))
            
            result = {
                "data": all_typed_data,
                "record_count": len(all_typed_data),
                "device_ids": device_ids,
                "device_count": len(device_ids)
            }
            
            if backup:
                result["backup_data"] = all_backup_data
                result["backup_record_count"] = len(all_backup_data)
        
        # Close the pool
        await pool.close()
        
        return {
            "status": "success",
            "experiment_id": experiment_id,
            "include_backup": backup,
            **result
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error querying all experiment data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query all experiment data: {str(e)}"
        ) 