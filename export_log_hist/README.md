# Event Log History Export Directory

This directory contains exported event log files from the SurveillanceSentry system.

## Export Process

### Automatic Daily Export
- **Schedule**: Runs daily at midnight (00:00)
- **Format**: CSV files with timestamp in filename
- **Naming Convention**: `event_log_YYYYMMDD_HHMMSS.csv`
- **Content**: Complete event log data including track IDs, event types, descriptions, and timestamps
- **Post-Export**: Event log database is cleared after successful export (daily cleanup)
- **File Safety**: Each export creates a unique file - no overwriting occurs

### Manual Export
- **Trigger**: Via "Export Log" button in dashboard UI or `/api/export-events` API endpoint
- **Format**: CSV files with timestamp in filename
- **Naming Convention**: `event_log_YYYYMMDD_HHMMSS.csv`
- **Content**: Complete event log data at time of export
- **Post-Export**: Event log database is NOT cleared - data remains for continued monitoring
- **File Safety**: Each manual export creates a unique file with timestamp

## CSV File Structure

Each CSV file contains the following columns:
- `id`: Event database ID
- `track_id`: Associated track identifier
- `event_type`: Type of event (Track Update, Course Change, Speed Alert, etc.)
- `description`: Detailed event description
- `timestamp`: ISO format timestamp when event occurred

## Manual Export

You can manually trigger an export via the API endpoint:
```
POST /api/export-events
```

View export history:
```
GET /api/export-history
```

## File Management

- Files are automatically created daily if events exist
- No automatic cleanup - files accumulate for historical analysis
- Consider implementing log rotation for long-term storage management
- Files can be safely archived or removed manually if disk space is a concern

## Integration Notes

This export system ensures:
- **Data Preservation**: Complete historical record of all surveillance events
- **Performance**: Regular database cleanup prevents event log bloat
- **Compliance**: CSV format suitable for audit trails and data analysis
- **Reliability**: Automatic scheduling with error handling and rollback
