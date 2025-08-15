#!/usr/bin/env python3
"""
Test script untuk memvalidasi perbaikan yang telah dilakukan:
1. Windows compatibility
2. Image display issues  
3. File size optimization
"""

import os
import sys
import logging
from pathlib import Path
import tempfile
import shutil
from PIL import Image
import json

# Add current directory to path untuk import
sys.path.insert(0, str(Path(__file__).parent))

from app import (
    generate_image_url, 
    safe_subprocess_run, 
    get_file_size_info, 
    analyze_file_size_impact,
    BASE_DIR,
    UPLOAD_FOLDER,
    GENERATED_FOLDER
)

# Setup logging untuk test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_windows_compatibility():
    """Test pathlib dan subprocess compatibility"""
    print("\n🔧 Testing Windows Compatibility...")
    
    # Test 1: Path handling dengan pathlib
    try:
        test_path = BASE_DIR / 'test_path'
        assert isinstance(test_path, Path), "BASE_DIR should be Path object"
        print("✅ Path handling with pathlib: OK")
    except Exception as e:
        print(f"❌ Path handling failed: {e}")
        return False
    
    # Test 2: URL generation cross-platform
    try:
        url = generate_image_url("test\\folder", "test\\file.png")
        expected = "/static/generated/test/folder/test/file.png"
        assert url == expected, f"Expected {expected}, got {url}"
        print("✅ Cross-platform URL generation: OK")
    except Exception as e:
        print(f"❌ URL generation failed: {e}")
        return False
    
    # Test 3: Safe subprocess (mock test)
    try:
        # Test dengan command sederhana yang pasti ada
        result = safe_subprocess_run(['python', '--version'])
        assert result['success'] == True, "Python version check should succeed"
        print("✅ Safe subprocess execution: OK")
    except Exception as e:
        print(f"❌ Safe subprocess failed: {e}")
        return False
    
    return True

def test_image_display_fixes():
    """Test perbaikan image display"""
    print("\n🖼️ Testing Image Display Fixes...")
    
    # Test 1: URL generation consistency
    test_cases = [
        ("folder", "file.png", "/static/generated/folder/file.png"),
        ("sub\\folder", "image.jpg", "/static/generated/sub/folder/image.jpg"),
        ("path/with/slash", "test.png", "/static/generated/path/with/slash/test.png")
    ]
    
    for folder, filename, expected in test_cases:
        try:
            result = generate_image_url(folder, filename)
            assert result == expected, f"Expected {expected}, got {result}"
        except Exception as e:
            print(f"❌ URL generation test failed for {folder}/{filename}: {e}")
            return False
    
    print("✅ Image URL generation: OK")
    
    # Test 2: Directory structure
    try:
        assert UPLOAD_FOLDER.exists(), "Upload folder should exist"
        assert GENERATED_FOLDER.exists(), "Generated folder should exist"
        print("✅ Directory structure: OK")
    except Exception as e:
        print(f"❌ Directory structure test failed: {e}")
        return False
    
    return True

def test_file_size_optimization():
    """Test optimasi ukuran file"""
    print("\n📊 Testing File Size Optimization...")
    
    # Create test image untuk test
    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            # Buat test image sederhana
            test_img = Image.new('RGB', (100, 100), color='white')
            test_img.save(tmp.name, 'PNG')
            test_file1 = tmp.name
            
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            # Buat test image kedua dengan ukuran sedikit berbeda
            test_img = Image.new('RGB', (100, 100), color='red')
            test_img.save(tmp.name, 'PNG', optimize=True)
            test_file2 = tmp.name
        
        # Test file size analysis
        analysis = analyze_file_size_impact(test_file1, test_file2)
        
        required_keys = ['original_size', 'processed_size', 'size_change_ratio', 'recommendation']
        for key in required_keys:
            assert key in analysis, f"Missing key in analysis: {key}"
        
        assert 'status' in analysis['recommendation'], "Recommendation should have status"
        print("✅ File size analysis: OK")
        
        # Test file size info
        file_info = get_file_size_info(test_file1)
        required_info_keys = ['bytes', 'kb', 'mb', 'formatted']
        for key in required_info_keys:
            assert key in file_info, f"Missing key in file info: {key}"
        
        print("✅ File size info generation: OK")
        
        # Cleanup
        os.unlink(test_file1)
        os.unlink(test_file2)
        
    except Exception as e:
        print(f"❌ File size optimization test failed: {e}")
        return False
    
    return True

def test_error_handling():
    """Test error handling improvements"""
    print("\n🛡️ Testing Error Handling...")
    
    # Test 1: Safe subprocess dengan command yang tidak ada
    try:
        result = safe_subprocess_run(['nonexistent_command_12345'])
        assert result['success'] == False, "Non-existent command should fail safely"
        assert 'error' in result, "Should return error information"
        print("✅ Safe subprocess error handling: OK")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    # Test 2: File size analysis dengan file tidak ada
    try:
        analysis = analyze_file_size_impact('nonexistent1.txt', 'nonexistent2.txt')
        assert 'error' in analysis, "Should handle missing files gracefully"
        print("✅ File analysis error handling: OK")
    except Exception as e:
        print(f"❌ File analysis error handling failed: {e}")
        return False
    
    return True

def run_comprehensive_test():
    """Jalankan semua test"""
    print("🚀 Running Comprehensive Fix Validation Tests...")
    print("=" * 60)
    
    tests = [
        ("Windows Compatibility", test_windows_compatibility),
        ("Image Display Fixes", test_image_display_fixes), 
        ("File Size Optimization", test_file_size_optimization),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n❌ FAILED: {test_name} - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All fixes validated successfully!")
        print("✅ Windows compatibility: Fixed")
        print("✅ Image display issues: Fixed")  
        print("✅ File size optimization: Implemented")
        print("✅ Error handling: Enhanced")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)