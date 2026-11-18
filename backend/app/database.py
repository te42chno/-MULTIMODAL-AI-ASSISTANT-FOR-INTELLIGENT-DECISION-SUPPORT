import ssl

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _pg8000_ssl_context(sslmode: str):
    """Map libpq ``sslmode`` values to a pg8000-compatible ``ssl.SSLContext``.

    pg8000 does not accept libpq query parameters such as ``sslmode`` directly.
    SQLAlchemy passes unknown URL query values to ``DBAPI.connect()`` as keyword
    arguments, which raises ``TypeError: connect() got an unexpected keyword
    argument 'sslmode'``. We consume that value here and supply ``ssl_context``
    instead.
    """
    if not sslmode:
        return None
    mode = sslmode.strip().lower()
    if mode == "disable":
        return None

    # "verify-ca"/"verify-full" keep certificate validation enabled.
    # "require"/"allow"/"prefer" only require encryption (libpq semantics:
    # do not verify the server certificate) so self-signed hosts still connect.
    ctx = ssl.create_default_context()
    if mode in {"require", "allow", "prefer"}:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    elif mode == "verify-ca":
        ctx.check_hostname = False
    return ctx


def _engine_target():
    """Return the SQLAlchemy URL and connect_args, sanitised for the DB driver."""
    raw_url = settings.DATABASE_URL
    if raw_url.startswith("sqlite"):
        return raw_url, {"check_same_thread": False}

    url = make_url(raw_url)
    if "pg8000" not in (url.drivername or ""):
        # Other drivers (e.g. psycopg2) accept libpq params natively.
        return url, {}

    # pg8000 rejects every libpq query parameter (sslmode, channel_binding,
    # application_name, ...) so translate sslmode and drop the rest.
    query = dict(url.query)
    sslmode = query.pop("sslmode", None) or query.pop("ssl_mode", None)
    url = url.set(query={})

    connect_args = {}
    if sslmode:
        ctx = _pg8000_ssl_context(sslmode)
        if ctx is not None:
            connect_args["ssl_context"] = ctx

    return url, connect_args


_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_engine_url, _connect_args = _engine_target()

engine = create_engine(
    _engine_url,
    connect_args=_connect_args,
    pool_pre_ping=not _is_sqlite,
    pool_recycle=3600 if not _is_sqlite else -1,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
