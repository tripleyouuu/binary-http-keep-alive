# BHTTP/1: HTTP in binary

## 1. Overview

BHTTP/1 carries HTTP request/response semantics over one TCP connection using binary frames. A client sends requests and the server sends one response per request, **in the same order the requests were received**. A client may send further requests before earlier responses arrive (pipelining). The connection stays open until either side ends it (section 6). All integers are unsigned and big-endian.

## 2. Frame

Every byte on the connection belongs to a frame.

```
 0                   1                   2                   3                   4
+-------------------------------------------------------+---------------+---------------+
|                    Length (24)                        |   Type (8)    |   Flags (8)   |
+-------------------------------------------------------+---------------+---------------+
|                        Payload (Length bytes)  ...
+------------------------------------------------------------
```

The header is a fixed 5 bytes. The payload is exactly `Length` bytes. A receiver reads 5 bytes, then exactly `Length` bytes, and the next byte is the start of the next frame. This is the only rule that marks where one message ends and the next begins.

**Why 24 / 8 / 8.** HTTP/2 uses 24 / 8 / 8 / 31 (Length / Type / Flags / Stream ID, plus one reserved bit), a 9-byte header. BHTTP/1 keeps the first three fields and drops the stream ID.

- **Length, 24 bits** (up to 16,777,215 bytes). This is large enough that a small message fits in a single frame, and small enough that a receiver never needs to buffer more than 16 MiB for one frame. Larger bodies are sent as several DATA frames.
- **Type, 8 bits.** BHTTP/1 uses 2 of the 256 values. The rest leave room for later versions (section 5).
- **Flags, 8 bits.** BHTTP/1 uses 1 bit. The other 7 are reserved.
- **No stream ID.** HTTP/2 needs a stream ID because it interleaves many requests on one connection. BHTTP/1 answers in order, so the position of a response identifies its request, and each frame saves 4 bytes.

Every field is a whole number of bytes, so no bit masking is needed to parse the header.

## 3. Frame types and flags

| Type | Name    | Payload |
|------|---------|---------|
| 0x01 | HEADERS | A header block (section 4). Starts a message. |
| 0x02 | DATA    | Body bytes. |

| Flag | Name        | Meaning |
|------|-------------|---------|
| 0x01 | END_MESSAGE | This frame is the last frame of the message. |

Senders MUST set reserved flag bits to 0, and receivers MUST ignore them.

**Message.** A message is one HEADERS frame followed by zero or more DATA frames. The frame with END_MESSAGE set ends the message. A message with no body is a single HEADERS frame with END_MESSAGE set. The body is the DATA payloads concatenated in order, so splitting a body across several DATA frames is chunked transfer.

## 4. Header block

A HEADERS payload is a sequence of fields that runs to the end of the payload. Each field is in one of two forms:

```
Indexed:  | Index (8) = 1..255 | Value length (16) | Value |
Literal:  | 0x00 | Name length (8) | Name | Value length (16) | Value |
```

Names are lowercase ASCII and values are UTF-8. A name MUST NOT appear twice in one block. Indices 1 to 10 are the ten names BHTTP/1 implementations actually send:

| # | Name | Sent by | # | Name | Sent by |
|---|------|---------|---|------|---------|
| 1 | `:method` | client | 6 | `accept` | client |
| 2 | `:path` | client | 7 | `content-type` | server |
| 3 | `:status` | server | 8 | `content-length` | server |
| 4 | `host` | client | 9 | `server` | server |
| 5 | `user-agent` | client | 10 | `connection` | both |

Any other name is sent as a literal. Indexing turns a name such as `content-length` (14 bytes) into 1 byte. A receiver that meets an index above 10 MUST read its value length and skip the value. Because every value is length-prefixed, unknown fields can always be skipped.

A request MUST contain `:method`, `:path` and `host`. A response MUST contain `:status`, sent as three ASCII digits.

## 5. Unknown frame types

**A receiver that meets a frame type it does not know MUST read and discard its `Length` payload bytes and carry on as if the frame was never sent.** It ignores the frame's flags, and the frame does not start, continue or end a message. Unknown frames may appear anywhere, including between the HEADERS and DATA frames of a message. This is how a later version can add frame types without breaking BHTTP/1 peers.

## 6. Connection management

The connection is persistent by default. A client that sends `connection: close` receives its response, after which the server closes the connection. The server marks its own last response with `connection: close`, and otherwise sends `connection: keep-alive`.

**Idle timeout.** The server closes a connection when no bytes arrive for 120 seconds. That is long enough for a person testing by hand at a REPL to pause between requests. It is short enough that abandoned connections do not hold server resources indefinitely. Clients must be ready to reconnect.

## 7. Errors

| Problem | Response | Connection |
|---|---|---|
| Header block cannot be parsed (truncated field, invalid UTF-8) | 400 | stays open, since the frame boundary is still known |
| Required request field missing (including `host`) | 400 | stays open |
| DATA frame with no open message, or HEADERS inside an open message | 400 with `connection: close` | closed, since message boundaries can no longer be trusted |
| Connection ends partway through a frame | none | closed |

## 8. The calculator application

`:path` is `/<op>?a=<A>&b=<B>`. `<op>` is `add`, `sub`, `mul` or `div`. `A` and `B` are decimal integers matching `-?[0-9]+`, and query values may be percent-encoded. A success is `200` with `content-type: text/plain` and the result as the body. `div` returns an integer when the division is exact, and otherwise the shortest decimal that round-trips an IEEE-754 double (for example, `7/2` gives `3.5`). Error responses have no body.

The server checks each request in this order and stops at the first failure:

1. `:method`, `:path` or `host` is missing: **400**.
2. `<op>` is not one of the four operations: **404**.
3. `:method` is not `GET`: **405**.
4. `a` or `b` is missing or not an integer: **400**.
5. The operation is division by zero: **400**.
6. Otherwise: **200** with the result.
