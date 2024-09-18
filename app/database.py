from fastapi import Request
# from deta import Deta


# class DetaCollection:
#     def __init__(self, project_key: str, base_name: str, drive_name: str) -> None:
#         self.deta = Deta(project_key)
#         self.db = self.deta.Base(base_name)
#         self.drive = self.deta.Drive(drive_name)

#     def insert_to_db(self, data: dict):
#         self.db.put(data)

#     def read_db(self, get_all: bool = False):
#         if get_all:
#             return self.db.fetch().items

#         data = []
#         while True:
#             response = self.db.fetch()
#             data.extend(response.items)
#             if response.last is None:
#                 break

#         return data

#     def dump_to_drive(self, file_name: str, data: dict):
#         self.drive.put(file_name, data)

#     def read_from_file(self, file_name: str):
#         response = self.drive.get(file_name)
#         return response.read()

#     def get_drive_files(self):
#         return self.drive.list()["names"]


# def get_deta_collection(request: Request):
#     return request.app.state.deta_collection


def get_data_collector(request: Request):
    return request.app.state.data_collector


def get_google_service(request: Request):
    return request.app.state.google_accessor
