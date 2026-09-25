import socket
import sys
import time


def field(index, value):
    data = value.encode()
    return bytes([index]) + len(data).to_bytes(2, "big") + data


def frame(ftype, flags, payload):
    return len(payload).to_bytes(3, "big") + bytes([ftype, flags]) + payload


def request(method, path, body=b"", host=True):
    block = field(1, method) + field(2, path) + (field(4, "localhost") if host else b"")
    if not body:
        return frame(1, 1, block)
    half = len(body) // 2
    return frame(1, 0, block) + frame(2, 0, body[:half]) + frame(2, 1, body[half:])


def status_of(block):
    pos = 0
    while pos < len(block):
        index = block[pos]
        pos += 1
        if index == 0:
            pos += 1 + block[pos]
        length = int.from_bytes(block[pos:pos + 2], "big")
        value = block[pos + 2:pos + 2 + length].decode()
        pos += 2 + length
        if index == 3:
            return int(value)


def response(f):
    status = None
    body = b""
    while True:
        head = f.read(5)
        if len(head) < 5:
            return None, ""
        payload = f.read(int.from_bytes(head[:3], "big"))
        if head[3] == 1:
            status = status_of(payload)
        elif head[3] == 2:
            body += payload
        else:
            continue
        if head[4] & 1:
            return status, body.decode()


def check(f, cases):
    ok = True
    for label, _, want_status, want_body in cases:
        got = response(f)
        passed = got == (want_status, want_body)
        ok = ok and passed
        verdict = "ok" if passed else f"FAIL, wanted {want_status} {want_body}"
        print(f"  {label:<30} -> {got[0]} {got[1]:<4} {verdict}")
    return ok


def still_open(sock):
    time.sleep(0.2)
    sock.setblocking(False)
    try:
        return sock.recv(1) != b""
    except BlockingIOError:
        return True
    finally:
        sock.setblocking(True)


MARKER = [
    ("GET /add?a=2&b=3", request("GET", "/add?a=2&b=3"), 200, "5"),
    ("GET /sub?a=10&b=4", request("GET", "/sub?a=10&b=4"), 200, "6"),
    ("GET /mul?a=6&b=7", request("GET", "/mul?a=6&b=7"), 200, "42"),
    ("GET /div?a=1&b=0", request("GET", "/div?a=1&b=0"), 400, ""),
    ("GET /pow?a=2&b=8", request("GET", "/pow?a=2&b=8"), 404, ""),
    ("POST /add", request("POST", "/add", b"a=2&b=3"), 405, ""),
]

EXTRA = [
    ("GET /div?a=9&b=3", request("GET", "/div?a=9&b=3"), 200, "3"),
    ("GET /add?a=x&b=3", request("GET", "/add?a=x&b=3"), 400, ""),
    ("GET /add?a=2&b=3 (no Host)", request("GET", "/add?a=2&b=3", host=False), 400, ""),
]


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    sock = socket.create_connection(("localhost", port))
    f = sock.makefile("rb")

    print("one socket, every request")
    ok = True
    for case in MARKER:
        sock.sendall(case[1])
        ok = check(f, [case]) and ok
    first_open = still_open(sock)
    print(f"socket still open: {first_open}")
    print(f"1 TCP handshake, {len(MARKER)} responses")

    print("\nsame socket, all at once (pipelined), behind an unknown frame type")
    sock.sendall(frame(0x7F, 1, b"from version 2") + b"".join(c[1] for c in MARKER + EXTRA))
    ok = check(f, MARKER + EXTRA) and ok
    second_open = still_open(sock)
    print(f"socket still open: {second_open}")
    print(f"1 TCP handshake, {len(MARKER) * 2 + len(EXTRA)} responses")

    sock.close()
    sys.exit(0 if ok and first_open and second_open else 1)


if __name__ == "__main__":
    main()
