from app.database.session import SessionLocal
from app.commands.load_compensation_sites_command import LoadCompensationSitesCommand


def run() -> dict:
    session = SessionLocal()
    try:
        command = LoadCompensationSitesCommand(session)
        return command.execute()
    finally:
        session.close()