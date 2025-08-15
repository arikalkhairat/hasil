#!/usr/bin/env python3
"""
Test script untuk menguji opsi CRC32 pada pembuatan QR Code
"""

import requests
import json

# URL endpoint
BASE_URL = "http://127.0.0.1:5001"
GENERATE_QR_URL = f"{BASE_URL}/generate_qr"

def test_qr_with_crc32():
    """Test QR Code generation dengan CRC32 enabled"""
    print("🧪 Testing QR Code generation dengan CRC32...")
    
    data = {
        'qrData': 'Test data dengan CRC32',
        'useCrc32': 'true'
    }
    
    try:
        response = requests.post(GENERATE_QR_URL, data=data)
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        print(f"CRC32 Enabled: {result.get('crc32_enabled')}")
        
        if result.get('crc32_info'):
            print(f"CRC32 Info: {result['crc32_info']}")
        
        print("✅ Test dengan CRC32 berhasil!\n")
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return None

def test_qr_without_crc32():
    """Test QR Code generation tanpa CRC32"""
    print("🧪 Testing QR Code generation tanpa CRC32...")
    
    data = {
        'qrData': 'Test data tanpa CRC32',
        'useCrc32': 'false'
    }
    
    try:
        response = requests.post(GENERATE_QR_URL, data=data)
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        print(f"CRC32 Enabled: {result.get('crc32_enabled')}")
        
        if result.get('crc32_info'):
            print(f"CRC32 Info: {result['crc32_info']}")
        
        print("✅ Test tanpa CRC32 berhasil!\n")
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return None

if __name__ == "__main__":
    print("🚀 Memulai test CRC32 option functionality...\n")
    
    # Test dengan CRC32
    result_with_crc32 = test_qr_with_crc32()
    
    # Test tanpa CRC32
    result_without_crc32 = test_qr_without_crc32()
    
    # Validasi hasil
    if result_with_crc32 and result_without_crc32:
        print("🔍 Membandingkan hasil...")
        print(f"Dengan CRC32 - Integrity Protected: {result_with_crc32['crc32_info']['integrity_protected']}")
        print(f"Tanpa CRC32 - Integrity Protected: {result_without_crc32['crc32_info']['integrity_protected']}")
        
        if (result_with_crc32['crc32_enabled'] == True and 
            result_without_crc32['crc32_enabled'] == False):
            print("✅ Opsi CRC32 berfungsi dengan baik!")
        else:
            print("❌ Ada masalah dengan opsi CRC32")
    
    print("\n✨ Test selesai!")