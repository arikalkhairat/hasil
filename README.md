# QR Code LSB Watermarking System

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Overview

Sistem watermarking dokumen menggunakan teknik **LSB (Least Significant Bit) Steganography** untuk menyisipkan QR Code ke dalam gambar yang terdapat dalam dokumen DOCX dan PDF. Sistem ini dilengkapi dengan **Pixel Analysis Viewer** untuk analisis detail perubahan pixel.

### 🌟 Key Features

- **QR Code Generation** - Pembuat QR Code dengan CRC32 checksum protection
- **Document Watermarking** - Embed QR Code ke dokumen DOCX/PDF menggunakan LSB
- **Pixel Analysis Viewer** - Tool analisis pixel yang komprehensif ✨ NEW!
- **Quality Metrics** - Perhitungan MSE, PSNR, dan file size impact
- **Cross-platform Support** - Compatible dengan Windows, macOS, dan Linux

## 🚀 Features

### 1. QR Code Generation
- Generate QR Code dengan data custom
- CRC32 checksum untuk integrity protection
- Timestamp encoding untuk tracking
- PNG output dengan transparency support

### 2. Document Watermarking
- **DOCX Support** - Extract dan embed watermark ke gambar dalam dokumen
- **PDF Support** - Convert PDF ke gambar, watermark, dan reconstruct
- **LSB Steganography** - Modifikasi bit terakhir channel biru
- **Minimal Visual Impact** - Perubahan pixel ±1 saja

### 3. 🔬 Pixel Analysis Viewer (NEW!)
- **Interactive Pixel Grid** - Zoom dan inspect pixel individual
- **Side-by-side Comparison** - Bandingkan gambar asli vs watermarked
- **Bit-level Analysis** - Visualisasi bit planes dan LSB changes
- **Real-time Statistics** - MSE, PSNR, change percentage
- **RGB Value Inspector** - Detail nilai RGB dan binary representation

### 4. Quality Metrics
- **File Size Analysis** - Perbandingan ukuran file sebelum/sesudah
- **Visual Quality** - MSE dan PSNR calculation
- **Statistical Reports** - Comprehensive quality assessment

## 📦 Installation

### Prerequisites
- Python 3.8 atau lebih tinggi
- pip package manager

### 1. Clone Repository
```bash
git clone https://github.com/arikalkhairat/hasil.git
cd hasil
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python app.py
```

Aplikasi akan berjalan di `http://localhost:5001` (atau port yang tersedia)

## 🛠️ Dependencies

```
Flask>=2.0.0
Pillow>=8.0.0
numpy>=1.20.0
python-docx>=0.8.11
qrcode>=7.0
pyzbar>=0.1.8
opencv-python>=4.5.0
PyPDF2>=2.0.0
pdf2image>=1.16.0
```

## 📖 Usage

### 1. Generate QR Code
1. Masuk ke tab "Buat QR Code"
2. Input data yang ingin di-encode
3. Enable CRC32 checksum (recommended)
4. Download QR Code yang dihasilkan

### 2. Embed Watermark
1. Masuk ke tab "Embed Watermark"
2. Upload dokumen DOCX/PDF
3. Upload QR Code
4. Proses embedding akan berjalan otomatis
5. Download dokumen yang sudah di-watermark

### 3. Validate Document
1. Masuk ke tab "Validasi Dokumen"
2. Upload dokumen yang sudah di-watermark
3. Sistem akan extract dan validate QR Code
4. View hasil validasi dan quality metrics

### 4. 🔬 Pixel Analysis (NEW!)
1. Klik link **"Pixel Analysis"** di header
2. Input ID gambar asli dan watermarked
3. Load kedua gambar
4. Gunakan fitur:
   - **Zoom Controls** - Perbesar/perkecil view
   - **Pixel Inspector** - Klik pixel untuk detail
   - **Compare Images** - Statistik perbandingan
   - **Bit Analysis** - Visualisasi perubahan LSB

## 🎨 Pixel Analysis Features

### Interactive Pixel Grid
```
┌─────────────────────────────────────┐
│  Original Image    Watermarked Image│
│ ┌─────────────────┐ ┌─────────────────┐│
│ │ [Pixel Grid]    │ │ [Pixel Grid]    ││
│ │ 10x Zoom        │ │ 10x Zoom        ││
│ └─────────────────┘ └─────────────────┘│
│ [Zoom Controls]     [Zoom Controls]    │
└─────────────────────────────────────┘
```

### Pixel Inspector Output
```
Position: (125, 87)
┌──────────────────────────────────────┐
│          │ Original  │ Watermarked │ Diff │
│──────────│───────────│─────────────│──────│
│ Red      │ 218 (11011010)│ 218 (11011010)│  0   │
│ Green    │ 165 (10100101)│ 165 (10100101)│  0   │
│ Blue     │ 32  (00100000)│ 33  (00100001)│ +1   │
└──────────────────────────────────────┘
LSB Analysis: Blue channel LSB changed from 0 to 1
```

## 🔧 Technical Implementation

### LSB Steganography Process
1. **Extract Images** - Extract semua gambar dari dokumen
2. **Resize QR Code** - Sesuaikan ukuran dengan kapasitas gambar
3. **Bit Conversion** - Convert QR Code ke binary data
4. **LSB Embedding** - Modify LSB of blue channel
5. **Image Reconstruction** - Rebuild gambar dengan data tersembunyi
6. **Document Assembly** - Masukkan kembali ke dokumen

### Quality Assessment
```python
# MSE Calculation
mse = np.mean((original - watermarked) ** 2)

# PSNR Calculation  
psnr = 10 * log10(255.0^2 / mse)

# Quality Rating
if psnr > 40: quality = "Excellent"
elif psnr > 30: quality = "Very Good"  
elif psnr > 20: quality = "Good"
else: quality = "Poor"
```

## 📊 API Endpoints

### Pixel Analysis API
- `GET /api/pixel_data/<image_id>/<x>/<y>/<width>/<height>` - Get pixel region data
- `GET /api/bit_planes/<image_id>/<channel>` - Extract bit planes
- `GET /api/pixel_diff/<original_id>/<watermarked_id>` - Pixel comparison
- `GET /api/pixel_inspector/<image_id>/<x>/<y>` - Detailed pixel info

### Core API
- `POST /generate_qr` - Generate QR Code
- `POST /embed_docx` - Embed watermark to document
- `POST /extract_docx` - Extract and validate watermark
- `POST /validate_qr_integrity` - Validate QR Code integrity

## 📈 Performance Metrics

### Typical Results
- **File Size Impact**: < 5% increase
- **Visual Quality**: PSNR > 30dB (Very Good)
- **Processing Speed**: ~2-5 seconds per document
- **Detection Accuracy**: > 99% with CRC32

### Quality Categories
| PSNR Range | File Size Impact | Quality Rating |
|------------|------------------|----------------|
| > 40 dB    | < 1%            | Excellent      |
| 30-40 dB   | 1-3%            | Very Good      |
| 20-30 dB   | 3-5%            | Good           |
| < 20 dB    | > 5%            | Poor           |

## 🧪 Testing

### Run Tests
```bash
# Test basic functionality
python test_fixes.py

# Test file size analysis
python test_file_size.py

# Test CRC32 functionality  
python test_crc32_option.py

# Test PDF processing
python test_pdf.py
```

### Test Coverage
- ✅ QR Code generation and validation
- ✅ DOCX watermarking and extraction
- ✅ PDF processing pipeline
- ✅ File size impact analysis
- ✅ CRC32 integrity checking
- ✅ Pixel analysis API endpoints

## 📁 Project Structure

```
hasil/
├── app.py                 # Flask application server
├── main.py               # Core watermarking logic  
├── lsb_steganography.py  # LSB embedding algorithms
├── qr_utils.py           # QR Code utilities & CRC32
├── pdf_utils.py          # PDF processing functions
├── templates/
│   ├── index.html        # Main web interface
│   └── pixel_viewer.html # Pixel analysis interface
├── static/
│   ├── uploads/          # Temporary file uploads
│   └── generated/        # Generated files
├── public/
│   └── documents/        # Processed documents
├── tests/
│   ├── test_fixes.py     # Core functionality tests
│   ├── test_file_size.py # File size analysis tests
│   └── test_*.py         # Other test modules
└── docs/
    ├── README.md         # This file
    ├── update.md         # Enhancement roadmap
    └── FEATURE_*.md      # Feature documentation
```

## 🔄 Recent Updates (v2.0)

### ✨ New Features
- 🔬 **Pixel Analysis Viewer** - Interactive pixel inspection tool
- 📊 **Enhanced Statistics** - Comprehensive quality metrics
- 🎨 **Bit Plane Visualization** - Visual representation of LSB changes
- 🔍 **Real-time Comparison** - Side-by-side pixel analysis
- 📈 **API Endpoints** - RESTful API for pixel data access

### 🐛 Bug Fixes
- ✅ Windows path compatibility issues
- ✅ Image display problems in web interface
- ✅ File size calculation accuracy
- ✅ Memory management improvements

### 🚀 Performance Improvements
- ⚡ Faster image processing pipeline
- 💾 Optimized memory usage
- 🔄 Better error handling and recovery
- 📱 Responsive design for mobile devices

## 🛣️ Roadmap

### Phase 1: Core Enhancement ✅
- [x] Backend API endpoints for pixel analysis
- [x] Basic pixel viewer interface
- [x] Zoom and navigation controls
- [x] Pixel inspector functionality

### Phase 2: Advanced Analysis (In Progress)
- [ ] Histogram comparison tools
- [ ] LSB pattern detection algorithms
- [ ] Watermark density heatmaps
- [ ] Export analysis reports (PDF/CSV)

### Phase 3: User Experience
- [ ] Batch processing capabilities  
- [ ] Advanced filtering options
- [ ] Keyboard shortcuts
- [ ] Mobile-optimized interface

### Phase 4: Security & Performance
- [ ] Multi-threading support
- [ ] Advanced encryption options
- [ ] Cloud storage integration
- [ ] API rate limiting

## 👥 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/AmazingFeature`
3. Commit changes: `git commit -m 'Add AmazingFeature'`
4. Push to branch: `git push origin feature/AmazingFeature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Arikal Khairat**
- GitHub: [@arikalkhairat](https://github.com/arikalkhairat)
- Email: arikal.khairat@example.com

## 🙏 Acknowledgments

- Flask framework untuk web development
- Pillow library untuk image processing
- OpenCV untuk computer vision operations
- NumPy untuk numerical computations
- QRCode library untuk QR code generation

## 📞 Support

Jika Anda mengalami masalah atau memiliki pertanyaan:

1. 📋 Check [Issues](https://github.com/arikalkhairat/hasil/issues) 
2. 📖 Read the documentation
3. 💬 Start a [Discussion](https://github.com/arikalkhairat/hasil/discussions)
4. 📧 Contact the author

---

⭐ **Star this repo** if you find it helpful!

**Happy Watermarking! 🎉**
```bash
install.bat
```

**Linux/Mac:**
```bash
./install.sh
```

**Manual Installation:**
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Starting the Application

Run the application with:

```bash
# Activate the virtual environment (if not already activated)
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Start the application
python app.py
```

The application will start and be accessible at [http://localhost:5000](http://localhost:5000) in your web browser.

### Using the Web Interface

The application has four main functions:

1. **Generate QR Code**:
   - Enter your data
   - Click "Generate QR Code"
   - QR codes are automatically generated with CRC32 checksum for integrity protection
   - Download the generated QR code with built-in data validation

2. **Embed Watermark**:
   - Select a DOCX document
   - Select a QR code image (with or without CRC32 checksum)
   - Click "Embed Watermark"
   - Download the watermarked document

3. **Validate Document**:
   - Select a DOCX document
   - Click "Validate Document"
   - View extracted QR codes (if any)

4. **Validate QR Code Integrity**:
   - Select a QR code image
   - Click "Validate Integrity CRC32"
   - Verify if the QR code data has been modified or corrupted
   - View original data, checksum status, and creation timestamp

## Technical Details

### CRC32 Checksum Integration

All QR codes generated by this tool now include CRC32 checksums for data integrity validation:

- **Automatic Protection**: Every new QR code includes a CRC32 checksum and timestamp
- **Data Format**: QR codes contain JSON data: `{"data": "original_text", "crc32": checksum_value, "timestamp": unix_timestamp}`
- **Integrity Validation**: Verify if QR code data has been modified or corrupted
- **Backward Compatibility**: Legacy QR codes without checksums are still supported
- **Security Enhancement**: Provides an additional layer of data validation

### LSB Steganography

This tool implements LSB (Least Significant Bit) steganography, which works by replacing the least significant bit of each color channel with a bit of the data to be hidden. Since the least significant bit has the smallest impact on the color value, changes are virtually imperceptible to the human eye.

The implementation:
- Uses only the blue channel (less sensitive to the human eye)
- Includes dimension information in the header
- Automatically resizes QR codes if necessary to fit image capacity
- Calculates quality metrics (MSE, PSNR) to quantify the impact
- Supports both traditional QR codes and new CRC32-protected QR codes

### Image Quality Metrics

- **MSE (Mean Squared Error)**: Measures the average squared difference between the original and watermarked images.
- **PSNR (Peak Signal-to-Noise Ratio)**: Measures the ratio between the maximum possible power of a signal and the power of corrupting noise.
  - PSNR > 40 dB: Excellent quality
  - PSNR > 30 dB: Very good quality
  - PSNR > 20 dB: Good quality
  - PSNR < 20 dB: Poor quality

## Troubleshooting

### Common Issues

- **No images found**: Ensure your DOCX document contains images
- **Error during extraction**: The document may not contain watermarked images
- **Low PSNR values**: Image quality may be too low for effective watermarking
- **CRC32 validation failed**: QR code data may be corrupted or modified - try with the original QR code
- **Legacy QR code**: Old QR codes without CRC32 checksums will show as "format lama" but still work

### Support

For issues or questions, please open an issue on the GitHub repository or contact the developer at your.email@example.com.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Created by Arikal Khairat
- Built with Python, Flask, and modern web technologies
- Uses LSB steganography techniques for secure watermarking 
