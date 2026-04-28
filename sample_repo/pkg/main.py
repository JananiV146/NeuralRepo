import os
from .services.auth import AuthService

class App:
    def run(self):
        return AuthService().login()
