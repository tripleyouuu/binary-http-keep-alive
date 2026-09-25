# Annotated hexdump: one request and response

Captured with:

```
$ ./bcurl -v 'localhost:9000/add?a=2&b=3'
```

## Raw

```
> 0000  00 00 43 01 01 01 00 03 47 45 54 02 00 0c 2f 61  ..C.....GET.../a
> 0010  64 64 3f 61 3d 32 26 62 3d 33 04 00 0e 6c 6f 63  dd?a=2&b=3...loc
> 0020  61 6c 68 6f 73 74 3a 39 30 30 30 05 00 05 62 63  alhost:9000...bc
> 0030  75 72 6c 06 00 0a 74 65 78 74 2f 70 6c 61 69 6e  url...text/plain
> 0040  0a 00 05 63 6c 6f 73 65                          ...close
< 0000  00 00 28 01 00 03 00 03 32 30 30 09 00 06 62 73  ..(.....200...bs
< 0010  65 72 76 65 0a 00 05 63 6c 6f 73 65 07 00 0a 74  erve...close...t
< 0020  65 78 74 2f 70 6c 61 69 6e 08 00 01 31           ext/plain...1
< 0000  00 00 01 02 01 35                                .....5
```

`>` is sent by the client and `<` is received. Each `<` block is one frame.

## Request: 1 frame, 72 bytes

| Offset | Bytes | Meaning |
|---|---|---|
| 0x00 | `00 00 43` | Length = 67 bytes of payload |
| 0x03 | `01` | Type = HEADERS |
| 0x04 | `01` | Flags = END_MESSAGE (no body follows) |
| 0x05 | `01` | Field: index 1 = `:method` |
| 0x06 | `00 03` | Value length = 3 |
| 0x08 | `47 45 54` | `GET` |
| 0x0b | `02` | Field: index 2 = `:path` |
| 0x0c | `00 0c` | Value length = 12 |
| 0x0e | `2f 61 … 3d 33` | `/add?a=2&b=3` |
| 0x1a | `04` | Field: index 4 = `host` |
| 0x1b | `00 0e` | Value length = 14 |
| 0x1d | `6c 6f … 30 30` | `localhost:9000` |
| 0x2b | `05` | Field: index 5 = `user-agent` |
| 0x2c | `00 05` | Value length = 5 |
| 0x2e | `62 63 75 72 6c` | `bcurl` |
| 0x33 | `06` | Field: index 6 = `accept` |
| 0x34 | `00 0a` | Value length = 10 |
| 0x36 | `74 65 … 69 6e` | `text/plain` |
| 0x40 | `0a` | Field: index 10 = `connection` |
| 0x41 | `00 05` | Value length = 5 |
| 0x43 | `63 6c 6f 73 65` | `close` (last request, so the client asks the server to hang up afterwards) |

The payload is 67 bytes, from 0x05 to 0x47. Byte 0x48 would be the start of the next frame.

## Response frame 1: HEADERS, 45 bytes

| Offset | Bytes | Meaning |
|---|---|---|
| 0x00 | `00 00 28` | Length = 40 |
| 0x03 | `01` | Type = HEADERS |
| 0x04 | `00` | Flags = none, so a body follows |
| 0x05 | `03` `00 03` `32 30 30` | `:status` = `200` |
| 0x0b | `09` `00 06` `62 73 65 72 76 65` | `server` = `bserve` |
| 0x14 | `0a` `00 05` `63 6c 6f 73 65` | `connection` = `close` (echoes the client's close) |
| 0x1c | `07` `00 0a` `74 65 … 69 6e` | `content-type` = `text/plain` |
| 0x29 | `08` `00 01` `31` | `content-length` = `1` |

## Response frame 2: DATA, 6 bytes

| Offset | Bytes | Meaning |
|---|---|---|
| 0x00 | `00 00 01` | Length = 1 |
| 0x03 | `02` | Type = DATA |
| 0x04 | `01` | Flags = END_MESSAGE, so the response is complete |
| 0x05 | `35` | `5`, the result of 2 + 3 |

## Totals

The request is 72 bytes. The response is 51 bytes across two frames. Each of the ten indexed names costs 1 byte on the wire instead of its full spelling.
