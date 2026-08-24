import pytest
import time
import threading
from chatroom import ServerTCP, ClientTCP, ServerUDP, ClientUDP

# Ports offset from standard dev ports to prevent collisions during automated runs
TCP_TEST_PORT = 12380
UDP_TEST_PORT = 12381

# ---------------------------------------------------------------------------
# TCP TEST SUITE
# ---------------------------------------------------------------------------

@pytest.fixture
def run_tcp_server():
    """Fixture to launch and teardown TCP server cleanly per test."""
    server = ServerTCP(TCP_TEST_PORT)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    time.sleep(0.2)
    yield server
    server.shutdown()


def test_tcp_connection_and_disconnect(run_tcp_server):
    """Verify single TCP client connection registration and client numbers."""
    client = ClientTCP("Alice", TCP_TEST_PORT)
    assert client.connect_server() is True
    assert run_tcp_server.get_clients_number() == 1

    client.send("exit")
    time.sleep(0.2)
    assert run_tcp_server.get_clients_number() == 0


def test_tcp_duplicate_username_rejected(run_tcp_server):
    """Verify server rejects secondary connection attempting to use an existing name."""
    client1 = ClientTCP("Bob", TCP_TEST_PORT)
    client2 = ClientTCP("Bob", TCP_TEST_PORT)

    assert client1.connect_server() is True
    assert client2.connect_server() is False
    assert run_tcp_server.get_clients_number() == 1

    client1.send("exit")


def test_tcp_multi_client_broadcasting(run_tcp_server):
    """Verify multiple active clients can coexist concurrently on TCP."""
    c1 = ClientTCP("Client1", TCP_TEST_PORT)
    c2 = ClientTCP("Client2", TCP_TEST_PORT)
    c3 = ClientTCP("Client3", TCP_TEST_PORT)

    assert c1.connect_server() is True
    assert c2.connect_server() is True
    assert c3.connect_server() is True

    assert run_tcp_server.get_clients_number() == 3

    assert c1.send("Hello everyone!") is True
    assert c2.send("Hey Client1") is True

    c1.send("exit")
    c2.send("exit")
    c3.send("exit")


def test_tcp_server_graceful_shutdown(run_tcp_server):
    """Verify server shutdown notifies connected sockets and clears client mapping."""
    client = ClientTCP("Eve", TCP_TEST_PORT)
    assert client.connect_server() is True
    assert run_tcp_server.get_clients_number() == 1

    run_tcp_server.shutdown()
    time.sleep(0.2)

    assert run_tcp_server.get_clients_number() == 0


# ---------------------------------------------------------------------------
# UDP TEST SUITE
# ---------------------------------------------------------------------------

@pytest.fixture
def run_udp_server():
    """Fixture to launch and teardown UDP server cleanly per test."""
    server = ServerUDP(UDP_TEST_PORT)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    time.sleep(0.2)
    yield server
    server.shutdown()


def test_udp_client_join_and_leave(run_udp_server):
    """Verify UDP registration flow ('join') and disconnection ('exit')."""
    client = ClientUDP("UDP_Alice", UDP_TEST_PORT)
    assert client.connect_server() is True
    assert run_udp_server.get_clients_number() == 1

    client.send("exit")
    time.sleep(0.2)
    assert run_udp_server.get_clients_number() == 0


def test_udp_duplicate_username_rejected(run_udp_server):
    """Verify UDP server rejects connection if username is active."""
    client1 = ClientUDP("UDP_Bob", UDP_TEST_PORT)
    client2 = ClientUDP("UDP_Bob", UDP_TEST_PORT)

    assert client1.connect_server() is True
    assert client2.connect_server() is False
    assert run_udp_server.get_clients_number() == 1

    client1.send("exit")


def test_udp_multi_client_messaging(run_udp_server):
    """Verify multiple UDP clients register and send datagram payloads."""
    c1 = ClientUDP("User1", UDP_TEST_PORT)
    c2 = ClientUDP("User2", UDP_TEST_PORT)

    assert c1.connect_server() is True
    assert c2.connect_server() is True

    assert run_udp_server.get_clients_number() == 2

    c1.send("Datagram test from User1")
    c2.send("Datagram test from User2")

    c1.send("exit")
    c2.send("exit")


def test_udp_server_shutdown(run_udp_server):
    """Verify UDP server clears internal client dictionary upon shutdown."""
    client = ClientUDP("UDP_Eve", UDP_TEST_PORT)
    assert client.connect_server() is True

    run_udp_server.shutdown()
    assert run_udp_server.get_clients_number() == 0
