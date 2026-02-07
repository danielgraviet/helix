import socket

from config import PORT_RANGE_START, PORT_RANGE_END


def is_port_free(port: int) -> bool:
    """Check if a port is available on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return True
        except OSError:
            return False


def allocate_port() -> int:
    """Find the next free port in the configured range."""
    for port in range(PORT_RANGE_START, PORT_RANGE_END):
        if is_port_free(port):
            return port
    raise RuntimeError(f"No free ports in range {PORT_RANGE_START}-{PORT_RANGE_END}")
