#!/usr/bin/env python
"""
Performance monitoring script for POS offline sync system.
Monitors system resources during heavy load testing.
"""
import os
import sys
import time
import json
import psutil
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque


class PerformanceMonitor:
    """Monitor system performance during POS testing."""
    
    def __init__(self, monitoring_duration=300):
        """Initialize performance monitor."""
        self.monitoring_duration = monitoring_duration
        self.is_monitoring = False
        self.metrics = defaultdict(deque)
        self.start_time = None
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start performance monitoring."""
        print(f"🔍 Starting performance monitoring for {self.monitoring_duration}s...")
        
        self.is_monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        print("✅ Performance monitoring stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring and (time.time() - self.start_time) < self.monitoring_duration:
            try:
                timestamp = time.time()
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                
                # Memory metrics
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used_gb = memory.used / (1024**3)
                memory_total_gb = memory.total / (1024**3)
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                disk_used_gb = disk.used / (1024**3)
                disk_total_gb = disk.total / (1024**3)
                
                # Network metrics
                network = psutil.net_io_counters()
                
                # Process metrics (Docker containers)
                docker_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        if 'docker' in proc.info['name'].lower() or 'postgres' in proc.info['name'].lower():
                            docker_processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Store metrics
                self.metrics['timestamp'].append(timestamp)
                self.metrics['cpu_percent'].append(cpu_percent)
                self.metrics['cpu_count'].append(cpu_count)
                self.metrics['memory_percent'].append(memory_percent)
                self.metrics['memory_used_gb'].append(memory_used_gb)
                self.metrics['memory_total_gb'].append(memory_total_gb)
                self.metrics['disk_percent'].append(disk_percent)
                self.metrics['disk_used_gb'].append(disk_used_gb)
                self.metrics['disk_total_gb'].append(disk_total_gb)
                self.metrics['network_bytes_sent'].append(network.bytes_sent)
                self.metrics['network_bytes_recv'].append(network.bytes_recv)
                self.metrics['docker_processes'].append(len(docker_processes))
                
                # Keep only last 1000 measurements
                for key in self.metrics:
                    if len(self.metrics[key]) > 1000:
                        self.metrics[key].popleft()
                
                # Print real-time stats every 30 seconds
                if int(timestamp - self.start_time) % 30 == 0:
                    self._print_current_stats(timestamp)
                
            except Exception as e:
                print(f"⚠️ Monitoring error: {e}")
            
            time.sleep(1)
    
    def _print_current_stats(self, timestamp):
        """Print current performance statistics."""
        elapsed = timestamp - self.start_time
        
        if self.metrics['cpu_percent']:
            current_cpu = self.metrics['cpu_percent'][-1]
            current_memory = self.metrics['memory_percent'][-1]
            current_disk = self.metrics['disk_percent'][-1]
            
            print(f"\n📊 Performance Stats (T+{elapsed:.0f}s):")
            print(f"   CPU: {current_cpu:.1f}% | Memory: {current_memory:.1f}% | Disk: {current_disk:.1f}%")
    
    def get_performance_summary(self):
        """Get performance summary statistics."""
        if not self.metrics['cpu_percent']:
            return None
        
        summary = {
            'monitoring_duration': time.time() - self.start_time if self.start_time else 0,
            'cpu': {
                'avg': sum(self.metrics['cpu_percent']) / len(self.metrics['cpu_percent']),
                'max': max(self.metrics['cpu_percent']),
                'min': min(self.metrics['cpu_percent']),
                'count': self.metrics['cpu_count'][-1] if self.metrics['cpu_count'] else 0
            },
            'memory': {
                'avg_percent': sum(self.metrics['memory_percent']) / len(self.metrics['memory_percent']),
                'max_percent': max(self.metrics['memory_percent']),
                'avg_used_gb': sum(self.metrics['memory_used_gb']) / len(self.metrics['memory_used_gb']),
                'max_used_gb': max(self.metrics['memory_used_gb']),
                'total_gb': self.metrics['memory_total_gb'][-1] if self.metrics['memory_total_gb'] else 0
            },
            'disk': {
                'avg_percent': sum(self.metrics['disk_percent']) / len(self.metrics['disk_percent']),
                'max_percent': max(self.metrics['disk_percent']),
                'total_gb': self.metrics['disk_total_gb'][-1] if self.metrics['disk_total_gb'] else 0
            },
            'network': {
                'total_sent_mb': (self.metrics['network_bytes_sent'][-1] - self.metrics['network_bytes_sent'][0]) / (1024**2) if len(self.metrics['network_bytes_sent']) > 1 else 0,
                'total_recv_mb': (self.metrics['network_bytes_recv'][-1] - self.metrics['network_bytes_recv'][0]) / (1024**2) if len(self.metrics['network_bytes_recv']) > 1 else 0
            },
            'processes': {
                'avg_docker_processes': sum(self.metrics['docker_processes']) / len(self.metrics['docker_processes']) if self.metrics['docker_processes'] else 0
            }
        }
        
        return summary
    
    def print_performance_report(self):
        """Print detailed performance report."""
        summary = self.get_performance_summary()
        
        if not summary:
            print("❌ No performance data available")
            return
        
        print("\n" + "=" * 60)
        print("PERFORMANCE MONITORING REPORT")
        print("=" * 60)
        print(f"Monitoring Duration: {summary['monitoring_duration']:.1f}s")
        print()
        
        print("🖥️ CPU Performance:")
        print(f"   CPU Cores: {summary['cpu']['count']}")
        print(f"   Average Usage: {summary['cpu']['avg']:.1f}%")
        print(f"   Peak Usage: {summary['cpu']['max']:.1f}%")
        print(f"   Minimum Usage: {summary['cpu']['min']:.1f}%")
        print()
        
        print("💾 Memory Performance:")
        print(f"   Total Memory: {summary['memory']['total_gb']:.1f} GB")
        print(f"   Average Usage: {summary['memory']['avg_percent']:.1f}% ({summary['memory']['avg_used_gb']:.1f} GB)")
        print(f"   Peak Usage: {summary['memory']['max_percent']:.1f}% ({summary['memory']['max_used_gb']:.1f} GB)")
        print()
        
        print("💿 Disk Performance:")
        print(f"   Total Disk: {summary['disk']['total_gb']:.1f} GB")
        print(f"   Average Usage: {summary['disk']['avg_percent']:.1f}%")
        print(f"   Peak Usage: {summary['disk']['max_percent']:.1f}%")
        print()
        
        print("🌐 Network Performance:")
        print(f"   Data Sent: {summary['network']['total_sent_mb']:.1f} MB")
        print(f"   Data Received: {summary['network']['total_recv_mb']:.1f} MB")
        print()
        
        print("🐳 Process Performance:")
        print(f"   Average Docker Processes: {summary['processes']['avg_docker_processes']:.1f}")
        print()
        
        # Performance assessment
        self._assess_performance(summary)
    
    def _assess_performance(self, summary):
        """Assess performance and provide recommendations."""
        print("📋 Performance Assessment:")
        
        issues = []
        recommendations = []
        
        # CPU assessment
        if summary['cpu']['avg'] > 80:
            issues.append("High average CPU usage")
            recommendations.append("Consider increasing CPU resources or optimizing code")
        elif summary['cpu']['max'] > 95:
            issues.append("CPU usage spikes detected")
            recommendations.append("Monitor for CPU-intensive operations")
        
        # Memory assessment
        if summary['memory']['avg_percent'] > 85:
            issues.append("High average memory usage")
            recommendations.append("Consider increasing memory or optimizing memory usage")
        elif summary['memory']['max_percent'] > 95:
            issues.append("Memory usage spikes detected")
            recommendations.append("Monitor for memory leaks or optimize data structures")
        
        # Disk assessment
        if summary['disk']['avg_percent'] > 90:
            issues.append("High disk usage")
            recommendations.append("Consider disk cleanup or increasing storage")
        
        if issues:
            print("   ⚠️ Issues Detected:")
            for issue in issues:
                print(f"     - {issue}")
            print()
            print("   💡 Recommendations:")
            for rec in recommendations:
                print(f"     - {rec}")
        else:
            print("   ✅ No performance issues detected")
            print("   🎉 System performed well under load")
        
        print()
    
    def save_metrics_to_file(self, filename=None):
        """Save metrics to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pos_performance_metrics_{timestamp}.json'
        
        # Convert deque to list for JSON serialization
        metrics_dict = {}
        for key, values in self.metrics.items():
            metrics_dict[key] = list(values)
        
        summary = self.get_performance_summary()
        
        data = {
            'summary': summary,
            'raw_metrics': metrics_dict,
            'generated_at': datetime.now().isoformat()
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"📁 Performance metrics saved to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Failed to save metrics: {e}")
            return None


def monitor_docker_containers():
    """Monitor Docker container performance."""
    print("\n🐳 Docker Container Status:")
    
    try:
        import subprocess
        
        # Get container stats
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Failed to get Docker stats")
            
    except Exception as e:
        print(f"❌ Docker monitoring error: {e}")


def main():
    """Main monitoring function."""
    print("=" * 60)
    print("POS OFFLINE SYNC - PERFORMANCE MONITOR")
    print("=" * 60)
    
    # Check if monitoring should run
    if len(sys.argv) > 1:
        if sys.argv[1] == '--duration':
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        else:
            duration = int(sys.argv[1])
    else:
        duration = 300  # Default 5 minutes
    
    print(f"Monitoring duration: {duration}s ({duration/60:.1f} minutes)")
    
    # Initialize monitor
    monitor = PerformanceMonitor(monitoring_duration=duration)
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        
        # Monitor Docker containers periodically
        docker_monitor_interval = 60  # Every minute
        last_docker_check = 0
        
        # Wait for monitoring to complete
        while monitor.is_monitoring:
            current_time = time.time()
            
            # Check Docker containers periodically
            if current_time - last_docker_check >= docker_monitor_interval:
                monitor_docker_containers()
                last_docker_check = current_time
            
            time.sleep(10)  # Check every 10 seconds
        
        # Stop monitoring
        monitor.stop_monitoring()
        
        # Generate report
        monitor.print_performance_report()
        
        # Save metrics
        filename = monitor.save_metrics_to_file()
        
        print(f"\n🎯 Performance monitoring completed successfully!")
        if filename:
            print(f"📊 Detailed metrics saved to: {filename}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Monitoring interrupted by user")
        monitor.stop_monitoring()
        monitor.print_performance_report()
    
    except Exception as e:
        print(f"\n💥 Monitoring failed: {e}")
        monitor.stop_monitoring()


if __name__ == '__main__':
    main()