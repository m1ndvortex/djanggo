#!/usr/bin/env python3
"""
Verification script for Reports UI implementation.
Checks that all required files and content are properly implemented.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and return result."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (NOT FOUND)")
        return False

def check_content_in_file(file_path, content_list, description):
    """Check if specific content exists in a file."""
    if not os.path.exists(file_path):
        print(f"❌ {description}: File not found - {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        found_content = []
        missing_content = []
        
        for content in content_list:
            if content in file_content:
                found_content.append(content)
            else:
                missing_content.append(content)
        
        if missing_content:
            print(f"⚠️  {description}: Missing content - {missing_content}")
            return False
        else:
            print(f"✅ {description}: All required content found")
            return True
            
    except Exception as e:
        print(f"❌ {description}: Error reading file - {e}")
        return False

def main():
    """Main verification function."""
    print("🔍 Verifying Reports UI Implementation")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    results = []
    
    # 1. Check Template Files
    print("\n📄 Checking Template Files:")
    template_dir = base_dir / "templates" / "reports"
    
    required_templates = [
        ("dashboard.html", "Reports Dashboard Template"),
        ("generate.html", "Report Generation Template"),
        ("list.html", "Report List Template"),
        ("detail.html", "Report Detail Template"),
    ]
    
    for template_file, description in required_templates:
        template_path = template_dir / template_file
        results.append(check_file_exists(template_path, description))
    
    # Check preview templates
    preview_dir = template_dir / "previews"
    preview_templates = [
        ("trial_balance.html", "Trial Balance Preview Template"),
        ("inventory_valuation.html", "Inventory Valuation Preview Template"),
    ]
    
    for template_file, description in preview_templates:
        template_path = preview_dir / template_file
        results.append(check_file_exists(template_path, description))
    
    # Check schedule templates
    schedule_dir = template_dir / "schedules"
    schedule_templates = [
        ("list.html", "Schedule List Template"),
    ]
    
    for template_file, description in schedule_templates:
        template_path = schedule_dir / template_file
        results.append(check_file_exists(template_path, description))
    
    # 2. Check Static Files
    print("\n🎨 Checking Static Files:")
    static_dir = base_dir / "static"
    
    required_static_files = [
        ("css/reports.css", "Reports CSS File"),
        ("js/reports-dashboard.js", "Reports Dashboard JavaScript"),
        ("js/reports-generator.js", "Reports Generator JavaScript"),
    ]
    
    for static_file, description in required_static_files:
        static_path = static_dir / static_file
        results.append(check_file_exists(static_path, description))
    
    # 3. Check Persian Content in Templates
    print("\n🇮🇷 Checking Persian Content:")
    
    # Check dashboard template for Persian content
    dashboard_path = template_dir / "dashboard.html"
    persian_content = [
        "گزارش",
        "داشبورد",
        "تولید",
        "persian-numbers",
        'dir="rtl"'
    ]
    results.append(check_content_in_file(
        dashboard_path, persian_content, "Persian Content in Dashboard"
    ))
    
    # Check generate template for Persian content
    generate_path = template_dir / "generate.html"
    generate_persian_content = [
        "تولید گزارش جدید",
        "انتخاب نوع گزارش",
        "بازه زمانی گزارش",
        "از تاریخ (شمسی)",
        "تا تاریخ (شمسی)"
    ]
    results.append(check_content_in_file(
        generate_path, generate_persian_content, "Persian Content in Generate Form"
    ))
    
    # 4. Check Theme Support
    print("\n🎨 Checking Theme Support:")
    
    # Check CSS for theme support
    css_path = static_dir / "css" / "reports.css"
    theme_content = [
        "cyber-bg-primary",
        "cyber-text-primary",
        "cyber-neon-primary",
        ".dark",
        ".light"
    ]
    results.append(check_content_in_file(
        css_path, theme_content, "Theme Support in CSS"
    ))
    
    # Check templates for theme classes
    theme_template_content = [
        "is_dark_mode",
        "cyber-bg-primary",
        "cyber-text-primary"
    ]
    results.append(check_content_in_file(
        dashboard_path, theme_template_content, "Theme Support in Templates"
    ))
    
    # 5. Check RTL Support
    print("\n➡️ Checking RTL Support:")
    
    rtl_content = [
        'dir="rtl"',
        "text-right",
        "space-x-reverse",
        "Vazirmatn"
    ]
    results.append(check_content_in_file(
        dashboard_path, rtl_content, "RTL Support in Templates"
    ))
    
    # Check CSS for RTL support
    rtl_css_content = [
        "rtl",
        "text-right",
        "Vazirmatn",
        "persian-numbers"
    ]
    results.append(check_content_in_file(
        css_path, rtl_css_content, "RTL Support in CSS"
    ))
    
    # 6. Check JavaScript Functionality
    print("\n⚙️ Checking JavaScript Functionality:")
    
    # Check dashboard JavaScript
    dashboard_js_path = static_dir / "js" / "reports-dashboard.js"
    dashboard_js_content = [
        "ReportsDashboard",
        "persian",
        "initializePersianNumbers",
        "toPersianNumbers"
    ]
    results.append(check_content_in_file(
        dashboard_js_path, dashboard_js_content, "Dashboard JavaScript Functionality"
    ))
    
    # Check generator JavaScript
    generator_js_path = static_dir / "js" / "reports-generator.js"
    generator_js_content = [
        "ReportsGenerator",
        "generateReport",
        "monitorReportProgress",
        "PersianDate"
    ]
    results.append(check_content_in_file(
        generator_js_path, generator_js_content, "Generator JavaScript Functionality"
    ))
    
    # 7. Check Export Functionality
    print("\n📤 Checking Export Functionality:")
    
    # Check detail template for export options
    detail_path = template_dir / "detail.html"
    export_content = [
        "دانلود گزارش",
        "دانلود PDF",
        "دانلود Excel",
        "دانلود CSV"
    ]
    results.append(check_content_in_file(
        detail_path, export_content, "Export Options in Detail Template"
    ))
    
    # 8. Check Responsive Design
    print("\n📱 Checking Responsive Design:")
    
    responsive_content = [
        "md:grid-cols",
        "lg:grid-cols",
        "sm:flex",
        "@media"
    ]
    results.append(check_content_in_file(
        css_path, responsive_content, "Responsive Design in CSS"
    ))
    
    # 9. Check Form Validation
    print("\n✅ Checking Form Validation:")
    
    validation_content = [
        "validateForm",
        "validateField",
        "showNotification",
        "error-message"
    ]
    results.append(check_content_in_file(
        generator_js_path, validation_content, "Form Validation in JavaScript"
    ))
    
    # 10. Check Accessibility
    print("\n♿ Checking Accessibility:")
    
    accessibility_content = [
        "aria-label",
        "<label",
        "for=",
        "alt="
    ]
    results.append(check_content_in_file(
        generate_path, accessibility_content, "Accessibility Features"
    ))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    total_checks = len(results)
    passed_checks = sum(results)
    failed_checks = total_checks - passed_checks
    
    print(f"Total Checks: {total_checks}")
    print(f"✅ Passed: {passed_checks}")
    print(f"❌ Failed: {failed_checks}")
    print(f"Success Rate: {(passed_checks/total_checks)*100:.1f}%")
    
    if failed_checks == 0:
        print("\n🎉 ALL CHECKS PASSED! Reports UI implementation is complete.")
        return 0
    elif passed_checks >= total_checks * 0.8:
        print("\n⚠️  Most checks passed. Minor issues need attention.")
        return 1
    else:
        print("\n❌ Several checks failed. Implementation needs significant work.")
        return 2

if __name__ == "__main__":
    sys.exit(main())