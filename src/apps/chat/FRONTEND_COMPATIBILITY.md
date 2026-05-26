# Chat MVP frontend compatibility guide

This document describes the direct-message (1:1) chat MVP in the `chat` app, including
REST endpoints for history and WebSocket events for realtime updates. The implementation
assumes users are authenticated (JWT) and enrolled in a teacher-student relationship
through course enrollments.

## Scope

- Direct messages only (teacher <-> student).
- Only users who share a course in a teacher/student role can chat.
- Users can access only their own chat rooms and messages.
- File support is provided via REST uploads; WebSocket delivers realtime updates.

## Realtime (WebSocket)

### Connect

- URL: `/ws/chat/{chat_room_id}/`
- Auth: JWT is provided via the existing ASGI JWT middleware.

If the user does not belong to the room or is not authenticated, the socket closes.

### Client -> Server events

Send JSON frames with a `type` field.

1) Send a text message

```json
{
  "type": "send_message",
  "content": "Hello!"
}
```

Notes:
- WebSocket messages support text only.
- For file messages, use the REST endpoint (see below). Other participants will receive
  the file message in realtime via WebSocket.

2) Mark a message as read

```json
{
  "type": "mark_as_read",
  "message_id": 123
}
```

3) Typing indicator

```json
{
  "type": "typing",
  "is_typing": true
}
```

### Server -> Client events

1) New message

```json
{
  "type": "message",
  "data": {
    "id": 123,
    "chat_room_id": 45,
    "content": "Hello!",
    "sender": { /* user object */ },
    "file": null,
    "is_read": false,
    "created_at": "2026-05-20T10:15:30Z",
    "updated_at": "2026-05-20T10:15:30Z",
    "is_my_message": false,
    "message_direction": "received"
  }
}
```

Notes:
- `file` is a URL (if present). When a file is attached, `content` can be empty.
- `is_my_message` and `message_direction` are computed per connected user.

2) Message read

```json
{
  "type": "message_read",
  "message_id": 123
}
```

3) Typing indicator

```json
{
  "type": "typing",
  "user_id": 99,
  "user_name": "Alex Doe",
  "is_typing": true
}
```

4) Error

```json
{
  "type": "error",
  "message": "Invalid JSON format"
}
```

## REST API (history and uploads)

All REST endpoints are under `/api/chat/` and require authentication.

### Chat rooms

1) List chat rooms

- `GET /api/chat/rooms/`
- Returns only rooms where the user is the teacher or student.
- Rooms are ordered by `updated_at` descending.

2) Create or get a chat room

- `POST /api/chat/rooms/`
- Body:

```json
{
  "other_user_id": 99,
  "course": 12
}
```

Notes:
- `course` is optional and used to scope validation.
- If a room already exists for the teacher/student pair, it is returned.

3) Retrieve a chat room

- `GET /api/chat/rooms/{room_id}/`

4) Mark all messages in a room as read

- `POST /api/chat/rooms/{room_id}/mark_as_read/`

### Messages (history)

1) List messages (all rooms)

- `GET /api/chat/messages/`
- Use optional query param `room_id` to filter:
  - `GET /api/chat/messages/?room_id=45`

2) List messages for a room

- `GET /api/chat/rooms/{room_id}/messages/`

3) Send a message (text or file)

- `POST /api/chat/rooms/{room_id}/messages/`
- Content types:
  - `application/json` for text-only messages
  - `multipart/form-data` for file uploads

Examples:

Text-only JSON:

```json
{
  "content": "Hello!"
}
```

File upload (multipart form data):

- `file`: the file
- `content`: optional text (can be empty)

Notes:
- At least one of `content` or `file` is required.
- After a successful REST send, all connected WebSocket clients in the room receive
  a realtime `message` event.

### Ownership and access control

- A user can only access rooms where they are the teacher or student.
- A user can only read messages belonging to their rooms.
- A user cannot create a room with themselves or with users outside the teacher/student
  enrollment relationship.

## Frontend flow recommendations

1) List rooms via `GET /api/chat/rooms/`.
2) Open a WebSocket to `/ws/chat/{room_id}/` for the selected room.
3) Fetch history via `GET /api/chat/rooms/{room_id}/messages/` (or use pagination if
   enabled globally).
4) Send text messages via WebSocket `send_message`.
5) Send file messages via REST `POST /api/chat/rooms/{room_id}/messages/` with multipart
   form data, then rely on WebSocket updates for the other participant.

## Notes on pagination

If DRF pagination is enabled globally, list endpoints will return paginated results.
Clients should handle standard DRF pagination keys such as `results`, `next`, and
`previous`.

