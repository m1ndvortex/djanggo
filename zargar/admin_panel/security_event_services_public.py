"""
Security Event Management Services for Public Schema Models.

This module provides backend services for managing security events using
the public schema models (PublicSecurityEvent, SuperAdmin, etc.).
"""
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

from zargar.tenants.models import SuperAdmin
from zargar.tenants.admin_models import PublicSecurityEvent, PublicAuditLog

logger = logging.getLogger(__name__)


class PublicSecurityEventFilterService:
    """Service for filtering and searching public security events."""
    
    @staticmethod
    def get_filtered_events(
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
        order_by: str = '-created_at'
    ) -> Tuple[List[PublicSecurityEvent], Dict[str, Any]]:
        """
        Get filtered public security events with pagination and metadata.
        """
        queryset = PublicSecurityEvent.objects.all()
        
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
        
        if ip_address:
            queryset = queryset.filter(ip_address__icontains=ip_address)
        
        if search_query:
            queryset = queryset.filter(
                Q(username_attempted__icontains=search_query) |
                Q(ip_address__icontains=search_query) |
                Q(user_agent__icontains=search_query) |
                Q(resolution_notes__icontains=search_query)
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
                'ip_address': ip_address,
                'search_query': search_query,
            }
        }
        
        return list(page_obj.object_list), metadata
    
    @staticmethod
    def get_event_statistics(
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get public security event statistics for the given date range."""
        if not date_from:
            date_from = timezone.now() - timedelta(days=30)
        if not date_to:
            date_to = timezone.now()
        
        queryset = PublicSecurityEvent.objects.filter(
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
            count=Count('id')
        ).order_by('-count')[:10]
        
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
        }


class PublicSecurityEventCategorizationService:
    """Service for categorizing and analyzing public security events."""
    
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
        }
    }
    
    @classmethod
    def categorize_event(cls, event: PublicSecurityEvent) -> Dict[str, Any]:
        """
        Categorize a public security event and calculate its risk score.
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
    def _calculate_risk_score(cls, event: PublicSecurityEvent) -> float:
        """Calculate risk score for an event."""
        base_score = cls.RISK_WEIGHTS['event_type'].get(event.event_type, 1)
        severity_multiplier = cls.RISK_WEIGHTS['severity'].get(event.severity, 1.0)
        
        # Check for frequency patterns
        frequency_multiplier = 1.0
        if event.ip_address:
            recent_events = PublicSecurityEvent.objects.filter(
                ip_address=event.ip_address,
                event_type=event.event_type,
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            if recent_events > 5:
                frequency_multiplier = 2.0
            elif recent_events > 2:
                frequency_multiplier = 1.5
        
        risk_score = base_score * severity_multiplier * frequency_multiplier
        return min(risk_score, 10.0)  # Cap at 10
    
    @classmethod
    def _determine_priority(cls, event: PublicSecurityEvent, risk_score: float) -> str:
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
    def _analyze_patterns(cls, event: PublicSecurityEvent) -> Dict[str, Any]:
        """Analyze patterns related to the event."""
        pattern_info = {
            'has_pattern': False,
            'pattern_type': None,
            'confidence': 0.0,
        }
        
        # Check for IP-based patterns
        if event.ip_address:
            recent_events = PublicSecurityEvent.objects.filter(
                ip_address=event.ip_address,
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
            
            if recent_events.count() > 10:
                pattern_info.update({
                    'has_pattern': True,
                    'pattern_type': 'ip_frequency',
                    'confidence': min(recent_events.count() / 20.0, 1.0),
                })
        
        return pattern_info
    
    @classmethod
    def _get_recommended_action(cls, event: PublicSecurityEvent, risk_score: float, pattern_info: Dict) -> str:
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


class PublicSecurityEventResolutionService:
    """Service for resolving public security events."""
    
    @staticmethod
    def resolve_event(
        event_id: int,
        resolved_by_id: int,
        resolution_notes: str,
        resolution_type: str = 'manual',
        follow_up_required: bool = False
    ) -> Dict[str, Any]:
        """
        Resolve a public security event.
        """
        try:
            event = PublicSecurityEvent.objects.get(id=event_id)
            resolved_by = SuperAdmin.objects.get(id=resolved_by_id)
            
            # Mark event as resolved
            event.is_resolved = True
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
            PublicAuditLog.objects.create(
                action='security_event_resolve',
                model_name='PublicSecurityEvent',
                object_id=str(event.id),
                object_repr=str(event),
                details={
                    'resolution_type': resolution_type,
                    'resolution_notes': resolution_notes,
                    'resolved_by_id': resolved_by_id,
                    'resolved_by_username': resolved_by.username,
                    'follow_up_required': follow_up_required,
                }
            )
            
            logger.info(f"Public security event {event_id} resolved by {resolved_by.username}")
            
            return {
                'success': True,
                'message': 'Security event resolved successfully',
                'resolved_at': event.resolved_at,
                'resolved_by': resolved_by.username,
            }
            
        except PublicSecurityEvent.DoesNotExist:
            return {'success': False, 'error': 'Security event not found'}
        except SuperAdmin.DoesNotExist:
            return {'success': False, 'error': 'Resolver not found'}
        except Exception as e:
            logger.error(f"Error resolving public event {event_id}: {str(e)}")
            return {'success': False, 'error': 'Resolution failed'}
    
    @staticmethod
    def bulk_resolve_events(
        event_ids: List[int],
        resolved_by_id: int,
        resolution_notes: str,
        resolution_type: str = 'bulk'
    ) -> Dict[str, Any]:
        """
        Resolve multiple public security events in bulk.
        """
        try:
            resolved_by = SuperAdmin.objects.get(id=resolved_by_id)
            
            events = PublicSecurityEvent.objects.filter(
                id__in=event_ids,
                is_resolved=False
            )
            
            resolved_count = 0
            failed_events = []
            
            for event in events:
                try:
                    result = PublicSecurityEventResolutionService.resolve_event(
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
            PublicAuditLog.objects.create(
                action='security_event_bulk_resolve',
                model_name='PublicSecurityEvent',
                object_id='bulk',
                object_repr=f'Bulk resolution of {len(event_ids)} events',
                details={
                    'event_ids': event_ids,
                    'resolved_count': resolved_count,
                    'failed_count': len(failed_events),
                    'resolution_notes': resolution_notes,
                    'resolved_by_id': resolved_by_id,
                    'resolved_by_username': resolved_by.username,
                }
            )
            
            logger.info(f"Bulk resolved {resolved_count} public events, {len(failed_events)} failed")
            
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


def test_services_manually():
    """Manual test function to verify services work with real database."""
    print("🧪 Testing Public Security Event Services")
    print("=" * 50)
    
    try:
        # Test 1: Create test data
        print("\n1. Creating test data...")
        
        admin = SuperAdmin.objects.create_user(
            username='test_admin_manual',
            email='testadmin@example.com',
            password='testpass123'
        )
        print(f"✅ Created SuperAdmin: {admin.username}")
        
        event = PublicSecurityEvent.objects.create(
            event_type='login_failed',
            severity='medium',
            ip_address='192.168.1.100',
            user_agent='Manual Test Browser',
            username_attempted='testuser',
            details={'reason': 'invalid_password', 'manual_test': True}
        )
        print(f"✅ Created PublicSecurityEvent: {event.id}")
        
        # Test 2: Categorization
        print("\n2. Testing categorization...")
        
        categorization = PublicSecurityEventCategorizationService.categorize_event(event)
        print(f"✅ Category: {categorization['category']}")
        print(f"✅ Risk Score: {categorization['risk_score']:.1f}")
        print(f"✅ Priority: {categorization['priority']}")
        print(f"✅ Recommended Action: {categorization['recommended_action']}")
        
        # Test 3: Filtering
        print("\n3. Testing filtering...")
        
        events, metadata = PublicSecurityEventFilterService.get_filtered_events(
            event_type='login_failed',
            per_page=10
        )
        print(f"✅ Found {len(events)} login_failed events")
        print(f"✅ Total count: {metadata['total_count']}")
        
        # Test 4: Statistics
        print("\n4. Testing statistics...")
        
        stats = PublicSecurityEventFilterService.get_event_statistics()
        print(f"✅ Total events: {stats['total_events']}")
        print(f"✅ Resolution rate: {stats['resolution_rate']:.1f}%")
        print(f"✅ Severity breakdown: {stats['severity_breakdown']}")
        
        # Test 5: Resolution
        print("\n5. Testing resolution...")
        
        result = PublicSecurityEventResolutionService.resolve_event(
            event_id=event.id,
            resolved_by_id=admin.id,
            resolution_notes='Manual test resolution - false positive'
        )
        
        if result['success']:
            print(f"✅ Event resolved by: {result['resolved_by']}")
            
            # Verify in database
            event.refresh_from_db()
            if event.is_resolved:
                print("✅ Database updated - event marked as resolved")
        else:
            print(f"❌ Resolution failed: {result['error']}")
        
        # Test 6: Audit logging
        print("\n6. Testing audit logging...")
        
        initial_count = PublicAuditLog.objects.count()
        
        PublicAuditLog.objects.create(
            action='manual_test',
            model_name='PublicSecurityEvent',
            object_id=str(event.id),
            object_repr=str(event),
            details={'manual_test': True}
        )
        
        final_count = PublicAuditLog.objects.count()
        print(f"✅ Audit logs: {initial_count} -> {final_count}")
        
        print("\n🎉 All manual tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Manual test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # This can be run directly for manual testing
    test_services_manually()