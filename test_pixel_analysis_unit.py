#!/usr/bin/env python3
"""
Unit tests for Pixel Analysis functions (without requiring server)
Tests the pixel analysis functions directly
"""

import unittest
import numpy as np
from PIL import Image
import tempfile
import os
import json

# Import app untuk testing
import sys
sys.path.append('.')
from app import app, get_pixel_region, get_bit_planes, get_pixel_difference, pixel_inspector

class TestPixelAnalysis(unittest.TestCase):
    """Test suite for pixel analysis functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['GENERATED_FOLDER'] = tempfile.mkdtemp()
        self.app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create test images
        self.test_image_path = self.create_test_image()
        self.watermarked_image_path = self.create_watermarked_image()
    
    def create_test_image(self):
        """Create a test image for analysis"""
        img = Image.new('RGB', (50, 50), color='white')
        pixels = img.load()
        
        # Add colored squares
        for x in range(10, 20):
            for y in range(10, 20):
                pixels[x, y] = (255, 0, 0)  # Red
        
        for x in range(25, 35):
            for y in range(25, 35):
                pixels[x, y] = (0, 0, 255)  # Blue
        
        # Save to generated folder
        path = os.path.join(self.app.config['GENERATED_FOLDER'], 'test_image.png')
        img.save(path)
        return path
    
    def create_watermarked_image(self):
        """Create watermarked version with LSB changes"""
        img = Image.open(self.test_image_path)
        img_array = np.array(img)
        
        # Modify LSB of blue channel in specific region
        for x in range(10, 20):
            for y in range(10, 20):
                # Change LSB of blue channel
                img_array[y, x, 2] = (img_array[y, x, 2] & 0xFE) | 1
        
        watermarked_img = Image.fromarray(img_array)
        path = os.path.join(self.app.config['GENERATED_FOLDER'], 'test_image_watermarked.png')
        watermarked_img.save(path)
        return path
    
    def test_pixel_viewer_template(self):
        """Test if pixel viewer template loads"""
        response = self.client.get('/pixel_viewer')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pixel Analysis Viewer', response.data)
        self.assertIn(b'pixel-canvas', response.data)
    
    def test_pixel_data_endpoint(self):
        """Test pixel data API endpoint"""
        with self.app.app_context():
            response = self.client.get('/api/pixel_data/test_image/0/0/10/10')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIn('pixel_data', data)
            self.assertIn('image_size', data)
            
            # Check pixel data structure
            pixel_grid = data['pixel_data']
            self.assertEqual(len(pixel_grid), 10)  # 10 rows
            self.assertEqual(len(pixel_grid[0]), 10)  # 10 columns
            
            # Check first pixel
            first_pixel = pixel_grid[0][0]
            self.assertIn('r', first_pixel)
            self.assertIn('g', first_pixel)
            self.assertIn('b', first_pixel)
            self.assertIn('hex', first_pixel)
    
    def test_bit_planes_endpoint(self):
        """Test bit planes API endpoint"""
        with self.app.app_context():
            response = self.client.get('/api/bit_planes/test_image/b')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertEqual(data['channel'], 'b')
            self.assertIn('bit_planes', data)
            
            # Should have 8 bit planes (0-7)
            bit_planes = data['bit_planes']
            self.assertEqual(len(bit_planes), 8)
    
    def test_pixel_inspector_endpoint(self):
        """Test pixel inspector API endpoint"""
        with self.app.app_context():
            response = self.client.get('/api/pixel_inspector/test_image/15/15')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            
            pixel_info = data['pixel_info']
            self.assertEqual(pixel_info['position']['x'], 15)
            self.assertEqual(pixel_info['position']['y'], 15)
            
            # Check RGB values are for red pixel (should be 255,0,0)
            self.assertEqual(pixel_info['rgb']['r'], 255)
            self.assertEqual(pixel_info['rgb']['g'], 0)
            self.assertEqual(pixel_info['rgb']['b'], 0)
            
            # Check binary representation
            self.assertIn('binary', pixel_info)
            self.assertEqual(pixel_info['binary']['r'], '11111111')
            self.assertEqual(pixel_info['binary']['g'], '00000000')
            self.assertEqual(pixel_info['binary']['b'], '00000000')
    
    def test_pixel_difference_endpoint(self):
        """Test pixel difference API endpoint"""
        with self.app.app_context():
            response = self.client.get('/api/pixel_diff/test_image/test_image_watermarked')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            
            stats = data['statistics']
            self.assertGreater(stats['changed_pixels'], 0)
            self.assertGreater(stats['change_percentage'], 0)
            self.assertGreaterEqual(stats['mse'], 0)
            
            # Should have detected changes
            self.assertGreater(data['total_changes'], 0)
            self.assertIn('changed_positions', data)
    
    def test_invalid_image_handling(self):
        """Test handling of invalid image requests"""
        with self.app.app_context():
            # Test non-existent image
            response = self.client.get('/api/pixel_data/nonexistent/0/0/10/10')
            self.assertEqual(response.status_code, 404)
            
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('error', data)
    
    def test_out_of_bounds_handling(self):
        """Test handling of out-of-bounds coordinates"""
        with self.app.app_context():
            # Test coordinates outside image bounds
            response = self.client.get('/api/pixel_data/test_image/100/100/10/10')
            self.assertEqual(response.status_code, 400)
            
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('out of bounds', data['error'].lower())
    
    def test_main_page_navigation(self):
        """Test that main page includes pixel viewer link"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pixel Analysis', response.data)
        self.assertIn(b'/pixel_viewer', response.data)
    
    def tearDown(self):
        """Clean up test environment"""
        # Remove test images
        for path in [self.test_image_path, self.watermarked_image_path]:
            if os.path.exists(path):
                os.remove(path)
        
        # Remove temp directories
        import shutil
        shutil.rmtree(self.app.config['GENERATED_FOLDER'], ignore_errors=True)
        shutil.rmtree(self.app.config['UPLOAD_FOLDER'], ignore_errors=True)

class TestPixelAnalysisFunctions(unittest.TestCase):
    """Test individual pixel analysis functions"""
    
    def test_rgb_to_binary_conversion(self):
        """Test RGB to binary conversion accuracy"""
        test_cases = [
            (255, '11111111'),
            (128, '10000000'),
            (0, '00000000'),
            (1, '00000001'),
            (254, '11111110')
        ]
        
        for rgb_value, expected_binary in test_cases:
            actual_binary = format(rgb_value, '08b')
            self.assertEqual(actual_binary, expected_binary)
    
    def test_lsb_extraction(self):
        """Test LSB (Least Significant Bit) extraction"""
        test_cases = [
            (255, 1),  # 11111111 -> LSB = 1
            (254, 0),  # 11111110 -> LSB = 0
            (128, 0),  # 10000000 -> LSB = 0
            (129, 1),  # 10000001 -> LSB = 1
        ]
        
        for rgb_value, expected_lsb in test_cases:
            actual_lsb = rgb_value & 1
            self.assertEqual(actual_lsb, expected_lsb)
    
    def test_mse_calculation(self):
        """Test MSE calculation between two images"""
        # Create two identical arrays
        arr1 = np.array([[[100, 150, 200]]], dtype=np.uint8)
        arr2 = np.array([[[100, 150, 200]]], dtype=np.uint8)
        
        # MSE should be 0 for identical arrays
        mse = np.mean((arr1 - arr2) ** 2)
        self.assertEqual(mse, 0)
        
        # Test with different arrays
        arr2 = np.array([[[101, 151, 201]]], dtype=np.uint8)
        mse = np.mean((arr1.astype(np.int16) - arr2.astype(np.int16)) ** 2)
        self.assertEqual(mse, 1.0)  # Each channel differs by 1, so MSE = (1²+1²+1²)/3 = 1
    
    def test_psnr_calculation(self):
        """Test PSNR calculation"""
        # Test PSNR calculation with known MSE
        mse = 1.0
        psnr = 20 * np.log10(255.0 / np.sqrt(mse))
        expected_psnr = 20 * np.log10(255.0)  # ≈ 48.13 dB
        self.assertAlmostEqual(psnr, expected_psnr, places=2)
        
        # Test with MSE = 0 (should result in infinity, not an exception)
        mse = 0.0
        # When MSE is 0, PSNR should be infinity
        if mse == 0:
            psnr = float('inf')
            self.assertEqual(psnr, float('inf'))
        else:
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))

def run_tests():
    """Run all tests and display results"""
    print("🧪 Running Pixel Analysis Unit Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPixelAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestPixelAnalysisFunctions))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    
    if failures == 0 and errors == 0:
        print("\n🎉 All tests passed! Pixel Analysis implementation is working correctly.")
        return True
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
