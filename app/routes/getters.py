from fastapi import APIRouter, Depends

from app.database import get_google_service, get_data_collector
from app.pipeline import DataCollectorPipeline

router = APIRouter(tags=["Getters"], prefix="/query")


@router.post("/month")
async def get_month_data(year: int, month: int, symbol: str, google_accessor=Depends(get_google_service), data_collector=Depends(get_data_collector)):
    try:
        if symbol in data_collector.symbol_folder_ids.keys():
            # Retrieve spreadsheet_id
            spreadsheet_id = google_accessor.create_or_get_spreadsheet_in_folder(year,
                                                                                 data_collector.symbol_folder_ids[symbol],
                                                                                 tuple(
                                                                                     []),
                                                                                 tuple([]))
            data = google_accessor.retrieve_sheet_data(
                spreadsheet_id, DataCollectorPipeline.SHEET_NAMES[month - 1])

            return {"message": "success", "data": data}

    except Exception as e:
        return {'message': 'failed', 'error': str(e)}


@router.post("/year")
async def get_year_data(year: int, symbol: str, google_accessor=Depends(get_google_service), data_collector=Depends(get_data_collector)):
    try:
        if symbol in data_collector.symbol_folder_ids.keys():
            # Retrieve spreadsheet_id
            spreadsheet_id = google_accessor.create_or_get_spreadsheet_in_folder(year,
                                                                                 data_collector.symbol_folder_ids[symbol],
                                                                                 tuple(
                                                                                     []),
                                                                                 tuple([]))
            data = google_accessor.retrieve_spreadsheet_data(spreadsheet_id)

            return {"message": "success", "data": data}

    except Exception as e:
        return {'message': 'failed', 'error': str(e)}
