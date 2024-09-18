from os import path
from functools import lru_cache
import datetime
import json

import requests
from google.oauth2 import service_account
import google.auth.transport.requests

SERVICE_ACCOUNT_FILE = path.abspath(path.join(path.abspath(
    __file__), '../../env/google_credentials.json'))
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return float(obj)
        except (TypeError, ValueError):
            # If conversion fails, raise the original TypeError
            raise TypeError(
                f'Object of type {obj.__class__.__name__} is not JSON serializable. Custom Handling Failed.')


class GoogleAccessor:
    def __init__(self, service_account_file=SERVICE_ACCOUNT_FILE, scopes=SCOPES) -> None:
        # Load the service account credentials
        self.creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=scopes)
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self):
        # Check if the current token is expired or will expire within 5 minutes
        if not self.access_token or self.token_expiry <= datetime.datetime.utcnow() + datetime.timedelta(minutes=5):
            request = google.auth.transport.requests.Request()
            self.creds.refresh(request)
            self.access_token = self.creds.token
            self.token_expiry = self.creds.expiry

        return self.access_token

    @lru_cache(maxsize=None)
    def create_or_get_folder(self, name, parent_id=None):
        # Assuming get_access_token() is a method to obtain an access token
        access_token = self.get_access_token()

        # Prepare the headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Check if the folder exists
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={'q': query},
            timeout=10
        )
        files = response.json().get('files', [])

        if files:
            # Folder already exists
            return files[0]['id']
        else:
            # Create the folder
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id] if parent_id else []
            }
            response = requests.post(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                data=json.dumps(folder_metadata),
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('id')
            else:
                return None

    @lru_cache(maxsize=None)
    def create_or_get_spreadsheet_in_folder(self, name: str, folder_id: str, sheets: tuple, column_headers: tuple):
        access_token = self.get_access_token()

        # Headers for HTTP request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Check if the spreadsheet exists
        query = f"name='{name}' and mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents"
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={'q': query},
            timeout=10
        )
        files = response.json().get('files', [])

        if files:
            # Spreadsheet already exists
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
            response = requests.post(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                data=json.dumps(spreadsheet_metadata),
                timeout=10
            )

            if response.status_code != 200:
                print("Error in creating spreadsheet:", response.text)
                return None

            print(response.json())

            spreadsheet_id = response.json().get('id')

            if not spreadsheet_id:
                raise RuntimeError("Failed to create spreadsheet")

            # Prepare batch update requests to rename the first sheet and set headers
            batch_requests_sheets = [
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': 0,
                            'title': sheets[0],
                            'gridProperties': {
                                'columnCount': len(column_headers)
                            }
                        },
                        'fields': 'title,gridProperties.columnCount'
                    }
                }
            ]

            batch_requests_headers = [
                {
                    'updateCells': {
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': header}} for header in column_headers]}],
                        'fields': 'userEnteredValue',
                        'start': {'sheetId': 0, 'rowIndex': 0, 'columnIndex': 0}
                    }
                }]

            # Add additional sheets starting from the second item in sheets list
            for i, sheet in enumerate(sheets[1:], start=1):
                add_sheet_request = {
                    "addSheet": {"properties": {"title": sheet, "sheetId": i, 'gridProperties': {
                        'columnCount': len(column_headers)
                    }}}
                }
                update_cells_request = {
                    'updateCells': {
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': header}} for header in column_headers]}],
                        'fields': 'userEnteredValue',
                        'start': {'sheetId': i, 'rowIndex': 0, 'columnIndex': 0}
                    }
                }
                batch_requests_sheets.append(add_sheet_request)
                batch_requests_headers.append(update_cells_request)

            batch_update_body = {"requests": batch_requests_sheets}
            response = requests.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                headers=headers,
                data=json.dumps(batch_update_body),
                timeout=10
            )

            print(response.json())

            batch_update_body = {"requests": batch_requests_headers}
            response = requests.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                headers=headers,
                data=json.dumps(batch_update_body),
                timeout=10
            )

            print(response.json())

            if response.status_code != 200:
                print("Error in UPDATING Spreaadsheet:", response.text)
                return None

            return spreadsheet_id

    def add_row_data(self, spreadsheet_id, sheet_name, data):
        access_token = self.get_access_token()

        # Headers for HTTP request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Body for appending data
        body = {'values': data}
        response = requests.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A1:append",
            params={"valueInputOption": "USER_ENTERED"},
            headers=headers,
            data=json.dumps(body, cls=CustomJsonEncoder),
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return None

    def retrieve_sheet_data(self, spreadsheet_id, sheet_name):
        access_token = self.get_access_token()

        # Headers for HTTP request
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # GET request to retrieve data
        response = requests.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A:Z",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            return response.json().get('values', [])
        else:
            return None

    def retrieve_spreadsheet_data(self, spreadsheet_id):
        access_token = self.get_access_token()

        # Headers for HTTP request
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # GET request to get sheet names
        sheet_response = requests.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
            headers=headers,
            timeout=10
        )

        if sheet_response.status_code != 200:
            return None

        sheets = sheet_response.json().get('sheets', [])
        data = []

        for sheet in sheets:
            sheet_name = sheet.get('properties', {}).get('title', '')
            sheet_data = self.retrieve_sheet_data(spreadsheet_id, sheet_name)
            data.append({sheet_name: sheet_data})

        return data

    def delete_file(self, file_id):
        access_token = self.get_access_token()

        # Headers for HTTP request
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # DELETE request to remove the file
        response = requests.delete(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            timeout=10
        )

        return response.status_code == 204

    def share_folder(self, folder_id, email, role='reader'):
        access_token = self.get_access_token()

        # Headers for HTTP request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # POST request to add permissions
        user_permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }

        response = requests.post(
            f"https://www.googleapis.com/drive/v3/files/{folder_id}/permissions",
            headers=headers,
            data=json.dumps(user_permission),
            timeout=10
        )

        return response.status_code == 200

    def remove_user_permission(self, file_id, email):
        access_token = self.get_access_token()

        # Headers for HTTP request
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        # GET request to retrieve permissions
        permissions_response = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
            headers=headers,
            timeout=10
        )

        if permissions_response.status_code != 200:
            return None

        permissions = permissions_response.json().get('permissions', [])
        for permission in permissions:
            if permission.get('emailAddress') == email:
                permission_id = permission.get('id')

                # DELETE request to remove the permission
                delete_response = requests.delete(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions/{permission_id}",
                    headers=headers,
                    timeout=10
                )

                return delete_response.status_code == 204

        return False
