#!/usr/bin/env python3
# Test script untuk menguji implementasi PDF via DOCX conversion

import os
import tempfile
import shutil
from pdf_utils import convert_pdf_to_docx, convert_docx_to_pdf, embed_watermark_to_pdf_via_docx

def test_conversion_basic():
    """Test basic PDF to DOCX and back to PDF conversion"""
    print("=== Test Basic PDF ↔ DOCX Conversion ===")
    
    # Buat PDF dummy untuk test
    test_pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Simpan PDF test
        test_pdf_path = os.path.join(temp_dir, "test.pdf")
        with open(test_pdf_path, "wb") as f:
            f.write(test_pdf_content)
        
        # Test PDF → DOCX
        docx_path = os.path.join(temp_dir, "test.docx")
        result = convert_pdf_to_docx(test_pdf_path, docx_path)
        
        print(f"PDF → DOCX: {result.get('success', False)}")
        if not result.get('success'):
            print(f"Error: {result.get('message', 'Unknown error')}")
            return False
        
        # Test DOCX → PDF
        output_pdf_path = os.path.join(temp_dir, "test_output.pdf")
        result = convert_docx_to_pdf(docx_path, output_pdf_path)
        
        print(f"DOCX → PDF: {result.get('success', False)}")
        if not result.get('success'):
            print(f"Error: {result.get('message', 'Unknown error')}")
            return False
        
        print("✓ Basic conversion test passed")
        return True

def test_library_imports():
    """Test apakah semua library yang diperlukan dapat diimport"""
    print("=== Test Library Imports ===")
    
    try:
        from pdf2docx import Converter
        print("✓ pdf2docx import OK")
    except ImportError as e:
        print(f"✗ pdf2docx import failed: {e}")
        return False
    
    try:
        from docx2pdf import convert
        print("✓ docx2pdf import OK")
    except ImportError as e:
        print(f"✗ docx2pdf import failed: {e}")
        return False
    
    print("✓ All library imports passed")
    return True

def main():
    """Run all tests"""
    print("🧪 Testing PDF via DOCX Implementation\n")
    
    tests = [
        test_library_imports,
        test_conversion_basic
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Test Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    main()