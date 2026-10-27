# CLAUDE.md - Card Dispenser (Project Global Rules)

Simple desktop tool: press a button, the K720 card dispenser ejects one card, the card's RFID UID is read and stored in a local database. An admin area (password protected, inside the same app) manages cards. Target OS: Windows (primary) and Linux (development, must work).

Scope for now: dispense + store RFID UID + admin area. Nothing else until explicitly requested.

## 1. Core Principles

- **Single application, no server.** One desktop process, one local SQLite file. No web service, no cloud.
- **Hardware is behind an interface.** All serial/device code lives in `device/`. UI and services never touch `pyserial` directly. Every device feature must be testable with `FakeK720`.
- **Cross-platform by default.** No OS-specific APIs. Serial port names are configuration (`/dev/ttyUSB0` on Linux, `COM3` on Windows), never hard-coded.
- **Type safety.** All public functions have type hints. `mypy --strict` must pass on `src/`.
- **Explicit errors.** Device errors are typed exceptions (`DeviceError` subclasses). Never return `None` or magic ints to signal failure.
- **Secrets are never stored in plain text.** Admin password is stored only as an Argon2id hash.
- **Every hardware action is logged** (command, result, duration). Never log secrets, passwords, or full admin credentials.
- **Keep it simple.** No abstractions for features that do not exist yet. YAGNI.
- **Docstrings** on all public classes and functions (Google style).

## 2. Tech Stack

Language and runtime:
- **Python 3.12** (managed with `uv`)
- Rationale: runs natively on Windows and Linux, no vendor DLL needed (the K720 protocol is plain serial), fast to develop, easy to package.

Application:
- **PySide6 >= 6.8** (Qt 6) - GUI, cross-platform, LGPL
- **pyserial >= 3.5** - serial communication (works on `/dev/tty*` and `COMx`)
- **sqlite3** (stdlib) - local database, no ORM
- **argon2-cffi >= 23.1** - admin password hashing (Argon2id)
- **structlog >= 24.1** - structured logging (JSON in files, readable in console)

Tooling:
- **pytest >= 8.3** + **pytest-qt >= 4.4** (GUI tests) + **pytest-cov**
- **ruff >= 0.8** - linting and formatting (replaces black/isort/flake8)
- **mypy >= 1.13** (strict mode)
- **PyInstaller >= 6.11** - Windows packaging (must be built on Windows; Linux builds only for dev)

## 3. Architecture

Layered structure (dependencies point downward only):

```
ui/          PySide6 windows and dialogs (no business logic)
  |
services/    business logic (dispense flow, card registration, auth)
  |
device/      K720 driver + protocol + transport (serial)    persistence/  SQLite repositories
  |                                                              |
  +------------------- domain/ (plain dataclasses, enums) -------+
```

Layout:

```
carddispencer/
  pyproject.toml
  CLAUDE.md
  src/card_dispenser/
    __main__.py            # entry point: python -m card_dispenser
    app.py                 # Qt application bootstrap, wiring (composition root)
    config.py              # settings: serial port, device address, db path, log level
    logging_setup.py       # structlog configuration
    domain/
      models.py            # Card, DispenseResult (dataclasses)
      errors.py            # base DomainError
    device/
      protocol.py          # frame build/parse, BCC, constants (pure functions)
      k720.py              # K720 driver: status(), dispense(), read_card_uid()
      transport.py         # SerialTransport (pyserial) + FakeTransport (tests)
      errors.py            # DeviceError, DeviceTimeoutError, DeviceNakError, ...
    persistence/
      db.py                # connection, schema creation, migrations
      card_repository.py   # CRUD for cards
      admin_repository.py  # admin password hash storage
    services/
      dispense_service.py  # orchestrates: check status -> dispense -> read UID -> store
      card_service.py      # list/search/delete cards
      auth_service.py      # verify admin password, lockout after failed attempts
    ui/
      main_window.py       # "Dispense card" button, status label
      login_dialog.py      # admin login
      admin_window.py      # card list, delete, admin password change
  tests/
    unit/                  # no hardware, no GUI (protocol, services, repositories)
    integration/           # SQLite on tmp_path, device with FakeTransport
    ui/                    # pytest-qt tests
```

Key patterns:
- **Composition root**: `app.py` builds all objects and injects them. No global singletons.
- **Repository pattern** for SQLite access; services receive repositories via constructor.
- **Transport abstraction**: `K720` takes a `Transport` protocol; `SerialTransport` and `FakeTransport` both implement it.
- **Dispense is a state flow**, not a single call: check status, dispense, poll until card is out, read UID, persist. Each step is logged.
- **No threading in widgets.** Device I/O runs in a `QThread` worker; results return to the UI via Qt signals.

## 4. Code Style

Naming:
- Modules and functions: `snake_case` (`read_card_uid`, `card_repository.py`)
- Classes: `PascalCase` (`K720`, `DispenseService`, `CardRepository`)
- Constants and enum members: `UPPER_SNAKE_CASE` (`STX`, `ETX`, `DispenserState.CARD_EMPTY`)
- Private helpers: leading underscore (`_xor_checksum`)
- Qt widgets: suffix with widget type (`dispense_button`, `card_table_view`)
- Database: tables `snake_case` plural (`cards`, `admin_users`), columns `snake_case`, primary key `id` (INTEGER)
- Booleans: `is_`, `has_`, `can_` prefix

Types and dataclasses:

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Card:
    """A card dispensed by the K720 and identified by its RFID UID.

    Attributes:
        id: Database primary key, None before the card is persisted.
        uid: Hex string of the RFID UID, uppercase, no separators (e.g. "04A23B19").
        dispensed_at: UTC timestamp of dispensing.
    """

    id: int | None
    uid: str
    dispensed_at: datetime
```

Errors:

```python
class DeviceError(Exception):
    """Base class for all K720 communication errors."""


class DeviceTimeoutError(DeviceError):
    """Device did not answer within the protocol timeout."""


class DeviceNakError(DeviceError):
    """Device replied NAK (0x15): frame format error."""
```

Docstring format (Google style):

```python
def build_frame(address: int, payload: bytes) -> bytes:
    """Build a command frame for the K720 protocol.

    Args:
        address: Device address, 0-15 (DIP switch; sent as ASCII digits ADDH ADDL).
        payload: Command bytes, e.g. b"AP" or b"\\x3B\\x31".

    Returns:
        The complete frame including STX, length, ETX and BCC.

    Raises:
        ValueError: If the payload is empty or longer than 0xFFFF bytes.
    """
```

Formatting: `ruff format`, line length 100. Imports sorted by ruff. No wildcard imports.

## 5. Logging

Format: structured JSON in `logs/app.log` (rotating, 5 MB x 5 files), human-readable colored output on console in development. Use `structlog` everywhere; do not use `print()` or bare `logging.info("text " + x)`.

What to log:
- **Operations**: dispense started/finished, card registered, admin login success/failure, admin password changed
- **Device**: every command sent (command name only, never raw payload for admin-related ops), response code, duration in ms
- **Errors**: always with exception type and context (port, address, command). Use `logger.exception` in service layer.
- **Key state**: dispenser status changes (card empty, jam, sensor states)

What NOT to log: admin passwords (plain or hash), full card UIDs in INFO-level device chatter is acceptable, but never log secrets.

Backend (Python):

```python
import structlog

log = structlog.get_logger(__name__)

log.info(
    "dispense_completed",
    device_address=address,
    card_uid=card.uid,
    duration_ms=elapsed_ms,
)

try:
    uid = k720.read_card_uid()
except DeviceTimeoutError:
    log.exception("card_uid_read_timeout", device_address=address, port=port)
    raise
```

Event names are `snake_case` verbs/states, not sentences. Always pass context as keyword fields, never f-strings.

Frontend (Qt UI):
- UI code does not log business events itself; it logs only UI-level failures (e.g. widget not found).
- Errors shown to the user are logged by the service that raised them.

```python
log.warning("admin_login_failed", attempts=attempts, locked_until=locked_until.isoformat())
```

## 6. Testing

Framework: `pytest`, `pytest-qt` for GUI, `pytest-cov` for coverage. Target: **>= 85% line coverage on `device/`, `services/`, `persistence/`**.

Structure and naming:
- Tests mirror source: `src/card_dispenser/device/protocol.py` -> `tests/unit/device/test_protocol.py`
- File names: `test_<module>.py`
- Test names: `test_<unit>_<condition>_<expected>`, e.g. `test_build_frame_empty_payload_raises_value_error`

Rules:
- **No real hardware in tests.** Use `FakeTransport` (records written bytes, replays scripted responses).
- **No real database file.** Use `tmp_path` for SQLite.
- Use `pytest.mark.parametrize` for protocol edge cases (BCC, length bytes).
- Use `pytest-qt` `qtbot` for widget tests; never `time.sleep` in tests.

Example:

```python
from card_dispenser.device.protocol import build_frame


def test_build_frame_ap_command_has_correct_bcc() -> None:
    frame = build_frame(address=0x0000, payload=b"AP")

    assert frame[0] == 0x02  # STX
    assert frame[-2] == 0x03  # ETX
    bcc = 0
    for byte in frame[:-1]:  # XOR from STX through ETX
        bcc ^= byte
    assert frame[-1] == bcc
```

Run:
```bash
uv run pytest                              # all tests
uv run pytest tests/unit -q                # fast unit tests only
uv run pytest --cov=card_dispenser --cov-report=term-missing
```

## 7. Device Protocol Contract (K720)

The "API contract" of this project is the serial protocol between the PC and the K720. Source: `2018-7-23 K720 SDK-Eng/User Manual/Communication Protocol of K720&k730&k750.doc`. Treat that document as the authority; the Windows DLL is NOT used.

Serial settings: **9600 baud, 8 data bits, no parity, 1 stop bit**, half duplex.

Frame format (command):

| Byte(s)      | Meaning                                              |
|--------------|------------------------------------------------------|
| `0x02`       | STX                                                  |
| ADDH, ADDL   | Device address as ASCII digits "00"-"15" (DIP switch table) |
| LEN_H, LEN_L | Payload length, big endian                           |
| payload      | Command code and parameters                          |
| `0x03`       | ETX                                                  |
| BCC          | XOR of all bytes from STX to ETX inclusive           |

Handshake for "command list 1" (contactless card ops, e.g. `0x3B 0x31`):
1. Host sends command frame.
2. Device replies `ACK 0x06 ADDH ADDL` (accepted) or `NAK 0x15 ADDH ADDL` (format error).
3. Host sends `ENQ 0x05 ADDH ADDL` to request the response.
4. Device replies with response frame: payload `'P' 0x50` = success, `'N' 0x4E` = failure + error code.

Handshake for "command list 2" (`DC`, `FC*`, `RS`, `AP`, `RF`): the device sends **no response frame**. Send the command, wait for ACK/NAK, then poll `AP` (or `RF`) to see the result in the status bits.

Timing:
- Max 15 ms between command bytes (command list 1), 50 ms (command list 2); longer gaps = void.
- Wait at least **200 ms between two status checks** (`AP`/`RF`).
- Never send a new command before the previous one has finished.

Commands used by this project:

| Purpose                     | Command                      | Notes                                   |
|-----------------------------|------------------------------|-----------------------------------------|
| Machine status (16-bit)     | `AP` (0x41 0x50)             | Returns 4 ASCII hex chars = bit field   |
| Dispense card to front      | `DC` (0x44 0x43)             | Only if status shows card hopper ready  |
| Reset                       | `RS` (0x52 0x53)             | Recovery after errors                   |
| Search S50 card             | `0x3B 0x30`                  | Contactless card op, card type S50      |
| Read S50 serial number      | `0x3B 0x31`                  | Returns card UID                        |
| Search/read S70 / UL        | `0x3C 0x30/0x31`, `0x3D ...` | Only if card type is configured as such |

Status word (`AP`): interpret bits from the document's status table (e.g. `0008` = card empty, `0010` = card pre-empty, `0020` = card jam, `0040` = card overlap, `0001/0002/0004` = card at sensor 1/2/3). Map these to `DispenserState` enum values in `device/protocol.py`.

Dispense flow contract:
1. `AP` -> reject if card empty, jam, overlap, or error bits set. Raise typed error with the bit name.
2. `DC` -> expect ACK then success.
3. Poll `AP` (min. 200 ms interval) until the card is ejected (sensor 2 / read position bit set), with a timeout (default 10 s). On timeout raise `DeviceTimeoutError`.
4. Read UID: `search card` then `read serial`. If no card found, raise `CardNotFoundError`.
5. Persist `Card` via `CardRepository`. Only persist after step 4 succeeded.

## 8. Common Patterns

Backend service pattern (dispense flow):

```python
class DispenseService:
    """Dispense one card and register its UID."""

    def __init__(
        self, dispenser: K720, cards: CardRepository, clock: Callable[[], datetime]
    ) -> None:
        self._dispenser = dispenser
        self._cards = cards
        self._clock = clock

    def dispense_and_register(self) -> Card:
        """Dispense one card, read its UID and store it.

        Returns:
            The persisted Card.

        Raises:
            DeviceError: Dispenser is not ready or communication failed.
            CardNotFoundError: No card could be read after dispensing.
        """
        self._dispenser.ensure_ready()
        self._dispenser.dispense()
        uid = self._dispenser.read_card_uid()
        card = Card(id=None, uid=uid, dispensed_at=self._clock())
        saved = self._cards.add(card)
        log.info("card_registered", card_id=saved.id, card_uid=saved.uid)
        return saved
```

Frontend (Qt) pattern - worker thread, signals, no blocking in the UI:

```python
class DispenseWorker(QObject):
    """Runs the dispense flow off the UI thread."""

    finished = Signal(object)  # Card
    failed = Signal(str)  # user-facing message

    def __init__(self, service: DispenseService) -> None:
        super().__init__()
        self._service = service

    @Slot()
    def run(self) -> None:
        try:
            card = self._service.dispense_and_register()
        except DomainError as exc:
            log.warning("dispense_failed", reason=type(exc).__name__)
            self.failed.emit(str(exc))
            return
        self.finished.emit(card)
```

Repository pattern (SQLite, parameterized queries only):

```python
class CardRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    def add(self, card: Card) -> Card:
        cursor = self._conn.execute(
            "INSERT INTO cards (uid, dispensed_at) VALUES (?, ?)",
            (card.uid, card.dispensed_at.isoformat()),
        )
        self._conn.commit()
        return replace(card, id=cursor.lastrowid)
```

## 9. Development Commands

Setup:
```bash
uv sync                          # install runtime + dev dependencies from pyproject.toml
```

Run:
```bash
uv run python -m card_dispenser                                  # start app (Linux)
uv run python -m card_dispenser --port /dev/ttyUSB0 --address 0  # explicit config
uv run python -m card_dispenser --fake-device                    # run without hardware
```

Quality:
```bash
uv run ruff check .              # lint
uv run ruff format .             # format
uv run mypy src                  # type check (strict)
uv run pytest                    # tests
```

Serial port access on Linux (one-time):
```bash
sudo usermod -aG dialout $USER   # then log out/in
ls -l /dev/ttyUSB* /dev/ttyS*    # find the port
```

Packaging (Windows only, on a Windows machine):
```bash
uv run pyinstaller --noconfirm --windowed --name CardDispenser src/card_dispenser/__main__.py
```

Database:
- File: `data/carddispenser.db` (created on first start, path configurable)
- Schema changes go through `persistence/db.py` migrations (numbered SQL statements, applied in order, tracked in `schema_version` table). Never edit an applied migration.

## 10. AI Coding Assistant Instructions

1. Read this file first and follow it; if a request conflicts with it, ask before deviating.
2. Keep scope minimal: implement only the dispense/store/admin features; do not add features listed as "later" without an explicit request.
3. Never talk to the serial port from UI or service code; go through `K720` and the `Transport` protocol.
4. Never use the Windows DLL or Windows-only APIs; the code must run on Linux and Windows.
5. Make every device feature testable with `FakeTransport`; write unit tests for new protocol code (BCC, frames, status bits).
6. Use typed exceptions from `device/errors.py` and `domain/errors.py`; never return `None` or error codes for failures.
7. Use `structlog` with `snake_case` event names and keyword context; never log passwords, hashes, or secrets.
8. Store admin passwords only as Argon2id hashes; never write plain-text passwords to code, config, logs, or the database.
9. Use parameterized SQL queries only; never build SQL with f-strings.
10. Before finishing, run `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest` and fix all failures.

## Open Decisions (to confirm with the user)

- Card type in use (S50 / S70 / UL). Default assumed: **S50**, configurable.
- Device address (DIP switch setting). Default assumed: **0x0000**, configurable.
- Exact status bit for "card at read position" on the specific K720 firmware: verify on hardware.
- Whether the K720 "DC" command is used directly or a sensor-based `FC*` command is preferred for the read position.
