# QR Code LSB Watermarking - Pixel Viewer Enhancement

## 📋 Overview
Enhancement untuk menampilkan detail pixel dari gambar yang telah diproses watermarking, memungkinkan pengguna untuk melihat perubahan pixel secara visual dan numerik.

## 🎯 Tujuan Enhancement
1. **Visual Pixel Grid** - Menampilkan grid pixel dengan zoom untuk melihat perubahan LSB
2. **Pixel Value Comparison** - Membandingkan nilai RGB sebelum dan sesudah watermarking
3. **Interactive Pixel Inspector** - Klik pada pixel untuk melihat detail nilai
4. **Heatmap Visualization** - Visualisasi area yang mengalami perubahan
5. **Bit-level Analysis** - Menampilkan perubahan pada level bit LSB

## 🚀 Fitur yang Akan Ditambahkan

### 1. Pixel Grid Viewer
- Canvas-based pixel grid dengan zoom controls
- Hover untuk melihat nilai pixel
- Side-by-side comparison (Original vs Watermarked)

### 2. Pixel Analysis Panel
- RGB value breakdown
- Binary representation
- LSB changes highlighted
- Delta values

### 3. Interactive Features
- Region selection untuk analisis area tertentu
- Export pixel data ke CSV
- Histogram perbandingan
- Bit plane visualization

## 📝 TODO List

### Phase 1: Backend Enhancement
- [ ] Endpoint untuk mendapatkan pixel data dari region tertentu
- [ ] Fungsi untuk ekstrak bit planes
- [ ] API untuk pixel-by-pixel comparison
- [ ] Cache mechanism untuk performa

### Phase 2: Frontend Development
- [ ] Implementasi Canvas-based pixel viewer
- [ ] Zoom & pan controls
- [ ] Pixel tooltip on hover
- [ ] Color channel toggles (R/G/B)

### Phase 3: Analysis Tools
- [ ] Difference map visualization
- [ ] Statistical analysis per region
- [ ] LSB pattern detection
- [ ] Watermark density heatmap

### Phase 4: UI/UX Improvements
- [ ] Responsive design untuk pixel viewer
- [ ] Keyboard shortcuts
- [ ] Export functionality
- [ ] Print-friendly view

## 🛠️ Technical Implementation

### Backend API Endpoints

```python
# New endpoints to add in app.py

@app.route('/api/pixel_data/<image_id>/<int:x>/<int:y>/<int:width>/<int:height>')
def get_pixel_region(image_id, x, y, width, height):
    """Get pixel data for a specific region"""
    pass

@app.route('/api/bit_planes/<image_id>/<channel>')
def get_bit_planes(image_id, channel):
    """Extract bit planes for visualization"""
    pass

@app.route('/api/pixel_diff/<original_id>/<watermarked_id>')
def get_pixel_difference(original_id, watermarked_id):
    """Calculate pixel-wise differences"""
    pass
```

### Frontend Components

```javascript
// PixelViewer.js
class PixelViewer {
    constructor(canvas, imageData) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.imageData = imageData;
        this.zoom = 10; // 10x zoom default
        this.offset = {x: 0, y: 0};
    }
    
    drawPixelGrid() {
        // Implementation
    }
    
    getPixelInfo(x, y) {
        // Return RGB values and bit representation
    }
}

// PixelComparison.js
class PixelComparison {
    constructor(originalViewer, watermarkedViewer) {
        this.original = originalViewer;
        this.watermarked = watermarkedViewer;
    }
    
    syncViewports() {
        // Sync zoom and position
    }
    
    highlightDifferences() {
        // Highlight changed pixels
    }
}
```

## 📊 Mockup Design

```
+------------------------------------------------------------------+
|                    Pixel Analysis Dashboard                       |
+------------------------------------------------------------------+
| Original Image              | Watermarked Image                   |
| +-------------------------+ | +-------------------------+        |
| |                         | | |                         |        |
| |    [Canvas Grid]        | | |    [Canvas Grid]        |        |
| |                         | | |                         |        |
| +-------------------------+ | +-------------------------+        |
| Zoom: [-----|----] 10x      | Zoom: [-----|----] 10x            |
+------------------------------------------------------------------+
| Pixel Inspector                                                   |
| Position: (125, 87)                                              |
| +------------------------------------------------------------------+
| |          | Original      | Watermarked  | Difference           |
| |----------|---------------|--------------|---------------------|
| | Red      | 218 (11011010)| 218 (11011010)| 0                  |
| | Green    | 165 (10100101)| 165 (10100101)| 0                  |
| | Blue     | 32  (00100000)| 33  (00100001)| +1 (LSB changed)   |
| +------------------------------------------------------------------+
| LSB Analysis: Blue channel modified from 0 to 1                  |
+------------------------------------------------------------------+
```

## 🔧 Development