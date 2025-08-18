#!/usr/bin/env python3
"""
Test script for Pixel Analysis API endpoints
Tests the new pixel viewer enhancement features
"""

import requests
import json
import time
from PIL import Image
import numpy as np
import os

# Configuration
BASE_URL = "http://localhost:5001"
TEST_IMAGE_SIZE = (100, 100)
TEST_IMAGE_PATH = "test_pixel_image.png"

def create_test_image():
    """Create a test image for pixel analysis"""
    # Create a simple test image
    img = Image.new('RGB', TEST_IMAGE_SIZE, color='white')
    pixels = img.load()
    
    # Add some colored pixels for testing
    for x in range(10, 20):
        for y in range(10, 20):
            pixels[x, y] = (255, 0, 0)  # Red square
    
    for x in range(30, 40):
        for y in range(30, 40):
            pixels[x, y] = (0, 255, 0)  # Green square
    
    for x in range(50, 60):
        for y in range(50, 60):
            pixels[x, y] = (0, 0, 255)  # Blue square
    
    img.save(TEST_IMAGE_PATH)
    print(f"✅ Created test image: {TEST_IMAGE_PATH}")
    return TEST_IMAGE_PATH

def create_watermarked_test_image():
    """Create a watermarked version of test image"""
    img = Image.open(TEST_IMAGE_PATH)
    img_array = np.array(img)
    
    # Simulate LSB watermarking on blue channel
    for x in range(20, 30):
        for y in range(20, 30):
            # Modify LSB of blue channel
            original_blue = img_array[y, x, 2]
            img_array[y, x, 2] = (original_blue & 0xFE) | 1  # Set LSB to 1
    
    watermarked_img = Image.fromarray(img_array)
    watermarked_path = "test_pixel_image_watermarked.png"
    watermarked_img.save(watermarked_path)
    print(f"✅ Created watermarked test image: {watermarked_path}")
    return watermarked_path

def test_pixel_data_api():
    """Test the pixel data API endpoint"""
    print("\n🧪 Testing Pixel Data API...")
    
    # Copy test image to static folder for API access
    import shutil
    os.makedirs("static/generated", exist_ok=True)
    shutil.copy(TEST_IMAGE_PATH, "static/generated/test_pixel_image.png")
    
    try:
        response = requests.get(f"{BASE_URL}/api/pixel_data/test_pixel_image/0/0/20/20")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ Pixel Data API working")
                print(f"   - Image size: {data['image_size']}")
                print(f"   - Region: {data['region']}")
                print(f"   - Pixel grid size: {len(data['pixel_data'])}x{len(data['pixel_data'][0])}")
                
                # Check first pixel data
                first_pixel = data['pixel_data'][0][0]
                print(f"   - First pixel: RGB({first_pixel['r']}, {first_pixel['g']}, {first_pixel['b']})")
                return True
            else:
                print(f"❌ API returned error: {data['error']}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - make sure Flask app is running")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_bit_planes_api():
    """Test the bit planes API endpoint"""
    print("\n🧪 Testing Bit Planes API...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/bit_planes/test_pixel_image/b")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ Bit Planes API working")
                print(f"   - Channel: {data['channel']}")
                print(f"   - Bit planes count: {len(data['bit_planes'])}")
                print(f"   - LSB plane size: {len(data['bit_planes'][0])}x{len(data['bit_planes'][0][0])}")
                return True
            else:
                print(f"❌ API returned error: {data['error']}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_pixel_inspector_api():
    """Test the pixel inspector API endpoint"""
    print("\n🧪 Testing Pixel Inspector API...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/pixel_inspector/test_pixel_image/15/15")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ Pixel Inspector API working")
                pixel_info = data['pixel_info']
                print(f"   - Position: ({pixel_info['position']['x']}, {pixel_info['position']['y']})")
                print(f"   - RGB: ({pixel_info['rgb']['r']}, {pixel_info['rgb']['g']}, {pixel_info['rgb']['b']})")
                print(f"   - Hex: {pixel_info['hex']}")
                print(f"   - Binary R: {pixel_info['binary']['r']}")
                print(f"   - LSB Values: R={pixel_info['lsb']['r']}, G={pixel_info['lsb']['g']}, B={pixel_info['lsb']['b']}")
                return True
            else:
                print(f"❌ API returned error: {data['error']}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_pixel_diff_api():
    """Test the pixel difference API endpoint"""
    print("\n🧪 Testing Pixel Difference API...")
    
    # Copy watermarked image to static folder
    watermarked_path = create_watermarked_test_image()
    import shutil
    shutil.copy(watermarked_path, "static/generated/test_pixel_image_watermarked.png")
    
    try:
        response = requests.get(f"{BASE_URL}/api/pixel_diff/test_pixel_image/test_pixel_image_watermarked")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ Pixel Difference API working")
                stats = data['statistics']
                print(f"   - Total pixels: {stats['total_pixels']}")
                print(f"   - Changed pixels: {stats['changed_pixels']}")
                print(f"   - Change percentage: {stats['change_percentage']:.4f}%")
                print(f"   - MSE: {stats['mse']:.4f}")
                print(f"   - PSNR: {stats['psnr']}")
                print(f"   - Changes detected: {data['total_changes']}")
                
                if data['changed_positions']:
                    first_change = data['changed_positions'][0]
                    print(f"   - First change at: ({first_change['x']}, {first_change['y']})")
                    print(f"     Original: RGB({first_change['original']['r']}, {first_change['original']['g']}, {first_change['original']['b']})")
                    print(f"     Watermarked: RGB({first_change['watermarked']['r']}, {first_change['watermarked']['g']}, {first_change['watermarked']['b']})")
                
                return True
            else:
                print(f"❌ API returned error: {data['error']}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_pixel_viewer_page():
    """Test the pixel viewer web page"""
    print("\n🧪 Testing Pixel Viewer Web Page...")
    
    try:
        response = requests.get(f"{BASE_URL}/pixel_viewer")
        
        if response.status_code == 200:
            print("✅ Pixel Viewer page loads successfully")
            
            # Check if key elements are in the HTML
            html_content = response.text
            checks = [
                ("Canvas elements", "pixel-canvas" in html_content),
                ("JavaScript class", "PixelViewer" in html_content),
                ("API endpoints", "/api/pixel_data" in html_content),
                ("Zoom controls", "zoom-btn" in html_content),
                ("Pixel inspector", "pixel-inspector" in html_content)
            ]
            
            for check_name, result in checks:
                status = "✅" if result else "❌"
                print(f"   {status} {check_name}")
            
            return all(result for _, result in checks)
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def cleanup_test_files():
    """Clean up test files"""
    test_files = [
        TEST_IMAGE_PATH,
        "test_pixel_image_watermarked.png",
        "static/generated/test_pixel_image.png",
        "static/generated/test_pixel_image_watermarked.png"
    ]
    
    for file_path in test_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️ Could not remove {file_path}: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Pixel Analysis API Tests")
    print("=" * 50)
    
    # Create test images
    create_test_image()
    
    # Test results
    results = []
    
    # Run tests
    tests = [
        ("Pixel Viewer Page", test_pixel_viewer_page),
        ("Pixel Data API", test_pixel_data_api),
        ("Bit Planes API", test_bit_planes_api),
        ("Pixel Inspector API", test_pixel_inspector_api),
        ("Pixel Difference API", test_pixel_diff_api)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Pixel Analysis enhancement is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    cleanup_test_files()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
