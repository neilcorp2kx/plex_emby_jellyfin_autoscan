import logging
import os

from peewee import Model, CharField, IntegerField, IntegrityError, fn
from playhouse.pool import PooledSqliteDatabase

import config

logger = logging.getLogger("DB")

# Config
conf = config.Config()

db_path = conf.settings['queuefile']
database = PooledSqliteDatabase(
    db_path,
    max_connections=32,
    stale_timeout=180,
    pragmas={
        'journal_mode': 'wal',
        'cache_size': -1024 * 64,  # 64MB
        'foreign_keys': 1,
        'ignore_check_constraints': 0,
        'synchronous': 0
    }
)


class BaseQueueModel(Model):
    class Meta:
        database = database


class QueueItemModel(BaseQueueModel):
    scan_path = CharField(max_length=256, unique=True, null=False)
    scan_for = CharField(max_length=64, null=False)
    scan_section = IntegerField(null=False)
    scan_type = CharField(max_length=64, null=False)

    class Meta:
        database = database
        indexes = (
            (('scan_for', 'scan_type'), False),  # Composite index for common queries
        )


def create_database(db, db_path):
    if not os.path.exists(db_path):
        db.create_tables([QueueItemModel])
        logger.info("Created Plex Autoscan database tables.")


def connect(db):
    if not db.is_closed():
        return False
    return db.connect()


def init(db, db_path):
    if not os.path.exists(db_path):
        create_database(db, db_path)
    connect(db)


def get_next_item():
    item = None
    try:
        item = QueueItemModel.get()
    except Exception as e:
        logger.exception("Exception getting first item to scan: %s", e)
    return item


def exists_file_root_path(file_path):
    """Check if path or its parent directory is already queued - OPTIMIZED

    Uses database query instead of fetching all items and looping in Python.
    """
    if '.' in file_path:
        dir_path = os.path.dirname(file_path)
    else:
        dir_path = file_path

    try:
        # Use database query instead of Python loop (fixes N+1 query problem)
        item = QueueItemModel.select().where(
            fn.LOWER(QueueItemModel.scan_path).contains(dir_path.lower())
        ).first()

        if item:
            return True, item.scan_path
        return False, None
    except Exception as e:
        logger.exception("Error checking file path: %s", e)
        return False, None


def get_all_items():
    items = []
    try:
        for item in QueueItemModel.select():
            items.append({'scan_path': item.scan_path,
                          'scan_for': item.scan_for,
                          'scan_type': item.scan_type,
                          'scan_section': item.scan_section})
    except Exception:
        logger.exception("Exception getting all items from Plex Autoscan database: ")
        return None
    return items


def get_queue_count():
    count = 0
    try:
        count = QueueItemModel.select().count()
    except Exception:
        logger.exception("Exception getting queued item count from Plex Autoscan database: ")
    return count


def remove_item(scan_path):
    try:
        return QueueItemModel.delete().where(QueueItemModel.scan_path == scan_path).execute()
    except Exception:
        logger.exception("Exception deleting %r from Plex Autoscan database: ", scan_path)
        return False


def add_item(scan_path, scan_for, scan_section, scan_type):
    item = None
    try:
        return QueueItemModel.create(scan_path=scan_path, scan_for=scan_for, scan_section=scan_section,
                                     scan_type=scan_type)
    except AttributeError as ex:
        logger.exception("AttributeError adding %r to database: %s", scan_path, ex)
        return item
    except IntegrityError as e:
        logger.warning("Item %r already exists in database: %s", scan_path, e)
        return item
    except Exception as e:
        logger.exception("Exception adding %r to database: %s", scan_path, e)
    return item


def add_item_atomic(scan_path, scan_for, scan_section, scan_type):
    """Atomically check and add item to prevent race conditions"""
    try:
        with database.atomic():
            # Check if exists
            existing = QueueItemModel.select().where(
                QueueItemModel.scan_path == scan_path
            ).first()

            if existing:
                return False, "Already queued"

            item = QueueItemModel.create(
                scan_path=scan_path,
                scan_for=scan_for,
                scan_section=scan_section,
                scan_type=scan_type
            )
            return True, item
    except IntegrityError:
        logger.warning("Item %r already queued (concurrent insert)", scan_path)
        return False, "Already queued (concurrent)"
    except Exception as e:
        logger.exception("Error adding item atomically: %s", e)
        return False, str(e)


def queued_count():
    try:
        return QueueItemModel.select().count()
    except Exception as e:
        logger.exception("Exception retrieving queued count: %s", e)
    return 0


def close_database():
    """Close database connections gracefully"""
    if not database.is_closed():
        database.close()
        logger.info("Database connections closed")


# Init
init(database, db_path)
