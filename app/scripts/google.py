from os import path
from functools import lru_cache

from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = path.abspath(path.join(path.abspath(
    __file__), '../../env/google_credentials.json'))
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']


class GoogleAccessor:
    def __init__(self, service_account_file=SERVICE_ACCOUNT_FILE, scopes=SCOPES) -> None:
        # Load the service account credentials
        creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=scopes)

        # Build the service
        self.sheet_service = build('sheets', 'v4', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)

    @lru_cache(maxsize=None)
    def create_or_get_folder(self, name, parent_id=None):
        # Check if the folder already exists
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        response = self.drive_service.files().list(q=query, spaces='drive',
                                                   fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            # Folder already exists, return its ID
            return files[0]['id']
        else:
            # Create the folder
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = self.drive_service.files().create(
                body=file_metadata, fields='id').execute()
            return folder.get('id')

    @lru_cache(maxsize=None)
    def create_or_get_spreadsheet_in_folder(self,
                                            name: str,
                                            folder_id: str,
                                            sheets: list,
                                            column_headers: list):
        # Check if the spreadsheet already exists
        query = f"name='{name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents"
        response = self.drive_service.files().list(q=query, spaces='drive',
                                                   fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            # Spreadsheet already exists, return its ID
            return files[0]['id']
        else:
            if len(sheets) < 1 or len(column_headers) < 1:
                raise ValueError(
                    "Invalid Sheets Names and Column Headers Provided.")
            # Create the spreadsheet
            spreadsheet_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [folder_id]
            }
            spreadsheet = self.drive_service.files().create(
                body=spreadsheet_metadata, fields='id').execute()
            spreadsheet_id = spreadsheet.get('id')

            # Prepare batch update requests to add months and set headers
            requests = [{
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': 0,  # Default sheet has ID 0
                        'title': sheets[0]
                    },
                    'fields': 'title'
                }
            }, {
                'updateCells': {
                    'rows': [{'values': [{'userEnteredValue': {'stringValue': header}} for header in column_headers]}],
                    'fields': 'userEnteredValue',
                    'start': {'sheetId': 0, 'rowIndex': 0, 'columnIndex': 0}
                }
            }]

            for i, sheet in enumerate(sheets[1:]):
                sheet_id = i + 1
                requests.append({
                    'addSheet': {'properties': {'title': sheet, 'sheetId': sheet_id}}
                })
                requests.append({
                    'updateCells': {
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': header}} for header in column_headers]}],
                        'fields': 'userEnteredValue',
                        'start': {'sheetId': sheet_id, 'rowIndex': 0, 'columnIndex': 0}
                    }
                })

            # Execute batch update to add new sheets with headers
            batch_update_body = {'requests': requests}
            self.sheet_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id,
                                                          body=batch_update_body).execute()

            print(f"Spreadsheet created with ID: {spreadsheet_id}")

            return spreadsheet_id

    def add_row_data(self, spreadsheet_id: str, sheet_name: str, data: list) -> None:
        request = self.sheet_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A1',  # Append starting at column A
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': data}
        )

        response = request.execute()

        return response

    def retrieve_sheet_data(self, spreadsheet_id: str, sheet_name: str):
        range_name = f'{sheet_name}!A:Z'

        # Read the data
        result = self.sheet_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        rows = result.get('values', [])

        return rows

    def retrieve_spreadsheet_data(self, spreadsheet_id: str):
        sheet_metadata = self.sheet_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')

        data = []
        for sheet in sheets:
            sheet_name = sheet.get('properties', {}).get('title', '')
            data.extend(self.retrieve_sheet_data(
                self.sheet_service, spreadsheet_id, sheet_name))

        return data

    def delete_file(self, file_id):
        self.drive_service.files().delete(fileId=file_id).execute()
        print(f"File with ID {file_id} was deleted successfully.")

    def share_folder(self, folder_id, email, role='reader'):
        user_permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }
        self.drive_service.permissions().create(
            fileId=folder_id,
            body=user_permission,
            fields='id'
        ).execute()

    def remove_user_permission(self, file_id, email):
        # Retrieve all permissions for the file
        permissions = self.drive_service.permissions().list(
            fileId=file_id, fields='permissions(id,emailAddress)').execute()

        # Find the permission ID for the specified email
        permission_id = None
        for permission in permissions.get('permissions', []):
            if permission.get('emailAddress') == email:
                permission_id = permission.get('id')
                break

        if permission_id:
            # Remove the permission
            self.drive_service.permissions().delete(
                fileId=file_id, permissionId=permission_id).execute()
            print(f"Permission removed for user: {email}")
        else:
            print(f"No permission found for user: {email}")
