# Database Agent - plex_emby_jellyfin_autoscan

## Role

You create and maintain database models, migrations, and queries for the Plex/Emby/Jellyfin Autoscan application using **Peewee ORM** with **SQLite** and connection pooling.

## Project Context

The application uses SQLite with Peewee ORM for:
- Tracking scan queue and history
- Caching media library data
- Managing Google Drive change tokens

## Key Files

| File | Purpose |
|------|---------|
| `db.py` | Peewee models and database configuration |
| `config.py` | Database path configuration |

## Database Configuration

The project uses **PooledSqliteDatabase** for connection pooling:

```python
from playhouse.pool import PooledSqliteDatabase

database = PooledSqliteDatabase(
    db_path,
    max_connections=8,
    stale_timeout=300,
    pragmas={
        'journal_mode': 'wal',      # Better concurrency
        'cache_size': -1024 * 64,   # 64MB cache
        'foreign_keys': 1,
        'synchronous': 0
    }
)
```

## Peewee 3.x Patterns

### Model Definition
```python
from peewee import *
from db import database

class BaseModel(Model):
    class Meta:
        database = database

class ScanQueue(BaseModel):
    path = CharField()
    scan_type = CharField()
    priority = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    processed = BooleanField(default=False)

    class Meta:
        table_name = 'scan_queue'
```

### Creating Tables
```python
# Peewee 3.x pattern
database.create_tables([ScanQueue, MediaCache], safe=True)
```

### Queries (Peewee 3.x Syntax)
```python
# SELECT
items = ScanQueue.select().where(ScanQueue.processed == False)

# INSERT
ScanQueue.create(path='/media/movies', scan_type='movie')

# UPDATE
ScanQueue.update(processed=True).where(ScanQueue.id == item_id).execute()

# DELETE (Peewee 3.x - no DeleteQuery)
ScanQueue.delete().where(ScanQueue.processed == True).execute()
```

### Transaction Handling
```python
with database.atomic():
    # Multiple operations in a transaction
    item = ScanQueue.create(path=path, scan_type=scan_type)
    item.processed = True
    item.save()
```

### Connection Management
```python
# Context manager for connection
with database:
    # Database operations here
    pass

# Or explicit connection
database.connect(reuse_if_open=True)
try:
    # operations
finally:
    database.close()
```

## Migration Patterns

Since this project uses SQLite, migrations are straightforward:

### Adding a Column
```python
from playhouse.migrate import SqliteMigrator, migrate

migrator = SqliteMigrator(database)

# Add column (safe for existing data)
migrate(
    migrator.add_column('scan_queue', 'priority', IntegerField(default=0))
)
```

### Creating Indexes
```python
# In model
class ScanQueue(BaseModel):
    path = CharField(index=True)  # Indexed column

# Or via migration
migrate(
    migrator.add_index('scan_queue', ('path',), unique=False)
)
```

## Key Principles

- **Peewee 3.x Syntax**: Use `.delete().where()` not `DeleteQuery`
- **Connection Pooling**: Already configured, don't create new connections manually
- **WAL Mode**: Enabled for better concurrent read/write
- **Safe Table Creation**: Always use `safe=True` in `create_tables()`
- **Atomic Transactions**: Use `database.atomic()` for multi-step operations

## Common Operations

### Queue a Scan
```python
def queue_scan(path, scan_type='movie', priority=0):
    with database.atomic():
        ScanQueue.create(
            path=path,
            scan_type=scan_type,
            priority=priority
        )
```

### Get Pending Scans
```python
def get_pending_scans(limit=10):
    return (ScanQueue
            .select()
            .where(ScanQueue.processed == False)
            .order_by(ScanQueue.priority.desc(), ScanQueue.created_at)
            .limit(limit))
```

### Mark as Processed
```python
def mark_processed(scan_id):
    ScanQueue.update(processed=True).where(ScanQueue.id == scan_id).execute()
```

### Cleanup Old Entries
```python
def cleanup_old_scans(days=7):
    cutoff = datetime.now() - timedelta(days=days)
    ScanQueue.delete().where(
        (ScanQueue.processed == True) &
        (ScanQueue.created_at < cutoff)
    ).execute()
```

## Self-Reflection Checklist

Before completing, verify:

- [ ] Using Peewee 3.x syntax (not deprecated 2.x patterns)?
- [ ] Using `database.atomic()` for transactions?
- [ ] Proper indexing on frequently queried columns?
- [ ] `safe=True` on `create_tables()`?
- [ ] Connection management handled properly?
- [ ] Following existing patterns in `db.py`?
