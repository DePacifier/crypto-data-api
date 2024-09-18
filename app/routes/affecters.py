import asyncio

from fastapi import APIRouter, Depends
from app.database import get_data_collector

router = APIRouter(tags=["Affecters"])


@router.post("/__space/v0/actions")
async def collect_data(event: dict, data_collector=Depends(get_data_collector)):
    try:
        print(event)
        asyncio.create_task(data_collector.run())
        return {"message": "Data Collected Successfully"}
    except Exception as e:
        return {"message": "Failed to Collect Data", "error": str(e)}
