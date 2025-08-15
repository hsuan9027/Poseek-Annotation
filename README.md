# Poseek Annotation Tool

A pose annotation tool for labeling keypoints in images (e.g., human joints, animal body parts). It supports custom keypoint configurations, provides an intuitive visualization interface, and can export annotation data in multiple formats.

## Features

- **Custom Keypoint Configuration**: Define your own keypoints and connections
- **Intuitive Interface**: Easy-to-use GUI with real-time visualization
- **Multiple Export Formats**: CSV and COCO format support
- **Keyboard Shortcuts**: Efficient annotation workflow
- **Dark Theme**: Modern, eye-friendly interface

## Installation

### Prerequisites

- Python 3.9+
- Conda (recommended) or pip

### Quick Start

1. **Clone the repository**:
```bash
git clone https://github.com/hsuan9027/Poseek_Annotation.git
cd Poseek_Annotation
```

2. **Create conda environment** (recommended):
```bash
conda create -n poseek python=3.9 -y
conda activate poseek
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Run the application**:
```bash
python run.py
```

## Usage

### Basic Workflow

1. **Configure Keypoints**: Click "Edit Keypoints" to set up your annotation schema
2. **Load Images**: Select a folder containing your images
3. **Annotate**: Click on images or press `F` to add keypoints
4. **Save**: Press `Ctrl+S` to save annotations
5. **Navigate**: Use `D` for next image, `A` for previous

### Keyboard Shortcuts

- `F` - Add point at cursor position
- `D` - Next image
- `A` - Previous image
- `Ctrl+S` - Save annotations
- `Delete` - Delete selected points
- `Escape` - Clear selection
- `Arrow Keys` - Navigate view

### Configuration Example

```yaml
Mouse Pose:
  name: Mouse Pose
  bodyparts:
    - head
    - left_ear
    - right_ear
    - neck
    - back
    - tail_base
    - tail_end
  connections:
    - [0, 3]  # head to neck
    - [3, 4]  # neck to back
    - [4, 5]  # back to tail_base
    - [5, 6]  # tail_base to tail_end
```

## Output Formats

### CSV Format
```csv
filename,head_x,head_y,left_ear_x,left_ear_y,...
image001.jpg,100.5,200.3,150.2,180.7,...
```

### COCO Format
Standard COCO JSON format compatible with deep learning frameworks.

## Requirements

- PySide6>=6.5.0 (GUI framework)
- PyYAML>=6.0 (Configuration files)
- pandas>=1.5.0 (Data processing)
- Pillow>=9.0.0 (Image processing)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this tool in your research, please consider citing:

```bibtex
@software{poseek_annotation_tool,
  title={Poseek Annotation Tool},
  author={Your Name},
  year={2025},
  url={https://github.com/YOUR_USERNAME/Poseek_Annotation}
}
```

## Support

- 🐛 [Report Issues](https://github.com/YOUR_USERNAME/Poseek_Annotation/issues)
- 💬 [Discussions](https://github.com/YOUR_USERNAME/Poseek_Annotation/discussions)
- 📧 Email: your.email@example.com

---

**Star ⭐ this repository if it helped you!**