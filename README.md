# bhttp: a calculator that stays on the line

A binary framing of HTTP (BHTTP/1), with a server and a client written in plain Python using only sockets. The server is a calculator. Every request and response travels over a single persistent TCP connection.

## Disclaimer

This was made for an assignment as part of my computer science degree - not intended to be used as a standalone project or anything serious.

## Files

| File | What it is |
|---|---|
| `SPEC.md` | The protocol spec |
| `bserve` | The server |
| `bcurl` | The client |
| `HEXDUMP.md` | An annotated hexdump of one complete request and response |
| `mark.py` | Runs the marking sequence over one socket |

Requires Python 3.8 or later. There are no dependencies.

## Server

```
./bserve 9000
```

| Request | Response |
|---|---|
| `GET /add?a=2&b=3` | `200` `5` |
| `GET /sub?a=10&b=4` | `200` `6` |
| `GET /mul?a=6&b=7` | `200` `42` |
| `GET /div?a=9&b=3` | `200` `3` |
| `GET /div?a=1&b=0` | `400` |
| `GET /add?a=x&b=3` | `400` |
| `GET /pow?a=2&b=8` | `404` |
| `POST /add` | `405` |
| any request without `host` | `400` |

The server keeps each connection open until the client sends `connection: close`, the client disconnects, or 120 seconds pass with no bytes received. It handles several connections at once, one thread each.

## Client

```
./bcurl [-v] [-X METHOD] host:port/path [/path ...]
```

The client writes each response body to stdout. `-v` hexdumps every frame to stderr, with `>` for sent frames and `<` for received ones. The exit code is 1 if any response is 4xx or 5xx. Extra paths are sent over the same connection, because the client never opens a second one.

```
$ ./bcurl 'localhost:9000/add?a=2&b=3' '/sub?a=10&b=4' '/div?a=7&b=2'
5
6
3.5
$ ./bcurl 'localhost:9000/pow?a=2&b=8'; echo $?
1
$ ./bcurl -v 'localhost:9000/add?a=2&b=3'
```

## Marking run

```
./bserve 8080
python3 mark.py 8080
```

This sends the six marked requests one at a time over one socket and checks that the socket is still open. It then sends all nine feature-table requests at once on the same socket (pipelining), preceded by a frame of an unknown type, and checks the responses come back in order.

```
one socket, every request
  GET /add?a=2&b=3               -> 200 5    ok
  GET /sub?a=10&b=4              -> 200 6    ok
  GET /mul?a=6&b=7               -> 200 42   ok
  GET /div?a=1&b=0               -> 400      ok
  GET /pow?a=2&b=8               -> 404      ok
  POST /add                      -> 405      ok
socket still open: True
1 TCP handshake, 6 responses
```

## Protocol in brief

Every frame has a 5-byte header: Length (24 bits), Type (8), Flags (8). Type `0x01` is HEADERS and type `0x02` is DATA, and flag `0x01` marks the end of a message. A receiver reads exactly `Length` bytes of payload, so it always knows where the next message starts. Header names are sent as a 1-byte index into a table of ten names, or as a length-prefixed literal. Receivers skip unknown frame types. See `SPEC.md` for the full spec.

## Windows

The `./bserve` form relies on the shebang line, so on Windows run `python bserve 9000` and `python bcurl ...` instead.
