import os
import configparser


class AppConfig:
    REQUIRED_FIELDS = [
        "Tableau Server URL",
        "Tableau Site Name",
        "Access Token Name",
        "Access Token",
    ]

    OPTIONAL_FIELDS = [
        "Email Address",
        "NTLogin",
    ]

    ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

    def __init__(self, path=None):
        self.path = path or os.path.join(os.environ["USERPROFILE"], "tabmgt.env")
        self.config = configparser.ConfigParser()
        self.config.read(self.path)
        if "DEFAULT" not in self.config:
            self.config["DEFAULT"] = {}

    @property
    def data(self):
        return self.config["DEFAULT"]

    def get(self, key, default=""):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        with open(self.path, "w") as f:
            self.config.write(f)

    def is_valid(self):
        return all(self.get(field).strip() for field in self.REQUIRED_FIELDS)