import json
import os
import re
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "melodikita.db")))
APP_NAME = "MelodiKita"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
ALLOWED_INSTRUMENTS = {"Piano", "Vokal", "Gitar", "Drum"}
ALLOWED_LEARNING_MODES = {"Offline", "Online", "Hybrid"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9\s-]{9,18}$")


def get_db_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS testimonials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            quote TEXT NOT NULL,
            rating INTEGER NOT NULL DEFAULT 5,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            instrument TEXT NOT NULL,
            learning_mode TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_testimonials_created_at
        ON testimonials (created_at DESC)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_enrollments_created_at
        ON enrollments (created_at DESC)
        """
    )

    existing_testimonials = cursor.execute(
        "SELECT COUNT(*) AS total FROM testimonials"
    ).fetchone()["total"]

    if existing_testimonials == 0:
        now = datetime.now().isoformat(timespec="seconds")
        cursor.executemany(
            """
            INSERT INTO testimonials (name, role, quote, rating, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "Rina Prameswari",
                    "Orang tua siswa kelas piano",
                    "Anak saya awalnya malu tampil, sekarang sudah berani ikut mini concert. Mentornya sabar dan progress-nya terasa sekali.",
                    5,
                    now,
                ),
                (
                    "Kevin Mahendra",
                    "Siswa kelas vokal dewasa",
                    "Jadwal kelasnya fleksibel dan mentor vokalnya membantu saya menjaga konsistensi latihan walau kerja full-time.",
                    5,
                    now,
                ),
                (
                    "Dito Ramadhan",
                    "Siswa program band starter",
                    "Materinya rapi dan praktiknya relevan. Saya jadi lebih pede main gitar dan lebih paham kerja sama dalam band.",
                    5,
                    now,
                ),
            ],
        )

    connection.commit()
    connection.close()


def normalize_text(value, max_length, field_name, required=True):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{field_name} wajib diisi.")
    if len(text) > max_length:
        raise ValueError(f"{field_name} maksimal {max_length} karakter.")
    return text


def validate_payload(payload):
    website = normalize_text(payload.get("website"), 120, "Website", required=False)
    full_name = normalize_text(payload.get("fullName"), 80, "Nama lengkap")
    email = normalize_text(payload.get("email"), 120, "Email")
    phone = normalize_text(payload.get("phone"), 20, "Nomor WhatsApp")
    instrument = normalize_text(payload.get("instrument"), 20, "Instrumen")
    learning_mode = normalize_text(payload.get("learningMode"), 20, "Mode belajar")
    message = normalize_text(payload.get("message"), 500, "Pesan", required=False)

    if website:
        raise ValueError("Permintaan tidak valid.")

    if not EMAIL_PATTERN.match(email):
        raise ValueError("Format email tidak valid.")

    if not PHONE_PATTERN.match(phone):
        raise ValueError("Format nomor WhatsApp tidak valid.")

    if instrument not in ALLOWED_INSTRUMENTS:
        raise ValueError("Instrumen yang dipilih tidak valid.")

    if learning_mode not in ALLOWED_LEARNING_MODES:
        raise ValueError("Mode belajar yang dipilih tidak valid.")

    return {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "instrument": instrument,
        "learning_mode": learning_mode,
        "message": message,
    }


class MelodiKitaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        super().end_headers()

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        return json.loads(raw_body.decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "app": APP_NAME,
                    "time": datetime.now().isoformat(timespec="seconds"),
                }
            )
            return

        if parsed.path == "/api/testimonials":
            connection = get_db_connection()
            testimonials = connection.execute(
                """
                SELECT id, name, role, quote, rating, created_at
                FROM testimonials
                ORDER BY id DESC
                """
            ).fetchall()
            connection.close()

            self._send_json(
                {
                    "testimonials": [dict(item) for item in testimonials],
                }
            )
            return
        if parsed.path == "/api/enrollments":
            connection = get_db_connection()
            enrollments = connection.execute(
                """
                SELECT id, full_name, email, phone, instrument, learning_mode, message, created_at
                FROM enrollments
                ORDER BY id DESC
                """
            ).fetchall()
            connection.close()

            self._send_json({
                "enrollments": [dict(item) for item in enrollments]
            })
            return

        if parsed.path == "/api/site-stats":
            connection = get_db_connection()
            testimonial_total = connection.execute(
                "SELECT COUNT(*) AS total FROM testimonials"
            ).fetchone()["total"]
            enrollment_total = connection.execute(
                "SELECT COUNT(*) AS total FROM enrollments"
            ).fetchone()["total"]
            connection.close()

            self._send_json(
                {
                    "stats": {
                        "testimonials": testimonial_total,
                        "enrollments": enrollment_total,
                        "mentors": 25,
                    }
                }
            )
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/enrollments":
            self._send_json(
                {"error": "Endpoint tidak ditemukan."},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        try:
            payload = self._read_json_body()
        except json.JSONDecodeError:
            self._send_json(
                {"error": "Format JSON tidak valid."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            cleaned = validate_payload(payload)
        except ValueError as error:
            self._send_json(
                {"error": str(error)},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        connection = get_db_connection()
        connection.execute(
            """
            INSERT INTO enrollments (
                full_name,
                email,
                phone,
                instrument,
                learning_mode,
                message,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned["full_name"],
                cleaned["email"],
                cleaned["phone"],
                cleaned["instrument"],
                cleaned["learning_mode"],
                cleaned["message"],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        connection.commit()
        enrollment_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.close()

        self._send_json(
            {
                "message": "Pendaftaran berhasil disimpan ke database.",
                "enrollmentId": enrollment_id,
            },
            status=HTTPStatus.CREATED,
        )

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def run():
    init_db()
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((HOST, PORT), MelodiKitaHandler)
    preview_host = "127.0.0.1" if HOST == "0.0.0.0" else HOST
    print(f"{APP_NAME} berjalan di http://{preview_host}:{PORT}")
    print(f"Database SQLite: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
