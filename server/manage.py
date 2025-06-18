import os
import asyncpg
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
from auth import get_current_user, require_auth

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router for manage endpoints
router = APIRouter(prefix="/manage", tags=["manage"])

# Pydantic models for request/response
class ExperimentUpdate(BaseModel):
    pretty_name: Optional[str] = None
    is_public: Optional[bool] = None

class ExperimentResponse(BaseModel):
    id: str
    pretty_name: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
class ExperimentCreate(BaseModel):
    id: str
    pretty_name: Optional[str] = None
    is_public: bool = False

async def get_db_pool():
    """Get database connection pool"""
    database_uri = os.getenv("DATABASE_URI")
    if not database_uri:
        raise HTTPException(status_code=500, detail="DATABASE_URI not configured")
    
    try:
        pool = await asyncpg.create_pool(database_uri)
        return pool
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

async def ensure_experiment_exists(pool: asyncpg.Pool, experiment_id: str):
    """Ensure experiment exists in experiments table, create if not"""
    async with pool.acquire() as conn:
        # Check if experiment already exists
        existing = await conn.fetchrow(
            "SELECT id FROM experiments WHERE id = $1",
            experiment_id
        )
        
        if not existing:
            # Create experiment with default values
            pretty_name = experiment_id  # Default pretty name is the ID
            await conn.execute(
                "INSERT INTO experiments (id, pretty_name, is_public) VALUES ($1, $2, $3)",
                experiment_id, pretty_name, False
            )
            logger.info(f"Created new experiment entry: {experiment_id}")

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

async def experiment_has_data_tables(pool: asyncpg.Pool, experiment_id: str) -> bool:
    """Check if experiment has any device data tables"""
    device_ids = await get_experiment_device_ids(pool, experiment_id)
    return len(device_ids) > 0

async def get_experiment_record_count(pool: asyncpg.Pool, experiment_id: str) -> int:
    """Get total record count across all devices in an experiment"""
    device_ids = await get_experiment_device_ids(pool, experiment_id)
    total_count = 0
    
    async with pool.acquire() as conn:
        for device_id in device_ids:
            table_name = f"exp_{experiment_id}_{device_id}"
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
                total_count += count
            except Exception as e:
                logger.warning(f"Failed to count records in {table_name}: {e}")
    
    return total_count

@router.get("/experiments")
async def list_experiments(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """List all experiments from the experiments metadata table that have corresponding data tables"""
    try:
        # Debug logging
        if current_user is not None:
            logger.info(f"Authenticated user listing experiments: {current_user.get('user_name', 'unknown')}")
        else:
            logger.info("Unauthenticated user listing experiments")
        
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # If user is authenticated, show all experiments
            # If not authenticated, show only public experiments
            if current_user is not None:
                # Show all experiments for authenticated users
                logger.info("Fetching all experiments for authenticated user")
                exp_rows = await conn.fetch("""
                    SELECT * FROM experiments 
                    ORDER BY created_at DESC
                """)
            else:
                # Show only public experiments for unauthenticated users
                logger.info("Fetching only public experiments for unauthenticated user")
                exp_rows = await conn.fetch("""
                    SELECT * FROM experiments 
                    WHERE is_public = true
                    ORDER BY created_at DESC
                """)
            
            experiments = []
            
            for exp_data in exp_rows:
                exp_id = exp_data["id"]
                
                # Check if the experiment has any device data tables
                has_data = await experiment_has_data_tables(pool, exp_id)
                
                if has_data:
                    # Get total record count across all devices
                    record_count = await get_experiment_record_count(pool, exp_id)
                    
                    experiments.append({
                        "id": exp_data["id"],
                        "pretty_name": exp_data["pretty_name"],
                        "is_public": exp_data["is_public"],
                        "created_at": exp_data["created_at"].isoformat(),
                        "updated_at": exp_data["updated_at"].isoformat(),
                        "record_count": record_count
                    })
                else:
                    logger.warning(f"Experiment {exp_id} exists in metadata but has no device data tables")
        
        await pool.close()
        
        # Debug logging for final results
        logger.info(f"Returning {len(experiments)} experiments (authenticated: {current_user is not None})")
        
        return {
            "experiments": experiments,
            "total_count": len(experiments),
            "authenticated": current_user is not None,
            "user_info": current_user.get('user_name', None) if current_user else None
        }
        
    except Exception as e:
        logger.error(f"Error listing experiments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list experiments: {str(e)}")

@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get specific experiment details"""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Check if experiment has any device data tables
            has_data = await experiment_has_data_tables(pool, experiment_id)
            
            if not has_data:
                raise HTTPException(status_code=404, detail="Experiment not found")
            
            # Ensure experiment exists in experiments table
            await ensure_experiment_exists(pool, experiment_id)
            
            # Get experiment metadata
            exp_data = await conn.fetchrow(
                "SELECT * FROM experiments WHERE id = $1",
                experiment_id
            )
            
            if not exp_data:
                raise HTTPException(status_code=404, detail="Experiment metadata not found")
            
            # Check access permissions - if user is not authenticated, only allow public experiments
            if current_user is None and not exp_data["is_public"]:
                raise HTTPException(status_code=403, detail="Access denied: Experiment is private")
            
            # Get device IDs and record counts
            device_ids = await get_experiment_device_ids(pool, experiment_id)
            
            typed_count = 0
            backup_count = 0
            all_columns = set()
            
            # Aggregate data from all device tables
            for device_id in device_ids:
                typed_table = f"exp_{experiment_id}_{device_id}"
                backup_table = f"exp_{experiment_id}_{device_id}_backup"
                
                # Count records
                try:
                    device_typed_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{typed_table}"')
                    device_backup_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{backup_table}"')
                    typed_count += device_typed_count
                    backup_count += device_backup_count
                except Exception as e:
                    logger.warning(f"Failed to count records for device {device_id}: {e}")
                
                # Get column information for this device's typed table
                try:
                    columns = await conn.fetch(f"""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = $1 
                        AND column_name NOT IN ('id', 'device_id', 'timestamp')
                        ORDER BY ordinal_position
                    """, typed_table)
                    
                    for col in columns:
                        all_columns.add((col["column_name"], col["data_type"]))
                except Exception as e:
                    logger.warning(f"Failed to get columns for device {device_id}: {e}")
            
            # Convert set to list for JSON serialization
            column_info = [{"name": name, "type": data_type} for name, data_type in sorted(all_columns)]
        
        await pool.close()
        
        return {
            "id": exp_data["id"],
            "pretty_name": exp_data["pretty_name"],
            "is_public": exp_data["is_public"],
            "created_at": exp_data["created_at"].isoformat(),
            "updated_at": exp_data["updated_at"].isoformat(),
            "record_counts": {
                "typed": typed_count,
                "backup": backup_count
            },
            "columns": column_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get experiment: {str(e)}")

@router.put("/experiments/{experiment_id}")
async def update_experiment(
    experiment_id: str,
    update_data: ExperimentUpdate,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Update experiment settings"""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Check if experiment data table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, f"exp_{experiment_id}")
            
            if not table_exists:
                raise HTTPException(status_code=404, detail="Experiment not found")
            
            # Ensure experiment exists in experiments table
            await ensure_experiment_exists(pool, experiment_id)
            
            # Build update query
            update_fields = []
            values = []
            param_count = 1
            
            if update_data.pretty_name is not None:
                update_fields.append(f"pretty_name = ${param_count}")
                values.append(update_data.pretty_name)
                param_count += 1
            
            if update_data.is_public is not None:
                update_fields.append(f"is_public = ${param_count}")
                values.append(update_data.is_public)
                param_count += 1
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            # Add updated_at timestamp
            update_fields.append(f"updated_at = NOW()")
            
            # Add experiment_id for WHERE clause
            values.append(experiment_id)
            
            update_query = f"""
                UPDATE experiments 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING *
            """
            
            updated_exp = await conn.fetchrow(update_query, *values)
            
            if not updated_exp:
                raise HTTPException(status_code=404, detail="Experiment not found")
        
        await pool.close()
        
        logger.info(f"Updated experiment {experiment_id} by user {current_user['user_name']}")
        
        return {
            "id": updated_exp["id"],
            "pretty_name": updated_exp["pretty_name"],
            "is_public": updated_exp["is_public"],
            "created_at": updated_exp["created_at"].isoformat(),
            "updated_at": updated_exp["updated_at"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update experiment: {str(e)}")

@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Delete experiment and all its device data (use with caution!)"""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Get all device IDs for this experiment
            device_ids = await get_experiment_device_ids(pool, experiment_id)
            
            if not device_ids:
                raise HTTPException(status_code=404, detail="Experiment not found")
            
            # Count records before deletion
            total_typed_count = 0
            total_backup_count = 0
            
            # Delete all device tables
            for device_id in device_ids:
                typed_table = f"exp_{experiment_id}_{device_id}"
                backup_table = f"exp_{experiment_id}_{device_id}_backup"
                
                try:
                    # Get counts before deletion
                    typed_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{typed_table}"')
                    backup_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{backup_table}"')
                    total_typed_count += typed_count
                    total_backup_count += backup_count
                    
                    # Delete tables
                    await conn.execute(f'DROP TABLE IF EXISTS "{typed_table}"')
                    await conn.execute(f'DROP TABLE IF EXISTS "{backup_table}"')
                    logger.info(f"Deleted tables for device {device_id} in experiment {experiment_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to delete tables for device {device_id}: {e}")
            
            # Delete from experiments table
            deleted_exp = await conn.fetchrow(
                "DELETE FROM experiments WHERE id = $1 RETURNING *",
                experiment_id
            )
        
        await pool.close()
        
        logger.warning(f"DELETED experiment {experiment_id} by user {current_user['user_name']} - {len(device_ids)} devices, {total_typed_count} typed records, {total_backup_count} backup records")
        
        return {
            "message": f"Experiment '{experiment_id}' deleted successfully",
            "deleted_devices": len(device_ids),
            "deleted_records": {
                "typed": total_typed_count,
                "backup": total_backup_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete experiment: {str(e)}")

@router.get("/stats")
async def get_management_stats(current_user: Dict[str, Any] = Depends(require_auth)):
    """Get overall statistics for experiment management"""
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Count total experiments
            total_experiments = await conn.fetchval("SELECT COUNT(*) FROM experiments")
            public_experiments = await conn.fetchval("SELECT COUNT(*) FROM experiments WHERE is_public = true")
            
            # Get total record counts across all experiments and devices
            total_typed_records = 0
            total_backup_records = 0
            total_devices = 0
            
            # Get all device tables (typed tables, not backup)
            table_rows = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE 'exp_%' 
                AND table_name NOT LIKE '%_backup'
                AND table_schema = 'public'
            """)
            
            for row in table_rows:
                table_name = row["table_name"]
                backup_table = f"{table_name}_backup"
                
                try:
                    typed_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
                    backup_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{backup_table}"')
                    
                    total_typed_records += typed_count
                    total_backup_records += backup_count
                    total_devices += 1
                except Exception as e:
                    logger.warning(f"Failed to count records in {table_name}: {e}")
        
        await pool.close()
        
        return {
            "experiments": {
                "total": total_experiments,
                "public": public_experiments,
                "private": total_experiments - public_experiments
            },
            "devices": {
                "total": total_devices
            },
            "records": {
                "total_typed": total_typed_records,
                "total_backup": total_backup_records
            },
            "user": {
                "name": current_user["user_name"],
                "team": current_user["team_domain"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting management stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/debug/auth")
async def debug_auth_status(current_user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """Debug endpoint to check authentication status"""
    return {
        "authenticated": current_user is not None,
        "user_info": current_user if current_user else None,
        "timestamp": datetime.now().isoformat()
    } 