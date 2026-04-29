import sys
import types


def install_dependency_stubs():
    if "asyncpg" not in sys.modules:
        sys.modules["asyncpg"] = types.ModuleType("asyncpg")

    if "dotenv" not in sys.modules:
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv
