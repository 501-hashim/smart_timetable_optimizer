import os
import sys
import socket
import uvicorn
from dotenv import load_dotenv

load_dotenv()

def find_available_port(preferred_ports=[8000, 8080, 8001, 8081, 5000]):
    for port in preferred_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return 8000

if __name__ == "__main__":
    env = os.getenv("ENVIRONMENT", "development").lower()
    default_host = "127.0.0.1" if env == "development" else "0.0.0.0"
    host = os.getenv("HOST", default_host)
    port_env = os.getenv("PORT")
    port = int(port_env) if port_env else find_available_port()
    debug = os.getenv("DEBUG", "true" if env == "development" else "false").lower() in ("true", "1", "yes")

    print("=" * 60)
    print("  SMART ACADEMIC TIMETABLE OPTIMIZER")
    print(f"  Environment: {env.upper()} | Debug: {debug}")
    print(f"  Starting server on http://{host}:{port}")
    print("=" * 60)
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=debug)
