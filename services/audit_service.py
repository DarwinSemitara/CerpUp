"""
Audit Log Service
Handles logging of administrative actions for security and accountability
"""

from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def log_audit_action(supabase, action_type, description, performed_by, performed_by_email=None,
                     target_type=None, target_id=None, target_name=None, metadata=None):
    """
    Log an administrative action to the audit log

    Args:
        supabase: Supabase client instance
        action_type: Type of action (e.g., 'MEMBER_CREATED', 'SCHEDULE_MODIFIED')
        description: Human-readable description of the action
        performed_by: Name of the admin who performed the action
        performed_by_email: Email of the admin (optional)
        target_type: Type of entity affected (e.g., 'member', 'schedule')
        target_id: ID of the affected entity (optional)
        target_name: Name of the affected entity (optional)
        metadata: Additional details as dictionary (optional)

    Returns:
        The created audit log entry or None if failed
    """
    try:
        audit_entry = {
            'action_type': action_type,
            'description': description,
            'performed_by': performed_by,
            'performed_by_email': performed_by_email,
            'target_type': target_type,
            'target_id': target_id,
            'target_name': target_name,
            'metadata': metadata,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'is_read': False,
            'is_archived': False
        }

        result = supabase.table('audit_log').insert(audit_entry).execute()

        if result.data:
            logger.info(f"Audit log created: {action_type} by {performed_by}")
            return result.data[0]
        else:
            logger.warning(
                f"Audit log creation returned no data: {action_type}")
            return None

    except Exception as e:
        logger.error(f"Failed to log audit action: {e}", exc_info=True)
        return None


def get_recent_audit_logs(supabase, limit=7, unread_only=False):
    """
    Get recent audit log entries

    Args:
        supabase: Supabase client instance
        limit: Maximum number of entries to return
        unread_only: If True, only return unread entries

    Returns:
        List of audit log entries
    """
    try:
        query = supabase.table('audit_log').select(
            '*').eq('is_archived', False)

        if unread_only:
            query = query.eq('is_read', False)

        query = query.order('created_at', desc=True).limit(limit)

        result = query.execute()
        return result.data or []

    except Exception as e:
        # Silently return empty list if table doesn't exist yet
        if 'PGRST205' in str(e) or 'audit_log' in str(e):
            return []
        logger.error(f"Failed to get audit logs: {e}", exc_info=True)
        return []


def mark_audit_log_as_read(supabase, log_id):
    """
    Mark an audit log entry as read

    Args:
        supabase: Supabase client instance
        log_id: ID of the audit log entry

    Returns:
        True if successful, False otherwise
    """
    try:
        result = supabase.table('audit_log').update({
            'is_read': True
        }).eq('id', log_id).execute()

        return bool(result.data)

    except Exception as e:
        logger.error(f"Failed to mark audit log as read: {e}", exc_info=True)
        return False


def mark_all_audit_logs_as_read(supabase):
    """
    Mark all unread audit logs as read

    Args:
        supabase: Supabase client instance

    Returns:
        Number of entries marked as read
    """
    try:
        result = supabase.table('audit_log').update({
            'is_read': True
        }).eq('is_read', False).eq('is_archived', False).execute()

        return len(result.data) if result.data else 0

    except Exception as e:
        logger.error(
            f"Failed to mark all audit logs as read: {e}", exc_info=True)
        return 0


def archive_old_audit_logs(supabase, days=7):
    """
    Archive audit logs older than specified days or beyond the 7 most recent unread

    Args:
        supabase: Supabase client instance
        days: Number of days to keep unarchived

    Returns:
        Number of entries archived
    """
    try:
        from datetime import timedelta

        cutoff_date = (datetime.now(timezone.utc) -
                       timedelta(days=days)).isoformat()

        # Archive old entries
        result = supabase.table('audit_log').update({
            'is_archived': True
        }).lt('created_at', cutoff_date).eq('is_archived', False).execute()

        archived_count = len(result.data) if result.data else 0

        # Also archive unread entries beyond the 7 most recent
        unread_logs = supabase.table('audit_log').select('id').eq(
            'is_read', False).eq('is_archived', False).order('created_at', desc=True).execute()

        if unread_logs.data and len(unread_logs.data) > 7:
            ids_to_archive = [log['id'] for log in unread_logs.data[7:]]

            if ids_to_archive:
                archive_result = supabase.table('audit_log').update({
                    'is_archived': True
                }).in_('id', ids_to_archive).execute()

                if archive_result.data:
                    archived_count += len(archive_result.data)

        logger.info(f"Archived {archived_count} audit log entries")
        return archived_count

    except Exception as e:
        logger.error(f"Failed to archive old audit logs: {e}", exc_info=True)
        return 0


# Action type constants for consistency
class AuditAction:
    # Member actions
    MEMBER_CREATED = 'MEMBER_CREATED'
    MEMBER_UPDATED = 'MEMBER_UPDATED'
    MEMBER_DELETED = 'MEMBER_DELETED'
    MEMBER_DISABLED = 'MEMBER_DISABLED'
    MEMBER_ENABLED = 'MEMBER_ENABLED'

    # Schedule actions
    SCHEDULE_CREATED = 'SCHEDULE_CREATED'
    SCHEDULE_MODIFIED = 'SCHEDULE_MODIFIED'
    SCHEDULE_DELETED = 'SCHEDULE_DELETED'

    # Course actions
    COURSE_ASSIGNED = 'COURSE_ASSIGNED'
    COURSE_UNASSIGNED = 'COURSE_UNASSIGNED'

    # FSR actions
    FSR_UPLOADED = 'FSR_UPLOADED'
    FSR_DELETED = 'FSR_DELETED'

    # Research actions
    RESEARCH_ADDED = 'RESEARCH_ADDED'
    RESEARCH_DELETED = 'RESEARCH_DELETED'

    # Extension actions
    EXTENSION_ADDED = 'EXTENSION_ADDED'
    EXTENSION_DELETED = 'EXTENSION_DELETED'
