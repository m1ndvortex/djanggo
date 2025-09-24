"""
Security Event Management Services for Super Admin Panel.

This module provides backend services for managing security events including:
- Filtering and categorization
- Investigation workflow with status tracking
- Resolution system with notes and assignment
"""
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

from zargar.core.security_models import SecurityEvent, SuspiciousActivity, AuditLog
from zargar.tenants.models import SuperAdmin

logger = logging.getLogger(__name__)


class SecurityEventFilterService:
    """Service for filtering and searching security events."""
    
    @staticmethod
    def get_filtered_events(
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        search_query: Optional[str] = None,
        assigned_to: Optional[int] = None,
        investigation_status: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
        order_by: str = '-created_at'
    ) -> Tuple[List[SecurityEvent], Dict[str, Any]]:
        """
        Get filtered security events with pagination and metadata.
        
        Args:
            event_type: Filter by event type
            severity: Filter by severity level
            is_resolved: Filter by resolution status
            date_from: Filter events from this date
            date_to: Filter events to this date
            user_id: Filter by user ID
            ip_address: Filter by IP address
            search_query: General search query
            assigned_to: Filter by assigned investigator
            investigation_status: Filter by investigation status
            page: Page number for pagination
            per_page: Items per page
            order_by: Order by field
            
        Returns:
            Tuple of (events_list, metadata_dict)
        """
        queryset = SecurityEvent.objects.select_related('user', 'resolved_by').all()
        
        # Apply filters
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        if severity:
            queryset = queryset.filter(severity=severity)
        
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved)
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        if ip_address:
            queryset = queryset.filter(ip_address__icontains=ip_address)
        
        if assigned_to:
            # Add assigned_to field to SecurityEvent model if needed
            # For now, we'll use resolved_by as a proxy
            queryset = queryset.filter(resolved_by_id=assigned_to)
        
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(username_attempted__icontains=search_query) |
                Q(ip_address__icontains=search_query) |
                Q(user_agent__icontains=search_query) |
                Q(resolution_notes__icontains=search_query) |
                Q(details__icontains=search_query)
            )
        
        # Order results
        queryset = queryset.order_by(order_by)
        
        # Get total count before pagination
        total_count = queryset.count()
        
        # Apply pagination
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        # Prepare metadata
        metadata = {
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'filters_applied': {
                'event_type': event_type,
                'severity': severity,
                'is_resolved': is_resolved,
                'date_from': date_from,
                'date_to': date_to,
                'user_id': user_id,
                'ip_address': ip_address,
                'search_query': search_query,
                'assigned_to': assigned_to,
                'investigation_status': investigation_status,
            }
        }
        
        return list(page_obj.object_list), metadata
    
    @staticmethod
    def get_event_statistics(
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get security event statistics for the given date range.
        
        Args:
            date_from: Start date for statistics
            date_to: End date for statistics
            
        Returns:
            Dictionary containing various statistics
        """
        if not date_from:
            date_from = timezone.now() - timedelta(days=30)
        if not date_to:
            date_to = timezone.now()
        
        queryset = SecurityEvent.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        )
        
        # Basic counts
        total_events = queryset.count()
        resolved_events = queryset.filter(is_resolved=True).count()
        unresolved_events = total_events - resolved_events
        
        # Events by severity
        severity_stats = queryset.values('severity').annotate(
            count=Count('id')
        ).order_by('severity')
        
        # Events by type
        type_stats = queryset.values('event_type').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Top risk IPs
        ip_stats = queryset.filter(
            severity__in=['high', 'critical']
        ).values('ip_address').annotate(
            count=Count('id'),
            max_severity=Max('severity')
        ).order_by('-count')[:10]
        
        # Resolution time statistics (for resolved events)
        resolved_queryset = queryset.filter(
            is_resolved=True,
            resolved_at__isnull=False
        )
        
        resolution_stats = {}
        if resolved_queryset.exists():
            # Calculate average resolution time
            resolution_times = []
            for event in resolved_queryset:
                if event.resolved_at and event.created_at:
                    delta = event.resolved_at - event.created_at
                    resolution_times.append(delta.total_seconds())
            
            if resolution_times:
                avg_resolution_time = sum(resolution_times) / len(resolution_times)
                resolution_stats = {
                    'average_resolution_seconds': avg_resolution_time,
                    'average_resolution_hours': avg_resolution_time / 3600,
                    'fastest_resolution_seconds': min(resolution_times),
                    'slowest_resolution_seconds': max(resolution_times),
                }
        
        return {
            'date_range': {
                'from': date_from,
                'to': date_to,
            },
            'total_events': total_events,
            'resolved_events': resolved_events,
            'unresolved_events': unresolved_events,
            'resolution_rate': (resolved_events / total_events * 100) if total_events > 0 else 0,
            'severity_breakdown': {item['severity']: item['count'] for item in severity_stats},
            'top_event_types': list(type_stats),
            'top_risk_ips': list(ip_stats),
            'resolution_statistics': resolution_stats,
        }


class SecurityEventCategorizationService:
    """Service for categorizing and analyzing security events."""
    
    # Event categorization mapping
    CATEGORY_MAPPING = {
        'authentication': [
            'login_success', 'login_failed', 'login_blocked', 'logout',
            'password_change', 'password_reset_request', 'password_reset_complete',
            '2fa_enabled', '2fa_disabled', '2fa_success', '2fa_failed', '2fa_backup_used'
        ],
        'account_security': [
            'account_locked', 'account_unlocked', 'suspicious_activity',
            'brute_force_attempt', 'session_hijack'
        ],
        'access_control': [
            'unauthorized_access', 'privilege_escalation', 'admin_impersonation'
        ],
        'data_operations': [
            'data_export', 'bulk_operation'
        ],
        'system_security': [
            'api_rate_limit', 'csrf_failure'
        ]
    }
    
    # Risk scoring weights
    RISK_WEIGHTS = {
        'event_type': {
            'login_failed': 2,
            'login_blocked': 5,
            'brute_force_attempt': 8,
            'unauthorized_access': 7,
            'privilege_escalation': 9,
            'suspicious_activity': 6,
            'session_hijack': 8,
            'admin_impersonation': 5,
            'data_export': 4,
            'bulk_operation': 3,
            'api_rate_limit': 3,
            'csrf_failure': 4,
        },
        'severity': {
            'low': 1.0,
            'medium': 2.0,
            'high': 3.0,
            'critical': 4.0,
        },
        'frequency': {
            'single': 1.0,
            'multiple': 1.5,
            'pattern': 2.0,
        }
    }
    
    @classmethod
    def categorize_event(cls, event: SecurityEvent) -> Dict[str, Any]:
        """
        Categorize a security event and calculate its risk score.
        
        Args:
            event: SecurityEvent instance to categorize
            
        Returns:
            Dictionary containing categorization information
        """
        # Determine category
        category = 'other'
        for cat, event_types in cls.CATEGORY_MAPPING.items():
            if event.event_type in event_types:
                category = cat
                break
        
        # Calculate risk score
        risk_score = cls._calculate_risk_score(event)
        
        # Determine priority level
        priority = cls._determine_priority(event, risk_score)
        
        # Check for patterns
        pattern_info = cls._analyze_patterns(event)
        
        return {
            'category': category,
            'risk_score': risk_score,
            'priority': priority,
            'pattern_detected': pattern_info['has_pattern'],
            'pattern_type': pattern_info['pattern_type'],
            'pattern_confidence': pattern_info['confidence'],
            'recommended_action': cls._get_recommended_action(event, risk_score, pattern_info),
            'escalation_required': risk_score >= 7.0 or event.severity == 'critical',
        }
    
    @classmethod
    def _calculate_risk_score(cls, event: SecurityEvent) -> float:
        """Calculate risk score for an event."""
        base_score = cls.RISK_WEIGHTS['event_type'].get(event.event_type, 1)
        severity_multiplier = cls.RISK_WEIGHTS['severity'].get(event.severity, 1.0)
        
        # Check for frequency patterns
        frequency_multiplier = 1.0
        if event.ip_address:
            recent_events = SecurityEvent.objects.filter(
                ip_address=event.ip_address,
                event_type=event.event_type,
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            if recent_events > 5:
                frequency_multiplier = cls.RISK_WEIGHTS['frequency']['pattern']
            elif recent_events > 2:
                frequency_multiplier = cls.RISK_WEIGHTS['frequency']['multiple']
        
        risk_score = base_score * severity_multiplier * frequency_multiplier
        return min(risk_score, 10.0)  # Cap at 10
    
    @classmethod
    def _determine_priority(cls, event: SecurityEvent, risk_score: float) -> str:
        """Determine priority level based on event and risk score."""
        if event.severity == 'critical' or risk_score >= 8.0:
            return 'critical'
        elif event.severity == 'high' or risk_score >= 6.0:
            return 'high'
        elif event.severity == 'medium' or risk_score >= 4.0:
            return 'medium'
        else:
            return 'low'
    
    @classmethod
    def _analyze_patterns(cls, event: SecurityEvent) -> Dict[str, Any]:
        """Analyze patterns related to the event."""
        pattern_info = {
            'has_pattern': False,
            'pattern_type': None,
            'confidence': 0.0,
        }
        
        # Check for IP-based patterns
        if event.ip_address:
            recent_events = SecurityEvent.objects.filter(
                ip_address=event.ip_address,
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
            
            if recent_events.count() > 10:
                pattern_info.update({
                    'has_pattern': True,
                    'pattern_type': 'ip_frequency',
                    'confidence': min(recent_events.count() / 20.0, 1.0),
                })
        
        # Check for user-based patterns
        if event.user:
            user_events = SecurityEvent.objects.filter(
                user=event.user,
                event_type__in=['login_failed', 'unauthorized_access'],
                created_at__gte=timezone.now() - timedelta(hours=6)
            )
            
            if user_events.count() > 5:
                pattern_info.update({
                    'has_pattern': True,
                    'pattern_type': 'user_compromise',
                    'confidence': min(user_events.count() / 10.0, 1.0),
                })
        
        return pattern_info
    
    @classmethod
    def _get_recommended_action(cls, event: SecurityEvent, risk_score: float, pattern_info: Dict) -> str:
        """Get recommended action based on event analysis."""
        if pattern_info['has_pattern'] and pattern_info['confidence'] > 0.7:
            return 'pattern_investigation'
        elif risk_score >= 8.0 or event.severity == 'critical':
            return 'immediate_investigation'
        elif risk_score >= 6.0:
            return 'priority_review'
        elif risk_score >= 4.0:
            return 'standard_review'
        else:
            return 'monitor'
    
    @classmethod
    def get_categorized_events_summary(
        cls,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get summary of categorized events."""
        if not date_from:
            date_from = timezone.now() - timedelta(days=7)
        if not date_to:
            date_to = timezone.now()
        
        events = SecurityEvent.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        )
        
        category_summary = {}
        priority_summary = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for event in events:
            categorization = cls.categorize_event(event)
            
            # Update category summary
            category = categorization['category']
            if category not in category_summary:
                category_summary[category] = {
                    'count': 0,
                    'resolved': 0,
                    'avg_risk_score': 0.0,
                    'risk_scores': []
                }
            
            category_summary[category]['count'] += 1
            category_summary[category]['risk_scores'].append(categorization['risk_score'])
            
            if event.is_resolved:
                category_summary[category]['resolved'] += 1
            
            # Update priority summary
            priority_summary[categorization['priority']] += 1
        
        # Calculate averages
        for category_data in category_summary.values():
            if category_data['risk_scores']:
                category_data['avg_risk_score'] = sum(category_data['risk_scores']) / len(category_data['risk_scores'])
            del category_data['risk_scores']  # Remove raw scores from output
        
        return {
            'date_range': {'from': date_from, 'to': date_to},
            'category_summary': category_summary,
            'priority_summary': priority_summary,
            'total_events': events.count(),
        }


class SecurityEventInvestigationService:
    """Service for managing security event investigations."""
    
    # Investigation status choices
    INVESTIGATION_STATUSES = [
        ('not_started', 'Not Started'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending_info', 'Pending Information'),
        ('escalated', 'Escalated'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    @staticmethod
    def assign_investigator(
        event_id: int,
        investigator_id: int,
        assigned_by_id: int,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        Assign an investigator to a security event.
        
        Args:
            event_id: ID of the security event
            investigator_id: ID of the investigator (SuperAdmin)
            assigned_by_id: ID of the user making the assignment
            notes: Assignment notes
            
        Returns:
            Dictionary containing assignment result
        """
        try:
            event = SecurityEvent.objects.get(id=event_id)
            investigator = SuperAdmin.objects.get(id=investigator_id)
            assigned_by = SuperAdmin.objects.get(id=assigned_by_id)
            
            # Update event with assignment info
            # Note: We'll need to add these fields to SecurityEvent model
            # For now, we'll use the existing resolved_by field as a proxy
            event.resolved_by = investigator
            
            # Add assignment notes to resolution_notes
            assignment_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Assigned to {investigator.username} by {assigned_by.username}"
            if notes:
                assignment_note += f": {notes}"
            
            if event.resolution_notes:
                event.resolution_notes += f"\n{assignment_note}"
            else:
                event.resolution_notes = assignment_note
            
            event.save()
            
            # Log the assignment
            AuditLog.log_action(
                action='security_event_assign',
                content_object=event,
                details={
                    'investigator_id': investigator_id,
                    'investigator_username': investigator.username,
                    'assigned_by_id': assigned_by_id,
                    'assigned_by_username': assigned_by.username,
                    'assignment_notes': notes,
                }
            )
            
            logger.info(f"Security event {event_id} assigned to {investigator.username}")
            
            return {
                'success': True,
                'message': f'Event assigned to {investigator.username}',
                'investigator': {
                    'id': investigator.id,
                    'username': investigator.username,
                    'email': investigator.email,
                }
            }
            
        except SecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except SuperAdmin.DoesNotExist:
            return {'success': False, 'error': 'Investigator not found'}
        except Exception as e:
            logger.error(f"Error assigning investigator to event {event_id}: {str(e)}")
            return {'success': False, 'error': 'Assignment failed'}
    
    @staticmethod
    def update_investigation_status(
        event_id: int,
        status: str,
        updated_by_id: int,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        Update investigation status of a security event.
        
        Args:
            event_id: ID of the security event
            status: New investigation status
            updated_by_id: ID of the user updating status
            notes: Status update notes
            
        Returns:
            Dictionary containing update result
        """
        try:
            event = SecurityEvent.objects.get(id=event_id)
            updated_by = SuperAdmin.objects.get(id=updated_by_id)
            
            # Add status update to resolution notes
            status_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] Status updated to '{status}' by {updated_by.username}"
            if notes:
                status_note += f": {notes}"
            
            if event.resolution_notes:
                event.resolution_notes += f"\n{status_note}"
            else:
                event.resolution_notes = status_note
            
            # If status is resolved or closed, mark as resolved
            if status in ['resolved', 'closed']:
                event.is_resolved = True
                event.resolved_at = timezone.now()
                if not event.resolved_by:
                    event.resolved_by = updated_by
            
            event.save()
            
            # Log the status update
            AuditLog.log_action(
                action='security_event_status_update',
                content_object=event,
                details={
                    'new_status': status,
                    'updated_by_id': updated_by_id,
                    'updated_by_username': updated_by.username,
                    'status_notes': notes,
                }
            )
            
            logger.info(f"Security event {event_id} status updated to '{status}'")
            
            return {
                'success': True,
                'message': f'Status updated to {status}',
                'new_status': status,
                'is_resolved': event.is_resolved,
            }
            
        except SecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except SuperAdmin.DoesNotExist:
            return {'success': False, 'error': 'User not found'}
        except Exception as e:
            logger.error(f"Error updating status for event {event_id}: {str(e)}")
            return {'success': False, 'error': 'Status update failed'}
    
    @staticmethod
    def add_investigation_note(
        event_id: int,
        note: str,
        added_by_id: int,
        note_type: str = 'investigation'
    ) -> Dict[str, Any]:
        """
        Add an investigation note to a security event.
        
        Args:
            event_id: ID of the security event
            note: Investigation note content
            added_by_id: ID of the user adding the note
            note_type: Type of note (investigation, resolution, escalation)
            
        Returns:
            Dictionary containing result
        """
        try:
            event = SecurityEvent.objects.get(id=event_id)
            added_by = SuperAdmin.objects.get(id=added_by_id)
            
            # Format the note with timestamp and user
            formatted_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] {note_type.upper()} by {added_by.username}: {note}"
            
            if event.resolution_notes:
                event.resolution_notes += f"\n{formatted_note}"
            else:
                event.resolution_notes = formatted_note
            
            event.save()
            
            # Log the note addition
            AuditLog.log_action(
                action='security_event_note_add',
                content_object=event,
                details={
                    'note_type': note_type,
                    'note_content': note,
                    'added_by_id': added_by_id,
                    'added_by_username': added_by.username,
                }
            )
            
            logger.info(f"Investigation note added to security event {event_id}")
            
            return {
                'success': True,
                'message': 'Investigation note added',
                'formatted_note': formatted_note,
            }
            
        except SecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except SuperAdmin.DoesNotExist:
            return {'success': False, 'error': 'User not found'}
        except Exception as e:
            logger.error(f"Error adding note to event {event_id}: {str(e)}")
            return {'success': False, 'error': 'Failed to add note'}
    
    @staticmethod
    def get_investigation_timeline(event_id: int) -> Dict[str, Any]:
        """
        Get investigation timeline for a security event.
        
        Args:
            event_id: ID of the security event
            
        Returns:
            Dictionary containing timeline information
        """
        try:
            event = SecurityEvent.objects.get(id=event_id)
            
            # Parse timeline from resolution_notes
            timeline = []
            
            # Add event creation
            timeline.append({
                'timestamp': event.created_at,
                'type': 'event_created',
                'description': f'Security event created: {event.get_event_type_display()}',
                'severity': event.severity,
                'user': None,
            })
            
            # Parse notes for timeline entries
            if event.resolution_notes:
                lines = event.resolution_notes.split('\n')
                for line in lines:
                    if line.strip() and line.startswith('['):
                        try:
                            # Extract timestamp and content
                            end_bracket = line.find(']')
                            if end_bracket > 0:
                                timestamp_str = line[1:end_bracket]
                                content = line[end_bracket + 1:].strip()
                                
                                # Parse timestamp
                                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                timestamp = timezone.make_aware(timestamp)
                                
                                # Determine entry type
                                entry_type = 'note'
                                if 'Assigned to' in content:
                                    entry_type = 'assignment'
                                elif 'Status updated' in content:
                                    entry_type = 'status_update'
                                elif 'INVESTIGATION' in content:
                                    entry_type = 'investigation'
                                elif 'RESOLUTION' in content:
                                    entry_type = 'resolution'
                                
                                timeline.append({
                                    'timestamp': timestamp,
                                    'type': entry_type,
                                    'description': content,
                                    'user': None,  # Could extract from content if needed
                                })
                        except (ValueError, IndexError):
                            continue
            
            # Add resolution if resolved
            if event.is_resolved and event.resolved_at:
                timeline.append({
                    'timestamp': event.resolved_at,
                    'type': 'event_resolved',
                    'description': f'Event resolved by {event.resolved_by.username if event.resolved_by else "System"}',
                    'user': event.resolved_by.username if event.resolved_by else None,
                })
            
            # Sort timeline by timestamp
            timeline.sort(key=lambda x: x['timestamp'])
            
            return {
                'success': True,
                'event_id': event_id,
                'timeline': timeline,
                'total_entries': len(timeline),
            }
            
        except SecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except Exception as e:
            logger.error(f"Error getting timeline for event {event_id}: {str(e)}")
            return {'success': False, 'error': 'Failed to get timeline'}
    
    @staticmethod
    def get_related_events(event_id: int) -> Dict[str, Any]:
        """
        Get events related to the given security event.
        
        Args:
            event_id: ID of the security event
            
        Returns:
            Dictionary containing related events
        """
        try:
            event = SecurityEvent.objects.get(id=event_id)
            
            related_events = {
                'by_ip': [],
                'by_user': [],
                'by_type': [],
                'suspicious_activities': [],
            }
            
            # Events from same IP
            if event.ip_address:
                ip_events = SecurityEvent.objects.filter(
                    ip_address=event.ip_address
                ).exclude(id=event_id).order_by('-created_at')[:10]
                
                related_events['by_ip'] = [
                    {
                        'id': e.id,
                        'event_type': e.event_type,
                        'severity': e.severity,
                        'created_at': e.created_at,
                        'is_resolved': e.is_resolved,
                    }
                    for e in ip_events
                ]
            
            # Events by same user
            if event.user:
                user_events = SecurityEvent.objects.filter(
                    user=event.user
                ).exclude(id=event_id).order_by('-created_at')[:10]
                
                related_events['by_user'] = [
                    {
                        'id': e.id,
                        'event_type': e.event_type,
                        'severity': e.severity,
                        'created_at': e.created_at,
                        'is_resolved': e.is_resolved,
                    }
                    for e in user_events
                ]
            
            # Events of same type
            type_events = SecurityEvent.objects.filter(
                event_type=event.event_type
            ).exclude(id=event_id).order_by('-created_at')[:5]
            
            related_events['by_type'] = [
                {
                    'id': e.id,
                    'user': e.user.username if e.user else e.username_attempted,
                    'ip_address': e.ip_address,
                    'severity': e.severity,
                    'created_at': e.created_at,
                    'is_resolved': e.is_resolved,
                }
                for e in type_events
            ]
            
            # Related suspicious activities
            if event.user or event.ip_address:
                activities = SuspiciousActivity.objects.filter(
                    Q(user=event.user) | Q(ip_address=event.ip_address)
                ).order_by('-created_at')[:5]
                
                related_events['suspicious_activities'] = [
                    {
                        'id': a.id,
                        'activity_type': a.activity_type,
                        'risk_level': a.risk_level,
                        'confidence_score': a.confidence_score,
                        'created_at': a.created_at,
                        'is_investigated': a.is_investigated,
                    }
                    for a in activities
                ]
            
            return {
                'success': True,
                'event_id': event_id,
                'related_events': related_events,
            }
            
        except SecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except Exception as e:
            logger.error(f"Error getting related events for {event_id}: {str(e)}")
            return {'success': False, 'error': 'Failed to get related events'}


class SecurityEventResolutionService:
    """Service for resolving security events."""
    
    @staticmethod
    def resolve_event(
        event_id: int,
        resolved_by_id: int,
        resolution_notes: str,
        resolution_type: str = 'manual',
        follow_up_required: bool = False
    ) -> Dict[str, Any]:
        """
        Resolve a security event.
        
        Args:
            event_id: ID of the security event
            resolved_by_id: ID of the user resolving the event
            resolution_notes: Resolution notes
            resolution_type: Type of resolution (manual, automated, escalated)
            follow_up_required: Whether follow-up is required
            
        Returns:
            Dictionary containing resolution result
        """
        try:
            event = SecurityEvent.objects.get(id=event_id)
            resolved_by = SuperAdmin.objects.get(id=resolved_by_id)
            
            # Mark event as resolved
            event.is_resolved = True
            event.resolved_by = resolved_by
            event.resolved_at = timezone.now()
            
            # Add resolution note
            resolution_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] RESOLVED by {resolved_by.username}: {resolution_notes}"
            
            if follow_up_required:
                resolution_note += " [FOLLOW-UP REQUIRED]"
            
            if event.resolution_notes:
                event.resolution_notes += f"\n{resolution_note}"
            else:
                event.resolution_notes = resolution_note
            
            event.save()
            
            # Log the resolution
            AuditLog.log_action(
                action='security_event_resolve',
                content_object=event,
                details={
                    'resolution_type': resolution_type,
                    'resolution_notes': resolution_notes,
                    'resolved_by_id': resolved_by_id,
                    'resolved_by_username': resolved_by.username,
                    'follow_up_required': follow_up_required,
                }
            )
            
            logger.info(f"Security event {event_id} resolved by {resolved_by.username}")
            
            return {
                'success': True,
                'message': 'Security event resolved successfully',
                'resolved_at': event.resolved_at,
                'resolved_by': resolved_by.username,
            }
            
        except SecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except SuperAdmin.DoesNotExist:
            return {'success': False, 'error': 'Resolver not found'}
        except Exception as e:
            logger.error(f"Error resolving event {event_id}: {str(e)}")
            return {'success': False, 'error': 'Resolution failed'}
    
    @staticmethod
    def bulk_resolve_events(
        event_ids: List[int],
        resolved_by_id: int,
        resolution_notes: str,
        resolution_type: str = 'bulk'
    ) -> Dict[str, Any]:
        """
        Resolve multiple security events in bulk.
        
        Args:
            event_ids: List of event IDs to resolve
            resolved_by_id: ID of the user resolving the events
            resolution_notes: Resolution notes
            resolution_type: Type of resolution
            
        Returns:
            Dictionary containing bulk resolution result
        """
        try:
            resolved_by = SuperAdmin.objects.get(id=resolved_by_id)
            
            events = SecurityEvent.objects.filter(
                id__in=event_ids,
                is_resolved=False
            )
            
            resolved_count = 0
            failed_events = []
            
            for event in events:
                try:
                    result = SecurityEventResolutionService.resolve_event(
                        event.id,
                        resolved_by_id,
                        f"[BULK RESOLUTION] {resolution_notes}",
                        resolution_type
                    )
                    
                    if result['success']:
                        resolved_count += 1
                    else:
                        failed_events.append({'id': event.id, 'error': result['error']})
                        
                except Exception as e:
                    failed_events.append({'id': event.id, 'error': str(e)})
            
            # Log bulk resolution
            AuditLog.log_action(
                action='security_event_bulk_resolve',
                details={
                    'event_ids': event_ids,
                    'resolved_count': resolved_count,
                    'failed_count': len(failed_events),
                    'resolution_notes': resolution_notes,
                    'resolved_by_id': resolved_by_id,
                    'resolved_by_username': resolved_by.username,
                }
            )
            
            logger.info(f"Bulk resolved {resolved_count} events, {len(failed_events)} failed")
            
            return {
                'success': True,
                'resolved_count': resolved_count,
                'failed_count': len(failed_events),
                'failed_events': failed_events,
                'message': f'Resolved {resolved_count} events successfully',
            }
            
        except SuperAdmin.DoesNotExist:
            return {'success': False, 'error': 'Resolver not found'}
        except Exception as e:
            logger.error(f"Error in bulk resolution: {str(e)}")
            return {'success': False, 'error': 'Bulk resolution failed'}
    
    @staticmethod
    def reopen_event(
        event_id: int,
        reopened_by_id: int,
        reason: str
    ) -> Dict[str, Any]:
        """
        Reopen a resolved security event.
        
        Args:
            event_id: ID of the security event
            reopened_by_id: ID of the user reopening the event
            reason: Reason for reopening
            
        Returns:
            Dictionary containing reopen result
        """
        try:
            event = SecurityEvent.objects.get(id=event_id)
            
            if not event.is_resolved:
                return {'success': False, 'error': 'Event is not resolved'}
            
            reopened_by = SuperAdmin.objects.get(id=reopened_by_id)
            
            # Reopen the event
            event.is_resolved = False
            event.resolved_at = None
            # Keep resolved_by for audit trail
            
            # Add reopen note
            reopen_note = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] REOPENED by {reopened_by.username}: {reason}"
            
            if event.resolution_notes:
                event.resolution_notes += f"\n{reopen_note}"
            else:
                event.resolution_notes = reopen_note
            
            event.save()
            
            # Log the reopening
            AuditLog.log_action(
                action='security_event_reopen',
                content_object=event,
                details={
                    'reason': reason,
                    'reopened_by_id': reopened_by_id,
                    'reopened_by_username': reopened_by.username,
                }
            )
            
            logger.info(f"Security event {event_id} reopened by {reopened_by.username}")
            
            return {
                'success': True,
                'message': 'Security event reopened successfully',
                'reopened_by': reopened_by.username,
            }
            
        except SecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except SuperAdmin.DoesNotExist:
            return {'success': False, 'error': 'User not found'}
        except Exception as e:
            logger.error(f"Error reopening event {event_id}: {str(e)}")
            return {'success': False, 'error': 'Reopen failed'}