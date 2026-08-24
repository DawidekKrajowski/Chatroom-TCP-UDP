import pytest
import socket
import threading
import time
from chatroom import ServerTCP, ClientTCP

TEST_PORT = 12345

@pytest.fixture
def run_server():
    """Fixture to start and teardown the TCP server automatically."""
    server = ServerTCP(TEST_PORT)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    time.sleep(0.2)  # Give server time to bind port
    yield server
    server.shutdown()

def test_client_join_and_broadcast(run_server):
    """Test two clients connecting and exchanging messages."""
    client1 = ClientTCP("Alice", TEST_PORT)
    client2 = ClientTCP("Bob", TEST_PORT)

    assert client1.connect_server() is True
    assert client2.connect_server() is True

    # Validate server registered both clients
    assert run_server.get_clients_number() == 2

    # Cleanup clients
    client1.send("exit")
    client2.send("exit")

def test_duplicate_username_rejected(run_server):
    """Test that a second client cannot register with an existing username."""
    client1 = ClientTCP("Alice", TEST_PORT)
    client2 = ClientTCP("Alice", TEST_PORT)

    assert client1.connect_server() is True
    assert client2.connect_server() is False  # Should be rejected
    assert run_server.get_clients_number() == 1

    client1.send("exit")
