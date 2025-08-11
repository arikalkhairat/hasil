#!/usr/bin/env python3
# File: test_size_analysis.py
# Test script untuk menguji analisis ukuran file

import os
from app import get_file_size_info, calculate_file_size_comparison

def test_file_size_analysis():
    """Test fungsi analisis ukuran file"""
    
    print("=== TEST ANALISIS UKURAN FILE ===\n")
    
    # Test file yang ada
    test_files = [
        "app.py",
        "main.py", 
        "requirements.txt",
        "README.md"
    ]
    
    for filename in test_files:
        if os.path.exists(filename):
            print(f"📁 File: {filename}")
            size_info = get_file_size_info(filename)
            print(f"   Ukuran: {size_info['formatted']}")
            print(f"   Detail: {size_info['bytes']} bytes | {size_info['kb']} KB | {size_info['mb']} MB")
            print()
    
    # Test comparison dengan file simulasi
    print("=== TEST PERBANDINGAN UKURAN ===\n")
    
    if os.path.exists("app.py") and os.path.exists("main.py"):
        comparison = calculate_file_size_comparison("app.py", "main.py")
        print("Perbandingan app.py vs main.py:")
        print(f"   File 1: {comparison['original']['formatted']}")
        print(f"   File 2: {comparison['processed']['formatted']}")
        print(f"   Selisih: {comparison['difference_bytes']} bytes")
        print(f"   Persentase: {comparison['difference_percentage']}%")
        print(f"   Status: {comparison['size_change']}")

if __name__ == "__main__":
    test_file_size_analysis()
