"""
System Health Monitoring Backend for ZARGAR Admin Panel.
Provides real-time metrics collection and health status monitoring.
"""

import psutil
import redis
import logging
import socket
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from django.db import connection, connections
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from celery import current_app as celery_app
from celery.events.state import State

from .models import SystemHealthMetric, SystemHealthAlert

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """
    Main class for system health monitoring and metrics collection.
    """
    
    def __init__(self):
        self.hostname = socket.gethostname()
        self.redis_client = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection for health checks."""
        try:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url)
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all system health metrics.
        
        Returns:
            Dict containing all collected metrics
        """
        metrics = {}
        
        try:
            # System metrics
            metrics.update(self.get_system_metrics())
            
            # Database metrics
            metrics.update(self.get_database_metrics())
            
            # Redis metrics
            metrics.update(self.get_redis_metrics())
            
            # Celery metrics
            metrics.update(self.get_celery_metrics())
            
            # Application metrics
            metrics.update(self.get_application_metrics())
            
            # Store metrics in database
            self._store_metrics(metrics)
            
            # Check for alerts
            self._check_alert_thresholds(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Collect system-level metrics (CPU, Memory, Disk).
        
        Returns:
            Dict containing system metrics
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory usage
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network usage
            network_io = psutil.net_io_counters()
            
            # Load average (Unix systems)
            load_avg = None
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                # Windows doesn't have load average
                pass
            
            return {
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else None,
                    'load_average': load_avg,
                },
                'memory': {
                    'total_bytes': memory.total,
                    'available_bytes': memory.available,
                    'used_bytes': memory.used,
                    'usage_percent': memory.percent,
                    'swap_total_bytes': swap.total,
                    'swap_used_bytes': swap.used,
                    'swap_usage_percent': swap.percent,
                },
                'disk': {
                    'total_bytes': disk_usage.total,
                    'used_bytes': disk_usage.used,
                    'free_bytes': disk_usage.free,
                    'usage_percent': (disk_usage.used / disk_usage.total) * 100,
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0,
                },
                'network': {
                    'bytes_sent': network_io.bytes_sent if network_io else 0,
                    'bytes_recv': network_io.bytes_recv if network_io else 0,
                    'packets_sent': network_io.packets_sent if network_io else 0,
                    'packets_recv': network_io.packets_recv if network_io else 0,
                }
            }
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {'error': str(e)}
    
    def get_database_metrics(self) -> Dict[str, Any]:
        """
        Collect database health metrics.
        
        Returns:
            Dict containing database metrics
        """
        try:
            db_metrics = {}
            
            # Check default database
            db_status = self._check_database_connection('default')
            db_metrics['default'] = db_status
            
            # Get connection pool info
            db_metrics['connections'] = self._get_database_connections()
            
            # Get slow queries (if available)
            db_metrics['slow_queries'] = self._get_slow_queries()
            
            # Database size information
            db_metrics['size_info'] = self._get_database_size_info()
            
            return {'database': db_metrics}
        
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            return {'database': {'error': str(e)}}
    
    def _check_database_connection(self, db_alias: str) -> Dict[str, Any]:
        """Check database connection health."""
        try:
            start_time = timezone.now()
            
            with connections[db_alias].cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            end_time = timezone.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time_ms,
                'connection_alive': True,
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'connection_alive': False,
            }
    
    def _get_database_connections(self) -> Dict[str, Any]:
        """Get database connection pool information."""
        try:
            with connection.cursor() as cursor:
                # PostgreSQL specific queries
                cursor.execute("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                
                result = cursor.fetchone()
                
                return {
                    'total_connections': result[0],
                    'active_connections': result[1],
                    'idle_connections': result[2],
                }
        
        except Exception as e:
            logger.error(f"Error getting database connections: {e}")
            return {'error': str(e)}
    
    def _get_slow_queries(self) -> List[Dict[str, Any]]:
        """Get slow running queries."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pid,
                        now() - pg_stat_activity.query_start AS duration,
                        query,
                        state
                    FROM pg_stat_activity 
                    WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
                    AND state = 'active'
                    ORDER BY duration DESC
                    LIMIT 10
                """)
                
                columns = [col[0] for col in cursor.description]
                slow_queries = []
                
                for row in cursor.fetchall():
                    query_info = dict(zip(columns, row))
                    query_info['duration'] = str(query_info['duration'])
                    slow_queries.append(query_info)
                
                return slow_queries
        
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    def _get_database_size_info(self) -> Dict[str, Any]:
        """Get database size information."""
        try:
            with connection.cursor() as cursor:
                # Get database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                           pg_database_size(current_database()) as db_size_bytes
                """)
                
                db_size_result = cursor.fetchone()
                
                # Get table sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 10
                """)
                
                table_sizes = []
                for row in cursor.fetchall():
                    table_sizes.append({
                        'schema': row[0],
                        'table': row[1],
                        'size': row[2],
                        'size_bytes': row[3],
                    })
                
                return {
                    'database_size': db_size_result[0],
                    'database_size_bytes': db_size_result[1],
                    'largest_tables': table_sizes,
                }
        
        except Exception as e:
            logger.error(f"Error getting database size info: {e}")
            return {'error': str(e)}
    
    def get_redis_metrics(self) -> Dict[str, Any]:
        """
        Collect Redis health metrics.
        
        Returns:
            Dict containing Redis metrics
        """
        try:
            if not self.redis_client:
                return {'redis': {'status': 'unavailable', 'error': 'Redis client not initialized'}}
            
            # Test Redis connection
            start_time = timezone.now()
            self.redis_client.ping()
            end_time = timezone.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Get Redis info
            redis_info = self.redis_client.info()
            
            # Get memory usage
            memory_info = {
                'used_memory_bytes': redis_info.get('used_memory', 0),
                'used_memory_human': redis_info.get('used_memory_human', '0B'),
                'used_memory_peak_bytes': redis_info.get('used_memory_peak', 0),
                'used_memory_peak_human': redis_info.get('used_memory_peak_human', '0B'),
                'maxmemory_bytes': redis_info.get('maxmemory', 0),
                'maxmemory_human': redis_info.get('maxmemory_human', 'unlimited'),
            }
            
            # Calculate memory usage percentage
            if memory_info['maxmemory_bytes'] > 0:
                memory_usage_percent = (memory_info['used_memory_bytes'] / memory_info['maxmemory_bytes']) * 100
            else:
                memory_usage_percent = 0
            
            return {
                'redis': {
                    'status': 'healthy',
                    'response_time_ms': response_time_ms,
                    'version': redis_info.get('redis_version', 'unknown'),
                    'uptime_seconds': redis_info.get('uptime_in_seconds', 0),
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'total_commands_processed': redis_info.get('total_commands_processed', 0),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0),
                    'memory': memory_info,
                    'memory_usage_percent': memory_usage_percent,
                }
            }
        
        except Exception as e:
            logger.error(f"Error collecting Redis metrics: {e}")
            return {'redis': {'status': 'error', 'error': str(e)}}
    
    def get_celery_metrics(self) -> Dict[str, Any]:
        """
        Collect Celery worker health metrics.
        
        Returns:
            Dict containing Celery metrics
        """
        try:
            # Get Celery inspect instance
            inspect = celery_app.control.inspect()
            
            # Get worker statistics
            stats = inspect.stats()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()
            
            # Calculate totals
            total_workers = len(stats) if stats else 0
            total_active_tasks = sum(len(tasks) for tasks in (active_tasks or {}).values())
            total_scheduled_tasks = sum(len(tasks) for tasks in (scheduled_tasks or {}).values())
            total_reserved_tasks = sum(len(tasks) for tasks in (reserved_tasks or {}).values())
            
            # Get queue lengths (if using Redis as broker)
            queue_lengths = self._get_celery_queue_lengths()
            
            return {
                'celery': {
                    'status': 'healthy' if total_workers > 0 else 'warning',
                    'total_workers': total_workers,
                    'worker_stats': stats or {},
                    'active_tasks': {
                        'total': total_active_tasks,
                        'by_worker': active_tasks or {},
                    },
                    'scheduled_tasks': {
                        'total': total_scheduled_tasks,
                        'by_worker': scheduled_tasks or {},
                    },
                    'reserved_tasks': {
                        'total': total_reserved_tasks,
                        'by_worker': reserved_tasks or {},
                    },
                    'queue_lengths': queue_lengths,
                }
            }
        
        except Exception as e:
            logger.error(f"Error collecting Celery metrics: {e}")
            return {'celery': {'status': 'error', 'error': str(e)}}
    
    def _get_celery_queue_lengths(self) -> Dict[str, int]:
        """Get Celery queue lengths from Redis."""
        try:
            if not self.redis_client:
                return {}
            
            # Default Celery queue names
            queue_names = ['celery', 'backup', 'restore', 'notifications']
            queue_lengths = {}
            
            for queue_name in queue_names:
                # Celery uses Redis lists for queues
                queue_key = f"celery:{queue_name}"
                length = self.redis_client.llen(queue_key)
                queue_lengths[queue_name] = length
            
            return queue_lengths
        
        except Exception as e:
            logger.error(f"Error getting Celery queue lengths: {e}")
            return {}
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """
        Collect application-specific metrics.
        
        Returns:
            Dict containing application metrics
        """
        try:
            from zargar.tenants.models import Tenant
            from zargar.tenants.admin_models import SuperAdmin
            
            # Tenant statistics
            total_tenants = Tenant.objects.exclude(schema_name='public').count()
            active_tenants = Tenant.objects.exclude(schema_name='public').filter(is_active=True).count()
            
            # Admin statistics
            total_admins = SuperAdmin.objects.count()
            active_admins = SuperAdmin.objects.filter(is_active=True).count()
            
            # Recent activity
            recent_tenants = Tenant.objects.exclude(schema_name='public').filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            # Cache hit rate
            cache_stats = self._get_cache_hit_rate()
            
            return {
                'application': {
                    'tenants': {
                        'total': total_tenants,
                        'active': active_tenants,
                        'recent_signups': recent_tenants,
                    },
                    'admins': {
                        'total': total_admins,
                        'active': active_admins,
                    },
                    'cache': cache_stats,
                }
            }
        
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return {'application': {'error': str(e)}}
    
    def _get_cache_hit_rate(self) -> Dict[str, Any]:
        """Calculate cache hit rate."""
        try:
            if not self.redis_client:
                return {'status': 'unavailable'}
            
            redis_info = self.redis_client.info()
            keyspace_hits = redis_info.get('keyspace_hits', 0)
            keyspace_misses = redis_info.get('keyspace_misses', 0)
            
            total_requests = keyspace_hits + keyspace_misses
            hit_rate = (keyspace_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'status': 'available',
                'hit_rate_percent': round(hit_rate, 2),
                'total_hits': keyspace_hits,
                'total_misses': keyspace_misses,
                'total_requests': total_requests,
            }
        
        except Exception as e:
            logger.error(f"Error calculating cache hit rate: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _store_metrics(self, metrics: Dict[str, Any]):
        """Store collected metrics in the database."""
        try:
            timestamp = timezone.now()
            
            # Store system metrics
            if 'cpu' in metrics:
                SystemHealthMetric.objects.create(
                    metric_type='cpu_usage',
                    value=metrics['cpu']['usage_percent'],
                    unit='%',
                    hostname=self.hostname,
                    metadata=metrics['cpu']
                )
            
            if 'memory' in metrics:
                SystemHealthMetric.objects.create(
                    metric_type='memory_usage',
                    value=metrics['memory']['usage_percent'],
                    unit='%',
                    hostname=self.hostname,
                    metadata=metrics['memory']
                )
            
            if 'disk' in metrics:
                SystemHealthMetric.objects.create(
                    metric_type='disk_usage',
                    value=metrics['disk']['usage_percent'],
                    unit='%',
                    hostname=self.hostname,
                    metadata=metrics['disk']
                )
            
            # Store database metrics
            if 'database' in metrics and 'default' in metrics['database']:
                db_metrics = metrics['database']['default']
                if 'response_time_ms' in db_metrics:
                    SystemHealthMetric.objects.create(
                        metric_type='response_time',
                        value=db_metrics['response_time_ms'],
                        unit='ms',
                        hostname=self.hostname,
                        metadata={'service': 'database', **db_metrics}
                    )
            
            # Store Redis metrics
            if 'redis' in metrics and metrics['redis']['status'] == 'healthy':
                redis_metrics = metrics['redis']
                
                SystemHealthMetric.objects.create(
                    metric_type='redis_memory',
                    value=redis_metrics['memory_usage_percent'],
                    unit='%',
                    hostname=self.hostname,
                    metadata=redis_metrics
                )
            
            # Store Celery metrics
            if 'celery' in metrics:
                celery_metrics = metrics['celery']
                
                SystemHealthMetric.objects.create(
                    metric_type='celery_workers',
                    value=celery_metrics['total_workers'],
                    unit='count',
                    hostname=self.hostname,
                    metadata=celery_metrics
                )
            
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    def _check_alert_thresholds(self, metrics: Dict[str, Any]):
        """Check metrics against alert thresholds."""
        try:
            # Define thresholds
            thresholds = {
                'cpu_usage': {'warning': 80, 'critical': 95},
                'memory_usage': {'warning': 85, 'critical': 95},
                'disk_usage': {'warning': 85, 'critical': 95},
                'redis_memory': {'warning': 80, 'critical': 90},
                'database_response_time': {'warning': 1000, 'critical': 5000},  # ms
            }
            
            # Check CPU usage
            if 'cpu' in metrics:
                cpu_usage = metrics['cpu']['usage_percent']
                self._check_threshold_alert('cpu_usage', cpu_usage, thresholds['cpu_usage'])
            
            # Check memory usage
            if 'memory' in metrics:
                memory_usage = metrics['memory']['usage_percent']
                self._check_threshold_alert('memory_usage', memory_usage, thresholds['memory_usage'])
            
            # Check disk usage
            if 'disk' in metrics:
                disk_usage = metrics['disk']['usage_percent']
                self._check_threshold_alert('disk_usage', disk_usage, thresholds['disk_usage'])
            
            # Check Redis memory
            if 'redis' in metrics and 'memory_usage_percent' in metrics['redis']:
                redis_memory = metrics['redis']['memory_usage_percent']
                self._check_threshold_alert('redis_memory', redis_memory, thresholds['redis_memory'])
            
            # Check database response time
            if 'database' in metrics and 'default' in metrics['database']:
                db_metrics = metrics['database']['default']
                if 'response_time_ms' in db_metrics:
                    response_time = db_metrics['response_time_ms']
                    self._check_threshold_alert('database_response_time', response_time, thresholds['database_response_time'])
            
            # Check for service availability
            self._check_service_availability(metrics)
            
        except Exception as e:
            logger.error(f"Error checking alert thresholds: {e}")
    
    def _check_threshold_alert(self, metric_name: str, current_value: float, thresholds: Dict[str, float]):
        """Check if a metric exceeds thresholds and create alerts."""
        try:
            severity = None
            threshold_value = None
            
            if current_value >= thresholds['critical']:
                severity = 'critical'
                threshold_value = thresholds['critical']
            elif current_value >= thresholds['warning']:
                severity = 'warning'
                threshold_value = thresholds['warning']
            
            if severity:
                # Check if alert already exists
                existing_alert = SystemHealthAlert.objects.filter(
                    category=metric_name,
                    status='active',
                    severity=severity
                ).first()
                
                if not existing_alert:
                    # Create new alert
                    SystemHealthAlert.objects.create(
                        title=f'{metric_name.replace("_", " ").title()} {severity.title()} Alert',
                        description=f'{metric_name.replace("_", " ").title()} is at {current_value}%, which exceeds the {severity} threshold of {threshold_value}%',
                        severity=severity,
                        category=metric_name,
                        threshold_value=threshold_value,
                        current_value=current_value,
                    )
                    
                    logger.warning(f"Created {severity} alert for {metric_name}: {current_value}% > {threshold_value}%")
            
        except Exception as e:
            logger.error(f"Error checking threshold alert for {metric_name}: {e}")
    
    def _check_service_availability(self, metrics: Dict[str, Any]):
        """Check service availability and create alerts for unavailable services."""
        try:
            services = {
                'database': metrics.get('database', {}).get('default', {}).get('status'),
                'redis': metrics.get('redis', {}).get('status'),
                'celery': metrics.get('celery', {}).get('status'),
            }
            
            for service_name, status in services.items():
                if status in ['error', 'unavailable']:
                    # Check if alert already exists
                    existing_alert = SystemHealthAlert.objects.filter(
                        category=f'{service_name}_availability',
                        status='active'
                    ).first()
                    
                    if not existing_alert:
                        SystemHealthAlert.objects.create(
                            title=f'{service_name.title()} Service Unavailable',
                            description=f'{service_name.title()} service is currently unavailable or experiencing errors',
                            severity='critical',
                            category=f'{service_name}_availability',
                        )
                        
                        logger.error(f"Created critical alert for {service_name} service unavailability")
                
                elif status == 'healthy':
                    # Resolve any existing availability alerts
                    existing_alerts = SystemHealthAlert.objects.filter(
                        category=f'{service_name}_availability',
                        status='active'
                    )
                    
                    for alert in existing_alerts:
                        alert.resolve(
                            user_id=None,
                            username='system',
                            notes=f'{service_name.title()} service is now healthy'
                        )
            
        except Exception as e:
            logger.error(f"Error checking service availability: {e}")
    
    def get_historical_metrics(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get historical metrics for a specific type.
        
        Args:
            metric_type: Type of metric to retrieve
            hours: Number of hours of history to retrieve
            
        Returns:
            List of historical metric data points
        """
        try:
            since = timezone.now() - timedelta(hours=hours)
            
            metrics = SystemHealthMetric.objects.filter(
                metric_type=metric_type,
                timestamp__gte=since
            ).order_by('timestamp')
            
            return [
                {
                    'timestamp': metric.timestamp.isoformat(),
                    'value': metric.value,
                    'unit': metric.unit,
                    'metadata': metric.metadata,
                }
                for metric in metrics
            ]
        
        except Exception as e:
            logger.error(f"Error getting historical metrics for {metric_type}: {e}")
            return []
    
    def get_active_alerts(self) -> List[SystemHealthAlert]:
        """Get all active system health alerts."""
        try:
            return SystemHealthAlert.objects.filter(
                status='active'
            ).order_by('-created_at')
        
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    def cleanup_old_metrics(self, days: int = 30):
        """
        Clean up old metrics to prevent database bloat.
        
        Args:
            days: Number of days of metrics to keep
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            deleted_count = SystemHealthMetric.objects.filter(
                timestamp__lt=cutoff_date
            ).delete()[0]
            
            logger.info(f"Cleaned up {deleted_count} old health metrics")
            
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")


# Global instance
system_health_monitor = SystemHealthMonitor()